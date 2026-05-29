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
    monkeypatch.setattr(daily_krx, "forward_tracking_task", make_recorder("forward_tracking", payload={"status": "disabled"}))  # [E3]
    monkeypatch.setattr(daily_krx, "alert_task", make_recorder("alert", payload={"dispatched": 1}))

    out = daily_krx.daily_krx_flow(dry_run=True)

    expected = ["ingest", "corp_actions", "factors", "model", "portfolio", "recommend", "dashboard", "forward_tracking", "alert"]
    assert calls == expected
    for stage in expected:
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
    monkeypatch.setattr(daily_krx, "forward_tracking_task", lambda *a, **kw: {"status": "disabled"})  # [E3]

    def _alert(summary, *, dry_run=False, forward_tracking_status=None, **kw):
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


# ---------------------------------------------------------------------------
# E3 (Wave 3): forward_tracking_task + FORWARD_TRACKING_ENABLED flag
# ---------------------------------------------------------------------------


def test_forward_tracking_task_disabled_when_flag_false(monkeypatch):
    """FORWARD_TRACKING_ENABLED=false → status=disabled immediately."""
    monkeypatch.setattr(daily_krx, "_FORWARD_TRACKING_ENABLED", False)
    result = daily_krx.forward_tracking_task(ticker="005930.KS", evidence_dir="/tmp/e3_test")
    assert result["status"] == "disabled"
    assert "FORWARD_TRACKING_ENABLED=false" in result.get("reason", "")


def test_forward_tracking_task_enabled_calls_recorder(monkeypatch, tmp_path):
    """FORWARD_TRACKING_ENABLED=true → AutoForwardRecorder.record_today() called."""
    monkeypatch.setattr(daily_krx, "_FORWARD_TRACKING_ENABLED", True)
    captured: dict = {}

    import stock_rtx4060.live_review.auto_forward_recorder as afr_mod

    class _FakeRecorder:
        def __init__(self, *, symbol: str, evidence_dir: str, **kw) -> None:
            captured["symbol"] = symbol

        def record_today(self) -> dict:
            return {"status": "SKIPPED_NON_TRADING_DAY", "date": "2026-05-29",
                    "symbol": "005930.KS", "row_count": 0, "reason": None}

    monkeypatch.setattr(afr_mod, "AutoForwardRecorder", _FakeRecorder)
    result = daily_krx.forward_tracking_task(ticker="005930.KS", evidence_dir=str(tmp_path))
    assert result["status"] == "SKIPPED_NON_TRADING_DAY"
    assert captured["symbol"] == "005930.KS"


def test_daily_krx_flow_includes_forward_tracking(monkeypatch):
    """daily_krx_flow result dict contains forward_tracking key."""
    monkeypatch.setattr(daily_krx, "ingest_kis_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "corp_actions_adjust_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "factor_compute_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "model_predict_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "portfolio_optimize_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "recommend_task", lambda *a, **kw: {"result_count": 0})
    monkeypatch.setattr(daily_krx, "snapshot_dashboard_task", lambda *a, **kw: {})
    monkeypatch.setattr(daily_krx, "forward_tracking_task", lambda *a, **kw: {"status": "disabled"})
    monkeypatch.setattr(daily_krx, "alert_task", lambda *a, **kw: {"dispatched": 0})

    out = daily_krx.daily_krx_flow(dry_run=True)
    assert "forward_tracking" in out
    assert out["forward_tracking"]["status"] == "disabled"


def test_alert_task_message_includes_forward_tracking_status(monkeypatch):
    """alert_task message includes 'forward_tracking=...' when status provided."""
    dispatched_msgs: list[str] = []

    import stock_rtx4060.alert_engine as ae

    monkeypatch.setattr(ae, "dispatch", lambda alerts: (
        [dispatched_msgs.append(a.message) for a in alerts] or {"dispatched": len(alerts)}
    ))

    daily_krx.alert_task(
        {"result_count": 2},
        dry_run=False,
        forward_tracking_status="RECORDED",
    )
    assert any("forward_tracking=RECORDED" in m for m in dispatched_msgs)


def test_record_today_returns_serializable(tmp_path):
    """AutoForwardRecorder.record_today() returns JSON-serialisable dict."""
    import json

    from stock_rtx4060.live_review.auto_forward_recorder import AutoForwardRecorder

    rec = AutoForwardRecorder(symbol="005930.KS", evidence_dir=str(tmp_path))
    result = rec.record_today()
    # Must be JSON-serialisable (Prefect requirement)
    json.dumps(result)
    assert result["symbol"] == "005930.KS"
    assert result["status"] in (
        "RECORDED", "SKIPPED_NON_TRADING_DAY", "SKIPPED_BEFORE_EOD",
        "SKIPPED_DUPLICATE_DATE", "ALREADY_COMPLETED", "COMPLETE_REVIEW_REQUIRED", "error",
    )
