# R58 | 26,012-match M9 goal-difference distribution audit

## Research question

Does the original M9-class bivariate score grid systematically misallocate probability across Asian-handicap-relevant final goal differences, and does the R57 prior-forecast-residual correction repair those errors?

Same 26,012 test fixtures, 43 leagues, 121 league-year groups as R57. Annual frozen model-class fits; not exact per-run production M9 and not historical Crown price backtest.

## Goal-difference calibration

| Margin | Actual % | Original % | R57 residual-corrected % |
|---|---:|---:|---:|
| away3plus | 5.720% | 5.520% | 5.519% |
| away2 | 8.319% | 8.729% | 8.730% |
| away1 | 17.134% | 17.345% | 17.346% |
| draw | 25.573% | 24.820% | 24.818% |
| home1 | 21.152% | 20.863% | 20.860% |
| home2 | 12.094% | 12.519% | 12.517% |
| home3plus | 10.007% | 10.204% | 10.208% |

## Scoring metrics

| Scope | N | Original 7-bin margin LL | Corrected LL | Original Brier | Corrected Brier |
|---|---:|---:|---:|---:|---:|
| 2024 | 8,878 | 1.754896 | 1.753470 | 0.806520 | 0.806182 |
| 2025 | 9,038 | 1.764658 | 1.762230 | 0.809201 | 0.808577 |
| 2026 | 8,096 | 1.781613 | 1.779379 | 0.812914 | 0.812356 |
| ALL | 26,012 | 1.766603 | 1.764578 | 0.809442 | 0.808935 |

## Interpretation

- Baseline draw actual 25.573% vs predicted 24.820% (underestimated by 0.753 percentage points). Home win by two actual 12.094% vs predicted 12.519% (overestimated by 0.425 points).
- R57 residual correction modestly improves individual-fixture multiclass margin LL and Brier, but does not materially remove aggregate draw/home-margin calibration bias.
- The observed aggregate margin bias is a research lead, **not yet a verified tradable advantage**. Per-league/per-year variation, uncertainty and prior-only calibration need further testing.
- These are unconditioned goal-difference categories. The distribution at each actual Crown handicap line can differ materially; no Crown AH ROI is calculated.

## Caveats

- The M1 history cache is a latest snapshot; kickoff filtering is not historical as-of receipt proof.
- R57 inherited annual frozen model-class training and exploratory coefficient 0.1, not exact production M9 replay or approved parameters.
- 2026 is incomplete. League/year group coverage varies; pooled bias may conceal league-specific reversals.
- No production code, formal Telegram, Crown evidence or official ledger changed.

## Next research (optional, not a new rule)

Test goal-difference recalibration using only earlier-season data and later untouched fixtures, then translate to five-state AH probabilities across line values; assess real Crown ROI only where pre-kickoff received quotes exist.
