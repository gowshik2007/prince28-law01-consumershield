"""Integration tests for parsing and storing documents."""

from pathlib import Path
from uuid import uuid4

import fitz
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from consumershield.config import Settings
from consumershield.db.models import Document, Page, ParseFailure
from consumershield.db.session import make_engine, make_sessionmaker
from consumershield.ingest.parse import ParseError, parse_file
from consumershield.ingest.store import (
    document_id,
    failed_paths,
    parsed_ids,
    save_document,
    save_failure,
)


@pytest.fixture
async def db_session(database_url: str):
    """Create a database session using the temporary integration database."""
    settings = Settings(
        app_env="ci",
        database_url=database_url,
        _env_file=None,
    )
    engine = make_engine(settings)

    try:
        async with make_sessionmaker(engine)() as session:
            yield session
    finally:
        await engine.dispose()


def make_pdf(path: Path) -> Path:
    """Create a PDF with enough text for the parser."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        (
            "ConsumerShield integration test document. "
            "This document contains enough text for the parser "
            "to extract and save the content successfully."
        ),
    )
    doc.save(path)
    doc.close()
    return path


@pytest.mark.asyncio
async def test_save_document(db_session: AsyncSession, tmp_path: Path) -> None:
    path = make_pdf(tmp_path / "integration.pdf")
    parsed = parse_file(path)

    record = {
        "path": f"test/{uuid4()}/integration.pdf",
        "sha256": "a" * 64,
        "url": "https://example.com/integration.pdf",
        "source": "integration-test",
        "licence": "Test licence",
        "title": "Integration Test Document",
    }

    await save_document(db_session, record, parsed)

    result = await db_session.scalar(
        select(Document).where(Document.external_id == document_id(record["sha256"]))
    )

    assert result is not None
    assert result.title == "Integration Test Document"
    assert result.doc_type == "pdf"
    assert result.sha256 == record["sha256"]

    pages = await db_session.scalars(select(Page).where(Page.document_id == result.id))
    saved_pages = list(pages)

    assert len(saved_pages) == 1
    assert "ConsumerShield integration test document" in saved_pages[0].text


@pytest.mark.asyncio
async def test_save_failure(db_session: AsyncSession) -> None:
    record = {
        "path": f"test/{uuid4()}/broken.pdf",
        "sha256": "b" * 64,
        "url": "https://example.com/broken.pdf",
        "source": "integration-test",
    }

    error = ParseError("no_text_layer", "PDF requires OCR")

    await save_failure(db_session, record, error)

    result = await db_session.scalar(
        select(ParseFailure).where(ParseFailure.path == record["path"])
    )

    assert result is not None
    assert result.reason == "no_text_layer"
    assert result.attempts == 1

    await save_failure(db_session, record, error)
    await db_session.refresh(result)

    assert result.attempts == 2


@pytest.mark.asyncio
async def test_parsed_ids_and_failed_paths(
    db_session: AsyncSession,
) -> None:
    record = {
        "path": f"test/{uuid4()}/failed.pdf",
        "sha256": "c" * 64,
        "url": "https://example.com/failed.pdf",
        "source": "integration-test",
    }

    error = ParseError("no_text_layer", "PDF requires OCR")

    await save_failure(db_session, record, error)

    ids = await parsed_ids(db_session)
    failures = await failed_paths(db_session)

    assert isinstance(ids, set)
    assert record["path"] in failures
