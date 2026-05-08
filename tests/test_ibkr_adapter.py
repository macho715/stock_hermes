"""Tests for IBKRAdapter (Phase 8).

All tests use unittest.mock — no live TWS/Gateway connection.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers — mock ib_insync
# ---------------------------------------------------------------------------

def _make_ib_mocks(connected: bool = True, raise_on_connect: Exception | None = None):
    """Build a fake ib_insync module."""
    mock_ib_instance = MagicMock()
    mock_ib_instance.isConnected.return_value = connected

    if raise_on_connect:
        mock_ib_instance.connect.side_effect = raise_on_connect
    else:
        mock_ib_instance.connect.return_value = None

    mock_ib_class = MagicMock(return_value=mock_ib_instance)

    ib_insync_module = MagicMock()
    ib_insync_module.IB = mock_ib_class
    ib_insync_module.Stock = MagicMock(return_value=MagicMock())
    ib_insync_module.Order = MagicMock(return_value=MagicMock())

    return SimpleNamespace(
        module=ib_insync_module,
        ib_class=mock_ib_class,
        ib_instance=mock_ib_instance,
    )


def _patch_ib(mocks):
    return patch.dict(sys.modules, {"ib_insync": mocks.module})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIBKRAdapterConnectionRefused:
    """Graceful handling when TWS is not running."""

    def test_connection_refused_does_not_raise(self):
        mocks = _make_ib_mocks(raise_on_connect=ConnectionRefusedError("Connection refused"))

        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter

            adapter = IBKRAdapter(host="127.0.0.1", port=7497, client_id=1, timeout=2.0)
            assert not adapter._connected

    def test_os_error_does_not_raise(self):
        mocks = _make_ib_mocks(raise_on_connect=OSError("Network unreachable"))

        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter

            adapter = IBKRAdapter(host="127.0.0.1", port=7497, client_id=1, timeout=2.0)
            assert not adapter._connected


class TestIBKRAdapterRequireConnected:
    """Methods raise BrokerNotConfiguredError when not connected."""

    def test_get_account_requires_connection(self):
        mocks = _make_ib_mocks(raise_on_connect=ConnectionRefusedError())

        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter
            from stock_rtx4060.broker import BrokerNotConfiguredError

            adapter = IBKRAdapter(host="127.0.0.1", port=7497, timeout=1.0)
            with pytest.raises(BrokerNotConfiguredError):
                adapter.get_account_info()

    def test_get_positions_requires_connection(self):
        mocks = _make_ib_mocks(raise_on_connect=ConnectionRefusedError())

        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter
            from stock_rtx4060.broker import BrokerNotConfiguredError

            adapter = IBKRAdapter(host="127.0.0.1", port=7497, timeout=1.0)
            with pytest.raises(BrokerNotConfiguredError):
                adapter.get_positions()

    def test_submit_order_requires_connection(self):
        mocks = _make_ib_mocks(raise_on_connect=ConnectionRefusedError())

        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter
            from stock_rtx4060.broker import BrokerNotConfiguredError
            from stock_rtx4060.broker_bridge import OrderRequest

            adapter = IBKRAdapter(host="127.0.0.1", port=7497, timeout=1.0)
            order = OrderRequest(ticker="AAPL", quantity=1, side="BUY")
            with pytest.raises(BrokerNotConfiguredError):
                adapter.submit_order(order)


class TestIBKRAdapterGetAccountConnected:
    """Test get_account_info with mocked connected IB."""

    def test_get_account_info(self):
        mocks = _make_ib_mocks(connected=True)

        # Mock account summary values
        def make_tag(tag, value):
            v = MagicMock()
            v.tag = tag
            v.value = value
            return v

        mocks.ib_instance.accountSummary.return_value = [
            make_tag("CashBalance", "50000.0"),
            make_tag("BuyingPower", "100000.0"),
            make_tag("NetLiquidation", "150000.0"),
            make_tag("AccountCode", "DU12345"),
            make_tag("Currency", "USD"),
        ]

        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter

            adapter = IBKRAdapter(host="127.0.0.1", port=7497, timeout=1.0)
            adapter._connected = True  # Manually set connected
            info = adapter.get_account_info()

        assert info.cash == 50000.0
        assert info.buying_power == 100000.0
        assert info.portfolio_value == 150000.0
        assert info.account_id == "DU12345"


class TestIBKRAdapterGetPositions:
    """Test get_positions with mocked IB positions."""

    def test_get_positions_empty(self):
        mocks = _make_ib_mocks(connected=True)
        mocks.ib_instance.positions.return_value = []

        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter

            adapter = IBKRAdapter(host="127.0.0.1", port=7497, timeout=1.0)
            adapter._connected = True
            positions = adapter.get_positions()

        assert positions == []

    def test_get_positions_with_data(self):
        mocks = _make_ib_mocks(connected=True)

        fake_contract = MagicMock()
        fake_contract.symbol = "AAPL"

        fake_pos = MagicMock()
        fake_pos.contract = fake_contract
        fake_pos.position = 100.0
        fake_pos.avgCost = 185.0
        mocks.ib_instance.positions.return_value = [fake_pos]

        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter

            adapter = IBKRAdapter(host="127.0.0.1", port=7497, timeout=1.0)
            adapter._connected = True
            positions = adapter.get_positions()

        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == 100
        assert positions[0].avg_cost == 185.0


class TestIBKRAdapterBrokerName:
    """Test broker_name property."""

    def test_paper_port_name(self):
        mocks = _make_ib_mocks(raise_on_connect=ConnectionRefusedError())
        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter

            adapter = IBKRAdapter(port=7497, timeout=1.0)
            assert adapter.broker_name == "IBKR_PAPER"

    def test_live_port_name(self):
        mocks = _make_ib_mocks(raise_on_connect=ConnectionRefusedError())
        with _patch_ib(mocks):
            from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter

            adapter = IBKRAdapter(port=7496, timeout=1.0)
            assert adapter.broker_name == "IBKR_LIVE"


class TestIBKRAdapterEnumMapping:
    """Test enum mappings."""

    def test_side_map(self):
        from stock_rtx4060.broker.ibkr_adapter import _SIDE_MAP
        from stock_rtx4060.broker_bridge import OrderSide

        assert _SIDE_MAP[OrderSide.BUY] == "BUY"
        assert _SIDE_MAP[OrderSide.SELL] == "SELL"

    def test_order_type_map(self):
        from stock_rtx4060.broker.ibkr_adapter import _ORDER_TYPE_MAP
        from stock_rtx4060.broker_bridge import OrderType

        assert _ORDER_TYPE_MAP[OrderType.MARKET] == "MKT"
        assert _ORDER_TYPE_MAP[OrderType.LIMIT] == "LMT"
        assert _ORDER_TYPE_MAP[OrderType.STOP] == "STP"
        assert _ORDER_TYPE_MAP[OrderType.STOP_LIMIT] == "STP LMT"


class TestIBKRImportError:
    """Test graceful handling when ib_insync is not installed."""

    def test_import_error_when_no_ib_insync(self, monkeypatch):
        # Remove ib_insync from sys.modules so the import raises
        with patch.dict(sys.modules, {"ib_insync": None}):
            with pytest.raises((ImportError, AttributeError)):
                from stock_rtx4060.broker.ibkr_adapter import IBKRAdapter  # noqa: F401
                IBKRAdapter()
