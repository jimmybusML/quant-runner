# 2019–2026 full-history recovery checkpoint

Snapshot: 2026-11-21T15:13:33Z. The collection and reconciliation task remains active and incomplete.

## TotalCorner supplemental schedule recovery

Collector PID 10634 was confirmed running. The append-only request log has 658 successful page responses; the live progress file records 659 request attempts, 19309 new target-period FIDs and 4 identity conflicts. Current target status:

| League ID | Competition | Pages / source total | Target FIDs | New FIDs | Failed pages |
|---:|---|---:|---:|---:|---|
| 15 | Spain Segunda | 126 / 196 | 3731 | 3611 | none |
| 57 | Portugal Segunda Liga | 80 / 149 | 2366 | 2366 | none |
| 63 | Ukraine Persha Liga | 38 / 65 | 1101 | 1101 | none |
| 121 | Netherlands Eerste Divisie | 102 / 157 | 3017 | 3017 | none |
| 128 | Japan J2-League | 112 / 184 | 3307 | 3307 | none |
| 210 | China Division 1 | 66 / 98 | 1934 | 1934 | none |
| 252 | Israel Leumit Liga | 80 / 122 | 2369 | 2369 | none |
| 270 | Scotland Championship | 49 / 76 | 1424 | 1424 | none |
| 337 | Serbia Prva Liga | 6 / 87 | 180 | 180 | none |

The request log and progress JSON are separate append/checkpoint views and may differ by an in-flight page. Remaining identified provider league candidates still need to be paged.

## Current all-source inventory
- `schedule_fids_union`: 133,549
- `totalcorner_schedule_fids`: 113,634
- `expanded_universe_fids`: 96,503
- `supplemental_schedule_fids`: 19,429
- `crown_fixture_metadata_fids`: 9
- `M1_history_cache_fids`: 68,196
- `T6_priced_inventory_fids`: 48,890
- `complete_FT_fids`: 128,105
- `unverified_FT_fids`: 5,444
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
- `uncovered_schedule_fids`: 80,550

Normalized supplemental snapshot: 19,429 unique FIDs / 659 verified page responses, SHA256 `b0c0a1488b917edffc2c54bd670b0b19e98d20d0b30d1d12b4101c863b17a065`. It was consolidated while the live collector continued, so it is a checkpoint, not a terminal ledger.

FT readiness at 2026-11-21T15:13:33.238161Z: 5,444 unresolved; future/not due 305; past kickoff with missing/unknown status 4,474; provider reports non-full 665; placeholder 0:0 5,006. No score was inferred.

Crown-only metadata overlay: 9 in-scope Portugal Primeira Liga future fixture IDs plus one China-date/UTC-2018 boundary item. These have no Crown bookmaker AH quote in the referenced response and are not verified FT. The overlay remains a distinct metadata source.

## Next collection work

Continue all candidate league pages to the 2019 UTC boundary, refresh FID/season/year matrices, then reconcile all newly found FIDs against saved Crown raw response caches and recover any obtainable missing historical AH movement. Continue exact-ID FT reconciliation from trustworthy sources. No strategy or model research was performed.
