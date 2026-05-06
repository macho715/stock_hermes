"""Evidence-only backtest honesty checks for report-only recommendations."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any, Literal

HonestyStatus = Literal["PASS", "AMBER", "FAIL"]

STATUS_ORDER: dict[str, int] = {"PASS": 0, "AMBER": 1, "FAIL": 2}


def evaluate_backtest_honesty(
    *,
    oof_coverage: float | None,
    min_oof_coverage: float,
    sharpe: float | None,
    min_sharpe: float,
    mdd_pct: float | None,
    max_mdd_pct: float,
    total_return_pct: float | None,
    transaction_cost_buffer_pct: float,
    cv_gap: int | None,
    horizon: int,
) -> dict[str, Any]:
    """Return additive PASS/AMBER/FAIL evidence without changing ranking."""

    checks = [
        _numeric_floor_check(
            name="OOF_COVERAGE",
            value=oof_coverage,
            threshold=min_oof_coverage,
            unit="ratio",
            fail_below=min_oof_coverage * 0.50,
        ),
        _numeric_floor_check(
            name="SHARPE_FLOOR",
            value=sharpe,
            threshold=min_sharpe,
            unit="ratio",
            fail_below=min_sharpe - 1.0,
        ),
        _drawdown_check(mdd_pct=mdd_pct, max_mdd_pct=max_mdd_pct),
        _cost_buffer_check(total_return_pct=total_return_pct, transaction_cost_buffer_pct=transaction_cost_buffer_pct),
        _walk_forward_gap_check(cv_gap=cv_gap, horizon=horizon),
    ]
    status = _worst_status(check["status"] for check in checks)
    return {
        "status": status,
        "checks": checks,
        "passed": sum(1 for check in checks if check["status"] == "PASS"),
        "amber": sum(1 for check in checks if check["status"] == "AMBER"),
        "failed": sum(1 for check in checks if check["status"] == "FAIL"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def summarize_honesty(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate result-level honesty evidence into a run-level summary."""

    statuses = [str(item.get("status", "AMBER")) for item in items]
    checks = [check for item in items for check in item.get("checks", []) if isinstance(check, dict)]
    return {
        "status": _worst_status(statuses),
        "result_count": len(items),
        "passed": sum(1 for check in checks if check.get("status") == "PASS"),
        "amber": sum(1 for check in checks if check.get("status") == "AMBER"),
        "failed": sum(1 for check in checks if check.get("status") == "FAIL"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _numeric_floor_check(
    *,
    name: str,
    value: float | None,
    threshold: float,
    unit: str,
    fail_below: float,
) -> dict[str, Any]:
    if not _valid_number(value):
        return _check(name, "AMBER", value, threshold, f"{name.lower()} missing; cannot verify honesty evidence")
    status: HonestyStatus = "PASS"
    if float(value) < fail_below:
        status = "FAIL"
    elif float(value) < threshold:
        status = "AMBER"
    return _check(name, status, value, threshold, f"{name.lower()}={_fmt(value, unit)}, threshold={_fmt(threshold, unit)}")


def _drawdown_check(*, mdd_pct: float | None, max_mdd_pct: float) -> dict[str, Any]:
    if not _valid_number(mdd_pct):
        return _check("MAX_DRAWDOWN", "AMBER", mdd_pct, max_mdd_pct, "max drawdown missing; cannot verify drawdown honesty")
    status: HonestyStatus = "PASS" if float(mdd_pct) <= max_mdd_pct else "FAIL"
    return _check("MAX_DRAWDOWN", status, mdd_pct, max_mdd_pct, f"mdd={float(mdd_pct):.2f}%, max={max_mdd_pct:.2f}%")


def _cost_buffer_check(*, total_return_pct: float | None, transaction_cost_buffer_pct: float) -> dict[str, Any]:
    if not _valid_number(total_return_pct):
        return _check("TRANSACTION_COST_BUFFER", "AMBER", total_return_pct, transaction_cost_buffer_pct, "return missing; cannot verify cost buffer")
    status: HonestyStatus = "PASS" if float(total_return_pct) >= transaction_cost_buffer_pct else "AMBER"
    return _check(
        "TRANSACTION_COST_BUFFER",
        status,
        total_return_pct,
        transaction_cost_buffer_pct,
        f"return={float(total_return_pct):.2f}%, buffer={transaction_cost_buffer_pct:.2f}%",
    )


def _walk_forward_gap_check(*, cv_gap: int | None, horizon: int) -> dict[str, Any]:
    if cv_gap is None:
        return _check("WALK_FORWARD_GAP", "AMBER", cv_gap, horizon, "cv_gap missing; cannot verify purge gap")
    status: HonestyStatus = "PASS" if int(cv_gap) >= int(horizon) else "AMBER"
    return _check("WALK_FORWARD_GAP", status, cv_gap, horizon, f"gap={cv_gap}, horizon={horizon}")


def _check(name: str, status: HonestyStatus, value: Any, threshold: Any, reason: str) -> dict[str, Any]:
    return {"name": name, "status": status, "value": value, "threshold": threshold, "reason": reason}


def _worst_status(statuses: Any) -> HonestyStatus:
    values = [str(status) for status in statuses]
    if not values:
        return "AMBER"
    return max(values, key=lambda status: STATUS_ORDER.get(status, 1))  # type: ignore[return-value]


def _valid_number(value: float | None) -> bool:
    return value is not None and isfinite(float(value))


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return "missing"
    if unit == "ratio":
        return f"{float(value):.2%}"
    return f"{float(value):.3f}"
