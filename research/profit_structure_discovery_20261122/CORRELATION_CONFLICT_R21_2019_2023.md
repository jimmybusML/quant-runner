# R21 | Exact duplicate signals and vote correlation sensitivity

2019-2023 Crown AH, R7-R15 494 historically selected definitions. Research-only.

Exact signal footprints: 453 among 494 candidate definitions, 41 exact redundant definitions.

## One order per fixture, experimental comparison

| Quote choice | Vote weighting | Opposite-side handling | Orders | Net U | ROI | MDD U |
|---|---|---|---:|---:|---:|---:|
| earliest | raw | skip_conflict | 11678 | 1049.77 | 8.9893% | 30.25 |
| earliest | raw | net | 13137 | 1154.46 | 8.7879% | 32.955 |
| earliest | identical_cluster | skip_conflict | 11678 | 1049.77 | 8.9893% | 30.25 |
| earliest | identical_cluster | net | 13082 | 1158.66 | 8.8569% | 32.955 |
| earliest | batch_cap | skip_conflict | 11678 | 1049.77 | 8.9893% | 30.25 |
| earliest | batch_cap | net | 12823 | 1136.66 | 8.8642% | 33.64 |
| latest | raw | skip_conflict | 11962 | 835.565 | 6.9852% | 30.16 |
| latest | raw | net | 13410 | 888.38 | 6.6248% | 37.37 |
| latest | identical_cluster | skip_conflict | 11962 | 835.565 | 6.9852% | 30.16 |
| latest | identical_cluster | net | 13379 | 882.745 | 6.598% | 36.87 |
| latest | batch_cap | skip_conflict | 11962 | 835.565 | 6.9852% | 30.16 |
| latest | batch_cap | net | 12998 | 878.79 | 6.761% | 35.18 |

## Scope and limitations

- Exact duplicate means identical (fixture, quote horizon, physical side) footprint across the five years. Partial correlation remains unmeasured.
- Raw votes count all definitions; identical_cluster gives one vote to each exact footprint; batch_cap gives at most one vote per research batch and physical side.
- Skip_conflict abstains when both physical sides signal; net chooses larger vote total and abstains on ties. Same-side signals merge into one 1U order.
- Earliest means maximum T among signal-bearing quote horizons; latest means minimum T. This is a comparison, not a user-approved time rule.
- Candidate definitions were selected using outcomes from all 2019-2023, so all results have selection leakage and are not honest out-of-sample tests.
- No 2024-2026 outcomes used; no changes to M8, Telegram, or production.
