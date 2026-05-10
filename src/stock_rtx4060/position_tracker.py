"""
Position Tracker — 실시간持仓 추적 및 손익 계산

Stage 1 of 5-stage investment system upgrade.
읽기 전용. 주문 실행 없음.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yfinance as yf

from .krx_calendar import KRXCalendarUnavailable, load_krx_calendar_fixture


class PositionStatus(StrEnum):
    UNINITIALIZED = "UNINITIALIZED"
    OPEN = "OPEN"
    CLOSED_BY_STOP = "CLOSED_BY_STOP"
    CLOSED_BY_TP1 = "CLOSED_BY_TP1"
    CLOSED_BY_TP2 = "CLOSED_BY_TP2"
    MANUAL_CLOSE = "MANUAL_CLOSE"
    STOP_APPROACHING = "STOP_APPROACHING"  # <3% to stop
    TP_APPROACHING = "TP_APPROACHING"  # <3% to TP2


class CloseReason(StrEnum):
    STOP_HIT = "stop_hit"
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    MANUAL = "manual"
    TRAILING_STOP = "trailing_stop"


SCHEMA_VERSION = "position_tracker.v1"


@dataclass(frozen=True)
class PriceQuote:
    ticker: str
    current_price: float
    timestamp_utc: str
    currency: str = "USD"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrackedPosition:
    """단일 종목 추적 상태."""

    ticker: str
    track: str  # "S" short-term, "L" long-term
    entry_date: str
    entry_price: float
    quantity: int
    stop: float
    tp1: float
    tp2: float
    currency: str = "USD"
    status: str = PositionStatus.UNINITIALIZED.value
    close_reason: str | None = None
    close_date: str | None = None

    # Price tracking
    current_price: float = 0.0
    peak_price: float = 0.0
    trough_price: float = float("inf")

    # Computed
    unrealized_pnl_pct: float = 0.0
    unrealized_pnl_abs: float = 0.0
    distance_to_stop_pct: float = 0.0
    distance_to_tp2_pct: float = 0.0
    max_favorable_move_pct: float = 0.0  # from entry
    max_adverse_move_pct: float = 0.0  # from entry

    # State flags
    trailing_stop_activated: bool = False
    last_updated: str = ""

    def mark_open(self, current_price: float, timestamp_utc: str) -> None:
        self.current_price = current_price
        self.peak_price = max(self.peak_price, current_price)
        self.trough_price = min(self.trough_price, current_price)
        self.status = PositionStatus.OPEN.value
        self.last_updated = timestamp_utc
        self._recompute()
        self._check_warning_states()

    def update(self, current_price: float, timestamp_utc: str) -> str | None:
        """Update price, recompute pnl. Returns close_reason if position closed."""
        self.current_price = current_price
        self.peak_price = max(self.peak_price, current_price)
        self.trough_price = min(self.trough_price, current_price)
        self.last_updated = timestamp_utc

        close_reason = self._check_exit_conditions()

        if close_reason:
            self._close(close_reason)
            return close_reason

        self._recompute()
        self._check_warning_states()
        return None

    def _recompute(self) -> None:
        if self.current_price <= 0 or self.entry_price <= 0:
            return
        self.unrealized_pnl_pct = (self.current_price - self.entry_price) / self.entry_price
        self.unrealized_pnl_abs = (self.current_price - self.entry_price) * self.quantity

        risk_per_share = self.entry_price - self.stop
        if risk_per_share > 0:
            self.distance_to_stop_pct = (self.current_price - self.stop) / self.stop
        else:
            self.distance_to_stop_pct = 1.0  # safe if stop >= entry

        if self.tp2 > 0:
            self.distance_to_tp2_pct = (self.tp2 - self.current_price) / self.current_price
        else:
            self.distance_to_tp2_pct = 999.0

        if self.entry_price > 0:
            self.max_favorable_move_pct = (self.peak_price - self.entry_price) / self.entry_price
            mame = (self.entry_price - self.trough_price) / self.entry_price
            self.max_adverse_move_pct = max(0.0, mame)

    def _check_exit_conditions(self) -> str | None:
        """Check if TP or stop hit. Returns reason or None."""
        price = self.current_price

        # Stop loss — always checked first
        if price <= self.stop:
            return CloseReason.STOP_HIT.value

        # TP2 — always take if reached
        if price >= self.tp2:
            return CloseReason.TP2_HIT.value

        # TP1 — for Track-S, we hold through TP1 to TP2
        # TP1 is a partial exit signal, not full close
        # So we only close on stop or TP2 for now

        # Trailing stop activation: price > TP1 and then pulls back
        if not self.trailing_stop_activated and price >= self.tp1:
            self.trailing_stop_activated = True

        if self.trailing_stop_activated:
            # Trail stop: 2 * ATR-like: entry + (peak - entry) * 0.5
            trailing_stop_level = self.entry_price + (self.peak_price - self.entry_price) * 0.5
            if price <= trailing_stop_level:
                return CloseReason.TRAILING_STOP.value

        return None

    def _check_warning_states(self) -> None:
        """Update warning states without closing."""
        if self.distance_to_stop_pct < 0.03:  # <3% to stop
            self.status = PositionStatus.STOP_APPROACHING.value
        elif self.distance_to_tp2_pct < 0.03:  # <3% to TP2
            self.status = PositionStatus.TP_APPROACHING.value
        else:
            self.status = PositionStatus.OPEN.value

    def _close(self, reason: str) -> None:
        self.status = {
            CloseReason.STOP_HIT.value: PositionStatus.CLOSED_BY_STOP.value,
            CloseReason.TP2_HIT.value: PositionStatus.CLOSED_BY_TP2.value,
            CloseReason.TP1_HIT.value: PositionStatus.CLOSED_BY_TP1.value,
            CloseReason.TRAILING_STOP.value: PositionStatus.CLOSED_BY_STOP.value,
            CloseReason.MANUAL.value: PositionStatus.MANUAL_CLOSE.value,
        }.get(reason, PositionStatus.MANUAL_CLOSE.value)
        self.close_reason = reason
        self.close_date = datetime.now(UTC).date().isoformat()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = SCHEMA_VERSION
        return d


def fetch_quote(ticker: str, currency: str | None = None) -> PriceQuote | None:
    """Fetch current/recent price from yfinance."""
    try:
        tk = yf.Ticker(ticker)
        info = tk.fast_info
        price = info.last_price or info.previous_close
        if price is None or price <= 0:
            # fallback: history
            hist = tk.history(period="5d", auto_adjust=True)
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])

        if price is None or price <= 0:
            return None

        return PriceQuote(
            ticker=ticker,
            current_price=float(price),
            timestamp_utc=datetime.now(UTC).isoformat(),
            currency=currency or "USD",
        )
    except Exception:
        return None


def fetch_quotes_bulk(tickers: Iterable[str], delay: float = 0.1) -> dict[str, PriceQuote]:
    """Fetch quotes for multiple tickers with rate limiting."""
    results: dict[str, PriceQuote] = {}
    for ticker in tickers:
        quote = fetch_quote(ticker)
        if quote:
            results[ticker.upper()] = quote
        time.sleep(delay)  # avoid rate limiting
    return results


def business_days_between(start_date: str, end_date: str) -> int:
    """Count business days between two ISO date strings."""
    try:
        fixture = load_krx_calendar_fixture()
        trading_days = fixture.trading_day_set
        start_iso = start_date[:10]
        end_iso = end_date[:10]
        if start_iso in trading_days and end_iso in trading_days:
            days = sorted(trading_days)
            return len([d for d in days if start_iso <= d <= end_iso])
    except KRXCalendarUnavailable:
        pass

    # fallback: count weekdays
    from datetime import datetime
    start = datetime.fromisoformat(start_date[:10])
    end = datetime.fromisoformat(end_date[:10])
    days = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days += 1
        cur = cur.replace(day=cur.day + 1) if cur.day < 28 else end
    return days


@dataclass
class PortfolioSnapshot:
    """전체 포트폴리오 상태 요약."""

    schema_version: str = SCHEMA_VERSION
    generated_at: str = ""
    total_positions: int = 0
    open_positions: int = 0
    closed_positions: int = 0

    # P&L
    total_unrealized_pnl_abs: float = 0.0
    total_unrealized_pnl_pct: float = 0.0
    realized_pnl_abs: float = 0.0

    # Track breakdown
    track_s_value: float = 0.0
    track_l_value: float = 0.0
    track_s_unrealized_pct: float = 0.0
    track_l_unrealized_pct: float = 0.0

    # Risk
    total_exposure: float = 0.0
    total_position_value: float = 0.0
    warning_count: int = 0
    stop_approaching_tickers: list[str] = field(default_factory=list)
    tp_approaching_tickers: list[str] = field(default_factory=list)

    # Per-position details
    positions: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now(UTC).isoformat()

    @classmethod
    def from_positions(cls, positions: list[TrackedPosition]) -> PortfolioSnapshot:
        snapshot = cls()
        snapshot.total_positions = len(positions)

        open_pos = [p for p in positions if p.status == PositionStatus.OPEN.value or p.status == PositionStatus.STOP_APPROACHING.value or p.status == PositionStatus.TP_APPROACHING.value]
        closed_pos = [p for p in positions if p.status not in (PositionStatus.OPEN.value, PositionStatus.UNINITIALIZED.value, PositionStatus.STOP_APPROACHING.value, PositionStatus.TP_APPROACHING.value)]

        snapshot.open_positions = len(open_pos)
        snapshot.closed_positions = len(closed_pos)

        snapshot.total_unrealized_pnl_abs = sum(p.unrealized_pnl_abs for p in open_pos)
        snapshot.total_position_value = sum(p.current_price * p.quantity for p in open_pos)

        if snapshot.total_position_value > 0:
            snapshot.total_unrealized_pnl_pct = snapshot.total_unrealized_pnl_abs / snapshot.total_position_value

        track_s = [p for p in open_pos if p.track == "S"]
        track_l = [p for p in open_pos if p.track == "L"]
        snapshot.track_s_value = sum(p.current_price * p.quantity for p in track_s)
        snapshot.track_l_value = sum(p.current_price * p.quantity for p in track_l)

        if track_s:
            entry_vals = sum(p.entry_price * p.quantity for p in track_s)
            snapshot.track_s_unrealized_pct = (snapshot.track_s_value - entry_vals) / entry_vals if entry_vals > 0 else 0.0
        if track_l:
            entry_vals = sum(p.entry_price * p.quantity for p in track_l)
            snapshot.track_l_unrealized_pct = (snapshot.track_l_value - entry_vals) / entry_vals if entry_vals > 0 else 0.0

        snapshot.stop_approaching_tickers = [p.ticker for p in open_pos if p.status == PositionStatus.STOP_APPROACHING.value]
        snapshot.tp_approaching_tickers = [p.ticker for p in open_pos if p.status == PositionStatus.TP_APPROACHING.value]
        snapshot.warning_count = len(snapshot.stop_approaching_tickers) + len(snapshot.tp_approaching_tickers)

        snapshot.total_exposure = snapshot.total_position_value  # no leverage assumption
        snapshot.positions = [p.to_dict() for p in positions]
        return snapshot

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_positions_from_recommendation_json(json_path: str | Path) -> list[TrackedPosition]:
    """Load tracked positions from a recommendation engine JSON output."""
    path = Path(json_path)
    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    results = data if isinstance(data, list) else data.get("results", [])

    positions: list[TrackedPosition] = []
    for item in results:
        verdict = item.get("verdict", "")
        if verdict in ("ELIGIBLE_RECOMMENDATION", "ACCUMULATE_RECOMMENDATION"):
            entry_date = item.get("generated_at_utc", datetime.now(UTC).date().isoformat())[:10]
            positions.append(
                TrackedPosition(
                    ticker=item["ticker"],
                    track=item.get("track", "S"),
                    entry_date=entry_date,
                    entry_price=float(item["entry"]),
                    quantity=int(item.get("suggested_quantity", 0)),
                    stop=float(item["stop"]),
                    tp1=float(item["tp1"]),
                    tp2=float(item["tp2"]),
                    currency="USD",
                    status=PositionStatus.UNINITIALIZED.value,
                )
            )
    return positions


def save_portfolio_snapshot(snapshot: PortfolioSnapshot, output_dir: str | Path) -> tuple[Path, Path]:
    """Save portfolio snapshot as JSON and Markdown."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"portfolio_snapshot_{timestamp}.json"
    md_path = output_dir / f"portfolio_snapshot_{timestamp}.md"

    json_path.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        f"# Portfolio Snapshot — {snapshot.generated_at[:19]}Z",
        "",
        f"**Status:** {snapshot.open_positions} open / {snapshot.closed_positions} closed",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Unrealized P&L | {snapshot.total_unrealized_pnl_abs:+,.2f} ({snapshot.total_unrealized_pnl_pct:+.2%}) |",
        f"| Track-S Value | ${snapshot.track_s_value:,.2f} ({snapshot.track_s_unrealized_pct:+.2%}) |",
        f"| Track-L Value | ${snapshot.track_l_value:,.2f} ({snapshot.track_l_unrealized_pct:+.2%}) |",
        f"| Total Exposure | ${snapshot.total_exposure:,.2f} |",
    ]

    if snapshot.warning_count > 0:
        md_lines.append("")
        md_lines.append(f"⚠️ **Warnings:** {snapshot.warning_count}")
        if snapshot.stop_approaching_tickers:
            md_lines.append(f"  - STOP approaching: {', '.join(snapshot.stop_approaching_tickers)}")
        if snapshot.tp_approaching_tickers:
            md_lines.append(f"  - TP2 approaching: {', '.join(snapshot.tp_approaching_tickers)}")

    md_lines.extend(["", "## Positions", ""])
    for p in snapshot.positions:
        status_emoji = "🔴" if "STOP" in p["status"] else ("🟢" if "TP2" in p["status"] else ("🟡" if "OPEN" in p["status"] else "⚪"))
        md_lines.append(
            f"{status_emoji} **{p['ticker']}** ({p['track']}) — {p['status']} | "
            f"Entry: ${p['entry_price']:.2f} | Current: ${p['current_price']:.2f} | "
            f"P&L: {p['unrealized_pnl_pct']:+.2%} / ${p['unrealized_pnl_abs']:+,.2f}"
        )

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return json_path, md_path


