"""Liveness and readiness endpoints."""

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from consumershield.api.deps import SessionDep, SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    """Liveness: is the application process alive?"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "git_sha": settings.git_sha,
    }


@router.get("/ready")
async def ready(
    session: SessionDep,
    response: Response,
) -> dict:
    """Readiness: can this application connect to PostgreSQL?"""
    try:
        await session.execute(text("SELECT 1"))
        database_ok = True
    except (SQLAlchemyError, OSError):
        database_ok = False

    checks = {"database": database_ok}
    ok = all(checks.values())

    if not ok:
        response.status_code = 503

    return {
        "status": "ready" if ok else "not_ready",
        "checks": checks,
    }
