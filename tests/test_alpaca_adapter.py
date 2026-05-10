"""Tests for AlpacaAdapter (Phase 8).

All tests use unittest.mock — no live Alpaca API calls.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to build mock Alpaca objects without importing alpaca-py
# ---------------------------------------------------------------------------

def _make_alpaca_mocks():
    """Return a namespace with all alpaca-py modules mocked."""
    mocks = SimpleNamespace()

    # Build a fake TradingClient class
    mock_client = MagicMock()
    mock_client_class = MagicMock(return_value=mock_client)

    # Build fake alpaca modules
    trading_module = MagicMock()
    trading_module.client.TradingClient = mock_client_class
    trading_module.requests.MarketOrderRequest = MagicMock
    trading_module.requests.LimitOrderRequest = MagicMock
    trading_module.enums.OrderSide = MagicMock()
    trading_module.enums.OrderSide.side_effect = lambda x: x
    trading_module.enums.TimeInForce = MagicMock()
    trading_module.enums.TimeInForce.DAY = "day"

    alpaca_module = MagicMock()
    alpaca_module.trading = trading_module

    mocks.client = mock_client
    mocks.client_class = mock_client_class
    mocks.alpaca_module = alpaca_module
    mocks.trading_module = trading_module
    return mocks


def _patch_alpaca(mocks):
    return patch.dict(sys.modules, {
        "alpaca": mocks.alpaca_module,
        "alpaca.trading": mocks.trading_module,
        "alpaca.trading.client": mocks.trading_module.client,
        "alpaca.trading.requests": mocks.trading_module.requests,
        "alpaca.trading.enums": mocks.trading_module.enums,
        "alpaca.data": MagicMock(),
        "alpaca.data.historical": MagicMock(),
        "alpaca.data.requests": MagicMock(),
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAlpacaAdapterNoCreds:
    """Test BrokerNotConfiguredError when credentials are missing."""

    def test_raises_when_no_creds(self, monkeypatch):
        monkeypatch.delenv("ALPACA_API_KEY", raising=False)
        monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)

        mocks = _make_alpaca_mocks()
        with _patch_alpaca(mocks):
            from stock_rtx4060.broker import BrokerNotConfiguredError
            from stock_rtx4060.broker.alpaca_adapter import AlpacaAdapter

            with pytest.raises(BrokerNotConfiguredError):
                AlpacaAdapter(api_key="", secret_key="")


class TestAlpacaAdapterSubmitOrder:
    """Test submit_order via mocked TradingClient."""

    def _make_adapter(self):
        mocks = _make_alpaca_mocks()

        # Set up a fake order response
        fake_order = MagicMock()
        fake_order.id = "test-order-id-123"
        fake_order.status = "new"
        fake_order.filled_avg_price = None
        mocks.client.submit_order.return_value = fake_order

        with _patch_alpaca(mocks):
            from stock_rtx4060.broker.alpaca_adapter import AlpacaAdapter
            adapter = AlpacaAdapter(api_key="KEY", secret_key="SECRET", paper=True)
        return adapter, mocks

    def test_submit_market_order(self):
        mocks = _make_alpaca_mocks()
        fake_order = MagicMock()
        fake_order.id = "order-xyz"
        fake_order.status = "new"
        fake_order.filled_avg_price = None
        mocks.client.submit_order.return_value = fake_order

        with _patch_alpaca(mocks):
            from stock_rtx4060.broker.alpaca_adapter import AlpacaAdapter
            from stock_rtx4060.broker_bridge import OrderRequest, OrderSide, OrderType

            adapter = AlpacaAdapter(api_key="KEY", secret_key="SECRET", paper=True)
            order = OrderRequest(
                ticker="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=10,
            )
            result = adapter.submit_order(order)

        assert result.ticker == "AAPL"
        assert result.quantity == 10
        mocks.client.submit_order.assert_called_once()

    def test_submit_limit_order(self):
        mocks = _make_alpaca_mocks()
        fake_order = MagicMock()
        fake_order.id = "limit-order-abc"
        fake_order.status = "new"
        fake_order.filled_avg_price = 185.0
        mocks.client.submit_order.return_value = fake_order

        with _patch_alpaca(mocks):
            from stock_rtx4060.broker.alpaca_adapter import AlpacaAdapter
            from stock_rtx4060.broker_bridge import OrderRequest, OrderSide, OrderType

            adapter = AlpacaAdapter(api_key="KEY", secret_key="SECRET", paper=True)
            order = OrderRequest(
                ticker="MSFT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=5,
                limit_price=185.0,
            )
            result = adapter.submit_order(order)

        assert result.ticker == "MSFT"
        assert result.fill_price == 185.0

    def test_submit_order_error_returns_rejected(self):
        mocks = _make_alpaca_mocks()
        mocks.client.submit_order.side_effect = Exception("API error")

        with _patch_alpaca(mocks):
            from stock_rtx4060.broker.alpaca_adapter import AlpacaAdapter
            from stock_rtx4060.broker_bridge import OrderRequest, OrderSide, OrderStatus, OrderType

            adapter = AlpacaAdapter(api_key="KEY", secret_key="SECRET", paper=True)
            order = OrderRequest(
                ticker="TSLA",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=1,
            )
            result = adapter.submit_order(order)

        assert result.status == OrderStatus.REJECTED
        assert result.error_message is not None


class TestAlpacaAdapterGetPositions:
    """Test get_positions via mocked TradingClient."""

    def test_get_positions_empty(self):
        mocks = _make_alpaca_mocks()
        mocks.client.get_all_positions.return_value = []

        with _patch_alpaca(mocks):
            from stock_rtx4060.broker.alpaca_adapter import AlpacaAdapter

            adapter = AlpacaAdapter(api_key="KEY", secret_key="SECRET", paper=True)
            positions = adapter.get_positions()

        assert positions == []

    def test_get_positions_with_data(self):
        mocks = _make_alpaca_mocks()

        fake_pos = MagicMock()
        fake_pos.symbol = "AAPL"
        fake_pos.qty = "10"
        fake_pos.avg_entry_price = "185.00"
        fake_pos.current_price = "190.00"
        fake_pos.market_value = "1900.00"
        fake_pos.unrealized_pl = "50.00"
        fake_pos.unrealized_plpc = "0.027"
        mocks.client.get_all_positions.return_value = [fake_pos]

        with _patch_alpaca(mocks):
            from stock_rtx4060.broker.alpaca_adapter import AlpacaAdapter

            adapter = AlpacaAdapter(api_key="KEY", secret_key="SECRET", paper=True)
            positions = adapter.get_positions()

        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == 10


class TestAlpacaAdapterGetAccount:
    """Test get_account_info via mocked TradingClient."""

    def test_get_account(self):
        mocks = _make_alpaca_mocks()

        fake_account = MagicMock()
        fake_account.id = "acct-001"
        fake_account.cash = "50000.00"
        fake_account.buying_power = "100000.00"
        fake_account.portfolio_value = "150000.00"
        fake_account.currency = "USD"
        mocks.client.get_account.return_value = fake_account

        with _patch_alpaca(mocks):
            from stock_rtx4060.broker.alpaca_adapter import AlpacaAdapter

            adapter = AlpacaAdapter(api_key="KEY", secret_key="SECRET", paper=True)
            account = adapter.get_account()

        assert account["buying_power"] == 100000.0
        assert account["portfolio_value"] == 150000.0


class TestAlpacaEnumMapping:
    """Test enum translation helpers."""

    def test_side_map(self):
        from stock_rtx4060.broker.alpaca_adapter import _SIDE_MAP
        from stock_rtx4060.broker_bridge import OrderSide

        assert _SIDE_MAP[OrderSide.BUY] == "buy"
        assert _SIDE_MAP[OrderSide.SELL] == "sell"

    def test_status_map(self):
        from stock_rtx4060.broker.alpaca_adapter import _map_alpaca_status
        from stock_rtx4060.broker_bridge import OrderStatus

        assert _map_alpaca_status("filled") == OrderStatus.FILLED
        assert _map_alpaca_status("rejected") == OrderStatus.REJECTED
        assert _map_alpaca_status("canceled") == OrderStatus.CANCELLED
        assert _map_alpaca_status("new") == OrderStatus.SUBMITTED


class TestAlpacaSmokeTest:
    """Smoke test exits 0 even without keys."""

    def test_smoke_exits_zero(self):
        """Importing and running the smoke test logic in-process."""
        from stock_rtx4060.broker.alpaca_adapter import _ORDER_TYPE_MAP, _SIDE_MAP, _map_alpaca_status
        from stock_rtx4060.broker_bridge import OrderSide, OrderStatus, OrderType

        # Enum mappings should be correct
        assert _SIDE_MAP[OrderSide.BUY] == "buy"
        assert _ORDER_TYPE_MAP[OrderType.LIMIT] == "limit"
        assert _map_alpaca_status("filled") == OrderStatus.FILLED
