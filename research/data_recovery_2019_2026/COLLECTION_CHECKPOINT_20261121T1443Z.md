# 2019–2026 all-league historical recovery checkpoint

Snapshot time: 2026-11-21 14:43 UTC. The inventory is changing while the supplemental collector runs; this is not a completion claim.

## Active TotalCorner schedule recovery

PID 10634 continues serialized schedule pagination, preserving raw HTTP bodies and append-only logs locally. It waits through identified scheduled settlement jobs. Current totals are 495 successful requests and 14,512 new FIDs.

| Provider league | Pages read / reported | FIDs in target years | Status |
|---|---:|---:|---|
| Spain Segunda (15) | 126 / 196 | 3,731 | Reached pre-2019 boundary, no failed pages |
| Portugal Segunda Liga (57) | 80 / 149 | 2,366 | Reached pre-2019 boundary, no failed pages |
| Ukraine Persha Liga (63) | 38 / 65 | 1,101 | Reached pre-2019 boundary, no failed pages |
| Netherlands Eerste Divisie (121) | 102 / 157 | 3,017 | Reached pre-2019 boundary, no failed pages |
| Japan J2 (128) | 112 / 184 | 3,307 | Reached pre-2019 boundary, no failed pages |
| China Division 1 (210) | 37 / 98 | 1,110 | Still paging, no failed pages |

The six sources above are among 15 provider-league candidates outside the earlier master list. Nine remain to be checked.

## Refreshed all-source inventory

- 128,653 unique schedule FIDs across 71 provider league IDs.
- 568 provider-league by UTC-year cells; 494 provider-league by source-season cells.
- Verified full-time score: 123,514 FIDs; unresolved: 5,139.
- Crown movement quotes: 52,999 FIDs / 4,429,709 rows; explicit movement responses without AH quotes: 49,697 FIDs; failed attempts: 951; schedule FIDs without movement quote rows: 75,654.
- Crown summary quotes: 49,144 FIDs / 99,520 rows.
- Nine source identity/date conflicts remain isolated; no cached schedule page parse errors.

`league_season_coverage_2019_2026.csv` uses only explicit source season labels. It currently has 71 `UNKNOWN_SOURCE_SEASON` league-season buckets; these are missing season metadata, not season guesses. `league_year_coverage_2019_2026.csv` remains the complete calendar-year view.

The normalized supplemental schedule snapshot contains 14,542 source-record versions and has SHA256 `2fbb613478d3ddda211634b8cb1ac3579529551b39039884797e89c4c4d50056`.

## Score and offline Crown checks

The strict raw Crown FT audit checked 5,139 unresolved FIDs; 456 had captures and 1,493 deduplicated raw responses were read. No additional candidate met exact FID, league, kickoff, team, full-status and integer-score checks. Issues: 0; API requests: 0; SQLite writes: 0.

The latest offline normalization batch contains 62 historical summary captures / 124 quote rows. Its exact FID/layer/SHA reference audit passed 62/62 captures and 124/124 quote rows. A broad time-window check also encountered 70 unrelated historical movement captures collected during the same period; those were excluded from the import batch scope, and no capture timestamps were changed. The earlier full import verification ledger remains preserved.

## Status

The coverage matrix, source-season matrix, per-FID raw FT audit, exact batch verification and `PROJECT_HANDOFF.md` reflect this snapshot. No strategy/model/backtest work was performed. Remaining work includes nine external schedule sources, unresolved scores, a rebuilt Crown movement gap queue over the expanded schedule union, and continuing to preserve all obtainable Crown AH timestamps and quotes through the latest available date.
