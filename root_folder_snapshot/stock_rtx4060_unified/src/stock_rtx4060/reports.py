"""Markdown/JSON report writers for the investment OS."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .risk_rules import CandidateVerdict, RiskConfig, portfolio_targets


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


class ReportWriter:
    def __init__(self, output_dir: str | Path = "reports") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def daily_brief(self, candidates: Iterable[CandidateVerdict], runtime_gate: str = "AMBER", benchmark_summary: dict[str, Any] | None = None, filename: str | None = None) -> Path:
        rows = [candidate.to_dict() for candidate in candidates]
        df = pd.DataFrame(rows)
        filename = filename or f"daily_brief_{now_stamp()}.md"
        path = self.output_dir / filename
        lines = ["# Daily Brief", "", f"Generated: {datetime.now().isoformat(timespec='seconds')}", f"Runtime Gate: **{runtime_gate}**", "", "## Track-S / Track-L Candidates", ""]
        if df.empty:
            lines.append("No candidates generated.")
        else:
            display_cols = ["ticker", "track", "score", "gate", "verdict", "entry", "stop", "tp1", "tp2", "risk_reward", "quantity", "open_risk"]
            lines.append(df[display_cols].to_markdown(index=False))
        if benchmark_summary:
            lines.extend(["", "## Benchmark Summary", "", _dict_table(benchmark_summary)])
        lines.extend(["", "## Operating Guardrails", "", "- No automatic broker order is emitted by this report.", "- Track-S monthly stop: -5.00%. If triggered, new short-term entries are blocked.", "- Margin, 0DTE/options, and no-stop entries are fail-safe ZERO conditions."])
        return _write_text(path, "\n".join(lines))

    def risk_dashboard(self, candidates: Iterable[CandidateVerdict], config: RiskConfig | None = None, filename: str | None = None) -> Path:
        cfg = config or RiskConfig()
        rows = [candidate.to_dict() for candidate in candidates]
        df = pd.DataFrame(rows)
        open_risk = float(df.get("open_risk", pd.Series(dtype=float)).sum()) if not df.empty else 0.0
        filename = filename or f"risk_dashboard_{now_stamp()}.md"
        path = self.output_dir / filename
        lines = ["# Risk Dashboard", "", f"Generated: {datetime.now().isoformat(timespec='seconds')}", "", "## Capital Buckets", "", portfolio_targets(cfg).to_markdown(index=False), "", "## Open Risk", "", f"- Open risk: {open_risk:,.2f}", f"- Track-S open-risk limit: {cfg.track_s_capital * cfg.max_open_risk_pct:,.2f}", f"- Status: {'PASS' if open_risk <= cfg.track_s_capital * cfg.max_open_risk_pct else 'FAIL'}", "", "## Gate Counts", ""]
        if df.empty:
            lines.append("No gates to summarize.")
        else:
            lines.append(df.groupby(["track", "gate"]).size().reset_index(name="count").to_markdown(index=False))
        return _write_text(path, "\n".join(lines))

    def track_l_thesis(self, candidates: Iterable[CandidateVerdict], filename: str | None = None) -> Path:
        filename = filename or f"track_l_thesis_{now_stamp()}.md"
        path = self.output_dir / filename
        lines = ["# Track-L Thesis Report", "", f"Generated: {datetime.now().isoformat(timespec='seconds')}", "", "Long-term entries require Score >= 80.00 and must be reviewed against thesis damage conditions.", ""]
        l_candidates = [candidate for candidate in candidates if candidate.track == "L"]
        if not l_candidates:
            lines.append("No Track-L candidates generated.")
        for candidate in l_candidates:
            lines.extend([f"## {candidate.ticker}", "", f"- Gate: {candidate.gate.value}", f"- Score: {candidate.score:.2f}", f"- Verdict: {candidate.verdict}", f"- Max single-name position value under policy: {candidate.position_value:,.2f}", "- Thesis damage triggers: business quality deterioration, earnings miss cluster, balance-sheet stress, valuation overshoot, or bucket concentration.", f"- Reasons: {'; '.join(candidate.reasons)}", ""])
        return _write_text(path, "\n".join(lines))

    def monthly_scorecard(self, backtest_result: dict[str, Any] | None = None, rule_violations: list[str] | None = None, filename: str | None = None) -> Path:
        filename = filename or f"monthly_scorecard_{now_stamp()}.md"
        path = self.output_dir / filename
        rule_violations = rule_violations or []
        lines = ["# Monthly Scorecard", "", f"Generated: {datetime.now().isoformat(timespec='seconds')}", "", "## Track-S Performance", ""]
        if backtest_result:
            lines.append(_dict_table(backtest_result, keys=["total_return_pct", "sharpe_ratio", "max_drawdown_pct", "win_rate_pct", "n_trades"]))
        else:
            lines.append("No backtest result attached.")
        lines.extend(["", "## Rule Violations", ""])
        lines.extend([f"- {item}" for item in rule_violations] if rule_violations else ["- None recorded."])
        lines.extend(["", "## Review Actions", "", "- If Track-S reaches +10.00% monthly target gate, reduce trading intensity.", "- If Track-S reaches -5.00% monthly loss gate, stop new Track-S trades for the month.", "- Track-L: DCA/rebalance only after thesis review and bucket drift check."])
        return _write_text(path, "\n".join(lines))

    def journal_append(self, entry: dict[str, Any], filename: str = "decision_journal.csv") -> Path:
        path = self.output_dir / filename
        payload = {"timestamp": datetime.now().isoformat(timespec="seconds"), **entry}
        frame = pd.DataFrame([payload])
        if path.exists():
            existing = pd.read_csv(path)
            frame = pd.concat([existing, frame], ignore_index=True)
        frame.to_csv(path, index=False)
        return path

    def json_report(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.output_dir / f"{name}_{now_stamp()}.json"
        path.write_text(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def _dict_table(payload: dict[str, Any], keys: list[str] | None = None) -> str:
    keys = keys or list(payload.keys())
    rows = [{"Metric": key, "Value": payload.get(key)} for key in keys if key in payload]
    return pd.DataFrame(rows).to_markdown(index=False)


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_to_jsonable(item) for item in value]
    return value


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    return path
