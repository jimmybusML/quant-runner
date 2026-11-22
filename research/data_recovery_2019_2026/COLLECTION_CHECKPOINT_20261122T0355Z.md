# Collection checkpoint — 2026-11-22 03:55 UTC

Fixed snapshot time: `2026-11-22T03:55:11.652769Z`. Coverage table snapshot: `2026-11-22T03:55:08.080249Z`. The Crown SQLite was read-only; a concurrent historical collector may append after these snapshots.

## Known-source inventory and FT

- Reconciled known-source inventory: **203,962 unique FIDs**, **118 provider league IDs**, **902 provider-league × UTC-year buckets**. The 73 exact M7 competition names remain mapped with 0 unmapped names. This is a known-source union, not a claim of worldwide competition completeness.
- Verified FT: **193,518**; unresolved: **10,444**. Existing-source overlays remain provenance evidence; no new FT was produced in this checkpoint. Provider status and placeholder 0:0 values are not inferred as FT.
- Coverage includes 24 records with unknown event year. The data remains in an explicit `unknown` bucket; no year was inferred.
- Three previously unnamed league-year buckets (provider ID 27391, years 2022/2024/2026) are now labeled **UEFA Nations League D** only after exact FID, league ID and home/away team ID matches against the cached M1 rows. Cache SHA256: `b474015b933f79b6265e67f8d6c627b298d91bc0295e3526e6d43d819ac0128c`.

## Crown historical movement recovery

- Safe-window driver PID `59381` remains alive in `historical` mode. At the status snapshot it was between scheduled collection windows (`collector_pids=[]`); no competing collector was started.
- Immutable queue: **101,266 FIDs**, SHA256 `5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`. Log state: **1,122 unique terminal FIDs** (329 `SAVED`, 793 `NO_CROWN_AH_QUOTES`); **100,144 remain without terminal status**. All 30 earlier `IncompleteRead` attempts have later terminal results; there are 0 retryable FIDs lacking a terminal result.
- The independent read-only persistence audit matched all 1,122 terminal FIDs to SQLite and their raw response files. Missing raw files: 0; SHA mismatch: 0; response-receipt mismatch: 0; quote-row-count mismatch: 0. Result: `pass=true`. Audit made 0 HTTP requests and 0 DB writes.
- Across the full current inventory, the SQLite read snapshot contains 103,818 historical movement capture FIDs, of which 53,328 have Crown AH rows (4,499,297 rows) and 50,490 are recorded as `NO_CROWN_AH_QUOTES`. A captured no-quote response only means that response contained no Crown AH quote; it is not proof that Crown never quoted the fixture.
- The exact recovery queue audit has 100,144 of its 101,266 FIDs still missing a terminal historical capture. Historical source-event times and actual HTTP receipt times are separate. These requests are retrospective retrieval, never contemporaneous live receipts.
- Full-inventory movement gaps: 100,144 FIDs lack any movement capture in the read snapshot. Summary-layer historical captures: 50,200 FIDs / 99,242 quote rows; the separate immutable summary queue still contains 153,762 FIDs without historical summary captures and has not been started concurrently.

## Per-league × UTC-year coverage and reproducibility

- The snapshot contains **902 rows** and partitions every inventory FID exactly once; verified FT and unresolved-FT bucket totals reconcile to their respective FID ledgers.
- Table: `league_year_quote_coverage_20261122T0354Z.csv`; full snapshot: `league_year_quote_coverage_20261122T0354Z.json`; builder: `build_league_year_live_coverage_20261122.py`.
- This is a read-transaction snapshot while the database writer can be active. It deliberately omits the changing main SQLite file SHA; it records SQLite snapshot times, capture counts and last response receipt time instead. The 118-ID inventory remains a known-source union, not proof of exhaustive global discovery.
- No strategy/backtest, production model, Telegram, formal-ledger, collector code/configuration or production schedule was changed.
