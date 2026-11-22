# Collection checkpoint — 2026-11-22 04:20 UTC

Status snapshot `2026-11-22T04:20:01.738780Z`; league-year quote snapshot `2026-11-22T04:20:20.694830Z`; league-season snapshot `2026-11-22T04:20:25.220424Z`; persistence audit `2026-11-22T04:20:25.426547Z`. The collector is a live append-only writer, so each read snapshot has its own exact timestamp.

## Inventory, schedule scope, FT, and seasons

- Reconciled known-source inventory: **203,962 unique FIDs / 118 provider league IDs**; exact M7 name map has 0 unmapped names. The union is not proof of worldwide competition completeness.
- The season audit provides **541 league×source-season/unknown buckets**. Exactly 96,503 FIDs have one source-supplied season label across 14 labels; 107,459 have no season field in their exact source record; conflicting labels: 0. Missing season is left unknown, never replaced with UTC year.
- Verified FT: 193,518; unresolved FT: 10,444. The 24 no-year FIDs remain unknown. No status/placeholder inference was made.
- Provider league 27391 is named UEFA Nations League D for 2022/2024/2026 only after exact FID, league ID and home/away team-ID checks against M1 cache.

## Crown historical coverage

- Immutable movement queue has 101,266 candidates, SHA `5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`. At 04:20:01Z the log had 1,249 terminal FIDs (329 saved; 920 no-AH response), with 100,017 pending. At the 04:20:25Z persistence audit the log advanced to 1,252 terminal. All 1,252 matched SQLite and raw response evidence; raw/SHA/receipt/quote-count mismatches: 0; `pass=true`; audit made 0 requests and 0 writes.
- Full inventory quote snapshot at 04:20:20Z: 103,947 movement captures; 53,328 FIDs with 4,499,297 quote rows; 50,619 no-AH capture statuses; 100,015 FIDs still lacking movement capture. Historic empty responses do not prove Crown never offered a market.
- Summary historic layer: 50,200 capture FIDs / 99,242 quote rows; the immutable summary gap queue has 153,762 FIDs.

## Existing raw cache available for append-only summary reuse

- At 04:08:58–04:09:56Z, 105,559 existing raw response files were scanned for the full 203,962-FID inventory. All files matched exact SQLite SHA anchors; 0 unanchored, 0 parse/identity issues.
- Identified 328 unique exact FID+SHA raw responses with 656 summary rows missing from the historical summary layer. All 328 have a single exact response receive time recorded against the same FID+SHA in the existing movement capture; no timestamp was inferred. Candidate ledger: `unindexed_summary_layer_reuse_candidates_20261122T0410Z.jsonl.gz`.
- Candidate import is prepared but not yet written because the shared Crown SQLite collector continues. After the movement writer is safely idle, append using the existing parser and exact recorded receive time, then rebuild the summary gap queue. Raw files remain unchanged.

## Reproducibility files

- UTC-year market coverage: `league_year_quote_coverage_20261122T0420Z.csv/.json`.
- Source-faithful season coverage: `league_season_inventory_coverage_20261122T0420Z.csv/.json`; generator `build_league_season_inventory_20261122.py`.
- Full raw-cache audit: `offline_raw_Crown_response_inventory_audit_2019_2026_20261122T0410Z.json` and compressed per-FID digest ledger.
- All source/output SHA256 values: `CHECKPOINT_SHA256_20261122T0420Z.txt`.
- Source-event timestamps, HTTP receive timestamps, capture modes and quote layers remain distinct. No strategy/backtest, production model, Telegram or formal ledger work was performed.
