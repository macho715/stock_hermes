"""Phase 7: validate Grafana dashboard JSON files have required schema/keys."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "observability" / "grafana" / "dashboards"

REQUIRED_TOP_LEVEL = {"title", "panels", "schemaVersion"}


@pytest.mark.parametrize(
    "filename, expected_metrics",
    [
        (
            "recommendations.json",
            {
                "stock1901_recommendation_latency_ms",
                "stock1901_gate_count_total",
                "stock1901_provider_fetch_ms",
                "stock1901_advisor_calls_total",
            },
        ),
        (
            "data_lake.json",
            {
                "stock1901_data_lake_row_count",
                "stock1901_data_lake_provenance_total",
                "stock1901_corp_actions_total",
            },
        ),
    ],
)
def test_dashboard_has_required_top_level_keys(filename, expected_metrics):
    path = DASHBOARD_DIR / filename
    assert path.exists(), f"missing dashboard file {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))

    missing = REQUIRED_TOP_LEVEL - set(payload.keys())
    assert not missing, f"{filename} missing keys: {missing}"

    assert isinstance(payload["panels"], list)
    assert payload["panels"], f"{filename} has no panels"
    assert isinstance(payload["schemaVersion"], int)
    assert payload["schemaVersion"] >= 30  # Grafana 9+ schema floor

    # Collect every PromQL/expr string and assert each metric appears at least once.
    panel_text = json.dumps(payload)
    for metric in expected_metrics:
        assert metric in panel_text, f"{filename} should reference metric '{metric}'"


def test_dashboards_are_unique_uids():
    uids: list[str] = []
    for path in DASHBOARD_DIR.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        uid = payload.get("uid")
        assert uid, f"{path.name} missing uid"
        uids.append(uid)
    assert len(uids) == len(set(uids)), f"duplicate Grafana UIDs detected: {uids}"
