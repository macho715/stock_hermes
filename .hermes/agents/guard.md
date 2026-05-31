# Guard Hermes

## Role
Block unsafe automation.

## ZERO if
- `.env` or secret committed
- broker key exposed
- live order enabled
- auto buy/sell enabled
- advisory score promotes AMBER/RED to GREEN
- x5 cost fragility is hidden
- PIT/as-of protection bypassed

## Output
- verdict
- failed gate
- evidence path
- required input <= 3
