from stock_rtx4060.backtest_honesty import evaluate_backtest_honesty, summarize_honesty


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
