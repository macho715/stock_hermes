"""Measure Quant1901 signal IC / IR on real OHLCV data.

Uses Spearman rank correlation (robust for binary signals) instead of Pearson,
which can return NaN when signal variance is near-zero or returns are degenerate.

Usage:
    PYTHONPATH=src python scripts/measure_quant1901_ic.py --ticker 005930.KS --period 2y
    PYTHONPATH=src python scripts/measure_quant1901_ic.py --universe "005930.KS,000660.KS,035420.KS"

Output:
    Per-ticker IC / IR summary + factor_zoo registration recommendation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Path setup — works from repo root
_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT / "src"), str(_ROOT / "quant1901_executable_bundle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from quant1901_executor import StrategyConfig, build_signal_frame  # noqa: E402
from stock_rtx4060.data_providers import load_ohlcv_with_provider  # noqa: E402


def _spearman_ic(signal: pd.Series, forward_ret: pd.Series) -> float:
    """Spearman rank IC — robust for binary/sparse signals.

    Returns NaN if fewer than 30 valid observations or signal has zero variance.
    """
    df = pd.DataFrame({"s": signal, "r": forward_ret}).dropna()
    if len(df) < 30:
        return float("nan")
    if df["s"].std() < 1e-9 or df["r"].std() < 1e-9:
        return float("nan")
    return float(df["s"].rank(pct=True).corr(df["r"].rank(pct=True)))


def _pearson_ic(signal: pd.Series, forward_ret: pd.Series) -> float:
    """Pearson IC — included for comparison; may be NaN for binary signals."""
    df = pd.DataFrame({"s": signal, "r": forward_ret}).dropna()
    if len(df) < 30 or df["s"].std() < 1e-9 or df["r"].std() < 1e-9:
        return float("nan")
    return float(df["s"].corr(df["r"]))


def _ir(ic_series: list[float]) -> float:
    """Information Ratio = mean(IC) / std(IC) across periods."""
    arr = [v for v in ic_series if not np.isnan(v)]
    if len(arr) < 5:
        return float("nan")
    mu, sd = np.mean(arr), np.std(arr, ddof=1)
    return float(mu / sd) if sd > 1e-9 else float("nan")


def measure_ticker(ticker: str, period: str, horizon: int = 1) -> dict:
    """Compute IC statistics for a single ticker."""
    print(f"\n{'=' * 55}")
    print(f"  Ticker: {ticker}  |  Period: {period}  |  Horizon: h={horizon}")
    print(f"{'=' * 55}")

    try:
        r = load_ohlcv_with_provider(ticker, period, command="ic-measure")
        df = r.frame.copy()
        print(f"  Source:  {r.source}  |  Rows: {len(df)}")
    except Exception as exc:
        print(f"  ⚠ LOAD FAILED: {exc}")
        return {"ticker": ticker, "status": "LOAD_FAILED", "error": str(exc)}

    try:
        frame = build_signal_frame(df, StrategyConfig())
    except Exception as exc:
        print(f"  ⚠ BUILD_SIGNAL FAILED: {exc}")
        return {"ticker": ticker, "status": "SIGNAL_FAILED", "error": str(exc)}

    signal = frame["raw_signal"].astype(float)
    # Use frame["Close"] (same DatetimeIndex as signal) not df["Close"]
    # (df may have RangeIndex if Date is a column, causing alignment failure).
    forward_ret_h1 = frame["Close"].pct_change(horizon).shift(-horizon)

    # Rolling monthly IC (21-day windows, step 5)
    monthly_ic: list[float] = []
    n = len(signal)
    for start in range(0, n - 21, 5):
        end = start + 21
        w_sig = signal.iloc[start:end]
        w_ret = forward_ret_h1.iloc[start:end]
        monthly_ic.append(_spearman_ic(w_sig, w_ret))

    ic_spearman = _spearman_ic(signal, forward_ret_h1)
    ic_pearson = _pearson_ic(signal, forward_ret_h1)
    ir_val = _ir(monthly_ic)

    signal_active_pct = float((signal == 1.0).mean() * 100)
    n_transitions = int((signal.diff().abs() > 0).sum())

    print(f"  Signal active:    {signal_active_pct:.1f}% of bars")
    print(f"  Transitions:      {n_transitions}")
    print(f"  IC Spearman (h={horizon}): {ic_spearman:+.4f}" + ("  ⚠ NaN" if np.isnan(ic_spearman) else ""))
    print(f"  IC Pearson  (h={horizon}): {ic_pearson:+.4f}" + ("  ⚠ NaN" if np.isnan(ic_pearson) else ""))
    print(f"  IR (rolling):     {ir_val:+.4f}" + ("  ⚠ NaN" if np.isnan(ir_val) else ""))

    # Recommendation
    FACTOR_ZOO_IC_THRESHOLD = 0.02
    if np.isnan(ic_spearman):
        rec = "INCONCLUSIVE — check data length or signal variance"
        symbol = "⚠"
    elif ic_spearman > FACTOR_ZOO_IC_THRESHOLD:
        rec = f"IC {ic_spearman:.4f} > {FACTOR_ZOO_IC_THRESHOLD} → consider factor_zoo registration"
        symbol = "✓"
    else:
        rec = f"IC {ic_spearman:.4f} ≤ {FACTOR_ZOO_IC_THRESHOLD} → hold off on factor_zoo (marginal)"
        symbol = "⚠"

    print(f"\n  {symbol} {rec}")

    return {
        "ticker": ticker,
        "status": "OK",
        "rows": len(df),
        "source": r.source,
        "signal_active_pct": round(signal_active_pct, 1),
        "n_transitions": n_transitions,
        "ic_spearman": round(ic_spearman, 4) if not np.isnan(ic_spearman) else None,
        "ic_pearson": round(ic_pearson, 4) if not np.isnan(ic_pearson) else None,
        "ir_rolling": round(ir_val, 4) if not np.isnan(ir_val) else None,
        "recommendation": rec,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Quant1901 signal IC/IR measurement")
    ap.add_argument("--ticker", help="single ticker (e.g. 005930.KS)")
    ap.add_argument("--universe", help="comma-separated tickers")
    ap.add_argument("--period", default="2y", help="lookback period (default: 2y)")
    ap.add_argument("--horizon", type=int, default=1, help="forward return horizon in days")
    args = ap.parse_args()

    if args.universe:
        tickers = [t.strip().upper() for t in args.universe.split(",") if t.strip()]
    elif args.ticker:
        tickers = [args.ticker.strip().upper()]
    else:
        tickers = ["005930.KS", "000660.KS", "035420.KS"]
        print(f"No ticker specified — running default universe: {tickers}")

    results = [measure_ticker(t, args.period, args.horizon) for t in tickers]

    print(f"\n{'=' * 55}")
    print("  SUMMARY")
    print(f"{'=' * 55}")
    ok = [r for r in results if r.get("status") == "OK" and r.get("ic_spearman") is not None]
    if ok:
        avg_ic = np.mean([r["ic_spearman"] for r in ok])
        print(f"  Tickers measured:  {len(ok)} / {len(tickers)}")
        print(f"  Mean Spearman IC:  {avg_ic:+.4f}")
        if avg_ic > 0.02:
            print("  → Recommend factor_zoo registration (IC > 0.02 threshold)")
        else:
            print("  → Hold off on factor_zoo (marginal IC)")
    else:
        print("  No valid IC measurements obtained.")


if __name__ == "__main__":
    main()
