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
SOURCE_CONFLICT_WARNING_MESSAGE = (
    "AMBER SOURCE CONFLICT\n"
    "REC, Signal, Backtest, or model evidence does not share a consistent source/mode/timestamp.\n"
    "Live review and new capital are blocked. Paper recording only."
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


def _first_text(result: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = result.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().upper().replace("-", "_").replace(" ", "_")


def _coerce_model_score(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= numeric <= 1.0:
        return numeric * 100.0
    return numeric


def _model_score_spread(result: dict[str, Any]) -> float | None:
    scores: list[float] = []
    model_scores = result.get("model_scores")
    if isinstance(model_scores, dict):
        for value in model_scores.values():
            score = _coerce_model_score(value)
            if score is not None:
                scores.append(score)
    for key in (
        "main_score",
        "main_model_score",
        "backend_model_score",
        "logreg_score",
        "logistic_score",
        "xgboost_score",
        "xgb_score",
        "rnn_score",
        "lstm_score",
    ):
        score = _coerce_model_score(result.get(key))
        if score is not None:
            scores.append(score)
    if len(scores) < 2:
        return None
    return max(scores) - min(scores)


def _source_mode_timestamp_conflict_reasons(result: dict[str, Any]) -> tuple[list[str], float | None]:
    reasons: list[str] = []

    rec_mode = _normalized_text(_first_text(result, "rec_mode", "recommendation_mode", "rec_source_mode"))
    if rec_mode in {"FILE", "FILE_STATIC", "STATIC", "STATIC_FILE", "SNAPSHOT", "FILE_SNAPSHOT"}:
        reasons.append("REC_USES_FILE_STATIC_SNAPSHOT")

    signal = _normalized_text(_first_text(result, "signal", "backend_signal", "signal_panel_signal"))
    rec_signal = _normalized_text(_first_text(result, "rec_signal", "recommendation_signal"))
    benchmark_signal = _normalized_text(_first_text(result, "benchmark_signal", "benchmark_sig"))
    if signal and rec_signal and signal != rec_signal:
        reasons.append("SIGNAL_REC_SOURCE_MISMATCH")
    if signal and benchmark_signal and signal != benchmark_signal:
        reasons.append("SIGNAL_BENCHMARK_MISMATCH")

    for label, keys in {
        "SOURCE": ("signal_source", "rec_source", "backtest_source"),
        "MODE": ("signal_mode", "rec_mode", "backtest_mode"),
        "TIMESTAMP": ("signal_timestamp", "rec_timestamp", "backtest_timestamp"),
    }.items():
        values = {
            _normalized_text(result.get(key))
            for key in keys
            if result.get(key) is not None and str(result.get(key)).strip()
        }
        if len(values) > 1:
            reasons.append(f"SIGNAL_REC_BACKTEST_{label}_MISMATCH")

    spread = _model_score_spread(result)
    if spread is not None and spread >= 50.0:
        reasons.append("MODEL_DISAGREEMENT")

    return reasons, spread


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().upper() in {"1", "TRUE", "YES", "Y", "PASS"}
    return value == 1


def _is_false(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    if isinstance(value, str):
        return value.strip().upper() in {"0", "FALSE", "NO", "N", "FAIL"}
    return value == 0


def _data_lag_event_conflict_reasons(result: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    after_market_close = _is_true(result.get("after_market_close")) or _is_true(result.get("market_closed"))
    eod_confirmed = _is_true(result.get("eod_confirmed"))
    bar_type = _normalized_text(result.get("bar_type"))
    source = _normalized_text(result.get("source"))
    cache_like_source = "CACHE" in source or "CACHE" in bar_type or "INTRADAY" in bar_type
    final_bar_locked = eod_confirmed and bar_type in {"EOD_FINAL", "FINAL_EOD"}

    if after_market_close and (not final_bar_locked or cache_like_source):
        reasons.append("EOD_FINAL_BAR_NOT_LOCKED")

    has_external_candidates = any(
        result.get(key) is not None
        for key in (
            "external_close_candidate",
            "external_volume_candidate",
            "external_target_price_candidate",
            "close_final_candidate",
            "volume_final_candidate",
            "target_price_candidate",
        )
    )
    if has_external_candidates and not _is_true(result.get("source_evidence_lock")):
        reasons.append("EXTERNAL_MARKET_VALUES_NOT_LOCKED")

    signal = _normalized_text(_first_text(result, "signal", "backend_signal", "model_signal"))
    if _is_true(result.get("event_shock")) and signal == "SELL":
        reasons.append("EVENT_SHOCK_SIGNAL_CONFLICT")

    if _is_true(result.get("volume_breakout")) and "EOD_FINAL_BAR_NOT_LOCKED" in reasons:
        reasons.append("VOLUME_BREAKOUT_REQUIRES_FINAL_BAR")

    return reasons


def _pbo_summary_for_card(backtest_honesty: dict[str, Any] | None) -> dict[str, Any] | None:
    """[E2] Extract per-candidate PBO fields for RecommendationCard badge.

    Returns a minimal dict {pbo, pbo_status} when pbo_status is present,
    otherwise None so the badge stays hidden (hasPbo = false in JSX).
    """
    if not isinstance(backtest_honesty, dict):
        return None
    pbo_status = backtest_honesty.get("pbo_status")
    if pbo_status is None:
        return None
    return {
        "pbo": backtest_honesty.get("pbo"),
        "pbo_status": str(pbo_status),
    }


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
            "investment_execution_ready": False,
            "live_review_candidate": False,
            "auto_promote": False,
            "live_queue_action": "HARD_BLOCK",
            "research_queue_action": "EXCLUDE_UNTIL_FIXED",
            "live_investable": False,
            "new_capital_allowed": False,
            "broker_order_execution": False,
            "paper_trading_only": True,
            "safety_flags": safety_flags,
            "ready_for_manual_review": False,
            "dashboard_warning": True,
            "dashboard_warning_message": "HARD FAIL\n" + "\n".join(hard_reasons),
            "blocking_reasons": hard_reasons,
            "readiness_gate_failures": readiness_reasons,
        }

    data_lag_event_reasons = _data_lag_event_conflict_reasons(result)
    if data_lag_event_reasons:
        safety_flags = _readiness_safety_flags(result, new_capital_allowed=False)
        badges = ["DATA NOT FINAL", "REPORT ONLY", "PAPER ONLY"]
        if "EVENT_SHOCK_SIGNAL_CONFLICT" in data_lag_event_reasons:
            badges.append("EVENT SHOCK")
        if "VOLUME_BREAKOUT_REQUIRES_FINAL_BAR" in data_lag_event_reasons:
            badges.append("VOLUME BREAKOUT UNLOCKED")
        if "EXTERNAL_MARKET_VALUES_NOT_LOCKED" in data_lag_event_reasons:
            badges.append("EVIDENCE LOCK REQUIRED")
        return {
            "readiness_status": "AMBER_DATA_LAG_EVENT_CONFLICT",
            "investment_readiness_status": "AMBER_DATA_LAG_EVENT_CONFLICT",
            "investment_readiness_score": round(min(score, READINESS_SCORE_CAP), 2),
            "investment_execution_ready": False,
            "live_review_candidate": False,
            "auto_promote": False,
            "live_queue_action": "HARD_BLOCK",
            "research_queue_action": "PAPER_RECORDING_ALLOWED",
            "live_investable": False,
            "new_capital_allowed": False,
            "broker_order_execution": False,
            "paper_trading_only": True,
            "paper_recording_allowed": True,
            "safety_flags": safety_flags,
            "ready_for_manual_review": False,
            "manual_approval_required": True,
            "dashboard_warning": True,
            "dashboard_warning_message": (
                "AMBER_DATA_LAG_EVENT_CONFLICT\n"
                "Final market data or event evidence is not source-locked. "
                "This candidate is blocked from live review and remains paper-only."
            ),
            "display_badges": badges,
            "blocking_reasons": data_lag_event_reasons + readiness_reasons,
            "readiness_gate_failures": readiness_reasons,
        }

    source_conflict_reasons, model_score_spread = _source_mode_timestamp_conflict_reasons(result)
    if source_conflict_reasons:
        if alpha is not None and alpha < 0:
            source_conflict_reasons.append("BACKTEST_ALPHA_NEGATIVE")
        if completed_trades is not None and completed_trades < 50:
            source_conflict_reasons.append("COMPLETED_TRADES_BELOW_50")
        safety_flags = _readiness_safety_flags(result, new_capital_allowed=False)
        badges = ["SOURCE CONFLICT", "REPORT ONLY"]
        if "REC_USES_FILE_STATIC_SNAPSHOT" in source_conflict_reasons:
            badges.append("STATIC SNAPSHOT")
        if any(reason in source_conflict_reasons for reason in ("SIGNAL_REC_SOURCE_MISMATCH", "SIGNAL_BENCHMARK_MISMATCH")):
            badges.append("SIGNAL != REC")
        if "MODEL_DISAGREEMENT" in source_conflict_reasons:
            badges.append("MODEL DISAGREEMENT")
        if "BACKTEST_ALPHA_NEGATIVE" in source_conflict_reasons:
            badges.append("BACKTEST ALPHA NEGATIVE")
        if "COMPLETED_TRADES_BELOW_50" in source_conflict_reasons:
            badges.append("INSUFFICIENT TRADES")
        return {
            "readiness_status": "AMBER_SOURCE_CONFLICT",
            "investment_readiness_status": "AMBER_SOURCE_CONFLICT",
            "investment_readiness_score": round(min(score, READINESS_SCORE_CAP), 2),
            "investment_execution_ready": False,
            "live_review_candidate": False,
            "auto_promote": False,
            "live_queue_action": "HARD_BLOCK",
            "research_queue_action": "PAPER_RECORDING_ALLOWED",
            "live_investable": False,
            "new_capital_allowed": False,
            "broker_order_execution": False,
            "paper_trading_only": True,
            "paper_recording_allowed": True,
            "safety_flags": safety_flags,
            "ready_for_manual_review": False,
            "dashboard_warning": True,
            "dashboard_warning_message": SOURCE_CONFLICT_WARNING_MESSAGE,
            "display_badges": badges,
            "model_score_spread": round(model_score_spread, 2) if model_score_spread is not None else None,
            "blocking_reasons": source_conflict_reasons + readiness_reasons,
            "readiness_gate_failures": readiness_reasons,
        }

    if readiness_reasons:
        safety_flags = _readiness_safety_flags(result, new_capital_allowed=False)
        return {
            "readiness_status": "AMBER_WATCHLIST",
            "investment_readiness_status": "AMBER_WATCHLIST",
            "investment_readiness_score": round(min(score, READINESS_SCORE_CAP), 2),
            "investment_execution_ready": False,
            "live_review_candidate": False,
            "auto_promote": False,
            "live_queue_action": "HARD_BLOCK",
            "research_queue_action": "AMBER_WATCHLIST",
            "live_investable": False,
            "new_capital_allowed": False,
            "broker_order_execution": False,
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
    spread = _model_score_spread(result)
    if live_review_candidate:
        safety_flags = _readiness_safety_flags(result, new_capital_allowed=False)
        return {
            "readiness_status": "LIVE_REVIEW_CANDIDATE",
            "investment_readiness_status": "LIVE_REVIEW_CANDIDATE",
            "investment_readiness_score": round(score, 2),
            "investment_execution_ready": False,
            "live_review_candidate": True,
            "auto_promote": False,
            "live_queue_action": "MANUAL_REVIEW_REQUIRED",
            "research_queue_action": "MONITOR",
            "live_investable": False,
            "new_capital_allowed": False,
            "broker_order_execution": False,
            "paper_trading_only": False,
            "safety_flags": safety_flags,
            "ready_for_manual_review": True,
            "dashboard_warning": False,
            "dashboard_warning_message": None,
            "model_score_spread": round(spread, 2) if spread is not None else None,
            "blocking_reasons": result.get("remaining_blocks") or [],
            "readiness_gate_failures": result.get("remaining_blocks") or [],
        }

    safety_flags = _readiness_safety_flags(result, new_capital_allowed=True)
    return {
        "readiness_status": "READY_FOR_MANUAL_REVIEW",
        "investment_readiness_status": "READY_FOR_MANUAL_REVIEW",
        "investment_readiness_score": round(score, 2),
        "investment_execution_ready": False,
        "live_review_candidate": live_review_candidate,
        "auto_promote": False,
        "live_queue_action": "MANUAL_REVIEW_REQUIRED",
        "research_queue_action": "MONITOR",
        "live_investable": True,
        "new_capital_allowed": True,
        "broker_order_execution": False,
        "paper_trading_only": False,
        "safety_flags": safety_flags,
        "ready_for_manual_review": True,
        "dashboard_warning": False,
        "dashboard_warning_message": None,
        "model_score_spread": round(spread, 2) if spread is not None else None,
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


def _build_scenario_fallback(result: dict) -> dict:
    """Generate bull/base/bear scenario from existing price plan fields."""
    entry = result.get("entry") or result.get("latest_close") or 0.0
    tp2 = result.get("tp2") or 0.0
    stop = result.get("stop") or 0.0
    rr = result.get("risk_reward") or 1.0
    prob = result.get("direction_prob") or 0.5

    bull_prob = round(max(0.10, min(0.50, prob * 0.65)), 2)
    bear_prob = round(max(0.10, min(0.40, (1 - prob) * 0.60)), 2)
    base_prob = round(max(0.10, 1.0 - bull_prob - bear_prob), 2)

    if entry > 0 and tp2 > 0:
        bull_ret = round((tp2 - entry) / entry * 100, 1)
    else:
        bull_ret = 10.0
    if entry > 0 and stop > 0:
        bear_ret = round((stop - entry) / entry * 100, 1)
    else:
        bear_ret = -8.0

    return {
        "bull": {
            "range": f"${tp2:.0f}+" if entry > 0 else "—",
            "return": f"+{bull_ret:.1f}%",
            "probability": bull_prob,
        },
        "base": {
            "range": f"${entry:.0f} - ${tp2 * 0.6 + entry * 0.4:.0f}" if entry > 0 else "—",
            "return": f"+{bull_ret * 0.4:.1f}%",
            "probability": base_prob,
        },
        "bear": {
            "range": f"${stop:.0f}" if stop > 0 else "—",
            "return": f"{bear_ret:.1f}%",
            "probability": bear_prob,
        },
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
        "raw_score": result.get("raw_score", result["recommendation_rank_score"]),
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
        # [E2] Per-candidate PBO summary for RecommendationCard badge
        "backtest_honesty_summary": _pbo_summary_for_card(result.get("backtest_honesty")),
        "size_multiplier": result.get("size_multiplier"),
        "sizing_strategy_used": result.get("sizing_strategy_used"),
        "sizing_coverage_status": result.get("sizing_coverage_status"),
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
        # [Wave 4 Dashboard] New optional display fields — None when not computed.
        "tft_prob": result.get("tft_prob"),
        "advisor_regime": result.get("advisor_regime"),
        "model_kind_used": result.get("model_kind_used"),
        # [NotebookLM News Intelligence] Additive fields — None when NLM not enriched.
        # notebooklm_impact: market impact label from NotebookLM analysis (LOW/MEDIUM/MEDIUM_HIGH/HIGH)
        # notebooklm_confidence: analysis confidence score 0.0-1.0
        # notebooklm_source_count: number of news sources used
        # notebooklm_as_of: ISO timestamp of the NotebookLM analysis
        "notebooklm_impact": result.get("notebooklm_impact"),
        "notebooklm_confidence": result.get("notebooklm_confidence"),
        "notebooklm_source_count": result.get("notebooklm_source_count"),
        "notebooklm_as_of": result.get("notebooklm_as_of"),
        # [Executive Dashboard v2.1] Additive — None when not available
        # notebook_analysis: full NotebookLM analysis dict (passthrough from result)
        "notebook_analysis": result.get("notebook_analysis"),
        # scenario_outlook: bull/base/bear scenarios — generated from existing fields if absent
        "scenario_outlook": result.get("scenario_outlook") or _build_scenario_fallback(result),
    }
