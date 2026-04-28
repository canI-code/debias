"""SQLAlchemy models and Pydantic schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class ChatLog(Base):
    """Persisted request/response audit record."""

    __tablename__ = "chat_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)

class ScoredLog(Base):
    """Scored output log produced by the fairness worker."""

    __tablename__ = "scored_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    log_id: Mapped[str] = mapped_column(String(36), nullable=False)
    toxicity: Mapped[float | None] = mapped_column(Float, nullable=True)
    identity_attack: Mapped[float | None] = mapped_column(Float, nullable=True)
    stereotype_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    refusal_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)
    group_proxy: Mapped[str] = mapped_column(String(128), nullable=False)
    intersection_key: Mapped[str] = mapped_column(String(256), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class MetricSnapshot(Base):
    """Aggregated metrics for dashboarding and audits."""

    __tablename__ = "metric_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_proxy: Mapped[str] = mapped_column(String(128), nullable=False)
    intersection_key: Mapped[str] = mapped_column(String(256), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    mean: Mapped[float] = mapped_column(Float, nullable=False)
    std: Mapped[float] = mapped_column(Float, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    alert_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class ChatRequest(BaseModel):
    """Incoming chat request."""

    prompt: str = Field(validation_alias=AliasChoices("prompt", "message"), min_length=1, max_length=12000)
    user_id: str | None = Field(default=None, max_length=256)
    system_prompt: str | None = Field(default=None, max_length=4000)

    @field_validator("prompt")
    @classmethod
    def _normalize_prompt(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("prompt must not be empty")
        return normalized

    @field_validator("user_id", "system_prompt")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ChatResponse(BaseModel):
    """Chat response payload returned by the API."""

    request_id: str
    response_text: str
    model: str
    status: str
    latency_ms: float
    queued_for_fairness: bool = True


class MetricRow(BaseModel):
    """Aggregated distribution row for dashboards and audits."""

    group_proxy: str
    intersection_key: str
    metric_name: str
    mean: float
    std: float
    count: int
    ci_low: float | None
    ci_high: float | None
    computed_at: datetime
    alert_flag: bool
    low_confidence: bool = False
    definition: str
    harm_context: str
    limitations: str


class HealthStatus(BaseModel):
    """Readiness and liveness status."""

    status: str
    db: bool
    redis: bool
    llm: bool
    worker_lag_seconds: float | None
    stale: bool
    queue_depth: int
    request_id: str
    details: dict[str, Any] = Field(default_factory=dict)
