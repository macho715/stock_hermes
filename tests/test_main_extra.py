"""Tests for stock_rtx4060.main — cmd_* functions, load_ohlcv, normalize_legacy_args, _mean."""
from __future__ import annotations

import argparse
import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import pytest

import stock_rtx4060.main as main_mod
from stock_rtx4060.feature_engine import make_synthetic_ohlcv
from stock_rtx4060.main import (
    _mean,
    build_parser,
    cmd_benchmark,
    cmd_dashboard_export,
    cmd_demo,
    cmd_env,
    cmd_journal,
    cmd_ops_v1,
    cmd_paper_run,
    cmd_predict,
    cmd_recommend,
    cmd_report,
    cmd_self_test,
    load_ohlcv,
    main,
    normalize_legacy_args,
)


# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------

@dataclass
class _FakeRuntimeStatus:
    gate: str = "GREEN"
    backend: str = "xgb-cpu"


def _fake_runtime_status(**kw):
    return _FakeRuntimeStatus()


class _FakeCandidate:
    ticker: str = "TEST"
    verdict: str = "ELIGIBLE_RECOMMENDATION"
    quantity: int = 10

    def to_dict(self):
        return {"ticker": self.ticker, "verdict": self.verdict}


class _FakeBacktestResult:
    final_capital: float = 105_000.0

    def to_dict(self):
        return {"final_capital": self.final_capital, "return_pct": 5.0}


class _FakeBacktester:
    def run(self, prices, signals):
        return _FakeBacktestResult()


class _FakeModel:
    trained: bool = True

    def __init__(self, config=None):
        from types import SimpleNamespace
        self.xgb = SimpleNamespace(backend="mock")

    def fit(self, df):
        return [{"accuracy": 0.55, "auc": 0.60}]

    def predict_latest(self, df):
        return {"direction_prob": 0.55, "backend": "mock"}

    def predict_proba(self, X):
        return [0.5] * len(X)


class _FakeReportWriter:
    def __init__(self, output_dir):
        pass

    def daily_brief(self, *a, **kw):
        return "reports/daily.md"

    def risk_dashboard(self, *a, **kw):
        return "reports/risk.md"

    def track_l_thesis(self, *a, **kw):
        return "reports/thesis.md"

    def monthly_scorecard(self, *a, **kw):
        return "reports/scorecard.md"

    def json_report(self, *a, **kw):
        return "reports/pipeline.json"

    def journal_append(self, row):
        return "reports/journal.csv"


class _FakeResult:
    ticker: str = "SYNTH"
    verdict: str = "ELIGIBLE_RECOMMENDATION"
    recommendation_rank_score: float = 80.0
    model_auc: float = 0.6
    model_accuracy: float = 0.55
    oof_coverage: float = 0.8

    def to_dict(self):
        return {"ticker": self.ticker, "verdict": self.verdict}


class _FakeRecommendationEngine:
    def __init__(self, config):
        pass

    def run(self):
        return [_FakeResult()]

    def write_reports(self, results):
        return {"markdown": "m.md", "json": "j.json", "audit": "a.jsonl"}


class _FakeEmptyEngine:
    def __init__(self, config):
        pass

    def run(self):
        return []

    def write_reports(self, results):
        return {"markdown": "m.md", "json": "j.json", "audit": "a.jsonl"}


class _FakePaperEngine:
    def __init__(self, config):
        pass

    def run(self, signals, bars):
        return {"run_id": "test-run", "run_dir": "/tmp/run", "positions": []}


@dataclass
class _FakeBenchmarkItem:
    name: str = "smoke"
    duration: float = 0.1


@dataclass
class _FakeBenchmarkReport:
    items: list = None

    def __post_init__(self):
        if self.items is None:
            self.items = [_FakeBenchmarkItem()]


# ---------------------------------------------------------------------------
# _mean
# ---------------------------------------------------------------------------

