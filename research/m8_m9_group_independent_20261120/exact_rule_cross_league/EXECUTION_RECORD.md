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

## Full rerun and report completeness update — 2026-11-21 China time (2026-11-20 17:33 UTC)

- Started from the user-designated clean branch `research/m8-m9-groups` at `25ac39c`; no pre-existing uncommitted edits were present in that worktree. The source files were opened read-only.
- Re-ran Python compilation, the complete T6/T3/T1 reconstruction and exact base/A–G replay, independent Crown raw-response/FT/quarter-line settlement verification, frozen-E direction audit, report/weekly builder, and SHA manifest writer.
- Current source hashes: finished expanded schedule `a9d48b40cba84e5bf49f490b4b25bada9bc12a6266e6da0eed51c063166b8258`; Crown SQLite `7401078708d56a122987fde6231ae4b8cf296020d7fae54048437e73462c8a3f`; frozen membership `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665` (10,294 FIDs, +236.015U).
- Full-scope replay reproduced the same 18,374 target FIDs, 11,266 `NO_CROWN_AH_QUOTES`, 7,108 with saved quotes, 7,106 with at least one pregame source quote, 6,967 complete T6/T3/T1 paths, 139 missing T6, and 2 post-kickoff-only/no-valid-pregame records. Those incomplete-path FIDs remain data gaps, not strategy misses.
- Frozen-priority replay reproduced 1,160 unique outside-frozen orders, +10.890U, ROI +0.939%, MDD 20.460U; frozen overlap 0. Independent raw-Crown/FT verifier passed 1,160/1,160. The original-E direction audit passed 267/267 frozen members. Live Crown receipts remain 0/18,374.
- The regenerated report now also renders every group’s annual order count/net U/ROI directly, while the JSON retains full group-by-year, group-by-league, and ISO-week detail. G remains the original independent score-rate/expected-AH-EV logic and is not replaced with M9.
- Gzip ledger content was compared after decompression with the committed run; it is identical. The refreshed manifest hashes all current deliverables and the current local SQLite input. No membership, rule, direction, cutoff, odds, FT, or P&L changed.
- This is a historical source-event replay only: no actual receipt or Telegram/production order was created. No production strategy, collector, workflow, or formal ledger was changed.

## User-requested full rerun — 2026-11-20 18:16 UTC

