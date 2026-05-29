import pytest

from stock_rtx4060.backtest_honesty import (
    build_dsr_report,
    evaluate_backtest_honesty,
    load_dsr_report,
    merge_cpcv_dsr_evidence,
    summarize_honesty,
    write_dsr_report,
)


def test_backtest_honesty_legacy_api_still_exists():
    assert evaluate_backtest_honesty
    assert summarize_honesty


def test_backtest_honesty_passes_with_strong_evidence():
    summary = evaluate_backtest_honesty(
        oof_coverage=0.72,
        min_oof_coverage=0.45,
        sharpe=0.42,
        min_sharpe=-0.25,
        mdd_pct=12.0,
        max_mdd_pct=25.0,
        total_return_pct=4.5,
        transaction_cost_buffer_pct=0.5,
        cv_gap=20,
        horizon=20,
    )

    assert summary["status"] == "PASS"
    assert summary["passed"] == len(summary["checks"])
    assert all(check["reason"] for check in summary["checks"])


def test_backtest_honesty_flags_weak_oof_and_cost_buffer():
    summary = evaluate_backtest_honesty(
        oof_coverage=0.30,
        min_oof_coverage=0.45,
        sharpe=-0.10,
        min_sharpe=-0.25,
        mdd_pct=18.0,
        max_mdd_pct=25.0,
        total_return_pct=0.10,
        transaction_cost_buffer_pct=0.50,
        cv_gap=5,
        horizon=20,
    )

    assert summary["status"] == "AMBER"
    assert {check["name"]: check["status"] for check in summary["checks"]}["OOF_COVERAGE"] == "AMBER"
    assert {check["name"]: check["status"] for check in summary["checks"]}["TRANSACTION_COST_BUFFER"] == "AMBER"
    assert {check["name"]: check["status"] for check in summary["checks"]}["EMBARGO_VS_HORIZON"] == "AMBER"


def test_backtest_honesty_fails_on_excessive_drawdown():
    summary = evaluate_backtest_honesty(
        oof_coverage=0.72,
        min_oof_coverage=0.45,
        sharpe=0.30,
        min_sharpe=-0.25,
        mdd_pct=40.0,
        max_mdd_pct=25.0,
        total_return_pct=3.0,
        transaction_cost_buffer_pct=0.5,
        cv_gap=20,
        horizon=20,
    )

    assert summary["status"] == "FAIL"
    assert {check["name"]: check["status"] for check in summary["checks"]}["MAX_DRAWDOWN"] == "FAIL"


def test_backtest_honesty_adds_sizing_coverage_gate():
    summary = evaluate_backtest_honesty(
        oof_coverage=0.72,
        min_oof_coverage=0.45,
        sharpe=0.30,
        min_sharpe=-0.25,
        mdd_pct=12.0,
        max_mdd_pct=25.0,
        total_return_pct=3.0,
        transaction_cost_buffer_pct=0.5,
        cv_gap=20,
        horizon=20,
        sizing_coverage_result={
            "status": "ZERO",
            "empirical": 0.60,
            "claimed": 0.90,
            "n": 100,
            "screening_output_only": True,
        },
    )

    checks = {check["name"]: check["status"] for check in summary["checks"]}
    assert checks["SIZING_COVERAGE"] == "FAIL"
    assert summary["status"] == "FAIL"
    assert summary["sizing_coverage"]["status"] == "ZERO"


def test_summarize_honesty_keeps_worst_status_and_counts():
    summary = summarize_honesty(
        [
            {"status": "PASS", "checks": [{"status": "PASS"}]},
            {"status": "AMBER", "checks": [{"status": "AMBER"}]},
            {"status": "FAIL", "checks": [{"status": "FAIL"}]},
        ]
    )

    assert summary["status"] == "FAIL"
    assert summary["result_count"] == 3
    assert summary["passed"] == 1
    assert summary["amber"] == 1
    assert summary["failed"] == 1


def test_dsr_report_supports_direct_evidence_and_load(tmp_path):
    report = build_dsr_report(
        symbol="005930",
        deflated_sharpe=0.94,
        sharpe=1.2,
        psr_vs_zero=0.73,
        mc_drawdown_p95=0.18,
        path_count=5,
    )
    path = write_dsr_report(report, "005930", reports_root=tmp_path)
    loaded = load_dsr_report("005930", reports_root=tmp_path)

    assert path.exists()
    assert report["status"] == "PASS"
    assert loaded["deflated_sharpe"] == 0.94
    assert loaded["symbol"] == "005930"


def test_merge_cpcv_dsr_evidence_normalizes_reports():
    merged = merge_cpcv_dsr_evidence(
        cpcv_result={"pass_rate": 0.8, "status": "PASS"},
        pbo_report={"pbo": 0.08, "status": "PASS"},
        dsr_report={"deflated_sharpe": 0.94, "status": "PASS"},
    )

    assert merged["path_pass_rate"] == 0.8
    assert merged["pbo"] == 0.08
    assert merged["deflated_sharpe"] == 0.94
    assert merged["report_only"] is True


# ---------------------------------------------------------------------------
# E2 (Wave 3 Gap): summarize_honesty pbo aggregation — PR-P1
# ---------------------------------------------------------------------------


def test_summarize_honesty_includes_pbo_worst_case():
    """summarize_honesty returns worst (max) pbo and pbo_status."""
    items = [
        {"status": "PASS", "pbo": 0.10, "checks": []},
        {"status": "AMBER", "pbo": 0.35, "checks": []},
    ]
    result = summarize_honesty(items)
    assert result["pbo"] == pytest.approx(0.35)
    assert result["pbo_status"] == "AMBER"


def test_summarize_honesty_pbo_none_when_no_cpcv():
    """pbo=None and pbo_status=NO_DATA when items have no pbo key."""
    items = [{"status": "AMBER", "checks": []}]
    result = summarize_honesty(items)
    assert result["pbo"] is None
    assert result["pbo_status"] == "NO_DATA"


@pytest.mark.parametrize("pbos,expected_worst,expected_status", [
    ([0.05, 0.10], 0.10, "PASS"),
    ([0.10, 0.25], 0.25, "AMBER"),
    ([0.10, 0.60], 0.60, "RED"),
    ([], None, "NO_DATA"),
])
def test_summarize_honesty_pbo_thresholds(pbos, expected_worst, expected_status):
    items = [{"status": "PASS", "pbo": p, "checks": []} for p in pbos]
    result = summarize_honesty(items)
    if expected_worst is None:
        assert result["pbo"] is None
    else:
        assert result["pbo"] == pytest.approx(expected_worst)
    assert result["pbo_status"] == expected_status


def test_summarize_honesty_existing_fields_preserved():
    """Existing fields unchanged — additive only."""
    items = [{"status": "PASS", "pbo": 0.10, "checks": [{"status": "PASS"}]}]
    result = summarize_honesty(items)
    assert result["status"] == "PASS"
    assert result["result_count"] == 1
    assert result["passed"] == 1
