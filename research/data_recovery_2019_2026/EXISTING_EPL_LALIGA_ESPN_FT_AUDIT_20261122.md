# Existing EPL/La Liga ESPN FT archive audit

Generated 2026-11-22 (UTC; Crown state snapshot at 02:53:39–02:53:45Z). This is a score-source reconciliation inside the ongoing 2019–2026 history inventory task. It is not an odds source, model test, or profitability study.

## Result

The existing local file `epl_laliga_crown_5seasons/英超_西甲_2021-22至2025-26_Crown亚洲盘.csv` contains 3,800 unique TotalCorner FIDs and references archived ESPN result enrichment. Its SHA256 is `05a84544b25cf88ba2fb078f736e231b478a4dd917b957858d158ad2fe3643ed`. The audited enrichment has 43 supplemental result rows, 12 score corrections, and no ambiguous identity rows. The 12 saved raw season responses cover English Premier League and La Liga seasons 2021–2026; exact response hashes are recorded in `epl_laliga_espn_ft_archive_reconciliation_20261122.json`.

The strict audit produced:

| Evidence class | FIDs | Handling |
| --- | ---: | --- |
| Raw ESPN FT supplement rows verified | 43 | Full-time status, score, raw response SHA, exact fixture identity checked |
| New verified FT FIDs in the current unresolved queue | 42 | Appended as separately sourced FT evidence |
| Already verified with same score | 1 | Retained as cross-source corroboration; no duplicate result |
| Verified ESPN FT scores conflicting with stored TotalCorner scores | 12 | Preserved in a conflict-only artifact; no score overwrite |
| Failed raw SHA/FID/status/kickoff/identity checks | 0 | No row silently accepted |
| Network requests / Crown prices used for FT | 0 / 0 | Fully offline audit |

The merged inventory remains 203,962 unique FIDs across the currently audited 118 provider league IDs. Verified FT increases from 193,476 to **193,518**; unresolved FT falls from 10,486 to **10,444**. Inventory FIDs, kickoff values, Crown quotes, and stored TotalCorner scores were not rewritten by the external evidence layer.

## Validation rules

For each accepted result, the auditor verifies the archived raw ESPN response against its SHA; finds exactly one matching ESPN event ID; requires `STATUS_FULL_TIME` and `completed=true`; checks the numeric home/away score; checks raw event kickoff; checks raw home/away team names against the saved season-specific mapping; then requires exact TotalCorner FID, provider league, home/away IDs and canonical names in the current inventory. The 3,800-row CSV is used as an FID crosswalk, not as a substitute score authority.

The audit's baseline denominator is frozen in `unverified_FT_candidates_pre_epl_laliga_20261122.jsonl.gz` (10,486 FIDs; SHA256 `b546ad74b816d5f41a0651b56ad5e1eeb6d9084453fbe3759d6de3e898af34d6`). This makes the 42-new / 1-already-verified classification reproducible after the overlay has been merged into current inventory. The new 42-row overlay is `epl_laliga_espn_verified_ft_overlay_20261122.jsonl`. The 12 conflicting rows are in `epl_laliga_espn_verified_ft_conflicts_20261122.jsonl`. The inventory join preserves `source_event_kickoff_utc` separately from canonical TotalCorner `kickoff_utc`. FID `133320493` has a 152-second difference (ESPN event at 20:00:00Z; inventory at 20:02:32Z); exact FID, league, team IDs and names corroborate identity, and the TotalCorner timestamp remains canonical and unchanged.

## Remaining FT readiness

The reclassified 10,444 unique unresolved FIDs contain 298 future-dated events, 2 missing kickoff times, 9,032 past events with missing/unknown status and 1,112 provider-reported non-full statuses. Those labels are retained literally; no state is interpreted as cancelled, postponed, abandoned or completed. `0:0` appears as an observed placeholder on 9,722 records and is never promoted to verified FT. The classification used zero network requests and does not itself establish any result.

## Reproduction and files

Run from the repository root:

```bash
python3 research/data_recovery_2019_2026/audit_epl_laliga_espn_ft_archive_20261122.py
python3 research/data_recovery_2019_2026/reconcile_53_league_schedule_union_20261122.py
python3 research/data_recovery_2019_2026/classify_merged_unverified_ft_readiness_20261122.py
python3 research/data_recovery_2019_2026/build_recovery_checkpoint_20261122.py
python3 research/data_recovery_2019_2026/build_ft_audit_sha_manifest_20261122.py
```

The first command strictly rebuilds the overlay against the frozen pre-overlay gap. The second independently revalidates raw ESPN evidence and appends provenance to the inventory while isolating score conflicts. The third regenerates the current unresolved queue readiness classification. The fourth captures the active Crown collection state and a read-only SQLite/WAL snapshot. The fifth validates and writes the audit digest list. Inputs, outputs, exact hashes, and process state are listed in `CHECKPOINT_SHA256_20261122T0253Z.txt`.

Raw Crown/ESPN response bodies, the SQLite database, and the full licensed fixture inventory remain local and are not included in the public repository. Historical Crown receive times remain separate from source-event times. This work does not claim all leagues, FT results, or Crown prices are complete, and it did not run strategy/backtest work or touch Telegram, the formal ledger, or production collection settings.
