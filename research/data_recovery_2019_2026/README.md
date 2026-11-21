# 2019–2026 all-league historical data recovery

This is an active collection and reconciliation task, not a strategy or model study. The local authoritative stores remain under `/Users/mac/QuantAsiaDesk/`; this public directory contains reproducible audit code and sanitized aggregate snapshots, not licensed raw Crown response bodies or the private SQLite database.

## Current evidence

- `inventory_coverage_summary_2019_2026.json` and `league_year_coverage_2019_2026.csv`: per-provider-league/per-UTC-year coverage snapshot generated 2026-11-21 10:23 UTC, with source file content digests and conflict counts.
- `collection_progress_snapshot_*.json` and matching checkpoint Markdown: later live progress snapshots. They explicitly state the run is incomplete.
- `score_source_disagreements.jsonl`: two exact-FID FT conflicts retained for audit; the source score records are not rewritten.

## Reproduction on the authorized local host

The audit scripts read the existing local schedule caches, M1 history cache and Crown SQLite. `safe_window_collection_driver.py` invokes the existing `crown_capture_store.py` collector at its default 5.2-second request spacing, but only while known scheduled TotalCorner jobs are idle; its JSONL resume manifest is derived from the append-only collector log. It does not change the collector, production schedules, models or ledgers.

Raw Crown response files and full per-FID inventories are intentionally not committed here. Their SHA manifests and exact local file locations are recorded in the local audit output and handoff.

## Offline reuse of cached Crown layers — 2026-11-21

- Read-only raw-cache audit found 104,167 existing response files for 103,115 unique schedule FIDs with valid fixture identity and Crown bookmaker; no SHA was left without a content-addressed filename, legacy index or current SQLite capture-layer SHA anchor after normalization.
- The cache already held open/close Crown AH summaries for 38,598 FIDs that had not been normalized under the `summary` layer, plus three movement responses not normalized under `movement`. These bodies were reused locally with the existing `crown_capture_store` parser; no API calls were made. Historical capture mode and exact indexed receive times were preserved, `prospective_observation=false`.
- Persisted in this import window: 38,606 captures and 77,230 quote rows across 38,601 unique FIDs (38,603 summary captures / 77,206 rows, plus 3 movement captures / 24 rows). The independent verifier re-read each raw response and compared SHA, FID/Crown identity, parsed contract values, source-event timestamp, receive-time provenance, quote count and historical/non-prospective flags; 38,606/38,606 passed.
- At the import audit, the normalized history store had 52,929 movement FIDs / 4,422,398 movement rows and 49,011 summary FIDs / 99,118 summary rows. Later append-only historical collection may increase these counts. See the independent audit JSON, digest-only per-fixture ledgers and execution record; no raw response bodies or SQLite database are committed.
- Movement batch 02 is still in progress. At 2026-11-21 11:21 UTC, 88/11,703 FIDs had been attempted and 11,615 remained unattempted; the safe-window driver was live but waiting for the scheduled MR1 job to finish. Four `IncompleteRead` failures are retained as retryable errors, not classified as no-quote results.
