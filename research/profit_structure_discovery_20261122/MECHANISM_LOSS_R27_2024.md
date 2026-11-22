# R27 | 2024 frozen-structure mechanism and loss diagnostics

2019-2023 frozen 494 R7-R15 structures; 2024 earliest quote + equal net voting; 1U per fixture. All bins are descriptive research comparisons, not new rules.

Baseline: {'n': 9225, 'net_U': -306.735, 'roi_pct': -3.325}

## Fixed portfolio loss attribution

| Dimension | Group | Orders | Net U | ROI |
|---|---|---:|---:|---:|
| line_abs | 0 | 1211 | -86.99 | -7.1833% |
| line_abs | 0.25-0.75 | 5330 | -133.655 | -2.5076% |
| line_abs | 1-1.75 | 2265 | -50.665 | -2.2369% |
| line_abs | 2+ | 419 | -35.425 | -8.4547% |
| odds | 1.8-1.9 | 3092 | -56.32 | -1.8215% |
| odds | 1.9-2.0 | 3193 | -154.43 | -4.8365% |
| odds | 2.0-2.1 | 1892 | -63.05 | -3.3325% |
| odds | 2.1+ | 207 | -14.98 | -7.2367% |
| odds | <1.8 | 841 | -17.955 | -2.135% |
| overround | 3-5% | 5677 | -139.605 | -2.4591% |
| overround | 5-7% | 997 | -44.48 | -4.4614% |
| overround | 7%+ | 382 | -18.97 | -4.966% |
| overround | <3% | 2169 | -103.68 | -4.7801% |
| line_movement | 0 | 8102 | -292.01 | -3.6042% |
| line_movement | <=0.25 | 1098 | -9.865 | -0.8985% |
| line_movement | <=0.75 | 25 | -4.86 | -19.44% |
| ticks | 1 | 2578 | -124.955 | -4.847% |
| ticks | 2 | 1457 | 17.955 | 1.2323% |
| ticks | 3-5 | 2383 | -116.15 | -4.8741% |
| ticks | 6+ | 2807 | -83.585 | -2.9777% |
| vote_support | 1 | 4721 | -173.21 | -3.6689% |
| vote_support | 2 | 2338 | -66.5 | -2.8443% |
| vote_support | 3-5 | 1783 | -59.4 | -3.3315% |
| vote_support | 6+ | 383 | -7.625 | -1.9909% |
| distinct_batches | 1 | 5852 | -196.365 | -3.3555% |
| distinct_batches | 2 | 2321 | -65.685 | -2.83% |
| distinct_batches | 3 | 690 | -43.255 | -6.2688% |
| distinct_batches | 4 | 268 | 1.57 | 0.5858% |
| distinct_batches | 5 | 70 | -8.055 | -11.5071% |
| distinct_batches | 6 | 21 | 5.28 | 25.1429% |
| distinct_batches | 7 | 3 | -0.225 | -7.5% |
| direction | away | 4538 | -108.225 | -2.3849% |
| direction | home | 4687 | -198.51 | -4.2353% |
| conflict | no | 7982 | -217.73 | -2.7278% |
| conflict | yes | 1243 | -89.005 | -7.1605% |
| horizon | T12 | 4066 | -90.11 | -2.2162% |
| horizon | T2 | 867 | -51.705 | -5.9637% |
| horizon | T24 | 2392 | -94.405 | -3.9467% |
| horizon | T6 | 1900 | -70.515 | -3.7113% |
| batch_present_chosen | R11 | 946 | -61.945 | -6.5481% |
| batch_present_chosen | R12 | 3100 | -179.63 | -5.7945% |
| batch_present_chosen | R13 | 2121 | -55.7 | -2.6261% |
| batch_present_chosen | R14 | 2401 | -104.5 | -4.3524% |
| batch_present_chosen | R15 | 3602 | -33.195 | -0.9216% |
| batch_present_chosen | R7 | 595 | -3.255 | -0.5471% |
| batch_present_chosen | R9 | 1368 | -23.165 | -1.6933% |
| batch_present_opposed | R11 | 62 | -12.09 | -19.5% |
| batch_present_opposed | R12 | 361 | -15.145 | -4.1953% |
| batch_present_opposed | R13 | 146 | -13.075 | -8.9555% |
| batch_present_opposed | R14 | 334 | -27.47 | -8.2246% |
| batch_present_opposed | R15 | 301 | -15.93 | -5.2924% |
| batch_present_opposed | R7 | 82 | -11.435 | -13.9451% |
| batch_present_opposed | R9 | 89 | -6.215 | -6.9831% |

## Exploratory leave-one-existing-batch-out comparison

**Caution:** This sensitivity compares only fixtures with a non-tied full-494 baseline vote; fixtures tied in baseline but untied by removing a batch are excluded. Thus it is not a complete reconstituted batch-removed portfolio. All removals were evaluated after seeing 2024 and are not independently validated.

| Removed batch | Remaining baseline-fixture orders | Net U | ROI |
|---|---:|---:|---:|
| R11 | 8988 | -266.985 | -2.9705% |
| R12 | 7741 | -220.83 | -2.8527% |
| R13 | 8206 | -281.735 | -3.4333% |
| R14 | 7941 | -233.54 | -2.9409% |
| R15 | 7391 | -300.575 | -4.0668% |
| R7 | 9129 | -327.36 | -3.5859% |
| R9 | 8717 | -287.665 | -3.3% |

## Interpretation

- Flat 0 and deep 2+ handicap have more negative ROI than intermediate lines, but no causal conclusion.
- The two-tick quote-window group is positive on 2024, but post-hoc and possibly explained by quote collection/coverage; not a valid standalone strategy.
- Vote support count and number of distinct research batches do not show a simple monotonic positive relationship with 2024 returns.
- Batch-presence segments overlap and cannot be added. Leave-one-out ablations change order sets, so net U changes are not marginal contributions.
- Need verified quote-availability and historical tick coverage analysis before treating quote-window differences as a market effect.
- Original historical Crown quotes are retrospective, not confirmed contemporaneously executable. No 2025-2026, no M8 or production modifications.

