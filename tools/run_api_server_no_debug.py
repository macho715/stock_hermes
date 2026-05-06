"""Run the local Flask API without debug reloader for browser verification."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api_server import app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the local Flask API without debug reloader")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5151)
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
