"""Tests for interrupted and resumed corpus downloads."""

import asyncio

import httpx

from consumershield.ingest.fetch import Source, fetch_all


class InterruptedStream(httpx.AsyncByteStream):
    """Send some bytes, then simulate a dropped connection."""

    async def __aiter__(self):
        yield b"first-part-of-the-document"
        raise httpx.ReadError("Simulated connection interruption")

    async def aclose(self):
        pass


def test_interrupted_download_resumes_with_range_request(tmp_path):
    async def run():
        document = b"first-part-of-the-document-second-part-of-the-document"
        prefix = b"first-part-of-the-document"
        requests = []

        async def no_sleep(_delay):
            pass

        async def handler(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nAllow: /\n",
                )

            requests.append(request)

            if len(requests) == 1:
                return httpx.Response(
                    200,
                    headers={"Content-Type": "application/pdf"},
                    stream=InterruptedStream(),
                )

            expected_range = f"bytes={len(prefix)}-"
            assert request.headers.get("Range") == expected_range

            return httpx.Response(
                206,
                content=document[len(prefix) :],
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Range": (f"bytes {len(prefix)}-{len(document) - 1}/{len(document)}"),
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
        ) as client:
            source = Source(
                "https://example.com/act.pdf",
                "test",
                "Test terms",
                "Test Act",
            )

            result = await fetch_all(
                [source],
                root=tmp_path,
                client=client,
                per_host_delay=0,
                max_attempts=2,
                sleep=no_sleep,
            )

        assert result["downloaded"] == 1
        assert result["failed"] == 0
        assert len(requests) == 2
        assert requests[1].headers["Range"] == f"bytes={len(prefix)}-"

        downloaded_files = list((tmp_path / "data" / "raw").rglob("*.pdf"))

        assert len(downloaded_files) == 1
        assert downloaded_files[0].read_bytes() == document

        partial_files = list((tmp_path / "data" / "raw").rglob("*.part"))
        assert partial_files == []

    asyncio.run(run())
