"""Dashboard snapshot export for report-only recommendation outputs."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RESULT_REQUIRED_FIELDS = {
    "ticker",
    "track",
    "verdict",
    "recommendation_rank_score",
    "direction_prob",
    "expected_value_pct",
    "entry",
    "stop",
    "tp2",
    "risk_reward",
    "screening_output_only",
    "validations",
}

KEVPE_OPTIONAL_FIELDS = {
    "kevpe_available",
    "kevpe_regime",
    "kevpe_score",
    "kevpe_expected_return_pct",
    "kevpe_ci",
    "kevpe_confidence",
    "kevpe_reason",
}


class DashboardBridgeError(ValueError):
    """Raised when a recommendation payload cannot become a dashboard snapshot."""


def load_recommendation_payload(path: str | Path) -> dict[str, Any]:
    recommendation_path = Path(path)
    try:
        payload = json.loads(recommendation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DashboardBridgeError(f"invalid recommendation JSON: {recommendation_path}") from exc
    if not isinstance(payload, dict):
        raise DashboardBridgeError("recommendation JSON must contain a top-level object")
    return payload


def build_dashboard_snapshot(payload: dict[str, Any], *, source_json_path: str | Path | None = None) -> dict[str, Any]:
    results = payload.get("results")
    if not isinstance(results, list):
        raise DashboardBridgeError("recommendation JSON must contain a list field: results")

    source_config = payload.get("config", {})
    if not isinstance(source_config, dict):
        source_config = {}

    provider_summary = payload.get("provider_summary")
    snapshot_results = [
        _normalize_result(item, rank=index + 1, provider_summary=provider_summary)
        for index, item in enumerate(results)
    ]

    # Phase-5: optional `meta` block with risk attribution.  Absent unless the
    # caller supplied a `meta` field on the payload.  The schema stays
    # `dashboard_snapshot.v1` since this is purely additive.
    meta_block = payload.get("meta") if isinstance(payload.get("meta"), dict) else None
    if meta_block is not None:
        meta_block = {
            **meta_block,
            "risk_attribution": meta_block.get("risk_attribution"),
        }

    return {
        "schema_version": "dashboard_snapshot.v1",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "stock_rtx4060_unified",
        "source_recommendation_json": str(source_json_path) if source_json_path else None,
        "mode": "report_only",
        "disclaimer": payload.get(
            "disclaimer",
            "screening_output_only; manual approval required; no broker order execution; not financial advice",
        ),
        "audit_log_path": payload.get("audit_log_path"),
        "algorithm_patch": payload.get("algorithm_patch"),
        "provider_summary": provider_summary,
        "backtest_honesty_summary": payload.get("backtest_honesty_summary"),
        "config": {
            "universe": source_config.get("universe"),
            "track": source_config.get("track"),
            "period": source_config.get("period"),
            "top_n": source_config.get("top_n"),
            "synthetic": source_config.get("synthetic"),
            "data_provider": source_config.get("data_provider"),
            "model_kind": source_config.get("model_kind"),
            "xgb_device": source_config.get("xgb_device"),
            "cv_gap": source_config.get("cv_gap"),
        },
        "result_count": len(snapshot_results),
        "results": snapshot_results,
        "meta": meta_block,
    }


def write_dashboard_snapshot(
    recommendation_json: str | Path,
    output: str | Path | None = None,
) -> Path:
    source_path = Path(recommendation_json)
    payload = load_recommendation_payload(source_path)
    snapshot = build_dashboard_snapshot(payload, source_json_path=source_path)
    output_path = Path(output) if output else source_path.with_name("dashboard_snapshot.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def export_dashboard_public_assets(
    recommendation_json: str | Path,
    dashboard_snapshot: str | Path,
    public_dir: str | Path,
    *,
    approval_journal: str | Path | None = None,
) -> dict[str, str | None]:
    """Copy dashboard browser assets into a Vite public directory."""
    source_path = Path(recommendation_json)
    snapshot_path = Path(dashboard_snapshot)
    public_path = Path(public_dir)
    public_path.mkdir(parents=True, exist_ok=True)

    exported: dict[str, str | None] = {
        "dashboard_snapshot": _copy_file(snapshot_path, public_path / "dashboard_snapshot.json"),
        "audit_log": None,
        "approval_journal": None,
    }

    payload = load_recommendation_payload(source_path)
    audit_log_path = _resolve_existing_path(
        payload.get("audit_log_path"),
        base_dirs=[Path.cwd(), source_path.parent, source_path.parent.parent],
        fallback_name="audit_log.jsonl",
    )
    if audit_log_path:
        exported["audit_log"] = _copy_file(audit_log_path, public_path / "audit_log.jsonl")

    approval_path = _resolve_existing_path(
        approval_journal,
        base_dirs=[Path.cwd(), source_path.parent, source_path.parent.parent],
        fallback_name="approval_journal_template.csv",
    )
    if approval_path is None:
        approval_path = _find_nearby_file(source_path, "approval_journal_template.csv")
    if approval_path:
        exported["approval_journal"] = _copy_file(approval_path, public_path / "approval_journal_template.csv")

    return exported


def _copy_file(source: Path, destination: Path) -> str:
    if not source.exists() or not source.is_file():
        raise DashboardBridgeError(f"cannot export missing file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return str(destination)


def _resolve_existing_path(
    value: Any,
    *,
    base_dirs: list[Path],
    fallback_name: str | None = None,
) -> Path | None:
    candidates: list[Path] = []
    if isinstance(value, str) and value.strip():
        raw = Path(value)
        candidates.append(raw)
        if not raw.is_absolute():
            candidates.extend(base / raw for base in base_dirs)
            candidates.extend(base / raw.name for base in base_dirs)
    elif fallback_name:
        candidates.extend(base / fallback_name for base in base_dirs)

    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _find_nearby_file(source_path: Path, file_name: str) -> Path | None:
    for directory in [source_path.parent, source_path.parent.parent]:
        candidate = directory / file_name
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _truncate_advisor_rationale(value: Any) -> str | None:
    """Clip the LLM rationale to 240 chars for dashboard display."""
    if value is None:
        return None
    text = str(value)
    if len(text) <= 240:
        return text
    return text[:237] + "..."


READINESS_SCORE_CAP = 44.0
READINESS_WARNING_MESSAGE = (
    "AMBER WATCHLIST\n"
    "Model failed one or more readiness gates.\n"
    "New capital is not allowed.\n"
    "Paper trading and monitoring only."
)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_number(result: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _to_float(result.get(key))
        if value is not None:
            return value
    return None


def _first_int(result: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = _to_int(result.get(key))
        if value is not None:
            return value
    return None


def _has_failed_validation(result: dict[str, Any], names: set[str]) -> bool:
    validations = result.get("validations")
    if not isinstance(validations, list):
        return False
    for item in validations:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).upper()
        status = str(item.get("status", "")).upper()
        if status == "FAIL" and any(token in name for token in names):
            return True
    return False


def _evaluate_investment_readiness(result: dict[str, Any], *, provider_summary: Any) -> dict[str, Any]:
    """Return dashboard-only readiness metadata without changing raw rank score."""
    score = _first_number(result, "investment_readiness_score", "recommendation_rank_score") or 0.0
    accuracy = _first_number(result, "model_accuracy", "accuracy")
    auc = _first_number(result, "model_auc", "auc")
    alpha = _first_number(result, "alpha_pct", "backtest_alpha_pct", "benchmark_alpha_pct", "alpha")
    completed_trades = _first_int(result, "completed_trades", "completedTrades", "n_trades", "trade_count")
    backtest_honesty = result.get("backtest_honesty")

    hard_reasons: list[str] = []
    if result.get("screening_output_only") is not True:
        hard_reasons.append("screening_output_only missing")
    if result.get("broker_order_execution") is True or result.get("broker_execution_enabled") is True:
        hard_reasons.append("broker order execution possible")
    if provider_summary is None:
        hard_reasons.append("provider audit missing")
    if isinstance(provider_summary, dict) and str(provider_summary.get("status", "")).upper() == "FAIL":
        hard_reasons.append("provider audit failed")
    backtest_honesty_status = ""
    if not isinstance(backtest_honesty, dict):
        hard_reasons.append("backtest honesty missing")
    else:
        backtest_honesty_status = str(backtest_honesty.get("status", "")).upper()
        if backtest_honesty_status == "FAIL":
            hard_reasons.append("backtest honesty failed")
    if result.get("point_in_time_clear") is False or result.get("pit_status") == "FAIL":
        hard_reasons.append("point-in-time unclear")
    if result.get("data_leakage_suspected") is True or _has_failed_validation(result, {"LEAK", "LOOKAHEAD"}):
        hard_reasons.append("data leakage suspected")
    text_blob = " ".join(str(result.get(key, "")) for key in ("candidate_label", "reasons", "warning", "disclaimer")).lower()
    if any(token in text_blob for token in ("guaranteed return", "수익 보장", "자동매매")):
        hard_reasons.append("prohibited performance or automation wording")

    readiness_reasons: list[str] = []
    if backtest_honesty_status and backtest_honesty_status != "PASS":
        readiness_reasons.append(f"Backtest honesty {backtest_honesty_status} != PASS")
    if accuracy is None:
        readiness_reasons.append("Accuracy missing")
    elif accuracy < 0.50:
        readiness_reasons.append(f"Accuracy {accuracy:.2%} < 50.00%")
    if auc is None:
        readiness_reasons.append("AUC missing")
    elif auc < 0.50:
        readiness_reasons.append(f"AUC {auc:.4f} < 0.50")
    if alpha is None:
        readiness_reasons.append("Alpha missing")
    elif alpha < 0:
        readiness_reasons.append(f"Alpha {alpha:.2f}% < 0.00%")
    if completed_trades is None:
        readiness_reasons.append("Completed trades missing")
    elif completed_trades < 50:
        readiness_reasons.append(f"Completed trades {completed_trades} < 50")

    if hard_reasons:
        safety_flags = _readiness_safety_flags(result, new_capital_allowed=False)
        return {
            "readiness_status": "HARD_FAIL",
            "investment_readiness_status": "HARD_FAIL",
            "investment_readiness_score": 0.0,
            "live_review_candidate": False,
            "live_queue_action": "HARD_BLOCK",
            "research_queue_action": "EXCLUDE_UNTIL_FIXED",
            "live_investable": False,
            "new_capital_allowed": False,
            "paper_trading_only": True,
            "safety_flags": safety_flags,
            "ready_for_manual_review": False,
            "dashboard_warning": True,
            "dashboard_warning_message": "HARD FAIL\n" + "\n".join(hard_reasons),
            "blocking_reasons": hard_reasons,
            "readiness_gate_failures": readiness_reasons,
        }

    if readiness_reasons:
        safety_flags = _readiness_safety_flags(result, new_capital_allowed=False)
        return {
            "readiness_status": "AMBER_WATCHLIST",
            "investment_readiness_status": "AMBER_WATCHLIST",
            "investment_readiness_score": round(min(score, READINESS_SCORE_CAP), 2),
            "live_review_candidate": False,
            "live_queue_action": "HARD_BLOCK",
            "research_queue_action": "AMBER_WATCHLIST",
            "live_investable": False,
            "new_capital_allowed": False,
            "paper_trading_only": True,
            "safety_flags": safety_flags,
            "ready_for_manual_review": False,
            "dashboard_warning": True,
            "dashboard_warning_message": READINESS_WARNING_MESSAGE,
            "blocking_reasons": readiness_reasons,
            "readiness_gate_failures": readiness_reasons,
        }

    live_review_candidate = (
        result.get("live_review_candidate") is True
        or str(result.get("readiness_status", "")).upper() == "LIVE_REVIEW_CANDIDATE"
        or str(result.get("investment_readiness_status", "")).upper() == "LIVE_REVIEW_CANDIDATE"
    )
    if live_review_candidate:
        safety_flags = _readiness_safety_flags(result, new_capital_allowed=False)
        return {
            "readiness_status": "LIVE_REVIEW_CANDIDATE",
            "investment_readiness_status": "LIVE_REVIEW_CANDIDATE",
            "investment_readiness_score": round(score, 2),
            "live_review_candidate": True,
            "live_queue_action": "MANUAL_REVIEW_REQUIRED",
            "research_queue_action": "MONITOR",
            "live_investable": False,
            "new_capital_allowed": False,
            "paper_trading_only": False,
            "safety_flags": safety_flags,
            "ready_for_manual_review": True,
            "dashboard_warning": False,
            "dashboard_warning_message": None,
            "blocking_reasons": result.get("remaining_blocks") or [],
            "readiness_gate_failures": result.get("remaining_blocks") or [],
        }

    safety_flags = _readiness_safety_flags(result, new_capital_allowed=True)
    return {
        "readiness_status": "READY_FOR_MANUAL_REVIEW",
        "investment_readiness_status": "READY_FOR_MANUAL_REVIEW",
        "investment_readiness_score": round(score, 2),
        "live_review_candidate": live_review_candidate,
        "live_queue_action": "MANUAL_REVIEW_REQUIRED",
        "research_queue_action": "MONITOR",
        "live_investable": True,
        "new_capital_allowed": True,
        "paper_trading_only": False,
        "safety_flags": safety_flags,
        "ready_for_manual_review": True,
        "dashboard_warning": False,
        "dashboard_warning_message": None,
        "blocking_reasons": [],
        "readiness_gate_failures": [],
    }


def _readiness_safety_flags(result: dict[str, Any], *, new_capital_allowed: bool) -> dict[str, bool]:
    return {
        "screening_output_only": result.get("screening_output_only") is True,
        "manual_approval_required": True,
        "broker_order_execution": False,
        "new_capital_allowed": bool(new_capital_allowed),
    }


def _normalize_result(result: Any, *, rank: int, provider_summary: Any = None) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise DashboardBridgeError(f"result #{rank} must be an object")
    missing = sorted(field for field in RESULT_REQUIRED_FIELDS if field not in result)
    if missing:
        raise DashboardBridgeError(f"result #{rank} missing required field(s): {', '.join(missing)}")
    if result.get("screening_output_only") is not True:
        raise DashboardBridgeError(f"result #{rank} must preserve screening_output_only=true")

    readiness = _evaluate_investment_readiness(result, provider_summary=provider_summary)

    return {
        "rank": rank,
        "ticker": result["ticker"],
        "track": result["track"],
        "verdict": result["verdict"],
        "dashboard_status": readiness["investment_readiness_status"],
        "candidate_label": result.get("candidate_label"),
        "score": result["recommendation_rank_score"],
        "raw_score": result["recommendation_rank_score"],
        **readiness,
        "probability": result["direction_prob"],
        "expected_value_pct": result["expected_value_pct"],
        "entry": result["entry"],
        "latest_close": result.get("latest_close"),
        "stop": result["stop"],
        "tp1": result.get("tp1"),
        "tp2": result["tp2"],
        "stop_pct": result.get("stop_pct"),
        "tp2_pct": result.get("tp2_pct"),
        "risk_reward": result["risk_reward"],
        "risk_budget_pct": result.get("risk_budget_pct"),
        "max_position_pct": result.get("max_position_pct"),
        "suggested_quantity": result.get("suggested_quantity"),
        "suggested_position_value": result.get("suggested_position_value"),
        "model_accuracy": result.get("model_accuracy"),
        "model_auc": result.get("model_auc"),
        "oof_coverage": result.get("oof_coverage"),
        "backtest_return_pct": result.get("backtest_return_pct"),
        "alpha_pct": _first_number(result, "alpha_pct", "backtest_alpha_pct", "benchmark_alpha_pct", "alpha"),
        "completed_trades": _first_int(result, "completed_trades", "completedTrades", "n_trades", "trade_count"),
        "backtest_sharpe": result.get("backtest_sharpe"),
        "backtest_sortino": result.get("backtest_sortino"),
        "backtest_mdd_pct": result.get("backtest_mdd_pct"),
        "profit_factor": result.get("profit_factor"),
        "confirmations_passed": result.get("confirmations_passed"),
        "confirmations_total": result.get("confirmations_total"),
        "screening_output_only": result["screening_output_only"],
        "validations": result["validations"],
        "backtest_honesty": result.get("backtest_honesty"),
        "reasons": result.get("reasons", []),
        "generated_at_utc": result.get("generated_at_utc"),
        # KEVPE overlay (optional — only present when kevpe_adapter was used)
        "kevpe_available": result.get("kevpe_available", False),
        "kevpe_regime": result.get("kevpe_regime"),
        "kevpe_score": result.get("kevpe_score"),
        "kevpe_expected_return_pct": result.get("kevpe_expected_return_pct"),
        "kevpe_ci": result.get("kevpe_ci"),
        "kevpe_confidence": result.get("kevpe_confidence"),
        "kevpe_reason": result.get("kevpe_reason"),
        # Phase-6 advisor overlay (optional — None when advisor not run).
        # Schema stays at v1 — these fields default to None for backward
        # compatibility.
        "advisor_score": result.get("advisor_score"),
        "advisor_rationale": _truncate_advisor_rationale(result.get("advisor_rationale")),
    }
