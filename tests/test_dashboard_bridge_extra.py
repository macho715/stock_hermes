"""Extra tests for dashboard_bridge.py — covers uncovered lines.

Missing lines targeted:
  45-46, 48, 55, 59, 68, 142->145, 151, 152->155, 160,
  177-178, 179->182, 186-188, 192-196, 203-206, 211
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from stock_rtx4060.dashboard_bridge import (
    DashboardBridgeError,
    _copy_file,
    _find_nearby_file,
    _normalize_result,
    _resolve_existing_path,
    _truncate_advisor_rationale,
    build_dashboard_snapshot,
    export_dashboard_public_assets,
    load_recommendation_payload,
    write_dashboard_snapshot,
)


# ---------------------------------------------------------------------------
# Shared payload builder
# ---------------------------------------------------------------------------

def _base_result() -> dict:
    return {
        "ticker": "AAPL",
        "track": "S",
        "verdict": "GREEN",
        "recommendation_rank_score": 80.0,
        "direction_prob": 0.62,
        "expected_value_pct": 2.5,
        "entry": 185.0,
        "stop": 177.0,
        "tp2": 203.5,
        "risk_reward": 2.4,
        "screening_output_only": True,
        "validations": [],
    }


def _base_payload() -> dict:
    return {
        "config": {"universe": ["AAPL"], "track": "S"},
        "results": [_base_result()],
    }


# ---------------------------------------------------------------------------
# load_recommendation_payload — invalid JSON (lines 45-46)
# ---------------------------------------------------------------------------

def test_load_invalid_json_raises(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(DashboardBridgeError, match="invalid recommendation JSON"):
        load_recommendation_payload(bad_file)


# ---------------------------------------------------------------------------
# load_recommendation_payload — top-level not a dict (line 48)
# ---------------------------------------------------------------------------

def test_load_non_dict_json_raises(tmp_path):
    bad_file = tmp_path / "list.json"
    bad_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(DashboardBridgeError, match="top-level object"):
        load_recommendation_payload(bad_file)


# ---------------------------------------------------------------------------
# build_dashboard_snapshot — results not a list (line 55)
# ---------------------------------------------------------------------------

def test_build_snapshot_non_list_results_raises():
    payload = {"results": "not a list"}
    with pytest.raises(DashboardBridgeError, match="list field: results"):
        build_dashboard_snapshot(payload)


# ---------------------------------------------------------------------------
# build_dashboard_snapshot — non-dict config falls back to {} (line 59)
# ---------------------------------------------------------------------------

def test_build_snapshot_non_dict_config_uses_empty():
    payload = _base_payload()
    payload["config"] = "not-a-dict"
    # Should not raise; config fields default to None
    snapshot = build_dashboard_snapshot(payload)
    assert snapshot["config"]["universe"] is None


# ---------------------------------------------------------------------------
# build_dashboard_snapshot — meta block present (line 68)
# ---------------------------------------------------------------------------

def test_build_snapshot_with_meta_block():
    payload = _base_payload()
    payload["meta"] = {"risk_attribution": {"sector": 0.3}, "custom_field": "value"}
    snapshot = build_dashboard_snapshot(payload)
    assert snapshot["meta"] is not None
    assert snapshot["meta"]["risk_attribution"] == {"sector": 0.3}


def test_build_snapshot_meta_is_not_dict_gives_none():
    payload = _base_payload()
    payload["meta"] = "bad_meta"
    snapshot = build_dashboard_snapshot(payload)
    assert snapshot["meta"] is None


# ---------------------------------------------------------------------------
# export_dashboard_public_assets — audit log resolved from payload path
# (lines 142->145)
# ---------------------------------------------------------------------------

def test_export_resolves_audit_log_from_relative_path(tmp_path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    audit = reports_dir / "audit_log.jsonl"
    audit.write_text('{"event_type":"test"}\n', encoding="utf-8")

    payload = _base_payload()
    payload["audit_log_path"] = str(audit)

    source = reports_dir / "recommendations.json"
    source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    snapshot_path = reports_dir / "dashboard_snapshot.json"
    write_dashboard_snapshot(source, snapshot_path)

    public_dir = tmp_path / "public"
    exported = export_dashboard_public_assets(source, snapshot_path, public_dir)
    assert exported["audit_log"] is not None
    assert (public_dir / "audit_log.jsonl").exists()


# ---------------------------------------------------------------------------
# export_dashboard_public_assets — approval journal found via find_nearby_file
# (line 151)
# ---------------------------------------------------------------------------

def test_export_finds_approval_journal_nearby(tmp_path):
    reports_dir = tmp_path / "reports" / "sub"
    reports_dir.mkdir(parents=True)

    payload = _base_payload()
    source = reports_dir / "recommendations.json"
    source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # Place approval_journal_template.csv in parent dir (nearby)
    approval = reports_dir.parent / "approval_journal_template.csv"
    approval.write_text("ticker,action\nAAPL,REVIEW\n", encoding="utf-8")

    snapshot_path = reports_dir / "dashboard_snapshot.json"
    write_dashboard_snapshot(source, snapshot_path)

    public_dir = tmp_path / "public"
    exported = export_dashboard_public_assets(source, snapshot_path, public_dir)
    assert exported["approval_journal"] is not None


# ---------------------------------------------------------------------------
# export_dashboard_public_assets — no audit log, no approval (lines 152->155)
# ---------------------------------------------------------------------------

def test_export_no_audit_no_approval(tmp_path):
    reports_dir = tmp_path / "reports2"
    reports_dir.mkdir()
    payload = _base_payload()
    source = reports_dir / "recommendations.json"
    source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    snapshot_path = reports_dir / "dashboard_snapshot.json"
    write_dashboard_snapshot(source, snapshot_path)

    public_dir = tmp_path / "public2"
    exported = export_dashboard_public_assets(source, snapshot_path, public_dir)

    assert exported["audit_log"] is None
    assert exported["approval_journal"] is None
    assert exported["dashboard_snapshot"] is not None


# ---------------------------------------------------------------------------
# _copy_file — source missing raises (line 160)
# ---------------------------------------------------------------------------

def test_copy_file_missing_source_raises(tmp_path):
    missing = tmp_path / "nonexistent.json"
    dest = tmp_path / "out.json"
    with pytest.raises(DashboardBridgeError, match="cannot export missing file"):
        _copy_file(missing, dest)


# ---------------------------------------------------------------------------
# _resolve_existing_path — value None / empty + fallback not found (lines 177-188)
# ---------------------------------------------------------------------------

def test_resolve_existing_path_none_value_no_fallback():
    result = _resolve_existing_path(
        None,
        base_dirs=[Path("/nonexistent")],
        fallback_name=None,
    )
    assert result is None


def test_resolve_existing_path_none_value_with_fallback_not_found(tmp_path):
    result = _resolve_existing_path(
        None,
        base_dirs=[tmp_path],
        fallback_name="missing_file.csv",
    )
    assert result is None


def test_resolve_existing_path_empty_string_no_fallback():
    result = _resolve_existing_path(
        "   ",  # empty/whitespace string
        base_dirs=[Path("/nonexistent")],
        fallback_name=None,
    )
    assert result is None


def test_resolve_existing_path_relative_value_found(tmp_path):
    target = tmp_path / "data" / "audit_log.jsonl"
    target.parent.mkdir(parents=True)
    target.write_text("data", encoding="utf-8")

    result = _resolve_existing_path(
        "audit_log.jsonl",
        base_dirs=[tmp_path / "data"],
        fallback_name=None,
    )
    assert result == target


def test_resolve_existing_path_absolute_value_found(tmp_path):
    target = tmp_path / "absolute_file.jsonl"
    target.write_text("data", encoding="utf-8")

    result = _resolve_existing_path(
        str(target),
        base_dirs=[],
        fallback_name=None,
    )
    assert result == target


def test_resolve_existing_path_oserror_continues(tmp_path, monkeypatch):
    """OSError during exists() check is caught and skipped."""
    target = tmp_path / "trigger_oserror.jsonl"
    target.write_text("data", encoding="utf-8")

    original_exists = Path.exists

    def patched_exists(self: Path) -> bool:
        if "trigger_oserror" in str(self):
            raise OSError("permission denied")
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", patched_exists)
    result = _resolve_existing_path(
        str(target),
        base_dirs=[],
        fallback_name=None,
    )
    assert result is None


# ---------------------------------------------------------------------------
# _find_nearby_file (lines 192-196)
# ---------------------------------------------------------------------------

def test_find_nearby_file_found_in_parent(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    source_path = subdir / "source.json"
    source_path.write_text("{}", encoding="utf-8")
    target = tmp_path / "approval_journal_template.csv"
    target.write_text("header\n", encoding="utf-8")

    result = _find_nearby_file(source_path, "approval_journal_template.csv")
    assert result == target


def test_find_nearby_file_not_found_returns_none(tmp_path):
    source_path = tmp_path / "source.json"
    source_path.write_text("{}", encoding="utf-8")

    result = _find_nearby_file(source_path, "nonexistent.csv")
    assert result is None


# ---------------------------------------------------------------------------
# _truncate_advisor_rationale (lines 203-206)
# ---------------------------------------------------------------------------

def test_truncate_advisor_rationale_none():
    assert _truncate_advisor_rationale(None) is None


def test_truncate_advisor_rationale_short():
    text = "short text"
    assert _truncate_advisor_rationale(text) == text


def test_truncate_advisor_rationale_long():
    text = "x" * 300
    result = _truncate_advisor_rationale(text)
    assert len(result) == 240
    assert result.endswith("...")


def test_truncate_advisor_rationale_exactly_240():
    text = "x" * 240
    result = _truncate_advisor_rationale(text)
    assert result == text
    assert len(result) == 240


# ---------------------------------------------------------------------------
# _normalize_result — result not a dict (line 211)
# ---------------------------------------------------------------------------

def test_normalize_result_non_dict_raises():
    with pytest.raises(DashboardBridgeError, match="must be an object"):
        _normalize_result("not a dict", rank=1)


# ---------------------------------------------------------------------------
# build_dashboard_snapshot — source_json_path=None (line 77)
# ---------------------------------------------------------------------------

def test_build_snapshot_no_source_json_path():
    snapshot = build_dashboard_snapshot(_base_payload(), source_json_path=None)
    assert snapshot["source_recommendation_json"] is None


# ---------------------------------------------------------------------------
# write_dashboard_snapshot — default output path (line 111)
# ---------------------------------------------------------------------------

def test_write_snapshot_default_output_path(tmp_path):
    source = tmp_path / "recommendations.json"
    source.write_text(json.dumps(_base_payload()), encoding="utf-8")

    path = write_dashboard_snapshot(source)  # no output arg

    expected = tmp_path / "dashboard_snapshot.json"
    assert path == expected
    assert expected.exists()
