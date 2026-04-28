"""FastAPI application for the bias-mitigated chat backend."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import structlog
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from backend.aggregator import latest_metric_metadata, run_aggregation_cycle
from backend.config import Settings, get_settings
from backend.database import dispose_engine, get_session, get_session_maker, init_db
from backend.llm_client import LLMClient, build_llm_client
from backend.models import ChatLog, ChatRequest, ChatResponse, HealthStatus, MetricRow, MetricSnapshot, ScoredLog
from backend.queue import enqueue_fairness_job, get_redis_connection, queue_depths
from backend.routes.compliance import router as compliance_router
from backend.routes.compliance import stream_audit_export, purge_user_by_hash
from backend.utils import generate_safe_fallback, hash_sensitive, sanitize_prompt

logger = structlog.get_logger(__name__)
settings = get_settings()
app = FastAPI(title=settings.APP_NAME, version="0.1.0")

# Simple in-memory rate limiter (replaces SlowAPI which caused route parameter injection bugs)
_rate_limit_store: dict[str, tuple[int, float]] = {}


def _check_rate_limit(client_ip: str, limit_rpm: int) -> bool:
    """Return False if the client has exceeded the rate limit."""
    now = time.time()
    window_start = now - 60.0
    count, first_seen = _rate_limit_store.get(client_ip, (0, now))
    if first_seen < window_start:
        _rate_limit_store[client_ip] = (1, now)
        return True
    if count >= limit_rpm:
        return False
    _rate_limit_store[client_ip] = (count + 1, first_seen)
    return True


class RequestIDAndLatencyMiddleware(BaseHTTPMiddleware):
    """Attach a request id, measure latency, and emit structured logs."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover - handled by exception handlers too.
            latency_ms = (time.perf_counter() - start) * 1000.0
            logger.exception(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                latency_ms=round(latency_ms, 2),
                error_type=type(exc).__name__,
            )
            raise
        latency_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
        )
        return response


