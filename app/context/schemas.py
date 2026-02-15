from enum import StrEnum

from pydantic import BaseModel


class LifeEventType(StrEnum):
    expecting_baby = "expecting_baby"
    job_change = "job_change"
    retirement_planning = "retirement_planning"
    major_purchase = "major_purchase"
    debt_payoff = "debt_payoff"
    education = "education"
    relocation = "relocation"
    marriage = "marriage"
    health_event = "health_event"
    other = "other"


class LifeEventCreate(BaseModel):
    event_type: LifeEventType
    description: str | None = None
    date: str
    impact: str | None = None


class LifeEventUpdate(BaseModel):
    description: str | None = None
    date: str | None = None
    impact: str | None = None


class LifeEventResponse(BaseModel):
    id: str
    event_type: str
    description: str | None
    date: str
    impact: str | None
    created_at: str
    updated_at: str


class UserProfile(BaseModel):
    life_events: list[LifeEventResponse]
    summary: str
