# M8 referee-history and Crown AH study (2026-11-20)

## Conclusion

**No independent profitable source was identified.** On the same 5,467 FIDs outside the frozen original eight, the referee-only model lost 170.705U (-3.122%), and Crown+referee lost 79.745U (-1.459%). Crown-only on the same eligible sample lost 27.770U (-0.508%); the referee feature therefore worsened the combined 2024–2026 net by 51.975U. The referee assignment in the source is retrospective and has no publication/receipt timestamp, so none of these results establishes a usable pre-match information advantage.

This is a historical Crown source-event replay, not an HTTP-receipt replay, a formal trade, or a Telegram result. Original eight membership, M9/M1/MR1, production and ledger were not changed.

## Scope and data

- The already audited paired Crown T24/T12 historical inventory supplied 38,846 unique FIDs; the full paired market file contains 41,059 T12 rows before the paired-path restriction. The experiment only used T12 rows in that paired inventory. Prices and FT came from the Crown historical event-time inventory; historical retrieval is not proof of receipt time.
- A strict league/team crosswalk, ordered home/away identity, date within ±1 day, exact FT and referee-name join matched 12,851 of 38,846 paired FIDs (711 normalized league-scoped referee identities). Coverage loss: {"one_or_both_teams_unmapped": 13541, "no_exact_team_date_match": 3916, "matched_with_retrospective_referee": 12851, "FT_identity_conflict": 55, "no_competition_crosswalk": 8478, "missing_referee_name": 5}.
- Of those matched cases, 6,967 target fixtures in 2024–2026 had a prior referee history and entered the common model sample: 2024 2,160; 2025 3,239; 2026 1,568. Test dates run 2024-01-01 through 2026-07-06 China-time date labels.
- The common test contains 1,500 frozen-eight overlaps and 5,467 unique incremental FIDs. Every model has one direction per FID; models overlap completely and must not be summed.
- The source match uses retrospective referee identity in Transfermarkt games.csv.gz. It contains no referee appointment publication or receipt time; the games source ends 2026-07-06. The saved actual Crown receipt archive has 12,550 rows / 1,607 FIDs dated 2026-10-08 through 2026-11-14, zero FID overlap with model targets, and zero referee-assignment timestamp evidence.

## Method

- Target is the difference between one-unit net AH payouts for home and away at the Crown T12 line and both Crown prices. Quarter-handicap contracts are split into equal half-line legs and settled separately.
- Historical referee feature is within-league prior mean (home goals − away goals + Crown home AH line), minus that league’s prior mean, shrunk by n/(n+20); a log(1+n) history count is also included. Prior matches are embargoed through target date minus three calendar days because the source has date but no finish time.
- Models are fixed Ridge alpha 100: Crown prices/line only; referee features only; Crown+referee; and a same-FID low-price-side control. 2024/2025/2026 are expanding-year test folds trained only on earlier calendar years (5,173 / 7,333 / 10,572 eligible training rows respectively). No threshold or league search was used.
- Frozen membership is used only after prediction for unique incremental attribution; it is not a feature. AH only; no OU.

## Eight-group-excluded performance

| Method | Incremental unique FIDs | Net U | ROI | MDD U | ISO weeks in span | Average orders / week | Active weeks |
|---|---:|---:|---:|---:|---:|---:|---:|
| Crown-only market control | 5,467 | -27.770 | -0.508% | +59.060 | 132 | 41.42 | 117 |
| Referee history only | 5,467 | -170.705 | -3.122% | +205.465 | 132 | 41.42 | 117 |
| Crown + referee history | 5,467 | -79.745 | -1.459% | +109.415 | 132 | 41.42 | 117 |
| Same-fixture lower-price side | 5,467 | -290.930 | -5.322% | +304.655 | 132 | 41.42 | 117 |

## Year-by-year results

| Method | 2024 orders / net U / ROI | 2025 orders / net U / ROI | 2026 orders / net U / ROI |
|---|---:|---:|---:|
| Crown-only market control | 1,700 / -32.920 / -1.936% | 2,522 / +33.960 / +1.347% | 1,245 / -28.810 / -2.314% |
| Referee history only | 1,700 / -38.825 / -2.284% | 2,522 / -83.600 / -3.315% | 1,245 / -48.280 / -3.878% |
| Crown + referee history | 1,700 / +0.675 / +0.040% | 2,522 / -47.915 / -1.900% | 1,245 / -32.505 / -2.611% |
| Same-fixture lower-price side | 1,700 / -91.005 / -5.353% | 2,522 / -149.165 / -5.915% | 1,245 / -50.760 / -4.077% |

