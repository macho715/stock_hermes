# Design Upgrade Report

## 1. Baseline diagnosis
- Target surface: STOCK.PRED v5.0 operational investment dashboard at `http://127.0.0.1:5178/`.
- Editable source: `root_folder_snapshot/stock-pred-v5/src/StockPredV5.jsx`.
- Main issues: dense first viewport, operational source state split across panels, and report-only safety posture not visible before score-heavy sections.

## 2. Reference log
| No. | URL | Why relevant | Pattern to transfer | Pattern to avoid |
|---|---|---|---|---|
| 1 | https://www.designrush.com/best-designs/websites | Current design archive with strong first-viewport hierarchy examples | Compact top-level grouping and clear section rhythm | Marketing hero treatment |
| 2 | https://www.webdesignawards.io/winners | Award gallery showing concise scan-first card systems | Sharper active state contrast and restrained elevation | Oversized decorative cards |
| 3 | https://www.awwwards.com/websites/nominees | Live nominee reference set for contemporary visual hierarchy | Stronger typography tiering and band separation | Low-density editorial layout |

## 3. Transferable design elements
| No. | Element | Reason | Expected benefit | Patch target | Risk |
|---|---|---|---|---|---|
| 1 | Compact evidence/status strip | Dashboard users need source state before score interpretation | Faster risk scan | Header-to-body transition | Low |
| 2 | Stronger active-state contrast | Current state labels competed with dense data | Clearer visual priority | First viewport status cards | Low |
| 3 | Operational warnings above score panels | Safety gates must not be hidden inside REC details | Lower chance of live-trading misread | Execution status card | Low |

## 4. Patch map
| File / Section | Current problem | Proposed change | Reference anchor | Impact | Risk |
|---|---|---|---|---|---|
| top-of-page structure | Source and execution state were not grouped before panels | Add `OperationalEvidenceStrip` below header | https://www.designrush.com/best-designs/websites | High | Low |
| content grouping | Dense dashboard needed one more readable band | Use 5 compact status cells with colored evidence borders | https://www.webdesignawards.io/winners | Medium | Low |
| execution safety | Report-only posture was visible later than score content | Surface `REPORT ONLY` and broker-order prohibition in first viewport | https://www.awwwards.com/websites/nominees | High | Low |

## 5. Applied change summary
- Changed files: `root_folder_snapshot/stock-pred-v5/src/StockPredV5.jsx`.
- Preview artifacts: `before.png`, `after.png`, `visual-benchmark.json`, `design-scorecard.json`.
- Notable trade-offs: the dashboard is 35px taller because the safety/source strip is now always visible.

## 6. Visible design delta
| Benchmark element | Patch target | Visible evidence |
|---|---|---|
| Compact evidence/status strips above dense sections | Top-of-page structure | Active symbol, data route, model evidence, REC mode, and execution status are grouped below the header |
| Sharper active-state contrast and restrained elevation | Status cards | Colored top borders and value emphasis create a clearer scanning lane |
| Operational warnings prominent, secondary scores visible for audit | Execution card | `REPORT ONLY` and no broker-order language appear before detailed right-panel scores |

## 7. Validation summary
- Scorecard path: `artifacts/design-upgrade/20260530_020950/design-scorecard.json`.
- Average score: 4.19.
- Weakest metric: 4.00.
- Blocking issues: none.
- Verdict: PASS.

## 8. Remaining risks
- Automated `analyze_visual_benchmark.py` could not run because `cv2` is not installed in this environment; visual analysis was produced from Playwright screenshots and benchmark evidence instead.
