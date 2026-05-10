from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from stock_rtx4060 import recommendation_engine as recommendation_module
from stock_rtx4060.backtester import Backtester
from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot
from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig
from stock_rtx4060.feature_engine import TechnicalIndicators, make_synthetic_ohlcv
from stock_rtx4060.kevpe_adapter import KevpeAdapterResult
from stock_rtx4060.recommendation_engine import RecommendationConfig, RecommendationEngine
from stock_rtx4060.risk_rules import evaluate_track_s_candidate, position_size_by_risk


def test_feature_engine_generates_targets():
    df = make_synthetic_ohlcv(360)
    features = TechnicalIndicators(df).build_all(horizon=5)
    assert len(features) > 100
    assert "target_direction" in features
    assert set(features["target_direction"].unique()).issubset({0, 1})
    assert features.isna().sum().sum() == 0


def test_model_fallback_and_backtester_run():
    df = make_synthetic_ohlcv(360)
    features = TechnicalIndicators(df).build_all(horizon=5)
    model = EnsemblePredictor(ModelConfig(n_splits=3, lite=True))
    metrics = model.fit(features)
    assert metrics
    proba = model.predict_proba(features.drop(columns=["target_direction", "target_return"]))
    assert len(proba) == len(features)
    result = Backtester().run(df["Close"].reindex(features.index).ffill(), proba)
    assert result.final_capital > 0
    assert result.max_drawdown_pct >= 0
    assert "sortino_ratio" in result
    assert "profit_factor" in result
    assert "monthly_stop_triggered" in result


def test_model_uses_gap_and_keeps_oof_partial():
    df = make_synthetic_ohlcv(460)
    features = TechnicalIndicators(df).build_all(horizon=10)
    model = EnsemblePredictor(ModelConfig(horizon=10, n_splits=3, gap=10, model_kind="logistic", lite=True))
    metrics = model.fit(features)
    assert metrics
    assert all(item["gap"] == 10 for item in metrics)
    assert model.oof_probabilities_ is not None
    coverage = float(model.oof_probabilities_.notna().mean())
    assert 0.2 < coverage < 1.0


def test_track_s_risk_gate_and_position_sizing():
    qty, position_value, open_risk = position_size_by_risk(100, 96, 20_000, 0.0075)
    assert qty == 37
    assert position_value == 3700
    assert open_risk == 148
    df = make_synthetic_ohlcv(360)
    features = TechnicalIndicators(df).build_all(horizon=5)
    candidate = evaluate_track_s_candidate("TEST", features.iloc[-1], float(df["Close"].iloc[-1]))
    assert candidate.quantity >= 0
    assert candidate.gate.value in {"GREEN", "AMBER", "RED", "ZERO"}


def test_recommendation_engine_synthetic_run(tmp_path):
    config = RecommendationConfig(
        universe=["SYNTH-A", "SYNTH-B"],
        track="BOTH",
        top_n=3,
        synthetic=True,
        output_dir=str(tmp_path),
    )
    engine = RecommendationEngine(config)
    results = engine.run()
    paths = engine.write_reports(results)
    assert results
    assert all(result.screening_output_only for result in results)
    assert Path(paths["markdown"]).exists()
    assert Path(paths["json"]).exists()
    assert Path(paths["audit"]).exists()
    payload = __import__("json").loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert payload["provider_summary"]["status"] in {"PASS", "AMBER"}
    assert "synthetic" in payload["provider_summary"]["providers_used"]
    assert payload["backtest_honesty_summary"]["status"] in {"PASS", "AMBER", "FAIL"}
    assert payload["backtest_honesty_summary"]["result_count"] == len(results)
    assert all(result["backtest_honesty"]["checks"] for result in payload["results"])
    assert any(
        event.get("event_type") == "backtest_honesty_summary"
        for event in [__import__("json").loads(line) for line in Path(paths["audit"]).read_text(encoding="utf-8").splitlines() if line.strip()]
    )


