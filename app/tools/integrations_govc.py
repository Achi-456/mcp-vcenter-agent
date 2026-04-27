"""
Restricted govc (github.com/vmware/govmomi/govc) bridge.
Requires govc binary on PATH and GOVC_* env (or VCENTER_* synced to GOVC_URL).
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from typing import Any

# Substrings that indicate high-risk operations (denylist on the first command token).
_GOVC_DENY_SUBSTRINGS = (
    "destroy",
    ".remove",
    "remove.",
    "disk.remove",
    "license.remove",
    "host.remove",
    "vsan.remove",
    "object.destroy",
)

# First token must look like a govc command (alphanumerics and dots).
_CMD_RE = re.compile(r"^[a-z][a-z0-9.]*$", re.I)


def sync_govc_env_from_vcenter() -> None:
    """If GOVC_URL is unset, derive from VCENTER_HOST/PORT (HTTPS SDK path)."""
    if os.environ.get("GOVC_URL"):
        return
    host = os.environ.get("VCENTER_HOST")
    if not host:
        return
    port = int(os.environ.get("VCENTER_PORT", "443"))
    scheme = "https"
    os.environ.setdefault("GOVC_URL", f"{scheme}://{host}:{port}/sdk")
    if os.environ.get("VCENTER_USER"):
        os.environ.setdefault("GOVC_USERNAME", os.environ["VCENTER_USER"])
    if os.environ.get("VCENTER_PASSWORD"):
        os.environ.setdefault("GOVC_PASSWORD", os.environ["VCENTER_PASSWORD"])


def _is_denied(args: list[str]) -> str | None:
    if not args:
        return "Empty govc command."
    # First token: either "vm.info" style or "vm" (multi-token command)
    head = args[0]
    if not _CMD_RE.match(head) and not head.replace("-", "").isalnum():
        return f"Invalid govc subcommand: {head!r}"
    lower = " ".join(args).lower()
    for bad in _GOVC_DENY_SUBSTRINGS:
        if bad in lower:
            return f"Subcommand blocked by policy (matched {bad!r})."
    return None


def govc_command(args: str, timeout_sec: int = 60) -> dict[str, Any]:
    """
    Run: govc <args> where `args` is a shell-style string (split with shlex).
    No shell=True; only the govc binary is invoked.
    """
    sync_govc_env_from_vcenter()
    govc = shutil.which("govc")
    if not govc:
        return {
            "error": "govc not found on PATH. Install govc or set PATH in the container.",
        }

    try:
        parts = shlex.split(args, posix=True)
    except ValueError as e:
        return {"error": f"Invalid command line: {e}"}

    err = _is_denied(parts)
    if err:
        return {"error": err}

    cmd = [govc] + parts
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"govc timed out after {timeout_sec}s", "args": args}
    except OSError as e:
        return {"error": str(e)}

    out = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    if proc.returncode != 0 and not proc.stdout and proc.stderr:
        out["error"] = proc.stderr.strip()
    return out
