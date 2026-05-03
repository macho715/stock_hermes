"""Backward-compatible entrypoint for the previous single-file script name."""

from main import cli

if __name__ == "__main__":
    raise SystemExit(cli())
