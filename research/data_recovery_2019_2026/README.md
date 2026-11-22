# 2019–2026 all-league historical data recovery

This is an active collection and reconciliation task, not a strategy or model study. The local authoritative stores remain under `/Users/mac/QuantAsiaDesk/`; this public directory contains reproducible audit code and sanitized aggregate snapshots, not licensed raw Crown response bodies or the private SQLite database.

## Current evidence

- Latest persisted checkpoint: `COLLECTION_CHECKPOINT_20261122T0227Z.md` and `COLLECTION_STATUS_20261122T0227Z.json`; the 203,962-FID known-source union has 193,476 verified FT records and 10,486 unresolved. The completed 53-league supplemental schedule audit contributes 62,339 new unique FIDs. All 73 M7 competition names map to the known 118 provider IDs; this is not a global completeness claim.
- The 12 M1 records whose event kickoff differs from another stored schedule version are retained with both values in `m1_ft_evidence_in_unverified_ledger_20261122.jsonl`; the score evidence is not used to overwrite the conflicting kickoff.
- Crown movement recovery is still running in historical mode. Its latest checkpoint is a moving snapshot, not a completion claim; raw responses and the SQLite remain local.
- `inventory_coverage_summary_2019_2026.json` and `league_year_coverage_2019_2026.csv`: moving per-provider-league/per-UTC-year coverage snapshot; current committed checkpoint is described below.
- `collection_progress_snapshot_*.json` and matching checkpoint Markdown: later live progress snapshots. They explicitly state the run is incomplete.
- `score_source_disagreements.jsonl`: two exact-FID FT conflicts retained for audit; the source score records are not rewritten.

## Completed supplemental schedule reconciliation — 2026-11-22 02:28 UTC

- The 38-target TotalCorner schedule run completed at 2026-11-21 22:37:41 UTC after 2,140 requests. Its 2,098 referenced response pages and all 62,339 source-record hashes verified with zero raw-source errors. The separate 15-target run verified 936 pages and 27,503 unique FIDs; these 27,503 were already in the baseline inventory. The 38-target FIDs had no baseline or cross-batch overlap, so the audited 53-target source union added 62,339 unique FIDs and brought the inventory to 203,962.
- The 53-target schedule source carries 83,990 numeric `full` FT rows and 5,852 rows that remain unverified or non-full. The merged global FT ledger remains 193,476 verified / 10,486 unresolved. Missing provider season fields remain missing; UTC kickoff year is not substituted as season.
- The explicit source audit maps all 73 M7 exact competition names to 118 known provider league IDs, with no IDs missing or outside the reviewed union. This closes the named-source mapping gap only; it does not establish exhaustive global fixture coverage.
- A read-only Crown SQLite snapshot at 02:27:43 UTC found 173 historical movement captures among the 38-target batch, with zero AH quote FIDs. This is a moving WAL-aware snapshot during an active writer. It is not a stable database hash and does not imply Crown has no market for the other fixtures. The 02:28:14 UTC history queue log records 601 terminal FIDs (329 `SAVED`, 272 `NO_CROWN_AH_QUOTES`) and 100,665 not yet logged out of 101,266 candidates.
- Reproduction: `audit_supplemental_15_and_38_schedule_batches_20261122.py`, `reconcile_53_league_schedule_union_20261122.py`, `audit_league_scope_union_2019_2026.py`, and `build_recovery_checkpoint_20261122.py`. Exact result and code digests are listed in `CHECKPOINT_SHA256_20261122T0227Z.txt`.

## Reproduction on the authorized local host

The audit scripts read the existing local schedule caches, M1 history cache and Crown SQLite. `safe_window_collection_driver.py` invokes the existing `crown_capture_store.py` collector at its default 5.2-second request spacing, but only while known scheduled TotalCorner jobs are idle; its JSONL resume manifest is derived from the append-only collector log. It does not change the collector, production schedules, models or ledgers.

Raw Crown response files and full per-FID inventories are intentionally not committed here. Their SHA manifests and exact local file locations are recorded in the local audit output and handoff.

## Reconciled history inventory and newly mapped leagues — 2026-11-22

