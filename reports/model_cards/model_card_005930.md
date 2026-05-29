# Model Card - 005930

Generated UTC: 2026-05-29T05:02:46+00:00

Report-only / Manual review / No broker order execution.

## Gate Decision

- status: PAPER_PASS
- live_review_candidate: False
- paper_pass: True

## Blocking Reasons

- FORWARD_PAPER_DAYS 0 < 30
- FORWARD_PAPER_ALPHA None < 0.0
- RULE_VIOLATIONS None > 0

## Evidence

- CPCV pass rate: 0.8000
- PBO: 0.0800
- Deflated Sharpe: 0.9430

## Safety Boundary

- broker_order_execution: false
- manual_approval_required: true
- screening_output_only: true
