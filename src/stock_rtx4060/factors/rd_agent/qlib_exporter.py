"""DuckDB OHLCV → Qlib CSV → Qlib bin conversion for RD-Agent.

This exporter bridges the PIT-correct DuckDB data lake to Qlib's binary format,
which is required by the ``rdagent fin_factor`` subcommand.

Pipeline
---------
1. Load OHLCV from DuckDB via ``load_ohlcv_with_provider(as_of=run_date)``.
   The PIT as_of guard is enforced at the data_lake level — data with
   ``_ingested_at > run_date`` is never returned.
2. Write per-ticker CSV files to ``~/.qlib/csv_data/stock1901/``.
   Columns: Date,Open,High,Low,Close,Volume  (Qlib convention).
3. Run ``qlib_get_data`` CLI to convert CSV → bin format in-place,
   producing ``~/.qlib/qlib_data/stock1901/``.

Graceful degradation
--------------------
If ``qlib`` is not installed, step 3 is skipped and a warning is logged.
The CSV layer (``~/.qlib/csv_data/stock1901/``) is still produced so the
user can manually run the bin conversion later.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from datetime import date
from importlib.util import find_spec
from pathlib import Path

import numpy as np
import pandas as pd

_logger = logging.getLogger(__name__)

# Qlib directory layout
QLIB_HOME = Path.home() / ".qlib"
CSV_DIR = QLIB_HOME / "csv_data" / "stock1901"
BIN_DIR = QLIB_HOME / "qlib_data" / "stock1901"

# Expected OHLCV columns from the data lake (flat single-ticker frame)
_OHLCV_COLS = ["Open", "High", "Low", "Close", "Volume"]


def _qlib_installed() -> bool:
    return find_spec("qlib") is not None


def _qlib_get_data_available() -> bool:
    return find_spec("qlib_get_data") is not None or shutil.which("qlib_get_data") is not None


def export_ohlcv_to_qlib_csv(
    tickers: list[str],
    run_date: str | date,
    *,
    data_lake_first: bool = True,
) -> dict[str, int]:
    """Export OHLCV data for ``tickers`` to Qlib CSV format.

    Parameters
    ----------
    tickers:
        List of ticker strings to export (e.g. ``["AAPL", "MSFT"]``).
    run_date:
        ISO date string (``YYYY-MM-DD``) or ``date`` object. Acts as the
        ``as_of`` point-in-time boundary — only data with
        ``_ingested_at <= run_date`` is included.
    data_lake_first:
        Passed through to ``load_ohlcv_with_provider``. When True the
        PIT-correct DuckDB lake is queried first.

    Returns
    -------
    dict[str, int]
        Mapping of ticker → number of rows written to CSV.

    Raises
    ------
    RuntimeError
        If ``load_ohlcv_with_provider`` raises due to a lake miss on an
        ``as_of`` query (PIT violation attempt).

    Notes
    -----
    - Each ticker produces one CSV file: ``<CSV_DIR>/<TICKER>.csv``.
    - The ``Date`` column is written as ``YYYY-MM-DD`` (no timezone).
    - Files are overwritten if they already exist.
    """
    from ...data_providers import load_ohlcv_with_provider

    run_ts = pd.Timestamp(run_date)
    rows_written: dict[str, int] = {}

    # Ensure output directory exists
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    for ticker in tickers:
        try:
            result = load_ohlcv_with_provider(
                ticker=ticker,
                period="max",  # let as_of truncate; no live fetch
                as_of=str(run_ts.date()),
                data_lake_first=data_lake_first,
            )
        except RuntimeError:
            # PIT guard: lake miss on as_of query → re-raise immediately
            _logger.error(
                "PIT violation: load_ohlcv_with_provider raised RuntimeError "
                "for ticker=%r as_of=%r. Check data_lake ingest status.",
                ticker,
                run_ts.date(),
            )
            raise

        frame = result.frame
        if frame.empty:
            _logger.warning("No data for ticker=%r as_of=%s — skipping", ticker, run_ts.date())
            continue

        # Verify required columns are present
        missing = [c for c in _OHLCV_COLS if c not in frame.columns]
        if missing:
            _logger.warning(
                "Ticker=%r frame missing columns %s — skipping (got %s)",
                ticker,
                missing,
                list(frame.columns),
            )
            continue

        # Select & order columns to match Qlib convention
        csv_frame = frame[_OHLCV_COLS].copy()

        # Cast datetime index to plain date string (no timezone), sorted ascending
        csv_frame.index = pd.to_datetime(csv_frame.index).strftime("%Y-%m-%d")
        csv_frame.index.name = "Date"

        out_path = CSV_DIR / f"{ticker}.csv"
        csv_frame.to_csv(out_path)
        rows_written[ticker] = len(csv_frame)
        _logger.debug("Wrote %d rows for ticker=%r → %s", len(csv_frame), ticker, out_path)

    return rows_written


def export_synthetic_ohlcv_to_qlib_csv(
    tickers: list[str],
    run_date: str | date,
    *,
    periods: int = 32,
) -> dict[str, int]:
    """Write deterministic synthetic OHLCV CSV files for RD-Agent smoke tests."""

    run_ts = pd.Timestamp(run_date)
    dates = pd.bdate_range(end=run_ts, periods=periods)
    rows_written: dict[str, int] = {}
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    for idx, ticker in enumerate(tickers):
        base = 100.0 + idx * 10.0
        steps = pd.Series(range(len(dates)), index=dates, dtype="float64")
        frame = pd.DataFrame(
            {
                "Open": base + steps * 0.10,
                "High": base + steps * 0.10 + 1.0,
                "Low": base + steps * 0.10 - 1.0,
                "Close": base + steps * 0.12,
                "Volume": 1_000_000.0 + steps * 1000.0,
            },
            index=dates,
        )
        frame.index = pd.to_datetime(frame.index).strftime("%Y-%m-%d")
        frame.index.name = "Date"
        frame.to_csv(CSV_DIR / f"{ticker}.csv")
        rows_written[ticker] = len(frame)

    return rows_written


def convert_csv_to_qlib_bin(
    calendar: str | None = None,
    symbol: str | None = None,
    include_fields: str = "open,high,low,close,volume",
    start_date: str | None = None,
    end_date: str | None = None,
    timeout_sec: int = 600,
) -> bool:
    """Run ``qlib_get_data`` to convert CSV → Qlib bin format.

    Parameters
    ----------
    calendar:
        Calendar name passed to ``qlib_get_data`` (e.g. ``cn``). If None,
        no ``--calendar`` flag is passed.
    symbol:
        Symbol (ticker) to convert. If None, all symbols in ``CSV_DIR`` are
        processed via the stock1901 provider config.
    include_fields:
        CSV columns to include in bin (passed as ``--include-fields``).
    start_date, end_date:
        Optional ISO date bounds for the bin conversion.
    timeout_sec:
        Seconds to wait before killing the subprocess. Default 600 (10 min).

    Returns
    -------
    bool
        True if the conversion succeeded (exit code 0), False otherwise.
        If ``qlib`` is not installed, returns False immediately.
    """
    if not _qlib_installed():
        _logger.warning(
            "qlib is not installed — skipping bin conversion. "
            "CSV data is available at %s. Install qlib to enable bin conversion: "
            "pip install pyqlib",
            CSV_DIR,
        )
        return False
    if not _qlib_get_data_available():
        _logger.warning(
            "qlib is installed but qlib_get_data is not available — skipping bin conversion. "
            "Using the local dump_bin-compatible fallback. CSV data is available at %s.",
            CSV_DIR,
        )
        return _convert_csv_to_minimal_qlib_bin()

    # Write qlib provider config for stock1901 CSV source
    _write_qlib_provider_config(CSV_DIR)

    try:
        cmd = [
            sys.executable,
            "-m",
            "qlib_get_data",
            "--provider_uri", "binary",
            "--source_dir", str(CSV_DIR),
        ]
        if calendar:
            cmd.extend(["--calendar", calendar])
        if symbol:
            cmd.extend(["--symbol", symbol])
        if include_fields:
            cmd.extend(["--include_fields", include_fields])
        if start_date:
            cmd.extend(["--start_date", start_date])
        if end_date:
            cmd.extend(["--end_date", end_date])

        _logger.info("Running Qlib bin conversion: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        if result.returncode == 0:
            _logger.info("Qlib bin conversion succeeded")
            return True
        else:
            _logger.error(
                "Qlib bin conversion failed (exit %d): %s",
                result.returncode,
                result.stderr[:500],
            )
            return False
    except subprocess.TimeoutExpired:
        _logger.error("Qlib bin conversion timed out after %d seconds", timeout_sec)
        return False
    except FileNotFoundError:
        _logger.warning(
            "qlib_get_data not found in PATH — skipping bin conversion. "
            "Using the local dump_bin-compatible fallback."
        )
        return _convert_csv_to_minimal_qlib_bin()


def _convert_csv_to_minimal_qlib_bin() -> bool:
    """Convert stock1901 CSV files into Qlib's file layout without dump_bin.py.

    This fallback mirrors the core binary layout used by Qlib's official
    ``scripts/dump_bin.py``: each feature file starts with the float date-index
    offset followed by little-endian float values for that feature.
    """

    csv_files = sorted(CSV_DIR.glob("*.csv"))
    if not csv_files:
        _logger.warning("No CSV files found at %s — skipping fallback bin conversion", CSV_DIR)
        return False

    raw_frames: dict[str, pd.DataFrame] = {}
    calendar_values: set[str] = set()
    for csv_file in csv_files:
        frame = pd.read_csv(csv_file)
        if "Date" not in frame.columns:
            _logger.warning("CSV file %s has no Date column — skipping", csv_file)
            continue
        frame["Date"] = pd.to_datetime(frame["Date"]).dt.strftime("%Y-%m-%d")
        missing = [col for col in _OHLCV_COLS if col not in frame.columns]
        if missing:
            _logger.warning("CSV file %s missing columns %s — skipping", csv_file, missing)
            continue
        symbol = csv_file.stem.lower()
        raw_frames[symbol] = frame[["Date", *_OHLCV_COLS]].copy()
        calendar_values.update(raw_frames[symbol]["Date"].tolist())

    if not raw_frames or not calendar_values:
        return False

    calendar = sorted(calendar_values)
    calendar_index = {value: idx for idx, value in enumerate(calendar)}
    calendar_dir = BIN_DIR / "calendars"
    instruments_dir = BIN_DIR / "instruments"
    features_dir = BIN_DIR / "features"
    calendar_dir.mkdir(parents=True, exist_ok=True)
    instruments_dir.mkdir(parents=True, exist_ok=True)
    features_dir.mkdir(parents=True, exist_ok=True)

    (calendar_dir / "day.txt").write_text("\n".join(calendar) + "\n", encoding="utf-8")
    instrument_lines: list[str] = []

    for symbol, frame in raw_frames.items():
        symbol_dir = features_dir / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)
        frame = frame.sort_values("Date")
        date_index = float(calendar_index[str(frame["Date"].iloc[0])])
        for field in _OHLCV_COLS:
            values = pd.to_numeric(frame[field], errors="coerce").to_numpy(dtype="float32")
            payload = np.hstack([[date_index], values]).astype("<f")
            payload.tofile(symbol_dir / f"{field.lower()}.day.bin")
        instrument_lines.append(f"{symbol}\t{frame['Date'].iloc[0]}\t{frame['Date'].iloc[-1]}")

    (instruments_dir / "all.txt").write_text("\n".join(instrument_lines) + "\n", encoding="utf-8")
    _logger.info("Qlib fallback bin conversion wrote %d instrument(s) to %s", len(instrument_lines), BIN_DIR)
    return True


def _write_qlib_provider_config(csv_dir: Path) -> None:
    """Write a qlib provider config that references our CSV directory as a custom source."""
    config_text = f"""# qlib provider config for stock1901 custom CSV data
