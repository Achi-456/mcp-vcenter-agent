from pydantic import BaseModel


class AlarmItem(BaseModel):
    entity_name: str | None
    entity_type: str | None
    overall_status: str | None
    alarm_name: str | None


class EventItem(BaseModel):
    created_time: str | None
    username: str | None
    full_formatted_message: str | None
    entity_name: str | None
    event_type: str
