"""
Pre-trade compliance gate (Phase 8).

Usage::

    from stock_rtx4060.broker.compliance import check_order, ComplianceError

    check_order(
        ticker="AAPL",
        qty=100,
        side="BUY",
        current_positions={...},
        portfolio_value=500_000.0,
        config=ComplianceConfig(),
    )

All checks raise ``ComplianceError`` with a human-readable reason if they fail.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default config file paths
# ---------------------------------------------------------------------------

_DEFAULT_SECTOR_MAP = (
    Path(__file__).resolve().parents[3]  # project root
    / "config" / "sector_map.json"
)
_DEFAULT_RESTRICTED = (
    Path(__file__).resolve().parents[3]
    / "config" / "restricted_tickers.txt"
)


# ---------------------------------------------------------------------------
# Error + config
# ---------------------------------------------------------------------------

class ComplianceError(ValueError):
    """Raised when a pre-trade compliance check fails."""


@dataclass
class ComplianceConfig:
    """Configuration for the compliance gate.

    Parameters
    ----------
    max_single_position_pct : float
        Maximum single-position weight as a fraction of portfolio value
        (default 0.10 = 10%).
    max_sector_exposure_pct : float
        Maximum sector exposure as a fraction of portfolio value
        (default 0.25 = 25%).
    allow_leverage : bool
        If False (default), total long notional must not exceed
        portfolio_value.
    krx_price_limit_pct : float
        KRX daily price move limit (default 0.30 = ±30%).
    wash_sale_days : int
        Minimum days between a loss sale and a buy of the same ticker
        (default 30).
    sector_map_path : Path, optional
        Path to ``sector_map.json``.
    restricted_tickers_path : Path, optional
        Path to ``restricted_tickers.txt``.
    """

    max_single_position_pct: float = 0.10
    max_sector_exposure_pct: float = 0.25
    allow_leverage: bool = False
    krx_price_limit_pct: float = 0.30
    wash_sale_days: int = 30
    sector_map_path: Path = field(default_factory=lambda: _DEFAULT_SECTOR_MAP)
    restricted_tickers_path: Path = field(default_factory=lambda: _DEFAULT_RESTRICTED)

    def load_sector_map(self) -> dict[str, str]:
        try:
            return json.loads(Path(self.sector_map_path).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def load_restricted_tickers(self) -> set[str]:
        try:
            lines = Path(self.restricted_tickers_path).read_text(encoding="utf-8").splitlines()
            return {ln.strip().upper() for ln in lines if ln.strip() and not ln.startswith("#")}
        except FileNotFoundError:
            return set()


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_single_position(
    ticker: str,
    qty: int,
    price: float,
    portfolio_value: float,
    current_positions: dict[str, Any],
    max_pct: float,
) -> None:
    """Single position ≤ max_pct of portfolio_value."""
    if portfolio_value <= 0:
        return
    existing_value = 0.0
    pos = current_positions.get(ticker.upper()) or current_positions.get(ticker)
    if pos is not None:
        if hasattr(pos, "market_value"):
            existing_value = float(pos.market_value or 0.0)
        elif isinstance(pos, dict):
            existing_value = float(pos.get("market_value", 0.0) or 0.0)

    new_value = qty * price + existing_value
    pct = new_value / portfolio_value
    if pct > max_pct:
        raise ComplianceError(
            f"Single-position limit breach: {ticker} would be "
            f"{pct:.1%} of portfolio (limit {max_pct:.1%}). "
            f"Notional={new_value:,.2f}, portfolio={portfolio_value:,.2f}"
        )


def _check_sector_exposure(
    ticker: str,
    qty: int,
    price: float,
    portfolio_value: float,
    current_positions: dict[str, Any],
    sector_map: dict[str, str],
    max_sector_pct: float,
) -> None:
    """Sector exposure ≤ max_sector_pct of portfolio_value."""
    if portfolio_value <= 0:
        return

    raw_ticker = ticker.upper().replace(".KS", "").replace(".KQ", "")
    sector = sector_map.get(raw_ticker) or sector_map.get(ticker.upper())
    if sector is None:
        logger.debug("No sector mapping for %s — skipping sector check", ticker)
        return

    # Compute current sector exposure
    sector_value = 0.0
    for sym, pos in current_positions.items():
        sym_raw = sym.upper().replace(".KS", "").replace(".KQ", "")
        sym_sector = sector_map.get(sym_raw) or sector_map.get(sym.upper())
        if sym_sector != sector:
            continue
        if hasattr(pos, "market_value"):
            sector_value += float(pos.market_value or 0.0)
        elif isinstance(pos, dict):
            sector_value += float(pos.get("market_value", 0.0) or 0.0)

    new_sector_value = sector_value + qty * price
    pct = new_sector_value / portfolio_value
    if pct > max_sector_pct:
        raise ComplianceError(
            f"Sector exposure limit breach: sector '{sector}' would be "
            f"{pct:.1%} of portfolio (limit {max_sector_pct:.1%}). "
            f"New sector total={new_sector_value:,.2f}"
        )


def _check_no_leverage(
    qty: int,
    price: float,
    portfolio_value: float,
    current_positions: dict[str, Any],
) -> None:
    """Total long notional ≤ portfolio_value."""
    if portfolio_value <= 0:
        return
    existing_long = sum(
        float(
            pos.market_value if hasattr(pos, "market_value")
            else pos.get("market_value", 0.0)  # type: ignore[union-attr]
        )
        for pos in current_positions.values()
        if pos is not None
    )
    new_notional = existing_long + qty * price
    if new_notional > portfolio_value:
        raise ComplianceError(
            f"Leverage check failed: total long notional {new_notional:,.2f} "
            f"would exceed portfolio value {portfolio_value:,.2f}"
        )


def _check_krx_price_limit(
    ticker: str,
    price: float,
    current_positions: dict[str, Any],
    limit_pct: float,
) -> None:
    """KRX ±30% daily limit check for KRX tickers."""
    t = ticker.upper()
    if not (t.endswith(".KS") or t.endswith(".KQ")):
        return  # Not a KRX ticker

    pos = current_positions.get(ticker.upper()) or current_positions.get(ticker)
    if pos is None:
        return  # No reference price available

    if hasattr(pos, "avg_cost"):
        ref_price = float(pos.avg_cost or 0.0)
    elif isinstance(pos, dict):
        ref_price = float(pos.get("avg_cost", 0.0) or pos.get("avg_price", 0.0) or 0.0)
    else:
        return

    if ref_price <= 0:
        return

    change_pct = abs(price - ref_price) / ref_price
    if change_pct > limit_pct:
        raise ComplianceError(
            f"KRX price limit breach: {ticker} price {price:,.2f} is "
            f"{change_pct:.1%} away from reference {ref_price:,.2f} "
            f"(limit ±{limit_pct:.1%})"
        )


def _check_restricted_tickers(ticker: str, restricted: set[str]) -> None:
    """Ticker not in restricted list."""
    raw = ticker.upper()
    if raw in restricted:
        raise ComplianceError(
            f"Ticker {ticker} is on the restricted tickers list."
        )


def _check_wash_sale(
    ticker: str,
    side: str,
    position_tracker: Any,
    wash_sale_days: int,
) -> None:
    """US wash-sale: no buy within 30 days of a loss sale of the same ticker.

    Parameters
    ----------
    position_tracker
        Object with ``.get_recent_closes(ticker)`` → list of dicts with
        ``{"date": str, "pnl": float}`` or a dict with ``closed_positions``.
        If the tracker doesn't have this interface, the check is skipped
        (fail-open is acceptable for this rule).
    """
    if side.upper() != "BUY":
        return
    if position_tracker is None:
        return

    t = ticker.upper()
    # Only applies to US tickers
    if t.endswith(".KS") or t.endswith(".KQ"):
        return

    try:
        # Try various interface shapes
        recent_closes: list[dict] = []
        if hasattr(position_tracker, "get_recent_closes"):
            recent_closes = position_tracker.get_recent_closes(ticker) or []
        elif hasattr(position_tracker, "closed_positions"):
            cp = position_tracker.closed_positions
            if isinstance(cp, dict):
                recent_closes = cp.get(t, [])
            elif isinstance(cp, list):
                recent_closes = [r for r in cp if str(r.get("ticker", "")).upper() == t]

        cutoff = date.today() - timedelta(days=wash_sale_days)
        for close in recent_closes:
            pnl = float(close.get("pnl", close.get("unrealized_pnl", 1.0)) or 1.0)
            close_date_str = str(close.get("date", close.get("close_date", "")) or "")
            if not close_date_str:
                continue
            try:
                close_date = date.fromisoformat(close_date_str[:10])
            except ValueError:
                continue
            if pnl < 0 and close_date >= cutoff:
                raise ComplianceError(
                    f"Wash-sale rule: cannot buy {ticker} within {wash_sale_days} days "
                    f"of a loss sale on {close_date_str} (PnL={pnl:,.2f})"
                )
    except ComplianceError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.debug("wash-sale check skipped for %s: %s", ticker, exc)


# ---------------------------------------------------------------------------
# Main gate function
# ---------------------------------------------------------------------------

def check_order(
    ticker: str,
    qty: int,
    side: str,
    current_positions: dict[str, Any],
    portfolio_value: float,
    config: ComplianceConfig | None = None,
    price: float = 0.0,
    position_tracker: Any = None,
) -> None:
    """Pre-trade compliance gate.

    Runs all compliance checks sequentially.  Raises ``ComplianceError`` with
    a descriptive reason on the first failure.

    Parameters
    ----------
    ticker : str
        Ticker symbol (e.g. ``"AAPL"`` or ``"005930.KS"``).
    qty : int
        Number of shares/units in the proposed order.
    side : str
        ``"BUY"`` or ``"SELL"``.
    current_positions : dict[str, Any]
        Current open positions keyed by ticker.  Values can be
        ``BrokerPosition`` objects or plain dicts with ``market_value``.
    portfolio_value : float
        Current portfolio value (used as denominator for % checks).
    config : ComplianceConfig, optional
        Compliance parameters.  Defaults to standard settings.
    price : float
        Estimated execution price.  Required for notional checks.
        If 0, size-based checks are skipped.
    position_tracker : optional
        Position tracker with historical close data for wash-sale check.

    Raises
    ------
    ComplianceError
        If any compliance check fails.
    """
    cfg = config or ComplianceConfig()

    sector_map = cfg.load_sector_map()
    restricted = cfg.load_restricted_tickers()

    # 1) Restricted tickers
    _check_restricted_tickers(ticker, restricted)

    # 2) Only proceed with notional checks if we have a price
    if price > 0 and side.upper() == "BUY":
        # 3) Single position limit
        _check_single_position(
            ticker, qty, price, portfolio_value, current_positions,
            cfg.max_single_position_pct,
        )

        # 4) Sector exposure
        _check_sector_exposure(
            ticker, qty, price, portfolio_value, current_positions,
            sector_map, cfg.max_sector_exposure_pct,
        )

        # 5) No leverage
        if not cfg.allow_leverage:
            _check_no_leverage(qty, price, portfolio_value, current_positions)

        # 6) KRX price limit
        _check_krx_price_limit(ticker, price, current_positions, cfg.krx_price_limit_pct)

    # 7) Wash-sale
    _check_wash_sale(ticker, side, position_tracker, cfg.wash_sale_days)

    logger.debug("Compliance check PASSED: %s %d %s", side, qty, ticker)
