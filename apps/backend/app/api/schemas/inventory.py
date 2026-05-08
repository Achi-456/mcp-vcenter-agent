from pydantic import BaseModel


class VMInventoryItem(BaseModel):
    id: str
    name: str
    power_state: str
    cpu: int
    memory_gb: float
    guest_os: str | None = None
    ip_address: str | None = None
    host: str | None = None
    cluster: str | None = None
    datastore: str | None = None
    tools_status: str | None = None
    uptime_seconds: int | None = None
    path: str | None = None


class HostInventoryItem(BaseModel):
    id: str
    name: str
    connection_state: str
    power_state: str
    cpu_cores: int
    cpu_threads: int
    memory_gb: float
    vm_count: int
    vendor: str | None = None
    model: str | None = None
    version: str | None = None
    cluster: str | None = None


class DatastoreInventoryItem(BaseModel):
    id: str
    name: str
    type: str
    capacity_gb: float
    free_gb: float
    used_gb: float
    used_percent: float
    accessible: bool
    multiple_host_access: bool


class NetworkInventoryItem(BaseModel):
    id: str
    name: str
    type: str
    accessible: bool


class ClusterInventoryItem(BaseModel):
    id: str
    name: str
    num_hosts: int
    num_vms: int
    total_cpu_mhz: int
    total_memory_mb: int


class AlarmItem(BaseModel):
    id: str
    name: str
    entity: str
    entity_type: str
    severity: str
    acknowledged: bool = False
    time: str | None = None
    description: str = ""


class EventItem(BaseModel):
    id: int
    type: str
    message: str
    username: str = ""
    created_at: str | None = None
    severity: str = "info"
    entity: str = ""
    entity_type: str = ""


class InventoryListResponse(BaseModel):
    items: list
    count: int
    source: str = "vcenter"
    cached: bool = False
    collected_at: str


class InventoryOverviewResponse(BaseModel):
    vms: dict
    hosts: dict
    datastores: dict
    networks: dict
    alarms: dict | None = None
    source: str = "vcenter"
    cached: bool = False
    collected_at: str


class ContextResponse(BaseModel):
    summary: str
    count: int | None = None
    vms: list | None = None
    overview: dict | None = None
    healthy: int | None = None
    warning: int | None = None
    critical: int | None = None
    datastores: list | None = None
    alarms: list | None = None
    events: list | None = None
    total: int | None = None
    errors: int | None = None


class LLMProvider(BaseModel):
    id: str
    name: str
    enabled: bool
    models: list[str] = []


class LLMModel(BaseModel):
    id: str
    name: str


class LLMStatus(BaseModel):
    configured: bool
    provider: str | None = None
    model: str | None = None
    ready: bool = False


class InventoryErrorResponse(BaseModel):
    ok: bool = False
    error_code: str
    message: str
