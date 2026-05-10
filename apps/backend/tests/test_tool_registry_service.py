import pytest

from app.services.tool_registry_service import ToolRegistryService


def test_registry_contains_required_tools() -> None:
    registry = ToolRegistryService()
    names = {tool.name for tool in registry.list_tools()}

    assert "get_environment_overview" in names
    assert "get_vm_details" in names
    assert "get_rke2_vms" in names
    assert "get_csi_va_check" in names
    assert "power_on_vm" in names
    assert "delete_vm" in names


def test_phase2_pyvmomi_tools_implemented() -> None:
    registry = ToolRegistryService()
    implemented = {
        "get_environment_overview",
        "list_vms",
        "get_vm_details",
        "list_hosts",
        "get_host_details",
        "list_datastores",
        "get_datastore_health",
        "get_active_alarms",
        "get_recent_events",
        "get_rke2_vms",
    }

    for name in implemented:
        assert registry.get_tool(name).implemented is True

    assert registry.get_tool("power_on_vm").enabled is False
    assert registry.get_tool("delete_vm").enabled is False
    assert registry.get_tool("get_csi_va_check").implemented is False


def test_registry_categories_and_agents() -> None:
    registry = ToolRegistryService()

    assert "Inventory" in registry.categories()
    assert "vcenter_inventory_agent" in registry.agents()


def test_missing_tool_raises_key_error() -> None:
    with pytest.raises(KeyError):
        ToolRegistryService().get_tool("missing")
