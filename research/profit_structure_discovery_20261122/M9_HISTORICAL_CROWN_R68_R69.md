# R68–R69 | Codex 2023–2026 historical Crown movement T-6h and T-12h replay

## Four-year Codex historical recovery and lead-time sensitivity
This study uses the four-year historical Codex recovered match and bookmaker database. The former R64 M9 formal 275 orders were an irrelevant sample and **are not used here**. No production files were changed.

## Original historical data audit
An additional audit of all selected source files found 0 hash/Crown-identity failures. The T−6h source-quote median lead was about 6.7 hours; the T−12h median about 14.1 hours. Among 64,260 selected source-quote observations, only 180 have a recorded response-receipt time before kickoff. The historical database is genuine but most records were backfilled after the matches.

- 2023–2026 completed cache fixtures: 42,701, from 61 league files.
- Joined SHA-verified historical Crown T−6h/T−12h movement/open snapshots: 64,260 price events, 32,467 unique complete fixtures, 32,467 distinct SHA-verified response/fixture identity combinations; SHA/Crown identity errors: {}.
- The database also preserves over four million historical Crown AH movement rows; we selected the latest eligible Crown historical movement/open source quote at or before the start minus 6h and minus 12h. These are two lead-time sensitivity scenarios, **not** user-approved production constraints. Other timestamps remain in the original database.

| Year | Completed unique games | Matched Crown T−6h | Matched Crown T−12h |
|---|---|---|---|
| 2023 | 9,887 | 5,212 | 5,127 |
| 2024 | 10,029 | 8,875 | 8,694 |
| 2025 | 10,308 | 8,904 | 8,696 |
| 2026 | 12,477 | 9,476 | 9,276 |

## Model-compatible historical Crown paired samples

All three fitted models produced same-fixture prediction + retrospective AH payout on 55,130 price events (not distinct fixtures); 6h and 12h snapshots from one fixture are dependent. 9,130 price events could not be paired across all model classes, chiefly unavailable pre-year training or unseen teams. No fabricated probabilities for those rows. There were 429 per-fixture valid-rho adjustments in DC implementation.

## Historical model decisions using actual Crown odds
At each historical T−6h or T−12h source quote, each model selects home or away by maximum **model expected return using that Crown price**, even if both estimated returns are negative. This is deliberately not EV-threshold-filtered; the payout is a retrospective counterfactual for one unit on the chosen side. These two lead-time scenarios correspond to different hypothetical execution times and should **not** be combined as separate fixtures. No Telegram was sent.

### Crown lead6h event — 27,826 matched price observations, 27,826 matches
Provider quote lead-time p10 / median / p90 (minutes): 364.3 / 402.0 / 623.4.

| Model | Prob 1X2 LL | Simulated net U | Simulated ROI | Model predicted EV / bet | Home picks |
|---|---|---|---|---|---|
| Annual bivariate Poisson | 1.028840 | -881.765 | -3.169% | +0.1495 | 13516 |
| Annual Dixon-Coles | 1.022124 | -879.890 | -3.162% | +0.1453 | 13489 |
| Online Poisson EKF | 0.999817 | -1067.700 | -3.837% | +0.1177 | 13504 |

### By year: historical quote-level simulation

| Year | Matched | BP ROI | DC ROI | EKF ROI |
|---|---|---|---|---|
| 2023 | 4618 | -2.04% | -1.89% | -3.87% |
| 2024 | 7925 | -3.83% | -3.94% | -3.79% |
| 2025 | 8115 | -2.87% | -2.78% | -4.18% |
| 2026 | 7168 | -3.51% | -3.55% | -3.48% |

### Descriptive league-cluster ROI differences

| Comparison | ROI gain (percentage points) | Leagues improving | Bootstrap 95% range (percentage points) |
|---|---|---|---|
| dynamic_vs_annual_bp_Ev_choice | -0.668 | 22/44 | [-2.010, +0.677] |
| dynamic_vs_annual_dc_Ev_choice | -0.675 | 23/44 | [-1.995, +0.639] |
| annual_dc_vs_annual_bp_Ev_choice | +0.007 | 20/44 | [-0.214, +0.240] |

### Crown lead12h event — 27,304 matched price observations, 27,304 matches
Provider quote lead-time p10 / median / p90 (minutes): 730.5 / 844.8 / 2120.8.

| Model | Prob 1X2 LL | Simulated net U | Simulated ROI | Model predicted EV / bet | Home picks |
|---|---|---|---|---|---|
| Annual bivariate Poisson | 1.027806 | -970.410 | -3.554% | +0.1435 | 13282 |
| Annual Dixon-Coles | 1.021201 | -971.625 | -3.559% | +0.1394 | 13239 |
| Online Poisson EKF | 0.999568 | -996.185 | -3.648% | +0.1129 | 13264 |

### By year: historical quote-level simulation

| Year | Matched | BP ROI | DC ROI | EKF ROI |
|---|---|---|---|---|
| 2023 | 4545 | -2.60% | -2.27% | -3.30% |
| 2024 | 7766 | -4.23% | -4.08% | -3.98% |
| 2025 | 7936 | -3.11% | -3.36% | -3.43% |
| 2026 | 7057 | -3.92% | -4.04% | -3.76% |

### Descriptive league-cluster ROI differences

| Comparison | ROI gain (percentage points) | Leagues improving | Bootstrap 95% range (percentage points) |
|---|---|---|---|
| dynamic_vs_annual_bp_Ev_choice | -0.094 | 22/44 | [-1.395, +1.263] |
| dynamic_vs_annual_dc_Ev_choice | -0.090 | 25/44 | [-1.440, +1.298] |
| annual_dc_vs_annual_bp_Ev_choice | -0.004 | 17/44 | [-0.237, +0.211] |

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
- m9_historical_crown_lead_r68.py: SHA-audited historic Crown open/movement selection at or before T−6h / T−12h.
- m9_historical_crown_models_r66.py: three model grids, real Crown source-quote price EV, independent settlement simulation.
- m9_historical_crown_lead_summary_r69.py: public aggregate 4-year practical lead-time analysis.
- M9_HISTORICAL_CROWN_LEAD_R68.json, M9_HISTORICAL_CROWN_R68_R69.json: summary evidence.

## Optional further investigation
Explore other timestamps within the already preserved full movement-price timeline, genuine archived pre-match receipts where available, and a same-update-frequency model challenger. Distinguish historical market-EV exploration from actual auditable forward orders. No deployment or user rule changes.
