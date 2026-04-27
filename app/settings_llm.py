"""Persist LLM-related keys to `.env` and apply to the current process."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Mapping

# Env var names (single source for file + os.environ updates)
ENV_ANTHROPIC = "ANTHROPIC_API_KEY"
ENV_OPENAI = "OPENAI_API_KEY"
ENV_GOOGLE = "GOOGLE_API_KEY"
ENV_XAI = "XAI_API_KEY"
ENV_MOONSHOT = "MOONSHOT_API_KEY"
ENV_MOONSHOT_BASE_URL = "MOONSHOT_BASE_URL"
ENV_MOONSHOT_MODEL = "MOONSHOT_MODEL"
ENV_AGENT_PROVIDER = "AGENT_PROVIDER"
ENV_AGENT_FALLBACK_PROVIDER = "AGENT_FALLBACK_PROVIDER"

MANAGED_KEYS: tuple[str, ...] = (
    ENV_ANTHROPIC,
    ENV_OPENAI,
    ENV_GOOGLE,
    ENV_XAI,
    ENV_MOONSHOT,
    ENV_MOONSHOT_BASE_URL,
    ENV_MOONSHOT_MODEL,
    ENV_AGENT_PROVIDER,
    ENV_AGENT_FALLBACK_PROVIDER,
)


def env_file_path() -> Path:
    """Project root `.env` (works with Docker volume `/app/.env`)."""
    return Path(__file__).resolve().parent.parent / ".env"


def _format_env_line(key: str, value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError(f"Value for {key} must be a single line")
    if not value:
        return f"{key}="
    if re.search(r'[\s#"\'\\]', value) or "=" in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'{key}="{escaped}"'
    return f"{key}={value}"


def upsert_env_file(path: Path, updates: Mapping[str, str | None]) -> None:
    """
    Merge `updates` into the dotenv file. Keys not present are appended.
    ``None`` or empty string clears: ``KEY=``.
    """
    path = Path(path)
    raw_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    key_to_index: dict[str, int] = {}
    for i, line in enumerate(raw_lines):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
        if m and m.group(1) in MANAGED_KEYS:
            key_to_index[m.group(1)] = i

    new_lines = list(raw_lines)

    for key, val in updates.items():
        if key not in MANAGED_KEYS:
            continue
        line_content = _format_env_line(key, "" if val is None else str(val))
        if key in key_to_index:
            new_lines[key_to_index[key]] = line_content
        else:
            new_lines.append(line_content)

    out = "\n".join(new_lines)
    if out:
        out += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=".env.", suffix=".tmp", dir=str(path.parent), text=True
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(out)
        os.replace(tmp, path)
    finally:
        if os.path.isfile(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def apply_env_to_process(updates: Mapping[str, str | None]) -> None:
    """Update ``os.environ`` after a successful file write."""
    for key, val in updates.items():
        if key not in MANAGED_KEYS:
            continue
        if val is None or str(val).strip() == "":
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(val).strip()
