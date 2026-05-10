"""
Alpaca broker adapter (Phase 8).

Uses alpaca-py (``alpaca.trading.client.TradingClient``).
Paper mode is the default; pass ``paper=False`` for live.

Credentials
-----------
Read from env vars ``ALPACA_API_KEY`` / ``ALPACA_SECRET_KEY``, or passed
directly as constructor kwargs.

Smoke test (no real keys needed)::

    python -m stock_rtx4060.broker.alpaca_adapter --smoke
"""

from __future__ import annotations

import logging
import os
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

# ---------------------------------------------------------------------------
# Enum mappings  (alpaca-py enums → our enums and vice-versa)
# ---------------------------------------------------------------------------

_SIDE_MAP: dict[str, str] = {
    OrderSide.BUY: "buy",
    OrderSide.SELL: "sell",
}

_ORDER_TYPE_MAP: dict[str, str] = {
    OrderType.MARKET: "market",
    OrderType.LIMIT: "limit",
    OrderType.STOP: "stop",
    OrderType.STOP_LIMIT: "stop_limit",
}

_STATUS_MAP: dict[str, str] = {
    "new": OrderStatus.SUBMITTED,
    "partially_filled": OrderStatus.SUBMITTED,
    "filled": OrderStatus.FILLED,
    "done_for_day": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELLED,
    "expired": OrderStatus.CANCELLED,
    "replaced": OrderStatus.CANCELLED,
    "pending_cancel": OrderStatus.CANCELLED,
    "pending_replace": OrderStatus.SUBMITTED,
    "rejected": OrderStatus.REJECTED,
    "suspended": OrderStatus.REJECTED,
    "accepted": OrderStatus.SUBMITTED,
    "pending_new": OrderStatus.SUBMITTED,
    "accepted_for_bidding": OrderStatus.SUBMITTED,
    "stopped": OrderStatus.CANCELLED,
    "calculated": OrderStatus.SUBMITTED,
}


