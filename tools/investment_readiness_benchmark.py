"""Investment-readiness benchmark for stock recommendation candidates.

Boundary
--------
This tool produces screening benchmarks only. It never places broker orders
and never claims personalised investment advice.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

CheckStatus = Literal["PASS", "AMBER", "FAIL", "NOT_APPLICABLE", "INVALID_INPUT"]
RunVerdict = Literal["READY", "AMBER", "NO_CANDIDATES", "NOT_INVESTMENT_READY"]
CandidateStatus = Literal["PASS", "AMBER_WATCHLIST", "FAIL", "INVALID_INPUT"]


@dataclass
class BenchmarkCheck:
    status: CheckStatus
    evidence: str


@dataclass
class CandidateBenchmark:
    ticker: str
    track: str
    ready_for_manual_review: bool
    new_capital_allowed: bool
    paper_trading_only: bool
    raw_score: float
    investment_score: float
    status: CandidateStatus
    blocking_reasons: list[str]
    checks: dict[str, BenchmarkCheck]


@dataclass
class RunBenchmark:
    schema_version: str = "1.0"
    generated_at_utc: str = ""
    input_path: str = ""
    run_verdict: RunVerdict = "NOT_INVESTMENT_READY"
    candidate_count: int = 0
    ready_count: int = 0
    candidates: list[CandidateBenchmark] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_number(value: Any) -> bool:
    try:
        return value is not None and float(value) == float(value)  # NaN check
    except (TypeError, ValueError):
        return False


def _cost_stress_check(
    *,
    backtest_return_pct: float | None,
    transaction_cost_buffer_pct: float,
    multiplier: int,
) -> BenchmarkCheck:
    """Evaluate cost survival at 1x / 2x / 3x stress level."""
    if not _valid_number(backtest_return_pct):
        return BenchmarkCheck(
            status="AMBER",
            evidence="backtest_return_pct missing; cannot evaluate cost stress",
        )
    threshold = transaction_cost_buffer_pct * multiplier
    ret = float(backtest_return_pct)
    if ret > threshold:
        return BenchmarkCheck(
            status="PASS",
            evidence=f"return={ret:.2f}% exceeds {multiplier}x threshold={threshold:.2f}%",
        )
    return BenchmarkCheck(
        status="FAIL",
        evidence=f"return={ret:.2f}% does not exceed {multiplier}x threshold={threshold:.2f}%",
    )


def _embargo_stress_check(
    *,
    cv_gap: int | None,
    horizon: int,
) -> BenchmarkCheck:
    """Evaluate walk-forward gap embargo stress."""
    if not _valid_number(cv_gap):
        return BenchmarkCheck(
            status="AMBER",
            evidence="cv_gap missing; cannot evaluate embargo stress",
        )
    gap = int(cv_gap)
    if gap >= horizon:
        return BenchmarkCheck(
            status="PASS",
            evidence=f"cv_gap={gap} >= horizon={horizon}",
        )
    return BenchmarkCheck(
        status="FAIL",
        evidence=f"cv_gap={gap} < horizon={horizon}",
    )


def _advisor_audit_check(
    *,
    advisor_score: float | None,
    audit_log_path: str | Path | None,
    ticker: str,
) -> BenchmarkCheck:
    """Check advisor audit consistency for a candidate."""
    if advisor_score is None:
        return BenchmarkCheck(
            status="NOT_APPLICABLE",
            evidence="advisor_score is null; advisor audit not applicable",
        )

    if audit_log_path is None:
        return BenchmarkCheck(
            status="FAIL",
            evidence=f"advisor_score={advisor_score} present but no audit_log_path in run",
        )

    audit_path = Path(audit_log_path)
    if not audit_path.exists():
        return BenchmarkCheck(
            status="FAIL",
            evidence=f"advisor_score={advisor_score} present but audit log not found at {audit_path}",
        )

    # Look for a matching ticker entry in today's audit lines
    today = datetime.now(UTC).date().isoformat()
    found = False
    try:
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = str(record.get("timestamp_utc", ""))
            if not ts.startswith(today):
                continue
            if str(record.get("ticker", "")) == ticker:
                found = True
                break
    except Exception as exc:
        return BenchmarkCheck(
            status="FAIL",
            evidence=f"advisor_score={advisor_score} present but audit read error: {exc}",
        )

    if found:
        return BenchmarkCheck(
            status="PASS",
            evidence=f"advisor_score={advisor_score} with audit evidence for {ticker}",
        )
    return BenchmarkCheck(
        status="FAIL",
        evidence=f"advisor_score={advisor_score} present but no audit entry for {ticker} today",
    )


def _model_quality_gate(
    *,
    model_accuracy: float | None,
    model_auc: float | None,
    alpha_pct: float | None,
    completed_trades: int | None,
    raw_score: float,
) -> tuple[CandidateStatus, bool, bool, float, list[str]]:
    """Evaluate model quality gate.

    Returns (status, new_capital_allowed, paper_trading_only, investment_score, blocking_reasons).
    """
    blocking: list[str] = []
    amber = False

    accuracy = float(model_accuracy) if _valid_number(model_accuracy) else None
    auc = float(model_auc) if _valid_number(model_auc) else None
    alpha = float(alpha_pct) if _valid_number(alpha_pct) else None
    trades = int(completed_trades) if _valid_number(completed_trades) else None

    if accuracy is not None and accuracy < 0.50:
        blocking.append(f"accuracy={accuracy:.4f} < 0.50")
        amber = True
    if auc is not None and auc < 0.50:
        blocking.append(f"auc={auc:.4f} < 0.50")
        amber = True
    if alpha is not None and alpha < 0:
        blocking.append(f"alpha={alpha:.2f}% < 0")
        amber = True
    if trades is not None and trades < 50:
        blocking.append(f"completed_trades={trades} < 50")
        amber = True

    if not amber:
        return ("PASS", True, False, raw_score, [])

    # Cap investment_score at 44 when any gate fails
    investment_score = min(raw_score, 44.0)
    return ("AMBER_WATCHLIST", False, True, investment_score, blocking)


# ---------------------------------------------------------------------------
# Core benchmark logic (exported for tests)
# ---------------------------------------------------------------------------

RunConfig = dict[str, Any]


def evaluate_candidate(
    candidate: dict[str, Any],
    run_config: RunConfig,
) -> CandidateBenchmark:
    """Evaluate a single recommendation candidate for investment readiness."""
    ticker = str(candidate.get("ticker", ""))
    if not ticker:
        return CandidateBenchmark(
            ticker="<missing>",
            track=str(candidate.get("track", "")),
            ready_for_manual_review=False,
            new_capital_allowed=False,
            paper_trading_only=True,
            raw_score=0.0,
            investment_score=0.0,
            status="INVALID_INPUT",
            blocking_reasons=["ticker is missing"],
            checks={},
        )

    track = str(candidate.get("track", ""))
    raw_score = float(candidate.get("recommendation_rank_score", 0.0))

    # --- Config extraction ---
    # run_config may be the bare config dict (when called from tests) or the
    # full input_data dict (when called from run_benchmark with config inside).
    config = run_config.get("config", run_config)  # prefer nested, fall back to bare
    transaction_cost_buffer_pct = float(config.get("transaction_cost_buffer_pct", 0.50))
    horizon_s = int(config.get("horizon_s", 20))
    horizon_l = int(config.get("horizon_l", 63))
    horizon = horizon_s if track == "S" else horizon_l
    audit_log_path = run_config.get("audit_log_path")

    # --- BACKTEST_HONESTY check ---
    bh = candidate.get("backtest_honesty")
    if bh is None:
        bh_status: CheckStatus = "AMBER"
        bh_evidence = "backtest_honesty missing"
    else:
        bh_status = str(bh.get("status", "AMBER"))
        bh_evidence = f"backtest_honesty.status={bh_status}"

    backtest_honesty_check = BenchmarkCheck(status=bh_status, evidence=bh_evidence)

    # --- COST_STRESS checks ---
    backtest_return_pct = candidate.get("backtest_return_pct")
    cost_1x = _cost_stress_check(
        backtest_return_pct=backtest_return_pct,
        transaction_cost_buffer_pct=transaction_cost_buffer_pct,
        multiplier=1,
    )
    cost_2x = _cost_stress_check(
        backtest_return_pct=backtest_return_pct,
        transaction_cost_buffer_pct=transaction_cost_buffer_pct,
        multiplier=2,
    )
    cost_3x = _cost_stress_check(
        backtest_return_pct=backtest_return_pct,
        transaction_cost_buffer_pct=transaction_cost_buffer_pct,
        multiplier=3,
    )

    # --- EMBARGO_STRESS check ---
    # Extract cv_gap from backtest_honesty if available, else from config
    cv_gap: int | None = None
    if bh and isinstance(bh, dict):
        for check in bh.get("checks", []):
            if isinstance(check, dict) and check.get("name") == "WALK_FORWARD_GAP":
                cv_gap = int(check["value"]) if check.get("value") is not None else None
                break
    # Fall back to config-level cv_gap
    if cv_gap is None:
        cv_gap = config.get("cv_gap")

    embargo_check = _embargo_stress_check(cv_gap=cv_gap, horizon=horizon)

    # --- ADVISOR_AUDIT check ---
    advisor_score = candidate.get("advisor_score")
    advisor_check = _advisor_audit_check(
        advisor_score=advisor_score,
        audit_log_path=audit_log_path,
        ticker=ticker,
    )

    # --- MODEL_QUALITY gate ---
    model_accuracy = candidate.get("model_accuracy")
    model_auc = candidate.get("model_auc")
    alpha_pct = candidate.get("alpha_pct")
    completed_trades = candidate.get("completed_trades")

    (mq_status, new_capital_allowed, paper_trading_only, investment_score, mq_blocking) = (
        _model_quality_gate(
            model_accuracy=model_accuracy,
            model_auc=model_auc,
            alpha_pct=alpha_pct,
            completed_trades=completed_trades,
            raw_score=raw_score,
        )
    )

    model_quality_check = BenchmarkCheck(
        status=mq_status,
        evidence=f"accuracy={model_accuracy}, auc={model_auc}, alpha={alpha_pct}, completed_trades={completed_trades}",
    )

    # --- Assemble checks ---
    checks = {
        "BACKTEST_HONESTY": backtest_honesty_check,
        "COST_STRESS_1X": cost_1x,
        "COST_STRESS_2X": cost_2x,
        "COST_STRESS_3X": cost_3x,
        "EMBARGO_STRESS": embargo_check,
        "ADVISOR_AUDIT": advisor_check,
        "MODEL_QUALITY": model_quality_check,
    }

    # --- Blocking reasons aggregation ---
    blocking_reasons: list[str] = list(mq_blocking)

    if bh_status != "PASS":
        blocking_reasons.append(f"backtest_honesty={bh_status}")

    if cost_3x.status == "FAIL":
        blocking_reasons.append("COST_STRESS_3X=FAIL")

    if embargo_check.status == "FAIL":
        blocking_reasons.append("EMBARGO_STRESS=FAIL")

    if advisor_check.status == "FAIL":
        blocking_reasons.append(f"ADVISOR_AUDIT=FAIL ({advisor_check.evidence})")

    # --- ready_for_manual_review ---
    # Must pass BACKTEST_HONESTY, COST_STRESS_3X, EMBARGO_STRESS
    ready = (
        backtest_honesty_check.status == "PASS"
        and cost_3x.status == "PASS"
        and embargo_check.status in ("PASS", "NOT_APPLICABLE")
        and mq_status in ("PASS", "AMBER_WATCHLIST")
    )

    return CandidateBenchmark(
        ticker=ticker,
        track=track,
        ready_for_manual_review=ready,
        new_capital_allowed=new_capital_allowed,
        paper_trading_only=paper_trading_only,
        raw_score=raw_score,
        investment_score=investment_score,
        status=mq_status if mq_status != "PASS" else (
            "PASS" if ready else "FAIL"
        ),
        blocking_reasons=blocking_reasons,
        checks=checks,
    )


def run_benchmark(input_data: dict[str, Any], input_path: str = "") -> RunBenchmark:
    """Core benchmark logic — exported for direct test import."""
    results: list[dict[str, Any]] = input_data.get("results", [])
    run_config: RunConfig = input_data.get("config", {})

    if not results:
        return RunBenchmark(
            schema_version="1.0",
            generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
            input_path=input_path,
            run_verdict="NO_CANDIDATES",
            candidate_count=0,
            ready_count=0,
            candidates=[],
        )

    candidates: list[CandidateBenchmark] = []
    for cand in results:
        benchmark = evaluate_candidate(cand, run_config)
        candidates.append(benchmark)

    ready_count = sum(1 for c in candidates if c.ready_for_manual_review)

    # Determine run verdict
    if ready_count > 0:
        # Check if any ready candidate has amber model quality
        if any(c.status == "AMBER_WATCHLIST" for c in candidates if c.ready_for_manual_review):
            run_verdict: RunVerdict = "AMBER"
        else:
            run_verdict = "READY"
    elif len(candidates) == 0:
        run_verdict = "NO_CANDIDATES"
    else:
        run_verdict = "NOT_INVESTMENT_READY"

    return RunBenchmark(
        schema_version="1.0",
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        input_path=input_path,
        run_verdict=run_verdict,
        candidate_count=len(candidates),
        ready_count=ready_count,
        candidates=candidates,
    )


# ---------------------------------------------------------------------------
# JSON loading
# ---------------------------------------------------------------------------


def load_recommendation_json(path: str | Path) -> dict[str, Any]:
    """Load and parse a recommendations_algo_v2_*.json file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input path does not exist: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {p}: {exc}") from exc


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _serialize_benchmark(obj: Any) -> Any:
    if isinstance(obj, BenchmarkCheck):
        return asdict(obj)
    if isinstance(obj, CandidateBenchmark):
        d = asdict(obj)
        d["checks"] = {k: asdict(v) for k, v in obj.checks.items()}
        return d
    if isinstance(obj, RunBenchmark):
        d = asdict(obj)
        d["candidates"] = [_serialize_benchmark(c) for c in obj.candidates]
        return d
    return obj


