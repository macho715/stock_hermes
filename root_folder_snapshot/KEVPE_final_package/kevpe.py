
"""
Korea Event-Volatility Pattern Engine (KEVPE)
목적: 한국 주식시장 급등락 구간과 글로벌 역사/뉴스 이벤트를 매칭해
      현재 시장을 GREEN/AMBER/RED 리스크 신호로 분류한다.

주의:
- 투자 추천/매매 지시가 아니라 리스크 참고 신호다.
- 실운영 전 공식/유료 데이터 계약, API rate limit, look-ahead bias 검증이 필요하다.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import math
import urllib.parse

import numpy as np
import pandas as pd


REQUIRED_OHLCV_COLUMNS = {"date", "open", "high", "low", "close"}


@dataclass(frozen=True)
class Event:
    date: pd.Timestamp
    headline: str
    country: str = ""
    tone: float = 0.0          # GDELT tone: negative -> risk-off
    volume: float = 1.0        # article count / event count / weighted volume
    source_diversity: float = 1.0
    topics: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Signal:
    date: pd.Timestamp
    regime: str                # GREEN / AMBER / RED
    score: float
    direction_bias: str         # RISK_ON / RISK_OFF / NEUTRAL
    reason: str


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
    s = pd.to_numeric(series, errors="coerce")
    med = s.rolling(window=window, min_periods=max(5, window // 3)).median()
    mad = (s - med).abs().rolling(window=window, min_periods=max(5, window // 3)).median()
    denom = 1.4826 * mad
    fallback = s.rolling(window=window, min_periods=max(5, window // 3)).std(ddof=0)
    denom = denom.where(denom > 1e-12, fallback)
    denom = denom.where(denom > 1e-12, np.nan)
    z = (s - med) / denom
    return z.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def detect_volatility_windows(
    ohlcv: pd.DataFrame,
    window: int = 20,
    z_threshold: float = 2.50,
    quantile: float = 0.95,
    min_abs_return: float = 0.015,
    merge_gap_days: int = 2,
) -> pd.DataFrame:
    """급등락 구간 탐지: robust z-score + 상위 분위수 + 최소 절대수익률."""
    df = validate_ohlcv(ohlcv)
    df["ret"] = df["close"].pct_change().fillna(0.0)
    df["abs_ret"] = df["ret"].abs()
    df["rz"] = robust_zscore(df["ret"], window=window).abs()

    q = float(df["abs_ret"].quantile(quantile))
    dyn_threshold = max(q, min_abs_return)

    shock = (df["rz"] >= z_threshold) | (df["abs_ret"] >= dyn_threshold)
    shock &= df["abs_ret"] >= min_abs_return
    shock_idx = df.index[shock].tolist()

    if not shock_idx:
        return pd.DataFrame(columns=[
            "start", "end", "days", "direction", "peak_abs_ret",
            "cum_return", "vol_z_max", "severity"
        ])

    groups: List[List[int]] = []
    cur = [shock_idx[0]]
    for idx in shock_idx[1:]:
        gap = (df.loc[idx, "date"] - df.loc[cur[-1], "date"]).days
        if gap <= merge_gap_days:
            cur.append(idx)
        else:
            groups.append(cur)
            cur = [idx]
    groups.append(cur)

    rows = []
    for g in groups:
        sub = df.loc[g]
        start, end = sub["date"].min(), sub["date"].max()
        cum_ret = float((1.0 + sub["ret"]).prod() - 1.0)
        direction = "UP" if cum_ret > 0 else "DOWN"
        peak_abs_ret = float(sub["abs_ret"].max())
        vol_z_max = float(sub["rz"].max())
        severity = float(0.60 * min(vol_z_max / 5.0, 2.0) + 0.40 * min(peak_abs_ret / 0.05, 2.0))
        rows.append({
            "start": start,
            "end": end,
            "days": int(len(g)),
            "direction": direction,
            "peak_abs_ret": peak_abs_ret,
            "cum_return": cum_ret,
            "vol_z_max": vol_z_max,
            "severity": severity,
        })
    return pd.DataFrame(rows).sort_values(["severity", "start"], ascending=[False, True]).reset_index(drop=True)


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


def classify_event_topics(text: str) -> Tuple[str, ...]:
    t = (text or "").lower()
    topics = [topic for topic, keys in TOPIC_KEYWORDS.items() if any(k in t for k in keys)]
    return tuple(topics) if topics else ("general",)


TOPIC_WEIGHTS = {
    "war_conflict": 1.00,
    "pandemic_health": 0.95,
    "central_bank": 0.80,
    "oil_energy": 0.75,
    "fx_currency": 0.70,
    "semiconductor_ai": 0.65,
    "trade_supply": 0.65,
    "politics_policy": 0.55,
    "disaster": 0.60,
    "general": 0.30,
}


def event_relevance_score(event: Event, market_country: str = "Korea") -> float:
    """이벤트 중요도. 음수 tone은 위험도를 높이고, 반도체/AI 긍정 뉴스는 방향성 판단에서 별도 처리."""
    topics = event.topics or classify_event_topics(event.headline)
    topic_score = max(TOPIC_WEIGHTS.get(t, 0.30) for t in topics)

    vol_score = math.log1p(max(float(event.volume), 0.0)) / math.log1p(1000.0)
    div_score = math.log1p(max(float(event.source_diversity), 0.0)) / math.log1p(100.0)
    tone_risk = min(abs(float(event.tone)) / 10.0, 1.0)

    country_text = f"{event.country} {event.headline}".lower()
    geo_score = 1.0 if any(k in country_text for k in ["korea", "south korea", "seoul", "krx", "kospi"]) else 0.55

    score = 0.35 * topic_score + 0.25 * vol_score + 0.20 * div_score + 0.10 * tone_risk + 0.10 * geo_score
    return float(np.clip(score, 0.0, 1.0))


def match_events_to_windows(
    windows: pd.DataFrame,
    events: Sequence[Event],
    pre_days: int = 2,
    post_days: int = 3,
    max_events_per_window: int = 5,
) -> pd.DataFrame:
    if windows.empty:
        return pd.DataFrame(columns=["window_start", "window_end", "event_date", "headline", "match_score", "topics"])

    rows = []
    for _, w in windows.iterrows():
        start = pd.to_datetime(w["start"]) - pd.Timedelta(days=pre_days)
        end = pd.to_datetime(w["end"]) + pd.Timedelta(days=post_days)
        candidates = [ev for ev in events if start <= pd.to_datetime(ev.date) <= end]
        scored = sorted(
            candidates,
            key=lambda ev: event_relevance_score(ev) * (1.0 + float(w["severity"])),
            reverse=True
        )[:max_events_per_window]
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


def feature_vector_from_event(event: Event, market_ret: float = 0.0, vol_z: float = 0.0) -> Dict[str, float]:
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


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    va = np.asarray(a, dtype=float)
    vb = np.asarray(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(va, vb) / denom)


def current_signal_from_patterns(
    current_feature: Dict[str, float],
    historical_features: Sequence[Dict[str, float]],
    historical_forward_returns: Sequence[float],
    top_k: int = 7,
) -> Signal:
    if not historical_features or not historical_forward_returns:
        return Signal(pd.Timestamp.today().normalize(), "AMBER", 0.50, "NEUTRAL", "역사 패턴 부족")

    keys = sorted(current_feature.keys())
    cur = [current_feature.get(k, 0.0) for k in keys]
    sims = []
    for feat, fwd_ret in zip(historical_features, historical_forward_returns):
        vec = [feat.get(k, 0.0) for k in keys]
        sims.append((cosine_similarity(cur, vec), float(fwd_ret)))
    sims.sort(reverse=True, key=lambda x: x[0])
    top = sims[:top_k]

    if not top:
        return Signal(pd.Timestamp.today().normalize(), "AMBER", 0.50, "NEUTRAL", "유사 패턴 없음")

    weights = np.array([max(s, 0.0) for s, _ in top], dtype=float)
    if weights.sum() <= 1e-12:
        weights = np.ones(len(top), dtype=float)
    rets = np.array([r for _, r in top], dtype=float)
    expected = float(np.average(rets, weights=weights))
    similarity = float(np.mean([s for s, _ in top]))

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

    if risk_score >= 0.70:
        regime, bias = "RED", "RISK_OFF"
    elif risk_score >= 0.45:
        regime, bias = "AMBER", "NEUTRAL"
    else:
        regime, bias = "GREEN", "RISK_ON"

    reason = f"유사도={similarity:.2f}, 유사구간 기대수익={expected:.2%}, 이벤트점수={event_score:.2f}, vol_z={vol_z:.2f}"
    return Signal(pd.Timestamp.today().normalize(), regime, risk_score, bias, reason)


def backtest_risk_overlay(ohlcv: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    """신호는 다음 거래일부터 반영한다. look-ahead 방지."""
    df = validate_ohlcv(ohlcv)
    sig = signals.copy()
    sig["date"] = pd.to_datetime(sig["date"])
    sig["weight"] = sig["regime"].map({"GREEN": 1.00, "AMBER": 0.50, "RED": 0.20}).fillna(0.50)

    out = df[["date", "close"]].copy()
    out["ret"] = out["close"].pct_change().fillna(0.0)
    out = out.merge(sig[["date", "weight"]], on="date", how="left")
    out["weight"] = out["weight"].ffill().fillna(1.0)
    out["exec_weight"] = out["weight"].shift(1).fillna(1.0)  # 중요: 다음 날 반영
    out["strategy_ret"] = out["exec_weight"] * out["ret"]
    out["equity"] = (1.0 + out["strategy_ret"]).cumprod()
    return out


def gdelt_doc_timeline_url(query: str, start: date, end: date, mode: str = "timelinevolraw") -> str:
    """GDELT DOC 2.0 URL 생성. 실제 호출은 requests.get(url).json()으로 수행."""
    params = {
        "query": query,
        "mode": mode,
        "format": "json",
        "startdatetime": start.strftime("%Y%m%d") + "000000",
        "enddatetime": end.strftime("%Y%m%d") + "235959",
    }
    return "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)


def gdelt_doc_article_url(query: str, start: date, end: date, maxrecords: int = 250) -> str:
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": maxrecords,
        "sort": "datedesc",
        "startdatetime": start.strftime("%Y%m%d") + "000000",
        "enddatetime": end.strftime("%Y%m%d") + "235959",
    }
    return "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)


def run_pipeline_example(ohlcv: pd.DataFrame, events: Sequence[Event]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    windows = detect_volatility_windows(ohlcv)
    matches = match_events_to_windows(windows, events)
    return windows, matches
