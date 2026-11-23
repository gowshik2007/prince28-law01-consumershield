"""Polite, resumable downloader for the ConsumerShield corpus."""

import asyncio
import csv
import hashlib
import json
import random
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

import httpx
from protego import Protego

CONTACT = "https://github.com/gowshik2007/prince28-law01-consumershield"
ROBOTS_TOKEN = "examate-student-bot"
USER_AGENT = f"{ROBOTS_TOKEN}/0.1 (student project; +{CONTACT})"

RETRYABLE = {408, 425, 429, 500, 502, 503, 504}
MAX_WAIT = 120.0
MAX_BYTES = 200 * 1024 * 1024
ATTEMPT_TIMEOUT = 300.0

KNOWN_EXT = {
    ".pdf",
    ".html",
    ".htm",
    ".json",
    ".txt",
    ".md",
    ".mdx",
    ".rst",
    ".adoc",
    ".csv",
    ".xml",
    ".yaml",
    ".yml",
    ".zip",
    ".docx",
    ".xlsx",
    ".xls",
}

EXT_BY_TYPE = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "application/json": ".json",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/xml": ".xml",
    "text/xml": ".xml",
    "application/zip": ".zip",
    "application/yaml": ".yaml",
}

Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class Source:
    url: str
    source: str
    licence: str
    title: str = ""


class DownloadError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        retry_after: float | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class RobotsBlocked(DownloadError):
    pass


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def slug(text: str, limit: int = 60) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit] or "file"


def file_stem(url: str) -> str:
    parts = urlsplit(url)
    last = unquote(parts.path.rstrip("/").rsplit("/", 1)[-1]) or parts.netloc
    name = last.rsplit(".", 1)[0] if "." in last else last
    digest = hashlib.sha256(url.encode()).hexdigest()[:8]
    return f"{slug(name)}-{digest}"


def pick_ext(url: str, content_type: str) -> str:
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix in KNOWN_EXT:
        return suffix
    return EXT_BY_TYPE.get(content_type.split(";")[0].strip().lower(), ".bin")


def backoff_delay(
    attempt: int,
    *,
    base: float = 1.0,
    cap: float = 60.0,
) -> float:
    return random.uniform(0, min(cap, base * 2**attempt))


def retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def read_sources(path: Path) -> list[Source]:
    sources = []
    seen = set()

    with path.open(encoding="utf-8-sig", newline="") as handle:
        lines = (line for line in handle if line.strip() and not line.lstrip().startswith("#"))
        for number, row in enumerate(csv.DictReader(lines), start=1):
            url = (row.get("url") or "").strip()
            name = (row.get("source") or "").strip()
            licence = (row.get("licence") or "").strip()

            parts = urlsplit(url)
            if parts.scheme not in {"http", "https"} or not parts.netloc:
                raise ValueError(f"Invalid URL in sources row {number}: {url!r}")
            if not name or not licence:
                raise ValueError(f"sources row {number}: source and licence are required")

            if url not in seen:
                seen.add(url)
                sources.append(
                    Source(
                        url,
                        name,
                        licence,
                        (row.get("title") or "").strip(),
                    )
                )

    return sources


class Manifest:
    def __init__(self, path: Path):
        self.path = path
        self.records = {}

        if path.exists():
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                try:
                    record = json.loads(line)
                    self.records[record["url"]] = record
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

            if content and not content.endswith("\n"):
                with path.open("a", encoding="utf-8") as handle:
                    handle.write("\n")

    def done(self, url: str, root: Path) -> bool:
        record = self.records.get(url)
        if not record or record.get("status") != "downloaded":
            return False
        return (root / record["path"]).is_file()

    def add(self, record: dict) -> None:
        self.records[record["url"]] = record
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


class Robots:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.rules = {}
        self.locks = {}

    async def _load(self, origin: str):
        try:
            response = await self.client.get(origin + "/robots.txt", follow_redirects=False)
        except httpx.HTTPError:
            return None

        if 300 <= response.status_code < 400:
            return None
        if response.status_code == 429 or response.status_code >= 500:
            return None
        if response.status_code == 404:
            return Protego.parse("")
        if response.status_code >= 400:
            return None

        return Protego.parse(response.text)

    async def check(self, url: str) -> tuple[bool, float]:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"

        async with self.locks.setdefault(origin, asyncio.Lock()):
            if origin not in self.rules:
                self.rules[origin] = await self._load(origin)

        rules = self.rules[origin]
        if rules is None:
            return False, 0.0

        return (
            rules.can_fetch(url, ROBOTS_TOKEN),
            float(rules.crawl_delay(ROBOTS_TOKEN) or 0.0),
        )


class HostGate:
    def __init__(self, delay: float, sleep: Sleep):
        self.delay = delay
        self.sleep = sleep
        self.next_ok = {}
        self.locks = {}

    async def wait(self, host: str, crawl_delay: float = 0.0):
        async with self.locks.setdefault(host, asyncio.Lock()):
            pause = self.next_ok.get(host, 0.0) - time.monotonic()
            if pause > 0:
                await self.sleep(pause)
            self.next_ok[host] = time.monotonic() + max(self.delay, crawl_delay)


def make_client(max_concurrency: int = 4) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(max_connections=max_concurrency),
        follow_redirects=False,
    )


