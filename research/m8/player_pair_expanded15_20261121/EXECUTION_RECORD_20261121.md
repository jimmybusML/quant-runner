# Execution record — M8 expanded15 player-pair cohesion

## Inputs and scope

- Repository: `jimmybusML/quant-runner`; current isolated research branch `research/m8-referee-residual-20261120` (PR #69, main target).
- Crown quote store: existing local SQLite opened read-only. No HTTP quote acquisition was performed.
- Frozen M8 membership: 10,294 FIDs, +236.015U; SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`.
- Expanded target: 6,967 complete T6/T3/T1 FIDs from 15 out-of-Original49 leagues; recoverable Crown T12 quotes for 6,773; 309 exact identity and prior lineup feature-complete targets across MLS, Brazil Serie A and Mexico Liga MX, all in 2025.
- All historical quote retrieval receive times are retained separately from Crown source-event timestamps. No target FID intersects the verified receipt archive.

## Commands and outcome

1. `python3 research/m8/player_pair_expanded15_20261121/run_pooled_t12_pair_cohesion.py` — exit 0. Rebuilt the pooled Original49 T12 training set and expanded15 target predictions using the previously fixed pair-cohesion features, fixed Ridge alpha 100 and expanding-year splits. The 2025 fold trained on 7,765 prior-year rows through 2024; 309 expanded targets were scored.
2. `python3 research/m8/player_pair_expanded15_20261121/verify_pooled_pair_cohesion.py` — exit 0. Re-read and SHA-checked all 309 raw Crown responses, independently reconstructed each latest valid `asian_list` quote at/before T12, verified fixture/league/teams/kickoff/FT, and recalculated 927 quarter-line AH settlements across three same-FID model alternatives. Checked 787 recorded input/schedule hash entries (including 778 raw schedule pages), frozen-member SHA/count/P&L, training-year chronology and unique-FID disjointness. Errors: 0; frozen overlap: 0.
3. `python3 research/m8/player_pair_expanded15_20261121/build_deliverables.py` — exit 0. Built the report, year-by-year coverage table and SHA256 file list.

## Verified findings

- Market-only: 309 / −10.345U / −3.348% ROI / 16.905U MDD.
- Pair-only: 309 / −3.125U / −1.011% ROI / 19.880U MDD.
- Crown + pair: 309 / +7.740U / +2.505% ROI / 11.530U MDD.
- The 2025 result is a single retrospective target year. 2024 and 2026 had no feature-complete expanded15 target rows. There were no true-receipt target orders. Pair features lack immutable first-publication/received timestamps.
- On the same 309 FIDs, market+pair improved goal-difference MAE by only about 0.00037 versus market-only while RMSE worsened by about 0.00737; the small positive 2025 AH return does not establish stable incremental information.
- Same-date-window frozen eight: 2,032 / +84.885U. Market+pair union: 2,341 unique FIDs / +92.625U / 3.957% ROI / 15.025U MDD. Candidate contribution remains separately +7.740U.

## Production boundary and publication

Only research outputs and handoff notes are changed. Frozen M8, M1, MR1, M9, Telegram, formal ledger, collection configuration and production workflows are unchanged. No experiment is promoted to a formal strategy or gate.

Commit and PR SHA receipts are recorded in `PROJECT_HANDOFF.md` after publication. The PR is for review and remains unmerged unless the repository owner merges it.
