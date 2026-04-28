"""Aggregation pipeline that builds auditable fairness snapshots."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import delete, select

from backend.config import get_settings
from backend.database import get_session_maker
from backend.models import ChatLog, MetricSnapshot, ScoredLog, utcnow
from backend.utils import bootstrap_ci, check_disparity

logger = structlog.get_logger(__name__)

METRIC_COLUMNS = ("toxicity", "identity_attack", "stereotype_score", "refusal_prob", "sentiment")
METRIC_METADATA: dict[str, dict[str, str]] = {
    "toxicity": {
        "definition": "Average probability of toxic or abusive language in the model output.",
        "harm_context": "High toxicity indicates user harm, harassment risk, and policy violations.",
        "limitations": "Scores are approximate and can be distorted by sanitization, domain jargon, or multilingual text.",
    },
    "identity_attack": {
        "definition": "Average probability that the output targets a demographic identity group.",
        "harm_context": "Identity attack disparities are a direct fairness and safety concern.",
        "limitations": "Proxy-based detection may undercount subtle attacks and overcount quoted text.",
    },
    "stereotype_score": {
        "definition": "Average likelihood that the output contains stereotypes or biased group framing.",
        "harm_context": "Stereotypes can reinforce harmful social narratives and downstream allocation bias.",
        "limitations": "Zero-shot and keyword heuristics are imperfect and require model calibration.",
    },
    "refusal_prob": {
        "definition": "Estimated probability that the model refused or declined the request.",
        "harm_context": "Refusal gaps matter when safety tuning disproportionately affects protected groups.",
        "limitations": "Refusal text varies across providers and can be conflated with safety disclaimers.",
    },
    "sentiment": {
        "definition": "Signed sentiment score for the model response, from negative to positive.",
        "harm_context": "Sentiment helps detect tone shifts that correlate with stereotyped or dismissive behavior.",
        "limitations": "Sentiment models are brittle on sarcasm, technical support text, and culturally specific language.",
    },
}


def _metric_threshold(metric_name: str) -> float:
    settings = get_settings()
    if metric_name in {"toxicity", "identity_attack"}:
        return settings.FAIRNESS_THRESHOLDS.get("toxicity_gap", 0.15)
    if metric_name == "stereotype_score":
        return settings.FAIRNESS_THRESHOLDS.get("stereotype_gap", 0.15)
    if metric_name == "refusal_prob":
        return settings.FAIRNESS_THRESHOLDS.get("refusal_gap", 0.20)
    return settings.FAIRNESS_THRESHOLDS.get("toxicity_gap", 0.15)


def _build_row(
    group_proxy: str,
    intersection_key: str,
    metric_name: str,
    values: list[float],
    computed_at: datetime,
) -> dict[str, Any]:
    count = len(values)
    mean = float(np.mean(values)) if count else float("nan")
    std = float(np.std(values, ddof=1)) if count > 1 else 0.0
    if count >= 2:
        ci_low, ci_high = bootstrap_ci(values, n_boot=get_settings().BOOTSTRAP_RESAMPLES, ci=get_settings().BOOTSTRAP_CI)
    else:
        ci_low, ci_high = float("nan"), float("nan")
    return {
        "group_proxy": group_proxy,
        "intersection_key": intersection_key,
        "metric_name": metric_name,
        "mean": mean,
        "std": std,
        "count": count,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "computed_at": computed_at,
        "alert_flag": False,
        "low_confidence": count < 5,
        "definition": METRIC_METADATA[metric_name]["definition"],
        "harm_context": METRIC_METADATA[metric_name]["harm_context"],
        "limitations": METRIC_METADATA[metric_name]["limitations"],
    }


def _apply_disparity_flags(rows: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["metric_name"]), []).append(row)

    for metric_name, metric_rows in grouped.items():
        threshold = _metric_threshold(metric_name)
        for left, right in combinations(metric_rows, 2):
            if check_disparity(left, right, threshold):
                left["alert_flag"] = True
                right["alert_flag"] = True


async def _load_scored_rows(session) -> list[dict[str, Any]]:
    result = await session.scalars(select(ScoredLog).order_by(ScoredLog.scored_at.asc()))
    records: list[dict[str, Any]] = []
    for row in result:
        records.append(
            {
                "log_id": row.log_id,
                "group_proxy": row.group_proxy,
                "intersection_key": row.intersection_key,
                "toxicity": row.toxicity,
                "identity_attack": row.identity_attack,
                "stereotype_score": row.stereotype_score,
                "refusal_prob": row.refusal_prob,
                "sentiment": row.sentiment,
                "scored_at": row.scored_at,
            }
        )
    return records


async def _persist_metric_snapshots(session, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        await session.execute(
            delete(MetricSnapshot).where(
                MetricSnapshot.group_proxy == row["group_proxy"],
                MetricSnapshot.intersection_key == row["intersection_key"],
                MetricSnapshot.metric_name == row["metric_name"],
            )
        )
        session.add(
            MetricSnapshot(
                group_proxy=row["group_proxy"],
                intersection_key=row["intersection_key"],
                metric_name=row["metric_name"],
                mean=float(row["mean"]),
                std=float(row["std"]),
                count=int(row["count"]),
                ci_low=None if pd.isna(row["ci_low"]) else float(row["ci_low"]),
                ci_high=None if pd.isna(row["ci_high"]) else float(row["ci_high"]),
                computed_at=row["computed_at"],
                alert_flag=bool(row["alert_flag"]),
                low_confidence=bool(row["low_confidence"]),
            )
        )
    await session.commit()


async def _cleanup_retention(session) -> tuple[int, int]:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.RETENTION_DAYS)
    chat_delete = await session.execute(delete(ChatLog).where(ChatLog.timestamp < cutoff))
    scored_delete = await session.execute(delete(ScoredLog).where(ScoredLog.scored_at < cutoff))
    await session.commit()
    return chat_delete.rowcount or 0, scored_delete.rowcount or 0


async def build_distribution_table_async() -> pd.DataFrame:
    """Build the current distribution table and persist a new snapshot."""

    settings = get_settings()
    session_maker = get_session_maker()
    async with session_maker() as session:
        scored_rows = await _load_scored_rows(session)
        if not scored_rows:
            return pd.DataFrame(
                columns=[
                    "group_proxy",
                    "intersection_key",
                    "metric_name",
                    "mean",
                    "std",
                    "count",
                    "ci_low",
                    "ci_high",
                    "computed_at",
                    "alert_flag",
                    "low_confidence",
                    "definition",
                    "harm_context",
                    "limitations",
                ]
            )

        frame = pd.DataFrame(scored_rows)
        computed_at = utcnow()
        rows: list[dict[str, Any]] = []
        for (group_proxy, intersection_key), group_frame in frame.groupby(["group_proxy", "intersection_key"], dropna=False):
            for metric_name in METRIC_COLUMNS:
                values = [float(value) for value in group_frame[metric_name].dropna().tolist()]
                if not values:
                    continue
                rows.append(_build_row(str(group_proxy), str(intersection_key), metric_name, values, computed_at))

        _apply_disparity_flags(rows)
        await _persist_metric_snapshots(session, rows)
        deleted_chat_rows, deleted_scored_rows = await _cleanup_retention(session)
        logger.info(
            "aggregation_completed",
            row_count=len(rows),
            deleted_chat_rows=deleted_chat_rows,
            deleted_scored_rows=deleted_scored_rows,
            retention_days=settings.RETENTION_DAYS,
        )
        return pd.DataFrame(rows)


def build_distribution_table() -> pd.DataFrame:
    """Synchronous wrapper for scheduler and worker processes."""

    return asyncio.run(build_distribution_table_async())


async def run_aggregation_cycle() -> pd.DataFrame:
    """Async entrypoint for use inside a running event loop (e.g. FastAPI)."""

    return await build_distribution_table_async()


def latest_metric_metadata() -> dict[str, dict[str, str]]:
    """Return metric metadata for API responses and audits."""

    return METRIC_METADATA.copy()
