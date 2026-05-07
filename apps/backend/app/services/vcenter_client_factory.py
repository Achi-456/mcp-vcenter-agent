from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

from app.services.k8s_secret_store import get_secret, VCENTER_SECRET_NAME
from app.core.inventory_errors import error_response


def get_vcenter_credentials() -> dict | None:
    s = get_secret(VCENTER_SECRET_NAME)
    if not s:
        return None
    url = s.get("VCENTER_URL", "")
    user = s.get("VCENTER_USERNAME", "")
    pwd = s.get("VCENTER_PASSWORD", "")
    ssl = s.get("VCENTER_VERIFY_SSL", "false") == "true"
    if not url or not user or not pwd:
        return None
    return {"url": url, "username": user, "password": pwd, "verify_ssl": ssl}


def connect_to_vcenter(creds: dict) -> vim.ServiceInstance:
    host = creds["url"].replace("https://", "").replace("http://", "").split("/")[0]
    port = 443
    if ":" in host:
        host, port_str = host.split(":", 1)
        port = int(port_str)
    return SmartConnect(
        host=host,
        user=creds["username"],
        pwd=creds["password"],
        port=port,
        disableSslCertValidation=not creds["verify_ssl"],
    )


def disconnect_from_vcenter(si: vim.ServiceInstance) -> None:
    try:
        Disconnect(si)
    except Exception:
        pass


def with_vcenter(fn):
    creds = get_vcenter_credentials()
    if not creds:
        return error_response("VCENTER_NOT_CONFIGURED")
    try:
        si = connect_to_vcenter(creds)
        result = fn(si, si.RetrieveContent())
        disconnect_from_vcenter(si)
        return result
    except Exception as e:
        msg = str(e).lower()
        if "auth" in msg or "login" in msg:
            return error_response("VCENTER_AUTH_FAILED")
        if "refused" in msg or "timeout" in msg:
            return error_response("VCENTER_UNREACHABLE")
        if "ssl" in msg or "certificate" in msg:
            return error_response("VCENTER_SSL_ERROR")
        return error_response("VCENTER_INVENTORY_ERROR")