async def _download(
    client: httpx.AsyncClient,
    src: Source,
    root: Path,
    raw_dir: Path,
    robots: Robots,
    gate: HostGate,
) -> dict:
    current_url = src.url
    visited = set()

    for _ in range(11):
        if current_url in visited:
            raise DownloadError("Redirect loop detected")
        visited.add(current_url)

        parts = urlsplit(current_url)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise DownloadError("Redirect destination is not a valid HTTP(S) URL")

        allowed, crawl_delay = await robots.check(current_url)
        if not allowed:
            raise RobotsBlocked("Redirect destination blocked by robots.txt or robots unavailable")

        await gate.wait(parts.netloc, crawl_delay)

        async with client.stream(
            "GET",
            current_url,
            follow_redirects=False,
        ) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                if not location:
                    raise DownloadError("Redirect response has no Location header")
                current_url = urljoin(current_url, location)
                continue

            if response.status_code != 200:
                raise DownloadError(
                    f"HTTP {response.status_code}",
                    code=response.status_code,
                    retry_after=retry_after_seconds(response.headers.get("Retry-After")),
                )

            content_type = response.headers.get("Content-Type", "")
            name = file_stem(src.url) + pick_ext(src.url, content_type)
            target = raw_dir / slug(src.source) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            part = target.with_name(name + ".part")

            digest = hashlib.sha256()
            size = 0

            try:
                with part.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise DownloadError(f"File exceeds {MAX_BYTES // 2**20} MB")
                        digest.update(chunk)
                        handle.write(chunk)

                part.replace(target)
            finally:
                part.unlink(missing_ok=True)

        return {
            "path": target.relative_to(root).as_posix(),
            "bytes": size,
            "sha256": digest.hexdigest(),
            "content_type": content_type.split(";")[0].strip(),
            "http_status": 200,
        }

    raise DownloadError("Too many redirects")


async def fetch_one(
    client: httpx.AsyncClient,
    src: Source,
    *,
    root: Path,
    raw_dir: Path,
    robots: Robots,
    gate: HostGate,
    slots: asyncio.Semaphore,
    max_attempts: int,
    sleep: Sleep,
) -> dict:
    record = {
        "url": src.url,
        "source": src.source,
        "licence": src.licence,
        "title": src.title,
        "via": "http",
    }

    error = ""
    code = None

    for attempt in range(1, max_attempts + 1):
        wait = backoff_delay(attempt - 1)

        async with slots:
            try:
                async with asyncio.timeout(ATTEMPT_TIMEOUT):
                    fields = await _download(client, src, root, raw_dir, robots, gate)

                return (
                    record
                    | fields
                    | {
                        "status": "downloaded",
                        "attempts": attempt,
                        "fetched_at": now_iso(),
                    }
                )

            except RobotsBlocked as exc:
                return record | {
                    "status": "blocked",
                    "error": str(exc),
                    "fetched_at": now_iso(),
                }

            except DownloadError as exc:
                error, code = str(exc), exc.code
                if code not in RETRYABLE:
                    break
                if exc.retry_after is not None:
                    if exc.retry_after > MAX_WAIT:
                        error = f"{error}: retry later"
                        break
                    wait = max(wait, exc.retry_after)

            except (httpx.TransportError, TimeoutError) as exc:
                error, code = type(exc).__name__, None

            except httpx.HTTPError as exc:
                error, code = type(exc).__name__, None
                break

        if attempt < max_attempts:
            await sleep(min(wait, MAX_WAIT))

    return record | {
        "status": "failed",
        "http_status": code,
        "error": error,
        "attempts": attempt,
        "fetched_at": now_iso(),
    }


async def fetch_all(
    sources: list[Source],
    *,
    root: Path = Path("."),
    max_concurrency: int = 4,
    per_host_delay: float = 0.5,
    max_attempts: int = 4,
    client: httpx.AsyncClient | None = None,
    sleep: Sleep = asyncio.sleep,
    on_result: Callable[[dict], None] | None = None,
) -> dict[str, int]:
    if max_concurrency < 1 or max_attempts < 1:
        raise ValueError("Concurrency and attempts must be at least 1")

    raw_dir = root / "data" / "raw"
    manifest = Manifest(root / "data" / "manifest.jsonl")
    todo = [src for src in sources if not manifest.done(src.url, root)]

    counts = {
        "downloaded": 0,
        "skipped": len(sources) - len(todo),
        "blocked": 0,
        "failed": 0,
    }

    own_client = client is None
    active_client = client or make_client(max_concurrency)
    robots = Robots(active_client)
    gate = HostGate(per_host_delay, sleep)
    slots = asyncio.Semaphore(max_concurrency)

    try:
        tasks = [
            asyncio.create_task(
                fetch_one(
                    active_client,
                    src,
                    root=root,
                    raw_dir=raw_dir,
                    robots=robots,
                    gate=gate,
                    slots=slots,
                    max_attempts=max_attempts,
                    sleep=sleep,
                )
            )
            for src in todo
        ]

        for finished in asyncio.as_completed(tasks):
            record = await finished
            counts[record["status"]] += 1

            before = manifest.records.get(record["url"], {})
            same_problem = (
                before.get("status"),
                before.get("error"),
            ) == (
                record["status"],
                record.get("error"),
            )

            if record["status"] == "downloaded" or not same_problem:
                manifest.add(record)

            if on_result:
                on_result(record)

    finally:
        if own_client:
            await active_client.aclose()

    return counts
