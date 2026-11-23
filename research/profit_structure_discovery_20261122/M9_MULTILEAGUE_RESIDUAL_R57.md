# R57 | Large-scale multi-league, multi-year true forecast residual score-grid research

## Scope and method

Read-only research using **all 61 available M1 history league cache files**, 69,200 raw completed fixtures, and annual-frozen BivariatePoissonGoalModel model-class fits. 2024, 2025 and 2026 are test years; earlier years used for training and prior-model out-of-sample team expected-points residual calibration. Same-fixture original and residual-enhanced full score grids are evaluated. Exploratory coefficient 0.1, **not a user-confirmed production parameter**.

Some league-year groups lack historical pre-cutoff training or eligible fixtures and are reported as skipped, not silently discarded or counted as tests.

## Verified aggregate results

| Scope | Test fixtures | Baseline 1X2 LL | Enhanced 1X2 LL | Gain (lower better) | Improved league-year groups |
|---|---:|---:|---:|---:|---:|
| 2024 | 8,878 | 1.018661 | 1.017689 | +0.000973 | 32/39 |
| 2025 | 9,038 | 1.021094 | 1.019118 | +0.001976 | 27/39 |
| 2026 | 8,096 | 1.009594 | 1.008168 | +0.001426 | 32/43 |
| ALL | 26,012 | 1.016685 | 1.015222 | +0.001462 | 91/121 |

Effective test: **26,012** matches, **43** leagues, **121** league-year groups. Skipped **62** groups, model fit errors **0**.

Overall positive leagues: **35/43**; all-observed-years positive leagues: **19**.

Exact-score log loss improvement: **+0.002053**.

Synthetic neutral AH0 direction changed **342** fixtures (not Crown trade signals).

Exploratory 10,000-replicate league-cluster bootstrap 95% interval for 1X2 LL improvement: **[+0.000908, +0.002054]**. This does not resolve temporal dependence or data snapshot limitations.

## League-level results

| League ID | N | 1X2 LL improvement | Improved years / tested years |
|---|---:|---:|---:|
| 1 | 994 | +0.002202 | 3/3 |
| 10 | 720 | -0.002804 | 1/3 |
| 12 | 1020 | +0.001118 | 2/3 |
| 14 | 984 | +0.000435 | 2/3 |
| 16 | 801 | +0.001746 | 3/3 |
| 25 | 830 | +0.001089 | 3/3 |
| 29 | 535 | +0.000923 | 3/3 |
| 31 | 817 | +0.001008 | 2/3 |
| 35 | 749 | +0.000772 | 1/3 |
| 37 | 853 | +0.000879 | 2/3 |
| 40 | 503 | +0.000389 | 2/3 |
| 45 | 386 | +0.001335 | 2/3 |
| 46 | 491 | +0.005188 | 3/3 |
| 47 | 457 | +0.002030 | 3/3 |
| 48 | 809 | -0.000551 | 1/3 |
| 51 | 831 | -0.000294 | 1/3 |
| 52 | 805 | +0.002169 | 3/3 |
| 55 | 341 | +0.001469 | 2/3 |
| 60 | 450 | +0.005711 | 3/3 |
| 61 | 652 | +0.001069 | 3/3 |
| 62 | 863 | +0.004157 | 3/3 |
| 70 | 544 | -0.000028 | 1/3 |
| 73 | 857 | +0.002092 | 3/3 |
| 75 | 573 | -0.000088 | 1/3 |
| 141 | 620 | +0.000156 | 2/3 |
| 145 | 1090 | -0.000469 | 2/3 |
| 152 | 489 | +0.009100 | 3/3 |
| 177 | 490 | +0.002752 | 3/3 |
| 262 | 621 | +0.001402 | 3/3 |
| 290 | 780 | +0.002232 | 3/3 |
| 299 | 492 | +0.003479 | 3/3 |
| 303 | 767 | +0.001344 | 2/3 |
| 319 | 572 | +0.000208 | 2/3 |
| 328 | 640 | +0.002213 | 2/3 |
| 670 | 29 | +0.002975 | 2/3 |
| 779 | 973 | +0.003044 | 3/3 |
| 8172 | 789 | +0.000398 | 2/3 |
| 8293 | 309 | +0.002629 | 2/3 |
| 11498 | 277 | +0.002029 | 2/3 |
| 26540 | 157 | +0.000130 | 1/1 |
| 27388 | 23 | +0.000000 | 0/1 |
| 27389 | 13 | +0.000000 | 0/1 |
| 27390 | 16 | +0.000000 | 1/1 |

## Caveats
- M1 latest history snapshot is not a point-in-time archive; pre-match cutoff based on kickoff, not guaranteed historical data receipt.
- Annual frozen model-class replay differs from exact per-run production M9.
- Single exploratory residual score-grid tilt 0.1 is not a production rule; no parameter selection or independent parameter confirmation.
- Full grid and 1X2 log-loss are prediction metrics; AH0 direction flips at neutral 2.0 are not real Crown decisions or ROI.
- League-cluster bootstrap resamples leagues, but within-league temporal dependence and selection from available league cache remain.
- 2026 is incomplete and leagues differ in coverage.
- No actual Crown historical price receipt match for the 26,012 held-out fixtures; do not claim tradable ROI.

## Decision

Predictive log loss improves modestly in this broad exploratory pilot; this is NOT a validated positive expected value at real Crown Asian handicap prices. No change to official M9, Telegram or production ledger.

## Next research options (not rules)

- Compute five-state AH expected return and actual settlement on a sufficiently covered historical Crown quote receipt dataset; do not substitute retrospective price discovery for pre-match received quotes.
- Investigate sensitivity to correction strength using a strictly prior-season chosen parameter and later-year untouched validation.
- Compare exact production training snapshots and same-time challenger predictions before recommending deployment.
