from __future__ import annotations

import time

import numpy as np
from fastapi.testclient import TestClient

import backend.main as main_module


class FastLLMClient:
    async def generate(self, prompt: str, system: str) -> str:  # noqa: ARG002
        return "fast"

    async def health_check(self) -> bool:
        return True


class LoadRedis:
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


def test_burst_latency_p95_under_threshold(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "build_llm_client", lambda settings=None: FastLLMClient())
    monkeypatch.setattr(main_module, "get_redis_connection", lambda: LoadRedis())
    monkeypatch.setattr(main_module, "enqueue_fairness_job", lambda log_entry: "job-1")
    with TestClient(main_module.app) as client:
        client.app.state.runtime.llm_client = FastLLMClient()
        latencies: list[float] = []
        for index in range(50):
            start = time.perf_counter()
            response = client.post("/chat", json={"message": f"Request {index}"})
            latencies.append((time.perf_counter() - start) * 1000.0)
            assert response.status_code == 200
    p95 = float(np.percentile(latencies, 95))
    assert p95 < 800
