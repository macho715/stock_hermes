"""Phase 7: tests for flows.research_weekly — promotion gate semantics."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flows import research_weekly  # noqa: E402


def test_research_weekly_flow_runs_three_phases(monkeypatch):
    calls: list[str] = []

    def _mining(universe, *, cycles=1, budget_usd=1.0):
        calls.append("mining")
        return {"new_factor_files": [], "count": 0}

    def _hpo(universe, *, n_trials=10):
        calls.append("hpo")
        return {"best_value": 0.20, "best_params": {"learning_rate": 0.05}, "skipped": False}

    def _gate(summary, *, model_name="direction_v1", threshold=0.05):
        calls.append("gate")
        return {"promoted": False, "delta": 0.0}

    monkeypatch.setattr(research_weekly, "factor_mining_task", _mining)
    monkeypatch.setattr(research_weekly, "hpo_task", _hpo)
    monkeypatch.setattr(research_weekly, "promotion_gate_task", _gate)

    out = research_weekly.research_weekly_flow(universe=["AAPL"])

    assert calls == ["mining", "hpo", "gate"]
    assert out["universe"] == ["AAPL"]
    assert out["mining"]["count"] == 0
    assert out["hpo"]["best_value"] == pytest.approx(0.20)
    assert out["promotion"] == {"promoted": False, "delta": 0.0}


def test_promotion_gate_skips_when_hpo_skipped():
    out = research_weekly.promotion_gate_task({"skipped": True})
    assert out["promoted"] is False
    assert out["reason"] == "hpo_skipped"


def test_promotion_gate_skips_on_nan_value():
    out = research_weekly.promotion_gate_task({"skipped": False, "best_value": float("nan")})
    assert out["promoted"] is False
    assert out["reason"] == "nan_best_value"


def test_promotion_gate_promotes_when_no_baseline(monkeypatch):
    """No baseline -> infinite delta -> always promote."""
    promote_calls: list[tuple] = []

    def _fake_promote(*, name, version, stage):
        promote_calls.append((name, version, stage))

    monkeypatch.setattr(research_weekly, "_current_production_score", lambda _: None)
    monkeypatch.setattr(research_weekly, "_latest_candidate_version", lambda _: 1)
    monkeypatch.setattr("stock_rtx4060.ml.registry.promote", _fake_promote)

    out = research_weekly.promotion_gate_task({"skipped": False, "best_value": 0.18})
    assert out["promoted"] is True
    assert promote_calls == [("direction_v1", 1, "Production")]
    assert out["version"] == 1


def test_promotion_gate_skips_when_no_candidate_version(monkeypatch):
    """No registered version -> cannot promote even with cold-start."""
    monkeypatch.setattr(research_weekly, "_current_production_score", lambda _: None)
    monkeypatch.setattr(research_weekly, "_latest_candidate_version", lambda _: None)
    out = research_weekly.promotion_gate_task({"skipped": False, "best_value": 0.18})
    assert out["promoted"] is False
    assert out["reason"] == "no_candidate_version"


def test_promotion_gate_does_not_promote_when_delta_below_threshold(monkeypatch):
    # Brier loss is minimised: baseline=0.20, new=0.195 → delta = 0.025 (2.5%) < 5% threshold
    monkeypatch.setattr(research_weekly, "_current_production_score", lambda _: 0.20)
    promote_calls: list[tuple] = []
    monkeypatch.setattr(
        "stock_rtx4060.ml.registry.promote",
        lambda **kw: promote_calls.append(kw),
    )

    out = research_weekly.promotion_gate_task({"skipped": False, "best_value": 0.195})
    assert out["promoted"] is False
    assert out["delta"] == pytest.approx(0.025)
    assert promote_calls == []


def test_promotion_gate_promotes_when_delta_exceeds_threshold(monkeypatch):
    # baseline=0.20, new=0.18 → delta = 0.10 (10%) > 5% threshold
    monkeypatch.setattr(research_weekly, "_current_production_score", lambda _: 0.20)
    monkeypatch.setattr(research_weekly, "_latest_candidate_version", lambda _: 7)
    promote_calls: list[dict] = []
    monkeypatch.setattr(
        "stock_rtx4060.ml.registry.promote",
        lambda **kw: promote_calls.append(kw),
    )

    out = research_weekly.promotion_gate_task({"skipped": False, "best_value": 0.18})
    assert out["promoted"] is True
    assert out["delta"] == pytest.approx(0.10)
    assert len(promote_calls) == 1
    assert promote_calls[0]["stage"] == "Production"
    assert promote_calls[0]["version"] == 7  # uses latest, not hardcoded 1


def test_promotion_gate_swallows_promote_errors(monkeypatch):
    monkeypatch.setattr(research_weekly, "_current_production_score", lambda _: 0.20)
    monkeypatch.setattr(research_weekly, "_latest_candidate_version", lambda _: 1)

    def _boom(**_):
        raise RuntimeError("mlflow down")

    monkeypatch.setattr("stock_rtx4060.ml.registry.promote", _boom)
    out = research_weekly.promotion_gate_task({"skipped": False, "best_value": 0.18})
    assert out["promoted"] is False
    assert "promote_error" in out["reason"]


def test_research_weekly_cron_constants():
    assert research_weekly.RESEARCH_FLOW_CRON == "0 2 * * 6"
    assert research_weekly.PROMOTION_DELTA_THRESHOLD == 0.05
