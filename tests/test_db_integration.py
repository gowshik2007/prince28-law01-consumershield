import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from consumershield.db.models import Document
from consumershield.db.repository import DocumentRepository
from consumershield.db.url import to_asyncpg_url


@pytest.fixture(scope="module")
def test_session_factory():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = create_async_engine(
        to_asyncpg_url(database_url),
        pool_pre_ping=True,
    )

    async def check_connection():
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    asyncio.run(check_connection())

    yield async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    asyncio.run(engine.dispose())


def test_repository_lists_documents(test_session_factory):
    external_id = f"integration-{uuid4().hex}"

    async def run():
        async with test_session_factory() as session, session.begin():
            session.add(
                Document(
                    external_id=external_id,
                    title="Integration test guideline",
                    doc_type="guideline",
                    sha256=uuid4().hex,
                    metadata_={"test_marker": "integration"},
                )
            )
            await session.flush()

            repository = DocumentRepository(session)
            total, items = await repository.list(
                q="Integration test guideline",
                filters={},
                limit=10,
                offset=0,
            )

            assert total >= 1
            assert any(item["id"] == external_id for item in items)

            await session.execute(delete(Document).where(Document.external_id == external_id))

    asyncio.run(run())


def test_repository_filters_json_metadata(test_session_factory):
    external_id = f"integration-{uuid4().hex}"

    async def run():
        async with test_session_factory() as session, session.begin():
            session.add(
                Document(
                    external_id=external_id,
                    title="Metadata filter test",
                    doc_type="guideline",
                    sha256=uuid4().hex,
                    metadata_={"test_marker": "filter-check"},
                )
            )
            await session.flush()

            repository = DocumentRepository(session)
            total, items = await repository.list(
                q=None,
                filters={"test_marker": "filter-check"},
                limit=10,
                offset=0,
            )

            assert total >= 1
            assert any(item["id"] == external_id for item in items)

            await session.execute(delete(Document).where(Document.external_id == external_id))

    asyncio.run(run())


def test_repository_gets_document_by_external_id(test_session_factory):
    external_id = f"integration-{uuid4().hex}"

    async def run():
        async with test_session_factory() as session, session.begin():
            session.add(
                Document(
                    external_id=external_id,
                    title="Document retrieval test",
                    doc_type="record",
                    sha256=uuid4().hex,
                    metadata_={},
                )
            )
            await session.flush()

            repository = DocumentRepository(session)
            document = await repository.get(external_id)

            assert document is not None
            assert document["id"] == external_id
            assert document["title"] == "Document retrieval test"

            await session.execute(delete(Document).where(Document.external_id == external_id))

    asyncio.run(run())
