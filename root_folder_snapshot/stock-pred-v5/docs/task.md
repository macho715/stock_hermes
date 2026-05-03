# Task

| ID | Task | Owner | Status | Evidence | Blocker | Next |
|---|---|---|---|---|---|---|
| T-001 | Bootstrap docs/ structure | claude | DONE | `docs/` dirs created | NONE | — |
| T-002 | Write plan.md | claude | DONE | File written | NONE | — |
| T-003 | Write changelog.md | claude | DONE | File written | NONE | — |
| T-004 | Write system-architecture.md | claude | DONE | File written | NONE | — |
| T-005 | Write layout.md | claude | DONE | File written | NONE | — |
| T-006 | Write spec.md | claude | DONE | File written | NONE | — |
| T-007 | Write task.md | claude | DONE | File written | NONE | — |
| T-008 | Write heartbeat.md | claude | DONE | File written | NONE | — |
| T-009 | Write CONTRIB.md | claude | DONE | File written | NONE | — |
| T-010 | Write RUNBOOK.md | claude | DONE | File written | NONE | — |
| T-011 | Round 1 review: re-read StockPredV5.jsx | claude | TODO | — | NONE | Verify REC tab integration |
| T-012 | Round 1 review: re-read RecommendationPanel.jsx | claude | TODO | — | NONE | Verify FILE/API fetch |
| T-013 | Round 1 review: re-read api_server.py | claude | TODO | — | NONE | Verify CORS config |
| T-014 | Browser smoke test (REC tab) | user | TODO | — | NONE | Manual browser check |
| T-015 | Update heartbeat.md after smoke test | claude | TODO | — | T-014 pending | Set status |

## Notes
- T-014 (browser smoke test) is blocked on user confirming the REC tab renders cards in browser
- CORS is hardcoded to `localhost:5173` — if Vite port changes, `api_server.py` must be updated
- `preview_server.py` uses hardcoded `C:\nvm4w\nodejs\npm.cmd` — mitigated by `shutil.which` fallback, but may fail on non-nvm4w installs
