from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", default="reports/hermes")
    parser.add_argument("--out", default="reports/hermes/hermes-issue.md")
    args = parser.parse_args()
    manifest_path = Path(args.reports) / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    lines = [
        "# Hermes Daily Automation Report",
        "",
        f"Verdict: **{manifest.get('verdict', 'UNKNOWN')}**",
        "",
        "## Safety",
        "- new_capital_allowed=false",
        "- paper_trading_only=true",
        "- live_order_execution=false",
        "- auto_buy_sell=false",
        "",
        "## Commands",
    ]
    for item in manifest.get("results", []):
        lines.append(f"- `{' '.join(item.get('command', []))}` -> `{item.get('returncode')}`")
    lines.extend(["", "## Next action", "Review `reports/hermes/run_manifest.json` artifact."])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
