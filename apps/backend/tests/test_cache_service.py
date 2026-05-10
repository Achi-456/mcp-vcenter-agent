from app.core.errors import ErrorCode
from app.services.cache_service import CacheService


def test_failed_results_not_cacheable() -> None:
    cache = CacheService()

    assert cache.is_cacheable({"ok": False, "error_code": ErrorCode.VCENTER_AUTH_FAILED}) is False
    assert cache.is_cacheable({"error_code": ErrorCode.VCENTER_SESSION_EXPIRED}) is False
    assert cache.is_cacheable({"error_code": ErrorCode.VCENTER_SSL_ERROR}) is False
    assert cache.is_cacheable({"error_code": ErrorCode.TOOL_POLICY_BLOCKED}) is False
    assert cache.is_cacheable({"error_code": ErrorCode.TOOL_REQUIRES_APPROVAL}) is False
    assert cache.is_cacheable({"status": "failed"}) is False
    assert cache.is_cacheable({"message": "permission denied"}) is False


def test_success_result_cacheable() -> None:
    assert CacheService().is_cacheable({"ok": True, "data": {"value": 1}}) is True
