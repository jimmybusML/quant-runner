# M8 squad market value × Crown AH study (2026-11-20)

## Conclusion

**No independent profitable expansion was found.** All 4,275 out-of-eight unique candidate FIDs lost under each fixed model. Crown+value lost 179.985U (−4.210%), worse than Crown-only on the same fixtures (−42.370U, −0.991%). The value-only model lost 166.610U (−3.897%). This is a retrospective historical Crown event-time replay. The available player-value archive is truncated and ends in 2024, while appearance history ends in June 2026; it does not prove when valuations or reconstructed rosters were published or received. Actual receipt profitability is therefore unavailable.

The frozen original eight remained unchanged. No M8/M9/M1/MR1 production, Telegram, formal ledger, collector or schedule changes were made.

## Hypothesis and data

- New mechanism: a prior-appearance-based squad proxy measured from player market values may identify strength or depth information not fully reflected in Crown AH prices. This differs from the previous score/Elo, shots/possession, lineup repetition/load and transfer-activity studies by measuring accumulated player valuation rather than match outcomes or workload.
- Historical training/test source: 38,846 paired Crown T24/T12 FIDs across 48 Crown leagues. The reused, audited crosswalk covers 25 Transfermarkt competitions and 453 Crown clubs. Only cases with both teams mapped and a usable estimated squad-value feature were modeled.
- The original cross-league expansion’s 15 league IDs were checked directly: paired Crown T24/T12 inventory overlap 0 FIDs; mapped Transfermarkt club crosswalk overlap 0 leagues. Therefore this mechanism was not evaluated in any of the new 15 leagues; no result below should be extrapolated to them.
- Feature rows: 10,850; missing/omitted coverage: {"team_mapping_missing": 19494, "one_or_both_team_value_unavailable": 4916, "appearance_history_does_not_reach_feature_cutoff": 3586}. Test feature IDs: 5,369, including 1,094 frozen-eight overlaps and 4,275 unique new candidates.
- Test rows by year: {"2024": 1985, "2025": 2192, "2026": 1192}; target date range 2024-01-01 to 2026-05-24. The mapped-team appearances source ends 2026-05-24; later targets are excluded when the fixed three-day pre-match feature cutoff would exceed that source coverage.
- The locally saved `player_valuations.csv.gz` fails gzip EOF/CRC. The script salvages 589,239 newline-terminated complete records, excludes the incomplete final record, and uses only dated values at least 30 days before each target. Newest complete value date: 2024-12-27; no valuation publication/receipt timestamps are present.
- A squad proxy includes players with a mapped-team appearance in the prior 365 days whose latest pre-cutoff appearance across mapped clubs remains with that team. It is not the target lineup, a verified roster, or a contemporaneous roster snapshot. Valuation age is retained as a feature and reported rather than filtered to improve ROI.
- Mean value ages (both teams) were 116.5 days in 2024, 227.5 days in 2025, and 471.7 days in the 2026 partial sample (maximum 627 days in 2026). The old valuation file makes later-year results a stale-value stress test, not a fresh current squad-value test.

## Fixed model design

- Target: home one-unit net AH payout minus away one-unit net AH payout at the paired Crown T12 AH contract. Quarter-handicap bets are independently split into equal half-line legs.
- Crown baseline uses Crown AH line, both decimal prices and price-derived variables. Squad-value features include top-11 and active-squad aggregate value, median/mean value, valued-player count, appearance-roster count, coverage, concentration and value age; model includes both home-away differences and sums.
- Fixed Ridge alpha=100, expanding-year folds. Test year Y uses only earlier calendar years; no target-year fitting, subgroup threshold search, league filter or ROI gate. Fold sample sizes:

| Test year | Prior-year training rows | Feature-eligible test rows |
|---|---:|---:|
| 2024 | 5,481 | 1,985 |
| 2025 | 7,466 | 2,192 |
| 2026 | 9,658 | 1,192 |

All model variants use the same FIDs. The lower-price side is a same-fixture descriptive benchmark; it is not a candidate rule.

## Unique out-of-eight performance

