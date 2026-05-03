---
name: Report Contract
description: Validate recommendation report fields, disclaimers, and evidence structure.
---

Review this change for report contract violations.

Fail this check if recommendation Markdown, JSON, or Ops v1 CSV reports omit required fields:

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
- manual approval status where Ops v1 is involved
- broker order execution boundary where Ops v1 is involved
- `audit_log.jsonl` path for recommendation and Ops v1 provider attempts

Fail this check if:

- Red/ZERO outputs do not include the failed check and a human-readable reason.
- Report language says "buy now", "must buy", "guaranteed", or equivalent execution guidance.
- Markdown and JSON outputs diverge materially for the same run.
- `approval_journal_template.csv` omits `REVIEW_PENDING`, `manual_approval_required`, `broker_order_execution`, or `screening_output_only`.
- `zero_log.md` or `zero_log.csv` omits AUTO_BUY, BROKER_ORDER, or MARGIN_OPTIONS blocking rules.
- Audit JSONL omits provider requested, provider used, status, ticker, period, command, timestamp, or failure reason when a provider fails.

Pass only if:

- Reports remain audit-ready and manual-review-only.
- Numbers are consistently rounded for display where applicable.
- Ops v1 outputs are sufficient for a human to approve, reject, or journal candidates without implying automatic execution.
- Provider provenance can be traced from generated JSON/summary paths to the audit JSONL file.

When failing, propose the missing field additions in the report writer.
