from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.router import router as auth_router
from app.database import database_is_ready, get_db_session, lifespan

REDACTED_VALUE = "[redacted]"
SENSITIVE_FIELDS = {"password", "password_hash"}

app = FastAPI(title="Untexted API", lifespan=lifespan)
app.include_router(auth_router)


def _redact_sensitive_values(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: (
                REDACTED_VALUE
                if key in SENSITIVE_FIELDS
                else _redact_sensitive_values(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_sensitive_values(item) for item in value]
    return value


def _redact_validation_errors(
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    redacted_errors: list[dict[str, Any]] = []

    for error in errors:
        item = dict(error)
        location = item.get("loc", ())
        if any(field in location for field in SENSITIVE_FIELDS):
            if "input" in item:
                item["input"] = REDACTED_VALUE
        elif "input" in item:
            item["input"] = _redact_sensitive_values(item["input"])
        if "ctx" in item:
            item["ctx"] = _redact_sensitive_values(item["ctx"])
        redacted_errors.append(item)

    return redacted_errors


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return FastAPI's validation format without echoing sensitive input."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(_redact_validation_errors(exc.errors()))},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Return the current service liveness status."""
    return {"status": "ok"}


@app.get("/ready")
async def ready(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JSONResponse:
    """Return readiness based on a database query."""
    if not await database_is_ready(session):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok"},
    )
