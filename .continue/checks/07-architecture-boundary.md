---
name: Architecture Boundary
description: Preserve the current local CLI architecture unless an architecture change is explicitly scoped.
---

Review this change for architecture boundary drift.

Fail this check if any change does one or more of the following without explicit task approval:

- Adds FastAPI, Flask, Dash, Gradio, Streamlit, HTTP server, port binding, web dashboard, or browser app.
- Adds broker integration, order router, trade execution, or account-affecting module.
- Adds MCP server, agent runtime server, background worker, scheduler, or external automation daemon.
- Moves active code outside `src/stock_rtx4060/` without updating wrappers, layout docs, tests, and import paths.
- Treats generated evidence folders as source code.
- Edits archive, `review_needed/`, or duplicate evidence folders as primary source without explicit instruction.

Pass only if:

- The system remains a local Python CLI writing Markdown/JSON/CSV reports.
- Active code changes are placed under `src/stock_rtx4060/` unless wrappers, docs, tests, or config need updates.
- Generated output remains under `reports/` or a documented evidence folder.

When failing, recommend either reverting the architecture drift or creating a separate scoped design.
