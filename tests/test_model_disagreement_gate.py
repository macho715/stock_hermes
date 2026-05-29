"""Model disagreement gate tests — TDD RED for P1 gap coverage.

Spec requirement (dashboard_bridge.py):
  spread = _model_score_spread(result)
  if spread is not None and spread >= 50.0:
      reasons.append("MODEL_DISAGREEMENT")

_score collection from two sources:
  - model_scores dict: coerce values (0-1 range → *100, else as-is)
  - top-level keys: main_score, main_model_score, backend_model_score,
    logreg_score, logistic_score, xgboost_score, xgb_score, rnn_score, lstm_score

Coverage gaps identified in review-report.md:
  - No test for spread exactly 50.0 (boundary case)
  - No test for spread exactly 49.9 (should NOT fire)
  - No test for only 1 score (should return None, no gate)
  - No test for model_scores dict with 0-1 range values
  - No test for top-level keys only (no model_scores dict)
  - No test for empty model_scores dict
  - No test for model_scores values that fail coercion
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


# -----------------------------------------------------------------------------
# MODEL_DISAGREEMENT gate tests
# -----------------------------------------------------------------------------


def test_model_disagreement_fires_at_spread_50():
    """RED test: spread == 50.0 → MODEL_DISAGREEMENT fires."""
    payload = _payload()
    result = payload["results"][0]
    result.update(
        {
            "model_scores": {
                "main": 0.90,  # → 90.0
                "rnn": 0.40,  # → 40.0
            }
        }
    )
    # spread = 90.0 - 40.0 = 50.0 (exactly threshold)

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" in row["blocking_reasons"]
    assert row["model_score_spread"] == 50.0


def test_model_disagreement_fires_above_spread_50():
    """RED test: spread > 50.0 → MODEL_DISAGREEMENT fires."""
    payload = _payload()
    result = payload["results"][0]
    result.update(
        {
            "model_scores": {
                "main": 99.0,
                "rnn": 30.0,
            }
        }
    )
    # spread = 99.0 - 30.0 = 69.0 (> 50.0)

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" in row["blocking_reasons"]
    assert row["model_score_spread"] == 69.0


def test_model_disagreement_does_not_fire_at_spread_49_9():
    """RED test: spread == 49.9 → MODEL_DISAGREEMENT must NOT fire."""
    payload = _payload()
    result = payload["results"][0]
    result.update(
        {
            "model_scores": {
                "main": 80.0,
                "rnn": 30.1,
            }
        }
    )
    # spread = 80.0 - 30.1 = 49.9 (< 50.0, so no gate)

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" not in row.get("blocking_reasons", [])
    assert row["model_score_spread"] == 49.9


def test_model_disagreement_does_not_fire_with_single_score():
    """RED test: only 1 score → model_score_spread returns None → no gate."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"model_scores": {"main": 75.0}})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" not in row.get("blocking_reasons", [])
    assert row["model_score_spread"] is None


def test_model_disagreement_does_not_fire_with_no_scores():
    """RED test: no model scores at all → no gate."""
    payload = _payload()
    # No model_scores key, no top-level score keys

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" not in row.get("blocking_reasons", [])
    assert row["model_score_spread"] is None


def test_model_disagreement_with_01_range_values_coerced():
    """RED test: model_scores dict with 0-1 range values → coerced to 0-100."""
    payload = _payload()
    result = payload["results"][0]
    result.update(
        {
            "model_scores": {
                "main": 0.55,  # → 55.0
                "rnn": 0.05,  # → 5.0
                "lstm": 0.95,  # → 95.0
            }
        }
    )
    # spread = 95.0 - 5.0 = 90.0 (> 50.0)

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" in row["blocking_reasons"]
    assert row["model_score_spread"] == 90.0


def test_model_disagreement_with_top_level_keys_only():
    """RED test: top-level score keys (no model_scores dict) → works."""
    payload = _payload()
    result = payload["results"][0]
    result.update(
        {
            "main_score": 95.0,
            "logreg_score": 10.0,
        }
    )
    # spread = 95.0 - 10.0 = 85.0 (> 50.0)

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" in row["blocking_reasons"]
    assert row["model_score_spread"] == 85.0


def test_model_disagreement_does_not_fire_empty_model_scores_dict():
    """RED test: model_scores = {} → no scores collected → no gate."""
    payload = _payload()
    result = payload["results"][0]
    result.update({"model_scores": {}})

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" not in row.get("blocking_reasons", [])
    assert row["model_score_spread"] is None


def test_model_disagreement_with_mixed_sources():
    """RED test: model_scores dict + top-level keys both contribute."""
    payload = _payload()
    result = payload["results"][0]
    result.update(
        {
            "model_scores": {
                "main": 0.80,  # → 80.0
                "rnn": 0.30,  # → 30.0
            },
            "logreg_score": 90.0,
        }
    )
    # All scores: 80.0, 30.0, 90.0 → spread = 90.0 - 30.0 = 60.0 (> 50.0)

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" in row["blocking_reasons"]
    assert row["model_score_spread"] == 60.0


def test_model_disagreement_with_non_numeric_scores_filtered():
    """RED test: non-numeric model_scores values are filtered out."""
    payload = _payload()
    result = payload["results"][0]
    result.update(
        {
            "model_scores": {
                "main": 0.90,  # → 90.0
                "rnn": "N/A",  # filtered
                "lstm": None,  # filtered
            }
        }
    )
    # Only main=90.0 passes → only 1 score → no spread → no gate

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" not in row.get("blocking_reasons", [])
    assert row["model_score_spread"] is None


def test_model_disagreement_with_xgb_score_key():
    """RED test: xgb_score top-level key contributes to spread."""
    payload = _payload()
    result = payload["results"][0]
    result.update(
        {
            "main_score": 20.0,
            "xgb_score": 80.0,
        }
    )
    # spread = 80.0 - 20.0 = 60.0 (> 50.0)

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" in row["blocking_reasons"]
    assert row["model_score_spread"] == 60.0


def test_model_disagreement_boundary_49_99_does_not_fire():
    """RED test: spread = 49.99 (just below threshold) → no gate."""
    payload = _payload()
    result = payload["results"][0]
    result.update(
        {
            "model_scores": {
                "main": 70.0,
                "rnn": 20.01,
            }
        }
    )
    # spread = 70.0 - 20.01 = 49.99 (< 50.0)

    row = build_dashboard_snapshot(payload)["results"][0]

    assert "MODEL_DISAGREEMENT" not in row.get("blocking_reasons", [])
    assert row["model_score_spread"] == 49.99
