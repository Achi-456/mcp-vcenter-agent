from app.core.config import Settings, get_settings
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.health_service import HealthService
from app.services.llm_model_service import LLMModelService
from app.services.govc_service import GovcService
from app.services.mcp_gateway_service import MCPGatewayService
from app.services.mcp_server_registry_service import MCPServerRegistryService
from app.services.policy_service import PolicyService
from app.services.secret_store import SecretStore
from app.services.tool_registry_service import ToolRegistryService
from app.services.vcenter_inventory_service import VCenterInventoryService
from app.services.vcenter_monitoring_service import VCenterMonitoringService
from app.services.vcenter_session import VCenterSession, get_vcenter_session
from app.services.vsphere_rest_service import VSphereRestService


def settings_dep() -> Settings:
    return get_settings()


def tool_registry_dep() -> ToolRegistryService:
    return ToolRegistryService()


def policy_dep() -> PolicyService:
    return PolicyService()


def audit_dep() -> AuditService:
    return AuditService()


def cache_dep() -> CacheService:
    return CacheService()


def secret_store_dep() -> SecretStore:
    return SecretStore()


def health_dep() -> HealthService:
    return HealthService()


def llm_model_dep() -> LLMModelService:
    return LLMModelService()


def mcp_server_registry_dep() -> MCPServerRegistryService:
    return MCPServerRegistryService()


def mcp_gateway_dep() -> MCPGatewayService:
    return MCPGatewayService()


def vcenter_session_dep() -> VCenterSession:
    return get_vcenter_session()


def vcenter_inventory_dep() -> VCenterInventoryService:
    return VCenterInventoryService()


def vcenter_monitoring_dep() -> VCenterMonitoringService:
    return VCenterMonitoringService()


def govc_dep() -> GovcService:
    return GovcService()


def vsphere_rest_dep() -> VSphereRestService:
    return VSphereRestService()
