from __future__ import annotations

import math

import numpy as np

from backend.utils import bootstrap_ci, check_disparity, hash_sensitive, sanitize_prompt


def test_hash_sensitive_is_deterministic() -> None:
    first = hash_sensitive("abc@example.com")
    second = hash_sensitive("abc@example.com")
    assert first == second
    assert len(first) == 64


def test_sanitize_prompt_removes_pii() -> None:
    text = "Email me at jane@example.com or call 555-123-4567. SSN 123-45-6789."
    sanitized = sanitize_prompt(text)
    assert "jane@example.com" not in sanitized
    assert "555-123-4567" not in sanitized
    assert "123-45-6789" not in sanitized
    assert "[EMAIL]" in sanitized
    assert "[PHONE]" in sanitized
    assert "[SSN]" in sanitized


def test_bootstrap_ci_tracks_mean_for_simple_distribution() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    low, high = bootstrap_ci(values, n_boot=500, ci=0.95)
    assert low < np.mean(values) < high
    assert not math.isnan(low)
    assert not math.isnan(high)


def test_bootstrap_ci_handles_tiny_samples() -> None:
    low, high = bootstrap_ci([1.0], n_boot=100, ci=0.95)
    assert math.isnan(low)
    assert math.isnan(high)


def test_check_disparity_threshold_logic() -> None:
    row_a = {"mean": 0.1, "ci_low": 0.05, "ci_high": 0.15}
    row_b = {"mean": 0.5, "ci_low": 0.45, "ci_high": 0.55}
    assert check_disparity(row_a, row_b, threshold=0.2) is True
    assert check_disparity(row_a, {"mean": 0.12, "ci_low": 0.11, "ci_high": 0.13}, threshold=0.2) is False