class TestMean:
    def test_empty(self):
        assert _mean([]) == 0.0

    def test_single(self):
        assert _mean([0.5]) == 0.5

    def test_multiple(self):
        assert abs(_mean([0.4, 0.6]) - 0.5) < 1e-5

    def test_rounds_to_6_decimals(self):
        result = _mean([1 / 3, 1 / 3, 1 / 3])
        assert isinstance(result, float)
        # 0.333333 or similar — 6 decimal places max
        dec_part = str(result).split(".")[-1]
        assert len(dec_part) <= 6


# ---------------------------------------------------------------------------
# normalize_legacy_args
# ---------------------------------------------------------------------------

class TestNormalizeLegacyArgs:
    def test_empty(self):
        assert normalize_legacy_args([]) == []

    def test_test_flag(self):
        result = normalize_legacy_args(["--test"])
        assert result[0] == "self-test"

    def test_test_flag_preserves_trailing(self):
        result = normalize_legacy_args(["--test", "--foo"])
        assert result == ["self-test", "--foo"]

    def test_recommend_flag(self):
        result = normalize_legacy_args(["--recommend"])
        assert result[0] == "recommend"

    def test_recommend_flag_with_args(self):
        result = normalize_legacy_args(["--recommend", "--universe", "AAPL"])
        assert result[:2] == ["recommend", "--universe"]

    def test_legacy_ticker_flag(self):
        result = normalize_legacy_args(["--ticker", "AAPL", "--period", "3y"])
        assert result[0] == "predict"

    def test_legacy_csv_flag(self):
        result = normalize_legacy_args(["--csv", "data.csv", "--horizon", "5"])
        assert result[0] == "predict"

    def test_passthrough_command(self):
        result = normalize_legacy_args(["recommend", "--universe", "AAPL"])
        assert result == ["recommend", "--universe", "AAPL"]

    def test_passthrough_no_known_flag(self):
        result = normalize_legacy_args(["--unknown-xyz"])
        assert result == ["--unknown-xyz"]


# ---------------------------------------------------------------------------
# load_ohlcv
# ---------------------------------------------------------------------------

class TestLoadOhlcv:
    def test_csv_path(self, tmp_path):
        df = make_synthetic_ohlcv(60)
        csv_path = tmp_path / "ohlcv.csv"
        df.to_csv(csv_path)
        result = load_ohlcv(csv_path=str(csv_path), ticker="TEST", period="1y")
        assert not result.empty
        assert "Close" in result.columns

    def test_yfinance_raises_uses_synthetic(self, monkeypatch):
        fake_yf = types.ModuleType("yfinance")

        def _raise(*a, **kw):
            raise RuntimeError("no network")

        fake_yf.download = _raise
        monkeypatch.setitem(sys.modules, "yfinance", fake_yf)
        result = load_ohlcv(csv_path=None, ticker="TEST", period="1y")
        assert not result.empty
        assert "Close" in result.columns

    def test_yfinance_empty_triggers_synthetic(self, monkeypatch):
        import pandas as pd
        fake_yf = types.ModuleType("yfinance")
        fake_yf.download = lambda *a, **kw: pd.DataFrame()
        monkeypatch.setitem(sys.modules, "yfinance", fake_yf)
        # empty DataFrame raises RuntimeError("yfinance returned empty data") → synthetic fallback
        result = load_ohlcv(csv_path=None, ticker="TEST", period="1y")
        assert not result.empty

    def test_csv_has_ohlcv_columns(self, tmp_path):
        df = make_synthetic_ohlcv(30)
        csv_path = tmp_path / "test.csv"
        df.to_csv(csv_path)
        result = load_ohlcv(csv_path=str(csv_path), ticker="X", period="1y")
        for col in ("Open", "High", "Low", "Close", "Volume"):
            assert col in result.columns


