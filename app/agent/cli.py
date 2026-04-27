"""
vcenter_agent.py
================
Multi-provider AI agent REPL for VMware vCenter administration.
Uses the shared agent engine (multi-turn, govc, web search) with CLI confirmation
for dangerous operations. Supports Anthropic, OpenAI, Gemini, and Grok.
"""

import os
import json
import time
from dotenv import load_dotenv

import app.tools.vcenter as vc

from app.agent import engine
from app.agent.prompts import vcenter_system_cli, build_system
from app.agent.safety import VCENTER_DESTRUCTIVE
from app.agent.config import get_max_tokens, get_max_turns
from app.llm.factory import get_provider, list_configured_providers

load_dotenv()

MAX_RETRIES = 3


# ─────────────────────────────────────────────
# Safety Confirmation
# ─────────────────────────────────────────────

def _confirm_destructive(tool_name: str, tool_input: dict) -> bool:
    print(f"\n[!] CONFIRMATION REQUIRED: {tool_name}")
    print(f"    Parameters: {json.dumps(tool_input, indent=4)}")
    answer = input("    Type 'yes' to confirm, anything else to cancel: ").strip().lower()
    return answer == "yes"


# ─────────────────────────────────────────────
# AI Agent
# ─────────────────────────────────────────────

class VCenterAgent:
    def __init__(self, provider_id: str | None = None, model: str | None = None):
        self.provider_id = (provider_id or os.environ.get("AGENT_PROVIDER") or "anthropic").lower()
        self.provider = get_provider(self.provider_id)
        if not self.provider.is_configured():
            configured = [p for p in list_configured_providers() if p["configured"]]
            if configured:
                fallback = configured[0]["id"]
                print(f"[warn] {self.provider_id} not configured. Falling back to {fallback}.")
                self.provider_id = fallback
                self.provider = get_provider(self.provider_id)
            else:
                raise RuntimeError(
                    "No LLM provider is configured. Set one of MOONSHOT_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY / XAI_API_KEY."
                )
        self.model = model or os.environ.get("AGENT_MODEL") or self.provider.default_model

        self.history: list[dict] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.skip_confirmations = False

    def set_provider(self, provider_id: str) -> None:
        inst = get_provider(provider_id.lower())
        if not inst.is_configured():
            raise RuntimeError(f"{provider_id} not configured (missing {inst.env_key}).")
        self.provider_id = provider_id.lower()
        self.provider = inst
        self.model = inst.default_model
        print(f"[info] provider={self.provider_id} model={self.model}")

    def set_model(self, model: str) -> None:
        self.model = model
        print(f"[info] model={self.model}")

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                reply = self._agent_loop()
                self.history.append({"role": "assistant", "content": reply})
                return reply
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise
                wait = 2**attempt
                print(f"\n[retrying in {wait}s after error: {e}]")
                time.sleep(wait)
        raise RuntimeError("Max retries exceeded.")

    def reset(self) -> None:
        self.history = []
        print("[conversation reset]\n")

    def print_usage(self) -> None:
        total = self.total_input_tokens + self.total_output_tokens
        print("\n-- Token Usage --")
        print(f"  Input:  {self.total_input_tokens}")
        print(f"  Output: {self.total_output_tokens}")
        print(f"  Total:  {total}\n")

    def _confirm_wrapper(self, tool_name: str, tool_input: dict) -> bool:
        if self.skip_confirmations:
            return True
        return _confirm_destructive(tool_name, tool_input)

    def _agent_loop(self) -> str:
        messages = list(self.history)
        buf: list[str] = []
        last_summary = ""
        final_text = ""

        for ev in engine.stream_agent_events(
            self.provider,
            build_system(vcenter_system_cli()),
            messages,
            model=self.model,
            max_tokens=get_max_tokens(),
            max_turns=get_max_turns(),
            on_reload_modules=False,
            cli_confirm=self._confirm_wrapper,
        ):
            et = ev.get("type")
            if et == "iteration":
                buf.clear()
            elif et == "text":
                chunk = ev.get("content", "")
                print(chunk, end="", flush=True)
                buf.append(chunk)
            elif et == "planner":
                plan = ev.get("content", "")
                print(f"\n--- Auto plan ---\n{plan}\n---\n")
            elif et == "tool_call":
                print(f"\n  [tool] {ev.get('tool')} {json.dumps(ev.get('args'), indent=2)[:400]}")
            elif et == "busy":
                print(f"\n  […] {ev.get('message') or ev.get('phase', '')}\n")
            elif et == "checkpoint":
                line = ev.get("summary") or ""
                if ev.get("llm_note"):
                    line += " — " + str(ev["llm_note"])
                if ev.get("plan_steps_estimate") is not None:
                    line += f" [plan ~{ev['plan_steps_estimate']} steps]"
                print(f"\n  [checkpoint] {line}\n")
            elif et == "tool_result":
                preview = str(ev.get("result", ""))[:300]
                ctag = " (cached)" if ev.get("cached") else ""
                print(f"    -> {preview}...{ctag}")
            elif et == "report":
                print("\n  (Report section generated)\n")
            elif et == "reviewer":
                rtxt = ev.get("text", "")
                if rtxt:
                    print(f"\n--- Peer review ---\n{rtxt}\n")
            elif et == "reflection":
                print(f"\n  [reflection] {ev.get('nudge', '')}\n")
            elif et == "error":
                print(f"\n  [error] {ev.get('error', 'error')}")
            elif et == "usage":
                self.total_input_tokens += int(ev.get("input_tokens", 0) or 0)
                self.total_output_tokens += int(ev.get("output_tokens", 0) or 0)
            elif et == "done":
                final_text = (ev.get("full_text") or "").strip() or ev.get("summary") or ""
                last_summary = ev.get("summary") or ""
                break

        out = (final_text or "").strip() or "".join(buf)
        return out if out.strip() else (last_summary or "")


