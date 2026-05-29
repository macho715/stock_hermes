from __future__ import annotations

import json

import pytest

from stock_rtx4060.dashboard_bridge import (
    DashboardBridgeError,
    build_dashboard_snapshot,
    export_dashboard_public_assets,
    write_dashboard_snapshot,
)


def _recommendation_payload() -> dict:
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
                "profit_factor": 1.2,
                "avg_dollar_volume_20d": 10000000.0,
                "volume_ratio_20d": 1.1,
                "market_regime_score": 55.0,
                "return_20d_pct": 1.3,
                "return_60d_pct": 4.5,
                "drawdown_252d_pct": -8.0,
                "confirmations_passed": 6,
                "confirmations_total": 9,
                "validations": [{"name": "AUTOMATION_BOUNDARY", "status": "PASS", "evidence": "screening_output_only"}],
                "backtest_honesty": {
                    "status": "PASS",
                    "checks": [{"name": "OOF_COVERAGE", "status": "PASS", "reason": "coverage=88.00%"}],
                },
                "reasons": ["manual approval required"],
                "generated_at_utc": "2026-05-03T00:00:00+00:00",
            }
        ],
    }


def test_build_dashboard_snapshot_preserves_report_only_contract():
    snapshot = build_dashboard_snapshot(_recommendation_payload(), source_json_path="reports/in/recommendations.json")

    assert snapshot["schema_version"] == "dashboard_snapshot.v1"
    assert snapshot["mode"] == "report_only"
    assert snapshot["audit_log_path"] == "reports/dashboard_bridge_smoke/audit_log.jsonl"
    assert snapshot["source_recommendation_json"] == "reports/in/recommendations.json"
    assert snapshot["config"]["data_provider"] == "synthetic"
    assert "provider_config" not in snapshot["config"]
    assert snapshot["provider_summary"]["status"] == "PASS"
    assert snapshot["provider_summary"]["providers_used"] == ["synthetic"]
    assert snapshot["backtest_honesty_summary"]["status"] == "PASS"
    assert snapshot["results"][0]["ticker"] == "SYNTH-A"
    assert snapshot["results"][0]["score"] == 73.5
    assert snapshot["results"][0]["raw_score"] == 73.5
    assert snapshot["results"][0]["investment_readiness_status"] == "READY_FOR_MANUAL_REVIEW"
    assert snapshot["results"][0]["investment_readiness_score"] == 73.5
    assert snapshot["results"][0]["new_capital_allowed"] is True
    assert snapshot["results"][0]["paper_trading_only"] is False
    assert snapshot["results"][0]["dashboard_warning"] is False
    assert snapshot["results"][0]["probability"] == 0.54
    assert snapshot["results"][0]["screening_output_only"] is True
    assert snapshot["results"][0]["backtest_honesty"]["status"] == "PASS"


def test_build_dashboard_snapshot_exports_sizing_fields_additively():
    payload = _recommendation_payload()
    payload["results"][0]["raw_score"] = 88.0
    payload["results"][0]["recommendation_rank_score"] = 44.0
    payload["results"][0]["size_multiplier"] = 0.5
    payload["results"][0]["sizing_strategy_used"] = "global"
    payload["results"][0]["sizing_coverage_status"] = "PASS"

    snapshot = build_dashboard_snapshot(payload)
    row = snapshot["results"][0]

    assert row["score"] == 44.0
    assert row["raw_score"] == 88.0
    assert row["size_multiplier"] == 0.5
    assert row["sizing_strategy_used"] == "global"
    assert row["sizing_coverage_status"] == "PASS"


def test_write_dashboard_snapshot_creates_file(tmp_path):
    source = tmp_path / "recommendations_algo_v2_20260503_000000.json"
    output = tmp_path / "dashboard_snapshot.json"
    source.write_text(json.dumps(_recommendation_payload(), ensure_ascii=False), encoding="utf-8")

    path = write_dashboard_snapshot(source, output)

    assert path == output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["result_count"] == 1
    assert payload["results"][0]["verdict"] == "AMBER_REVIEW_ONLY"


