"""RQ worker jobs for scoring and persistence."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

import numpy as np
import structlog
from sqlalchemy import select

from backend.config import get_settings
from backend.database import get_session_maker
from backend.models import ChatLog, ScoredLog, utcnow
from backend.queue import enqueue_dead_letter, enqueue_scored_job
from backend.utils import hash_sensitive, sanitize_prompt

logger = structlog.get_logger(__name__)

REFUSAL_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bcannot\b",
        r"\bi['’]m unable\b",
        r"\bas an ai\b",
        r"\bi do not\b",
        r"\bi don't\b",
        r"\bi can't\b",
        r"\bi cannot\b",
    )
)

POSITIVE_WORDS = {"inclusive", "respectful", "helpful", "support", "fair", "neutral", "balanced", "kind"}
NEGATIVE_WORDS = {"hate", "idiot", "stupid", "inferior", "disgusting", "violent", "remove", "exclude", "barbaric", "lazy", "criminal"}
STEREOTYPE_MARKERS = {
    "all women",
    "all men",
    "boys are",
    "girls are",
    "black people",
    "white people",
    "asians are",
    "jews are",
    "muslims are",
    "elderly people",
    "disabled people",
}
PROXY_KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "gender": {
        "woman": ("woman", "women", "female", "girl", "girls", "she", "her", "nonbinary", "non-binary"),
        "man": ("man", "men", "male", "boy", "boys", "he", "him"),
        "nonbinary": ("nonbinary", "non-binary", "genderqueer", "gender fluid"),
    },
    "race": {
        "black": ("black", "african", "afro", "brown"),
        "white": ("white", "caucasian", "european"),
        "asian": ("asian", "east asian", "south asian", "indian", "chinese", "japanese", "korean"),
        "latino": ("latino", "latina", "hispanic", "latinx", "mexican", "puerto rican", "cuban"),
    },
    "age": {
        "elderly": ("elderly", "older", "senior", "old people", "retired"),
        "youth": ("youth", "young", "teen", "teenager", "child", "children", "kid", "kids"),
    },
    "ability": {
        "disabled": ("disabled", "disability", "wheelchair", "blind", "deaf", "autistic", "neurodivergent"),
    },
}


@lru_cache(maxsize=1)
def _load_detoxify_model() -> Any | None:
    try:  # pragma: no cover - model availability depends on runtime environment.
        from detoxify import Detoxify

        return Detoxify("original")
    except Exception as exc:  # pragma: no cover
        logger.warning("detoxify_model_unavailable", error_type=type(exc).__name__)
        return None


@lru_cache(maxsize=1)
def _load_zero_shot_classifier() -> Any | None:
    try:  # pragma: no cover - model availability depends on runtime environment.
        from transformers import pipeline

        return pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
    except Exception as exc:  # pragma: no cover
        logger.warning("zero_shot_classifier_unavailable", error_type=type(exc).__name__)
        return None


@lru_cache(maxsize=1)
def _load_sentiment_pipeline() -> Any | None:
    try:  # pragma: no cover - model availability depends on runtime environment.
        from transformers import pipeline

        return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", device=-1)
    except Exception as exc:  # pragma: no cover
        logger.warning("sentiment_pipeline_unavailable", error_type=type(exc).__name__)
        return None


@lru_cache(maxsize=1)
def _load_spacy_model() -> Any | None:
    try:  # pragma: no cover - optional dependency.
        import spacy

        return spacy.load("en_core_web_sm")
    except Exception as exc:  # pragma: no cover
        logger.info("spacy_model_unavailable", error_type=type(exc).__name__)
        return None


def _keyword_score(text: str, positive: Iterable[str], negative: Iterable[str]) -> float:
    lowered = text.lower()
    positive_hits = sum(1 for token in positive if token in lowered)
    negative_hits = sum(1 for token in negative if token in lowered)
    total_hits = positive_hits + negative_hits
    if total_hits == 0:
        return 0.0
    return float(np.clip(negative_hits / total_hits, 0.0, 1.0))


def _score_toxicity(text: str) -> tuple[float, float]:
    model = _load_detoxify_model()
    if model is not None:
        try:
            output = model.predict(text)
            toxicity = float(np.clip(float(output.get("toxicity", 0.0)), 0.0, 1.0))
            identity_attack = float(np.clip(float(output.get("identity_attack", toxicity)), 0.0, 1.0))
            return toxicity, identity_attack
        except Exception as exc:  # pragma: no cover
            logger.warning("detoxify_prediction_failed", error_type=type(exc).__name__)
    toxicity = _keyword_score(text, POSITIVE_WORDS, NEGATIVE_WORDS)
    identity_attack = min(1.0, toxicity * 0.9)
    return toxicity, identity_attack


def _score_stereotype(text: str) -> float:
    classifier = _load_zero_shot_classifier()
    labels = ["stereotypical", "biased against a group", "neutral", "inclusive"]
    if classifier is not None:
        try:
            result = classifier(text, labels)
            mapping = dict(zip(result["labels"], result["scores"], strict=False))
            biased_score = max(float(mapping.get("stereotypical", 0.0)), float(mapping.get("biased against a group", 0.0)))
            return float(np.clip(biased_score, 0.0, 1.0))
        except Exception as exc:  # pragma: no cover
            logger.warning("zero_shot_classification_failed", error_type=type(exc).__name__)
    lowered = text.lower()
    hits = sum(1 for marker in STEREOTYPE_MARKERS if marker in lowered)
    return float(np.clip(hits / max(len(STEREOTYPE_MARKERS), 1), 0.0, 1.0))


def _score_refusal(text: str) -> float:
    lowered = text.lower()
    hits = sum(1 for pattern in REFUSAL_PATTERNS if pattern.search(lowered))
    if hits == 0:
        return 0.0
    return float(np.clip(hits / 5.0, 0.0, 1.0))


def _score_sentiment(text: str) -> float:
    pipeline = _load_sentiment_pipeline()
    if pipeline is not None:
        try:
            result = pipeline(text[:512])[0]
            label = str(result.get("label", "")).upper()
            score = float(result.get("score", 0.0))
            if "POS" in label:
                return float(np.clip(score, 0.0, 1.0))
            if "NEG" in label:
                return float(np.clip(-score, -1.0, 0.0))
        except Exception as exc:  # pragma: no cover
            logger.warning("sentiment_scoring_failed", error_type=type(exc).__name__)
    lowered = text.lower()
    positive_hits = sum(1 for word in POSITIVE_WORDS if word in lowered)
    negative_hits = sum(1 for word in NEGATIVE_WORDS if word in lowered)
    denominator = positive_hits + negative_hits
    if denominator == 0:
        return 0.0
    return float(np.clip((positive_hits - negative_hits) / denominator, -1.0, 1.0))


def _extract_proxies(text: str) -> tuple[str, str]:
    lowered = text.lower()
    proxy_parts: dict[str, str] = {}
    for dimension, values in PROXY_KEYWORDS.items():
        for label, keywords in values.items():
            if any(keyword in lowered for keyword in keywords):
                proxy_parts[dimension] = label
                break

    if not proxy_parts:
        nlp = _load_spacy_model()
        if nlp is not None:
            try:
                doc = nlp(text[:2000])
                for ent in doc.ents:
                    candidate = ent.text.lower()
                    if any(keyword in candidate for keyword in PROXY_KEYWORDS["gender"]["woman"]):
                        proxy_parts.setdefault("gender", "woman")
                    elif any(keyword in candidate for keyword in PROXY_KEYWORDS["gender"]["man"]):
                        proxy_parts.setdefault("gender", "man")
                    elif any(keyword in candidate for keyword in PROXY_KEYWORDS["race"]["black"]):
                        proxy_parts.setdefault("race", "black")
                    elif any(keyword in candidate for keyword in PROXY_KEYWORDS["race"]["white"]):
                        proxy_parts.setdefault("race", "white")
            except Exception as exc:  # pragma: no cover
                logger.warning("spacy_proxy_extraction_failed", error_type=type(exc).__name__)

    if not proxy_parts:
        proxy_parts["unknown"] = "unknown"

    ordered_parts = [f"{dimension}:{label}" for dimension, label in sorted(proxy_parts.items())]
    intersection_key = "|".join(ordered_parts)
    group_proxy = ordered_parts[0]
    return group_proxy, intersection_key


def _normalize_text(log_entry: dict[str, Any]) -> tuple[str, str]:
    prompt = sanitize_prompt(str(log_entry.get("prompt", "")))
    response = sanitize_prompt(str(log_entry.get("response_text", "")))
    return prompt, response


def _dead_letter_payload(log_entry: dict[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        "log_id": log_entry.get("log_id"),
        "request_id": log_entry.get("request_id"),
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "timestamp": utcnow().isoformat(),
    }


def score_and_tag(log_entry: dict[str, Any]) -> dict[str, Any]:
    """Score a queued chat log and enqueue it for persistence."""

    settings = get_settings()
    try:
        prompt_text, response_text = _normalize_text(log_entry)
        scoring_text = response_text or prompt_text
        group_proxy_plain, intersection_plain = _extract_proxies(f"{prompt_text} {response_text}".strip())
        toxicity, identity_attack = _score_toxicity(scoring_text)
        stereotype_score = _score_stereotype(f"{prompt_text} {response_text}".strip())
        refusal_prob = _score_refusal(scoring_text)
        sentiment = _score_sentiment(scoring_text)
        user_id_hash = str(log_entry.get("user_id_hash") or hash_sensitive(str(log_entry.get("user_id", "anonymous"))))
        prompt_hash = str(log_entry.get("prompt_hash") or hash_sensitive(prompt_text))
        scored_entry = {
            "log_id": str(log_entry["log_id"]),
            "request_id": str(log_entry.get("request_id", "")),
            "user_id_hash": user_id_hash,
            "prompt_hash": prompt_hash,
            "response_text": response_text,
            "model": str(log_entry.get("model", settings.LLM_MODEL)),
            "status": "scored",
            "toxicity": toxicity,
            "identity_attack": identity_attack,
            "stereotype_score": stereotype_score,
            "refusal_prob": refusal_prob,
            "sentiment": sentiment,
            "group_proxy": group_proxy_plain,
            "intersection_key": intersection_plain,
            "scored_at": utcnow().isoformat(),
        }
        enqueue_scored_job(scored_entry)
        logger.info(
            "fairness_scored",
            log_id=scored_entry["log_id"],
            request_id=scored_entry["request_id"],
            toxicity=toxicity,
            stereotype_score=stereotype_score,
            refusal_prob=refusal_prob,
        )
        return scored_entry
    except Exception as exc:  # pragma: no cover - failure path exercised in worker failures
        payload = _dead_letter_payload(log_entry, exc)
        enqueue_dead_letter(payload)
        logger.exception("fairness_scoring_failed", log_id=log_entry.get("log_id"), error_type=type(exc).__name__)
        raise


async def _persist_scored_log_async(scored_entry: dict[str, Any]) -> str:
    session_maker = get_session_maker()
    async with session_maker() as session:
        log_id = str(scored_entry["log_id"])
        chat_log = await session.get(ChatLog, log_id)
        if chat_log is None:
            chat_log = ChatLog(
                id=log_id,
                user_id_hash=str(scored_entry["user_id_hash"]),
                prompt_hash=str(scored_entry["prompt_hash"]),
                response_text=str(scored_entry["response_text"]),
                timestamp=utcnow(),
                model=str(scored_entry["model"]),
                status=str(scored_entry.get("status", "scored")),
            )
            session.add(chat_log)
        else:
            chat_log.user_id_hash = str(scored_entry["user_id_hash"])
            chat_log.prompt_hash = str(scored_entry["prompt_hash"])
            chat_log.response_text = str(scored_entry["response_text"])
            chat_log.model = str(scored_entry["model"])
            chat_log.status = str(scored_entry.get("status", "scored"))

        scored_log = await session.scalar(select(ScoredLog).where(ScoredLog.log_id == log_id))
        if scored_log is None:
            scored_log = ScoredLog(
                log_id=log_id,
                toxicity=float(scored_entry.get("toxicity")) if scored_entry.get("toxicity") is not None else None,
                identity_attack=float(scored_entry.get("identity_attack")) if scored_entry.get("identity_attack") is not None else None,
                stereotype_score=float(scored_entry.get("stereotype_score")) if scored_entry.get("stereotype_score") is not None else None,
                refusal_prob=float(scored_entry.get("refusal_prob")) if scored_entry.get("refusal_prob") is not None else None,
                sentiment=float(scored_entry.get("sentiment")) if scored_entry.get("sentiment") is not None else None,
                group_proxy=str(scored_entry["group_proxy"]),
                intersection_key=str(scored_entry["intersection_key"]),
                scored_at=utcnow(),
            )
            session.add(scored_log)
        else:
            scored_log.toxicity = float(scored_entry.get("toxicity")) if scored_entry.get("toxicity") is not None else None
            scored_log.identity_attack = float(scored_entry.get("identity_attack")) if scored_entry.get("identity_attack") is not None else None
            scored_log.stereotype_score = float(scored_entry.get("stereotype_score")) if scored_entry.get("stereotype_score") is not None else None
            scored_log.refusal_prob = float(scored_entry.get("refusal_prob")) if scored_entry.get("refusal_prob") is not None else None
            scored_log.sentiment = float(scored_entry.get("sentiment")) if scored_entry.get("sentiment") is not None else None
            scored_log.group_proxy = str(scored_entry["group_proxy"])
            scored_log.intersection_key = str(scored_entry["intersection_key"])
            scored_log.scored_at = utcnow()

        await session.commit()
        return log_id


def persist_scored_log(scored_entry: dict[str, Any]) -> str:
    """Persist a scored log row in the audit database."""

    try:
        return asyncio.run(_persist_scored_log_async(scored_entry))
    except Exception as exc:  # pragma: no cover - failure path exercised in worker failures
        payload = _dead_letter_payload(scored_entry, exc)
        enqueue_dead_letter(payload)
        logger.exception("persist_scored_log_failed", log_id=scored_entry.get("log_id"), error_type=type(exc).__name__)
        raise


def store_dead_letter(payload: dict[str, Any]) -> dict[str, Any]:
    """Record a dead-letter payload. The RQ queue itself preserves the audit trail."""

    logger.error("dead_letter_recorded", **payload)
    return payload
