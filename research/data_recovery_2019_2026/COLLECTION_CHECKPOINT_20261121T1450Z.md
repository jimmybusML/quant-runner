# 2019–2026 all-league historical recovery checkpoint

Snapshot time: 2026-11-21 14:50 UTC. This is an interim coverage view while schedule recovery is still active.

## Current supplemental TotalCorner recovery

The serialized collector (PID 10634) has logged 523 successful request attempts and 15,336 new FIDs. It waits when known scheduled settlement jobs are running. Current page status:

| League ID | Competition | Pages read / reported | Target FIDs | Status |
|---:|---|---:|---:|---|
| 15 | Spain Segunda | 126 / 196 | 3,731 | Reached 2019 boundary; no failed pages |
| 57 | Portugal Segunda Liga | 80 / 149 | 2,366 | Reached 2019 boundary; no failed pages |
| 63 | Ukraine Persha Liga | 38 / 65 | 1,101 | Reached 2019 boundary; no failed pages |
| 121 | Netherlands Eerste Divisie | 102 / 157 | 3,017 | Reached 2019 boundary; no failed pages |
| 128 | Japan J2 | 112 / 184 | 3,307 | Reached 2019 boundary; no failed pages |
| 210 | China Division 1 | 65 / 98 | 1,934 | Still paging; no failed pages |

Nine of the previously unresolved provider competition IDs remain to be checked after this ID finishes.

## All-source inventory

- 129,567 unique schedule FIDs across 71 provider league IDs; 568 league × UTC-year cells.
- Verified FT: 124,387; unresolved FT: 5,180.
- Crown movement quotes: 52,999 FIDs / 4,429,709 rows; explicit successful no-AH-movement responses: 49,697 FIDs; failed attempts: 951; schedule FIDs without movement quotes: 76,568.
- Crown summary quotes: 49,144 FIDs / 99,520 rows.
- Nine source identity/date conflicts remain isolated; no bad schedule pages.

The normalized supplemental schedule has 15,456 record versions, SHA256 `eba93d676ab97ad4b3cda29ea8b5ffab67ee893a92ebc40ce6c959cb3ae60125`.

## Season coverage correction

The first season matrix revision counted pre-2019 cached fixtures. It has been recomputed from the normalized inventory already filtered to 2019–2026. Its 494 league/source-season buckets sum to exactly 129,567 unique FIDs, matching the target-period schedule inventory. Within each bucket, verified plus unresolved FT equals the schedule count. No source season labels are inferred from kickoff date. Source season is unknown for 33,064 FIDs (represented as 71 league-specific `UNKNOWN_SOURCE_SEASON` buckets).

## Unresolved FT and quote provenance

Strict Crown raw response review covers all 5,180 unresolved FT candidates: 456 candidates have captures; 1,493 deduplicated raw responses were checked against SHA, FID, provider league, UTC kickoff, exact teams, full status and integer scores. No new FT qualifies. Issues: 0; API requests: 0; SQLite writes: 0. Non-full or missing statuses remain unresolved.

The 62-response offline summary import independently passed exact reference checks (62 captures / 124 quote rows). The older complete import ledger remains intact; 70 contemporaneous historical movement captures outside this import reference list were excluded from that batch check, without altering their recorded receive times.

## Status

Current evidence and hashes are in `supplemental_schedule_progress_snapshot_20261121T1450Z.json` and `CHECKPOINT_SHA256_20261121T1450Z.txt`. No strategy research, model training or backtest was performed. After finishing the current schedule source, continue the other provider IDs, then rebuild the Crown movement missing-capture queue over the expanded FID union and recover remaining price histories and independently verifiable results.
