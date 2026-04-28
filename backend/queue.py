"""Redis queue and idempotent enqueue helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import redis
from rq import Queue, Retry

from backend.config import get_settings

QUEUE_JOB_TTL_SECONDS = 300
RESULT_TTL_SECONDS = 3600


@lru_cache(maxsize=1)
def get_redis_connection() -> redis.Redis[str]:
    """Return a shared Redis client with safe socket defaults."""

    settings = get_settings()
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        health_check_interval=30,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


@lru_cache(maxsize=1)
def fairness_queue() -> Queue:
    """Queue for heavy fairness scoring jobs."""

    return Queue("fairness_queue", connection=get_redis_connection(), default_timeout=QUEUE_JOB_TTL_SECONDS)


@lru_cache(maxsize=1)
def scored_queue() -> Queue:
    """Queue for persistence of scored logs."""

    return Queue("scored_queue", connection=get_redis_connection(), default_timeout=QUEUE_JOB_TTL_SECONDS)


@lru_cache(maxsize=1)
def dead_letter_queue() -> Queue:
    """Queue that records unrecoverable failures for audit handling."""

    return Queue("dead_letter_queue", connection=get_redis_connection(), default_timeout=QUEUE_JOB_TTL_SECONDS)


def enqueue_fairness_job(log_entry: dict[str, Any]) -> str:
    """Enqueue a fairness scoring job with an idempotent RQ job id."""

    from backend.worker import score_and_tag

    log_id = str(log_entry["log_id"])
    job = fairness_queue().enqueue(
        score_and_tag,
        log_entry,
        job_id=f"fairness:{log_id}",
        ttl=QUEUE_JOB_TTL_SECONDS,
        result_ttl=RESULT_TTL_SECONDS,
        failure_ttl=RESULT_TTL_SECONDS,
        retry=Retry(max=3, interval=[5, 15, 45]),
    )
    return job.id


def enqueue_scored_job(scored_entry: dict[str, Any]) -> str:
    """Enqueue a persistence job for scored output."""

    from backend.worker import persist_scored_log

    log_id = str(scored_entry["log_id"])
    job = scored_queue().enqueue(
        persist_scored_log,
        scored_entry,
        job_id=f"scored:{log_id}",
        ttl=QUEUE_JOB_TTL_SECONDS,
        result_ttl=RESULT_TTL_SECONDS,
        failure_ttl=RESULT_TTL_SECONDS,
        retry=Retry(max=3, interval=[5, 15, 45]),
    )
    return job.id


def enqueue_dead_letter(payload: dict[str, Any]) -> str:
    """Record an unrecoverable failure in the dead-letter queue."""

    job_id = payload.get("log_id") or payload.get("request_id") or payload.get("error_type") or "unknown"
    job = dead_letter_queue().enqueue(
        "backend.worker.store_dead_letter",
        payload,
        job_id=f"dead:{job_id}",
        ttl=RESULT_TTL_SECONDS,
        result_ttl=RESULT_TTL_SECONDS,
        failure_ttl=RESULT_TTL_SECONDS,
    )
    return job.id


def queue_depths() -> dict[str, int]:
    """Return queue depths for health checks and alerting."""

    connection = get_redis_connection()
    return {
        "fairness_queue": int(connection.llen(fairness_queue().key)),
        "scored_queue": int(connection.llen(scored_queue().key)),
        "dead_letter_queue": int(connection.llen(dead_letter_queue().key)),
    }
