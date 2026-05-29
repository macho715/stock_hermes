"""TDD tests for AutoForwardRecorder — 005930.KS 30-day forward paper tracking.

All tests verify report-only / paper-trading-only boundaries:
  - auto_promote is always False
  - new_capital_allowed is always False
  - broker_order_execution is always False
  - manual_approval_required is always True
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_recorder(tmp_path: Path, *, days_recorded: int = 0):
    from stock_rtx4060.live_review.auto_forward_recorder import AutoForwardRecorder

    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir()

    rec = AutoForwardRecorder(
        symbol="005930.KS",
        market="KRX",
        benchmark_symbol="069500.KS",
        readiness="PAPER_PASS",
        evidence_dir=str(ev_dir),
        stop_after_days=30,
        auto_promote=False,
    )

    # Pre-populate state if needed
    if days_recorded > 0:
        log_file = ev_dir / "paper_trading_log_005930KS.csv"  # matches symbol.replace('.','')=005930KS
        with log_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "date", "symbol", "market", "close", "raw_signal", "raw_score",
                "readiness_status", "paper_action", "paper_position_qty",
                "paper_cash", "paper_equity", "benchmark_symbol",
                "benchmark_close", "benchmark_equity", "daily_return_pct",
                "benchmark_daily_return_pct", "daily_alpha_pct",
                "cumulative_alpha_pct", "max_drawdown_pct",
                "rule_violation", "rule_violation_reason",
                "data_quality_status", "provider", "generated_at_utc",
            ])
            base = date(2026, 4, 1)
            for i in range(days_recorded):
                d = base + timedelta(days=i)
                writer.writerow([
                    d.isoformat(), "005930.KS", "KRX", 300000.0,
                    "HOLD", 50.0, "FORWARD_PAPER_RUNNING",
                    "NO_ACTION", 0, 10_000_000.0, 10_000_000.0,
                    "069500.KS", 100000.0, 10_000_000.0,
                    0.0, 0.0, 0.0, 0.5, 0.1,
                    False, "", "PASS", "pykrx",
                    datetime.utcnow().isoformat() + "Z",
                ])
        # write state
        state = {
            "schema_version": "auto_forward_recorder_state.v1",
            "symbol": "005930.KS",
            "status": "FORWARD_PAPER_RUNNING",
            "days_recorded": days_recorded,
            "target_days": 30,
            "completed": False,
            "last_recorded_date": (base + timedelta(days=days_recorded - 1)).isoformat(),
            "last_run_at_utc": datetime.utcnow().isoformat() + "Z",
            "auto_promote": False,
            "new_capital_allowed": False,
            "broker_order_execution": False,
            "manual_approval_required": True,
        }
        (ev_dir / "auto_forward_recorder_state.json").write_text(
            json.dumps(state, indent=2), encoding="utf-8"
        )

    return rec, ev_dir


# ---------------------------------------------------------------------------
# Safety invariants — highest priority
# ---------------------------------------------------------------------------


def test_never_enables_broker_execution(tmp_path: Path):
    """broker_order_execution must always be False in state file."""
    rec, ev_dir = _make_recorder(tmp_path)
    state = rec.get_state()
    assert state["broker_order_execution"] is False


def test_never_allows_new_capital(tmp_path: Path):
    """new_capital_allowed must always be False in state file."""
    rec, ev_dir = _make_recorder(tmp_path)
    state = rec.get_state()
    assert state["new_capital_allowed"] is False


def test_auto_promote_always_false(tmp_path: Path):
    """auto_promote must always be False — never auto-promote to LIVE_REVIEW."""
    rec, ev_dir = _make_recorder(tmp_path)
    state = rec.get_state()
    assert state["auto_promote"] is False


def test_manual_approval_required_always_true(tmp_path: Path):
    """manual_approval_required must always be True."""
    rec, ev_dir = _make_recorder(tmp_path)
    state = rec.get_state()
    assert state["manual_approval_required"] is True


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------


def test_auto_recorder_skips_non_trading_day(tmp_path: Path, monkeypatch):
    """Recorder returns SKIPPED on KRX non-trading day (weekend)."""
    rec, ev_dir = _make_recorder(tmp_path)
    # Force a known Saturday
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._today",
        lambda: date(2026, 5, 30),  # Saturday
    )
    result = rec.run_once(dry_run=True)
    assert result == "SKIPPED_NON_TRADING_DAY"


def test_auto_recorder_skips_before_eod(tmp_path: Path, monkeypatch):
    """Recorder returns SKIPPED when called before KRX EOD (15:30 KST)."""
    rec, ev_dir = _make_recorder(tmp_path)
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._today",
        lambda: date(2026, 5, 29),  # weekday
    )
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._now_kst_hour",
        lambda: 10,  # 10:00 KST — before EOD
    )
    result = rec.run_once(dry_run=True)
    assert result == "SKIPPED_BEFORE_EOD"


def test_auto_recorder_rejects_duplicate_date(tmp_path: Path, monkeypatch):
    """Recorder rejects a date that is already in the CSV log."""
    rec, ev_dir = _make_recorder(tmp_path, days_recorded=5)
    # The last recorded date is 2026-04-05 (Sunday) — use Friday 2026-04-03
    # which is also within the 5-day window of the pre-populated data
    # (base=2026-04-01, days=5 → last recorded = 2026-04-05)
    # Use 2026-04-02 (Thursday) as a recorded weekday
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._today",
        lambda: date(2026, 4, 2),   # Thursday — weekday, already in CSV
    )
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._now_kst_hour",
        lambda: 16,
    )
    result = rec.run_once(dry_run=True)
    assert result == "SKIPPED_DUPLICATE_DATE"


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------


def test_auto_recorder_appends_one_row_per_day(tmp_path: Path, monkeypatch):
    """Each successful run appends exactly one row to the CSV."""
    rec, ev_dir = _make_recorder(tmp_path, days_recorded=3)
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._today",
        lambda: date(2026, 4, 7),  # Tuesday (next weekday after 3-day pre-fill ending 2026-04-03)
    )
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._now_kst_hour",
        lambda: 16,
    )

    log_file = ev_dir / "paper_trading_log_005930KS.csv"
    rows_before = sum(1 for _ in open(log_file)) - 1  # minus header

    result = rec.run_once(
        dry_run=False,
        mock_close=300000.0,
        mock_benchmark_close=100000.0,
    )

    log_file = ev_dir / "paper_trading_log_005930KS.csv"
    rows_after = sum(1 for _ in open(log_file)) - 1
    assert result in ("RECORDED", "COMPLETE_REVIEW_REQUIRED")
    assert rows_after == rows_before + 1


def test_auto_recorder_writes_summary_each_run(tmp_path: Path, monkeypatch):
    """Summary JSON is created/updated after each successful run."""
    rec, ev_dir = _make_recorder(tmp_path, days_recorded=5)
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._today",
        lambda: date(2026, 4, 6),
    )
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._now_kst_hour",
        lambda: 16,
    )
    rec.run_once(dry_run=False, mock_close=300000.0, mock_benchmark_close=100000.0)

    summary_file = ev_dir / "forward_paper_summary_005930KS.json"
    assert summary_file.exists()
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary["days"] >= 6
    assert "forward_paper_alpha_pct" in summary


def test_auto_recorder_completes_after_30_days(tmp_path: Path, monkeypatch):
    """After 30 recorded days the status becomes FORWARD_COMPLETE_USER_REVIEW_REQUIRED."""
    rec, ev_dir = _make_recorder(tmp_path, days_recorded=29)
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._today",
        lambda: date(2026, 5, 15),  # 30th day
    )
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._now_kst_hour",
        lambda: 16,
    )
    result = rec.run_once(dry_run=False, mock_close=300000.0, mock_benchmark_close=100000.0)

    assert result == "COMPLETE_REVIEW_REQUIRED"
    state = json.loads((ev_dir / "auto_forward_recorder_state.json").read_text())
    assert state["status"] == "FORWARD_COMPLETE_USER_REVIEW_REQUIRED"
    assert state["completed"] is True
    assert state["auto_promote"] is False  # still False after completion
    assert state["new_capital_allowed"] is False


def test_review_pack_generated_after_30_days(tmp_path: Path, monkeypatch):
    """review_pack_005930.md is created when 30 days are recorded."""
    rec, ev_dir = _make_recorder(tmp_path, days_recorded=29)
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._today",
        lambda: date(2026, 5, 15),
    )
    monkeypatch.setattr(
        "stock_rtx4060.live_review.auto_forward_recorder._now_kst_hour",
        lambda: 16,
    )
    rec.run_once(dry_run=False, mock_close=300000.0, mock_benchmark_close=100000.0)

    review_pack = ev_dir / "review_pack_005930KS.md"
    assert review_pack.exists()
    content = review_pack.read_text(encoding="utf-8")
    # Must contain the mandatory report-only disclaimer
    assert "paper-trading evidence report only" in content
    assert "No broker order was executed" in content
    assert "No new capital" in content
    assert "FORWARD_COMPLETE_USER_REVIEW_REQUIRED" in content


def test_forward_summary_pass_requires_alpha_ge_0(tmp_path: Path, monkeypatch):
    """Forward summary status=FAIL when cumulative alpha < 0."""
    from stock_rtx4060.live_review.auto_forward_recorder import AutoForwardRecorder
    from stock_rtx4060.reports.forward_review_pack import evaluate_forward_summary

    summary = {
        "schema_version": "forward_paper_summary.v1",
        "symbol": "005930.KS",
        "days": 30,
        "forward_paper_alpha_pct": -1.5,   # negative → FAIL
        "rule_violation_count": 0,
        "critical_data_missing_count": 0,
        "max_forward_drawdown_pct": 3.0,
        "forward_mdd_limit": 20.0,
    }
    status = evaluate_forward_summary(summary)
    assert status == "FAIL"