def refresh_positions(positions: list[TrackedPosition], delay: float = 0.15) -> list[TrackedPosition]:
    """Refresh current prices for all positions. Returns updated positions with close_reason if any closed."""
    tickers = [p.ticker for p in positions if p.status not in (PositionStatus.CLOSED_BY_STOP.value, PositionStatus.CLOSED_BY_TP1.value, PositionStatus.CLOSED_BY_TP2.value, PositionStatus.MANUAL_CLOSE.value)]
    quotes = fetch_quotes_bulk(tickers, delay=delay)
    timestamp = datetime.now(UTC).isoformat()

    closed_events: list[tuple[str, str]] = []  # (ticker, reason)

    for pos in positions:
        if pos.status in (PositionStatus.CLOSED_BY_STOP.value, PositionStatus.CLOSED_BY_TP1.value, PositionStatus.CLOSED_BY_TP2.value, PositionStatus.MANUAL_CLOSE.value):
            continue
        quote = quotes.get(pos.ticker.upper())
        if quote is None:
            continue
        close_reason = pos.update(quote.current_price, timestamp)
        if close_reason:
            closed_events.append((pos.ticker, close_reason))

    return positions


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Position Tracker — Stage 1")
    parser.add_argument("--tickers", type=str, default="AAPL,MSFT,NVDA", help="Comma-separated tickers")
    parser.add_argument("--portfolio-json", type=str, default=None, help="Load from recommendation JSON")
    parser.add_argument("--watch", action="store_true", help="Watch mode — refresh periodically")
    parser.add_argument("--interval", type=int, default=300, help="Refresh interval in seconds (watch mode)")
    parser.add_argument("--output-dir", type=str, default="reports/position_tracker", help="Output directory")
    args = parser.parse_args()

    if args.portfolio_json:
        positions = load_positions_from_recommendation_json(args.portfolio_json)
        print(f"Loaded {len(positions)} positions from {args.portfolio_json}")
    else:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
        # Create dummy positions for demo
        positions = [
            TrackedPosition(ticker=t, track="S", entry_date=datetime.now(UTC).date().isoformat(), entry_price=100.0, quantity=10, stop=95.0, tp1=105.0, tp2=110.0)
            for t in tickers
        ]

    if args.watch:
        print(f"Watching {len(positions)} positions, refreshing every {args.interval}s. Ctrl+C to stop.")
        import time

        while True:
            positions = refresh_positions(positions)
            snapshot = PortfolioSnapshot.from_positions(positions)
            json_path, md_path = save_portfolio_snapshot(snapshot, args.output_dir)
            print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}Z] Updated → {json_path}")
            time.sleep(args.interval)
    else:
        positions = refresh_positions(positions)
        snapshot = PortfolioSnapshot.from_positions(positions)
        json_path, md_path = save_portfolio_snapshot(snapshot, args.output_dir)
        print(f"\nPortfolio Snapshot ({snapshot.open_positions} open, {snapshot.closed_positions} closed):")
        print(f"  Unrealized P&L: {snapshot.total_unrealized_pnl_abs:+,.2f} ({snapshot.total_unrealized_pnl_pct:+.2%})")
        print(f"  Track-S: ${snapshot.track_s_value:,.2f} ({snapshot.track_s_unrealized_pct:+.2%})")
        print(f"  Track-L: ${snapshot.track_l_value:,.2f} ({snapshot.track_l_unrealized_pct:+.2%})")
        if snapshot.warning_count > 0:
            print(f"  ⚠️ Warnings: stop approaching {snapshot.stop_approaching_tickers}, TP2 approaching {snapshot.tp_approaching_tickers}")
        print(f"\n  Reports: {json_path} | {md_path}")