class AppState:
    """Typed container for shared application state."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm_client: LLMClient | None = None


app.state.runtime = AppState(settings)
app.add_middleware(RequestIDAndLatencyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


def _configure_logging() -> None:
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


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    client_ip = get_remote_address(request)
    logger.warning(
        "rate_limit_exceeded",
        endpoint=request.url.path,
        method=request.method,
        ip_hash=hash_sensitive(client_ip),
        limited_at=datetime.now(UTC).isoformat(),
        detail=str(exc.detail),
    )
    response = _rate_limit_exceeded_handler(request, exc)
    response.headers["Retry-After"] = "60"
    return response


app.include_router(compliance_router, prefix="/compliance")


async def _score_and_persist_inline(log_entry: dict[str, Any]) -> None:
    """Inline scoring — fully Redis-free. Used when Redis is unavailable (local dev).

    Calls the worker's pure scoring functions directly, then persists to ScoredLog
    without any queue involvement.
    """
    # Import pure scoring helpers — none of these touch Redis
    from backend.worker import (  # noqa: PLC0415
        _score_toxicity,
        _score_stereotype,
        _score_refusal,
        _score_sentiment,
        _extract_proxies,
    )
    from backend.utils import sanitize_prompt as _sanitize  # noqa: PLC0415

    def _run_scoring() -> dict[str, Any]:
        prompt_text = _sanitize(str(log_entry.get("prompt", "")))
        response_text = _sanitize(str(log_entry.get("response_text", "")))
        combined = f"{prompt_text} {response_text}".strip()
        scoring_text = response_text or prompt_text

        toxicity, identity_attack = _score_toxicity(scoring_text)
        stereotype_score = _score_stereotype(combined)
        refusal_prob = _score_refusal(scoring_text)
        sentiment = _score_sentiment(scoring_text)
        group_proxy, intersection_key = _extract_proxies(combined)

        return {
            "toxicity": toxicity,
            "identity_attack": identity_attack,
            "stereotype_score": stereotype_score,
            "refusal_prob": refusal_prob,
            "sentiment": sentiment,
            "group_proxy": group_proxy,
            "intersection_key": intersection_key,
        }

    try:
        scores = await asyncio.to_thread(_run_scoring)
        session_maker = get_session_maker()
        async with session_maker() as session:
            from backend.models import ScoredLog  # noqa: PLC0415
            from sqlalchemy import select as _select  # noqa: PLC0415
            log_id = str(log_entry["log_id"])
            existing = await session.scalar(_select(ScoredLog).where(ScoredLog.log_id == log_id))
            if existing is None:
                session.add(ScoredLog(
                    log_id=log_id,
                    toxicity=float(scores["toxicity"]),
                    identity_attack=float(scores["identity_attack"]),
                    stereotype_score=float(scores["stereotype_score"]),
                    refusal_prob=float(scores["refusal_prob"]),
                    sentiment=float(scores["sentiment"]),
                    group_proxy=str(scores["group_proxy"]),
                    intersection_key=str(scores["intersection_key"]),
                    scored_at=datetime.now(UTC),
                ))
                await session.commit()
                logger.info("inline_scoring_persisted", log_id=log_id)
    except Exception as exc:
        logger.warning("inline_scoring_failed", error_type=type(exc).__name__, error=str(exc))


async def _persist_chat_log_and_enqueue(log_entry: dict[str, Any]) -> None:
    """Persist the sanitized chat log and queue fairness work off-thread.

    Falls back to inline scoring when Redis is unavailable (e.g. local dev).
    """

    session_maker = get_session_maker()
    async with session_maker() as session:
        existing = await session.get(ChatLog, str(log_entry["log_id"]))
        if existing is None:
            session.add(
                ChatLog(
                    id=str(log_entry["log_id"]),
                    user_id_hash=str(log_entry["user_id_hash"]),
                    prompt_hash=str(log_entry["prompt_hash"]),
                    response_text=str(log_entry["response_text"]),
                    timestamp=datetime.now(UTC),
                    model=str(log_entry["model"]),
                    status=str(log_entry.get("status", "queued")),
                )
            )
        else:
            existing.user_id_hash = str(log_entry["user_id_hash"])
            existing.prompt_hash = str(log_entry["prompt_hash"])
            existing.response_text = str(log_entry["response_text"])
            existing.model = str(log_entry["model"])
            existing.status = str(log_entry.get("status", "queued"))
        await session.commit()

    # Try Redis queue first; fall back to inline scoring if Redis is down
    try:
        enqueue_fairness_job(log_entry)
    except Exception as exc:
        logger.info(
            "redis_unavailable_using_inline_scoring",
            error_type=type(exc).__name__,
            log_id=log_entry.get("log_id"),
        )
        await _score_and_persist_inline(log_entry)



async def _health_check_db() -> bool:
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(select(func.count()).select_from(ChatLog))
        return result.scalar_one() >= 0


async def _health_check_redis() -> bool:
    try:
        return bool(await asyncio.to_thread(get_redis_connection().ping))
    except Exception:
        return False


def _safe_queue_depths() -> dict[str, int]:
    try:
        return queue_depths()
    except Exception:
        return {"fairness_queue": 0, "scored_queue": 0, "dead_letter_queue": 0}


async def _latest_snapshot_time(session: AsyncSession) -> datetime | None:
    result = await session.execute(select(func.max(MetricSnapshot.computed_at)))
    return result.scalar_one()


async def _latest_scored_time(session: AsyncSession) -> datetime | None:
    result = await session.execute(select(func.max(ScoredLog.scored_at)))
    return result.scalar_one()


async def _load_latest_metric_rows(session: AsyncSession) -> list[MetricSnapshot]:
    result = await session.scalars(select(MetricSnapshot).order_by(MetricSnapshot.computed_at.desc()))
    seen: set[tuple[str, str, str]] = set()
    rows: list[MetricSnapshot] = []
    for row in result:
        key = (row.group_proxy, row.intersection_key, row.metric_name)
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


@app.on_event("startup")
async def startup_event() -> None:
    _configure_logging()
    await init_db()
    try:
        app.state.runtime.llm_client = build_llm_client(settings)
    except Exception as exc:
        logger.warning("llm_client_init_failed", error_type=type(exc).__name__)

        class _FallbackLLMClient:
            async def generate(self, prompt: str, system: str) -> str:  # noqa: ARG002
                return generate_safe_fallback()

            async def health_check(self) -> bool:
                return False

        app.state.runtime.llm_client = _FallbackLLMClient()
    logger.info("application_started", app_name=settings.APP_NAME, environment=settings.APP_ENV)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await dispose_engine()
    try:
        connection = get_redis_connection()
        connection.close()
    except Exception as exc:  # pragma: no cover - shutdown should continue even if Redis is unavailable.
        logger.warning("redis_close_failed", error_type=type(exc).__name__)
    logger.info("application_stopped")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "invalid request payload",
            "errors": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": getattr(request.state, "request_id", None)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception("unhandled_exception", request_id=request_id, error_type=type(exc).__name__)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "internal server error", "request_id": request_id})


@app.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    """Generate a response immediately and enqueue fairness work asynchronously."""

    # Simple in-process rate limiting for the chat endpoint
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip, settings.RATE_LIMIT_RPM):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    runtime: AppState = request.app.state.runtime
    llm_client = runtime.llm_client
    if llm_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="llm client unavailable")

    start = time.perf_counter()
    sanitized_prompt = sanitize_prompt(payload.prompt)
    system_prompt = payload.system_prompt or "You are a helpful assistant. Be accurate, concise, and avoid stereotypes."
    response_text = await llm_client.generate(prompt=sanitized_prompt, system=system_prompt)
    latency_ms = (time.perf_counter() - start) * 1000.0
    request_id = getattr(request.state, "request_id", uuid4().hex)
    user_identifier = payload.user_id or (request.client.host if request.client else "anonymous")
    log_entry = {
        "log_id": uuid4().hex,
        "request_id": request_id,
        "user_id": user_identifier,
        "user_id_hash": hash_sensitive(user_identifier),
        "prompt": sanitized_prompt,
        "prompt_hash": hash_sensitive(sanitized_prompt),
        "response_text": sanitize_prompt(response_text),
        "model": settings.LLM_MODEL,
        "status": "queued",
    }
    background_tasks.add_task(_persist_chat_log_and_enqueue, log_entry)
    logger.info(
        "chat_completed",
        request_id=request_id,
        user_id_hash=log_entry["user_id_hash"],
        latency_ms=round(latency_ms, 2),
        status_code=status.HTTP_200_OK,
    )
    return ChatResponse(
        request_id=request_id,
        response_text=response_text,
        model=settings.LLM_MODEL,
        status="ok",
        latency_ms=round(latency_ms, 2),
        queued_for_fairness=True,
    )


@app.get("/metrics")
async def metrics(
    request: Request,
    page: int = 1,
    page_size: int = settings.METRICS_PAGE_SIZE,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return the latest aggregated fairness metrics as paginated JSON."""

    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page must be >= 1")
    page_size = max(1, min(page_size, settings.METRICS_PAGE_SIZE))

    # Always re-aggregate so "Refresh Data" picks up new chats immediately
    try:
        await run_aggregation_cycle()
    except Exception as agg_exc:
        logger.warning("aggregation_failed_on_metrics", error_type=type(agg_exc).__name__)

    rows = await _load_latest_metric_rows(session)
    total = len(rows)
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    page_rows = rows[start_index:end_index]
    latest_snapshot = rows[0].computed_at if rows else None
    # SQLite returns naive datetimes — normalize to UTC-aware before comparing
    if latest_snapshot is not None and latest_snapshot.tzinfo is None:
        latest_snapshot = latest_snapshot.replace(tzinfo=UTC)
    stale = bool(
        latest_snapshot is None
        or (datetime.now(UTC) - latest_snapshot) > timedelta(seconds=settings.WORKER_LAG_WARN_SECONDS)
    )
    items = [
        MetricRow(
            group_proxy=row.group_proxy,
            intersection_key=row.intersection_key,
            metric_name=row.metric_name,
            mean=row.mean,
            std=row.std,
            count=row.count,
            ci_low=row.ci_low,
            ci_high=row.ci_high,
            computed_at=row.computed_at,
            alert_flag=row.alert_flag,
            low_confidence=row.low_confidence,
            definition=latest_metric_metadata()[row.metric_name]["definition"],
            harm_context=latest_metric_metadata()[row.metric_name]["harm_context"],
            limitations=latest_metric_metadata()[row.metric_name]["limitations"],
        ).model_dump(mode="json")
        for row in page_rows
    ]
    return {
        "request_id": getattr(request.state, "request_id", None),
        "page": page,
        "page_size": page_size,
        "total": total,
        "stale": stale,
        "generated_at": datetime.now(UTC).isoformat(),
        "items": items,
        "metadata": latest_metric_metadata(),
        "trade_off_note": "Lower toxicity can increase refusal rate; both metrics are exposed together for transparency.",
    }


