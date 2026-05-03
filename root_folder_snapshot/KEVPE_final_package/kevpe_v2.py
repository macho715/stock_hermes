"""
Korea Event-Volatility Pattern Engine — v2 (Investment-Grade Upgrade)
=====================================================================

목적
----
v1 프로토타입(robust z-score + 코사인 유사도 + 단순 weight 백테스트)을
실제 자본 운용에서 참고 가능한 수준으로 끌어올린 버전.

v1 대비 핵심 개선
-----------------
1) KevpeConfig dataclass — 모든 튜닝 파라미터 단일 진입점
2) FeatureScaler — 학습 구간만 fit (look-ahead 제거), 코사인 유사도 정상화
3) Regime hysteresis (confirm_days + cooloff_days) — 신호 채터링 방지
4) 거래비용·슬리피지 반영 백테스트 (cost_bps_per_turn × |Δweight|)
5) Volatility-target position sizing (옵션, target_annual_vol)
6) Drawdown circuit breaker — equity DD > threshold 시 강제 디리스킹
7) Bootstrap confidence interval — 유사 패턴 기대수익의 [5,95]% 분포
8) Walk-forward 검증 — purged k-fold + embargo, OOS 성능지표
9) 결정론적 as_of — `current_signal_v2` 는 today() 의존 제거
10) 종합 성능지표(Sharpe, Sortino, Calmar, MDD, CVaR5, hit-rate, turnover, cost-drag)

주의
----
- 본 엔진은 리스크 참고 신호이며, 매수·매도 추천이 아니다.
- 실운영 전 (a) 공식/유료 데이터 계약, (b) 실제 체결 슬리피지 측정,
  (c) 다중 자산 포트폴리오 조합, (d) 컴플라이언스 검토가 필요하다.
"""

from __future__ import annotations

import math
import urllib.parse
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

REQUIRED_OHLCV_COLUMNS = {"date", "open", "high", "low", "close"}
REGIMES = ("GREEN", "AMBER", "RED")
DEFAULT_REGIME_WEIGHTS = {"GREEN": 1.00, "AMBER": 0.50, "RED": 0.20}


# =============================================================================
# 1. Config
# =============================================================================

@dataclass(frozen=True)
class KevpeConfig:
    """모든 튜닝 파라미터의 단일 소스. 백테스트/운영 reproducibility 보장."""
    # --- volatility window detection ---
    z_window: int = 20
    z_threshold: float = 2.50
    shock_quantile: float = 0.95
    min_abs_return: float = 0.015
    merge_gap_days: int = 2
    # --- event matching ---
    pre_days: int = 2
    post_days: int = 3
    max_events_per_window: int = 5
    # --- pattern signal engine ---
    top_k: int = 7
    min_similarity: float = 0.30
    bootstrap_n: int = 500
    bootstrap_seed: int = 42
    # --- regime thresholds (risk_score 0~1) ---
    red_threshold: float = 0.70
    amber_threshold: float = 0.45
    # --- hysteresis ---
    confirm_days: int = 2
    cooloff_days: int = 3
    # --- backtest cost model ---
    cost_bps_per_turn: float = 5.0
    max_gross_leverage: float = 1.0
    realized_vol_window: int = 20
    vol_target_annual: Optional[float] = None
    dd_circuit_breaker: float = 0.20
    dd_recovery_threshold: float = 0.05
    regime_weights: Mapping[str, float] = field(
        default_factory=lambda: dict(DEFAULT_REGIME_WEIGHTS)
    )
    # --- walk-forward ---
    wf_n_folds: int = 5
    wf_embargo_days: int = 5
    wf_min_train_size: int = 60
    # --- annualization ---
    trading_days: int = 252


def _override_cfg(cfg: KevpeConfig, **kw) -> KevpeConfig:
    d = asdict(cfg)
    d.update(kw)
    rw = d.pop("regime_weights")
    return KevpeConfig(**d, regime_weights=rw)


# =============================================================================
# 2. Validation & robust statistics  (v1 호환)
# =============================================================================

def validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_OHLCV_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"OHLCV 필수 컬럼 누락: {sorted(missing)}")
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if "volume" in out.columns:
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0.0)
    else:
        out["volume"] = 0.0
    out = out.dropna(subset=["open", "high", "low", "close"])
    if len(out) < 30:
        raise ValueError("OHLCV 데이터가 너무 짧음: 최소 30 trading days 권장")
    return out


def robust_zscore(series: pd.Series, window: int = 20) -> pd.Series:
    """MAD 기반 robust z. fat-tail 분포에서 표준 z 보다 안정적."""
    s = pd.to_numeric(series, errors="coerce")
    med = s.rolling(window=window, min_periods=max(5, window // 3)).median()
    mad = (s - med).abs().rolling(window=window, min_periods=max(5, window // 3)).median()
    denom = 1.4826 * mad
    fallback = s.rolling(window=window, min_periods=max(5, window // 3)).std(ddof=0)
    denom = denom.where(denom > 1e-12, fallback)
    denom = denom.where(denom > 1e-12, np.nan)
    z = (s - med) / denom
    return z.replace([np.inf, -np.inf], np.nan).fillna(0.0)


# =============================================================================
# 3. Volatility window detection
# =============================================================================

def detect_volatility_windows(
    ohlcv: pd.DataFrame,
    config: Optional[KevpeConfig] = None,
    **overrides,
) -> pd.DataFrame:
    cfg = config or KevpeConfig()
    if overrides:
        cfg = _override_cfg(cfg, **overrides)

    df = validate_ohlcv(ohlcv)
    df["ret"] = df["close"].pct_change().fillna(0.0)
    df["abs_ret"] = df["ret"].abs()
    df["rz"] = robust_zscore(df["ret"], window=cfg.z_window).abs()

    q = float(df["abs_ret"].quantile(cfg.shock_quantile))
    dyn_threshold = max(q, cfg.min_abs_return)
    shock = (df["rz"] >= cfg.z_threshold) | (df["abs_ret"] >= dyn_threshold)
    shock &= df["abs_ret"] >= cfg.min_abs_return
    shock_idx = df.index[shock].tolist()

    if not shock_idx:
        return pd.DataFrame(columns=[
            "start", "end", "days", "direction", "peak_abs_ret",
            "cum_return", "vol_z_max", "severity"
        ])

    groups: List[List[int]] = [[shock_idx[0]]]
    for idx in shock_idx[1:]:
        gap = (df.loc[idx, "date"] - df.loc[groups[-1][-1], "date"]).days
        if gap <= cfg.merge_gap_days:
            groups[-1].append(idx)
        else:
            groups.append([idx])

    rows = []
    for g in groups:
        sub = df.loc[g]
        cum_ret = float((1.0 + sub["ret"]).prod() - 1.0)
        rows.append({
            "start": sub["date"].min(),
            "end": sub["date"].max(),
            "days": int(len(g)),
            "direction": "UP" if cum_ret > 0 else "DOWN",
            "peak_abs_ret": float(sub["abs_ret"].max()),
            "cum_return": cum_ret,
            "vol_z_max": float(sub["rz"].max()),
            "severity": float(
                0.60 * min(float(sub["rz"].max()) / 5.0, 2.0)
                + 0.40 * min(float(sub["abs_ret"].max()) / 0.05, 2.0)
            ),
        })
    return (pd.DataFrame(rows)
            .sort_values(["severity", "start"], ascending=[False, True])
            .reset_index(drop=True))


# =============================================================================
# 4. Event objects
# =============================================================================

@dataclass(frozen=True)
class Event:
    date: pd.Timestamp
    headline: str
    country: str = ""
    tone: float = 0.0
    volume: float = 1.0
    source_diversity: float = 1.0
    topics: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Signal:
    date: pd.Timestamp
    regime: str
    score: float
    direction_bias: str
    reason: str
    expected_return: float = 0.0
    ci_low: float = 0.0
    ci_high: float = 0.0
    similarity_mean: float = 0.0
    n_matches: int = 0


TOPIC_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "war_conflict": ("war", "attack", "missile", "invasion", "conflict", "ceasefire", "terror", "military"),
    "pandemic_health": ("pandemic", "covid", "virus", "outbreak", "disease", "lockdown"),
    "central_bank": ("fed", "fomc", "rate", "interest", "inflation", "central bank", "boj", "ecb", "bok"),
    "oil_energy": ("oil", "crude", "opec", "energy", "gas", "middle east", "iran"),
    "fx_currency": ("won", "dollar", "currency", "exchange rate", "usdkrw", "yen"),
    "semiconductor_ai": ("semiconductor", "chip", "hbm", "ai", "nvidia", "samsung", "sk hynix", "memory"),
    "trade_supply": ("export", "import", "tariff", "sanction", "supply chain", "shipping", "port"),
    "politics_policy": ("election", "government", "policy", "regulation", "tax", "budget"),
    "disaster": ("earthquake", "tsunami", "flood", "hurricane", "fire", "disaster"),
}

TOPIC_WEIGHTS = {
    "war_conflict": 1.00, "pandemic_health": 0.95, "central_bank": 0.80,
    "oil_energy": 0.75, "fx_currency": 0.70, "semiconductor_ai": 0.65,
    "trade_supply": 0.65, "politics_policy": 0.55, "disaster": 0.60,
    "general": 0.30,
}


def classify_event_topics(text: str) -> Tuple[str, ...]:
    t = (text or "").lower()
    topics = [topic for topic, keys in TOPIC_KEYWORDS.items() if any(k in t for k in keys)]
    return tuple(topics) if topics else ("general",)


def event_relevance_score(event: Event, market_country: str = "Korea") -> float:
    topics = event.topics or classify_event_topics(event.headline)
    topic_score = max(TOPIC_WEIGHTS.get(t, 0.30) for t in topics)
    vol_score = math.log1p(max(float(event.volume), 0.0)) / math.log1p(1000.0)
    div_score = math.log1p(max(float(event.source_diversity), 0.0)) / math.log1p(100.0)
    tone_risk = min(abs(float(event.tone)) / 10.0, 1.0)
    country_text = f"{event.country} {event.headline}".lower()
    geo_score = 1.0 if any(k in country_text for k in
                           ["korea", "south korea", "seoul", "krx", "kospi"]) else 0.55
    score = (0.35 * topic_score + 0.25 * vol_score + 0.20 * div_score
             + 0.10 * tone_risk + 0.10 * geo_score)
    return float(np.clip(score, 0.0, 1.0))


def match_events_to_windows(
    windows: pd.DataFrame,
    events: Sequence[Event],
    config: Optional[KevpeConfig] = None,
) -> pd.DataFrame:
    cfg = config or KevpeConfig()
    if windows.empty:
        return pd.DataFrame(columns=["window_start", "window_end", "event_date",
                                     "headline", "match_score", "topics"])
    rows = []
    for _, w in windows.iterrows():
        start = pd.to_datetime(w["start"]) - pd.Timedelta(days=cfg.pre_days)
        end = pd.to_datetime(w["end"]) + pd.Timedelta(days=cfg.post_days)
        candidates = [ev for ev in events if start <= pd.to_datetime(ev.date) <= end]
        scored = sorted(
            candidates,
            key=lambda ev: event_relevance_score(ev) * (1.0 + float(w["severity"])),
            reverse=True,
        )[:cfg.max_events_per_window]
        for ev in scored:
            rows.append({
                "window_start": pd.to_datetime(w["start"]),
                "window_end": pd.to_datetime(w["end"]),
                "event_date": pd.to_datetime(ev.date),
                "headline": ev.headline,
                "match_score": event_relevance_score(ev) * (1.0 + float(w["severity"])),
                "topics": ",".join(ev.topics or classify_event_topics(ev.headline)),
                "market_direction": w["direction"],
                "market_cum_return": float(w["cum_return"]),
                "severity": float(w["severity"]),
            })
    return pd.DataFrame(rows).sort_values(["match_score"], ascending=False).reset_index(drop=True)


def feature_vector_from_event(event: Event, market_ret: float = 0.0,
                              vol_z: float = 0.0) -> Dict[str, float]:
    topics = set(event.topics or classify_event_topics(event.headline))
    return {
        "event_score": event_relevance_score(event),
        "tone": float(event.tone),
        "volume_log": math.log1p(max(event.volume, 0.0)),
        "source_diversity_log": math.log1p(max(event.source_diversity, 0.0)),
        "market_ret": float(market_ret),
        "vol_z": float(vol_z),
        "is_war": float("war_conflict" in topics),
        "is_rate": float("central_bank" in topics),
        "is_oil": float("oil_energy" in topics),
        "is_chip_ai": float("semiconductor_ai" in topics),
        "is_fx": float("fx_currency" in topics),
    }


# =============================================================================
# 5. FeatureScaler — 학습 구간만 fit (look-ahead 제거)
# =============================================================================

@dataclass
class FeatureScaler:
    """Z-score 정규화. fit() 은 학습 구간 통계만 사용한다.

    v1 cosine similarity 는 event_score(0~1) 와 volume_log(0~7) 를 한 벡터에서
    동등하게 다뤄 큰 스케일이 지배. v2 는 표준화 후 비교한다.
    """
    keys: Tuple[str, ...] = ()
    mean: np.ndarray = field(default_factory=lambda: np.zeros(0))
    std: np.ndarray = field(default_factory=lambda: np.ones(0))

    def fit(self, features: Sequence[Mapping[str, float]]) -> "FeatureScaler":
        if not features:
            raise ValueError("FeatureScaler.fit: 빈 feature 리스트")
        keys = tuple(sorted({k for f in features for k in f.keys()}))
        mat = np.array([[float(f.get(k, 0.0)) for k in keys] for f in features], dtype=float)
        mean = mat.mean(axis=0)
        std = mat.std(axis=0, ddof=0)
        std = np.where(std < 1e-9, 1.0, std)
        self.keys = keys
        self.mean = mean
        self.std = std
        return self

    def transform(self, feature: Mapping[str, float]) -> np.ndarray:
        if not self.keys:
            raise RuntimeError("FeatureScaler 미fit")
        v = np.array([float(feature.get(k, 0.0)) for k in self.keys], dtype=float)
        return (v - self.mean) / self.std

    def fit_transform(self, features: Sequence[Mapping[str, float]]) -> np.ndarray:
        self.fit(features)
        return np.vstack([self.transform(f) for f in features])


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    den = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / den) if den > 1e-12 else 0.0


# =============================================================================
# 6. Bootstrap CI
# =============================================================================

def bootstrap_pattern_ci(
    weighted_returns: Sequence[float],
    weights: Sequence[float],
    n_bootstrap: int = 500,
    seed: int = 42,
    ci: Tuple[float, float] = (5.0, 95.0),
) -> Tuple[float, float, float]:
    """가중 부트스트랩으로 expected forward return 의 (low, mean, high) 반환."""
    rets = np.asarray(weighted_returns, dtype=float)
    w = np.asarray(weights, dtype=float)
    if rets.size == 0:
        return 0.0, 0.0, 0.0
    if w.sum() <= 1e-12:
        w = np.ones_like(rets)
    p = w / w.sum()
    rng = np.random.default_rng(seed)
    n = rets.size
    samples = rng.choice(rets, size=(int(n_bootstrap), n), replace=True, p=p)
    means = samples.mean(axis=1)
    lo, hi = np.percentile(means, ci)
    return float(lo), float(means.mean()), float(hi)


# =============================================================================
# 7. v2 Signal generator — 정규화·결정론·CI 포함
# =============================================================================

def current_signal_v2(
    current_feature: Mapping[str, float],
    historical_features: Sequence[Mapping[str, float]],
    historical_forward_returns: Sequence[float],
    config: Optional[KevpeConfig] = None,
    scaler: Optional[FeatureScaler] = None,
    as_of: Optional[pd.Timestamp] = None,
) -> Signal:
    cfg = config or KevpeConfig()
    ts = pd.to_datetime(as_of) if as_of is not None else pd.Timestamp("1970-01-01")

    if not historical_features or len(historical_forward_returns) == 0:
        return Signal(ts, "AMBER", 0.50, "NEUTRAL", "역사 패턴 부족")
    if len(historical_features) != len(historical_forward_returns):
        raise ValueError("historical_features 와 forward_returns 길이 불일치")

    sc = scaler or FeatureScaler().fit(historical_features)
    cur_vec = sc.transform(current_feature)
    hist_vecs = np.vstack([sc.transform(f) for f in historical_features])
    rets = np.asarray(historical_forward_returns, dtype=float)

    sims = np.array([_cosine(cur_vec, h) for h in hist_vecs])
    order = np.argsort(-sims)
    top_idx = order[: cfg.top_k]
    top_sims = sims[top_idx]
    top_rets = rets[top_idx]

    keep = top_sims >= cfg.min_similarity
    if not keep.any():
        return Signal(ts, "AMBER", 0.50, "NEUTRAL",
                      f"유사도 < {cfg.min_similarity:.2f} (best={top_sims.max():.2f})",
                      n_matches=0, similarity_mean=float(top_sims.mean()))
    top_sims = top_sims[keep]
    top_rets = top_rets[keep]

    weights = np.clip(top_sims, 0.0, None)
    if weights.sum() <= 1e-12:
        weights = np.ones_like(top_sims)
    expected = float(np.average(top_rets, weights=weights))
    similarity = float(top_sims.mean())

    ci_lo, ci_mean, ci_hi = bootstrap_pattern_ci(
        top_rets, weights,
        n_bootstrap=cfg.bootstrap_n, seed=cfg.bootstrap_seed,
    )

    event_score = float(current_feature.get("event_score", 0.0))
    vol_z = abs(float(current_feature.get("vol_z", 0.0)))
    tone = float(current_feature.get("tone", 0.0))

    risk_score = (
        0.35 * min(event_score, 1.0)
        + 0.25 * min(vol_z / 5.0, 1.0)
        + 0.20 * max(-tone / 10.0, 0.0)
        + 0.20 * max(-expected / 0.05, 0.0)
    )
    risk_score = float(np.clip(risk_score, 0.0, 1.0))

    if risk_score >= cfg.red_threshold:
        regime, bias = "RED", "RISK_OFF"
    elif risk_score >= cfg.amber_threshold:
        regime, bias = "AMBER", "NEUTRAL"
    else:
        regime, bias = "GREEN", "RISK_ON"

    reason = (f"sim={similarity:.2f}, E[r]={expected:+.2%} "
              f"[CI5={ci_lo:+.2%}, CI95={ci_hi:+.2%}], evt={event_score:.2f}, "
              f"vol_z={vol_z:.2f}, n={len(top_rets)}")
    return Signal(ts, regime, risk_score, bias, reason,
                  expected_return=expected, ci_low=ci_lo, ci_high=ci_hi,
                  similarity_mean=similarity, n_matches=int(len(top_rets)))


# =============================================================================
# 8. Regime hysteresis — 채터링 방지 FSM
# =============================================================================

def apply_regime_hysteresis(
    signals: pd.DataFrame,
    config: Optional[KevpeConfig] = None,
) -> pd.DataFrame:
    """raw regime 시퀀스를 confirm_days·cooloff_days 로 안정화.

    규칙:
      - 새 regime 이 confirm_days 일 연속 관측되어야 전환
      - 한 번 전환되면 cooloff_days 동안 반대 방향 전환 금지
      - 더 보수적(GREEN→AMBER→RED) 방향은 안전을 위해 즉시 전환
    """
    cfg = config or KevpeConfig()
    if signals.empty:
        return signals.copy()

    df = signals.sort_values("date").reset_index(drop=True).copy()
    raw = df["regime"].astype(str).tolist()
    n = len(raw)
    severity = {"GREEN": 0, "AMBER": 1, "RED": 2}
    out = [raw[0]] * n
    last_change_idx = 0
    current = raw[0]

    for i in range(1, n):
        candidate = raw[i]
        if candidate == current:
            out[i] = current
            continue
        if severity.get(candidate, 1) > severity.get(current, 1):
            current = candidate
            last_change_idx = i
            out[i] = current
            continue
        if i - last_change_idx < cfg.cooloff_days:
            out[i] = current
            continue
        lookback_start = max(0, i - cfg.confirm_days + 1)
        if all(raw[k] == candidate for k in range(lookback_start, i + 1)) and \
           (i - lookback_start + 1) >= cfg.confirm_days:
            current = candidate
            last_change_idx = i
            out[i] = current
        else:
            out[i] = current

    df["regime_raw"] = raw
    df["regime"] = out
    return df


# =============================================================================
# 9. Performance metrics
# =============================================================================

@dataclass(frozen=True)
class PerformanceStats:
    n_days: int
    ann_return: float
    ann_vol: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    cvar_5: float
    hit_rate: float
    turnover_ann: float
    gross_total_return: float
    net_total_return: float
    cost_drag: float


def compute_performance_stats(
    daily: pd.DataFrame,
    trading_days: int = 252,
) -> PerformanceStats:
    """daily DataFrame 필요 컬럼: ret, gross_ret, net_ret, weight."""
    n = len(daily)
    if n == 0:
        return PerformanceStats(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    net = daily["net_ret"].fillna(0.0).to_numpy()
    gross = daily["gross_ret"].fillna(0.0).to_numpy()
    weight = daily["weight"].fillna(0.0).to_numpy()

    ann_ret = float((1 + net).prod() ** (trading_days / n) - 1) if n > 0 else 0.0
    ann_vol = float(net.std(ddof=0) * math.sqrt(trading_days))
    sharpe = float(ann_ret / ann_vol) if ann_vol > 1e-12 else 0.0
    downside = net[net < 0]
    dn_vol = float(downside.std(ddof=0) * math.sqrt(trading_days)) if downside.size else 0.0
    sortino = float(ann_ret / dn_vol) if dn_vol > 1e-12 else 0.0

    eq = (1 + net).cumprod()
    peak = np.maximum.accumulate(eq)
    dd = (eq / peak) - 1.0
    mdd = float(dd.min())
    calmar = float(ann_ret / abs(mdd)) if abs(mdd) > 1e-12 else 0.0

    cvar5 = float(np.mean(np.sort(net)[: max(1, int(0.05 * n))]))
    hit_rate = float((net > 0).sum() / n)
    turnover_daily = float(np.mean(np.abs(np.diff(weight, prepend=weight[0]))))
    turnover_ann = turnover_daily * trading_days

    gross_total = float((1 + gross).prod() - 1)
    net_total = float((1 + net).prod() - 1)
    cost_drag = gross_total - net_total

    return PerformanceStats(
        n_days=n, ann_return=ann_ret, ann_vol=ann_vol,
        sharpe=sharpe, sortino=sortino, max_drawdown=mdd, calmar=calmar,
        cvar_5=cvar5, hit_rate=hit_rate, turnover_ann=turnover_ann,
        gross_total_return=gross_total, net_total_return=net_total,
        cost_drag=cost_drag,
    )


# =============================================================================
# 10. Backtest v2 — 비용·슬리피지·vol-target·DD circuit breaker
# =============================================================================

def backtest_v2(
    ohlcv: pd.DataFrame,
    signals: pd.DataFrame,
    config: Optional[KevpeConfig] = None,
) -> Dict[str, object]:
    """투자 등급 백테스트.

    look-ahead 방지:
      - 신호 weight 는 t+1 일부터 적용
      - vol-target 은 t-1 까지의 rolling std 만 사용
    cost:
      - |Δw| × cost_bps_per_turn / 1e4 만큼 net_ret 차감
    DD circuit breaker:
      - equity drawdown <= -cfg.dd_circuit_breaker → weight 강제 0
      - drawdown 이 dd_recovery_threshold 이내로 회복되면 해제
    """
    cfg = config or KevpeConfig()
    df = validate_ohlcv(ohlcv)[["date", "close"]].copy()
    df["ret"] = df["close"].pct_change().fillna(0.0)

    sig = signals.copy()
    sig["date"] = pd.to_datetime(sig["date"])
    rw = dict(cfg.regime_weights)
    sig["weight"] = sig["regime"].map(rw)
    sig = sig[["date", "weight"]].dropna()

    df = df.merge(sig, on="date", how="left")
    df["weight"] = df["weight"].ffill().fillna(1.0)

    if cfg.vol_target_annual is not None:
        rv = df["ret"].rolling(cfg.realized_vol_window, min_periods=5).std(ddof=0).shift(1)
        rv_ann = rv * math.sqrt(cfg.trading_days)
        scale = (cfg.vol_target_annual / rv_ann).clip(upper=cfg.max_gross_leverage).fillna(1.0)
        df["weight"] = (df["weight"] * scale).clip(upper=cfg.max_gross_leverage)

    df["target_weight"] = df["weight"]
    df["exec_weight"] = df["target_weight"].shift(1).fillna(1.0)

    n = len(df)
    exec_w = df["exec_weight"].to_numpy().copy()
    ret = df["ret"].to_numpy()
    gross_ret = exec_w * ret
    eq = np.empty(n)
    peak = -np.inf
    breaker_on = False
    cur_eq = 1.0
    for i in range(n):
        peak = max(peak, cur_eq)
        dd = cur_eq / peak - 1.0
        if not breaker_on and dd <= -cfg.dd_circuit_breaker:
            breaker_on = True
        elif breaker_on and dd >= -cfg.dd_recovery_threshold:
            breaker_on = False
        if breaker_on:
            exec_w[i] = 0.0
        gross_ret[i] = exec_w[i] * ret[i]
        cur_eq = cur_eq * (1 + gross_ret[i])
        eq[i] = cur_eq

    dw = np.abs(np.diff(exec_w, prepend=exec_w[0]))
    cost = dw * (cfg.cost_bps_per_turn / 1e4)
    net_ret = gross_ret - cost

    df["exec_weight"] = exec_w
    df["gross_ret"] = gross_ret
    df["cost"] = cost
    df["net_ret"] = net_ret
    df["equity"] = (1 + df["net_ret"]).cumprod()
    df["drawdown"] = df["equity"] / df["equity"].cummax() - 1.0
    df["weight"] = df["target_weight"]

    stats = compute_performance_stats(df, trading_days=cfg.trading_days)

    bh = pd.DataFrame({"date": df["date"], "ret": df["ret"], "weight": 1.0,
                       "gross_ret": df["ret"], "net_ret": df["ret"]})
    bh_stats = compute_performance_stats(bh, trading_days=cfg.trading_days)

    return {
        "daily": df,
        "stats": stats,
        "buy_and_hold_stats": bh_stats,
    }


def backtest_risk_overlay(ohlcv: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    """v1 시그니처 유지 (cost=0, no breaker). 기존 코드와 호환."""
    cfg = KevpeConfig(cost_bps_per_turn=0.0, dd_circuit_breaker=10.0,
                      vol_target_annual=None)
    res = backtest_v2(ohlcv, signals, cfg)
    daily = res["daily"]
    out = daily[["date", "close", "ret", "exec_weight"]].copy()
    out["weight"] = daily["target_weight"]
    out["strategy_ret"] = daily["gross_ret"]
    out["equity"] = (1 + out["strategy_ret"]).cumprod()
    return out


# =============================================================================
# 11. Walk-forward validation
# =============================================================================

def walk_forward_validate(
    ohlcv: pd.DataFrame,
    historical_features: Sequence[Mapping[str, float]],
    historical_forward_returns: Sequence[float],
    feature_dates: Sequence[pd.Timestamp],
    config: Optional[KevpeConfig] = None,
) -> pd.DataFrame:
    """purged k-fold + embargo. fold 별 OOS 성능지표 반환.

    가정:
      - feature i 는 시점 feature_dates[i] 에 관측되었고,
        forward_return 은 그 이후 H 영업일 누적 수익이다 (별도 정의).
      - fold 별로 train (정규화 fit + 패턴풀) → test (예측) 분리.
      - embargo: train 끝 ~ test 시작 사이 wf_embargo_days 일 강제 공백.
    """
    cfg = config or KevpeConfig()
    n = len(historical_features)
    if n < cfg.wf_min_train_size + cfg.wf_n_folds:
        raise ValueError(
            f"walk-forward 데이터 부족: n={n}, min_train={cfg.wf_min_train_size}, "
            f"folds={cfg.wf_n_folds}"
        )

    feats = list(historical_features)
    rets = np.asarray(historical_forward_returns, dtype=float)
    dates = pd.to_datetime(pd.Series(feature_dates)).reset_index(drop=True)

    fold_size = max(1, (n - cfg.wf_min_train_size) // cfg.wf_n_folds)
    rows = []
    for k in range(cfg.wf_n_folds):
        train_end = cfg.wf_min_train_size + k * fold_size
        test_start = train_end + cfg.wf_embargo_days
        test_end = min(n, test_start + fold_size)
        if test_start >= n or test_end <= test_start:
            continue
        train_idx = list(range(0, train_end))
        test_idx = list(range(test_start, test_end))
        scaler = FeatureScaler().fit([feats[i] for i in train_idx])

        oos_preds, oos_actual = [], []
        for j in test_idx:
            sig = current_signal_v2(
                current_feature=feats[j],
                historical_features=[feats[i] for i in train_idx],
                historical_forward_returns=[rets[i] for i in train_idx],
                config=cfg, scaler=scaler, as_of=dates.iloc[j],
            )
            oos_preds.append(sig.expected_return)
            oos_actual.append(rets[j])

        preds = np.array(oos_preds)
        actual = np.array(oos_actual)
        dir_hit = float(np.mean(np.sign(preds) == np.sign(actual))) if len(preds) else 0.0
        if actual.size and actual.var() > 1e-12:
            sse = float(((actual - preds) ** 2).sum())
            sst = float(((actual - actual.mean()) ** 2).sum())
            r2 = 1.0 - sse / sst
        else:
            r2 = 0.0
        rows.append({
            "fold": k,
            "train_n": len(train_idx),
            "test_n": len(test_idx),
            "embargo_days": cfg.wf_embargo_days,
            "dir_hit_rate": dir_hit,
            "mean_pred": float(preds.mean()) if preds.size else 0.0,
            "mean_actual": float(actual.mean()) if actual.size else 0.0,
            "r2_oos": r2,
        })
    return pd.DataFrame(rows)


# =============================================================================
# 12. GDELT URL helpers
# =============================================================================

def gdelt_doc_timeline_url(query: str, start: date, end: date,
                           mode: str = "timelinevolraw") -> str:
    params = {
        "query": query, "mode": mode, "format": "json",
        "startdatetime": start.strftime("%Y%m%d") + "000000",
        "enddatetime": end.strftime("%Y%m%d") + "235959",
    }
    return "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)


def gdelt_doc_article_url(query: str, start: date, end: date,
                          maxrecords: int = 250) -> str:
    params = {
        "query": query, "mode": "artlist", "format": "json",
        "maxrecords": maxrecords, "sort": "datedesc",
        "startdatetime": start.strftime("%Y%m%d") + "000000",
        "enddatetime": end.strftime("%Y%m%d") + "235959",
    }
    return "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)


# =============================================================================
# 13. End-to-end pipeline
# =============================================================================

def run_pipeline_v2(
    ohlcv: pd.DataFrame,
    events: Sequence[Event],
    config: Optional[KevpeConfig] = None,
) -> Dict[str, object]:
    """단일 진입점: 윈도우 → 매칭. raw signals 는 외부에서 주입 후 backtest_v2 호출."""
    cfg = config or KevpeConfig()
    windows = detect_volatility_windows(ohlcv, cfg)
    matches = match_events_to_windows(windows, events, cfg)
    return {"windows": windows, "matches": matches, "config": cfg}


__all__ = [
    "REQUIRED_OHLCV_COLUMNS", "REGIMES", "DEFAULT_REGIME_WEIGHTS",
    "KevpeConfig", "Event", "Signal", "FeatureScaler", "PerformanceStats",
    "validate_ohlcv", "robust_zscore",
    "detect_volatility_windows", "classify_event_topics", "event_relevance_score",
    "match_events_to_windows", "feature_vector_from_event",
    "bootstrap_pattern_ci", "current_signal_v2",
    "apply_regime_hysteresis", "compute_performance_stats",
    "backtest_v2", "backtest_risk_overlay",
    "walk_forward_validate",
    "gdelt_doc_timeline_url", "gdelt_doc_article_url",
    "run_pipeline_v2",
]
