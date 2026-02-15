from datetime import UTC, datetime
from uuid import uuid4

import structlog

from app.context.repository import ContextRepository
from app.context.schemas import (
    LifeEventCreate,
    LifeEventResponse,
    LifeEventUpdate,
    UserProfile,
)
from app.event_store.models import AggregateType, EventType
from app.event_store.service import EventStoreService
from app.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()


class ContextService:
    def __init__(self, event_store: EventStoreService, repo: ContextRepository) -> None:
        self._event_store = event_store
        self._repo = repo

    async def add_event(self, data: LifeEventCreate) -> LifeEventResponse:
        event_id = str(uuid4())
        now = datetime.now(UTC).isoformat()

        event_data = {
            "id": event_id,
            "event_type": data.event_type.value,
            "description": data.description,
            "date": data.date,
            "impact": data.impact,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        await self._event_store.append_event(
            aggregate_type=AggregateType.life_event,
            aggregate_id=event_id,
            event_type=EventType.life_event_created,
            event_data=event_data,
        )

        logger.info(
            "life_event_created",
            event_id=event_id,
            event_type=data.event_type.value,
        )

        return self._build_response(event_data)

    async def list_events(self) -> list[LifeEventResponse]:
        events = await self._repo.list_all()
        return [self._build_response(e) for e in events]

    async def update_event(
        self, event_id: str, data: LifeEventUpdate
    ) -> LifeEventResponse:
        existing = await self._repo.get_by_id(event_id)
        if not existing:
            raise NotFoundError("LifeEvent", event_id)

        updates: dict = {}
        if data.description is not None:
            updates["description"] = data.description
        if data.date is not None:
            updates["date"] = data.date
        if data.impact is not None:
            updates["impact"] = data.impact

        if not updates:
            raise ValidationError("No update fields provided")

        now = datetime.now(UTC).isoformat()
        updates["id"] = event_id
        updates["updated_at"] = now

        await self._event_store.append_event(
            aggregate_type=AggregateType.life_event,
            aggregate_id=event_id,
            event_type=EventType.life_event_updated,
            event_data=updates,
        )

        logger.info("life_event_updated", event_id=event_id)

        updated = await self._repo.get_by_id(event_id)
        if not updated:
            raise NotFoundError("LifeEvent", event_id)

        return self._build_response(updated)

    async def delete_event(self, event_id: str) -> None:
        existing = await self._repo.get_by_id(event_id)
        if not existing:
            raise NotFoundError("LifeEvent", event_id)

        now = datetime.now(UTC).isoformat()

        event_data = {
            "id": event_id,
            "is_deleted": True,
            "updated_at": now,
        }

        await self._event_store.append_event(
            aggregate_type=AggregateType.life_event,
            aggregate_id=event_id,
            event_type=EventType.life_event_deleted,
            event_data=event_data,
        )

        logger.info("life_event_deleted", event_id=event_id)

    async def get_profile(self) -> UserProfile:
        profile_data = await self._repo.get_profile()
        life_events = [
            self._build_response(e) for e in profile_data["life_events"]
        ]
        return UserProfile(
            life_events=life_events,
            summary=profile_data["summary"],
        )

    async def get_assembled_profile(self) -> dict:
        profile_data = await self._repo.get_profile()
        return {
            "life_events": [
                {
                    "id": e["id"],
                    "event_type": e["event_type"],
                    "description": e.get("description"),
                    "date": e["date"],
                    "impact": e.get("impact"),
                    "created_at": e["created_at"],
                    "updated_at": e["updated_at"],
                }
                for e in profile_data["life_events"]
            ],
            "summary": profile_data["summary"],
        }

    @staticmethod
    def _build_response(event: dict) -> LifeEventResponse:
        return LifeEventResponse(
            id=event["id"],
            event_type=event["event_type"],
            description=event.get("description"),
            date=event["date"],
            impact=event.get("impact"),
            created_at=event["created_at"],
            updated_at=event["updated_at"],
        )
