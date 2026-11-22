# 2019–2026 历史数据恢复检查点｜2026-11-22 04:46 UTC

本检查点记录全联赛数据盘点、历史 Crown movement 队列落库和完场状态复核。只处理数据采集/核对/持久化，不进行策略、模型、回测或盈利筛选。

## Crown movement 回取

- 固定目标队列 101,266 FID，SHA256 `5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`。队列处理到 04:46:39 UTC 时有 1,413 个唯一终态：329 `SAVED`、1,084 `NO_CROWN_AH_QUOTES`；剩余 99,853 个尚无终态。
- 日志 1,443 次尝试、30 次 `IncompleteRead`，这些失败都已有终态；没有未解决的重试错误。
- 只读审计核对1,413个终态的 SQLite capture、raw response SHA、HTTP收件时间与报价行数，全部一致，raw缺失/哈希差异/收件时间差异/报价行数差异均为0，`pass=true`。审计0个HTTP请求、0次数据库写入。
- 本队列已持久化movement报价69,588行，329个 `SAVED` FID；新增终态尚未增加带AH报价的FID。其余响应的 `NO_CROWN_AH_QUOTES` 只说明响应时无Crown AH报价，不证明该比赛从未有过盘口。
- 最新响应时间从2026-11-21 23:18:38 UTC至2026-11-22 04:46:34 UTC。报价属于历史回取，HTTP在比赛之后收到，不是赛前真实收据。

## FT 状态复核

- 截止04:46:34 UTC，本批1,413个终态与固定10,444个未核FT名单相交135场。逐场原始响应SHA及FID、联赛、主客球队ID、开赛时间均匹配。
- 135场状态：115缺失、17个非`full`数字状态码、3个`half`，明确`full`为0。所有可见比分字段不因此升级为最终比分；本批新增可信FT仍为0，未并入FT库存。
- 对本批所有raw response做来源状态校准，336场满足完全相同的比赛身份：328场状态为`full|full`；另外8场是相同的非full状态（`half|half`或数字44、45、55、76、77、80、86）。未发现数字状态码对应`full`。135场交集中有7场找到同FID/联赛/球队ID/开赛时间的原赛程状态副本，其状态仍是相同数字码或`half`。
- FT候选逐场账本、审计JSON和复跑代码保存在 `crown_movement_batch_ft_candidates_20261122T0446Z.jsonl.gz`、`crown_movement_batch_ft_status_audit_20261122T0446Z.json` 和 `audit_crown_movement_batch_ft_status_20261122.py`。
- 保留04:42:05Z中间核验快照（133个未核FT交集、0个明确full）及逐场证据：`crown_movement_batch_ft_candidates_20261122T0442Z.jsonl.gz`、`crown_movement_batch_ft_status_audit_20261122T0442Z.json`。后续04:46快照扩大到135场，结论未变。

## 总库存与剩余工作

- 最新稳定全局盘点仍以04:26快照为准：203,962个known-source FID、118个已发现provider league IDs、902个联赛×UTC年桶；可信FT 193,518、未核FT 10,444。该来源并集不代表全球赛事范围穷尽。
- 历史summary层上一只读快照有50,236个capture FID，其中49,054个有价、1,182个响应无价，共99,242行报价。328个已SHA核验的raw cache候选（656条open/close summary行）尚待导入并重建缺口队列；共享SQLite writer运行时不并发写。
- 联赛来源season上一快照为96,503个FID有精确season标签、107,459个来源缺season、冲突0；不得以UTC年推定赛季。
- 安全窗口driver PID 59381仍运行并按计划任务自动暂停/恢复。分批补采仍在进行，不能宣称2019–2026历史数据已补齐。

