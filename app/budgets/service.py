from datetime import UTC, datetime
from uuid import uuid4

import structlog

from app.budgets.repository import BudgetRepository
from app.budgets.schemas import BudgetAlert, BudgetCreate, BudgetResponse, BudgetUpdate
from app.event_store.models import AggregateType, EventType
from app.event_store.service import EventStoreService
from app.exceptions import ConflictError, NotFoundError, ValidationError

logger = structlog.get_logger()


class BudgetService:
    def __init__(self, event_store: EventStoreService, repo: BudgetRepository) -> None:
        self._event_store = event_store
        self._repo = repo

    async def create(self, data: BudgetCreate) -> BudgetResponse:
        existing = await self._repo.get_by_category(data.category)
        if existing:
            raise ConflictError(f"Budget for category '{data.category}' already exists")

        budget_id = str(uuid4())
        now = datetime.now(UTC).isoformat()

        event_data = {
            "id": budget_id,
            "category": data.category,
            "monthly_limit": data.monthly_limit,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        await self._event_store.append_event(
            aggregate_type=AggregateType.budget,
            aggregate_id=budget_id,
            event_type=EventType.budget_created,
            event_data=event_data,
        )

        logger.info("budget_created", budget_id=budget_id, category=data.category)

        usage = await self._repo.get_current_usage(data.category)
        return self._build_response(event_data, usage)

    async def list_all(self) -> list[BudgetResponse]:
        budgets = await self._repo.list_all(active_only=True)
        all_usage = await self._repo.get_all_usage()

        results: list[BudgetResponse] = []
        for budget in budgets:
            usage = all_usage.get(budget["category"], 0.0)
            results.append(self._build_response(budget, usage))

        return results

    async def update(self, budget_id: str, data: BudgetUpdate) -> BudgetResponse:
        budget = await self._repo.get_by_id(budget_id)
        if not budget:
            raise NotFoundError("Budget", budget_id)

        if not budget["is_active"]:
            raise ValidationError(f"Budget '{budget_id}' is deactivated")

        if data.monthly_limit is None:
            raise ValidationError("No update fields provided")

        now = datetime.now(UTC).isoformat()

        event_data = {
            "id": budget_id,
            "monthly_limit": data.monthly_limit,
            "updated_at": now,
        }

        await self._event_store.append_event(
            aggregate_type=AggregateType.budget,
            aggregate_id=budget_id,
            event_type=EventType.budget_updated,
            event_data=event_data,
        )

        logger.info(
            "budget_updated",
            budget_id=budget_id,
            monthly_limit=data.monthly_limit,
        )

        updated = await self._repo.get_by_id(budget_id)
        if not updated:
            raise NotFoundError("Budget", budget_id)

        usage = await self._repo.get_current_usage(updated["category"])
        return self._build_response(updated, usage)

    async def delete(self, budget_id: str) -> None:
        budget = await self._repo.get_by_id(budget_id)
        if not budget:
            raise NotFoundError("Budget", budget_id)

        now = datetime.now(UTC).isoformat()

        event_data = {
            "id": budget_id,
            "is_active": False,
            "updated_at": now,
        }

        await self._event_store.append_event(
            aggregate_type=AggregateType.budget,
            aggregate_id=budget_id,
            event_type=EventType.budget_deleted,
            event_data=event_data,
        )

        logger.info("budget_deleted", budget_id=budget_id)

    async def get_alerts(self) -> list[BudgetAlert]:
        budgets = await self._repo.list_all(active_only=True)
        all_usage = await self._repo.get_all_usage()

        alerts: list[BudgetAlert] = []
        for budget in budgets:
            usage = all_usage.get(budget["category"], 0.0)
            monthly_limit = budget["monthly_limit"]
            utilization = usage / monthly_limit if monthly_limit > 0 else 0.0
            alert_level = self._calculate_alert_level(utilization)

            if alert_level != "ok":
                alerts.append(
                    BudgetAlert(
                        category=budget["category"],
                        monthly_limit=monthly_limit,
                        current_usage=usage,
                        utilization_pct=round(utilization * 100, 2),
                        alert_level=alert_level,
                    )
                )

        return alerts

    async def get_status(self, category: str | None = None) -> list[dict]:
        if category:
            budget = await self._repo.get_by_category(category)
            if not budget:
                return []
            usage = await self._repo.get_current_usage(category)
            monthly_limit = budget["monthly_limit"]
            utilization = usage / monthly_limit if monthly_limit > 0 else 0.0
            return [
                {
                    "category": budget["category"],
                    "monthly_limit": monthly_limit,
                    "current_usage": usage,
                    "utilization_pct": round(utilization * 100, 2),
                    "alert_level": self._calculate_alert_level(utilization),
                    "is_active": bool(budget["is_active"]),
                }
            ]

        budgets = await self._repo.list_all(active_only=True)
        all_usage = await self._repo.get_all_usage()

        results: list[dict] = []
        for budget in budgets:
            usage = all_usage.get(budget["category"], 0.0)
            monthly_limit = budget["monthly_limit"]
            utilization = usage / monthly_limit if monthly_limit > 0 else 0.0
            results.append(
                {
                    "category": budget["category"],
                    "monthly_limit": monthly_limit,
                    "current_usage": usage,
                    "utilization_pct": round(utilization * 100, 2),
                    "alert_level": self._calculate_alert_level(utilization),
                    "is_active": bool(budget["is_active"]),
                }
            )

        return results

    def _build_response(self, budget: dict, usage: float) -> BudgetResponse:
        monthly_limit = budget["monthly_limit"]
        utilization = usage / monthly_limit if monthly_limit > 0 else 0.0

        return BudgetResponse(
            id=budget["id"],
            category=budget["category"],
            monthly_limit=monthly_limit,
            current_usage=usage,
            utilization_pct=round(utilization * 100, 2),
            alert_level=self._calculate_alert_level(utilization),
            is_active=bool(budget.get("is_active", True)),
            created_at=budget["created_at"],
            updated_at=budget["updated_at"],
        )

    @staticmethod
    def _calculate_alert_level(utilization_pct: float) -> str:
        if utilization_pct > 1.2:
            return "critical"
        if utilization_pct > 1.0:
            return "exceeded"
        if utilization_pct >= 0.8:
            return "warning"
        return "ok"
