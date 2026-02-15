from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import AppError, ConflictError, NotFoundError, ValidationError


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": exc.code, "message": exc.message},
    )


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": exc.code, "message": exc.message},
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": exc.code, "message": exc.message},
    )


async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": exc.code, "message": exc.message},
    )


def register_exception_handlers(app):
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(ConflictError, conflict_handler)
    app.add_exception_handler(AppError, app_error_handler)
