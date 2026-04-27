"""
Shared multi-step, multi-provider tool loop for web (SSE) and CLI.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Callable, Generator, Optional

from app.agent.config import (
    entity_cache_enabled,
    get_max_tokens,
    get_max_turns,
    get_reflection_max_nudges,
    get_reviewer_min_tool_turns,
    get_summary_interval,
    minitask_llm_enabled,
    planner_enabled,
    reflection_enabled,
    reviewer_enabled,
    rolling_summary_enabled,
    tool_cache_enabled,
)
from app.agent.entity_cache import EntityCache
from app.agent.safety import is_read_only, needs_cli_confirmation
from app.llm.base import LLMProvider, NormalizedMessage, StepResult
from app.tools.combined import build_combined_tools, execute_combined, reload_all_tools

log = logging.getLogger(__name__)

PLANNER_SYSTEM = """You are a planning module for a VMware vCenter admin assistant.
Read the human message describing a task and output a short execution plan as **JSON only** — no prose, no markdown fences, no commentary.

Schema:
{"steps": [{"id": <int>, "type": "query"|"mutate"|"report", "tool": "<optional tool name>", "desc": "<one short sentence>"}]}

Rules:
- 1 to 8 steps. IDs start at 1 and increase by 1.
- type=query  → read-only inspection (list_*, get_*, govc info, web_search).
- type=mutate → any change to vCenter (power, snapshot, clone, delete, maintenance mode, etc.).
- type=report → final summary or emit_session_report.
- Be specific to VMware / vCenter where relevant.
- If the request is a single trivial question, return one step with type=report.
- Output ONLY the JSON object."""

REFLECTION_SYSTEM = """You are a strict task monitor for a vCenter admin assistant.
Read the user task and a short summary of the last tool results.
Output exactly two lines, no other text.
Line 1: exactly one of these tokens — COMPLETE, NEEDS_MORE_TOOLS, NEEDS_HUMAN
Line 2: a short message:
  - COMPLETE → the word done
  - NEEDS_MORE_TOOLS → one short sentence telling the assistant what to do next
  - NEEDS_HUMAN → one short sentence stating exactly what the operator must clarify or approve
Do not use tools.

Pick NEEDS_HUMAN when the task is blocked on a human decision (ambiguous target VM, missing credentials, destructive op needs explicit go-ahead, or contradictory requirements). Otherwise pick NEEDS_MORE_TOOLS or COMPLETE."""

REVIEWER_SYSTEM = """You are a quality reviewer for a VMware vCenter admin assistant.
Read the user request and the assistant's final answer. Do not use tools.

First, answer this vCenter checklist with one short line each (yes/no plus a justification):
1. Did the agent verify every VM/host/datastore name it referenced?
2. Did it check alarm state and overall status where relevant?
3. Were destructive operations confirmed and reported?
4. Did it cite tool results for every claim about inventory state?

