# R50 | True historical forecast-error residual: 1-season vs 2-season pooled

Previous one or two full seasons per league: actual team points (win=1, draw=.5) minus model forecast expected points (Pwin+.5*Pdraw), divided by games; home minus away residual as exponential offsets to home/away 1X2. Test season is entirely held out; zero test-season results in calibration. No future information. Two-season variant pools all available prior two seasons' OOS predictions, not raw goal difference.

## Results (1X2 log loss; lower is better)

| Season | N | Original | Prior 1 season | Prior 2 seasons pooled |
|---|---:|---:|---:|---:|
| 2324 | 1890 | 1.000021 | 1.003403 | 0.998962 |
| 2425 | 1882 | 1.007160 | 1.004010 | 0.998933 |
| 2526 | 1880 | 1.001400 | 1.000089 | 0.998463 |
| 2627 | 528 | 0.956162 | 0.953698 | 0.949589 |

## Pooled 2023/24 onward

| Metric | Original | Prior 1 season | Prior 2 seasons pooled |
|---|---:|---:|---:|
| logloss | 0.998868 | 0.998333 | 0.994583 |
| brier | 0.596152 | 0.596035 | 0.593118 |

Total 6180 test fixtures. The two-season pooled prior-forecast residual improved 1X2 LL across all four recent test seasons.

## Limitations
- True prior-season model forecast residual, unlike R49 raw goal difference.
- These are 1X2 post-processing corrections to independent M3 season-forward bivariate predictions, NOT refitted M9 goal intensities or full score grid.
- Model source contains date-only fixtures, different training/league universe than production M9.
- No Crown AH quotes, historical receipt timestamps, Telegram orders, or ROI.
- No production logic, rules or order counts changed.

## Next research (optional, not production rule)

Map true pre-cutoff forecast residuals to full M9 bivariate score matrices and evaluate actual Asian handicap five-state settlements against timestamp-verifiable Crown quotes. Keep production M9 unchanged.
