# Collection checkpoint — 2026-11-22 04:13 UTC

Collection state `2026-11-22T04:13:18.443375Z`; quote coverage `2026-11-22T04:13:40.351591Z`; terminal persistence audit `2026-11-22T04:13:40.811502Z`. All counts below are time-stamped snapshots; the authorized collector continues under its safe-window driver.

## Known-source inventory and FT

- **203,962 unique FIDs / 118 provider league IDs / 902 provider-league × UTC-year buckets.** The 73 exact M7 names map into this known-source union. It is not a claim of global competition completeness.
- Verified FT: 193,518; unresolved FT: 10,444. The 24 no-year FIDs remain in the unknown-year bucket. No results were inferred from provider statuses or 0:0 placeholders.
- Provider 27391 2022/2024/2026 is labeled UEFA Nations League D after exact FID, league ID and home/away team ID matching to local M1 cache rows (cache SHA in coverage JSON).

## Crown movement recovery

- Immutable queue: 101,266 FIDs; SHA256 `5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`. At 04:13:18Z, 1,213 were terminal (329 `SAVED`, 884 `NO_CROWN_AH_QUOTES`); 100,053 remained without terminal results. All 30 prior `IncompleteRead` attempts have a later terminal result.
- Independent read-only verification matched all 1,213 terminal results to SQLite and raw files. Missing raw files 0; raw SHA mismatch 0; HTTP receive-time mismatch 0; quote count mismatch 0; pass=true. Audit made 0 requests and 0 DB writes.
- Current inventory movement layer: 103,909 historical capture FIDs; 53,328 FIDs with 4,499,297 quote rows; 50,581 no-AH responses; 100,053 without a movement capture. A captured empty response is not proof that the provider never quoted the match.
- Summary historical layer remains separate: 50,200 FIDs / 99,242 rows, with 153,762 fixture FIDs in the existing missing-summary queue.

## Reusable raw Crown summary data found offline

- Re-audited all 105,559 existing raw Crown response files against the current 203,962-FID inventory. Every raw file passed exact response SHA anchoring to the local SQLite; exact fixture identity checks and parse issues: none; unanchored files: 0.
- The raw cache contains 104,442 unique FIDs with valid exact-FID responses. All raw movement quote rows are already indexed in the movement layer. Found **328 unique FID+SHA pairs with 656 summary quote rows** present in raw files but not yet normalized in the historical summary layer.
- Rechecked every candidate against raw SHA, FID, Crown bookmaker and open/close rows. All 328 candidates have one exact response receive timestamp recorded for the same FID+SHA in an existing historical movement capture; missing/ambiguous timestamps: 0. Candidate ledger: `unindexed_summary_layer_reuse_candidates_20261122T0410Z.jsonl.gz`.
- This is an append-only reuse candidate list, not an import. The shared SQLite writer was still active at preparation time, so no concurrent DB write was attempted. Once that writer is idle, import these rows using the existing Crown parser while preserving the exact response SHA and receipt time; then rebuild the summary gap queue to avoid re-requesting them. No raw response files were changed.

## Artifacts and limits

- Per-league/year coverage: `league_year_quote_coverage_20261122T0413Z.csv/.json`; latest movement log→SQLite audit: `movement_collection_persisted_audit_20261122T0413Z.json`.
- Full raw-cache audit: `offline_raw_Crown_response_inventory_audit_2019_2026_20261122T0410Z.json` and compressed per-FID SHA ledger. Candidate preparation: `prepare_unindexed_summary_reuse_20261122.py` and its JSON/JSONL outputs.
- Everything under this section is historical-source reconciliation. Source-event time and actual HTTP receive time are distinct. No other bookmaker prices are substituted. No strategy, model, backtest, production flow, Telegram, or formal ledger changes.
