"""Compatibility wrapper for the stock_rtx4060 CLI."""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path


def _root_help() -> str:
    return (
        "usage: main.py [-h] {env,benchmark,report,predict,recommend,ops-v1,dashboard-export,demo,journal,self-test} ...\n\n"
        "stock_rtx4060 investment OS\n\n"
        "positional arguments:\n"
        "  {env,benchmark,report,predict,recommend,ops-v1,dashboard-export,demo,journal,self-test}\n"
        "    env                 validate runtime/GPU environment\n"
        "    benchmark           run synthetic CPU/GPU benchmark\n"
        "    report              generate Daily Brief/Risk reports\n"
        "    predict             train/predict from CSV or yfinance\n"
        "    recommend           rank report-only Track-S/Track-L candidates\n"
        "    ops-v1              run report-only Ops v1 workflow\n"
        "    dashboard-export    convert recommendation JSON into dashboard snapshot\n"
        "    demo                create sample data and reports\n"
        "    journal             append decision journal row\n"
        "    self-test           run internal smoke tests\n\n"
        "options:\n"
        "  -h, --help            show this help message and exit\n"
    )


def _dependency_help(exc: ModuleNotFoundError) -> str:
    missing = exc.name or "required package"
    return (
        f"Missing Python package: {missing}\n\n"
        "Run with a prepared Python environment, for example:\n"
        "  .\\run.ps1 self-test\n\n"
        "Or install dependencies manually:\n"
        "  py -3.11 -m venv .venv\n"
        "  .\\.venv\\Scripts\\Activate.ps1\n"
        "  python -m pip install --upgrade pip\n"
        "  pip install -r requirements.txt\n"
        "  python main.py self-test\n"
    )


def cli() -> int:
    root = Path(__file__).resolve().parent
    unified_root = root / "stock_rtx4060_unified"
    unified_main = unified_root / "main.py"
    unified_python = unified_root / ".venv" / "Scripts" / "python.exe"
    if not unified_main.exists():
        print(f"Unified entrypoint not found: {unified_main}", file=sys.stderr)
        return 1
    python = str(unified_python if unified_python.exists() else sys.executable)
    try:
        return subprocess.call([python, str(unified_main), *sys.argv[1:]], cwd=str(unified_root))
    except ModuleNotFoundError as exc:
        print(_dependency_help(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
