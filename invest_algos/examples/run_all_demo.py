#!/usr/bin/env python3
"""Generate synthetic prices and run A/B/C scripts for smoke testing."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "examples" / "data"
OUT_DIR = ROOT / "demo_output"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)


def save_demo_prices(path: Path, n_days: int = 300, seed: int = 42) -> Path:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    assets = ["SPY", "QQQ", "IWM", "TLT", "IEF", "GLD", "DBC", "UUP"]
    n = len(assets)
    regime = np.zeros(n_days, dtype=int)
    for t in range(1, n_days):
        regime[t] = rng.integers(0, 3) if rng.random() < 0.02 else regime[t - 1]
    mu = np.array([
        [0.00035, 0.00045, 0.00040, 0.00010, 0.00008, 0.00015, 0.00012, 0.00002],
        [-0.00055, -0.00070, -0.00080, 0.00045, 0.00030, 0.00035, -0.00020, 0.00025],
        [0.00005, -0.00005, 0.00000, -0.00035, -0.00020, 0.00045, 0.00065, 0.00025],
    ])
    vols = np.array([
        [0.010, 0.012, 0.014, 0.009, 0.006, 0.010, 0.012, 0.005],
        [0.020, 0.024, 0.026, 0.014, 0.010, 0.016, 0.018, 0.008],
        [0.015, 0.017, 0.020, 0.013, 0.009, 0.017, 0.022, 0.007],
    ])
    corr = np.full((n, n), 0.20)
    np.fill_diagonal(corr, 1.0)
    for i in [0, 1, 2]:
        for j in [3, 4]:
            corr[i, j] = corr[j, i] = -0.25
    corr[5, 6] = corr[6, 5] = 0.30
    chol = np.linalg.cholesky(corr + np.eye(n) * 1e-6)
    rets = np.zeros((n_days, n))
    for t in range(n_days):
        s = regime[t]
        rets[t] = mu[s] + vols[s] * (rng.standard_normal(n) @ chol.T)
    prices = 100.0 * pd.DataFrame(1.0 + rets, index=dates, columns=assets).cumprod()
    prices.reset_index(names="Date").to_csv(path, index=False)
    return path


def run(cmd: list[str]) -> None:
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    print("done: " + Path(cmd[1]).name, flush=True)


def main() -> None:
    prices_path = save_demo_prices(DATA_DIR / "demo_prices.csv", n_days=300, seed=42)
    print(f"Demo prices saved: {prices_path}", flush=True)

    py = sys.executable
    run([
        py, str(ROOT / "algos" / "a_regime_hrp_hmv_cvt.py"),
        "--prices", str(prices_path),
        "--outdir", str(OUT_DIR / "a_regime_hrp_hmv_cvt"),
        "--lookback", "80",
        "--rebalance-days", "100",
        "--n-regimes", "2",
        "--target-vol", "0.10",
        "--max-weight", "0.25",
        "--cvar-lambda", "0.0",
    ])
    run([
        py, str(ROOT / "algos" / "b_meta_temporal_conformal_gate.py"),
        "--prices", str(prices_path),
        "--outdir", str(OUT_DIR / "b_meta_temporal_conformal_gate"),
        "--horizon", "5",
        "--alpha", "0.50",
        "--meta-threshold", "0.50",
        "--min-edge-bps", "0",
        "--max-weight", "0.15",
        "--min-train-days", "80",
        "--calibration-window", "40",
        "--retrain-step", "60",
    ])
    run([
        py, str(ROOT / "algos" / "c_decision_focused_multi_period_optimizer.py"),
        "--prices", str(prices_path),
        "--outdir", str(OUT_DIR / "c_decision_focused_mpo"),
        "--lookback", "80",
        "--rebalance-days", "100",
        "--horizon", "2",
        "--target-vol", "0.10",
        "--max-weight", "0.25",
        "--turnover-budget", "0.30",
        "--cvar-lambda", "0.0",
    ])
    summary = {}
    for name in ["a_regime_hrp_hmv_cvt", "b_meta_temporal_conformal_gate", "c_decision_focused_mpo"]:
        sp = OUT_DIR / name / "summary.json"
        summary[name] = json.loads(sp.read_text(encoding="utf-8"))
    (OUT_DIR / "demo_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDemo completed. Summary: {OUT_DIR / 'demo_summary.json'}", flush=True)


if __name__ == "__main__":
    main()
