# 2019–2026 历史数据恢复检查点｜2026-11-22 05:11 UTC

本增量检查点承接 `COLLECTION_CHECKPOINT_20261122T0507Z.md`，只记录继续补采后的实际变化及核验结果。目标仍是完整补齐所有已发现联赛、赛季、比赛及可获得的历史数据；当前工作未完成。

## Crown movement 历史回取

- 只读进程核对：安全窗口driver PID 59381仍在运行，当前historical/movement子进程PID 27715；driver仍依据已确认的既有计划在正式定时任务期间暂停/恢复，队列清单未改。
- 截至 `2026-11-22T05:10:38Z`，101,266个固定队列FID有1,556个唯一终态：329 `SAVED`、1,227 `NO_CROWN_AH_QUOTES`，剩余99,710个未终结。1,586次尝试中的30次 `IncompleteRead` 均已有终态。
- 独立只读持久化审计将1,556/1,556个终态与SQLite capture、raw response SHA、HTTP收件时间、报价行数逐一匹配；错误0、`pass=true`、0个API请求、0次SQLite写入。回填过程累计仍为69,588条movement AH报价、329个带价FID；本次新增终态没有新增可计数报价FID。

## FT缺口复核

- 截至 `05:10:23Z`，该批与固定10,444个未核FT队列交集146场；146/146身份精确。状态125缺失、18个未映射数字状态、3个 `half`，明确 `full` 为0。可信FT增量为0，未合并任何推断比分。
- 保留已核336行状态交叉样本：328行精确身份下为 `full|full`，另8行均为相同的非full状态（数字码或 `half`）；数字码未作状态映射。

## 全库存覆盖快照

- SQLite只读事务截至 `05:10:44Z`：203,962个统一库存FID、118个已知provider联赛ID、902个联赛×UTC年/unknown桶；193,518个可信FT，10,444个未核FT。该known-source并集不是全球联赛穷尽声明。
- movement历史层104,254个库存FID有capture；53,328个有AH报价、共4,499,297行；50,926个capture响应没有AH报价；99,708个库存FID没有movement capture。source-event早于开赛报价3,165,248行；prospective报价为0。
- historical summary层50,200个capture FID、49,054个有价FID、99,242行open/close；仍有153,762个FID没有historical summary capture。328条已SHA核验的缓存open/close候选仍待共享SQLite writer安全空闲后用既有解析器追加并重建summary缺口队列。
- 902行覆盖表：`league_year_quote_coverage_20261122T0510Z.csv/.json`。source-season仍为96,503个精确来源标签、107,459个缺来源season、冲突0；不以UTC年份代替赛季。

## 来源交叉核验

- 05:07Z离线审计核对1,102个当前扩展库存中早于旧基础库存且已有Crown capture的FID。1,008场在Crown原始响应与3,075份缓存TotalCorner赛程页中拥有一致的精确身份、`full`状态和比分，均已经算入可信FT；94场非full/不完整，仍在未核FT清单。1,102场关联movement报价行均为0，库存及FT净新增均为0。
- 当前统一库存之外的37个可解析Crown capture身份均在UTC 2015或UTC 2018-12-31，没有2019–2026范围的capture-only赛程。原始元数据仍有逐FID SHA引用；本地TotalCorner原始赛程页SHA目录含3,075页：`totalcorner_schedule_page_source_sha256_20261122.jsonl.gz`。
- 以上交叉核验全为离线本地检查，无HTTP请求、无SQLite写入。2019–2026正式库存已知source范围内没有因此新增FID；不会重复计数。

## 执行记录及剩余事项

- 最新持久化审计：`movement_collection_persisted_audit_20261122T0510Z.json`；FT逐场审计：`crown_movement_batch_ft_status_audit_20261122T0510Z.json`及对应JSONL；覆盖数据与两类离线交叉核验见本目录同时间戳/固定日期文件。
- 继续复用当前historical movement队列；未启动summary collector，避免与共享writer并行。待movement writer安全空闲后再处理328条summary缓存候选并重建全库存summary缺口。
- 所有collection仍是历史回取；本次未修改生产模型、采集行为/频率、Telegram、正式订单或结算账本。没有训练模型或策略回测。
