"""Create the async SQLAlchemy engine and session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from consumershield.config import get_settings
from consumershield.db.url import to_asyncpg_url


def make_engine(settings):
    """Create an async engine using the supplied settings."""
    return create_async_engine(
        to_asyncpg_url(settings.database_url),
        pool_pre_ping=True,
    )


def make_sessionmaker(engine):
    """Create an async session factory for the supplied engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


settings = get_settings()
engine = make_engine(settings)
SessionFactory = make_sessionmaker(engine)
