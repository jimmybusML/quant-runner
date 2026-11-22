# 2019–2026 历史数据补齐检查点

状态生成时间：2026-11-22 02:53:39 UTC。中间快照；Crown movement历史回收仍未完成。

## 赛程来源并集与FT

- 当前已审阅来源并集为203,962个唯一FID、118个provider league ID；M7的73个精确赛事名称均有唯一ID映射。当前已知来源间没有ID缺口或额外ID；不据此声称全球赛事范围穷尽。
- 53项补充赛程最终对账：15项936个页响应、27,503 FID均已在原141,623 FID基线；38项2,140次请求、62,339 FID、2,098个已引用响应页，62,339条source-record SHA通过、raw-source errors为0。53批共89,842个唯一FID，净增62,339；数值比分且`status=full`有83,990条，其余5,852仍未核实/非full。源数据没有season字段，未用UTC年推断赛季。
- 对已有EPL/西甲ESPN档案做离线重核：43条原始完场补充行全部通过SHA、FID、赛果状态、比分、开赛时间及球队身份检查。42个FID属于冻结的并入前FT缺口，1个FID已有相同可信FT；12条ESPN比分与库存比分冲突，保存在独立冲突文件及证据字段中，不覆盖原值。FID `133320493` 的ESPN事件开赛时间比TotalCorner规范时间早152秒，两者分列保留，未改写库存时间。
- 当前可信FT 193,518，未核FT 10,444。未核队列分类：298场未来开赛、2场缺开赛时间、9,032场过去开赛但状态缺失/未知、1,112场来源状态非full且语义未解释；9,722条观察到占位`0:0`，未作为赛果。
- 审计使用并入前10,486个缺口FID冻结快照`unverified_FT_candidates_pre_epl_laliga_20261122.jsonl.gz`（SHA `b546ad74b816d5f41a0651b56ad5e1eeb6d9084453fbe3759d6de3e898af34d6`），因此并入后重新运行仍复现42新FT、1重复佐证、12冲突。

## Crown历史movement回收

- 安全driver PID 59381仍运行historical回收模式，底层collector PID 96227当时运行。101,266个候选中759个唯一FID已有终态（329 `SAVED`、430 `NO_CROWN_AH_QUOTES`），100,507个尚未有终态。日志保留30次`IncompleteRead`，这些FID均后来已有终态。
- 02:53:39–02:53:45 UTC只读SQLite/WAL快照：历史movement报价53,328 FID/4,499,297行；另50,128个FID记录`NO_CROWN_AH_QUOTES`。Movement source-event时间缺失0行，HTTP receive时间缺失1,488行。活动writer期间不声明主数据库文件SHA为稳定逻辑快照。所有历史回取与真实赛前receipt分开。

## 可复核文件与边界

- ESPN FT逐场离线审计：`audit_epl_laliga_espn_ft_archive_20261122.py`；结果`EXISTING_EPL_LALIGA_ESPN_FT_AUDIT_20261122.md`、`epl_laliga_espn_verified_ft_overlay_20261122.jsonl`及`epl_laliga_espn_verified_ft_conflicts_20261122.jsonl`。
- 并集合并：`reconcile_53_league_schedule_union_20261122.py`；FT readiness：`classify_merged_unverified_ft_readiness_20261122.py`；Crown状态快照：`build_recovery_checkpoint_20261122.py`；机器状态为`COLLECTION_STATUS_20261122T0253Z.json`。
- 输入、输出及脚本SHA见`CHECKPOINT_SHA256_20261122T0253Z.txt`。原始ESPN/Crown响应、Crown SQLite和私有逐场库存仍留本地，不在公开仓库发布。
- 此次没有策略/模型/盈利回测，没有Telegram或正式账本写入，没有修改生产采集配置或collector行为。赛程和FT来源仍非全局完备，movement/summary报价时间路径亦未完成。
