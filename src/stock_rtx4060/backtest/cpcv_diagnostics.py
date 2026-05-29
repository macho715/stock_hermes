"""CPCV path diagnostics for live-review evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
from typing import Any


def build_cpcv_report(
    *,
    ticker: str,
    sharpe_paths: list[float],
    pass_threshold: float = 0.0,
    min_pass_rate: float = 0.60,
) -> dict[str, Any]:
    paths = [float(value) for value in sharpe_paths if isfinite(float(value))]
    passed = sum(1 for value in paths if value > pass_threshold)
    path_count = len(paths)
    pass_rate = passed / path_count if path_count else 0.0
    return {
        "schema_version": "cpcv_report.v1",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "ticker": ticker,
        "path_count": path_count,
        "pass_threshold": pass_threshold,
        "passed_paths": passed,
        "failed_paths": path_count - passed,
        "pass_rate": pass_rate,
        "min_pass_rate": min_pass_rate,
        "status": "PASS" if pass_rate >= min_pass_rate else "AMBER",
        "sharpe_paths": paths,
        "report_only": True,
    }


def write_cpcv_report(path: str | Path, **kwargs: Any) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_cpcv_report(**kwargs), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
