"""
Preview server for stock_rtx4060 unified — runs Vite + API in one command.

Run: python preview_server.py
Starts:
  1. Flask API server (port 5151) in background thread
  2. Vite dev server (port 5173) in background subprocess
  3. Opens browser

CORS configured automatically. No additional setup needed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VITE_APP = ROOT.parent / "stock-pred-v5"


def run_api():
    print("[preview] Starting API server on http://127.0.0.1:5151")
    import api_server  # noqa: F401
    from api_server import app
    app.run(host="127.0.0.1", port=5151, debug=False, use_reloader=False)


def run_vite():
    print("[preview] Starting Vite dev server on http://localhost:5173")
    if sys.platform == "win32":
        npm_cmd = r"C:\nvm4w\nodejs\npm.cmd"
        if not os.path.exists(npm_cmd):
            import shutil
            found = shutil.which("npm.cmd") or shutil.which("npm")
            npm_cmd = found if found and os.path.exists(found) else "npm.cmd"
        proc = subprocess.Popen(
            [npm_cmd, "--prefix", str(VITE_APP), "run", "dev"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        # Stream Vite output line by line
        for line in proc.stdout:
            print(line.decode("utf-8", errors="replace").rstrip())
        return proc.returncode
    else:
        result = subprocess.run(
            ["npm", "--prefix", str(VITE_APP), "run", "dev"],
            capture_output=False,
        )
        return result.returncode


def main():
    # Start API in background thread (daemon so it stops when main exits)
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    time.sleep(1.5)  # Wait for API server to initialize

    # Open browser
    vite_url = "http://localhost:5173"
    print(f"[preview] Opening browser at {vite_url}")
    webbrowser.open(vite_url)

    # Run Vite in this process (blocking) — stdout piped to parent
    try:
        rc = run_vite()
    except KeyboardInterrupt:
        print("[preview] Shutting down...")
        rc = 0
    sys.exit(rc)


if __name__ == "__main__":
    main()