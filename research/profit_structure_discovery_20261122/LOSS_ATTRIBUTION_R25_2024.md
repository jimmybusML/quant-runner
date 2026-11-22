# R25 | 2024 original candidate survival and loss attribution

494 fixed original definitions from 2019-2023; 2024 not used for candidate selection.

## Candidate outcomes
{'total': 494, 'positive': 208, 'negative': 286, 'zero': 0, 'no_2024_signals': 0}

## Research batches
{'R11': {'definitions': 40, 'positive': 17, 'negative': 23, 'zero': 0, 'aggregate_signal_occurrences': 5460, 'aggregate_net_U': -90.0}, 'R12': {'definitions': 85, 'positive': 33, 'negative': 52, 'zero': 0, 'aggregate_signal_occurrences': 12755, 'aggregate_net_U': -468.695}, 'R13': {'definitions': 42, 'positive': 16, 'negative': 26, 'zero': 0, 'aggregate_signal_occurrences': 5419, 'aggregate_net_U': -183.65}, 'R14': {'definitions': 80, 'positive': 42, 'negative': 38, 'zero': 0, 'aggregate_signal_occurrences': 8850, 'aggregate_net_U': -235.74}, 'R15': {'definitions': 159, 'positive': 67, 'negative': 92, 'zero': 0, 'aggregate_signal_occurrences': 14988, 'aggregate_net_U': -242.22}, 'R7': {'definitions': 27, 'positive': 13, 'negative': 14, 'zero': 0, 'aggregate_signal_occurrences': 2917, 'aggregate_net_U': 10.29}, 'R9': {'definitions': 61, 'positive': 20, 'negative': 41, 'zero': 0, 'aggregate_signal_occurrences': 7802, 'aggregate_net_U': -258.18}}

## Original structures profitable in 2024 (post-hoc descriptive only)
('T12|quote_age,prob_sign,line|quote_age=3;prob_sign=1;line=1|underdog', {'n': 437, 'net_U': 24.115, 'roi_pct': 5.5183})
('T6|side_price,odds_spread|side_price=0;odds_spread=4|underdog', {'n': 527, 'net_U': 17.97, 'roi_pct': 3.4099})
('T6|line_quarter,price_gap_fine,line_move_quarter|line_quarter=1;price_gap_fine=3;line_move_quarter=0|home', {'n': 194, 'net_U': 17.29, 'roi_pct': 8.9124})
('T2|price_imbalance,line_change_size|price_imbalance=3;line_change_size=1|home', {'n': 241, 'net_U': 17.235, 'roi_pct': 7.1515})
('T2|line_quarter,side_price_fine,quote_age|line_quarter=6;side_price_fine=3;quote_age=0|away', {'n': 80, 'net_U': 16.72, 'roi_pct': 20.9})
('T6|kickoff_hour,quote_age|kickoff_hour=1;quote_age=3|away', {'n': 92, 'net_U': 16.645, 'roi_pct': 18.0924})
('T2|momentum,age|momentum=1;age=1|underdog', {'n': 438, 'net_U': 15.795, 'roi_pct': 3.6062})
('T24|book_overround,side_prob_change|book_overround=3;side_prob_change=3|favorite', {'n': 85, 'net_U': 15.035, 'roi_pct': 17.6882})
('T12|price,momentum|price=2;momentum=3|away', {'n': 125, 'net_U': 15.01, 'roi_pct': 12.008})
('T6|side_price|side_price=0|underdog', {'n': 576, 'net_U': 14.515, 'roi_pct': 2.52})
('T12|weekday,line,side_implied_prob|weekday=3;line=1;side_implied_prob=2|favorite', {'n': 67, 'net_U': 14.28, 'roi_pct': 21.3134})
('T2|line_quarter,side_price_fine,quote_age|line_quarter=0;side_price_fine=4;quote_age=0|favorite', {'n': 77, 'net_U': 13.61, 'roi_pct': 17.6753})
('T12|side_price_fine,prob_sign|side_price_fine=1;prob_sign=0|favorite', {'n': 275, 'net_U': 13.365, 'roi_pct': 4.86})
('T6|prob_sign,side_price|prob_sign=0;side_price=0|underdog', {'n': 305, 'net_U': 12.405, 'roi_pct': 4.0672})
('T6|side_prob_change,side_price|side_prob_change=3;side_price=0|underdog', {'n': 176, 'net_U': 12.105, 'roi_pct': 6.8778})
('T24|line,price,momentum|line=3;price=1;momentum=2|underdog', {'n': 165, 'net_U': 11.83, 'roi_pct': 7.1697})
('T12|side_implied_prob,quote_age|side_implied_prob=1;quote_age=4|home', {'n': 104, 'net_U': 11.78, 'roi_pct': 11.3269})
('T12|weekday,line,side_implied_prob|weekday=0;line=3;side_implied_prob=2|favorite', {'n': 45, 'net_U': 11.715, 'roi_pct': 26.0333})
('T12|line_quarter,price_gap_fine|line_quarter=2;price_gap_fine=3|favorite', {'n': 191, 'net_U': 11.55, 'roi_pct': 6.0471})
('T24|side_prob_change,line|side_prob_change=3;line=3|underdog', {'n': 72, 'net_U': 11.425, 'roi_pct': 15.8681})

