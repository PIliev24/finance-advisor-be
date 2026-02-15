from datetime import UTC, datetime

import aiosqlite
import structlog

from app.transactions.schemas import TransactionFilter

logger = structlog.get_logger()


def _months_ago(months: int) -> datetime:
    """Return a datetime that is `months` months before now (UTC)."""
    now = datetime.now(UTC)
    month = now.month - months
    year = now.year
    while month < 1:
        month += 12
        year -= 1
    day = min(now.day, 28)
    return now.replace(year=year, month=month, day=day)


class TransactionRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get_by_id(self, transaction_id: str) -> dict | None:
        cursor = await self._db.execute(
            """
            SELECT id, type, amount, currency, category, description,
                   date, is_deleted, created_at, updated_at
            FROM transactions_projection
            WHERE id = ?
            """,
            (transaction_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def list_filtered(self, filters: TransactionFilter) -> list[dict]:
        conditions: list[str] = ["is_deleted = 0"]
        params: list = []

        if filters.date_from is not None:
            conditions.append("date >= ?")
            params.append(filters.date_from)
        if filters.date_to is not None:
            conditions.append("date <= ?")
            params.append(filters.date_to)
        if filters.category is not None:
            conditions.append("category = ?")
            params.append(filters.category)
        if filters.type is not None:
            conditions.append("type = ?")
            params.append(filters.type)

        where_clause = " AND ".join(conditions)
        params.extend([filters.limit, filters.offset])

        cursor = await self._db.execute(
            f"""
            SELECT id, type, amount, currency, category, description,
                   date, is_deleted, created_at, updated_at
            FROM transactions_projection
            WHERE {where_clause}
            ORDER BY date DESC
            LIMIT ? OFFSET ?
            """,
            params,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_summary(self, year_month: str | None = None) -> list[dict]:
        if year_month is not None:
            cursor = await self._db.execute(
                """
                SELECT year_month, category, total_income, total_expenses, transaction_count
                FROM monthly_summary_projection
                WHERE year_month = ?
                ORDER BY category
                """,
                (year_month,),
            )
        else:
            cursor = await self._db.execute(
                """
                SELECT year_month, category, total_income, total_expenses, transaction_count
                FROM monthly_summary_projection
                ORDER BY year_month DESC, category
                """
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_recent(self, months: int = 3) -> list[dict]:
        cutoff_date = _months_ago(months).strftime("%Y-%m-%d")

        cursor = await self._db.execute(
            """
            SELECT id, type, amount, currency, category, description,
                   date, is_deleted, created_at, updated_at
            FROM transactions_projection
            WHERE is_deleted = 0 AND date >= ?
            ORDER BY date DESC
            """,
            (cutoff_date,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_spending_trend(self, category: str, months: int = 6) -> list[dict]:
        cutoff_month = _months_ago(months).strftime("%Y-%m")

        cursor = await self._db.execute(
            """
            SELECT year_month, category, total_income, total_expenses, transaction_count
            FROM monthly_summary_projection
            WHERE category = ? AND year_month >= ?
            ORDER BY year_month ASC
            """,
            (category, cutoff_month),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def calculate_savings_rate(self, months: int = 3) -> dict:
        cutoff_month = _months_ago(months).strftime("%Y-%m")

        cursor = await self._db.execute(
            """
            SELECT
                COALESCE(SUM(total_income), 0) AS total_income,
                COALESCE(SUM(total_expenses), 0) AS total_expenses
            FROM monthly_summary_projection
            WHERE year_month >= ?
            """,
            (cutoff_month,),
        )
        row = await cursor.fetchone()
        total_income = row["total_income"] if row else 0.0
        total_expenses = row["total_expenses"] if row else 0.0
        net_savings = total_income - total_expenses
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net_savings,
            "savings_rate": round(savings_rate, 2),
            "months_analyzed": months,
        }
