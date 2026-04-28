"""Application settings and environment validation."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    LLM_PROVIDER: Literal["openai", "anthropic", "groq"] = "openai"
    LLM_API_KEY: str = Field(default="change-me", min_length=1)
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str | None = None
    LLM_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0.0)
    LLM_RETRIES: int = Field(default=3, ge=0, le=10)
    REDIS_URL: str = "redis://redis:6379/0"
    DATABASE_URL: str = "sqlite+aiosqlite:///./fair_llm_backend.db"
    SALT: str = Field(default="change-me-salt", min_length=8)
    RETENTION_DAYS: int = Field(default=30, ge=1, le=3650)
    RATE_LIMIT_RPM: int = Field(default=60, ge=1, le=6000)
    FAIRNESS_THRESHOLDS: dict[str, float] = Field(
        default_factory=lambda: {
            "toxicity_gap": 0.15,
            "stereotype_gap": 0.15,
            "refusal_gap": 0.20,
        }
    )
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    APP_NAME: str = "fair-llm-backend"
    APP_ENV: Literal["local", "development", "staging", "production"] = "local"
    STRICT_ENV_VALIDATION: bool = True
    BOOTSTRAP_RESAMPLES: int = Field(default=1000, ge=100, le=10000)
    BOOTSTRAP_CI: float = Field(default=0.95, gt=0.5, lt=1.0)
    METRICS_PAGE_SIZE: int = Field(default=100, ge=1, le=1000)
    MAX_PROMPT_CHARS: int = Field(default=12000, ge=1, le=50000)
    WORKER_LAG_WARN_SECONDS: int = Field(default=900, ge=60)

    @field_validator("LLM_API_KEY", "SALT", mode="before")
    @classmethod
    def _strip_secrets(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return ["http://localhost:3000"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ["http://localhost:3000"]
            if raw.startswith("["):
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS JSON must decode to a list")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in raw.split(",") if item.strip()]
        raise TypeError("CORS_ORIGINS must be a list or comma-separated string")

    @field_validator("FAIRNESS_THRESHOLDS", mode="before")
    @classmethod
    def _parse_thresholds(cls, value: Any) -> dict[str, float]:
        if value is None:
            return {
                "toxicity_gap": 0.15,
                "stereotype_gap": 0.15,
                "refusal_gap": 0.20,
            }
        if isinstance(value, dict):
            return {str(key): float(amount) for key, amount in value.items()}
        if isinstance(value, str):
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError("FAIRNESS_THRESHOLDS must decode to a JSON object")
            return {str(key): float(amount) for key, amount in parsed.items()}
        raise TypeError("FAIRNESS_THRESHOLDS must be a dict or JSON string")

    @model_validator(mode="after")
    def _validate_settings(self) -> "Settings":
        if not self.LLM_API_KEY:
            raise ValueError("LLM_API_KEY must be provided")
        if not self.SALT:
            raise ValueError("SALT must be provided")
        if not self.DATABASE_URL.strip():
            raise ValueError("DATABASE_URL must be provided")
        if self.LLM_BASE_URL is not None:
            self.LLM_BASE_URL = self.LLM_BASE_URL.strip() or None

        if self.APP_ENV == "production" and self.STRICT_ENV_VALIDATION:
            if self.LLM_API_KEY in {"change-me", ""}:
                raise ValueError("LLM_API_KEY must be a non-default secret in production")
            if self.SALT in {"change-me-salt", "replace-with-a-long-random-secret", ""}:
                raise ValueError("SALT must be a non-default secret in production")
            if any(origin.strip() == "*" for origin in self.CORS_ORIGINS):
                raise ValueError("CORS_ORIGINS cannot include '*' in production")
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must include at least one explicit origin in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
