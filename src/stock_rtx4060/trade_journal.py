"""
Trade Journal — 사용자 거래 일지 및 의사결정 기록

Stage 4 of 5-stage investment system upgrade.
수동 기록 전용. 자동 주문 실행 없음.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "trade_journal.v1"
JOURNAL_DIR = Path("reports/trade_journal")


class EntryState(StrEnum):
    DRAFT = "DRAFT"      # 작성 중
    OPEN = "OPEN"        # 진입 완료
    CLOSED = "CLOSED"    # 종료 완료
    REVIEWED = "REVIEWED"  # 후기 작성 완료


class Outcome(StrEnum):
    TP = "TP"            # Take Profit (TP2)
    TP1 = "TP1"          # Partial TP1
    STOP = "STOP"        # Stop Loss
    MANUAL = "MANUAL"    # 수동 종료
    BREAKEVEN = "BREAKEVEN"  # 손절 이하


class EntryReason(StrEnum):
    SCREENING_RECOMMENDATION = "screening_recommendation"  # Algo 추천
    OWN_RESEARCH = "own_research"  # 자체 분석
    NEWS_EVENT = "news_event"  # 뉴스/이벤트
    TECHNICAL = "technical"  # 기술적 패턴
    OTHER = "other"


@dataclass
class JournalEntry:
    """단일 거래 일지 항목."""

    schema_version: str = SCHEMA_VERSION
    id: str = ""  # UUID-like unique id
    ticker: str = ""
    track: str = "S"  # "S" or "L"
    direction: str = "LONG"

    # Entry
    entry_date: str = ""  # ISO date
    entry_price: float = 0.0
    quantity: int = 0

    # Plan
    stop_price: float = 0.0
    tp1_price: float = 0.0
    tp2_price: float = 0.0
    risk_budget_pct: float = 0.0
    expected_rr: float = 0.0
    entry_reason: str = EntryReason.OTHER.value

    # State
    state: str = EntryState.DRAFT.value

    # Close
    close_date: str | None = None
    close_price: float | None = None
    outcome: str | None = None
    realized_pnl_abs: float | None = None
    realized_pnl_pct: float | None = None

    # Notes
    pre_trade_notes: str = ""
    post_trade_notes: str = ""
    lessons_learned: str = ""

    # Meta
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = _generate_id()
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()
        self.updated_at = datetime.now(UTC).isoformat()

    def open_position(self, entry_price: float, quantity: int, entry_date: str | None = None) -> None:
        self.entry_price = entry_price
        self.quantity = quantity
        self.entry_date = entry_date or date.today().isoformat()
        self.state = EntryState.OPEN.value
        self.updated_at = datetime.now(UTC).isoformat()

    def close_position(self, close_price: float, outcome: str, close_date: str | None = None, post_trade_notes: str = "") -> None:
        self.close_price = close_price
        self.outcome = outcome
        self.close_date = close_date or date.today().isoformat()
        self.state = EntryState.CLOSED.value
        self.post_trade_notes = post_trade_notes
        self.updated_at = datetime.now(UTC).isoformat()

        if self.entry_price > 0 and self.quantity > 0:
            pnl = (close_price - self.entry_price) * self.quantity
            self.realized_pnl_abs = round(pnl, 2)
            self.realized_pnl_pct = round((close_price - self.entry_price) / self.entry_price, 4)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> JournalEntry:
        # Strip schema_version if present
        data = {k: v for k, v in data.items() if k != "schema_version"}
        return cls(**data)


def _generate_id() -> str:
    """간단한 UUID-like ID 생성."""
    import uuid
    return uuid.uuid4().hex[:16]


def _journal_path(output_dir: Path | str = JOURNAL_DIR) -> Path:
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p / "journal_entries.jsonl"


@dataclass
class TradeJournal:
    """거래 일지 컬렉션."""

    output_dir: Path = field(default_factory=lambda: JOURNAL_DIR)

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> list[JournalEntry]:
        path = _journal_path(self.output_dir)
        if not path.exists():
            return []
        entries = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    data = json.loads(line)
                    entries.append(JournalEntry.from_dict(data))
                except Exception:
                    pass
        return entries

    def _save_all(self, entries: list[JournalEntry]) -> None:
        path = _journal_path(self.output_dir)
        lines = [json.dumps(e.to_dict(), ensure_ascii=False) for e in entries]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def add_entry(self, entry: JournalEntry) -> JournalEntry:
        entries = self._load_all()
        # Replace existing entry with same id, or append
        existing_ids = {e.id for e in entries}
        if entry.id in existing_ids:
            entries = [e if e.id != entry.id else entry for e in entries]
        else:
            entries.append(entry)
        self._save_all(entries)
        return entry

    def update_entry(self, entry_id: str, updates: dict) -> JournalEntry | None:
        entries = self._load_all()
        for i, e in enumerate(entries):
            if e.id == entry_id:
                for k, v in updates.items():
                    if hasattr(e, k):
                        setattr(e, k, v)
                e.updated_at = datetime.now(UTC).isoformat()
                entries[i] = e
                self._save_all(entries)
                return e
        return None

    def get_entry(self, entry_id: str) -> JournalEntry | None:
        entries = self._load_all()
        for e in entries:
            if e.id == entry_id:
                return e
        return None

    def get_ticker_entry(self, ticker: str, state: str | None = None) -> JournalEntry | None:
        entries = self._load_all()
        for e in entries:
            if e.ticker.upper() == ticker.upper():
                if state is None or e.state == state:
                    return e
        return None

    def list_entries(self, ticker: str | None = None, state: str | None = None, track: str | None = None, limit: int = 50) -> list[JournalEntry]:
        entries = self._load_all()
        if ticker:
            entries = [e for e in entries if e.ticker.upper() == ticker.upper()]
        if state:
            entries = [e for e in entries if e.state == state]
        if track:
            entries = [e for e in entries if e.track == track]
        return entries[-limit:]

    def open_tickers(self) -> list[str]:
        entries = self._load_all()
        return [e.ticker for e in entries if e.state == EntryState.OPEN.value]

    def statistics(self) -> dict[str, Any]:
        """거래 통계."""
        entries = self._load_all()
        closed = [e for e in entries if e.state == EntryState.CLOSED.value]
        total = len(entries)
        closed_count = len(closed)

        wins = [e for e in closed if e.realized_pnl_abs and e.realized_pnl_abs > 0]
        losses = [e for e in closed if e.realized_pnl_abs and e.realized_pnl_abs <= 0]

        total_pnl = sum((e.realized_pnl_abs or 0) for e in closed)
        win_rate = len(wins) / closed_count if closed_count > 0 else 0.0
        avg_win = sum(e.realized_pnl_abs or 0 for e in wins) / len(wins) if wins else 0.0
        avg_loss = sum(e.realized_pnl_abs or 0 for e in losses) / len(losses) if losses else 0.0

        outcome_counts: dict[str, int] = {}
        for e in closed:
            if e.outcome:
                outcome_counts[e.outcome] = outcome_counts.get(e.outcome, 0) + 1

        return {
            "total_entries": total,
            "open_positions": len([e for e in entries if e.state == EntryState.OPEN.value]),
            "closed_positions": closed_count,
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": round(win_rate, 4),
            "total_realized_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0.0,
            "outcome_counts": outcome_counts,
            "track_s_count": len([e for e in entries if e.track == "S"]),
            "track_l_count": len([e for e in entries if e.track == "L"]),
        }

    def generate_report(self, output_dir: Path | str | None = None) -> tuple[Path, Path]:
        """일지 리포트 생성."""
        out_dir = Path(output_dir) if output_dir else self.output_dir / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        json_path = out_dir / f"journal_report_{timestamp}.json"
        md_path = out_dir / f"journal_report_{timestamp}.md"

        entries = self._load_all()
        stats = self.statistics()
        closed = [e for e in entries if e.state == EntryState.CLOSED.value]
        open_entries = [e for e in entries if e.state == EntryState.OPEN.value]

        report = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "statistics": stats,
            "recent_entries": [e.to_dict() for e in entries[-20:]],
            "open_positions": [e.to_dict() for e in open_entries],
        }
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        md_lines = [
            f"# Trade Journal Report — {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}Z",
            "",
            "## Statistics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Entries | {stats['total_entries']} |",
            f"| Open Positions | {stats['open_positions']} |",
            f"| Closed Positions | {stats['closed_positions']} |",
            f"| Win Rate | {stats['win_rate']:.1%} |",
            f"| Total Realized P&L | ${stats['total_realized_pnl']:+,.2f} |",
            f"| Avg Win | ${stats['avg_win']:+,.2f} |",
            f"| Avg Loss | ${stats['avg_loss']:+,.2f} |",
            f"| Profit Factor | {stats['profit_factor']} |",
        ]

        if stats["outcome_counts"]:
            md_lines.extend(["", "### Outcomes", ""])
            for outcome, count in stats["outcome_counts"].items():
                md_lines.append(f"- {outcome}: {count}")

        md_lines.extend(["", "### Open Positions", ""])
        if open_entries:
            md_lines.append("| Ticker | Track | Entry Date | Entry | Qty | Stop | TP2 |")
            md_lines.append("|--------|-------|------------|-------|-----|------|-----|")
            for e in open_entries:
                md_lines.append(f"| {e.ticker} | {e.track} | {e.entry_date} | ${e.entry_price:.2f} | {e.quantity} | ${e.stop_price:.2f} | ${e.tp2_price:.2f} |")
        else:
            md_lines.append("_No open positions_")

        md_lines.extend(["", "### Recent Closed (Last 10)", ""])
        if closed:
            recent = sorted(closed, key=lambda x: x.close_date or "")[-10:]
            md_lines.append("| Ticker | Close Date | Entry | Close | Outcome | P&L |")
            md_lines.append("|--------|------------|-------|-------|---------|-----|")
            for e in recent:
                pnl_str = f"${e.realized_pnl_abs:+,.2f}" if e.realized_pnl_abs is not None else "—"
                md_lines.append(f"| {e.ticker} | {e.close_date} | ${e.entry_price:.2f} | ${e.close_price:.2f} | {e.outcome} | {pnl_str} |")
        else:
            md_lines.append("_No closed positions_")

        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        return json_path, md_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trade Journal — Stage 4")
    parser.add_argument("--add", action="store_true", help="Add new journal entry")
    parser.add_argument("--ticker", type=str, default=None, help="Ticker symbol")
    parser.add_argument("--track", type=str, default="S", help="Track: S or L")
    parser.add_argument("--entry-price", type=float, default=None, help="Entry price")
    parser.add_argument("--qty", type=int, default=None, help="Quantity")
    parser.add_argument("--entry-date", type=str, default=None, help="Entry date (ISO)")
    parser.add_argument("--stop", type=float, default=None, help="Stop price")
    parser.add_argument("--tp1", type=float, default=None, help="TP1 price")
    parser.add_argument("--tp2", type=float, default=None, help="TP2 price")
    parser.add_argument("--reason", type=str, default="own_research", help="Entry reason")
    parser.add_argument("--notes", type=str, default="", help="Pre-trade notes")
    parser.add_argument("--close", action="store_true", help="Close a position")
    parser.add_argument("--close-price", type=float, default=None, help="Close price")
    parser.add_argument("--outcome", type=str, default=None, help="Outcome: TP/STOP/MANUAL")
    parser.add_argument("--post-notes", type=str, default="", help="Post-trade notes")
    parser.add_argument("--list", action="store_true", help="List journal entries")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--output-dir", type=str, default="reports/trade_journal", help="Output directory")
    args = parser.parse_args()

    journal = TradeJournal(output_dir=Path(args.output_dir))

    if args.add:
        if not args.ticker or not args.entry_price or not args.qty:
            print("Error: --ticker, --entry-price, and --qty required for --add")
            exit(1)
        entry = JournalEntry(
            ticker=args.ticker.upper(),
            track=args.track,
            entry_reason=args.reason,
            pre_trade_notes=args.notes,
            stop_price=args.stop or 0.0,
            tp1_price=args.tp1 or 0.0,
            tp2_price=args.tp2 or 0.0,
        )
        entry.open_position(entry_price=args.entry_price, quantity=args.qty, entry_date=args.entry_date)
        result = journal.add_entry(entry)
        print(f"✅ Added entry {result.id} for {result.ticker} @ ${result.entry_price:.2f} x {result.quantity}")

    elif args.close:
        if not args.ticker or not args.close_price or not args.outcome:
            print("Error: --ticker, --close-price, and --outcome required for --close")
            exit(1)
        entry = journal.get_ticker_entry(args.ticker.upper(), state=EntryState.OPEN.value)
        if not entry:
            print(f"No open position found for {args.ticker}")
            exit(1)
        entry.close_position(close_price=args.close_price, outcome=args.outcome, post_trade_notes=args.post_notes)
        journal.add_entry(entry)  # re-save
        print(f"✅ Closed {entry.ticker} @ ${entry.close_price:.2f} — {entry.outcome} — P&L: ${entry.realized_pnl_abs:+,.2f} ({entry.realized_pnl_pct:+.2%})")

    elif args.list:
        entries = journal.list_entries(limit=20)
        print(f"\nTrade Journal ({len(entries)} entries):")
        for e in entries:
            state_icon = {"DRAFT": "📝", "OPEN": "🔵", "CLOSED": "✅", "REVIEWED": "📚"}[e.state]
            pnl_str = f"${e.realized_pnl_abs:+,.2f}" if e.realized_pnl_abs is not None else "—"
            print(f"  {state_icon} {e.ticker} ({e.track}) | {e.state} | Entry: ${e.entry_price:.2f} | P&L: {pnl_str} | {e.entry_date}")

    elif args.report:
        json_path, md_path = journal.generate_report()
        stats = journal.statistics()
        print("Journal Report:")
        print(f"  Total: {stats['total_entries']} entries, {stats['open_positions']} open, {stats['closed_positions']} closed")
        print(f"  Win Rate: {stats['win_rate']:.1%} | Total P&L: ${stats['total_realized_pnl']:+,.2f}")
        print(f"\n  Reports: {json_path}")
        print(f"           {md_path}")

    else:
        stats = journal.statistics()
        print("Trade Journal Summary:")
        print(f"  Total: {stats['total_entries']} | Open: {stats['open_positions']} | Closed: {stats['closed_positions']}")
        print(f"  Win Rate: {stats['win_rate']:.1%} | P&L: ${stats['total_realized_pnl']:+,.2f}")
        print("\nOptions: --add, --close, --list, --report")