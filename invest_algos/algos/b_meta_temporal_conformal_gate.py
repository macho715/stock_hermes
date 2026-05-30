#!/usr/bin/env python3
"""
B. Meta-label + Temporal Conformal Gate

Reference implementation for signal reliability filtering:
1) build or load a primary directional signal,
2) train a meta-label model that estimates post-cost signal validity,
3) compute temporal conformal lower bounds for signed edge,
4) trade only when meta probability and conformal lower bound both pass,
5) emit signals, weights, orders, and backtest metrics.

Input options:
    A) --prices wide price CSV: Date + assets. Script builds momentum/volatility features.
    B) --panel long CSV: Date, Asset, primary_score, fwd_return or meta_label, feature columns.

Run:
    python algos/b_meta_temporal_conformal_gate.py --prices data/prices.csv --outdir output/b
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from algos.common import (  # noqa: E402
    EPS,
    annualized_metrics,
    apply_turnover_cap,
    cap_and_normalize,
    ensure_outdir,
    load_price_csv,
    realized_portfolio_return,
    returns_from_prices,
    transaction_cost,
    write_json,
)

CASH = "__CASH__"
POLICY_VERDICT = "REJECT_RETRAIN"
RESERVED_COLS = {
    "Date",
    "Asset",
    "primary_score",
    "fwd_return",
    "signed_realized_edge",
    "edge_hat",
    "meta_label",
    "cost_return",
    "volatility",
}


class ConstantProbabilityModel:
    """Fallback model when the training window has one class only."""

    def __init__(self, p: float):
        self.p = float(np.clip(p, 0.0, 1.0))

    def predict_proba(self, x):
        n = len(x)
        return np.c_[np.repeat(1.0 - self.p, n), np.repeat(self.p, n)]


@dataclass
class GateResult:
    signals: pd.DataFrame
    weights: pd.Series
    q_conformal: float
    coverage_proxy: float
    abstention_rate: float


def conformal_quantile(residuals: np.ndarray, alpha: float) -> float:
    residuals = np.asarray(residuals, dtype=float)
    residuals = residuals[np.isfinite(residuals)]
    if len(residuals) == 0:
        return float("inf")
    # Split conformal finite-sample quantile.
    q_level = min(1.0, math.ceil((len(residuals) + 1) * (1.0 - alpha)) / max(len(residuals), 1))
    return float(np.quantile(residuals, q_level, method="higher"))


def make_panel_from_prices(prices: pd.DataFrame, horizon: int, cost_bps: float) -> pd.DataFrame:
    """Build a long feature panel from wide prices.

    primary_score is a simple H-day expected return proxy based on rolling momentum.
    It is deliberately replaceable: in production, replace this column with the
    alpha model's forecast.
    """
    returns = returns_from_prices(prices)
    rows = []
    for asset in prices.columns:
        px = prices[asset].astype(float)
        r = returns[asset].reindex(prices.index).fillna(0.0)
        ret_1 = r
        ret_5 = px.pct_change(5, fill_method=None)
        ret_21 = px.pct_change(21, fill_method=None)
        ret_63 = px.pct_change(63, fill_method=None)
        vol_20 = r.rolling(20, min_periods=10).std(ddof=0) * math.sqrt(252)
        vol_60 = r.rolling(60, min_periods=20).std(ddof=0) * math.sqrt(252)
        ewm_mu = r.ewm(span=20, min_periods=10).mean()
        # Replaceable primary alpha proxy. For demo data, combine short/medium
        # momentum and EWMA drift so that the conformal gate has non-zero coverage.
        primary_score = (0.50 * ret_21 + 0.25 * ret_5 + 0.25 * ewm_mu * horizon).clip(-0.12, 0.12)
        fwd_return = px.shift(-horizon) / px - 1.0
        signed_edge = np.sign(primary_score) * fwd_return
        df = pd.DataFrame({
            "Date": prices.index,
            "Asset": asset,
            "ret_1": ret_1.values,
            "ret_5": ret_5.values,
            "ret_21": ret_21.values,
            "ret_63": ret_63.values,
            "vol_20": vol_20.values,
            "vol_60": vol_60.values,
            "primary_score": primary_score.values,
            "fwd_return": fwd_return.values,
            "cost_return": cost_bps / 10000.0,
            "volatility": vol_20.values,
        })
        df["edge_hat"] = df["primary_score"].abs()
        df["signed_realized_edge"] = signed_edge.values
        df["meta_label"] = (df["signed_realized_edge"] > df["cost_return"]).astype(float)
        rows.append(df)
    panel = pd.concat(rows, ignore_index=True)
    panel = panel.replace([np.inf, -np.inf], np.nan)
    # Keep rows with missing future labels for latest inference, but drop unusable feature rows.
    feature_cols = [c for c in panel.columns if c not in RESERVED_COLS]
    panel = panel.dropna(subset=["primary_score", "edge_hat", "volatility"] + feature_cols)
    panel["Date"] = pd.to_datetime(panel["Date"])
    return panel.sort_values(["Date", "Asset"]).reset_index(drop=True)


def load_panel_csv(path: str | Path, cost_bps: float) -> pd.DataFrame:
    panel = pd.read_csv(path)
    required = {"Date", "Asset", "primary_score"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel CSV 필수 컬럼 누락: {sorted(missing)}")
    panel["Date"] = pd.to_datetime(panel["Date"])
    panel["Asset"] = panel["Asset"].astype(str)
    if "cost_return" not in panel.columns:
        panel["cost_return"] = cost_bps / 10000.0
    if "edge_hat" not in panel.columns:
        panel["edge_hat"] = panel["primary_score"].abs()
    if "signed_realized_edge" not in panel.columns and "fwd_return" in panel.columns:
        panel["signed_realized_edge"] = np.sign(panel["primary_score"]) * panel["fwd_return"]
    if "meta_label" not in panel.columns:
        if "signed_realized_edge" not in panel.columns:
            raise ValueError("panel에는 meta_label 또는 fwd_return/signed_realized_edge가 필요합니다.")
        panel["meta_label"] = (panel["signed_realized_edge"] > panel["cost_return"]).astype(float)
    if "volatility" not in panel.columns:
        panel["volatility"] = 0.15
    panel = panel.replace([np.inf, -np.inf], np.nan)
    return panel.sort_values(["Date", "Asset"]).reset_index(drop=True)


def feature_columns(panel: pd.DataFrame) -> List[str]:
    cols = []
    for c in panel.columns:
        if c in RESERVED_COLS:
            continue
        if pd.api.types.is_numeric_dtype(panel[c]):
            cols.append(c)
    if not cols:
        raise ValueError("Meta model 학습용 numeric feature column이 없습니다.")
    return cols


def fit_meta_model(train: pd.DataFrame, cols: List[str]):
    train = train.dropna(subset=cols + ["meta_label"])
    y = train["meta_label"].astype(int)
    if len(train) < 50:
        return ConstantProbabilityModel(float(y.mean()) if len(y) else 0.5)
    if y.nunique() < 2:
        return ConstantProbabilityModel(float(y.mean()))
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", C=0.75, solver="lbfgs")),
    ])
    model.fit(train[cols], y)
    return model


def predict_meta(model, frame: pd.DataFrame, cols: List[str]) -> np.ndarray:
    clean = frame[cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return model.predict_proba(clean)[:, 1]


def build_weights_from_signals(
    signals: pd.DataFrame,
    max_weight: float,
    long_short: bool,
    gross_cap: float,
    cash: bool = True,
    fully_invested: bool = False,
) -> pd.Series:
    if signals.empty or not signals["trade"].any():
        return pd.Series({CASH: 1.0}) if cash and not long_short else pd.Series(dtype=float)
    s = signals[signals["trade"]].copy()
    raw = s.set_index("Asset")["raw_weight_score"].astype(float)
    raw = raw.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if long_short:
        if raw.abs().sum() <= EPS:
            return pd.Series(dtype=float)
        w = raw / raw.abs().sum() * gross_cap
        w = w.clip(lower=-max_weight, upper=max_weight)
        gross = w.abs().sum()
        if gross > gross_cap and gross > EPS:
            w = w / gross * gross_cap
        return w
    raw = raw.clip(lower=0.0)
    if raw.sum() <= EPS:
        return pd.Series({CASH: 1.0}) if cash else pd.Series(dtype=float)
    if fully_invested:
        w = raw / raw.sum()
        return cap_and_normalize(w, max_weight=max_weight, long_only=True)

    risky_budget = float(np.clip(gross_cap, 0.0, 1.0))
    w = (raw / raw.sum() * risky_budget).clip(lower=0.0, upper=max_weight)
    if cash:
        w[CASH] = max(0.0, 1.0 - float(w.sum()))
    w = w[w.abs() > 1e-12]
    return w


def apply_beta_hedge(
    weights: pd.Series,
    returns_window: Optional[pd.DataFrame],
    hedge_asset: Optional[str],
    max_hedge_weight: float,
) -> pd.Series:
    if hedge_asset is None or returns_window is None or hedge_asset not in returns_window.columns or weights.empty:
        return weights
    hedge_ret = returns_window[hedge_asset].dropna()
    if len(hedge_ret) < 30 or hedge_ret.var() <= EPS:
        return weights
    betas = {}
    for asset in weights.index:
        if asset == CASH or asset not in returns_window.columns:
            betas[asset] = 0.0
            continue
        joined = pd.concat([returns_window[asset], hedge_ret], axis=1).dropna()
        if len(joined) < 30 or joined.iloc[:, 1].var() <= EPS:
            betas[asset] = 0.0
        else:
            betas[asset] = float(joined.iloc[:, 0].cov(joined.iloc[:, 1]) / joined.iloc[:, 1].var())
    beta_exposure = sum(float(weights.get(a, 0.0)) * b for a, b in betas.items())
    hedge_delta = float(np.clip(-beta_exposure, -max_hedge_weight, max_hedge_weight))
    weights = weights.copy()
    weights[hedge_asset] = weights.get(hedge_asset, 0.0) + hedge_delta
    return weights[weights.abs() > 1e-10]


def gate_for_date(
    date: pd.Timestamp,
    current_panel: pd.DataFrame,
    train_panel: pd.DataFrame,
    calibration_panel: pd.DataFrame,
    feature_cols: List[str],
    model,
    args: argparse.Namespace,
    returns_window: Optional[pd.DataFrame] = None,
) -> GateResult:
    frame = current_panel.copy()
    p_meta = predict_meta(model, frame, feature_cols)
    frame["p_meta"] = p_meta
    residuals = (calibration_panel["signed_realized_edge"] - calibration_panel["edge_hat"]).abs().dropna().values
    q = conformal_quantile(residuals, args.alpha)
    frame["conformal_q"] = q
    frame["lower_bound"] = frame["edge_hat"] - q
    frame["side"] = np.sign(frame["primary_score"]).replace(0, np.nan).fillna(0.0)
    min_edge = args.min_edge_bps / 10000.0
    frame["trade"] = (
        (frame["p_meta"] >= args.meta_threshold)
        & (frame["lower_bound"] > frame["cost_return"] + min_edge)
        & (frame["side"] != 0)
    )
    if not args.long_short:
        frame["trade"] = frame["trade"] & (frame["side"] > 0)
    frame["edge_after_cost"] = frame["lower_bound"] - frame["cost_return"]
    vol = frame["volatility"].replace(0, np.nan).abs().fillna(frame["volatility"].abs().median())
    vol = vol.replace(0, 0.15).fillna(0.15)
    frame["raw_weight_score"] = frame["side"] * np.maximum(frame["p_meta"] - args.meta_threshold, 0.0) * np.maximum(frame["edge_after_cost"], 0.0) / vol
    frame.loc[~frame["trade"], "raw_weight_score"] = 0.0
    weights = build_weights_from_signals(
        frame,
        max_weight=args.max_weight,
        long_short=args.long_short,
        gross_cap=args.gross_cap,
        cash=True,
        fully_invested=getattr(args, "fully_invested", False),
    )
    if args.beta_hedge and args.hedge_asset:
        weights = apply_beta_hedge(weights, returns_window, args.hedge_asset, args.max_hedge_weight)
    total = len(frame)
    abstention_rate = 1.0 - float(frame["trade"].mean()) if total else 1.0
    # Ex-post proxy on calibration data: interval coverage for signed edge.
    if len(calibration_panel.dropna(subset=["signed_realized_edge", "edge_hat"])):
        cp = calibration_panel.dropna(subset=["signed_realized_edge", "edge_hat"])
        coverage = float((cp["signed_realized_edge"] >= cp["edge_hat"] - q).mean())
    else:
        coverage = 0.0
    frame["Date"] = date
    return GateResult(frame, weights, q, coverage, abstention_rate)


def run_backtest(panel: pd.DataFrame, prices: Optional[pd.DataFrame], args: argparse.Namespace) -> Dict[str, object]:
    cols = feature_columns(panel)
    dates = sorted(panel["Date"].dropna().unique())
    dates = [pd.Timestamp(d) for d in dates]
    if len(dates) < args.min_train_days + args.horizon + 5:
        raise ValueError("Backtest 기간이 너무 짧습니다. min_train_days/horizon을 낮추거나 데이터를 늘리십시오.")
    returns = returns_from_prices(prices) if prices is not None else None
    all_assets = sorted(panel["Asset"].unique())
    current_w = pd.Series({CASH: 1.0})
    model = None
    last_fit_k = -10**9

    signal_rows = []
    weights_history = []
    order_rows = []
    net_returns = []
    costs = []
    turnovers = []
    diagnostics = []

    start_k = max(args.min_train_days, args.calibration_window + args.horizon + 5)
    for k in range(start_k, len(dates) - 1):
        date = dates[k]
        next_date = dates[k + 1]
        train_dates = set(dates[: max(0, k - args.horizon)])
        if len(train_dates) < args.min_train_days:
            continue
        train_panel = panel[panel["Date"].isin(train_dates)].dropna(subset=["meta_label", "signed_realized_edge"])
        if model is None or (k - last_fit_k) >= args.retrain_step:
            model = fit_meta_model(train_panel, cols)
            last_fit_k = k
        cal_start = max(0, k - args.horizon - args.calibration_window)
        cal_dates = set(dates[cal_start : max(0, k - args.horizon)])
        calibration_panel = panel[panel["Date"].isin(cal_dates)].dropna(subset=["signed_realized_edge", "edge_hat"])
        current_panel = panel[panel["Date"] == date].copy()
        if current_panel.empty:
            continue
        returns_window = None
        if returns is not None:
            hist_dates = [d for d in returns.index if d < date]
            if hist_dates:
                returns_window = returns.loc[hist_dates].tail(120)
        gate = gate_for_date(date, current_panel, train_panel, calibration_panel, cols, model, args, returns_window=returns_window)
        target_w = gate.weights
        if not args.long_short and CASH not in target_w.index:
            risky_sum = float(target_w.sum())
            if risky_sum < 1.0 - EPS:
                target_w[CASH] = 1.0 - risky_sum
        target_w = apply_turnover_cap(target_w, current_w, args.turnover_cap)
        cost_today = transaction_cost(current_w, target_w, args.cost_bps)
        turnover_today = float((target_w.reindex(current_w.index.union(target_w.index)).fillna(0.0) - current_w.reindex(current_w.index.union(target_w.index)).fillna(0.0)).abs().sum())

        # Use next-day return for signal generated at `date`.
        gross_ret = 0.0
        if returns is not None and next_date in returns.index:
            gross_ret = realized_portfolio_return(target_w.drop(labels=[CASH], errors="ignore"), returns.loc[next_date])
        net_ret = gross_ret - cost_today
        net_returns.append((next_date, net_ret))
        costs.append((next_date, cost_today))
        turnovers.append((next_date, turnover_today))
        weights_history.append(target_w.rename(date))
        for asset, d in (target_w.reindex(current_w.index.union(target_w.index)).fillna(0.0) - current_w.reindex(current_w.index.union(target_w.index)).fillna(0.0)).items():
            if abs(d) > 1e-8:
                order_rows.append({
                    "Date": date,
                    "Asset": asset,
                    "prev_weight": float(current_w.get(asset, 0.0)),
                    "target_weight": float(target_w.get(asset, 0.0)),
                    "delta_weight": float(d),
                    "estimated_cost": float(abs(d) * args.cost_bps / 10000.0),
                })
        current_w = target_w
        signal_rows.append(gate.signals)
        diagnostics.append({
            "Date": date,
            "q_conformal": gate.q_conformal,
            "coverage_proxy": gate.coverage_proxy,
            "abstention_rate": gate.abstention_rate,
            "n_trade": int(gate.signals["trade"].sum()),
            "n_candidates": int(len(gate.signals)),
        })

    net = pd.Series(dict(net_returns), name="net_return").sort_index()
    cost = pd.Series(dict(costs), name="transaction_cost").sort_index()
    turnover = pd.Series(dict(turnovers), name="turnover").sort_index()
    signals = pd.concat(signal_rows, ignore_index=True) if signal_rows else pd.DataFrame()
    weights = pd.DataFrame(weights_history).sort_index() if weights_history else pd.DataFrame()
    orders = pd.DataFrame(order_rows)
    diag = pd.DataFrame(diagnostics).sort_values("Date") if diagnostics else pd.DataFrame()
    metrics = annualized_metrics(net, turnover=turnover, cost=cost)
    if not diag.empty:
        metrics.update({
            "avg_abstention_rate": float(diag["abstention_rate"].mean()),
            "avg_coverage_proxy": float(diag["coverage_proxy"].replace([np.inf, -np.inf], np.nan).dropna().mean()),
            "avg_trades_per_day": float(diag["n_trade"].mean()),
        })
    metrics.update({"horizon": int(args.horizon), "alpha": float(args.alpha), "meta_threshold": float(args.meta_threshold)})
    return {
        "net_returns": net,
        "costs": cost,
        "turnover": turnover,
        "signals": signals,
        "weights": weights,
        "orders": orders,
        "diagnostics": diag,
        "metrics": metrics,
    }


def latest_gate(panel: pd.DataFrame, prices: Optional[pd.DataFrame], args: argparse.Namespace) -> GateResult:
    cols = feature_columns(panel)
    latest_date = pd.Timestamp(panel["Date"].max())
    dates = sorted(pd.Timestamp(d) for d in panel["Date"].dropna().unique())
    k = dates.index(latest_date)
    train_dates = set(dates[: max(0, k - args.horizon)]) if k > args.horizon else set(dates[:-args.horizon])
    train = panel[panel["Date"].isin(train_dates)].dropna(subset=["meta_label", "signed_realized_edge"])
    model = fit_meta_model(train, cols)
    cal_start = max(0, len(dates) - args.horizon - args.calibration_window)
    cal_dates = set(dates[cal_start : max(0, len(dates) - args.horizon)])
    calibration = panel[panel["Date"].isin(cal_dates)].dropna(subset=["signed_realized_edge", "edge_hat"])
    current = panel[panel["Date"] == latest_date]
    returns_window = None
    if prices is not None:
        returns_window = returns_from_prices(prices).tail(120)
    return gate_for_date(latest_date, current, train, calibration, cols, model, args, returns_window=returns_window)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="B Meta-label + Temporal Conformal Gate")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prices", help="Wide price CSV. Columns: Date + assets")
    g.add_argument("--panel", help="Long panel CSV. Required: Date,Asset,primary_score plus fwd_return or meta_label")
    p.add_argument("--outdir", default="output/b_meta_conformal_gate")
    p.add_argument("--horizon", type=int, default=5)
    p.add_argument("--alpha", type=float, default=0.10)
    p.add_argument("--calibration-window", type=int, default=100)
    p.add_argument("--meta-threshold", type=float, default=0.60)
    p.add_argument("--min-edge-bps", type=float, default=2.0)
    p.add_argument("--min-train-days", type=int, default=252)
    p.add_argument("--retrain-step", type=int, default=20)
    p.add_argument("--max-weight", type=float, default=0.10)
    p.add_argument("--gross-cap", type=float, default=1.0)
    p.add_argument("--turnover-cap", type=float, default=0.30)
    p.add_argument("--cost-bps", type=float, default=7.5)
    p.add_argument("--long-short", action="store_true", help="Allow negative weights. Default is long-only abstention gate.")
    p.add_argument("--fully-invested", action="store_true", help="For long-only mode, allocate the full risky sleeve instead of leaving residual cash.")
    p.add_argument("--beta-hedge", action="store_true", help="Add hedge overlay using --hedge-asset beta estimates.")
    p.add_argument("--hedge-asset", default=None, help="Asset used as futures/index hedge proxy, e.g., SPY")
    p.add_argument("--max-hedge-weight", type=float, default=0.50)
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    outdir = ensure_outdir(args.outdir)
    prices = None
    if args.prices:
        prices = load_price_csv(args.prices)
        panel = make_panel_from_prices(prices, horizon=args.horizon, cost_bps=args.cost_bps)
        panel.to_csv(outdir / "generated_panel.csv", index=False)
    else:
        panel = load_panel_csv(args.panel, cost_bps=args.cost_bps)

    bt = run_backtest(panel, prices, args)
    latest = latest_gate(panel, prices, args)

    bt["net_returns"].to_csv(outdir / "backtest_net_returns.csv", index_label="Date")
    bt["costs"].to_csv(outdir / "transaction_costs.csv", index_label="Date")
    bt["turnover"].to_csv(outdir / "turnover.csv", index_label="Date")
    bt["weights"].to_csv(outdir / "weights_history.csv", index_label="Date")
    bt["signals"].to_csv(outdir / "signals_history.csv", index=False)
    bt["orders"].to_csv(outdir / "orders.csv", index=False)
    bt["diagnostics"].to_csv(outdir / "gate_diagnostics.csv", index=False)
    latest.signals.sort_values(["trade", "p_meta", "lower_bound"], ascending=[False, False, False]).to_csv(outdir / "latest_signals.csv", index=False)
    latest.weights.rename("Weight").reset_index().rename(columns={"index": "Asset"}).to_csv(outdir / "latest_weights.csv", index=False)
    write_json(bt["metrics"], outdir / "metrics.json")

    summary = {
        "algorithm": "B Meta-label + Temporal Conformal Gate",
        "latest_date": str(pd.Timestamp(panel["Date"].max()).date()),
        "latest_q_conformal": latest.q_conformal,
        "latest_abstention_rate": latest.abstention_rate,
        "latest_coverage_proxy": latest.coverage_proxy,
        "latest_trade_count": int(latest.signals["trade"].sum()) if not latest.signals.empty else 0,
        "policy_verdict": POLICY_VERDICT,
        "metrics": bt["metrics"],
    }
    write_json(summary, outdir / "summary.json")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
