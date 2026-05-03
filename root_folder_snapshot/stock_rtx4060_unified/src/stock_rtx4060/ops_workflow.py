"""Ops v1 manual-approval workflow for report-only stock screening."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .recommendation_engine import RecommendationConfig, RecommendationEngine, RecommendationResult

ZERO_RULES = [
    {"code": "AUTO_BUY", "reason": "manual approval is required before any account action", "decision": "ZERO"},
    {"code": "BROKER_ORDER", "reason": "broker order execution is outside this repository boundary", "decision": "ZERO"},
    {"code": "MARGIN_OPTIONS", "reason": "margin, options, 0DTE, and leveraged account actions require separate approval", "decision": "ZERO"},
    {"code": "NO_STOP", "reason": "candidate without a defined stop cannot pass the risk plan", "decision": "ZERO"},
    {"code": "INSIDE_INFO", "reason": "non-public information is disallowed", "decision": "ZERO"},
    {"code": "GUARANTEED_RETURN", "reason": "guaranteed-return language is prohibited", "decision": "ZERO"},
]


def run_ops_v1_workflow(config: RecommendationConfig, output_dir: str | Path = "reports/ops_v1") -> dict[str, str]:
    """Run candidate screening and create manual approval artifacts.

    The workflow deliberately stops before any broker/account side effect.  It
    creates review artifacts that a human can use to approve, reject, or journal
    candidates after checking the risk gates.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    recommendation_dir = out_dir / "recommendations"
    workflow_config = replace(config, output_dir=str(recommendation_dir), audit_command="ops-v1")
    engine = RecommendationEngine(workflow_config)
    results = engine.run()
    recommendation_run = engine.write_reports(results)

    daily_brief = _write_ops_daily_brief(out_dir / f"ops_v1_daily_brief_{_stamp()}.md", results, workflow_config)
    approval_template = _write_approval_journal_template(out_dir / "approval_journal_template.csv", results)
    zero_log_md, zero_log_csv = _write_zero_logs(out_dir, results)
    summary_json = _write_summary(out_dir / f"ops_v1_summary_{_stamp()}.json", results, workflow_config, {
        "recommendation_markdown": recommendation_run.markdown_path,
        "recommendation_json": recommendation_run.json_path,
        "audit_log": recommendation_run.audit_path,
        "daily_brief": str(daily_brief),
        "approval_journal_template": str(approval_template),
        "zero_log": str(zero_log_md),
        "zero_log_csv": str(zero_log_csv),
    })

    return {
        "recommendation_markdown": recommendation_run.markdown_path,
        "recommendation_json": recommendation_run.json_path,
        "audit_log": recommendation_run.audit_path,
        "daily_brief": str(daily_brief),
        "approval_journal_template": str(approval_template),
        "zero_log": str(zero_log_md),
        "zero_log_csv": str(zero_log_csv),
        "summary_json": str(summary_json),
    }


def _write_ops_daily_brief(path: Path, results: list[RecommendationResult], config: RecommendationConfig) -> Path:
    rows = [
        {
            "ticker": item.ticker,
            "track": item.track,
            "verdict": item.verdict,
            "score": item.recommendation_rank_score,
            "entry": item.entry,
            "stop": item.stop,
            "tp1": item.tp1,
            "tp2": item.tp2,
            "risk_reward": item.risk_reward,
            "manual_approval_required": True,
            "screening_output_only": item.screening_output_only,
        }
        for item in results
    ]
    lines = [
        "# Ops v1 Daily Brief",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Boundary: `screening_output_only`; manual approval required; no broker order execution.",
        "",
        "Workflow: Universe -> data collection -> candidate scoring -> validation gates -> risk plan -> manual approval -> journal.",
        "",
        f"Universe: {', '.join(config.universe)}",
        f"Track: {config.track} | Period: {config.period} | Top-N: {config.top_n}",
        "",
        "## Candidate Review Table",
        "",
    ]
    if rows:
        lines.append(pd.DataFrame(rows).to_markdown(index=False))
    else:
        lines.append("No candidates generated.")
    lines.extend([
        "",
        "## Human Gate",
        "",
        "- Leave all candidates as `REVIEW_PENDING` until a human records an approval or rejection.",
        "- Do not connect this report to broker order execution.",
        "- Record any final decision with `run.ps1 journal ...` after review.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_approval_journal_template(path: Path, results: list[RecommendationResult]) -> Path:
    rows = []
    for item in results:
        rows.append({
            "ticker": item.ticker,
            "track": item.track,
            "verdict": item.verdict,
            "score": item.recommendation_rank_score,
            "entry": item.entry,
            "stop": item.stop,
            "tp1": item.tp1,
            "tp2": item.tp2,
            "risk_reward": item.risk_reward,
            "suggested_quantity": item.suggested_quantity,
            "suggested_position_value": item.suggested_position_value,
            "manual_action": "REVIEW_PENDING",
            "manual_approval_required": True,
            "broker_order_execution": False,
            "screening_output_only": item.screening_output_only,
            "reviewer": "",
            "reviewed_at": "",
            "final_decision": "",
            "journal_reason": "",
        })
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _write_zero_logs(out_dir: Path, results: list[RecommendationResult]) -> tuple[Path, Path]:
    csv_path = out_dir / "zero_log.csv"
    md_path = out_dir / "zero_log.md"
    frame = pd.DataFrame(ZERO_RULES)
    frame.to_csv(csv_path, index=False)

    lines = [
        "# ZERO Log",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "These rules block account-affecting actions in Ops v1.",
        "",
        frame.to_markdown(index=False),
        "",
        "## Current Run",
        "",
        f"- Candidate rows: {len(results)}",
        f"- Error rows: {sum(1 for item in results if item.verdict == 'RED_DATA_OR_MODEL_ERROR')}",
        "- Broker order execution: false",
        "- Automation boundary: screening/report only",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, csv_path


def _write_summary(path: Path, results: list[RecommendationResult], config: RecommendationConfig, paths: dict[str, str]) -> Path:
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workflow": "ops_v1_manual_approval",
        "config": asdict(config),
        "candidate_count": len(results),
        "error_count": sum(1 for item in results if item.verdict == "RED_DATA_OR_MODEL_ERROR"),
        "safety_boundary": {
            "screening_output_only": True,
            "manual_approval_required": True,
            "broker_order_execution": False,
            "auto_buy": False,
            "margin_options": False,
        },
        "paths": paths,
        "candidates": [item.to_dict() for item in results],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
