from fastapi.testclient import TestClient

from consumershield.api.deps import get_ingest_repo, get_manifest
from consumershield.api.main import create_app
from consumershield.config import Settings

TOKEN = {"X-Admin-Token": "test-token"}


def test_start_queues_new_items(client, queue, ingest_repo):
    response = client.post("/v1/ingest", json={}, headers=TOKEN)

    assert response.status_code == 202
    assert response.json() == {
        "job_id": "job1",
        "queued": 2,
        "status_url": "/v1/ingest/job1",
    }
    assert queue.items == [1, 2]
    assert [r["url"] for r in ingest_repo.jobs["job1"]] == [
        "https://x.test/1.pdf",
        "https://x.test/2.pdf",
    ]


def test_admin_token_is_required(client, queue):
    missing = client.post("/v1/ingest", json={})
    wrong = client.post(
        "/v1/ingest",
        json={},
        headers={"X-Admin-Token": "wrong"},
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.headers["content-type"].startswith("application/problem+json")
    assert queue.items == []


def test_production_requires_configured_admin_token():
    settings = Settings(
        app_env="production",
        database_url="postgresql://localhost:5432/unused",
        admin_token="",
        _env_file=None,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post("/v1/ingest", json={})

    assert response.status_code == 403


def test_nothing_new_returns_200(client, queue, ingest_repo):
    ingest_repo.known |= {"f-" + "1" * 20, "f-" + "2" * 20}

    response = client.post("/v1/ingest", json={}, headers=TOKEN)

    assert response.status_code == 200
    assert response.json()["queued"] == 0
    assert queue.items == []


def test_limit_and_source_filters(client):
    limited = client.post(
        "/v1/ingest",
        json={"limit": 1},
        headers=TOKEN,
    )
    assert limited.status_code == 202
    assert limited.json()["queued"] == 1

    other_source = client.post(
        "/v1/ingest",
        json={"source": "somewhere-else"},
        headers=TOKEN,
    )
    assert other_source.status_code == 200
    assert other_source.json()["queued"] == 0

    invalid_limit = client.post(
        "/v1/ingest",
        json={"limit": 0},
        headers=TOKEN,
    )
    assert invalid_limit.status_code == 422


def test_retry_failed_items(client, queue):
    response = client.post(
        "/v1/ingest",
        json={"retry_failed": True},
        headers=TOKEN,
    )

    assert response.status_code == 202
    assert response.json()["queued"] == 1
    assert queue.items == [1]


def test_progress_is_public(client):
    started = client.post("/v1/ingest", json={}, headers=TOKEN)
    job_id = started.json()["job_id"]

    response = client.get(f"/v1/ingest/{job_id}")

    assert response.status_code == 200
    assert response.json()["counts"]["queued"] == 2

    missing = client.get("/v1/ingest/not-a-job")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/problem+json")


def test_dead_letter_list(client):
    response = client.get("/v1/ingest/dead-letter")

    assert response.status_code == 200
    assert response.json() == {
        "count": 1,
        "items": [
            {
                "item": 7,
                "job_id": "old",
                "url": "https://x.test/bad.pdf",
                "path": "data/raw/x/bad.pdf",
                "attempts": 3,
                "error": "parse: corrupt",
            }
        ],
    }


def test_redis_unavailable_does_not_break_health():
    settings = Settings(
        app_env="ci",
        database_url="postgresql://localhost:5432/unused",
        redis_url="redis://127.0.0.1:1",
        admin_token="test-token",
        _env_file=None,
    )
    app = create_app(settings)

    # Redis should fail before the route needs either dependency.
    app.dependency_overrides[get_ingest_repo] = lambda: None
    app.dependency_overrides[get_manifest] = lambda: []

    with TestClient(app) as client:
        response = client.post("/v1/ingest", json={}, headers=TOKEN)
        health = client.get("/health")

    assert response.status_code == 503
    assert "Redis" in response.json()["detail"]
    assert health.status_code == 200
