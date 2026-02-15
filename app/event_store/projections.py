import json

import aiosqlite
import structlog

from app.event_store.models import Event, EventType

logger = structlog.get_logger()


class ProjectionEngine:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def project(self, event: Event) -> None:
        handler = self._get_handler(event.event_type)
        if handler is not None:
            data = json.loads(event.event_data)
            await handler(event, data)
            logger.info(
                "projection_applied",
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
            )

    def _get_handler(self, event_type: str):
        handlers = {
            EventType.transaction_created: self._handle_transaction_created,
            EventType.transaction_updated: self._handle_transaction_updated,
            EventType.transaction_deleted: self._handle_transaction_deleted,
            EventType.budget_created: self._handle_budget_created,
            EventType.budget_updated: self._handle_budget_updated,
            EventType.budget_deleted: self._handle_budget_deleted,
            EventType.life_event_created: self._handle_life_event_created,
            EventType.life_event_updated: self._handle_life_event_updated,
            EventType.life_event_deleted: self._handle_life_event_deleted,
        }
        return handlers.get(event_type)

    async def _handle_transaction_created(self, event: Event, data: dict) -> None:
        await self._db.execute(
            """
            INSERT INTO transactions_projection (
                id, type, amount, currency, category, description,
                date, is_deleted, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                event.aggregate_id,
                data["type"],
                data["amount"],
                data.get("currency", "EUR"),
                data["category"],
                data.get("description"),
                data["date"],
                event.created_at,
                event.created_at,
            ),
        )
        await self._update_monthly_summary(data)

    async def _handle_transaction_updated(self, event: Event, data: dict) -> None:
        cursor = await self._db.execute(
            """
            SELECT type, amount, currency, category, description, date
            FROM transactions_projection
            WHERE id = ? AND is_deleted = 0
            """,
            (event.aggregate_id,),
        )
        old_row = await cursor.fetchone()
        if old_row is None:
            return

        old_data = {
            "type": old_row["type"],
            "amount": old_row["amount"],
            "category": old_row["category"],
            "date": old_row["date"],
        }
        await self._reverse_monthly_summary(old_data)

        new_amount = data.get("amount", old_row["amount"])
        new_category = data.get("category", old_row["category"])
        new_description = data.get("description", old_row["description"])
        new_date = data.get("date", old_row["date"])

        await self._db.execute(
            """
            UPDATE transactions_projection
            SET amount = ?, category = ?, description = ?, date = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                new_amount,
                new_category,
                new_description,
                new_date,
                event.created_at,
                event.aggregate_id,
            ),
        )

        updated_data = {
            "type": old_row["type"],
            "amount": new_amount,
            "category": new_category,
            "date": new_date,
        }
        await self._update_monthly_summary(updated_data)

    async def _handle_transaction_deleted(self, event: Event, data: dict) -> None:
        cursor = await self._db.execute(
            """
            SELECT type, amount, category, date
            FROM transactions_projection
            WHERE id = ? AND is_deleted = 0
            """,
            (event.aggregate_id,),
        )
        old_row = await cursor.fetchone()

        await self._db.execute(
            """
            UPDATE transactions_projection
            SET is_deleted = 1, updated_at = ?
            WHERE id = ?
            """,
            (event.created_at, event.aggregate_id),
        )

        if old_row is not None:
            old_data = {
                "type": old_row["type"],
                "amount": old_row["amount"],
                "category": old_row["category"],
                "date": old_row["date"],
            }
            await self._reverse_monthly_summary(old_data)

    async def _update_monthly_summary(self, data: dict) -> None:
        year_month = data["date"][:7]
        category = data["category"]
        amount = data["amount"]
        txn_type = data["type"]

        income_delta = amount if txn_type == "income" else 0.0
        expense_delta = amount if txn_type == "expense" else 0.0

        await self._db.execute(
            """
            INSERT INTO monthly_summary_projection (
                year_month, category, total_income, total_expenses, transaction_count
            ) VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(year_month, category) DO UPDATE SET
                total_income = total_income + ?,
                total_expenses = total_expenses + ?,
                transaction_count = transaction_count + 1
            """,
            (
                year_month,
                category,
                income_delta,
                expense_delta,
                income_delta,
                expense_delta,
            ),
        )

    async def _reverse_monthly_summary(self, data: dict) -> None:
        year_month = data["date"][:7]
        category = data["category"]
        amount = data["amount"]
        txn_type = data["type"]

        income_delta = amount if txn_type == "income" else 0.0
        expense_delta = amount if txn_type == "expense" else 0.0

        await self._db.execute(
            """
            UPDATE monthly_summary_projection
            SET total_income = total_income - ?,
                total_expenses = total_expenses - ?,
                transaction_count = transaction_count - 1
            WHERE year_month = ? AND category = ?
            """,
            (income_delta, expense_delta, year_month, category),
        )

    async def _handle_budget_created(self, event: Event, data: dict) -> None:
        await self._db.execute(
            """
            INSERT INTO budgets_projection (
                id, category, monthly_limit, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?)
            """,
            (
                event.aggregate_id,
                data["category"],
                data["monthly_limit"],
                event.created_at,
                event.created_at,
            ),
        )

    async def _handle_budget_updated(self, event: Event, data: dict) -> None:
        set_clauses: list[str] = []
        params: list = []

        if "monthly_limit" in data:
            set_clauses.append("monthly_limit = ?")
            params.append(data["monthly_limit"])
        if "category" in data:
            set_clauses.append("category = ?")
            params.append(data["category"])
        if "is_active" in data:
            set_clauses.append("is_active = ?")
            params.append(1 if data["is_active"] else 0)

        set_clauses.append("updated_at = ?")
        params.append(event.created_at)
        params.append(event.aggregate_id)

        await self._db.execute(
            f"""
            UPDATE budgets_projection
            SET {', '.join(set_clauses)}
            WHERE id = ?
            """,
            params,
        )

    async def _handle_budget_deleted(self, event: Event, data: dict) -> None:
        await self._db.execute(
            """
            UPDATE budgets_projection
            SET is_active = 0, updated_at = ?
            WHERE id = ?
            """,
            (event.created_at, event.aggregate_id),
        )

    async def _handle_life_event_created(self, event: Event, data: dict) -> None:
        await self._db.execute(
            """
            INSERT INTO life_events_projection (
                id, event_type, description, date, impact,
                is_deleted, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                event.aggregate_id,
                data["event_type"],
                data.get("description"),
                data["date"],
                data.get("impact"),
                event.created_at,
                event.created_at,
            ),
        )

    async def _handle_life_event_updated(self, event: Event, data: dict) -> None:
        set_clauses: list[str] = []
        params: list = []

        if "event_type" in data:
            set_clauses.append("event_type = ?")
            params.append(data["event_type"])
        if "description" in data:
            set_clauses.append("description = ?")
            params.append(data["description"])
        if "date" in data:
            set_clauses.append("date = ?")
            params.append(data["date"])
        if "impact" in data:
            set_clauses.append("impact = ?")
            params.append(data["impact"])

        set_clauses.append("updated_at = ?")
        params.append(event.created_at)
        params.append(event.aggregate_id)

        await self._db.execute(
            f"""
            UPDATE life_events_projection
            SET {', '.join(set_clauses)}
            WHERE id = ?
            """,
            params,
        )

    async def _handle_life_event_deleted(self, event: Event, data: dict) -> None:
        await self._db.execute(
            """
            UPDATE life_events_projection
            SET is_deleted = 1, updated_at = ?
            WHERE id = ?
            """,
            (event.created_at, event.aggregate_id),
        )
