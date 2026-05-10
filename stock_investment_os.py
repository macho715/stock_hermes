"""Backward-compatible old entrypoint name for the unified package."""

from __future__ import annotations

from main import cli

if __name__ == "__main__":
    raise SystemExit(cli())
