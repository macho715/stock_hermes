# LIVE_REVIEW Forward Evidence Policy

This repository treats `reports/live_review/005930/` forward-paper outputs as mutable runtime artifacts.

## Scope

The policy applies to generated 005930 live-review evidence such as:

- `forward_paper_summary_005930.json`
- `paper_pass_snapshot.json`
- `provenance.json`
- `paper_trading_log_005930.csv`
- recorder logs
- generated review packs

## Git Policy

Do not mix these files into behavior or source-code commits.

The default path is to keep mutable evidence ignored by Git while the 30-trading-day forward paper recorder is running.

When a final review package is needed, store it outside the source tree:

```text
artifacts/live_review/005930/<review-date>_review_pack/
```

If evidence must be reviewed in Git, use a separate evidence branch:

```text
evidence/005930-forward-<date>
```

## Safety Boundary

Until forward paper trading reaches the required gate:

```text
readiness_status=FORWARD_PAPER_RUNNING
live_review_candidate=false
new_capital_allowed=false
broker_order_execution=false
manual_approval_required=true
```

`LIVE_REVIEW_CANDIDATE` still does not allow broker execution or new capital.
