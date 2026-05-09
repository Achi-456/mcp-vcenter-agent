from app.core.config import Settings, get_settings
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.health_service import HealthService
from app.services.policy_service import PolicyService
from app.services.secret_store import SecretStore
from app.services.tool_registry_service import ToolRegistryService


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
