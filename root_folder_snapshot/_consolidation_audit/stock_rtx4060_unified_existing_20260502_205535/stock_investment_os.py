"""Backward-compatible entrypoint for the unified CLI."""

from main import cli

if __name__ == "__main__":
    raise SystemExit(cli())
