import aiosqlite


class ContextRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get_by_id(self, event_id: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM life_events_projection WHERE id = ? AND is_deleted = 0",
            (event_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def list_all(self) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM life_events_projection WHERE is_deleted = 0 ORDER BY date DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_profile(self) -> dict:
        events = await self.list_all()

        if not events:
            summary = "No life events recorded yet."
        else:
            event_descriptions = []
            for event in events:
                desc = f"{event['event_type']} on {event['date']}"
                if event.get("description"):
                    desc += f": {event['description']}"
                if event.get("impact"):
                    desc += f" (impact: {event['impact']})"
                event_descriptions.append(desc)
            summary = (
                f"User has {len(events)} life event(s): " + "; ".join(event_descriptions) + "."
            )

        return {
            "life_events": events,
            "summary": summary,
        }
