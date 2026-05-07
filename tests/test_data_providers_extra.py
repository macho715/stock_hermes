"""Extended tests for data_providers.py — covers uncovered branches."""

from __future__ import annotations

import builtins
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest

import stock_rtx4060.data_providers as dp
from stock_rtx4060.audit_log import AuditEvent, AuditLogger
from stock_rtx4060.data_providers import (
    ProviderResult,
    _elapsed_ms,
    _make_synthetic_ohlcv,
    _normalize_pykrx_columns,
    _openbb_to_frame,
    _period_to_end_date,
    _period_to_start_date,
    _period_to_start_date_yyyymmdd,
    _stable_seed,
    _write_audit,
    load_ohlcv_with_provider,
    load_provider_config,
    resolve_provider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv_frame(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [10.0 + i for i in range(n)],
            "High": [11.0 + i for i in range(n)],
            "Low": [9.0 + i for i in range(n)],
            "Close": [10.5 + i for i in range(n)],
            "Volume": [1_000_000.0 + i * 100 for i in range(n)],
        },
        index=pd.date_range("2026-01-01", periods=n),
    )


# ---------------------------------------------------------------------------
# load_provider_config
# ---------------------------------------------------------------------------

def test_load_provider_config_no_path():
    assert load_provider_config(None) == {}
    assert load_provider_config("") == {}


def test_load_provider_config_valid_file(tmp_path):
    cfg = {"default_provider": "yfinance", "openbb_provider": "fmp"}
    p = tmp_path / "provider_config.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    result = load_provider_config(str(p))
    assert result["default_provider"] == "yfinance"
    assert result["openbb_provider"] == "fmp"


def test_load_provider_config_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_provider_config(str(tmp_path / "nonexistent.json"))


# ---------------------------------------------------------------------------
# resolve_provider
# ---------------------------------------------------------------------------

def test_resolve_provider_unsupported_raises():
    with pytest.raises(ValueError, match="unsupported data provider"):
        resolve_provider("polars_finance")


def test_resolve_provider_auto_with_unknown_configured_falls_back_to_yfinance():
    result = resolve_provider("auto", provider_config={"default_provider": "not_a_real_provider"})
    assert result == "yfinance"


def test_resolve_provider_auto_with_no_config_defaults_to_yfinance():
    assert resolve_provider("auto") == "yfinance"


# ---------------------------------------------------------------------------
# _period_to_start_date
# ---------------------------------------------------------------------------

def test_period_to_start_date_valid():
    result = _period_to_start_date("3y")
    assert result is not None
    assert len(result) == 10  # ISO date YYYY-MM-DD


def test_period_to_start_date_short_returns_none():
    assert _period_to_start_date("") is None
    assert _period_to_start_date("3") is None  # len < 2 check: "3" is len 1


def test_period_to_start_date_unknown_unit_returns_none():
    assert _period_to_start_date("3x") is None


def test_period_to_start_date_invalid_amount_returns_none():
    assert _period_to_start_date("xy") is None


def test_period_to_start_date_all_units():
    for unit in ("d", "w", "m", "y"):
        result = _period_to_start_date(f"5{unit}")
        assert result is not None


# ---------------------------------------------------------------------------
# _period_to_start_date_yyyymmdd
# ---------------------------------------------------------------------------

def test_period_to_start_date_yyyymmdd_valid():
    result = _period_to_start_date_yyyymmdd("3y")
    assert len(result) == 8
    assert result.isdigit()


def test_period_to_start_date_yyyymmdd_empty_uses_default_3y():
    result = _period_to_start_date_yyyymmdd("")
    assert len(result) == 8
    assert result.isdigit()


# ---------------------------------------------------------------------------
# _period_to_end_date
# ---------------------------------------------------------------------------

def test_period_to_end_date_valid():
    result = _period_to_end_date("3m")
    assert len(result) == 8
    assert result.isdigit()


def test_period_to_end_date_short_returns_today():
    result = _period_to_end_date("")
    assert len(result) == 8


def test_period_to_end_date_unknown_unit_returns_today():
    result = _period_to_end_date("3x")
    assert len(result) == 8


def test_period_to_end_date_invalid_amount_returns_today():
    result = _period_to_end_date("abm")
    assert len(result) == 8


# ---------------------------------------------------------------------------
# _normalize_pykrx_columns
# ---------------------------------------------------------------------------

def test_normalize_pykrx_columns_renames_korean():
    frame = pd.DataFrame({
        "시가": [10.0], "고가": [11.0], "저가": [9.0], "종가": [10.5], "거래량": [1000.0]
    })
    result = _normalize_pykrx_columns(frame)
    assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]


