"""Tests for the advisor audit log helpers."""

from __future__ import annotations

import json
from pathlib import Path

from stock_rtx4060.advisors.audit import check_completeness, log_advisor_call
from stock_rtx4060.advisors.base import AdvisoryOutput


def _build(ticker: str, agent: str = "news_sentiment", score: float = 0.5):
    return AdvisoryOutput(
        agent=agent,
        ticker=ticker,
        score=score,
        confidence=0.7,
        rationale="rationale",
        citations=["http://x"],
        prompt_hash="h",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.01,
    )


def test_log_advisor_call_creates_jsonl_record(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    out = _build("AAPL")
    written = log_advisor_call(out, path=target)
    assert written == target
    assert target.exists()
    record = json.loads(target.read_text(encoding="utf-8").strip())
    assert record["ticker"] == "AAPL"
    assert record["agent"] == "news_sentiment"
    assert "timestamp_utc" in record


def test_log_advisor_call_appends_multiple_records(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    log_advisor_call(_build("AAPL"), path=target)
    log_advisor_call(_build("MSFT"), path=target)
    lines = target.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    tickers = [json.loads(line)["ticker"] for line in lines]
    assert tickers == ["AAPL", "MSFT"]


def test_check_completeness_flags_missing_tickers(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    log_advisor_call(_build("AAPL", score=0.5), path=target)
    ok, missing = check_completeness([("AAPL", 0.5), ("NVDA", 0.3)], audit_path=target)
    assert not ok
    assert missing == ["NVDA"]


def test_check_completeness_ignores_zero_scores(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    log_advisor_call(_build("AAPL"), path=target)
    ok, missing = check_completeness([("AAPL", 0.5), ("ZERO", 0.0)], audit_path=target)
    assert ok
    assert missing == []


def test_check_completeness_returns_ok_when_all_present(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    log_advisor_call(_build("AAPL"), path=target)
    log_advisor_call(_build("MSFT"), path=target)
    ok, missing = check_completeness([("AAPL", 0.4), ("MSFT", -0.2)], audit_path=target)
    assert ok
    assert missing == []


def test_check_completeness_missing_log_file(tmp_path: Path) -> None:
    target = tmp_path / "missing.jsonl"
    ok, missing = check_completeness([("AAPL", 0.5)], audit_path=target)
    assert not ok
    assert missing == ["AAPL"]
