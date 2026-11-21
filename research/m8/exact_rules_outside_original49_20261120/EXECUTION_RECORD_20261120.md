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
- Rule-provenance audit: the historical full-path extractor assigns E direction using the first nonzero fallback among net, T6→T3, T3→T1, and last move. This differs from the later boundary module's `group_side('E')`, which returns no side for zero endpoint movement. Of 161 frozen E members with both path features and independent Crown settlement evidence, all 161 directions match the historical extractor; 106 members lack one of those paired records. The report preserves this discrepancy and explains why the original extractor is used.
- Reproducible E-rule check: `python3 research/m8/exact_rules_outside_original49_20261120/audit_frozen_E_direction_consistency_20261120.py`; result is saved in `audit_frozen_E_direction_consistency_20261120.json` (267 frozen E members, 192 with settlement ledger, 161 paired path/settlement checks, 161 direction matches, zero mismatches; all 52 crossleague E orders have zero endpoint movement).
- Published research commit: `dd2f3d610ec9d1eed1475c9f4944a1992276b33b`; branch `research/m8-exact-cross-league-expansion`.
- Pull request: `https://github.com/jimmybusML/quant-runner/pull/68`, targeting `main`; it is not merged.

## 2026-11-21 独立复算

- 从现有已授权工作区重新运行主回放、真实收据审计、独立 Crown/FT 结算校验和报告生成器；没有发起 Crown 采集请求。
- 回放仍输出21,096个赛事FID、6,967条完整T6/T3/T1路径和1,271个按冻结优先级去重的新增FID，净值+7.185U/ROI+0.565303%。新增FID与冻结10,294个FID交集为0。
- 独立复核重读现有Crown原响应SHA、赔率/盘线、赛程FT及冻结FID：1,271/1,271通过，0差异，quarter-line两腿重算净值+7.185U。目标15联赛真实赛前receipt仍为0。
- 与已发布账本逐行解压比较：完整路径、覆盖FID、订单及独立结算JSONL语义内容完全相同；gzip文件字节SHA因gzip时间头变化，已刷新输出SHA清单。结果数字未变化。
- 修复报告生成器，使其持续保留E组历史方向实现差异审计，且自动写入本次复算结果。
