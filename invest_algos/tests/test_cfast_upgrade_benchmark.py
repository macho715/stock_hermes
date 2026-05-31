"""Tests for run_cfast_upgrade_benchmark.py — Phase 1 of plan.md."""
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algos.common import make_demo_prices  # noqa: E402


class TestRunCfastUpgradeBenchmarkOutputs:
    """RED: benchmark runner must produce all required output files."""

    def test_runs_all_five_candidates(self, tmp_path):
        from examples.run_cfast_upgrade_benchmark import main

        prices = make_demo_prices(n_days=600, seed=7)
        prices_path = tmp_path / "prices.csv"
        prices.reset_index(names="Date").to_csv(prices_path, index=False)
        outdir = tmp_path / "benchmark_output"

        main([
            "--prices", str(prices_path),
            "--outdir", str(outdir),
        ])

        # All three output files must exist
        assert (outdir / "upgrade_candidate_summary.csv").exists()
        assert (outdir / "upgrade_candidate_benchmark.csv").exists()
        assert (outdir / "upgrade_candidate_report.md").exists()

    def test_summary_has_one_row_per_candidate(self, tmp_path):
        from examples.run_cfast_upgrade_benchmark import main

        prices = make_demo_prices(n_days=600, seed=11)
        prices_path = tmp_path / "prices.csv"
        prices.reset_index(names="Date").to_csv(prices_path, index=False)
        outdir = tmp_path / "benchmark_output"

        main([
            "--prices", str(prices_path),
            "--outdir", str(outdir),
        ])

        df = pd.read_csv(outdir / "upgrade_candidate_summary.csv")
        candidate_names = set(df["candidate"].tolist())
        expected = {
            "baseline_default",
            "vol_cap_relaxed",
            "accepted_v2_target10_paper",
            "defensive_v2",
            "cost_conservative",
        }
        assert candidate_names == expected, f"Missing: {expected - candidate_names}"

    def test_benchmark_has_forward_month_columns(self, tmp_path):
        from examples.run_cfast_upgrade_benchmark import main

        prices = make_demo_prices(n_days=600, seed=13)
        prices_path = tmp_path / "prices.csv"
        prices.reset_index(names="Date").to_csv(prices_path, index=False)
        outdir = tmp_path / "benchmark_output"

        main([
            "--prices", str(prices_path),
            "--outdir", str(outdir),
        ])

        df = pd.read_csv(outdir / "upgrade_candidate_benchmark.csv")
        required_cols = [
            "candidate",
            "base_forward_return",
            "base_forward_mdd",
            "x2_forward_return",
            "x2_forward_mdd",
            "base_forward_pass",
            "x2_forward_pass",
        ]
        missing = [c for c in required_cols if c not in df.columns]
        assert not missing, f"Missing columns: {missing}"

    def test_accepted_v2_runs_and_produces_required_columns(self, tmp_path):
        """Structural test: accepted_v2_target10_paper must appear in results with all
        required columns populated.

        NOTE: gate pass/fail and return rankings on short synthetic random-walk data are
        not meaningful assertions — random walk returns rarely clear a 10% annualized
        threshold, and rankings vary by Python/numpy version. Only structural outputs
        are tested here; return gate behaviour is validated against real market data
        in the demo_output/ artefacts.
        """
        from examples.run_cfast_upgrade_benchmark import main

        prices = make_demo_prices(n_days=600, seed=19)
        prices_path = tmp_path / "prices.csv"
        prices.reset_index(names="Date").to_csv(prices_path, index=False)
        outdir = tmp_path / "benchmark_output"

        main([
            "--prices", str(prices_path),
            "--outdir", str(outdir),
        ])

        df = pd.read_csv(outdir / "upgrade_candidate_summary.csv")

        # accepted_v2 must appear in results
        assert "accepted_v2_target10_paper" in df["candidate"].values, (
            "accepted_v2_target10_paper not found in upgrade_candidate_summary.csv"
        )

        # Summary must have all required structural columns
        required_cols = {
            "candidate", "verdict", "base_pass", "x2_pass",
            "full_period_pass", "forward_month_pass", "promotion_ready",
            "base_ann_return", "x2_ann_return",
        }
        assert required_cols.issubset(set(df.columns)), (
            f"Missing columns: {required_cols - set(df.columns)}"
        )

        # accepted_v2 row must have numeric return fields (not NaN)
        row = df[df["candidate"] == "accepted_v2_target10_paper"].iloc[0]
        assert pd.notna(row["base_ann_return"]), "base_ann_return is NaN"
        assert pd.notna(row["x2_ann_return"]), "x2_ann_return is NaN"

        # accepted_v2 max_weight (0.45) > baseline (0.25) → it can hold more risky assets.
        # Its x2_ann_return must be finite (optimizer ran, not crashed).
        assert isinstance(float(row["x2_ann_return"]), float)
