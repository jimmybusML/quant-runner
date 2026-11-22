# 2019–2026 全联赛数据补齐检查点

生成时间：2026-11-22 02:01 UTC。此为滚动中间快照；恢复目标仍未完成。

## 赛事库存与赛果

- 当前来源并集为203,962个唯一FID、118个已发现provider league ID。仍不能声称全球联赛全集已枚举。
- 当前核实FT 193,476场，待核验10,486场。核验依据为原始TotalCorner/Crown或外部已存来源，不使用比分占位或模型推断。
- 修正合并器对`M1_history_cache_records`字段的大小写遗漏后，441个FT从50个缓存文件中通过精确FID、联赛、主客身份、`status=full`和数字比分复核；12个开赛时间版本不一致项保留全部来源版本。
- M5核验27个raw结果响应（24个与M1重叠，净新增3个）；另63个索引记录接收时未完场而拒绝。
- 既有历史Crown movement raw又通过18个FT核验。17个有报价的movement capture与1个`NO_CROWN_AH_QUOTES`状态的完整FT响应分开保留。全部为赛后historical接收，绝非赛前实收。
- 独立复算确认203,962唯一库存、193,476核实FT、10,486唯一缺口，FT与缺口交集为0。

## Crown历史AH报价回收

- movement队列101,266个候选；日志已记录449个终态FID（329`SAVED`、120`NO_CROWN_AH_QUOTES`），另外30个`IncompleteRead`错误未形成终态、需要恢复；尚余100,817个未终结FID。
- 只读SQLite计数保存在`COLLECTION_STATUS_20261122T0201Z.json`。历史response receive与source-event时间分列；采集器运行期间不声明主数据库文件SHA为稳定数据库快照。
- raw Crown响应和SQLite仍在本地。缺capture或`NO_CROWN_AH_QUOTES`只描述采集结果，不能推断历史上市场从未有报价。

## 来源与执行边界

- 历史movement安全驱动PID 59381仍运行，使用原有historical模式、缓存复用、默认5.2秒请求间隔和互斥等待。
- M1/M5目标快照分别固定为10,948个FID；Crown FT核验目标固定为10,504个FID。清单由当时缺口FID与经核实overlay按精确FID重建，保存于`ft_reconciliation_targets_*.jsonl.gz`。
- 最新可见具名联赛分页检查点仍为2026-11-21 19:46:29 UTC，35个候选中20个完成；当前未检测到其进程，本检查点未启动新分页任务。
- 复跑脚本、源输入/输出SHA、逐场证据及快照见`CHECKPOINT_SHA256_20261122T0201Z.txt`。本阶段未做策略研究/训练/回测，无Telegram或账本写入，也未改生产采集设置。
