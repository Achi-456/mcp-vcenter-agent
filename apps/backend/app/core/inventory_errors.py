import structlog

logger = structlog.get_logger()

ERROR_CODES = {
    "VCENTER_NOT_CONFIGURED": "vCenter credentials are not configured. Please configure vCenter in Settings first.",
    "VCENTER_SECRET_INVALID": "vCenter credentials in Secret are incomplete.",
    "VCENTER_AUTH_FAILED": "Credentials may be invalid. Update Settings.",
    "VCENTER_UNREACHABLE": "Cannot reach vCenter from FastAPI pod.",
    "VCENTER_SSL_ERROR": "SSL verification failed. Disable Verify SSL for self-signed lab certificates.",
    "VCENTER_SESSION_EXPIRED": "vCenter session expired. Reconnecting.",
    "VCENTER_INVENTORY_ERROR": "vCenter inventory collection failed.",
    "VCENTER_TIMEOUT": "vCenter inventory request timed out.",
    "INVENTORY_UNKNOWN_ERROR": "An unknown inventory error occurred.",
}


def error_response(code: str) -> dict:
    return {
        "ok": False,
        "error_code": code,
        "message": ERROR_CODES.get(code, code),
    }
