# Execution record — M8 cross-league transfer inference

- Execution date: 2026-11-20, Asia/Shanghai.
- Input path inventory: 6,967 complete Crown historical T6/T3/T1 paths across the 15 leagues outside Original49.
- Frozen Original49 membership: 10,294 unique FIDs; SHA-256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`.
- Commands run from repository root:
  - `python3 research/m8/exact_rules_outside_original49_20261120/m8_cross_league_transfer_inference_20261120.py` — exit 0.
  - `python3 research/m8/exact_rules_outside_original49_20261120/verify_cross_league_transfer_inference_20261120.py` — exit 0; JSON `pass=true`.
  - `python3 research/m8/exact_rules_outside_original49_20261120/build_transfer_inference_manifest_20261120.py` — exit 0.
- Recomputed exact-rule union: 1,271 unique incremental FIDs, +7.185U, ROI +0.565303%, MDD 27.755U. 2024–2026: 798 orders, −2.515U, ROI −0.315163%.
- Stratified ISO-week bootstrap: 20,000 replicates; fixed seed 20261120; recent period net-U 95% empirical range −46.975 to +42.1205U.
- Independent verifier: 1,271/1,271 AH settlements match; no overlap with 10,294 frozen FIDs; merged unique count 11,565 and merged P&L +243.200U.
- True prospective Crown receipt intersection for the incremental target pool: 0. All candidate calculations remain historical source-event replays.
- Changes limited to research deliverables and handoff; no production strategy, collector, Telegram, formal ledger, scheduler or workflow change.
