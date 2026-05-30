"""Volume breakout gate — detects event-driven volume/price breakouts.

A breakout is confirmed when:
  1. final_volume >= avg_volume_20d * BREAKOUT_VOLUME_RATIO  (default 3×)
  2. final_close >= bb_upper * BB_UPPER_TOLERANCE            (default 99.5%)

When a breakout is detected while ``contrarian_mode=True`` is active, the
contrarian flag is disabled and the readiness status is downgraded to
AMBER_VOLUME_BREAKOUT_CONTRARIAN_DISABLED.

Safety invariants (always true regardless of input):
  * ``new_capital_allowed`` is always ``False``.
  * ``broker_order_execution`` is always ``False``.
  * ``signal`` is never emitted — direction decisions belong to the caller.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

#: Minimum ratio of final_volume / avg_volume_20d to trigger breakout.
BREAKOUT_VOLUME_RATIO: float = 3.0

#: close must be >= bb_upper * this tolerance to trigger the price leg.
BB_UPPER_TOLERANCE: float = 0.995

# ---------------------------------------------------------------------------
# Readiness statuses
# ---------------------------------------------------------------------------

STATUS_PASS = "PASS"
STATUS_AMBER_BREAKOUT = "AMBER_VOLUME_BREAKOUT"
STATUS_AMBER_CONTRARIAN_DISABLED = "AMBER_VOLUME_BREAKOUT_CONTRARIAN_DISABLED"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_volume_breakout(
    *,
    final_volume: float,
    avg_volume_20d: float,
    final_close: float,
    bb_upper: float,
    contrarian_mode: bool = False,
    volume_ratio_threshold: float = BREAKOUT_VOLUME_RATIO,
    bb_tolerance: float = BB_UPPER_TOLERANCE,
) -> dict[str, Any]:
    """Evaluate the volume breakout gate for a single bar.

    Parameters
    ----------
    final_volume:
        EOD final volume (authoritative, from KRX/broker).
    avg_volume_20d:
        20-day rolling average volume.  Must be > 0 (guarded internally).
    final_close:
        EOD final close price.
    bb_upper:
        Bollinger Band upper value for the same bar.
    contrarian_mode:
        Whether contrarian mode is currently active.  When ``True`` and a
        breakout is detected, the flag is disabled.
    volume_ratio_threshold:
        Override for the volume multiplier (default 3.0).
    bb_tolerance:
        Override for the Bollinger Band tolerance (default 0.995).

    Returns
    -------
    dict with keys:
        ``volume_breakout`` bool,
        ``contrarian_disabled`` bool,
        ``readiness_status`` str,
        ``volume_ratio`` float,
        ``new_capital_allowed`` bool (always False),
        ``broker_order_execution`` bool (always False).
    """
    safe_avg = max(float(avg_volume_20d), 1.0)
    volume_ratio = float(final_volume) / safe_avg

    volume_leg = volume_ratio >= volume_ratio_threshold
    price_leg = float(final_close) >= float(bb_upper) * bb_tolerance

    volume_breakout = volume_leg and price_leg
    contrarian_disabled = volume_breakout and contrarian_mode

    if contrarian_disabled:
        readiness_status = STATUS_AMBER_CONTRARIAN_DISABLED
    elif volume_breakout:
        readiness_status = STATUS_AMBER_BREAKOUT
    else:
        readiness_status = STATUS_PASS

    return {
        "volume_breakout": volume_breakout,
        "contrarian_disabled": contrarian_disabled,
        "readiness_status": readiness_status,
        "volume_ratio": round(volume_ratio, 2),
        "new_capital_allowed": False,
        "broker_order_execution": False,
    }
