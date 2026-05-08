"""
Smart Order Router (SOR) — Phase 8.

Routing rules
-------------
* ``*.KS`` / ``*.KQ``  → KIS adapter
* US tickers           → Alpaca primary, IBKR fallback

Every ``submit_order`` call checks the kill switch first.
``KillSwitchError`` propagates up and is never silently swallowed.

Kill switch
-----------
``OrderRouter.kill_switch()`` sets a global in-memory flag AND writes
``~/.cache/stock_1901/KILLED``.

``OrderRouter._check_kill_switch()`` raises ``KillSwitchError`` if either
the in-memory flag is True OR the KILLED file exists on disk.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Any

from ..broker_bridge import (
    BrokerAdapter,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
)
from . import BrokerNotConfiguredError, get_broker

logger = logging.getLogger(__name__)

KILLED_FILE = Path.home() / ".cache" / "stock_1901" / "KILLED"


class KillSwitchError(RuntimeError):
    """Raised when the global kill switch is active."""


class OrderRouter:
    """Routes orders to the correct broker adapter.

    Parameters
    ----------
    alpaca_kwargs : dict, optional
        Keyword arguments forwarded to AlpacaAdapter constructor.
    ibkr_kwargs : dict, optional
        Keyword arguments forwarded to IBKRAdapter constructor.
    kis_kwargs : dict, optional
        Keyword arguments forwarded to KISAdapter constructor.
    paper_fallback : bool
        When True (default), fall back to PaperBroker if a live adapter
        fails to initialise due to missing credentials.
    """

    def __init__(
        self,
        alpaca_kwargs: dict[str, Any] | None = None,
        ibkr_kwargs: dict[str, Any] | None = None,
        kis_kwargs: dict[str, Any] | None = None,
        paper_fallback: bool = True,
    ) -> None:
        self._paper_fallback = paper_fallback
        self._killed = False  # in-memory flag

        # Lazily initialised adapters
        self._alpaca: BrokerAdapter | None = None
        self._ibkr: BrokerAdapter | None = None
        self._kis: BrokerAdapter | None = None
        self._paper: BrokerAdapter = get_broker("paper")

        self._alpaca_kwargs: dict[str, Any] = alpaca_kwargs or {}
        self._ibkr_kwargs: dict[str, Any] = ibkr_kwargs or {}
        self._kis_kwargs: dict[str, Any] = kis_kwargs or {}

    # ------------------------------------------------------------------
    # Kill switch
    # ------------------------------------------------------------------

    def kill_switch(self) -> None:
        """Activate global kill switch.

        Sets in-memory flag AND writes the KILLED sentinel file.
        Any subsequent ``submit_order`` call raises ``KillSwitchError``.
        """
        self._killed = True
        KILLED_FILE.parent.mkdir(parents=True, exist_ok=True)
        KILLED_FILE.write_text(
            f"KILLED at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n",
            encoding="utf-8",
        )
        logger.critical("KILL SWITCH ACTIVATED — all order submissions blocked")

    def reset_kill_switch(self) -> None:
        """Remove the kill switch (in-memory + file). Use with extreme care."""
        self._killed = False
        try:
            KILLED_FILE.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
        logger.warning("Kill switch reset")

    def _check_kill_switch(self) -> None:
        """Raise KillSwitchError if kill switch is active."""
        if self._killed:
            raise KillSwitchError(
                "Kill switch is active (in-memory flag). "
                "No orders will be submitted."
            )
        if KILLED_FILE.exists():
            self._killed = True  # sync in-memory flag
            raise KillSwitchError(
                f"Kill switch file {KILLED_FILE} exists. "
                "No orders will be submitted."
            )

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _is_krx(self, ticker: str) -> bool:
        t = ticker.upper()
        return t.endswith(".KS") or t.endswith(".KQ")

    def _get_alpaca(self) -> BrokerAdapter:
        if self._alpaca is None:
            try:
                self._alpaca = get_broker("alpaca", **self._alpaca_kwargs)
            except (BrokerNotConfiguredError, ImportError) as exc:
                if self._paper_fallback:
                    logger.warning(
                        "Alpaca not configured (%s); falling back to PaperBroker", exc
                    )
                    return self._paper
                raise
        return self._alpaca

    def _get_ibkr(self) -> BrokerAdapter:
        if self._ibkr is None:
            try:
                self._ibkr = get_broker("ibkr", **self._ibkr_kwargs)
            except (BrokerNotConfiguredError, ImportError) as exc:
                if self._paper_fallback:
                    logger.warning(
                        "IBKR not configured (%s); falling back to PaperBroker", exc
                    )
                    return self._paper
                raise
        return self._ibkr

    def _get_kis(self) -> BrokerAdapter:
        if self._kis is None:
            try:
                self._kis = get_broker("kis", **self._kis_kwargs)
            except (BrokerNotConfiguredError, ImportError) as exc:
                if self._paper_fallback:
                    logger.warning(
                        "KIS not configured (%s); falling back to PaperBroker", exc
                    )
                    return self._paper
                raise
        return self._kis

    def _route(self, ticker: str) -> BrokerAdapter:
        if self._is_krx(ticker):
            return self._get_kis()
        # US ticker: Alpaca primary, IBKR fallback
        try:
            return self._get_alpaca()
        except BrokerNotConfiguredError:
            return self._get_ibkr()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit_order(
        self,
        ticker: str,
        qty: int,
        side: str,
        order_type: str = OrderType.MARKET,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> OrderResult:
        """Route and submit an order.

        Parameters
        ----------
        ticker : str
            Ticker symbol (e.g. ``"AAPL"`` or ``"005930.KS"``).
        qty : int
            Number of shares/units.
        side : str
            ``"BUY"`` or ``"SELL"``.
        order_type : str
            One of ``"MARKET"``, ``"LIMIT"``, ``"STOP"``, ``"STOP_LIMIT"``.
        limit_price : float, optional
        stop_price : float, optional

        Raises
        ------
        KillSwitchError
            If the kill switch is active.
        """
        self._check_kill_switch()  # always first!

        order = OrderRequest(
            ticker=ticker.upper(),
            side=side.upper(),
            order_type=order_type.upper(),
            quantity=qty,
            limit_price=limit_price,
            stop_price=stop_price,
        )
        adapter = self._route(ticker)
        logger.info(
            "OrderRouter: routing %s %d %s → %s",
            side, qty, ticker, adapter.broker_name,
        )
        return adapter.submit_order(order)

    def get_positions(self, market: str = "all") -> dict[str, BrokerAdapter]:
        """Return positions from configured adapters."""
        results: dict[str, list] = {}
        for name, adapter in [("kis", self._kis), ("alpaca", self._alpaca), ("ibkr", self._ibkr)]:
            if adapter is not None:
                try:
                    results[name] = adapter.get_positions()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("get_positions(%s) failed: %s", name, exc)
        return results

    def close(self) -> None:
        for adapter in (self._alpaca, self._ibkr, self._kis):
            if adapter is not None:
                try:
                    adapter.close()
                except Exception:  # noqa: BLE001
                    pass


# ---------------------------------------------------------------------------
# TWAP Executor
# ---------------------------------------------------------------------------

class TWAPExecutor:
    """Time-Weighted Average Price order slicer.

    Parameters
    ----------
    router : OrderRouter
        The order router to use for slice submission.
    """

    def __init__(self, router: OrderRouter) -> None:
        self._router = router

    def execute(
        self,
        ticker: str,
        total_qty: int,
        side: str,
        slices: int,
        interval_secs: float,
        order_type: str = OrderType.MARKET,
        limit_price: float | None = None,
    ) -> list[OrderResult]:
        """Split *total_qty* into *slices* equal parts separated by *interval_secs*.

        Returns
        -------
        list[OrderResult]
            One result per slice.
        """
        if slices < 1:
            raise ValueError("slices must be >= 1")
        if total_qty < 1:
            raise ValueError("total_qty must be >= 1")

        base_qty = total_qty // slices
        remainder = total_qty % slices
        results: list[OrderResult] = []

        for i in range(slices):
            qty = base_qty + (1 if i < remainder else 0)
            if qty < 1:
                continue
            try:
                result = self._router.submit_order(
                    ticker=ticker,
                    qty=qty,
                    side=side,
                    order_type=order_type,
                    limit_price=limit_price,
                )
                results.append(result)
                logger.info(
                    "TWAP slice %d/%d: %s %d %s → %s",
                    i + 1, slices, side, qty, ticker, result.status,
                )
            except KillSwitchError:
                raise  # propagate kill switch immediately
            except Exception as exc:  # noqa: BLE001
                logger.error("TWAP slice %d/%d failed: %s", i + 1, slices, exc)
                results.append(
                    OrderResult(
                        ticker=ticker,
                        side=side,
                        status=OrderStatus.REJECTED,
                        quantity=qty,
                        simulation_only=False,
                        simulation_reason="",
                        error_message=str(exc),
                    )
                )

            if i < slices - 1:
                time.sleep(interval_secs)

        return results


# ---------------------------------------------------------------------------
# VWAP Executor
# ---------------------------------------------------------------------------

class VWAPExecutor:
    """Volume-Weighted Average Price order slicer.

    Parameters
    ----------
    router : OrderRouter
        The order router to use for slice submission.
    """

    def __init__(self, router: OrderRouter) -> None:
        self._router = router

    def execute(
        self,
        ticker: str,
        total_qty: int,
        side: str,
        volume_curve: list[float],
        order_type: str = OrderType.MARKET,
        limit_price: float | None = None,
    ) -> list[OrderResult]:
        """Distribute *total_qty* according to *volume_curve* weights.

        Parameters
        ----------
        volume_curve : list[float]
            Relative volume weights for each slice (will be normalised).
            E.g. ``[0.1, 0.2, 0.4, 0.2, 0.1]`` for 5 intraday buckets.

        Returns
        -------
        list[OrderResult]
        """
        if not volume_curve:
            raise ValueError("volume_curve must not be empty")
        if total_qty < 1:
            raise ValueError("total_qty must be >= 1")

        total_weight = sum(volume_curve)
        if total_weight <= 0:
            raise ValueError("volume_curve weights must sum to a positive number")

        normalised = [w / total_weight for w in volume_curve]
        results: list[OrderResult] = []
        allocated = 0

        for i, weight in enumerate(normalised):
            is_last = i == len(normalised) - 1
            if is_last:
                qty = total_qty - allocated
            else:
                qty = round(total_qty * weight)
            if qty < 1:
                continue
            allocated += qty
            try:
                result = self._router.submit_order(
                    ticker=ticker,
                    qty=qty,
                    side=side,
                    order_type=order_type,
                    limit_price=limit_price,
                )
                results.append(result)
                logger.info(
                    "VWAP bucket %d/%d (weight=%.2f): %s %d %s → %s",
                    i + 1, len(normalised), weight, side, qty, ticker, result.status,
                )
            except KillSwitchError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("VWAP bucket %d/%d failed: %s", i + 1, len(normalised), exc)
                results.append(
                    OrderResult(
                        ticker=ticker,
                        side=side,
                        status=OrderStatus.REJECTED,
                        quantity=qty,
                        simulation_only=False,
                        simulation_reason="",
                        error_message=str(exc),
                    )
                )

        return results
