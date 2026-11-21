# 2019–2026 full-history recovery checkpoint

Snapshot time: 2026-11-21T15:09:36Z. Collection remains active and incomplete.

## Live supplemental schedule recovery

The existing TotalCorner recovery process (PID 10634) was confirmed running while this snapshot was created. The append-only request log has 636 successful page responses; its checkpoint records 18695 newly discovered target-period FIDs and 4 identity conflicts. Current target page state:

| League ID | Competition | Pages read / reported | Target FIDs | New FIDs | Failed pages |
|---:|---|---:|---:|---:|---|
| 15 | Spain Segunda | 126 / 196 | 3731 | 3611 | none recorded |
| 57 | Portugal Segunda Liga | 80 / 149 | 2366 | 2366 | none recorded |
| 63 | Ukraine Persha Liga | 38 / 65 | 1101 | 1101 | none recorded |
| 121 | Netherlands Eerste Divisie | 102 / 157 | 3017 | 3017 | none recorded |
| 128 | Japan J2-League | 112 / 184 | 3307 | 3307 | none recorded |
| 210 | China Division 1 | 66 / 98 | 1934 | 1934 | none recorded |
| 252 | Israel Leumit Liga | 80 / 122 | 2369 | 2369 | none recorded |
| 270 | Scotland Championship | 33 / 76 | 990 | 990 | none recorded |

Targets marked as reaching the 2019 cutoff are only complete for their target-period pagination as verified so far; remaining provider IDs still need examination. Do not infer full-history completion from successful-page counts.

## Reconciled inventory at this snapshot

- `schedule_fids_union`: 129,576
- `totalcorner_schedule_fids`: 113,634
- `expanded_universe_fids`: 96,503
- `supplemental_schedule_fids`: 15,456
- `crown_fixture_metadata_fids`: 9
- `M1_history_cache_fids`: 68,196
- `T6_priced_inventory_fids`: 48,890
- `complete_FT_fids`: 124,387
- `unverified_FT_fids`: 5,189
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
- `uncovered_schedule_fids`: 76,577

FT readiness as of 2026-11-21T15:06:43.580083Z: 5,189 unresolved, future/not-due 300, past-kickoff with missing/unknown status 4,254, explicitly non-full status 635; 4,766 contain placeholder 0:0. No score was inferred.

## Newly reconciled Crown-only fixture identities

The metadata-only overlay contains nine UTC-scope FIDs in Portugal Primeira Liga (ID 51), plus one China-date boundary item outside UTC 2019–2026. These are not TotalCorner schedule-page rows, AH quotes, or verified FT. The nine in-scope items are kept distinct because the referenced live summary response SHA had no Crown bookmaker entry. See `crown_only_fixture_identity_candidates_2019_2026.json` and its JSONL.gz evidence.

## Data boundary and next work

Inventory and FT-readiness audits made zero API requests and zero SQLite writes. The live TotalCorner schedule recovery is separate and was already running. Continue all identified league schedule sources; then refresh and reconcile Crown raw quote coverage over the expanded unique-FID union, preserve source-event and response-received times, and resolve FT/status gaps from trustworthy exact-ID sources. No model/backtest or production action was performed.

Machine snapshot: `supplemental_schedule_progress_snapshot_20261121T1507Z.json`.
