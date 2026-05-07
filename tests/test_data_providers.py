import builtins
import json
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from stock_rtx4060.audit_log import AuditLogger
from stock_rtx4060.data_providers import load_ohlcv_with_provider, resolve_provider


def test_resolve_provider_cli_overrides_config_and_synthetic_flag():
    assert resolve_provider("auto", provider_config={"default_provider": "openbb"}) == "openbb"
    assert resolve_provider("yfinance", provider_config={"default_provider": "openbb"}) == "yfinance"
    assert resolve_provider("auto", synthetic=True, provider_config={"default_provider": "openbb"}) == "synthetic"


def test_synthetic_provider_writes_audit_event(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    logger = AuditLogger(tmp_path / "audit_log.jsonl")
    result = load_ohlcv_with_provider("SYNTH-A", "3y", synthetic=True, audit_logger=logger, command="recommend")

    assert not result.frame.empty
    assert result.provider_used == "synthetic"
    rows = [json.loads(line) for line in (tmp_path / "audit_log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["status"] == "SUCCESS"
    assert rows[0]["provider_used"] == "synthetic"
    assert rows[0]["metadata"]["provider_validation_status"] == "PASS"
    assert rows[0]["metadata"]["row_count"] == len(result.frame)
    assert result.metadata["provider_validation"]["status"] == "PASS"


def test_openbb_provider_normalizes_mocked_historical_response(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DATA_CACHE", "0")
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=3),
            "open": [10, 11, 12],
            "high": [11, 12, 13],
            "low": [9, 10, 11],
            "close": [10.5, 11.5, 12.5],
            "volume": [1000, 1100, 1200],
        }
    )
    calls = {}

    class FakeResult:
        def to_df(self):
            return frame

    def historical(**kwargs):
        calls.update(kwargs)
        return FakeResult()

    fake_obb = SimpleNamespace(equity=SimpleNamespace(price=SimpleNamespace(historical=historical)))
    monkeypatch.setitem(sys.modules, "openbb", SimpleNamespace(obb=fake_obb))

    logger = AuditLogger(tmp_path / "audit_log.jsonl")
    result = load_ohlcv_with_provider("AAPL", "1y", data_provider="openbb", audit_logger=logger)

    assert result.provider_used == "openbb"
    assert result.source == "openbb:yfinance"
    assert calls["symbol"] == "AAPL"
    assert calls["provider"] == "yfinance"
    assert list(result.frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    log_text = (tmp_path / "audit_log.jsonl").read_text(encoding="utf-8")
    assert "obb.equity.price.historical" in log_text
    rows = [json.loads(line) for line in log_text.splitlines()]
    assert rows[0]["metadata"]["provider_validation_status"] == "AMBER"
    assert result.metadata["provider_validation"]["row_count"] == 3


def test_openbb_missing_does_not_break_synthetic(tmp_path, monkeypatch):
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "openbb":
            raise ImportError("blocked openbb for test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    logger = AuditLogger(tmp_path / "audit_log.jsonl")
    result = load_ohlcv_with_provider("SYNTH-B", "3y", synthetic=True, data_provider="auto", audit_logger=logger)

    assert result.provider_used == "synthetic"


def test_openbb_missing_records_failure(tmp_path, monkeypatch):
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "openbb":
            raise ImportError("blocked openbb for test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    logger = AuditLogger(tmp_path / "audit_log.jsonl")

    with pytest.raises(RuntimeError, match="OpenBB provider failed"):
        load_ohlcv_with_provider("AAPL", "3y", data_provider="openbb", audit_logger=logger)

    log_text = (tmp_path / "audit_log.jsonl").read_text(encoding="utf-8")
    assert '"status": "FAIL"' in log_text
    assert '"provider_used": "openbb"' in log_text