def test_export_dashboard_public_assets_copies_snapshot_audit_and_approval(tmp_path, monkeypatch):
    source = tmp_path / "reports" / "ops_v1" / "recommendations" / "recommendations_algo_v2_20260503_000000.json"
    output = source.with_name("dashboard_snapshot.json")
    audit = source.parent / "audit_log.jsonl"
    approval = source.parent.parent / "approval_journal_template.csv"
    public_dir = tmp_path / "public"
    source.parent.mkdir(parents=True)
    payload = _recommendation_payload()
    payload["audit_log_path"] = str(audit)
    source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    audit.write_text('{"event_type":"provider_attempt","status":"SUCCESS"}\n', encoding="utf-8")
    approval.write_text("ticker,manual_action,manual_approval_required,broker_order_execution\nSYNTH-A,REVIEW_PENDING,True,False\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    snapshot_path = write_dashboard_snapshot(source, output)
    exported = export_dashboard_public_assets(source, snapshot_path, public_dir)

    assert (public_dir / "dashboard_snapshot.json").exists()
    assert (public_dir / "audit_log.jsonl").read_text(encoding="utf-8").count("SUCCESS") == 1
    assert (public_dir / "approval_journal_template.csv").read_text(encoding="utf-8").startswith("ticker")
    assert exported["dashboard_snapshot"].endswith("dashboard_snapshot.json")
    assert exported["audit_log"].endswith("audit_log.jsonl")
    assert exported["approval_journal"].endswith("approval_journal_template.csv")


def test_dashboard_snapshot_rejects_missing_required_result_field():
    payload = _recommendation_payload()
    del payload["results"][0]["recommendation_rank_score"]

    with pytest.raises(DashboardBridgeError, match="recommendation_rank_score"):
        build_dashboard_snapshot(payload)


def test_dashboard_snapshot_rejects_non_report_only_result():
    payload = _recommendation_payload()
    payload["results"][0]["screening_output_only"] = False

    with pytest.raises(DashboardBridgeError, match="screening_output_only=true"):
        build_dashboard_snapshot(payload)


def test_dashboard_snapshot_accepts_older_payload_without_provider_summary():
    payload = _recommendation_payload()
    del payload["provider_summary"]
    del payload["backtest_honesty_summary"]
    del payload["results"][0]["backtest_honesty"]

    snapshot = build_dashboard_snapshot(payload)

    assert snapshot["provider_summary"] is None
    assert snapshot["backtest_honesty_summary"] is None
    assert snapshot["results"][0]["backtest_honesty"] is None
    assert snapshot["results"][0]["investment_readiness_status"] == "HARD_FAIL"
    assert snapshot["results"][0]["new_capital_allowed"] is False


def test_dashboard_snapshot_caps_readiness_and_blocks_live_queue_for_amber_gate_failure():
    payload = _recommendation_payload()
    result = payload["results"][0]
    result["recommendation_rank_score"] = 88.81
    result["model_accuracy"] = 0.433
    result["model_auc"] = 0.4814
    result["alpha_pct"] = -44.62
    result["completed_trades"] = 4

    snapshot = build_dashboard_snapshot(payload)
    row = snapshot["results"][0]

    assert row["score"] == 88.81
    assert row["raw_score"] == 88.81
    assert row["dashboard_status"] == "AMBER_WATCHLIST"
    assert row["investment_readiness_status"] == "AMBER_WATCHLIST"
    assert row["investment_readiness_score"] == 44.0
    assert row["live_queue_action"] == "HARD_BLOCK"
    assert row["research_queue_action"] == "AMBER_WATCHLIST"
    assert row["live_investable"] is False
    assert row["new_capital_allowed"] is False
    assert row["paper_trading_only"] is True
    assert row["ready_for_manual_review"] is False
    assert row["dashboard_warning"] is True
    assert row["dashboard_warning_message"].startswith("AMBER WATCHLIST")
    assert "Accuracy 43.30% < 50.00%" in row["blocking_reasons"]
    assert "AUC 0.4814 < 0.50" in row["blocking_reasons"]
    assert "Alpha -44.62% < 0.00%" in row["blocking_reasons"]
    assert "Completed trades 4 < 50" in row["blocking_reasons"]


def test_dashboard_snapshot_blocks_live_queue_when_backtest_honesty_is_amber():
    payload = _recommendation_payload()
    payload["results"][0]["backtest_honesty"]["status"] = "AMBER"

    row = build_dashboard_snapshot(payload)["results"][0]

    assert row["investment_readiness_status"] == "AMBER_WATCHLIST"
    assert row["new_capital_allowed"] is False
    assert row["paper_trading_only"] is True
    assert "Backtest honesty AMBER != PASS" in row["blocking_reasons"]


# ---------------------------------------------------------------------------
# E2 (Wave 3 Gap — PR-P2): per-candidate backtest_honesty_summary with pbo
# ---------------------------------------------------------------------------


def test_dashboard_candidate_has_pbo_summary_when_cpcv_provided():
    """Per-candidate backtest_honesty_summary.pbo_status is present when pbo in backtest_honesty."""
    payload = _recommendation_payload()
    payload["results"][0]["backtest_honesty"]["pbo"] = 0.18
    payload["results"][0]["backtest_honesty"]["pbo_status"] = "PASS"

    candidate = build_dashboard_snapshot(payload)["results"][0]

    assert "backtest_honesty_summary" in candidate
    assert candidate["backtest_honesty_summary"]["pbo_status"] == "PASS"
    assert abs(candidate["backtest_honesty_summary"]["pbo"] - 0.18) < 1e-9


def test_dashboard_candidate_pbo_summary_none_without_pbo():
    """backtest_honesty_summary is None when backtest_honesty has no pbo_status."""
    payload = _recommendation_payload()
    # backtest_honesty has no pbo or pbo_status key

    candidate = build_dashboard_snapshot(payload)["results"][0]

    assert candidate.get("backtest_honesty_summary") is None


def test_dashboard_candidate_backtest_honesty_key_preserved():
    """Original backtest_honesty key is preserved (additive change)."""
    payload = _recommendation_payload()
    payload["results"][0]["backtest_honesty"]["pbo"] = 0.10
    payload["results"][0]["backtest_honesty"]["pbo_status"] = "PASS"

    candidate = build_dashboard_snapshot(payload)["results"][0]

    assert "backtest_honesty" in candidate
    assert candidate["backtest_honesty"]["status"] == "PASS"