# Auto-generated by stock_rtx4060.qlib_exporter — do not edit manually.

provider_uri: binary
csv_dir: {csv_dir}
market: custom
include_fields: open,high,low,close,volume
"""
    config_path = QLIB_HOME / "provider_config" / "stock1901.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_text, encoding="utf-8")
    _logger.debug("Wrote qlib provider config → %s", config_path)


def export_ohlcv_to_qlib(
    tickers: list[str],
    run_date: str | date,
    *,
    convert_bin: bool = True,
    data_lake_first: bool = True,
) -> dict[str, int]:
    """Full export pipeline: DuckDB → Qlib CSV → Qlib bin.

    This is the main entrypoint called by ``research_weekly_flow``.

    Parameters
    ----------
    tickers:
        List of ticker strings to export.
    run_date:
        ISO date string or date object used as the PIT as_of boundary.
    convert_bin:
        If True, run ``qlib_get_data`` after writing CSV files.
        If False, only produce CSV output.
    data_lake_first:
        Passed through to ``load_ohlcv_with_provider``.

    Returns
    -------
    dict[str, int]
        Mapping of ticker → rows written to CSV. Empty dict if qlib is
        not installed and ``convert_bin=False``.

    Examples
    --------
    >>> from stock_rtx4060.factors.rd_agent.qlib_exporter import export_ohlcv_to_qlib
    >>> rows = export_ohlcv_to_qlib(["AAPL", "MSFT"], "2026-05-25")
    >>> print(rows)
    {'AAPL': 5040, 'MSFT': 5040}
    """
    if not _qlib_installed():
        _logger.warning(
            "qlib not installed — bin conversion disabled. "
            "CSV data will be written to %s only.",
            CSV_DIR,
        )
        convert_bin = False

    csv_rows = export_ohlcv_to_qlib_csv(tickers, run_date, data_lake_first=data_lake_first)

    if not csv_rows:
        _logger.warning("No OHLCV data exported — skipping Qlib bin conversion")
        return csv_rows

    if convert_bin:
        success = convert_csv_to_qlib_bin()
        if not success:
            _logger.warning(
                "Qlib bin conversion reported errors — check log above. "
                "CSV files are still available at %s.",
                CSV_DIR,
            )

    return csv_rows


# ---------------------------------------------------------------------------
# Public API (matches plan.md F1 contract)
# ---------------------------------------------------------------------------
__all__ = [
    "export_ohlcv_to_qlib",
    "export_ohlcv_to_qlib_csv",
    "export_synthetic_ohlcv_to_qlib_csv",
    "convert_csv_to_qlib_bin",
    "_convert_csv_to_minimal_qlib_bin",
    "CSV_DIR",
    "BIN_DIR",
]
