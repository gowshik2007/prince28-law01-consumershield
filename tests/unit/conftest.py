import pytest
from fastapi.testclient import TestClient

from consumershield.api.deps import (
    get_document_repository,
    get_gateway,
    get_session,
    get_usage_repo,
)
from consumershield.api.main import create_app
from consumershield.config import Settings
from consumershield.llm.gateway import FakeLLM, LLMGateway

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


class FakeUsage:
    async def by_day(self, days=30):
        return [
            {
                "day": "2026-11-25",
                "calls": 3,
                "tokens_in": 300,
                "tokens_out": 150,
                "cost_inr": 0.0642,
            }
        ]


@pytest.fixture
def settings():
    return Settings(
        app_env="ci",
        database_url="postgresql://localhost:5432/unused",
        _env_file=None,
    )


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def client(settings, llm):
    app = create_app(settings)
    gateway = LLMGateway([llm], max_attempts=1)

    async def fake_session():
        yield FakeSession()

    def fake_repository():
        return FakeRepository()

    def fake_gateway():
        return gateway

    def fake_usage():
        return FakeUsage()

    app.dependency_overrides[get_session] = fake_session
    app.dependency_overrides[get_document_repository] = fake_repository
    app.dependency_overrides[get_gateway] = fake_gateway
    app.dependency_overrides[get_usage_repo] = fake_usage

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