## Original structures with largest 2024 losses
('T12|quote_age,side_price|quote_age=3;side_price=2|home', {'n': 788, 'net_U': -73.69, 'roi_pct': -9.3515})
('T2|side_price,prob_delta|side_price=2;prob_delta=1|favorite', {'n': 903, 'net_U': -54.965, 'roi_pct': -6.0869})
('T6|calendar_month,side_prob_change|calendar_month=1;side_prob_change=2|favorite', {'n': 688, 'net_U': -51.325, 'roi_pct': -7.46})
('T24|side_implied_prob,prob_sign|side_implied_prob=2;prob_sign=1|underdog', {'n': 778, 'net_U': -50.625, 'roi_pct': -6.5071})
('T6|kickoff_hour,quote_age|kickoff_hour=4;quote_age=2|favorite', {'n': 1109, 'net_U': -49.65, 'roi_pct': -4.477})
('T6|side_implied_prob,side_prob_change|side_implied_prob=2;side_prob_change=4|underdog', {'n': 230, 'net_U': -49.135, 'roi_pct': -21.363})
('T6|quote_age,price_imbalance|quote_age=2;price_imbalance=1|home', {'n': 407, 'net_U': -47.185, 'roi_pct': -11.5934})
('T6|quote_age,price_imbalance|quote_age=2;price_imbalance=1|favorite', {'n': 407, 'net_U': -44.89, 'roi_pct': -11.0295})
('T2|line_quarter,side_prob_change|line_quarter=4;side_prob_change=1|underdog', {'n': 221, 'net_U': -37.92, 'roi_pct': -17.1584})
('T6|quote_age,price_imbalance|quote_age=2;price_imbalance=4|home', {'n': 424, 'net_U': -37.915, 'roi_pct': -8.9422})
('T6|quote_age,prob_sign|quote_age=3;prob_sign=1|underdog', {'n': 272, 'net_U': -36.265, 'roi_pct': -13.3327})
('T12|line_change_size,prob_sign|line_change_size=1;prob_sign=2|away', {'n': 417, 'net_U': -33.7, 'roi_pct': -8.0815})
('T2|price_imbalance,signed_line|price_imbalance=2;signed_line=2|home', {'n': 225, 'net_U': -32.36, 'roi_pct': -14.3822})
('T2|price_imbalance,signed_line|price_imbalance=2;signed_line=2|favorite', {'n': 225, 'net_U': -32.36, 'roi_pct': -14.3822})
('T2|side_price,prob_sign,line_delta_sign|side_price=1;prob_sign=2;line_delta_sign=1|underdog', {'n': 752, 'net_U': -31.495, 'roi_pct': -4.1882})
('T2|side_price,momentum,prob_delta|side_price=2;momentum=2;prob_delta=1|favorite', {'n': 717, 'net_U': -30.9, 'roi_pct': -4.3096})
('T24|weekday,line,side_implied_prob|weekday=6;line=1;side_implied_prob=3|underdog', {'n': 199, 'net_U': -29.845, 'roi_pct': -14.9975})
('T12|calendar_month,signed_line|calendar_month=1;signed_line=3|favorite', {'n': 572, 'net_U': -29.59, 'roi_pct': -5.1731})
('T2|calendar_month,side_price|calendar_month=5;side_price=1|underdog', {'n': 477, 'net_U': -27.35, 'roi_pct': -5.7338})
('T12|kickoff_hour,line,prob_sign|kickoff_hour=3;line=3;prob_sign=1|favorite', {'n': 196, 'net_U': -26.535, 'roi_pct': -13.5383})

