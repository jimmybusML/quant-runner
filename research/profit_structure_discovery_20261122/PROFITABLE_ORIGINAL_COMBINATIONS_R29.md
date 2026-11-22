# R29 | Original profitable candidate fixture-level combination study

No new candidate definitions. All candidate sets are subsets of original frozen 494 R7-R15. **2024 winners and top candidates were selected AFTER seeing 2024 outcomes; 2024 PnL is post-hoc, not independent holdout.**

## Deduplicated earliest eligible horizon, equal-net voting

| Set | Definitions | Historical orders | Historical ROI | 2024 orders | 2024 net U | 2024 ROI | 2024 fixture overlap | 2024 opposed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all_494 | 494 | 13137 | 8.7879% | 9225 | -306.735 | -3.325% | 5436 | 2175 |
| 2024_profitable_208_POSTHOC | 208 | 9680 | 10.2555% | 6876 | 319.035 | 4.6398% | 2813 | 611 |
| top6_by_2024_net_POSTHOC | 6 | 1675 | 8.7961% | 1493 | 97.87 | 6.5553% | 8 | 5 |
| top12_by_2024_net_POSTHOC | 12 | 2474 | 9.5629% | 2160 | 144.955 | 6.7109% | 534 | 37 |

## Yearly ROI, historical in-sample

| Set | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 (post-hoc selection) |
|---|---:|---:|---:|---:|---:|---:|
| all_494 | 13.2733% | 10.8657% | 8.3355% | 9.3857% | 6.7241% | -3.325% |
| 2024_profitable_208_POSTHOC | 15.1822% | 11.0078% | 12.1129% | 11.6925% | 6.9799% | 4.6398% |
| top6_by_2024_net_POSTHOC | 11.683% | 16.5893% | 7.4377% | 9.4066% | 6.5805% | 6.5553% |
| top12_by_2024_net_POSTHOC | 13.4898% | 12.0455% | 9.1761% | 13.3482% | 6.6544% | 6.7109% |

## 2024 alternative vote policies, descriptive only

| Set | Equal net | Skip opposed | Margin >=2 |
|---|---|---|---|
| all_494 | 9225 / -3.325% | 7982 / -2.7278% | 3800 / -2.2993% |
| 2024_profitable_208_POSTHOC | 6876 / 4.6398% | 6579 / 5.1699% | 2328 / 8.1624% |
| top6_by_2024_net_POSTHOC | 1493 / 6.5553% | 1493 / 6.5553% | 3 / 40.5% |
| top12_by_2024_net_POSTHOC | 2160 / 6.7109% | 2159 / 6.6959% | 497 / 4.1197% |

## Original top 12 candidate identities (selected after seeing 2024)

| Exact candidate ID | Historical n | Historical ROI | 2024 n | 2024 net U | 2024 ROI |
|---|---:|---:|---:|---:|---:|
| T12|quote_age,prob_sign,line|quote_age=3;prob_sign=1;line=1|underdog | 411 | 8.1861% | 437 | 24.115 | 5.5183% |
| T6|side_price,odds_spread|side_price=0;odds_spread=4|underdog | 345 | 7.5449% | 527 | 17.97 | 3.4099% |
| T6|line_quarter,price_gap_fine,line_move_quarter|line_quarter=1;price_gap_fine=3;line_move_quarter=0|home | 296 | 5.4932% | 194 | 17.29 | 8.9124% |
| T2|price_imbalance,line_change_size|price_imbalance=3;line_change_size=1|home | 308 | 9.9935% | 241 | 17.235 | 7.1515% |
| T2|line_quarter,side_price_fine,quote_age|line_quarter=6;side_price_fine=3;quote_age=0|away | 140 | 12.9179% | 80 | 16.72 | 20.9% |
| T6|kickoff_hour,quote_age|kickoff_hour=1;quote_age=3|away | 257 | 12.6012% | 92 | 16.645 | 18.0924% |
| T2|momentum,age|momentum=1;age=1|underdog | 346 | 5.8251% | 438 | 15.795 | 3.6062% |
| T24|book_overround,side_prob_change|book_overround=3;side_prob_change=3|favorite | 137 | 11.2409% | 85 | 15.035 | 17.6882% |
| T12|price,momentum|price=2;momentum=3|away | 239 | 9.5105% | 125 | 15.01 | 12.008% |
| T6|side_price|side_price=0|underdog | 365 | 7.7616% | 576 | 14.515 | 2.52% |
| T12|weekday,line,side_implied_prob|weekday=3;line=1;side_implied_prob=2|favorite | 62 | 8.8548% | 67 | 14.28 | 21.3134% |
| T2|line_quarter,side_price_fine,quote_age|line_quarter=0;side_price_fine=4;quote_age=0|favorite | 166 | 16.0% | 77 | 13.61 | 17.6753% |

## Limits
- The 208/top6/top12 sets are selected with 2024 outcomes; 2024 performance is selection-biased and NOT a forward test.
- Training 2019-2023 already used to select original 494; historical outcomes are in-sample.
- Every fixture counted once per portfolio; choose earliest eligible signal horizon and majority side at that horizon.
- When the selected candidate set changes, the earliest eligible horizon can change, so comparisons are not identical-order marginal contributions.
- Skip-opposite and margin2 are research descriptive alternative policies, not new user-approved production gates.
- Retrospective Crown quotes are not proven executable. No 2025-2026 or production changes.
