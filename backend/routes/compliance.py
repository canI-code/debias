"""Compliance endpoints for audit export and GDPR purge operations."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_session
from backend.models import ChatLog, MetricSnapshot, ScoredLog
from backend.utils import hash_sensitive

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(tags=["compliance"])

MITIGATION_CHANGELOG: list[dict[str, Any]] = [
    {
        "version": "1.0.0",
        "summary": "Initial fairness pipeline with asynchronous scoring, hashed audit logs, and dashboard snapshots.",
        "date": "2026-04-25",
    },
    {
        "version": "1.1.0",
        "summary": "Added production hardening for compliance endpoints and retention scheduling.",
        "date": "2026-04-25",
    },
]


def _export_headers() -> dict[str, str]:
    return {
        "Content-Disposition": "attachment; filename=audit-export.jsonl",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }


async def _iter_audit_jsonl(session: AsyncSession) -> AsyncIterator[bytes]:
    """Stream JSONL payload in chunks to avoid loading the full dataset in memory."""

    header = {
        "type": "header",
        "data": {
            "exported_at": datetime.now(UTC).isoformat(),
            "thresholds": settings.FAIRNESS_THRESHOLDS,
            "mitigation_changelog": MITIGATION_CHANGELOG,
        },
    }
    yield (json.dumps(header, separators=(",", ":")) + "\n").encode("utf-8")

    stream = await session.stream_scalars(select(MetricSnapshot).order_by(MetricSnapshot.computed_at.asc()))
    async for snapshot in stream:
        payload = {
            "type": "snapshot",
            "data": {
                "id_hash": hash_sensitive(snapshot.id),
                "group_proxy_hash": hash_sensitive(snapshot.group_proxy),
                "intersection_key_hash": hash_sensitive(snapshot.intersection_key),
                "metric_name": snapshot.metric_name,
                "mean": snapshot.mean,
                "std": snapshot.std,
                "count": snapshot.count,
                "ci_low": snapshot.ci_low,
                "ci_high": snapshot.ci_high,
                "computed_at": snapshot.computed_at.isoformat(),
                "alert_flag": snapshot.alert_flag,
                "low_confidence": snapshot.low_confidence,
            },
        }
        yield (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")


async def stream_audit_export(session: AsyncSession) -> StreamingResponse:
    return StreamingResponse(
        _iter_audit_jsonl(session=session),
        media_type="application/x-ndjson",
        headers=_export_headers(),
    )


@router.get("/audit-export")
async def audit_export(session: AsyncSession = Depends(get_session)) -> StreamingResponse:
    """Export snapshots in JSONL format with hashed identifiers for external audit use."""

    return await stream_audit_export(session=session)


async def purge_user_by_hash(user_id_hash: str, session: AsyncSession) -> dict[str, int]:
    """Delete all user-linked logs and associated scored rows in a single transaction."""

    if not user_id_hash.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id_hash must be provided")

    chat_rows = list((await session.scalars(select(ChatLog).where(ChatLog.user_id_hash == user_id_hash))).all())
    if not chat_rows:
        logger.info("gdpr_purge_noop", user_id_hash=user_id_hash)
        return {"deleted": 0}

    log_ids = [row.id for row in chat_rows]
    scored_delete = await session.execute(delete(ScoredLog).where(ScoredLog.log_id.in_(log_ids)))
    chat_delete = await session.execute(delete(ChatLog).where(ChatLog.id.in_(log_ids)))
    await session.commit()

    deleted = int((scored_delete.rowcount or 0) + (chat_delete.rowcount or 0))
    logger.info(
        "gdpr_purge_completed",
        user_id_hash=user_id_hash,
        deleted=deleted,
        deleted_chat_logs=int(chat_delete.rowcount or 0),
        deleted_scored_logs=int(scored_delete.rowcount or 0),
    )
    return {"deleted": deleted}


@router.delete("/user/{user_id_hash}")
async def delete_user_data(
    user_id_hash: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """GDPR/CCPA erase operation for all data mapped to a hashed user identifier."""

    result = await purge_user_by_hash(user_id_hash=user_id_hash, session=session)
    logger.info(
        "gdpr_purge_event",
        user_id_hash=user_id_hash,
        request_id=getattr(request.state, "request_id", None),
        deleted=result["deleted"],
        event_timestamp=datetime.now(UTC).isoformat(),
    )
    return result
