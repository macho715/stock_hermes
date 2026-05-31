from __future__ import annotations

from pathlib import Path
import subprocess

def git_files() -> list[Path]:
    proc = subprocess.run(["git", "ls-files"], text=True, capture_output=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return []
    return [Path(line.strip()) for line in proc.stdout.splitlines() if line.strip()]


def scan_tracked_files() -> list[str]:
    blockers: list[str] = []
    allowed_examples = {".env.example", ".env.sample", ".env.template"}
    for path in git_files():
        if path.name.startswith(".env") and path.name not in allowed_examples:
            blockers.append(f"tracked env file: {path}")
        if path.suffix.lower() in {".pem", ".ppk", ".key"}:
            blockers.append(f"tracked private key-like file: {path}")
    return blockers


def main() -> int:
    blockers = scan_tracked_files()
    if blockers:
        Path("reports/hermes").mkdir(parents=True, exist_ok=True)
        out = Path("reports/hermes/ZERO-sensitive.md")
        out.write_text("# ZERO - sensitive data gate failed\n\n" + "\n".join(f"- {b}" for b in blockers) + "\n", encoding="utf-8")
        print(out.read_text(encoding="utf-8"))
        return 2
    print("Hermes sensitive gate PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