def test_normalize_pykrx_columns_preserves_extra():
    frame = pd.DataFrame({"시가": [10.0], "extra": [1.0]})
    result = _normalize_pykrx_columns(frame)
    assert "Open" in result.columns
    assert "extra" in result.columns


# ---------------------------------------------------------------------------
# _openbb_to_frame
# ---------------------------------------------------------------------------

def test_openbb_to_frame_with_to_df():
    inner = _make_ohlcv_frame(3)

    class Fake:
        def to_df(self):
            return inner

    result = _openbb_to_frame(Fake())
    assert not result.empty


def test_openbb_to_frame_without_to_df_uses_results():
    inner = _make_ohlcv_frame(3)
    fake = SimpleNamespace(results=inner.reset_index().rename(columns={"index": "date"}))
    result = _openbb_to_frame(fake)
    assert not result.empty


def test_openbb_to_frame_with_date_column():
    frame = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=3),
        "open": [10.0, 11.0, 12.0],
        "high": [11.0, 12.0, 13.0],
        "low": [9.0, 10.0, 11.0],
        "close": [10.5, 11.5, 12.5],
        "volume": [1000.0, 1100.0, 1200.0],
    })

    class Fake:
        def to_df(self_inner):
            return frame

    result = _openbb_to_frame(Fake())
    # normalize_ohlcv should produce standard column names
    assert not result.empty


# ---------------------------------------------------------------------------
# _stable_seed and _make_synthetic_ohlcv
# ---------------------------------------------------------------------------

def test_stable_seed_deterministic():
    assert _stable_seed("AAPL") == _stable_seed("AAPL")
    assert _stable_seed("AAPL") != _stable_seed("MSFT")


def test_make_synthetic_ohlcv_shape():
    frame = _make_synthetic_ohlcv(n=100, seed=42)
    assert len(frame) == 100
    assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(frame.columns)


def test_make_synthetic_ohlcv_deterministic():
    f1 = _make_synthetic_ohlcv(n=20, seed=0)
    f2 = _make_synthetic_ohlcv(n=20, seed=0)
    pd.testing.assert_frame_equal(f1, f2)


# ---------------------------------------------------------------------------
# _elapsed_ms
# ---------------------------------------------------------------------------

def test_elapsed_ms_non_negative():
    import time
    start = time.perf_counter()
    result = _elapsed_ms(start)
    assert result >= 0.0


# ---------------------------------------------------------------------------
# _write_audit
# ---------------------------------------------------------------------------

def test_write_audit_with_none_logger_is_noop():
    # Should not raise
    _write_audit(
        None,
        AuditEvent(event_type="test", status="SUCCESS", command="test", ticker="AAPL", period="1y"),
    )


def test_write_audit_with_logger_writes_event(tmp_path):
    logger = AuditLogger(tmp_path / "audit.jsonl")
    _write_audit(
        logger,
        AuditEvent(
            event_type="provider_attempt",
            status="SUCCESS",
            command="recommend",
            ticker="AAPL",
            period="1y",
            provider_requested="yfinance",
            provider_used="yfinance",
        ),
    )
    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["status"] == "SUCCESS"
    assert data["ticker"] == "AAPL"


# ---------------------------------------------------------------------------
# Cache hit path (line 81)
# ---------------------------------------------------------------------------

