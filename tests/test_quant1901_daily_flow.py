"""Smoke tests for the quant1901 daily Prefect flow.

Uses synthetic OHLCV data (dry_run=True) to avoid network calls and
verify the flow contract without requiring a live data provider or
Prefect server.

Run:
    PYTHONPATH=src pytest tests/test_quant1901_daily_flow.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT / "quant1901_executable_bundle")):
    if p not in sys.path:
        sys.path.insert(0, p)

from quant1901_executor import make_synthetic_ohlcv  # noqa: E402
from stock_rtx4060.backtest.quant1901_runner import Quant1901Runner  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────
def _run_flow_directly(tickers: list[str], tmp_path: Path) -> dict:
    """Call the flow function directly (bypasses Prefect scheduler)."""
    from flows.quant1901_daily import quant1901_daily_flow  # noqa: PLC0415

    # Patch load_ohlcv_with_provider to return synthetic data
    df = make_synthetic_ohlcv(rows=200, seed=1901)
    mock_provider_result = MagicMock()
    mock_provider_result.frame = df
    mock_provider_result.source = "synthetic_test"

    with patch(
        "stock_rtx4060.data_providers.load_ohlcv_with_provider",
        return_value=mock_provider_result,
    ), patch(
        "stock_rtx4060.backtest.quant1901_runner.Quant1901Runner",
        return_value=Quant1901Runner(),
    ):
        return quant1901_daily_flow(
            universe=tickers,
            period="2y",
            optimize=False,
            dry_run=True,
            output_dir=str(tmp_path),
        )


# ── tests ────────────────────────────────────────────────────────────────────
def test_flow_returns_summary_dict(tmp_path):
    result = _run_flow_directly(["SYNTH_TEST"], tmp_path)
    assert isinstance(result, dict)
    assert "results" in result
    assert "SYNTH_TEST" in result["results"]


def test_flow_dry_run_true_by_default(tmp_path):
    result = _run_flow_directly(["SYNTH_TEST"], tmp_path)
    assert result["dry_run"] is True


def test_flow_writes_snapshot_json(tmp_path):
    result = _run_flow_directly(["SYNTH_TEST"], tmp_path)
    ticker_result = result["results"]["SYNTH_TEST"]
    assert ticker_result["status"] == "OK"
    assert ticker_result["output_path"] is not None
    out_path = Path(ticker_result["output_path"])
    assert out_path.exists()
    snap = json.loads(out_path.read_text(encoding="utf-8"))
    assert snap["schema_version"] == "dashboard_snapshot.v1"


def test_flow_execution_controls_always_locked(tmp_path):
    result = _run_flow_directly(["SYNTH_TEST"], tmp_path)
    ticker_result = result["results"]["SYNTH_TEST"]
    assert ticker_result["live_trading_allowed"] is False
    assert ticker_result["broker_execution_allowed"] is False


def test_flow_handles_individual_ticker_failure_gracefully(tmp_path):
    """A failing ticker must not abort the whole flow."""
    from flows.quant1901_daily import quant1901_daily_flow  # noqa: PLC0415

    df = make_synthetic_ohlcv(rows=200, seed=1901)
    mock_ok = MagicMock()
    mock_ok.frame = df
    mock_ok.source = "synthetic_test"

    call_count = [0]

    def side_effect(ticker, *args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("simulated provider failure")
        return mock_ok

    with patch(
        "stock_rtx4060.data_providers.load_ohlcv_with_provider",
        side_effect=side_effect,
    ), patch(
        "stock_rtx4060.backtest.quant1901_runner.Quant1901Runner",
        return_value=Quant1901Runner(),
    ):
        result = quant1901_daily_flow(
            universe=["FAIL_TICKER", "OK_TICKER"],
            period="2y",
            optimize=False,
            dry_run=True,
            output_dir=str(tmp_path),
        )

    assert result["results"]["FAIL_TICKER"]["status"] == "ERROR"
    assert result["results"]["OK_TICKER"]["status"] == "OK"


def test_flow_compile():
    """Syntax check for the flow module itself."""
    import py_compile  # noqa: PLC0415

    flow_path = ROOT / "flows" / "quant1901_daily.py"
    py_compile.compile(str(flow_path), doraise=True)