## Frozen-eight same-horizon combination

The frozen group baseline for the same 2024–2026 dates is 6,873 FIDs, +197.765U, ROI 2.877%. Each row below adds that model’s unique outside-eight candidates once. The original eight is not changed.

| Method | Combined unique FIDs | Combined net U | Combined ROI | Change vs frozen baseline |
|---|---:|---:|---:|---:|
| Crown-only market control | 12,340 | +169.995 | +1.378% | -27.770U |
| Referee history only | 12,340 | +27.060 | +0.219% | -170.705U |
| Crown + referee history | 12,340 | +118.020 | +0.956% | -79.745U |

## Weekly uncertainty and dispersion

A descriptive ISO-week block bootstrap resampled active weeks with replacement within each test year (20,000 repetitions, seed 20261120). It does not correct for the fact that these years have been examined in prior M8 research.

| Method | 95% interval net U | 95% interval ROI | Bootstrap share net-positive |
|---|---:|---:|---:|
| Crown-only market control | [-147.370, +94.625] | [-2.670%, +1.748%] | 33.16% |
| Referee history only | [-307.080, -40.225] | [-5.507%, -0.737%] | 0.53% |
| Crown + referee history | [-208.675, +47.780] | [-3.752%, +0.881%] | 11.08% |
| Same-fixture lower-price side | [-394.740, -187.890] | [-7.111%, -3.515%] | 0.00% |

Candidate ISO-week count and net U for every method are preserved in `m8_referee_history_results_20261120.json` and `referee_history_independent_verification_20261120.json`.

## League distribution

The central Crown+referee candidate was positive in 8 of 25 leagues and negative in 17; league IDs are the Crown IDs. Positive groups were 1, 12, 25, 29, 48, 52, 70, 75; all 25 counts, net U and ROI are in the result JSON. The largest positive entries include ID 1 (459 orders, +25.165U), ID 48 (351, +15.345U), ID 52 (142, +11.450U), ID 70 (109, +8.245U), and ID 75 (41, +7.275U). The largest negative entries include ID 14 (601, −29.845U), ID 262 (257, −21.730U), ID 26540 (246, −13.270U), ID 61 (160, −11.410U), and ID 319 (101, −10.360U). These are descriptive, not a basis for league filtering; no league-specific rule was fit or selected.

## Independent verification

- Independent verifier reopened the paired Crown T12 market inventory, frozen membership and gzip ledger. It checked exact FID/date/league/home/away, Crown AH line, both Crown prices and FT, then independently settled all bets, including split quarters: 27,868/27,868 quote/FT checks passed; 27,868/27,868 settlement checks passed; direction/price selection checks 27,868/27,868 passed.
- Duplicate FIDs within each model: 0; frozen overlap: 1,500; incremental unique FIDs per model: 5,467. Annual ledger sums independently match the result JSON.
- The verifier validates archived source-event prices and stored FT, not raw HTTP receipt bodies. There are no valid same-target referee-information receipts, so true receipt performance is not computable (zero eligible fixtures), not zero-profit live trading.

## Answer and limits

Retrospective referee identity alone has no independent profitable AH value in this design. Adding it to Crown prices improved one narrow test slice in 2024 by only +0.675U, then lost 47.915U in 2025 and 32.505U in 2026; total incremental loss was 79.745U. This does not support a stable signal or an actionable edge. The reason the hypothesis cannot be conclusively tested as a real pre-match information source is not just limited statistical power: the dataset lacks appointment publication/receipt timestamps, and the later genuine Crown receipt archive has no joinable target with a referee snapshot. The retrospective upper-bound is negative despite that optimistic availability assumption.

## Reproduction and artifacts

- Main research: `m8_referee_history_ah_20261120.py`
- Independent source/settlement validator: `verify_referee_history_ah_20261120.py`
- Report renderer: `build_referee_history_report_20261120.py`
- Per-fixture ledger (four method rows per eligible FID): `referee_history_per_fixture_20261120.jsonl.gz`
- Complete year/week/league results and coefficients: `m8_referee_history_results_20261120.json`
- Independent verifier and block bootstrap: `referee_history_independent_verification_20261120.json`
- Re-run: `python3 research/m8/referee_history_ah_20261120/m8_referee_history_ah_20261120.py`, then run the verifier, then this renderer.

Historical experiment only. No production, original-eight, Telegram, formal ledger, collector or schedule changes.
