import copy
import re

SENSITIVE_PATTERNS = [
    re.compile(r"(?i)password"),
    re.compile(r"(?i)api_key"),
    re.compile(r"(?i)token"),
    re.compile(r"(?i)secret"),
    re.compile(r"(?i)authorization"),
    re.compile(r"(?i)cookie"),
    re.compile(r"VCENTER_PASSWORD"),
    re.compile(r"LLM_API_KEY"),
    re.compile(r"ANTHROPIC_API_KEY"),
    re.compile(r"OPENAI_API_KEY"),
    re.compile(r"GOOGLE_API_KEY"),
    re.compile(r"XAI_API_KEY"),
    re.compile(r"MOONSHOT_API_KEY"),
]

REDACT_LABEL = "**REDACTED**"


def _redact_value(value: str) -> str:
    return REDACT_LABEL


def _redact_dict(d: dict) -> dict:
    result = {}
    for key, value in d.items():
        is_sensitive = any(p.search(key) for p in SENSITIVE_PATTERNS)
        if is_sensitive:
            result[key] = _redact_value(str(value))
        elif isinstance(value, dict):
            result[key] = _redact_dict(value)
        elif isinstance(value, list):
            result[key] = [_redact_dict(v) if isinstance(v, dict) else v for v in value]
        else:
            result[key] = value
    return result


def redact_context(context: dict) -> dict:
    return _redact_dict(copy.deepcopy(context))


def redact_for_log(data: dict) -> dict:
    return _redact_dict(copy.deepcopy(data))
