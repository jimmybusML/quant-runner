# 2019–2026 历史数据恢复检查点｜2026-11-22 05:07 UTC

本检查点只处理历史数据发现、回取、身份/结果核对与持久化；没有策略研究、模型训练、回测或盈利筛选。Crown source-event 时间与 HTTP 实收时间保持分开，历史回取不标记为实时收据。

## Crown movement 队列

- 只读核对确认安全窗口驱动 PID `59381` 继续运行；最近一次恢复的 collector 子进程 PID `26389`，队列仍为不可变的101,266个FID，SHA256 `5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`。没有并发启动其他采集器，也没有改请求频率或采集配置。
- 独立持久化审计生成于 `2026-11-22T05:04:56Z`：1,551次尝试、1,521个唯一终态（329 `SAVED`、1,192 `NO_CROWN_AH_QUOTES`），99,745个队列FID尚无终态；30次 `IncompleteRead` 均有后续终态。1,521/1,521均匹配SQLite capture、原始响应SHA、实际收件时间和报价行数；raw缺失、SHA差异、收件时间差异、报价数差异均为0，`pass=true`，该审计0 HTTP请求、0 SQLite写入。
- 本批已持久化69,588条Crown AH movement报价，仍为329个有价FID；本段新增终态均未增加有价FID。`NO_CROWN_AH_QUOTES`仅描述该次响应，不证明该赛事历史上从未有过报价。
- 运行日志响应区间：2026-11-21 23:18:38Z 至 2026-11-22 05:04:56Z。此为历史模式批次，不能当成赛前实时实收。

## FT缺口交叉核验

- 固定的10,444个未核FT清单截至 `05:04:45Z` 与该批相交139场。139/139的FID、联赛、主客队ID和开赛时间身份均精确匹配；状态为118缺失、18个未映射数字状态、3个 `half`，明确 `full` 为0，因此本批没有新增可信FT。
- 既有336场精确身份状态交叉样本中，328组是 `full|full`，另8组是相同的非full状态（`half`或数字44/45/55/76/77/80/86）。数字码没有被映射成完场状态，比分未并入可信FT库存。

## 联赛与年份覆盖快照

- 05:05:06Z SQLite只读事务快照对应当前统一库存203,962个FID、118个已发现provider league ID、902个联赛×UTC年/unknown桶；可信FT 193,518、未核FT 10,444。此为已知来源并集，不代表全球赛事范围已穷尽。
- movement历史层：104,219个库存FID有capture；其中53,328个有AH报价，共4,499,297条报价记录；50,891个capture状态为该次响应无AH报价；99,743个FID没有movement capture。3,165,248条movement报价的source-event时间早于开赛；本历史批次没有prospective quote。
- summary历史层：50,200个FID有capture，49,054个有价，共99,242条open/close报价行；历史summary缺capture 153,762个FID。328个已核验raw cache open/close候选仍等待共享SQLite writer安全空闲后再走既有解析器入库和重建缺口队列。
- 更新后的902行provider league×UTC year覆盖表、总计及队列对账见 `league_year_quote_coverage_20261122T0505Z.csv/.json`。来源季节表维持96,503个FID有精确source season、107,459个来源无season、冲突0；不按UTC年推断赛季。

## Crown capture元数据与赛程来源交叉核对

- 将当前203,962-FID扩展库存与旧基础库存比较，并用3,075份本地缓存TotalCorner原始赛程页核验新增FID。当前扩展库存中，有1,102个旧基础库存以外FID已有Crown capture raw响应：provider 10635共420场、provider 10653共682场。1,102场均有精确FID、联赛ID、主客队ID/名称、UTC开赛时间匹配；Crown及TotalCorner都标为 `full` 的1,008场比分一致，且均已在现有库存中列为可信FT；另94场状态仍非full/不完整，均保留在未核FT队列。1,102场Crown AH报价行均为0，因此未增加可用价格或FT数量。
- 以当前扩展库存（而不是旧基础库存）为比较基线再次扫描所有Crown capture ID，共发现37个不在扩展库存中的可解析身份：36场在UTC年2015，1场UTC 2018-12-31（中国日期2019边界）；均不属于本次UTC 2019–2026范围。3,075份本地2019–2026 TotalCorner页没有这些FID；没有发现漏入目标时段的capture-only赛程。元数据原样保留为边界/超范围证据。
- 两项身份盘点均只读本地文件/SQLite，0网络请求、0数据库写入；没有将Crown响应中的比分独立升级，也未增补重复FID。

## 执行与剩余事项

- 代码和结果：`audit_crown_movement_batch_ft_status_20261122.py`、`audit_movement_collection_persistence.py`、`build_league_year_live_coverage_20261122.py`、`audit_crown_only_fixture_metadata.py`、`audit_crown_metadata_candidates_against_schedule_pages_20261122.py`、`audit_crown_metadata_expanded_inventory_crosschecks_20261122.py`及其带SHA逐场输出。TotalCorner本地页输入SHA索引为 `totalcorner_schedule_page_source_sha256_20261122.jsonl.gz`（3,075页）。
- 本次修改仅是研究目录中可复跑审计/覆盖快照脚本与结果；正式模型、TG、账本、生产采集器及生产调度未改。
- 2019–2026全库存、未核FT、movement和summary缺口仍未完成；继续让现有安全窗口driver按其既有计划续跑。不要因本检查点的中间计数宣布补采完成。
