"""The worker process:  uv run arq consumershield.workers.main.WorkerSettings

It runs the same code as the API, with the same settings and the same database. The only
difference is where its work comes from: Redis instead of HTTP.
"""

import asyncio
import logging

from arq.worker import Worker

from consumershield.config import Settings, get_settings
from consumershield.db.ingest_jobs import IngestRepository
from consumershield.db.llm_calls import make_recorder
from consumershield.db.session import make_engine, make_sessionmaker
from consumershield.ingest.fetch import make_client
from consumershield.llm.doc_meta import DocMeta
from consumershield.llm.gateway import build_gateway
from consumershield.llm.prompts import latest, read_prompt
from consumershield.logging_setup import setup_logging
from consumershield.workers.ingest import Pace, ingest_document
from consumershield.workers.queue import Queue, redis_settings

logger = logging.getLogger("consumershield.worker")


async def startup(ctx: dict) -> None:
    settings: Settings = ctx["settings"]
    if not ctx.get("embedded"):
        setup_logging(settings.log_level)
        logging.getLogger("arq").handlers.clear()
    logging.getLogger("httpx").setLevel(logging.WARNING)

    engine = make_engine(settings)
    ctx["engine"], ctx["sessionmaker"] = engine, make_sessionmaker(engine)
    ctx["gateway"] = build_gateway(settings, make_recorder(ctx["sessionmaker"]))
    ctx["http"] = make_client(2)
    ctx["pace"] = Pace(settings.ingest_rpm)
    ctx["extract"] = None

    if ctx["gateway"].providers:
        try:
            version = latest(settings.prompts_dir, "extract")
        except FileNotFoundError:
            logger.warning("no prompts/extract_v*.md: documents are parsed, not extracted")
        else:
            prompt = read_prompt(settings.prompts_dir, version)
            ctx["extract"] = {
                "schema": DocMeta,
                "prompt": prompt,
                "version": version,
                "chars": 6000,
            }

    async with ctx["sessionmaker"]() as session:
        lost = await Queue(ctx["redis"]).put(await IngestRepository(session).open_item_ids())
    logger.info("worker ready, %s unfinished item(s) put back in the queue", lost)


async def shutdown(ctx: dict) -> None:
    await ctx["http"].aclose()
    await ctx["engine"].dispose()


def worker_options(settings: Settings, *, embedded: bool = False) -> dict:
    return {
        "functions": [ingest_document],
        "on_startup": startup,
        "on_shutdown": shutdown,
        "redis_settings": redis_settings(settings.redis_url),
        "ctx": {"settings": settings, "embedded": embedded},
        "max_jobs": settings.ingest_concurrency,
        "job_timeout": settings.ingest_job_timeout,
        "max_tries": settings.ingest_max_tries,
        "keep_result": 0,
        "poll_delay": 1.0,
    }


async def run_embedded(settings: Settings) -> None:
    """A worker inside the API process, for hosts that offer no free worker service."""
    worker = Worker(**worker_options(settings, embedded=True), handle_signals=False)
    try:
        await worker.async_run()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("the embedded worker stopped: is REDIS_URL right?")
    finally:
        await worker.close()


WorkerSettings = worker_options(get_settings())
