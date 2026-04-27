"""Agent environment-driven configuration."""
import os

DEFAULT_MAX_TURNS = 25
DEFAULT_MAX_TOKENS = 4096
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def get_max_turns() -> int:
    return int(os.environ.get("AGENT_MAX_TURNS", str(DEFAULT_MAX_TURNS)))


def get_max_tokens() -> int:
    return int(os.environ.get("AGENT_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))


def get_model() -> str:
    return os.environ.get("AGENT_MODEL", DEFAULT_MODEL)


def planner_enabled() -> bool:
    """Pre-plan the user request as structured JSON before the main loop (default on)."""
    return _env_truthy("AGENT_PLANNER", True)


def reflection_enabled() -> bool:
    """Up to N between-turn nudges if the model may have stopped early (see engine)."""
    return os.environ.get("AGENT_REFLECTION", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def get_reflection_max_nudges() -> int:
    """Maximum number of reflection nudges per session (AGENT_REFLECTION_MAX_NUDGES, default 3)."""
    raw = os.environ.get("AGENT_REFLECTION_MAX_NUDGES", "3").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 3


def reviewer_enabled() -> bool:
    """After the final answer, a no-tools peer review pass and optional appendix."""
    return os.environ.get("AGENT_REVIEWER", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def get_reviewer_min_tool_turns() -> int:
    """Minimum number of tool-use turns before the reviewer runs (AGENT_REVIEWER_MIN_TOOL_TURNS, default 3)."""
    raw = os.environ.get("AGENT_REVIEWER_MIN_TOOL_TURNS", "3").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 3


def destructive_web_env_allowed() -> bool:
    """If true, the API allows high-risk tool calls without request-level confirmation (insecure)."""
    return os.environ.get("AGENT_ALLOW_DESTRUCTIVE_WEB", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _env_truthy(key: str, default: bool) -> bool:
    raw = os.environ.get(key, "")
    if raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def tool_cache_enabled() -> bool:
    """Per-run cache for identical tool name+arguments (default on). Set AGENT_TOOL_CACHE=false to disable."""
    return _env_truthy("AGENT_TOOL_CACHE", True)


def minitask_llm_enabled() -> bool:
    """Optional one-sentence LLM summary after each tool batch (AGENT_MINITASK_LLM)."""
    return _env_truthy("AGENT_MINITASK_LLM", False)


def get_fallback_provider() -> str | None:
    """Return the AGENT_FALLBACK_PROVIDER name, or None if not set.

    When set to a valid provider id (e.g. 'openai'), the factory wraps the primary provider
    in a FailoverProvider that automatically delegates after retry exhaustion or 5xx errors.
    """
    val = os.environ.get("AGENT_FALLBACK_PROVIDER", "").strip().lower()
    return val or None


# ── Memory / session helpers ──────────────────────────────────────────────────

def get_summary_interval() -> int:
    """Number of turns between rolling-summary compressions (AGENT_SUMMARIZE_EVERY, default 8).

    Set to 0 to disable rolling summaries entirely.
    """
    raw = os.environ.get("AGENT_SUMMARIZE_EVERY", "8").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 8


def rolling_summary_enabled() -> bool:
    """True when AGENT_SUMMARIZE_EVERY is non-zero (default True)."""
    return get_summary_interval() > 0


def entity_cache_enabled() -> bool:
    """Inject known VM/host/datastore names as context at each turn (AGENT_ENTITY_CACHE, default on)."""
    return _env_truthy("AGENT_ENTITY_CACHE", True)


def session_store_enabled() -> bool:
    """Persist session summaries to SQLite for cross-restart resume (AGENT_SESSION_STORE, default off)."""
    return _env_truthy("AGENT_SESSION_STORE", False)


def get_session_db_path() -> str:
    """Path to the SQLite sessions database (AGENT_SESSION_DB, default .data/sessions.db)."""
    return os.environ.get("AGENT_SESSION_DB", ".data/sessions.db").strip()
