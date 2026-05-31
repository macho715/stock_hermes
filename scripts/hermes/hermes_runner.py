from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPORT_DIR = Path("reports/hermes")


def run(command: list[str], *, cwd: str | None = None) -> dict:
    proc = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=900,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": command,
        "cwd": cwd or ".",
        "returncode": proc.returncode,
        "stdout": proc.stdout[-8000:],
        "stderr": proc.stderr[-8000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="read_report")
    parser.add_argument("--task", default="daily")
    parser.add_argument("--symbol", default="")
    parser.add_argument("--config", default=".hermes/hermes.config.yaml")
    args = parser.parse_args()

    if args.mode not in {"read_report", "full_dry_run", "write_pr"}:
        print(json.dumps({"verdict": "AMBER", "error": f"unsupported mode: {args.mode}"}, indent=2))
        return 1

    started = datetime.now(timezone.utc).isoformat()
    checks = [
        run(["python", "scripts/hermes/guard_safety.py", "--config", args.config]),
        run(["python", "scripts/hermes/guard_sensitive.py"]),
        run(["python", "scripts/hermes/repo_scan.py"]),
        run(["python", "scripts/hermes/dashboard_smoke.py"]),
        run(["python", "-m", "compileall", "-q", "scripts/hermes"]),
    ]
    if args.task in {"daily", "quant", "cfast_profit"} or args.mode == "full_dry_run":
        checks.append(run(["python", "scripts/hermes/cfast_profit_benchmark.py", "--notify"]))
    verdict = "PASS" if all(item["returncode"] == 0 for item in checks) else "AMBER"
    payload = {
        "schema_version": "hermes_run.v1",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "task": args.task,
        "symbol": args.symbol,
        "verdict": verdict,
        "results": checks,
        "safety": {
            "new_capital_allowed": False,
            "paper_trading_only": True,
            "live_order_execution": False,
            "auto_buy_sell": False,
        },
    }
    if args.mode == "write_pr":
        payload["write_pr"] = {
            "approval_required": True,
            "approval_environment": "hermes-write",
            "draft_pr_only": True,
            "auto_merge": False,
        }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "run_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "report": "reports/hermes/run_manifest.json"}, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
