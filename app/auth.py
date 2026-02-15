from fastapi import Header

from app.config import settings
from app.exceptions import AppError


async def verify_api_key(x_api_key: str = Header()) -> str:
    if x_api_key != settings.api_key:
        raise AppError("Invalid API key", code="UNAUTHORIZED")
    return x_api_key
