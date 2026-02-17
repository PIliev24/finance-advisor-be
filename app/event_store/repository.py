import aiosqlite
import structlog

from app.event_store.models import Event

logger = structlog.get_logger()


class EventRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def append(self, event: Event) -> None:
        await self._db.execute(
            """
            INSERT INTO events (
                event_id, aggregate_type, aggregate_id, event_type,
                event_data, metadata, version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.aggregate_type,
                event.aggregate_id,
                event.event_type,
                event.event_data,
                event.metadata,
                event.version,
                event.created_at,
            ),
        )
        logger.info(
            "event_appended",
            event_id=event.event_id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            version=event.version,
        )

    async def get_by_aggregate(self, aggregate_type: str, aggregate_id: str) -> list[Event]:
        cursor = await self._db.execute(
            """
            SELECT event_id, aggregate_type, aggregate_id, event_type,
                   event_data, metadata, version, created_at
            FROM events
            WHERE aggregate_type = ? AND aggregate_id = ?
            ORDER BY version ASC
            """,
            (aggregate_type, aggregate_id),
        )
        rows = await cursor.fetchall()
        return [
            Event(
                event_id=row["event_id"],
                aggregate_type=row["aggregate_type"],
                aggregate_id=row["aggregate_id"],
                event_type=row["event_type"],
                event_data=row["event_data"],
                metadata=row["metadata"],
                version=row["version"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def get_all(self, aggregate_type: str | None = None, limit: int = 100) -> list[Event]:
        if aggregate_type is not None:
            cursor = await self._db.execute(
                """
                SELECT event_id, aggregate_type, aggregate_id, event_type,
                       event_data, metadata, version, created_at
                FROM events
                WHERE aggregate_type = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (aggregate_type, limit),
            )
        else:
            cursor = await self._db.execute(
                """
                SELECT event_id, aggregate_type, aggregate_id, event_type,
                       event_data, metadata, version, created_at
                FROM events
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = await cursor.fetchall()
        return [
            Event(
                event_id=row["event_id"],
                aggregate_type=row["aggregate_type"],
                aggregate_id=row["aggregate_id"],
                event_type=row["event_type"],
                event_data=row["event_data"],
                metadata=row["metadata"],
                version=row["version"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def get_latest_version(self, aggregate_id: str) -> int:
        cursor = await self._db.execute(
            """
            SELECT COALESCE(MAX(version), 0) AS latest_version
            FROM events
            WHERE aggregate_id = ?
            """,
            (aggregate_id,),
        )
        row = await cursor.fetchone()
        return row["latest_version"] if row else 0

    async def check_idempotency(self, idempotency_key: str) -> bool:
        cursor = await self._db.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM events
            WHERE metadata IS NOT NULL
              AND json_extract(metadata, '$.idempotency_key') = ?
            """,
            (idempotency_key,),
        )
        row = await cursor.fetchone()
        return row["cnt"] > 0 if row else False
