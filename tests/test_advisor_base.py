"""Tests for :mod:`stock_rtx4060.advisors.base`."""

from __future__ import annotations

import pytest

from stock_rtx4060.advisors.base import Advisor, AdvisoryOutput


def _build(**overrides):
    payload = dict(
        agent="news",
        ticker="AAPL",
        score=0.5,
        confidence=0.7,
        rationale="r",
        citations=["http://x"],
        prompt_hash="h",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.01,
    )
    payload.update(overrides)
    return AdvisoryOutput(**payload)


def test_advisory_output_is_frozen():
    out = _build()
    with pytest.raises((AttributeError, Exception)):
        out.score = 0.9  # type: ignore[misc]


def test_advisory_output_score_lower_bound():
    with pytest.raises(ValueError):
        _build(score=-1.5)


def test_advisory_output_score_upper_bound():
    with pytest.raises(ValueError):
        _build(score=1.5)


def test_advisory_output_score_boundaries_inclusive():
    assert _build(score=-1.0).score == -1.0
    assert _build(score=1.0).score == 1.0


def test_advisory_output_confidence_range():
    with pytest.raises(ValueError):
        _build(confidence=-0.1)
    with pytest.raises(ValueError):
        _build(confidence=1.1)


def test_advisory_output_token_counts_non_negative():
    with pytest.raises(ValueError):
        _build(tokens_in=-1)
    with pytest.raises(ValueError):
        _build(tokens_out=-1)


def test_advisory_output_cost_non_negative():
    with pytest.raises(ValueError):
        _build(cost_usd=-0.01)


def test_advisor_protocol_is_runtime_checkable():
    class _Probe:
        name = "x"

        async def analyze(self, ticker, context):  # pragma: no cover - shape only
            return _build()

    assert isinstance(_Probe(), Advisor)