## Historical ROI quartiles vs 2024
{'1': {'definitions': 123, 'test_positive': 38, 'signal_occurrences': 34500, 'test_net_U': -1150.305, 'test_roi_pct': -3.3342, 'train_roi_range': [1.5428, 8.41]}, '2': {'definitions': 124, 'test_positive': 56, 'signal_occurrences': 12468, 'test_net_U': -133.3, 'test_roi_pct': -1.0691, 'train_roi_range': [8.4386, 13.6805]}, '3': {'definitions': 123, 'test_positive': 60, 'signal_occurrences': 7862, 'test_net_U': -119.32, 'test_roi_pct': -1.5177, 'train_roi_range': [13.7079, 21.1154]}, '4': {'definitions': 124, 'test_positive': 54, 'signal_occurrences': 3361, 'test_net_U': -65.27, 'test_roi_pct': -1.942, 'train_roi_range': [21.1364, 83.25]}}

## Fixed earliest equal-net portfolio loss segmentation
('conflict:both_sides', {'n': 1243, 'net_U': -89.005, 'roi_pct': -7.1605})
('conflict:one_side', {'n': 7982, 'net_U': -217.73, 'roi_pct': -2.7278})
('direction:away', {'n': 4538, 'net_U': -108.225, 'roi_pct': -2.3849})
('direction:home', {'n': 4687, 'net_U': -198.51, 'roi_pct': -4.2353})
('horizon:T12', {'n': 4066, 'net_U': -90.11, 'roi_pct': -2.2162})
('horizon:T2', {'n': 867, 'net_U': -51.705, 'roi_pct': -5.9637})
('horizon:T24', {'n': 2392, 'net_U': -94.405, 'roi_pct': -3.9467})
('horizon:T6', {'n': 1900, 'net_U': -70.515, 'roi_pct': -3.7113})
('margin:1', {'n': 5425, 'net_U': -219.36, 'roi_pct': -4.0435})
('margin:2', {'n': 2007, 'net_U': -33.36, 'roi_pct': -1.6622})
('margin:3', {'n': 799, 'net_U': -34.605, 'roi_pct': -4.331})
('margin:4', {'n': 384, 'net_U': -16.31, 'roi_pct': -4.2474})
('margin:5', {'n': 610, 'net_U': -3.1, 'roi_pct': -0.5082})
('month:2024-01', {'n': 462, 'net_U': 1.525, 'roi_pct': 0.3301})
('month:2024-02', {'n': 777, 'net_U': -21.575, 'roi_pct': -2.7767})
('month:2024-03', {'n': 903, 'net_U': 3.56, 'roi_pct': 0.3942})
('month:2024-04', {'n': 1167, 'net_U': -61.015, 'roi_pct': -5.2284})
('month:2024-05', {'n': 1064, 'net_U': -41.935, 'roi_pct': -3.9413})
('month:2024-06', {'n': 270, 'net_U': -32.175, 'roi_pct': -11.9167})
('month:2024-07', {'n': 376, 'net_U': -18.815, 'roi_pct': -5.004})
('month:2024-08', {'n': 915, 'net_U': 6.285, 'roi_pct': 0.6869})
('month:2024-09', {'n': 956, 'net_U': -20.185, 'roi_pct': -2.1114})
('month:2024-10', {'n': 830, 'net_U': -33.01, 'roi_pct': -3.9771})
('month:2024-11', {'n': 828, 'net_U': -60.495, 'roi_pct': -7.3062})
('month:2024-12', {'n': 677, 'net_U': -28.9, 'roi_pct': -4.2688})

## Interpretation
Individual candidate returns overlap by fixture and quote horizon and are not additive portfolio PnL. 2024 profitable candidates cannot be retrospectively selected as a held-out winning portfolio. Crown event-time quotes were retrospectively collected; actual executable prices unverified. No 2025-2026 or production changes.
