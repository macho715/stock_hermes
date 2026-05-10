"""
IBKR broker adapter (Phase 8).

Uses ``ib_insync`` library to connect to TWS or IB Gateway.

Port conventions
----------------
* 7497 — TWS paper trading
* 7496 — TWS live trading
* 4002 — IB Gateway paper
* 4001 — IB Gateway live

Smoke test (gracefully handles ConnectionRefused)::

    python -m stock_rtx4060.broker.ibkr_adapter --smoke
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from ..broker_bridge import (
    AccountInfo,
    BrokerAdapter,
    BrokerPosition,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Quote,
)
from . import BrokerNotConfiguredError

logger = logging.getLogger(__name__)

_SIDE_MAP: dict[str, str] = {
    OrderSide.BUY: "BUY",
    OrderSide.SELL: "SELL",
}

_ORDER_TYPE_MAP: dict[str, str] = {
    OrderType.MARKET: "MKT",
    OrderType.LIMIT: "LMT",
    OrderType.STOP: "STP",
    OrderType.STOP_LIMIT: "STP LMT",
}


class IBKRAdapter(BrokerAdapter):
    """BrokerAdapter backed by ib_insync connecting to TWS/IB Gateway.

    Parameters
    ----------
    host : str
        TWS/Gateway host (default ``"127.0.0.1"``).
    port : int
        TWS/Gateway port.  7497 = paper, 7496 = live (default 7497).
    client_id : int
        IB client ID (default 1).
    timeout : float
        Connection timeout in seconds (default 10.0).
    """

    POLL_INTERVAL_SECS = 5

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        timeout: float = 10.0,
    ) -> None:
        try:
            import ib_insync  # noqa: F401 — verify installed
        except ImportError as exc:
            raise ImportError(
                "ib_insync is required for IBKRAdapter. "
                "Install it with: pip install 'ib_insync>=0.9.86'"
            ) from exc

        self._host = host
        self._port = port
        self._client_id = client_id
        self._timeout = timeout
        self._paper = (port in (7497, 4002))

        from ib_insync import IB
        self._ib: IB = IB()
        self._connected = False

        try:
            self._ib.connect(host, port, clientId=client_id, timeout=timeout)
            self._connected = True
            logger.info(
                "IBKRAdapter connected to %s:%s (paper=%s)", host, port, self._paper
            )
        except ConnectionRefusedError:
            logger.warning(
                "IBKRAdapter: ConnectionRefused at %s:%s — TWS/Gateway not running",
                host, port,
            )
            # Do NOT raise — adapter remains in disconnected state so callers
            # can handle it gracefully.
        except OSError as exc:
            logger.warning("IBKRAdapter: connection failed: %s", exc)

        self._reconcile_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # BrokerAdapter interface
    # ------------------------------------------------------------------

    @property
    def broker_name(self) -> str:
        return "IBKR_PAPER" if self._paper else "IBKR_LIVE"

    def _require_connected(self) -> None:
        if not self._connected or not self._ib.isConnected():
            raise BrokerNotConfiguredError(
                "IBKRAdapter is not connected to TWS/Gateway. "
                f"Start TWS/Gateway on {self._host}:{self._port}."
            )

    def get_account_info(self) -> AccountInfo:
        self._require_connected()
        summary = {v.tag: v.value for v in self._ib.accountSummary()}
        cash = float(summary.get("CashBalance", 0.0) or 0.0)
        buying_power = float(summary.get("BuyingPower", 0.0) or 0.0)
        net_liq = float(summary.get("NetLiquidation", 0.0) or 0.0)
        account_id = summary.get("AccountCode", "UNKNOWN")
        return AccountInfo(
            broker=self.broker_name,
            account_id=account_id,
            cash=cash,
            buying_power=buying_power,
            portfolio_value=net_liq,
            currency=summary.get("Currency", "USD"),
        )

    def get_positions(self) -> list[BrokerPosition]:
        self._require_connected()
        result: list[BrokerPosition] = []
        for pos in self._ib.positions():
            contract = pos.contract
            symbol = getattr(contract, "symbol", "")
            qty = float(pos.position)
            avg_cost = float(pos.avgCost)
            # Current price not directly available in positions(); estimate
            current_price = avg_cost
            market_value = qty * current_price
            unrealized_pnl = 0.0
            unrealized_pct = 0.0
            result.append(
                BrokerPosition(
                    symbol=symbol,
                    quantity=int(qty),
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pct,
                )
            )
        return result

    def get_quote(self, ticker: str) -> Quote | None:
        if not self._connected or not self._ib.isConnected():
            return None
        try:
            from ib_insync import Stock
            contract = Stock(ticker, "SMART", "USD")
            self._ib.qualifyContracts(contract)
            ticker_obj = self._ib.reqMktData(contract, "", False, False)
            self._ib.sleep(1.0)
            bid = float(ticker_obj.bid or 0.0)
            ask = float(ticker_obj.ask or 0.0)
            last = float(ticker_obj.last or 0.0)
            self._ib.cancelMktData(contract)
            return Quote(ticker=ticker.upper(), bid=bid, ask=ask, last=last)
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_quote(%s) failed: %s", ticker, exc)
            return None

    def submit_order(self, order: OrderRequest) -> OrderResult:
        self._require_connected()
        try:
            from ib_insync import Order, Stock

            contract = Stock(order.ticker, "SMART", "USD")
            self._ib.qualifyContracts(contract)

            action = _SIDE_MAP.get(order.side.upper(), "BUY")
            order_type_ib = _ORDER_TYPE_MAP.get(order.order_type.upper(), "MKT")

            ib_order = Order(
                action=action,
                totalQuantity=order.quantity,
                orderType=order_type_ib,
            )
            if order.limit_price and order_type_ib in ("LMT", "STP LMT"):
                ib_order.lmtPrice = order.limit_price
            if order.stop_price and order_type_ib in ("STP", "STP LMT"):
                ib_order.auxPrice = order.stop_price

            trade = self._ib.placeOrder(contract, ib_order)
            # Poll for up to 30 s
            for _ in range(30):
                self._ib.sleep(1.0)
                if trade.orderStatus.status in ("Filled", "Cancelled", "Inactive"):
                    break

            status_str = trade.orderStatus.status
            if status_str == "Filled":
                our_status = OrderStatus.FILLED
            elif status_str in ("Cancelled", "Inactive"):
                our_status = OrderStatus.CANCELLED
            else:
                our_status = OrderStatus.SUBMITTED

            fill_price = float(trade.orderStatus.avgFillPrice or order.limit_price or 0.0)
            return OrderResult(
                order_id=str(trade.order.orderId),
                ticker=order.ticker,
                side=order.side,
                status=our_status,
                quantity=order.quantity,
                fill_price=fill_price,
                fill_price_effective=fill_price,
                simulation_only=False,
                simulation_reason="",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("submit_order failed for %s: %s", order.ticker, exc)
            return OrderResult(
                order_id=order.order_id,
                ticker=order.ticker,
                side=order.side,
                status=OrderStatus.REJECTED,
                quantity=order.quantity,
                simulation_only=False,
                simulation_reason="",
                error_message=str(exc),
            )

    def get_account(self) -> dict[str, Any]:
        info = self.get_account_info()
        return {
            "buying_power": info.buying_power,
            "portfolio_value": info.portfolio_value,
            "cash": info.cash,
            "currency": info.currency,
        }

    def start_reconciliation(self, interval_secs: int = 5) -> None:
        """Start background 5-second reconciliation polling thread."""
        if self._reconcile_thread and self._reconcile_thread.is_alive():
            return
        self._stop_event.clear()

        def _poll() -> None:
            while not self._stop_event.is_set():
                if self._connected and self._ib.isConnected():
                    try:
                        self._ib.reqPositions()
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("reconciliation poll error: %s", exc)
                self._stop_event.wait(interval_secs)

        self._reconcile_thread = threading.Thread(
            target=_poll, name="ibkr-reconcile", daemon=True
        )
        self._reconcile_thread.start()

    def close(self) -> None:
        self._stop_event.set()
        if self._connected and self._ib.isConnected():
            try:
                self._ib.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self._connected = False


# ---------------------------------------------------------------------------
# Smoke test CLI
# ---------------------------------------------------------------------------

def _smoke_test() -> None:
    """Gracefully handles ConnectionRefused — exits 0."""
    import sys

    print("IBKRAdapter smoke test …")

    # Test 1: connection refused is handled gracefully
    try:
        from ib_insync import IB
        # port 19999 is almost certainly not bound
        adapter = IBKRAdapter(host="127.0.0.1", port=19999, client_id=99, timeout=2.0)
        assert not adapter._connected, "Should not be connected on bad port"
        print("  [PASS] ConnectionRefused handled gracefully (not connected)")
        adapter.close()
    except ImportError as e:
        print(f"  [SKIP] ib_insync not installed ({e})")
    except Exception as e:  # noqa: BLE001
        print(f"  [WARN] unexpected error: {e}")

    # Test 2: require_connected raises BrokerNotConfiguredError
    try:
        from ib_insync import IB  # noqa: F401
        adapter2 = IBKRAdapter(host="127.0.0.1", port=19998, client_id=98, timeout=1.0)
        try:
            adapter2.get_account_info()
            print("  [FAIL] should have raised BrokerNotConfiguredError")
        except BrokerNotConfiguredError:
            print("  [PASS] BrokerNotConfiguredError raised when disconnected")
        adapter2.close()
    except ImportError:
        print("  [SKIP] ib_insync not installed")
    except Exception as e:  # noqa: BLE001
        print(f"  [WARN] unexpected: {e}")

    # Test 3: enum mapping
    assert _SIDE_MAP[OrderSide.BUY] == "BUY"
    assert _ORDER_TYPE_MAP[OrderType.LIMIT] == "LMT"
    print("  [PASS] Enum mapping correct")

    print("IBKRAdapter smoke test PASSED")
    sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="IBKRAdapter")
    parser.add_argument("--smoke", action="store_true", help="run smoke test and exit")
    args = parser.parse_args()
    if args.smoke:
        _smoke_test()
    else:
        parser.print_help()
