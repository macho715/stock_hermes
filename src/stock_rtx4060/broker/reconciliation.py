"""
Position reconciliation (Phase 8).

Compares broker positions against the internal position tracker and
emits warnings + Prometheus metrics on discrepancies.

Usage::

    from stock_rtx4060.broker.reconciliation import Reconciler, ReconciliationDiff

    reconciler = Reconciler()
    diffs = reconciler.run_once(broker, position_tracker)

    # Background mode (runs every 60 s by default)
    reconciler.start_background(interval_secs=60)
    # ...
    reconciler.stop()
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold — large diff triggers order pause
# ---------------------------------------------------------------------------
LARGE_DIFF_THRESHOLD_PCT = 0.10  # 10%


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ReconciliationDiff:
    """A single position discrepancy."""

    ticker: str
    broker_qty: float
    tracked_qty: float
    delta: float  # broker_qty - tracked_qty

    @property
    def is_large(self) -> bool:
        """True if the relative delta exceeds LARGE_DIFF_THRESHOLD_PCT."""
        denominator = max(abs(self.broker_qty), abs(self.tracked_qty), 1)
        return abs(self.delta) / denominator > LARGE_DIFF_THRESHOLD_PCT

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "broker_qty": self.broker_qty,
            "tracked_qty": self.tracked_qty,
            "delta": self.delta,
            "is_large": self.is_large,
        }


# ---------------------------------------------------------------------------
# Prometheus counter (optional — no-ops when prometheus_client not installed)
# ---------------------------------------------------------------------------

def _get_mismatch_counter():
    try:
        from prometheus_client import Counter
        return Counter(
            "reconciliation_mismatch_total",
            "Number of position reconciliation mismatches detected",
            ["ticker"],
        )
    except ImportError:
        class _NoopCounter:
            def labels(self, **_):
                return self
            def inc(self):
                pass
        return _NoopCounter()


_MISMATCH_COUNTER = None


def _mismatch_counter():
    global _MISMATCH_COUNTER
    if _MISMATCH_COUNTER is None:
        _MISMATCH_COUNTER = _get_mismatch_counter()
    return _MISMATCH_COUNTER


# ---------------------------------------------------------------------------
# Reconciler
# ---------------------------------------------------------------------------

class Reconciler:
    """Compare broker positions against internal position tracker.

    Parameters
    ----------
    on_large_diff : callable, optional
        Called with ``(diff: ReconciliationDiff)`` when a large diff is
        detected.  Default: logs a critical warning.
    pause_new_orders_flag : threading.Event, optional
        Set when a large diff is detected.  Downstream order submission
        should check this flag before sending orders.
    """

    def __init__(
        self,
        on_large_diff=None,
        pause_new_orders_flag: threading.Event | None = None,
    ) -> None:
        self._on_large_diff = on_large_diff or self._default_large_diff_handler
        self._pause_flag = pause_new_orders_flag or threading.Event()
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self.last_run_at: str | None = None
        self.last_diffs: list[ReconciliationDiff] = []

    # ------------------------------------------------------------------
    # Core reconciliation logic
    # ------------------------------------------------------------------

    def run_once(
        self,
        broker: Any,
        position_tracker: Any,
    ) -> list[ReconciliationDiff]:
        """Compare broker positions vs tracked positions.

        Parameters
        ----------
        broker : BrokerAdapter
            Live broker adapter (must implement ``get_positions()``).
        position_tracker
            Object with a ``.positions`` attribute that is a dict mapping
            ticker → position object/dict with ``quantity`` or ``qty``.

        Returns
        -------
        list[ReconciliationDiff]
        """
        self.last_run_at = datetime.now(UTC).isoformat()

        # Gather broker positions
        broker_positions: dict[str, float] = {}
        try:
            for pos in broker.get_positions():
                if hasattr(pos, "symbol"):
                    sym = pos.symbol.upper()
                    qty = float(pos.quantity or 0.0)
                elif isinstance(pos, dict):
                    sym = str(pos.get("symbol", pos.get("ticker", ""))).upper()
                    qty = float(pos.get("quantity", pos.get("qty", 0.0)) or 0.0)
                else:
                    continue
                if sym:
                    broker_positions[sym] = qty
        except Exception as exc:  # noqa: BLE001
            logger.error("Reconciler: get_positions() failed: %s", exc)
            return []

        # Gather tracked positions
        tracked_positions: dict[str, float] = {}
        try:
            raw = getattr(position_tracker, "positions", {}) or {}
            if isinstance(raw, dict):
                for sym, pos in raw.items():
                    sym_upper = sym.upper()
                    if hasattr(pos, "quantity"):
                        qty = float(pos.quantity or 0.0)
                    elif hasattr(pos, "qty"):
                        qty = float(pos.qty or 0.0)
                    elif isinstance(pos, dict):
                        qty = float(pos.get("quantity", pos.get("qty", 0.0)) or 0.0)
                    else:
                        qty = 0.0
                    tracked_positions[sym_upper] = qty
            elif isinstance(raw, list):
                for pos in raw:
                    if hasattr(pos, "ticker"):
                        sym_upper = pos.ticker.upper()
                        qty = float(getattr(pos, "quantity", 0.0) or 0.0)
                    elif isinstance(pos, dict):
                        sym_upper = str(pos.get("ticker", pos.get("symbol", ""))).upper()
                        qty = float(pos.get("quantity", pos.get("qty", 0.0)) or 0.0)
                    else:
                        continue
                    if sym_upper:
                        tracked_positions[sym_upper] = qty
        except Exception as exc:  # noqa: BLE001
            logger.error("Reconciler: reading position_tracker failed: %s", exc)
            return []

        # Compute diffs
        all_tickers = set(broker_positions) | set(tracked_positions)
        diffs: list[ReconciliationDiff] = []

        for ticker in sorted(all_tickers):
            b_qty = broker_positions.get(ticker, 0.0)
            t_qty = tracked_positions.get(ticker, 0.0)
            if abs(b_qty - t_qty) < 1e-9:
                continue

            diff = ReconciliationDiff(
                ticker=ticker,
                broker_qty=b_qty,
                tracked_qty=t_qty,
                delta=b_qty - t_qty,
            )
            diffs.append(diff)

            # Prometheus
            try:
                _mismatch_counter().labels(ticker=ticker).inc()
            except Exception:  # noqa: BLE001
                pass

            if diff.is_large:
                logger.critical(
                    "LARGE reconciliation mismatch: %s broker=%s tracked=%s delta=%s",
                    ticker, b_qty, t_qty, diff.delta,
                )
                try:
                    self._on_large_diff(diff)
                except Exception as exc:  # noqa: BLE001
                    logger.error("on_large_diff callback failed: %s", exc)
                self._pause_flag.set()
            else:
                logger.warning(
                    "Reconciliation mismatch: %s broker=%s tracked=%s delta=%s",
                    ticker, b_qty, t_qty, diff.delta,
                )

        self.last_diffs = diffs
        logger.info(
            "Reconciliation run complete: %d mismatches", len(diffs)
        )
        return diffs

    # ------------------------------------------------------------------
    # Background mode
    # ------------------------------------------------------------------

    def start_background(
        self,
        broker: Any,
        position_tracker: Any,
        interval_secs: int = 60,
    ) -> None:
        """Start a background thread that calls run_once every interval_secs."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()

        def _loop() -> None:
            while not self._stop_event.is_set():
                try:
                    self.run_once(broker, position_tracker)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Reconciler background loop error: %s", exc)
                self._stop_event.wait(interval_secs)

        self._thread = threading.Thread(
            target=_loop,
            name="reconciler-bg",
            daemon=True,
        )
        self._thread.start()
        logger.info("Reconciler background thread started (interval=%ds)", interval_secs)

    def stop(self) -> None:
        """Stop the background thread."""
        self._stop_event.set()
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("Reconciler stopped")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_large_diff_handler(diff: ReconciliationDiff) -> None:
        logger.critical(
            "ALERT: Large position reconciliation mismatch for %s "
            "(broker=%s, tracked=%s, delta=%s). "
            "New orders have been paused.",
            diff.ticker, diff.broker_qty, diff.tracked_qty, diff.delta,
        )

    @property
    def orders_paused(self) -> bool:
        """True if the pause-new-orders flag is set due to a large diff."""
        return self._pause_flag.is_set()

    def clear_pause(self) -> None:
        """Clear the pause flag (after manual review)."""
        self._pause_flag.clear()
        logger.info("Reconciler pause flag cleared")
