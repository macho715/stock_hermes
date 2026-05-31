from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPORT_DIR = Path("reports/hermes")
BENCHMARK_SOURCE = Path("invest_algos/demo_output/internet_latest_yahoo/profit_engine_benchmark/profit_engine_benchmark.csv")
BENCHMARK_REPORT = Path("invest_algos/demo_output/internet_latest_yahoo/profit_engine_benchmark/profit_engine_report.md")
RUNNER = Path("invest_algos/examples/run_cfast_profit_engine_benchmark.py")

TARGET_CANDIDATE = "cfast_profit_engine_patch"
TARGET_ANNUAL_RETURN = 0.1371
TARGET_X5_ANNUAL_RETURN = 0.05


def _run_benchmark() -> dict:
    proc = subprocess.run(
        ["python", str(RUNNER)],
        text=True,
        capture_output=True,
        timeout=1800,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": ["python", str(RUNNER)],
        "returncode": proc.returncode,
        "stdout": proc.stdout[-8000:],
        "stderr": proc.stderr[-8000:],
    }


def _read_candidate(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row.get("candidate") == TARGET_CANDIDATE:
            return row
    raise RuntimeError(f"candidate not found: {TARGET_CANDIDATE}")


def _as_float(row: dict, key: str) -> float:
    return float(row[key])


def _as_bool(row: dict, key: str) -> bool:
    return str(row.get(key, "")).strip().lower() == "true"


def _send_telegram(text: str) -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return {"sent": False, "reason": "missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"}
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with urllib.request.urlopen(url, data=data, timeout=20) as response:
            payload = response.read().decode("utf-8", errors="replace")
        return {"sent": True, "response": payload[:500]}
    except Exception as exc:  # pragma: no cover - network boundary
        return {"sent": False, "reason": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    run_result = _run_benchmark()

    verdict = "PASS"
    blockers: list[str] = []
    if run_result["returncode"] != 0:
        verdict = "ZERO"
        blockers.append("benchmark_runner_failed")

    row: dict = {}
    if not blockers:
        row = _read_candidate(BENCHMARK_SOURCE)
        annual_return = _as_float(row, "ann_return_net")
        x5_return = _as_float(row, "x5_ann_return_net")
        base_forward_pass = _as_bool(row, "base_forward_pass")
        x2_forward_pass = _as_bool(row, "x2_forward_pass")

        if abs(annual_return - TARGET_ANNUAL_RETURN) > 0.0001:
            verdict = "ZERO"
            blockers.append("annual_return_not_reproduced")
        if x5_return < TARGET_X5_ANNUAL_RETURN:
            verdict = "AMBER" if verdict == "PASS" else verdict
            blockers.append("x5_cost_stress_below_5pct_target")
        if not (base_forward_pass and x2_forward_pass):
            verdict = "AMBER" if verdict == "PASS" else verdict
            blockers.append("forward_pass_false")

    if BENCHMARK_SOURCE.exists():
        shutil.copy2(BENCHMARK_SOURCE, REPORT_DIR / "profit_engine_benchmark.csv")
    if BENCHMARK_REPORT.exists():
        shutil.copy2(BENCHMARK_REPORT, REPORT_DIR / "profit_engine_report.md")

    annual_return = _as_float(row, "ann_return_net") if row else None
    x5_return = _as_float(row, "x5_ann_return_net") if row else None
    base_forward_pass = _as_bool(row, "base_forward_pass") if row else None
    x2_forward_pass = _as_bool(row, "x2_forward_pass") if row else None
    march_return = _as_float(row, "march_2026_return") if row else None
    march_dbc_weight = _as_float(row, "march_dbc_weight") if row else None

    payload = {
        "schema_version": "hermes_cfast_profit_benchmark.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "blockers": blockers,
        "candidate": TARGET_CANDIDATE,
        "annual_return_reproduced": annual_return is not None and abs(annual_return - TARGET_ANNUAL_RETURN) <= 0.0001,
        "annual_return": annual_return,
        "target_annual_return": TARGET_ANNUAL_RETURN,
        "x5_cost_stress": {
            "annual_return": x5_return,
            "target": TARGET_X5_ANNUAL_RETURN,
            "pass": x5_return is not None and x5_return >= TARGET_X5_ANNUAL_RETURN,
        },
        "forward_pass": {
            "base": base_forward_pass,
            "x2": x2_forward_pass,
            "pass": bool(base_forward_pass and x2_forward_pass),
        },
        "march_2026_return": march_return,
        "march_dbc_weight": march_dbc_weight,
        "safety": {
            "paper_trading_only": True,
            "live_trading_allowed": False,
            "broker_execution_allowed": False,
            "guaranteed_return_wording": False,
        },
        "run_result": run_result,
    }
    summary_path = REPORT_DIR / "cfast_profit_benchmark_summary.json"
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Hermes CFAST Profit Benchmark",
        "",
        f"- verdict: {verdict}",
        f"- candidate: {TARGET_CANDIDATE}",
        f"- annual_return: {annual_return:.2%}" if annual_return is not None else "- annual_return: unavailable",
        f"- 13.71_reproduced: {payload['annual_return_reproduced']}",
        f"- x5_annual_return: {x5_return:.2%}" if x5_return is not None else "- x5_annual_return: unavailable",
        f"- forward_pass: {payload['forward_pass']['pass']}",
        f"- blockers: {', '.join(blockers) if blockers else 'none'}",
        "",
        "Safety: paper_trading_only=true, no broker API, no live trading, no guaranteed-return wording.",
    ]
    (REPORT_DIR / "cfast_profit_benchmark_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    if args.notify:
        message = (
            "Hermes CFAST profit benchmark\n"
            f"Verdict: {verdict}\n"
            f"Annual return: {annual_return:.2%}\n" if annual_return is not None else f"Verdict: {verdict}\n"
        )
        if annual_return is not None:
            message += (
                f"13.71 reproduced: {payload['annual_return_reproduced']}\n"
                f"x5 annual: {x5_return:.2%}\n"
                f"forward_pass: {payload['forward_pass']['pass']}\n"
                f"blockers: {', '.join(blockers) if blockers else 'none'}"
            )
        payload["telegram"] = _send_telegram(message)
        summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"verdict": verdict, "report": str(summary_path)}, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
