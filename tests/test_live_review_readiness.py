from __future__ import annotations

import json

from stock_rtx4060.backtest.cpcv_diagnostics import build_cpcv_report, write_cpcv_report
from stock_rtx4060.backtest.pbo import build_pbo_report, write_pbo_report
from stock_rtx4060.backtest_honesty import build_dsr_report, write_dsr_report
from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot
from stock_rtx4060.readiness.classifier import classify_live_review
from stock_rtx4060.readiness.snapshots import build_readiness_snapshot, write_readiness_snapshot
from stock_rtx4060.reports.model_card import write_model_card


def _safety_flags():
    return {
        "screening_output_only": True,
        "manual_approval_required": True,
        "broker_order_execution": False,
        "new_capital_allowed": False,
    }


def test_live_review_classifier_blocks_until_forward_paper_gates_pass():
    decision = classify_live_review(
        ticker="005930",
        cpcv_pass_rate=0.80,
        pbo=0.08,
        deflated_sharpe=0.94,
        forward_paper_days=0,
        forward_paper_alpha=None,
        rule_violations=None,
        model_card_present=True,
        dashboard_safety_flags=_safety_flags(),
    )

    assert decision["status"] == "PAPER_PASS"
    assert decision["paper_pass"] is True
    assert decision["live_review_candidate"] is False
    assert "FORWARD_PAPER_DAYS" in decision["failed_gates"]
    assert "FORWARD_PAPER_ALPHA" in decision["failed_gates"]
    assert "RULE_VIOLATIONS" in decision["failed_gates"]


def test_live_review_classifier_promotes_only_when_all_gates_pass():
    decision = classify_live_review(
        ticker="005930",
        cpcv_pass_rate=0.80,
        pbo=0.08,
        deflated_sharpe=0.94,
        forward_paper_days=31,
        forward_paper_alpha=0.1,
        rule_violations=0,
        model_card_present=True,
        dashboard_safety_flags=_safety_flags(),
    )

    assert decision["status"] == "LIVE_REVIEW_CANDIDATE"
    assert decision["live_review_candidate"] is True
    assert decision["blocking_reasons"] == []


def test_live_review_report_writers_and_snapshot(tmp_path):
    cpcv_path = write_cpcv_report(
        tmp_path / "cpcv.json",
        ticker="005930",
        sharpe_paths=[1.0] * 20 + [-0.1] * 5,
    )
    pbo_path = write_pbo_report(
        tmp_path / "pbo.json",
        ticker="005930",
        sharpe_paths=[1.0] * 23 + [-0.1] * 2,
    )
    dsr_path = write_dsr_report(
        tmp_path / "dsr.json",
        ticker="005930",
        sharpe=1.0,
        n_trials=1,
        n_obs=252,
    )
    decision = classify_live_review(
        ticker="005930",
        cpcv_pass_rate=0.80,
        pbo=0.08,
        deflated_sharpe=0.94,
        forward_paper_days=0,
        forward_paper_alpha=None,
        rule_violations=None,
        model_card_present=True,
        dashboard_safety_flags=_safety_flags(),
    )
    card_path = write_model_card(
        tmp_path / "model_card.md",
        ticker="005930",
        gate_decision=decision,
        cpcv_report=json.loads(cpcv_path.read_text(encoding="utf-8")),
        pbo_report=json.loads(pbo_path.read_text(encoding="utf-8")),
        dsr_report=json.loads(dsr_path.read_text(encoding="utf-8")),
    )
    snapshot_path = write_readiness_snapshot(
        tmp_path / "snapshot.json",
        ticker="005930",
        cpcv_report=cpcv_path,
        pbo_report=pbo_path,
        dsr_report=dsr_path,
        paper_status={"equity_curve": [], "rule_violations_detail": []},
        model_card_path=card_path,
        dashboard_safety_flags=_safety_flags(),
    )

    cpcv = json.loads(cpcv_path.read_text(encoding="utf-8"))
    pbo = json.loads(pbo_path.read_text(encoding="utf-8"))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert cpcv["pass_rate"] == 0.80
    assert pbo["pbo"] == 0.08
    assert snapshot["decision"]["status"] == "PAPER_PASS"
    assert snapshot["decision"]["live_review_candidate"] is False
    assert "FORWARD_PAPER_DAYS" in snapshot["decision"]["failed_gates"]
    card_text = card_path.read_text(encoding="utf-8")
    assert "No broker order execution" in card_text
    assert "broker_order_execution: false" in card_text


def test_dashboard_snapshot_adds_live_review_fields():
    payload = {
        "disclaimer": "screening_output_only; manual approval required; no broker order execution; not financial advice",
        "provider_summary": {"status": "PASS"},
        "results": [
            {
                "ticker": "SYNTH-A",
                "track": "S",
                "verdict": "AMBER_REVIEW_ONLY",
                "recommendation_rank_score": 88.0,
                "screening_output_only": True,
                "direction_prob": 0.55,
                "expected_value_pct": 2.0,
                "entry": 100.0,
                "stop": 96.0,
                "tp2": 110.0,
                "risk_reward": 2.5,
                "validations": [],
                "model_accuracy": 0.51,
                "model_auc": 0.55,
                "alpha_pct": 1.0,
                "completed_trades": 60,
                "backtest_honesty": {"status": "PASS", "checks": []},
            }
        ],
    }

    row = build_dashboard_snapshot(payload)["results"][0]

    assert row["readiness_status"] == "READY_FOR_MANUAL_REVIEW"
    assert row["live_review_candidate"] is False
    assert row["safety_flags"]["broker_order_execution"] is False


def test_readiness_snapshot_accepts_dict_reports(tmp_path):
    card = tmp_path / "model_card.md"
    card.write_text("# card\n", encoding="utf-8")

    snapshot = build_readiness_snapshot(
        ticker="005930",
        cpcv_report=build_cpcv_report(ticker="005930", sharpe_paths=[1.0] * 20 + [-0.1] * 5),
        pbo_report=build_pbo_report(ticker="005930", sharpe_paths=[1.0] * 23 + [-0.1] * 2),
        dsr_report=build_dsr_report(ticker="005930", sharpe=1.0, n_trials=1, n_obs=252),
        paper_status={"equity_curve": [{"equity": 100.0}, {"equity": 101.0}], "rule_violations": 0},
        model_card_path=card,
        dashboard_safety_flags=_safety_flags(),
    )

    assert snapshot["evidence"]["model_card_present"] is True
    assert snapshot["decision"]["status"] == "PAPER_PASS"
