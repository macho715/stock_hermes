---
name: Report Contract
description: Validate recommendation report fields, disclaimers, and evidence structure.
---

Review this change for report contract violations.

Fail this check if recommendation Markdown or JSON reports omit required fields:

- generated timestamp
- universe
- track
- period
- top-N
- boundary disclaimer
- ranking table
- validation details
- ticker
- verdict
- score
- probability
- expected value
- entry
- stop
- TP2
- Risk/Reward
- risk budget
- max position
- suggested quantity
- confirmations
- evidence
- data source
- CV gap
- model accuracy/AUC where available
- OOF coverage
- backtest return/Sharpe/MDD where available
- risk-plan fields

Fail this check if:

- Red/ZERO outputs do not include the failed check and a human-readable reason.
- Report language says "buy now", "must buy", "guaranteed", or equivalent execution guidance.
- Markdown and JSON outputs diverge materially for the same run.

Pass only if:

- Reports remain audit-ready and manual-review-only.
- Numbers are consistently rounded for display where applicable.

When failing, propose the missing field additions in the report writer.
