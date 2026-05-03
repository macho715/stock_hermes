# ZERO Log

Generated: 2026-05-02T18:18:56+00:00

These rules block account-affecting actions in Ops v1.

| code              | reason                                                                         | decision   |
|:------------------|:-------------------------------------------------------------------------------|:-----------|
| AUTO_BUY          | manual approval is required before any account action                          | ZERO       |
| BROKER_ORDER      | broker order execution is outside this repository boundary                     | ZERO       |
| MARGIN_OPTIONS    | margin, options, 0DTE, and leveraged account actions require separate approval | ZERO       |
| NO_STOP           | candidate without a defined stop cannot pass the risk plan                     | ZERO       |
| INSIDE_INFO       | non-public information is disallowed                                           | ZERO       |
| GUARANTEED_RETURN | guaranteed-return language is prohibited                                       | ZERO       |

## Current Run

- Candidate rows: 2
- Error rows: 0
- Broker order execution: false
- Automation boundary: screening/report only
