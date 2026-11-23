"""Tests for the ConsumerShield corpus downloader."""

import asyncio
import json

import httpx
import pytest

from consumershield.ingest.fetch import (
    HostGate,
    Manifest,
    Robots,
    Source,
    backoff_delay,
    fetch_all,
    file_stem,
    pick_ext,
    read_sources,
    retry_after_seconds,
    slug,
)


def test_slug():
    assert slug("Consumer Protection Act 2019") == ("consumer-protection-act-2019")


def test_file_stem_is_stable():
    url = "https://example.com/act.pdf"
    assert file_stem(url) == file_stem(url)


def test_pick_ext():
    assert pick_ext("https://example.com/file", "application/pdf") == ".pdf"


def test_backoff_delay_is_bounded():
    for attempt in range(5):
        delay = backoff_delay(attempt)
        assert 0 <= delay <= min(60, 2**attempt)


def test_retry_after_seconds():
    assert retry_after_seconds("120") == 120.0
    assert retry_after_seconds(None) is None
    assert retry_after_seconds("invalid") is None


def test_read_sources(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        'url,source,licence,title\nhttps://example.com/a.pdf,test,"Public law",Example\n',
        encoding="utf-8",
    )

    sources = read_sources(path)

    assert len(sources) == 1
    assert sources[0].source == "test"
    assert sources[0].licence == "Public law"


def test_read_sources_rejects_missing_licence(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "url,source,licence,title\nhttps://example.com/a.pdf,test,,Example\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="licence"):
        read_sources(path)


def test_read_sources_rejects_invalid_url(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "url,source,licence,title\nftp://example.com/a.pdf,test,Public law,Example\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid URL"):
        read_sources(path)


def test_manifest_records_and_resume(tmp_path):
    manifest = Manifest(tmp_path / "data" / "manifest.jsonl")
    record = {
        "url": "https://example.com/a.pdf",
        "status": "downloaded",
        "path": "data/raw/test/a.pdf",
    }

    target = tmp_path / record["path"]
    target.parent.mkdir(parents=True)
    target.write_bytes(b"test")

    manifest.add(record)

    reloaded = Manifest(tmp_path / "data" / "manifest.jsonl")
    assert reloaded.done(record["url"], tmp_path)


def test_manifest_missing_file_is_not_done(tmp_path):
    path = tmp_path / "data" / "manifest.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "url": "https://example.com/a.pdf",
                "status": "downloaded",
                "path": "data/raw/missing.pdf",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = Manifest(path)
    assert not manifest.done("https://example.com/a.pdf", tmp_path)


def test_retry_after_date():
    result = retry_after_seconds("Wed, 21 Oct 2099 07:28:00 GMT")
    assert result is not None
    assert result > 0


def test_host_gate_initializes():
    async def run():
        gate = HostGate(0, asyncio.sleep)
        await gate.wait("example.com")

    asyncio.run(run())


def test_robots_allows_and_blocks():
    async def run():
        async def handler(request):
            return httpx.Response(
                200,
                text="User-agent: *\nDisallow: /private\nAllow: /\n",
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            robots = Robots(client)

            allowed, _ = await robots.check("https://example.com/public")
            blocked, _ = await robots.check("https://example.com/private")

            assert allowed
            assert not blocked

    asyncio.run(run())


def test_fetch_all_downloads_and_resumes(tmp_path):
    async def run():
        requests = []

        async def handler(request):
            requests.append(request.url.path)

            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nAllow: /\n",
                )

            return httpx.Response(
                200,
                content=b"sample consumer law document",
                headers={"Content-Type": "application/pdf"},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = Source(
                "https://example.com/act.pdf",
                "test",
                "Test terms",
                "Test Act",
            )

            first = await fetch_all(
                [source],
                root=tmp_path,
                client=client,
                per_host_delay=0,
            )

            assert first["downloaded"] == 1
            assert first["skipped"] == 0

            second = await fetch_all(
                [source],
                root=tmp_path,
                client=client,
                per_host_delay=0,
            )

            assert second["downloaded"] == 0
            assert second["skipped"] == 1

            raw_files = list((tmp_path / "data" / "raw").rglob("*"))
            assert any(path.is_file() for path in raw_files)
            assert not any(path.name.endswith(".part") for path in raw_files)

    asyncio.run(run())


def test_fetch_all_respects_robots_block(tmp_path):
    async def run():
        async def handler(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nDisallow: /\n",
                )
            pytest.fail("Blocked URL must never be requested")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = Source(
                "https://example.com/blocked.pdf",
                "test",
                "Test terms",
            )

            result = await fetch_all(
                [source],
                root=tmp_path,
                client=client,
                per_host_delay=0,
            )

            assert result["blocked"] == 1
            assert result["downloaded"] == 0

    asyncio.run(run())


def test_fetch_all_does_not_retry_404(tmp_path):
    async def run():
        attempts = 0

        async def handler(request):
            nonlocal attempts

            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nAllow: /\n",
                )

            attempts += 1
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = Source(
                "https://example.com/missing.pdf",
                "test",
                "Test terms",
            )

            result = await fetch_all(
                [source],
                root=tmp_path,
                client=client,
                per_host_delay=0,
                max_attempts=3,
            )

            assert result["failed"] == 1
            assert attempts == 1

    asyncio.run(run())