- After the 15 previously identified schedule candidates finished pagination, the all-source UTC 2019–2026 inventory was rebuilt from saved schedule pages, the expanded fixture universe, M1 cache, Crown fixture metadata, and the verified supplemental TotalCorner ledger. Snapshot: **141,623 unique FIDs / 80 provider league IDs / 640 league×UTC-year rows**; 135,167 verified FT and 6,456 unresolved. The supplemental source contributes 27,503 distinct FIDs/record versions; relative to the previous 134,839-FID inventory, the union increased by 6,784 unique FIDs.
- Existing Crown movement data remains 52,999 FIDs / 4,429,709 quote rows. The recovered schedule pages added no corresponding movement quote rows. Historical source-event quotes and actual HTTP receive times remain separate.
- A local exact-name audit checked 105,871 SHA-anchored Crown response files and 105,909 saved MR1 result-check attempts, accepting only exact TotalCorner `l`/`l_id` pairs whose response SHA validated. It mapped 35 further M7 competition names to 35 provider IDs not yet in the schedule inventory, bringing the explicit known union to 115 IDs. Three names remain unmapped: `Bulgaria B PFG`, `Georgia First League`, and `Iceland 1 Deild`; no similar-name inference was used.
- The existing resumable schedule collector is now processing those 35 IDs. At the 2026-11-21 16:30 UTC checkpoint, it had read 7 of 22 pages for provider ID 877 and added 210 FIDs, with 0 failed pages/conflicts. This is an active intermediate snapshot, not a complete recovery. No Crown batch is started while TotalCorner pagination runs.
- Checkpoint JSON: `schedule_recovery_checkpoint_20261122T1630Z.json`. Mapping evidence and target list: `crown_raw_exact_league_name_mapping_2019_2026.json` and `m7_named_competition_schedule_targets_20261122.json`.

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

## Refreshed schedule and inventory checkpoint — 2026-11-21 15:13 UTC

- A live snapshot of 659 verified TotalCorner response pages has been normalized to 19,429 unique FIDs. The separately verified process checkpoint had 659 request attempts, 19,309 newly observed target FIDs, and had moved from Scotland Championship to Serbia Prva Liga (6/87 pages); the append-only response log can lead the checkpoint by one page.
- Reconciled all-source inventory: 133,549 unique target-period FIDs across 74 provider league IDs and 592 league × UTC-year rows. Verified FT 128,105; unresolved FT 5,444. Crown movement quotes remain 52,999 FIDs / 4,429,709 rows; 80,550 inventory FIDs still have no saved movement quote row. This is not a claim that Crown has no market: capture absence and explicit no-quote responses remain separate.
- The normalized supplemental file is a time-stamped intermediate snapshot while the collector continues. See `COLLECTION_CHECKPOINT_20261121T1513Z.md`, `supplemental_schedule_progress_snapshot_20261121T1513Z.json`, and `CHECKPOINT_SHA256_20261121T1513Z.txt` for exact inputs, results and digests.

## Historical Crown raw-cache re-audit — 2026-11-21 15:20 UTC

- Re-ran the read-only raw-response/cache audit against the 133,549-FID inventory. It inspected 104,365 existing raw Crown response files; all 104,365 matched an existing SQLite raw-response SHA reference, with zero parse/identity issues and zero unanchored files.
- The cache contained 52,999 movement FIDs / 4,429,709 movement rows and 49,621 summary-bearing response records / 99,242 summary rows; all available movement and summary response hashes were already indexed in the corresponding historical layer. No raw-cache movement rows were available to import from this snapshot.
- Of 19,429 supplemental schedule FIDs, zero had a valid Crown raw-cache response. Thus their currently missing movement quotes require a new authorized historical request when the active TotalCorner pagination is idle; no alternative bookmaker or synthesized quote was used.
- Audit script: `audit_offline_raw_crown_inventory.py`; sanitized result and per-response digest ledger are in `offline_raw_Crown_response_inventory_audit_2019_2026.json` and `offline_raw_Crown_response_index_audit_2019_2026.jsonl.gz`. This audit made no API requests and no SQLite writes.

## Refreshed inventory after active schedule recovery — 2026-11-21 15:24 UTC

