"""Evidence-only backtest honesty checks for report-only recommendations."""

from __future__ import annotations

from datetime import UTC, datetime
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
    # v5.1 P1 additions — optional, None = not yet run
    cost_stress_result: dict[str, Any] | None = None,
    cpcv_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return additive PASS/AMBER/FAIL evidence without changing ranking.

    v5.1 additions (P1):
    - ``cost_stress_result``: output of :func:`run_cost_stress`.  When
      provided, a ``COST_STRESS`` check is added.
    - ``cpcv_result``: dict with keys ``pbo``, ``path_pass_rate``,
      ``deflated_sharpe``.  When provided, ``CPCV_PBO`` and ``CPCV_DSR``
      checks are added.
    """
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

    # v5.1 P1: cost stress check
    if cost_stress_result is not None:
        checks.append(_cost_stress_check(cost_stress_result))

    # v5.1 P1: CPCV/PBO/DSR checks
    if cpcv_result is not None:
        checks.extend(_cpcv_checks(cpcv_result))

    status = _worst_status(check["status"] for check in checks)
    result: dict[str, Any] = {
        "status": status,
        "checks": checks,
        "passed": sum(1 for check in checks if check["status"] == "PASS"),
        "amber": sum(1 for check in checks if check["status"] == "AMBER"),
        "failed": sum(1 for check in checks if check["status"] == "FAIL"),
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if cost_stress_result is not None:
        result["cost_stress"] = {
            k: v for k, v in cost_stress_result.items() if k != "scenarios"
        }
    if cpcv_result is not None:
        result["cpcv"] = cpcv_result
    return result


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
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
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
    """Renamed to EMBARGO_VS_HORIZON (v5.1 §2 CV-03).  Legacy key kept for compat."""
    if cv_gap is None:
        return _check("EMBARGO_VS_HORIZON", "AMBER", cv_gap, horizon, "embargo_samples missing; cannot verify purge adequacy")
    status: HonestyStatus = "PASS" if int(cv_gap) >= int(horizon) else "AMBER"
    return _check(
        "EMBARGO_VS_HORIZON",
        status,
        cv_gap,
        horizon,
        f"embargo_samples={cv_gap}, label_horizon_bars={horizon}; "
        f"{'embargo >= horizon (purge adequate)' if int(cv_gap) >= int(horizon) else 'embargo < horizon (purge may be insufficient)'}",
    )


def _cost_stress_check(cost_stress_result: dict[str, Any]) -> dict[str, Any]:
    """COST_STRESS: alpha_after_1x > 0 AND alpha_after_3x >= 0."""
    status_str = str(cost_stress_result.get("cost_stress_status", "AMBER"))
    status: HonestyStatus = "PASS" if status_str == "PASS" else "AMBER"
    a1 = cost_stress_result.get("alpha_after_1x_cost")
    a3 = cost_stress_result.get("alpha_after_3x_cost")
    reason = f"alpha_1x={a1}, alpha_3x={a3}; need 1x>0 and 3x>=0"
    return _check("COST_STRESS", status, a1, 0.0, reason)


def _cpcv_checks(cpcv_result: dict[str, Any]) -> list[dict[str, Any]]:
    """CPCV_PBO and CPCV_DSR checks from CombinatorialPurgedCV results."""
    checks: list[dict[str, Any]] = []
    pbo = cpcv_result.get("pbo")
    dsr = cpcv_result.get("deflated_sharpe")
    path_pass = cpcv_result.get("path_pass_rate")

    # PBO check: pbo <= 0.20 required for LIVE_REVIEW_CANDIDATE
    if pbo is not None:
        pbo_status: HonestyStatus = "PASS" if float(pbo) <= 0.20 else "AMBER"
        checks.append(_check("CPCV_PBO", pbo_status, pbo, 0.20, f"pbo={pbo:.3f}; need <=0.20"))
    else:
        checks.append(_check("CPCV_PBO", "AMBER", None, 0.20, "CPCV not run"))

    # DSR check: deflated_sharpe > 0
    if dsr is not None:
        dsr_status: HonestyStatus = "PASS" if float(dsr) > 0.0 else "AMBER"
        checks.append(_check("CPCV_DSR", dsr_status, dsr, 0.0, f"deflated_sharpe={dsr:.4f}; need >0"))
    else:
        checks.append(_check("CPCV_DSR", "AMBER", None, 0.0, "CPCV not run"))

    # Path pass rate check: >= 60% required
    if path_pass is not None:
        pp_status: HonestyStatus = "PASS" if float(path_pass) >= 0.60 else "AMBER"
        checks.append(_check("CPCV_PATH_RATE", pp_status, path_pass, 0.60, f"path_pass_rate={path_pass:.2%}; need >=60%"))

    return checks


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
