# Collection checkpoint — 2026-11-22 03:29 UTC

Snapshot time: `2026-11-22T03:29:34Z`. This is a fixed progress snapshot while the collector remains active.

## Crown historical movement batch

- Safe-window driver PID `59381` remains active; its current collector child at the snapshot is PID `4927`. No second collector was started. The collector uses the existing `crown_capture_store.py`, historical mode, existing 5.2-second request pacing, and scheduled-job mutual exclusion.
- Immutable candidate queue: `crown_missing_movement_2019_2026.jsonl`, 101,266 FIDs; SHA256 `5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`.
- Append-log snapshot: 1,005 attempts covering 975 unique FIDs, all 975 at a terminal status: 329 `SAVED`, 646 `NO_CROWN_AH_QUOTES`; 30 earlier `IncompleteRead` attempts each later reached a terminal status. Remaining without terminal result: 100,291.
- The 329 saved responses contain 69,588 AH movement quote rows. This batch is historical retrieval; no record is presented as a contemporaneous live receipt.
- Read-only persistence audit `movement_collection_persisted_audit_20261122T0329Z.json` matched all 975 terminal FIDs to SQLite captures. Raw response files missing: 0; SHA mismatches: 0; receive-time mismatches: 0; quote-row-count mismatches: 0. Audit result `pass=true`; the audit made zero network requests and zero database writes. Latest received response in this snapshot: `2026-11-22T03:29:30Z`.

## Existing verified FT evidence reconciliation

- Added a reproducible, read-only union audit of existing M1, M5, Crown raw-result, and archived ESPN FT evidence. It checks exact FID/inventory membership, league and available identity/kickoff fields, score agreement across sources, and membership in the current unresolved FT queue. It does not fetch data or update the canonical inventory.
- Source rows: M1 441, M5 27, Crown 18, ESPN 42; 528 rows reduce to 504 unique FIDs after deduplication. There are 24 overlapping source rows, no cross-source score conflicts, and no identity errors. All 504 FIDs are already absent from the 10,444-row unresolved queue, so this audit discovers no additional FT rows to merge.
- These are source-provenance overlays, not newly collected results in this turn. M1/M5/Crown/ESPN raw-response checks remain in their respective source audit records. Crown responses contribute FT evidence only, never substitute odds.
- Outputs: `verified_ft_overlay_union_203962_20261122.json` and `verified_ft_overlay_union_203962_20261122.jsonl.gz`; code: `audit_verified_ft_overlay_union_20261122.py`.

## Remaining work

- Global baseline remains 203,962 known-source FIDs / 118 provider league IDs, with 193,518 verified FT and 10,444 unresolved as of the earlier 02:53 UTC inventory snapshot. The 118-ID set is a reconciled known-source union, not proof of exhaustive global league discovery.
- The movement queue is far from complete. The separate summary-layer audit lists 153,762 candidate FIDs, and no summary collector was started while the movement collector is active. Rebuild both layer queues after this batch reaches terminal status.
- Continue discovering any additional exact league IDs and seasons, refreshing the per-league/year inventory, resolving the 10,444 FT gaps, then process summary and movement gaps through the existing safe collection method. Do not infer no market from missing captures or from explicit no-quote responses outside the recorded response.
- No strategy, training, backtest, profitability selection, Telegram, formal ledger, or production model work was performed.