def test_cache_hit_returns_cache_result(monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    fake_frame = _make_ohlcv_frame(10)
    # Monkeypatch the cache get to return a hit
    monkeypatch.setattr(dp._cache, "get", lambda *args: fake_frame)
    monkeypatch.setattr(dp._cache, "set", lambda *args: None)
    # Re-enable cache check by bypassing is_enabled check too
    # The code: if cached is not None: return ProviderResult(..., source=f"{selected}:cache")
    # But first resolve_provider selects "yfinance", then _cache.get is called
    # With USE_DATA_CACHE=0, _cache.get normally returns None — but we monkeypatched it
    result = load_ohlcv_with_provider(
        "AAPL", "1y", data_provider="yfinance", provider_config={}
    )
    assert result.source == "yfinance:cache"
    assert result.provider_used == "yfinance"


# ---------------------------------------------------------------------------
# _load_yfinance — success
# ---------------------------------------------------------------------------

def test_load_yfinance_success(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    frame = _make_ohlcv_frame(3)

    fake_yf = SimpleNamespace(download=lambda *args, **kwargs: frame)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    logger = AuditLogger(tmp_path / "audit.jsonl")
    result = load_ohlcv_with_provider(
        "AAPL", "1y",
        data_provider="yfinance",
        audit_logger=logger,
        provider_config={},
    )
    assert result.provider_used == "yfinance"
    assert result.source == "yfinance"
    assert not result.frame.empty
    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert any('"status": "SUCCESS"' in l for l in lines)


# ---------------------------------------------------------------------------
# _load_yfinance — failure (download raises)
# ---------------------------------------------------------------------------

def test_load_yfinance_download_raises_runtime_error(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")

    def bad_download(*args, **kwargs):
        raise ConnectionError("network unavailable")

    fake_yf = SimpleNamespace(download=bad_download)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    logger = AuditLogger(tmp_path / "audit.jsonl")
    with pytest.raises(RuntimeError, match="yfinance provider failed"):
        load_ohlcv_with_provider(
            "AAPL", "1y",
            data_provider="yfinance",
            audit_logger=logger,
            provider_config={},
        )
    log = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert '"status": "FAIL"' in log


# ---------------------------------------------------------------------------
# _load_yfinance — empty frame raises
# ---------------------------------------------------------------------------

def test_load_yfinance_empty_frame_raises(monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    # Return a frame that normalizes to empty
    empty_frame = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    fake_yf = SimpleNamespace(download=lambda *args, **kwargs: empty_frame)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    with pytest.raises(RuntimeError, match="yfinance provider failed"):
        load_ohlcv_with_provider("AAPL", "1y", data_provider="yfinance", provider_config={})


# ---------------------------------------------------------------------------
# _load_pykrx — success
# ---------------------------------------------------------------------------

def _fake_pykrx_stock_class(frame: pd.DataFrame):
    class FakePykrxStock:
        @staticmethod
        def get_market_ohlcv_by_date(start, end, symbol, freq, adjusted):
            return frame
    return FakePykrxStock()


def test_load_pykrx_success(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    krx_frame = pd.DataFrame(
        {
            "시가": [10.0, 11.0, 12.0],
            "고가": [11.0, 12.0, 13.0],
            "저가": [9.0, 10.0, 11.0],
            "종가": [10.5, 11.5, 12.5],
            "거래량": [1_000_000.0, 1_100_000.0, 1_200_000.0],
        },
        index=pd.date_range("2026-01-01", periods=3),
    )
    fake_stock = _fake_pykrx_stock_class(krx_frame)
    monkeypatch.setitem(sys.modules, "pykrx", SimpleNamespace(stock=fake_stock))
    monkeypatch.setitem(sys.modules, "pykrx.stock", fake_stock)

    logger = AuditLogger(tmp_path / "audit.jsonl")
    result = load_ohlcv_with_provider(
        "005930.KS", "1y",
        data_provider="pykrx",
        audit_logger=logger,
        provider_config={},
    )
    assert result.provider_used == "pykrx"
    assert result.source == "pykrx"
    assert not result.frame.empty


# ---------------------------------------------------------------------------
# _load_pykrx — failure falls back to FDR
# ---------------------------------------------------------------------------

def test_load_pykrx_fallback_to_fdr(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")

    class FakePykrxStock:
        @staticmethod
        def get_market_ohlcv_by_date(*args, **kwargs):
            raise RuntimeError("pykrx connection refused")

    monkeypatch.setitem(sys.modules, "pykrx", SimpleNamespace(stock=FakePykrxStock()))
    monkeypatch.setitem(sys.modules, "pykrx.stock", FakePykrxStock())

    fdr_frame = _make_ohlcv_frame(3)

    class FakeFDR:
        @staticmethod
        def DataReader(symbol, start):
            return fdr_frame

    monkeypatch.setitem(sys.modules, "FinanceDataReader", FakeFDR())

    logger = AuditLogger(tmp_path / "audit.jsonl")
    result = load_ohlcv_with_provider(
        "005930.KS", "1y",
        data_provider="pykrx",
        audit_logger=logger,
        provider_config={},
    )
    assert result.provider_used == "fdr"
    assert result.fallback_reason is not None
    assert "pykrx failed" in result.fallback_reason


# ---------------------------------------------------------------------------
# _load_fdr — success (.KS suffix)
# ---------------------------------------------------------------------------

def test_load_fdr_ks_suffix_maps_to_krx(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    fdr_frame = _make_ohlcv_frame(3)
    captured = {}

    class FakeFDR:
        @staticmethod
        def DataReader(symbol, start):
            captured["symbol"] = symbol
            return fdr_frame

    monkeypatch.setitem(sys.modules, "FinanceDataReader", FakeFDR())

    logger = AuditLogger(tmp_path / "audit.jsonl")
    result = load_ohlcv_with_provider(
        "005930.KS", "1y",
        data_provider="fdr",
        audit_logger=logger,
        provider_config={},
    )
    assert result.provider_used == "fdr"
    assert "KRX" in captured["symbol"]


def test_load_fdr_kq_suffix_maps_to_kosdaq(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    fdr_frame = _make_ohlcv_frame(3)
    captured = {}

    class FakeFDR:
        @staticmethod
        def DataReader(symbol, start):
            captured["symbol"] = symbol
            return fdr_frame

    monkeypatch.setitem(sys.modules, "FinanceDataReader", FakeFDR())

    load_ohlcv_with_provider(
        "000660.KQ", "1y",
        data_provider="fdr",
        provider_config={},
    )
    assert "KOSDAQ" in captured["symbol"]


# ---------------------------------------------------------------------------
# _load_fdr — failure raises RuntimeError
# ---------------------------------------------------------------------------

def test_load_fdr_failure_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")

    class FakeFDR:
        @staticmethod
        def DataReader(symbol, start):
            raise ConnectionError("FDR down")

    monkeypatch.setitem(sys.modules, "FinanceDataReader", FakeFDR())

    logger = AuditLogger(tmp_path / "audit.jsonl")
    with pytest.raises(RuntimeError, match="FDR provider failed"):
        load_ohlcv_with_provider(
            "AAPL", "1y",
            data_provider="fdr",
            audit_logger=logger,
            provider_config={},
        )
    log = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert '"status": "FAIL"' in log


# ---------------------------------------------------------------------------
# _load_fdr — empty frame raises
# ---------------------------------------------------------------------------

def test_load_fdr_empty_frame_raises(monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    class FakeFDR:
        @staticmethod
        def DataReader(symbol, start):
            return empty

    monkeypatch.setitem(sys.modules, "FinanceDataReader", FakeFDR())
    with pytest.raises(RuntimeError, match="FDR provider failed"):
        load_ohlcv_with_provider("AAPL", "1y", data_provider="fdr", provider_config={})


# ---------------------------------------------------------------------------
# _load_openbb — no start_date (short period)
# ---------------------------------------------------------------------------

def test_load_openbb_no_start_date(tmp_path, monkeypatch):
    """Period too short to produce start_date → kwargs without start_date."""
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    frame = _make_ohlcv_frame(3)
    calls = {}

    class FakeResult:
        def to_df(self):
            return frame

    def historical(**kwargs):
        calls.update(kwargs)
        return FakeResult()

    fake_obb = SimpleNamespace(equity=SimpleNamespace(price=SimpleNamespace(historical=historical)))
    monkeypatch.setitem(sys.modules, "openbb", SimpleNamespace(obb=fake_obb))

    result = load_ohlcv_with_provider(
        "AAPL", "3",  # too short → no start_date
        data_provider="openbb",
        provider_config={},
    )
    assert result.provider_used == "openbb"
    assert "start_date" not in calls


# ---------------------------------------------------------------------------
# _load_openbb — empty frame raises
# ---------------------------------------------------------------------------

def test_load_openbb_empty_frame_raises(monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    class FakeResult:
        def to_df(self):
            return empty

    def historical(**kwargs):
        return FakeResult()

    fake_obb = SimpleNamespace(equity=SimpleNamespace(price=SimpleNamespace(historical=historical)))
    monkeypatch.setitem(sys.modules, "openbb", SimpleNamespace(obb=fake_obb))

    with pytest.raises(RuntimeError, match="OpenBB provider failed"):
        load_ohlcv_with_provider("AAPL", "1y", data_provider="openbb", provider_config={})


# ---------------------------------------------------------------------------
# Cache set — verify _cache.set called after non-empty result
# ---------------------------------------------------------------------------

def test_cache_set_called_after_provider_load(monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    frame = _make_ohlcv_frame(3)
    fake_yf = SimpleNamespace(download=lambda *args, **kwargs: frame)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    set_calls = []
    monkeypatch.setattr(dp._cache, "get", lambda *args: None)
    monkeypatch.setattr(dp._cache, "set", lambda *args: set_calls.append(args))

    load_ohlcv_with_provider("AAPL", "1y", data_provider="yfinance", provider_config={})
    assert len(set_calls) == 1
    assert set_calls[0][0] == "AAPL"


# ---------------------------------------------------------------------------
# provider_config_path integration
# ---------------------------------------------------------------------------

def test_load_ohlcv_uses_provider_config_path(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    cfg = {"default_provider": "yfinance"}
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    frame = _make_ohlcv_frame(3)
    fake_yf = SimpleNamespace(download=lambda *args, **kwargs: frame)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)
    monkeypatch.setattr(dp._cache, "get", lambda *args: None)
    monkeypatch.setattr(dp._cache, "set", lambda *args: None)

    result = load_ohlcv_with_provider(
        "AAPL", "1y",
        data_provider="auto",
        provider_config_path=str(cfg_path),
    )
    assert result.provider_used == "yfinance"
