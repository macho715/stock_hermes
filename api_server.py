"""
Flask API server for stock_rtx4060 unified — provides /api/recommend endpoint.

Run: python api_server.py [--port 5151]
Serves dashboard_snapshot.v1 JSON for Vite dashboard integration.

CORS enabled for localhost:5173 (Vite dev server).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stock_rtx4060.recommendation_engine import RecommendationConfig, RecommendationEngine, parse_universe
from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})


@app.route("/api/recommend", methods=["GET"])
def api_recommend():
    """
    Query params:
      universe  — comma-separated tickers (default: built-in sample)
      track     — S | L | BOTH (default: BOTH)
      period    — yfinance period (default: 3y)
      top       — top N candidates (default: 5)
      synthetic — 1 to use synthetic data (default: 0)
      model_kind — auto | xgb | logistic (default: logistic)
      output_dir — directory for JSON output (default: reports/api_recommend)
    Returns: dashboard_snapshot.v1 JSON
    """
    universe = request.args.get("universe")
    track = request.args.get("track", "BOTH")
    period = request.args.get("period", "3y")
    top = int(request.args.get("top", 5))
    synthetic = request.args.get("synthetic", "0") == "1"
    model_kind = request.args.get("model_kind", "logistic")
    output_dir = request.args.get("output_dir", "reports/api_recommend")

    config = RecommendationConfig(
        universe=parse_universe(universe),
        track=track,
        period=period,
        top_n=top,
        synthetic=synthetic,
        output_dir=output_dir,
        model_kind=model_kind,
        xgb_device="cpu",
    )

    try:
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


def main(port: int = 5151):
    parser = argparse.ArgumentParser(description="stock_rtx4060 unified API server")
    parser.add_argument("--port", type=int, default=port)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    print(f"Starting stock_rtx4060 unified API server on http://{args.host}:{args.port}")
    print(f"CORS enabled for http://localhost:5173")
    print(f"Endpoints:")
    print(f"  GET /api/health           — health check")
    print(f"  GET /api/recommend        — run recommendation + return snapshot")
    print(f"  GET /api/snapshot?path=X  — serve existing recommendation JSON as snapshot")
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()