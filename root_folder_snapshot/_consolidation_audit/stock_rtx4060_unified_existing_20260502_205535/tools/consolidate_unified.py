from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\jichu\Downloads\주식")
TARGET = ROOT / "stock_rtx4060_unified"
AUDIT = ROOT / "_consolidation_audit"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

SOURCE_ROOTS = [
    ("algo_v2", ROOT / "stock_rtx4060_algo_v2"),
    ("bundle_algo_v2", ROOT / "stock_rtx4060_algo_v2_bundle" / "stock_rtx4060_algo_v2"),
    ("recommendation_patch", ROOT / "stock_rtx4060_recommendation_patch"),
    ("workspaces", ROOT / "workspaces"),
]

EXCLUDED_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
    "coverage",
    "tmp",
    "cache",
    "logs",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def detect_type(path: Path) -> str:
    ext = path.suffix.lower()
    low = str(path).lower()
    if any(part.lower() in EXCLUDED_DIR_NAMES for part in path.parts):
        return "cache/build/runtime-excluded"
    if ext == ".py":
        return "python"
    if ext in {".md", ".txt", ".rst"}:
        return "document"
    if ext in {".json", ".toml", ".yaml", ".yml", ".ini", ".cfg"}:
        return "config_or_json"
    if ext in {".csv", ".tsv"}:
        return "data"
    if ext in {".ps1", ".bat", ".cmd", ".sh"}:
        return "script"
    if ext in {".zip", ".7z", ".tar", ".gz"}:
        return "archive"
    if "report" in low or "benchmark" in low:
        return "generated_report_or_evidence"
    return "other"


def role_for(relative_path: str) -> str:
    rel = relative_path.replace("\\", "/").lower()
    if "__pycache__" in rel or ".pytest_cache" in rel:
        return "cache artifact"
    if rel.startswith("recommendation_reports/") or rel.startswith("reports/") or "/reports/" in rel:
        return "generated output/evidence"
    if rel.endswith("main.py"):
        return "entry point candidate"
    if rel.endswith(("requirements.txt", "requirements-gpu-wsl.txt", "requirements-gpu-wsl2.txt")):
        return "dependency config candidate"
    if rel.endswith("pyproject.toml"):
        return "project config candidate"
    if rel.startswith("tests/") or "/tests/" in rel:
        return "test candidate"
    if rel.endswith(".py"):
        return "python source candidate"
    if rel.endswith(("readme.md", "setup.md", "changelog.md")) or any(
        key in rel for key in ("architecture", "layout", "spec", "uiux", "plan", "agent", "patch_notes")
    ):
        return "documentation candidate"
    if rel.endswith(".csv"):
        return "sample/input data candidate"
    return "support/evidence candidate"


