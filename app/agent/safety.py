"""User confirmation for high-risk tool calls (CLI). Web UI can leave hooks unset."""


def is_govc_likely_destructive(args: str) -> bool:
    """Heuristic: ask user before govc power/destroy-class ops (CLI)."""
    if not args:
        return False
    lo = args.lower()
    if "vm.destroy" in lo or "object.destroy" in lo:
        return True
    if "vm.power" in lo and any(
        x in lo for x in ("-off", "-s", "shutdown", "-k", "suspend", "reset", "-r")
    ):
        return True
    if "datastore.remove" in lo or "host.remove" in lo:
        return True
    if "vsan" in lo and "evacuate" in lo:
        return True
    return False


VCENTER_DESTRUCTIVE = frozenset(
    {
        "power_off_vm",
        "reset_vm",
        "suspend_vm",
        "revert_to_snapshot",
        "delete_snapshot",
        "enter_maintenance_mode",
        "clone_vm",
        "delete_vm",
    }
)


def needs_cli_confirmation(name: str, tool_input: dict) -> bool:
    if name in VCENTER_DESTRUCTIVE:
        return True
    if name == "govc_command":
        return is_govc_likely_destructive(str((tool_input or {}).get("args", "") or ""))
    return False
