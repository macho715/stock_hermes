"""Track-S / Track-L risk gates and position sizing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from math import floor
from typing import Any

import numpy as np
import pandas as pd


class Gate(StrEnum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    ZERO = "ZERO"


@dataclass(frozen=True)
class RiskConfig:
    total_capital: float = 100_000.0
    track_s_alloc_pct: float = 0.20
    track_l_alloc_pct: float = 0.75
    cash_alloc_pct: float = 0.05
    track_s_monthly_stop_pct: float = -0.05
    track_s_risk_per_trade_pct: float = 0.0075
    track_s_stop_pct: float = 0.04
    track_s_tp1_pct: float = 0.05
    track_s_tp2_pct: float = 0.10
    track_s_min_score: float = 75.0
    track_s_min_rr: float = 2.0
    track_l_min_score: float = 80.0
    track_l_single_name_limit_pct: float = 0.12
    rebalance_band_pct: float = 0.05
    min_dollar_volume: float = 5_000_000.0
    max_open_risk_pct: float = 0.02

    @property
    def track_s_capital(self) -> float:
        return self.total_capital * self.track_s_alloc_pct

    @property
    def track_l_capital(self) -> float:
        return self.total_capital * self.track_l_alloc_pct

    @property
    def cash_capital(self) -> float:
        return self.total_capital * self.cash_alloc_pct


@dataclass(frozen=True)
class CandidateVerdict:
    ticker: str
    track: str
    score: float
    gate: Gate
    verdict: str
    entry: float
    stop: float
    tp1: float
    tp2: float
    risk_reward: float
    risk_per_share: float
    quantity: int
    position_value: float
    open_risk: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["gate"] = self.gate.value
        return result


def position_size_by_risk(
    entry: float,
    stop: float,
    track_capital: float,
    risk_per_trade_pct: float,
    *,
    optimizer_weight: float | None = None,
) -> tuple[int, float, float]:
    """Compute (quantity, position_value, open_risk) for a single name.

    When ``optimizer_weight`` is ``None`` the function uses the original
    risk-budget sizing rule.  When supplied, the position value is taken as
    ``optimizer_weight * track_capital`` (still respecting the Track-S/Track-L
    capital cap) and quantity is back-calculated from the entry price.  The
    open-risk figure is always ``quantity * (entry - stop)``.
    """
    if entry <= 0 or stop <= 0 or stop >= entry:
        return 0, 0.0, 0.0
    risk_per_share = entry - stop
    if optimizer_weight is not None:
        weight = max(0.0, min(float(optimizer_weight), 1.0))
        target_value = track_capital * weight
        quantity = max(0, floor(target_value / entry))
    else:
        risk_budget = track_capital * risk_per_trade_pct
        quantity = max(0, floor(risk_budget / risk_per_share))
    position_value = quantity * entry
    open_risk = quantity * risk_per_share
    return quantity, position_value, open_risk


def score_track_s(row: pd.Series, prediction_prob: float | None = None) -> tuple[float, list[str]]:
    reasons: list[str] = []
    rsi = _clamp(float(row.get("rsi_14", 50.0)), 0, 100)
    adx = _clamp(float(row.get("adx_14", 20.0)), 0, 60)
    volume_ratio = _clamp(float(row.get("volume_ratio_20", 1.0)), 0, 4)
    macd_hist = float(row.get("macd_hist", 0.0))
    return_5d = float(row.get("return_5d", 0.0))
    sma_20 = float(row.get("sma_ratio_20", 0.0))
    bb_pct = _clamp(float(row.get("bb_pct", 0.5)), 0, 1)
    cmf = _clamp(float(row.get("cmf_20", 0.0)), -1, 1)
    vi_diff = float(row.get("vi_diff_14", 0.0))
    score = 50.0
    score += 10.0 if 45 <= rsi <= 68 else (-8.0 if rsi > 80 or rsi < 25 else 0.0)
    score += min(12.0, adx / 5.0)
    score += min(10.0, volume_ratio * 3.0)
    score += 8.0 if macd_hist > 0 else -4.0
    score += 8.0 if return_5d > 0 else -5.0
    score += 7.0 if sma_20 > 0 else -4.0
    score += 4.0 if 0.35 <= bb_pct <= 0.85 else -3.0
    # CMF: positive money flow adds conviction; negative subtracts.
    score += _clamp(cmf * 8.0, -6.0, 8.0)
    # Vortex: VI+ > VI- confirms bullish momentum.
    score += 4.0 if vi_diff > 0.05 else (-3.0 if vi_diff < -0.05 else 0.0)
    if prediction_prob is not None:
        score += (float(prediction_prob) - 0.5) * 30.0
        reasons.append(f"model_prob={prediction_prob:.3f}")
    reasons.extend([f"rsi_14={rsi:.1f}", f"adx_14={adx:.1f}", f"volume_ratio_20={volume_ratio:.2f}", f"macd_hist={macd_hist:.4f}", f"cmf_20={cmf:.3f}", f"vi_diff_14={vi_diff:.3f}"])
    return _clamp(score, 0.0, 100.0), reasons


def score_track_l(row: pd.Series, prediction_prob: float | None = None) -> tuple[float, list[str]]:
    reasons: list[str] = []
    business_quality = float(row.get("business_quality", 0.0))
    earnings_quality = float(row.get("earnings_quality", 0.0))
    balance_sheet = float(row.get("balance_sheet", 0.0))
    valuation = float(row.get("valuation", 0.0))
    if max(business_quality, earnings_quality, balance_sheet, valuation) > 0:
        score = 0.35 * business_quality + 0.25 * earnings_quality + 0.20 * balance_sheet + 0.20 * valuation
        reasons.extend([f"business_quality={business_quality:.1f}", f"earnings_quality={earnings_quality:.1f}", f"balance_sheet={balance_sheet:.1f}", f"valuation={valuation:.1f}"])
    else:
        hist_vol = float(row.get("hist_vol_20", 0.25))
        sma_200 = float(row.get("sma_ratio_200", 0.0))
        return_20d = float(row.get("return_20d", 0.0))
        score = 70.0 + (8.0 if sma_200 > 0 else -8.0) + (5.0 if return_20d > 0 else -5.0)
        score -= min(15.0, max(0.0, hist_vol - 0.25) * 35.0)
        reasons.extend([f"sma_ratio_200={sma_200:.4f}", f"return_20d={return_20d:.4f}", f"hist_vol_20={hist_vol:.4f}"])
    if prediction_prob is not None:
        score += (float(prediction_prob) - 0.5) * 10.0
        reasons.append(f"model_prob={prediction_prob:.3f}")
    return _clamp(score, 0.0, 100.0), reasons


def evaluate_track_s_candidate(
    ticker: str,
    row: pd.Series,
    entry: float,
    config: RiskConfig | None = None,
    prediction_prob: float | None = None,
    monthly_pnl_pct: float = 0.0,
    allow_margin: bool = False,
    allow_options: bool = False,
    atr_pct: float | None = None,
) -> CandidateVerdict:
    cfg = config or RiskConfig()
    # ATR-based dynamic stop: use max(fixed_stop, 2×ATR) for volatility-adaptive risk management.
    if atr_pct is not None and np.isfinite(atr_pct) and atr_pct > 0:
        effective_stop_pct = max(cfg.track_s_stop_pct, 2.0 * float(atr_pct))
    else:
        effective_stop_pct = cfg.track_s_stop_pct
    stop = entry * (1 - effective_stop_pct)
    tp1 = entry * (1 + cfg.track_s_tp1_pct)
    tp2 = entry * (1 + cfg.track_s_tp2_pct)
    score, reasons = score_track_s(row, prediction_prob=prediction_prob)
    risk_per_share = max(0.0, entry - stop)
    risk_reward = (tp2 - entry) / risk_per_share if risk_per_share > 0 else 0.0
    quantity, position_value, open_risk = position_size_by_risk(entry, stop, cfg.track_s_capital, cfg.track_s_risk_per_trade_pct)
    dollar_volume = float(row.get("dollar_volume", 0.0))
    gate = Gate.GREEN
    if not np.isfinite(entry) or entry <= 0 or stop >= entry:
        gate = Gate.ZERO
        reasons.append("invalid entry/stop")
    if allow_margin or allow_options:
        gate = Gate.ZERO
        reasons.append("margin/options are disabled by fail-safe")
    if monthly_pnl_pct <= cfg.track_s_monthly_stop_pct:
        gate = Gate.ZERO
        reasons.append("monthly Track-S stop reached")
    if dollar_volume and dollar_volume < cfg.min_dollar_volume:
        gate = min_gate(gate, Gate.RED)
        reasons.append(f"liquidity below minimum: {dollar_volume:,.0f}")
    if risk_reward < cfg.track_s_min_rr:
        gate = min_gate(gate, Gate.AMBER)
        reasons.append(f"risk_reward<{cfg.track_s_min_rr:.1f}")
    if score < cfg.track_s_min_score:
        gate = min_gate(gate, Gate.AMBER if score >= 65 else Gate.RED)
        reasons.append(f"score<{cfg.track_s_min_score:.1f}")
    if open_risk > cfg.track_s_capital * cfg.max_open_risk_pct:
        gate = min_gate(gate, Gate.RED)
        reasons.append("open risk exceeds Track-S cap")
    verdict = {Gate.GREEN: "Watch/Buy", Gate.AMBER: "Watch Only", Gate.RED: "Reject", Gate.ZERO: "No Trade"}[gate]
    return CandidateVerdict(ticker, "S", round(score, 2), gate, verdict, round(entry, 4), round(stop, 4), round(tp1, 4), round(tp2, 4), round(risk_reward, 3), round(risk_per_share, 4), quantity, round(position_value, 2), round(open_risk, 2), reasons)


def evaluate_track_l_candidate(ticker: str, row: pd.Series, entry: float, config: RiskConfig | None = None, prediction_prob: float | None = None) -> CandidateVerdict:
    cfg = config or RiskConfig()
    score, reasons = score_track_l(row, prediction_prob=prediction_prob)
    stop, tp1, tp2 = entry * 0.88, entry * 1.10, entry * 1.20
    gate = Gate.GREEN if score >= cfg.track_l_min_score else (Gate.AMBER if score >= 70 else Gate.RED)
    if entry <= 0 or not np.isfinite(entry):
        gate = Gate.ZERO
        reasons.append("invalid entry")
    verdict = {Gate.GREEN: "Eligible/DCA", Gate.AMBER: "Hold/Monitor", Gate.RED: "Reject", Gate.ZERO: "No Action"}[gate]
    max_position_value = cfg.track_l_capital * cfg.track_l_single_name_limit_pct
    quantity = floor(max_position_value / entry) if entry > 0 else 0
    return CandidateVerdict(ticker, "L", round(score, 2), gate, verdict, round(entry, 4), round(stop, 4), round(tp1, 4), round(tp2, 4), 0.0, 0.0, quantity, round(quantity * entry, 2), 0.0, reasons)


def portfolio_targets(config: RiskConfig | None = None) -> pd.DataFrame:
    cfg = config or RiskConfig()
    return pd.DataFrame([
        {"Track": "Track-S", "Allocation": cfg.track_s_alloc_pct, "Value": cfg.track_s_capital},
        {"Track": "Track-L", "Allocation": cfg.track_l_alloc_pct, "Value": cfg.track_l_capital},
        {"Track": "Cash", "Allocation": cfg.cash_alloc_pct, "Value": cfg.cash_capital},
    ])


def min_gate(current: Gate, proposed: Gate) -> Gate:
    order = {Gate.GREEN: 3, Gate.AMBER: 2, Gate.RED: 1, Gate.ZERO: 0}
    return proposed if order[proposed] < order[current] else current


def _clamp(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return low
    return max(low, min(high, value))