def copy_tree_filtered(src: Path, dst: Path) -> None:
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        if set(part.lower() for part in path.relative_to(src).parts) & EXCLUDED_DIR_NAMES:
            continue
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def safe_name(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{path.parent.name}_{path.name}")


def inventory_sources() -> tuple[list[dict], dict[str, list[dict]]]:
    records: list[dict] = []
    for source_root, root_path in SOURCE_ROOTS:
        if not root_path.exists():
            continue
        for path in root_path.rglob("*"):
            if not path.is_file():
                continue
            rel_path = path.relative_to(root_path)
            stat = path.stat()
            parts_lower = {part.lower() for part in rel_path.parts}
            record = {
                "source_root": source_root,
                "source_root_path": str(root_path),
                "source_path": str(path),
                "relative_path": str(rel_path),
                "file_name": path.name,
                "extension": path.suffix.lower(),
                "size": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                "sha256_hash": sha256(path),
                "detected_type": detect_type(rel_path),
                "role": role_for(str(rel_path)),
                "excluded_by_dir": bool(parts_lower & EXCLUDED_DIR_NAMES),
                "duplicate_group_id": "",
                "keep_or_exclude_decision": "",
                "decision_reason": "",
                "risk": "",
                "required_patch": "",
                "target_path": "",
                "duplicate_of": "",
            }
            records.append(record)

    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[record["sha256_hash"]].append(record)
    duplicate_no = 1
    for group in groups.values():
        if len(group) < 2:
            continue
        duplicate_id = f"DUP-{duplicate_no:04d}"
        duplicate_no += 1
        first = group[0]["source_path"]
        for record in group:
            record["duplicate_group_id"] = duplicate_id
            if record["source_path"] != first:
                record["duplicate_of"] = first
    return records, groups


def write_runtime_files() -> None:
    pkg_dst = TARGET / "src" / "stock_rtx4060"
    pkg_dst.mkdir(parents=True, exist_ok=True)
    for path in (ROOT / "workspaces" / "stock_rtx4060").glob("*.py"):
        shutil.copy2(path, pkg_dst / path.name)

    main_py = '''"""Compatibility wrapper for the stock_rtx4060 unified CLI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _root_help() -> str:
    return (
        "usage: main.py [-h] {env,benchmark,report,predict,recommend,demo,journal,self-test} ...\\n\\n"
        "stock_rtx4060 unified investment OS\\n\\n"
        "positional arguments:\\n"
        "  {env,benchmark,report,predict,recommend,demo,journal,self-test}\\n"
        "    env                 validate runtime/GPU environment\\n"
        "    benchmark           run synthetic CPU/GPU benchmark\\n"
        "    report              generate Daily Brief/Risk reports\\n"
        "    predict             train/predict from CSV or yfinance\\n"
        "    recommend           rank report-only Track-S/Track-L candidates\\n"
        "    demo                create sample data and reports\\n"
        "    journal             append decision journal row\\n"
        "    self-test           run internal smoke tests\\n\\n"
        "options:\\n"
        "  -h, --help            show this help message and exit\\n"
    )


def _dependency_help(exc: ModuleNotFoundError) -> str:
    missing = exc.name or "required package"
    return (
        f"Missing Python package: {missing}\\n\\n"
        "Run with a prepared Python environment, for example:\\n"
        "  .\\run.ps1 self-test\\n\\n"
        "Or install dependencies manually:\\n"
        "  py -3.11 -m venv .venv\\n"
        "  .\\.venv\\Scripts\\Activate.ps1\\n"
        "  python -m pip install --upgrade pip\\n"
        "  pip install -r requirements.txt\\n"
        "  python main.py self-test\\n"
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
'''
    (TARGET / "main.py").write_text(main_py, encoding="utf-8")
    (TARGET / "stock_investment_os.py").write_text(
        '"""Backward-compatible entrypoint for the unified CLI."""\n\nfrom main import cli\n\nif __name__ == "__main__":\n    raise SystemExit(cli())\n',
        encoding="utf-8",
    )
    shutil.copy2(ROOT / "run.ps1", TARGET / "run.ps1")

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    if "scikit-learn" not in requirements:
        requirements = requirements.replace("pandas>=2.2\n", "pandas>=2.2\nscikit-learn>=1.1\n")
    (TARGET / "requirements.txt").write_text(requirements, encoding="utf-8")
    (TARGET / "requirements-dev.txt").write_text("-r requirements.txt\npytest>=8\n", encoding="utf-8")
    shutil.copy2(ROOT / "requirements-gpu-wsl.txt", TARGET / "requirements-gpu-wsl.txt")

    pyproject = '''[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]

[tool.black]
line-length = 120
target-version = ["py311"]

[tool.setuptools.packages.find]
where = ["src"]
'''
    (TARGET / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    test_core = (ROOT / "tests" / "test_core.py").read_text(encoding="utf-8")
    test_core = test_core.replace("from workspaces.stock_rtx4060.", "from stock_rtx4060.")
    (TARGET / "tests").mkdir(parents=True, exist_ok=True)
    (TARGET / "tests" / "test_core.py").write_text(test_core, encoding="utf-8")


def write_docs() -> None:
    (TARGET / "docs").mkdir(parents=True, exist_ok=True)
    (TARGET / "README.md").write_text(
        """# stock_rtx4060_unified

`stock_rtx4060_unified` is a consolidated, local, report-only stock investment analysis CLI.

It keeps one executable package under `src/stock_rtx4060` and removes duplicate bundle, patch, cache, and generated-output copies from the runtime path.

## Verified Scope

| Area | Current implementation |
|---|---|
| CLI | `main.py` delegates to `src/stock_rtx4060/main.py`. |
| Runner | `run.ps1` resolves `.venv`, Python 3.12, Python 3.11, then `python`. |
| Features | `feature_engine.py` builds lagged Algorithm v2 OHLCV indicators and targets. |
| Model | `ensemble_model.py` supports leak-safe walk-forward CV, OOF probabilities, logistic fallback, XGBoost CPU/CUDA request, and optional LSTM. |
| Backtest | `backtester.py` supports fixed risk, fractional Kelly, costs, slippage, stops, and monthly stop. |
| Recommendation | `recommendation_engine.py` writes `screening_output_only` `recommendations_algo_v2_*.md/json`. |
| Reports | Markdown, JSON, and CSV files are written locally. |

## Run

```powershell
python main.py --help
.\\run.ps1 self-test
.\\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations
```

## Test

```powershell
python -m compileall .
pytest
```

If the default `python` lacks pytest, use the validated Python 3.12 interpreter on this machine:

```powershell
C:\\Users\\jichu\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m pytest -q
```

## Safety Boundary

This project does not place broker orders. Outputs are screening reports only and require manual review.
""",
        encoding="utf-8",
    )
    (TARGET / "CHANGELOG.md").write_text(
        f"""# Changelog

All notable changes to `stock_rtx4060_unified` are documented here.

## [Unreleased]

### Added

- Created unified executable folder at `stock_rtx4060_unified` on {NOW}.
- Added `src/stock_rtx4060` as the single active package location.
- Added consolidation audit reports under `reports/`.

### Changed

- Selected the validated active package from `workspaces/stock_rtx4060` over raw bundle and patch variants.
- Patched root `main.py`, `pyproject.toml`, and tests for `src` layout.
- Normalized docs into root `README.md`, root `CHANGELOG.md`, and `docs/`.

### Removed From Runtime Path

- Exact duplicate bundle files.
- Python cache files.
- Generated benchmark/recommendation reports from source folders.
- Superseded raw patch source variants.

### Security

- No broker execution path was added.
- Source folders were not deleted.
""",
        encoding="utf-8",
    )
    docs = {
        "SETUP.md": """# SETUP

## Install

```powershell
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For tests in a clean environment:

```powershell
pip install -r requirements-dev.txt
```

## Validate

```powershell
python --version
python -m compileall .
python main.py --help
pytest
powershell -ExecutionPolicy Bypass -File .\\run.ps1
```

## Common Commands

```powershell
.\\run.ps1 self-test
.\\run.ps1 env --xgboost --output reports/runtime_status.json
.\\run.ps1 benchmark --rows 800 --repeats 1 --output-dir reports/benchmark_smoke
.\\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations
```

## GPU Note

`requirements-gpu-wsl.txt` is for WSL2/Linux TensorFlow GPU validation. Do not install it by default on native Windows.
""",
        "SYSTEM_ARCHITECTURE.md": """# SYSTEM_ARCHITECTURE

## Overview

`stock_rtx4060_unified` is a local Python CLI. It has no HTTP API, no web server, and no broker execution integration.

## Component Diagram

```mermaid
flowchart TD
    User[Operator] --> Run[run.ps1]
    User --> Main[main.py]
    Run --> Main
    Main --> CLI[src/stock_rtx4060/main.py]
    CLI --> Feature[feature_engine.py]
    CLI --> Model[ensemble_model.py]
    CLI --> Risk[risk_rules.py]
    CLI --> Backtest[backtester.py]
    CLI --> Recommend[recommendation_engine.py]
    CLI --> Reports[reports.py]
    CLI --> Env[hw_profile.py]
    Feature --> Model
    Model --> Backtest
    Model --> Recommend
    Risk --> Recommend
    Backtest --> Reports
    Recommend --> Out[Markdown/JSON reports]
    Reports --> Out
```

## Data Flow

```mermaid
flowchart LR
    A[CSV, yfinance, or synthetic OHLCV] --> B[normalize_ohlcv]
    B --> C[Algorithm v2 lagged features]
    C --> D[leak-safe CV with gap]
    D --> E[OOF probabilities]
    E --> F[dry-run backtest]
    D --> G[risk-gated recommendation]
    F --> H[Markdown/JSON outputs]
    G --> H
```

## Boundaries

| Boundary | State |
|---|---|
| Broker orders | Not implemented. |
| Web dashboard | Not implemented. |
| Runtime state | Local reports only. |
| Secrets | No secret loader found in selected runtime path. |
""",
        "LAYOUT.md": """# LAYOUT

## Tree

```text
stock_rtx4060_unified/
├── README.md
├── CHANGELOG.md
├── main.py
├── stock_investment_os.py
├── run.ps1
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── requirements-gpu-wsl.txt
├── src/
│   └── stock_rtx4060/
├── tests/
├── docs/
├── examples/
├── reports/
├── workspaces/
├── archive/
│   └── original_inputs/
├── review_needed/
└── tools/
```

## Active Source

| Path | Purpose |
|---|---|
| `src/stock_rtx4060/main.py` | CLI router. |
| `src/stock_rtx4060/feature_engine.py` | Algorithm v2 feature generation. |
| `src/stock_rtx4060/ensemble_model.py` | Model training, CV, and prediction. |
| `src/stock_rtx4060/backtester.py` | Dry-run backtesting. |
| `src/stock_rtx4060/recommendation_engine.py` | Report-only candidate ranking. |
| `src/stock_rtx4060/reports.py` | Markdown/JSON/CSV report writer. |
| `src/stock_rtx4060/risk_rules.py` | Track-S and Track-L gates. |
| `src/stock_rtx4060/hw_profile.py` | Runtime/GPU checks. |
| `tests/test_core.py` | Regression tests for selected runtime path. |

## Generated/Review Areas

- `reports/`: consolidation reports and future runtime output.
- `review_needed/`: non-runtime source evidence requiring manual review.
- `workspaces/`: reserved for future generated runs; source workspaces were not copied wholesale.
""",
        "AGENTS.md": """# AGENTS

## Scope

These instructions apply to `stock_rtx4060_unified`.

## Rules

- Keep active code under `src/stock_rtx4060`.
- Do not add broker order execution without a separate approved spec.
- Do not write secrets, account IDs, or broker credentials into reports.
- Treat `review_needed/` as non-runtime evidence.
- Run `python -m compileall .`, `python main.py --help`, and pytest after code changes.
""",
        "SPEC.md": """# SPEC

## Purpose

`stock_rtx4060_unified` is a consolidated report-only stock screening and backtesting CLI.

## Functional Contract

| Requirement | Contract |
|---|---|
| CLI | Must support `env`, `benchmark`, `report`, `predict`, `recommend`, `demo`, `journal`, and `self-test`. |
| Feature pipeline | Must build lagged OHLCV features and target columns without using future target values as features. |
| Model pipeline | Must report leak-safe walk-forward CV with explicit gap and OOF coverage when available. |
| Recommendation | Must label outputs `screening_output_only` and write local Markdown/JSON reports. |
| Backtest | Must remain dry-run and must not trigger live orders. |
| GPU | Must be validated through explicit runtime checks before performance claims. |

## Non-Goals

- Broker order execution.
- Personalized investment advice.
- Browser dashboard or HTTP API.
- Secret storage.

## Open Items

- 가정: real portfolio capital, broker, market scope, and data vendor are not defined in source files.
""",
        "UIUX.md": """# UIUX

The current user experience is CLI plus Markdown/JSON/CSV output.

A browser dashboard is not implemented. The current dashboard equivalent is the generated `risk_dashboard_*.md` report.
""",
        "PATCH_NOTES.md": """# PATCH_NOTES

This unified folder selects the active, validated `workspaces/stock_rtx4060` implementation and excludes raw duplicate patch bundles from the runtime path.

See `reports/consolidation_report.md`, `reports/conflict_resolution.md`, and `reports/deleted_or_excluded_candidates.csv` for the evidence trail.
""",
    }
    for name, text in docs.items():
        (TARGET / "docs" / name).write_text(text, encoding="utf-8")


def tree_lines(base: Path, max_files: int = 260) -> list[str]:
    lines = [base.name + "/"]
    count = 0

    def walk(path: Path, prefix: str = "") -> None:
        nonlocal count
        entries = sorted([p for p in path.iterdir() if p.name not in {"__pycache__", ".pytest_cache"}], key=lambda p: (not p.is_dir(), p.name.lower()))
        for index, entry in enumerate(entries):
            if count >= max_files:
                return
            connector = "└── " if index == len(entries) - 1 else "├── "
            lines.append(prefix + connector + entry.name + ("/" if entry.is_dir() else ""))
            count += 1
            if entry.is_dir():
                walk(entry, prefix + ("    " if index == len(entries) - 1 else "│   "))

    walk(base)
    if count >= max_files:
        lines.append("... truncated ...")
    return lines


def write_reports(records: list[dict], groups: dict[str, list[dict]]) -> None:
    inventory_fields = [
        "source_root",
        "relative_path",
        "file_name",
        "extension",
        "size",
        "modified_time",
        "sha256_hash",
        "detected_type",
        "role",
        "duplicate_group_id",
        "keep_or_exclude_decision",
        "decision_reason",
        "risk",
        "required_patch",
        "target_path",
    ]
    write_csv(TARGET / "reports" / "source_inventory.csv", records, inventory_fields)

    excluded = [r for r in records if r["keep_or_exclude_decision"] != "KEPT"]
    excluded_rows = [
        {
            "No": i,
            "Source Path": r["source_path"],
            "Reason": r["decision_reason"],
            "Duplicate Of": r["duplicate_of"],
            "Hash": r["sha256_hash"],
            "Risk": r["risk"],
            "Decision": r["keep_or_exclude_decision"],
        }
        for i, r in enumerate(excluded, start=1)
    ]
    write_csv(
        TARGET / "reports" / "deleted_or_excluded_candidates.csv",
        excluded_rows,
        ["No", "Source Path", "Reason", "Duplicate Of", "Hash", "Risk", "Decision"],
    )

    conflict_rows: list[dict] = []
    no = 1
    by_rel: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if not record["excluded_by_dir"]:
            by_rel[record["relative_path"].replace("\\", "/")].append(record)
    for rel, group in by_rel.items():
        hashes = {item["sha256_hash"] for item in group}
        if len(group) > 1 and len(hashes) > 1:
            selected = next((item for item in group if item["keep_or_exclude_decision"] == "KEPT"), None)
            conflict_rows.append(
                {
                    "No": no,
                    "File": rel,
                    "Conflict Type": "Same path different content",
                    "Selected Version": selected["source_path"] if selected else "Generated normalized target or review_needed",
                    "Rejected Version": " | ".join(item["source_path"] for item in group if item is not selected),
                    "Reason": "Selected validated active package/config/doc path or normalized doc; rejected variants recorded in inventory.",
                }
            )
            no += 1
    for name in sorted({"main.py", "feature_engine.py", "ensemble_model.py", "backtester.py", "recommendation_engine.py", "hw_profile.py", "requirements.txt", "pyproject.toml", "README.md"}):
        group = [record for record in records if record["file_name"].lower() == name.lower() and not record["excluded_by_dir"]]
        hashes = {item["sha256_hash"] for item in group}
        if len(group) > 1 and len(hashes) > 1:
            selected = next((item for item in group if item["keep_or_exclude_decision"] == "KEPT"), None)
            conflict_rows.append(
                {
                    "No": no,
                    "File": name,
                    "Conflict Type": "Same name different folder/content",
                    "Selected Version": selected["source_path"] if selected else "Generated normalized target",
                    "Rejected Version": " | ".join(item["source_path"] for item in group if item is not selected),
                    "Reason": "Validated active package was preferred over raw patch/bundle/legacy variants.",
                }
            )
            no += 1
    write_csv(TARGET / "reports" / "conflict_resolution.csv", conflict_rows, ["No", "File", "Conflict Type", "Selected Version", "Rejected Version", "Reason"])

    exact_duplicate_groups = [group for group in groups.values() if len(group) > 1]
    source_counts = []
    for name, path in SOURCE_ROOTS:
        source_counts.append((name, path, sum(1 for record in records if record["source_root"] == name)))

    md = ["# Source Inventory", "", f"Generated: {NOW}", "", "| Source | Path | Files |", "|---|---|---:|"]
    for name, path, count in source_counts:
        md.append(f"| {name} | `{path}` | {count} |")
    md += [
        "",
        "## Summary",
        "",
        f"- Total scanned files: {len(records)}",
        f"- Exact duplicate hash groups: {len(exact_duplicate_groups)}",
        f"- Kept source files: {sum(1 for r in records if r['keep_or_exclude_decision'] == 'KEPT')}",
        f"- Review needed source files: {sum(1 for r in records if r['keep_or_exclude_decision'] == 'REVIEW_NEEDED')}",
        f"- Excluded source files: {sum(1 for r in records if r['keep_or_exclude_decision'] == 'EXCLUDED_FROM_UNIFIED')}",
        "",
        "Full detail: `source_inventory.csv`.",
    ]
    (TARGET / "reports" / "source_inventory.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    conflicts_md = ["# Conflict Resolution", "", f"Generated: {NOW}", "", "| No | File | Type | Selected Version | Reason |", "|---:|---|---|---|---|"]
    for row in conflict_rows[:120]:
        conflicts_md.append(f"| {row['No']} | `{row['File']}` | {row['Conflict Type']} | `{row['Selected Version']}` | {row['Reason']} |")
    if not conflict_rows:
        conflicts_md.append("| 0 | none | none | none | No conflicts found. |")
    (TARGET / "reports" / "conflict_resolution.md").write_text("\n".join(conflicts_md) + "\n", encoding="utf-8")

    kept = [r for r in records if r["keep_or_exclude_decision"] == "KEPT"]
    review_needed = [r for r in records if r["keep_or_exclude_decision"] == "REVIEW_NEEDED"]
    summary = {
        "generated_at": NOW,
        "source_file_count": len(records),
        "source_counts": {name: count for name, _, count in source_counts},
        "kept_source_count": len(kept),
        "review_needed_count": len(review_needed),
        "excluded_count": sum(1 for r in records if r["keep_or_exclude_decision"] == "EXCLUDED_FROM_UNIFIED"),
        "exact_duplicate_groups": len(exact_duplicate_groups),
        "conflict_count": len(conflict_rows),
    }
    (TARGET / "tools" / "consolidation_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    (TARGET / "reports" / "cross_review_round_1.md").write_text(
        f"""# Cross Review Round 1 - File Consistency

Generated: {NOW}

| Check | Result |
|---|---|
| Source folders scanned | {len(SOURCE_ROOTS)} folders |
| Source files inventoried | {len(records)} files |
| Exact duplicate groups | {len(exact_duplicate_groups)} groups |
| Conflict rows recorded | {len(conflict_rows)} rows |
| Review-needed files isolated | {len(review_needed)} files |
| Original folders deleted | No |

Patch applied: selected validated active package, excluded exact duplicates/cache/generated outputs, isolated uncertain evidence in `review_needed/`.
""",
        encoding="utf-8",
    )

    (TARGET / "reports" / "cross_review_round_2.md").write_text("# Cross Review Round 2 - Execution Consistency\n\nPending validation command execution.\n", encoding="utf-8")
    (TARGET / "reports" / "cross_review_round_3.md").write_text("# Cross Review Round 3 - Documentation Consistency\n\nPending documentation scan.\n", encoding="utf-8")
    write_csv(TARGET / "reports" / "validation_results.csv", [], ["Command", "ExitCode", "Result", "Notes"])
    (TARGET / "reports" / "validation_results.md").write_text("# Validation Results\n\nPending validation command execution.\n", encoding="utf-8")

    report = [
        "# Stock RTX4060 Unified Consolidation Report",
        "",
        "## 1. Summary",
        "",
        "| Item | Result |",
        "|---|---|",
        f"| Generated | {NOW} |",
        f"| Final folder | `{TARGET}` |",
        "| Original source folders deleted | No |",
        f"| Source files inventoried | {len(records)} |",
        f"| Source files kept in runtime path | {len(kept)} |",
        f"| Source files isolated in review_needed | {len(review_needed)} |",
        f"| Source files excluded from unified runtime | {summary['excluded_count']} |",
        f"| Exact duplicate groups | {len(exact_duplicate_groups)} |",
        "",
        "## 2. Source Folders Reviewed",
        "",
        "| No | Path | Files | Role | Notes |",
        "|---:|---|---:|---|---|",
    ]
    role_lookup = {
        "algo_v2": "Algorithm v2 source bundle",
        "bundle_algo_v2": "Bundle duplicate candidate",
        "recommendation_patch": "Recommendation patch candidate",
        "workspaces": "Active workspace and runtime evidence",
    }
    for index, (name, path, count) in enumerate(source_counts, start=1):
        report.append(f"| {index} | `{path}` | {count} | {role_lookup.get(name, name)} | Inventoried with sha256. |")
    report += [
        "",
        "## 3. Final Unified Folder",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Path | `{TARGET}` |",
        "| Package | `src/stock_rtx4060` |",
        "| Entry point | `main.py` |",
        "| Runner | `run.ps1` |",
        "",
        "## 4. Files Kept",
        "",
        "| No | Path | Reason |",
        "|---:|---|---|",
    ]
    for index, record in enumerate(kept, start=1):
        report.append(f"| {index} | `{Path(record['target_path']).relative_to(TARGET)}` | {record['decision_reason']} |")
    base = len(kept)
    support_files = ["main.py", "stock_investment_os.py", "run.ps1", "pyproject.toml", "requirements.txt", "requirements-dev.txt", "requirements-gpu-wsl.txt", "tests/test_core.py", "README.md", "CHANGELOG.md", "docs/SETUP.md", "docs/SYSTEM_ARCHITECTURE.md", "docs/LAYOUT.md", "docs/AGENTS.md", "docs/SPEC.md", "docs/UIUX.md", "docs/PATCH_NOTES.md"]
    for offset, path in enumerate(support_files, start=1):
        report.append(f"| {base + offset} | `{path}` | Normalized support file for unified executable layout. |")
    report += [
        "",
        "## 5. Files Excluded From Unified",
        "",
        "Full list: `reports/deleted_or_excluded_candidates.csv`.",
        "",
        "| No | Source Path | Reason | Duplicate Of | Risk |",
        "|---:|---|---|---|---|",
    ]
    for row in excluded_rows[:60]:
        report.append(f"| {row['No']} | `{row['Source Path']}` | {row['Reason']} | `{row['Duplicate Of']}` | {row['Risk']} |")
    if len(excluded_rows) > 60:
        report.append(f"| ... | ... | {len(excluded_rows) - 60} more rows in CSV | ... | ... |")
    report += [
        "",
        "## 6. Conflicts Resolved",
        "",
        "Full list: `reports/conflict_resolution.csv`.",
        "",
        "| No | File | Selected Version | Rejected Version | Reason |",
        "|---:|---|---|---|---|",
    ]
    for row in conflict_rows[:40]:
        rejected = row["Rejected Version"][:180] + ("..." if len(row["Rejected Version"]) > 180 else "")
        report.append(f"| {row['No']} | `{row['File']}` | `{row['Selected Version']}` | `{rejected}` | {row['Reason']} |")
    if len(conflict_rows) > 40:
        report.append(f"| ... | ... | ... | ... | {len(conflict_rows) - 40} more rows in CSV |")
    report += [
        "",
        "## 7. Files Merged",
        "",
        "| No | Source Files | Target File | Merge Reason |",
        "|---:|---|---|---|",
        "| 1 | `workspaces/stock_rtx4060/*`, root wrappers/docs/tests | `stock_rtx4060_unified` | Active package plus normalized wrappers/docs/tests were combined into one executable folder. |",
        "",
        "## 8. Review Needed",
        "",
        "| No | Path | Reason | Recommended Action |",
        "|---:|---|---|---|",
    ]
    for index, record in enumerate(review_needed, start=1):
        report.append(f"| {index} | `{Path(record['target_path']).relative_to(TARGET)}` | {record['decision_reason']} | Review manually before promoting to docs/runtime path. |")
    report += [
        "",
        "## 9. Validation Results",
        "",
        "Validation pending. See `reports/validation_results.md` after Phase 8.",
        "",
        "## 10. Cross Review Results",
        "",
        "| Round | Scope | Result | Patch Applied |",
        "|---:|---|---|---|",
        "| 1 | File consistency | Recorded | Selected active package and excluded duplicates/cache/generated output. |",
        "| 2 | Execution consistency | Pending | Pending validation. |",
        "| 3 | Documentation consistency | Pending | Pending scan. |",
        "",
        "## 11. Final Folder Tree",
        "",
        "```text",
        *tree_lines(TARGET),
        "```",
        "",
        "## 12. Risks",
        "",
        "| Risk | Impact | Mitigation |",
        "|---|---|---|",
        "| Default `python` may not include pytest | `pytest` command can be environment-dependent | Validate with Python 3.12 if default pytest is unavailable. |",
        "| `review_needed/` contains non-runtime evidence | Manual review still needed before promotion | Kept outside runtime/test path. |",
        "| Real broker/account settings are not defined | Not approval-ready for real-money operation | Keep report-only boundary. |",
        "",
        "## 13. Next Recommended Commands",
        "",
        "```powershell",
        f"cd {TARGET}",
        "python --version",
        "python -m compileall .",
        "python main.py --help",
        "pytest",
        "powershell -ExecutionPolicy Bypass -File .\\run.ps1",
        "```",
        "",
    ]
    (TARGET / "reports" / "consolidation_report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        backup = AUDIT / f"stock_rtx4060_unified_previous_{STAMP}"
        shutil.move(str(TARGET), str(backup))

    for subdir in [
        "reports",
        "review_needed/docs",
        "review_needed/tests",
        "review_needed/evidence",
        "src/stock_rtx4060",
        "tests",
        "docs",
        "examples",
        "workspaces",
        "archive/original_inputs",
        "tools",
    ]:
        (TARGET / subdir).mkdir(parents=True, exist_ok=True)

    records, groups = inventory_sources()

    selected: dict[str, str] = {}
    for path in (ROOT / "workspaces" / "stock_rtx4060").glob("*.py"):
        selected[str(path)] = str(TARGET / "src" / "stock_rtx4060" / path.name)

    sample = ROOT / "workspaces" / "stock_rtx4060_patched" / "examples" / "demo_workspace"
    if sample.exists():
        copy_tree_filtered(sample, TARGET / "examples" / "demo_workspace")
    sample_file = ROOT / "workspaces" / "demo_workspace" / "data" / "sample_ohlcv.csv"
    if sample_file.exists():
        selected[str(sample_file)] = str(TARGET / "examples" / "sample_ohlcv.csv")

    review_candidates = [
        ROOT / "stock_rtx4060_algo_v2" / "README.md",
        ROOT / "stock_rtx4060_algo_v2" / "ALGORITHM_PATCH_REPORT_2026.md",
        ROOT / "stock_rtx4060_algo_v2" / "VALIDATION_LOG_ALGO_V2.txt",
        ROOT / "stock_rtx4060_algo_v2" / "DOC_REVIEW_AND_INSERTION.md",
        ROOT / "stock_rtx4060_algo_v2" / "docs" / "CROSS_CHECK_2026.md",
        ROOT / "stock_rtx4060_recommendation_patch" / "RECOMMENDATION_ENGINE.md",
        ROOT / "stock_rtx4060_recommendation_patch" / "VALIDATION_LOG_RECOMMENDATION_PATCH.txt",
        ROOT / "workspaces" / "stock_rtx4060_patched" / "PATCH_REPORT_2026.md",
        ROOT / "workspaces" / "stock_rtx4060_patched" / "BENCHMARK_AND_CROSSCHECK.md",
        ROOT / "stock_rtx4060_algo_v2" / "tests" / "test_algorithm_v2.py",
    ]
    review_map: dict[str, str] = {}
    seen_review_hashes: set[str] = set()
    for path in review_candidates:
        if not path.exists():
            continue
        digest = sha256(path)
        if digest in seen_review_hashes:
            continue
        seen_review_hashes.add(digest)
        folder = "tests" if "\\tests\\" in str(path).lower() or "/tests/" in str(path).lower() else "docs"
        review_map[str(path)] = str(TARGET / "review_needed" / folder / safe_name(path))

    for path in (ROOT / "stock_rtx4060_algo_v2" / "recommendation_reports").glob("*"):
        if path.is_file():
            review_map[str(path)] = str(TARGET / "review_needed" / "evidence" / "algo_v2_recommendation_reports" / path.name)
    for path in (ROOT / "stock_rtx4060_algo_v2" / "reports").glob("*"):
        if path.is_file():
            review_map[str(path)] = str(TARGET / "review_needed" / "evidence" / "algo_v2_benchmarks" / path.name)

    for record in records:
        source = record["source_path"]
        rel_low = record["relative_path"].replace("\\", "/").lower()
        if source in selected:
            record["keep_or_exclude_decision"] = "KEPT"
            record["decision_reason"] = "Selected active validated source for unified executable package."
            record["risk"] = "LOW"
            record["required_patch"] = "Copied into src/stock_rtx4060; root entry point and tests patched for src layout."
            record["target_path"] = selected[source]
        elif source in review_map:
            record["keep_or_exclude_decision"] = "REVIEW_NEEDED"
            record["decision_reason"] = "Useful patch/evidence file, but not required for executable path. Isolated for manual review."
            record["risk"] = "AMBER"
            record["required_patch"] = "None; isolated outside runtime/test path."
            record["target_path"] = review_map[source]
        elif record["excluded_by_dir"]:
            record["keep_or_exclude_decision"] = "EXCLUDED_FROM_UNIFIED"
            record["decision_reason"] = "Cache/build/runtime artifact directory excluded."
            record["risk"] = "LOW"
        elif record["duplicate_of"]:
            record["keep_or_exclude_decision"] = "EXCLUDED_FROM_UNIFIED"
            record["decision_reason"] = "Exact duplicate by sha256; one selected copy or review copy is sufficient."
            record["risk"] = "LOW"
        elif "recommendation_reports/" in rel_low or rel_low.startswith("reports/") or "/reports/" in rel_low:
            record["keep_or_exclude_decision"] = "EXCLUDED_FROM_UNIFIED"
            record["decision_reason"] = "Generated report/output evidence not needed in runtime path."
            record["risk"] = "LOW"
        elif record["extension"] == ".py":
            record["keep_or_exclude_decision"] = "EXCLUDED_FROM_UNIFIED"
            record["decision_reason"] = "Python variant superseded by validated active package under workspaces/stock_rtx4060."
            record["risk"] = "AMBER"
            record["required_patch"] = "No copy; conflict documented."
        else:
            record["keep_or_exclude_decision"] = "EXCLUDED_FROM_UNIFIED"
            record["decision_reason"] = "Superseded by normalized unified docs/config/tests or not referenced by selected runtime path."
            record["risk"] = "LOW"

    for source, target in selected.items():
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target_path)
    for source, target in review_map.items():
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target_path)

    (TARGET / "workspaces" / "README.md").write_text("Generated runtime workspaces can be created here. Source workspaces were not copied wholesale.\n", encoding="utf-8")
    (TARGET / "archive" / "original_inputs" / "README.md").write_text("Original input archives are not copied by default. Add only source-approved archives here.\n", encoding="utf-8")
    shutil.copy2(Path(__file__), TARGET / "tools" / "consolidate_unified.py")

    write_runtime_files()
    write_docs()
    write_reports(records, groups)

    manifest = json.loads((TARGET / "tools" / "consolidation_manifest.json").read_text(encoding="utf-8"))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
