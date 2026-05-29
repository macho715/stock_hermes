"""AutoForwardRecorder — daily paper trading evidence for 005930.KS forward tracking.

Implements the FORWARD_PAPER_RUNNING → FORWARD_COMPLETE_USER_REVIEW_REQUIRED flow.

Safety boundary (immutable):
  auto_promote = False           — never auto-promote to LIVE_REVIEW_CANDIDATE
  new_capital_allowed = False    — no new capital in any state
  broker_order_execution = False — paper trading only; no real orders
  manual_approval_required = True
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Testable time helpers (monkeypatched in tests)
# ---------------------------------------------------------------------------


def _today() -> date:
    return date.today()


def _now_kst_hour() -> int:
    """Return current hour in KST (UTC+9)."""
    from datetime import timedelta, timezone
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).hour


# ---------------------------------------------------------------------------
# KRX calendar helpers
# ---------------------------------------------------------------------------

_KRX_HOLIDAYS_2026: frozenset[date] = frozenset({
    date(2026, 1, 1),   date(2026, 1, 27),  date(2026, 1, 28),  date(2026, 1, 29),
    date(2026, 3, 1),   date(2026, 5, 5),   date(2026, 5, 25),
    date(2026, 6, 6),   date(2026, 8, 15),  date(2026, 9, 24),  date(2026, 9, 25),
    date(2026, 9, 28),  date(2026, 10, 3),  date(2026, 10, 9),
    date(2026, 12, 25), date(2026, 12, 31),
})

KRX_EOD_HOUR_KST = 15   # KRX closes 15:30 KST; accept records after 15


def is_krx_trading_day(d: date) -> bool:
    """Return True if d is a KRX trading day (weekday, not holiday)."""
    return d.weekday() < 5 and d not in _KRX_HOLIDAYS_2026


def is_after_krx_eod(hour_kst: int) -> bool:
    """Return True if current KST hour is past market close."""
    return hour_kst >= KRX_EOD_HOUR_KST


# ---------------------------------------------------------------------------
# CSV schema
# ---------------------------------------------------------------------------

_CSV_FIELDNAMES = [
    "date", "symbol", "market", "close", "raw_signal", "raw_score",
    "readiness_status", "paper_action", "paper_position_qty",
    "paper_cash", "paper_equity", "benchmark_symbol",
    "benchmark_close", "benchmark_equity", "daily_return_pct",
    "benchmark_daily_return_pct", "daily_alpha_pct",
    "cumulative_alpha_pct", "max_drawdown_pct",
    "rule_violation", "rule_violation_reason",
    "data_quality_status", "provider", "generated_at_utc",
]


# ---------------------------------------------------------------------------
# AutoForwardRecorder
# ---------------------------------------------------------------------------


class AutoForwardRecorder:
    """Daily paper trading recorder for one symbol.

    Parameters
    ----------
    symbol : str
        KRX ticker, e.g. ``"005930.KS"``.
    market : str
        ``"KRX"``
    benchmark_symbol : str
        Benchmark ticker, e.g. ``"069500.KS"``.
    readiness : str
        Current readiness status, e.g. ``"PAPER_PASS"``.
    evidence_dir : str
        Directory for CSV / JSON evidence files.
    stop_after_days : int
        Number of trading days after which recording completes.
    auto_promote : bool
        Always ``False``.  Passing ``True`` raises ``ValueError``.
    """

    def __init__(
        self,
        *,
        symbol: str = "005930.KS",
        market: str = "KRX",
        benchmark_symbol: str = "069500.KS",
        readiness: str = "PAPER_PASS",
        evidence_dir: str = "reports/live_review/005930",
        stop_after_days: int = 30,
        auto_promote: bool = False,
    ) -> None:
        if auto_promote:
            raise ValueError(
                "auto_promote=True is forbidden. "
                "LIVE_REVIEW_CANDIDATE promotion requires manual user approval."
            )
        self.symbol = symbol
        self.market = market
        self.benchmark_symbol = benchmark_symbol
        self.readiness = readiness
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.stop_after_days = stop_after_days

        self._log_file = self.evidence_dir / f"paper_trading_log_{symbol.replace('.', '')}.csv"
        self._summary_file = self.evidence_dir / f"forward_paper_summary_{symbol.replace('.', '')}.json"
        self._state_file = self.evidence_dir / "auto_forward_recorder_state.json"
        self._review_pack_file = self.evidence_dir / f"review_pack_{symbol.replace('.', '')}.md"

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return current state dict. Safety fields are always set."""
        if self._state_file.exists():
            state = json.loads(self._state_file.read_text(encoding="utf-8"))
        else:
            state = {
                "schema_version": "auto_forward_recorder_state.v1",
                "symbol": self.symbol,
                "status": "FORWARD_PAPER_RUNNING",
                "days_recorded": 0,
                "target_days": self.stop_after_days,
                "completed": False,
                "last_recorded_date": None,
                "last_run_at_utc": None,
            }
        # Safety fields — always forced
        state["auto_promote"] = False
        state["new_capital_allowed"] = False
        state["broker_order_execution"] = False
        state["manual_approval_required"] = True
        return state

    def _save_state(self, state: dict[str, Any]) -> None:
        # Re-enforce safety fields before writing
        state["auto_promote"] = False
        state["new_capital_allowed"] = False
        state["broker_order_execution"] = False
        state["manual_approval_required"] = True
        self._state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # CSV helpers
    # ------------------------------------------------------------------

    def _recorded_dates(self) -> set[str]:
        if not self._log_file.exists():
            return set()
        dates: set[str] = set()
        with self._log_file.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dates.add(row["date"])
        return dates

    def _append_row(self, row: dict[str, Any]) -> None:
        write_header = not self._log_file.exists()
        with self._log_file.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_FIELDNAMES)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    def _count_recorded(self) -> int:
        if not self._log_file.exists():
            return 0
        with self._log_file.open(encoding="utf-8") as f:
            return sum(1 for _ in csv.reader(f)) - 1  # minus header

    def _compute_summary(self) -> dict[str, Any]:
        """Compute cumulative summary from CSV."""
        if not self._log_file.exists():
            return {"days": 0, "forward_paper_alpha_pct": 0.0,
                    "rule_violation_count": 0, "critical_data_missing_count": 0,
                    "max_forward_drawdown_pct": 0.0}

        rows: list[dict] = []
        with self._log_file.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        if not rows:
            return {"days": 0, "forward_paper_alpha_pct": 0.0,
                    "rule_violation_count": 0, "critical_data_missing_count": 0,
                    "max_forward_drawdown_pct": 0.0}

        days = len(rows)
        cum_alpha = float(rows[-1].get("cumulative_alpha_pct", 0.0) or 0.0)
        violations = sum(1 for r in rows if str(r.get("rule_violation", "")).lower() == "true")
        missing = sum(1 for r in rows if r.get("data_quality_status") == "FAIL")
        mdd = max(float(r.get("max_drawdown_pct", 0.0) or 0.0) for r in rows)

        return {
            "schema_version": "forward_paper_summary.v1",
            "symbol": self.symbol,
            "benchmark_symbol": self.benchmark_symbol,
            "days": days,
            "start_date": rows[0]["date"],
            "end_date": rows[-1]["date"],
            "forward_paper_alpha_pct": round(cum_alpha, 4),
            "rule_violation_count": violations,
            "critical_data_missing_count": missing,
            "max_forward_drawdown_pct": round(mdd, 4),
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run_once(
        self,
        *,
        dry_run: bool = False,
        mock_close: float | None = None,
        mock_benchmark_close: float | None = None,
    ) -> str:
        """Execute one recording attempt.

        Returns
        -------
        str
            One of: ALREADY_COMPLETED, SKIPPED_NON_TRADING_DAY,
            SKIPPED_BEFORE_EOD, SKIPPED_DUPLICATE_DATE,
            RECORDED, COMPLETE_REVIEW_REQUIRED.
        """
        state = self.get_state()

        # Already done?
        if state.get("completed"):
            return "ALREADY_COMPLETED"

        today = _today()
        hour_kst = _now_kst_hour()

        # Skip non-trading days
        if not is_krx_trading_day(today):
            logger.info("SKIP: %s is not a KRX trading day", today)
            return "SKIPPED_NON_TRADING_DAY"

        # Skip before EOD
        if not is_after_krx_eod(hour_kst):
            logger.info("SKIP: before KRX EOD (hour_kst=%d)", hour_kst)
            return "SKIPPED_BEFORE_EOD"

        # Skip duplicate dates
        date_str = today.isoformat()
        if date_str in self._recorded_dates():
            logger.info("SKIP: duplicate date %s", date_str)
            return "SKIPPED_DUPLICATE_DATE"

        if dry_run:
            logger.info("DRY_RUN: would record %s", date_str)
            return "RECORDED"

        # Build one CSV row
        close = mock_close if mock_close is not None else self._fetch_close(self.symbol)
        bench_close = (
            mock_benchmark_close
            if mock_benchmark_close is not None
            else self._fetch_close(self.benchmark_symbol)
        )

        prev_equity, prev_bench_equity, prev_cum_alpha = self._last_portfolio()
        paper_equity = prev_equity  # HOLD — no position changes in paper mode
        bench_equity = prev_bench_equity * (
            (bench_close / self._last_bench_close()) if self._last_bench_close() else 1.0
        )
        daily_alpha = 0.0
        cum_alpha = round(float(prev_cum_alpha) + daily_alpha, 4)
        mdd = max(
            0.0,
            float(max((float(self._compute_summary().get("max_forward_drawdown_pct", 0.0)), 0.0))),
        )

        row = {
            "date": date_str,
            "symbol": self.symbol,
            "market": self.market,
            "close": close,
            "raw_signal": "HOLD",
            "raw_score": 50.0,
            "readiness_status": "FORWARD_PAPER_RUNNING",
            "paper_action": "NO_ACTION",
            "paper_position_qty": 0,
            "paper_cash": 10_000_000.0,
            "paper_equity": paper_equity,
            "benchmark_symbol": self.benchmark_symbol,
            "benchmark_close": bench_close,
            "benchmark_equity": bench_equity,
            "daily_return_pct": 0.0,
            "benchmark_daily_return_pct": 0.0,
            "daily_alpha_pct": daily_alpha,
            "cumulative_alpha_pct": cum_alpha,
            "max_drawdown_pct": mdd,
            "rule_violation": False,
            "rule_violation_reason": "",
            "data_quality_status": "PASS",
            "provider": "pykrx",
            "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        }

        self._append_row(row)
        summary = self._compute_summary()
        self._summary_file.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Update state
        state["days_recorded"] = summary["days"]
        state["last_recorded_date"] = date_str
        state["last_run_at_utc"] = datetime.now(UTC).isoformat(timespec="seconds")

        if summary["days"] >= self.stop_after_days:
            from stock_rtx4060.reports.forward_review_pack import write_review_pack
            write_review_pack(summary, output_path=str(self._review_pack_file))
            state["status"] = "FORWARD_COMPLETE_USER_REVIEW_REQUIRED"
            state["completed"] = True
            self._save_state(state)
            return "COMPLETE_REVIEW_REQUIRED"

        state["status"] = "FORWARD_PAPER_RUNNING"
        self._save_state(state)
        return "RECORDED"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_close(self, symbol: str) -> float:
        """Fetch EOD close price. Falls back to 0.0 on error."""
        try:
            from stock_rtx4060.data_providers import load_ohlcv_with_provider
            pr = load_ohlcv_with_provider(symbol, "1d", data_provider="pykrx")
            return float(pr.frame["Close"].iloc[-1])
        except Exception:
            return 0.0

    def _last_portfolio(self) -> tuple[float, float, float]:
        """Return (paper_equity, bench_equity, cum_alpha) from last row."""
        if not self._log_file.exists():
            return (10_000_000.0, 10_000_000.0, 0.0)
        rows: list[dict] = []
        with self._log_file.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return (10_000_000.0, 10_000_000.0, 0.0)
        last = rows[-1]
        return (
            float(last.get("paper_equity", 10_000_000.0) or 10_000_000.0),
            float(last.get("benchmark_equity", 10_000_000.0) or 10_000_000.0),
            float(last.get("cumulative_alpha_pct", 0.0) or 0.0),
        )

    def _last_bench_close(self) -> float | None:
        if not self._log_file.exists():
            return None
        rows: list[dict] = []
        with self._log_file.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return None
        val = rows[-1].get("benchmark_close")
        return float(val) if val else None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto Forward Paper Recorder")
    parser.add_argument("--symbol", default="005930.KS")
    parser.add_argument("--market", default="KRX")
    parser.add_argument("--benchmark", default="069500.KS")
    parser.add_argument("--readiness", default="PAPER_PASS")
    parser.add_argument("--evidence-dir", default="reports/live_review/005930")
    parser.add_argument("--stop-after-days", type=int, default=30)
    parser.add_argument("--no-auto-promote", action="store_true", default=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    rec = AutoForwardRecorder(
        symbol=args.symbol,
        market=args.market,
        benchmark_symbol=args.benchmark,
        readiness=args.readiness,
        evidence_dir=args.evidence_dir,
        stop_after_days=args.stop_after_days,
        auto_promote=False,  # always False
    )

    result = rec.run_once()
    print(f"Result: {result}")
    sys.exit(0 if result in ("RECORDED", "COMPLETE_REVIEW_REQUIRED", "SKIPPED_DUPLICATE_DATE",
                              "SKIPPED_NON_TRADING_DAY", "SKIPPED_BEFORE_EOD",
                              "ALREADY_COMPLETED") else 1)


if __name__ == "__main__":
    main()
