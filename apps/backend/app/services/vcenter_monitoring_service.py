from typing import Any

from pyVmomi import vim

from app.services.vcenter_session import VCenterSession, get_vcenter_session


SUPPORTED_RECENT_EVENT_TYPES = [
    "AlarmStatusChangedEvent",
    "DatastoreCreatedEvent",
    "DatastoreDestroyedEvent",
    "HostConnectedEvent",
    "HostConnectionLostEvent",
    "HostDisconnectedEvent",
    "UserLoginSessionEvent",
    "UserLogoutSessionEvent",
    "VmCreatedEvent",
    "VmPoweredOffEvent",
    "VmPoweredOnEvent",
    "VmReconfiguredEvent",
    "VmRemovedEvent",
    "VmRenamedEvent",
    "VmSuspendedEvent",
]


def normalize_alarm(alarm_state: Any) -> dict[str, Any]:
    alarm = getattr(alarm_state, "alarm", None)
    entity = getattr(alarm_state, "entity", None)
    info = getattr(alarm, "info", None)
    return {
        "entity_name": getattr(entity, "name", None),
        "entity_type": entity.__class__.__name__ if entity is not None else None,
        "overall_status": str(getattr(alarm_state, "overallStatus", None)),
        "alarm_name": getattr(info, "name", None),
    }


def normalize_event(event: Any) -> dict[str, Any]:
    entity = getattr(event, "vm", None) or getattr(event, "host", None) or getattr(event, "datastore", None)
    created_time = getattr(event, "createdTime", None)
    return {
        "created_time": created_time.isoformat() if created_time else None,
        "username": getattr(event, "userName", None),
        "full_formatted_message": getattr(event, "fullFormattedMessage", None),
        "entity_name": getattr(entity, "name", None),
        "event_type": event.__class__.__name__,
    }


class VCenterMonitoringService:
    def __init__(self, session: VCenterSession | None = None) -> None:
        self.session = session or get_vcenter_session()

    async def get_active_alarms(self) -> list[dict[str, Any]]:
        def collect(_si: Any, content: Any) -> list[dict[str, Any]]:
            root = content.rootFolder
            alarms = getattr(root, "triggeredAlarmState", []) or []
            return [normalize_alarm(alarm) for alarm in alarms]

        return await self.session.run(collect)

    async def get_recent_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        def collect(_si: Any, content: Any) -> list[dict[str, Any]]:
            event_filter = vim.event.EventFilterSpec()
            # Some broad task events can reference vCenter objects not
            # deserializable by pyVmomi 8.0 U3, such as ContentLibrary.
            # Limit Phase 2 to concrete infrastructure event classes.
            event_filter.eventTypeId = SUPPORTED_RECENT_EVENT_TYPES
            events = content.eventManager.QueryEvents(event_filter) or []
            return [normalize_event(event) for event in events[-limit:]]

        return await self.session.run(collect)
