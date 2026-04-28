from __future__ import annotations

from types import SimpleNamespace

import pytest

import backend.worker as worker_module


@pytest.mark.asyncio
async def test_score_and_tag_isolates_scorer_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "_load_detoxify_model", lambda: SimpleNamespace(predict=lambda text: (_ for _ in ()).throw(RuntimeError("bad detoxify"))))
    monkeypatch.setattr(worker_module, "_load_zero_shot_classifier", lambda: lambda text, labels: {"labels": labels, "scores": [0.9, 0.1, 0.05, 0.03]})
    monkeypatch.setattr(worker_module, "_load_sentiment_pipeline", lambda: None)
    monkeypatch.setattr(worker_module, "enqueue_scored_job", lambda scored_entry: "scored-job")
    entry = {
        "log_id": "log-1",
        "request_id": "req-1",
        "user_id": "user-1",
        "prompt": "Tell me about a woman engineer",
        "response_text": "The woman engineer is highly capable and inclusive.",
        "model": "gpt-4o-mini",
    }
    scored = worker_module.score_and_tag(entry)
    assert scored["log_id"] == "log-1"
    assert scored["group_proxy"]
    assert scored["intersection_key"]
    assert scored["toxicity"] >= 0.0
    assert scored["stereotype_score"] >= 0.0


@pytest.mark.asyncio
async def test_proxy_extraction_and_hashing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "_load_detoxify_model", lambda: None)
    monkeypatch.setattr(worker_module, "_load_zero_shot_classifier", lambda: None)
    monkeypatch.setattr(worker_module, "_load_sentiment_pipeline", lambda: None)
    monkeypatch.setattr(worker_module, "enqueue_scored_job", lambda scored_entry: "scored-job")
    scored = worker_module.score_and_tag(
        {
            "log_id": "log-2",
            "request_id": "req-2",
            "user_id": "user-2",
            "prompt": "A black woman asked for help.",
            "response_text": "A respectful answer.",
            "model": "gpt-4o-mini",
        }
    )
    assert scored["group_proxy"] != scored["intersection_key"]
    assert len(scored["user_id_hash"]) == 64
    assert len(scored["prompt_hash"]) == 64


def test_persist_scored_log_accepts_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, str]] = []

    async def fake_persist(scored_entry):  # noqa: ANN001
        calls.append(scored_entry)
        return scored_entry["log_id"]

    monkeypatch.setattr(worker_module, "_persist_scored_log_async", fake_persist)
    result = worker_module.persist_scored_log({"log_id": "x", "user_id_hash": "u", "prompt_hash": "p", "response_text": "r", "model": "m", "group_proxy": "g", "intersection_key": "i"})
    assert result == "x"
    assert calls