def test_recommendation_engine_reuses_ohlcv_for_same_ticker(monkeypatch, tmp_path):
    calls = []
    frame = make_synthetic_ohlcv(760)

    def fake_load_ohlcv_result(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(
            frame=frame,
            source="synthetic_demo_data",
            provider_used="synthetic",
            endpoint=None,
            fallback_reason=None,
            metadata={
                "provider_validation_status": "PASS",
                "provider_used": "synthetic",
                "row_count": len(frame),
                "last_date": str(frame.index.max().date()),
                "freshness_days": 0,
            },
        )

    monkeypatch.setattr(recommendation_module, "load_ohlcv_result", fake_load_ohlcv_result)
    config = RecommendationConfig(
        universe=["CACHE-A"],
        track="BOTH",
        top_n=2,
        synthetic=True,
        output_dir=str(tmp_path),
        model_kind="logistic",
    )
    engine = RecommendationEngine(config)

    results = engine.run()

    assert len(results) == 2
    assert len(calls) == 1


def test_recommendation_engine_loads_kevpe_events_and_exports_dashboard_fields(monkeypatch, tmp_path):
    frame = make_synthetic_ohlcv(760)

    def fake_load_ohlcv_result(*args, **kwargs):
        return SimpleNamespace(
            frame=frame,
            source="synthetic_demo_data",
            provider_used="synthetic",
            endpoint=None,
            fallback_reason=None,
            metadata={"provider_validation_status": "PASS", "provider_used": "synthetic", "row_count": len(frame)},
        )

    class FakeKevpeAdapter:
        def get_signal_for_ticker(self, ohlcv, events, as_of=None):
            assert len(events) == 1
            assert events[0]["headline"] == "FOMC rate decision surprises semiconductor market"
            return KevpeAdapterResult(
                regime="RED",
                score=0.82,
                expected_return_pct=-3.5,
                ci_low_pct=-6.0,
                ci_high_pct=-1.0,
                reason="event risk overlay",
                confidence="medium",
                is_available=True,
            )

    events_path = tmp_path / "kevpe_events.json"
    events_path.write_text(
        """
        [
          {
            "ticker": "CACHE-A",
            "date": "2026-05-01",
            "headline": "FOMC rate decision surprises semiconductor market",
            "tone": -6,
            "volume": 120,
            "source_diversity": 10,
            "topics": ["central_bank", "semiconductor_ai"]
          },
          {
            "ticker": "OTHER",
            "date": "2026-05-01",
            "headline": "unrelated ticker event"
          }
        ]
        """,
        encoding="utf-8",
    )

    monkeypatch.setattr(recommendation_module, "load_ohlcv_result", fake_load_ohlcv_result)
    monkeypatch.setattr(recommendation_module, "get_kevpe_adapter", lambda: FakeKevpeAdapter())

    config = RecommendationConfig(
        universe=["CACHE-A"],
        track="S",
        top_n=1,
        synthetic=True,
        output_dir=str(tmp_path / "reports"),
        model_kind="logistic",
        kevpe_events=str(events_path),
    )
    engine = RecommendationEngine(config)

    results = engine.run()
    paths = engine.write_reports(results)

    assert results[0].kevpe_available is True
    assert results[0].kevpe_regime == "RED"
    assert results[0].kevpe_score == 0.82

    payload = __import__("json").loads(Path(paths["json"]).read_text(encoding="utf-8"))
    snapshot = build_dashboard_snapshot(payload, source_json_path=paths["json"])
    assert snapshot["results"][0]["kevpe_available"] is True
    assert snapshot["results"][0]["kevpe_regime"] == "RED"


def test_ops_v1_workflow_generates_manual_approval_artifacts(tmp_path):
    from stock_rtx4060.ops_workflow import run_ops_v1_workflow

    config = RecommendationConfig(
        universe=["SYNTH-A", "SYNTH-B"],
        track="BOTH",
        top_n=2,
        synthetic=True,
        output_dir=str(tmp_path / "recommendations"),
    )
    result = run_ops_v1_workflow(config, output_dir=tmp_path)

    assert Path(result["recommendation_markdown"]).exists()
    assert Path(result["recommendation_json"]).exists()
    assert Path(result["audit_log"]).exists()
    assert Path(result["daily_brief"]).exists()
    assert Path(result["approval_journal_template"]).exists()
    assert Path(result["zero_log"]).exists()
    assert Path(result["summary_json"]).exists()

    journal = pd.read_csv(result["approval_journal_template"])
    assert {"ticker", "track", "verdict", "manual_action", "manual_approval_required", "broker_order_execution", "screening_output_only"}.issubset(journal.columns)
    assert set(journal["manual_action"]) == {"REVIEW_PENDING"}
    assert journal["manual_approval_required"].all()
    assert not journal["broker_order_execution"].any()
    assert journal["screening_output_only"].all()

    zero_log = Path(result["zero_log"]).read_text(encoding="utf-8")
    assert "AUTO_BUY" in zero_log
    assert "BROKER_ORDER" in zero_log
