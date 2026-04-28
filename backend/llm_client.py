"""Provider-agnostic LLM client abstraction with retries and safe fallbacks."""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any

import structlog

from backend.config import Settings, get_settings
from backend.utils import generate_safe_fallback

logger = structlog.get_logger(__name__)

try:  # pragma: no cover - availability depends on environment.
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore[assignment]

try:  # pragma: no cover - availability depends on environment.
    from anthropic import AsyncAnthropic
except Exception:  # pragma: no cover
    AsyncAnthropic = None  # type: ignore[assignment]


class LLMClient(ABC):
    """Abstract async client for text generation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    async def _generate_once(self, prompt: str, system: str) -> tuple[str, dict[str, Any]]:
        """Perform one provider call and return text plus usage metadata."""

    @abstractmethod
    async def _probe(self) -> bool:
        """Return whether the provider is reachable."""

    async def generate(self, prompt: str, system: str) -> str:
        """Generate text with timeout, retries, and a safe fallback."""

        last_error: Exception | None = None
        for attempt in range(self.settings.LLM_RETRIES + 1):
            try:
                text, usage = await asyncio.wait_for(
                    self._generate_once(prompt=prompt, system=system),
                    timeout=self.settings.LLM_TIMEOUT_SECONDS,
                )
                if usage:
                    logger.info(
                        "llm_usage",
                        provider=self.settings.LLM_PROVIDER,
                        model=self.settings.LLM_MODEL,
                        prompt_tokens=usage.get("prompt_tokens"),
                        completion_tokens=usage.get("completion_tokens"),
                        total_tokens=usage.get("total_tokens"),
                    )
                return text.strip() or generate_safe_fallback()
            except Exception as exc:  # pragma: no cover - failure path is environment dependent.
                last_error = exc
                logger.warning(
                    "llm_request_failed",
                    provider=self.settings.LLM_PROVIDER,
                    model=self.settings.LLM_MODEL,
                    attempt=attempt + 1,
                    max_attempts=self.settings.LLM_RETRIES + 1,
                    error_type=type(exc).__name__,
                )
                if attempt < self.settings.LLM_RETRIES:
                    delay = min(2.0 ** attempt, 8.0) + random.uniform(0.0, 0.25)
                    await asyncio.sleep(delay)
        logger.error(
            "llm_fallback_used",
            provider=self.settings.LLM_PROVIDER,
            model=self.settings.LLM_MODEL,
            error_type=type(last_error).__name__ if last_error else None,
        )
        return generate_safe_fallback()

    async def health_check(self) -> bool:
        """Check provider connectivity without surfacing secrets."""

        try:
            return await asyncio.wait_for(self._probe(), timeout=min(self.settings.LLM_TIMEOUT_SECONDS, 5.0))
        except Exception:
            return False


class OpenAIClient(LLMClient):
    """OpenAI-compatible client. Works with OpenRouter through a base URL."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        if AsyncOpenAI is None:
            raise RuntimeError("openai package is not installed")
        client_kwargs: dict[str, Any] = {"api_key": settings.LLM_API_KEY}
        if settings.LLM_BASE_URL:
            client_kwargs["base_url"] = settings.LLM_BASE_URL
        self._client = AsyncOpenAI(**client_kwargs)

    async def _generate_once(self, prompt: str, system: str) -> tuple[str, dict[str, Any]]:
        response = await self._client.chat.completions.create(
            model=self.settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
            "completion_tokens": getattr(response.usage, "completion_tokens", None),
            "total_tokens": getattr(response.usage, "total_tokens", None),
        }
        return content, usage

    async def _probe(self) -> bool:
        response = await self._client.chat.completions.create(
            model=self.settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": "Reply with ok."},
                {"role": "user", "content": "ping"},
            ],
            temperature=0.0,
            max_tokens=1,
        )
        return bool(response.choices and response.choices[0].message.content is not None)


class AnthropicClient(LLMClient):
    """Anthropic client implementation."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        if AsyncAnthropic is None:
            raise RuntimeError("anthropic package is not installed")
        self._client = AsyncAnthropic(api_key=settings.LLM_API_KEY)

    async def _generate_once(self, prompt: str, system: str) -> tuple[str, dict[str, Any]]:
        response = await self._client.messages.create(
            model=self.settings.LLM_MODEL,
            max_tokens=512,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        content = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                content += getattr(block, "text", "")
        usage = {
            "prompt_tokens": getattr(response.usage, "input_tokens", None),
            "completion_tokens": getattr(response.usage, "output_tokens", None),
            "total_tokens": None,
        }
        return content, usage

    async def _probe(self) -> bool:
        response = await self._client.messages.create(
            model=self.settings.LLM_MODEL,
            max_tokens=1,
            temperature=0.0,
            system="Reply with ok.",
            messages=[{"role": "user", "content": "ping"}],
        )
        return bool(response.content)


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    """Instantiate the configured provider client.

    Groq uses the OpenAI-compatible API, so it reuses OpenAIClient with a
    custom base_url. Set LLM_BASE_URL=https://api.groq.com/openai/v1 in .env.
    """

    active_settings = settings or get_settings()
    if active_settings.LLM_PROVIDER == "anthropic":
        return AnthropicClient(active_settings)
    # openai and groq both use the OpenAI-compatible client
    return OpenAIClient(active_settings)
