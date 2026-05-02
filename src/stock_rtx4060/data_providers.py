"""OHLCV data provider router for recommendation workflows."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from .audit_log import AuditEvent, AuditLogger, mask_secret
from .feature_engine import normalize_ohlcv

DataProviderName = Literal["auto", "synthetic", "yfinance", "openbb"]

OPENBB_EQUITY_HISTORICAL_ENDPOINT = "obb.equity.price.historical"
ALLOWED_PROVIDERS = {"auto", "synthetic", "yfinance", "openbb"}


@dataclass(frozen=True)
class ProviderResult:
    frame: pd.DataFrame
    provider_requested: str
    provider_used: str
    source: str
    endpoint: str | None = None
    fallback_reason: str | None = None


def load_provider_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"provider config not found: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def resolve_provider(data_provider: str = "auto", synthetic: bool = False, provider_config: dict[str, Any] | None = None) -> str:
    requested = str(data_provider or "auto").lower()
    if requested not in ALLOWED_PROVIDERS:
        raise ValueError(f"unsupported data provider: {data_provider}")
    if synthetic:
        return "synthetic"
    if requested != "auto":
        return requested
    config = provider_config or {}
    configured = str(config.get("default_provider", "yfinance")).lower()
    return configured if configured in {"synthetic", "yfinance", "openbb"} else "yfinance"


def load_ohlcv_with_provider(
    ticker: str,
    period: str,
    *,
    synthetic: bool = False,
    data_provider: str = "auto",
    provider_config_path: str | None = None,
    provider_config: dict[str, Any] | None = None,
    audit_logger: AuditLogger | None = None,
    command: str = "recommend",
) -> ProviderResult:
    config = provider_config if provider_config is not None else load_provider_config(provider_config_path)
    requested = str(data_provider or "auto").lower()
    selected = resolve_provider(requested, synthetic=synthetic, provider_config=config)

    if selected == "synthetic":
        return _load_synthetic(ticker, period, requested, audit_logger, command, fallback_reason="synthetic flag enabled" if synthetic else None)
    if selected == "openbb":
        return _load_openbb(ticker, period, requested, config, audit_logger, command)
    return _load_yfinance(ticker, period, requested, audit_logger, command)


def _load_synthetic(
    ticker: str,
    period: str,
    requested: str,
    audit_logger: AuditLogger | None,
    command: str,
    fallback_reason: str | None = None,
) -> ProviderResult:
    started = time.perf_counter()
    frame = _make_synthetic_ohlcv(seed=_stable_seed(ticker))
    _write_audit(
        audit_logger,
        AuditEvent(
            event_type="provider_attempt",
            status="SUCCESS",
            command=command,
            ticker=ticker,
            period=period,
            provider_requested=requested,
            provider_used="synthetic",
            source="synthetic_demo_data",
            message=fallback_reason,
            duration_ms=_elapsed_ms(started),
        ),
    )
    return ProviderResult(frame=frame, provider_requested=requested, provider_used="synthetic", source="synthetic_demo_data", fallback_reason=fallback_reason)


def _load_yfinance(
    ticker: str,
    period: str,
    requested: str,
    audit_logger: AuditLogger | None,
    command: str,
) -> ProviderResult:
    started = time.perf_counter()
    try:
        import yfinance as yf  # type: ignore

        frame = yf.download(ticker, period=period, auto_adjust=True, progress=False, threads=False)
        normalized = normalize_ohlcv(frame)
        if normalized.empty:
            raise RuntimeError("empty OHLCV frame")
        _write_audit(
            audit_logger,
            AuditEvent(
                event_type="provider_attempt",
                status="SUCCESS",
                command=command,
                ticker=ticker,
                period=period,
                provider_requested=requested,
                provider_used="yfinance",
                source="yfinance",
                duration_ms=_elapsed_ms(started),
            ),
        )
        return ProviderResult(frame=normalized, provider_requested=requested, provider_used="yfinance", source="yfinance")
    except Exception as exc:
        _write_audit(
            audit_logger,
            AuditEvent(
                event_type="provider_attempt",
                status="FAIL",
                command=command,
                ticker=ticker,
                period=period,
                provider_requested=requested,
                provider_used="yfinance",
                source="yfinance",
                message=str(exc),
                error_type=type(exc).__name__,
                duration_ms=_elapsed_ms(started),
            ),
        )
        raise RuntimeError(f"{ticker}: yfinance provider failed: {exc}") from exc


def _load_openbb(
    ticker: str,
    period: str,
    requested: str,
    config: dict[str, Any],
    audit_logger: AuditLogger | None,
    command: str,
) -> ProviderResult:
    started = time.perf_counter()
    openbb_provider = str(config.get("openbb_provider", "yfinance"))
    try:
        from openbb import obb  # type: ignore

        kwargs: dict[str, Any] = {"symbol": ticker, "provider": openbb_provider}
        start_date = _period_to_start_date(period)
        if start_date:
            kwargs["start_date"] = start_date
        result = obb.equity.price.historical(**kwargs)
        frame = _openbb_to_frame(result)
        if frame.empty:
            raise RuntimeError("empty OHLCV frame")
        _write_audit(
            audit_logger,
            AuditEvent(
                event_type="provider_attempt",
                status="SUCCESS",
                command=command,
                ticker=ticker,
                period=period,
                provider_requested=requested,
                provider_used="openbb",
                endpoint=OPENBB_EQUITY_HISTORICAL_ENDPOINT,
                source=f"openbb:{openbb_provider}",
                metadata={"openbb_provider": openbb_provider, "arguments": mask_secret(kwargs)},
                duration_ms=_elapsed_ms(started),
            ),
        )
        return ProviderResult(
            frame=frame,
            provider_requested=requested,
            provider_used="openbb",
            source=f"openbb:{openbb_provider}",
            endpoint=OPENBB_EQUITY_HISTORICAL_ENDPOINT,
        )
    except Exception as exc:
        _write_audit(
            audit_logger,
            AuditEvent(
                event_type="provider_attempt",
                status="FAIL",
                command=command,
                ticker=ticker,
                period=period,
                provider_requested=requested,
                provider_used="openbb",
                endpoint=OPENBB_EQUITY_HISTORICAL_ENDPOINT,
                source=f"openbb:{openbb_provider}",
                message=str(exc),
                error_type=type(exc).__name__,
                duration_ms=_elapsed_ms(started),
            ),
        )
        raise RuntimeError(f"{ticker}: OpenBB provider failed: {exc}") from exc


def _openbb_to_frame(result: Any) -> pd.DataFrame:
    if hasattr(result, "to_df"):
        frame = result.to_df()
    else:
        results = getattr(result, "results", result)
        frame = pd.DataFrame(results)
    if "date" in frame.columns:
        frame = frame.copy()
        frame.index = pd.to_datetime(frame["date"], errors="coerce")
    return normalize_ohlcv(frame)


def _period_to_start_date(period: str) -> str | None:
    value = str(period or "").strip().lower()
    if len(value) < 2:
        return None
    unit = value[-1]
    try:
        amount = int(value[:-1])
    except ValueError:
        return None
    days_by_unit = {"d": 1, "w": 7, "m": 30, "y": 365}
    days = days_by_unit.get(unit)
    if days is None:
        return None
    start = datetime.now(timezone.utc).date() - timedelta(days=amount * days)
    return start.isoformat()


def _stable_seed(value: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(value.upper())) % 1_000_000


def _make_synthetic_ohlcv(n: int = 760, seed: int = 42, drift: float = 0.00035) -> pd.DataFrame:
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


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _write_audit(audit_logger: AuditLogger | None, event: AuditEvent) -> None:
    if audit_logger is None:
        return
    audit_logger.write(event)
