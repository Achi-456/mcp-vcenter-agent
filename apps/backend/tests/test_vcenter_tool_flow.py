from app.api.routes.vcenter_tool_flow import run_vcenter_tool
from app.schemas.tools import RiskLevel, ToolSpec
from app.services.policy_service import PolicyService
from app.services.tool_registry_service import ToolRegistryService


class FakeCache:
    def __init__(self):
        self.values = {}
        self.set_calls = 0

    async def get(self, key, *, refresh=False):
        if refresh:
            return None
        return self.values.get(key)

    async def set(self, key, value, *, ttl_seconds):
        self.set_calls += 1
        self.values[key] = value
        return True


class FakeAudit:
    def __init__(self):
        self.decisions = []

    async def record_tool_decision(self, **kwargs):
        self.decisions.append(kwargs)


def registry_for(tool: ToolSpec) -> ToolRegistryService:
    return ToolRegistryService(tools=(tool,))


def make_tool(*, enabled=True, implemented=True) -> ToolSpec:
    return ToolSpec(
        name="list_vms",
        display_name="List VMs",
        description="List VMs",
        domain="vcenter",
        category="Inventory",
        agent="vcenter_inventory_agent",
        backend="pyvmomi",
        risk_level=RiskLevel.READ_ONLY,
        enabled=enabled,
        implemented=implemented,
        requires_approval=False,
        input_schema={},
        output_schema={},
    )


async def test_tool_flow_caches_successful_read_only_result() -> None:
    cache = FakeCache()
    audit = FakeAudit()

    response = await run_vcenter_tool(
        tool_name="list_vms",
        operation=lambda: async_value([{"name": "vm01"}]),
        registry=registry_for(make_tool()),
        policy=PolicyService(),
        cache=cache,
        audit=audit,
    )

    assert response["ok"] is True
    assert cache.set_calls == 1
    assert audit.decisions[0]["status"] == "success"


async def test_tool_flow_refresh_bypasses_cache() -> None:
    cache = FakeCache()
    cache.values["toolcache:list_vms:default"] = [{"name": "cached"}]

    response = await run_vcenter_tool(
        tool_name="list_vms",
        operation=lambda: async_value([{"name": "fresh"}]),
        registry=registry_for(make_tool()),
        policy=PolicyService(),
        cache=cache,
        audit=FakeAudit(),
        refresh=True,
    )

    assert response["data"] == [{"name": "fresh"}]


async def test_tool_flow_audits_blocked_tool() -> None:
    audit = FakeAudit()

    response = await run_vcenter_tool(
        tool_name="list_vms",
        operation=lambda: async_value([]),
        registry=registry_for(make_tool(enabled=False)),
        policy=PolicyService(),
        cache=FakeCache(),
        audit=audit,
    )

    assert response.status_code == 403
    assert audit.decisions[0]["status"] == "blocked"


async def async_value(value):
    return value
