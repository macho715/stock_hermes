"""Tests for journal.py — pure-function coverage."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from stock_rtx4060.journal import (
    _stable_json,
    compute_file_hash,
    generate_journal_id,
    sha256_hex,
    write_journal_entry,
)


def test_sha256_hex_returns_64_char_hex():
    result = sha256_hex("hello")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_sha256_hex_deterministic():
    assert sha256_hex("abc") == sha256_hex("abc")
    assert sha256_hex("abc") != sha256_hex("xyz")


def test_stable_json_is_deterministic():
    obj = {"z": 1, "a": 2, "m": [3, 4]}
    result = _stable_json(obj)
    assert result == _stable_json(obj)
    parsed = json.loads(result)
    assert parsed["z"] == 1 and parsed["a"] == 2


def test_generate_journal_id_format():
    ts = datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc)
    jid = generate_journal_id("AAPL", "S", 1, timestamp=ts)
    assert jid == "JRN-2026-0507-AAPL-S-001"


def test_generate_journal_id_uses_utc_now_when_no_timestamp():
    jid = generate_journal_id("MSFT", "L", 3)
    assert jid.startswith("JRN-")
    assert "MSFT" in jid
    assert jid.endswith("-003")


def test_write_journal_entry_creates_file(tmp_path):
    file_path = write_journal_entry(
        output_dir=tmp_path,
        ticker="AAPL",
        track="S",
        verdict="ELIGIBLE_RECOMMENDATION",
        approval_state="APPROVED",
        analyst="analyst@example.com",
        approver="approver@example.com",
        cleared_gates=["DATA_ROWS", "LIQUIDITY"],
        report_hash="abc123",
        snapshot_hash="def456",
        kevpe_regime="BULLISH",
        kevpe_score=72.5,
        risk_plan={"stop_pct": -4.0, "tp2_pct": 10.0},
        position_value=10000.0,
        quantity=100,
    )
    assert file_path.exists()
    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert data["ticker"] == "AAPL"
    assert data["verdict"] == "ELIGIBLE_RECOMMENDATION"
    assert data["kevpe_regime"] == "BULLISH"
    assert data["position_value"] == 10000.0


def test_write_journal_entry_optional_fields_omitted_when_none(tmp_path):
    file_path = write_journal_entry(
        output_dir=tmp_path,
        ticker="MSFT",
        track="L",
        verdict="RED_SCORE",
        approval_state="BLOCKED",
        analyst="analyst@example.com",
        approver=None,
        cleared_gates=[],
        report_hash="x",
        snapshot_hash="y",
        kevpe_regime=None,
        kevpe_score=None,
        risk_plan={},
        position_value=None,
        quantity=None,
    )
    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert "kevpe_regime" not in data
    assert "kevpe_score" not in data
    assert "position_value" not in data
    assert "quantity" not in data
    assert data["approver"] is None


def test_compute_file_hash_matches_sha256(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("hello world", encoding="utf-8")
    h = compute_file_hash(p)
    assert h == sha256_hex("hello world")
