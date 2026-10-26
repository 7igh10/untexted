from typing import Annotated

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import database_is_ready, get_db_session, lifespan

app = FastAPI(title="Untexted API", lifespan=lifespan)


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
