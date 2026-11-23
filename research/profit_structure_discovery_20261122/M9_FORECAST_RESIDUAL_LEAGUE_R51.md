# R51 | Which leagues explain R50 forecast-residual improvement?

Source: independent M3 penaltyblog bivariate OOS season-forward predictions; R50 postprocessing. NOT formal M9 or Crown AH ROI.

Improvement = original 1X2 log loss minus two-season prior forecast-residual corrected log loss (positive is better).

| League | Matches | Improvement | Seasons with improvement / observed |
|---|---:|---:|---:|
| B1 | 902 | +0.001516 | 2/4 |
| D1 | 858 | +0.001624 | 3/4 |
| E0 | 1107 | +0.019980 | 4/4 |
| F1 | 930 | -0.001238 | 2/4 |
| I1 | 1174 | -0.000553 | 2/4 |
| SP1 | 1209 | +0.002811 | 2/4 |

All leagues: n=6180, gain=+0.004284. Excluding E0: n=5073, gain=+0.000859.

## By season

| League | 2023/24 | 2024/25 | 2025/26 | 2026/27 partial |
|---|---:|---:|---:|---:|
| B1 | +0.012512 | -0.007443 | +0.001372 | -0.005640 |
| D1 | -0.012937 | +0.009810 | +0.004855 | +0.009141 |
| E0 | +0.006692 | +0.033869 | +0.017872 | +0.026349 |
| F1 | -0.002904 | +0.003991 | -0.006547 | +0.002479 |
| I1 | -0.007567 | +0.005072 | -0.001546 | +0.009277 |
| SP1 | +0.007972 | +0.001620 | -0.000426 | -0.000939 |

## Interpretation

E0 is the main source of overall gain; four observed test periods all improved. Other leagues mixed, with F1 and I1 slightly worse overall. This is a diagnostic, not evidence of a tradable edge or an approved league filter.

## Caveats
- No confidence interval or formal statistical significance test
- Same R50 dataset, not an independent replication
- No full M9 score grid or Crown Asian handicap ROI
- League-specific performance does not authorize new production filter

## Next research (not a new rule)

Investigate whether E0 forecast residuals persist at the individual-team level and map prior-only residual corrections into the actual M9 bivariate score grid; compare same-fixture Asian handicap settlement only with valid Crown price provenance.
