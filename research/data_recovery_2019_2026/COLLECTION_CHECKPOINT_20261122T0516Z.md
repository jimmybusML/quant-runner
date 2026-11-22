# 2019–2026 历史数据恢复检查点｜2026-11-22 05:16 UTC

本检查点承接 `COLLECTION_CHECKPOINT_20261122T0511Z.md`，记录下一批movement回取、FT复核和最新联赛/年份覆盖。全量补采仍在继续。

## Crown movement 回取

- 安全窗口driver PID 59381继续运行；固定101,266-FID队列保持不变。截止 `2026-11-22T05:16:05Z`，1,582个唯一FID取得终态：329 `SAVED`、1,253 `NO_CROWN_AH_QUOTES`；其余99,684个尚未终结。1,612次attempt中30次 `IncompleteRead` 均已后续解决。
- 独立只读落库审计核对1,582/1,582终态，SQLite/raw SHA/HTTP收件时间/quote count差异均为0，`pass=true`。0网络请求、0数据库写入。该队列仍有69,588行Crown movement AH数据、329个带价FID；本时段没有新增带价FID。
- 本批为historical mode，HTTP接收时间晚于历史赛事，不作为真实赛前收据。

## FT及总库存状态

- 05:15:33Z，movement批次与10,444个未核FT相交147场，147/147身份精确；126状态缺失、18个数字状态码未映射、3个 `half`，明确 `full` 为0。没有新增可信FT。
- 05:16:12Z SQLite只读事务覆盖203,962个已知source FID、118个provider联赛ID、902个联赛×UTC年/unknown桶；193,518可信FT、10,444未核FT。movement历史capture 104,280 FID，53,328个有价FID/4,499,297行，50,952个该次无AH报价响应，99,682个无movement capture。3,165,248行source-event报价早于开赛，prospective报价行0。
- historical summary仍为50,200 capture FID、49,054个有价FID/99,242行；153,762个库存FID仍缺historical summary capture。328条已SHA核实的raw-cache summary报价仍未入库，需等待共享SQLite writer空闲。
- 最新902行联赛×UTC年表为 `league_year_quote_coverage_20261122T0516Z.csv/.json`。season字段覆盖仍为96,503个有精确source season、107,459个来源未提供season、冲突0。

## 来源审计与未完事项

- 05:07离线审计仍显示1,102个Crown capture且相对旧base新、但已在plus-53库存中的FID中，1,008场Crown/TotalCorner full状态与比分完全匹配；94场保持未核FT。1,102场movement AH报价行均为0。
- 当前统一库存以外的37个可解析Crown capture ID均在UTC 2015或2018-12-31，不属于目标UTC 2019–2026；目标期没有新的capture-only FID。
- 最新逐场与汇总证据见 `movement_collection_persisted_audit_20261122T0515Z.json`、`crown_movement_batch_ft_status_audit_20261122T0515Z.json`及逐场JSONL。已知全库存并集尚不证明全球赛事范围穷尽；movement队列、summary缺口及FT缺口均未完成。
- 只更新研究数据/审计文件，没有策略、模型、生产采集配置、调度、Telegram或正式账本改动。
