"""Check that ConsumerShield can connect to Neon PostgreSQL."""

import asyncio

from sqlalchemy import text

from consumershield.db.session import engine


async def main() -> None:
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT current_database(), version()"))
            database, version = result.one()

            print(f"Connected to database '{database}' {version}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
