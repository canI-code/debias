"""Daily retention scheduler for compliance-grade data lifecycle control."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import structlog
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError

from backend.config import get_settings
from backend.database import get_session_maker, init_db
from backend.models import ChatLog, ScoredLog

settings = get_settings()
logger = structlog.get_logger(__name__)


async def purge_expired_logs() -> dict[str, int]:
    """Delete records older than retention policy; safe to run multiple times daily."""

    cutoff = datetime.now(UTC) - timedelta(days=settings.RETENTION_DAYS)
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            stale_log_ids = list(
                (
                    await session.scalars(
                        select(ChatLog.id).where(ChatLog.timestamp < cutoff)
                    )
                ).all()
            )
            deleted_scored = 0
            if stale_log_ids:
                scored_result = await session.execute(delete(ScoredLog).where(ScoredLog.log_id.in_(stale_log_ids)))
                deleted_scored = int(scored_result.rowcount or 0)

            chat_result = await session.execute(delete(ChatLog).where(ChatLog.timestamp < cutoff))
            deleted_chat = int(chat_result.rowcount or 0)
            await session.commit()
            logger.info(
                "retention_purge_completed",
                cutoff=cutoff.isoformat(),
                deleted_chat_logs=deleted_chat,
                deleted_scored_logs=deleted_scored,
                retention_days=settings.RETENTION_DAYS,
            )
            return {"chat_logs": deleted_chat, "scored_logs": deleted_scored}
        except OperationalError as exc:
            await session.rollback()
            if "locked" in str(exc).lower():
                logger.warning("retention_purge_db_locked", cutoff=cutoff.isoformat())
                return {"chat_logs": 0, "scored_logs": 0}
            raise


def _run_purge_job() -> None:
    result = asyncio.run(purge_expired_logs())
    logger.info("retention_job_cycle_complete", deleted=result)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    asyncio.run(init_db())
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _run_purge_job,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_retention_purge",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    logger.info("retention_scheduler_started", schedule="02:00 UTC daily")
    scheduler.start()


if __name__ == "__main__":
    main()
