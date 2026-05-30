# C Fast Paper-Trading Restriction Plan

## Overview

C fast remains a paper-trading dry-run candidate because base and x2 validation pass and optimizer failures are currently zero. It must not be promoted to live trading while x5 cost stress remains below the warning threshold.

## Goals

- Keep C fast eligible for paper-trading dry-run observation.
- Block live trading and promotion while x5 cost fragility remains.
- Make the promotion block explicit in validation summary and report outputs.

## Scope

### In Scope

- C fast validation result interpretation.
- `cost_fragile` warning retention.
- `PAPER_TRADING_DRY_RUN_ONLY` execution mode.
- `BLOCKED_BY_X5_COST_FRAGILITY` promotion status.
- Dry-run validation report and summary fields.

### Out of Scope

- Broker connection.
- Order execution.
- Live trading approval.
- A or B retraining.
- C heavy rerun.

## Constraints

- No broker execution.
- No live trading.
- Dry-run outputs only.
- Base and x2 pass do not imply x5 pass.
- x5 is a promotion blocker, not a paper-trading candidate rejection rule.

## Phases

1. Preserve C fast validation verdict when base and x2 pass.
2. Add explicit dry-run execution controls.
3. Block promotion when x5 produces `cost_fragile`.
4. Review paper-trading results before any future promotion decision.

## Tasks

- Keep `C_fast = CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE` when base and x2 policy thresholds pass.
- Set `execution_mode = PAPER_TRADING_DRY_RUN_ONLY` for passing C fast validation.
- Set `promotion_status = BLOCKED_BY_X5_COST_FRAGILITY` when `cost_fragile` is present.
- Keep `broker_execution_allowed = false`.
- Keep `live_trading_allowed = false`.
- Include the execution controls in `validation_summary.json`.
- Include the execution controls in `validation_report.md`.

## Risks

- x5 cost stress may better approximate adverse execution conditions than base or x2.
- A good paper-trading result could be overestimated if real costs are closer to x5.
- Removing the promotion block too early could allow live trading before cost robustness is established.

## Review Criteria

- Base Sharpe is at least 1.00.
- x2 Sharpe is at least 1.00.
- Base and x2 max drawdown are at least -10.00%.
- Base and x2 optimizer success rates are at least 90.00%.
- x5 Sharpe below 1.00 keeps `cost_fragile`.
- `cost_fragile` sets `promotion_status = BLOCKED_BY_X5_COST_FRAGILITY`.
- Broker and live trading flags remain false.

## Deliverables

- Paper-trading restriction plan.
- Validation summary execution controls.
- Validation report execution controls.
- Tests for cost-fragile promotion blocking.
