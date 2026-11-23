# R49 | M9 bivariate score-grid exploratory team goal-difference tilt

## Important method identity

This test applies **raw observed team goal-difference per match**, not an actual forecast residual. Its code filename contains `residual`, but the calculation is NOT the R47 previous-season predicted-vs-actual residual. The goal-difference signal may double-count strength already learned by M9.

## Read-only same-fixture results

| League ID | Year | N | Original 1X2 LL | Prior 1-year goal difference | Prior 2-year goal difference |
|---|---:|---:|---:|---:|---:|
| 1 | 2024 | 353 | 0.974228 | 0.979473 | 0.981373 |
| 1 | 2025 | 360 | 0.975295 | 0.978635 | 0.979183 |
| 1 | 2026 | 281 | 1.097969 | 1.116152 | 1.121295 |
| 10 | 2024 | 220 | 1.112610 | 1.218522 | 1.228813 |
| 10 | 2025 | 187 | 1.044016 | 1.111932 | 1.116663 |
| 10 | 2026 | 313 | 0.969200 | 1.008908 | 1.005808 |
| 12 | 2024 | 343 | 0.994743 | 0.991120 | 0.998253 |
| 12 | 2025 | 349 | 1.018684 | 1.035866 | 1.034403 |
| 12 | 2026 | 328 | 0.951919 | 0.937754 | 0.946729 |
| 61 | 2024 | 228 | 1.060819 | 1.090122 | 1.093119 |
| 61 | 2025 | 232 | 1.040705 | 1.045127 | 1.052106 |
| 61 | 2026 | 192 | 1.056397 | 1.067703 | 1.059769 |

## Overall

| Metric | Original | Prior 1-year | Prior 2-year |
|---|---:|---:|---:|
| 1X2 log loss (lower better) | 1.016535 | 1.036198 | 1.039196 |
| Exact-score log loss (lower better) | 3.015821 | 3.052638 | 3.058271 |
| Synthetic neutral AH0 unit (NOT Crown ROI) | 0.276137 | 0.278500 | 0.283816 |

Total 3386 same fixtures; errors: 0.

## Interpretation

Both goal-difference tilts worsened the overall 1X2 and exact-score likelihood. This does not refute R47 true forecast residual result because it is a different signal and different model/sample. Do not equate neutral synthetic AH0 unit with Crown ROI.

## Caveats
- This is observed goal-difference signal, not forecast-error residual, and can double-count model strength. Results must not be described as R47 residual directly embedded.
- 0.1 tilt and 1y/2y windows are exploratory only, not approved production parameters.
- Annual frozen model is not exact M9 per-run retraining.
- Only four pilot league IDs; source is latest historical cache, not proven historically available at each cutoff.
- Synthetic AH0 at 2.0 is not Crown AH or tradable ROI.
- No production or Telegram changes.

## Research continuation (not a production rule)

Estimate strictly pre-cutoff model **forecast-error residuals** (rather than raw goal difference), apply residual shrinkage to the actual bivariate grid, and then compare same-fixture accuracy and Crown AH settlement where point-in-time quote provenance is available.
