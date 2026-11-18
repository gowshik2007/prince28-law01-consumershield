import pytest
from fastapi.testclient import TestClient

from consumershield.api.deps import get_document_repository, get_session
from consumershield.api.main import create_app
from consumershield.config import Settings

SAMPLE = [
    {"id": "001", "title": "Alpha guideline", "year": 2023},
    {"id": "002", "title": "Beta circular", "year": 2024},
    {"id": "003", "title": "Gamma notice", "year": 2025},
]


class FakeSession:
    async def execute(self, statement):
        return 1


class FakeRepository:
    async def list(self, *, q, filters, limit, offset):
        records = SAMPLE

        if q:
            records = [record for record in records if q.lower() in str(record).lower()]

        for key, value in filters.items():
            records = [record for record in records if str(record.get(key)) == value]

        total = len(records)
        return total, records[offset : offset + limit]

    async def get(self, external_id):
        return next(
            (record for record in SAMPLE if record["id"] == external_id),
            None,
        )


@pytest.fixture
def client():
    settings = Settings(app_env="ci")
    app = create_app(settings)

    async def fake_session():
        yield FakeSession()

    def fake_repository():
        return FakeRepository()

    app.dependency_overrides[get_session] = fake_session
    app.dependency_overrides[get_document_repository] = fake_repository

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
