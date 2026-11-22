# R38 | Original R7 within shared leagues: market, horizon, quote and team presence

Original R7 27 candidate identities unchanged. Retrospective 2023 vs 2024 Crown historical AH results, 45 leagues present in both years. No 2025 results inspected.

## Matched league baseline

| Year | n | Net U | ROI |
|---|---:|---:|---:|
| 2023 | 883 | 42.78 | 4.8448% |
| 2024 | 1664 | 23.83 | 1.4321% |

## Within-league-by-category decompositions

Only league × category cells observed in both years enter each decomposition. Excluded cells are reported separately; each row uses a different matched population. The 2023-reference mix and within-category decomposition is descriptive, not causal.

| Category | Matched cells | 2023 n | 2023 ROI | 2024 n | 2024 ROI | Mix pp | Within pp | Excluded 2023 n | Excluded 2024 n |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| horizon | 150 | 878 | 5.3041% | 1587 | 1.0239% | 4.1875 | -8.4676 | 5 | 77 |
| line | 143 | 872 | 4.4243% | 1596 | 1.4073% | 3.1504 | -6.1675 | 11 | 68 |
| ticks | 143 | 875 | 5.0423% | 1594 | 2.0885% | 2.9675 | -5.9214 | 8 | 70 |
| odds | 178 | 874 | 4.9108% | 1550 | 2.0932% | 5.5783 | -8.3958 | 9 | 114 |
| side | 87 | 882 | 4.7551% | 1654 | 1.769% | 3.0315 | -6.0176 | 1 | 10 |

## Team presence overlap

- Unique (league_id,team_id) identities 2023: 586, 2024: 682; shared: 540.

| Scope | 2023 n | 2023 net U | 2023 ROI | 2024 n | 2024 net U | 2024 ROI |
|---|---:|---:|---:|---:|---:|---:|
| at_least_one_team_seen_both_years | 876 | 38.3 | 4.3721% | 1597 | 34.945 | 2.1882% |
| both_teams_seen_both_years | 784 | 54.165 | 6.9088% | 1164 | 2.875 | 0.247% |

## Interpretation

Within common league and quote/market bins, 2024 return remains lower in each displayed matched population. Matched both-teams-present cohort 2023 ROI +6.9088% (n784) vs 2024 +0.2470% (n1164), but matching presence does not establish identical team strength or conditions. This is not independent validation.

## Caveats
- All 2023-2024 historical Crown receipts are 2026 retrospective; these are not live-executable results.
- League-by-market cell decomposition excludes categories without observations in both years; compare coverage explicitly.
- Team matching means a team appeared in both years within the same league, not identical fixture, roster or strength.
- The 2024 sample has been repeatedly inspected; do not choose gates or filters using its favorable subgroups.
- No 2025-2026 data, no candidate definition or production changes.
