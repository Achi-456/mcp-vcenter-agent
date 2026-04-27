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


# Tool-name prefixes that are always considered read-only inspections of vCenter state.
_READ_ONLY_PREFIXES: tuple[str, ...] = ("list_", "get_", "query_", "find_", "describe_")

# Explicit read-only allowlist for non-vCenter tools and any vCenter tool whose
# name does not start with the standard read-only prefixes above.
READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {
        "web_search",
        "emit_session_report",
    }
)


def needs_cli_confirmation(name: str, tool_input: dict) -> bool:
    if name in VCENTER_DESTRUCTIVE:
        return True
    if name == "govc_command":
        return is_govc_likely_destructive(str((tool_input or {}).get("args", "") or ""))
    return False


def is_read_only(name: str, tool_input: dict | None = None) -> bool:
    """Return True if a tool call is safe to run concurrently with peers.

    Conservative by default: only known read-only inspection tools qualify.
    `govc_command` is always treated as serial because subcommands cannot be
    parsed reliably without re-implementing govc's argument grammar.
    """
    if not name:
        return False
    if name in VCENTER_DESTRUCTIVE:
        return False
    if name == "govc_command":
        return False
    if name in READ_ONLY_TOOLS:
        return True
    return name.startswith(_READ_ONLY_PREFIXES)
