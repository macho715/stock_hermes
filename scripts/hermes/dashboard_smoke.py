from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    checks = {
        "dashboard_root": Path("root_folder_snapshot/stock-pred-v5").exists(),
        "dashboard_entry": Path("root_folder_snapshot/stock-pred-v5/src/StockPredV5.jsx").exists(),
        "package_json": Path("root_folder_snapshot/stock-pred-v5/package.json").exists(),
    }
    verdict = "PASS" if all(checks.values()) else "AMBER"
    Path("reports/hermes").mkdir(parents=True, exist_ok=True)
    Path("reports/hermes/dashboard_smoke.json").write_text(
        json.dumps({"schema_version": "hermes_dashboard_smoke.v1", "verdict": verdict, "checks": checks}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"verdict": verdict, "report": "reports/hermes/dashboard_smoke.json"}))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
