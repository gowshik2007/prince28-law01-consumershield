"""Queue ingestion through the API and watch the worker.

Examples:
    uv run python scripts/ingest.py --limit 20
    uv run python scripts/ingest.py --limit 20 --url https://your-app.onrender.com
    uv run python scripts/ingest.py --retry-failed
    uv run python scripts/ingest.py --watch JOB_ID
"""

import argparse
import sys
import time

import httpx

from consumershield.config import get_settings


def show(progress: dict) -> str:
    counts = progress["counts"]
    parts = " ".join(f"{key}={value}" for key, value in counts.items())
    return f"{progress['status']:<9} {parts}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Queue and watch ConsumerShield ingestion.")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--source", default="")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--watch", metavar="JOB_ID")
    args = parser.parse_args()

    settings = get_settings()
    headers = {}
    if settings.admin_token:
        headers["X-Admin-Token"] = settings.admin_token

    with httpx.Client(base_url=args.url.rstrip("/"), headers=headers, timeout=30) as client:
        if args.watch:
            job_id = args.watch
        else:
            response = client.post(
                "/v1/ingest",
                json={
                    "limit": args.limit,
                    "source": args.source,
                    "retry_failed": args.retry_failed,
                },
            )
            if response.status_code not in (200, 202):
                print(f"Could not queue ingestion: {response.status_code} {response.text}")
                return 1

            result = response.json()
            if not result.get("job_id"):
                print(result.get("detail", "Nothing to do."))
                return 0

            job_id = result["job_id"]
            print(f"Queued {result['queued']} items. Job: {job_id}")

        last = None
        while True:
            response = client.get(f"/v1/ingest/{job_id}")
            if response.status_code != 200:
                print(f"Could not read job: {response.status_code} {response.text}")
                return 1

            progress = response.json()
            line = show(progress)
            if line != last:
                print(line)
                last = line

            if progress["status"] in {"finished", "failed"}:
                return 0 if progress["status"] == "finished" else 1

            time.sleep(2)


if __name__ == "__main__":
    sys.exit(main())
