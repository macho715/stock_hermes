"""Backward-compatibility guard for AdvisoryOutput (AMH Memory — W4 FR-1).

All existing code creates AdvisoryOutput with the original 10 positional
fields only.  The two new optional fields (regime_label, logical_proposition)
must default to "" so that no existing call-site breaks.
"""
from __future__ import annotations

import pytest

from stock_rtx4060.advisors.base import AdvisoryOutput


def _base_output(**overrides) -> AdvisoryOutput:
    defaults = dict(
        agent="test_agent",
        ticker="AAPL",
        score=0.5,
        confidence=0.8,
        rationale="test rationale",
        citations=["http://example.com"],
        prompt_hash="abc123",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.001,
    )
    defaults.update(overrides)
    return AdvisoryOutput(**defaults)


def test_advisory_output_backward_compat_no_regime_fields():
    """Creating AdvisoryOutput with original 10 fields must succeed."""
    out = _base_output()
    assert out.regime_label == ""
    assert out.logical_proposition == ""


def test_advisory_output_regime_label_set():
    out = _base_output(regime_label="risk_off")
    assert out.regime_label == "risk_off"


def test_advisory_output_logical_proposition_set():
    out = _base_output(logical_proposition="IF VIX>25 THEN bearish WITH 0.7")
    assert out.logical_proposition == "IF VIX>25 THEN bearish WITH 0.7"


def test_advisory_output_score_bounds_still_enforced():
    with pytest.raises(ValueError, match="score"):
        _base_output(score=1.5)


def test_advisory_output_confidence_bounds_still_enforced():
    with pytest.raises(ValueError, match="confidence"):
        _base_output(confidence=1.1)


def test_advisory_output_is_frozen():
    out = _base_output()
    with pytest.raises((AttributeError, TypeError)):
        out.score = 0.9  # type: ignore[misc]