def format_json(benchmark: RunBenchmark) -> str:
    return json.dumps(
        _serialize_benchmark(benchmark),
        ensure_ascii=False,
        indent=2,
    )


def format_markdown(benchmark: RunBenchmark) -> str:
    lines = [
        "# Investment Readiness Benchmark",
        "",
        f"- **Schema version**: {benchmark.schema_version}",
        f"- **Generated at (UTC)**: {benchmark.generated_at_utc}",
        f"- **Input path**: {benchmark.input_path}",
        f"- **Run verdict**: `{benchmark.run_verdict}`",
        f"- **Candidate count**: {benchmark.candidate_count}",
        f"- **Ready count**: {benchmark.ready_count}",
        "",
        "---",
        "",
    ]

    for i, cand in enumerate(benchmark.candidates, 1):
        lines += [
            f"## {i}. {cand.ticker} ({cand.track})",
            "",
            f"- **Status**: `{cand.status}`",
            f"- **ready_for_manual_review**: {cand.ready_for_manual_review}",
            f"- **new_capital_allowed**: {cand.new_capital_allowed}",
            f"- **paper_trading_only**: {cand.paper_trading_only}",
            f"- **raw_score**: {cand.raw_score}",
            f"- **investment_score**: {cand.investment_score}",
            f"- **blocking_reasons**: {cand.blocking_reasons}",
            "",
            "### Checks",
            "",
        ]
        for check_name, check in cand.checks.items():
            lines.append(f"- **{check_name}**: `{check.status}` — {check.evidence}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Investment-readiness benchmark for stock recommendation candidates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to recommendations_algo_v2_*.json input file",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write benchmark output",
    )
    parser.add_argument(
        "--format",
        choices=["json", "md"],
        default="json",
        help="Output format (default: json)",
    )
    args = parser.parse_args()

    try:
        input_data = load_recommendation_json(args.input)
    except FileNotFoundError:
        print(f"ERROR: Input path does not exist: {args.input}", file=sys.stderr)
        sys.exit(1)
    except ValueError:
        print(f"ERROR: Malformed JSON in input file: {args.input}", file=sys.stderr)
        sys.exit(1)

    benchmark = run_benchmark(input_data, input_path=args.input)

    output_text = format_json(benchmark) if args.format == "json" else format_markdown(benchmark)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")

    print(f"Benchmark written to {output_path}")
    print(f"Run verdict: {benchmark.run_verdict}")
    print(f"Candidates: {benchmark.candidate_count}, Ready: {benchmark.ready_count}")


if __name__ == "__main__":
    main()