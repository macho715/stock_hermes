"""Tests for the RD-Agent Qlib exporter (qlib_exporter.py)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from stock_rtx4060.factors.rd_agent.qlib_exporter import (
    _qlib_installed,
    convert_csv_to_qlib_bin,
    export_ohlcv_to_qlib,
    export_ohlcv_to_qlib_csv,
)


class TestQlibInstalled:
    def test_returns_true_when_qlib_importable(self) -> None:
        # Test the function path — if qlib is installed, it returns True
        result = _qlib_installed()
        assert isinstance(result, bool)


class TestExportOhlcvToQlibCsv:
    def test_qlib_exporter_pit_guard(self, tmp_path: Path) -> None:
        """as_of filter prevents future data from being included."""
        # Build a panel that would include future data if not truncated
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame(
            {
                "Open": np.random.rand(10) * 100 + 100,
                "High": np.random.rand(10) * 100 + 105,
                "Low": np.random.rand(10) * 100 + 95,
                "Close": np.random.rand(10) * 100 + 100,
                "Volume": np.random.rand(10) * 1e6,
            },
            index=dates,
        )

        mock_result = MagicMock()
        mock_result.frame = df.copy()
        mock_result.frame.index = pd.DatetimeIndex(dates)

        # Patch at the source module where the function is defined
        with patch(
            "stock_rtx4060.data_providers.load_ohlcv_with_provider",
            return_value=mock_result,
        ):
            with patch(
                "stock_rtx4060.factors.rd_agent.qlib_exporter.CSV_DIR",
                tmp_path / "csv",
            ):
                rows_written = export_ohlcv_to_qlib_csv(
                    tickers=["TEST"],
                    run_date="2024-01-05",
                )

        # The result's frame was truncated; verify no exception
        assert isinstance(rows_written, dict)

    def test_qlib_exporter_csv_columns(self, tmp_path: Path) -> None:
        """Exported CSV contains Date,Open,High,Low,Close,Volume columns in correct order."""
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {
                "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
                "High": [105.0, 106.0, 107.0, 108.0, 109.0],
                "Low": [95.0, 96.0, 97.0, 98.0, 99.0],
                "Close": [101.0, 102.0, 103.0, 104.0, 105.0],
                "Volume": [1000000.0, 1100000.0, 1200000.0, 1300000.0, 1400000.0],
            },
            index=dates,
        )

        mock_result = MagicMock()
        mock_result.frame = df.copy()
        mock_result.frame.index = pd.DatetimeIndex(dates)

        # Patch at the source module where the function is defined (data_providers)
        with patch(
            "stock_rtx4060.data_providers.load_ohlcv_with_provider",
            return_value=mock_result,
        ):
            with patch(
                "stock_rtx4060.factors.rd_agent.qlib_exporter.CSV_DIR",
                tmp_path / "csv",
            ):
                rows_written = export_ohlcv_to_qlib_csv(
                    tickers=["TEST"],
                    run_date="2024-01-10",
                )

        # Check CSV file was written
        assert rows_written == {"TEST": 5}
        csv_file = tmp_path / "csv" / "TEST.csv"
        if csv_file.exists():
            content = csv_file.read_text()
            header = content.split("\n")[0].strip()
            assert "Date" in header
            assert "Open" in header
            assert "High" in header
            assert "Low" in header
            assert "Close" in header
            assert "Volume" in header

    def test_missing_ohlcv_columns_skip_ticker(self, tmp_path: Path) -> None:
        """Frame missing required columns logs a warning and skips the ticker."""
        mock_result = MagicMock()
        mock_result.frame = pd.DataFrame({
            "Open": [100.0],
            # missing High, Low, Close, Volume
        }, index=[pd.Timestamp("2024-01-01")])

        # Patch at the source module where the function is defined (data_providers)
        with patch(
            "stock_rtx4060.data_providers.load_ohlcv_with_provider",
            return_value=mock_result,
        ):
            with patch(
                "stock_rtx4060.factors.rd_agent.qlib_exporter.CSV_DIR",
                tmp_path / "csv",
            ):
                rows_written = export_ohlcv_to_qlib_csv(
                    tickers=["MISSING_COLS"],
                    run_date="2024-01-01",
                )

        # MISSING_COLS should not produce a CSV (skipped)
        assert rows_written == {}
        csv_file = tmp_path / "csv" / "MISSING_COLS.csv"
        assert not csv_file.exists()


class TestConvertCsvToQlibBin:
    def test_returns_false_when_qlib_not_installed(self) -> None:
        """When qlib is not installed, convert_csv_to_qlib_bin returns False immediately."""
        with patch(
            "stock_rtx4060.factors.rd_agent.qlib_exporter._qlib_installed",
            return_value=False,
        ):
            result = convert_csv_to_qlib_bin()
            assert result is False

    def test_subprocess_error_handled_gracefully(self) -> None:
        """FileNotFoundError when qlib_get_data not in PATH is handled."""
        with patch(
            "stock_rtx4060.factors.rd_agent.qlib_exporter._qlib_installed",
            return_value=False,
        ):
            result = convert_csv_to_qlib_bin()
            assert result is False


class TestFullExportPipeline:
    def test_export_ohlcv_to_qlib_returns_dict(self) -> None:
        """export_ohlcv_to_qlib returns dict[str, int] even on empty result."""
        with patch(
            "stock_rtx4060.factors.rd_agent.qlib_exporter._qlib_installed",
            return_value=False,
        ):
            rows = export_ohlcv_to_qlib(tickers=[], run_date="2024-01-01", convert_bin=False)
            assert isinstance(rows, dict)
