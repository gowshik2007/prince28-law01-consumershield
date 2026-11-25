import asyncio

from sqlalchemy import inspect

from consumershield.db.session import engine


async def main():
    async with engine.connect() as conn:
        exists = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("llm_calls"))

        columns = await conn.run_sync(
            lambda sync_conn: [
                column["name"] for column in inspect(sync_conn).get_columns("llm_calls")
            ]
        )

        print("llm_calls exists:", exists)
        print("Columns:", columns)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
