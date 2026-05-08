"""Phase 7: smoke tests for flows.daily_krx — DAG ordering and dry_run behaviour."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flows import daily_krx  # noqa: E402


@pytest.fixture(autouse=True)
def _stub_universe(monkeypatch):
    monkeypatch.setenv("STOCK1901_KRX_UNIVERSE", "005930,000660")
    yield


def test_daily_krx_flow_executes_eight_steps_in_order(monkeypatch):
    calls: list[str] = []

    def make_recorder(name, payload=None):
        def _f(*a, **kw):
            calls.append(name)
            return payload if payload is not None else {"ok": True, "name": name}

        return _f

    monkeypatch.setattr(daily_krx, "ingest_kis_task", make_recorder("ingest"))
    monkeypatch.setattr(daily_krx, "corp_actions_adjust_task", make_recorder("corp_actions"))
    monkeypatch.setattr(daily_krx, "factor_compute_task", make_recorder("factors"))
    monkeypatch.setattr(daily_krx, "model_predict_task", make_recorder("model"))
    monkeypatch.setattr(daily_krx, "portfolio_optimize_task", make_recorder("portfolio"))
    monkeypatch.setattr(
        daily_krx,
        "recommend_task",
        make_recorder("recommend", payload={"result_count": 0, "verdicts": []}),
    )
    monkeypatch.setattr(daily_krx, "snapshot_dashboard_task", make_recorder("dashboard"))
    monkeypatch.setattr(daily_krx, "alert_task", make_recorder("alert", payload={"dispatched": 1}))

    out = daily_krx.daily_krx_flow(dry_run=True)

    expected = ["ingest", "corp_actions", "factors", "model", "portfolio", "recommend", "dashboard", "alert"]
    assert calls == expected
    for stage in ("ingest", "corp_actions", "factors", "model", "portfolio", "recommend", "dashboard", "alert"):
        assert stage in out


def test_daily_krx_flow_dry_run_passes_flag_to_alert(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(daily_krx, "ingest_kis_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "corp_actions_adjust_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "factor_compute_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "model_predict_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "portfolio_optimize_task", lambda *a, **kw: {})
    monkeypatch.setattr(
        daily_krx,
        "recommend_task",
        lambda universe, *, dry_run=False: {"result_count": 0, "dry_run": dry_run},
    )
    monkeypatch.setattr(daily_krx, "snapshot_dashboard_task", lambda *a, **kw: {})

    def _alert(summary, *, dry_run=False):
        captured["dry_run"] = dry_run
        captured["summary"] = summary
        return {"dispatched": 1}

    monkeypatch.setattr(daily_krx, "alert_task", _alert)

    out = daily_krx.daily_krx_flow(dry_run=True)
    assert captured["dry_run"] is True
    assert out["dry_run"] is True


def test_daily_krx_flow_propagates_failure_via_slack(monkeypatch):
    monkeypatch.setattr(daily_krx, "ingest_kis_task", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    notified: list[str] = []
    monkeypatch.setattr(daily_krx, "slack_on_failure", lambda msg, **kw: notified.append(msg))

    with pytest.raises(RuntimeError, match="boom"):
        daily_krx.daily_krx_flow(dry_run=True)
    assert notified  # slack notifier was invoked
    assert "daily_krx_flow failed" in notified[0]


def test_daily_krx_cron_constants():
    assert daily_krx.KRX_FLOW_CRON == "30 16 * * 1-5"
    assert daily_krx.KRX_FLOW_TIMEZONE == "Asia/Seoul"
