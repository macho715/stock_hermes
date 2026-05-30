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
from .dashboard_bridge import write_dashboard_snapshot
from .ensemble_model import EnsemblePredictor, ModelConfig
from .feature_engine import TechnicalIndicators, make_synthetic_ohlcv, normalize_ohlcv
from .hw_profile import print_hw_summary, runtime_status, save_runtime_status
from .ops_workflow import run_ops_v1_workflow
from .paper_trading import PaperTradingConfig, PaperTradingEngine, PaperTradingSignal
from .recommendation_engine import RecommendationConfig, RecommendationEngine, parse_universe
from .reports import ReportWriter
from .risk_rules import RiskConfig, evaluate_track_l_candidate, evaluate_track_s_candidate

PROVIDER_CHOICES = ["auto", "synthetic", "yfinance", "openbb", "pykrx", "krx_final", "broker_final", "fdr"]


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
    recommend.add_argument("--data-provider", choices=PROVIDER_CHOICES, default="auto", help="OHLCV provider; CLI value overrides provider config")
    recommend.add_argument("--provider-config", help="optional JSON provider config; see config/data_providers.example.json")
    recommend.add_argument("--after-market-close", action="store_true", help="use authoritative final-bar provider policy for post-close KRX recommendation runs")
    recommend.add_argument("--kevpe-events", help="optional KEVPE event JSON/CSV file with date/headline/ticker fields")
    recommend.add_argument("--capital", type=float, default=100_000.0)
    recommend.add_argument("--prefer-gpu", action="store_true")
    recommend.add_argument("--full", action="store_true", help="use non-lite model settings")
    recommend.add_argument("--model-kind", choices=["auto", "xgb", "logistic", "rf"], default="logistic")
    recommend.add_argument("--xgb-device", choices=["cpu", "cuda"], default="cpu")
    recommend.add_argument("--cv-gap", type=int, help="PurgedKFold embargo gap (rows); must be >= horizon")
    recommend.add_argument("--sizing-kind", choices=["off", "global", "mondrian", "auto"], default="off")
    recommend.add_argument("--sizing-alpha", type=float, default=0.1)
    recommend.add_argument("--sizing-n-min", type=int, default=30)
    recommend.add_argument("--output-dir", default="reports/recommendations")

    paper = sub.add_parser("paper-run", help="paper-only virtual trading — no broker orders (screening only)")
    paper.add_argument("--universe", help="comma-separated ticker list")
    paper.add_argument("--track", choices=["S", "L", "BOTH"], default="BOTH")
    paper.add_argument("--period", default="3y")
    paper.add_argument("--top", type=int, default=5)
    paper.add_argument("--synthetic", action="store_true", help="use deterministic synthetic OHLCV")
    paper.add_argument("--data-provider", choices=PROVIDER_CHOICES, default="auto")
    paper.add_argument("--provider-config", help="optional JSON provider config")
    paper.add_argument("--after-market-close", action="store_true", help="use authoritative final-bar provider policy for post-close KRX paper runs")
    paper.add_argument("--kevpe-events", help="optional KEVPE event JSON/CSV file")
    paper.add_argument("--capital", type=float, default=100_000.0)
    paper.add_argument("--prefer-gpu", action="store_true")
    paper.add_argument("--full", action="store_true")
    paper.add_argument("--model-kind", choices=["auto", "xgb", "logistic", "rf"], default="logistic")
    paper.add_argument("--xgb-device", choices=["cpu", "cuda"], default="cpu")
    paper.add_argument("--cv-gap", type=int)
    paper.add_argument("--sizing-kind", choices=["off", "global", "mondrian", "auto"], default="off")
    paper.add_argument("--sizing-alpha", type=float, default=0.1)
    paper.add_argument("--sizing-n-min", type=int, default=30)
    paper.add_argument("--output-dir", default="reports/recommendations")
    paper.add_argument("--output-root", default="reports/paper_trading/runs", help="root directory for paper trading run output")
    paper.add_argument("--run-date", help="YYYY-MM-DD override for run_id; defaults to today")
    paper.add_argument("--force-rerun", action="store_true", help="override existing run for same date/universe")
    paper.add_argument("--rerun-reason", help="required when --force-rerun is set")
    paper.add_argument(
        "--broker",
        choices=["paper", "alpaca", "ibkr", "kis"],
        default="paper",
        help=(
            "Broker backend (default: paper). "
            "'paper' uses PaperBroker (no credentials needed). "
            "'alpaca'/'ibkr'/'kis' route through OrderRouter."
        ),
    )

    ops = sub.add_parser("ops-v1", help="run report-only Ops v1 workflow with manual approval artifacts")
    ops.add_argument("--universe", help="comma-separated ticker list; defaults to built-in sample universe")
    ops.add_argument("--track", choices=["S", "L", "BOTH"], default="BOTH")
    ops.add_argument("--period", default="3y")
    ops.add_argument("--top", type=int, default=5)
    ops.add_argument("--synthetic", action="store_true", help="use deterministic synthetic OHLCV for offline validation")
    ops.add_argument("--data-provider", choices=PROVIDER_CHOICES, default="auto", help="OHLCV provider; CLI value overrides provider config")
    ops.add_argument("--provider-config", help="optional JSON provider config; see config/data_providers.example.json")
    ops.add_argument("--after-market-close", action="store_true", help="use authoritative final-bar provider policy for post-close KRX ops runs")
    ops.add_argument("--kevpe-events", help="optional KEVPE event JSON/CSV file with date/headline/ticker fields")
    ops.add_argument("--capital", type=float, default=100_000.0)
    ops.add_argument("--prefer-gpu", action="store_true")
    ops.add_argument("--full", action="store_true", help="use non-lite model settings")
    ops.add_argument("--model-kind", choices=["auto", "xgb", "logistic", "rf"], default="logistic")
    ops.add_argument("--xgb-device", choices=["cpu", "cuda"], default="cpu")
    ops.add_argument("--cv-gap", type=int, help="PurgedKFold embargo gap (rows); must be >= horizon")
    ops.add_argument("--sizing-kind", choices=["off", "global", "mondrian", "auto"], default="off")
    ops.add_argument("--sizing-alpha", type=float, default=0.1)
    ops.add_argument("--sizing-n-min", type=int, default=30)
    ops.add_argument("--output-dir", default="reports/ops_v1")

    dashboard = sub.add_parser("dashboard-export", help="convert recommendation JSON into a dashboard snapshot")
    dashboard.add_argument("--recommendation-json", required=True, help="path to recommendations_algo_v2_*.json")
    dashboard.add_argument("--output", help="snapshot output path; defaults to dashboard_snapshot.json beside the recommendation JSON")
    dashboard.add_argument("--public-dir", help="optional Vite public directory to receive dashboard_snapshot.json, audit_log.jsonl, and approval_journal_template.csv")
    dashboard.add_argument("--approval-journal", help="optional approval_journal_template.csv path to copy with --public-dir")

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

    # ── PR-8: RD-Agent Alpha Factory — factor subcommands ──────────────────────
    factor = sub.add_parser("factor-mine", help="run RD-Agent factor mining (produces new .py factor modules)")
    factor.add_argument("--universe", help="comma-separated ticker list; defaults to built-in sample universe")
    factor.add_argument("--cycles", type=int, default=1, help="number of RD-Agent evolution cycles (default: 1)")
    factor.add_argument("--budget-usd", type=float, default=1.0, help="LLM spend cap in USD (default: 1.0)")
    factor.add_argument("--synthetic", action="store_true", help="skip live Qlib export; useful for RDAGENT_DRY_RUN smoke tests")

    factor_list = sub.add_parser("factor-list", help="list discovered / pending factors from the audit log")
    factor_list.add_argument("--status", choices=["all", "discovered", "staged", "registered"], default="all", help="filter by factor status (default: all)")

    factor_approve = sub.add_parser("factor-approve", help="approve and register staged factors via registry_hook")
    factor_approve.add_argument("--factor-id", action="append", help="specific factor ID to approve (repeatable); if omitted all staged factors are approved)")
    factor_approve.add_argument("--run-date", help="ISO date string for the approval run (YYYY-MM-DD); defaults to today")

    factor_status = sub.add_parser("factor-status", help="show status of all registered discovered factors")
    factor_status.add_argument("--ticker", help="show only factors for this ticker")

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
            case "paper-run":
                return cmd_paper_run(args)
            case "ops-v1":
                return cmd_ops_v1(args)
            case "dashboard-export":
                return cmd_dashboard_export(args)
            case "demo":
                return cmd_demo(args)
            case "journal":
                return cmd_journal(args)
            case "self-test":
                return cmd_self_test()
            case "factor-mine":
                return cmd_factor_mine(args)
            case "factor-list":
                return cmd_factor_list(args)
            case "factor-approve":
                return cmd_factor_approve(args)
            case "factor-status":
                return cmd_factor_status(args)
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
    s_candidate = evaluate_track_s_candidate(args.ticker, latest_row, entry, risk_cfg, prediction_prob=latest_pred["direction_prob"], atr_pct=float(latest_row.get("atr_pct_14", 0.0)))
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
        after_market_close=getattr(args, "after_market_close", False),
        kevpe_events=args.kevpe_events,
        sizing_kind=getattr(args, "sizing_kind", "off"),
        sizing_alpha=getattr(args, "sizing_alpha", 0.1),
        sizing_n_min=getattr(args, "sizing_n_min", 30),
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


