<!-- ⚠️ ROOT-PINNED DOCUMENT — DO NOT MOVE
This file must remain in: C:\Users\jichu\Downloads\주식\
Managed by: Document Architecture Policy v1.0
Rebuilt from scratch: 2026-05-03 by Sub-Agent V3-C
Scope: root (excl. _consolidation_audit/), docs/, docs/archive/, stock-pred-v5/docs/, stock_rtx4060_unified/docs/
-->

# DOCUMENT_INDEX.md

> Rebuilt from scratch: 2026-05-03 by Sub-Agent V3-C
> Scope: root (excl. `_consolidation_audit/`), `docs/`, `docs/archive/`, `stock-pred-v5/docs/`, `stock_rtx4060_unified/docs/`

---

## ROOT-PINNED (root-level project config and policy files)

| File | Category | Purpose |
|------|----------|---------|
| `AGENTS.md` | Project Root | Package purpose, source-of-truth files, recommendation contract, risk gate rules, GPU/CI conventions |
| `CLAUDE.md` | Project Root | Claude Code scope, validation gates, response contract (Korean/English hybrid) |
| `Spec.md` | Spec | Master specification — algorithm version, data sources, CLI args, screening outputs, audit trail |
| `plan.md` | Plan | Active implementation plan |
| `plan_rev.md` | Plan | Revised/updated plan (consolidation-era) |
| `SETUP.md` | Setup | Python environment / pip setup instructions |
| `SETUP_2026.md` | Setup | 2026-era updated setup guide |
| `PATCH_NOTES.md` | Patch | Algorithm and package patch notes, version history |
| `BENCHMARK_2026_REVIEW.md` | Review | Benchmark results review and analysis |
| `SYSTEM_ARCHITECTURE.md` | Architecture | System component diagram, data flow |
| `LAYOUT.md` | Architecture | Directory layout and file inventory |
| `GITHUB_CROSS_CHECK.md` | Review | Cross-check against GitHub state / version alignment |
| `uiux.md` | UX | UI/UX design notes, report format guidance |
| `MOVE_PLAN.md` | Ops | File reorganisation / move plan |
| `MOVE_LOG.md` | Ops | File move operation log |
| `RECON_MANIFEST.md` | Ops | Reconstruction manifest |
| `ops_rules_v1.md` | Ops | Operational rules v1 |
| `R1_A_ROOT_PIN.md` | Review | Root-pin review — Round 1A |
| `R1_B_DOCS_COMPLETE.md` | Review | Docs completeness review — Round 1B |
| `R1_C_INPLACE.md` | Review | In-place consolidation review — Round 1C |
| `R1_D_INDEX_ACCURACY.md` | Review | Index accuracy review — Round 1D |
| `A2_CLASSIFICATION.md` | Review | File classification review — Round A2 |
| `A3_MERGE_PLAN.md` | Review | Merge plan review — Round A3 |
| `R2_A_MERGE_QUALITY.md` | Review | Merge quality review — Round R2-A |
| `R2_B_NAMING.md` | Review | Naming convention review — R2-B |
| `R2_C_ROOT_CONTENT.md` | Review | Root content review — R2-C |
| `R2_D_DELETION_SAFETY.md` | Review | Deletion safety review — R2-D |
| `DISCARDED_LOG.md` | Ops | Discarded/deleted files log |

**Root-pinned count: 28 files**

---

## `docs/` — Core Documentation

| File | Category | Purpose |
|------|----------|---------|
| `AGENTS.md` | Project Config | Agent orchestration, subagent routing, skill registry |
| `LAYOUT.md` | Architecture | Directory layout documentation |
| `PATCH_NOTES.md` | Patch | Algorithm patch notes (v1/v2 history) |
| `plan.md` | Plan | Active implementation plan |
| `plan_rev.md` | Plan | Revised plan (consolidation update) |
| `SETUP.md` | Setup | Setup instructions |
| `SETUP_2026.md` | Setup | 2026-era updated setup guide |
| `Spec.md` | Spec | Master specification document |
| `SYSTEM_ARCHITECTURE.md` | Architecture | Component architecture, data flows |
| `uiux.md` | UX | UI/UX design notes |

**docs/ count: 10 files**

---

## `docs/archive/` — Archived / Deprecated Documentation

