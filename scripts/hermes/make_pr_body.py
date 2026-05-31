from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", default="reports/hermes")
    parser.add_argument("--out", default="reports/hermes/pr-body.md")
    args = parser.parse_args()
    manifest_path = Path(args.reports) / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    lines = [
        "# Hermes PR Factory",
        "",
        f"Verdict: **{manifest.get('verdict', 'UNKNOWN')}**",
        f"Mode: `{manifest.get('mode', 'UNKNOWN')}`",
        f"Task: `{manifest.get('task', 'UNKNOWN')}`",
        "",
        "## Safety Boundary",
        "- paper trading only",
        "- draft PR only",
        "- no auto-merge",
        "- no broker action",
        "",
        "## Checks",
    ]
    for item in manifest.get("results", []):
        lines.append(f"- `{' '.join(item.get('command', []))}` -> `{item.get('returncode')}`")
    lines.extend(["", "## Review Notes", "Review the patch and artifacts before merging."])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
