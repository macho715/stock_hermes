# R2-B: Renamed Document Accuracy
**Agent:** Sub-Agent R2-B — Renamed Document Accuracy
**Date:** 2026-05-03
**Working Dir:** `C:\Users\jichu\Downloads\주식`

---

## Scope
Per A3 MERGE_PLAN, no renames were executed (all decisions = KEEP).
R2-B verifies whether root-level file names are accurate descriptions of actual content.

---

## Files Checked

### 1. `stock_investment_os.py` — **MISLEADING → RENAME NEEDED**

| Aspect | Detail |
|--------|--------|
| Actual content | 6-line backward-compatible entrypoint wrapper: imports `cli` from `main` and raises `SystemExit(cli())` |
| Name suggests | Full stock investment OS module/script |
| Reality | Thin redirect script, not an OS |
| Verdict | **MISLEADING** |

**Proposed better names (pick one):**
- `main_compat.py` — signals backward compatibility entrypoint
- `cli_entry.py` — clarifies it routes to the CLI
- `stock_pred_v5_compat.py` — if the original script name was `stock_pred_v5` and this is its alias

**Recommendation:** `main_compat.py`

---

### 2. `uiux2.md` — **MISLEADING → RENAME NEEDED**

| Aspect | Detail |
|--------|--------|
| Actual content | v1.0 live-ops operational rules document — NOT a UI/UX design doc |
| Name suggests | Version 2 of a UI/UX specification |
| A3 verdict | KEEP (different content from `docs/uiux.md`) |
| Problem | "2" in `uiux2.md` is ambiguous — could mean v2 of a UI spec, but content is operational rules labeled v1.0 |
| A2 described it as | "v1.0 ops rules" — not a UI/UX doc |

**Proposed better names:**
- `ops_rules_v1.md` — operational rules, v1.0, explicit
- `live_ops_v1.md` — live operations version 1
- `track_rules_v1.md` — Track-S/Track-L rules, explicit

**Recommendation:** `ops_rules_v1.md`

---

### 3. `CONTINUE_MERGED_USAGE_GUIDE.md` — **NOT AT ROOT**

| Aspect | Detail |
|--------|--------|
| Found at | `docs/archive/CONTINUE_MERGED_USAGE_GUIDE.md` |
| Not at root | `C:\Users\jichu\Downloads\주식\` has no such file |
| Content | AI quality gate integration guide for Continue plugin |
| Name accuracy | Name is accurate to content |
| Verdict | **OK (archived location)** — no rename needed |

---

### 4. `deep-research-report.md` — **NOT AT ROOT**

| Aspect | Detail |
|--------|--------|
| Found at | `docs/archive/deep-research-report.md` |
| Not at root | No such file at root |
| Content | Technical upgrade document (upgrade path from research to live-ops) |
| Name accuracy | "deep research report" is an accurate label |
| Verdict | **OK (archived location)** — no rename needed |

---

## Summary

| File | Root Location | Status |
|------|--------------|--------|
| `stock_investment_os.py` | YES | **RENAME_PROPOSED** — content is a CLI wrapper, not an OS |
| `uiux2.md` | YES | **RENAME_PROPOSED** — content is v1.0 ops rules, not a UI/UX v2 spec |
| `CONTINUE_MERGED_USAGE_GUIDE.md` | NO (in archive) | PASS — name accurate to content |
| `deep-research-report.md` | NO (in archive) | PASS — name accurate to content |

**Root-level misleading names: 2 of 4**
**Files requiring rename at root: 2**

---

## Recommended Actions

```text
1. stock_investment_os.py → main_compat.py
2. uiux2.md              → ops_rules_v1.md
```

Both renames are non-destructive. A3 MERGE_PLAN archiving decisions for JSX files remain pending user confirmation (not executed by A3).