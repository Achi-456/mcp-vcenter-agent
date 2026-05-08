from pydantic import BaseModel, Field


class VCenterConnectionRequest(BaseModel):
    name: str = Field(min_length=1, description="Connection name label")
    vcenter_url: str = Field(min_length=1, pattern=r"^https?://", description="vCenter URL")
    username: str = Field(min_length=1, description="vCenter username")
    password: str = Field(min_length=1, description="vCenter password")
    verify_ssl: bool = Field(default=False, description="Verify SSL certificate")


class VCenterTestResponse(BaseModel):
    ok: bool
    status: str
    message: str
    error_code: str | None = None


class VCenterConnectionStatus(BaseModel):
    configured: bool
    name: str | None = None
    vcenter_url: str | None = None
    username_hint: str | None = None
    verify_ssl: bool | None = None
    password_set: bool = False
    last_test_status: str | None = None
    last_tested_at: str | None = None


class VCenterSaveResponse(BaseModel):
    ok: bool
    status: str
    message: str
    connection: VCenterConnectionStatus | None = None


class LLMConnectionRequest(BaseModel):
    provider: str = Field(min_length=1)
    base_url: str = Field(min_length=1, pattern=r"^https?://")
    model: str = Field(min_length=1)
    api_key: str = Field(min_length=1)


class LLMTestResponse(BaseModel):
    ok: bool
    status: str
    message: str
    error_code: str | None = None


class LLMConnectionStatus(BaseModel):
    configured: bool
    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    api_key_set: bool = False
    last_test_status: str | None = None
    last_tested_at: str | None = None


class LLMSaveResponse(BaseModel):
    ok: bool
    status: str
    message: str
    connection: LLMConnectionStatus | None = None


class ConnectionDeleteResponse(BaseModel):
    ok: bool
    status: str
    message: str
