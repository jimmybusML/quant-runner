# Execution record — M8 squad value and Crown AH

- Execution date: 2026-11-20 Asia/Shanghai.
- Branch: `research/m8-exact-cross-league-expansion`; worktree contained no unrelated user edits.
- Main research: `python3 research/m8/squad_value_crown_ah_20261120/m8_squad_value_crown_ah_20261120.py` — final run exit 0. It re-read the existing paired Crown T24/T12 inventory, mapped-team appearances, complete rows from the truncated valuation gzip, frozen M8 membership, receipt archive, and the prior cross-league expansion's target league list.
- Coverage correction: mapped-team appearance history ends 2026-05-24. Primary features omit Crown fixtures when the three-day pre-match history cutoff lies after the source end. An earlier unguarded run that carried an old roster snapshot into later 2026 rows is preserved as `SUPERSEDED_UNGUARDED_APPEARANCE_CUTOFF_*` and excluded from the primary result.
- Final sample: 10,850 FIDs with two-side value features across the dated history; forward test 5,369 FIDs in 2024-2026 (2026 through May 24), with 1,094 frozen-eight overlaps and 4,275 incremental unique FIDs. The 15 expansion league IDs have zero FID overlap with the paired Crown T24/T12 inventory and zero Transfermarkt crosswalk coverage.
- Independent verifier: `python3 research/m8/squad_value_crown_ah_20261120/verify_squad_value_crown_ah_20261120.py` — exit 0; 21,476 Crown quote/FT identity checks, independent AH settlement checks, side-selection checks, feature cutoff and frozen-membership checks all passed.
- Report renderer: `python3 research/m8/squad_value_crown_ah_20261120/build_squad_value_report_20261120.py` — exit 0.
- Primary results, unique outside-eight 4,275 FIDs: Crown-only −42.370U/−0.991%; value-only −166.610U/−3.897%; Crown+value −179.985U/−4.210%; lower-price side −277.805U/−6.498%. No candidate was profitable in any annual fold. True Crown receipt score is unavailable: no timestamped value snapshot and zero receipt-FID overlap with the coverage-corrected candidate set.
- The player-values gzip is truncated; only 589,239 complete newline-terminated records were parsed, with the final four-byte partial record discarded. Latest complete valuation date is 2024-12-27. Valuation age averaged 116.5 days in 2024, 227.5 in 2025 and 471.7 in the partial 2026 target pool.
- No formal strategy, production code, Telegram, ledger, Crown collection chain or schedule changed. No formal order or ledger write occurred.
- Input/output hashes: `SHA256SUMS_20261120.txt`.