# ─────────────────────────────────────────────
# Auto-connect helper
# ─────────────────────────────────────────────

def _startup_connect():
    host = os.environ.get("VCENTER_HOST")
    user = os.environ.get("VCENTER_USER")
    pwd = os.environ.get("VCENTER_PASSWORD")
    if host and user and pwd:
        print(f"Auto-connecting to vCenter: {host} ...")
        print(vc.connect_vcenter(host, user, pwd))
    else:
        print("[info] No VCENTER_* env vars found. Use connect_vcenter or the dashboard to connect.")


# ─────────────────────────────────────────────
# Interactive REPL
# ─────────────────────────────────────────────

HELP_TEXT = f"""
Commands:
  reset          clear conversation history
  usage/tokens   show token usage
  noconfirm      skip safety confirmations
  confirm        re-enable safety confirmations
  provider X     switch to provider X (anthropic|openai|kimi|gemini|grok)
  model Y        switch to model Y for current provider
  providers      list configured providers
  quit/exit      exit

Tools: pyVmomi vCenter, govc (if installed), web_search (if TAVILY_API_KEY set).
Confirmations are prompted for: {", ".join(sorted(VCENTER_DESTRUCTIVE))} and destructive govc subcommands.
"""


def main():
    print("=" * 60)
    print("  vCenter AI Admin Agent  (multi-provider)")
    print("=" * 60)

    agent = VCenterAgent()
    print(f"[provider={agent.provider_id} model={agent.model}]")
    _startup_connect()
    print(HELP_TEXT)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        lo = user_input.lower()

        if lo in ("quit", "exit", "bye"):
            print("Goodbye!")
            break
        if lo in ("reset", "clear"):
            agent.reset()
            continue
        if lo in ("usage", "tokens"):
            agent.print_usage()
            continue
        if lo == "noconfirm":
            agent.skip_confirmations = True
            print("[safety OFF]")
            continue
        if lo == "confirm":
            agent.skip_confirmations = False
            print("[safety ON]")
            continue
        if lo == "providers":
            for p in list_configured_providers():
                print(f"  - {p['id']:<10s} {'configured' if p['configured'] else 'no key'}   (default: {p['default_model']})")
            continue
        if lo.startswith("provider "):
            try:
                agent.set_provider(user_input.split(None, 1)[1].strip())
            except Exception as e:
                print(f"[error] {e}")
            continue
        if lo.startswith("model "):
            agent.set_model(user_input.split(None, 1)[1].strip())
            continue
        if lo == "help":
            print(HELP_TEXT)
            continue

        try:
            print()
            agent.chat(user_input)
            print()
        except Exception as e:
            print(f"\n[Error: {e}]")

    agent.print_usage()


if __name__ == "__main__":
    main()
