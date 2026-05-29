"""Tests for SPRT promotion gate — Wave 4 BEST-1."""

from __future__ import annotations

import pytest

from flows.research_weekly import _sprt_promotion_decision


# ---------------------------------------------------------------------------
# Basic boundary behaviour
# ---------------------------------------------------------------------------

def test_sprt_continue_on_first_week():
    """n_weeks < 4 always returns CONTINUE."""
    result = _sprt_promotion_decision(0.30, 0.35, n_weeks=2)
    assert result["status"] == "CONTINUE"
    assert "n_weeks < 4" in result.get("reason", "")


def test_sprt_promote_when_large_improvement():
    """Very large improvement → PROMOTE."""
    result = _sprt_promotion_decision(
        new_oos_brier=0.10,    # much better
        prod_oos_brier=0.40,   # old model was bad
        n_weeks=52,
    )
    assert result["status"] == "PROMOTE"
    assert result["z_stat"] > 0


def test_sprt_stop_when_no_improvement():
    """Candidate is worse than production → STOP."""
    result = _sprt_promotion_decision(
        new_oos_brier=0.45,    # worse
        prod_oos_brier=0.30,   # prod is better
        n_weeks=52,
    )
    assert result["status"] == "STOP"
    assert result["z_stat"] < 0


def test_sprt_continue_in_ambiguous_zone():
    """Tiny, noisy improvement → CONTINUE (more data needed)."""
    result = _sprt_promotion_decision(
        new_oos_brier=0.299,   # barely better
        prod_oos_brier=0.300,
        n_weeks=4,
    )
    assert result["status"] == "CONTINUE"


# ---------------------------------------------------------------------------
# Return schema
# ---------------------------------------------------------------------------

def test_sprt_result_has_required_keys():
    result = _sprt_promotion_decision(0.25, 0.30, n_weeks=10)
    required = {"status", "z_stat", "n_weeks", "sprt_enabled", "alpha", "beta", "delta"}
    assert required.issubset(result.keys())


def test_sprt_z_stat_is_float():
    result = _sprt_promotion_decision(0.25, 0.30, n_weeks=10)
    assert isinstance(result["z_stat"], float)


def test_sprt_n_weeks_preserved():
    result = _sprt_promotion_decision(0.25, 0.30, n_weeks=13)
    assert result["n_weeks"] == 13


# ---------------------------------------------------------------------------
# Legacy fallback path
# ---------------------------------------------------------------------------

def test_sprt_disabled_uses_legacy_threshold():
    """sprt_enabled=False → reverts to 5% relative-delta check."""
    # 10% improvement > 5% threshold → PROMOTE
    result = _sprt_promotion_decision(0.27, 0.30, n_weeks=4, sprt_enabled=False)
    assert result["status"] == "PROMOTE"
    assert result["sprt_enabled"] is False


def test_sprt_disabled_stop_below_threshold():
    # 1% improvement < 5% threshold → STOP
    result = _sprt_promotion_decision(0.297, 0.30, n_weeks=4, sprt_enabled=False)
    assert result["status"] == "STOP"
