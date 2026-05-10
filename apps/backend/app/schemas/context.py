from pydantic import BaseModel


class DatastoreHealthItem(BaseModel):
    name: str
    used_percent: float | None
    status: str
    capacity_gb: float | None
    free_gb: float | None
    accessible: bool | None


class EnvironmentOverview(BaseModel):
    vm_count: int
    host_count: int
    datastore_count: int
    active_alarm_count: int
    critical_datastore_count: int
    warning_datastore_count: int
    rke2_vm_count: int
