"""Load JSON records into PostgreSQL using SHA-256 fingerprints.

New records are inserted, changed records are updated,
and unchanged records are skipped.
"""

import asyncio
import hashlib
import json
from datetime import date

from sqlalchemy import select, update

from consumershield.config import get_settings
from consumershield.db.models import Document
from consumershield.db.session import SessionFactory, engine

TITLE_FIELD = "case_no"

KNOWN = {
    "id",
    "title",
    "source_url",
    "licence",
    "doc_type",
    "published_on",
    "date",
}


def fingerprint(record: dict) -> str:
    """Create a stable SHA-256 fingerprint for a record."""
    canonical = json.dumps(
        record,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def to_row(record: dict) -> dict:
    """Convert a JSON record into database column values."""
    published = record.get("published_on") or record.get("date")

    return {
        "external_id": str(record["id"]),
        "title": str(record.get("title") or record.get(TITLE_FIELD) or record["id"]),
        "source_url": record.get("source_url"),
        "licence": record.get("licence"),
        "doc_type": record.get("doc_type") or "record",
        "published_on": date.fromisoformat(published) if published else None,
        "sha256": fingerprint(record),
        "metadata_": {key: value for key, value in record.items() if key not in KNOWN},
    }


async def main() -> None:
    settings = get_settings()
    records = json.loads(settings.data_file.read_text(encoding="utf-8"))

    inserted = updated = unchanged = 0

    try:
        async with SessionFactory() as session, session.begin():
            result = await session.execute(select(Document.external_id, Document.sha256))
            existing = dict(result.all())

            for record in records:
                row = to_row(record)
                old_hash = existing.get(row["external_id"])

                if old_hash is None:
                    session.add(Document(**row))
                    inserted += 1

                elif old_hash != row["sha256"]:
                    await session.execute(
                        update(Document)
                        .where(Document.external_id == row["external_id"])
                        .values(**row)
                    )
                    updated += 1

                else:
                    unchanged += 1

    finally:
        await engine.dispose()

    print(f"records={len(records)} inserted={inserted} updated={updated} unchanged={unchanged}")


if __name__ == "__main__":
    asyncio.run(main())
