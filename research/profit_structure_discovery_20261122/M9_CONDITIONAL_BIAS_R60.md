# R60 | Do league-specific goal-margin calibration errors persist year to year?

## Scope

Read-only analysis of previously produced R58 held-out, year-frozen M9-class predictions. Compare 2024 residual to 2025 residual, and 2025 residual to 2026 residual, for the same league and each of seven goal-difference categories. **78 unique adjacent-year league pairs**, **16,925 distinct target-year matches**, **546 league-year-category comparisons** (7 bins per match, not 118,475 distinct fixtures).

Residual definition: observed frequency minus predicted frequency for a goal-difference bin. Direct carry-forward candidate: next-year predicted residual = previous-year residual. This is an explanatory group-level persistence test, not per-match calibration or a Crown AH trading strategy.

## Aggregate

| Metric | Result |
|---|---:|
| Unique league-year adjacent pairs | 78 |
| Target-year distinct fixtures | 16,925 |
| Bin-level comparisons | 546 |
| Pearson correlation across pooled bin residuals | +0.0262 |
| Same-sign share weighted by target-year fixtures | 52.16% |
| Prior-error direct correction / no correction MSE | 2.025× |

The pooled correlation combines bins with different base rates and should not be interpreted as a pure league-specific effect.

## By goal-difference category

| Category | Paired league-years | Pearson | Same sign weighted | Carry-forward / no-correction MSE |
|---|---:|---:|---:|---:|
| away3plus | 78 | +0.116 | 46.0% | 1.515× |
| away2 | 78 | -0.043 | 51.7% | 2.447× |
| away1 | 78 | -0.049 | 59.5% | 2.469× |
| draw | 78 | +0.077 | 55.2% | 1.851× |
| home1 | 78 | +0.071 | 50.4% | 1.955× |
| home2 | 78 | -0.125 | 57.2% | 1.857× |
| home3plus | 78 | +0.033 | 45.1% | 2.142× |

## By next test year

| Next year | League-year-category comparisons | Pearson | Same sign weighted | Carry-forward / no-correction MSE |
|---|---:|---:|---:|---:|
| 2025 | 273 | +0.144 | 55.3% | 1.999× |
| 2026 | 273 | -0.072 | 48.5% | 2.049× |

## Interpretation

- The direct prior-year error-carry-forward hypothesis fails at the league/year/margin-category aggregation level; it roughly doubles residual MSE versus not correcting.
- Some category sign-persistence rates exceed 50%, but magnitude and calibration are unreliable; do not infer profitable betting or approve a filter from these aggregates.
- A conditional model based on match features could differ; this R60 does **not** fit such a model and cannot establish its value.

## Evidence limitations

- Input R58 is from latest M1 historical cache, filtered by kickoff, not verified true historical as-of snapshots.
- R58 uses annually frozen model-class fits, not exact historical per-run production M9.
- Each of the seven margin categories for a fixture is dependent; 546 comparisons are not 546 independent samples.
- 2026 incomplete; different leagues have different coverage.
- No pre-match received Crown odds for the held-out universe; no actual AH ROI. No official M9, Telegram, or ledger changes.

## Optional next research

Condition on model-implied probabilities, predicted expected goals, or handicap lines using fixture-level historical predictions generated with strictly earlier information, rather than extrapolating league-average prior-year category error. This is a proposal only, not an approved production rule.
