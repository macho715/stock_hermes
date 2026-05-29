"""Tests for the RD-Agent provenance / audit logging (provenance.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stock_rtx4060.factors.rd_agent.provenance import (
    RDAgentAuditEvent,
    _timestamp,
)


class TestTimestamp:
    def test_timestamp_is_iso8601_with_z(self) -> None:
        ts = _timestamp()
        # Should end with 'Z' (UTC)
        assert ts.endswith("Z")
        # Should be parseable as ISO format
        assert "T" in ts  # contains date-time separator


class TestRDAgentAuditEvent:
    def test_event_dataclass_creation(self) -> None:
        event = RDAgentAuditEvent(
            ts="2026-05-29T02:00:00.000Z",
            session_id="rd_20260529_abc123",
            event="cycle_complete",
            cycles_run=2,
            budget_spent_usd=3.42,
            budget_limit_usd=10.0,
            new_factor_files=["discovered/rd_20260529_abc123/rd_mom_vol.py"],
            validated_pass=1,
            validated_fail=1,
            approved_by="",
        )
        assert event.ts == "2026-05-29T02:00:00.000Z"
        assert event.session_id == "rd_20260529_abc123"
        assert event.event == "cycle_complete"
        assert event.cycles_run == 2
        assert event.budget_spent_usd == pytest.approx(3.42)
        assert event.budget_limit_usd == 10.0
        assert len(event.new_factor_files) == 1

    def test_event_default_values(self) -> None:
        event = RDAgentAuditEvent(
            ts="2026-05-29T02:00:00.000Z",
            session_id="rd_20260529_abc123",
            event="factor_validated",
            cycles_run=1,
            budget_spent_usd=1.0,
            budget_limit_usd=10.0,
        )
        assert event.new_factor_files == []
        assert event.validated_pass == 0
        assert event.validated_fail == 0
        assert event.approved_by == ""


class TestAuditLogFormat:
    def test_provenance_audit_log_format(self, tmp_path: Path) -> None:
        """JSONL format with required fields: ts, session_id, event, cycles_run, budget_spent_usd, budget_limit_usd."""
        import stock_rtx4060.factors.rd_agent.provenance as provenance_module

        # Override log path to tmp
        audit_root = tmp_path / "audit_log"
        audit_root.mkdir(parents=True, exist_ok=True)
        log_path = audit_root / "rd_agent.jsonl"

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(provenance_module, "_AUDIT_ROOT", audit_root)
            mp.setattr(provenance_module, "_LOG_PATH", log_path)

            # Write an event
            provenance_module.log_cycle_complete(
                session_id="rd_20260529_abc123",
                cycles_run=2,
                budget_spent_usd=3.42,
                budget_limit_usd=10.0,
                new_factor_files=["discovered/rd_20260529_abc123/rd_mom_vol.py"],
                validated_pass=1,
                validated_fail=1,
                approved_by="operator",
            )

        # Read back and validate JSONL format
        assert log_path.exists(), "audit log file should exist"
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1

        record = json.loads(lines[0])

        # Required fields from E1 schema
        assert "ts" in record, "ts field required"
        assert "session_id" in record, "session_id field required"
        assert "event" in record, "event field required"
        assert "cycles_run" in record, "cycles_run field required"
        assert "budget_spent_usd" in record, "budget_spent_usd field required"
        assert "budget_limit_usd" in record, "budget_limit_usd field required"
        assert "new_factor_files" in record, "new_factor_files field required"

        # Validate types
        assert isinstance(record["ts"], str)
        assert isinstance(record["session_id"], str)
        assert isinstance(record["event"], str)
        assert isinstance(record["cycles_run"], int)
        assert isinstance(record["budget_spent_usd"], (int, float))
        assert isinstance(record["budget_limit_usd"], (int, float))
        assert isinstance(record["new_factor_files"], list)

    def test_jsonl_is_newline_delimited(self, tmp_path: Path) -> None:
        """Multiple events are on separate lines (JSONL, not JSON array)."""
        import stock_rtx4060.factors.rd_agent.provenance as provenance_module

        audit_root = tmp_path / "audit_log"
        audit_root.mkdir(parents=True, exist_ok=True)
        log_path = audit_root / "rd_agent.jsonl"

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(provenance_module, "_AUDIT_ROOT", audit_root)
            mp.setattr(provenance_module, "_LOG_PATH", log_path)

            # Write 3 events
            for i in range(3):
                provenance_module.log_cycle_complete(
                    session_id=f"rd_20260529_session{i}",
                    cycles_run=1,
                    budget_spent_usd=1.0 * (i + 1),
                    budget_limit_usd=10.0,
                    new_factor_files=[],
                    validated_pass=0,
                    validated_fail=0,
                )

        content = log_path.read_text()
        lines = [line_text for line_text in content.strip().split("\n") if line_text]
        assert len(lines) == 3

        # Each line is a valid JSON object
        for line in lines:
            record = json.loads(line)
            assert "ts" in record

    def test_log_budget_exceeded_event(self, tmp_path: Path) -> None:
        """budget_exceeded event written with correct event type."""
        import stock_rtx4060.factors.rd_agent.provenance as provenance_module

        audit_root = tmp_path / "audit_log"
        audit_root.mkdir(parents=True, exist_ok=True)
        log_path = audit_root / "rd_agent.jsonl"

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(provenance_module, "_AUDIT_ROOT", audit_root)
            mp.setattr(provenance_module, "_LOG_PATH", log_path)

            provenance_module.log_budget_exceeded(
                session_id="rd_20260529_overbudget",
                cycles_run=2,
                budget_spent_usd=12.50,
                budget_limit_usd=10.0,
                new_factor_files=["discovered/rd_20260529_overbudget/rd_factor.py"],
                validated_pass=0,
                validated_fail=2,
            )

        record = json.loads(log_path.read_text().strip())
        assert record["event"] == "budget_exceeded"
        assert record["budget_spent_usd"] == 12.50
        assert record["budget_limit_usd"] == 10.0

    def test_log_factor_approved_event(self, tmp_path: Path) -> None:
        """factor_approved event includes approved_by field."""
        import stock_rtx4060.factors.rd_agent.provenance as provenance_module

        audit_root = tmp_path / "audit_log"
        audit_root.mkdir(parents=True, exist_ok=True)
        log_path = audit_root / "rd_agent.jsonl"

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(provenance_module, "_AUDIT_ROOT", audit_root)
            mp.setattr(provenance_module, "_LOG_PATH", log_path)

            provenance_module.log_factor_approved(
                session_id="rd_20260529_approved",
                cycles_run=2,
                budget_spent_usd=3.42,
                budget_limit_usd=10.0,
                new_factor_files=["rd_momentum", "rd_reversal"],
                approved_by="operator",
            )

        record = json.loads(log_path.read_text().strip())
        assert record["event"] == "factor_approved"
        assert record["approved_by"] == "operator"
        assert record["new_factor_files"] == ["rd_momentum", "rd_reversal"]
