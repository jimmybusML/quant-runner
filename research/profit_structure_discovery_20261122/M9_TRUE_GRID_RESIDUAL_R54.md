# R54 | TRUE pre-cutoff forecast residual in M9 bivariate full score grid

## What was executed

- Fit the same penaltyblog BivariatePoissonGoalModel class as production M9, but with **annual frozen** models in four pilot M1 historical league IDs, not production M9 per-run training.
- Fit earlier calibration model on data before prior calendar year. Predict previous-year fixtures (known teams only); estimate team actual points minus forecast expected points.
- Fit baseline model on all matches before target year. Apply earlier forecast residual to entire full score grid via normalized exponential score-difference tilt (research scale 0.1).
- Evaluate original vs corrected score grid on identical held-out fixtures in 2024–2026. No test-year outcomes used in calibration.

## Results by league (1X2 log loss, lower better)

| League ID | N | Original | Corrected |
|---|---:|---:|---:|
| 1 | 994 | 1.009596 | 1.007394 |
| 10 | 720 | 1.032451 | 1.035255 |
| 12 | 1020 | 0.989163 | 0.988046 |
| 61 | 652 | 1.052360 | 1.051291 |

## Results by year

| Year | N | Original 1X2 LL | Corrected 1X2 LL |
|---|---:|---:|---:|
| 2024 | 1144 | 1.024248 | 1.025108 |
| 2025 | 1128 | 1.013565 | 1.012100 |
| 2026 | 1114 | 1.011622 | 1.010422 |

## All 3,386 fixtures

| Metric | Original | Corrected |
|---|---:|---:|
| 1X2 log loss (lower better) | 1.016535 | 1.015942 |
| Exact-score log loss (lower better) | 3.015821 | 3.015025 |
| Synthetic neutral AH0 2.0 unit per fixture (NOT Crown ROI) | 0.276137 | 0.283225 |

## Crown evidence inspection

- Inspected local `~/QuantAsiaDesk/state/m9_crown_evidence/`: 519 raw evidence JSON files, of which 272 contain a Crown bookmaker record and Asian handicap quote list.
- These are primarily recent 2026 evidence and have **not** been matched to 2024–26 annual-frozen historical forecast fixtures with independently verified receipt-before-kickoff timestamps.
- A quote’s source timestamp before kickoff alone is insufficient proof that the quote was actually received before kickoff. Therefore **no historical Crown ROI is claimed**.

## Caveats
- Calibration uses a prior-year OOS model forecast residual, not raw goal difference; model class is same as M9.
- Calibration model is annual frozen, not per-match updated; previous-year OOS forecasts can be less recent than production.
- Historical cache is latest snapshot and does not establish as-of historical receipt for each match.
- 0.1 score-grid tilt is exploratory, not fitted or authorized production setting.
- Synthetic neutral AH0 2.0 is NOT Crown, no Crown ROI or tradable orders.
- No formal M9, Telegram or ledger changes.

## Next research (not a new rule)

- Produce matched point-in-time Crown quote/receipt and fixture identity coverage audit; do not substitute post-match retrieved prices.
- Expand league coverage and re-fit timing, then compare actual five-state AH settlement, order count and ROI on the same fixtures when evidence permits.
- Keep production M9 and Telegram formal receipts untouched.
