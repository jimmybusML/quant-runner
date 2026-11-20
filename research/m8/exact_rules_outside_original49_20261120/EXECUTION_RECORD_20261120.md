# Execution record

- Repository: `jimmybusML/quant-runner`; isolated branch: `research/m8-exact-cross-league-expansion`, updated fast-forward to fetched latest `main` at `c6c8d3324c06f645496c33ce7e3270c24ab1678a` before publication.
- Frozen membership: 10,294 FIDs, +236.015U; SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`. Main runner asserts both count and P&L before computing the expansion.
- Target scope: the 15 league IDs in the existing 64-ID expanded schedule, excluding the frozen Original49. FID-deduplicated 2019–2026 schedule inventory: 21,096.
- Main command: `python3 research/m8/exact_rules_outside_original49_20261120/exact_rule_cross_league_20261120.py`
- Receipt command: `python3 research/m8/exact_rules_outside_original49_20261120/actual_receipt_exact_rule_audit_20261120.py`
- Independent settlement command: `python3 research/m8/exact_rules_outside_original49_20261120/verify_exact_rule_cross_league_20261120.py`
- Report and checksums: `python3 research/m8/exact_rules_outside_original49_20261120/build_exact_rule_report_20261120.py`
- Results: 6,967 complete T6/T3/T1 paths; 1,271 priority-assigned unique orders; +7.185U, +0.565% ROI; all 1,271 settlements independently verified from Crown raw response hashes and the schedule FT source.
- Receipt result: zero target-league FIDs intersected the verified forward-shadow, M8/MR1 receipt archives or SQLite `capture_mode=live` records. No true-receipt profit claim is made.
- Source provenance: historical event-time Crown prices are replayed from the existing local SQLite response archive. HTTP `response_received_at_utc` is kept distinct; historical response retrieval time is not treated as a contemporaneous receipt.
- The out-of-scope partial Original49 gap-fetch incident is documented in `out_of_scope_collection_stopped_20261120.json`. None of those FIDs belongs to the 15 target leagues or enters these calculations.
- Production boundary: no original group definition/member, M9, M1/MR1, production workflow, Telegram, formal ledger, or collector configuration changed.
- Independent audit: `independent_settlement_verification_20261120.json` reports 1,271 expected, 1,271 checked, 1,271 verified, zero discrepancies, +7.185U recomputed.
- Publication status at record creation: analysis complete; commit and pull request are recorded in the updated `PROJECT_HANDOFF.md` after publication.
