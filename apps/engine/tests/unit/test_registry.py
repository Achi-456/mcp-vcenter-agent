from app.tools.schemas import RiskLevel, ToolCategory, ToolSpec
from app.tools.registry import (
    RegisteredTool,
    get_enabled_tools,
    get_tool_spec,
    list_tools,
    register_tool,
    execute_tool,
    get_all_tools,
    get_tool as get_legacy_tool,
    TOOLS,
)
from app.tools.vcenter_tools import get_all_tool_specs
from app.tools.cache import should_cache, make_cache_key


class TestRiskLevel:
    def test_has_expected_values(self):
        assert RiskLevel.READ_ONLY.value == "read_only"
        assert RiskLevel.LOW_RISK.value == "low_risk"
        assert RiskLevel.APPROVAL_REQUIRED.value == "approval_required"
        assert RiskLevel.DESTRUCTIVE.value == "destructive"


class TestToolCategory:
    def test_has_expected_values(self):
        assert ToolCategory.INVENTORY.value == "Inventory & Information"
        assert ToolCategory.VM_MANAGEMENT.value == "VM Management"


class TestToolSpec:
    def test_can_create(self):
        spec = ToolSpec(
            name="test_tool",
            display_name="Test Tool",
            description="A test tool.",
            category=ToolCategory.INVENTORY,
            risk_level=RiskLevel.READ_ONLY,
        )
        assert spec.name == "test_tool"
        assert spec.risk_level == RiskLevel.READ_ONLY
        assert spec.enabled is True
        assert spec.implemented is True

    def test_defaults(self):
        spec = ToolSpec(name="minimal", display_name="Min", description="Min")
        assert spec.risk_level == RiskLevel.READ_ONLY
        assert spec.category == ToolCategory.INVENTORY
        assert spec.cache_ttl_seconds == 30


class TestRegistry:
    def test_contains_core_tools(self):
        names = [t.spec.name for t in list_tools(include_disabled=True)]
        assert "list_vms" in names
        assert "get_vm_details" in names
        assert "list_hosts" in names
        assert "list_datastores" in names

    def test_contains_all_vcenter_specs(self):
        spec_names = {s.name for s in get_all_tool_specs()}
        registered_names = {t.spec.name for t in list_tools(include_disabled=True)}
        for name in spec_names:
            assert name in registered_names, f"Missing: {name}"

    def test_get_tool_spec(self):
        t = get_tool_spec("list_vms")
        assert t is not None
        assert t.spec.name == "list_vms"
        assert t.spec.risk_level == RiskLevel.READ_ONLY

    def test_get_enabled_tools_only_read_only(self):
        enabled = get_enabled_tools()
        for t in enabled:
            assert t.spec.enabled is True
            assert t.spec.implemented is True
            assert t.spec.risk_level == RiskLevel.READ_ONLY

    def test_non_read_only_not_in_enabled(self):
        enabled_names = {t.spec.name for t in get_enabled_tools()}
        assert "power_on_vm" not in enabled_names
        assert "power_off_vm" not in enabled_names


class TestLegacyCompat:
    def test_get_all_tools_alias(self):
        tools = get_all_tools()
        assert len(tools) > 0
        names = [t.name for t in tools]
        assert "list_vms" in names

    def test_legacy_get_tool(self):
        t = get_legacy_tool("list_vms")
        assert t is not None
        assert t.name == "list_vms"

    def test_legacy_tools_list(self):
        assert len(TOOLS) > 0
        assert any(t.name == "list_vms" for t in TOOLS)


class TestBlockedTools:
    async def test_power_on_blocked(self):
        result = await execute_tool("power_on_vm", {"vm_name": "test"})
        assert result.get("ok") is False
        assert result.get("error_code") == "TOOL_REQUIRES_APPROVAL"

    async def test_power_off_blocked(self):
        result = await execute_tool("power_off_vm", {"vm_name": "test"})
        assert result.get("ok") is False
        assert result.get("error_code") == "TOOL_REQUIRES_APPROVAL"


class TestCache:
    def test_make_cache_key(self):
        key1 = make_cache_key("list_vms", {})
        key2 = make_cache_key("list_vms", {"refresh": False})
        assert key1.startswith("tool:list_vms:")
        assert key2.startswith("tool:list_vms:")
        assert key1 != key2

    def test_should_cache_read_only_ok(self):
        spec = ToolSpec(name="t", display_name="T", description="T", risk_level=RiskLevel.READ_ONLY)
        assert should_cache(spec.risk_level.value, {"ok": True}) is True

    def test_should_cache_not_ok(self):
        spec = ToolSpec(name="t", display_name="T", description="T", risk_level=RiskLevel.READ_ONLY)
        assert should_cache(spec.risk_level.value, {"ok": False}) is False

    def test_should_cache_error_status(self):
        spec = ToolSpec(name="t", display_name="T", description="T", risk_level=RiskLevel.READ_ONLY)
        assert should_cache(spec.risk_level.value, {"ok": True, "status": "error"}) is False

    def test_should_cache_auth_failure(self):
        spec = ToolSpec(name="t", display_name="T", description="T", risk_level=RiskLevel.READ_ONLY)
        result = {"ok": False, "error_code": "VCENTER_SESSION_EXPIRED", "message": "session is not authenticated"}
        assert should_cache(spec.risk_level.value, result) is False

    def test_should_cache_not_authenticated(self):
        spec = ToolSpec(name="t", display_name="T", description="T", risk_level=RiskLevel.READ_ONLY)
        result = {"ok": False, "error_code": "NotAuthenticated"}
        assert should_cache(spec.risk_level.value, result) is False

    def test_non_read_only_not_cached(self):
        spec = ToolSpec(name="t", display_name="T", description="T", risk_level=RiskLevel.APPROVAL_REQUIRED)
        assert should_cache(spec.risk_level.value, {"ok": True}) is False

    def test_should_cache_vcenter_auth_failed(self):
        spec = ToolSpec(name="t", display_name="T", description="T", risk_level=RiskLevel.READ_ONLY)
        assert should_cache(spec.risk_level.value, {"ok": False, "error_code": "VCENTER_AUTH_FAILED"}) is False

    def test_should_cache_vcenter_unreachable(self):
        spec = ToolSpec(name="t", display_name="T", description="T", risk_level=RiskLevel.READ_ONLY)
        assert should_cache(spec.risk_level.value, {"ok": False, "error_code": "VCENTER_UNREACHABLE"}) is False

    def test_should_cache_invalid_login(self):
        spec = ToolSpec(name="t", display_name="T", description="T", risk_level=RiskLevel.READ_ONLY)
        assert should_cache(spec.risk_level.value, {"ok": False, "error_code": "VCENTER_AUTH_FAILED", "message": "invalid login"}) is False