- Normalized 702 verified pages / 20,719 target-period FIDs in the current supplemental snapshot; all-source inventory is 134,839 unique FIDs across 74 provider league IDs. The active collector had discovered 20,599 new FIDs and reached Serbia Prva Liga ID 337, page 49/87.
- Verified FT is 129,337; unresolved FT is 5,502. The 497 provider-season buckets sum to the global inventory and each bucket's verified plus unresolved FT equals its fixture count. Movement quote coverage remains 52,999 FIDs / 4,429,709 rows; 81,840 inventory FIDs currently lack a movement quote row.
- No raw Crown cache matched any of the 20,719 supplemental FIDs. Full inventory, FT readiness and raw Crown cache audits were rerun and stored with SHA manifests at `COLLECTION_CHECKPOINT_20261121T1523Z.md` and `CHECKPOINT_SHA256_20261121T1523Z.txt`.

## Explicit league-scope union audit — 2026-11-21 15:32 UTC, expanded with M7 name inventories

- `audit_league_scope_union_2019_2026.py` reconciles explicit provider-ID sources: formal M1 scope (51 IDs), expanded schedule universe (64), prior scoped schedule candidates (15), plus the observed M1-history-only ID 27391. This gives an 80-ID known union. The latest consolidated inventory has 74 IDs and six unmerged candidate IDs: 542, 765, 10808, 10989, 11958, 11959. At the current live check, ID 542 was at page 50/57 and ID 765 had started; those newer responses were not yet merged into the public inventory.
- A further local-config audit found three named M7 inventory lists with 73 unique exact competition names. Existing exact ID/name sources map 35 names; **38 remain without a traceable provider ID**. The unresolved names and which M7 list contains them are recorded in the JSON. The `deprecated_second_tier_totalcorner_exact` list is retained as historical inventory evidence only; it is not applied as a production filter.
- The explicit ID union is not an exhaustive-ever claim. Continue reconciling the 38 name-only competitions against local schedule/ID mapping records and available source discovery, and add verified mappings or documented unavailability. The audit used zero network requests and no Crown/SQLite writes.
- Machine-readable results and input hashes: `league_scope_union_2019_2026.json`; rerun using `audit_league_scope_union_2019_2026.py` after the moving schedule inventory is consolidated.

## Raw-schedule provenance and live pagination checkpoint — 2026-11-21 16:07 UTC

- Extended the zero-network scope audit to inspect saved TotalCorner shared-history exports, M1 schedule pages, M7 schedule refreshes, and the active supplemental response archive. The raw M7 lists remain 73 exact names: 35 map to a known provider ID and 38 are still unresolved; no ID was inferred from a similar competition name. The audit records 56 raw-source evidence rows across 71 cached files. An independent read verified each recorded exact ID/name pair, body SHA and applicable sidecar SHA with zero mismatches.
- This confirms source evidence for Wales Championship North / provider ID 11958 from its saved `/v1/league/schedule/11958` response, with matching response and sidecar SHA. The mapping count remains 35; this is additional provenance, not six new mappings. The output retains the complete unresolved-name list and marks the union incomplete.
- Supplemental TotalCorner process PID 10634 remains live. At the checkpoint, 935 requests had been issued and 27,368 new target-period FIDs were observed. IDs 15, 57, 63, 121, 128, 210, 252, 270, 337, 542, 765, 10808, 10989 and 11958 had reached the 2019 cutoff/provider end without recorded failed pages; ID 11959 Wales Championship South was at page 38, 1,140 FIDs, with page total not yet reported. The live response pages are not yet merged into the reconciled inventory. Do not start Crown collection or issue another TotalCorner request while this process is active.
- Current inventory remains the earlier consolidated snapshot: 74 provider IDs, with six known candidate IDs 542, 765, 10808, 10989, 11958 and 11959 not yet merged. This count must be refreshed after pagination exits and all current pages are consolidated. The scope audit made zero network requests and zero SQLite writes.
- Audit script/JSON SHA256: `287980b040261772b18d1b1575cdafd20ade65c842aba5ee5e5ca2cc93f88000` / `02a0f91f7e0715a75200aa91f63aec3c1fbed65a6069c39add9306e2efa3f6f0`.

## Exact-name supplemental provider pages and live schedule recovery — 2026-11-21 17:02 UTC

