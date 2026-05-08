import structlog

from pyVim.connect import SmartConnect, Disconnect

from app.services.k8s_secret_store import _now, mask_username

logger = structlog.get_logger()


def test_vcenter_connection(
    vcenter_url: str,
    username: str,
    password: str,
    verify_ssl: bool = False,
) -> tuple[bool, str, str | None]:
    host = vcenter_url.replace("https://", "").replace("http://", "").split("/")[0]
    port = 443
    if ":" in host:
        host, port_str = host.split(":", 1)
        port = int(port_str)

    logger.info("vcenter_test_started", host=host, username_hint=mask_username(username))

    try:
        si = SmartConnect(host=host, user=username, pwd=password, port=port, disableSslCertValidation=not verify_ssl)
        _ = si.RetrieveContent()
        Disconnect(si)
        logger.info("vcenter_test_success", host=host)
        return True, "Connected to vCenter successfully.", None
    except Exception as exc:
        error_code = _classify_error(str(exc))
        logger.warning("vcenter_test_failed", host=host, error_code=error_code)
        return False, _friendly_message(error_code), error_code


def _classify_error(msg: str) -> str:
    m = msg.lower()
    if "auth" in m or "password" in m or "login" in m or "cannot complete login" in m:
        return "VCENTER_AUTH_FAILED"
    if "name" in m or "resolve" in m or "getaddrinfo" in m or "dns" in m:
        return "VCENTER_DNS_FAILED"
    if "refused" in m or "timeout" in m or "unreachable" in m or "connect" in m:
        return "VCENTER_UNREACHABLE"
    if "ssl" in m or "certificate" in m:
        return "VCENTER_SSL_ERROR"
    return "VCENTER_UNKNOWN_ERROR"


def _friendly_message(code: str) -> str:
    return {
        "VCENTER_AUTH_FAILED": "Authentication failed. Check username and password.",
        "VCENTER_DNS_FAILED": "Cannot resolve hostname. Check the vCenter URL.",
        "VCENTER_UNREACHABLE": "Could not reach vCenter. Check network connectivity.",
        "VCENTER_SSL_ERROR": "SSL certificate error. Try enabling 'Ignore SSL'.",
        "VCENTER_UNKNOWN_ERROR": "An unknown error occurred connecting to vCenter.",
    }.get(code, "Connection failed.")
