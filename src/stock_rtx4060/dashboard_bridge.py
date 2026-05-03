"""Dashboard snapshot export for report-only recommendation outputs."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
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

    snapshot_results = [_normalize_result(item, rank=index + 1) for index, item in enumerate(results)]

    return {
        "schema_version": "dashboard_snapshot.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "stock_rtx4060_unified",
        "source_recommendation_json": str(source_json_path) if source_json_path else None,
        "mode": "report_only",
        "disclaimer": payload.get(
            "disclaimer",
            "screening_output_only; manual approval required; no broker order execution; not financial advice",
        ),
        "audit_log_path": payload.get("audit_log_path"),
        "algorithm_patch": payload.get("algorithm_patch"),
        "provider_summary": payload.get("provider_summary"),
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


def _normalize_result(result: Any, *, rank: int) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise DashboardBridgeError(f"result #{rank} must be an object")
    missing = sorted(field for field in RESULT_REQUIRED_FIELDS if field not in result)
    if missing:
        raise DashboardBridgeError(f"result #{rank} missing required field(s): {', '.join(missing)}")
    if result.get("screening_output_only") is not True:
        raise DashboardBridgeError(f"result #{rank} must preserve screening_output_only=true")

    return {
        "rank": rank,
        "ticker": result["ticker"],
        "track": result["track"],
        "verdict": result["verdict"],
        "candidate_label": result.get("candidate_label"),
        "score": result["recommendation_rank_score"],
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
        "backtest_sharpe": result.get("backtest_sharpe"),
        "backtest_sortino": result.get("backtest_sortino"),
        "backtest_mdd_pct": result.get("backtest_mdd_pct"),
        "profit_factor": result.get("profit_factor"),
        "confirmations_passed": result.get("confirmations_passed"),
        "confirmations_total": result.get("confirmations_total"),
        "screening_output_only": result["screening_output_only"],
        "validations": result["validations"],
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
    }