| File | Category | Purpose |
|------|----------|---------|
| `CONTINUE_MERGED_USAGE_GUIDE.md` | Archive | Deprecated — Continue merged workspace usage guide |
| `deep-research-report.md` | Archive | Deprecated — Deep research report output |

**docs/archive/ count: 2 files**

---

## Sub-package: `stock-pred-v5/docs/`

| File | Category | Purpose |
|------|----------|---------|
| `ARCHITECTURE.md` | Architecture | Package system architecture |
| `LAYOUT.md` | Architecture | Package directory layout |
| `spec.md` | Spec | Package specification |
| `plan.md` | Plan | Implementation plan |
| `task.md` | Plan | Task definitions |
| `changelog.md` | Patch | Version changelog |
| `RUNBOOK.md` | Ops | Operational runbook |
| `CONTRIB.md` | Meta | Contribution guidelines |
| `system-architecture.md` | Architecture | Alternate architecture doc |
| `ops/heartbeat.md` | Ops | Heartbeat / liveness monitoring |
| `_review/V1A_README_ARCHITECTURE.md` | Review | Round 1A review: README + architecture |
| `_review/V1B_ARCHITECTURE_LAYOUT.md` | Review | Round 1B review: architecture + layout |
| `_review/V1C_CHANGELOG_VERIFIED.md` | Review | Round 1C review: changelog verified |
| `_review/V1D_MERMAID.md` | Review | Round 1D review: Mermaid diagrams |
| `_review/V2A_COMPLETENESS.md` | Review | Round 2A review: completeness check |
| `_review/V2B_ACCURACY.md` | Review | Round 2B review: accuracy check |
| `_review/V2C_DELETION.md` | Review | Round 2C review: deletion audit |
| `_review/review-round-1.md` | Review | Review round 1 |
| `_review/review-round-2.md` | Review | Review round 2 |
| `_review/FINAL_MERMAID_RECHECK.md` | Review | Final review: Mermaid recheck |
| `_review/FINAL_VALIDATION_REPORT.md` | Review | Final validation report |

**stock-pred-v5/docs/ count: 21 files**

---

## Sub-package: `stock_rtx4060_unified/docs/`

| File | Category | Purpose |
|------|----------|---------|
| `AGENTS.md` | Project Config | Agent orchestration + skill routing |
| `LAYOUT.md` | Architecture | Directory layout |
| `PATCH_NOTES.md` | Patch | Unified package patch notes |
| `plan.md` | Plan | Active implementation plan |
| `SPEC.md` | Spec | Master specification |
| `SETUP.md` | Setup | Setup instructions |
| `SYSTEM_ARCHITECTURE.md` | Architecture | Component architecture |
| `UIUX.md` | UX | UI/UX design notes |
| `CONTINUE_MERGED_USAGE_GUIDE.md` | Ops | Continue merged workspace usage guide |
| `REPORTS_POLICY.md` | Policy | Report generation and output policy |
| `plan_dashboard_bridge_2026-05-03.md` | Plan | Dashboard bridge implementation plan (2026-05-03) |
| `plan_dashboard_bridge_risk_mitigation_2026-05-03.md` | Plan | Risk mitigation plan for dashboard bridge (2026-05-03) |
| `plan_real_data_ops_upgrade_2026-05-03.md` | Plan | Real-data ops upgrade plan (2026-05-03) |
| `SPEC_DASHBOARD_BRIDGE_2026-05-03.md` | Spec | Dashboard bridge spec (2026-05-03) |
| `SPEC_REAL_DATA_OPS_UPGRADE_2026-05-03.md` | Spec | Real-data ops upgrade spec (2026-05-03) |
| `analysis_real_data_ops_upgrade_2026-05-03.md` | Review | Analysis of real-data ops upgrade (2026-05-03) |
| `superpowers/plans/2026-05-02-continue-quality-gates.md` | Plan | Continue quality gates plan (2026-05-02) |

**stock_rtx4060_unified/docs/ count: 17 files**

---

## Summary

| Section | Count |
|---------|-------|
| Root-pinned | 28 |
| `docs/` | 10 |
| `docs/archive/` | 2 |
| `stock-pred-v5/docs/` | 21 |
| `stock_rtx4060_unified/docs/` | 17 |
| **Total indexed** | **78** |

---

*Generated: 2026-05-03 by Sub-Agent V3-C (DOCUMENT_INDEX rebuild from scratch)*