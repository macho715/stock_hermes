"""Event shock gate tests — TDD RED for P1 gap coverage.

Spec requirement (dashboard_bridge.py):
  if _is_true(result.get("event_shock")) and signal == "SELL":
      reasons.append("EVENT_SHOCK_SIGNAL_CONFLICT")

Coverage gaps identified in review-report.md:
  - No test for event_shock=True + signal=BUY (should NOT fire)
  - No test for event_shock=False + signal=SELL (should NOT fire)
  - No test for string "true" / "false" values
  - No test for missing signal field
  - No test for event_shock=None

This file tests the gate as implemented (dashboard_bridge), not the producer.
"""

from __future__ import annotations

from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot


def _payload() -> dict:
    """Minimal recommendation payload with a SYNTH-A candidate."""
    return {
        "generated_at_utc": "2026-05-03T00:00:00+00:00",
        "config": {
            "universe": ["SYNTH-A"],
            "track": "BOTH",
            "period": "3y",
            "top_n": 1,
            "synthetic": True,
            "data_provider": "synthetic",
            "model_kind": "logistic",
            "xgb_device": "cpu",
            "cv_gap": 5,
            "provider_config": "config/secret-bearing-file.json",
        },
        "disclaimer": "screening_output_only; manual approval required; no broker order execution; not financial advice",
        "algorithm_patch": "v2",
        "audit_log_path": "reports/dashboard_bridge_smoke/audit_log.jsonl",
        "provider_summary": {
            "status": "PASS",
            "providers_used": ["synthetic"],
            "event_count": 1,
            "row_count_min": 760,
            "last_date_max": "2026-05-03",
            "freshness_days_max": 0,
            "fallbacks": [],
        },
        "backtest_honesty_summary": {
            "status": "PASS",
            "result_count": 1,
            "passed": 5,
            "amber": 0,
            "failed": 0,
        },
        "errors": [],
        "results": [
            {
                "ticker": "SYNTH-A",
                "track": "S",
                "verdict": "AMBER_REVIEW_ONLY",
                "recommendation_rank_score": 73.5,
                "candidate_label": "검토 대상",
                "screening_output_only": True,
                "latest_close": 101.0,
                "entry": 101.0,
                "stop": 96.96,
                "tp1": 106.05,
                "tp2": 111.1,
                "stop_pct": -0.04,
                "tp2_pct": 0.10,
                "risk_reward": 2.5,
                "risk_budget_pct": 0.0075,
                "max_position_pct": 0.20,
                "suggested_quantity": 18.0,
                "suggested_position_value": 1818.0,
                "direction_prob": 0.54,
                "expected_value_pct": 1.2,
                "model_accuracy": 0.51,
                "model_auc": 0.55,
                "oof_coverage": 0.88,
                "backtest_return_pct": 3.5,
                "alpha_pct": 1.4,
                "completed_trades": 72,
                "backtest_sharpe": 0.8,
                "backtest_sortino": 1.1,
                "backtest_mdd_pct": -4.2,
                "live_review_candidate": True,
                "confirmations_passed": 6,
                "confirmations_total": 9,
                "validations": [{"name": "AUTOMATION_BOUNDARY", "status": "PASS", "evidence": "screening_output_only"}],
                "bar_type": "EOD_FINAL",
                "source": "KRX_FINAL",
                "eod_confirmed": True,
                "after_market_close": True,
                "source_evidence_lock": True,
                "backtest_honesty": {"pbo": 0.2, "pbo_status": "PASS"},
            }
        ],
    }


def test_event_shock_true_signal_sell_fires_gate():
    """RED test: event_shock=True + signal=SELL → EVENT_SHOCK_SIGNAL_CONFLICT."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"signal": "SELL", "event_shock": True})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" in row["blocking_reasons"]


def test_event_shock_true_signal_buy_does_not_fire_gate():
    """RED test: event_shock=True + signal=BUY → EVENT_SHOCK_SIGNAL_CONFLICT must NOT fire."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"signal": "BUY", "event_shock": True})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" not in row.get("blocking_reasons", [])


def test_event_shock_false_signal_sell_does_not_fire_gate():
    """RED test: event_shock=False + signal=SELL → EVENT_SHOCK_SIGNAL_CONFLICT must NOT fire."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"signal": "SELL", "event_shock": False})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" not in row.get("blocking_reasons", [])


def test_event_shock_string_true_signal_sell_fires_gate():
    """RED test: event_shock="true" (string) + signal=SELL → EVENT_SHOCK_SIGNAL_CONFLICT."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"signal": "SELL", "event_shock": "true"})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" in row["blocking_reasons"]


def test_event_shock_string_true_signal_buy_does_not_fire():
    """RED test: event_shock="true" (string) + signal=BUY → must NOT fire."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"signal": "BUY", "event_shock": "true"})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" not in row.get("blocking_reasons", [])


def test_event_shock_string_false_signal_sell_does_not_fire():
    """RED test: event_shock="false" (string) + signal=SELL → must NOT fire."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"signal": "SELL", "event_shock": "false"})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" not in row.get("blocking_reasons", [])


def test_event_shock_none_signal_sell_does_not_fire():
    """RED test: event_shock=None + signal=SELL → must NOT fire."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"signal": "SELL", "event_shock": None})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" not in row.get("blocking_reasons", [])


def test_event_shock_missing_signal_sell_does_not_fire():
    """RED test: event_shock=True with no signal field → must NOT fire."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"event_shock": True})
    # Remove signal from result dict
    result.pop("signal", None)

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" not in row.get("blocking_reasons", [])


def test_event_shock_true_signal_hold_does_not_fire():
    """RED test: event_shock=True + signal=HOLD → must NOT fire (only SELL triggers)."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"signal": "HOLD", "event_shock": True})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" not in row.get("blocking_reasons", [])


def test_event_shock_string_yes_signal_sell_fires():
    """RED test: event_shock="YES" (string) + signal=SELL → EVENT_SHOCK_SIGNAL_CONFLICT."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"signal": "SELL", "event_shock": "YES"})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "EVENT_SHOCK_SIGNAL_CONFLICT" in row["blocking_reasons"]