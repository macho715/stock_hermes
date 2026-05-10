"""Tests for data_lake/corp_actions/splits_dividends.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from stock_rtx4060.data_lake.corp_actions.splits_dividends import (
    CorpAction,
    fetch_pykrx_actions,
    fetch_yf_actions,
)


# ---------------------------------------------------------------------------
# CorpAction dataclass
# ---------------------------------------------------------------------------


class TestCorpAction:
    def test_split_to_dict(self):
        ts = pd.Timestamp("2023-06-01")
        action = CorpAction(date=ts, type="split", ratio=2.0)
        d = action.to_dict()
        assert d["type"] == "split"
        assert d["ratio"] == 2.0
        assert d["cash_amount"] is None
        assert d["date"] == ts.isoformat()

    def test_dividend_to_dict(self):
        ts = pd.Timestamp("2023-12-15")
        action = CorpAction(date=ts, type="dividend", cash_amount=0.23)
        d = action.to_dict()
        assert d["type"] == "dividend"
        assert d["cash_amount"] == pytest.approx(0.23)
        assert d["ratio"] is None

    def test_frozen_immutable(self):
        ts = pd.Timestamp("2024-01-01")
        action = CorpAction(date=ts, type="split", ratio=3.0)
        with pytest.raises((AttributeError, TypeError)):
            action.ratio = 4.0  # type: ignore[misc]

    def test_split_zero_cash(self):
        ts = pd.Timestamp("2022-07-01")
        action = CorpAction(date=ts, type="split", ratio=4.0, cash_amount=None)
        assert action.cash_amount is None

    def test_dividend_zero_ratio(self):
        ts = pd.Timestamp("2022-09-01")
        action = CorpAction(date=ts, type="dividend", ratio=None, cash_amount=1.50)
        assert action.ratio is None
        assert action.cash_amount == pytest.approx(1.50)


# ---------------------------------------------------------------------------
# fetch_yf_actions — mocked yfinance
# ---------------------------------------------------------------------------


class TestFetchYfActions:
    def _make_actions_df(self, data: dict) -> pd.DataFrame:
        """Build a yfinance-style actions DataFrame with a DatetimeIndex."""
        idx = pd.to_datetime(list(data.keys()))
        rows = list(data.values())
        df = pd.DataFrame(rows, index=idx)
        return df

    def test_returns_empty_when_yfinance_unavailable(self, monkeypatch):
        """ImportError inside fetch_yf_actions yields empty list."""
        with patch.dict("sys.modules", {"yfinance": None}):
            result = fetch_yf_actions("AAPL")
        assert result == []

    def test_returns_empty_on_none_dataframe(self, monkeypatch):
        yf_mod = MagicMock()
        ticker_mock = MagicMock()
        ticker_mock.actions = None
        yf_mod.Ticker.return_value = ticker_mock
        monkeypatch.setitem(__import__("sys").modules, "yfinance", yf_mod)
        result = fetch_yf_actions("AAPL")
        assert result == []

    def test_returns_empty_on_empty_dataframe(self, monkeypatch):
        yf_mod = MagicMock()
        ticker_mock = MagicMock()
        ticker_mock.actions = pd.DataFrame()
        yf_mod.Ticker.return_value = ticker_mock
        monkeypatch.setitem(__import__("sys").modules, "yfinance", yf_mod)
        result = fetch_yf_actions("AAPL")
        assert result == []

    def test_two_for_one_split_parsed(self, monkeypatch):
        yf_mod = MagicMock()
        ticker_mock = MagicMock()
        df = pd.DataFrame(
            [{"Dividends": 0.0, "Stock Splits": 2.0}],
            index=pd.to_datetime(["2021-08-16"]),
        )
        ticker_mock.actions = df
        yf_mod.Ticker.return_value = ticker_mock
        monkeypatch.setitem(__import__("sys").modules, "yfinance", yf_mod)
        result = fetch_yf_actions("TSLA")
        assert len(result) == 1
        assert result[0].type == "split"
        assert result[0].ratio == pytest.approx(2.0)
        assert result[0].cash_amount is None

    def test_dividend_parsed(self, monkeypatch):
        yf_mod = MagicMock()
        ticker_mock = MagicMock()
        df = pd.DataFrame(
            [{"Dividends": 0.88, "Stock Splits": 0.0}],
            index=pd.to_datetime(["2023-02-10"]),
        )
        ticker_mock.actions = df
        yf_mod.Ticker.return_value = ticker_mock
        monkeypatch.setitem(__import__("sys").modules, "yfinance", yf_mod)
        result = fetch_yf_actions("AAPL")
        assert len(result) == 1
        assert result[0].type == "dividend"
        assert result[0].cash_amount == pytest.approx(0.88)

    def test_split_and_dividend_on_same_row(self, monkeypatch):
        yf_mod = MagicMock()
        ticker_mock = MagicMock()
        df = pd.DataFrame(
            [{"Dividends": 0.50, "Stock Splits": 3.0}],
            index=pd.to_datetime(["2023-05-01"]),
        )
        ticker_mock.actions = df
        yf_mod.Ticker.return_value = ticker_mock
        monkeypatch.setitem(__import__("sys").modules, "yfinance", yf_mod)
        result = fetch_yf_actions("X")
        types = {a.type for a in result}
        assert "split" in types
        assert "dividend" in types
        assert len(result) == 2

    def test_no_actions_row_zero_split_and_zero_div(self, monkeypatch):
        yf_mod = MagicMock()
        ticker_mock = MagicMock()
        df = pd.DataFrame(
            [{"Dividends": 0.0, "Stock Splits": 0.0}],
            index=pd.to_datetime(["2023-01-01"]),
        )
        ticker_mock.actions = df
        yf_mod.Ticker.return_value = ticker_mock
        monkeypatch.setitem(__import__("sys").modules, "yfinance", yf_mod)
        result = fetch_yf_actions("NVDA")
        assert result == [], "Zero split and zero dividend should produce no actions"

    def test_four_for_one_split(self, monkeypatch):
        yf_mod = MagicMock()
        ticker_mock = MagicMock()
        df = pd.DataFrame(
            [{"Dividends": 0.0, "Stock Splits": 4.0}],
            index=pd.to_datetime(["2022-07-18"]),
        )
        ticker_mock.actions = df
        yf_mod.Ticker.return_value = ticker_mock
        monkeypatch.setitem(__import__("sys").modules, "yfinance", yf_mod)
        result = fetch_yf_actions("GOOGL")
        assert len(result) == 1
        assert result[0].ratio == pytest.approx(4.0)

    def test_multiple_rows_multiple_actions(self, monkeypatch):
        yf_mod = MagicMock()
        ticker_mock = MagicMock()
        df = pd.DataFrame(
            [
                {"Dividends": 0.23, "Stock Splits": 0.0},
                {"Dividends": 0.0, "Stock Splits": 2.0},
                {"Dividends": 0.25, "Stock Splits": 0.0},
            ],
            index=pd.to_datetime(["2022-03-01", "2022-06-01", "2022-09-01"]),
        )
        ticker_mock.actions = df
        yf_mod.Ticker.return_value = ticker_mock
        monkeypatch.setitem(__import__("sys").modules, "yfinance", yf_mod)
        result = fetch_yf_actions("MSFT")
        assert len(result) == 3
        divs = [a for a in result if a.type == "dividend"]
        splits = [a for a in result if a.type == "split"]
        assert len(divs) == 2
        assert len(splits) == 1


# ---------------------------------------------------------------------------
# fetch_pykrx_actions — mocked pykrx
# ---------------------------------------------------------------------------


class TestFetchPykrxActions:
    def test_returns_empty_when_pykrx_unavailable(self):
        with patch.dict("sys.modules", {"pykrx": None, "pykrx.stock": None}):
            result = fetch_pykrx_actions("005930", "20230101", "20231231")
        assert result == []

    def test_returns_empty_on_none_dataframe(self, monkeypatch):
        pkx_mod = MagicMock()
        pkx_mod.get_market_fundamental_by_date.return_value = None
        stock_mod = MagicMock()
        stock_mod.get_market_fundamental_by_date.return_value = None
        monkeypatch.setitem(__import__("sys").modules, "pykrx", pkx_mod)
        monkeypatch.setitem(__import__("sys").modules, "pykrx.stock", stock_mod)
        result = fetch_pykrx_actions("005930", "20230101", "20231231")
        assert result == []

    def test_returns_empty_on_empty_dataframe(self, monkeypatch):
        pkx_mod = MagicMock()
        stock_mod = MagicMock()
        stock_mod.get_market_fundamental_by_date.return_value = pd.DataFrame()
        pkx_mod.stock = stock_mod
        monkeypatch.setitem(__import__("sys").modules, "pykrx", pkx_mod)
        monkeypatch.setitem(__import__("sys").modules, "pykrx.stock", stock_mod)
        result = fetch_pykrx_actions("005930", "20230101", "20231231")
        assert result == []

    def test_returns_empty_when_no_dps_column(self, monkeypatch):
        pkx_mod = MagicMock()
        stock_mod = MagicMock()
        df = pd.DataFrame({"PBR": [1.2, 1.3]}, index=pd.to_datetime(["2023-03-01", "2023-06-01"]))
        stock_mod.get_market_fundamental_by_date.return_value = df
        pkx_mod.stock = stock_mod
        monkeypatch.setitem(__import__("sys").modules, "pykrx", pkx_mod)
        monkeypatch.setitem(__import__("sys").modules, "pykrx.stock", stock_mod)
        result = fetch_pykrx_actions("005930", "20230101", "20231231")
        assert result == []

    def test_dividend_detected_on_dps_change(self, monkeypatch):
        pkx_mod = MagicMock()
        stock_mod = MagicMock()
        df = pd.DataFrame(
            {"DPS": [0.0, 500.0, 500.0]},
            index=pd.to_datetime(["2023-01-01", "2023-04-01", "2023-07-01"]),
        )
        stock_mod.get_market_fundamental_by_date.return_value = df
        pkx_mod.stock = stock_mod
        monkeypatch.setitem(__import__("sys").modules, "pykrx", pkx_mod)
        monkeypatch.setitem(__import__("sys").modules, "pykrx.stock", stock_mod)
        result = fetch_pykrx_actions("005930", "20230101", "20231231")
        assert len(result) == 1
        assert result[0].type == "dividend"
        assert result[0].cash_amount == pytest.approx(500.0)

    def test_no_dividend_when_dps_constant(self, monkeypatch):
        pkx_mod = MagicMock()
        stock_mod = MagicMock()
        df = pd.DataFrame(
            {"DPS": [200.0, 200.0, 200.0]},
            index=pd.to_datetime(["2023-01-01", "2023-04-01", "2023-07-01"]),
        )
        stock_mod.get_market_fundamental_by_date.return_value = df
        pkx_mod.stock = stock_mod
        monkeypatch.setitem(__import__("sys").modules, "pykrx", pkx_mod)
        monkeypatch.setitem(__import__("sys").modules, "pykrx.stock", stock_mod)
        result = fetch_pykrx_actions("005930", "20230101", "20231231")
        # Only first non-zero change from prev=0 should trigger
        assert len(result) == 1
        assert result[0].cash_amount == pytest.approx(200.0)

    def test_zero_dps_rows_produce_no_actions(self, monkeypatch):
        pkx_mod = MagicMock()
        stock_mod = MagicMock()
        df = pd.DataFrame(
            {"DPS": [0.0, 0.0, 0.0]},
            index=pd.to_datetime(["2023-01-01", "2023-04-01", "2023-07-01"]),
        )
        stock_mod.get_market_fundamental_by_date.return_value = df
        pkx_mod.stock = stock_mod
        monkeypatch.setitem(__import__("sys").modules, "pykrx", pkx_mod)
        monkeypatch.setitem(__import__("sys").modules, "pykrx.stock", stock_mod)
        result = fetch_pykrx_actions("005930", "20230101", "20231231")
        assert result == []

    def test_exception_during_fetch_returns_empty(self, monkeypatch):
        pkx_mod = MagicMock()
        stock_mod = MagicMock()
        stock_mod.get_market_fundamental_by_date.side_effect = RuntimeError("network")
        pkx_mod.stock = stock_mod
        monkeypatch.setitem(__import__("sys").modules, "pykrx", pkx_mod)
        monkeypatch.setitem(__import__("sys").modules, "pykrx.stock", stock_mod)
        result = fetch_pykrx_actions("005930", "20230101", "20231231")
        assert result == []
