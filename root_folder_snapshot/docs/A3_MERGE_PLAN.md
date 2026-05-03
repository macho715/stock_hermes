# A3 MERGE PLAN
**Agent:** Duplicate Detector & Merge Planner
**Date:** 2026-05-03
**Working Dir:** `C:\Users\jichu\Downloads\주식`

---

## Analysis Summary

| File A | File B | Relationship | Decision |
|--------|--------|-------------|----------|
| `CONTINUE_MERGED_USAGE_GUIDE.md` | `docs/SETUP.md` | Different topics — NOT duplicates | KEEP both, rename descriptively |
| `uiux2.md` | `docs/uiux.md` | Different content, different dates — NOT duplicates | KEEP both separately |
| `stock_pred_v5.jsx` | `stock-pred-v5/src/StockPredV5.jsx` | Orphaned backup vs active source (v5.0 with REC tab) | KEEP in archive |
| `stock_prediction_dashboard_1.jsx` | `stock-pred-v5/src/StockPredV5.jsx` | Older v4.5 (9 symbols, no KRX, no REC tab) vs active v5.0 | KEEP in archive |

**Total files assessed:** 7 pairs/groups
**Duplicates found:** 0 (different content in all cases)
**Archivals:** 2 orphaned JSX backups
**Renames:** 0 (all current names are appropriate)

---

## Group 1: Usage Guide Duo
**Files:** `CONTINUE_MERGED_USAGE_GUIDE.md`, `docs/SETUP.md`

- `CONTINUE_MERGED_USAGE_GUIDE.md` — Continue AI quality gate integration guide (614 lines). Covers PR-level financial-safety/backtest-integrity/recommendation-contract checks, `.continue/checks/` file set, AGENTS.md/CLAUDE.md blocks, and branch protection rules.
- `docs/SETUP.md` — Windows laptop setup guide (103 lines). Covers CPU-safe install, GPU validation commands, TensorFlow note, and common CLI commands.

**Action:** KEEP
**Output:** Same filenames — no rename needed.
**Content rationale:** Completely different topics; no merge or rename needed. `CONTINUE_MERGED_USAGE_GUIDE.md` belongs at repo root per Continue scanning requirements. `docs/SETUP.md` belongs in `docs/` alongside other setup/architecture docs.

---

## Group 2: UI/UX Doc Duo
**Files:** `uiux2.md`, `docs/uiux.md`

- `uiux2.md` (root, ~306 lines) — v1.0 live-ops version. Starts with "판정: 조건부 예 — 실제 투자 운영 버전으로 올리되". Covers v1.0 operating boundary, Track-S/Track-L rules, 5 report types, v1.0 algorithm, approval gate, ZERO log.
- `docs/uiux.md` (docs/, 424 lines) — Full investment OS structure. Starts with "판정: AMBER — 1개월 +10.00% 단타 목표는 공격적이고...". Covers Track-S tactical scoring (100pt), Track-L long-term allocation (40/20/15/10/10/5 buckets), integrated data/AI structure, Python module design.

**Action:** KEEP
**Output:** `uiux2.md` at root, `docs/uiux.md` at `docs/`.
**Content rationale:** Different dates (uiux2.md is v1.0 ops version), different focus (ops rules vs investment OS architecture). Both are valid. Do NOT merge — they cover different phases of the same project.

---

## Group 3: Orphaned JSX Backups (READ-ONLY Archive)
**Files:** `stock_pred_v5.jsx`, `stock_prediction_dashboard_1.jsx`

**stock_prediction_dashboard_1.jsx:**
- Version: v4.5, US-only (9 symbols: AAPL/MSFT/NVDA/TSLA/AMZN/GOOGL/META/SPY/QQQ)
- No KRX market support, no REC/BACKEND tab, no `import RecommendationPanel`
- Backend snapshot import not present
- 1863 lines

**stock_pred_v5.jsx:**
- Version: v4.5-derived, US+KRX dual market
- Has KRX symbols, dual-market toggle
- No `import RecommendationPanel`
- Has `backendSnapshot` state and `snapshotInputRef` for BACKEND tab
- 1863 lines

**Active source:** `stock-pred-v5/src/StockPredV5.jsx`
- Version: v5.0
- US + KRX, LSTM+LR+XGB+RNN ensemble (30/25/25/20 weights)
- REC tab (RecommendationPanel), BACKEND tab via snapshot import
- 1722 lines

**Action:** KEEP in archive
**Output:** Move both to `archive/` folder — do NOT delete without user confirmation.
**Content rationale:** These are historical versions. They may contain patterns/approaches not yet ported to v5.0. Archive preserves them without polluting active source. Deletion requires explicit user confirmation per safety rules.

---

## Execution Log

```
[EXECUTED] Group 1: KEEP — CONTINUE_MERGED_USAGE_GUIDE.md (root), docs/SETUP.md (docs/)
[EXECUTED] Group 2: KEEP — uiux2.md (root), docs/uiux.md (docs/)
[PENDING]  Group 3: ARCHIVE — stock_pred_v5.jsx → archive/stock_pred_v5_v4.5.jsx
[PENDING]  Group 3: ARCHIVE — stock_prediction_dashboard_1.jsx → archive/stock_prediction_dashboard_1_v4.5.jsx
```

**Note:** Archive moves require user confirmation before execution (safety rule: no deletion without approval).

---

## Key Decisions Explained

1. **No merge of usage guides** — `CONTINUE_MERGED_USAGE_GUIDE.md` is about AI quality gates, `docs/SETUP.md` is about Python runtime setup. Merging would make both harder to find.

2. **No merge of uiux docs** — `uiux2.md` is an operational v1.0 rules doc, `docs/uiux.md` is a full investment OS architecture doc. They serve different readers (ops team vs design/planning).

3. **Archive orphaned JSX backups** — Both `stock_pred_v5.jsx` and `stock_prediction_dashboard_1.jsx` predate the active v5.0 source in `stock-pred-v5/src/`. They should move to `archive/` rather than be deleted, pending user confirmation.
