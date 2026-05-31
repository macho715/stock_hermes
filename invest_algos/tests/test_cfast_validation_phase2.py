"""Tests for Phase 2 plan.md additions to run_cfast_validation.py.

Tests: evaluate_forward_month, regime_diagnostics, sleeve_cap_warnings.
"""
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algos.common import make_demo_prices  # noqa: E402


class TestEvaluateForwardMonth:
    """RED: forward-month gate must exist and enforce -2% return / -5% MDD thresholds."""

    def test_forward_month_gate_exists(self):
        from examples.run_cfast_validation import evaluate_forward_month
        assert callable(evaluate_forward_month)

    def test_passes_when_forward_return_and_mdd_above_thresholds(self):
        from examples.run_cfast_validation import evaluate_forward_month

        result = evaluate_forward_month(
            base_metrics={"ann_return": 0.12, "max_drawdown": -0.05},
            forward_metrics={"forward_return": 0.01, "forward_mdd": -0.02},
            cost_label="base",
        )
        assert result["forward_pass"] is True
        assert result["warnings"] == []

    def test_fails_when_forward_return_below_minus_2pct(self):
        from examples.run_cfast_validation import evaluate_forward_month

        result = evaluate_forward_month(
            base_metrics={"ann_return": 0.12, "max_drawdown": -0.05},
            forward_metrics={"forward_return": -0.03, "forward_mdd": -0.02},
            cost_label="base",
        )
        assert result["forward_pass"] is False
        assert any("forward_month_return_below_threshold" in w for w in result["warnings"])

    def test_fails_when_forward_mdd_below_minus_5pct(self):
        from examples.run_cfast_validation import evaluate_forward_month

        result = evaluate_forward_month(
            base_metrics={"ann_return": 0.12, "max_drawdown": -0.05},
            forward_metrics={"forward_return": 0.01, "forward_mdd": -0.06},
            cost_label="x2",
        )
        assert result["forward_pass"] is False
        assert any("forward_month_mdd_below_threshold" in w for w in result["warnings"])

    def test_warnings_include_cost_label(self):
        from examples.run_cfast_validation import evaluate_forward_month

        result = evaluate_forward_month(
            base_metrics={"ann_return": 0.12, "max_drawdown": -0.05},
            forward_metrics={"forward_return": -0.03, "forward_mdd": -0.06},
            cost_label="x2",
        )
        assert any("x2" in w for w in result["warnings"])


