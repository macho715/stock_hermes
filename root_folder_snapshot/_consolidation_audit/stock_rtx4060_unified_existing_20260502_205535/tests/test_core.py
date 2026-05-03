from pathlib import Path

from stock_rtx4060.backtester import Backtester
from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig
from stock_rtx4060.feature_engine import TechnicalIndicators, make_synthetic_ohlcv
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
