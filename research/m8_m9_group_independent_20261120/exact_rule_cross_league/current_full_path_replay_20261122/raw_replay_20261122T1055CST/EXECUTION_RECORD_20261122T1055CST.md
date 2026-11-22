# M8 frozen exact-rule cross-league replay — refreshed Crown snapshot

Execution time: 2026-11-22 10:55 CST. This is a separate refresh run; the earlier committed `raw_replay_20261122/` directory remains unchanged.

## Snapshot and frozen inputs

- Source: existing local Crown SQLite, opened read-only for a SQLite online backup while the authorized historical collection driver was active. The backup passed `PRAGMA quick_check=ok`; SHA256 `090bb6a8154d41ff8b756ee0e1177f59f61123cd13c9e9d5ea6e296038162e3e`. No Crown request was issued by this replay.
- Scope stayed fixed at the original `schedule_universe.jsonl` cohort: 96,504 schedule rows, 18,374 unique FIDs outside the frozen 49 provider-league IDs. Schedule SHA256 `a9d48b40cba84e5bf49f490b4b25bada9bc12a6266e6da0eed51c063166b8258`.
- Frozen membership remains 10,294 FIDs, SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`, +236.015U. The original exact base/A–G helper and independent G model sources were re-hashed in `INPUT_SHA256_MANIFEST.json`.

## Replay and verification

- Reproduction commands:

```bash
CROWN_SQLITE_PATH=/path/to/crown_snapshot.sqlite3 CROWN_SQLITE_IMMUTABLE=1 python3 run_exact_rule_cross_league_from_snapshot.py
CROWN_SQLITE_PATH=/path/to/crown_snapshot.sqlite3 CROWN_SQLITE_IMMUTABLE=1 python3 verify_exact_rule_cross_league_from_snapshot.py
python3 build_exact_rule_cross_league_deliverables.py
```

- Coverage is unchanged: 11,266 movement captures explicitly report no AH quotes; 6,967 FIDs have complete T6/T3/T1 paths; 139 have pregame quotes but no quote at/before T6; 2 have no valid pregame AH row. Missing path cases remain data insufficiency, not strategy misses.
- The unchanged frozen rules assign 1,273 unique outside-49 FIDs after priority de-duplication: +10.750U, ROI +0.844462%, MDD 26.645U, 3.306 orders per target-observed ISO week (3.281 over the 388-week calendar span). Live-mode receipt FIDs in the target cohort: 0.
- Independent validation re-read raw Crown bodies and independently recalculated Asian Handicap outcomes: 1,273/1,273 passed; issues `{}`. It also checked all 18,374 target FIDs for live-mode captures; count 0.
- Compared with the earlier committed `raw_replay_20261122/` ledger: 1,273 FIDs on each side and zero added, removed or changed rows across group, side, net U, T1 AH line, both odds, FT, raw-response SHA and selected quote event time. All fresh input and output digests passed.

## Interpretation and delivery

This refresh confirms the previous historical replay against a later read-only Crown snapshot; it does not turn historical source-event quotes into real pregame receipts. The result remains research-only and is not Telegram or formal-ledger performance. It did not change the frozen eight groups, M9/M1/MR1, production, Telegram, formal ledger, collector behavior, or scheduling.

This new run is part of the existing `research/m8-m9-groups` branch and PR #67 (`main` base, OPEN, not merged). The shared worktree's pre-existing formation/referee untracked files were left untouched and excluded.