- The archived-Crown-response mapping audit still correctly reports zero response-derived provider IDs for `Bulgaria B PFG`, `Georgia First League`, and `Iceland 1 Deild`. A separate exact provider-page check verified IDs 10653, 702, and 114 respectively; the three were added as explicitly distinct page-verified mappings (not fuzzy name matches). Evidence URLs are recorded in `m7_named_competition_schedule_targets_20261122.json`.
- The current live process loaded the original 35 SHA-anchored exact Crown-response mappings; it had completed IDs 877, 11559, 11260, 227 and 119, adding 4,663 unique schedule FIDs. ID 911 was in progress at page 10/56, bringing its partial count to 300 and process total to 4,963 FIDs. The three page-verified mappings were added to the on-disk 38-target follow-on input but are queued until this live process exits. No page failures or record-version conflicts had occurred in these six targets.
- For the five finished leagues only, read-only lookup against the Crown SQLite found no capture or Asian quote rows for 4,663 newly recovered FIDs. This is an interim cache-coverage observation, not evidence that every match lacked an AH market. No Crown requests were started during TotalCorner pagination.
- Exact progress, process identity and input/source hashes are snapshotted in `schedule_recovery_checkpoint_20261121T1702Z.json`; pagination remains active and incomplete. A follow-on resumable run will process the 3 supplemental page-verified IDs after this collector exits.

## Provider-scope audit refresh — 2026-11-21 17:13 UTC

- `audit_league_scope_union_2019_2026.py` now uses a distinct evidence class for the three exact TotalCorner league pages; it does not mislabel them as saved Crown-response mappings. Re-run result: all **73/73 exact M7 competition names** have one provider ID, the currently explicit union is **118 provider league IDs**, and **38 IDs** remain absent from the reconciled fixture inventory.
- At the same checkpoint, the active 35-target run had made 225 requests and recorded 6,514 new FIDs: six targets complete (6,184 FIDs total) and Bulgaria Second League ID 26528 at page 11/39 (330 partial FIDs). It was waiting while the existing unified settlement job was active; no request was made during the wait.
- The current 38-target queued input SHA and private live progress/source ledger hashes are recorded in `schedule_recovery_checkpoint_20261121T1713Z.json`. The 3 page-verified league IDs remain queued for a resumable follow-on after the active 35-target run exits.

## Crown source-cache preparation — 2026-11-21 17:18 UTC

- Completed schedule subset is now 7,353 FIDs across seven finished provider leagues. A read-only lookup found 0 corresponding SQLite captures, 0 Asian quote rows, and 0 files in the collector's own historical raw cache or the two supported legacy response directories. The database main-file SHA matched the prior inventory snapshot (`292ccb…d298`). The upcoming batch therefore requires source requests for any rows not recovered from another cache, while preserving actual no-quote and failed-response statuses separately.
- Added `build_recovered_fixture_manifest.py` to emit deduplicated `match_id` inputs with fixture identity and TotalCorner page/response SHA provenance. Extended `safe_window_collection_driver.py` to select `summary` or `movement` separately and retain the collector's default 5.2-second pacing and scheduled-job guard. Failed IDs are retained in collector logs for a later explicit retry pass; no unbounded automatic retry loop is used.
- These utilities have not yet been used to issue Crown requests. The TotalCorner schedule pager remains active; current checkpoint is in `schedule_recovery_checkpoint_20261121T1718Z.json`.

## Named-competition schedule recovery checkpoint — 2026-11-21 17:54 UTC

- The active TotalCorner schedule process (PID 65966) had completed 11 of its 35 launch-time targets: 13,092 unique schedule FIDs from 485 request attempts. Egypt Division 2 (ID 417) was at page 36/114 with 1,080 rows at the checkpoint; the process remains resumable and the 35-target batch was not complete.
- A read-only cross-reference of those 11 completed leagues found 12,087 provider rows with `status=full` and numeric scores, and zero matching Crown SQLite capture or AH quote FIDs. This is a local-cache gap, not evidence that the provider has no historical prices.
- The process launch-time target SHA is `9c698b6e74cb58a43038be4f9d21eb40832de711a821acb1a524c64748d076d9` (35 entries). The current queued file has 38 exact IDs, SHA `effae3204c03736cb3b27dbfbda4e3b9e27c1b093df17628a532a62382d6f778`; IDs 10653, 702 and 114 remain queued for a follow-up after the active process exits.
- Checkpoint and private source-ledger hash references are in `schedule_recovery_checkpoint_20261121T1754Z.json` (SHA `c1f1fc695daf97489d67cb4da28f8075a9ab0b0760d308ce048397d52c901ce0`). No Crown request or SQLite write occurred. Schedule reconciliation, complete inventory refresh, and all Crown summary/movement and unresolved-FT queues remain unfinished.

