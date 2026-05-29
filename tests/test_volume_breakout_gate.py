"""Volume breakout gate tests — TDD RED for P0.2 gap coverage.

Spec requirement (P0.2):
  if volume_today >= avg_volume_20d * 3.0 and close >= bb_upper:
      volume_breakout = True

The gate logic in dashboard_bridge.py:
  if _is_true(result.get("volume_breakout")) and "EOD_FINAL_BAR_NOT_LOCKED" in reasons:
      reasons.append("VOLUME_BREAKOUT_REQUIRES_FINAL_BAR")

Coverage gaps identified in review-report.md:
  - No test for `volume_breakout=True` WITHOUT `EOD_FINAL_BAR_NOT_LOCKED`
    (VOLUME_BREAKOUT_REQUIRES_FINAL_BAR should NOT fire in that case)
  - `CONTRARIAN_DISABLED_VOLUME_BREAKOUT` reason never emitted (separate spec gap)

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


def test_volume_breakout_true_without_eod_final_bar_locked_adds_gate():
    """RED 테스트: volume_breakout=True + EOD_FINAL_BAR_NOT_LOCKED → VOLUME_BREAKOUT_REQUIRES_FINAL_BAR."""
    payload = _payload()
    result = payload["results"][0]

    # Set final bar to CACHE (not locked) to trigger EOD_FINAL_BAR_NOT_LOCKED
    result.update(
        {
            "bar_type": "INTRADAY_CACHE",
            "source": "PYKRX:CACHE",
            "eod_confirmed": False,
            "source_evidence_lock": False,
            "after_market_close": True,
            "volume_breakout": True,
        }
    )

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "VOLUME_BREAKOUT_REQUIRES_FINAL_BAR" in row["blocking_reasons"]


def test_volume_breakout_true_with_final_bar_locked_does_not_add_gate():
    """RED 테스트: volume_breakout=True + EOD_FINAL_BAR_LOCKED → 게이트不许发动."""
    payload = _payload()
    result = payload["results"][0]

    # Final bar IS locked — no EOD_FINAL_BAR_NOT_LOCKED reason
    result.update(
        {
            "bar_type": "EOD_FINAL",
            "source": "KRX_FINAL",
            "eod_confirmed": True,
            "source_evidence_lock": True,
            "after_market_close": True,
            "volume_breakout": True,
        }
    )

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "VOLUME_BREAKOUT_REQUIRES_FINAL_BAR" not in row.get("blocking_reasons", [])
    assert "EOD_FINAL_BAR_NOT_LOCKED" not in row.get("blocking_reasons", [])


def test_volume_breakout_false_does_not_add_gate():
    """RED 테스트: volume_breakout=False → 게이트不许发动 even if final bar not locked."""
    payload = _payload()
    result = payload["results"][0]

    result.update(
        {
            "bar_type": "INTRADAY_CACHE",
            "source": "PYKRX:CACHE",
            "eod_confirmed": False,
            "source_evidence_lock": False,
            "after_market_close": True,
            "volume_breakout": False,
        }
    )

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "VOLUME_BREAKOUT_REQUIRES_FINAL_BAR" not in row.get("blocking_reasons", [])
    assert "EOD_FINAL_BAR_NOT_LOCKED" in row.get("blocking_reasons", [])


def test_volume_breakout_string_false_still_false():
    """RED 테스트: 문자열 'false' volume_breakout은 falsy로 처리."""
    payload = _payload()
    result = payload["results"][0]

    result.update(
        {
            "bar_type": "INTRADAY_CACHE",
            "source": "PYKRX:CACHE",
            "eod_confirmed": False,
            "source_evidence_lock": False,
            "after_market_close": True,
            "volume_breakout": "false",
        }
    )

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "VOLUME_BREAKOUT_REQUIRES_FINAL_BAR" not in row.get("blocking_reasons", [])


def test_volume_breakout_string_true_with_final_bar_locked_no_gate():
    """RED 테스트: 문자열 'true' volume_breakout + final bar locked → 게이트不许发动."""
    payload = _payload()
    result = payload["results"][0]

    result.update(
        {
            "bar_type": "EOD_FINAL",
            "source": "KRX_FINAL",
            "eod_confirmed": True,
            "source_evidence_lock": True,
            "after_market_close": True,
            "volume_breakout": "true",
        }
    )

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "VOLUME_BREAKOUT_REQUIRES_FINAL_BAR" not in row.get("blocking_reasons", [])