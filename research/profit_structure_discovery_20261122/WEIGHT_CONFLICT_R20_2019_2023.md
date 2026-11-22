# R20 | Weighting and conflict resolution, 2019-2023

Research only: 494 R7-R15 historical Crown AH candidate definitions, already selected for positive net U in all five years. This creates selection leakage.

## Fixture-level: one historical signal-bearing quote horizon per fixture

| Horizon | Weights | Conflict | Orders | Net U | ROI | MDD U | 2019 U | 2020 U | 2021 U | 2022 U | 2023 U |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| earliest_quote | equal | skip_conflict | 11678 | 1049.77 | 8.9893% | 30.25 | 160.82 | 192.975 | 193.915 | 185.975 | 316.085 |
| earliest_quote | equal | net | 13137 | 1154.46 | 8.7879% | 32.955 | 188.215 | 213.945 | 214.805 | 194.565 | 342.93 |
| earliest_quote | equal | best | 14213 | 1119.495 | 7.8766% | 33.53 | 182.755 | 193.82 | 221.06 | 198.925 | 322.935 |
| earliest_quote | sample | skip_conflict | 11678 | 1049.77 | 8.9893% | 30.25 | 160.82 | 192.975 | 193.915 | 185.975 | 316.085 |
| earliest_quote | sample | net | 14191 | 1010.625 | 7.1216% | 33.335 | 176.285 | 183.905 | 173.305 | 182.33 | 294.8 |
| earliest_quote | sample | best | 14213 | 1008.15 | 7.0932% | 34.335 | 174.285 | 184.785 | 171.645 | 184.875 | 292.56 |
| earliest_quote | full_roi | skip_conflict | 11678 | 1049.77 | 8.9893% | 30.25 | 160.82 | 192.975 | 193.915 | 185.975 | 316.085 |
| earliest_quote | full_roi | net | 14213 | 1219.205 | 8.5781% | 38.85 | 199.285 | 206.235 | 227.755 | 209.545 | 376.385 |
| earliest_quote | full_roi | best | 14213 | 1219.205 | 8.5781% | 38.85 | 199.285 | 206.235 | 227.755 | 209.545 | 376.385 |
| earliest_quote | prior_roi | skip_conflict | 11678 | 1049.77 | 8.9893% | 30.25 | 160.82 | 192.975 | 193.915 | 185.975 | 316.085 |
| earliest_quote | prior_roi | net | 12714 | 1016.815 | 7.9976% | 32.01 | 0 | 229.675 | 245.465 | 197.11 | 344.565 |
| earliest_quote | prior_roi | best | 12714 | 1016.815 | 7.9976% | 32.01 | 0 | 229.675 | 245.465 | 197.11 | 344.565 |
| latest_quote | equal | skip_conflict | 11962 | 835.565 | 6.9852% | 30.16 | 163.725 | 135.745 | 211.005 | 133.86 | 191.23 |
| latest_quote | equal | net | 13410 | 888.38 | 6.6248% | 37.37 | 181.49 | 150.13 | 219.095 | 129.51 | 208.155 |
| latest_quote | equal | best | 14213 | 914.205 | 6.4322% | 35.225 | 182.28 | 144.915 | 240.855 | 129.795 | 216.36 |
| latest_quote | sample | skip_conflict | 11962 | 835.565 | 6.9852% | 30.16 | 163.725 | 135.745 | 211.005 | 133.86 | 191.23 |
| latest_quote | sample | net | 14202 | 842.3 | 5.9309% | 38.14 | 165.795 | 141.535 | 234.73 | 122.825 | 177.415 |
| latest_quote | sample | best | 14213 | 844.5 | 5.9417% | 38.14 | 166.695 | 141.435 | 235.51 | 124.445 | 176.415 |
| latest_quote | full_roi | skip_conflict | 11962 | 835.565 | 6.9852% | 30.16 | 163.725 | 135.745 | 211.005 | 133.86 | 191.23 |
| latest_quote | full_roi | net | 14213 | 929.28 | 6.5382% | 39.02 | 189.485 | 153.56 | 213.705 | 129.87 | 242.66 |
| latest_quote | full_roi | best | 14213 | 929.28 | 6.5382% | 39.02 | 189.485 | 153.56 | 213.705 | 129.87 | 242.66 |
| latest_quote | prior_roi | skip_conflict | 11962 | 835.565 | 6.9852% | 30.16 | 163.725 | 135.745 | 211.005 | 133.86 | 191.23 |
| latest_quote | prior_roi | net | 12714 | 693.655 | 5.4558% | 39.88 | 0 | 143.925 | 215.79 | 118.725 | 215.215 |
| latest_quote | prior_roi | best | 12714 | 693.655 | 5.4558% | 39.88 | 0 | 143.925 | 215.79 | 118.725 | 215.215 |

## Same-horizon comparisons (may repeat fixture across horizons)

| Weights | Conflict | Orders | Net U | ROI | MDD U |
|---|---|---:|---:|---:|---:|
| equal | both | 39646 | 1925.295 | 4.8562% | 50.465 |
| equal | skip_conflict | 26760 | 2270.05 | 8.483% | 47.18 |
| equal | net | 30719 | 2537.415 | 8.2601% | 43.61 |
| equal | best | 33203 | 2547.78 | 7.6733% | 41.165 |
| sample | both | 39646 | 1925.295 | 4.8562% | 50.465 |
| sample | skip_conflict | 26760 | 2270.05 | 8.483% | 47.18 |
| sample | net | 33157 | 2224.695 | 6.7096% | 46.475 |
| sample | best | 33203 | 2226.27 | 6.705% | 47.475 |
| full_roi | both | 39646 | 1925.295 | 4.8562% | 50.465 |
| full_roi | skip_conflict | 26760 | 2270.05 | 8.483% | 47.18 |
| full_roi | net | 33203 | 2651.72 | 7.9864% | 42.89 |
| full_roi | best | 33203 | 2651.72 | 7.9864% | 42.89 |
| prior_roi | both | 39646 | 1925.295 | 4.8562% | 50.465 |
| prior_roi | skip_conflict | 26760 | 2270.05 | 8.483% | 47.18 |
| prior_roi | net | 29668 | 2131.865 | 7.1857% | 45.69 |
| prior_roi | best | 29668 | 2131.865 | 7.1857% | 45.69 |

## Limitations

- 33,203 fixture-horizon groups, 18,608 multi-signal groups, 6,443 opposite-side conflicts.
- Same physical side duplicates become one 1U order; definitions may be correlated and not independent votes.
- Conflict skip means abstain when both sides appear; net means compare summed signal weights and abstain on ties; best has an arbitrary home-side tie break.
- Equal weight=1 per candidate; sample weight=square root of five-year sample count; full ROI uses five-year candidate ROI; prior ROI uses earlier-year ROI but candidates were already selected using all years.
- Earliest signal-bearing horizon chooses maximum T hours, latest chooses minimum T hours. These are alternatives, not user-approved production restrictions.
- Weights only choose direction; this is not optimized capital allocation or bet sizing.
- 494 R7-R15 candidates are included; the full R17/R18 survivor universes are not reconstructed, so this is a partial universe.
- The same years were used for selecting candidates and evaluating policies. No independent out-of-sample evidence or executable historical quote proof.
- No 2024-2026 outcomes used; M8 and production unchanged.
