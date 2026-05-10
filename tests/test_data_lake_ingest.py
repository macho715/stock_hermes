"""Unit tests for data_lake ingest modules — no network, all external calls mocked."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ohlcv_df(n: int = 20, tz_aware: bool = False) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=n)
    if tz_aware:
        idx = idx.tz_localize("America/New_York")
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame(
        {
            "Open": close * 0.99,
            "High": close * 1.02,
            "Low": close * 0.98,
            "Close": close,
            "Volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
        },
        index=idx,
    )


def _make_mock_store(written: int = 20) -> MagicMock:
    store = MagicMock()
    store.write.return_value = written
    return store


# ---------------------------------------------------------------------------
# yf_ingestor
# ---------------------------------------------------------------------------

class TestYFIngestor:
    def test_successful_ingest_returns_row_count(self, tmp_path):
        from stock_rtx4060.data_lake.ingest.yf_ingestor import ingest_yf

        df = _ohlcv_df(20)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        store = _make_mock_store(written=20)

        with patch.dict(sys.modules, {"yfinance": mock_yf}), \
             patch("stock_rtx4060.data_lake.ingest.yf_ingestor.log_pit_write"):
            result = ingest_yf("AAPL", period="5y", store=store)

        assert result == 20
        store.write.assert_called_once()
        call_kwargs = store.write.call_args
        assert call_kwargs.kwargs["source"] == "yfinance"

    def test_empty_response_returns_zero(self):
        from stock_rtx4060.data_lake.ingest.yf_ingestor import ingest_yf

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        store = _make_mock_store()

        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = ingest_yf("AAPL", store=store)

        assert result == 0
        store.write.assert_not_called()

    def test_none_response_returns_zero(self):
        from stock_rtx4060.data_lake.ingest.yf_ingestor import ingest_yf

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = None

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        store = _make_mock_store()

        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = ingest_yf("AAPL", store=store)

        assert result == 0

    def test_yfinance_absent_returns_zero(self):
        from stock_rtx4060.data_lake.ingest.yf_ingestor import ingest_yf

        store = _make_mock_store()

        with patch.dict(sys.modules, {"yfinance": None}):
            result = ingest_yf("AAPL", store=store)

        assert result == 0

    def test_tz_aware_index_stripped(self, tmp_path):
        from stock_rtx4060.data_lake.ingest.yf_ingestor import ingest_yf

        df_tz = _ohlcv_df(10, tz_aware=True)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df_tz

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        written_dfs: list[pd.DataFrame] = []

        def _capture_write(ticker, df, *, source):
            written_dfs.append(df)
            return len(df)

        store = MagicMock()
        store.write.side_effect = _capture_write

        with patch.dict(sys.modules, {"yfinance": mock_yf}), \
             patch("stock_rtx4060.data_lake.ingest.yf_ingestor.log_pit_write"):
            ingest_yf("AAPL", store=store)

        assert len(written_dfs) == 1
        assert written_dfs[0].index.tz is None

    def test_output_columns_subset(self, tmp_path):
        """Ingestor must only pass OHLCV columns to store.write."""
        from stock_rtx4060.data_lake.ingest.yf_ingestor import ingest_yf

        df = _ohlcv_df(5)
        df["Dividends"] = 0.0
        df["Stock Splits"] = 0.0
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        written_dfs: list[pd.DataFrame] = []

        def _capture(ticker, frame, *, source):
            written_dfs.append(frame)
            return len(frame)

        store = MagicMock()
        store.write.side_effect = _capture

        with patch.dict(sys.modules, {"yfinance": mock_yf}), \
             patch("stock_rtx4060.data_lake.ingest.yf_ingestor.log_pit_write"):
            ingest_yf("AAPL", store=store)

        assert set(written_dfs[0].columns) == {"Open", "High", "Low", "Close", "Volume"}


# ---------------------------------------------------------------------------
# alpaca_ingestor
# ---------------------------------------------------------------------------

class TestAlpacaIngestor:
    def _setup_alpaca_mocks(self, df: pd.DataFrame):
        """Build a minimal alpaca-py SDK mock tree."""
        mock_bars_resp = MagicMock()
        mock_bars_resp.df = df

        mock_client = MagicMock()
        mock_client.get_stock_bars.return_value = mock_bars_resp

        mock_stock_client_cls = MagicMock(return_value=mock_client)
        mock_req_cls = MagicMock()

        mock_tf = MagicMock()
        mock_tf.Day = "Day"
        mock_tf.Hour = "Hour"
        mock_tf.Minute = "Minute"

        mock_tfu = MagicMock()
        mock_tfu.Minute = "Minute"

        mock_data_hist = MagicMock()
        mock_data_hist.StockHistoricalDataClient = mock_stock_client_cls

        mock_data_req = MagicMock()
        mock_data_req.StockBarsRequest = mock_req_cls

        mock_data_tf = MagicMock()
        mock_data_tf.TimeFrame = mock_tf
        mock_data_tf.TimeFrameUnit = mock_tfu

        alpaca_mocks = {
            "alpaca": MagicMock(),
            "alpaca.data": MagicMock(),
            "alpaca.data.historical": mock_data_hist,
            "alpaca.data.requests": mock_data_req,
            "alpaca.data.timeframe": mock_data_tf,
        }
        return alpaca_mocks, mock_client

    def test_missing_env_vars_returns_zero(self, monkeypatch):
        from stock_rtx4060.data_lake.ingest.alpaca_ingestor import ingest_alpaca

        monkeypatch.delenv("ALPACA_API_KEY", raising=False)
        monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
        result = ingest_alpaca("AAPL")
        assert result == 0

    def test_alpaca_sdk_missing_returns_zero(self, monkeypatch):
        from stock_rtx4060.data_lake.ingest.alpaca_ingestor import ingest_alpaca

        monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")

        with patch.dict(sys.modules, {
            "alpaca": None,
            "alpaca.data": None,
            "alpaca.data.historical": None,
            "alpaca.data.requests": None,
            "alpaca.data.timeframe": None,
        }):
            result = ingest_alpaca("AAPL")
        assert result == 0

    def test_successful_ingest(self, monkeypatch):
        from stock_rtx4060.data_lake.ingest.alpaca_ingestor import ingest_alpaca

        monkeypatch.setenv("ALPACA_API_KEY", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")

        df = pd.DataFrame(
            {
                "open": [100.0, 101.0],
                "high": [102.0, 103.0],
                "low": [99.0, 100.0],
                "close": [101.0, 102.0],
                "volume": [1000.0, 2000.0],
            },
            index=pd.bdate_range("2024-01-02", periods=2),
        )

        alpaca_mocks, _ = self._setup_alpaca_mocks(df)
        store = _make_mock_store(written=2)

        with patch.dict(sys.modules, alpaca_mocks), \
             patch("stock_rtx4060.data_lake.ingest.alpaca_ingestor.log_pit_write"):
            import importlib
            import stock_rtx4060.data_lake.ingest.alpaca_ingestor as mod
            importlib.reload(mod)
            result = mod.ingest_alpaca("AAPL", store=store)

        assert result == 2

    def test_empty_bars_returns_zero(self, monkeypatch):
        from stock_rtx4060.data_lake.ingest.alpaca_ingestor import ingest_alpaca

        monkeypatch.setenv("ALPACA_API_KEY", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")

        alpaca_mocks, _ = self._setup_alpaca_mocks(pd.DataFrame())
        store = _make_mock_store()

        with patch.dict(sys.modules, alpaca_mocks), \
             patch("stock_rtx4060.data_lake.ingest.alpaca_ingestor.log_pit_write"):
            import importlib
            import stock_rtx4060.data_lake.ingest.alpaca_ingestor as mod
            importlib.reload(mod)
            result = mod.ingest_alpaca("AAPL", store=store)

        assert result == 0
        store.write.assert_not_called()

    def test_tz_aware_index_stripped(self, monkeypatch):
        from stock_rtx4060.data_lake.ingest.alpaca_ingestor import ingest_alpaca

        monkeypatch.setenv("ALPACA_API_KEY", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")

        idx = pd.bdate_range("2024-01-02", periods=3).tz_localize("UTC")
        df = pd.DataFrame(
            {"open": [1.0]*3, "high": [1.0]*3, "low": [1.0]*3, "close": [1.0]*3, "volume": [1.0]*3},
            index=idx,
        )
        alpaca_mocks, _ = self._setup_alpaca_mocks(df)

        written_dfs: list[pd.DataFrame] = []

        def _cap(ticker, frame, *, source):
            written_dfs.append(frame)
            return len(frame)

        store = MagicMock()
        store.write.side_effect = _cap

        with patch.dict(sys.modules, alpaca_mocks), \
             patch("stock_rtx4060.data_lake.ingest.alpaca_ingestor.log_pit_write"):
            import importlib
            import stock_rtx4060.data_lake.ingest.alpaca_ingestor as mod
            importlib.reload(mod)
            mod.ingest_alpaca("AAPL", store=store)

        assert len(written_dfs) == 1
        assert written_dfs[0].index.tz is None

    def test_date_range_defaults(self, monkeypatch):
        """When start/end omitted, client.get_stock_bars must still be called."""
        monkeypatch.setenv("ALPACA_API_KEY", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")

        df = pd.DataFrame(
            {"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0]},
            index=pd.bdate_range("2024-01-02", periods=1),
        )
        alpaca_mocks, mock_client = self._setup_alpaca_mocks(df)
        store = _make_mock_store(written=1)

        with patch.dict(sys.modules, alpaca_mocks), \
             patch("stock_rtx4060.data_lake.ingest.alpaca_ingestor.log_pit_write"):
            import importlib
            import stock_rtx4060.data_lake.ingest.alpaca_ingestor as mod
            importlib.reload(mod)
            mod.ingest_alpaca("AAPL", store=store)

        mock_client.get_stock_bars.assert_called_once()

    def test_output_columns_renamed_correctly(self, monkeypatch):
        monkeypatch.setenv("ALPACA_API_KEY", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")

        df = pd.DataFrame(
            {"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0]},
            index=pd.bdate_range("2024-01-02", periods=1),
        )
        alpaca_mocks, _ = self._setup_alpaca_mocks(df)

        written_dfs: list[pd.DataFrame] = []

        def _cap(ticker, frame, *, source):
            written_dfs.append(frame)
            return len(frame)

        store = MagicMock()
        store.write.side_effect = _cap

        with patch.dict(sys.modules, alpaca_mocks), \
             patch("stock_rtx4060.data_lake.ingest.alpaca_ingestor.log_pit_write"):
            import importlib
            import stock_rtx4060.data_lake.ingest.alpaca_ingestor as mod
            importlib.reload(mod)
            mod.ingest_alpaca("AAPL", store=store)

        assert set(written_dfs[0].columns) == {"Open", "High", "Low", "Close", "Volume"}


# ---------------------------------------------------------------------------
# kis_ingestor — KISCredentials and helpers
# ---------------------------------------------------------------------------

class TestKISCredentials:
    def test_load_credentials_missing_file(self, tmp_path):
        from stock_rtx4060.data_lake.ingest.kis_ingestor import _load_credentials

        with pytest.raises(FileNotFoundError, match="credential"):
            _load_credentials(tmp_path / "nonexistent.toml")

    def test_load_credentials_success(self, tmp_path):
        from stock_rtx4060.data_lake.ingest.kis_ingestor import _load_credentials

        cred_file = tmp_path / "kis.toml"
        cred_file.write_text(
            'appkey = "MYKEY"\nappsecret = "MYSECRET"\naccount_number = "123"\npaper = true\n',
            encoding="utf-8",
        )
        creds = _load_credentials(cred_file)
        assert creds.appkey == "MYKEY"
        assert creds.appsecret == "MYSECRET"
        assert creds.account_number == "123"
        assert creds.paper is True

    def test_load_credentials_defaults(self, tmp_path):
        from stock_rtx4060.data_lake.ingest.kis_ingestor import _load_credentials

        cred_file = tmp_path / "kis.toml"
        cred_file.write_text(
            'appkey = "K"\nappsecret = "S"\n',
            encoding="utf-8",
        )
        creds = _load_credentials(cred_file)
        assert creds.account_number == ""
        assert creds.paper is True


class TestKISFetchToken:
    def test_returns_cached_token_when_fresh(self, tmp_path, monkeypatch):
        import json
        import time

        from stock_rtx4060.data_lake.ingest.kis_ingestor import KISCredentials, _fetch_token

        cache_file = tmp_path / "kis_token.json"
        cache_file.write_text(
            json.dumps({"access_token": "CACHED_TOK", "expires_at": time.time() + 7200}),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "stock_rtx4060.data_lake.ingest.kis_ingestor.KIS_TOKEN_CACHE",
            cache_file,
        )
        creds = KISCredentials(appkey="K", appsecret="S")
        token = _fetch_token(creds)
        assert token == "CACHED_TOK"

    def test_fetches_new_token_when_cache_expired(self, tmp_path, monkeypatch):
        import json
        import time

        from stock_rtx4060.data_lake.ingest.kis_ingestor import KISCredentials, _fetch_token

        cache_file = tmp_path / "kis_token.json"
        cache_file.write_text(
            json.dumps({"access_token": "OLD", "expires_at": time.time() - 100}),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "stock_rtx4060.data_lake.ingest.kis_ingestor.KIS_TOKEN_CACHE",
            cache_file,
        )
        monkeypatch.setattr(
            "stock_rtx4060.data_lake.ingest.kis_ingestor.KIS_BASE_URL",
            "http://fake-url",
        )

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "NEW_TOK", "expires_in": 86400}
        mock_resp.raise_for_status.return_value = None

        mock_httpx = MagicMock()
        mock_httpx.post.return_value = mock_resp

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            import importlib
            import stock_rtx4060.data_lake.ingest.kis_ingestor as mod
            importlib.reload(mod)
            mod.KIS_TOKEN_CACHE = cache_file
            mod.KIS_BASE_URL = "http://fake-url"
            creds = mod.KISCredentials(appkey="K", appsecret="S")
            token = mod._fetch_token(creds)

        assert token == "NEW_TOK"


class TestKISFetchDailyBars:
    def _mock_response(self, rows: list[dict]) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"output2": rows}
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    def test_returns_empty_df_on_no_rows(self, tmp_path, monkeypatch):
        from stock_rtx4060.data_lake.ingest.kis_ingestor import KISCredentials, _fetch_daily_bars

        mock_httpx = MagicMock()
        mock_httpx.get.return_value = self._mock_response([])

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            import importlib
            import stock_rtx4060.data_lake.ingest.kis_ingestor as mod
            importlib.reload(mod)
            creds = mod.KISCredentials(appkey="K", appsecret="S")
            df = mod._fetch_daily_bars("005930", "20240101", "20240131",
                                       creds=creds, token="T")

        assert df.empty

    def test_returns_correct_columns(self, monkeypatch):
        from stock_rtx4060.data_lake.ingest.kis_ingestor import KISCredentials, _fetch_daily_bars

        rows = [
            {
                "stck_bsop_date": "20240102",
                "stck_oprc": "71000",
                "stck_hgpr": "72000",
                "stck_lwpr": "70500",
                "stck_clpr": "71500",
                "acml_vol": "9000000",
            }
        ]
        mock_httpx = MagicMock()
        mock_httpx.get.return_value = self._mock_response(rows)

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            import importlib
            import stock_rtx4060.data_lake.ingest.kis_ingestor as mod
            importlib.reload(mod)
            creds = mod.KISCredentials(appkey="K", appsecret="S")
            df = mod._fetch_daily_bars("005930", "20240102", "20240102",
                                       creds=creds, token="T")

        assert set(df.columns) == {"Open", "High", "Low", "Close", "Volume"}
        assert len(df) == 1
        assert df["Close"].iloc[0] == pytest.approx(71500.0)


class TestIngestKIS:
    def test_ingest_kis_empty_bars_returns_zero(self, tmp_path, monkeypatch):
        from stock_rtx4060.data_lake.ingest.kis_ingestor import ingest_kis

        cred_file = tmp_path / "kis.toml"
        cred_file.write_text(
            'appkey = "K"\nappsecret = "S"\n', encoding="utf-8"
        )
        store = _make_mock_store()

        with patch("stock_rtx4060.data_lake.ingest.kis_ingestor._load_credentials") as mock_load, \
             patch("stock_rtx4060.data_lake.ingest.kis_ingestor._fetch_token", return_value="T"), \
             patch("stock_rtx4060.data_lake.ingest.kis_ingestor._fetch_daily_bars",
                   return_value=pd.DataFrame()):
            from stock_rtx4060.data_lake.ingest.kis_ingestor import KISCredentials
            mock_load.return_value = KISCredentials(appkey="K", appsecret="S")
            result = ingest_kis("005930", start="20240101", end="20240131", store=store)

        assert result == 0
        store.write.assert_not_called()

    def test_ingest_kis_success(self, tmp_path):
        from stock_rtx4060.data_lake.ingest.kis_ingestor import KISCredentials, ingest_kis

        df = _ohlcv_df(5)
        store = _make_mock_store(written=5)

        with patch("stock_rtx4060.data_lake.ingest.kis_ingestor._load_credentials") as mock_load, \
             patch("stock_rtx4060.data_lake.ingest.kis_ingestor._fetch_token", return_value="T"), \
             patch("stock_rtx4060.data_lake.ingest.kis_ingestor._fetch_daily_bars", return_value=df), \
             patch("stock_rtx4060.data_lake.ingest.kis_ingestor.log_pit_write"):
            mock_load.return_value = KISCredentials(appkey="K", appsecret="S")
            result = ingest_kis("005930", start="20240101", end="20240131", store=store)

        assert result == 5
        store.write.assert_called_once()
        assert store.write.call_args.kwargs["source"] == "kis"
