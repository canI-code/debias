from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.models import ChatLog, MetricSnapshot, ScoredLog, utcnow


class DummyLLMClient:
    async def generate(self, prompt: str, system: str) -> str:  # noqa: ARG002
        return "safe response"

    async def health_check(self) -> bool:
        return True


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key: str, ttl: int) -> bool:  # noqa: ARG002
        return True

    def ping(self) -> bool:
        return True

    def llen(self, key: str) -> int:
        return self.store.get(key, 0)

    def close(self) -> None:
        return None


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main_module, "build_llm_client", lambda settings=None: DummyLLMClient())
    monkeypatch.setattr(main_module, "get_redis_connection", lambda: FakeRedis())
    monkeypatch.setattr(main_module, "enqueue_fairness_job", lambda log_entry: "job-1")
    monkeypatch.setattr(main_module, "run_aggregation_cycle", lambda: None)
    with TestClient(main_module.app) as test_client:
        test_client.app.state.runtime.llm_client = DummyLLMClient()
        yield test_client


def test_chat_round_trip_and_latency(client: TestClient) -> None:
    start = time.perf_counter()
    response = client.post("/chat", json={"message": "Write a respectful summary.", "user_id": "user-1"})
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["response_text"] == "safe response"
    assert elapsed_ms < 800


def test_health_endpoint_reports_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert payload["redis"] is True
    assert payload["llm"] is True


@pytest.mark.asyncio
async def test_metrics_schema_with_seeded_rows(client: TestClient) -> None:
    session_maker = main_module.get_session_maker()
    async with session_maker() as session:
        chat_log = ChatLog(
            id="11111111-1111-1111-1111-111111111111",
            user_id_hash="u",
            prompt_hash="p",
            response_text="x",
            timestamp=utcnow(),
            model="test-model",
            status="scored",
        )
        scored_log = ScoredLog(
            log_id=chat_log.id,
            toxicity=0.1,
            identity_attack=0.05,
            stereotype_score=0.02,
            refusal_prob=0.0,
            sentiment=0.3,
            group_proxy="gender:woman",
            intersection_key="gender:woman|race:black",
            scored_at=utcnow(),
        )
        snapshot = MetricSnapshot(
            group_proxy="gender:woman",
            intersection_key="gender:woman|race:black",
            metric_name="toxicity",
            mean=0.1,
            std=0.0,
            count=1,
            ci_low=None,
            ci_high=None,
            computed_at=utcnow(),
            alert_flag=False,
            low_confidence=True,
        )
        session.add_all([chat_log, scored_log, snapshot])
        await session.commit()

    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert payload["metadata"]["toxicity"]["definition"]


def test_rate_limiting_triggers_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module.settings, "RATE_LIMIT_RPM", 1)
    monkeypatch.setattr(main_module, "build_llm_client", lambda settings=None: DummyLLMClient())
    monkeypatch.setattr(main_module, "get_redis_connection", lambda: FakeRedis())
    monkeypatch.setattr(main_module, "enqueue_fairness_job", lambda log_entry: "job-1")
    with TestClient(main_module.app) as test_client:
        test_client.app.state.runtime.llm_client = DummyLLMClient()
        first = test_client.post("/chat", json={"message": "One"})
        second = test_client.post("/chat", json={"message": "Two"})
    assert first.status_code == 200
    assert second.status_code == 429