@app.get("/health", response_model=HealthStatus)
async def health(request: Request, session: AsyncSession = Depends(get_session)) -> HealthStatus:
    """Check database, Redis, and LLM connectivity."""

    runtime: AppState = request.app.state.runtime
    llm_client = runtime.llm_client
    db_ok, redis_ok, llm_ok = await asyncio.gather(
        _health_check_db(),
        _health_check_redis(),
        llm_client.health_check() if llm_client is not None else asyncio.sleep(0, result=False),
    )
    queue_depth_breakdown = _safe_queue_depths()
    queue_depth = sum(queue_depth_breakdown.values())
    latest_snapshot_time = await _latest_snapshot_time(session)
    latest_scored_time = await _latest_scored_time(session)
    worker_lag_seconds: float | None = None
    if latest_scored_time is not None:
        worker_lag_seconds = (datetime.now(UTC) - latest_scored_time).total_seconds()
    stale = bool(
        latest_snapshot_time is None
        or (datetime.now(UTC) - latest_snapshot_time) > timedelta(seconds=settings.WORKER_LAG_WARN_SECONDS)
    )
    status_value = "ok" if db_ok and redis_ok and llm_ok and queue_depth < 1000 else "degraded"
    return HealthStatus(
        status=status_value,
        db=bool(db_ok),
        redis=bool(redis_ok),
        llm=bool(llm_ok),
        worker_lag_seconds=worker_lag_seconds,
        stale=stale,
        queue_depth=queue_depth,
        request_id=getattr(request.state, "request_id", None) or uuid4().hex,
        details={
            "latest_snapshot_time": latest_snapshot_time.isoformat() if latest_snapshot_time else None,
            "latest_scored_time": latest_scored_time.isoformat() if latest_scored_time else None,
            "queue_depth_breakdown": queue_depth_breakdown,
        },
    )


@app.delete("/user/{user_id_hash}")
async def delete_user_artifacts(user_id_hash: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Backward-compatible purge endpoint mirrored from /compliance/user/{user_id_hash}."""

    return await purge_user_by_hash(user_id_hash=user_id_hash, session=session)


@app.get("/audit-export")
async def audit_export(session: AsyncSession = Depends(get_session)) -> Response:
    """Backward-compatible audit export endpoint mirrored from /compliance/audit-export."""

    return await stream_audit_export(session=session)
