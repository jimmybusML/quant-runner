# Execution record — M8 exact frozen-rule cross-league replay

- Research workspace: `/Users/mac/Documents/ChatGPT/m8-m9-group-research`
- Branch: `research/m8-m9-groups`
- Pre-research HEAD: `2b3e09f` (the existing three local research commits were retained).
- Execution date: 2026-11-20 UTC.
- Market scope: Crown AH only. Historical quote source-event replay. No production workflow, Telegram, formal order/settlement ledger, collection configuration, M8 frozen membership/rule, M9, M1, or MR1 was modified.

## Inputs fixed for this run

- `crown-drop-expanded-62/schedule_universe.jsonl`: 96,504 unique finished FIDs, 64 provider league IDs; original 49 IDs explicitly excluded; outside inventory 18,374 FIDs across 15 IDs, 2019-01-01 through 2026-06-01.
- Frozen M8 membership: 10,294 unique FIDs, SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`, baseline +236.015U, ROI 2.293%.
- Crown SQLite was opened read-only. Its SHA256 is `86a40523e94e5013c16e626a14820425c2e7ba4f48f4a245235f1ce8b3a3911d`.
- Existing frozen classifier, direction code and AH settlement provenance are documented in `exact_rule_cross_league_summary.json` and `SHA256SUMS.txt`.

## Commands run

```text
python3 -m py_compile research/m8_m9_group_independent_20261120/exact_rule_cross_league/*.py
python3 research/m8_m9_group_independent_20261120/exact_rule_cross_league/run_exact_rule_cross_league.py
python3 research/m8_m9_group_independent_20261120/exact_rule_cross_league/verify_exact_rule_cross_league.py
python3 research/m8_m9_group_independent_20261120/exact_rule_cross_league/verify_frozen_e_direction.py
python3 research/m8_m9_group_independent_20261120/exact_rule_cross_league/build_deliverables.py
```

## Actual result

- All 18,374 outside FIDs have a stored historical movement-capture row. Database status: 11,266 `NO_CROWN_AH_QUOTES`, 7,108 `QUOTES_SAVED`; 7,106 have at least one valid pre-kickoff source-event quote (the other two saved quote rows are post-kickoff only).
- 6,967 FIDs have a complete T6/T3/T1 path, 139 have no quote at or before T6, and 2 have no valid pre-kickoff AH row. Missing-path fixtures are not counted as no-signal.
- Frozen-priority assignments: 1,160 unique outside-49 orders. Net +10.890U, ROI +0.939%, MDD 20.460U. No overlap with the frozen 10,294 FIDs.
- Group outcomes: base 691/+8.580U; A 54/−13.190U; B 217/−5.955U; C 1/+0.910U; D 11/+4.860U; E 38/+1.900U; F 109/+12.180U; G 39/+1.605U. Cross-group assignments use frozen priority; 34 FIDs have multiple raw trigger predicates.
- Yearly outside-49 result: 2024 382/+7.890U; 2025 337/−0.390U; 2026 through 2026-06-01 27/−5.160U. These are not stable positive year-over-year results.
- Frozen eight plus de-duplicated candidates: 11,454 unique FIDs, +246.905U, ROI 2.156%, MDD 61.095U. This combined figure is retrospective and does not turn the new order slice into a stable or prospective strategy.
- Independent source-and-settlement audit passed for 1,160/1,160 orders: raw response SHA, FID, league/team/kickoff/FT, Crown T1 line and paired odds, horizon ordering, five-state quarter-line settlement, group/union arithmetic and frozen overlap. Live-mode Crown captures for outside-49 FIDs: 0/18,374.
- Original E direction was checked against every frozen E member: 267/267 frozen PnL matches. A later helper's E direction formula is inconsistent with the original path-sign rule; this is explicitly documented in the main report and the original rule semantics are retained.

## Published status

- Research files are confined to this independent research directory.
- No GitHub Actions/workflow execution, formal Telegram dispatch, or formal ledger write occurred.
- Commit and PR references are appended to `PROJECT_HANDOFF.md` after the research branch push and PR creation.
