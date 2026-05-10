"""
broker — Live Broker Layer (Phase 8)

Re-exports the BrokerAdapter ABC, enums, and factory function so that
downstream code can do:

    from stock_rtx4060.broker import BrokerAdapter, get_broker, OrderType, Side, Status
"""

from __future__ import annotations

from ..broker_bridge import (
    AccountInfo,
    BrokerAdapter,
    BrokerPosition,
    OrderRequest,
    OrderResult,
    OrderType,
    PaperBroker,
    Quote,
)
from ..broker_bridge import (
    OrderSide as Side,
)
from ..broker_bridge import (
    OrderStatus as Status,
)


class BrokerNotConfiguredError(RuntimeError):
    """Raised when a broker adapter is requested but credentials are absent."""


def get_broker(
    name: str = "paper",
    **kwargs,
) -> BrokerAdapter:
    """Factory that returns a configured broker adapter.

    Parameters
    ----------
    name : str
        One of ``"paper"``, ``"alpaca"``, ``"ibkr"``, ``"kis"``.
    **kwargs :
        Passed through to the adapter constructor.

    Raises
    ------
    BrokerNotConfiguredError
        If the adapter requires credentials that are not present.
    ValueError
        If *name* is not a known adapter.
    """
    name_lower = name.lower()
    if name_lower == "paper":
        return PaperBroker(**kwargs)
    if name_lower == "alpaca":
        from .alpaca_adapter import AlpacaAdapter
        return AlpacaAdapter(**kwargs)
    if name_lower in ("ibkr", "ib", "interactive_brokers"):
        from .ibkr_adapter import IBKRAdapter
        return IBKRAdapter(**kwargs)
    if name_lower == "kis":
        from .kis_adapter import KISAdapter
        return KISAdapter(**kwargs)
    raise ValueError(
        f"Unknown broker '{name}'. Valid choices: paper, alpaca, ibkr, kis"
    )


__all__ = [
    "AccountInfo",
    "BrokerAdapter",
    "BrokerNotConfiguredError",
    "BrokerPosition",
    "OrderRequest",
    "OrderResult",
    "OrderType",
    "Quote",
    "Side",
    "Status",
    "get_broker",
]