# ---------------------------------------------------------------------------
# build_parser smoke
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_smoke(self):
        assert build_parser() is not None

    def test_parse_self_test(self):
        args = build_parser().parse_args(["self-test"])
        assert args.command == "self-test"

    def test_parse_env(self):
        args = build_parser().parse_args(["env"])
        assert args.command == "env"

    def test_parse_recommend(self):
        args = build_parser().parse_args(["recommend", "--universe", "AAPL", "--top", "3"])
        assert args.command == "recommend"
        assert args.top == 3

    def test_help_exits_zero(self):
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(["--help"])
        assert exc.value.code == 0


# ---------------------------------------------------------------------------
# cmd_env
# ---------------------------------------------------------------------------

class TestCmdEnv:
    def test_returns_zero(self, monkeypatch, tmp_path):
        monkeypatch.setattr("stock_rtx4060.main.print_hw_summary", lambda: None)
        monkeypatch.setattr("stock_rtx4060.main.runtime_status", _fake_runtime_status)
        monkeypatch.setattr("stock_rtx4060.main.save_runtime_status", lambda path, status: path)
        args = argparse.Namespace(tensorflow=False, xgboost=True, output=str(tmp_path / "rt.json"))
        assert cmd_env(args) == 0

    def test_tensorflow_flag(self, monkeypatch, tmp_path):
        calls = {}
        monkeypatch.setattr("stock_rtx4060.main.print_hw_summary", lambda: None)
        monkeypatch.setattr("stock_rtx4060.main.runtime_status",
                            lambda **kw: calls.update(kw) or _FakeRuntimeStatus())
        monkeypatch.setattr("stock_rtx4060.main.save_runtime_status", lambda p, s: p)
        args = argparse.Namespace(tensorflow=True, xgboost=False, output=str(tmp_path / "rt.json"))
        cmd_env(args)
        assert calls.get("include_tensorflow") is True


# ---------------------------------------------------------------------------
# cmd_benchmark
# ---------------------------------------------------------------------------

class TestCmdBenchmark:
    def test_returns_zero(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.run_benchmark",
                            lambda **kw: _FakeBenchmarkReport())
        monkeypatch.setattr("stock_rtx4060.main.write_benchmark_report",
                            lambda r, d: ("m.md", "j.json"))
        args = argparse.Namespace(rows=100, repeats=1, include_gpu=False,
                                  include_lstm=False, full=False, output_dir="reports")
        assert cmd_benchmark(args) == 0


# ---------------------------------------------------------------------------
# cmd_report
# ---------------------------------------------------------------------------

class TestCmdReport:
    def _stub(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.load_ohlcv",
                            lambda csv_path, ticker, period: make_synthetic_ohlcv(360))
        monkeypatch.setattr("stock_rtx4060.main.EnsemblePredictor", _FakeModel)
        monkeypatch.setattr("stock_rtx4060.main.Backtester", _FakeBacktester)
        monkeypatch.setattr("stock_rtx4060.main.evaluate_track_s_candidate",
                            lambda *a, **kw: _FakeCandidate())
        monkeypatch.setattr("stock_rtx4060.main.evaluate_track_l_candidate",
                            lambda *a, **kw: _FakeCandidate())
        monkeypatch.setattr("stock_rtx4060.main.ReportWriter", _FakeReportWriter)
        monkeypatch.setattr("stock_rtx4060.main.runtime_status", _fake_runtime_status)

    def test_returns_zero(self, monkeypatch):
        self._stub(monkeypatch)
        args = argparse.Namespace(ticker="SAMPLE", csv=None, horizon=5,
                                  capital=100_000.0, prefer_gpu=False,
                                  use_lstm=False, lite=True, output_dir="reports")
        assert cmd_report(args) == 0

    def test_prefer_gpu_flag(self, monkeypatch):
        self._stub(monkeypatch)
        args = argparse.Namespace(ticker="SAMPLE", csv=None, horizon=5,
                                  capital=100_000.0, prefer_gpu=True,
                                  use_lstm=False, lite=False, output_dir="reports")
        assert cmd_report(args) == 0


# ---------------------------------------------------------------------------
# cmd_predict
# ---------------------------------------------------------------------------

