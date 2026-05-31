from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reason", required=True)
    parser.add_argument("--out", default="reports/hermes/ZERO.md")
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(["# ZERO - Hermes Automation Blocked", "", f"time_utc: {datetime.now(timezone.utc).isoformat()}", f"reason: {args.reason}", ""]) ,
        encoding="utf-8",
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
