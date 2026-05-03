# Recommendation Report

This report is `screening_output_only`. It is not a broker order, auto-trading instruction, or personalized investment advice.

## Summary

- Track: `BOTH`
- Universe: `SYNTH-A SYNTH-B`
- Top N: `2`
- Synthetic data: `True`

## Candidates

| Rank | Ticker | Track | Gate | Verdict | Score | Prob | Entry | Stop | TP2 | R/R | Backend |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | SYNTH-A SYNTH-B | L | GREEN | Eligible/DCA | 89.89 | 0.437 | 179.86 | 158.27 | 215.83 | 0.00 | numpy-logistic |
| 2 | SYNTH-A SYNTH-B | S | AMBER | Watch Only | 75.12 | 0.343 | 179.86 | 172.66 | 197.84 | 2.50 | numpy-logistic |
