"""Tests for OrderRouter, TWAPExecutor, VWAPExecutor (Phase 8).

Uses unittest.mock — no live broker connections.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_adapter(broker_name: str = "MOCK"):
    adapter = MagicMock()
    adapter.broker_name = broker_name
    from stock_rtx4060.broker_bridge import OrderResult, OrderStatus
    result = OrderResult(
        ticker="AAPL",
        side="BUY",
        status=OrderStatus.SUBMITTED,
        quantity=10,
        simulation_only=False,
        simulation_reason="",
    )
    adapter.submit_order.return_value = result
    return adapter


# ---------------------------------------------------------------------------
# OrderRouter routing tests
# ---------------------------------------------------------------------------

class TestOrderRouterRouting:
    """Test that tickers route to the correct adapter."""

    def _make_router_with_mocks(self):
        from stock_rtx4060.broker.order_router import OrderRouter

        router = OrderRouter(paper_fallback=True)
        # Inject mock adapters
        router._alpaca = _make_mock_adapter("ALPACA_PAPER")
        router._ibkr = _make_mock_adapter("IBKR_PAPER")
        router._kis = _make_mock_adapter("KIS_MOCK")
        return router

    def test_krx_ks_routes_to_kis(self):
        router = self._make_router_with_mocks()
        assert router._route("005930.KS") is router._kis

    def test_krx_kq_routes_to_kis(self):
        router = self._make_router_with_mocks()
        assert router._route("086520.KQ") is router._kis

    def test_us_ticker_routes_to_alpaca(self):
        router = self._make_router_with_mocks()
        assert router._route("AAPL") is router._alpaca

    def test_us_ticker_falls_back_to_ibkr_if_alpaca_none(self):
        router = self._make_router_with_mocks()
        router._alpaca = None  # Simulate alpaca not configured

        # _get_alpaca should raise, then _get_ibkr should be used
        from stock_rtx4060.broker import BrokerNotConfiguredError
        router._alpaca_kwargs = {}  # empty kwargs → will try to construct AlpacaAdapter

        # Override _get_alpaca to raise
        def _raise():
            raise BrokerNotConfiguredError("no alpaca")
        router._get_alpaca = _raise

        adapter = router._route("TSLA")
        assert adapter is router._ibkr


class TestOrderRouterSubmitOrder:
    """Test submit_order method."""

    def test_submit_us_order(self):
        from stock_rtx4060.broker.order_router import OrderRouter
        from stock_rtx4060.broker_bridge import OrderStatus

        router = OrderRouter(paper_fallback=True)
        router._alpaca = _make_mock_adapter("ALPACA_PAPER")

        result = router.submit_order("AAPL", 10, "BUY", order_type="MARKET")
        assert result.status == OrderStatus.SUBMITTED
        router._alpaca.submit_order.assert_called_once()

    def test_submit_krx_order(self):
        from stock_rtx4060.broker.order_router import OrderRouter
        from stock_rtx4060.broker_bridge import OrderResult, OrderStatus

        router = OrderRouter(paper_fallback=True)
        mock_kis = _make_mock_adapter("KIS_MOCK")
        kis_result = OrderResult(
            ticker="005930.KS",
            side="BUY",
            status=OrderStatus.SUBMITTED,
            quantity=5,
            simulation_only=False,
            simulation_reason="",
        )
        mock_kis.submit_order.return_value = kis_result
        router._kis = mock_kis

        result = router.submit_order("005930.KS", 5, "BUY", order_type="LIMIT", limit_price=50000.0)
        assert result.status == OrderStatus.SUBMITTED
        mock_kis.submit_order.assert_called_once()


# ---------------------------------------------------------------------------
# Kill switch tests
# ---------------------------------------------------------------------------

class TestKillSwitch:
    """Test kill switch functionality."""

    def setup_method(self):
        """Remove KILLED file before each test."""
        from stock_rtx4060.broker.order_router import KILLED_FILE
        KILLED_FILE.unlink(missing_ok=True)

    def teardown_method(self):
        """Clean up KILLED file after each test."""
        from stock_rtx4060.broker.order_router import KILLED_FILE
        KILLED_FILE.unlink(missing_ok=True)

    def test_kill_switch_blocks_orders(self):
        from stock_rtx4060.broker.order_router import KillSwitchError, OrderRouter

        router = OrderRouter(paper_fallback=True)
        router._alpaca = _make_mock_adapter("ALPACA_PAPER")

        router.kill_switch()

        with pytest.raises(KillSwitchError):
            router.submit_order("AAPL", 10, "BUY")

    def test_kill_switch_writes_file(self):
        from stock_rtx4060.broker.order_router import KILLED_FILE, OrderRouter

        router = OrderRouter(paper_fallback=True)
        router.kill_switch()

        assert KILLED_FILE.exists()
        content = KILLED_FILE.read_text(encoding="utf-8")
        assert "KILLED" in content.upper()

    def test_killed_file_blocks_orders(self, tmp_path):
        from stock_rtx4060.broker.order_router import KILLED_FILE, KillSwitchError, OrderRouter

        # Write KILLED file manually
        KILLED_FILE.parent.mkdir(parents=True, exist_ok=True)
        KILLED_FILE.write_text("KILLED at 2026-01-01T00:00:00Z\n", encoding="utf-8")

        router = OrderRouter(paper_fallback=True)
        router._alpaca = _make_mock_adapter()

        with pytest.raises(KillSwitchError):
            router.submit_order("AAPL", 10, "BUY")

    def test_check_kill_switch_no_file_no_flag(self):
        from stock_rtx4060.broker.order_router import OrderRouter

        router = OrderRouter(paper_fallback=True)
        # Should not raise
        router._check_kill_switch()

    def test_reset_kill_switch(self):
        from stock_rtx4060.broker.order_router import KILLED_FILE, KillSwitchError, OrderRouter

        router = OrderRouter(paper_fallback=True)
        router._alpaca = _make_mock_adapter("ALPACA_PAPER")
        router.kill_switch()

        # Confirm blocked
        with pytest.raises(KillSwitchError):
            router.submit_order("AAPL", 1, "BUY")

        router.reset_kill_switch()

        # Should not raise anymore
        router._check_kill_switch()
        assert not KILLED_FILE.exists()


# ---------------------------------------------------------------------------
# TWAP executor tests
# ---------------------------------------------------------------------------

class TestTWAPExecutor:
    """Test TWAPExecutor order slicing."""

    def setup_method(self):
        from stock_rtx4060.broker.order_router import KILLED_FILE
        KILLED_FILE.unlink(missing_ok=True)

    def teardown_method(self):
        from stock_rtx4060.broker.order_router import KILLED_FILE
        KILLED_FILE.unlink(missing_ok=True)

    def _make_router(self):
        from stock_rtx4060.broker.order_router import OrderRouter

        router = OrderRouter(paper_fallback=True)
        router._alpaca = _make_mock_adapter("ALPACA_PAPER")
        return router

    def test_twap_splits_correctly(self):
        from stock_rtx4060.broker.order_router import TWAPExecutor

        router = self._make_router()
        executor = TWAPExecutor(router)

        results = executor.execute(
            ticker="AAPL",
            total_qty=10,
            side="BUY",
            slices=5,
            interval_secs=0,  # no sleep in tests
        )

        # 5 slices submitted — each slice calls submit_order once
        assert len(results) == 5
        # Each slice should have been submitted with the correct portion
        # (router._alpaca.submit_order is a mock, qty in result is from mock)
        assert router._alpaca.submit_order.call_count == 5

    def test_twap_remainder_distributed(self):
        from stock_rtx4060.broker.order_router import TWAPExecutor

        router = self._make_router()
        executor = TWAPExecutor(router)

        # 11 shares in 3 slices
        results = executor.execute(
            ticker="AAPL",
            total_qty=11,
            side="BUY",
            slices=3,
            interval_secs=0,
        )

        assert len(results) == 3
        # Verify the actual qtys passed to submit_order sum to 11
        submitted_qtys = [
            call.args[0].quantity
            for call in router._alpaca.submit_order.call_args_list
        ]
        assert sum(submitted_qtys) == 11

    def test_twap_kill_switch_propagates(self):
        from stock_rtx4060.broker.order_router import KillSwitchError, TWAPExecutor

        router = self._make_router()
        router.kill_switch()
        executor = TWAPExecutor(router)

        with pytest.raises(KillSwitchError):
            executor.execute("AAPL", 10, "BUY", slices=2, interval_secs=0)

    def test_twap_invalid_slices(self):
        from stock_rtx4060.broker.order_router import TWAPExecutor

        router = self._make_router()
        executor = TWAPExecutor(router)

        with pytest.raises(ValueError, match="slices"):
            executor.execute("AAPL", 10, "BUY", slices=0, interval_secs=0)


# ---------------------------------------------------------------------------
# VWAP executor tests
# ---------------------------------------------------------------------------

class TestVWAPExecutor:
    """Test VWAPExecutor weighted slicing."""

    def setup_method(self):
        from stock_rtx4060.broker.order_router import KILLED_FILE
        KILLED_FILE.unlink(missing_ok=True)

    def teardown_method(self):
        from stock_rtx4060.broker.order_router import KILLED_FILE
        KILLED_FILE.unlink(missing_ok=True)

    def _make_router(self):
        from stock_rtx4060.broker.order_router import OrderRouter

        router = OrderRouter(paper_fallback=True)
        router._alpaca = _make_mock_adapter("ALPACA_PAPER")
        return router

    def test_vwap_distributes_by_curve(self):
        from stock_rtx4060.broker.order_router import VWAPExecutor

        router = self._make_router()
        executor = VWAPExecutor(router)

        curve = [0.2, 0.3, 0.3, 0.2]
        results = executor.execute(
            ticker="AAPL",
            total_qty=100,
            side="BUY",
            volume_curve=curve,
        )

        assert len(results) == 4
        # Verify the actual qtys passed to submit_order sum to 100
        submitted_qtys = [
            call.args[0].quantity
            for call in router._alpaca.submit_order.call_args_list
        ]
        assert sum(submitted_qtys) == 100

    def test_vwap_kill_switch_propagates(self):
        from stock_rtx4060.broker.order_router import KillSwitchError, VWAPExecutor

        router = self._make_router()
        router.kill_switch()
        executor = VWAPExecutor(router)

        with pytest.raises(KillSwitchError):
            executor.execute("AAPL", 100, "BUY", volume_curve=[1.0])

    def test_vwap_empty_curve_raises(self):
        from stock_rtx4060.broker.order_router import VWAPExecutor

        router = self._make_router()
        executor = VWAPExecutor(router)

        with pytest.raises(ValueError, match="volume_curve"):
            executor.execute("AAPL", 10, "BUY", volume_curve=[])

    def test_vwap_zero_curve_raises(self):
        from stock_rtx4060.broker.order_router import VWAPExecutor

        router = self._make_router()
        executor = VWAPExecutor(router)

        with pytest.raises(ValueError, match="positive"):
            executor.execute("AAPL", 10, "BUY", volume_curve=[0.0, 0.0])
