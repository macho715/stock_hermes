from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

SAFE_POLICY = {
    "new_capital_allowed": "false",
    "paper_trading_only": "true",
    "live_order_execution": "false",
    "auto_buy_sell": "false",
    "broker_adapter_activation": "false",
}

ENV_GATES = {
    "NEW_CAPITAL_ALLOWED": "false",
    "PAPER_TRADING_ONLY": "true",
    "LIVE_ORDER_EXECUTION": "false",
    "AUTO_BUY_SELL": "false",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*([^\s#]+)", text)
    if not match:
        return None
    return match.group(1).strip().strip("\"'").lower()


def check_config(config: Path) -> list[str]:
    if not config.exists():
        return [f"missing config: {config}"]
    text = read_text(config)
    blockers = []
    for key, expected in SAFE_POLICY.items():
        actual = yaml_scalar(text, key)
        if actual != expected:
            blockers.append(f"{key} must be {expected}, found {actual!r}")
    return blockers


def check_environment() -> list[str]:
    blockers = []
    for name, expected in ENV_GATES.items():
        actual = os.environ.get(name)
        if actual is not None and actual.strip().lower() != expected:
            blockers.append(f"{name} must be {expected}, found {actual!r}")
    return blockers


def check_tracked_env() -> list[str]:
    proc = subprocess.run(["git", "ls-files", ".env", ".env.*"], text=True, capture_output=True)
    if proc.returncode != 0:
        return []
    allowed_examples = {".env.example", ".env.sample", ".env.template"}
    return [
        f"tracked env file is prohibited: {line}"
        for line in proc.stdout.splitlines()
        if line.strip() and Path(line.strip()).name not in allowed_examples
    ]


def write_zero(blockers: list[str]) -> None:
    Path("reports/hermes").mkdir(parents=True, exist_ok=True)
    out = Path("reports/hermes/ZERO.md")
    out.write_text("# ZERO - Hermes safety gate failed\n\n" + "\n".join(f"- {b}" for b in blockers) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=".hermes/hermes.config.yaml")
    args = parser.parse_args()
    blockers: list[str] = []
    blockers.extend(check_config(Path(args.config)))
    blockers.extend(check_environment())
    blockers.extend(check_tracked_env())
    if blockers:
        write_zero(blockers)
        for blocker in blockers:
            print(f"ZERO: {blocker}")
        return 2
    print("Hermes safety gate PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