Then output a short markdown block (3-6 bullets): **Strengths**, **Gaps**, and one **Follow-up** for the operator."""

MINITASK_SYSTEM = """You summarize one agent turn for a vCenter administrator.
Read the user task excerpt and a short JSON excerpt of tools just executed and their results.
Output exactly one concise sentence (max 40 words): what was accomplished this turn.
No tools, no markdown, no bullet points, no numbered list."""

ROLLING_SUMMARY_SYSTEM = """You are a context-compression assistant for a VMware vCenter agent.
Summarize the following conversation turns into one concise paragraph (max 300 words).
Focus on: what was discovered, key values (VM names, host names, counts, IP addresses, error states, actions taken).
Do not reproduce tool call syntax or raw JSON. Output plain prose only."""


def _normalize_for_cache(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _normalize_for_cache(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [_normalize_for_cache(x) for x in obj]
    return obj


def _tool_cache_key(tool_name: str, inp: dict) -> str:
    payload = {"tool": tool_name, "args": _normalize_for_cache(inp or {})}
    return json.dumps(payload, sort_keys=True, default=str)


_VALID_PLAN_TYPES = ("query", "mutate", "report")


def _parse_plan_json(text: str) -> dict | None:
    """Extract and validate a planner JSON object. Returns the dict or None on failure."""
    if not (text or "").strip():
        return None
    try:
        obj = json.loads(text)
    except Exception:
        # Pull the first {...} block out and try again.
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return None
    if not isinstance(obj, dict):
        return None
    steps = obj.get("steps")
    if not isinstance(steps, list) or not steps:
        return None
    cleaned: list[dict] = []
    for i, raw in enumerate(steps, start=1):
        if not isinstance(raw, dict):
            continue
        step_type = str(raw.get("type", "")).strip().lower()
        if step_type not in _VALID_PLAN_TYPES:
            continue
        desc = str(raw.get("desc", "")).strip()
        if not desc:
            continue
        try:
            sid = int(raw.get("id", i))
        except Exception:
            sid = i
        out: dict = {"id": sid, "type": step_type, "desc": desc[:300]}
        tool = raw.get("tool")
        if isinstance(tool, str) and tool.strip():
            out["tool"] = tool.strip()[:80]
        cleaned.append(out)
    if not cleaned:
        return None
    return {"steps": cleaned}


def _plan_to_markdown(plan_obj: dict) -> str:
    """Render a parsed plan dict as a markdown numbered list for UI display."""
    lines: list[str] = []
    for step in plan_obj.get("steps", []):
        sid = step.get("id", "?")
        stype = step.get("type", "?")
        tool = step.get("tool")
        desc = step.get("desc", "")
        suffix = f" — `{tool}`" if tool else ""
        lines.append(f"{sid}. [{stype}] {desc}{suffix}")
    return "\n".join(lines)


def _estimate_plan_steps_markdown(plan_markdown: str) -> int | None:
    """Fallback: count numbered list items in a markdown plan."""
    if not (plan_markdown or "").strip():
        return None
    n = len(re.findall(r"^\s*\d+\.\s", plan_markdown, re.MULTILINE))
    return n if n > 0 else None


def _build_plan_system_block(plan_obj: dict) -> str:
    """Embed the JSON plan as a machine-readable block to prepend to the system prompt each turn."""
    plan_json = json.dumps(plan_obj, separators=(",", ":"))
    return (
        "## Execution plan (machine-readable)\n"
        "Follow the plan below. Tick steps off as you complete them and reference each `step.id` in your reasoning. "
        "Run `query` steps with read tools, `mutate` steps with write tools (after confirming any destructive op), "
        "and `report` steps with a final summary or `emit_session_report`.\n"
        f"```json\n{plan_json}\n```\n"
    )


def _deterministic_checkpoint_summary(
    turn_1based: int, max_turns: int, runs: list[tuple[str, bool]]
) -> str:
    if not runs:
        return f"Turn {turn_1based}/{max_turns}: (no tools)"
    parts: list[str] = []
    i = 0
    n = len(runs)
    while i < n:
        name = runs[i][0]
        cached_in_group = 1 if runs[i][1] else 0
        j = i + 1
        while j < n and runs[j][0] == name:
            if runs[j][1]:
                cached_in_group += 1
            j += 1
        cnt = j - i
        seg = name if cnt == 1 else f"{name} x{cnt}"
        if cached_in_group:
            seg += f" ({cached_in_group} from cache)"
        parts.append(seg)
        i = j
    return f"Turn {turn_1based}/{max_turns}: " + ", ".join(parts)


def _run_minitask_summary(
    provider: LLMProvider,
    model: str,
    user_task: str,
    tool_results: list[dict],
) -> str:
    excerpt = json.dumps(tool_results, default=str)[:6000]
    body = (
        f"User task (excerpt):\n{user_task[:2000]}\n\n"
        f"Tools run this turn (JSON excerpt):\n{excerpt}\n"
    )
    out = ""
    try:
        for ev in provider.stream_step(
            system=MINITASK_SYSTEM,
            messages=[{"role": "user", "content": body}],
            tools=[],
            model=model,
            max_tokens=128,
        ):
            if ev.get("type") == "text":
                out += ev.get("content", "")
            elif ev.get("type") == "step_result":
                break
    except Exception as e:
        log.warning("minitask summary LLM failed: %s", e)
        return ""
    return (out or "").strip().replace("\n", " ")[:500]


def _run_rolling_summary(
    provider: LLMProvider,
    model: str,
    messages_to_compress: list[NormalizedMessage],
) -> str:
    """Compress *messages_to_compress* into a short prose paragraph.

    Formats each message as a readable text block, then asks the LLM to summarise.
    Returns the summary string (stripped), or '' on failure.
    """
    parts: list[str] = []
    for m in messages_to_compress:
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(f"[{role}]: {content[:2000]}")
        elif isinstance(content, list):
            # Flatten parts: keep text + tool_use name/input, trim tool_result content
            for p in content:
                ptype = p.get("type", "")
                if ptype == "text":
                    parts.append(f"[{role}/text]: {p.get('text', '')[:1000]}")
                elif ptype == "tool_use":
                    inp = json.dumps(p.get("input") or {}, default=str)[:400]
                    parts.append(f"[tool_call {p.get('name', '?')}]: {inp}")
                elif ptype == "tool_result":
                    parts.append(f"[tool_result]: {str(p.get('content', ''))[:800]}")

    body = "\n".join(parts)[:12000]
    out = ""
    try:
        for ev in provider.stream_step(
            system=ROLLING_SUMMARY_SYSTEM,
            messages=[{"role": "user", "content": body}],
            tools=[],
            model=model,
            max_tokens=512,
        ):
            if ev.get("type") == "text":
                out += ev.get("content", "")
            elif ev.get("type") == "step_result":
                break
    except Exception as exc:
        log.warning("rolling summary LLM failed: %s", exc)
        return ""
    return (out or "").strip()


def _store_tool_result_in_cache(
    tool_cache: dict[str, str],
    enabled: bool,
    cache_key: str,
    result_str: str,
) -> None:
    if not enabled or not result_str:
        return
    try:
        o = json.loads(result_str)
        if isinstance(o, dict) and o.get("status") == "cancelled":
            return
    except Exception:
        pass
    tool_cache[cache_key] = result_str


def _summary_from_text(text: str) -> str:
    """Heuristic 'report' / summary for done payload (UI can show in sidebar)."""
    t = (text or "").strip()
    if not t:
        return ""
    if "### " in t or "## " in t:
        m = re.search(
            r"(###\s*Objective[\s\S]+?)(?=###\s*Open questions|$)", t, re.I
        )
        if m:
            return m.group(1).strip()[:2500]
    return t[:2000] + ("…" if len(t) > 2000 else "")


def _full_text_block(text: str) -> str:
    return (text or "").strip()


def _run_planner_pass(
    provider: LLMProvider,
    model: str,
    user_message: str,
) -> tuple[dict | None, str]:
    """First pass: ask the planner for JSON. Returns (plan_obj_or_None, raw_text).

    The caller decides whether to use the structured plan or fall back to the raw text
    rendered as markdown for UI display.
    """
    planner_msgs: list[NormalizedMessage] = [
        {"role": "user", "content": user_message}
    ]
    acc = ""
    for ev in provider.stream_step(
        system=PLANNER_SYSTEM,
        messages=planner_msgs,
        tools=[],
        model=model,
        max_tokens=1024,
    ):
        if ev.get("type") == "text":
            acc += ev.get("content", "")
        elif ev.get("type") == "step_result":
            break
    return _parse_plan_json(acc), acc


def _run_reflection_nudge(
    provider: LLMProvider,
    model: str,
    user_task: str,
    last_tool_excerpt: str,
) -> dict:
    """Run a reflection pass and return a 3-tier verdict.

    Returns a dict with shape:
        {"verdict": "COMPLETE" | "NEEDS_MORE_TOOLS" | "NEEDS_HUMAN", "message": str}

    `message` is empty for COMPLETE; for the other two it is a single short sentence.
    On any parse failure, returns COMPLETE so the loop falls through gracefully.
    """
    body = (
        f"User task:\n{user_task[:4000]}\n\n"
        f"Recent tool results (excerpt):\n{last_tool_excerpt[:8000]}\n"
    )
    out = ""
    for ev in provider.stream_step(
        system=REFLECTION_SYSTEM,
        messages=[{"role": "user", "content": body}],
        tools=[],
        model=model,
        max_tokens=256,
    ):
        if ev.get("type") == "text":
            out += ev.get("content", "")
        elif ev.get("type") == "step_result":
            break
    lines = [x.strip() for x in (out or "").splitlines() if x.strip()]
    if not lines:
        return {"verdict": "COMPLETE", "message": ""}
    head = lines[0].upper().strip(" .:-")
    message = lines[1] if len(lines) > 1 else ""
    if head.startswith("COMPLETE"):
        return {"verdict": "COMPLETE", "message": ""}
    if head.startswith("NEEDS_HUMAN"):
        return {"verdict": "NEEDS_HUMAN", "message": message or "Operator input required."}
    if head.startswith("NEEDS_MORE_TOOLS") or head.startswith("INCOMPLETE"):
        msg = message if message and message.lower() != "done" else ""
        return {"verdict": "NEEDS_MORE_TOOLS", "message": msg}
    return {"verdict": "COMPLETE", "message": ""}


def _execute_tool_sync(
    tool_name: str,
    inp: dict,
    dispatch: dict,
) -> tuple[str, float]:
    """Execute one tool call synchronously, returning (result_str, elapsed_ms).

    Errors are caught and serialised into the result string (matching the
    behaviour of the original inline loop).
    """
    t0 = time.perf_counter()
    try:
        result_data = execute_combined(tool_name, inp, dispatch)
        result_str = json.dumps(result_data, default=str)
    except Exception as exc:
        result_str = json.dumps({"error": str(exc)})
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return result_str, elapsed_ms


def _can_parallelize_tool_uses(
    tool_uses: list[dict],
    cli_confirm: Optional[Callable[[str, dict], bool]],
) -> bool:
    """Return True only when every tool call in this turn is read-only and confirmation-free.

    Order matters for write operations, so a single mutation in the batch falls
    back to serial dispatch.
    """
    if len(tool_uses) <= 1:
        return False
    for tu in tool_uses:
        name = tu.get("name", "")
        inp = tu.get("input") or {}
        if not is_read_only(name, inp):
            return False
        if cli_confirm is not None and needs_cli_confirmation(name, inp):
            return False
    return True


def _run_tools_in_parallel(
    tool_uses: list[dict],
    dispatch: dict,
) -> list[tuple[str, float]]:
    """Run a batch of read-only tool calls concurrently via asyncio.to_thread.

    Returns a list of (result_str, elapsed_ms) tuples in the same order as `tool_uses`.
    Safe to call from a synchronous generator: spins up a private event loop.
    """

    async def _gather() -> list[tuple[str, float]]:
        coros = [
            asyncio.to_thread(
                _execute_tool_sync, tu.get("name", ""), tu.get("input") or {}, dispatch
            )
            for tu in tool_uses
        ]
        return await asyncio.gather(*coros)

    return asyncio.run(_gather())


def _run_reviewer_pass(
    provider: LLMProvider, model: str, user_task: str, final_answer: str
) -> str:
    acc = ""
    for ev in provider.stream_step(
        system=REVIEWER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"**User request:**\n{user_task[:4000]}\n\n**Assistant answer:**\n{final_answer[:12000]}",
            }
        ],
        tools=[],
        model=model,
        max_tokens=1024,
    ):
        if ev.get("type") == "text":
            acc += ev.get("content", "")
        elif ev.get("type") == "step_result":
            break
    return (acc or "").strip()


def stream_agent_events(
    provider: LLMProvider,
    system_prompt: str,
    messages: list[NormalizedMessage],
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    max_turns: int | None = None,
    tools_provider: Callable[[], tuple[list[dict], dict]] = build_combined_tools,
    on_reload_modules: bool = False,
    cli_confirm: Optional[Callable[[str, dict], bool]] = None,
) -> Generator[dict, None, None]:
    """Run the agent loop with any LLMProvider and emit UI-facing SSE event dicts."""
    model = model or provider.default_model
    max_tokens = max_tokens or get_max_tokens()
    max_turns = max_turns or get_max_turns()
    work: list[NormalizedMessage] = [dict(m) for m in messages]  # type: ignore[assignment]

    # Last user content in the initial request (for review / reflection context)
    user_task_for_meta = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                user_task_for_meta = c
            break
    if not user_task_for_meta and work:
        c0 = work[-1].get("content")
        if isinstance(c0, str):
            user_task_for_meta = c0

    reflection_nudges_used = 0
    reflection_max_nudges = get_reflection_max_nudges()
    tool_turns_used = 0
    plan_steps_estimate: int | None = None
    plan_system_block: str = ""
    tool_cache: dict[str, str] = {}
    entity_cache = EntityCache()

    # Optional planner pass
    if work and work[-1].get("role") == "user" and planner_enabled():
        uc = work[-1].get("content")
        if isinstance(uc, str) and uc.strip():
            try:
                yield {
                    "type": "busy",
                    "phase": "planner",
                    "message": "Generating execution plan…",
                }
                plan_obj, plan_raw = _run_planner_pass(provider, model, uc)
                if plan_obj:
                    plan_steps_estimate = len(plan_obj["steps"])
                    plan_system_block = _build_plan_system_block(plan_obj)
                    plan_md = _plan_to_markdown(plan_obj)
                    yield {
                        "type": "planner",
                        "content": plan_md[:3000],
                        "plan": plan_obj,
                    }
                else:
                    # Parse failure: keep the legacy markdown-on-user-message behaviour.
                    plan_steps_estimate = _estimate_plan_steps_markdown(plan_raw)
                    if plan_raw.strip():
                        work[-1] = {
                            **work[-1],
                            "content": (
                                f"{uc}\n\n---\n**Execution plan (auto-generated; follow as guidance)**\n{plan_raw}\n"
                            ),
                        }
                        yield {"type": "planner", "content": plan_raw[:3000]}
            except Exception as e:
                yield {"type": "error", "error": f"Planner failed: {e}"}

    for turn in range(max_turns):
        if on_reload_modules:
            try:
                reload_all_tools()
            except Exception:
                pass
        tools, dispatch = tools_provider()
        yield {"type": "iteration", "n": turn + 1, "max": max_turns}

        # Prepend entity-cache + plan blocks to the system prompt each turn.
        prefix_parts: list[str] = []
        if entity_cache_enabled():
            ctx = entity_cache.format_context_block()
            if ctx:
                prefix_parts.append(ctx)
        if plan_system_block:
            prefix_parts.append(plan_system_block)
        if prefix_parts:
            effective_system = "\n\n".join(prefix_parts) + "\n\n" + system_prompt
        else:
            effective_system = system_prompt

        step: StepResult | None = None
        for ev in provider.stream_step(
            system=effective_system,
            messages=work,
            tools=tools,
            model=model,
            max_tokens=max_tokens,
        ):
            et = ev.get("type")
            if et == "step_result":
                step = ev["result"]
            else:
                yield ev

        if step is None:
            log.warning("LLM returned no step result (stream produced no step_result event)")
            yield {
                "type": "error",
                "error": "The LLM returned no response. This may indicate context window exhaustion or an API issue.",
            }
            yield {
                "type": "done",
                "summary": "",
                "full_text": "",
                "review_text": None,
            }
            return

        # Bail out if the provider detected context exhaustion
        if step.stop_reason == "context_exhausted":
            log.warning("Agent stopping: provider reported context_exhausted on turn %d", turn + 1)
            yield {
                "type": "done",
                "summary": _summary_from_text(step.text),
                "full_text": _full_text_block(step.text),
                "review_text": None,
            }
            return

        if step.text and ("### " in step.text or "## " in step.text):
            rep_full = _full_text_block(step.text)
            yield {
                "type": "report",
                "text": _summary_from_text(step.text),
                "full_text": rep_full,
            }

        if step.stop_reason != "tool_use" or not step.tool_uses:
            final_text = _full_text_block(step.text)
            review_text: str | None = None
            reviewer_min = get_reviewer_min_tool_turns()
            if (
                reviewer_enabled()
                and final_text
                and tool_turns_used >= reviewer_min
            ):
                try:
                    yield {
                        "type": "busy",
                        "phase": "reviewer",
                        "message": "Running peer review…",
                    }
                    review_text = _run_reviewer_pass(
                        provider, model, user_task_for_meta, final_text
                    )
                    if review_text:
                        yield {"type": "reviewer", "text": review_text}
                except Exception as e:
                    yield {"type": "error", "error": f"Reviewer failed: {e}"}
            out_text = final_text
            if review_text:
                out_text = final_text + "\n\n---\n### Peer review\n" + review_text
            yield {
                "type": "done",
                "summary": _summary_from_text(step.text),
                "full_text": out_text,
                "review_text": review_text,
            }
            return

        if turn == max_turns - 1:
            yield {
                "type": "error",
                "error": f"Max agent turns ({max_turns}) reached; stopping before more tool use.",
            }
            final_text = _full_text_block(step.text)
            yield {
                "type": "done",
                "summary": _summary_from_text(step.text),
                "full_text": final_text,
                "review_text": None,
            }
            return

        work.append(step.assistant_message)
        tool_turns_used += 1

        tool_results: list[dict] = []
        runs: list[tuple[str, bool]] = []
        use_cache = tool_cache_enabled()
        parallel = _can_parallelize_tool_uses(step.tool_uses, cli_confirm)

        if parallel:
            # Pre-resolve cache hits and gather the rest concurrently; emit ordered events.
            for tu in step.tool_uses:
                yield {
                    "type": "tool_call",
                    "tool": tu["name"],
                    "args": tu.get("input") or {},
                }

            slots: list[dict[str, Any]] = []
            to_execute: list[tuple[int, dict]] = []
            for idx, tu in enumerate(step.tool_uses):
                inp = tu.get("input") or {}
                cache_key = _tool_cache_key(tu["name"], inp)
                if use_cache and cache_key in tool_cache:
                    slots.append(
                        {
                            "result_str": tool_cache[cache_key],
                            "from_cache": True,
                            "elapsed_ms": 0.0,
                            "cache_key": cache_key,
                        }
                    )
                else:
                    slots.append(
                        {
                            "result_str": None,
                            "from_cache": False,
                            "elapsed_ms": 0.0,
                            "cache_key": cache_key,
                        }
                    )
                    to_execute.append((idx, tu))

            if to_execute:
                yield {
                    "type": "busy",
                    "phase": "tool_parallel",
                    "message": (
                        f"Executing {len(to_execute)} read-only tools in parallel…"
                    ),
                }
                try:
                    par_results = _run_tools_in_parallel(
                        [tu for _, tu in to_execute], dispatch
                    )
                except Exception as exc:
                    log.warning("Parallel dispatch failed, falling back: %s", exc)
                    par_results = [
                        _execute_tool_sync(
                            tu.get("name", ""), tu.get("input") or {}, dispatch
                        )
                        for _, tu in to_execute
                    ]
                for (idx, _tu), (result_str, elapsed_ms) in zip(to_execute, par_results):
                    slots[idx]["result_str"] = result_str
                    slots[idx]["elapsed_ms"] = elapsed_ms

            for tu, slot in zip(step.tool_uses, slots):
                result_str = slot["result_str"] or ""
                from_cache = bool(slot["from_cache"])
                if not from_cache:
                    _store_tool_result_in_cache(
                        tool_cache, use_cache, slot["cache_key"], result_str
                    )
                if from_cache:
                    yield {
                        "type": "busy",
                        "phase": "cache",
                        "tool": tu["name"],
                        "message": f"Using cached result for {tu['name']}…",
                    }
                    log.info("agent tool tool=%s cached=yes", tu["name"])
                else:
                    log.info(
                        "agent tool tool=%s ms=%.1f err=%s parallel=yes",
                        tu["name"],
                        slot["elapsed_ms"],
                        "yes" if '"error"' in result_str[:200] else "no",
                    )
                yield {
                    "type": "tool_result",
                    "tool": tu["name"],
                    "result": result_str[:2000],
                    "full": result_str,
                    "cached": from_cache,
                }
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": result_str,
                    }
                )
                runs.append((tu["name"], from_cache))
                if entity_cache_enabled():
                    entity_cache.update(tu["name"], result_str)
        else:
            for tu in step.tool_uses:
                yield {
                    "type": "tool_call",
                    "tool": tu["name"],
                    "args": tu.get("input") or {},
                }
                inp = tu.get("input") or {}
                cache_key = _tool_cache_key(tu["name"], inp)
                from_cache = False
                t0 = time.perf_counter()
                needs_confirm = cli_confirm is not None and needs_cli_confirmation(
                    tu["name"], inp
                )

                if use_cache and not needs_confirm and cache_key in tool_cache:
                    result_str = tool_cache[cache_key]
                    from_cache = True
                    yield {
                        "type": "busy",
                        "phase": "cache",
                        "tool": tu["name"],
                        "message": f"Using cached result for {tu['name']}…",
                    }
                elif needs_confirm:
                    if not cli_confirm(tu["name"], inp):
                        result_str = json.dumps(
                            {
                                "status": "cancelled",
                                "reason": "User cancelled the operation (or web confirmation not granted).",
                            }
                        )
                    else:
                        yield {
                            "type": "busy",
                            "phase": "tool",
                            "tool": tu["name"],
                            "message": f"Executing {tu['name']} (vCenter / tools)…",
                        }
                        result_str, _ = _execute_tool_sync(tu["name"], inp, dispatch)
                    _store_tool_result_in_cache(
                        tool_cache, use_cache, cache_key, result_str
                    )
                else:
                    yield {
                        "type": "busy",
                        "phase": "tool",
                        "tool": tu["name"],
                        "message": f"Executing {tu['name']} (vCenter / tools)…",
                    }
                    result_str, _ = _execute_tool_sync(tu["name"], inp, dispatch)
                    _store_tool_result_in_cache(
                        tool_cache, use_cache, cache_key, result_str
                    )

                if from_cache:
                    log.info("agent tool tool=%s cached=yes", tu["name"])
                else:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    log.info(
                        "agent tool tool=%s ms=%.1f err=%s",
                        tu["name"],
                        elapsed_ms,
                        "yes" if '"error"' in result_str[:200] else "no",
                    )
                yield {
                    "type": "tool_result",
                    "tool": tu["name"],
                    "result": result_str[:2000],
                    "full": result_str,
                    "cached": from_cache,
                }
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": result_str,
                    }
                )
                runs.append((tu["name"], from_cache))

                if entity_cache_enabled():
                    entity_cache.update(tu["name"], result_str)

        summary = _deterministic_checkpoint_summary(turn + 1, max_turns, runs)
        llm_note = ""
        if minitask_llm_enabled() and tool_results:
            try:
                yield {
                    "type": "busy",
                    "phase": "minitask_llm",
                    "message": "Summarizing this tool batch…",
                }
                llm_note = _run_minitask_summary(
                    provider, model, user_task_for_meta, tool_results
                )
            except Exception as e:
                log.warning("minitask LLM: %s", e)
        checkpoint: dict[str, Any] = {
            "type": "checkpoint",
            "turn": turn + 1,
            "max_turns": max_turns,
            "tools": [{"name": n, "cached": c} for n, c in runs],
            "cached_count": sum(1 for _, c in runs if c),
            "summary": summary,
            "plan_steps_estimate": plan_steps_estimate,
        }
        if llm_note:
            checkpoint["llm_note"] = llm_note
        yield checkpoint

        work.append({"role": "user", "content": tool_results})  # type: ignore[typeddict-item]

        # Rolling summary: compress older turns every N turns to limit context growth.
        if rolling_summary_enabled():
            interval = get_summary_interval()
            _ROLLING_TAIL = 4  # always keep last 2 turns (4 messages) verbatim
            if (turn + 1) % interval == 0 and len(work) > 1 + _ROLLING_TAIL:
                yield {
                    "type": "busy",
                    "phase": "rolling_summary",
                    "message": "Compressing conversation history…",
                }
                try:
                    summary_text = _run_rolling_summary(provider, model, work[1:-_ROLLING_TAIL])
                    if summary_text:
                        work[1:-_ROLLING_TAIL] = [
                            {
                                "role": "user",
                                "content": f"[Summary of earlier turns]\n{summary_text}",
                            }
                        ]
                        yield {"type": "rolling_summary", "summary": summary_text}
                        log.info(
                            "rolling summary applied at turn %d; work list compressed to %d messages",
                            turn + 1,
                            len(work),
                        )
                except Exception as exc:
                    log.warning("Rolling summary failed at turn %d: %s", turn + 1, exc)

        if (
            reflection_enabled()
            and reflection_nudges_used < reflection_max_nudges
            and turn < max_turns - 1
        ):
            try:
                yield {
                    "type": "busy",
                    "phase": "reflection",
                    "message": "Checking whether more tools are needed…",
                }
                tr_json = json.dumps(tool_results, default=str)
                verdict_obj = _run_reflection_nudge(
                    provider, model, user_task_for_meta, tr_json
                )
                verdict = verdict_obj.get("verdict", "COMPLETE")
                message = verdict_obj.get("message", "")
                if verdict == "NEEDS_HUMAN":
                    yield {
                        "type": "needs_human",
                        "message": message or "Operator input required.",
                    }
                    final_text = _full_text_block(step.text)
                    yield {
                        "type": "done",
                        "summary": _summary_from_text(step.text),
                        "full_text": final_text,
                        "review_text": None,
                    }
                    return
                if verdict == "NEEDS_MORE_TOOLS" and message:
                    work.append(
                        {
                            "role": "user",
                            "content": f"[System: continuation hint — run more tools if needed]\n{message}",
                        }
                    )
                    reflection_nudges_used += 1
                    yield {
                        "type": "reflection",
                        "nudge": message,
                        "verdict": verdict,
                        "nudges_used": reflection_nudges_used,
                        "max_nudges": reflection_max_nudges,
                    }
            except Exception as e:
                yield {"type": "error", "error": f"Reflection failed: {e}"}
