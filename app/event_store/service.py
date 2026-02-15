import json
from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite
import structlog

from app.event_store.models import Event
from app.event_store.projections import ProjectionEngine
from app.event_store.repository import EventRepository
from app.exceptions import ConflictError

logger = structlog.get_logger()


class EventStoreService:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db
        self._repository = EventRepository(db)
        self._projection_engine = ProjectionEngine(db)

    async def append_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        event_data: dict,
        metadata: dict | None = None,
        idempotency_key: str | None = None,
    ) -> Event:
        if idempotency_key is not None:
            if await self._repository.check_idempotency(idempotency_key):
                raise ConflictError(
                    f"Event with idempotency key '{idempotency_key}' already exists"
                )
            if metadata is None:
                metadata = {}
            metadata["idempotency_key"] = idempotency_key

        version = await self._repository.get_latest_version(aggregate_id) + 1

        event = Event(
            event_id=str(uuid4()),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            event_data=json.dumps(event_data),
            metadata=json.dumps(metadata) if metadata else None,
            version=version,
            created_at=datetime.now(UTC).isoformat(),
        )

        await self._repository.append(event)
        await self._projection_engine.project(event)
        await self._db.commit()

        logger.info(
            "event_stored_and_projected",
            event_id=event.event_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            version=version,
        )

        return event

    async def get_events(
        self,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
    ) -> list[Event]:
        if aggregate_id is not None and aggregate_type is not None:
            return await self._repository.get_by_aggregate(aggregate_type, aggregate_id)
        return await self._repository.get_all(aggregate_type=aggregate_type)
