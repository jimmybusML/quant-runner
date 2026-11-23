# R65–R67 | Codex 2023–2026 historical Crown audit and probability/return replay

## Correct research scope
This study uses the four-year historical Codex recovered match and bookmaker database. The former R64 M9 formal 275 orders were an irrelevant sample and **are not used here**. No production files were changed.

## Original historical data audit
- 2023–2026 completed cache fixtures: 42,701, from 61 league files.
- Joined SHA-verified historical Crown open/close rows: 57,667 price events, 29,653 unique complete fixtures, 29,664 distinct checked original source files; SHA/Crown identity errors: {}.
- The database also preserves over four million historical Crown AH movement rows; we selected documented open/close snapshots for a reproducible two-timepoint comparison. That is an experiment definition, **not** a user-approved data restriction; later movement-time studies remain possible.

| Year | Completed unique games | Matched Crown open | Matched Crown close |
|---|---|---|---|
| 2023 | 9,887 | 3,727 | 3,711 |
| 2024 | 10,029 | 7,761 | 7,724 |
| 2025 | 10,308 | 8,951 | 8,931 |
| 2026 | 12,477 | 9,214 | 7,648 |

## Model-compatible historical Crown paired samples

All three fitted models produced same-fixture prediction + retrospective AH payout on 49,451 price events (not distinct fixtures); open and close observations of one fixture are dependent. 8,216 price events could not be paired across all model classes, chiefly unavailable pre-year training or unseen teams. No fabricated probabilities for those rows. There were 404 per-fixture valid-rho adjustments in DC implementation.

## Historical model decisions using actual Crown odds
At each open or close historical quote, each model selects home or away by maximum **model expected return using that Crown price**, even if both estimated returns are negative. This is deliberately not EV-threshold-filtered; the payout is a retrospective counterfactual for one unit on the chosen side. Different quote types correspond to different hypothetical execution times and should **not** be combined as separate fixtures. No Telegram was sent.

### Crown open event — 25,209 matched price observations, 25,209 matches
Provider quote lead-time p10 / median / p90 (minutes): 1787.0 / 8197.6 / 19028.0.

| Model | Prob 1X2 LL | Simulated net U | Simulated ROI | Model predicted EV / bet | Home picks |
|---|---|---|---|---|---|
| Annual bivariate Poisson | 1.030647 | -1000.135 | -3.967% | +0.1324 | 12137 |
| Annual Dixon-Coles | 1.024166 | -1053.900 | -4.181% | +0.1285 | 12096 |
| Online Poisson EKF | 1.001208 | -837.480 | -3.322% | +0.1079 | 12141 |

### By year: historical quote-level simulation

| Year | Matched | BP ROI | DC ROI | EKF ROI |
|---|---|---|---|---|
| 2023 | 3306 | -3.88% | -4.22% | -3.27% |
| 2024 | 6856 | -3.87% | -4.22% | -2.89% |
| 2025 | 8146 | -3.34% | -3.39% | -3.55% |
| 2026 | 6901 | -4.85% | -5.05% | -3.51% |

### Descriptive league-cluster ROI differences

| Comparison | ROI gain (percentage points) | Leagues improving | Bootstrap 95% range (percentage points) |
|---|---|---|---|
| dynamic_vs_annual_bp_Ev_choice | +0.645 | 22/44 | [-0.911, +2.159] |
| dynamic_vs_annual_dc_Ev_choice | +0.859 | 25/44 | [-0.644, +2.364] |
| annual_dc_vs_annual_bp_Ev_choice | -0.213 | 15/44 | [-0.483, +0.052] |

### Crown close event — 24,242 matched price observations, 24,242 matches
Provider quote lead-time p10 / median / p90 (minutes): 0.3 / 2.5 / 22.0.

| Model | Prob 1X2 LL | Simulated net U | Simulated ROI | Model predicted EV / bet | Home picks |
|---|---|---|---|---|---|
| Annual bivariate Poisson | 1.033747 | -701.505 | -2.894% | +0.1559 | 11737 |
| Annual Dixon-Coles | 1.026791 | -743.465 | -3.067% | +0.1517 | 11718 |
| Online Poisson EKF | 1.002704 | -838.590 | -3.459% | +0.1231 | 11757 |

### By year: historical quote-level simulation

| Year | Matched | BP ROI | DC ROI | EKF ROI |
|---|---|---|---|---|
| 2023 | 3346 | -3.66% | -3.86% | -2.78% |
| 2024 | 6834 | -3.37% | -3.67% | -4.20% |
| 2025 | 8143 | -2.46% | -2.40% | -3.63% |
| 2026 | 5919 | -2.51% | -2.84% | -2.75% |

### Descriptive league-cluster ROI differences

| Comparison | ROI gain (percentage points) | Leagues improving | Bootstrap 95% range (percentage points) |
|---|---|---|---|
| dynamic_vs_annual_bp_Ev_choice | -0.565 | 19/44 | [-2.055, +0.925] |
| dynamic_vs_annual_dc_Ev_choice | -0.392 | 20/44 | [-1.859, +1.092] |
| annual_dc_vs_annual_bp_Ev_choice | -0.173 | 17/44 | [-0.414, +0.041] |

## Evidential limits and next decisions
- These are archived Crown historical **provider source timestamps**, not actual 2023–25 system-received bid/ask confirmations. Captures taken in November 2026 cannot prove quotes were accessible at past event times. Do not label this live trade ROI or formal achieved ROI.
- Actual first receipt of every historical final score is not archived in this cache; training used kickoff+3h as an exploratory availability proxy. This is not a user-approved production gate or proof of exact historical causality.
- Full 2023–26 Crown quote and fixture universes differ; results cover the intersection only and are not an unfiltered production trading universe.
- Annual frozen Bivariate/DC model versus dynamic EKF differ in update cadence. R63 monthly refit comparison remains relevant. All EKF prior/process parameters are exploratory, not final product logic.
- All outcomes include full win, half win, push, half loss, full loss using independent Asian payout settlement code; no EV score threshold, order cap, new model switching rule, or live runner deployment introduced.
- Price-before-kickoff event timing is not necessarily practical: late closing prices can be seconds before start. Opening prices give another historical timepoint; neither assures execution.
- Bootstrap resamples whole league histories, not proof of independent years or conclusive true ROI. Several repeated research comparisons mean apparent wins may be chance.
- All raw fixture-level strategy comparisons remain in local nonproduction state files, not published order identifiers.

## Research files
- m9_historical_crown_audit_r65.py: SHA-audited historical source and score join.
- m9_historical_crown_models_r66.py: three model grids, real Crown source-quote price EV, independent settlement simulation.
- m9_historical_crown_summary_r67.py: public aggregate 4-year analysis.
- M9_HISTORICAL_CROWN_AUDIT_R65.json, M9_HISTORICAL_CROWN_R65_R67.json: summary evidence.

## Optional further investigation
Use the full movement-price timeline, genuine archived pre-match receipts where available, and a same-update-frequency model challenger. Distinguish historical market-EV exploration from actual auditable forward orders. No deployment or user rule changes.
