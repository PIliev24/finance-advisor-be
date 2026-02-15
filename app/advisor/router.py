"""Advisor API endpoints — sync and streaming chat."""

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.dependencies import AdvisorServiceDep, APIKey

router = APIRouter()


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_class=EventSourceResponse)
async def chat_stream(
    request: ChatRequest,
    service: AdvisorServiceDep,
    _api_key: APIKey,
) -> EventSourceResponse:
    """Stream advisor responses via Server-Sent Events."""
    return EventSourceResponse(service.chat_stream(request.query))


@router.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(
    request: ChatRequest,
    service: AdvisorServiceDep,
    _api_key: APIKey,
) -> ChatResponse:
    """Synchronous advisor chat -- returns the full response at once."""
    response = await service.chat(request.query)
    return ChatResponse(response=response)
