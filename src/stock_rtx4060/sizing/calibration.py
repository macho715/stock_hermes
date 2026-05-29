"""Calibration helpers for CMRS sizing.

The recommendation engine passes out-of-fold probabilities and realized targets
here.  This module turns those into residual buckets without changing ranking or
order-related state.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .strategy import CRISIS, CalibBook, HorizonScore, SizingResult

CALM = "CALM"
TREND = "TREND"
RISK = "RISK"


@dataclass(frozen=True)
class SizingInputs:
    horizon_scores: list[HorizonScore]
    calib_book: CalibBook
    regime: str
    regime_probs: dict[str, float]
    coverage_status: str = "NO_DATA"


def horizon_label(horizon: int) -> str:
    return f"{int(horizon)}d"


def regime_from_feature_row(row: pd.Series) -> str:
    """Map lagged technical features into a coarse sizing regime."""

    atr = _num(row.get("atr_pct_14"), default=0.0)
    fast = _num(row.get("trend_regime_fast"), default=0.0)
    slow = _num(row.get("trend_regime_slow"), default=0.0)
    if atr >= 0.08:
        return CRISIS
    if slow >= 0.5:
        return TREND
    if fast >= 0.5 and atr <= 0.05:
        return CALM
    if atr >= 0.05:
        return RISK
    return CALM


def regime_probs_from_label(label: str) -> dict[str, float]:
    crisis_prob = {
        CRISIS: 1.0,
        RISK: 0.5,
        TREND: 0.0,
        CALM: 0.0,
    }.get(label, 0.25)
    return {CRISIS: crisis_prob, label: 1.0}


def build_calib_book(
    feature_df: pd.DataFrame,
    oof_probs: pd.Series,
    *,
    horizon: int,
) -> CalibBook:
    """Build global and regime residual buckets from OOF probabilities."""

    label = horizon_label(horizon)
    aligned = pd.DataFrame(
        {
            "prob": pd.to_numeric(oof_probs, errors="coerce"),
            "target": pd.to_numeric(feature_df["target_direction"], errors="coerce"),
        },
        index=feature_df.index,
    ).dropna()
    if aligned.empty:
        return CalibBook(by_regime={}, global_pool={})

    residuals = (aligned["target"] - aligned["prob"]).abs().astype(float)
    global_pool = {label: residuals.to_numpy(dtype=float)}
    by_regime: dict[str, dict[str, np.ndarray]] = {}
    for regime in (regime_from_feature_row(feature_df.loc[idx]) for idx in aligned.index):
        by_regime.setdefault(regime, {}).setdefault(label, [])
    for idx, residual in residuals.items():
        regime = regime_from_feature_row(feature_df.loc[idx])
        by_regime[regime][label].append(float(residual))

    regime_arrays = {
        regime: {h: np.asarray(values, dtype=float) for h, values in horizons.items()}
        for regime, horizons in by_regime.items()
    }
    return CalibBook(by_regime=regime_arrays, global_pool=global_pool)


def build_sizing_inputs(
    feature_df: pd.DataFrame,
    model_stats: dict,
    *,
    horizon: int,
) -> SizingInputs:
    label = horizon_label(horizon)
    latest_prob = float(model_stats.get("latest_prob", 0.5))
    hs = [HorizonScore(label, latest_prob - 0.5)]
    oof_probs = model_stats.get("oof_probs")
    if not isinstance(oof_probs, pd.Series):
        oof_probs = pd.Series(dtype=float)
    book = build_calib_book(feature_df, oof_probs, horizon=horizon)
    regime = regime_from_feature_row(feature_df.iloc[-1]) if not feature_df.empty else CALM
    return SizingInputs(
        horizon_scores=hs,
        calib_book=book,
        regime=regime,
        regime_probs=regime_probs_from_label(regime),
    )


def coverage_hits_for_result(
    book: CalibBook,
    result: SizingResult,
    *,
    regime: str,
) -> np.ndarray:
    hits: list[np.ndarray] = []
    for horizon, info in result.per_horizon.items():
        q = _num(info.get("q"), default=float("inf"))
        source = result.sources.get(horizon)
        if source == "mondrian":
            residuals = book.by_regime.get(regime, {}).get(horizon, np.array([]))
        else:
            residuals = book.global_pool.get(horizon, np.array([]))
        if residuals.size and np.isfinite(q):
            hits.append((np.abs(residuals) <= q).astype(float))
    if not hits:
        return np.array([], dtype=float)
    return np.concatenate(hits)


def _num(value: object, *, default: float) -> float:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(val):
        return default
    return val
