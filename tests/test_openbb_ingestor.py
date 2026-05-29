"""Tests for OpenBB macro ingestor + paper_trading chaos boundaries."""
from __future__ import annotations

import logging
import os
import py_compile

import pytest

from stock_rtx4060.data_lake.ingest import openbb_ingestor
from stock_rtx4060.paper_trading import PaperTradingConfig, PaperTradingEngine, PaperTradingSignal

# =====================================================================
# PR-O: OpenBB Macro Ingestor
# =====================================================================

class TestOpenBBIngestor:
    """OpenBB ingestor graceful-degradation coverage."""

    def test_openbb_module_compiles(self):
        """openbb_ingestor.py must compile without import errors."""
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "src", "stock_rtx4060", "data_lake", "ingest", "openbb_ingestor.py"
        )
        assert os.path.exists(path), f"openbb_ingestor.py not found at {path}"
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as exc:
            pytest.fail(f"openbb_ingestor.py does not compile: {exc}")

    def test_ingest_openbb_graceful_degradation_no_openbb(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ):
        """OpenBB unavailable → warning log + return 0, no crash."""
        monkeypatch.setattr(openbb_ingestor, "_openbb_available", lambda: False)

        with caplog.at_level(logging.WARNING):
            assert openbb_ingestor.ingest_openbb_macro() == 0

        assert "openbb not installed" in caplog.text

    def test_ingest_openbb_no_hard_dependency_in_trading_path(self, monkeypatch: pytest.MonkeyPatch):
        """ingest_openbb_macro must not crash when OpenBB is absent."""
        monkeypatch.setattr(openbb_ingestor, "_openbb_available", lambda: False)

        assert openbb_ingestor.ingest_openbb_macro(store=None) == 0


# =====================================================================
# PR-C: paper_trading chaos — RED (using actual API from codebase)
# =====================================================================

class TestChaosPaperTradingRealAPI:
    """Chaos tests using actual PaperTradingSignal / PaperTradingConfig fields.

    The real signal is a frozen dataclass:
      ticker, score, signal, model_auc, model_accuracy, oof_coverage, warning

    The real config has:
      max_open_positions: int | None = None  (default: None = unlimited)
      max_daily_new_positions: int | None = None  (default: None = unlimited)
      min_buy_score: float = 56.0
      stale_days: int = 10
      max_missing_bar_ratio: float = 0.05
    """

    def test_chaos_reject_signal_without_model_auc(self):
        """PR-C1: signal with model_auc=None → rejected by engine."""
        config = PaperTradingConfig(min_buy_score=56.0)
        signal = PaperTradingSignal(
            ticker="AAPL",
            score=60.0,
            signal="buy",
            model_auc=None,        # missing → reject
            model_accuracy=0.55,
            oof_coverage=0.90,
        )
        engine = PaperTradingEngine(config)
        decision = engine.evaluate_signal(signal, bars=None)
        assert decision.status == "REJECTED"
        assert "model_evidence_missing" in decision.reason

    def test_chaos_reject_signal_without_model_accuracy(self):
        """PR-C2: signal with model_accuracy=None → rejected."""
        config = PaperTradingConfig(min_buy_score=56.0)
        signal = PaperTradingSignal(
            ticker="AAPL",
            score=60.0,
            signal="buy",
            model_auc=0.60,
            model_accuracy=None,   # missing → reject
            oof_coverage=0.90,
        )
        engine = PaperTradingEngine(config)
        decision = engine.evaluate_signal(signal, bars=None)
        assert decision.status == "REJECTED"
        assert "model_evidence_missing" in decision.reason

    def test_chaos_reject_signal_without_oof_coverage(self):
        """PR-C3: signal with oof_coverage=None → rejected."""
        config = PaperTradingConfig(min_buy_score=56.0)
        signal = PaperTradingSignal(
            ticker="AAPL",
            score=60.0,
            signal="buy",
            model_auc=0.60,
            model_accuracy=0.55,
            oof_coverage=None,     # missing → reject
        )
        engine = PaperTradingEngine(config)
        decision = engine.evaluate_signal(signal, bars=None)
        assert decision.status == "REJECTED"

    def test_chaos_accept_valid_signal(self):
        """PR-C4: valid signal with all model evidence + valid bars → accepted."""
        config = PaperTradingConfig(min_buy_score=56.0)
        signal = PaperTradingSignal(
            ticker="AAPL",
            score=60.0,
            signal="buy",
            model_auc=0.60,
            model_accuracy=0.55,
            oof_coverage=0.90,
        )
        # Valid bars (non-empty, with proper OHLCV) needed to pass _validate_bars
        valid_bars = [
            {"date": "2026-05-25", "open": 190.0, "high": 195.0, "low": 189.0, "close": 193.0, "volume": 50_000_000},
            {"date": "2026-05-26", "open": 193.0, "high": 196.0, "low": 192.0, "close": 194.0, "volume": 48_000_000},
        ]
        engine = PaperTradingEngine(config)
        decision = engine.evaluate_signal(signal, bars=valid_bars)
        assert decision.status == "ACCEPTED", f"Expected ACCEPTED but got {decision.status}: {decision.reason}"

    def test_chaos_reject_weak_model_quality_warning(self):
        """PR-C5: signal.warning containing '모델 품질 낮음' → rejected."""
        config = PaperTradingConfig(min_buy_score=56.0)
        signal = PaperTradingSignal(
            ticker="AAPL",
            score=60.0,
            signal="buy",
            model_auc=0.60,
            model_accuracy=0.55,
            oof_coverage=0.90,
            warning="모델 품질 낮음: auc < 0.55",
        )
        engine = PaperTradingEngine(config)
        decision = engine.evaluate_signal(signal, bars=None)
        assert decision.status == "REJECTED"
        assert "weak_model_quality" in decision.reason

    def test_chaos_reject_krx_ticker_when_us_only(self):
        """PR-C6: KRX ticker (.KS/.KQ suffix) rejected when phase1_us_only=True."""
        config = PaperTradingConfig(phase1_us_only=True)
        signal = PaperTradingSignal(
            ticker="005930.KS",   # KRX ticker with .KS suffix
            score=60.0,
            signal="buy",
            model_auc=0.60,
            model_accuracy=0.55,
            oof_coverage=0.90,
        )
        valid_bars = [
            {"date": "2026-05-25", "open": 58000, "high": 59000, "low": 57500, "close": 58500, "volume": 30_000_000},
        ]
        engine = PaperTradingEngine(config)
        decision = engine.evaluate_signal(signal, bars=valid_bars)
        assert decision.status == "REJECTED"
        assert "market_not_enabled_phase1" in decision.reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
