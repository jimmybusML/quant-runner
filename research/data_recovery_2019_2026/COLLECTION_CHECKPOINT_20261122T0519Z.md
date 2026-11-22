# 2019–2026 历史数据恢复检查点｜2026-11-22 05:19 UTC

本增量检查点承接 `COLLECTION_CHECKPOINT_20261122T0516Z.md`，记录historical Crown movement队列和最新库存事务快照；全目标仍未完成。

## 实际回取与持久化

- 安全窗口driver PID 59381仍运行。遇到MR1计划任务后于 `05:19:06Z` 暂停collector子进程；当前由driver等待计划任务结束，未手动并行发起请求。
- 截止 `05:19:24Z`，固定101,266-FID movement队列已有1,617个唯一终态：329 `SAVED`、1,288 `NO_CROWN_AH_QUOTES`，剩余99,649个。1,647次请求中30次 `IncompleteRead` 均有后续终态。
- 独立只读持久化审计匹配全部1,617终态到SQLite及原始响应SHA、收件时间、quote count；所有差异为0，`pass=true`，0网络请求、0数据库写入。队列目前69,588条AH报价/329个有价FID；本段没有新带价FID。历史回取不是赛前实时收据。

## FT及全库存覆盖

- 05:19:05Z与10,444个未核FT名单相交151场，151/151身份完全一致。130条比赛状态缺失、18个数字码未映射、3条 `half`；明确 `full` 为0，没有新增可信FT。
- 05:19:03Z只读库存事务：203,962个唯一FID、118个known-source provider league ID、902个联赛×UTC年/unknown桶；可信FT 193,518、未核10,444。该联赛来源并集不是全球赛事穷尽证明。
- movement历史层104,313个FID有capture，53,328个FID有报价/4,499,297行，50,985个响应无AH报价，99,649个库存FID未采。3,165,248行source-event报价早于开赛，prospective报价行0。
- historical summary仍为50,200个capture FID、49,054个有价FID/99,242行；153,762个FID仍缺historical summary capture。328条已核验raw-cache open/close候选仍待共享writer安全空闲后导入。
- 902行覆盖矩阵为 `league_year_quote_coverage_20261122T0519Z.csv/.json`；来源season覆盖为96,503精确标签、107,459来源缺season、冲突0。

## 缺口与边界

- Crown/TotalCorner扩展库存crosswalk未变：1,102个新增于旧base且已在扩展库存的FID中，1,008个两来源full FT比分完全一致，94个仍未核；这1,102场AH报价行0。当前库存外37个解析capture均在UTC 2015或2018-12-31；目标期没有capture-only漏出赛事。
- 逐场材料：`movement_collection_persisted_audit_20261122T0519Z.json`、`crown_movement_batch_ft_status_audit_20261122T0519Z.json`及同时间戳JSONL。已发现联赛覆盖、FT、movement、summary仍有缺口；不据此宣布完成。
- 无模型/策略工作；未改正式采集器配置、采集频率、TG、正式账本或生产调度。
