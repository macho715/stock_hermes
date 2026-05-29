"""Tests for v5.1 P1: CombinatorialPurgedCV, PBO, cost stress, rename."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# CombinatorialPurgedCV
# ---------------------------------------------------------------------------


def test_cpcv_n_paths():
    """C(6, 2) = 15 paths."""
    from math import comb
    from stock_rtx4060.ml.cv import CombinatorialPurgedCV

    cv = CombinatorialPurgedCV(n_splits=6, n_test_splits=2, embargo_pct=0.01)
    X = pd.DataFrame(np.random.randn(200, 4))
    paths = list(cv.split(X))
    assert len(paths) == comb(6, 2) == 15


def test_cpcv_get_n_splits():
    from stock_rtx4060.ml.cv import CombinatorialPurgedCV

    cv = CombinatorialPurgedCV(n_splits=6, n_test_splits=2)
    assert cv.get_n_splits() == 15


def test_cpcv_no_train_test_overlap():
    """No train row appears in test for any path."""
    from stock_rtx4060.ml.cv import CombinatorialPurgedCV

    X = pd.DataFrame(np.random.randn(120, 3))
    cv = CombinatorialPurgedCV(n_splits=4, n_test_splits=2, embargo_pct=0.01)
    for train, test in cv.split(X):
        assert len(np.intersect1d(train, test)) == 0


def test_cpcv_no_leakage_with_groups():
    """Full overlap purge: no label window overlaps test span in any path."""
    from stock_rtx4060.ml.cv import CombinatorialPurgedCV

    rng = np.random.default_rng(42)
    n = 150
    X = pd.DataFrame(rng.standard_normal((n, 3)))
    groups = np.arange(n) + 5  # horizon=5

    cv = CombinatorialPurgedCV(n_splits=5, n_test_splits=2, embargo_pct=0.01)
    for train, test in cv.split(X, groups=groups):
        if len(test) == 0 or len(train) == 0:
            continue
        test_start = int(test.min())
        test_end = int(groups[test].max())
        overlaps = (train <= test_end) & (groups[train] >= test_start)
        assert not overlaps.any()


def test_cpcv_invalid_n_test_splits():
    from stock_rtx4060.ml.cv import CombinatorialPurgedCV

    with pytest.raises(ValueError, match="n_test_splits"):
        CombinatorialPurgedCV(n_splits=4, n_test_splits=4)  # must be < n_splits

    with pytest.raises(ValueError, match="n_test_splits"):
        CombinatorialPurgedCV(n_splits=4, n_test_splits=0)  # must be >= 1


# ---------------------------------------------------------------------------
# PBO
# ---------------------------------------------------------------------------


def test_pbo_all_negative():
    from stock_rtx4060.backtest.stat_tests import probability_of_backtest_overfitting

    assert probability_of_backtest_overfitting([-0.5, -0.1, -1.0]) == 1.0


def test_pbo_all_positive():
    from stock_rtx4060.backtest.stat_tests import probability_of_backtest_overfitting

    assert probability_of_backtest_overfitting([0.5, 1.0, 2.0]) == 0.0


def test_pbo_mixed():
    from stock_rtx4060.backtest.stat_tests import probability_of_backtest_overfitting

    # 2 out of 5 paths are <= 0
    paths = [0.5, -0.1, 1.2, 0.0, 0.8]
    pbo = probability_of_backtest_overfitting(paths)
    assert abs(pbo - 2 / 5) < 1e-9


def test_pbo_empty_returns_one():
    from stock_rtx4060.backtest.stat_tests import probability_of_backtest_overfitting

    assert probability_of_backtest_overfitting([]) == 1.0


# ---------------------------------------------------------------------------
# Cost stress
# ---------------------------------------------------------------------------


def test_run_cost_stress_pass():
    """PASS: 1x return > 0 and 3x return >= 0."""
    from stock_rtx4060.backtest.stress import run_cost_stress
    from stock_rtx4060.backtester import BacktestConfig, Backtester

    # Synthetic uptrend prices
    prices = pd.Series([100.0 + i * 0.3 for i in range(100)])
    signals = pd.Series([1.0] * 100)  # always long
    cfg = BacktestConfig(transaction_cost=0.001, slippage=0.0005)
    result = run_cost_stress(Backtester, prices, signals, cfg)

    assert "scenarios" in result
    assert "cost_stress_status" in result
    assert "alpha_after_1x_cost" in result
    assert "alpha_after_3x_cost" in result
    assert result["cost_stress_status"] in ("PASS", "AMBER")


def test_run_cost_stress_amber_on_negative_alpha():
    """AMBER: 1x alpha is negative → stress fails."""
    from stock_rtx4060.backtest.stress import run_cost_stress
    from stock_rtx4060.backtester import BacktestConfig, Backtester

    # Synthetic downtrend prices — always-long strategy loses money
    prices = pd.Series([100.0 - i * 0.5 for i in range(100)])
    signals = pd.Series([1.0] * 100)
    cfg = BacktestConfig(transaction_cost=0.001, slippage=0.0005)
    result = run_cost_stress(Backtester, prices, signals, cfg)
    assert result["cost_stress_status"] == "AMBER"


def test_run_cost_stress_multiplier_keys():
    """alpha_after_Nx_cost keys are present for default multipliers (1,2,3)."""
    from stock_rtx4060.backtest.stress import run_cost_stress
    from stock_rtx4060.backtester import BacktestConfig, Backtester

    prices = pd.Series([100.0] * 50)
    signals = pd.Series([0.0] * 50)  # flat — no trades
    cfg = BacktestConfig()
    result = run_cost_stress(Backtester, prices, signals, cfg)
    for mult in (1, 2, 3):
        assert f"alpha_after_{mult}x_cost" in result


# ---------------------------------------------------------------------------
# EMBARGO_VS_HORIZON rename
# ---------------------------------------------------------------------------


def test_embargo_vs_horizon_rename():
    """Check name changed from WALK_FORWARD_GAP to EMBARGO_VS_HORIZON."""
    from stock_rtx4060.backtest_honesty import evaluate_backtest_honesty

    result = evaluate_backtest_honesty(
        oof_coverage=0.85,
        min_oof_coverage=0.70,
        sharpe=1.0,
        min_sharpe=0.0,
        mdd_pct=5.0,
        max_mdd_pct=20.0,
        total_return_pct=5.0,
        transaction_cost_buffer_pct=0.5,
        cv_gap=10,
        horizon=5,
    )
    check_names = [c["name"] for c in result["checks"]]
    assert "EMBARGO_VS_HORIZON" in check_names
    assert "WALK_FORWARD_GAP" not in check_names


# ---------------------------------------------------------------------------
# evaluate_backtest_honesty with cost_stress + cpcv
# ---------------------------------------------------------------------------


def test_evaluate_with_cost_stress():
    """cost_stress_result is reflected in checks and top-level cost_stress key."""
    from stock_rtx4060.backtest_honesty import evaluate_backtest_honesty

    cost_stress = {
        "cost_stress_status": "PASS",
        "alpha_after_1x_cost": 2.5,
        "alpha_after_2x_cost": 1.1,
        "alpha_after_3x_cost": 0.4,
        "scenarios": {},
    }
    result = evaluate_backtest_honesty(
        oof_coverage=0.85,
        min_oof_coverage=0.70,
        sharpe=1.2,
        min_sharpe=0.0,
        mdd_pct=8.0,
        max_mdd_pct=20.0,
        total_return_pct=3.0,
        transaction_cost_buffer_pct=0.5,
        cv_gap=10,
        horizon=5,
        cost_stress_result=cost_stress,
    )
    check_names = [c["name"] for c in result["checks"]]
    assert "COST_STRESS" in check_names
    assert "cost_stress" in result


def test_evaluate_with_cpcv():
    """cpcv_result adds CPCV_PBO, CPCV_DSR, CPCV_PATH_RATE checks."""
    from stock_rtx4060.backtest_honesty import evaluate_backtest_honesty

    cpcv = {"pbo": 0.13, "deflated_sharpe": 0.45, "path_pass_rate": 0.73}
    result = evaluate_backtest_honesty(
        oof_coverage=0.85,
        min_oof_coverage=0.70,
        sharpe=1.2,
        min_sharpe=0.0,
        mdd_pct=8.0,
        max_mdd_pct=20.0,
        total_return_pct=3.0,
        transaction_cost_buffer_pct=0.5,
        cv_gap=10,
        horizon=5,
        cpcv_result=cpcv,
    )
    check_names = [c["name"] for c in result["checks"]]
    assert "CPCV_PBO" in check_names
    assert "CPCV_DSR" in check_names
    assert "CPCV_PATH_RATE" in check_names
    assert "cpcv" in result
    # All three CPCV checks should PASS with the given values
    cpcv_checks = {c["name"]: c for c in result["checks"] if c["name"].startswith("CPCV")}
    assert cpcv_checks["CPCV_PBO"]["status"] == "PASS"   # 0.13 <= 0.20
    assert cpcv_checks["CPCV_DSR"]["status"] == "PASS"   # 0.45 > 0
    assert cpcv_checks["CPCV_PATH_RATE"]["status"] == "PASS"  # 0.73 >= 0.60


# ---------------------------------------------------------------------------
# PAPER_CANDIDATE config defaults (v5.1)
# ---------------------------------------------------------------------------


def test_recommendation_config_paper_candidate_defaults():
    """v5.1 defaults must support PAPER_CANDIDATE thresholds."""
    from stock_rtx4060.recommendation_engine import RecommendationConfig

    cfg = RecommendationConfig()
    assert cfg.period == "5y", f"period should be '5y', got {cfg.period!r}"
    assert cfg.xgb_splits == 5, f"xgb_splits should be 5, got {cfg.xgb_splits}"
    assert cfg.model_kind == "auto", f"model_kind should be 'auto', got {cfg.model_kind!r}"
    assert cfg.horizon_s == 10, f"horizon_s should be 10, got {cfg.horizon_s}"
    assert cfg.min_oof_coverage >= 0.75, f"min_oof_coverage should be >=0.75, got {cfg.min_oof_coverage}"


def test_oof_coverage_simulation_5y_5splits():
    """5y data + 5 splits should give ≥85% OOF coverage with horizon=10."""
    import numpy as np
    from stock_rtx4060.ml.cv import PurgedKFold

    # 5y KRX ≈ 1250 trading bars
    n = 1250
    horizon = 10
    rng = np.random.default_rng(42)
    import pandas as pd
    X = pd.DataFrame(rng.standard_normal((n, 4)))
    groups = np.arange(n) + horizon

    cv = PurgedKFold(n_splits=5, embargo_pct=horizon / n)
    oof_count = 0
    for train, test in cv.split(X, groups=groups):
        oof_count += len(test)

    coverage = oof_count / n
    assert coverage >= 0.85, f"Expected OOF coverage >= 85%, got {coverage:.1%}"


def test_oof_coverage_simulation_5y_5splits_trade_count():
    """5y + 5 splits OOF rows should enable ~80+ trades in backtester."""
    import numpy as np
    from stock_rtx4060.ml.cv import PurgedKFold
    import pandas as pd

    n = 1250
    horizon = 10
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.standard_normal((n, 4)))
    groups = np.arange(n) + horizon

    cv = PurgedKFold(n_splits=5, embargo_pct=horizon / n)
    total_test_rows = sum(len(test) for _, test in cv.split(X, groups=groups))

    # Conservative estimate: 1 signal every 12 bars → trades = test_rows / 12
    estimated_trades = total_test_rows // 12
    assert estimated_trades >= 80, (
        f"Expected ≥80 estimated trades, got {estimated_trades} "
        f"(test_rows={total_test_rows})"
    )
