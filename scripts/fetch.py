"""Command-line interface for the ConsumerShield corpus downloader."""

import argparse
import asyncio
import hashlib
import mimetypes
import time
from pathlib import Path

from consumershield.ingest.fetch import (
    Manifest,
    fetch_all,
    now_iso,
    read_sources,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the ConsumerShield source corpus.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    urls = subparsers.add_parser("urls", help="Download URLs from data/sources.csv")
    urls.add_argument("--delay", type=float, default=0.5)
    urls.add_argument("--max-concurrency", type=int, default=4)
    urls.add_argument("--max-attempts", type=int, default=4)

    manual = subparsers.add_parser("manual", help="Register a permitted manual download")
    manual.add_argument("file", type=Path)
    manual.add_argument("--from-url", required=True)
    manual.add_argument("--source", required=True)
    manual.add_argument("--licence", required=True)
    manual.add_argument("--title", default="")

    args = parser.parse_args()
    root = Path.cwd()

    if args.command == "manual":
        path = args.file.resolve()
        raw_dir = (root / "data" / "raw").resolve()

        if not path.is_file():
            parser.error(f"File not found: {path}")

        try:
            relative_path = path.relative_to(raw_dir).as_posix()
        except ValueError:
            parser.error("Manual downloads must be inside data/raw/")

        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)

        manifest = Manifest(root / "data" / "manifest.jsonl")
        if manifest.done(args.from_url, root):
            print("Already registered and downloaded; skipped.")
            return

        record = {
            "url": args.from_url,
            "source": args.source,
            "licence": args.licence,
            "title": args.title,
            "status": "downloaded",
            "attempts": 0,
            "fetched_at": now_iso(),
            "path": f"data/raw/{relative_path}",
            "bytes": path.stat().st_size,
            "sha256": digest.hexdigest(),
            "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "http_status": None,
        }
        manifest.add(record)
        print(f"[registered] {record['bytes']:,} bytes  {record['path']}")
        return

    sources = read_sources(root / "data" / "sources.csv")
    started = time.monotonic()

    def report(record: dict) -> None:
        status = record["status"]
        path = record.get("path", record.get("error", ""))
        size = record.get("bytes", 0)
        print(f"[{status:10}] {size:10,} bytes  {path}", flush=True)

    counts = asyncio.run(
        fetch_all(
            sources,
            root=root,
            max_concurrency=args.max_concurrency,
            per_host_delay=args.delay,
            max_attempts=args.max_attempts,
            on_result=report,
        )
    )

    elapsed = time.monotonic() - started
    print(
        f"sources={len(sources)} "
        f"downloaded={counts['downloaded']} "
        f"skipped={counts['skipped']} "
        f"blocked={counts['blocked']} "
        f"failed={counts['failed']} "
        f"seconds={elapsed:.1f}"
    )


if __name__ == "__main__":
    main()
