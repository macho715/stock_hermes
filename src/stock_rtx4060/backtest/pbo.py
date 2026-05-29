"""PBO report helpers for CPCV path diagnostics."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .stat_tests import probability_of_backtest_overfitting


def build_pbo_report(
    *,
    ticker: str,
    sharpe_paths: list[float],
    max_pbo: float = 0.20,
) -> dict[str, Any]:
    pbo = probability_of_backtest_overfitting([float(value) for value in sharpe_paths])
    return {
        "schema_version": "pbo_report.v1",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "ticker": ticker,
        "pbo": pbo,
        "max_pbo": max_pbo,
        "status": "PASS" if pbo <= max_pbo else "AMBER",
        "sharpe_paths": [float(value) for value in sharpe_paths],
        "report_only": True,
    }


def write_pbo_report(path: str | Path, **kwargs: Any) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_pbo_report(**kwargs), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
