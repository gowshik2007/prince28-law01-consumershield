"""Command-line interface for the ConsumerShield corpus downloader."""

import argparse
import asyncio
import time
from pathlib import Path

from consumershield.ingest.fetch import fetch_all, read_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the ConsumerShield source corpus.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    urls = subparsers.add_parser("urls", help="Download URLs from data/sources.csv")
    urls.add_argument("--delay", type=float, default=0.5)
    urls.add_argument("--max-concurrency", type=int, default=4)
    urls.add_argument("--max-attempts", type=int, default=4)

    args = parser.parse_args()
    root = Path.cwd()

    if args.command == "urls":
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
