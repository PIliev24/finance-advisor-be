from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.exceptions import UnauthorizedError

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest) -> TokenResponse:
    if data.username != settings.auth_username or data.password != settings.auth_password:
        raise UnauthorizedError("Invalid credentials")

    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": data.username, "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return TokenResponse(access_token=token)