| Method | New unique FIDs | Net U | ROI | MDD U | ISO-week span | Mean orders/week | Active weeks |
|---|---:|---:|---:|---:|---:|---:|---:|
| Crown-only | 4,275 | -42.370 | -0.991% | +81.530 | 125 | 34.20 | 103 |
| Squad-value only | 4,275 | -166.610 | -3.897% | +174.190 | 125 | 34.20 | 103 |
| Crown + squad value | 4,275 | -179.985 | -4.210% | +189.140 | 125 | 34.20 | 103 |
| Lower-price side | 4,275 | -277.805 | -6.498% | +285.935 | 125 | 34.20 | 103 |

## Year-by-year

| Method | 2024 orders / net U / ROI | 2025 orders / net U / ROI | 2026 partial orders / net U / ROI |
|---|---:|---:|---:|
| Crown-only | 1,565 / -5.960 / -0.381% | 1,758 / -23.230 / -1.321% | 952 / -13.180 / -1.384% |
| Squad-value only | 1,565 / -45.670 / -2.918% | 1,758 / -32.870 / -1.870% | 952 / -88.070 / -9.251% |
| Crown + squad value | 1,565 / -37.850 / -2.419% | 1,758 / -60.890 / -3.464% | 952 / -81.245 / -8.534% |
| Lower-price side | 1,565 / -82.240 / -5.255% | 1,758 / -112.180 / -6.381% | 952 / -83.385 / -8.759% |

## Frozen-eight same-horizon combination

Frozen baseline over the 2024–2026 test period: 6,873 FIDs, +197.765U, ROI +2.877%. Each model adds only its unique out-of-eight FIDs.

| Method | Combined unique FIDs | Combined net U | Combined ROI | Change vs frozen baseline |
|---|---:|---:|---:|---:|
| Crown-only | 11,148 | +155.395 | +1.394% | -42.370U |
| Squad-value only | 11,148 | +31.155 | +0.279% | -166.610U |
| Crown + squad value | 11,148 | +17.780 | +0.159% | -179.985U |

## Annual estimate freshness and receipt audit

The genuine Crown receipt archive has 12,550 rows / 1,607 unique FIDs, but overlap with the corrected feature-test set is 0. It has 0 timestamped player-value snapshots. No true-receipt model result can be computed; the model's latest target is May 24, 2026, before the later archived receipt window.

## Independent verification

The independent verifier re-opened the Crown T12 market inventory, FT, frozen membership and per-fixture ledger. It passed 21,476 Crown quote/FT identity checks, 21,476 independently recomputed AH settlements, 21,476 model direction checks, and 21,476 date-cutoff/membership checks. Every model uses the same 5,369 FIDs; no duplicate FID within a model; all four variants have 4,275 out-of-eight candidates. Full per-week and per-league tables are in `m8_squad_value_results_20261120.json`.

## Preserved superseded attempt

The first complete run included matches later than the appearance-source end date, applying a stale frozen roster history to later fixtures. That run is preserved as `SUPERSEDED_UNGUARDED_APPEARANCE_CUTOFF_RESULTS_20261120.json` and `SUPERSEDED_UNGUARDED_APPEARANCE_CUTOFF_LEDGER_20261120.jsonl.gz`, with the reason documented in `SUPERSEDED_ATTEMPT_NOTE_20261120.md`. It is not part of the primary results above. The corrected run excludes those fixtures solely because the required pre-match appearance-history cutoff lies beyond source coverage.

## Reproduction

- Main research: `m8_squad_value_crown_ah_20261120.py`
- Independent verifier: `verify_squad_value_crown_ah_20261120.py`
- Report renderer: `build_squad_value_report_20261120.py`
- Full per-fixture ledger: `squad_value_per_fixture_20261120.jsonl.gz`
- Complete summary, annual, ISO-week and league tables: `m8_squad_value_results_20261120.json`
- Independent audit: `squad_value_independent_verification_20261120.json`
- Re-run main script, verifier, then report renderer. SHA256 manifest records inputs/outputs.

Historical research only; no formal strategy, production, Telegram or ledger behavior changed.
