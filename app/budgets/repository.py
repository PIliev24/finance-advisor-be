from datetime import UTC, datetime

import aiosqlite


class BudgetRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get_by_id(self, budget_id: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM budgets_projection WHERE id = ?",
            (budget_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def get_by_category(self, category: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM budgets_projection WHERE category = ? AND is_active = 1",
            (category,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def list_all(self, active_only: bool = True) -> list[dict]:
        if active_only:
            cursor = await self._db.execute(
                "SELECT * FROM budgets_projection WHERE is_active = 1 ORDER BY category"
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM budgets_projection ORDER BY category"
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_current_usage(self, category: str) -> float:
        year_month = datetime.now(UTC).strftime("%Y-%m")
        cursor = await self._db.execute(
            """
            SELECT COALESCE(SUM(total_expenses), 0) as usage
            FROM monthly_summary_projection
            WHERE category = ? AND year_month = ?
            """,
            (category, year_month),
        )
        row = await cursor.fetchone()
        return float(row["usage"]) if row else 0.0

    async def get_all_usage(self) -> dict[str, float]:
        year_month = datetime.now(UTC).strftime("%Y-%m")
        cursor = await self._db.execute(
            """
            SELECT category, COALESCE(SUM(total_expenses), 0) as usage
            FROM monthly_summary_projection
            WHERE year_month = ?
            GROUP BY category
            """,
            (year_month,),
        )
        rows = await cursor.fetchall()
        return {row["category"]: float(row["usage"]) for row in rows}
