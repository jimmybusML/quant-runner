# R36 | Crown 2023-2024 retrospective archive provenance and coverage audit

This audit reads the exact R7-R35 source ledger and its accompanying build report, without altering candidate definitions, rules or production.

## Source provenance

- Source: /Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl
- SHA256: 0a8dc0232f0dfb07f408183dbf799803bb0f7e85a40c0e7243df551d8de64a72
- Build report protocol: T30_TO_T2_FIXED_ENTRY_HORIZON_MOVEMENT_V1
- Build report entry policy: for each fixed T-h, latest archived Crown quote available by that cutoff and no earlier than T-30; no quote by cutoff means no order at that cutoff

## Year comparison

| Field | 2023 | 2024 |
|---|---:|---:|
| AH_rows | 18792 | 33603 |
| unique_fixtures | 5828 | 10581 |
| unique_fixture_months | 12 | 12 |
| first_quote_populated_pct | 100.0 | 100.0 |
| first_quote_received_after_match_year_pct | 100.0 | 100.0 |
| source_sha_populated_pct | 100.0 | 100.0 |
| distinct_source_sha | 5828 | 10581 |
| first_quote_equals_selected_quote_pct | 13.128 | 12.954 |
| ticks_mean | 14.649 | 13.207 |
| ticks_median | 8.0 | 8 |
| actual_hours_mean | 10.292 | 10.229 |
| actual_hours_median | 6.977778 | 7.155 |
| selected_quote_hours_before_kickoff_median | 6.978 | 7.155 |
| league_missing_pct | 100.0 | 100.0 |

## 2023 detail

- Horizon row counts: {"2": 5828, "12": 5141, "6": 5740, "24": 2083}
- Horizon coverage per fixture: {"1": 88, "3": 3058, "4": 2083, "2": 599}
- First quote received years: {"2026": 18792}
- First quote source layers: {"movement": 18792}
- First quote reference prefixes: {"asian_list": 18792}
- First quote received days: {"2026-11-10": 18729, "2026-11-13": 63}
- Rows per kickoff month: {"2023-01": 802, "2023-02": 890, "2023-03": 680, "2023-04": 1202, "2023-05": 1123, "2023-06": 303, "2023-07": 173, "2023-08": 2617, "2023-09": 2483, "2023-10": 3057, "2023-11": 2495, "2023-12": 2967}

## 2024 detail

- Horizon row counts: {"24": 3590, "12": 9121, "6": 10311, "2": 10581}
- Horizon coverage per fixture: {"4": 3590, "3": 5531, "2": 1190, "1": 270}
- First quote received years: {"2026": 33603}
- First quote source layers: {"movement": 33603}
- First quote reference prefixes: {"asian_list": 33603}
- First quote received days: {"2026-11-10": 9226, "2026-11-13": 174, "2026-11-11": 24203}
- Rows per kickoff month: {"2024-01": 1786, "2024-02": 2893, "2024-03": 3173, "2024-04": 4208, "2024-05": 3935, "2024-06": 960, "2024-07": 1426, "2024-08": 3324, "2024-09": 3464, "2024-10": 2971, "2024-11": 3011, "2024-12": 2452}

## Interpretation

- Every 2023 and 2024 AH ledger row has first-quote received year 2026, and first quote layer movement / ref asian_list. This is retrospective ingestion, not a 2023/2024 live receipt.
- 2023 covers 5828 fixtures and 2024 covers 10581 fixtures; this is a major universe expansion and cannot be equated with equivalent league mix.
- 2023/2024 metadata formats appear aligned, but this alone cannot verify identical historical API coverage or sampling behavior.
- 100% of these AH ledger rows lack a league field, so league-level matched comparison needs an external fixture-league mapping.
- R35 R7 ROI 2023 +4.9661% vs 2024 +1.2485% remains a historical simulation, not an executable production claim.
- Do not use the coverage audit to add a gate or alter candidate selection.

## Caveats
- The received timestamp is a 2026 retrospective ingestion timestamp, not a historical 2023/2024 pregame receipt.
- Archive event-time quotes are not proof of live historical accessibility or executability.
- The report entry policy is a retrospective quote selection procedure and must not be confused with live reception.
- No fixture-league mapping in this feature ledger, so league mix cannot be compared here.
- Different match/fixture coverage or source availability may confound 2023-2024 ROI; this audit does not estimate causality.
- No new strategy gates, production changes or 2025-2026 outcomes.
