import pytest

from app.schemas.tools import RiskLevel, ToolSpec
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


def test_phase5_diagnostic_tools_implemented_read_only() -> None:
    registry = ToolRegistryService()
    names = {
        "govc_about",
        "govc_vm_info",
        "govc_host_info",
        "govc_datastore_info",
        "govc_events",
        "govc_volume_ls",
        "vsphere_rest_about",
        "vsphere_rest_appliance_health",
        "vsphere_rest_list_tag_categories",
        "vsphere_rest_list_tags",
        "vsphere_rest_list_attached_tags",
        "vsphere_rest_list_content_libraries",
        "vsphere_rest_list_library_items",
        "vsphere_rest_list_recent_tasks",
    }

    for name in names:
        tool = registry.get_tool(name)
        assert tool.enabled is True
        assert tool.implemented is True
        assert tool.risk_level == "read_only"
        assert tool.requires_approval is False


def test_registry_categories_and_agents() -> None:
    registry = ToolRegistryService()

    assert "Inventory" in registry.categories()
    assert "vcenter_inventory_agent" in registry.agents()


def test_missing_tool_raises_key_error() -> None:
    with pytest.raises(KeyError):
        ToolRegistryService().get_tool("missing")


def test_get_tool_can_resolve_dynamic_extra_tool_without_persisting() -> None:
    registry = ToolRegistryService()
    dynamic = ToolSpec(
        name="mcp.default.server_info",
        display_name="MCP Server Info",
        description="Safe MCP server metadata.",
        domain="mcp",
        category="Diagnostics",
        agent="mcp_diagnostic_agent",
        backend="mcp",
        risk_level=RiskLevel.READ_ONLY,
        enabled=True,
        implemented=True,
        requires_approval=False,
        mcp_server="default",
    )

    assert registry.get_tool("mcp.default.server_info", extra_tools=[dynamic]) == dynamic
    with pytest.raises(KeyError):
        registry.get_tool("mcp.default.server_info")
