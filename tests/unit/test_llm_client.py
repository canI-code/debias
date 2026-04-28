from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from backend.llm_client import AnthropicClient, LLMClient, OpenAIClient, build_llm_client


class DummySettings:
    LLM_PROVIDER = "openai"
    LLM_API_KEY = "test-key"
    LLM_MODEL = "test-model"
    LLM_BASE_URL = None
    LLM_TIMEOUT_SECONDS = 0.1
    LLM_RETRIES = 2


class AlwaysFailClient(LLMClient):
    def __init__(self) -> None:
        super().__init__(DummySettings())
        self.calls = 0

    async def _generate_once(self, prompt: str, system: str):  # noqa: ARG002
        self.calls += 1
        raise RuntimeError("boom")

    async def _probe(self) -> bool:
        return False


class AlwaysPassClient(LLMClient):
    def __init__(self) -> None:
        super().__init__(DummySettings())

    async def _generate_once(self, prompt: str, system: str):  # noqa: ARG002
        return "ok", {"total_tokens": 1}

    async def _probe(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_generate_retries_and_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AlwaysFailClient()
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    result = await client.generate(prompt="hello", system="sys")
    assert "unable to answer" in result.lower()
    assert client.calls == 3
    assert len(sleep_calls) == 2


@pytest.mark.asyncio
async def test_generate_returns_provider_text() -> None:
    client = AlwaysPassClient()
    result = await client.generate(prompt="hello", system="sys")
    assert result == "ok"


def test_build_llm_client_routes_by_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = DummySettings()
    settings.LLM_PROVIDER = "openai"
    monkeypatch.setattr("backend.llm_client.AsyncOpenAI", object())
    monkeypatch.setattr("backend.llm_client.AsyncAnthropic", object())

    class StubOpenAI(OpenAIClient):
        def __init__(self, active_settings):
            LLMClient.__init__(self, active_settings)
            self._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None)))

    class StubAnthropic(AnthropicClient):
        def __init__(self, active_settings):
            LLMClient.__init__(self, active_settings)
            self._client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: None))

    monkeypatch.setattr("backend.llm_client.OpenAIClient", StubOpenAI)
    monkeypatch.setattr("backend.llm_client.AnthropicClient", StubAnthropic)
    client = build_llm_client(settings)
    assert isinstance(client, StubOpenAI)

    settings.LLM_PROVIDER = "anthropic"
    client = build_llm_client(settings)
    assert isinstance(client, StubAnthropic)
