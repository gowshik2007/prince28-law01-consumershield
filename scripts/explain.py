"""Show how PostgreSQL executes a JSONB metadata filter.

Run:
    python -m uv run python scripts/explain.py product_category "E-commerce goods and services"
"""

import asyncio
import json
import sys

from sqlalchemy import text

from consumershield.db.session import engine

SQL = """
EXPLAIN ANALYZE
SELECT id, title
FROM documents
WHERE metadata @> CAST(:f AS jsonb)
"""


async def main(field: str, value: str) -> None:
    params = {"f": json.dumps({field: value})}

    try:
        async with engine.connect() as connection:
            print("-- 1) What the planner chooses on its own:")
            result = await connection.execute(text(SQL), params)

            for line in result.scalars():
                print(line)

            await connection.execute(text("SET enable_seqscan = off"))

            print("\n-- 2) Seq scan switched off, to prove the index can be used:")
            result = await connection.execute(text(SQL), params)

            for line in result.scalars():
                print(line)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python -m uv run python scripts/explain.py <field> <value>")

    asyncio.run(main(sys.argv[1], sys.argv[2]))
