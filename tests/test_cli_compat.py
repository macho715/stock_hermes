"""CLI backward-compatibility lock: every documented verb must keep `--help` exit 0."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

CLI_VERBS = [
    "env",
    "benchmark",
    "report",
    "predict",
    "recommend",
    "paper-run",
    "ops-v1",
    "dashboard-export",
    "demo",
    "journal",
    "self-test",
]


@pytest.mark.parametrize("verb", CLI_VERBS)
def test_cli_help_exits_zero(verb: str) -> None:
    """Locked invariant: each top-level CLI verb keeps `--help` working."""
    result = subprocess.run(
        [sys.executable, "main.py", verb, "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"CLI verb '{verb}' broke `--help` (rc={result.returncode}).\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )


def test_top_level_help_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
