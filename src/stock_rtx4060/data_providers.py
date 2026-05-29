"""OHLCV data provider router for recommendation workflows."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from .audit_log import AuditEvent, AuditLogger, mask_secret
from .data_cache import DataCache
from .data_quality.final_bar_lock import provider_final_bar_metadata
from .feature_engine import normalize_ohlcv
from .provider_validation import validate_provider_frame

_cache = DataCache()

DataProviderName = Literal["auto", "synthetic", "yfinance", "openbb", "pykrx", "fdr"]

OPENBB_EQUITY_HISTORICAL_ENDPOINT = "obb.equity.price.historical"
ALLOWED_PROVIDERS = {"auto", "synthetic", "yfinance", "openbb", "pykrx", "fdr"}


@dataclass(frozen=True)
class ProviderResult:
    frame: pd.DataFrame
    provider_requested: str
    provider_used: str
    source: str
    endpoint: str | None = None
    fallback_reason: str | None = None
    metadata: dict[str, Any] | None = None


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
    as_of: str | None = None,
    data_lake_first: bool | None = None,
    after_market_close: bool = False,
) -> ProviderResult:
    config = provider_config if provider_config is not None else load_provider_config(provider_config_path)
    requested = str(data_provider or "auto").lower()
    selected = resolve_provider(requested, synthetic=synthetic, provider_config=config)

    if selected == "synthetic":
        return _load_synthetic(ticker, period, requested, audit_logger, command, fallback_reason="synthetic flag enabled" if synthetic else None)

    if data_lake_first is None:
        import os as _os
        data_lake_first = _os.environ.get("USE_DATA_LAKE", "0").lower() in ("1", "true", "yes")

    if data_lake_first or as_of is not None:
        lake_result = _try_data_lake(ticker, period, requested, selected, as_of, audit_logger, command)
        if lake_result is not None:
            return lake_result
        if as_of is not None:
            # Prevent look-ahead bias: never fall through to a live provider when an
            # as_of timestamp was specified.  The caller must ingest data first.
            raise RuntimeError(
                f"Data lake miss for as_of query: ticker={ticker!r} as_of={as_of!r}. "
                "Ingest historical data before issuing point-in-time queries."
            )

    cache_started = time.perf_counter()
    cached = _cache.get(ticker, period, selected)
    if cached is not None:
        validation = validate_provider_frame(cached, provider_used=selected, ticker=ticker, period=period)
        final_bar_metadata = provider_final_bar_metadata(
            source=f"{selected}:cache",
            bar_type="CACHE",
            eod_confirmed=False,
            source_evidence_lock=False,
            after_market_close=after_market_close,
        )
        metadata = {
            "provider_validation": validation.metadata,
            **validation.metadata,
            "cache_hit": True,
            **final_bar_metadata,
            "source_timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        _write_audit(
            audit_logger,
            AuditEvent(
                event_type="provider_attempt",
                status="SUCCESS",
                command=command,
                ticker=ticker,
                period=period,
                provider_requested=requested,
                provider_used=selected,
                source=f"{selected}:cache",
                metadata=metadata,
                duration_ms=_elapsed_ms(cache_started),
            ),
        )
        return ProviderResult(frame=cached, provider_requested=requested, provider_used=selected, source=f"{selected}:cache", metadata=metadata)

    if selected == "pykrx":
        result = _load_pykrx(ticker, period, requested, audit_logger, command)
    elif selected == "fdr":
        result = _load_fdr(ticker, period, requested, audit_logger, command)
    elif selected == "openbb":
        result = _load_openbb(ticker, period, requested, config, audit_logger, command)
    else:
        result = _load_yfinance(ticker, period, requested, audit_logger, command)

    if result.frame is not None and not result.frame.empty:
        _cache.set(ticker, period, selected, result.frame)
        if data_lake_first:
            _write_through_to_lake(ticker, result.frame, source=selected)
    return result


def _try_data_lake(
    ticker: str,
    period: str,
    requested: str,
    selected: str,
    as_of: str | None,
    audit_logger: AuditLogger | None,
    command: str,
) -> ProviderResult | None:
    """Read from PIT lake first. Returns None on miss so caller can fall back."""
    try:
        from .data_lake import pit_resolver
    except Exception:
        return None
    try:
        df = pit_resolver.read(ticker, as_of=as_of)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    cols = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    if len(cols) < 5:
        return None
    metadata: dict[str, Any] = {"data_lake_hit": True, "as_of": as_of, "rows": int(len(df))}
    return ProviderResult(
        frame=df[cols].copy(),
        provider_requested=requested,
        provider_used=f"{selected}+lake",
        source="data_lake",
        metadata=metadata,
    )


def _write_through_to_lake(ticker: str, frame: Any, *, source: str) -> None:
    try:
        from .data_lake.store import get_default_store
    except Exception:
        return
    try:
        store = get_default_store()
        store.write(ticker, frame, source=source)
    except Exception:
        pass


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
    validation = validate_provider_frame(frame, provider_used="synthetic", ticker=ticker, period=period)
    metadata = {"provider_validation": validation.metadata, **validation.metadata}
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
            metadata=metadata,
            duration_ms=_elapsed_ms(started),
        ),
    )
    return ProviderResult(frame=frame, provider_requested=requested, provider_used="synthetic", source="synthetic_demo_data", fallback_reason=fallback_reason, metadata=metadata)


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
        validation = validate_provider_frame(normalized, provider_used="yfinance", ticker=ticker, period=period)
        metadata = {"provider_validation": validation.metadata, **validation.metadata}
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
                metadata=metadata,
                duration_ms=_elapsed_ms(started),
            ),
        )
        return ProviderResult(frame=normalized, provider_requested=requested, provider_used="yfinance", source="yfinance", metadata=metadata)
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


def _load_pykrx(
    ticker: str,
    period: str,
    requested: str,
    audit_logger: AuditLogger | None,
    command: str,
) -> ProviderResult:
    started = time.perf_counter()
    try:
        from pykrx import stock as pykrx_stock

        # Strip .KS suffix for PyKRX
        symbol = ticker.replace(".KS", "").replace(".KQ", "")
        start_date = _period_to_start_date_yyyymmdd(period)
        end_date = pd.Timestamp.now('UTC').strftime("%Y%m%d")
        frame = pykrx_stock.get_market_ohlcv_by_date(start_date, end_date, symbol, freq="d", adjusted=True)
        if frame.empty:
            raise RuntimeError("empty OHLCV frame from PyKRX")
        normalized = normalize_ohlcv(_normalize_pykrx_columns(frame))
        validation = validate_provider_frame(normalized, provider_used="pykrx", ticker=ticker, period=period)
        _write_audit(
            audit_logger,
            AuditEvent(
                event_type="provider_attempt",
                status="SUCCESS",
                command=command,
                ticker=ticker,
                period=period,
                provider_requested=requested,
                provider_used="pykrx",
                source="pykrx",
                metadata={
                    "provider_validation": validation.metadata,
                    **validation.metadata,
                    "ticker_type": "KRX",
                    "data_freshness_minutes": 0,
                    "market_close_adj": True,
                    "source_timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
                },
                duration_ms=_elapsed_ms(started),
            ),
        )
        return ProviderResult(
            frame=normalized,
            provider_requested=requested,
            provider_used="pykrx",
            source="pykrx",
            metadata={
                "provider_validation": validation.metadata,
                **validation.metadata,
                "ticker_type": "KRX",
                "data_freshness_minutes": 0,
                "market_close_adj": True,
                "source_timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            },
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
                provider_used="pykrx",
                source="pykrx",
                message=str(exc),
                error_type=type(exc).__name__,
                duration_ms=_elapsed_ms(started),
            ),
        )
        # PyKRX failed — trigger fallback chain: try FDR
        return _load_fdr(ticker, period, requested, audit_logger, command, fallback_reason=f"pykrx failed: {exc}")


def _load_fdr(
    ticker: str,
    period: str,
    requested: str,
    audit_logger: AuditLogger | None,
    command: str,
    fallback_reason: str | None = None,
) -> ProviderResult:
    started = time.perf_counter()
    try:
        import FinanceDataReader as fdr

        # Map ticker for FDR (KRX: 005930 → KRX:005930, others as-is)
        fdr_symbol = ticker
        if ticker.endswith(".KS"):
            fdr_symbol = f"KRX:{ticker.replace('.KS', '')}"
        elif ticker.endswith(".KQ"):
            fdr_symbol = f"KOSDAQ:{ticker.replace('.KQ', '')}"
        start_date = _period_to_start_date(period)
        frame = fdr.DataReader(fdr_symbol, start=start_date)
        if frame.empty:
            raise RuntimeError("empty OHLCV frame from FDR")
        normalized = normalize_ohlcv(frame)
        validation = validate_provider_frame(normalized, provider_used="fdr", ticker=ticker, period=period)
        _write_audit(
            audit_logger,
            AuditEvent(
                event_type="provider_attempt",
                status="SUCCESS",
                command=command,
                ticker=ticker,
                period=period,
                provider_requested=requested,
                provider_used="fdr",
                source="FinanceDataReader",
                metadata={
                    "provider_validation": validation.metadata,
                    **validation.metadata,
                    "ticker_type": "KRX" if ticker.endswith((".KS", ".KQ")) else "UNKNOWN",
                    "data_freshness_minutes": 0,
                    "market_close_adj": False,
                    "source_timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
                },
                duration_ms=_elapsed_ms(started),
            ),
        )
        return ProviderResult(
            frame=normalized,
            provider_requested=requested,
            provider_used="fdr",
            source="FinanceDataReader",
            metadata={
                "provider_validation": validation.metadata,
                **validation.metadata,
                "ticker_type": "KRX" if ticker.endswith((".KS", ".KQ")) else "UNKNOWN",
                "data_freshness_minutes": 0,
                "market_close_adj": False,
                "source_timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            },
            fallback_reason=fallback_reason,
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
                provider_used="fdr",
                source="FinanceDataReader",
                message=str(exc),
                error_type=type(exc).__name__,
                duration_ms=_elapsed_ms(started),
            ),
        )
        raise RuntimeError(f"{ticker}: FDR provider failed: {exc}") from exc


def _period_to_end_date(period: str) -> str:
    """Convert period string (e.g. '3y', '6m') to end date in YYYYMMDD format."""
    value = str(period or "").strip().lower()
    if len(value) < 2:
        return pd.Timestamp.now('UTC').strftime("%Y%m%d")
    unit = value[-1]
    try:
        amount = int(value[:-1])
    except ValueError:
        return pd.Timestamp.now('UTC').strftime("%Y%m%d")
    days_by_unit = {"d": 1, "w": 7, "m": 30, "y": 365}
    days = days_by_unit.get(unit)
    if days is None:
        return pd.Timestamp.now('UTC').strftime("%Y%m%d")
    end = pd.Timestamp.now('UTC') - pd.Timedelta(days=amount * days)
    return end.strftime("%Y%m%d")


def _period_to_start_date_yyyymmdd(period: str) -> str:
    start_date = _period_to_start_date(period)
    if not start_date:
        return (datetime.now(UTC).date() - timedelta(days=365 * 3)).strftime("%Y%m%d")
    return start_date.replace("-", "")


def _normalize_pykrx_columns(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename(
        columns={
            "시가": "Open",
            "고가": "High",
            "저가": "Low",
            "종가": "Close",
            "거래량": "Volume",
        }
    )


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
        validation = validate_provider_frame(frame, provider_used="openbb", ticker=ticker, period=period)
        metadata = {"provider_validation": validation.metadata, **validation.metadata, "openbb_provider": openbb_provider, "arguments": mask_secret(kwargs)}
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
                metadata=metadata,
                duration_ms=_elapsed_ms(started),
            ),
        )
        return ProviderResult(
            frame=frame,
            provider_requested=requested,
            provider_used="openbb",
            source=f"openbb:{openbb_provider}",
            endpoint=OPENBB_EQUITY_HISTORICAL_ENDPOINT,
            metadata=metadata,
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
    start = datetime.now(UTC).date() - timedelta(days=amount * days)
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
    end = pd.offsets.BDay().rollback(pd.Timestamp.now("UTC").tz_localize(None).normalize())
    idx = pd.bdate_range(end=end, periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx)


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _write_audit(audit_logger: AuditLogger | None, event: AuditEvent) -> None:
    if audit_logger is None:
        return
    audit_logger.write(event)
