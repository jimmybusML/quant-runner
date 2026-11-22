# R35 | R7 original signal attribution and quote-capture diagnostics, 2023 vs 2024

Original R7 27 candidates, fixture-deduplicated earliest eligible horizon, equal-net vote. Winning-side candidate IDs share each order PnL equally, so exposure and net U sum to portfolio results. These are accounting attributions, NOT independent tradable candidate performance.

## Quote metadata and ledger coverage

| Metric | 2023 | 2024 |
|---|---:|---:|
| total_AH_ledger_rows | 18792 | 33603 |
| portfolio_quote_time_equals_first_pct | 11.199 | 9.524 |
| portfolio_reference_quote_available_pct | 100.0 | 100.0 |
| portfolio_ticks_mean | 13.327 | 14.553 |
| portfolio_ticks_median | 8.0 | 10.0 |
| portfolio_actual_hours_mean | 11.504 | 10.669 |
| portfolio_actual_hours_median | 12.068 | 8.662 |
| ledger_first_quote_nonmissing_pct | 100.0 | 100.0 |
| ledger_reference_quote_nonmissing_pct | 100.0 | 100.0 |

## Candidate identity return decomposition

| Mix shift (pp) | Within-candidate change (pp) | Total (pp) |
|---:|---:|---:|
| -0.5313 | -3.1863 | -3.7176 |

## All 27 original candidate identities and fractional portfolio attribution

| Candidate ID | 2023 fractional exposure | 2023 allocated net U | 2023 allocated ROI | 2024 fractional exposure | 2024 allocated net U | 2024 allocated ROI |
|---|---:|---:|---:|---:|---:|---:|
| T12|momentum,age|momentum=3;age=2|underdog | 58.6667 | 9.7933 | 16.6932% | 77.5 | -2.085 | -2.6903% |
| T12|line,age|line=2;age=4|underdog | 34.0 | 1.58 | 4.6471% | 63.0 | -7.81 | -12.3968% |
| T2|line,price,momentum|line=3;price=3;momentum=3|away | 5.0 | 0.05 | 1.0% | 27.0 | -7.445 | -27.5741% |
| T12|line,price,momentum|line=2;price=1;momentum=3|favorite | 25.0 | 3.005 | 12.02% | 38.5 | -2.4825 | -6.4481% |
| T2|line,price,momentum|line=2;price=4;momentum=2|favorite | 13.0 | 1.73 | 13.3077% | 21.0 | -2.27 | -10.8095% |
| T24|line,momentum|line=0;momentum=1|away | 5.0 | 1.24 | 24.8% | 6.0 | -1.795 | -29.9167% |
| T24|line,momentum|line=0;momentum=1|favorite | 5.0 | 1.24 | 24.8% | 6.0 | -1.795 | -29.9167% |
| T12|momentum|momentum=4|favorite | 2.5 | -0.19 | -7.6% | 3.5 | -2.58 | -73.7143% |
| T6|price,momentum|price=1;momentum=4|favorite | 5.0 | 0.775 | 15.5% | 11.0 | -1.515 | -13.7727% |
| T6|price|price=4|underdog | 44.3333 | 2.7279 | 6.1532% | 116.9167 | 0.5408 | 0.4626% |
| T6|price,momentum|price=4;momentum=2|underdog | 40.0833 | 1.4267 | 3.5593% | 100.0833 | -0.6858 | -0.6853% |
| T6|line,price|line=1;price=4|away | 16.5 | 1.5663 | 9.4924% | 31.0833 | -0.5258 | -1.6917% |
| T12|price,momentum|price=1;momentum=4|favorite | 1.0 | 0.44 | 44.0% | 1.5 | -0.58 | -38.6667% |
| T6|price,momentum|price=4;momentum=1|away | 4.25 | 1.3013 | 30.6176% | 5.5 | 0.43 | 7.8182% |
| T6|line,price|line=1;price=4|underdog | 20.8333 | 0.4479 | 2.15% | 38.4167 | 0.1758 | 0.4577% |
| T6|momentum,age|momentum=4;age=0|home | 5.0 | 0.56 | 11.2% | 8.0 | 0.72 | 9.0% |
| T6|price,momentum|price=2;momentum=4|home | 1.0 | -0.015 | -1.5% | 2.0 | 0.175 | 8.75% |
| T2|line,price,momentum|line=2;price=2;momentum=1|favorite | 55.0 | 1.335 | 2.4273% | 115.0 | 1.615 | 1.4043% |
| T12|line,age|line=0;age=0|favorite | 142.0 | 5.75 | 4.0493% | 222.5 | 6.46 | 2.9034% |
| T12|line,price,momentum|line=0;price=0;momentum=3|away | 2.6667 | -0.0617 | -2.3125% | 10.5 | 1.23 | 11.7143% |
| T12|line,price,momentum|line=0;price=0;momentum=3|underdog | 2.6667 | -0.0617 | -2.3125% | 10.5 | 1.23 | 11.7143% |
| T24|line,price|line=3;price=1|underdog | 65.0 | 0.6875 | 1.0577% | 105.5 | 1.98 | 1.8768% |
| T2|line,price|line=4;price=3|underdog | 32.5 | 2.6 | 8.0% | 63.5 | 4.125 | 6.4961% |
| T12|price,momentum|price=2;momentum=3|away | 44.5 | 4.345 | 9.764% | 90.0 | 6.425 | 7.1389% |
| T24|line,price,momentum|line=3;price=1;momentum=2|underdog | 49.0 | 3.1575 | 6.4439% | 82.5 | 5.915 | 7.1697% |
| T12|line,momentum|line=2;momentum=3|favorite | 34.0 | -0.825 | -2.4265% | 53.5 | 2.0275 | 3.7897% |
| T2|momentum,age|momentum=1;age=1|underdog | 170.5 | -0.705 | -0.4135% | 369.5 | 19.495 | 5.276% |

## Interpretation

- R7 ROI 2023 +4.9661% n884 versus 2024 +1.2485% n1680, change -3.7176pp. Candidate mix accounts for -0.5313pp and within-candidate return for -3.1863pp, under 2023-reference fractional attribution.
- Portfolio quote tick median 2023 8, 2024 10; quote tick mean 13.327 vs 14.553. Ledger first and same-line reference quote fields are populated for 100% of 2023 and 2024 AH ledger rows. This shows metadata completeness, NOT comparability of collection density or real-time availability.
- Portfolio mean actual hours before kickoff 2023 11.504, 2024 10.669; median 12.068 vs 8.662. Further inspect fixture/league universe and capture pipeline before causal conclusions.

## Caveats
- Equal fractional PnL allocation among winning-side candidate IDs is an accounting attribution, not independent candidate betting PnL or causal influence.
- 2023 vs 2024 candidate mix decomposition uses 2023 reference returns; all original candidate identities remain fixed.
- Quote metadata is from retrospectively collected Crown ledger, not proof that these quote histories existed in live 2023/2024 systems.
- Different years may have different league/fixture coverage, not controlled without a fixture-league map.
- 2019-2023 original R7 in-sample; 2024 repeatedly inspected; no untouched independent validation.
- No 2025-2026 or production changes, no new strategy filters.
