=== RECON MANIFEST ===
Root path: C:\Users\jichu\Downloads\주식

Total docs found: ~120+ (recursion partial — permission errors on pytest-cache dirs)

Docs already in /docs: 13 files
  AGENTS.md, BENCHMARK_2026_REVIEW.md, GITHUB_CROSS_CHECK.md, LAYOUT.md,
  MOVE_PLAN.md, PATCH_NOTES.md, plan.md, plan_rev.md, SETUP.md, SETUP_2026.md,
  Spec.md, SYSTEM_ARCHITECTURE.md, uiux.md

Root-pinned docs PRESENT: ✅ README.md, ✅ AGENTS.md, ✅ CHANGELOG.md, ✅ CLAUDE.md
Root-pinned docs PRESENT: ✅ README.md, ✅ AGENTS.md, ✅ CHANGELOG.md, ✅ CLAUDE.md, ✅ ARCHITECTURE.md (A1), ✅ LAYOUT.md (A1)
Root-pinned docs MISSING: ⚠️ DOCUMENT_INDEX.md (A5 to create)

Execution notes:
  - ARCHITECTURE.md created by A1
  - LAYOUT.md created by A1
  - DOCUMENT_INDEX.md created by A5
  - 7 files moved to docs/archive/
  - 2 files renamed: stock_investment_os.py → main_compat.py, uiux2.md → ops_rules_v1.md

Potential duplicates:
  - root/CONTINUE_MERGED_USAGE_GUIDE.md ↔ docs/SETUP.md (similar usage guide content)
  - root/deep-research-report.md ↔ reports/ (likely AI agent output)
  - stock-pred-v5/docs/ ← SEPARATE package docs (KEEP in-place)
  - stock_rtx4060_unified/docs/ ← SEPARATE package docs (KEEP in-place)
  - root/stock_pred_v5.jsx ↔ stock-pred-v5/src/StockPredV5.jsx (orphaned backup)
  - root/stock_prediction_dashboard_1.jsx ↔ stock-pred-v5/src/StockPredV5.jsx (orphaned backup)

Scope clarification:
  - TARGET: C:\Users\jichu\Downloads\주식\docs (root-level consolidated docs)
  - stock-pred-v5/docs/ and stock_rtx4060_unified/docs/ are PACKAGE-INTERNAL → KEEP in-place
  - Orphaned root-level files (stock_investment_os.py, stock_pred_v5.jsx, etc.) → ARCHIVE or delete
  - _consolidation_audit/ and continue-main/ → likely irrelevant, excluded from scope

Critical decision needed BEFORE Phase 1: each sub-package (stock-pred-v5, stock_rtx4060_unified) keeps its own docs/ folder. Only root-level orphaned docs should move to root docs/.
======================
