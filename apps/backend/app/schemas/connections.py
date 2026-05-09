from pydantic import BaseModel


class ConnectionStatus(BaseModel):
    name: str
    configured: bool
    status: str
    detail: str
    secret_name: str | None = None


class ConnectionTestResult(BaseModel):
    name: str
    status: str
    detail: str
