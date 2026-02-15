from pydantic import BaseModel


class EventResponse(BaseModel):
    event_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    event_data: str
    metadata: str | None
    version: int
    created_at: str
