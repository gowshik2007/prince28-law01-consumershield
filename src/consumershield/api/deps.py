"""Dependencies: endpoints ask for these instead of building them."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from consumershield.config import Settings
from consumershield.db.repository import DocumentRepository
from consumershield.db.session import SessionFactory


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide one database session per request."""
    async with SessionFactory() as session:
        yield session


def get_document_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentRepository:
    return DocumentRepository(session)


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DocumentRepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]

SessionDep = Annotated[AsyncSession, Depends(get_session)]
