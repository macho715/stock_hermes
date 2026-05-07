"""Tests for reports.py — coverage boost for formatting functions."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from stock_rtx4060.reports import (
    ReportWriter,
    _dict_table,
    _to_jsonable,
    _write_text,
    now_stamp,
)
from stock_rtx4060.risk_rules import CandidateVerdict, Gate, RiskConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_verdict(
    ticker: str = "AAPL",
    track: str = "S",
    score: float = 78.0,
    gate: Gate = Gate.GREEN,
    verdict: str = "ELIGIBLE_RECOMMENDATION",
    entry: float = 200.0,
    stop: float = 192.0,
    tp1: float = 210.0,
    tp2: float = 220.0,
    risk_reward: float = 2.5,
    risk_per_share: float = 8.0,
    quantity: int = 10,
    position_value: float = 2000.0,
    open_risk: float = 80.0,
    reasons: list[str] | None = None,
) -> CandidateVerdict:
    return CandidateVerdict(
        ticker=ticker,
        track=track,
        score=score,
        gate=gate,
        verdict=verdict,
        entry=entry,
        stop=stop,
        tp1=tp1,
        tp2=tp2,
        risk_reward=risk_reward,
        risk_per_share=risk_per_share,
        quantity=quantity,
        position_value=position_value,
        open_risk=open_risk,
        reasons=reasons or ["model_edge", "liquidity_ok"],
    )


# ---------------------------------------------------------------------------
# now_stamp
# ---------------------------------------------------------------------------

def test_now_stamp_format():
    stamp = now_stamp()
    # e.g. "2026-05-07_153045"
    assert len(stamp) == 17
    assert stamp[4] == "-"
    assert stamp[7] == "-"
    assert stamp[10] == "_"


# ---------------------------------------------------------------------------
# _write_text
# ---------------------------------------------------------------------------

def test_write_text_creates_file(tmp_path):
    p = tmp_path / "sub" / "out.md"
    result = _write_text(p, "hello world")
    assert result == p
    assert p.read_text(encoding="utf-8") == "hello world\n"


def test_write_text_overwrites(tmp_path):
    p = tmp_path / "out.md"
    _write_text(p, "first")
    _write_text(p, "second")
    assert p.read_text(encoding="utf-8") == "second\n"


# ---------------------------------------------------------------------------
# _dict_table
# ---------------------------------------------------------------------------

def test_dict_table_all_keys():
    result = _dict_table({"sharpe": 1.2, "mdd": -15.0})
    assert "sharpe" in result
    assert "1.2" in result


def test_dict_table_filtered_keys():
    result = _dict_table({"a": 1, "b": 2, "c": 3}, keys=["a", "c"])
    assert "a" in result
    assert "c" in result
    assert "b" not in result


def test_dict_table_missing_key_skipped():
    result = _dict_table({"a": 1}, keys=["a", "missing"])
    assert "a" in result
    assert "missing" not in result


# ---------------------------------------------------------------------------
# _to_jsonable
# ---------------------------------------------------------------------------

def test_to_jsonable_plain_value():
    assert _to_jsonable(42) == 42
    assert _to_jsonable("hello") == "hello"


def test_to_jsonable_path(tmp_path):
    p = tmp_path / "foo.json"
    result = _to_jsonable(p)
    assert result == str(p)


def test_to_jsonable_dict(tmp_path):
    p = tmp_path / "a"
    result = _to_jsonable({"p": p, "n": 1})
    assert result == {"p": str(p), "n": 1}


def test_to_jsonable_list(tmp_path):
    p = tmp_path / "a"
    result = _to_jsonable([p, 2])
    assert result == [str(p), 2]


def test_to_jsonable_tuple(tmp_path):
    p = tmp_path / "x"
    result = _to_jsonable((p, 3))
    assert result == [str(p), 3]


def test_to_jsonable_dataclass():
    @dataclass
    class Simple:
        x: int
        y: str

    result = _to_jsonable(Simple(x=1, y="hi"))
    assert result == {"x": 1, "y": "hi"}


# ---------------------------------------------------------------------------
# ReportWriter.__init__
# ---------------------------------------------------------------------------

def test_report_writer_creates_output_dir(tmp_path):
    d = tmp_path / "new_dir"
    assert not d.exists()
    rw = ReportWriter(d)
    assert d.is_dir()
    assert rw.output_dir == d


# ---------------------------------------------------------------------------
# ReportWriter.daily_brief
# ---------------------------------------------------------------------------

def test_daily_brief_empty_candidates(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.daily_brief([], filename="brief.md")
    text = path.read_text(encoding="utf-8")
    assert "# Daily Brief" in text
    assert "No candidates generated." in text
    assert "No automatic broker order" in text


def test_daily_brief_with_candidates(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.daily_brief([_make_verdict("AAPL"), _make_verdict("MSFT")], filename="brief.md")
    text = path.read_text(encoding="utf-8")
    assert "AAPL" in text
    assert "MSFT" in text
    assert "Runtime Gate:" in text


def test_daily_brief_runtime_gate_shown(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.daily_brief([], runtime_gate="GREEN", filename="brief.md")
    assert "**GREEN**" in path.read_text(encoding="utf-8")


def test_daily_brief_with_benchmark_summary(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.daily_brief(
        [],
        benchmark_summary={"cpu_score": 1500, "gpu_score": 3000},
        filename="brief.md",
    )
    text = path.read_text(encoding="utf-8")
    assert "## Benchmark Summary" in text
    assert "cpu_score" in text


def test_daily_brief_custom_filename(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.daily_brief([], filename="custom_brief.md")
    assert path.name == "custom_brief.md"


def test_daily_brief_auto_filename(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.daily_brief([])
    assert path.name.startswith("daily_brief_")
    assert path.suffix == ".md"


# ---------------------------------------------------------------------------
# ReportWriter.risk_dashboard
# ---------------------------------------------------------------------------

def test_risk_dashboard_empty(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.risk_dashboard([], filename="dash.md")
    text = path.read_text(encoding="utf-8")
    assert "# Risk Dashboard" in text
    assert "No gates to summarize." in text


def test_risk_dashboard_with_candidates(tmp_path):
    rw = ReportWriter(tmp_path)
    verdicts = [_make_verdict("AAPL", gate=Gate.GREEN), _make_verdict("NVDA", gate=Gate.AMBER)]
    path = rw.risk_dashboard(verdicts, filename="dash.md")
    text = path.read_text(encoding="utf-8")
    assert "## Capital Buckets" in text
    assert "## Open Risk" in text


def test_risk_dashboard_custom_config(tmp_path):
    rw = ReportWriter(tmp_path)
    cfg = RiskConfig(total_capital=200_000.0)
    path = rw.risk_dashboard([], config=cfg, filename="dash.md")
    text = path.read_text(encoding="utf-8")
    # Track-S open-risk limit = 200_000 * 0.20 * 0.02 = 800.0
    assert "800" in text


# ---------------------------------------------------------------------------
# ReportWriter.track_l_thesis
# ---------------------------------------------------------------------------

def test_track_l_thesis_no_l_candidates(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.track_l_thesis([_make_verdict(track="S")], filename="thesis.md")
    text = path.read_text(encoding="utf-8")
    assert "No Track-L candidates generated." in text


def test_track_l_thesis_with_l_candidate(tmp_path):
    rw = ReportWriter(tmp_path)
    verdict = _make_verdict(ticker="005930.KS", track="L", score=82.0)
    path = rw.track_l_thesis([verdict], filename="thesis.md")
    text = path.read_text(encoding="utf-8")
    assert "005930.KS" in text
    assert "82.00" in text
    assert "Thesis damage triggers" in text


def test_track_l_thesis_empty_candidates(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.track_l_thesis([], filename="thesis.md")
    text = path.read_text(encoding="utf-8")
    assert "# Track-L Thesis Report" in text


# ---------------------------------------------------------------------------
# ReportWriter.monthly_scorecard
# ---------------------------------------------------------------------------

def test_monthly_scorecard_no_backtest(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.monthly_scorecard(filename="sc.md")
    text = path.read_text(encoding="utf-8")
    assert "No backtest result attached." in text
    assert "None recorded." in text


def test_monthly_scorecard_with_backtest(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.monthly_scorecard(
        backtest_result={"total_return_pct": 8.5, "sharpe_ratio": 1.2, "max_drawdown_pct": -6.0, "win_rate_pct": 55.0, "n_trades": 12},
        filename="sc.md",
    )
    text = path.read_text(encoding="utf-8")
    assert "total_return_pct" in text
    assert "sharpe_ratio" in text


def test_monthly_scorecard_rule_violations(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.monthly_scorecard(rule_violations=["Stop skipped on AAPL", "Position over limit"], filename="sc.md")
    text = path.read_text(encoding="utf-8")
    assert "Stop skipped on AAPL" in text


# ---------------------------------------------------------------------------
# ReportWriter.journal_append
# ---------------------------------------------------------------------------

def test_journal_append_creates_csv(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.journal_append({"ticker": "AAPL", "action": "BUY"}, filename="journal.csv")
    assert path.exists()
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["action"] == "BUY"
    assert "timestamp" in rows[0]


def test_journal_append_accumulates_rows(tmp_path):
    rw = ReportWriter(tmp_path)
    rw.journal_append({"ticker": "AAPL", "action": "BUY"}, filename="j.csv")
    rw.journal_append({"ticker": "MSFT", "action": "SELL"}, filename="j.csv")
    rows = list(csv.DictReader((tmp_path / "j.csv").open(encoding="utf-8")))
    assert len(rows) == 2
    assert rows[1]["ticker"] == "MSFT"


# ---------------------------------------------------------------------------
# ReportWriter.json_report
# ---------------------------------------------------------------------------

def test_json_report_creates_json_file(tmp_path):
    rw = ReportWriter(tmp_path)
    path = rw.json_report("summary", {"score": 82.5, "verdict": "GREEN"})
    assert path.suffix == ".json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["score"] == 82.5
    assert data["verdict"] == "GREEN"


def test_json_report_serializes_path(tmp_path):
    rw = ReportWriter(tmp_path)
    src = tmp_path / "report.md"
    path = rw.json_report("meta", {"report_path": src})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["report_path"] == str(src)
