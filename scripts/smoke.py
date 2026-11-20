"""Smoke-test the production Consumershield API."""

import argparse
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def get_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        return json.loads(response.read())


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test Consumershield.")
    parser.add_argument("base_url", help="Base URL of the deployed API")
    parser.add_argument("--expect-version", help="Expected Git commit SHA")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    health_url = f"{base_url}/health"
    ready_url = f"{base_url}/ready"
    documents_url = f"{base_url}/v1/documents?limit=1"

    deadline = time.monotonic() + 300

    while True:
        try:
            health = get_json(health_url)
            actual_sha = health.get("git_sha")

            if args.expect_version and actual_sha != args.expect_version:
                print(
                    f"waiting: /health -> 200 (old SHA {actual_sha})",
                    flush=True,
                )
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Expected SHA {args.expect_version}, got {actual_sha}")
                time.sleep(5)
                continue

            print(f"ok   /health -> 200, git_sha {actual_sha}", flush=True)
            break

        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Health check failed: {exc}") from exc
            print(f"waiting: /health -> {exc}", flush=True)
            time.sleep(5)

    ready = get_json(ready_url)
    if ready.get("status") != "ready" or ready.get("checks", {}).get("database") is not True:
        raise RuntimeError(f"Database readiness check failed: {ready}")
    print(f"ok   /ready -> 200 {ready}", flush=True)

    documents = get_json(documents_url)
    if "items" not in documents or "total" not in documents:
        raise RuntimeError(f"Documents response is invalid: {documents}")
    print("ok   /v1/documents?limit=1 -> 200", flush=True)

    print("Smoke test passed", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        sys.exit(1)