## 2019–2022 audit of the three example leagues — 2026-11-21 17:24 UTC

The existing inventory already contains schedules for IDs 51, 61, and 10480 in 2019–2022. Across those 12 league-year rows it has 2,594 FIDs, 2,513 verified full-time scores, and 81 unverified results. There are 2,251 historical movement captures, all explicitly `NO_CROWN_AH_QUOTES`; summary quote coverage and movement quote rows are both zero. Another 343 FIDs lack a movement capture, with one recorded failed attempt. These are Crown price gaps, not absent schedules. Full row-level aggregates and the source CSV SHA are in `known_2019_2022_league_gap_audit.json`.

## Schedule pager checkpoint — 2026-11-21 17:24 UTC

The active 35-target run has 305 successful page requests and 8,898 newly discovered FIDs: eight leagues are complete (8,238 FIDs), and Cyprus Division 2 (571) is at page 22/56 (660 rows so far). For all eight completed leagues, a read-only cross-reference found no corresponding Crown SQLite capture, quote row, or supported local raw file. Checkpoint provenance is in `schedule_recovery_checkpoint_20261121T1724Z.json`.

## Current schedule and Crown backlog checkpoint — 2026-11-21 17:30 UTC

The live schedule run is at 321 successful page requests / 9,378 new FIDs. Eight of 35 targets are complete (8,238 FIDs); Cyprus Division 2 ID 571 is at page 38/56, with 1,140 partial rows. The previous reconciled 141,623-FID inventory has 38,927 FIDs without a historical movement capture and 91,423 without a historical summary capture; these baselines will be rebuilt after new schedules merge. The 35-target process remains active, and the 3 supplemental exact-page IDs remain queued. Details and hashes: `schedule_recovery_checkpoint_20261121T1726Z.json`.

## FT refresh queue prepared — 2026-11-21 17:30 UTC

- Existing TotalCorner/Crown match responses contain fixture `status`, `hg`, and `ag` fields, so a refreshed historical response can also help verify missing results while preserving the raw response. This is source collection, not score inference.
- From the current 6,456 unresolved-FT inventory, the offline manifest builder excludes 291 fixtures classified by the existing readiness audit as future/not due and includes the remaining 6,165 past-due unresolved/status-not-full FIDs. The manifest is private at `/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/crown_quote_recovery/ft_refresh_candidates_baseline.jsonl`, SHA `b2f185c063e1b9a6f2fc2df3ebe4e9b4c69ade00ed24a76527586a4e23eed0f7`. It has not been sent to the API.
- `safe_window_collection_driver.py` now forwards the existing collector's `--refresh` flag so an intentional FT-refresh batch can request a new immutable historical response; cache-reuse and data-layer runs remain separate. No Crown request has been started.

## Deduplicated collection queue snapshot — 2026-11-21 17:37 UTC

- For the then-current partial 38-target ledger plus the 141,623-FID inventory, read-only queue builders produced 49,948 FIDs without historical movement capture and 102,444 without historical summary capture. These are intermediate counts; rebuild after pagination/reconciliation before running either queue.
- The unresolved FT set is 6,165 past-due FIDs. Of these, 5,930 already lack movement capture and are included in the movement queue; only 235 have a movement capture and need a separate forced historical refresh to avoid duplicating the large movement batch. No request was issued when building these inputs.
- Nine existing 2026 fixture IDs have conflicting source kickoff dates. Their FID/team/league identity is retained, but the queue leaves `kickoff_utc` unset so the data collector uses the start value in the exact provider response it consumes; no date was guessed. Aggregate queue details and hashes are in `crown_queue_baseline_20261121T1737Z.json`.