class TestRegimeDiagnostics:
    """RED: regime diagnostics must compute GLD/DBC momentum, relative strength, drawdown state."""

    def test_regime_diagnostics_exists(self):
        from examples.run_cfast_validation import compute_regime_diagnostics
        assert callable(compute_regime_diagnostics)

    def test_returns_gld_dbc_momentum_fields(self):
        from examples.run_cfast_validation import compute_regime_diagnostics

        prices = make_demo_prices(n_days=252, seed=42)
        result = compute_regime_diagnostics(prices)

        required = [
            "gld_1m_momentum",
            "gld_3m_momentum",
            "dbc_1m_momentum",
            "dbc_3m_momentum",
            "gld_dbc_relative_strength",
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_returns_equity_bond_drawdown_state(self):
        from examples.run_cfast_validation import compute_regime_diagnostics

        prices = make_demo_prices(n_days=252, seed=42)
        result = compute_regime_diagnostics(prices)

        required = [
            "equity_drawdown_state",
            "bond_drawdown_state",
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"
        assert result["equity_drawdown_state"] in ("normal", "mild", "severe")
        assert result["bond_drawdown_state"] in ("normal", "mild", "severe")

    def test_latest_risky_exposure_by_sleeve(self):
        from examples.run_cfast_validation import compute_regime_diagnostics

        prices = make_demo_prices(n_days=252, seed=42)
        result = compute_regime_diagnostics(prices)

        assert "latest_risky_exposure_by_sleeve" in result
        exposure = result["latest_risky_exposure_by_sleeve"]
        assert isinstance(exposure, dict)
        assert "metal" in exposure
        assert "commodity" in exposure


class TestSleeveCapWarnings:
    """RED: sleeve cap warnings must fire when GLD/DBC avg_weight > 20% and latest return < -5%."""

    def test_metal_sleeve_warning_fires(self):
        from examples.run_cfast_validation import check_sleeve_cap_warnings

        warnings = check_sleeve_cap_warnings(
            latest_weights=pd.DataFrame({
                "Asset": ["GLD", "DBC", "SPY", "__CASH__"],
                "Weight": [0.28, 0.05, 0.40, 0.27],
            }),
            latest_asset_returns=pd.Series({
                "GLD": -0.08,
                "DBC": 0.02,
                "SPY": 0.01,
            }),
        )
        assert "metal_sleeve_forward_loss" in warnings

    def test_commodity_sleeve_warning_fires(self):
        from examples.run_cfast_validation import check_sleeve_cap_warnings

        warnings = check_sleeve_cap_warnings(
            latest_weights=pd.DataFrame({
                "Asset": ["GLD", "DBC", "SPY", "__CASH__"],
                "Weight": [0.05, 0.28, 0.40, 0.27],
            }),
            latest_asset_returns=pd.Series({
                "GLD": 0.02,
                "DBC": -0.08,
                "SPY": 0.01,
            }),
        )
        assert "commodity_sleeve_forward_loss" in warnings

    def test_no_warning_when_weight_below_threshold(self):
        from examples.run_cfast_validation import check_sleeve_cap_warnings

        warnings = check_sleeve_cap_warnings(
            latest_weights=pd.DataFrame({
                "Asset": ["GLD", "DBC", "SPY", "__CASH__"],
                "Weight": [0.15, 0.15, 0.40, 0.30],
            }),
            latest_asset_returns=pd.Series({
                "GLD": -0.08,
                "DBC": -0.08,
                "SPY": 0.01,
            }),
        )
        assert "metal_sleeve_forward_loss" not in warnings
        assert "commodity_sleeve_forward_loss" not in warnings

    def test_no_warning_when_return_above_minus_5pct(self):
        from examples.run_cfast_validation import check_sleeve_cap_warnings

        warnings = check_sleeve_cap_warnings(
            latest_weights=pd.DataFrame({
                "Asset": ["GLD", "DBC", "SPY", "__CASH__"],
                "Weight": [0.28, 0.28, 0.20, 0.24],
            }),
            latest_asset_returns=pd.Series({
                "GLD": -0.03,
                "DBC": -0.03,
                "SPY": 0.01,
            }),
        )
        assert "metal_sleeve_forward_loss" not in warnings
        assert "commodity_sleeve_forward_loss" not in warnings


class TestCandidateProfileSelector:
    """--candidate flag must load ALL optimizer params from CANDIDATE_PROFILES,
    reproducing benchmark results without manual per-flag overrides."""

    def test_candidate_profiles_exist(self):
        from examples.run_cfast_validation import CANDIDATE_PROFILES, CANDIDATE_IDS
        assert len(CANDIDATE_PROFILES) == 5
        assert "vol_cap_relaxed" in CANDIDATE_PROFILES
        assert set(CANDIDATE_IDS) == set(CANDIDATE_PROFILES.keys())

    def test_apply_candidate_profile_overrides_all_optimizer_params(self):
        import argparse
        from examples.run_cfast_validation import (
            CANDIDATE_PROFILES,
            apply_candidate_profile,
            parse_args,
        )
        args = parse_args(["--prices", "dummy.csv"])
        assert args.target_vol == 0.10   # default baseline

        updated = apply_candidate_profile(args, "vol_cap_relaxed")
        profile = CANDIDATE_PROFILES["vol_cap_relaxed"]

        # Every key in the profile must be reflected on updated args
        for key, expected in profile.items():
            actual = getattr(updated, key)
            assert actual == expected, (
                f"param '{key}': expected {expected}, got {actual}"
            )

    def test_apply_candidate_profile_preserves_non_optimizer_args(self):
        from examples.run_cfast_validation import apply_candidate_profile, parse_args
        args = parse_args(["--prices", "mydata.csv", "--outdir", "my_outdir"])
        updated = apply_candidate_profile(args, "defensive_v2")
        # Non-optimizer args must not be overwritten
        assert updated.prices == "mydata.csv"
        assert updated.outdir == "my_outdir"

    def test_apply_candidate_profile_raises_on_unknown_candidate(self):
        import pytest
        from examples.run_cfast_validation import apply_candidate_profile, parse_args
        args = parse_args([])
        with pytest.raises(ValueError, match="Unknown candidate"):
            apply_candidate_profile(args, "nonexistent_profile")

    def test_candidate_flag_in_cli_integration(self, tmp_path):
        """Smoke: --candidate vol_cap_relaxed must run without error."""
        import json
        from examples.run_cfast_validation import main
        from algos.common import make_demo_prices

        prices = make_demo_prices(n_days=600, seed=42)
        prices_path = tmp_path / "prices.csv"
        prices.reset_index(names="Date").to_csv(prices_path, index=False)
        outdir = tmp_path / "cand_val"

        main([
            "--prices", str(prices_path),
            "--outdir", str(outdir),
            "--candidate", "vol_cap_relaxed",
            "--cost-bps-list", "5,10",
            "--splits", "2",
            "--gap", "1",
            "--test-size", "10",
            "--lookback", "80",
        ])

        summary = json.loads((outdir / "validation_summary.json").read_text(encoding="utf-8"))
        # Summary must exist and record the run (verdict is data-driven, not asserted)
        assert "policy_verdicts" in summary
        assert "forward_month_gate" in summary

    def test_benchmark_and_validation_share_same_profiles(self):
        """CANDIDATE_PROFILES in benchmark must be imported from validation (single source)."""
        from examples.run_cfast_validation import CANDIDATE_PROFILES as val_profiles
        from examples.run_cfast_upgrade_benchmark import CANDIDATE_PROFILES as bench_profiles
        assert val_profiles is bench_profiles, (
            "CANDIDATE_PROFILES in benchmark is not the same object as in validation. "
            "It must be imported from run_cfast_validation, not redefined."
        )


class TestValidationSummarySchema:
    """RED: validation_summary.json must include regime_diagnostics and sleeve warnings."""

    def test_validation_summary_has_regime_diagnostics(self, tmp_path):
        from examples.run_cfast_validation import main

        prices = make_demo_prices(n_days=600, seed=7)
        prices_path = tmp_path / "prices.csv"
        prices.reset_index(names="Date").to_csv(prices_path, index=False)
        outdir = tmp_path / "validation"

        main([
            "--prices", str(prices_path),
            "--outdir", str(outdir),
            "--cost-bps-list", "5,10",
            "--splits", "2",
            "--gap", "1",
            "--test-size", "10",
            "--lookback", "80",
        ])

        import json
        summary = json.loads((outdir / "validation_summary.json").read_text(encoding="utf-8"))
        assert "regime_diagnostics" in summary, "validation_summary missing regime_diagnostics"
        diag = summary["regime_diagnostics"]
        assert "gld_1m_momentum" in diag
        assert "equity_drawdown_state" in diag

    def test_validation_summary_has_sleeve_warnings(self, tmp_path):
        from examples.run_cfast_validation import main

        prices = make_demo_prices(n_days=600, seed=7)
        prices_path = tmp_path / "prices.csv"
        prices.reset_index(names="Date").to_csv(prices_path, index=False)
        outdir = tmp_path / "validation"

        main([
            "--prices", str(prices_path),
            "--outdir", str(outdir),
            "--cost-bps-list", "5,10",
            "--splits", "2",
            "--gap", "1",
            "--test-size", "10",
            "--lookback", "80",
        ])

        import json
        summary = json.loads((outdir / "validation_summary.json").read_text(encoding="utf-8"))
        assert "warnings" in summary
        assert "regime_diagnostics" in summary
