# 2019–2026 历史数据补齐检查点

状态生成时间：2026-11-22 02:28:17 UTC。持续任务的中间快照，Crown movement 回收未完成。

## 赛程库存与来源范围

- 现有已审阅来源并集包含203,962个唯一FID、118个provider league ID。M7的73个精确赛事名称均有唯一ID映射。已审阅来源间没有ID缺口或额外ID；这不是全球赛事范围已穷尽的证明。
- 38项具名赛程补充批次已在2026-11-21 22:37:41 UTC完成：2,140次请求、62,339个唯一FID、2,098个引用原始响应页，62,339条source-record SHA验证通过、raw-source errors为0。
- 另15项补充批次完成936个响应页、27,503个唯一FID；全部已在141,623-FID原基线内。38项与原基线和15项均无FID交集，净增62,339。两批合并89,842个唯一FID；其中83,990行为数字FT且`status=full`，5,852行仍未核实或非full。
- 合并后的已发现来源库存为203,962个FID。可信FT为193,476，未核实FT为10,486。新增赛程源未提供的season字段保持缺失，不从UTC开赛年推断赛季。

## Crown 历史 movement 回收

- 安全driver PID 59381处于运行状态，底层collector PID 89870处于运行状态；均使用historical mode。
- 02:28:14 UTC日志快照：101,266个候选中601个唯一FID已有终态（329 `SAVED`、272 `NO_CROWN_AH_QUOTES`），100,665个尚未记录终态；30次`IncompleteRead`失败尝试对应FID均已有后续终态，当前无只以`FETCH_FAILED`结束的日志FID。329个成功记录合计69,588条报价。
- 02:27:43 UTC针对53批联赛的SQLite只读/WAL视图中，38批有173个FID出现historical movement capture，其中0个有AH quote行；15批没有capture。这个短时快照不能说明未捕获赛事没有皇冠盘口。
- 全库历史movement报价为53,328个FID、4,499,297行；source-event时间缺失0行，HTTP receive时间缺失1,488行。以上均为历史数据分层统计，不等于实际赛前收据。活动writer期间不声明稳定的SQLite逻辑库文件SHA。

## 复算与证据

- 赛程对账：`audit_supplemental_15_and_38_schedule_batches_20261122.py`、`reconcile_53_league_schedule_union_20261122.py`。
- 来源ID审计：`audit_league_scope_union_2019_2026.py`。
- 状态快照构建：`build_recovery_checkpoint_20261122.py`；机器快照：`COLLECTION_STATUS_20261122T0227Z.json`。
- 本次修正了并集summary中`supplemental_source_rows`字段局部变量覆盖，现返回正确的89,842行计数；FIDs、原始来源版本及FT值未因此改写。
- 本检查点未执行策略/模型/盈利回测，未写Telegram或正式账本，未修改生产配置或采集器参数。未使用替代赔率来源，也未将历史回取称为实时赛前收据。

本轮工作没有完成全部2019–2026皇冠movement覆盖，也没有完成全部未核FT或全球赛事源枚举。当前继续执行状态与输入/输出SHA见`CHECKPOINT_SHA256_20261122T0227Z.txt`。