def cmd_paper_run(args: argparse.Namespace) -> int:
    """Bridge RecommendationEngine output to PaperTradingEngine.

    Paper-only — no broker orders, no live account actions.
    screening_output_only=True and paper_trading_only=True are preserved.
    """
    import datetime

    model_kind = args.model_kind
    xgb_device = "cuda" if args.prefer_gpu else args.xgb_device
    if args.prefer_gpu and model_kind == "logistic":
        model_kind = "xgb"

    rec_config = RecommendationConfig(
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
        after_market_close=getattr(args, "after_market_close", False),
        kevpe_events=args.kevpe_events,
        sizing_kind=getattr(args, "sizing_kind", "off"),
        sizing_alpha=getattr(args, "sizing_alpha", 0.1),
        sizing_n_min=getattr(args, "sizing_n_min", 30),
    )
    rec_engine = RecommendationEngine(rec_config)
    results = rec_engine.run()

    buy_verdicts = {"ELIGIBLE_RECOMMENDATION", "ACCUMULATE_RECOMMENDATION"}
    signals = [
        PaperTradingSignal(
            ticker=r.ticker,
            score=r.recommendation_rank_score,
            signal="BUY" if r.verdict in buy_verdicts else "HOLD",
            model_auc=r.model_auc,
            model_accuracy=r.model_accuracy,
            oof_coverage=r.oof_coverage,
            warning=None,
        )
        for r in results
    ]

    tickers = [s.ticker for s in signals]
    bars_by_ticker: dict[str, list[dict[str, Any]]] = {}
    for ticker in tickers:
        if args.synthetic:
            df = make_synthetic_ohlcv(n=60)
            bars_by_ticker[ticker] = [
                {
                    "date": idx.date().isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "adjusted_close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
                for idx, row in df.iterrows()
            ]
        else:
            try:
                import yfinance as yf
                hist = yf.download(ticker, period=args.period, auto_adjust=True, progress=False)
                bars_by_ticker[ticker] = [
                    {
                        "date": idx.date().isoformat(),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "adjusted_close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    }
                    for idx, row in hist.iterrows()
                ]
            except Exception:
                bars_by_ticker[ticker] = []

    run_date = args.run_date or datetime.date.today().isoformat()
    paper_config = PaperTradingConfig(
        output_root=args.output_root,
        run_date=run_date,
        force_rerun=args.force_rerun,
        rerun_reason=args.rerun_reason,
    )
    paper_engine = PaperTradingEngine(paper_config)
    status = paper_engine.run(signals, bars_by_ticker)

    broker_name = getattr(args, "broker", "paper")
    if broker_name != "paper":
        # Skip live submission entirely when the paper engine returned a
        # previously cached run (no new decisions); otherwise re-running
        # paper-run on the same date/universe would resubmit duplicate live
        # orders.  Force-rerun is the intended escape hatch.
        if status.get("reused"):
            print(
                "INFO: paper engine returned a cached run — skipping live order routing. "
                "Use --force-rerun with --rerun-reason to regenerate decisions.",
                file=sys.stderr,
            )
        else:
            # Route accepted signals through the live OrderRouter instead of
            # silently consuming them in the paper engine.
            try:
                from .broker.order_router import KillSwitchError, OrderRouter

                router = OrderRouter(paper_fallback=True)
                accepted = [p for p in status.get("positions", [])]
                for pos in accepted:
                    ticker = pos.get("ticker", "")
                    shares = int(pos.get("shares", 0))
                    avg_price = float(pos.get("avg_price", 0.0))
                    if ticker and shares > 0:
                        try:
                            router.submit_order(
                                ticker=ticker,
                                qty=shares,
                                side="BUY",
                                order_type="LIMIT",
                                limit_price=avg_price,
                                broker=broker_name,
                            )
                        except KillSwitchError as exc:
                            print(f"KILL SWITCH active — aborting live order routing: {exc}", file=sys.stderr)
                            break
                        except Exception as exc:  # noqa: BLE001
                            print(f"WARNING: order routing failed for {ticker}: {exc}", file=sys.stderr)
                router.close()
            except ImportError as exc:
                print(f"WARNING: live broker not available ({exc}), paper mode used", file=sys.stderr)

    summary = {
        "paper_trading_only": broker_name == "paper",
        "screening_output_only": True,
        "broker": broker_name,
        "run_id": status.get("run_id"),
        "run_dir": str(status.get("run_dir", "")),
        "positions": len(status.get("positions", [])),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"saved: {status.get('run_dir')}")
    return 0


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
        after_market_close=getattr(args, "after_market_close", False),
        kevpe_events=args.kevpe_events,
        sizing_kind=getattr(args, "sizing_kind", "off"),
        sizing_alpha=getattr(args, "sizing_alpha", 0.1),
        sizing_n_min=getattr(args, "sizing_n_min", 30),
    )
    paths = run_ops_v1_workflow(config, output_dir=args.output_dir)
    print(json.dumps(paths, ensure_ascii=False, indent=2))
    for path in paths.values():
        print(f"saved: {path}")
    return 0


def cmd_dashboard_export(args: argparse.Namespace) -> int:
    from .dashboard_bridge import export_dashboard_public_assets

    path = write_dashboard_snapshot(args.recommendation_json, args.output)
    result = {"dashboard_snapshot": str(path)}
    if args.public_dir:
        result["public_assets"] = export_dashboard_public_assets(
            args.recommendation_json,
            path,
            args.public_dir,
            approval_journal=args.approval_journal,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"saved: {path}")
    if args.public_dir:
        print(f"exported public assets: {args.public_dir}")
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


# ── PR-8: RD-Agent Alpha Factory handlers ────────────────────────────────────

def _default_universe() -> list[str]:
    """Return the built-in sample universe used by research_weekly."""
    return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]


