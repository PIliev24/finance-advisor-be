from typing import Annotated

from fastapi import APIRouter, Depends

from app.budgets.schemas import BudgetAlert, BudgetCreate, BudgetResponse, BudgetUpdate
from app.budgets.service import BudgetService
from app.dependencies import APIKey

router = APIRouter()


def get_budget_service() -> BudgetService:
    from app.dependencies import get_budget_service as _get

    return _get()


BudgetServiceDep = Annotated[BudgetService, Depends(get_budget_service)]


@router.post("/", status_code=201, response_model=BudgetResponse)
async def create_budget(
    data: BudgetCreate,
    service: BudgetServiceDep,
    _api_key: APIKey,
) -> BudgetResponse:
    return await service.create(data)


@router.get("/", response_model=list[BudgetResponse])
async def list_budgets(
    service: BudgetServiceDep,
    _api_key: APIKey,
) -> list[BudgetResponse]:
    return await service.list_all()


@router.get("/alerts", response_model=list[BudgetAlert])
async def get_alerts(
    service: BudgetServiceDep,
    _api_key: APIKey,
) -> list[BudgetAlert]:
    return await service.get_alerts()


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    data: BudgetUpdate,
    service: BudgetServiceDep,
    _api_key: APIKey,
) -> BudgetResponse:
    return await service.update(budget_id, data)


@router.delete("/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: str,
    service: BudgetServiceDep,
    _api_key: APIKey,
) -> None:
    await service.delete(budget_id)
