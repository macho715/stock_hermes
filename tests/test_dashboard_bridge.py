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
    assert snapshot["results"][0]["ticker"] == "SYNTH-A"
    assert snapshot["results"][0]["score"] == 73.5
    assert snapshot["results"][0]["probability"] == 0.54
    assert snapshot["results"][0]["screening_output_only"] is True


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
