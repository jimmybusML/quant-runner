# Collection checkpoint — 2026-11-22 04:26 UTC

Status snapshot `2026-11-22T04:26:19.691372Z`; per-UTC-year coverage `2026-11-22T04:26:38.700279Z`; season coverage `2026-11-22T04:26:43.250638Z`; persistence audit `2026-11-22T04:26:43.461816Z`. The live historical writer continued during this period, so read snapshots can differ by a few FIDs.

## Current known-source inventory

- **203,962 unique FIDs / 118 provider league IDs / 902 league×UTC-year buckets.** The exact M7 name map is complete for the 73 audited names; this remains a known-source union, not proof of every worldwide competition.
- Full-time score evidence: 193,518 verified; 10,444 unresolved. Twenty-four records lack a reliable UTC year and remain in `unknown`.
- Season matrix: 96,503 FIDs have one explicit source season label across 14 labels; 107,459 source records lack the field; conflict FIDs 0. No season was inferred from UTC year.

## Crown movement collection

- Immutable historical queue: 101,266 FIDs, SHA256 `5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`. At 04:26:19Z, 1,289 terminal (329 `SAVED`, 960 `NO_CROWN_AH_QUOTES`) and 99,977 still pending.
- By the read-only persistence audit at 04:26:43Z, terminal count reached 1,293. All matched to SQLite and raw responses; missing files 0, SHA mismatches 0, receive-time mismatches 0, quote-count mismatches 0; pass=true. The verifier made 0 HTTP requests and 0 writes. Thirty historical IncompleteRead attempts all have later terminal outcomes.
- 04:26:38Z inventory/SQLite snapshot: 103,987 movement capture FIDs, 53,328 with 4,499,297 quote rows, 50,659 no-AH capture statuses, and 99,975 without a movement capture. An empty captured response describes that response only.
- Summary history remains 50,200 FIDs / 99,242 rows; 153,762 fixtures remain on the separate historical summary gap queue.

## Reusable summary rows already found

- The 04:10 full raw cache audit found 328 exact FID+SHA responses with 656 summary rows missing from the historical summary layer. Their FID, body SHA, Crown identity, row count and unique same-response receive time were independently checked. Candidate import is not yet executed because the shared safe-window writer continues.
- Do not represent these rows as persisted summary data until the append-only import is actually completed and independently verified.

## Artifacts

- Current per-UTC-year Crown matrix: `league_year_quote_coverage_20261122T0426Z.csv/.json`.
- Current source-season matrix: `league_season_inventory_coverage_20261122T0426Z.csv/.json`.
- Collection status and persistence audit: `COLLECTION_STATUS_20261122T0426Z.json`, `movement_collection_persisted_audit_20261122T0426Z.json`.
- SHA manifest: `CHECKPOINT_SHA256_20261122T0426Z.txt`.
- Source event time, HTTP receipt time, historical retrieval, prospective receipts and live captures remain distinct. No model, strategy, backtest, TG, formal ledger or production acquisition configuration changed.
