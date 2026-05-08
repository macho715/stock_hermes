"""
Risk-gated recommendation scanner for stock_rtx4060.

Boundary
--------
The scanner produces screening candidates and order-plan drafts only.  It never
places broker orders and never claims personalized investment advice.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import TimeSeriesSplit

from .audit_log import AuditEvent, AuditLogger
from .backtester import BacktestConfig, Backtester
from .backtest_honesty import evaluate_backtest_honesty, summarize_honesty
from .data_providers import ProviderResult, load_ohlcv_with_provider
from .kevpe_adapter import get_kevpe_adapter, kevpe_signal_to_supplement
from .ensemble_model import DirectionModel, ModelConfig, _safe_auc
from .feature_engine import TechnicalIndicators, feature_columns

Track = Literal["S", "L"]
Verdict = Literal[
    "ELIGIBLE_RECOMMENDATION",
    "ACCUMULATE_RECOMMENDATION",
    "AMBER_REVIEW_ONLY",
    "AMBER_WATCHLIST",
    "RED_NOT_RECOMMENDED",
    "RED_DATA_INSUFFICIENT",
    "RED_DATA_OR_MODEL_ERROR",
    "ZERO_RISK_PLAN_FAILED",
]

DEFAULT_UNIVERSE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMD",
    "AVGO",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "JPM",
    "XOM",
    "LLY",
    "UNH",
    "COST",
    "QQQ",
    "SPY",
    "XLK",
    "XLE",
    "GLD",
]


@dataclass
class RecommendationConfig:
    universe: list[str] = field(default_factory=lambda: DEFAULT_UNIVERSE.copy())
    track: Literal["S", "L", "BOTH"] = "BOTH"
    period: str = "3y"
    horizon_s: int = 20
    horizon_l: int = 63
    top_n: int = 5
    synthetic: bool = False
    min_rows: int = 260
    min_avg_dollar_volume: float = 10_000_000.0
    short_green_score: float = 75.0
    short_amber_score: float = 65.0
    long_green_score: float = 80.0
    long_amber_score: float = 70.0
    stop_loss_pct_s: float = 0.04
    hard_stop_loss_pct_s: float = 0.05
    take_profit_1_pct_s: float = 0.05
    take_profit_2_pct_s: float = 0.10
    stop_loss_pct_l: float = 0.12
    max_stop_loss_pct_l: float = 0.18
    target_return_pct_l: float = 0.20
    risk_per_trade_pct_s: float = 0.0075
    risk_per_trade_pct_l: float = 0.0050
    max_position_pct_s: float = 0.20
    max_position_pct_l: float = 0.12
    max_mdd_pct_s: float = 25.0
    max_mdd_pct_l: float = 35.0
    min_risk_reward: float = 2.0
    model_kind: Literal["auto", "xgb", "logistic", "rf"] = "logistic"
    xgb_device: Literal["cpu", "cuda"] = "cpu"
    xgb_estimators: int = 160
    xgb_splits: int = 3
    cv_gap: int | None = None
    min_oof_coverage: float = 0.45
    min_backtest_sharpe: float = -0.25
    transaction_cost_buffer_pct: float = 0.50
    capital: float = 100_000.0
    prefer_gpu: bool = False
    lite: bool = True
    output_dir: str = "recommendation_reports"
    data_provider: Literal["auto", "synthetic", "yfinance", "openbb", "pykrx", "fdr"] = "auto"
    provider_config: str | None = None
    kevpe_events: str | None = None
    audit_command: str = "recommend"

    def __post_init__(self) -> None:
        if self.prefer_gpu:
            self.xgb_device = "cuda"
        if self.lite:
            self.xgb_estimators = min(self.xgb_estimators, 120)


@dataclass
class ValidationCheck:
    name: str
    status: Literal["PASS", "AMBER", "FAIL"]
    evidence: str


@dataclass
class RiskPlan:
    entry: float
    stop: float
    tp1: float
    tp2: float
    stop_pct: float
    tp2_pct: float
    risk_reward: float
    risk_budget_pct: float
    max_position_pct: float
    suggested_quantity: float
    suggested_position_value: float


@dataclass
class RecommendationRun:
    """Report write result with legacy attribute and path-key access."""

    results: list["RecommendationResult"]
    errors: list[dict]
    markdown_path: str
    json_path: str
    audit_path: str

    def __getitem__(self, key: str) -> str:
        if key == "markdown":
            return self.markdown_path
        if key == "json":
            return self.json_path
        if key == "audit":
            return self.audit_path
        raise KeyError(key)


@dataclass
class RecommendationResult:
    ticker: str
    track: Track
    verdict: Verdict
    recommendation_rank_score: float
    candidate_label: str
    screening_output_only: bool
    latest_close: float
    entry: float
    stop: float
    tp1: float
    tp2: float
    stop_pct: float
    tp2_pct: float
    risk_reward: float
    risk_budget_pct: float
    max_position_pct: float
    suggested_quantity: float
    suggested_position_value: float
    direction_prob: float
    expected_value_pct: float
    model_accuracy: float
    model_auc: float
    oof_coverage: float
    backtest_return_pct: float
    backtest_sharpe: float
    backtest_sortino: float
    backtest_mdd_pct: float
    profit_factor: str | float
    avg_dollar_volume_20d: float
    volume_ratio_20d: float
    market_regime_score: float
    return_20d_pct: float
    return_60d_pct: float
    drawdown_252d_pct: float
    confirmations_passed: int
    confirmations_total: int
    validations: list[ValidationCheck]
    reasons: list[str]
    generated_at_utc: str
    backtest_honesty: dict | None = None
    # KEVPE risk overlay (optional — populated when KEVPE adapter is available)
    kevpe_available: bool = False
    kevpe_regime: str | None = None
    kevpe_score: float | None = None
    kevpe_expected_return_pct: float | None = None
    kevpe_ci: list[float] | None = None
    kevpe_confidence: str | None = None
    kevpe_reason: str | None = None
    # Phase-4 portfolio target weight (optional — 0.0 means "no portfolio guidance"
    # so the dashboard_snapshot.v1 schema remains backward-compatible).
    target_weight: float = 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["validations"] = [asdict(v) for v in self.validations]
        return data


# ────────────────────────────────────────────────────────────────
# Data loading
# ────────────────────────────────────────────────────────────────


def _stable_seed(text: str) -> int:
    return int.from_bytes(text.encode("utf-8")[:8].ljust(8, b"0"), "little") % (2**32 - 1)


def make_synthetic_ohlcv(n: int = 760, seed: int = 42, drift: float = 0.00035) -> pd.DataFrame:
    """Generate deterministic synthetic OHLCV for tests and offline demos."""
    rng = np.random.default_rng(seed)
    price = 100.0
    closes: list[float] = []
    for i in range(n):
        seasonal = 0.00025 * np.sin(i / 45.0) + 0.00015 * np.cos(i / 90.0)
        volatility = 0.010 + 0.006 * (1 + np.sin(i / 70.0)) / 2
        price *= 1.0 + rng.normal(drift + seasonal, volatility)
        closes.append(float(max(price, 1.0)))
    close = np.asarray(closes, dtype=float)
    high = close * (1.0 + rng.uniform(0.002, 0.020, n))
    low = close * (1.0 - rng.uniform(0.002, 0.020, n))
    open_ = low + rng.uniform(0.0, 1.0, n) * (high - low)
    volume = rng.integers(1_000_000, 7_000_000, n).astype(float)
    idx = pd.bdate_range(end=pd.Timestamp.utcnow().normalize(), periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx)


def load_ohlcv(
    ticker: str,
    period: str,
    synthetic: bool = False,
    data_provider: Literal["auto", "synthetic", "yfinance", "openbb", "pykrx", "fdr"] = "auto",
    provider_config: str | None = None,
    audit_logger: AuditLogger | None = None,
    command: str = "recommend",
) -> tuple[pd.DataFrame, str]:
    provider_result = load_ohlcv_result(
        ticker,
        period,
        synthetic=synthetic,
        data_provider=data_provider,
        provider_config=provider_config,
        audit_logger=audit_logger,
        command=command,
    )
    return provider_result.frame, provider_result.source


def load_ohlcv_result(
    ticker: str,
    period: str,
    synthetic: bool = False,
    data_provider: Literal["auto", "synthetic", "yfinance", "openbb", "pykrx", "fdr"] = "auto",
    provider_config: str | None = None,
    audit_logger: AuditLogger | None = None,
    command: str = "recommend",
) -> ProviderResult:
    provider_result = load_ohlcv_with_provider(
        ticker,
        period,
        synthetic=synthetic,
        data_provider=data_provider,
        provider_config_path=provider_config,
        audit_logger=audit_logger,
        command=command,
    )
    return provider_result


def parse_universe(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_UNIVERSE.copy()
    return [item.strip().upper() for item in value.replace(",", " ").split() if item.strip()]


# ────────────────────────────────────────────────────────────────
# Modeling
# ────────────────────────────────────────────────────────────────


def _model_config(cfg: RecommendationConfig, horizon: int) -> ModelConfig:
    return ModelConfig(
        horizon=horizon,
        n_splits=cfg.xgb_splits,
        gap=cfg.cv_gap if cfg.cv_gap is not None else horizon,
        model_kind=cfg.model_kind,
        xgb_device=cfg.xgb_device,
        use_lstm=False,
        xgb_params={
            "n_estimators": cfg.xgb_estimators,
            "max_depth": 4,
            "learning_rate": 0.04,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "min_child_weight": 3,
            "reg_lambda": 1.5,
            "reg_alpha": 0.05,
            "eval_metric": "logloss",
            "random_state": 42,
            "n_jobs": 4,
            "verbosity": 0,
            "use_label_encoder": False,
        },
    )


def _fit_walk_forward_model(feature_df: pd.DataFrame, horizon: int, cfg: RecommendationConfig) -> dict:
    cols = feature_columns(feature_df)
    X = feature_df.loc[:, cols].replace([np.inf, -np.inf], np.nan)
    y = feature_df["target_direction"].astype(int)
    if len(X) < 80 or y.nunique() < 2:
        raise RuntimeError("모델 학습 데이터 부족 또는 target class 단일값")

    model_cfg = _model_config(cfg, horizon)
    n_splits = min(cfg.xgb_splits, max(2, len(X) // 120))
    gap = min(max(0, model_cfg.gap or 0), max(0, len(X) // (n_splits + 1) - 1))
    splitter = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    oof = pd.Series(np.nan, index=X.index, dtype=float)
    accs: list[float] = []
    aucs: list[float] = []
    models_used: list[str] = []

    for train_idx, test_idx in splitter.split(X):
        x_tr, x_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        model = DirectionModel(model_cfg).fit(x_tr, y_tr)
        prob = model.predict_proba(x_te)
        oof.iloc[test_idx] = prob
        accs.append(float(accuracy_score(y_te, (prob >= 0.5).astype(int))))
        aucs.append(_safe_auc(y_te, prob))
        models_used.append(model.kind_used)

    final_model = DirectionModel(model_cfg).fit(X, y)
    latest_prob = float(final_model.predict_proba(X.iloc[[-1]])[0])
    coverage = float(oof.notna().mean())
    neutral_probs = oof.fillna(0.5).to_numpy(dtype=float)

    return {
        "model": final_model,
        "feature_cols": cols,
        "oof_probs": oof,
        "backtest_probs": neutral_probs,
        "latest_prob": latest_prob,
        "accuracy": float(np.mean(accs)) if accs else 0.0,
        "auc": float(np.mean(aucs)) if aucs else 0.5,
        "oof_coverage": coverage,
        "gap": gap,
        "models_used": sorted(set(models_used + [final_model.kind_used])),
    }


# ────────────────────────────────────────────────────────────────
# Scoring helpers
# ────────────────────────────────────────────────────────────────


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return float(max(low, min(high, value)))


def _pct(value: float) -> float:
    return round(float(value) * 100.0, 2)


def _safe_pct_change(close: pd.Series, period: int) -> float:
    if len(close) <= period:
        return 0.0
    value = close.pct_change(period).iloc[-1]
    return 0.0 if pd.isna(value) else float(value)


def _market_snapshot(df: pd.DataFrame) -> dict:
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    volume = df["Volume"].astype(float)
    latest = float(close.iloc[-1])
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else sma50
    high20 = float(high.rolling(20).max().iloc[-1])
    high252 = float(high.rolling(min(252, len(high))).max().iloc[-1])
    vol20 = float(volume.rolling(20).mean().iloc[-1])
    avg_dollar_vol = float((close * volume).rolling(20).mean().iloc[-1])
    volume_ratio = float(volume.iloc[-1] / vol20) if vol20 else 0.0
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr14 = float(tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().iloc[-1])
    atr_pct = atr14 / latest if latest else 0.0
    ret20 = _safe_pct_change(close, 20)
    ret60 = _safe_pct_change(close, 60)
    ret252 = _safe_pct_change(close, 252)
    dd252 = float(latest / high252 - 1.0) if high252 else 0.0

    regime_score = 0.0
    regime_score += 20.0 if latest > sma20 else 0.0
    regime_score += 20.0 if latest > sma50 else 0.0
    regime_score += 20.0 if latest > sma200 else 0.0
    regime_score += 15.0 if sma20 > sma50 else 0.0
    regime_score += 15.0 if sma50 > sma200 else 0.0
    regime_score += 10.0 if atr_pct <= 0.05 else 5.0 if atr_pct <= 0.08 else 0.0

    return {
        "latest": latest,
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "high20": high20,
        "high252": high252,
        "atr14": atr14,
        "atr_pct": atr_pct,
        "avg_dollar_volume_20d": avg_dollar_vol,
        "volume_ratio_20d": volume_ratio,
        "return_20d": ret20,
        "return_60d": ret60,
        "return_252d": ret252,
        "drawdown_252d": dd252,
        "market_regime_score": round(regime_score, 2),
    }


def _risk_plan(track: Track, snap: dict, cfg: RecommendationConfig, capital: float = 100_000.0) -> RiskPlan:
    entry = float(snap["latest"])
    atr_pct = float(snap.get("atr_pct", 0.0))
    if track == "S":
        stop_pct = min(cfg.hard_stop_loss_pct_s, max(cfg.stop_loss_pct_s, 1.35 * atr_pct))
        tp1_pct = max(cfg.take_profit_1_pct_s, stop_pct * 1.10)
        tp2_pct = max(cfg.take_profit_2_pct_s, stop_pct * cfg.min_risk_reward)
        risk_budget_pct = cfg.risk_per_trade_pct_s
        max_position_pct = cfg.max_position_pct_s
    else:
        stop_pct = min(cfg.max_stop_loss_pct_l, max(cfg.stop_loss_pct_l, 2.00 * atr_pct))
        tp1_pct = max(cfg.target_return_pct_l * 0.5, stop_pct * 0.75)
        tp2_pct = max(cfg.target_return_pct_l, stop_pct * 1.50)
        risk_budget_pct = cfg.risk_per_trade_pct_l
        max_position_pct = cfg.max_position_pct_l

    stop = entry * (1.0 - stop_pct)
    tp1 = entry * (1.0 + tp1_pct)
    tp2 = entry * (1.0 + tp2_pct)
    per_share_risk = max(entry - stop, 1e-12)
    risk_budget_value = capital * risk_budget_pct
    quantity_by_risk = risk_budget_value / per_share_risk
    quantity_by_cap = capital * max_position_pct / entry
    quantity = max(0.0, min(quantity_by_risk, quantity_by_cap))
    position_value = quantity * entry
    rr = (tp2 - entry) / per_share_risk if per_share_risk else 0.0
    return RiskPlan(
        entry=round(entry, 4),
        stop=round(stop, 4),
        tp1=round(tp1, 4),
        tp2=round(tp2, 4),
        stop_pct=round(stop_pct, 4),
        tp2_pct=round(tp2_pct, 4),
        risk_reward=round(rr, 2),
        risk_budget_pct=round(risk_budget_pct, 4),
        max_position_pct=round(max_position_pct, 4),
        suggested_quantity=round(quantity, 4),
        suggested_position_value=round(position_value, 2),
    )


def _expected_value_pct(prob: float, plan: RiskPlan) -> float:
    reward = plan.tp2_pct
    risk = plan.stop_pct
    return round((prob * reward - (1.0 - prob) * risk) * 100.0, 3)


def _score_track_s(prob: float, snap: dict, backtest: dict, plan: RiskPlan, model_stats: dict, cfg: RecommendationConfig) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    model_edge = _clip((prob - 0.50) / 0.22) * 18.0
    cv_quality = _clip((model_stats["auc"] - 0.50) / 0.18) * 7.0 + _clip((model_stats["accuracy"] - 0.50) / 0.15) * 5.0
    score += model_edge + cv_quality
    if prob >= 0.56:
        reasons.append(f"모델 상승확률 {prob:.2%}")

    trend = 0.0
    trend += 5.0 if snap["latest"] > snap["sma20"] else 0.0
    trend += 5.0 if snap["latest"] > snap["sma50"] else 0.0
    trend += 5.0 if snap["sma20"] > snap["sma50"] else 0.0
    trend += 4.0 if snap["return_20d"] > 0 else 0.0
    trend += 3.0 if snap["return_60d"] > 0 else 0.0
    score += trend
    if trend >= 14.0:
        reasons.append("단기/중기 추세 확인")

    liquidity = 0.0
    liquidity += 8.0 if snap["avg_dollar_volume_20d"] >= cfg.min_avg_dollar_volume else 0.0
    liquidity += 6.0 if snap["volume_ratio_20d"] >= 1.20 else 3.0 if snap["volume_ratio_20d"] >= 0.80 else 0.0
    score += liquidity

    breakout = 12.0 if snap["latest"] >= snap["high20"] * 0.995 else 6.0 if snap["latest"] >= snap["sma20"] else 0.0
    score += breakout
    if breakout >= 12.0:
        reasons.append("20일 고점권/돌파 후보")

    volatility_guard = 8.0 if snap["atr_pct"] <= 0.04 else 5.0 if snap["atr_pct"] <= 0.06 else 1.0
    regime = _clip(snap["market_regime_score"] / 100.0) * 8.0
    score += volatility_guard + regime

    bt_score = _clip((float(backtest.get("sharpe_ratio", 0.0)) + 0.2) / 1.7) * 7.0
    bt_score += _clip((cfg.max_mdd_pct_s - float(backtest.get("max_drawdown_pct", 99.0))) / cfg.max_mdd_pct_s) * 5.0
    score += bt_score
    if float(backtest.get("max_drawdown_pct", 99.0)) <= cfg.max_mdd_pct_s:
        reasons.append(f"백테스트 MDD {float(backtest.get('max_drawdown_pct', 0.0)):.2f}%")

    rr_score = 10.0 if plan.risk_reward >= cfg.min_risk_reward else plan.risk_reward / cfg.min_risk_reward * 10.0
    ev = _expected_value_pct(prob, plan)
    ev_score = 5.0 if ev > 2.0 else 3.0 if ev > 0 else 0.0
    score += rr_score + ev_score
    if plan.risk_reward >= cfg.min_risk_reward:
        reasons.append(f"R/R {plan.risk_reward:.2f} 통과")
    if ev > 0:
        reasons.append(f"기대값 {ev:.2f}%")

    return round(min(score, 100.0), 2), reasons


def _score_track_l(prob: float, snap: dict, backtest: dict, plan: RiskPlan, model_stats: dict, cfg: RecommendationConfig) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    quality_proxy = 0.0
    quality_proxy += 10.0 if snap["latest"] > snap["sma200"] else 0.0
    quality_proxy += 8.0 if snap["sma50"] > snap["sma200"] else 0.0
    quality_proxy += 7.0 if snap["market_regime_score"] >= 60.0 else 3.0 if snap["market_regime_score"] >= 45.0 else 0.0
    score += quality_proxy
    if quality_proxy >= 15:
        reasons.append("장기 추세 구조 양호")

    momentum = _clip((snap["return_252d"] + 0.10) / 0.35) * 13.0 + _clip((snap["return_60d"] + 0.08) / 0.22) * 10.0
    score += momentum

    stability = _clip((0.08 - snap["atr_pct"]) / 0.08) * 12.0
    score += stability

    dd = snap["drawdown_252d"]
    valuation_proxy = 14.0 if -0.22 <= dd <= -0.03 else 10.0 if dd < -0.22 else 6.0
    score += valuation_proxy
    if -0.22 <= dd <= -0.03:
        reasons.append("52주 고점 대비 과열이 아닌 조정권")

    model_score = _clip((prob - 0.50) / 0.18) * 10.0
    cv_quality = _clip((model_stats["auc"] - 0.50) / 0.18) * 5.0
    score += model_score + cv_quality

    bt_score = _clip((cfg.max_mdd_pct_l - float(backtest.get("max_drawdown_pct", 99.0))) / cfg.max_mdd_pct_l) * 8.0
    score += bt_score
    if float(backtest.get("max_drawdown_pct", 99.0)) <= cfg.max_mdd_pct_l:
        reasons.append("장기 MDD 한도 내")

    rr_score = 8.0 if plan.risk_reward >= 1.5 else 4.0 if plan.risk_reward >= 1.0 else 0.0
    dca_suitability = 7.0 if snap["avg_dollar_volume_20d"] >= cfg.min_avg_dollar_volume and snap["atr_pct"] <= 0.08 else 3.0
    score += rr_score + dca_suitability

    return round(min(score, 100.0), 2), reasons


def _validation_checks(track: Track, df: pd.DataFrame, snap: dict, model_stats: dict, backtest: dict, plan: RiskPlan, score: float, cfg: RecommendationConfig) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    checks.append(ValidationCheck("DATA_ROWS", "PASS" if len(df) >= cfg.min_rows else "FAIL", f"rows={len(df)}, min_rows={cfg.min_rows}"))
    checks.append(
        ValidationCheck(
            "LIQUIDITY",
            "PASS" if snap["avg_dollar_volume_20d"] >= cfg.min_avg_dollar_volume else "AMBER",
            f"avg_dollar_volume_20d={snap['avg_dollar_volume_20d']:.2f}",
        )
    )
    regime_min = 45.0 if track == "S" else 40.0
    checks.append(
        ValidationCheck(
            "MARKET_REGIME",
            "PASS" if snap["market_regime_score"] >= regime_min else "AMBER",
            f"regime_score={snap['market_regime_score']:.2f}, atr_pct={snap['atr_pct']:.4f}",
        )
    )
    min_prob = 0.56 if track == "S" else 0.53
    model_pass = model_stats["latest_prob"] >= min_prob and model_stats["accuracy"] >= 0.50
    checks.append(
        ValidationCheck(
            "MODEL_EDGE",
            "PASS" if model_pass else "AMBER",
            f"prob={model_stats['latest_prob']:.4f}, acc={model_stats['accuracy']:.4f}, auc={model_stats['auc']:.4f}, models={','.join(model_stats['models_used'])}",
        )
    )
    checks.append(
        ValidationCheck(
            "OOF_COVERAGE",
            "PASS" if model_stats["oof_coverage"] >= cfg.min_oof_coverage else "AMBER",
            f"coverage={model_stats['oof_coverage']:.2%}, gap={model_stats['gap']}",
        )
    )
    max_mdd = cfg.max_mdd_pct_s if track == "S" else cfg.max_mdd_pct_l
    bt_pass = float(backtest.get("max_drawdown_pct", 99.0)) <= max_mdd and float(backtest.get("sharpe_ratio", -99.0)) >= -0.25
    checks.append(
        ValidationCheck(
            "BACKTEST_SANITY",
            "PASS" if bt_pass else "AMBER",
            f"return={backtest.get('total_return_pct', 0.0):.2f}%, sharpe={backtest.get('sharpe_ratio', 0.0):.3f}, mdd={backtest.get('max_drawdown_pct', 0.0):.2f}%",
        )
    )
    rr_min = cfg.min_risk_reward if track == "S" else 1.5
    risk_pass = plan.stop > 0 and plan.stop < plan.entry and plan.risk_reward >= rr_min and plan.risk_budget_pct > 0
    checks.append(
        ValidationCheck(
            "RISK_PLAN",
            "PASS" if risk_pass else "FAIL",
            f"stop_pct={plan.stop_pct:.2%}, tp2_pct={plan.tp2_pct:.2%}, rr={plan.risk_reward:.2f}, risk_budget={plan.risk_budget_pct:.2%}",
        )
    )
    threshold = cfg.short_green_score if track == "S" else cfg.long_green_score
    amber = cfg.short_amber_score if track == "S" else cfg.long_amber_score
    checks.append(
        ValidationCheck(
            "TRACK_SCORE",
            "PASS" if score >= threshold else "AMBER" if score >= amber else "FAIL",
            f"score={score:.2f}, green_threshold={threshold:.2f}",
        )
    )
    checks.append(ValidationCheck("AUTOMATION_BOUNDARY", "PASS", "screening_output_only; broker_order_execution=False"))
    return checks


def _verdict(track: Track, score: float, checks: list[ValidationCheck], cfg: RecommendationConfig) -> tuple[Verdict, str]:
    fail_names = {c.name for c in checks if c.status == "FAIL"}
    pass_count = sum(1 for c in checks if c.status == "PASS")
    if "DATA_ROWS" in fail_names:
        return "RED_DATA_INSUFFICIENT", "데이터 부족으로 추천 차단"
    if "RISK_PLAN" in fail_names:
        return "ZERO_RISK_PLAN_FAILED", "손절/목표가/위험예산 구조 실패로 차단"

    if track == "S":
        if score >= cfg.short_green_score and pass_count >= 6:
            return "ELIGIBLE_RECOMMENDATION", "Track-S 추천 후보: 수동 승인 필요"
        if score >= cfg.short_amber_score:
            return "AMBER_REVIEW_ONLY", "Track-S 관찰 후보: 추가 확인 필요"
        return "RED_NOT_RECOMMENDED", "Track-S 기준 미달"

    if score >= cfg.long_green_score and pass_count >= 6:
        return "ACCUMULATE_RECOMMENDATION", "Track-L 누적 후보: 수동 승인 필요"
    if score >= cfg.long_amber_score:
        return "AMBER_WATCHLIST", "Track-L 관찰 후보: thesis/fundamental 확인 필요"
    return "RED_NOT_RECOMMENDED", "Track-L 기준 미달"


# ────────────────────────────────────────────────────────────────
# Engine
# ────────────────────────────────────────────────────────────────


class RecommendationEngine:
    def __init__(self, config: RecommendationConfig | None = None):
        self.config = config or RecommendationConfig()
        self.audit_logger = AuditLogger.for_output_dir(self.config.output_dir)
        self._ohlcv_cache: dict[tuple[str, str, bool, str, str | None], tuple[pd.DataFrame, str, dict]] = {}
        self._ohlcv_error_cache: dict[tuple[str, str, bool, str, str | None], str] = {}
        self._provider_metadata: list[dict] = []
        self._kevpe_events = load_kevpe_events(self.config.kevpe_events)

    def _ohlcv_cache_key(self, ticker: str) -> tuple[str, str, bool, str, str | None]:
        cfg = self.config
        return (ticker.strip().upper(), cfg.period, cfg.synthetic, cfg.data_provider, cfg.provider_config)

    def _load_ohlcv_cached(self, ticker: str) -> tuple[pd.DataFrame, str]:
        cfg = self.config
        key = self._ohlcv_cache_key(ticker)
        if key in self._ohlcv_cache:
            frame, source, _metadata = self._ohlcv_cache[key]
            return frame.copy(deep=False), source
        if key in self._ohlcv_error_cache:
            raise RuntimeError(self._ohlcv_error_cache[key])
        try:
            provider_result = load_ohlcv_result(
                ticker,
                cfg.period,
                synthetic=cfg.synthetic,
                data_provider=cfg.data_provider,
                provider_config=cfg.provider_config,
                audit_logger=self.audit_logger,
                command=cfg.audit_command,
            )
        except Exception as exc:
            self._ohlcv_error_cache[key] = str(exc)
            raise
        frame = provider_result.frame
        source = provider_result.source
        metadata = dict(provider_result.metadata or {})
        metadata.setdefault("provider_used", provider_result.provider_used)
        metadata.setdefault("source", provider_result.source)
        if provider_result.endpoint:
            metadata.setdefault("endpoint", provider_result.endpoint)
        if provider_result.fallback_reason:
            metadata.setdefault("fallback_reason", provider_result.fallback_reason)
        self._provider_metadata.append(metadata)
        self._ohlcv_cache[key] = (frame, source, metadata)
        return frame.copy(deep=False), source

    def evaluate_ticker(self, ticker: str, track: Track) -> RecommendationResult:
        cfg = self.config
        horizon = cfg.horizon_s if track == "S" else cfg.horizon_l
        df, data_source = self._load_ohlcv_cached(ticker)
        min_required = max(cfg.min_rows, horizon + 220)
        if len(df) < min_required:
            raise RuntimeError(f"{ticker}: 데이터 부족 rows={len(df)}, required={min_required}")

        feature_df = TechnicalIndicators(df).build_all(horizon=horizon)
        if feature_df.empty:
            raise RuntimeError(f"{ticker}: 피처 생성 결과가 비어 있습니다")
        model_stats = _fit_walk_forward_model(feature_df, horizon, cfg)
        prices = df.loc[feature_df.index, "Close"]
        signals = pd.Series(model_stats["backtest_probs"], index=feature_df.index)
        snap = _market_snapshot(df)
        plan = _risk_plan(track, snap, cfg, capital=cfg.capital)
        bt_cfg = BacktestConfig(
            initial_capital=100_000.0,
            threshold_buy=0.56 if track == "S" else 0.53,
            threshold_sell=0.45,
            stop_loss_pct=plan.stop_pct,
            take_profit_pct=plan.tp2_pct,
            risk_per_trade_pct=plan.risk_budget_pct,
            max_position_pct=plan.max_position_pct,
            max_monthly_loss_pct=0.05 if track == "S" else 0.12,
        )
        backtest = Backtester(bt_cfg).run(prices, signals)

        if track == "S":
            score, reasons = _score_track_s(model_stats["latest_prob"], snap, backtest, plan, model_stats, cfg)
        else:
            score, reasons = _score_track_l(model_stats["latest_prob"], snap, backtest, plan, model_stats, cfg)

        checks = _validation_checks(track, df, snap, model_stats, backtest, plan, score, cfg)
        honesty = evaluate_backtest_honesty(
            oof_coverage=float(model_stats["oof_coverage"]),
            min_oof_coverage=cfg.min_oof_coverage,
            sharpe=float(backtest.get("sharpe_ratio", 0.0)),
            min_sharpe=cfg.min_backtest_sharpe,
            mdd_pct=float(backtest.get("max_drawdown_pct", 0.0)),
            max_mdd_pct=cfg.max_mdd_pct_s if track == "S" else cfg.max_mdd_pct_l,
            total_return_pct=float(backtest.get("total_return_pct", 0.0)),
            transaction_cost_buffer_pct=cfg.transaction_cost_buffer_pct,
            cv_gap=int(model_stats["gap"]),
            horizon=horizon,
        )
        verdict, label = _verdict(track, score, checks, cfg)
        pass_count = sum(1 for check in checks if check.status == "PASS")
        ev = _expected_value_pct(model_stats["latest_prob"], plan)
        reasons = [f"data_source={data_source}", f"cv_gap={model_stats['gap']}"] + reasons + [label]

        # ── KEVPE risk overlay (supplementary only — never overrides Risk Gate) ──
        kevpe_result = get_kevpe_adapter().get_signal_for_ticker(df, self._events_for_ticker(ticker), as_of=pd.Timestamp.now().normalize())
        kevpe_supp = kevpe_signal_to_supplement(kevpe_result)

        return RecommendationResult(
            ticker=ticker,
            track=track,
            verdict=verdict,
            recommendation_rank_score=round(score, 2),
            candidate_label=label,
            screening_output_only=True,
            latest_close=round(float(snap["latest"]), 4),
            entry=plan.entry,
            stop=plan.stop,
            tp1=plan.tp1,
            tp2=plan.tp2,
            stop_pct=plan.stop_pct,
            tp2_pct=plan.tp2_pct,
            risk_reward=plan.risk_reward,
            risk_budget_pct=plan.risk_budget_pct,
            max_position_pct=plan.max_position_pct,
            suggested_quantity=plan.suggested_quantity,
            suggested_position_value=plan.suggested_position_value,
            direction_prob=round(float(model_stats["latest_prob"]), 4),
            expected_value_pct=ev,
            model_accuracy=round(float(model_stats["accuracy"]), 4),
            model_auc=round(float(model_stats["auc"]), 4),
            oof_coverage=round(float(model_stats["oof_coverage"]), 4),
            backtest_return_pct=round(float(backtest.get("total_return_pct", 0.0)), 2),
            backtest_sharpe=round(float(backtest.get("sharpe_ratio", 0.0)), 3),
            backtest_sortino=round(float(backtest.get("sortino_ratio", 0.0)), 3),
            backtest_mdd_pct=round(float(backtest.get("max_drawdown_pct", 0.0)), 2),
            profit_factor=backtest.get("profit_factor", 0.0),
            avg_dollar_volume_20d=round(float(snap["avg_dollar_volume_20d"]), 2),
            volume_ratio_20d=round(float(snap["volume_ratio_20d"]), 2),
            market_regime_score=round(float(snap["market_regime_score"]), 2),
            return_20d_pct=_pct(snap["return_20d"]),
            return_60d_pct=_pct(snap["return_60d"]),
            drawdown_252d_pct=_pct(snap["drawdown_252d"]),
            confirmations_passed=pass_count,
            confirmations_total=len(checks),
            validations=checks,
            reasons=reasons,
            generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            backtest_honesty=honesty,
            # KEVPE overlay fields (populated from supplementary signal)
            kevpe_available=kevpe_supp.get("kevpe_available", False),
            kevpe_regime=kevpe_supp.get("kevpe_regime"),
            kevpe_score=kevpe_supp.get("kevpe_score"),
            kevpe_expected_return_pct=kevpe_supp.get("kevpe_expected_return_pct"),
            kevpe_ci=kevpe_supp.get("kevpe_ci"),
            kevpe_confidence=kevpe_supp.get("kevpe_confidence"),
            kevpe_reason=kevpe_supp.get("kevpe_reason"),
        )

    def _events_for_ticker(self, ticker: str) -> list[dict]:
        clean = ticker.strip().upper()
        events: list[dict] = []
        for event in self._kevpe_events:
            event_ticker = str(event.get("ticker", "") or "").strip().upper()
            if event_ticker and event_ticker != clean:
                continue
            events.append(event)
        return events

    def run(self) -> list[RecommendationResult]:
        tracks: list[Track] = ["S", "L"] if self.config.track == "BOTH" else [self.config.track]  # type: ignore[list-item]
        results: list[RecommendationResult] = []
        for ticker in self.config.universe:
            clean_ticker = ticker.strip().upper()
            if not clean_ticker:
                continue
            for track in tracks:
                try:
                    results.append(self.evaluate_ticker(clean_ticker, track))
                except Exception as exc:
                    results.append(_error_result(clean_ticker, track, str(exc)))
        priority = {
            "ELIGIBLE_RECOMMENDATION": 0,
            "ACCUMULATE_RECOMMENDATION": 0,
            "AMBER_REVIEW_ONLY": 1,
            "AMBER_WATCHLIST": 1,
            "RED_NOT_RECOMMENDED": 2,
            "ZERO_RISK_PLAN_FAILED": 3,
            "RED_DATA_INSUFFICIENT": 4,
            "RED_DATA_OR_MODEL_ERROR": 5,
        }
        results.sort(key=lambda r: (priority.get(r.verdict, 9), -r.recommendation_rank_score, -r.expected_value_pct, r.ticker, r.track))
        return results[: self.config.top_n]

    def write_reports(self, results: list[RecommendationResult]) -> RecommendationRun:
        out_dir = Path(self.config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = out_dir / f"recommendations_algo_v2_{ts}.json"
        md_path = out_dir / f"recommendations_algo_v2_{ts}.md"
        errors = [r.to_dict() for r in results if r.verdict == "RED_DATA_OR_MODEL_ERROR"]
        honesty_summary = summarize_honesty([r.backtest_honesty or {} for r in results])
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "config": asdict(self.config),
            "disclaimer": "screening_output_only; manual approval required; no broker order execution; not financial advice",
            "algorithm_patch": "v2 leak-safe CV + ATR risk plan + fixed-risk sizing + OOF backtest",
            "audit_log_path": str(self.audit_logger.path),
            "provider_summary": self._provider_summary(),
            "backtest_honesty_summary": honesty_summary,
            "errors": errors,
            "results": [r.to_dict() for r in results],
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(render_markdown(results, self.config), encoding="utf-8")
        self.audit_logger.write(
            AuditEvent(
                event_type="backtest_honesty_summary",
                status="SUCCESS",
                command=self.config.audit_command,
                metadata=honesty_summary,
            )
        )
        return RecommendationRun(results=results, errors=errors, markdown_path=str(md_path), json_path=str(json_path), audit_path=str(self.audit_logger.path))

    def _provider_summary(self) -> dict | None:
        if not self._provider_metadata:
            return None
        status_order = {"PASS": 0, "AMBER": 1, "FAIL": 2}
        statuses = [str(item.get("provider_validation_status", "AMBER")) for item in self._provider_metadata]
        status = max(statuses, key=lambda item: status_order.get(item, 1))
        row_counts = [int(item["row_count"]) for item in self._provider_metadata if item.get("row_count") is not None]
        freshness_values = [int(item["freshness_days"]) for item in self._provider_metadata if item.get("freshness_days") is not None]
        last_dates = [str(item["last_date"]) for item in self._provider_metadata if item.get("last_date")]
        fallbacks = sorted({str(item["fallback_reason"]) for item in self._provider_metadata if item.get("fallback_reason")})
        return {
            "status": status,
            "providers_used": sorted({str(item.get("provider_used", "unknown")) for item in self._provider_metadata}),
            "event_count": len(self._provider_metadata),
            "row_count_min": min(row_counts) if row_counts else None,
            "last_date_max": max(last_dates) if last_dates else None,
            "freshness_days_max": max(freshness_values) if freshness_values else None,
            "fallbacks": fallbacks,
        }


def _error_result(ticker: str, track: Track, message: str) -> RecommendationResult:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fail = ValidationCheck("ERROR", "FAIL", message)
    return RecommendationResult(
        ticker=ticker,
        track=track,
        verdict="RED_DATA_OR_MODEL_ERROR",
        recommendation_rank_score=0.0,
        candidate_label="데이터/모델 오류로 추천 제외",
        screening_output_only=True,
        latest_close=0.0,
        entry=0.0,
        stop=0.0,
        tp1=0.0,
        tp2=0.0,
        stop_pct=0.0,
        tp2_pct=0.0,
        risk_reward=0.0,
        risk_budget_pct=0.0,
        max_position_pct=0.0,
        suggested_quantity=0.0,
        suggested_position_value=0.0,
        direction_prob=0.0,
        expected_value_pct=0.0,
        model_accuracy=0.0,
        model_auc=0.0,
        oof_coverage=0.0,
        backtest_return_pct=0.0,
        backtest_sharpe=0.0,
        backtest_sortino=0.0,
        backtest_mdd_pct=0.0,
        profit_factor=0.0,
        avg_dollar_volume_20d=0.0,
        volume_ratio_20d=0.0,
        market_regime_score=0.0,
        return_20d_pct=0.0,
        return_60d_pct=0.0,
        drawdown_252d_pct=0.0,
        confirmations_passed=0,
        confirmations_total=1,
        validations=[fail],
        reasons=[message],
        generated_at_utc=now,
        backtest_honesty={
            "status": "FAIL",
            "checks": [{"name": "ERROR", "status": "FAIL", "value": None, "threshold": None, "reason": message}],
            "passed": 0,
            "amber": 0,
            "failed": 1,
            "generated_at_utc": now,
        },
    )


def load_kevpe_events(path: str | None) -> list[dict]:
    if not path:
        return []
    event_path = Path(path)
    if not event_path.exists():
        raise FileNotFoundError(f"KEVPE event file not found: {event_path}")
    suffix = event_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(event_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("events", [])
        if not isinstance(payload, list):
            raise ValueError("KEVPE JSON event file must contain a list or an object with events")
        return [_normalize_kevpe_event(item) for item in payload if isinstance(item, dict)]
    if suffix == ".csv":
        frame = pd.read_csv(event_path)
        return [_normalize_kevpe_event(row) for row in frame.to_dict(orient="records")]
    raise ValueError(f"unsupported KEVPE event file extension: {event_path.suffix}")


def _normalize_kevpe_event(event: dict) -> dict:
    normalized = dict(event)
    topics = normalized.get("topics", ())
    if isinstance(topics, str):
        normalized["topics"] = tuple(item.strip() for item in topics.replace(";", ",").split(",") if item.strip())
    elif isinstance(topics, list):
        normalized["topics"] = tuple(str(item).strip() for item in topics if str(item).strip())
    elif not isinstance(topics, tuple):
        normalized["topics"] = ()
    return normalized


def render_markdown(results: list[RecommendationResult], cfg: RecommendationConfig) -> str:
    lines = [
        "# Stock Recommendation Report — Algorithm v2",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.",
        "",
        "Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.",
        "",
        f"Universe: {', '.join(cfg.universe)}",
        f"Track: {cfg.track} | Period: {cfg.period} | Top-N: {cfg.top_n}",
        f"Data provider: {cfg.data_provider} | Synthetic flag: {cfg.synthetic}",
        f"Audit log: {Path(cfg.output_dir) / 'audit_log.jsonl'}",
        "",
        "| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, r in enumerate(results, start=1):
        evidence = "; ".join(r.reasons[:4]).replace("|", "/")
        lines.append(
            f"| {rank} | {r.ticker} | {r.track} | {r.verdict} | {r.recommendation_rank_score:.2f} | "
            f"{r.direction_prob:.2%} | {r.expected_value_pct:.2f} | {r.entry:.2f} | {r.stop:.2f} | {r.tp2:.2f} | "
            f"{r.risk_reward:.2f} | {r.risk_budget_pct:.2%} | {r.max_position_pct:.2%} | {r.suggested_quantity:.2f} | "
            f"{r.confirmations_passed}/{r.confirmations_total} | {evidence} |"
        )
    lines += ["", "## Validation details", ""]
    for r in results:
        lines.append(f"### {r.ticker} / Track-{r.track} / {r.verdict}")
        lines.append(f"- Backtest: return={r.backtest_return_pct:.2f}%, Sharpe={r.backtest_sharpe:.3f}, Sortino={r.backtest_sortino:.3f}, MDD={r.backtest_mdd_pct:.2f}%")
        if r.backtest_honesty:
            lines.append(
                f"- Backtest honesty: {r.backtest_honesty.get('status')} "
                f"(pass={r.backtest_honesty.get('passed', 0)}, amber={r.backtest_honesty.get('amber', 0)}, fail={r.backtest_honesty.get('failed', 0)})"
            )
        lines.append(f"- Model: prob={r.direction_prob:.2%}, acc={r.model_accuracy:.2%}, auc={r.model_auc:.3f}, oof_coverage={r.oof_coverage:.2%}")
        lines.append(f"- Risk plan: stop={r.stop_pct:.2%}, tp2={r.tp2_pct:.2%}, R/R={r.risk_reward:.2f}, position_value={r.suggested_position_value:.2f}")
        for check in r.validations:
            lines.append(f"- {check.name}: {check.status} — {check.evidence}")
        lines.append("")
    return "\n".join(lines)


def run_recommendation_cli(args) -> int:
    universe = [item.strip().upper() for item in str(args.universe).split(",") if item.strip()]
    cfg = RecommendationConfig(
        universe=universe or DEFAULT_UNIVERSE.copy(),
        track=args.track,
        period=args.period,
        top_n=args.top,
        synthetic=args.synthetic,
        output_dir=args.output_dir,
        model_kind=args.model_kind,
        xgb_device=args.xgb_device,
        cv_gap=args.cv_gap,
        data_provider=getattr(args, "data_provider", "auto"),
        provider_config=getattr(args, "provider_config", None),
    )
    engine = RecommendationEngine(cfg)
    results = engine.run()
    paths = engine.write_reports(results)
    print(render_markdown(results, cfg))
    print(f"\nReport saved: {paths['markdown']}")
    print(f"JSON saved:   {paths['json']}")
    print(f"Audit saved:  {paths['audit']}")
    return 0
