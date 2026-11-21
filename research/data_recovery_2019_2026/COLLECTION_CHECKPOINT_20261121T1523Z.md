# 2019–2026 full-history recovery checkpoint

Snapshot: 2026-11-21T15:24:46Z. The collection goal remains active and incomplete.

## Live schedule-source recovery
PID 10634 was confirmed running. The append-only request log shows 701 successful page responses; progress.json records 702 attempts and 20599 newly discovered FIDs. Four old source-record SHA changes remain classified as source-version differences in preexisting ID15 cache rows; no team/league identity was changed. Current targets:

| League ID | Competition | Pages / provider total | Target FIDs | New FIDs | Failed pages |
|---:|---|---:|---:|---:|---|
| 15 | Spain Segunda | 126 / 196 | 3731 | 3611 | none |
| 57 | Portugal Segunda Liga | 80 / 149 | 2366 | 2366 | none |
| 63 | Ukraine Persha Liga | 38 / 65 | 1101 | 1101 | none |
| 121 | Netherlands Eerste Divisie | 102 / 157 | 3017 | 3017 | none |
| 128 | Japan J2-League | 112 / 184 | 3307 | 3307 | none |
| 210 | China Division 1 | 66 / 98 | 1934 | 1934 | none |
| 252 | Israel Leumit Liga | 80 / 122 | 2369 | 2369 | none |
| 270 | Scotland Championship | 49 / 76 | 1424 | 1424 | none |
| 337 | Serbia Prva Liga | 49 / 87 | 1470 | 1470 | none |

The supplemental normalized snapshot has 20,719 unique FIDs across 701 logged success pages (the consolidator's 702-page count includes one preexisting SHA-verified diagnostic page). SHA256 `3d2610b38d1c288e62bd29adb770175d30b3cd04e1c67e1ccb0052c06bfc6f19`. The live collector may have moved since this point.

## All-source inventory as of the joined snapshot
- `schedule_fids_union`: 134,839
- `totalcorner_schedule_fids`: 113,634
- `expanded_universe_fids`: 96,503
- `supplemental_schedule_fids`: 20,719
- `crown_fixture_metadata_fids`: 9
- `M1_history_cache_fids`: 68,196
- `T6_priced_inventory_fids`: 48,890
- `complete_FT_fids`: 129,337
- `unverified_FT_fids`: 5,502
- `external_verified_FT_fids`: 1
- `any_Crown_capture_fids`: 103,602
- `movement_with_quotes_fids`: 52,999
- `movement_capture_fids`: 102,696
- `movement_quote_rows`: 4,429,709
- `distinct_movement_source_event_timestamps`: 4,429,067
- `summary_with_quotes_fids`: 49,144
- `summary_quote_rows`: 99,520
- `live_quote_receipt_fids`: 95
- `live_quote_rows`: 278
- `explicit_no_Crown_AH_movement_fids`: 49,697
- `failed_attempts`: 951
- `uncovered_schedule_fids`: 81,840

The 497 source-season buckets sum to 134,839 FIDs; complete FT plus unresolved FT mismatch buckets: 0. Seasons are carried only where a source provides them.
FT readiness as of 2026-11-21T15:22:52.164072Z: 5,502 unresolved: future/not due 302; past kickoff with missing/unknown status 4,531; explicit non-full statuses 669; placeholder 0:0 5,061. No scores were inferred.

## Crown source and raw-cache reconciliation
The 104,365 existing raw Crown response files still have SHA anchors and no parse/identity errors. No existing raw Crown response matched the 20,719 supplemental schedule FIDs. Current movement layer remains 52,999 FIDs / 4,429,709 rows; the schedule expansion raised the inventory without fabricating or substituting any AH quotes. New historical movement requests wait until the existing TotalCorner page collector is idle.

## Next recovery work
Continue every unresolved provider competition through the 2019 UTC boundary, reconcile each schedule/FT version and source mapping, then recheck missing Crown historical movement through the authorized collector. Keep empty responses and failures distinct; do not infer FT from placeholders. No strategy or model work was performed.
