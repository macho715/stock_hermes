"""CLI entrypoint for stock_rtx4060."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from .backtester import Backtester
from .benchmark import run_benchmark, write_benchmark_report
from .ensemble_model import EnsemblePredictor, ModelConfig
from .feature_engine import TechnicalIndicators, make_synthetic_ohlcv, normalize_ohlcv
from .hw_profile import print_hw_summary, runtime_status, save_runtime_status
from .ops_workflow import run_ops_v1_workflow
from .recommendation_engine import RecommendationConfig, RecommendationEngine, parse_universe
from .reports import ReportWriter
from .risk_rules import RiskConfig, evaluate_track_l_candidate, evaluate_track_s_candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="stock_rtx4060 investment OS")
    sub = parser.add_subparsers(dest="command")

    env = sub.add_parser("env", help="validate runtime/GPU environment")
    env.add_argument("--tensorflow", action="store_true", help="include TensorFlow GPU probe")
    env.add_argument("--xgboost", action="store_true", default=True, help="include XGBoost CUDA probe")
    env.add_argument("--output", default="reports/runtime_status.json")

    bench = sub.add_parser("benchmark", help="run synthetic CPU/GPU benchmark")
    bench.add_argument("--rows", type=int, default=1500)
    bench.add_argument("--repeats", type=int, default=3)
    bench.add_argument("--include-gpu", action="store_true")
    bench.add_argument("--include-lstm", action="store_true")
    bench.add_argument("--full", action="store_true", help="use larger models")
    bench.add_argument("--output-dir", default="reports")

    report = sub.add_parser("report", help="generate Daily Brief/Risk reports")
    report.add_argument("--ticker", default="SAMPLE")
    report.add_argument("--csv", help="OHLCV CSV file; if omitted synthetic data is used")
    report.add_argument("--horizon", type=int, default=5)
    report.add_argument("--capital", type=float, default=100_000.0)
    report.add_argument("--prefer-gpu", action="store_true")
    report.add_argument("--use-lstm", action="store_true")
    report.add_argument("--lite", action="store_true")
    report.add_argument("--output-dir", default="reports")

    predict = sub.add_parser("predict", help="train/predict from CSV or yfinance")
    predict.add_argument("--ticker", default="AAPL")
    predict.add_argument("--csv")
    predict.add_argument("--period", default="3y")
    predict.add_argument("--horizon", type=int, default=5)
    predict.add_argument("--prefer-gpu", action="store_true")
    predict.add_argument("--use-lstm", action="store_true")
    predict.add_argument("--lite", action="store_true")

    recommend = sub.add_parser("recommend", help="rank report-only Track-S/Track-L candidates")
    recommend.add_argument("--universe", help="comma-separated ticker list; defaults to built-in sample universe")
    recommend.add_argument("--track", choices=["S", "L", "BOTH"], default="BOTH")
    recommend.add_argument("--period", default="3y")
    recommend.add_argument("--top", type=int, default=5)
    recommend.add_argument("--synthetic", action="store_true", help="use deterministic synthetic OHLCV for offline validation")
    recommend.add_argument("--data-provider", choices=["auto", "synthetic", "yfinance", "openbb"], default="auto", help="OHLCV provider; CLI value overrides provider config")
    recommend.add_argument("--provider-config", help="optional JSON provider config; see config/data_providers.example.json")
    recommend.add_argument("--capital", type=float, default=100_000.0)
    recommend.add_argument("--prefer-gpu", action="store_true")
    recommend.add_argument("--full", action="store_true", help="use non-lite model settings")
    recommend.add_argument("--model-kind", choices=["auto", "xgb", "logistic"], default="logistic")
    recommend.add_argument("--xgb-device", choices=["cpu", "cuda"], default="cpu")
    recommend.add_argument("--cv-gap", type=int, help="gap between train/test folds for leak-safe walk-forward CV")
    recommend.add_argument("--output-dir", default="reports/recommendations")

    ops = sub.add_parser("ops-v1", help="run report-only Ops v1 workflow with manual approval artifacts")
    ops.add_argument("--universe", help="comma-separated ticker list; defaults to built-in sample universe")
    ops.add_argument("--track", choices=["S", "L", "BOTH"], default="BOTH")
    ops.add_argument("--period", default="3y")
    ops.add_argument("--top", type=int, default=5)
    ops.add_argument("--synthetic", action="store_true", help="use deterministic synthetic OHLCV for offline validation")
    ops.add_argument("--data-provider", choices=["auto", "synthetic", "yfinance", "openbb"], default="auto", help="OHLCV provider; CLI value overrides provider config")
    ops.add_argument("--provider-config", help="optional JSON provider config; see config/data_providers.example.json")
    ops.add_argument("--capital", type=float, default=100_000.0)
    ops.add_argument("--prefer-gpu", action="store_true")
    ops.add_argument("--full", action="store_true", help="use non-lite model settings")
    ops.add_argument("--model-kind", choices=["auto", "xgb", "logistic"], default="logistic")
    ops.add_argument("--xgb-device", choices=["cpu", "cuda"], default="cpu")
    ops.add_argument("--cv-gap", type=int, help="gap between train/test folds for leak-safe walk-forward CV")
    ops.add_argument("--output-dir", default="reports/ops_v1")

    demo = sub.add_parser("demo", help="create sample data and reports")
    demo.add_argument("--workspace", default="workspaces/demo_workspace")

    journal = sub.add_parser("journal", help="append decision journal row")
    journal.add_argument("--output-dir", default="reports")
    journal.add_argument("--ticker", required=True)
    journal.add_argument("--track", choices=["S", "L"], required=True)
    journal.add_argument("--action", required=True)
    journal.add_argument("--reason", required=True)
    journal.add_argument("--entry", type=float, default=0.0)
    journal.add_argument("--stop", type=float, default=0.0)
    journal.add_argument("--target", type=float, default=0.0)
    journal.add_argument("--quantity", type=int, default=0)

    sub.add_parser("self-test", help="run internal smoke tests")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = normalize_legacy_args(list(argv) if argv is not None else sys.argv[1:])
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "self-test"
    try:
        match command:
            case "env":
                return cmd_env(args)
            case "benchmark":
                return cmd_benchmark(args)
            case "report":
                return cmd_report(args)
            case "predict":
                return cmd_predict(args)
            case "recommend":
                return cmd_recommend(args)
            case "ops-v1":
                return cmd_ops_v1(args)
            case "demo":
                return cmd_demo(args)
            case "journal":
                return cmd_journal(args)
            case "self-test":
                return cmd_self_test()
            case _:
                parser.print_help()
                return 2
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def cmd_env(args: argparse.Namespace) -> int:
    print_hw_summary()
    status = runtime_status(include_tensorflow=args.tensorflow, include_xgboost=args.xgboost)
    path = save_runtime_status(args.output, status)
    print(json.dumps(asdict(status), ensure_ascii=False, indent=2))
    print(f"saved: {path}")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    report = run_benchmark(rows=args.rows, repeats=args.repeats, include_gpu=args.include_gpu, include_lstm=args.include_lstm, lite=not args.full)
    md_path, json_path = write_benchmark_report(report, args.output_dir)
    print(pd.DataFrame([asdict(item) for item in report.items]).to_markdown(index=False))
    print(f"saved: {md_path}")
    print(f"saved: {json_path}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    df = load_ohlcv(csv_path=args.csv, ticker=args.ticker, period="3y")
    feature_df = TechnicalIndicators(df).build_all(horizon=args.horizon)
    config = ModelConfig(horizon=args.horizon, prefer_gpu=args.prefer_gpu, use_xgboost=args.prefer_gpu, use_lstm=args.use_lstm, lite=args.lite, n_splits=3)
    model = EnsemblePredictor(config)
    metrics = model.fit(feature_df)
    latest_pred = model.predict_latest(feature_df)
    latest_row = feature_df.iloc[-1]
    entry = float(normalize_ohlcv(df)["Close"].iloc[-1])
    risk_cfg = RiskConfig(total_capital=args.capital)
    s_candidate = evaluate_track_s_candidate(args.ticker, latest_row, entry, risk_cfg, prediction_prob=latest_pred["direction_prob"])
    l_candidate = evaluate_track_l_candidate(args.ticker, latest_row, entry, risk_cfg, prediction_prob=latest_pred["direction_prob"])
    candidates = [s_candidate, l_candidate]

    signals = pd.Series(model.predict_proba(feature_df.drop(columns=["target_direction", "target_return"])), index=feature_df.index)
    prices = normalize_ohlcv(df)["Close"].reindex(feature_df.index).ffill()
    backtest = Backtester().run(prices, signals)

    writer = ReportWriter(args.output_dir)
    gate = runtime_status(include_tensorflow=False, include_xgboost=args.prefer_gpu).gate
    paths = [
        writer.daily_brief(candidates, runtime_gate=gate, benchmark_summary={"backend": latest_pred["backend"], "cv_accuracy_mean": _mean([m["accuracy"] for m in metrics])}),
        writer.risk_dashboard(candidates, risk_cfg),
        writer.track_l_thesis(candidates),
        writer.monthly_scorecard(backtest.to_dict()),
        writer.json_report("pipeline_result", {"prediction": latest_pred, "metrics": metrics, "backtest": backtest.to_dict(), "candidates": [c.to_dict() for c in candidates]}),
    ]
    for path in paths:
        print(f"saved: {path}")
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    df = load_ohlcv(csv_path=args.csv, ticker=args.ticker, period=args.period)
    feature_df = TechnicalIndicators(df).build_all(horizon=args.horizon)
    model = EnsemblePredictor(ModelConfig(horizon=args.horizon, prefer_gpu=args.prefer_gpu, use_xgboost=args.prefer_gpu, use_lstm=args.use_lstm, lite=args.lite, n_splits=3))
    metrics = model.fit(feature_df)
    latest = model.predict_latest(feature_df)
    print(json.dumps({"latest": latest, "metrics": metrics}, ensure_ascii=False, indent=2))
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    model_kind = args.model_kind
    xgb_device = "cuda" if args.prefer_gpu else args.xgb_device
    if args.prefer_gpu and model_kind == "logistic":
        model_kind = "xgb"
    config = RecommendationConfig(
        universe=parse_universe(args.universe),
        track=args.track,
        period=args.period,
        top_n=args.top,
        synthetic=args.synthetic,
        capital=args.capital,
        prefer_gpu=args.prefer_gpu,
        lite=not args.full,
        model_kind=model_kind,
        xgb_device=xgb_device,
        cv_gap=args.cv_gap,
        output_dir=args.output_dir,
        data_provider=args.data_provider,
        provider_config=args.provider_config,
    )
    engine = RecommendationEngine(config)
    results = engine.run()
    paths = engine.write_reports(results)
    errors = [r.to_dict() for r in results if r.verdict == "RED_DATA_OR_MODEL_ERROR"]
    print(json.dumps({"results": [item.to_dict() for item in results], "errors": errors}, ensure_ascii=False, indent=2)[:4000])
    print(f"saved: {paths['markdown']}")
    print(f"saved: {paths['json']}")
    print(f"saved: {paths['audit']}")
    return 0 if results else 1


def cmd_ops_v1(args: argparse.Namespace) -> int:
    model_kind = args.model_kind
    xgb_device = "cuda" if args.prefer_gpu else args.xgb_device
    if args.prefer_gpu and model_kind == "logistic":
        model_kind = "xgb"
    config = RecommendationConfig(
        universe=parse_universe(args.universe),
        track=args.track,
        period=args.period,
        top_n=args.top,
        synthetic=args.synthetic,
        capital=args.capital,
        prefer_gpu=args.prefer_gpu,
        lite=not args.full,
        model_kind=model_kind,
        xgb_device=xgb_device,
        cv_gap=args.cv_gap,
        data_provider=args.data_provider,
        provider_config=args.provider_config,
    )
    paths = run_ops_v1_workflow(config, output_dir=args.output_dir)
    print(json.dumps(paths, ensure_ascii=False, indent=2))
    for path in paths.values():
        print(f"saved: {path}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    data_dir = workspace / "data"
    reports_dir = workspace / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    df = make_synthetic_ohlcv(720)
    csv_path = data_dir / "sample_ohlcv.csv"
    df.to_csv(csv_path)
    print(f"saved: {csv_path}")
    report_args = argparse.Namespace(ticker="SAMPLE", csv=str(csv_path), horizon=5, capital=100_000.0, prefer_gpu=False, use_lstm=False, lite=True, output_dir=str(reports_dir))
    return cmd_report(report_args)


def cmd_journal(args: argparse.Namespace) -> int:
    path = ReportWriter(args.output_dir).journal_append({"ticker": args.ticker, "track": args.track, "action": args.action, "entry": args.entry, "stop": args.stop, "target": args.target, "quantity": args.quantity, "reason": args.reason})
    print(f"saved: {path}")
    return 0


def cmd_self_test() -> int:
    df = make_synthetic_ohlcv(360)
    features = TechnicalIndicators(df).build_all(horizon=5)
    assert len(features) > 100
    assert {"target_direction", "target_return"}.issubset(features.columns)
    model = EnsemblePredictor(ModelConfig(n_splits=3, lite=True))
    metrics = model.fit(features)
    assert metrics and model.trained
    probabilities = model.predict_proba(features.drop(columns=["target_direction", "target_return"]))
    assert len(probabilities) == len(features)
    bt = Backtester().run(df["Close"].reindex(features.index).ffill(), pd.Series(probabilities, index=features.index))
    assert bt.final_capital > 0
    candidate = evaluate_track_s_candidate("TEST", features.iloc[-1], float(df["Close"].iloc[-1]))
    assert candidate.quantity >= 0
    print("self-test: PASS")
    print(json.dumps({"rows": len(features), "backend": model.xgb.backend, "backtest": bt.to_dict(), "candidate": candidate.to_dict()}, ensure_ascii=False, indent=2)[:2000])
    return 0


def load_ohlcv(csv_path: str | None, ticker: str, period: str) -> pd.DataFrame:
    if csv_path:
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        return normalize_ohlcv(df)
    try:
        import yfinance as yf  # type: ignore
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            raise RuntimeError("yfinance returned empty data")
        return normalize_ohlcv(df)
    except Exception as exc:
        print(f"yfinance unavailable/failed ({type(exc).__name__}: {exc}); using synthetic data", file=sys.stderr)
        return make_synthetic_ohlcv(720)


def normalize_legacy_args(argv: list[str]) -> list[str]:
    """Accept the older root-script commands documented in early drafts."""
    if not argv:
        return argv
    if argv[0] == "--test":
        return ["self-test", *argv[1:]]
    if argv[0] == "--recommend":
        return ["recommend", *argv[1:]]
    if argv[0].startswith("-") and any(arg in argv for arg in ("--ticker", "--csv", "--period", "--horizon", "--lite", "--prefer-gpu", "--use-lstm")):
        return ["predict", *argv]
    return argv


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
