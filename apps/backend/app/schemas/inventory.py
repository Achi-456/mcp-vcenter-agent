from pydantic import BaseModel


class VMInventoryItem(BaseModel):
    name: str
    power_state: str | None
    cpu: int | None
    memory_gb: float | None
    guest_os: str | None
    ip_address: str | None
    host: str | None
    datastore: str | None
    tools_status: str | None


class HostInventoryItem(BaseModel):
    name: str
    connection_state: str | None
    power_state: str | None
    version: str | None
    build: str | None
    vendor: str | None
    model: str | None
    cpu_cores: int | None
    memory_gb: float | None
    vm_count: int


class DatastoreInventoryItem(BaseModel):
    name: str
    type: str | None
    capacity_gb: float | None
    free_gb: float | None
    used_percent: float | None
    accessible: bool | None
