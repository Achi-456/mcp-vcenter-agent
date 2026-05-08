from app.tools.registry import FASTAPI_INTERNAL


BLOCKED_ACTIONS: list[str] = [
    "power off", "power on", "power_off", "power_on",
    "restart vm", "reboot", "shutdown",
    "delete vm", "destroy vm", "remove vm",
    "delete snapshot", "revert snapshot", "snapshot delete",
    "migrate", "vmotion", "v-motion",
    "maintenance mode", "enter maintenance",
    "disconnect host",
    "remove datastore", "delete datastore",
    "change network", "modify network",
    "format datastore",
]


def classify_safety(user_message: str) -> dict:
    lower = user_message.lower()
    for blocked in BLOCKED_ACTIONS:
        if blocked in lower:
            return {
                "blocked": True,
                "risk": "approval_required",
                "reason": "HIGH_RISK_ACTION",
                "message": (
                    f"This action is blocked for safety. "
                    f"Operation '{blocked}' requires approval and is not enabled in Phase 1.4. "
                    f"Only read-only inspection is available."
                ),
            }

    return {"blocked": False, "risk": "read_only"}
