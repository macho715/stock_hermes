import json
from pathlib import Path

import pytest

from stock_rtx4060.recommendation_engine import RecommendationConfig, RecommendationEngine


def test_recommendation_config_rejects_bad_sizing_values():
    with pytest.raises(ValueError, match="sizing_kind"):
        RecommendationConfig(sizing_kind="quantum")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="sizing_alpha"):
        RecommendationConfig(sizing_alpha=1.0)
    with pytest.raises(ValueError, match="sizing_n_min"):
        RecommendationConfig(sizing_n_min=0)


def test_recommendation_engine_sizing_off_preserves_score(tmp_path):
    config = RecommendationConfig(
        universe=["SYNTH-A"],
        track="S",
        top_n=1,
        synthetic=True,
        output_dir=str(tmp_path),
        model_kind="logistic",
        sizing_kind="off",
    )
    result = RecommendationEngine(config).run()[0]
    assert result.sizing_strategy_used == "off"
    assert result.size_multiplier == 1.0
    assert result.raw_score == result.recommendation_rank_score


def test_recommendation_engine_sizing_global_downgrades_and_audits(tmp_path):
    config = RecommendationConfig(
        universe=["SYNTH-A"],
        track="S",
        top_n=1,
        synthetic=True,
        output_dir=str(tmp_path),
        model_kind="logistic",
        sizing_kind="global",
        sizing_n_min=5,
    )
    engine = RecommendationEngine(config)
    result = engine.run()[0]
    paths = engine.write_reports([result])

    assert result.sizing_strategy_used == "global"
    assert 0.0 <= result.size_multiplier <= 1.0
    assert result.recommendation_rank_score <= result.raw_score
    assert result.sizing_coverage_status in {"PASS", "AMBER", "ZERO", "NO_DATA"}

    payload = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    row = payload["results"][0]
    assert row["raw_score"] == result.raw_score
    assert row["size_multiplier"] == result.size_multiplier
    assert "CMRS sizing optional downgrade-only" in payload["algorithm_patch"]
    assert any(
        json.loads(line).get("event_type") == "sizing_strategy_selected"
        for line in Path(paths["audit"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
