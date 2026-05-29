"""
Flask API server for stock_rtx4060 unified -provides /api/recommend endpoint.

Run: python api_server.py [--port 5151]
Serves dashboard_snapshot.v1 JSON for Vite dashboard integration.

CORS enabled for localhost:5173 (Vite dev server).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "root_folder_snapshot" / "stock-pred-v5" / "dist"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot
from stock_rtx4060.data_providers import load_ohlcv_with_provider
from stock_rtx4060.ensemble_model import EnsemblePredictor, GRUPredictor, ModelConfig, _has_torch
from stock_rtx4060.feature_engine import TechnicalIndicators
from stock_rtx4060.paper_trading import load_paper_status
from stock_rtx4060.recommendation_engine import RecommendationConfig, RecommendationEngine, parse_universe

app = Flask(__name__, static_folder=str(DIST), static_url_path="")
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://localhost:4173",
                "http://localhost:5151",
            ]
        }
    },
)

MARKET_UNIVERSES: dict[str, list[dict[str, str]]] = {
    "US": [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft"},
        {"symbol": "NVDA", "name": "NVIDIA"},
        {"symbol": "TSLA", "name": "Tesla"},
        {"symbol": "AMZN", "name": "Amazon"},
        {"symbol": "GOOGL", "name": "Alphabet"},
        {"symbol": "META", "name": "Meta"},
        {"symbol": "SPY", "name": "S&P 500 ETF"},
        {"symbol": "QQQ", "name": "Nasdaq 100 ETF"},
    ],
    "KRX": [
        {"symbol": "005930.KS", "name": "Samsung Electronics"},
        {"symbol": "000660.KS", "name": "SK Hynix"},
        {"symbol": "005380.KS", "name": "Hyundai Motor"},
        {"symbol": "005490.KS", "name": "POSCO Holdings"},
        {"symbol": "035420.KS", "name": "NAVER"},
        {"symbol": "035720.KS", "name": "Kakao"},
        {"symbol": "051910.KS", "name": "LG Chem"},
        {"symbol": "006400.KS", "name": "Samsung SDI"},
        {"symbol": "003670.KS", "name": "POSCO Future M"},
    ],
}


def _frame_to_ohlcv_records(frame: Any) -> list[dict[str, Any]]:
    if hasattr(frame.columns, "nlevels") and frame.columns.nlevels > 1:
        frame.columns = [
            "_".join(str(part) for part in col if str(part))
            for col in frame.columns.to_flat_index()
        ]
    rename_map: dict[str, str] = {}
    for col in frame.columns:
        base = str(col).split("_")[0].lower()
        if base in {"open", "high", "low", "close", "volume"}:
            rename_map[col] = base
    normalized = frame.rename(columns=rename_map)
    records: list[dict[str, Any]] = []
    for idx, row in normalized.iterrows():
        date_value = None
        for date_col in ("Date", "date", "Datetime", "datetime"):
            if date_col in normalized.columns:
                date_value = row.get(date_col)
                break
        date_ts = None
        if date_value is not None:
            try:
                date_ts = pd.Timestamp(date_value)
            except Exception:
                date_ts = None
        if date_ts is None and hasattr(idx, "to_pydatetime"):
            date_ts = pd.Timestamp(idx)
        close = row.get("close")
        if close is None:
            continue
        try:
            close_value = float(close)
        except (TypeError, ValueError):
            continue
        if close_value != close_value:
            continue
        timestamp_ms = int(date_ts.to_pydatetime().timestamp() * 1000) if date_ts is not None else 0
        records.append(
            {
                "date": date_ts.strftime("%Y-%m-%d") if date_ts is not None else str(idx)[:10],
                "timestamp": timestamp_ms,
                "open": float(row.get("open", close_value)),
                "high": float(row.get("high", close_value)),
                "low": float(row.get("low", close_value)),
                "close": close_value,
                "volume": int(float(row.get("volume", 0) or 0)),
            }
        )
    return records


def _score_signal(score: float) -> str:
    if score >= 56.0:
        return "BUY"
    if score <= 44.0:
        return "SELL"
    return "HOLD"


def _mean_metric(items: list[dict[str, Any]], key: str, fallback: float) -> float:
    values = [float(item[key]) for item in items if item.get(key) is not None]
    if not values:
        return fallback
    return float(sum(values) / len(values))


def _last_date_value(frame: Any) -> str | None:
    if frame is None or getattr(frame, "empty", True):
        return None
    last_index = frame.index[-1]
    if hasattr(last_index, "strftime"):
        return last_index.strftime("%Y-%m-%d")
    return str(last_index)[:10]


@app.route("/api/universe", methods=["GET"])
def api_universe():
    """Return dashboard-selectable symbols owned by the backend configuration."""
    market = request.args.get("market", "US").strip().upper()
    if market not in MARKET_UNIVERSES:
        return jsonify({"error": "market must be US or KRX", "market": market}), 400
    symbols = MARKET_UNIVERSES[market]
    return jsonify(
        {
            "market": market,
            "source": "backend_config",
            "count": len(symbols),
            "symbols": symbols,
        }
    )


@app.route("/api/symbol", methods=["GET"])
def api_symbol():
    """Return latest daily OHLCV records for the dashboard main chart."""
    symbol = request.args.get("symbol", "").strip().upper()
    period = request.args.get("period", "6mo")
    requested_provider = request.args.get("data_provider")
    use_synthetic = request.args.get("synthetic", "0") == "1"
    data_provider = (requested_provider or ("pykrx" if symbol.endswith((".KS", ".KQ")) else "yfinance")).lower()
    if not symbol:
        return jsonify({"error": "symbol param required"}), 400
    try:
        fallback_reason = None
        try:
            provider_result = load_ohlcv_with_provider(
                symbol,
                period,
                synthetic=use_synthetic,
                data_provider=data_provider,
                audit_logger=None,
                command="symbol_chart",
            )
        except Exception as provider_exc:
            if use_synthetic:
                raise
            fallback_reason = str(provider_exc)
            if symbol.endswith((".KS", ".KQ")) and data_provider in {"pykrx", "fdr"}:
                try:
                    provider_result = load_ohlcv_with_provider(
                        symbol,
                        period,
                        synthetic=False,
                        data_provider="yfinance",
                        audit_logger=None,
                        command="symbol_chart",
                    )
                except Exception:
                    # Both pykrx and yfinance failed -use synthetic
                    provider_result = load_ohlcv_with_provider(
                        symbol,
                        period,
                        synthetic=True,
                        data_provider="synthetic",
                        audit_logger=None,
                        command="symbol_chart",
                    )
            else:
                # Auto-fallback to synthetic on network failure
                provider_result = load_ohlcv_with_provider(
                    symbol,
                    period,
                    synthetic=True,
                    data_provider="synthetic",
                    audit_logger=None,
                    command="symbol_chart",
                )
        records = _frame_to_ohlcv_records(provider_result.frame)
        if len(records) < 30:
            return jsonify(
                {
                    "error": f"{symbol}: insufficient rows",
                    "row_count": len(records),
                    "provider": provider_result.provider_used,
                    "source": str(provider_result.source).upper(),
                }
            ), 502
        last_date = records[-1]["date"]
        last_dt = datetime.fromisoformat(last_date).replace(tzinfo=UTC)
        freshness_days = max(0, (datetime.now(UTC).date() - last_dt.date()).days)
        return jsonify(
            {
                "symbol": symbol,
                "period": period,
                "source": str(provider_result.source).upper(),
                "provider": provider_result.provider_used,
                "row_count": len(records),
                "last_date": last_date,
                "freshness_days": freshness_days,
                "provider_metadata": getattr(provider_result, "metadata", None) or {},
                "fallback_reason": fallback_reason,
                "data": records,
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc), "type": type(exc).__name__, "symbol": symbol}), 502


@app.route("/api/model-scores", methods=["GET"])
def api_model_scores():
    """Return backend model evidence for one selected ticker."""
    symbol = request.args.get("symbol", "").strip().upper()
    period = request.args.get("period", "3y")
    model_kind = request.args.get("model_kind", "logistic")
    data_provider = request.args.get("data_provider", "yfinance")
    synthetic = request.args.get("synthetic", "0") == "1"
    use_lstm = request.args.get("use_lstm", "0") == "1"
    horizon = int(request.args.get("horizon", 5))
    cv_kind = request.args.get("cv_kind", "purged")  # v5.1: default purged (was timeseries)
    # contrarian_mode: flip 1-prob for mean-reversion markets.
    # KRX (*.KS/*.KQ) defaults to True — empirically shows inverse AUC > 0.55 consistently.
    _contrarian_default = "1" if symbol.strip().upper().endswith((".KS", ".KQ")) else "0"
    contrarian_mode = request.args.get("contrarian", _contrarian_default) == "1"

    if not symbol:
        return jsonify({"error": "symbol param required"}), 400
    if model_kind not in {"auto", "xgb", "logistic", "rf", "lightgbm"}:
        return jsonify({"error": "model_kind must be auto, xgb, logistic, rf, or lightgbm"}), 400
    if horizon <= 0:
        return jsonify({"error": "horizon must be positive"}), 400

    # KRX symbols default to LightGBM when model_kind=auto — better for small datasets
    _is_krx = symbol.endswith((".KS", ".KQ"))
    _model_kind_effective = "lightgbm" if (_is_krx and model_kind == "auto") else model_kind

    try:
        provider_result = load_ohlcv_with_provider(
            symbol,
            period,
            synthetic=synthetic,
            data_provider=data_provider,
            command="model_scores",
        )
        feature_df = TechnicalIndicators(provider_result.frame).build_all(horizon=horizon)
        if feature_df.empty or len(feature_df) < 80:
            return jsonify(
                {
                    "schema_version": "model_scores.v1",
                    "ticker": symbol,
                    "period": period,
                    "provider": provider_result.provider_used,
                    "model_kind": model_kind,
                    "status": "FAIL",
                    "signal": "MODEL_EVIDENCE_UNAVAILABLE",
                    "error": "insufficient feature rows for backend model evidence",
                    "evidence": {
                        "row_count": int(len(provider_result.frame)),
                        "feature_rows": int(len(feature_df)),
                        "last_date": _last_date_value(provider_result.frame),
                        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                    },
                }
            ), 422

        _n_rows = len(feature_df)
        _embargo_pct = float(max(0.01, min(0.10, horizon / max(_n_rows, 1))))
        model = EnsemblePredictor(
            ModelConfig(
                horizon=horizon,
                n_splits=5,
                gap=horizon,
                model_kind=_model_kind_effective,  # type: ignore[arg-type]
                xgb_device="cpu",
                use_lstm=use_lstm,
                lite=False,
                cv_kind=cv_kind,
                embargo_pct=_embargo_pct,
                contrarian_mode=contrarian_mode,  # KRX default True
            )
        )
        cv_results = model.fit(feature_df)
        latest = model.predict_latest(feature_df)
        main_score = round(float(latest["direction_prob"]) * 100.0, 2)
        primary_score = round(float(latest.get("main_prob", latest["direction_prob"])) * 100.0, 2)
        lstm_score = (
            round(float(latest["lstm_prob"]) * 100.0, 2)
            if latest.get("lstm_enabled") and latest.get("lstm_prob") is not None
            else None
        )
        signal = _score_signal(main_score)
        backend_kind = str(latest["backend"])
        oof_coverage = 0.0
        if model.oof_probabilities_ is not None:
            oof_coverage = float(model.oof_probabilities_.notna().mean())

        # Fold diagnostics for AUC stability analysis
        fold_aucs = [float(r.get("auc", 0.5)) for r in cv_results]
        mean_auc = float(sum(fold_aucs) / len(fold_aucs)) if fold_aucs else 0.5
        inverse_auc = round(1.0 - mean_auc, 6)
        folds_above_50_pct = (
            sum(1 for a in fold_aucs if a > 0.50) / len(fold_aucs) if fold_aucs else 0.0
        )
        feature_df_cols = [c for c in feature_df.columns if not c.startswith("target")]
        train_rows_mean = int(sum(r.get("n_train", 0) for r in cv_results) / max(len(cv_results), 1))
        sample_feature_ratio = round(train_rows_mean / max(len(feature_df_cols), 1), 2)

        # Secondary LogReg score -always computed (fast, no extra deps)
        logistic_score: float | None
        if backend_kind == "logistic":
            logistic_score = primary_score
        else:
            try:
                _lr = EnsemblePredictor(ModelConfig(
                    horizon=horizon, n_splits=5, gap=horizon,
                    model_kind="logistic", use_lstm=False, lite=True,
                    cv_kind=cv_kind, embargo_pct=_embargo_pct,  # v5.1: purged
                ))
                _lr.fit(feature_df)
                _lr_latest = _lr.predict_latest(feature_df)
                logistic_score = round(float(_lr_latest["direction_prob"]) * 100.0, 2)
            except Exception:
                logistic_score = None

        # XGBoost secondary score — computed when primary backend is NOT xgb
        xgboost_score: float | None
        if backend_kind.startswith("xgb"):
            xgboost_score = primary_score
        else:
            try:
                _xgb = EnsemblePredictor(ModelConfig(
                    horizon=horizon, n_splits=5, gap=horizon,
                    model_kind="xgb", xgb_device="cpu", use_lstm=False, lite=True,
                    cv_kind=cv_kind, embargo_pct=_embargo_pct,
                ))
                _xgb.fit(feature_df)
                _xgb_latest = _xgb.predict_latest(feature_df)
                xgboost_score = round(float(_xgb_latest["direction_prob"]) * 100.0, 2)
            except Exception as _xgb_exc:
                print(f"[XGBoost secondary] FAILED: {type(_xgb_exc).__name__}: {_xgb_exc}", flush=True)
                xgboost_score = None

        # RNN (GRU) score — computed when PyTorch is available
        rnn_score: float | None = None
        if _has_torch():
            try:
                _gru_cfg = ModelConfig(
                    horizon=horizon, seq_len=model.config.seq_len, lite=True,
                )
                _gru = GRUPredictor(_gru_cfg)
                _gru.fit(
                    feature_df.loc[:, model.feature_cols],
                    feature_df["target_direction"].astype(int),
                )
                _gru_prob = _gru.predict_proba(feature_df.loc[:, model.feature_cols])
                if len(_gru_prob):
                    rnn_score = round(float(_gru_prob[-1]) * 100.0, 2)
            except Exception:
                rnn_score = None

        model_scores = {
            "main": main_score,
            "xgboost": xgboost_score,
            "logistic": logistic_score,
            "lstm": lstm_score,
            "rnn": rnn_score,
        }

        return jsonify(
            {
                "schema_version": "model_scores.v1",
                "ticker": symbol,
                "period": period,
                "provider": provider_result.provider_used,
                "model_kind": backend_kind,
                "requested_model_kind": model_kind,
                "signal": signal,
                "ensemble_score": main_score,
                "model_scores": model_scores,
                "evidence": {
                    "row_count": int(len(provider_result.frame)),
                    "feature_rows": int(len(feature_df)),
                    "feature_count": len(feature_df_cols),
                    "last_date": _last_date_value(provider_result.frame),
                    "oof_coverage": round(oof_coverage, 6),
                    "model_accuracy": round(_mean_metric(cv_results, "accuracy", 0.0), 6),
                    "model_auc": round(mean_auc, 6),
                    # Fold diagnostics (v5.1 — signal quality analysis)
                    "fold_aucs": [round(a, 4) for a in fold_aucs],
                    "inverse_auc": inverse_auc,
                    "folds_above_50_pct": round(folds_above_50_pct, 4),
                    "train_rows_mean": train_rows_mean,
                    "sample_feature_ratio": sample_feature_ratio,
                    # CV provenance
                    "cv_method": "purged_kfold_oof" if cv_kind == "purged" else "timeseries_kfold",
                    "cv_kind": cv_kind,
                    "label_horizon_bars": horizon,
                    "embargo_pct": round(_embargo_pct, 6),
                    "embargo_samples": int(_n_rows * _embargo_pct),
                    "backtest_probability_source": "OOF_ONLY_FILLED_0_5",
                    "cv_gap": int(model.config.gap or 0),  # legacy
                    "training_mode": "purged_kfold_oof_refit" if cv_kind == "purged" else "walk_forward_refit",
                    "lstm_requested": use_lstm,
                    "lstm_enabled": bool(latest.get("lstm_enabled")),
                    "contrarian_mode": contrarian_mode,
                    "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                },
                "effective_model_kind": _model_kind_effective,
                "status": "PASS",
            }
        )
    except Exception as exc:
        return jsonify(
            {
                "schema_version": "model_scores.v1",
                "ticker": symbol,
                "period": period,
                "provider": data_provider,
                "model_kind": model_kind,
                "status": "FAIL",
                "signal": "MODEL_EVIDENCE_UNAVAILABLE",
                "error": str(exc),
                "type": type(exc).__name__,
                "evidence": {
                    "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                },
            }
        ), 502


@app.route("/api/recommend", methods=["GET"])
def api_recommend():
    """
    Query params:
      universe  -comma-separated tickers (default: built-in sample)
      track     -S | L | BOTH (default: BOTH)
      period    -yfinance period (default: 3y)
      top       -top N candidates (default: 5)
      synthetic -1 to use synthetic data (default: 0)
      data_provider -auto | synthetic | yfinance | openbb | pykrx | fdr (default: auto)
      model_kind -auto | xgb | logistic (default: logistic)
      output_dir -directory for JSON output (default: reports/api_recommend)
    Returns: dashboard_snapshot.v1 JSON
    """
    universe = request.args.get("universe")
    track = request.args.get("track", "BOTH")
    period = request.args.get("period", "3y")
    synthetic = request.args.get("synthetic", "0") == "1"
    data_provider = request.args.get("data_provider", "auto")
    model_kind = request.args.get("model_kind", "logistic")
    output_dir = request.args.get("output_dir", "reports/api_recommend")
    advisor_run = request.args.get("advisor_run", "0") == "1"
    advisor_blend_weight = float(request.args.get("advisor_blend_weight", "0.3"))
    # cv_gap=5 default activates CPCV so pbo_status is populated in the snapshot
    cv_gap_raw = request.args.get("cv_gap")
    cv_gap = int(cv_gap_raw) if cv_gap_raw is not None else 5

    # Silently disable advisor when no supported live LLM key is available.
    from stock_rtx4060.advisors.claude_client import has_live_advisor_key

    if advisor_run and not has_live_advisor_key():
        advisor_run = False

    _tickers = parse_universe(universe)
    if len(_tickers) > 30:
        return jsonify({"error": f"universe too large: {len(_tickers)} tickers (max 30)"}), 400

    try:
        top = int(request.args.get("top", 5))
        config = RecommendationConfig(
            universe=_tickers,
            track=track,
            period=period,
            top_n=top,
            synthetic=synthetic,
            data_provider=data_provider,
            output_dir=output_dir,
            model_kind=model_kind,
            xgb_device="cpu",
            cv_gap=cv_gap,
            advisor_run=advisor_run,
            advisor_blend_weight=advisor_blend_weight if advisor_run else 0.0,
        )
        engine = RecommendationEngine(config)
        results = engine.run()
        paths = engine.write_reports(results)

        # Build snapshot from the generated JSON
        rec_json_path = Path(paths["json"])
        payload = json.loads(rec_json_path.read_text(encoding="utf-8"))
        snapshot = build_dashboard_snapshot(payload, source_json_path=rec_json_path)

        return jsonify(snapshot)
    except Exception as exc:
        return jsonify({"error": str(exc), "type": type(exc).__name__}), 500


@app.route("/api/snapshot", methods=["GET"])
def api_snapshot():
    """Serve an existing recommendation JSON as dashboard snapshot."""
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "path param required"}), 400
    try:
        p = Path(path)
        payload = json.loads(p.read_text(encoding="utf-8"))
        snapshot = build_dashboard_snapshot(payload, source_json_path=p)
        return jsonify(snapshot)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "ok", "service": "stock_rtx4060_unified", "version": "5.0.0"})


@app.route("/api/paper-status", methods=["GET"])
def api_paper_status():
    """Return latest paper-only trading state without mutating local reports."""
    try:
        status = load_paper_status(ROOT)
        status["krx_pilot"] = load_paper_status(ROOT / "reports" / "paper_trading" / "krx_runs")
        status["krx_pilot"]["market"] = "KRX"
        status["krx_pilot"]["pilot_label"] = "KRX paper trading pilot"
        return jsonify(status)
    except Exception as exc:
        return jsonify({"error": str(exc), "type": type(exc).__name__}), 500


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_dashboard(path: str):
    """Serve the built Vite dashboard static files."""
    if DIST.exists():
        target = DIST / path
        if path and target.exists() and target.is_file():
            return send_from_directory(str(DIST), path)
        return send_from_directory(str(DIST), "index.html")
    return jsonify({"error": "Dashboard not built. Run: npm run build in root_folder_snapshot/stock-pred-v5"}), 404


def main(port: int = 5151):
    parser = argparse.ArgumentParser(description="stock_rtx4060 unified API server")
    parser.add_argument("--port", type=int, default=port)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    dashboard_url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}"
    print(f"Starting stock_rtx4060 unified API server on http://0.0.0.0:{args.port}")
    print(f"Dashboard: {dashboard_url}/")
    print("Endpoints:")
    print("  GET /                     -React dashboard (built static)")
    print("  GET /api/health           -health check")
    print("  GET /api/universe         -dashboard-selectable symbols")
    print("  GET /api/symbol           -latest OHLCV for dashboard charts")
    print("  GET /api/model-scores     -backend model evidence for one symbol")
    print("  GET /api/paper-status     -latest paper-only virtual trading status")
    print("  GET /api/recommend        -run recommendation + return snapshot")
    print("  GET /api/snapshot?path=X  -serve existing recommendation JSON as snapshot")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
