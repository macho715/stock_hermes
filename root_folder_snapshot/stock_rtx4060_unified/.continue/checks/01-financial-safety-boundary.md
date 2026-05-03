---
name: Financial Safety Boundary
description: Enforce report-only stock screening boundary and block trading execution paths.
---

Review this change for financial safety boundary violations.

Fail this check if any change does one or more of the following:

- Adds broker API order execution, auto buy/sell, order router, trade placement, margin enabling, short selling, leveraged ETF execution, or options/0DTE execution.
- Converts a ranked screening candidate into a direct buy/sell instruction.
- Removes or weakens `screening_output_only=True` from recommendation result objects or reports.
- Claims or implies guaranteed Track-S +10.00%, Track-L +20.00%, Sharpe, win rate, or future returns.
- Uses suggested quantity, Kelly sizing, or risk budget as an executable order quantity.
- Adds account-affecting write actions without an explicit human approval gate.
- Converts `ops-v1` approval templates into executable orders or account-writing actions.

Pass only if:

- The system remains report-only and manual-review-only.
- Recommendation outputs are clearly labeled as screening candidates, not investment advice or broker instructions.
- Ops v1 artifacts remain review files: recommendation report, daily brief, approval journal template, ZERO log, and summary JSON.
- All external writes, credential handling, deployment, deletion, and account-affecting actions require manual approval.

When failing, identify the file and line area, explain the violated boundary, and propose a safe report-only alternative.