class TestCmdPredict:
    def test_returns_zero(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.load_ohlcv",
                            lambda csv_path, ticker, period: make_synthetic_ohlcv(360))
        monkeypatch.setattr("stock_rtx4060.main.EnsemblePredictor", _FakeModel)
        args = argparse.Namespace(ticker="AAPL", csv=None, period="3y",
                                  horizon=5, prefer_gpu=False, use_lstm=False, lite=True)
        assert cmd_predict(args) == 0

    def test_json_on_stdout(self, monkeypatch, capsys):
        monkeypatch.setattr("stock_rtx4060.main.load_ohlcv",
                            lambda csv_path, ticker, period: make_synthetic_ohlcv(360))
        monkeypatch.setattr("stock_rtx4060.main.EnsemblePredictor", _FakeModel)
        args = argparse.Namespace(ticker="AAPL", csv=None, period="3y",
                                  horizon=5, prefer_gpu=False, use_lstm=False, lite=True)
        cmd_predict(args)
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "latest" in parsed
        assert "direction_prob" in parsed["latest"]


# ---------------------------------------------------------------------------
# cmd_recommend
# ---------------------------------------------------------------------------

class TestCmdRecommend:
    def _args(self, **overrides):
        base = dict(
            universe="SYNTH-A,SYNTH-B",
            track="BOTH",
            period="3y",
            top=2,
            synthetic=True,
            data_provider="synthetic",
            provider_config=None,
            kevpe_events=None,
            capital=100_000.0,
            prefer_gpu=False,
            full=False,
            model_kind="logistic",
            xgb_device="cpu",
            cv_gap=5,
            output_dir="reports/test",
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_returns_zero_with_results(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.RecommendationEngine", _FakeRecommendationEngine)
        assert cmd_recommend(self._args()) == 0

    def test_returns_one_empty_results(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.RecommendationEngine", _FakeEmptyEngine)
        assert cmd_recommend(self._args()) == 1

    def test_prefer_gpu_switches_model_to_xgb(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.RecommendationEngine", _FakeRecommendationEngine)
        assert cmd_recommend(self._args(prefer_gpu=True, model_kind="logistic")) == 0

    def test_none_universe_uses_default(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.RecommendationEngine", _FakeRecommendationEngine)
        assert cmd_recommend(self._args(universe=None)) == 0


# ---------------------------------------------------------------------------
# cmd_paper_run
# ---------------------------------------------------------------------------

class TestCmdPaperRun:
    def _args(self, **overrides):
        base = dict(
            universe="SYNTH-A",
            track="BOTH",
            period="3y",
            top=1,
            synthetic=True,
            data_provider="synthetic",
            provider_config=None,
            kevpe_events=None,
            capital=100_000.0,
            prefer_gpu=False,
            full=False,
            model_kind="logistic",
            xgb_device="cpu",
            cv_gap=5,
            output_dir="reports/test",
            output_root="reports/paper_trading/runs",
            run_date=None,
            force_rerun=False,
            rerun_reason=None,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_synthetic_path_returns_zero(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.RecommendationEngine", _FakeRecommendationEngine)
        monkeypatch.setattr("stock_rtx4060.main.PaperTradingEngine", _FakePaperEngine)
        assert cmd_paper_run(self._args()) == 0

    def test_yfinance_error_returns_zero(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.RecommendationEngine", _FakeRecommendationEngine)
        monkeypatch.setattr("stock_rtx4060.main.PaperTradingEngine", _FakePaperEngine)
        fake_yf = types.ModuleType("yfinance")

        def _raise_dl(*a, **kw):
            raise RuntimeError("no net")

        fake_yf.download = _raise_dl
        monkeypatch.setitem(sys.modules, "yfinance", fake_yf)
        args = self._args(synthetic=False)
        # bars_by_ticker will be empty for failing tickers; run still succeeds
        assert cmd_paper_run(args) == 0

    def test_run_date_override(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.RecommendationEngine", _FakeRecommendationEngine)
        captured = {}
        class _CapturingEngine(_FakePaperEngine):
            def __init__(self, config):
                captured["run_date"] = config.run_date
        monkeypatch.setattr("stock_rtx4060.main.PaperTradingEngine", _CapturingEngine)
        cmd_paper_run(self._args(run_date="2026-01-15"))
        assert captured["run_date"] == "2026-01-15"


# ---------------------------------------------------------------------------
# cmd_ops_v1
# ---------------------------------------------------------------------------

class TestCmdOpsV1:
    def _args(self):
        return argparse.Namespace(
            universe="SYNTH-A,SYNTH-B",
            track="BOTH",
            period="3y",
            top=2,
            synthetic=True,
            data_provider="synthetic",
            provider_config=None,
            kevpe_events=None,
            capital=100_000.0,
            prefer_gpu=False,
            full=False,
            model_kind="logistic",
            xgb_device="cpu",
            cv_gap=5,
            output_dir="reports/ops_test",
        )

    def test_returns_zero(self, monkeypatch):
        monkeypatch.setattr(
            "stock_rtx4060.main.run_ops_v1_workflow",
            lambda config, output_dir: {"recommendation": "r.md", "ops_brief": "b.md"},
        )
        assert cmd_ops_v1(self._args()) == 0

    def test_prefer_gpu_model_kind_switch(self, monkeypatch):
        captured = {}

        def _fake_workflow(config, output_dir):
            captured["model_kind"] = config.model_kind
            return {"recommendation": "r.md"}

        monkeypatch.setattr("stock_rtx4060.main.run_ops_v1_workflow", _fake_workflow)
        args = self._args()
        args.prefer_gpu = True
        args.model_kind = "logistic"
        cmd_ops_v1(args)
        assert captured["model_kind"] == "xgb"


# ---------------------------------------------------------------------------
# cmd_dashboard_export
# ---------------------------------------------------------------------------

class TestCmdDashboardExport:
    def test_without_public_dir(self, monkeypatch, tmp_path):
        snap = tmp_path / "snap.json"
        monkeypatch.setattr(
            "stock_rtx4060.main.write_dashboard_snapshot",
            lambda rec_json, output: snap,
        )
        args = argparse.Namespace(
            recommendation_json="r.json",
            output=str(snap),
            public_dir=None,
            approval_journal=None,
        )
        assert cmd_dashboard_export(args) == 0

    def test_with_public_dir(self, monkeypatch, tmp_path):
        snap = tmp_path / "snap.json"
        monkeypatch.setattr(
            "stock_rtx4060.main.write_dashboard_snapshot",
            lambda rec_json, output: snap,
        )
        import stock_rtx4060.dashboard_bridge as _db  # ensure module loaded before patch
        monkeypatch.setattr(_db, "export_dashboard_public_assets",
                            lambda *a, **kw: {"snapshot": str(snap)})
        pub_dir = str(tmp_path / "public")
        args = argparse.Namespace(
            recommendation_json="r.json",
            output=str(snap),
            public_dir=pub_dir,
            approval_journal=None,
        )
        assert cmd_dashboard_export(args) == 0

    def test_output_none_uses_default(self, monkeypatch, tmp_path):
        snap = tmp_path / "snap.json"
        monkeypatch.setattr(
            "stock_rtx4060.main.write_dashboard_snapshot",
            lambda rec_json, output: snap,
        )
        args = argparse.Namespace(
            recommendation_json="r.json",
            output=None,
            public_dir=None,
            approval_journal=None,
        )
        assert cmd_dashboard_export(args) == 0


# ---------------------------------------------------------------------------
# cmd_demo
# ---------------------------------------------------------------------------

class TestCmdDemo:
    def test_returns_zero(self, monkeypatch, tmp_path):
        monkeypatch.setattr("stock_rtx4060.main.cmd_report", lambda args: 0)
        args = argparse.Namespace(workspace=str(tmp_path / "demo_ws"))
        assert cmd_demo(args) == 0

    def test_creates_csv_before_calling_report(self, monkeypatch, tmp_path):
        received = {}

        def _fake_report(args):
            received["csv"] = args.csv
            return 0

        monkeypatch.setattr("stock_rtx4060.main.cmd_report", _fake_report)
        args = argparse.Namespace(workspace=str(tmp_path / "ws"))
        cmd_demo(args)
        assert received.get("csv") is not None
        assert Path(received["csv"]).exists()


# ---------------------------------------------------------------------------
# cmd_journal
# ---------------------------------------------------------------------------

class TestCmdJournal:
    def test_returns_zero(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.ReportWriter", _FakeReportWriter)
        args = argparse.Namespace(
            output_dir="reports",
            ticker="AAPL",
            track="S",
            action="WATCH",
            reason="test reason",
            entry=150.0,
            stop=145.0,
            target=160.0,
            quantity=10,
        )
        assert cmd_journal(args) == 0

    def test_calls_journal_append(self, monkeypatch):
        calls = []

        class _CapturingWriter(_FakeReportWriter):
            def journal_append(self, row):
                calls.append(row)
                return "reports/journal.csv"

        monkeypatch.setattr("stock_rtx4060.main.ReportWriter", _CapturingWriter)
        args = argparse.Namespace(
            output_dir="reports",
            ticker="NVDA",
            track="L",
            action="ACCUMULATE",
            reason="strong fundamentals",
            entry=200.0,
            stop=190.0,
            target=250.0,
            quantity=5,
        )
        cmd_journal(args)
        assert len(calls) == 1
        assert calls[0]["ticker"] == "NVDA"


# ---------------------------------------------------------------------------
# cmd_self_test
# ---------------------------------------------------------------------------

class TestCmdSelfTest:
    def test_returns_zero(self):
        assert cmd_self_test() == 0


# ---------------------------------------------------------------------------
# main() dispatch
# ---------------------------------------------------------------------------

class TestMainDispatch:
    def _stub_all(self, monkeypatch):
        for cmd in [
            "cmd_env", "cmd_benchmark", "cmd_report", "cmd_predict",
            "cmd_recommend", "cmd_paper_run", "cmd_ops_v1",
            "cmd_dashboard_export", "cmd_demo", "cmd_journal",
        ]:
            monkeypatch.setattr(f"stock_rtx4060.main.{cmd}", lambda args: 0)
        monkeypatch.setattr("stock_rtx4060.main.cmd_self_test", lambda: 0)

    def test_self_test_dispatch(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.cmd_self_test", lambda: 0)
        assert main(["self-test"]) == 0

    def test_env_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(["env"]) == 0

    def test_benchmark_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(["benchmark"]) == 0

    def test_predict_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(["predict", "--ticker", "AAPL"]) == 0

    def test_recommend_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(["recommend"]) == 0

    def test_ops_v1_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(["ops-v1"]) == 0

    def test_paper_run_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(["paper-run"]) == 0

    def test_demo_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(["demo"]) == 0

    def test_journal_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(
            ["journal", "--ticker", "AAPL", "--track", "S", "--action", "BUY", "--reason", "test"]
        ) == 0

    def test_exception_in_cmd_returns_1(self, monkeypatch):
        def _explode(args):
            raise RuntimeError("boom")

        monkeypatch.setattr("stock_rtx4060.main.cmd_env", _explode)
        assert main(["env"]) == 1

    def test_no_command_defaults_to_self_test(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.cmd_self_test", lambda: 0)
        assert main([]) == 0

    def test_legacy_test_flag_routes_to_self_test(self, monkeypatch):
        monkeypatch.setattr("stock_rtx4060.main.cmd_self_test", lambda: 0)
        assert main(["--test"]) == 0

    def test_report_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(["report"]) == 0

    def test_dashboard_export_dispatch(self, monkeypatch):
        self._stub_all(monkeypatch)
        assert main(["dashboard-export", "--recommendation-json", "r.json"]) == 0
