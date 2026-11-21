# M8 exact frozen-rule cross-league replay: current full-path recheck

## Scope and method

This addendum keeps the specifically requested original `schedule_universe.jsonl` scope: 18,374 unique FIDs in 15 leagues outside the frozen 49. It uses the current full AH quote path snapshot, applies the repository's frozen `assign_exact_group` helper, keeps the original group priority `base → A → B → C → D → E → F → G`, and checks direction with `group_side`. The archived E rule has a documented endpoint-tie fallback: for 52 E assignments, `group_side` returns no side because `p1-p0=0`; the historical intermediate-path direction is retained, as in the earlier frozen-member audit. No market, stake, rule, or production setting changed.

The later full-path source includes all available Crown movement quotes between T6 and T1, not only the three sampled checkpoint rows. This resolves an implementation difference in the earlier 1,160-order snapshot. Among the 1,072 FIDs common to that earlier ledger and the current exact-scope ledger, 1,069 have identical group, direction, and net U. The current full-path logic has 199 additional FIDs and no longer assigns 88 earlier checkpoint-only hits. The old result remains in its original report; it is not overwritten.

## Coverage

- Original target schedule: 18,374 unique FIDs / 15 leagues.
- Current complete T6/T3/T1 paths: 6,967. Remaining statuses: {"movement_capture_no_quotes": 11266, "complete_path_no_signal": 5696, "complete_path_with_signal": 1271, "no_valid_pregame_quote": 2, "missing_T6": 139}.
- Complete-path observation period: 380 ISO weeks. Added orders: 1,271 unique FIDs; frozen FID overlap: 0.
- Full path union source: 21,096 FIDs / 6,971 complete paths / 1,273 orders. Exactly 2 of those orders lie outside the specifically requested 18,374-FID inventory and are excluded from this addendum.
- Historical source-event replay only. Verified live Crown receipt FIDs and live orders in this target cohort: 0.

## Group results

| Group | Unique orders | Net U | ROI | MDD U | Avg / observed ISO week |
|---|---:|---:|---:|---:|---:|
| base | 691 | +8.580 | +1.242% | 18.710 | 1.818 |
| A | 54 | -13.190 | -24.426% | 16.995 | 0.142 |
| B | 217 | -5.955 | -2.744% | 15.090 | 0.571 |
| C | 38 | +4.710 | +12.395% | 3.000 | 0.100 |
| D | 29 | +9.830 | +33.897% | 1.060 | 0.076 |
| E | 52 | +2.690 | +5.173% | 5.430 | 0.137 |
| F | 22 | +1.120 | +5.091% | 3.250 | 0.058 |
| G | 168 | -0.600 | -0.357% | 18.475 | 0.442 |
| **Deduplicated total** | **1271** | **+7.185** | **+0.565%** | **27.755** | **3.345** |

ROI is net U divided by unique orders. Asian quarter lines are settled by splitting into the adjacent half-point legs. The independent raw Crown/FT audit verifies 1,271/1,271 scoped orders, with zero discrepancies and +7.185U recomputed.

## Annual results

| Year | Added orders | Net U | ROI | MDD U | Observed ISO weeks | Avg orders/week |
|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 71 | +5.935 | +8.359% | 4.000 | 33 | 2.152 |
| 2020 | 54 | -5.660 | -10.481% | 10.950 | 38 | 1.421 |
| 2021 | 77 | -1.880 | -2.442% | 9.615 | 34 | 2.265 |
| 2022 | 90 | +1.775 | +1.972% | 4.630 | 34 | 2.647 |
| 2023 | 181 | +9.530 | +5.265% | 5.725 | 45 | 4.022 |
| 2024 | 409 | +13.310 | +3.254% | 20.665 | 53 | 7.717 |
| 2025 | 359 | -9.565 | -2.664% | 20.840 | 52 | 6.904 |
| 2026 | 30 | -6.260 | -20.867% | 8.320 | 21 | 1.429 |

Group annual count / net U:

