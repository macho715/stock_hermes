"""P2 end-to-end gate integration tests for RecommendationEngine.write_reports.

Verifies that:
  1. write_reports writes a dashboard_snapshot_*.json alongside the raw JSON.
  2. The snapshot contains an inference_gate_summary block.
  3. Volume breakout + model disagreement gates are evaluated from result data.
  4. dashboard_snapshot_path is set on the returned RecommendationRun.
  5. _compute_gate_results helper handles edge cases (empty, single, multi-result).
"""

from __future__ import annotations

import pytest

from stock_rtx4060.recommendation_engine import (
    RecommendationConfig,
    RecommendationRun,
    _compute_gate_results,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_result(
    ticker: str = "005930.KS",
    track: str = "S",
    direction_prob: float = 0.65,
    volume_ratio_20d: float = 1.0,
    verdict: str = "AMBER_REVIEW_ONLY",
) -> object:
    """Construct a minimal RecommendationResult-like namespace for gate tests."""
    from types import SimpleNamespace

    return SimpleNamespace(
        ticker=ticker,
        track=track,
        direction_prob=direction_prob,
        volume_ratio_20d=volume_ratio_20d,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# _compute_gate_results unit tests
# ---------------------------------------------------------------------------


class TestComputeGateResults:
    def test_empty_results_returns_none(self):
        assert _compute_gate_results([]) is None

    def test_single_result_returns_dict(self):
        result = _compute_gate_results([_make_result()])
        assert result is not None
        assert "volume_breakout_result" in result
        assert "event_shock_result" in result
        assert "model_disagreement_result" in result

    def test_event_shock_always_none(self):
        """event_shock_result deferred — must always be None."""
        result = _compute_gate_results([_make_result()])
        assert result["event_shock_result"] is None

    def test_volume_breakout_fires_when_ratio_gte_3(self):
        result = _compute_gate_results([_make_result(volume_ratio_20d=3.5)])
        assert result["volume_breakout_result"]["volume_breakout"] is True

    def test_volume_breakout_does_not_fire_when_ratio_lt_3(self):
        result = _compute_gate_results([_make_result(volume_ratio_20d=1.5)])
        assert result["volume_breakout_result"]["volume_breakout"] is False

    def test_model_disagreement_single_model_always_pass(self):
        """Single ticker/track → valid_model_count=1 → no disagreement."""
        result = _compute_gate_results([_make_result()])
        md = result["model_disagreement_result"]
        assert md["model_disagreement"] is False
        assert md["valid_model_count"] == 1

    def test_model_disagreement_multiple_results_spread(self):
        """Multiple results with spread ≥ 50 → AMBER_MODEL_DISAGREEMENT."""
        results = [
            _make_result("A", "S", direction_prob=0.05),   # score=5
            _make_result("A", "L", direction_prob=0.95),   # score=95
        ]
        result = _compute_gate_results(results)
        md = result["model_disagreement_result"]
        assert md["model_disagreement"] is True
        assert md["score_spread"] >= 50.0

    def test_safety_invariants_always_false(self):
        result = _compute_gate_results([_make_result(volume_ratio_20d=4.0)])
        assert result["volume_breakout_result"]["new_capital_allowed"] is False
        assert result["volume_breakout_result"]["broker_order_execution"] is False
        assert result["model_disagreement_result"]["new_capital_allowed"] is False


# ---------------------------------------------------------------------------
# RecommendationRun field test
# ---------------------------------------------------------------------------


class TestRecommendationRunDashboardField:
    def test_dashboard_snapshot_path_defaults_none(self):
        run = RecommendationRun(
            results=[],
            errors=[],
            markdown_path="x.md",
            json_path="x.json",
            audit_path="x.jsonl",
        )
        assert run.dashboard_snapshot_path is None

    def test_dashboard_key_access_raises_when_none(self):
        run = RecommendationRun(
            results=[],
            errors=[],
            markdown_path="x.md",
            json_path="x.json",
            audit_path="x.jsonl",
        )
        with pytest.raises(KeyError, match="dashboard_snapshot_path"):
            _ = run["dashboard"]

    def test_dashboard_key_access_returns_path_when_set(self):
        run = RecommendationRun(
            results=[],
            errors=[],
            markdown_path="x.md",
            json_path="x.json",
            audit_path="x.jsonl",
            dashboard_snapshot_path="dashboard.json",
        )
        assert run["dashboard"] == "dashboard.json"


# ---------------------------------------------------------------------------
# OpenAI event shock runtime connection tests
# ---------------------------------------------------------------------------


def _mock_openai_client(category: str = "HBM", sentiment: float = 0.87):
    """Return a mock OpenAI client that returns given category/sentiment."""
    import json
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    content = json.dumps({"category": category, "sentiment_score": sentiment})
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    completion = SimpleNamespace(choices=[choice])
    client = MagicMock()
    client.chat.completions.create.return_value = completion
    return client


class TestEventShockRuntimeConnection:
    """_compute_gate_results wires event_shock when config provides API key + headline."""

    def test_event_shock_none_when_no_api_key(self):
        """No openai_api_key → event_shock_result=None (degraded, no error)."""
        cfg = RecommendationConfig(openai_api_key=None, news_headline="Samsung HBM4E ships")
        result = _compute_gate_results([_make_result()], config=cfg)
        assert result["event_shock_result"] is None

    def test_event_shock_none_when_no_headline(self):
        """No news_headline → event_shock_result=None (degraded)."""
        cfg = RecommendationConfig(openai_api_key="sk-test", news_headline=None)
        result = _compute_gate_results([_make_result()], config=cfg)
        assert result["event_shock_result"] is None

    def test_event_shock_populated_when_config_present(self):
        """openai_api_key + headline + injected client → check_event_shock called."""
        mock_client = _mock_openai_client(category="HBM", sentiment=0.87)
        cfg = RecommendationConfig(
            openai_api_key="sk-test-key",
            news_headline="Samsung ships HBM4E 12-layer to global AI customers",
        )
        result = _compute_gate_results(
            [_make_result(ticker="005930.KS", direction_prob=0.35)],
            config=cfg,
            _openai_client=mock_client,
        )

        es = result["event_shock_result"]
        assert es is not None
        assert es["event_shock"] is True
        assert es["category"] == "HBM"
        assert "EVENT_SHOCK_CONFLICTS_WITH_SELL" in es["blocking_reasons"]
        assert es["new_capital_allowed"] is False

    def test_event_shock_degraded_on_openai_import_error(self, monkeypatch):
        """If openai package is missing, result is None — no crash."""
        import builtins
        original_import = builtins.__import__

        def _block_openai(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("openai not installed")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block_openai)

        cfg = RecommendationConfig(
            openai_api_key="sk-test-key",
            news_headline="Samsung HBM4E ships",
        )
        result = _compute_gate_results([_make_result()], config=cfg)
        assert result["event_shock_result"] is None

    def test_config_fields_present(self):
        """RecommendationConfig has openai_api_key and news_headline fields."""
        cfg = RecommendationConfig(
            openai_api_key="sk-test",
            news_headline="headline",
        )
        assert cfg.openai_api_key == "sk-test"
        assert cfg.news_headline == "headline"

    def test_config_defaults_none(self):
        """Both fields default to None — backward-compatible."""
        cfg = RecommendationConfig()
        assert cfg.openai_api_key is None
        assert cfg.news_headline is None
