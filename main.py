"""Compatibility wrapper for the unified stock_rtx4060 CLI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _root_help() -> str:
    return (
        "usage: main.py [-h] {env,benchmark,report,predict,recommend,paper-run,ops-v1,dashboard-export,demo,journal,self-test} ...\n\n"
        "stock_rtx4060 unified investment OS\n\n"
        "positional arguments:\n"
        "  {env,benchmark,report,predict,recommend,paper-run,ops-v1,dashboard-export,demo,journal,self-test}\n"
        "    env                 validate runtime/GPU environment\n"
        "    benchmark           run synthetic CPU/GPU benchmark\n"
        "    report              generate Daily Brief/Risk reports\n"
        "    predict             train/predict from CSV or yfinance\n"
        "    recommend           rank report-only Track-S/Track-L candidates\n"
        "    paper-run           paper-only virtual trading — no broker orders (screening only)\n"
        "    ops-v1              run report-only Ops v1 workflow with manual approval artifacts\n"
        "    dashboard-export    convert recommendation JSON into a dashboard snapshot\n"
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
        "  py -3.12 -m venv .venv\n"
        "  .\\.venv\\Scripts\\Activate.ps1\n"
        "  python -m pip install --upgrade pip\n"
        "  pip install -r requirements.txt\n"
        "  python main.py self-test\n"
    )


def cli() -> int:
    if sys.argv[1:] and sys.argv[1] in {"-h", "--help"}:
        print(_root_help())
        return 0
    try:
        from stock_rtx4060.main import main
    except ModuleNotFoundError as exc:
        print(_dependency_help(exc), file=sys.stderr)
        return 1
    return main()


if __name__ == "__main__":
    raise SystemExit(cli())
