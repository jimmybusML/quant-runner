# M8 frozen exact-rule cross-league replay — 13:23 CST current snapshot

Execution date: 2026-11-22, Asia/Shanghai. Snapshot transaction began at 13:23 CST; analysis summary timestamp is recorded in `exact_rule_cross_league_summary.json`.

## Inputs and execution

- Worktree branch: `research/m8-m9-groups`; starting HEAD `505e997cacc89a77c71751bff740fdd3ed92419a`. Existing unrelated untracked formation/referee research files were not staged or changed.
- Crown source: `/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3`. A SQLite online backup was opened read-only and passed `PRAGMA quick_check=ok`. Backup path was `/private/tmp/m8_crossleague_crown_snapshot_20261122T1323CST.sqlite3`, SHA256 `b4f1248086ccaf3a0eb3b0a46f8f931e7b93ec7374846788d5f7b82cd2f32394`; the private database copy is not committed.
- Snapshot counts: 156,625 capture rows and 4,598,817 AH quote rows overall. The fixed outside-49 target cohort has 18,374 FIDs, 24,818 capture rows, 7,108 priced FIDs and 456,242 AH quote rows.
- Schedule inventory: 96,504 rows / 64 provider leagues; outside the frozen 49 are 18,374 unique FIDs across 15 leagues, ending 2026-06-01. Schedule SHA256 `a9d48b40cba84e5bf49f490b4b25bada9bc12a6266e6da0eed51c063166b8258`.
- Frozen membership: 10,294 FIDs, SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`; historical baseline +236.015U. No new order overlaps this set.
- Frozen base/A–G rule helpers and original independent G score model were re-used; priority remained base → A → B → C → D → E → F → G. No threshold or rule changed. No M9 substitute was used.
- Reproduction commands (with the private snapshot available):

```bash
CROWN_SQLITE_PATH=/private/tmp/m8_crossleague_crown_snapshot_20261122T1323CST.sqlite3 CROWN_SQLITE_IMMUTABLE=1 python3 run_exact_rule_cross_league_from_snapshot.py
CROWN_SQLITE_PATH=/private/tmp/m8_crossleague_crown_snapshot_20261122T1323CST.sqlite3 CROWN_SQLITE_IMMUTABLE=1 python3 verify_exact_rule_cross_league_from_snapshot.py
python3 build_exact_rule_cross_league_deliverables.py
python3 reconcile_latest_snapshot.py
```

## Results and validation

- Coverage: 11,266 movement captures have no Crown AH quotes; 7,106 FIDs have pre-kickoff source-event AH; 6,967 have complete T6/T3/T1 paths; 139 lack an at-or-before-T6 quote; 2 have no usable pregame AH row. Incomplete cases remain data gaps, not rule misses.
- Frozen exact rules yielded 1,273 unique outside-49 FIDs / +10.750U / ROI +0.844462% / MDD 26.645U, with zero overlap against the 10,294 frozen FIDs. Priority de-duplication followed the frozen order.
- Group results: base 691/+8.580U; A 54/−13.190U; B 217/−5.955U; C 38/+4.710U; D 29/+9.830U; E 52/+2.690U; F 22/+1.120U; G 170/+2.965U.
- Added volume averages 3.306 orders per one of 385 ISO weeks containing target fixtures, or 3.281 per week over the 388-week full calendar span. 2024 added +13.825U, 2025 −8.455U, and 2026 through June 1 −6.260U; the 2024–2026 increment sums to −0.890U.
- Merged by unique FID: 11,567 orders / +246.765U / ROI 2.133354% / MDD 57.565U. New-segment performance remains separately reported.
- Independent raw Crown/FT/settlement verifier re-read 1,273/1,273 orders, including quote response SHA, event-time T1 line and both odds, match identity, FT, AH state and quarter-line split settlement: pass=true, issues empty. Live-mode receipt FIDs in all 18,374 target fixtures: 0. This remains historical source-event replay, not a pregame receipt, Telegram or formal ledger result.
- Compared with the 10:55 CST current-snapshot replay: 1,273 old/new orders, no added/removed/changed FIDs; all 18,374 full coverage rows unchanged. Detailed reconciliation is `latest_snapshot_reconciliation_20261122.json`.
- No TotalCorner/Crown network request was made by this replay. No production model, frozen group member/rule, M9/M1/MR1, Telegram, formal ledger, collector configuration, workflow or schedule was modified.

## Delivery

- This is an update to existing public PR #67, base `main`, state OPEN, not merged: https://github.com/jimmybusML/quant-runner/pull/67
- Only this run directory and the corresponding handoff entry are intended for the next commit; existing unrelated working-tree research remains untouched.
