# 2019–2026 历史数据补齐检查点

生成时间：2026-11-22 03:18 UTC。**中间快照，不是完成声明。**

## 已发现库存基线

- 当前已核对的来源并集为203,962个唯一FID、118个TotalCorner provider league ID；M7的73个精确赛事名称均映射到这118个已知ID。此为已审阅来源并集，不宣称全球赛事范围穷尽。
- 截至02:53 UTC的固定全局FT覆盖快照：193,518场有可信FT，10,444场未核实；未核队列含未来、开赛时间缺失、过去比赛状态未知及provider非full状态，不能把占位0:0作赛果。
- 已审计的53个补充赛程目标新增62,339个唯一FID；该源未提供season字段，未以开赛年份臆造赛季标签。

## Crown AH movement 回收进度

- 原始只读构建的候选为101,266个缺movement capture的FID，manifest SHA256：`5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`。原始清单保持不变，safe-window driver据append-only collector日志生成可续跑manifest。
- 截至03:18:45 UTC日志快照：932次尝试、902个唯一FID已有终态（329 `SAVED`、573 `NO_CROWN_AH_QUOTES`），100,364个FID仍未终结。30次`IncompleteRead`均有后续终态；329条成功capture包含69,588条Crown AH movement报价行。
- 独立落库核验：902/902终态FID对应SQLite历史movement capture；902/902原始响应文件存在且SHA一致；实际接收时间与报价行数量与collector日志一致；所有差异计数为0。原始响应正文和SQLite仍保存在Mac本机，不上传。
- 当前verified quote/capture比例随回收持续变化；显式`NO_CROWN_AH_QUOTES`只表示该条历史响应为空，不外推成永久无盘口。所有响应均为`historical`回取，不称实时赛前收到的行情。

## 当前执行与剩余工作

- 安全窗口driver PID 59381在本检查点时仍运行，底层collector由driver按原有节奏启动，并在MR1/结算等计划任务运行时暂停。未启动并行collector，没有更改Crown collector、节流、生产调度或正式系统。
- Crown summary缺失队列与10,444场FT核实队列仍需分别续采/复核；待movement批次结束后重建全局coverage和哈希清单。继续检查已知项目来源之外是否还有显式联赛配置或可复用历史文件。
- 本次只做数据补采与持久化抽核；无策略研究、模型训练、回测、盈利筛选、正式Telegram派单或正式账本写入。

## 可复核文件

- `audit_movement_collection_persistence.py`
- `movement_collection_persisted_audit_20261122T0318Z.json`
- `CHECKPOINT_SHA256_20261122T0318Z.txt`
