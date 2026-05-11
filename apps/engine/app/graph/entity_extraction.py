from __future__ import annotations

import re


GENERIC_ENTITIES = {
    "vcenter",
    "host",
    "hosts",
    "vm",
    "vms",
    "details",
    "detail",
    "health",
    "tags",
    "tag",
    "events",
    "event",
    "datastore",
    "datastores",
    "alarms",
    "alarm",
    "info",
    "about",
    "version",
    "rest",
    "govc",
    "cli",
}

HOST_RE = re.compile(r"\b(?:esxi[\w.-]*|esx-[\w.-]*|\d{1,3}(?:\.\d{1,3}){3})\b", re.IGNORECASE)
QUOTED_RE = re.compile(r"[\"']([^\"']+)[\"']")


def extract_value(message: str, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        pattern = rf"\b{re.escape(key)}\s*[=:]\s*(\"[^\"]+\"|'[^']+'|[^\s,?]+)"
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return _clean(match.group(1))
    return None


def extract_entity(message: str, *, prefer: str | None = None) -> str | None:
    preferred = {
        "vm": ("vm", "name"),
        "host": ("host", "name"),
        "datastore": ("datastore", "name"),
    }.get(prefer or "", ("name",))
    explicit = extract_value(message, preferred)
    if explicit and not is_generic_entity(explicit):
        return explicit

    quoted = QUOTED_RE.search(message)
    if quoted:
        value = _clean(quoted.group(1))
        if not is_generic_entity(value):
            return value

    if prefer == "host":
        host = HOST_RE.search(message)
        if host:
            return host.group(0)

    patterns = (
        r"\binspect\s+(\"[^\"]+\"|'[^']+'|[^\s,?]+)",
        r"\bdetails\s+for\s+(\"[^\"]+\"|'[^']+'|[^\s,?]+)",
        r"\bdetail\s+for\s+(\"[^\"]+\"|'[^']+'|[^\s,?]+)",
        r"\bfor\s+(\"[^\"]+\"|'[^']+'|[^\s,?]+)",
        r"\babout\s+(\"[^\"]+\"|'[^']+'|[^\s,?]+)",
        r"\bcheck\s+(\"[^\"]+\"|'[^']+'|[^\s,?]+)",
        r"\bverify\s+(\"[^\"]+\"|'[^']+'|[^\s,?]+)",
        r"\bis\s+(\"[^\"]+\"|'[^']+'|[^\s,?]+)\s+okay\b",
    )
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            value = _clean(match.group(1))
            if not is_generic_entity(value):
                return value
    return None


def is_generic_entity(value: str | None) -> bool:
    if not value:
        return True
    cleaned = _clean(value).lower()
    return cleaned in GENERIC_ENTITIES


def is_host_like(value: str | None) -> bool:
    return bool(value and HOST_RE.fullmatch(value))


def _clean(value: str) -> str:
    return value.strip().strip("\"'").strip()
