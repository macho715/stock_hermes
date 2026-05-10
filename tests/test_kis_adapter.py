"""Tests for KISAdapter (Phase 8).

Uses ``--mock`` mode — no real HTTP calls.
"""

from __future__ import annotations

import json
import os
import time
from unittest.mock import patch

import pytest


class TestKISAdapterMockMode:
    """Full adapter tests in mock mode — no HTTP."""

    def setup_method(self):
        """Ensure no real env vars pollute tests."""
        for k in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO"):
            os.environ.pop(k, None)

    def _make_adapter(self, **kwargs):
        from stock_rtx4060.broker.kis_adapter import KISAdapter
        return KISAdapter(
            app_key="MOCK_KEY",
            app_secret="MOCK_SECRET",
            account_no="MOCK12345678",
            mock=True,
            **kwargs,
        )

    def test_broker_name_mock(self):
        adapter = self._make_adapter()
        assert adapter.broker_name == "KIS_MOCK"

    def test_broker_name_paper(self):
        from stock_rtx4060.broker.kis_adapter import KISAdapter
        # With mock=False we need credentials; use env vars for this
        with patch.dict(os.environ, {
            "KIS_APP_KEY": "K",
            "KIS_APP_SECRET": "S",
            "KIS_ACCOUNT_NO": "A12345678",
        }):
            # Will try to fetch real token; patch _fetch_token instead
            with patch.object(KISAdapter, "_fetch_token", return_value="FAKE_TOKEN"):
                adapter = KISAdapter(paper=True)
                assert adapter.broker_name == "KIS_PAPER"

    def test_get_account_info_krw(self):
        adapter = self._make_adapter()
        info = adapter.get_account_info()
        assert info.currency == "KRW"
        assert info.cash > 0
        assert info.broker == "KIS_MOCK"

    def test_get_positions_empty(self):
        adapter = self._make_adapter()
        positions = adapter.get_positions()
        assert isinstance(positions, list)
        assert len(positions) == 0

    def test_get_quote_mock(self):
        adapter = self._make_adapter()
        q = adapter.get_quote("005930.KS")
        assert q is not None
        assert q.ticker == "005930.KS"
        assert q.last > 0

    def test_submit_order_buy(self):
        from stock_rtx4060.broker_bridge import OrderRequest, OrderSide, OrderStatus, OrderType

        adapter = self._make_adapter()
        order = OrderRequest(
            ticker="005930.KS",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            limit_price=50000.0,
        )
        result = adapter.submit_order(order)
        assert result.status == OrderStatus.SUBMITTED
        assert result.ticker == "005930.KS"

    def test_submit_order_sell(self):
        from stock_rtx4060.broker_bridge import OrderRequest, OrderSide, OrderStatus, OrderType

        adapter = self._make_adapter()
        order = OrderRequest(
            ticker="005930.KS",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=1,
        )
        result = adapter.submit_order(order)
        assert result.status == OrderStatus.SUBMITTED


class TestKISTokenCache:
    """Test token cache save/load."""

    def test_save_and_load(self, tmp_path):
        from stock_rtx4060.broker.kis_adapter import _TokenCache

        cache_path = tmp_path / "kis_token.json"
        cache = _TokenCache(path=cache_path)

        cache.save("MY_TOKEN", expires_in=3600)
        assert cache_path.exists()

        loaded = cache.load()
        assert loaded is not None
        assert loaded["access_token"] == "MY_TOKEN"

    def test_expired_token_returns_none(self, tmp_path):
        from stock_rtx4060.broker.kis_adapter import _TokenCache

        cache_path = tmp_path / "kis_token.json"
        cache = _TokenCache(path=cache_path)

        # Save with already-expired token
        data = {
            "access_token": "OLD_TOKEN",
            "expires_at": time.time() - 100,  # expired
        }
        cache_path.write_text(json.dumps(data), encoding="utf-8")

        loaded = cache.load()
        assert loaded is None

    def test_missing_token_file_returns_none(self, tmp_path):
        from stock_rtx4060.broker.kis_adapter import _TokenCache

        cache = _TokenCache(path=tmp_path / "nonexistent.json")
        assert cache.load() is None


class TestKISCredentialLoading:
    """Test credential loading priority."""

    def test_raises_without_credentials(self):
        from stock_rtx4060.broker import BrokerNotConfiguredError
        from stock_rtx4060.broker.kis_adapter import KISAdapter

        for k in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO"):
            os.environ.pop(k, None)

        with pytest.raises(BrokerNotConfiguredError):
            KISAdapter()

    def test_env_vars_used(self):
        from stock_rtx4060.broker.kis_adapter import KISAdapter

        with patch.dict(os.environ, {
            "KIS_APP_KEY": "ENVKEY",
            "KIS_APP_SECRET": "ENVSECRET",
            "KIS_ACCOUNT_NO": "ENV12345678",
        }):
            with patch.object(KISAdapter, "_fetch_token", return_value="FAKE_TOKEN"):
                adapter = KISAdapter()
                assert adapter._app_key == "ENVKEY"

    def test_toml_config_loaded(self, tmp_path, monkeypatch):
        import stock_rtx4060.broker.kis_adapter as kis_mod
        from stock_rtx4060.broker.kis_adapter import KISAdapter

        # Create a fake toml config
        config_file = tmp_path / "kis.toml"
        config_file.write_text(
            'app_key = "TOMLKEY"\napp_secret = "TOMLSECRET"\naccount_no = "TOML12345678"\n',
            encoding="utf-8",
        )
        config_file.chmod(0o600)

        for k in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO"):
            os.environ.pop(k, None)

        monkeypatch.setattr(kis_mod, "KIS_CONFIG_PATH", config_file)

        with patch.object(KISAdapter, "_fetch_token", return_value="FAKE_TOKEN"):
            adapter = KISAdapter()
            assert adapter._app_key == "TOMLKEY"
            assert adapter._account_no == "TOML12345678"

    @pytest.mark.skipif(os.name == "nt", reason="Windows chmod does not expose POSIX owner-only mode reliably")
    def test_chmod_600_enforced(self, tmp_path, monkeypatch):
        import stock_rtx4060.broker.kis_adapter as kis_mod
        from stock_rtx4060.broker.kis_adapter import KISAdapter

        config_file = tmp_path / "kis.toml"
        config_file.write_text(
            'app_key = "K"\napp_secret = "S"\naccount_no = "A12345678"\n',
            encoding="utf-8",
        )
        config_file.chmod(0o644)  # Too broad

        for k in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO"):
            os.environ.pop(k, None)

        monkeypatch.setattr(kis_mod, "KIS_CONFIG_PATH", config_file)

        with pytest.raises(PermissionError):
            KISAdapter()


class TestKISMockFetchToken:
    """Test token fetch in mock mode."""

    def test_mock_token(self):
        from stock_rtx4060.broker.kis_adapter import KISAdapter

        adapter = KISAdapter(
            app_key="K",
            app_secret="S",
            account_no="A12345678",
            mock=True,
        )
        # Token should be set to MOCK_TOKEN
        assert adapter._access_token == "MOCK_TOKEN"