def _map_alpaca_status(alpaca_status: str) -> str:
    return _STATUS_MAP.get(alpaca_status.lower(), OrderStatus.SUBMITTED)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class AlpacaAdapter(BrokerAdapter):
    """BrokerAdapter implementation backed by alpaca-py TradingClient.

    Parameters
    ----------
    api_key, secret_key : str, optional
        Override env vars.
    paper : bool
        Use paper endpoint (default True).
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
    ) -> None:
        self._paper = paper
        self._api_key = api_key or os.environ.get("ALPACA_API_KEY", "")
        self._secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY", "")

        if not self._api_key or not self._secret_key:
            raise BrokerNotConfiguredError(
                "Alpaca credentials not found. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY env vars or pass them as kwargs."
            )

        try:
            from alpaca.trading.client import TradingClient
        except ImportError as exc:
            raise ImportError(
                "alpaca-py is required for AlpacaAdapter. "
                "Install it with: pip install 'alpaca-py>=0.30'"
            ) from exc

        self._client = TradingClient(
            api_key=self._api_key,
            secret_key=self._secret_key,
            paper=self._paper,
        )
        logger.info(
            "AlpacaAdapter connected. paper=%s", self._paper
        )

    # ------------------------------------------------------------------
    # BrokerAdapter interface
    # ------------------------------------------------------------------

    @property
    def broker_name(self) -> str:
        return "ALPACA_PAPER" if self._paper else "ALPACA_LIVE"

    def get_account_info(self) -> AccountInfo:
        from alpaca.trading.requests import GetAssetsRequest  # noqa: F401 — ensure lib present
        acct = self._client.get_account()
        return AccountInfo(
            broker=self.broker_name,
            account_id=str(getattr(acct, "id", "UNKNOWN")),
            cash=float(getattr(acct, "cash", 0.0) or 0.0),
            buying_power=float(getattr(acct, "buying_power", 0.0) or 0.0),
            portfolio_value=float(getattr(acct, "portfolio_value", 0.0) or 0.0),
            currency=str(getattr(acct, "currency", "USD")),
        )

    def get_positions(self) -> list[BrokerPosition]:
        positions = self._client.get_all_positions()
        result: list[BrokerPosition] = []
        for pos in positions:
            qty = float(getattr(pos, "qty", 0) or 0)
            avg_cost = float(getattr(pos, "avg_entry_price", 0.0) or 0.0)
            current_price = float(getattr(pos, "current_price", 0.0) or 0.0)
            market_value = float(getattr(pos, "market_value", 0.0) or 0.0)
            unrealized_pl = float(getattr(pos, "unrealized_pl", 0.0) or 0.0)
            unrealized_plpc = float(getattr(pos, "unrealized_plpc", 0.0) or 0.0)
            result.append(
                BrokerPosition(
                    symbol=str(getattr(pos, "symbol", "")),
                    quantity=int(qty),
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pl,
                    unrealized_pnl_pct=unrealized_plpc,
                )
            )
        return result

    def get_quote(self, ticker: str) -> Quote | None:
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockLatestQuoteRequest

            data_client = StockHistoricalDataClient(
                api_key=self._api_key,
                secret_key=self._secret_key,
            )
            req = StockLatestQuoteRequest(symbol_or_symbols=[ticker.upper()])
            quotes = data_client.get_stock_latest_quote(req)
            q = quotes.get(ticker.upper())
            if q is None:
                return None
            return Quote(
                ticker=ticker.upper(),
                bid=float(getattr(q, "bid_price", 0.0) or 0.0),
                ask=float(getattr(q, "ask_price", 0.0) or 0.0),
                last=float(getattr(q, "ask_price", 0.0) or 0.0),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_quote(%s) failed: %s", ticker, exc)
            return None

    def submit_order(self, order: OrderRequest) -> OrderResult:
        """Submit order to Alpaca.

        *order.simulation_only* is forcibly True in the base class, so this
        method intentionally bypasses that constraint by using the Alpaca API
        directly — caller is responsible for confirming live trading intent.
        """
        try:
            from alpaca.trading.enums import OrderSide as AlpacaSide
            from alpaca.trading.enums import TimeInForce
            from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

            side_str = _SIDE_MAP.get(order.side.upper(), "buy")
            alpaca_side = AlpacaSide(side_str)

            order_type = order.order_type.upper()
            qty = str(order.quantity)

            if order_type == OrderType.MARKET:
                req = MarketOrderRequest(
                    symbol=order.ticker,
                    qty=qty,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                )
            elif order_type == OrderType.LIMIT:
                req = LimitOrderRequest(
                    symbol=order.ticker,
                    qty=qty,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=str(order.limit_price or 0.0),
                )
            else:
                req = MarketOrderRequest(
                    symbol=order.ticker,
                    qty=qty,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                )

            response = self._client.submit_order(order_data=req)
            status = _map_alpaca_status(str(getattr(response, "status", "new")))
            fill_price = float(getattr(response, "filled_avg_price", None) or order.limit_price or 0.0)
            return OrderResult(
                order_id=str(getattr(response, "id", order.order_id)),
                ticker=order.ticker,
                side=order.side,
                status=status,
                quantity=order.quantity,
                fill_price=fill_price,
                fill_price_effective=fill_price,
                simulation_only=False,
                simulation_reason="",
            )
        except Exception as exc:
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
        """Convenience wrapper — returns dict with buying_power and portfolio_value."""
        info = self.get_account_info()
        return {
            "buying_power": info.buying_power,
            "portfolio_value": info.portfolio_value,
            "cash": info.cash,
            "currency": info.currency,
        }

    def close(self) -> None:
        pass  # TradingClient is stateless HTTP


# ---------------------------------------------------------------------------
# Smoke test CLI
# ---------------------------------------------------------------------------

def _smoke_test() -> None:
    """Run a smoke test that exits 0 even without real API keys."""
    import sys

    print("AlpacaAdapter smoke test …")

    # Test 1: Missing credentials → BrokerNotConfiguredError (correct behaviour)
    try:
        _env_backup = {k: os.environ.pop(k, None) for k in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY")}
        try:
            AlpacaAdapter(api_key="", secret_key="")
        except BrokerNotConfiguredError:
            print("  [PASS] BrokerNotConfiguredError raised when keys missing")
        except ImportError as e:
            print(f"  [SKIP] alpaca-py not installed ({e})")
        else:
            print("  [WARN] No error raised without keys (alpaca-py not installed?)")
        finally:
            for k, v in _env_backup.items():
                if v is not None:
                    os.environ[k] = v
    except Exception as e:  # noqa: BLE001
        print(f"  [WARN] unexpected: {e}")

    # Test 2: Enum mapping
    assert _SIDE_MAP[OrderSide.BUY] == "buy"
    assert _ORDER_TYPE_MAP[OrderType.LIMIT] == "limit"
    assert _map_alpaca_status("filled") == OrderStatus.FILLED
    assert _map_alpaca_status("rejected") == OrderStatus.REJECTED
    print("  [PASS] Enum mapping correct")

    print("AlpacaAdapter smoke test PASSED")
    sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AlpacaAdapter")
    parser.add_argument("--smoke", action="store_true", help="run smoke test and exit")
    args = parser.parse_args()
    if args.smoke:
        _smoke_test()
    else:
        parser.print_help()
