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

## Read-only revalidation — 2026-11-20

- Re-ran `verify_exact_rule_cross_league.py`: 1,160/1,160 unique orders independently matched to Crown raw response SHA, fixture identity, FT, T1 quote and quarter-line settlement; zero issues. Live Crown receipt FIDs remain 0/18,374.
- Re-ran `verify_frozen_e_direction.py`: all 267 frozen E members reproduce their archived net U.
- Reconciled the compressed order ledger independently: 1,160 rows, 1,160 unique FIDs, zero frozen-member overlap; each base/A–G count and net U agrees with the summary JSON.
- The original execution manifest records Crown SQLite SHA256 `86a40523e94e5013c16e626a14820425c2e7ba4f48f4a245235f1ce8b3a3911d`; the current read-only database file hash is `7401078708d56a122987fde6231ae4b8cf296020d7fae54048437e73462c8a3f`. The database now contains 110,349 captures versus 110,133 at original execution, so its bytes have changed. For all 18,374 outside-49 FIDs, the per-FID movement capture status and quote counts are unchanged (11,266 `NO_CROWN_AH_QUOTES`, 7,108 `QUOTES_SAVED`); the order-level raw-response verifier still passes. The original input SHA is retained as provenance for the original calculation, not overwritten with the later database state.
- PR #67 remains open against `main`; no merge or production action was performed.

## Published status

- Research commit: `5aad821` (`research/m8-m9-groups`).
- Pull request: https://github.com/jimmybusML/quant-runner/pull/67, base `main`; created and intentionally not merged.
- `PROJECT_HANDOFF.md` now records the actual run, results, limitations, commit and PR.
- No production workflow, Telegram dispatch, formal ledger write, or production configuration change occurred.

## Full rerun and independent settlement recheck — 2026-11-20 16:08 UTC

- Re-ran `py_compile`, the full `run_exact_rule_cross_league.py`, raw Crown/FT verifier, frozen-E direction audit, report/weekly builder, and SHA manifest writer against the current local inputs. The current read-only Crown SQLite SHA is `7401078708d56a122987fde6231ae4b8cf296020d7fae54048437e73462c8a3f`; the original run's SQLite SHA `86a40523e94e5013c16e626a14820425c2e7ba4f48f4a245235f1ce8b3a3911d` remains preserved as historical provenance.
- Full replay reproduced all four coverage states exactly (11,266 no-quote capture FIDs; 6,967 complete T6/T3/T1; 139 no quote by T6; 2 post-kickoff-only/no valid pregame rows), all eight group totals, 1,160 unique orders and +10.890U. Frozen overlap remains 0.
- Independent verifier now computes quarter-line AH from its own two-leg settlement implementation (separate from the runner and shared project settlement helper). Re-read and settlement checks passed 1,160/1,160; all 18,374 outside-49 FIDs were checked for live capture, with 0 live receipts. E direction check passed 267/267 frozen E members.
- Report, output SHA manifest and current-source summary were regenerated. No rule, member, odds, FT, or outcome changed; the current database differs bytewise but the outside-49 quote/capture states and the replay result are unchanged.
- Existing PR #67 was confirmed OPEN against `main` before publishing this revalidation; this rerun updates its research branch. No workflow, Telegram, formal ledger or production change occurred.

## Full rerun — 2026-11-20 16:37 UTC

- On the PR #67 branch at `041d8b4db1530196addbbb576b7e6f67c8a010de`, re-ran the full replay, independent raw Crown/FT settlement audit, frozen E-direction audit, report/weekly builder, and SHA manifest writer.
- Reproduced the same four coverage states (11,266 no-quote capture FIDs; 6,967 complete T6/T3/T1; 139 missing T6; 2 with only post-kickoff/no valid pregame quotes), all base/A-G group outcomes, 1,160 unique added FIDs and +10.890U. No overlap with the frozen 10,294 FIDs.
- Independent audit passed for 1,160/1,160 orders and found no issues; live Crown captures remain 0/18,374. Frozen E-direction audit passed 267/267.
- Updated run timestamp and SHA manifest only; the research method, group membership, directions, quote inputs, FT, settlements and reported totals are unchanged. `sha256sum --check` passed for the existing manifest before this rerun; the regenerated manifest will be checked again before pushing.
- PR #67 remains the sole publication target; it is open against `main` and will not be merged by this task. No production workflow, Telegram, formal ledger, collector or production rules changed.
