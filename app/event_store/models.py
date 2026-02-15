from dataclasses import dataclass
from enum import StrEnum


class AggregateType(StrEnum):
    transaction = "transaction"
    budget = "budget"
    life_event = "life_event"


class EventType(StrEnum):
    transaction_created = "transaction_created"
    transaction_updated = "transaction_updated"
    transaction_deleted = "transaction_deleted"
    budget_created = "budget_created"
    budget_updated = "budget_updated"
    budget_deleted = "budget_deleted"
    life_event_created = "life_event_created"
    life_event_updated = "life_event_updated"
    life_event_deleted = "life_event_deleted"


@dataclass(frozen=True)
class Event:
    event_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    event_data: str
    metadata: str | None
    version: int
    created_at: str