- Research branch: `research/m8-m9-groups`; starting HEAD `fcdfe354a2ec49d92b7c6c8aaadb8e6c19614d40`, clean before run.
- Re-ran `py_compile`, `run_exact_rule_cross_league.py`, `verify_exact_rule_cross_league.py`, `verify_frozen_e_direction.py`, `build_deliverables.py`, and `write_sha256_manifest.py` against the current read-only inputs.
- Current input SHA256: expanded schedule `a9d48b40cba84e5bf49f490b4b25bada9bc12a6266e6da0eed51c063166b8258`; Crown SQLite `7401078708d56a122987fde6231ae4b8cf296020d7fae54048437e73462c8a3f`; frozen membership `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`.
- Reproduced the full 18,374-FID outside-49 inventory: 11,266 captures with `NO_CROWN_AH_QUOTES`, 7,108 with saved quotes, 7,106 with at least one pregame source quote, 6,967 complete T6/T3/T1 paths, 139 lacking a T6-or-earlier quote, and 2 with no valid pregame AH quote. Missing paths remain data gaps, not rule non-hits.
- Exact frozen-priority base/A-G replay reproduced 1,160 unique outside-frozen FIDs, +10.890U, +0.939% ROI, MDD 20.460U, and zero overlap with the 10,294 frozen FIDs. Independent re-read of raw Crown response, FT and quarter-line settlement passed 1,160/1,160 with no issues; all 18,374 outside FIDs were checked for live capture and there were 0. Frozen E direction reproduced 267/267.
- Report, summary, weekly ledger, compressed orders and SHA manifest were refreshed. No frozen rule, member, direction, cutoff, data source, production workflow, Telegram, formal ledger, or collector was modified. Historical source-event replay is not evidence of HTTP receipt execution or formal orders.
- Publication: result/rerun commit `4589ad4403c98d4743b94688e1547f7f59bc011a` was pushed to `research/m8-m9-groups`; remote ref matched. Existing PR [#67](https://github.com/jimmybusML/quant-runner/pull/67) targets `main`, is OPEN, and was not merged.

## User-requested exact-rule cross-league revalidation — 2026-11-21 11:16 UTC

- Replayed on `research/m8-m9-groups` from starting HEAD `ebf996469d9d645c8e2f3cc842cf28566b1293e8`; this worktree already contained unrelated untracked formation/referee research, which was left unstaged and unchanged.
- Recompiled the runner, independent verifier, frozen-E verifier and deliverable builders; reran `run_exact_rule_cross_league.py`, `verify_exact_rule_cross_league.py`, `verify_frozen_e_direction.py`, report/weekly builder and SHA manifest generation.
- Current inputs: frozen membership SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665` (10,294 FIDs, frozen baseline +236.015U); expanded schedule SHA256 `a9d48b40cba84e5bf49f490b4b25bada9bc12a6266e6da0eed51c063166b8258`; read-only Crown SQLite SHA256 `8d2422ab7b262f8d5a343ad7f8758babea7e854ebd45b9187acb318f42eddd8a`.
- Reproduced 96,504 schedule rows / 64 provider leagues, 18,374 outside-49 FIDs across 15 leagues, 11,266 `NO_CROWN_AH_QUOTES`, 7,108 quote-bearing captures, 7,106 with a pregame source-event AH quote, 6,967 complete T6/T3/T1 paths, 139 without a T6-or-earlier quote and 2 without a valid pregame AH row. Incomplete paths remain data gaps, not rule non-hits.
- Frozen-priority base/A-G exact replay again produced 1,160 unique outside-frozen orders, +10.890U, ROI +0.938793%, MDD 20.460U, and zero FID overlap with the frozen 10,294. The 1,160 raw Crown response/FT/T1 price/quarter-line settlements independently passed 1,160/1,160; live-mode receipts remain 0/18,374. Frozen E directions and PnL matched 267/267.
- G still uses the original independent dynamic attack/defence and league-baseline score-rate model with Crown two-sided AH EV comparison; it is not replaced by M9. No future target or same/next Beijing-date results enter G's pre-match model state.
- The decompressed order ledger is byte-identical to the previously committed ledger; only deterministic gzip metadata and run time/input database SHA changed. All 37 output-file hashes in the regenerated manifest were checked with Python SHA256 and matched. Historical source-event replay only; no receipt execution, Telegram order, ledger write or production change occurred.
- Existing PR #67 against `main` was confirmed OPEN before this revalidation and remains the publication target; no merge was performed.


## User-requested full replay rerun — 2026-11-21 12:41 UTC

- Re-ran the full exact base/A–G T6/T3/T1 replay against the user-specified 18,374-FID outside-49 inventory, then independently re-read Crown raw responses, fixture FT, T1 contracts and quarter-line settlement. Also repeated the frozen E-direction audit, rebuilt report/weekly files and refreshed the SHA256 manifest.
- Current input SHA256 at run: Crown SQLite `1af6ff08c2111d649903603b7043ca32ca75c1568d1b281b792fc117c84e16a2`; expanded schedule `a9d48b40cba84e5bf49f490b4b25bada9bc12a6266e6da0eed51c063166b8258`; frozen membership `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`.
- Coverage and results reproduced: 11,266 `NO_CROWN_AH_QUOTES`; 7,108 quote-bearing captures (7,106 with a pre-kickoff source-event quote); 6,967 complete paths; 139 missing T6; 2 without a valid pre-kickoff quote. Frozen-priority assignment yields 1,160 unique new FIDs, +10.890U, +0.938793% ROI, MDD 20.460U; no overlap with frozen 10,294 FIDs. Independent raw Crown/FT settlement passed 1,160/1,160; original E direction/PnL matched 267/267. Live receipts remain 0/18,374.
- All 37 OUTPUT hashes in the regenerated SHA manifest were recomputed and matched. The historical result is unchanged despite the Crown SQLite byte hash update. Historical source-event replay only; no formal orders or production actions.
- Existing PR #67 remains OPEN against `main`; this rerun is published by updating that PR. No merge, production model, Telegram, formal ledger, collector or schedule change occurred.

## Annual weekly-denominator consistency correction — 2026-11-21 13:51 UTC

- Re-ran the complete cross-league exact-rule replay, independent raw Crown/FT and quarter-line settlement audit, frozen-E direction audit, report builder, and SHA manifest writer against the same source files. The rerun reproduced all coverage states, all group totals, 1,160 unique orders, +10.890U, and zero overlap with the 10,294 frozen FIDs.
- Corrected a redundant annual summary field that had used only the first-to-last order date span while the report and merged-year table use the full observed schedule-week span. The JSON now labels both denominators separately: `avg_per_observed_schedule_week` is the annual schedule rate; `avg_per_order_date_span_week` is retained as a distinct diagnostic. Reported weekly rates are 2024 7.208/53 weeks, 2025 6.481/52, and 2026 1.350/20.
- Independent raw-source and AH settlement verification passed 1,160/1,160; live Crown capture remained 0/18,374; the original frozen-E direction/PnL audit passed 267/267. Seven input and 37 output SHA entries matched. Current Crown SQLite SHA256: `1af6ff08c2111d649903603b7043ca32ca75c1568d1b281b792fc117c84e16a2`.
- Publication remains on `research/m8-m9-groups`, PR #67 against `main`, OPEN and unmerged. Existing unrelated untracked formation/referee files in this shared worktree were not included.
