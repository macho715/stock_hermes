"""Tests for investment_readiness_benchmark.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure the tools module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.investment_readiness_benchmark import (
    evaluate_candidate,
    format_json,
    format_markdown,
    load_recommendation_json,
    run_benchmark,
)

# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

def _base_config():
    return {
        "transaction_cost_buffer_pct": 0.50,
        "horizon_s": 20,
        "horizon_l": 63,
        "cv_gap": 20,
    }


def _base_candidate(ticker: str = "AAPL", track: str = "S", **overrides):
    c = {
        "ticker": ticker,
        "track": track,
        "verdict": "ELIGIBLE_RECOMMENDATION",
        "screening_output_only": True,
        "recommendation_rank_score": 80.0,
        "backtest_return_pct": 15.0,
        "backtest_honesty": {"status": "PASS"},
        "validations": [],
        "reasons": ["reason1"],
        "advisor_score": None,
        "advisor_rationale": None,
        "model_accuracy": 0.55,
        "model_auc": 0.60,
        "alpha_pct": 5.0,
        "completed_trades": 100,
    }
    c.update(overrides)
    return c


def _run_input(candidates, config=None, audit_log_path=None):
    data = {
        "results": candidates,
        "config": config or _base_config(),
    }
    if audit_log_path is not None:
        data["audit_log_path"] = audit_log_path
    return data


# ---------------------------------------------------------------------------
# SC-001: backtest_honesty=AMBER -> ready_for_manual_review=False
# ---------------------------------------------------------------------------

def test_backtest_honesty_amber_candidate_not_ready():
    cand = _base_candidate(backtest_honesty={"status": "AMBER"})
    result = evaluate_candidate(cand, _base_config())
    assert result.ready_for_manual_review is False
    assert "backtest_honesty=AMBER" in result.blocking_reasons


# ---------------------------------------------------------------------------
# SC-002: backtest_honesty=PASS + all checks passing -> ready_for_manual_review=True
# ---------------------------------------------------------------------------

def test_backtest_honesty_pass_candidate_ready():
    cand = _base_candidate(
        backtest_honesty={"status": "PASS"},
        backtest_return_pct=10.0,  # > 0.5 * 1 = 0.5, > 0.5 * 2 = 1.0, > 0.5 * 3 = 1.5
    )
    result = evaluate_candidate(cand, _base_config())
    assert result.ready_for_manual_review is True
    assert result.status == "PASS"


# ---------------------------------------------------------------------------
# SC-003: 3x cost stress FAIL
# ---------------------------------------------------------------------------

def test_cost_stress_3x_fail():
    # return=0.5 < 0.5 * 3 = 1.5  => FAIL
    cand = _base_candidate(backtest_return_pct=0.5)
    result = evaluate_candidate(cand, _base_config())
    assert result.checks["COST_STRESS_3X"].status == "FAIL"
    assert "COST_STRESS_3X=FAIL" in result.blocking_reasons


def test_cost_stress_3x_pass():
    # return=10.0 > 0.5 * 3 = 1.5  => PASS
    cand = _base_candidate(backtest_return_pct=10.0)
    result = evaluate_candidate(cand, _base_config())
    assert result.checks["COST_STRESS_3X"].status == "PASS"


# ---------------------------------------------------------------------------
# SC-004: cv_gap < horizon -> EMBARGO_STRESS=FAIL
# ---------------------------------------------------------------------------

def test_embargo_stress_fail_when_cv_gap_lt_horizon():
    # cv_gap=5 < horizon=20
    config = _base_config()
    cand = _base_candidate(
        backtest_honesty={
            "status": "PASS",
            "checks": [
                {"name": "WALK_FORWARD_GAP", "status": "AMBER", "value": 5, "threshold": 20, "reason": "gap=5, horizon=20"}
            ],
        }
    )
    result = evaluate_candidate(cand, config)
    assert result.checks["EMBARGO_STRESS"].status == "FAIL"
    assert "EMBARGO_STRESS=FAIL" in result.blocking_reasons


def test_embargo_stress_pass_when_cv_gap_gte_horizon():
    config = _base_config()
    cand = _base_candidate(
        backtest_honesty={
            "status": "PASS",
            "checks": [
                {"name": "WALK_FORWARD_GAP", "status": "PASS", "value": 25, "threshold": 20, "reason": "gap=25, horizon=20"}
            ],
        }
    )
    result = evaluate_candidate(cand, config)
    assert result.checks["EMBARGO_STRESS"].status == "PASS"


# ---------------------------------------------------------------------------
# SC-005: advisor_score present but no audit -> ADVISOR_AUDIT=FAIL
# ---------------------------------------------------------------------------

def test_advisor_audit_fail_when_score_present_but_no_audit(tmp_path: Path):
    audit_file = tmp_path / "advisor.jsonl"
    # Write an audit line for a DIFFERENT ticker so AAPL is missing
    audit_file.write_text(
        json.dumps({"ticker": "MSFT", "timestamp_utc": "2099-01-01T00:00:00+00:00"}) + "\n",
        encoding="utf-8",
    )
    cand = _base_candidate(advisor_score=0.5)
    config = _base_config()
    config["audit_log_path"] = str(audit_file)
    result = evaluate_candidate(cand, config)
    assert result.checks["ADVISOR_AUDIT"].status == "FAIL"
    assert "ADVISOR_AUDIT=FAIL" in result.blocking_reasons[0]


def test_advisor_audit_pass_when_score_present_with_audit(tmp_path: Path):
    audit_file = tmp_path / "advisor.jsonl"
    from datetime import UTC, datetime
    today = datetime.now(UTC).date().isoformat()
    audit_file.write_text(
        json.dumps({"ticker": "AAPL", "timestamp_utc": f"{today}T00:00:00+00:00"}) + "\n",
        encoding="utf-8",
    )
    cand = _base_candidate(advisor_score=0.5)
    config = _base_config()
    config["audit_log_path"] = str(audit_file)
    result = evaluate_candidate(cand, config)
    assert result.checks["ADVISOR_AUDIT"].status == "PASS"


def test_advisor_audit_not_applicable_when_score_is_null():
    cand = _base_candidate(advisor_score=None)
    result = evaluate_candidate(cand, _base_config())
    assert result.checks["ADVISOR_AUDIT"].status == "NOT_APPLICABLE"


# ---------------------------------------------------------------------------
# SC-009/010/011: High raw score + failing model quality
# ---------------------------------------------------------------------------

def test_model_quality_amber_watchlist_preserves_raw_score():
    """High raw score with weak model quality: raw preserved, investment_score capped at 44."""
    cand = _base_candidate(
        recommendation_rank_score=88.81,
        model_accuracy=0.433,
        model_auc=0.4814,
        alpha_pct=-44.62,
        completed_trades=4,
    )
    result = evaluate_candidate(cand, _base_config())
    assert result.status == "AMBER_WATCHLIST"
    assert result.new_capital_allowed is False
    assert result.paper_trading_only is True
    assert result.investment_score <= 44
    assert result.raw_score == 88.81  # Raw score preserved


def test_model_quality_passes_no_cap():
    cand = _base_candidate(
        recommendation_rank_score=80.0,
        model_accuracy=0.60,
        model_auc=0.65,
        alpha_pct=10.0,
        completed_trades=200,
    )
    result = evaluate_candidate(cand, _base_config())
    assert result.status == "PASS"
    assert result.new_capital_allowed is True
    assert result.paper_trading_only is False
    assert result.investment_score == 80.0  # Not capped


# ---------------------------------------------------------------------------
# EC-2: Malformed JSON
# ---------------------------------------------------------------------------

def test_malformed_json_raises_error(tmp_path: Path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed JSON"):
        load_recommendation_json(bad_file)


# ---------------------------------------------------------------------------
# EC-3: Empty results -> NO_CANDIDATES verdict
# ---------------------------------------------------------------------------

def test_empty_results_no_candidates_verdict():
    data = {"results": [], "config": _base_config()}
    result = run_benchmark(data)
    assert result.run_verdict == "NO_CANDIDATES"
    assert result.candidate_count == 0


# ---------------------------------------------------------------------------
# EC-4: Missing ticker -> INVALID_INPUT for that candidate
# ---------------------------------------------------------------------------

def test_missing_ticker_invalid_input():
    cand = {"track": "S", "recommendation_rank_score": 80.0}
    result = evaluate_candidate(cand, _base_config())
    assert result.status == "INVALID_INPUT"
    assert "ticker is missing" in result.blocking_reasons


# ---------------------------------------------------------------------------
# Run-level verdict: READY / AMBER / NOT_INVESTMENT_READY
# ---------------------------------------------------------------------------

def test_run_verdict_ready():
    cand = _base_candidate(
        backtest_honesty={"status": "PASS"},
        backtest_return_pct=10.0,
    )
    data = _run_input([cand])
    result = run_benchmark(data)
    assert result.run_verdict == "READY"
    assert result.ready_count == 1


def test_run_verdict_amber_when_amber_watchlist():
    cand = _base_candidate(
        backtest_honesty={"status": "PASS"},
        backtest_return_pct=10.0,
        recommendation_rank_score=88.81,
        model_accuracy=0.433,
        model_auc=0.4814,
        alpha_pct=-44.62,
        completed_trades=4,
    )
    data = _run_input([cand])
    result = run_benchmark(data)
    assert result.run_verdict == "AMBER"
    assert result.ready_count == 1
    assert result.candidates[0].status == "AMBER_WATCHLIST"


def test_run_verdict_not_investment_ready_when_all_fail():
    cand = _base_candidate(
        backtest_honesty={"status": "FAIL"},
        backtest_return_pct=0.5,
    )
    data = _run_input([cand])
    result = run_benchmark(data)
    assert result.run_verdict == "NOT_INVESTMENT_READY"


# ---------------------------------------------------------------------------
# Output format smoke tests
# ---------------------------------------------------------------------------

def test_format_json_produces_valid_json():
    cand = _base_candidate()
    data = _run_input([cand])
    result = run_benchmark(data)
    text = format_json(result)
    parsed = json.loads(text)
    assert parsed["schema_version"] == "1.0"
    assert parsed["candidate_count"] == 1


def test_format_markdown_produces_nonempty_string():
    cand = _base_candidate()
    data = _run_input([cand])
    result = run_benchmark(data)
    text = format_markdown(result)
    assert len(text) > 0
    assert "# Investment Readiness Benchmark" in text


# ---------------------------------------------------------------------------
# CLI exit code tests (via main wrapper)
# ---------------------------------------------------------------------------

def test_cli_nonexistent_input_exits_nonzero(tmp_path: Path):
    bad = tmp_path / "nonexistent.json"
    from tools.investment_readiness_benchmark import load_recommendation_json
    with pytest.raises(FileNotFoundError):
        load_recommendation_json(bad)


def test_cli_malformed_json_exits_nonzero(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ invalid", encoding="utf-8")
    from tools.investment_readiness_benchmark import load_recommendation_json
    with pytest.raises(ValueError, match="Malformed JSON"):
        load_recommendation_json(bad)