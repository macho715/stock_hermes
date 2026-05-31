from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run(command: list[str]) -> dict:
    proc = subprocess.run(command, text=True, capture_output=True)
    return {"command": command, "returncode": proc.returncode, "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:]}


def main() -> int:
    report = {
        "schema_version": "hermes_repo_scan.v1",
        "git_status": run(["git", "status", "--short", "--branch"]),
        "tracked_count": run(["git", "ls-files"]),
        "key_paths": {
            "backend_root": Path("src/stock_rtx4060").exists(),
            "dashboard_root": Path("root_folder_snapshot/stock-pred-v5").exists(),
            "api_entry": Path("api_server.py").exists(),
            "cfast_validation": Path("invest_algos/examples/run_cfast_validation.py").exists(),
        },
    }
    Path("reports/hermes").mkdir(parents=True, exist_ok=True)
    Path("reports/hermes/repo_scan.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("reports/hermes/repo_scan.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
