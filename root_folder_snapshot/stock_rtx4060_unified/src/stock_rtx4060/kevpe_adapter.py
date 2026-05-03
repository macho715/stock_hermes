"""
KEVPE_v2 adapter for stock_rtx4060_unified.

Purpose
-------
Provides a单向 bridge between KEVPE_v2 (Korea Event-Volatility Pattern Engine) signals
and the stock_rtx4060 recommendation engine, without creating circular dependencies.

KEVPE_v2 is used as a **supplementary risk overlay signal** — it does NOT replace
the recommendation engine's Risk Gate verdicts. Both systems remain independent.

Boundary
--------
This adapter does NOT enable broker execution, auto-buy/sell, or personalized advice.
KEVPE signals are screening-only, same as the recommendation engine output.

Integration pattern
-------------------
KEVPE Signal (GREEN/AMBER/RED)
    → kevpe_adapter.get_kevpe_verdict() → auxiliary verdict supplement
    → recommendation_engine receives it as optional context
    → final verdict comes from recommendation_engine's own Risk Gate

Usage
-----
```python
from stock_rtx4060.kevpe_adapter import KevpeAdapter

adapter = KevpeAdapter()
kevpe_result = adapter.get_signal_for_ticker(
    ohlcv=ohlcv_df,
    events=events_list,
    as_of=pd.Timestamp("2026-05-01"),
)
print(kevpe_result.regime, kevpe_result.score)
```
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

# KEVPE_v2 types — imported dynamically to avoid hard dependency
_KevpeSignal = None
_KevpeConfig = None
_KevpeFeatureScaler = None

# ────────────────────────────────────────────────────────────────
# Adapter types (don't expose KEVPE internals to recommendation engine)
# ────────────────────────────────────────────────────────────────


@dataclass
class KevpeAdapterResult:
    """Normalized KEVPE signal result for consumption by recommendation engine."""

    regime: str  # "GREEN" | "AMBER" | "RED"
    score: float  # 0.0 ~ 1.0 (higher = more risky)
    expected_return_pct: float
    ci_low_pct: float
    ci_high_pct: float
    reason: str
    confidence: str  # "low" | "medium" | "high" — based on bootstrap CI width
    is_available: bool  # False if KEVPE not initialized or data insufficient

    @classmethod
    def unavailable(cls, reason: str = "KEVPE not configured") -> "KevpeAdapterResult":
        return cls(
            regime="AMBER",
            score=0.5,
            expected_return_pct=0.0,
            ci_low_pct=0.0,
            ci_high_pct=0.0,
            reason=reason,
            confidence="low",
            is_available=False,
        )


# ────────────────────────────────────────────────────────────────
# Adapter
# ────────────────────────────────────────────────────────────────


class KevpeAdapter:
    """
    Lightweight adapter to use KEVPE_v2 signals as risk overlay in recommendation engine.

    Does NOT import kevpe_v2 directly at module level — lazy import to allow
    stock_rtx4060 to run even if KEVPE is not installed.
    """

    def __init__(
        self,
        kevpe_package_path: str | None = None,
        default_config_kwargs: dict | None = None,
    ):
        """
        Args:
            kevpe_package_path: Path to KEVPE_final_package.
                                  Defaults to `../KEVPE_final_package` relative to stock_rtx4060 root.
            default_config_kwargs: Dict of KevpeConfig field values to override defaults.
        """
        self._kevpe_pkg_path = kevpe_package_path or self._infer_kevpe_path()
        self._config_kwargs = default_config_kwargs or {}
        self._initialized = False
        self._kevpe_module = None

    def _infer_kevpe_path(self) -> str:
        """Try to locate KEVPE_final_package relative to stock_rtx4060 root."""
        for base in Path(__file__).resolve().parents:
            kevpe_path = base / "KEVPE_final_package"
            if (kevpe_path / "kevpe_v2.py").exists():
                return str(kevpe_path.resolve())

        return ""  # not found

    def _ensure_init(self) -> bool:
        """Lazily import KEVPE_v2 and return True if successful, False otherwise."""
        if self._initialized:
            return self._kevpe_module is not None

        self._initialized = True

        if not self._kevpe_pkg_path or not Path(self._kevpe_pkg_path).exists():
            self._kevpe_module = None
            return False

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "kevpe_v2", Path(self._kevpe_pkg_path) / "kevpe_v2.py"
        )
        if spec is None or spec.loader is None:
            self._kevpe_module = None
            return False

        try:
            self._kevpe_module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = self._kevpe_module
            spec.loader.exec_module(self._kevpe_module)
            return True
        except Exception:
            self._kevpe_module = None
            return False

    def is_available(self) -> bool:
        return self._ensure_init()

    def get_default_config(self):
        """Return a KevpeConfig with optional overrides applied."""
        if not self._ensure_init():
            return None
        cfg_class = self._kevpe_module.KevpeConfig
        return cfg_class(**self._config_kwargs)

    def get_signal_for_ticker(
        self,
        ohlcv: pd.DataFrame,
        events: list,
        as_of: pd.Timestamp | None = None,
        config_overrides: dict | None = None,
    ) -> KevpeAdapterResult:
        """
        Compute KEVPE_v2 signal for given OHLCV + events.

        Args:
            ohlcv: DataFrame with columns [date, open, high, low, close] or
                   [Open, High, Low, Close] (indexed by date)
            events: List of Event objects (from kevpe_v2) or dict-like with
                    date, topic, score fields
            as_of: Timestamp for deterministic signal. Defaults to today.
            config_overrides: Dict of KevpeConfig field overrides for this call.

        Returns:
            KevpeAdapterResult — regime, score, expected_return, CI, reason
        """
        if not self._ensure_init():
            return KevpeAdapterResult.unavailable("KEVPE package not found")

        try:
            cfg = self.get_default_config()
            if cfg is None:
                return KevpeAdapterResult.unavailable("KEVPE config init failed")

            if config_overrides:
                cfg = self._merge_config(cfg, config_overrides)

            kevpe_v2 = self._kevpe_module

            ohlcv_clean = self._normalize_ohlcv_for_kevpe(ohlcv)

            if ohlcv_clean is None or len(ohlcv_clean) < 30:
                return KevpeAdapterResult.unavailable("Insufficient OHLCV data for KEVPE")

            kevpe_events = self._normalize_events(events, kevpe_v2)
            if kevpe_events:
                return self._signal_from_events(kevpe_events, ohlcv_clean, cfg, kevpe_v2, as_of)

            # ── detect volatility windows ─────────────────────────────
            windows = kevpe_v2.detect_volatility_windows(ohlcv_clean, cfg)

            # ── match events to windows ───────────────────────────────
            if kevpe_events:
                matches = kevpe_v2.match_events_to_windows(windows, kevpe_events, cfg)
            else:
                matches = []

            # ── build historical feature pool (for signal) ────────────
            # KEVPE requires historical patterns + forward returns to compute signal
            # Without historical data, we can still run volatility detection
            # and fall back to a "signal not computable" result
            if len(ohlcv_clean) < 60:
                return KevpeAdapterResult.unavailable("Need ≥60 days for KEVPE signal")

            # ── current signal ───────────────────────────────────────
            as_of_ts = as_of or pd.Timestamp.today().normalize()

            # Feature vector from most recent window
            cur_feat = self._extract_feature_from_windows(ohlcv_clean, windows[-1] if windows else None, cfg)
            hist_feats = self._build_historical_features(ohlcv_clean, windows, cfg)
            hist_fwd_rets = self._build_historical_forward_returns(ohlcv_clean, windows)

            if cur_feat is None or len(hist_feats) == 0:
                return KevpeAdapterResult.unavailable("Cannot build feature vector")

            scaler = kevpe_v2.FeatureScaler().fit(hist_feats)
            signal = kevpe_v2.current_signal_v2(
                current_feature=cur_feat,
                historical_features=hist_feats,
                historical_forward_returns=hist_fwd_rets,
                config=cfg,
                scaler=scaler,
                as_of=as_of_ts,
            )

            return self._result_from_signal(signal)

        except Exception as e:
            return KevpeAdapterResult.unavailable(f"KEVPE computation failed: {e}")

    def _normalize_ohlcv_for_kevpe(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        kevpe_v2 = self._kevpe_module
        frame = ohlcv.copy()
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = [str(col[0]) for col in frame.columns]
        if not isinstance(frame.index, pd.DatetimeIndex):
            if "date" in frame.columns:
                frame.index = pd.to_datetime(frame["date"], errors="coerce")
            elif "Date" in frame.columns:
                frame.index = pd.to_datetime(frame["Date"], errors="coerce")
        frame = frame.rename(columns={str(column): str(column).lower() for column in frame.columns})
        if "date" not in frame.columns:
            frame.insert(0, "date", pd.to_datetime(frame.index, errors="coerce"))
        return kevpe_v2.validate_ohlcv(frame)

    def _normalize_events(self, events: list[Any], kevpe_v2) -> list[Any]:
        normalized = []
        event_cls = kevpe_v2.Event
        for event in events or []:
            if isinstance(event, event_cls):
                normalized.append(event)
                continue
            if not isinstance(event, dict):
                continue
            headline = str(event.get("headline", "") or "").strip()
            if not headline:
                continue
            topics = event.get("topics", ())
            if isinstance(topics, list):
                topics = tuple(str(item).strip() for item in topics if str(item).strip())
            elif isinstance(topics, str):
                topics = tuple(item.strip() for item in topics.replace(";", ",").split(",") if item.strip())
            elif not isinstance(topics, tuple):
                topics = ()
            normalized.append(
                event_cls(
                    pd.Timestamp(event.get("date")),
                    headline,
                    country=str(event.get("country", "") or ""),
                    tone=float(event.get("tone", 0.0) or 0.0),
                    volume=float(event.get("volume", 1.0) or 1.0),
                    source_diversity=float(event.get("source_diversity", 1.0) or 1.0),
                    topics=topics,
                )
            )
        return sorted(normalized, key=lambda item: pd.Timestamp(item.date))

    def _signal_from_events(self, events: list[Any], ohlcv_clean: pd.DataFrame, cfg, kevpe_v2, as_of: pd.Timestamp | None) -> KevpeAdapterResult:
        latest = events[-1]
        current_feature = kevpe_v2.feature_vector_from_event(latest, market_ret=self._recent_return(ohlcv_clean), vol_z=self._recent_vol_z(ohlcv_clean, cfg))
        historical_events = events[:-1]
        if len(historical_events) >= 3:
            historical_features = [kevpe_v2.feature_vector_from_event(event) for event in historical_events]
            historical_returns = [self._forward_return_after_event(ohlcv_clean, event) for event in historical_events]
            signal = kevpe_v2.current_signal_v2(
                current_feature=current_feature,
                historical_features=historical_features,
                historical_forward_returns=historical_returns,
                config=cfg,
                scaler=kevpe_v2.FeatureScaler().fit(historical_features),
                as_of=as_of or pd.Timestamp.today().normalize(),
            )
            return self._result_from_signal(signal)

        score = float(kevpe_v2.event_relevance_score(latest))
        if score >= float(cfg.red_threshold):
            regime = "RED"
        elif score >= float(cfg.amber_threshold):
            regime = "AMBER"
        else:
            regime = "GREEN"
        expected = -score * 5.0 if regime == "RED" else -score * 2.0 if regime == "AMBER" else max(0.0, 1.0 - score)
        return KevpeAdapterResult(
            regime=regime,
            score=round(score, 4),
            expected_return_pct=round(expected, 4),
            ci_low_pct=round(expected - 2.0, 4),
            ci_high_pct=round(expected + 2.0, 4),
            reason=f"KEVPE event overlay: {latest.headline[:160]}",
            confidence="low",
            is_available=True,
        )

    def _result_from_signal(self, signal) -> KevpeAdapterResult:
        ci_width = float(signal.ci_high) - float(signal.ci_low)
        confidence = "low" if ci_width > 5.0 else "medium" if ci_width > 2.0 else "high"
        return KevpeAdapterResult(
            regime=str(signal.regime),
            score=float(getattr(signal, "risk_score", getattr(signal, "score", 0.0))),
            expected_return_pct=float(signal.expected_return),
            ci_low_pct=float(signal.ci_low),
            ci_high_pct=float(signal.ci_high),
            reason=str(signal.reason)[:200],
            confidence=confidence,
            is_available=True,
        )

    def _recent_return(self, ohlcv: pd.DataFrame) -> float:
        if len(ohlcv) < 21:
            return 0.0
        close = ohlcv["close"].astype(float)
        return float(close.iloc[-1] / close.iloc[-21] - 1.0)

    def _recent_vol_z(self, ohlcv: pd.DataFrame, cfg) -> float:
        close = ohlcv["close"].astype(float)
        ret = close.pct_change().fillna(0.0)
        if len(ret) < int(cfg.z_window) + 2:
            return 0.0
        window = ret.tail(int(cfg.z_window))
        std = float(window.std(ddof=0))
        return 0.0 if std <= 1e-9 else float((ret.iloc[-1] - window.mean()) / std)

    def _forward_return_after_event(self, ohlcv: pd.DataFrame, event) -> float:
        date = pd.Timestamp(event.date)
        frame = ohlcv.sort_values("date").reset_index(drop=True)
        idx = frame.index[frame["date"] >= date]
        if len(idx) == 0:
            return 0.0
        start = int(idx[0])
        end = min(start + 20, len(frame) - 1)
        if end <= start:
            return 0.0
        return float(frame.loc[end, "close"] / frame.loc[start, "close"] - 1.0)

    def _merge_config(self, cfg, overrides: dict):
        """Create a new KevpeConfig with overrides applied."""
        fields = {f.name: getattr(cfg, f.name) for f in cfg.__dataclass_fields__.values()}
        fields.update(overrides)
        return self._kevpe_module.KevpeConfig(**fields)

    def _extract_feature_from_windows(
        self, ohlcv: pd.DataFrame, window, cfg
    ):
        """Extract feature vector from a volatility window for current signal."""
        if window is None:
            return None
        kevpe_v2 = self._kevpe_module
        try:
            feat = kevpe_v2.feature_vector_from_event(
                ohlcv.loc[window.start : window.end],
                cfg,
            )
            return feat
        except Exception:
            return None

    def _build_historical_features(self, ohlcv, windows, cfg):
        """Build list of historical feature vectors from all windows."""
        kevpe_v2 = self._kevpe_module
        feats = []
        for w in windows[:-1]:  # exclude current window
            try:
                feat = kevpe_v2.feature_vector_from_event(
                    ohlcv.loc[w.start : w.end],
                    cfg,
                )
                feats.append(feat)
            except Exception:
                continue
        return feats if feats else []

    def _build_historical_forward_returns(self, ohlcv, windows):
        """Build list of forward returns for each historical window."""
        rets = []
        for i, w in enumerate(windows[:-1]):
            if i + 1 < len(windows):
                next_w = windows[i + 1]
                try:
                    curr_ret = ohlcv.loc[next_w.start : next_w.end]["close"].iloc[-1] / ohlcv.loc[w.start : w.end]["close"].iloc[0] - 1
                    rets.append(curr_ret)
                except Exception:
                    rets.append(0.0)
        return rets if rets else [0.0]


# ────────────────────────────────────────────────────────────────
# Singleton accessor for recommendation engine integration
# ────────────────────────────────────────────────────────────────

_kevpe_adapter_instance: Optional[KevpeAdapter] = None


def get_kevpe_adapter() -> KevpeAdapter:
    """Return the global KEVPE adapter instance (lazy singleton)."""
    global _kevpe_adapter_instance
    if _kevpe_adapter_instance is None:
        _kevpe_adapter_instance = KevpeAdapter()
    return _kevpe_adapter_instance


def kevpe_signal_to_supplement(result: KevpeAdapterResult) -> dict:
    """
    Convert KEVPE result to a dict supplement for recommendation report.

    Used by recommendation_engine to include KEVPE context in the report
    without changing the primary verdict logic.
    """
    if not result.is_available:
        return {"kevpe_available": False}

    return {
        "kevpe_available": True,
        "kevpe_regime": result.regime,
        "kevpe_score": result.score,
        "kevpe_expected_return_pct": result.expected_return_pct,
        "kevpe_ci": [result.ci_low_pct, result.ci_high_pct],
        "kevpe_confidence": result.confidence,
        "kevpe_reason": result.reason,
    }
