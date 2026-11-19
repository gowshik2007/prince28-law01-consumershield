"""App factory: build a fully wired FastAPI app from settings."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from consumershield.api.errors import register_error_handlers
from consumershield.api.middleware import request_context
from consumershield.api.routes import documents, health
from consumershield.config import Settings, get_settings
from consumershield.db.session import make_engine, make_sessionmaker
from consumershield.logging_setup import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    app_engine = make_engine(settings)
    app_session_factory = make_sessionmaker(app_engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await app_engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.session_factory = app_session_factory

    app.middleware("http")(request_context)
    register_error_handlers(app)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(documents.router)

    app.include_router(health.router)
    app.include_router(v1)

    return app