| Group | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| base | 49 / +1.285 | 24 / +0.680 | 44 / -4.530 | 44 / -3.455 | 103 / -0.540 | 231 / +8.910 | 187 / +5.080 | 9 / +1.150 |
| A | 3 / -0.440 | 1 / -1.000 | 2 / +1.495 | 6 / +1.220 | 6 / -4.550 | 18 / -9.000 | 15 / +0.115 | 3 / -1.030 |
| B | 9 / +3.100 | 7 / -1.910 | 12 / +0.320 | 18 / +1.775 | 30 / +3.850 | 63 / -5.385 | 68 / -1.555 | 10 / -6.150 |
| C | 0 / +0.000 | 2 / -2.000 | 2 / -0.200 | 2 / +1.800 | 3 / +0.810 | 18 / +2.570 | 10 / +2.730 | 1 / -1.000 |
| D | 1 / +0.000 | 5 / +1.850 | 2 / -0.060 | 4 / +1.180 | 5 / +0.070 | 6 / +4.020 | 6 / +2.770 | 0 / +0.000 |
| E | 2 / +1.910 | 3 / +1.840 | 2 / -1.000 | 2 / +1.990 | 8 / -1.030 | 19 / +3.490 | 16 / -4.510 | 0 / +0.000 |
| F | 0 / +0.000 | 0 / +0.000 | 0 / +0.000 | 0 / +0.000 | 1 / +0.850 | 5 / +0.760 | 14 / -0.330 | 2 / -0.160 |
| G | 7 / +0.080 | 12 / -5.120 | 13 / +2.095 | 14 / -2.735 | 25 / +10.070 | 49 / +7.945 | 43 / -13.865 | 5 / +0.930 |

Frozen and combined annual results:

| Year | Frozen orders / U | Added orders / U | Combined orders / U / ROI |
|---:|---:|---:|---:|
| 2019 | 291 / -1.330 | 71 / +5.935 | 362 / +4.605 / +1.272% |
| 2020 | 548 / -9.950 | 54 / -5.660 | 602 / -15.610 / -2.593% |
| 2021 | 731 / +23.370 | 77 / -1.880 | 808 / +21.490 / +2.660% |
| 2022 | 547 / +12.830 | 90 / +1.775 | 637 / +14.605 / +2.293% |
| 2023 | 1304 / +13.330 | 181 / +9.530 | 1485 / +22.860 / +1.539% |
| 2024 | 2224 / +31.550 | 409 / +13.310 | 2633 / +44.860 / +1.704% |
| 2025 | 2431 / +66.395 | 359 / -9.565 | 2790 / +56.830 / +2.037% |
| 2026 | 2218 / +99.820 | 30 / -6.260 | 2248 / +93.560 / +4.162% |

2024 was positive, while 2025 and the available portion of 2026 were negative. The 2024–2026 increment sums to -2.515U; the result does not show stable recent cross-year profit. The 2026 history ends June 1, 2026 and is partial.

## League results

| Provider league ID | Orders | Net U | ROI |
|---:|---:|---:|---:|
| 10 (International Match) | 153 | +15.060 | +9.843% |
| 10714 (Albania Championship) | 41 | +0.520 | +1.268% |
| 11498 (Andorra Premier Division) | 0 | +0.000 | — |
| 129 (Brazil Serie A) | 126 | -11.000 | -8.730% |
| 19290 (Argentina Liga Profesional) | 117 | +3.940 | +3.368% |
| 27388 (UEFA Nations League A) | 14 | -4.215 | -30.107% |
| 27389 (UEFA Nations League B) | 6 | -3.200 | -53.333% |
| 27390 (UEFA Nations League C) | 17 | -1.920 | -11.294% |
| 314 (Belarus Premier League) | 0 | +0.000 | — |
| 33 (Bosnia & Herzegovina Premier Liga) | 50 | -13.280 | -26.560% |
| 378 (Egypt Division 1) | 158 | -5.745 | -3.636% |
| 670 (Gulf Cup) | 6 | +5.480 | +91.333% |
| 779 (Mexico Liga MX) | 127 | +12.145 | +9.563% |
| 8293 (Kosovo Superliga) | 2 | -2.000 | -100.000% |
| 85 (USA MLS) | 454 | +11.400 | +2.511% |

Six leagues have positive point estimates, seven negative, and two no order. Gulf Cup is only six orders; its +5.480U is not evidence of a repeatable league effect. League rows are descriptive and are not filters.

## Frozen baseline combination

- Frozen original eight: 10,294 FIDs, +236.015U, ROI +2.293%.
- Added outside-49 cohort: 1,271 FIDs, +7.185U, ROI +0.565%, MDD 27.755U; 0 FID overlap.
- Combined by unique FID: 11565 FIDs, +243.200U, ROI 2.103%, MDD 57.565U. The addition improves historical net by +7.185U.
- Mean incremental order count: 3.345 per complete-path observed ISO week; 250 weeks carried at least one new order.

## Audit and files

The reproduction script directly calls the frozen group helper on all 6,967 target full paths; group mismatches: 0. It validates every emitted order against its path row and independently audited Crown/FT settlement. Detailed outputs and SHA256 manifests are in this directory. All of this remains research-only; no M8 member, production model, Telegram dispatch, formal ledger, collection workflow, or user-confirmed rule changed.
