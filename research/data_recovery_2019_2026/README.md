# 2019–2026 all-league historical data recovery

This is an active collection and reconciliation task, not a strategy or model study. The local authoritative stores remain under `/Users/mac/QuantAsiaDesk/`; this public directory contains reproducible audit code and sanitized aggregate snapshots, not licensed raw Crown response bodies or the private SQLite database.

## Current evidence

- `inventory_coverage_summary_2019_2026.json` and `league_year_coverage_2019_2026.csv`: moving per-provider-league/per-UTC-year coverage snapshot; current committed checkpoint is described below.
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

## Target-period schedule-page continuity — 2026-11-21 12:25 UTC

`audit_cached_schedule_page_coverage_2019_2026.py` re-read 5,505 unique cached page numbers for the 64 expanded provider leagues, preferring the original raw response when both raw and normalized copies exist; the baseline inventory records 9,840 physical page files. It found 0 missing page numbers before the last cached page containing a 2019–2026 fixture, 0 gaps between that page and the first cached page wholly before 2019, 0 response parse errors, and 0 league-ID mismatches. The source-reported 373 uncached pages are in the provider's all-history pagination beyond the verified 2019+ interval; they were not fetched because they fall before the requested 2019 start. Cached source dates span 2013-12-29 through 2026-11-24. This audit does not cover the separate 14 additional scoped competition candidates that still lack saved schedule pages, the partial league-15 supplement, or Crown quote completeness.

The detailed per-page SHA/date audit is in `cached_schedule_page_continuity_2019_2026.json`; the per-league summary is in the matching CSV. The 2019–2026 inventory includes 64 expanded schedule leagues plus M1-only league ID 27391; the latter currently appears in M1 history-cache rows rather than these page directories.

## Crown-captured fixture metadata overlay — 2026-11-21 15:06 UTC

- A read-only audit of Crown capture FIDs not yet represented in the reconciled schedule found 46 identifiers. Ten had SHA-valid, identity-consistent fixture metadata in existing Crown responses: nine fall inside UTC 2019–2026 and one is a China-date 2019 boundary match whose kickoff is UTC 2018-12-31, retained separately.
- The nine in-scope FIDs are Portugal Primeira Liga (provider ID 51) future fixtures. Their saved live summary responses have no Crown bookmaker entry and no AH quote rows. Their `0:0` values are placeholders, their status is absent, and they are not counted as verified FT or Crown AH. The row-level overlay records response SHA, receipt times, identity fields and the missing bookmaker fact.
- `audit_existing_inventory.py` now adds this as a distinct fixture-metadata source. It does not call these rows TotalCorner schedule records, priced quotes, or verified scores. Inventory rose from 129,567 to 129,576 unique in-scope FIDs; verified FT stayed 124,387, unverified FT rose to 5,189, and Crown movement quote FIDs stayed 52,999.
- Readiness classification at 15:06:43 UTC: 300 future/not-due, 4,254 past-kickoff with missing/unknown status, 635 with explicitly non-full status; 4,766 have a placeholder `0:0`, none promoted to FT. This is an as-of-time classification, not a final abandonment judgment.
- Full local audit, per-FID inventory and source response paths stay on the authorized host. Public aggregate summary, 71×8 league/year matrix, 501 source-season buckets, separate Crown-only overlay and SHA manifest are committed. The TotalCorner supplemental schedule collector remained live on provider league ID 270 (Scotland Championship), page 12/76, after 616 successful requests and 18,065 newly observed FIDs; the full scope is still incomplete.
