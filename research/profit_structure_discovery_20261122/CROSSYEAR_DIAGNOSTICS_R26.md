# R26 | Original 494 candidate train characteristics vs 2024

Research only: 494 definitions frozen using 2019-2023; 2024 is descriptive evaluation, not a candidate selection period.

## Historical characteristics of 2024 winners vs losers

| 2019-2023 feature | Median in 2024 profitable structures | Median in 2024 losing structures | Pearson vs 2024 candidate ROI |
|---|---:|---:|---:|
| train_n | 76.0 | 86.0 | -0.00504 |
| train_roi_pct | 14.81045 | 12.6245 | 0.05825 |
| train_year_roi_std | 12.207 | 13.29514 | 0.01216 |
| train_worst_year_roi | 3.7639 | 2.37555 | 0.029 |
| train_profit_largest_year_share | 0.3947 | 0.37418 | 0.0088 |
| train_month_positive_fraction | 0.6 | 0.59825 | 0.08514 |

## Historical quartiles compared with 2024

| Historical metric | Quartile low to high | 2024 positive definitions | Definitions | 2024 aggregate signal ROI |
|---|---|---:|---:|---:|
| train_n | 1 ([7, 42]) | 55 | 123 | -2.5816% |
| train_n | 2 ([42, 82]) | 54 | 124 | -2.271% |
| train_n | 3 ([82, 189]) | 53 | 123 | -1.9317% |
| train_n | 4 ([191, 1471]) | 46 | 124 | -2.7583% |
| train_roi_pct | 1 ([1.5428, 8.41]) | 38 | 123 | -3.3342% |
| train_roi_pct | 2 ([8.4386, 13.6805]) | 56 | 124 | -1.0691% |
| train_roi_pct | 3 ([13.7079, 21.1154]) | 60 | 123 | -1.5177% |
| train_roi_pct | 4 ([21.1364, 83.25]) | 54 | 124 | -1.942% |
| train_year_roi_std | 1 ([0.9208, 7.2649]) | 44 | 123 | -3.0615% |
| train_year_roi_std | 2 ([7.3044, 12.5664]) | 65 | 124 | -0.6461% |
| train_year_roi_std | 3 ([12.6604, 23.394]) | 48 | 123 | -2.5949% |
| train_year_roi_std | 4 ([23.4109, 48.3157]) | 51 | 124 | -3.1263% |
| train_worst_year_roi | 1 ([0.013, 1.1797]) | 34 | 123 | -3.8561% |
| train_worst_year_roi | 2 ([1.1797, 2.9859]) | 48 | 124 | -2.5895% |
| train_worst_year_roi | 3 ([3.0, 6.0]) | 64 | 123 | -0.174% |
| train_worst_year_roi | 4 ([6.0, 56.0]) | 62 | 124 | -1.1911% |
| train_profit_largest_year_share | 1 ([0.2219, 0.3315]) | 49 | 123 | -2.4222% |
| train_profit_largest_year_share | 2 ([0.3321, 0.3849]) | 42 | 124 | -4.2738% |
| train_profit_largest_year_share | 3 ([0.3849, 0.4636]) | 69 | 123 | -1.4193% |
| train_profit_largest_year_share | 4 ([0.464, 0.8489]) | 48 | 124 | -2.2456% |
| train_month_positive_fraction | 1 ([0.3902, 0.5472]) | 46 | 123 | -3.6194% |
| train_month_positive_fraction | 2 ([0.5476, 0.6]) | 55 | 124 | -1.9375% |
| train_month_positive_fraction | 3 ([0.6, 0.6545]) | 51 | 123 | -2.4378% |
| train_month_positive_fraction | 4 ([0.6571, 1.0]) | 56 | 124 | -1.8884% |

## Original structure family / horizon / direction

