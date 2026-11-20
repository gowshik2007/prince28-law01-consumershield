import pytest
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from consumershield.api.deps import get_session


def test_health_is_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["git_sha"] == "dev"


def test_health_returns_custom_git_sha(client, settings):
    settings.git_sha = "test-commit-123"
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["git_sha"] == "test-commit-123"


def test_ready_when_database_available(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["checks"]["database"] is True


def test_ready_is_503_when_database_unavailable(client):
    class UnavailableSession:
        async def execute(self, statement):
            raise SQLAlchemyError("Database unavailable")

    async def unavailable_session():
        yield UnavailableSession()

    client.app.dependency_overrides[get_session] = unavailable_session

    r = client.get("/ready")
    assert r.status_code == 503
    assert r.json()["status"] == "not_ready"
    assert r.json()["checks"]["database"] is False


def test_list_documents_paginates(client):
    r = client.get("/v1/documents", params={"limit": 2})
    body = r.json()
    assert r.status_code == 200
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_search_filters_records(client):
    r = client.get("/v1/documents", params={"q": "beta"})
    assert [d["id"] for d in r.json()["items"]] == ["002"]


def test_get_document_found(client):
    r = client.get("/v1/documents/001")
    assert r.status_code == 200
    assert r.json()["title"] == "Alpha guideline"


def test_missing_document_is_problem_details(client):
    r = client.get("/v1/documents/999")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body["status"] == 404
    assert body["title"] == "Not Found"
    assert body["request_id"] == r.headers["X-Request-ID"]


def test_bad_limit_is_422_problem(client):
    r = client.get("/v1/documents", params={"limit": 0})
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "query.limit"


def test_invalid_filter_name_is_400(client):
    r = client.get("/v1/documents", params={"Bad-Name": "1"})
    assert r.status_code == 400


def test_request_id_is_echoed(client):
    r = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"


def test_app_refuses_to_start_without_app_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    from consumershield.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_list_documents_default_pagination(client):
    r = client.get("/v1/documents")
    body = r.json()

    assert r.status_code == 200
    assert body["total"] == 3
    assert body["limit"] == 20
    assert body["offset"] == 0


def test_list_documents_with_offset(client):
    r = client.get("/v1/documents", params={"limit": 1, "offset": 1})

    assert r.status_code == 200
    assert [item["id"] for item in r.json()["items"]] == ["002"]


def test_filter_documents_by_year(client):
    r = client.get("/v1/documents", params={"year": 2024})

    assert r.status_code == 200
    assert [item["id"] for item in r.json()["items"]] == ["002"]


def test_limit_above_maximum_is_422(client):
    r = client.get("/v1/documents", params={"limit": 101})

    assert r.status_code == 422


def test_search_query_too_long_is_422(client):
    r = client.get("/v1/documents", params={"q": "a" * 201})

    assert r.status_code == 422
