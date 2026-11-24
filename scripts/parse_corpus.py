"""Build and parse the complete Open India Law corpus from Parquet."""

import argparse
import asyncio
import hashlib
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from consumershield.db.session import SessionFactory, engine
from consumershield.ingest.parse import ParseError, parse_file
from consumershield.ingest.store import (
    failed_paths,
    parsed_ids,
    save_document,
    save_failure,
)

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data/raw/in_central_legislation.parquet"
OUTPUT = ROOT / "data/raw/open-india-law/acts"
MANIFEST = ROOT / "data/manifest.jsonl"

DATASET_URL = "https://oss-data-in.vaquill.ai/v2026.08.1/in_central_legislation.parquet"


def slugify(value: str) -> str:
    """Create a safe filename."""
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower())
    return value.strip("-")[:80] or "act"


def build_documents(limit: int | None = None) -> list[dict]:
    """Create one Markdown file for each selected Act."""
    if not PARQUET.exists():
        raise FileNotFoundError(f"Parquet dataset not found: {PARQUET}")

    columns = [
        "act_id",
        "chunk_id",
        "title",
        "chapter",
        "section_number",
        "section_title",
        "text",
        "source_url",
        "year",
        "jurisdiction",
        "act_status",
        "language_code",
    ]

    print("Reading Parquet dataset...")
    table = pq.read_table(PARQUET, columns=columns)
    records = table.to_pylist()

    grouped = defaultdict(list)

    for row in records:
        grouped[row["act_id"]].append(row)

    selected = sorted(
        grouped.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    )

    if limit is not None:
        selected = selected[:limit]

    OUTPUT.mkdir(parents=True, exist_ok=True)

    manifest_records = []

    print(f"Generating Markdown files for {len(selected)} Acts...")

    for index, (act_id, rows) in enumerate(selected, start=1):
        title = rows[0]["title"]
        filename = f"{slugify(act_id)}-{slugify(title)}.md"
        path = OUTPUT / filename

        rows.sort(
            key=lambda row: (
                str(row.get("chapter") or ""),
                str(row.get("section_number") or ""),
                str(row.get("chunk_id") or ""),
            )
        )

        sections = [
            f"# {title}",
            "",
            f"Act ID: {act_id}",
            f"Jurisdiction: {rows[0].get('jurisdiction') or 'India'}",
            f"Status: {rows[0].get('act_status') or 'Unknown'}",
            f"Year: {rows[0].get('year') or 'Unknown'}",
            f"Source: {rows[0].get('source_url') or DATASET_URL}",
            "",
        ]

        for row in rows:
            number = row.get("section_number") or "Unnumbered"
            section_title = row.get("section_title") or ""
            section_text = row.get("text") or ""

            sections.extend(
                [
                    f"## Section {number}: {section_title}",
                    "",
                    section_text,
                    "",
                ]
            )

        content = "\n".join(sections).strip() + "\n"
        path.write_text(content, encoding="utf-8")

        digest = hashlib.sha256(path.read_bytes()).hexdigest()

        manifest_records.append(
            {
                "url": rows[0].get("source_url") or DATASET_URL,
                "source": "Open India Law",
                "licence": "CC BY 4.0",
                "title": title,
                "via": "parquet-extract",
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": digest,
                "content_type": "text/markdown",
                "status": "downloaded",
                "act_id": act_id,
                "sections": len(rows),
            }
        )

        if index % 50 == 0:
            print(f"Generated {index}/{len(selected)} files")

    existing = []

    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.append(json.loads(line))

    generated_paths = {record["path"] for record in manifest_records}

    existing = [record for record in existing if record.get("path") not in generated_paths]

    all_records = existing + manifest_records

    MANIFEST.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in all_records),
        encoding="utf-8",
    )

    return manifest_records


async def parse_records(
    records: list[dict],
    retry_failed: bool = False,
) -> dict:
    """Parse files, skip completed files, and optionally retry failures."""
    parsed_count = 0
    failed_count = 0
    already_parsed_count = 0
    failed_before_count = 0
    page_count = 0

    async with SessionFactory() as session:
        existing_ids = await parsed_ids(session)
        existing_failures = await failed_paths(session)

        for index, record in enumerate(records, start=1):
            path = ROOT / record["path"]
            document_id = f"f-{record['sha256'][:20]}"

            if document_id in existing_ids:
                already_parsed_count += 1

            elif record["path"] in existing_failures and not retry_failed:
                failed_before_count += 1

            else:
                try:
                    parsed = parse_file(path)

                    await save_document(session, record, parsed)

                    existing_ids.add(document_id)
                    parsed_count += 1
                    page_count += len(parsed.pages)

                    print(f"PARSED: {record['title']} | pages={len(parsed.pages)}")

                except ParseError as error:
                    await save_failure(session, record, error)
                    failed_count += 1

                    print(f"FAILED: {record['title']} | {error.reason}: {error.detail}")

            if index % 50 == 0:
                print(
                    f"Progress: {index}/{len(records)} "
                    f"| parsed={parsed_count} "
                    f"| already_parsed={already_parsed_count} "
                    f"| failed_before={failed_before_count} "
                    f"| failed={failed_count}"
                )

    return {
        "files": len(records),
        "parsed": parsed_count,
        "already_parsed": already_parsed_count,
        "failed_before": failed_before_count,
        "failed": failed_count,
        "pages": page_count,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Build and parse the Open India Law corpus.")

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of Acts to process.",
    )

    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry files previously recorded as failures.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    start = time.perf_counter()

    try:
        print("Building documents from Parquet...")
        records = build_documents(args.limit)

        print(f"Generated documents: {len(records)}")
        print("Parsing and saving to PostgreSQL...")

        summary = await parse_records(
            records,
            retry_failed=args.retry_failed,
        )

        elapsed = time.perf_counter() - start

        print("\n--- PARSE SUMMARY ---")

        for key, value in summary.items():
            print(f"{key}={value}")

        print(f"seconds={elapsed:.1f}")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
