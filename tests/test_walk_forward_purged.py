"""
Tests that _fit_walk_forward_model() now uses PurgedKFold and guards the API
universe cap.

P0 fixes — plan_p0_fix_20260511.md
"""
from __future__ import annotations

import os
import sys
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import api_server
from stock_rtx4060.feature_engine import TechnicalIndicators, make_synthetic_ohlcv
from stock_rtx4060.ml.cv import PurgedKFold
from stock_rtx4060.recommendation_engine import (
    RecommendationConfig,
    _fit_walk_forward_model,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_feature_df(n_rows: int = 500, horizon: int = 5) -> pd.DataFrame:
    """Return a feature DataFrame guaranteed to have both target classes."""
    for _ in range(10):
        ohlcv = make_synthetic_ohlcv(n_rows)
        df = TechnicalIndicators(ohlcv).build_all(horizon=horizon)
        if len(df) >= 80 and df["target_direction"].nunique() >= 2:
            return df
    raise RuntimeError("Could not produce two-class synthetic feature data")


def _minimal_cfg(**kwargs) -> RecommendationConfig:
    defaults = dict(
        universe=["SYNTH"],
        synthetic=True,
        xgb_splits=3,
        min_oof_coverage=0.3,
    )
    defaults.update(kwargs)
    return RecommendationConfig(**defaults)


# ── test 1: PurgedKFold code path is executed ────────────────────────────────

def test_uses_purged_kfold():
    """_fit_walk_forward_model must return oof_probs with coverage > 0."""
    feature_df = _make_feature_df(n_rows=500, horizon=5)
    cfg = _minimal_cfg()

    result = _fit_walk_forward_model(feature_df, horizon=5, cfg=cfg)

    assert "oof_probs" in result, "oof_probs key missing from result"
    coverage = float(result["oof_probs"].notna().mean())
    assert coverage > 0, f"oof_coverage is zero — PurgedKFold may not have run: {coverage}"
    assert result["oof_coverage"] == pytest.approx(coverage, abs=1e-9)


# ── test 2: pre-test training labels don't overlap the test window ───────────

def test_oof_no_lookahead():
    """PurgedKFold must purge pre-test training rows whose label overlaps the test fold.

    For groups = arange(N) + horizon:
      - t_lo = groups[test_start] = test_start + horizon
      - Any train row i (i < test_start) with groups[i] >= t_lo is label-overlapping.
      - After purging: all pre-test training rows must have groups[i] < t_lo.
    """
    feature_df = _make_feature_df(n_rows=500, horizon=5)
    horizon = 5
    n = len(feature_df)

    n_splits = min(3, max(2, n // 120))
    embargo_pct = float(np.clip(horizon / max(n, 1), 0.01, 0.10))
    splitter = PurgedKFold(n_splits=n_splits, embargo_pct=embargo_pct)
    groups = np.arange(n, dtype=int) + horizon

    for train_idx, test_idx in splitter.split(feature_df, groups=groups):
        if len(test_idx) == 0 or len(train_idx) == 0:
            continue
        test_start = int(test_idx.min())
        t_lo = float(groups[test_start])

        # Pre-test training rows must have label end-times < t_lo
        pre_test_train = train_idx[train_idx < test_start]
        if len(pre_test_train) > 0:
            violating = groups[pre_test_train][groups[pre_test_train] >= t_lo]
            assert len(violating) == 0, (
                f"Look-ahead: {len(violating)} pre-test training rows have "
                f"label end-time >= t_lo={t_lo}"
            )


# ── test 3: API rejects universes larger than 30 tickers ─────────────────────

def test_api_universe_cap():
    """GET /api/recommend with 31 tickers must return HTTP 400."""
    tickers = ",".join([f"T{i:03d}" for i in range(31)])
    client = api_server.app.test_client()
    response = client.get(f"/api/recommend?universe={tickers}")
    assert response.status_code == 400, (
        f"Expected 400 for oversized universe, got {response.status_code}"
    )
    body = response.get_json()
    assert "universe too large" in body.get("error", "").lower()


def test_api_recommend_accepts_sizing_params(monkeypatch, tmp_path):
    captured = {}

    class FakeEngine:
        def __init__(self, config):
            captured["config"] = config
            self.config = config

        def run(self):
            return []

        def write_reports(self, results):
            out_dir = Path(self.config.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / "recommendations_algo_v2_fake.json"
            path.write_text(
                json.dumps(
                    {
                        "generated_at_utc": "2026-05-29T00:00:00+00:00",
                        "config": asdict(self.config),
                        "disclaimer": "screening_output_only; manual approval required; no broker order execution; not financial advice",
                        "results": [],
                        "errors": [],
                    }
                ),
                encoding="utf-8",
            )
            return {"json": str(path), "markdown": str(path.with_suffix(".md")), "audit": str(out_dir / "audit_log.jsonl")}

    monkeypatch.setattr(api_server, "RecommendationEngine", FakeEngine)
    client = api_server.app.test_client()
    response = client.get(
        "/api/recommend"
        f"?universe=SYNTH-A&synthetic=1&output_dir={tmp_path}"
        "&sizing_kind=auto&sizing_alpha=0.2&sizing_n_min=7"
    )

    assert response.status_code == 200
    assert captured["config"].sizing_kind == "auto"
    assert captured["config"].sizing_alpha == pytest.approx(0.2)
    assert captured["config"].sizing_n_min == 7


def test_api_recommend_rejects_bad_sizing_kind():
    client = api_server.app.test_client()
    response = client.get("/api/recommend?sizing_kind=quantum")
    assert response.status_code == 400
