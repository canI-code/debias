"""Utility helpers for privacy, statistics, and safe fallbacks."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Any, Tuple

import numpy as np

from backend.config import get_settings

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?:(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}(?!\d))")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_WHITESPACE_RE = re.compile(r"\s+")


def hash_sensitive(value: str) -> str:
    """Hash sensitive data with SHA-256 and a server-side salt."""

    settings = get_settings()
    digest = hashlib.sha256()
    digest.update(settings.SALT.encode("utf-8"))
    digest.update(b":")
    digest.update(value.encode("utf-8"))
    return digest.hexdigest()


def sanitize_prompt(text: str) -> str:
    """Strip common PII patterns before logging or scoring."""

    sanitized = _EMAIL_RE.sub("[EMAIL]", text)
    sanitized = _PHONE_RE.sub("[PHONE]", sanitized)
    sanitized = _SSN_RE.sub("[SSN]", sanitized)
    sanitized = _CREDIT_CARD_RE.sub("[CARD]", sanitized)
    sanitized = _WHITESPACE_RE.sub(" ", sanitized)
    return sanitized.strip()


def bootstrap_ci(values: Sequence[float], n_boot: int = 1000, ci: float = 0.95) -> Tuple[float, float]:
    """Compute a bootstrap confidence interval for the mean.

    Returns (nan, nan) when the sample is too small to support a stable estimate.
    """

    cleaned = np.asarray(
        [value for value in values if value is not None and not math.isnan(float(value))],
        dtype=float,
    )
    if cleaned.size < 2:
        return float("nan"), float("nan")

    rng = np.random.default_rng()
    means = np.empty(n_boot, dtype=float)
    for index in range(n_boot):
        sample = rng.choice(cleaned, size=cleaned.size, replace=True)
        means[index] = float(np.mean(sample))

    tail = (1.0 - ci) / 2.0
    low = float(np.quantile(means, tail))
    high = float(np.quantile(means, 1.0 - tail))
    return low, high


def check_disparity(row_a: dict[str, Any], row_b: dict[str, Any], threshold: float) -> bool:
    """Flag disparity when confidence intervals do not overlap or gaps exceed threshold."""

    mean_a = float(row_a.get("mean", float("nan")))
    mean_b = float(row_b.get("mean", float("nan")))
    ci_low_a = row_a.get("ci_low")
    ci_high_a = row_a.get("ci_high")
    ci_low_b = row_b.get("ci_low")
    ci_high_b = row_b.get("ci_high")

    if any(value is None or math.isnan(float(value)) for value in (mean_a, mean_b)):
        return False

    gap = abs(mean_a - mean_b)
    if gap > threshold:
        return True

    if all(value is not None and not math.isnan(float(value)) for value in (ci_low_a, ci_high_a, ci_low_b, ci_high_b)):
        if float(ci_high_a) < float(ci_low_b) or float(ci_high_b) < float(ci_low_a):
            return True

    return False


def generate_safe_fallback() -> str:
    """Return a safe response when the upstream model fails."""

    return (
        "I am unable to answer that reliably right now. "
        "Please try again in a moment, or rephrase the request."
    )
