# 2019–2026 历史数据恢复检查点｜2026-11-22 04:33 UTC

本检查点只记录数据覆盖和历史 Crown movement 请求持久化状态，不含策略、模型、回测或盈利研究。

## 历史 Crown movement 批次

- 只读审计时间：2026-11-22 04:33:45 UTC。固定队列 101,266 个 FID，SHA256 `5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`。
- 已有终态 1,342 个：329 个 `SAVED`、1,013 个 `NO_CROWN_AH_QUOTES`；队列仍有 99,924 个 FID 尚无终态。
- collector 日志共 1,372 次尝试、1,342 个唯一 FID。30 次 `IncompleteRead` 均已有终态，没有仅以可重试失败结束的 FID。
- 1,342 个终态逐一匹配 SQLite capture 和原始响应：原始文件缺失 0、SHA 不符 0、实际 HTTP 收件时间不符 0、报价行数不符 0。审计结果 `pass=true`，HTTP 请求 0、数据库写入 0。
- 已落库 movement AH 报价行 69,588，均来自本轮 `historical` 回取；不是赛前实收或可成交记录。新增终态中没有新增带 AH 报价的 FID，当前 329 个 `SAVED` 仍为该队列的带价数。
- 本次 HTTP 响应时间范围为 2026-11-21 23:18:38 至 2026-11-22 04:33:45 UTC。

## 数据库只读快照

- 约 04:32 UTC 的 SQLite WAL 只读快照：movement 历史 capture 104,030 个 FID，其中 53,328 个有 Crown AH 报价、共 4,499,297 行；50,702 个 capture 状态为 `NO_CROWN_AH_QUOTES`。源响应没有返回 Crown AH 时只说明该次响应，不证明该赛事永久无市场。
- 同一只读快照的历史 summary 层有 50,236 个 capture FID（49,054 个有报价、1,182 个响应无报价），报价 99,242 行。历史 raw cache 中另有 328 个 FID+SHA、656 行 summary 候选已核实，但尚未导入；共享 SQLite writer 活跃期间不并发写库。导入后需重新生成 summary 缺口队列。
- 总库存覆盖基线仍引用 04:26 UTC 已核记录：203,962 FID、118 个已发现 provider league IDs、902 个联赛×UTC年桶；可信 FT 193,518，未核 FT 10,444。该全局库存未在本检查点重建，不表示来源范围已穷尽。
- 各赛事原始 season 字段上一快照为96,503个FID有精确season标签、107,459个来源未提供season、冲突0；不得使用UTC年份填充season。

## 运行与缺口边界

- 安全窗口 driver PID 59381 和其 movement collector 子进程在本次检查期间仍活动。未启动第二个 Crown 请求进程，未停止或重启现有 driver。
- 101,266 个 movement 队列 FID 尚未完成，历史 summary 候选导入及缺口重建尚待共享 SQLite writer 安全空闲。10,444 个可信 FT 缺口也仍需按来源状态继续核实。
- “无 Crown AH 报价”仅指真实成功 HTTP 响应内没有可用报价，不等于永久无盘口；不得以其他博彩公司或插值替代 Crown。

## 可复核材料

- 固定队列：`/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/crown_quote_recovery/queues_20261122/crown_missing_movement_2019_2026.jsonl`
- 原始 collector 日志：`/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/crown_quote_recovery/queues_20261122/movement_collection.log.jsonl`
- 本检查点只读审计副本：`/tmp/movement_collection_persisted_audit_20261122_current.json`
- 审计脚本：`research/data_recovery_2019_2026/audit_movement_collection_persistence.py`

