from typing import Annotated

from fastapi import APIRouter, Depends

from app.context.schemas import (
    LifeEventCreate,
    LifeEventResponse,
    LifeEventUpdate,
    UserProfile,
)
from app.context.service import ContextService
from app.dependencies import APIKey

router = APIRouter()


def get_context_service() -> ContextService:
    from app.dependencies import get_context_service as _get

    return _get()


ContextServiceDep = Annotated[ContextService, Depends(get_context_service)]


@router.post("/events", status_code=201, response_model=LifeEventResponse)
async def add_life_event(
    data: LifeEventCreate,
    service: ContextServiceDep,
    _api_key: APIKey,
) -> LifeEventResponse:
    return await service.add_event(data)


@router.get("/events", response_model=list[LifeEventResponse])
async def list_life_events(
    service: ContextServiceDep,
    _api_key: APIKey,
) -> list[LifeEventResponse]:
    return await service.list_events()


@router.put("/events/{event_id}", response_model=LifeEventResponse)
async def update_life_event(
    event_id: str,
    data: LifeEventUpdate,
    service: ContextServiceDep,
    _api_key: APIKey,
) -> LifeEventResponse:
    return await service.update_event(event_id, data)


@router.delete("/events/{event_id}", status_code=204)
async def delete_life_event(
    event_id: str,
    service: ContextServiceDep,
    _api_key: APIKey,
) -> None:
    await service.delete_event(event_id)


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    service: ContextServiceDep,
    _api_key: APIKey,
) -> UserProfile:
    return await service.get_profile()
