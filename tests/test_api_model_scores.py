from types import SimpleNamespace

import pandas as pd

import api_server


def test_model_scores_api_applies_xgboost_and_lstm_when_requested(monkeypatch):
    calls = {}

    frame = pd.DataFrame(
        {
            "Open": range(120),
            "High": range(1, 121),
            "Low": range(120),
            "Close": range(1, 121),
            "Volume": [1000] * 120,
        },
        index=pd.date_range("2026-01-01", periods=120),
    )
    feature_df = pd.DataFrame(
        {
            "feature_a": [float(i) for i in range(120)],
            "target_direction": [0, 1] * 60,
            "target_return": [0.01] * 120,
        },
        index=frame.index,
    )

    def fake_load_ohlcv_with_provider(*args, **kwargs):
        return SimpleNamespace(frame=frame, provider_used="synthetic")

    class FakeIndicators:
        def __init__(self, source_frame):
            self.source_frame = source_frame

        def build_all(self, horizon):
            calls["horizon"] = horizon
            return feature_df

    class FakePredictor:
        def __init__(self, config):
            # Track all instantiations; first is primary, rest are secondary
            calls.setdefault("configs", []).append(config)
            calls["config"] = calls["configs"][0]  # primary config always first
            self.config = config
            self.oof_probabilities_ = pd.Series([0.55] * len(feature_df), index=feature_df.index)
            self.feature_cols = ["feature_a"]

        def fit(self, features):
            calls["fit_rows"] = len(features)
            return [{"accuracy": 0.61, "auc": 0.64}]

        def predict_latest(self, features):
            return {
                "direction_prob": 0.68,
                "main_prob": 0.72,
                "lstm_prob": 0.59,
                "signal": "BUY_REVIEW",
                "confidence": 0.36,
                "backend": "xgb-cpu",
                "lstm_enabled": True,
            }

    monkeypatch.setattr(api_server, "load_ohlcv_with_provider", fake_load_ohlcv_with_provider)
    monkeypatch.setattr(api_server, "TechnicalIndicators", FakeIndicators)
    monkeypatch.setattr(api_server, "EnsemblePredictor", FakePredictor)
    # Disable GRU/RNN computation in this unit test (no torch in test env path)
    monkeypatch.setattr(api_server, "_has_torch", lambda: False)

    client = api_server.app.test_client()
    response = client.get(
        "/api/model-scores?symbol=TEST&synthetic=1&model_kind=auto&use_lstm=1&data_provider=synthetic"
    )

    assert response.status_code == 200
    payload = response.get_json()
    # Primary model: model_kind=auto, use_lstm=True
    assert calls["config"].model_kind == "auto"
    assert calls["config"].use_lstm is True
    assert payload["model_kind"] == "xgb-cpu"
    assert payload["model_scores"]["main"] == 68.0
    assert payload["model_scores"]["xgboost"] == 72.0
    assert payload["model_scores"]["lstm"] == 59.0
    # logistic is now always computed (secondary model) — must be a number not None
    assert payload["model_scores"]["logistic"] is not None
    assert payload["evidence"]["lstm_enabled"] is True


def test_symbol_api_uses_provider_router_for_krx_chart_data(monkeypatch):
    calls = {}
    frame = pd.DataFrame(
        {
            "Open": range(40),
            "High": range(1, 41),
            "Low": range(40),
            "Close": range(1, 41),
            "Volume": [1000] * 40,
        },
        index=pd.date_range("2026-01-01", periods=40),
    )

    def fake_load_ohlcv_with_provider(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return SimpleNamespace(frame=frame, provider_used="pykrx", source="pykrx")

    monkeypatch.setattr(api_server, "load_ohlcv_with_provider", fake_load_ohlcv_with_provider)

    client = api_server.app.test_client()
    response = client.get("/api/symbol?symbol=005930.KS&period=6mo")

    assert response.status_code == 200
    payload = response.get_json()
    assert calls["args"][0] == "005930.KS"
    assert calls["kwargs"]["data_provider"] == "pykrx"
    assert calls["kwargs"]["command"] == "symbol_chart"
    assert payload["provider"] == "pykrx"
    assert payload["source"] == "PYKRX"
    assert payload["row_count"] == 40
    assert len(payload["data"]) == 40


def test_symbol_api_falls_back_to_yfinance_when_krx_provider_fails(monkeypatch):
    calls = []
    frame = pd.DataFrame(
        {
            "Open": range(40),
            "High": range(1, 41),
            "Low": range(40),
            "Close": range(1, 41),
            "Volume": [1000] * 40,
        },
        index=pd.date_range("2026-01-01", periods=40),
    )

    def fake_load_ohlcv_with_provider(*args, **kwargs):
        calls.append(kwargs["data_provider"])
        if kwargs["data_provider"] == "pykrx":
            raise RuntimeError("pykrx/fdr unavailable")
        return SimpleNamespace(frame=frame, provider_used="yfinance", source="yfinance")

    monkeypatch.setattr(api_server, "load_ohlcv_with_provider", fake_load_ohlcv_with_provider)

    client = api_server.app.test_client()
    response = client.get("/api/symbol?symbol=005930.KS&period=6mo")

    assert response.status_code == 200
    payload = response.get_json()
    assert calls == ["pykrx", "yfinance"]
    assert payload["provider"] == "yfinance"
    assert payload["source"] == "YFINANCE"
    assert "pykrx/fdr unavailable" in payload["fallback_reason"]