| Dimension | Value | Definitions | Profitable | 2024 signal n | 2024 aggregate signal ROI |
|---|---|---:|---:|---:|---:|
| batch | R11 | 40 | 17 | 5460 | -1.6484% |
| batch | R12 | 85 | 33 | 12755 | -3.6746% |
| batch | R13 | 42 | 16 | 5419 | -3.389% |
| batch | R14 | 80 | 42 | 8850 | -2.6637% |
| batch | R15 | 159 | 67 | 14988 | -1.6161% |
| batch | R7 | 27 | 13 | 2917 | 0.3528% |
| batch | R9 | 61 | 20 | 7802 | -3.3092% |
| horizon | T12 | 131 | 51 | 13165 | -2.7362% |
| horizon | T2 | 131 | 50 | 19278 | -2.6605% |
| horizon | T24 | 107 | 52 | 5448 | -1.954% |
| horizon | T6 | 125 | 55 | 20300 | -2.407% |
| direction | away | 129 | 60 | 12339 | -0.9932% |
| direction | favorite | 101 | 39 | 14981 | -2.9834% |
| direction | home | 109 | 45 | 9379 | -3.2777% |
| direction | underdog | 155 | 64 | 21492 | -2.7511% |
| feature_presence | age | 7 | 3 | 1898 | -0.7719% |
| feature_presence | book_overround | 7 | 3 | 854 | -2.01% |
| feature_presence | calendar_month | 15 | 9 | 3500 | -3.3601% |
| feature_presence | kickoff_hour | 22 | 10 | 2783 | -2.3626% |
| feature_presence | line | 153 | 64 | 12151 | -2.2742% |
| feature_presence | line_change_size | 9 | 5 | 1451 | -1.4628% |
| feature_presence | line_delta_sign | 11 | 4 | 1929 | -2.557% |
| feature_presence | line_move_quarter | 38 | 15 | 3364 | -3.9826% |
| feature_presence | line_quarter | 135 | 57 | 11883 | -1.3903% |
| feature_presence | momentum | 36 | 14 | 3743 | -0.9204% |
| feature_presence | odds_spread | 24 | 8 | 2513 | -2.4341% |
| feature_presence | price | 18 | 10 | 1892 | 1.0238% |
| feature_presence | price_gap_fine | 34 | 14 | 3098 | -3.139% |
| feature_presence | price_imbalance | 21 | 7 | 4331 | -4.9379% |
| feature_presence | prob_delta | 50 | 18 | 6349 | -3.1005% |
| feature_presence | prob_magnitude | 32 | 18 | 3401 | -0.6682% |
| feature_presence | prob_sign | 112 | 50 | 13149 | -2.272% |
| feature_presence | quote_age | 89 | 29 | 10288 | -3.6898% |
| feature_presence | side_implied_prob | 56 | 26 | 5723 | -3.474% |
| feature_presence | side_price | 99 | 50 | 15278 | -2.1571% |
| feature_presence | side_price_fine | 104 | 46 | 8015 | -0.3044% |
| feature_presence | side_prob_change | 50 | 20 | 5993 | -3.4836% |
| feature_presence | signed_line | 64 | 26 | 5703 | -3.8425% |
| feature_presence | weekday | 46 | 23 | 2956 | -2.1062% |

## Findings and limits

- Historical candidate ROI correlation with 2024 candidate ROI is close to zero (Pearson +0.05825); no simple monotonic relationship emerges from training ROI quartiles.
- Historical sample count, annual ROI standard deviation, worst year, annual profit concentration and positive-month fraction show weak linear correlations with 2024 candidate ROI.
- R7 original batch has a slightly positive aggregate signal result, but it is not a fixture-deduplicated tradable portfolio; this is an observation, not a validated winning strategy.
- Feature groups and candidate signals overlap, so aggregate group net U is not additive and group associations are not causal.
- The historical Crown ledger lacks league metadata, so league-specific attribution requires a separately verified fixture-to-league mapping. Do not invent league classifications.
- 2024 winners are known after observing 2024, and cannot be treated as a 2024 holdout-selected strategy. 2025-2026 remain unused; no production changes.

