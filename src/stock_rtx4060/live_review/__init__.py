"""live_review package — forward paper trading evidence tracking.

This package handles automatic daily recording of paper trading results
for FORWARD_PAPER_RUNNING → FORWARD_COMPLETE_USER_REVIEW_REQUIRED flow.

Safety invariants (never break):
  auto_promote = False
  new_capital_allowed = False
  broker_order_execution = False
  manual_approval_required = True
"""
