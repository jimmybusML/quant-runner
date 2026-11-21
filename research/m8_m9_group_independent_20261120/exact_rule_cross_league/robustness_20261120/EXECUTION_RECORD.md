# Robustness audit execution record

- Date: 2026-11-20 (Asia/Shanghai)
- Command: `python3 research/m8_m9_group_independent_20261120/exact_rule_cross_league/robustness_20261120/audit_extension_robustness.py`
- Exit status: 0.
- Read-only input ledger: `../exact_rule_cross_league_orders.jsonl.gz`, 1,160 unique out-of-frozen FIDs, net +10.890U. The program asserts both row count and unique FID count.
- Output: `robustness_results.json`, including all 13 league leave-one-out results, all eight year leave-one-out results, every ISO week, 20,000 deterministic four-week circular block bootstrap replicates, and source ledger SHA.
- Result: remove International Match and remainder becomes -0.510U; remove USA MLS and +0.315U remains; remove both and remainder is -11.085U. Four-week bootstrap 95% net-U interval [-46.545, 68.420], ROI interval [-4.129243%, 5.791233%].
- Scope limitation: this is sensitivity analysis on the already evaluated historical fixed-rule candidate; it neither retrains the rules nor corrects selection bias from past research. All quote prices remain historical Crown source-event replay, not confirmed contemporaneous receipts or trades.
- Production effects: none; no formal order, Telegram, ledger, model, or collection-chain writes.
- The same rerunnable script also reads the frozen exact cross-league coverage summary and authoritative 15-league IDs, counts schedule fixtures and archive FID overlap: 252 fixtures in 2026 through 2026-06-01, 74 complete T6/T3/T1 paths in the earlier audit, and zero FIDs in the 2026-11-13 actual HTTP receipt archive. The report JSON records SHA256 for the summary, schedule and receipt archive inputs.
