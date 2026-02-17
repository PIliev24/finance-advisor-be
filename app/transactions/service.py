from uuid import uuid4

import structlog

from app.event_store.models import AggregateType, EventType
from app.event_store.service import EventStoreService
from app.exceptions import NotFoundError, ValidationError
from app.transactions.repository import TransactionRepository
from app.transactions.schemas import (
    MonthlySummary,
    TransactionCreate,
    TransactionFilter,
    TransactionResponse,
    TransactionUpdate,
)

logger = structlog.get_logger()


class TransactionService:
    def __init__(
        self,
        event_store: EventStoreService,
        repo: TransactionRepository,
    ) -> None:
        self._event_store = event_store
        self._repo = repo

    async def create(self, data: TransactionCreate) -> TransactionResponse:
        transaction_id = str(uuid4())

        event_data = {
            "type": data.type,
            "amount": data.amount,
            "category": data.category,
            "description": data.description,
            "date": data.date,
            "currency": data.currency,
        }

        await self._event_store.append_event(
            aggregate_type=AggregateType.transaction,
            aggregate_id=transaction_id,
            event_type=EventType.transaction_created,
            event_data=event_data,
        )

        row = await self._repo.get_by_id(transaction_id)
        if row is None:
            raise ValidationError("Failed to create transaction")

        logger.info("transaction_created", transaction_id=transaction_id)
        return self._to_response(row)

    async def get_by_id(self, transaction_id: str) -> TransactionResponse:
        row = await self._repo.get_by_id(transaction_id)
        if row is None or row["is_deleted"]:
            raise NotFoundError("Transaction", transaction_id)
        return self._to_response(row)

    async def list_transactions(self, filters: TransactionFilter) -> list[TransactionResponse]:
        rows = await self._repo.list_filtered(filters)
        return [self._to_response(row) for row in rows]

    async def update(self, transaction_id: str, data: TransactionUpdate) -> TransactionResponse:
        existing = await self._repo.get_by_id(transaction_id)
        if existing is None or existing["is_deleted"]:
            raise NotFoundError("Transaction", transaction_id)

        update_data = data.model_dump(exclude_none=True)
        if not update_data:
            raise ValidationError("No fields to update")

        await self._event_store.append_event(
            aggregate_type=AggregateType.transaction,
            aggregate_id=transaction_id,
            event_type=EventType.transaction_updated,
            event_data=update_data,
        )

        row = await self._repo.get_by_id(transaction_id)
        if row is None:
            raise NotFoundError("Transaction", transaction_id)

        logger.info("transaction_updated", transaction_id=transaction_id)
        return self._to_response(row)

    async def delete(self, transaction_id: str) -> None:
        existing = await self._repo.get_by_id(transaction_id)
        if existing is None or existing["is_deleted"]:
            raise NotFoundError("Transaction", transaction_id)

        await self._event_store.append_event(
            aggregate_type=AggregateType.transaction,
            aggregate_id=transaction_id,
            event_type=EventType.transaction_deleted,
            event_data={"deleted": True},
        )

        logger.info("transaction_deleted", transaction_id=transaction_id)

    async def get_summary(self, year_month: str | None = None) -> list[MonthlySummary]:
        rows = await self._repo.get_summary(year_month)
        return [
            MonthlySummary(
                year_month=row["year_month"],
                category=row["category"],
                total_income=row["total_income"],
                total_expenses=row["total_expenses"],
                transaction_count=row["transaction_count"],
            )
            for row in rows
        ]

    async def get_recent(self, months: int = 3) -> list[TransactionResponse]:
        rows = await self._repo.get_recent(months)
        return [self._to_response(row) for row in rows]

    async def get_spending_trend(self, category: str, months: int = 6) -> list[dict]:
        return await self._repo.get_spending_trend(category, months)

    async def calculate_savings_rate(self, months: int = 3) -> dict:
        return await self._repo.calculate_savings_rate(months)

    def _to_response(self, row: dict) -> TransactionResponse:
        return TransactionResponse(
            id=row["id"],
            type=row["type"],
            amount=row["amount"],
            currency=row["currency"],
            category=row["category"],
            description=row["description"],
            date=row["date"],
            is_deleted=bool(row["is_deleted"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