def cmd_factor_mine(args: argparse.Namespace) -> int:
    """Run RD-Agent factor mining via ``rd_agent.runner.run_factor_mining``."""
    from stock_rtx4060.factors.rd_agent.runner import run_factor_mining

    universe = parse_universe(args.universe) if args.universe else _default_universe()
    new_files = run_factor_mining(
        universe,
        cycles=args.cycles,
        budget_usd=args.budget_usd,
        prepare_qlib=True,
        synthetic=bool(getattr(args, "synthetic", False)),
    )
    result = {
        "new_factor_files": [str(p) for p in new_files],
        "count": len(new_files),
        "universe": universe,
        "cycles": args.cycles,
        "budget_usd": args.budget_usd,
        "synthetic": bool(getattr(args, "synthetic", False)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_factor_list(args: argparse.Namespace) -> int:
    """List discovered / pending factors from ``audit_log/*.jsonl``."""
    import json as _json
    from pathlib import Path

    audit_dir = Path("audit_log")
    candidates: list[dict[str, Any]] = []

    # Scan all .jsonl files in the audit log directory
    if audit_dir.is_dir():
        for fpath in sorted(audit_dir.glob("*.jsonl")):
            try:
                with open(fpath, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = _json.loads(line)
                        except Exception:
                            continue
                        # Accept any event that carries factor metadata
                        if "factor_id" in event or event.get("event") in (
                            "factor_discovered",
                            "factor_staged",
                            "factor_registered",
                        ):
                            status = (
                                "registered"
                                if event.get("event") == "factor_registered"
                                else "staged"
                                if event.get("event") == "factor_staged"
                                else "discovered"
                            )
                            if args.status != "all" and status != args.status:
                                continue
                            candidates.append({"event": event, "status": status})
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: could not read {fpath}: {exc}", file=sys.stderr)

    # Also check the discovered factors directory for orphan files
    discovered_dir = Path("src/stock_rtx4060/factors/discovered")
    if discovered_dir.is_dir():
        for fpath in sorted(discovered_dir.rglob("*.py")):
            fname = fpath.name
            if fname.startswith("_") or fname == "placeholder.py":
                continue
            # Skip if already in candidates
            if any(c["event"].get("factor_file") == str(fpath) for c in candidates):
                continue
            if args.status == "registered":
                continue
            candidates.append({
                "event": {"factor_id": None, "factor_file": str(fpath), "source": "discovered_dir"},
                "status": "discovered",
            })

    print(json.dumps(candidates, ensure_ascii=False, indent=2))
    return 0


def cmd_factor_approve(args: argparse.Namespace) -> int:
    """Approve and register staged factors via ``registry_hook.approve_and_register``."""
    from datetime import date as Date

    run_date = args.run_date or str(Date.today())
    factor_ids = args.factor_id or []  # empty list = approve all staged

    try:
        from stock_rtx4060.factors.rd_agent.registry_hook import approve_and_register
    except ImportError:
        print("ERROR: registry_hook module not found — ensure P7 infrastructure is installed", file=sys.stderr)
        return 1

    try:
        registered = approve_and_register(
            session_id=run_date,
            factor_names=factor_ids,
        )
        print(json.dumps({"approved": registered, "count": len(registered)}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"approved": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


def cmd_factor_status(args: argparse.Namespace) -> int:
    """Show status of all registered discovered factors."""
    import json as _json
    from pathlib import Path

    # Pull from the audit log the registered factors
    audit_dir = Path("audit_log")
    registered: list[dict[str, Any]] = []
    if audit_dir.is_dir():
        for fpath in sorted(audit_dir.glob("*.jsonl")):
            try:
                with open(fpath, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = _json.loads(line)
                        except Exception:
                            continue
                        if event.get("event") == "factor_registered":
                            ticker = event.get("ticker") or ""
                            if args.ticker and ticker != args.ticker:
                                continue
                            registered.append(event)
            except Exception:  # noqa: BLE001
                pass

    print(json.dumps(registered, ensure_ascii=False, indent=2))
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
