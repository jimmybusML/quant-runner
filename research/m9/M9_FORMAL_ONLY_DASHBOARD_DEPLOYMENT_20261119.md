# M9 正式双变量泊松 AH 与操作台改革｜2026-11-19

## 用户最新明确要求

从旧 M3 只保留双变量泊松 AH，或者建立独立 M9 供操作台直接操作；赛事范围、既有运行规则和调度时间不变；**只允许正式 Telegram，不允许任何研究 TG 勾选框或研究消息推送**。本轮选择独立 M9，以保留原 M3 历史影子账本、不混淆模型身份。未调整原八组及其他生产模型。

## 已实现的代码及实际状态

- 新独立执行器 `ops/m9_formal_ah.py`：复用 M3 `m1_history_forward.candidate/load_history` 的赛事范围、历史训练来源和原 `kickoff_gate`；仅 `openfootball_shadow.MODELS["bivariate_poisson"]` 和 AH；原 M3 的中性赔率2.0选择方向不变，不新增 EV Gate、赛事白名单或出单数量限制。
- 盘口只调用 TotalCorner 明确指定 `bookmaker=crown` 的 AH 原始响应；核验 Crown 身份、真实 HTTP 收件、原报价事件时间和开赛时间，保存原响应 SHA；严禁将旧 M3 的 `totalcorner_default_NOT_CROWN` 研究报价改名正式下注。
- 新独立 M9 正式事件账本位于 Mac `~/QuantAsiaDesk/state/m9_formal_events.jsonl`，新 Crown 原始响应目录位于 `state/m9_crown_evidence`。只有 Telegram 返回 message_id 的 `M9_TG_SENT` 才计正式已发送；无确认响应记 `UNKNOWN`，不自动盲目重发；按可信FT和完整 AH 四分之一盘结算。旧 M3 影子记录原样保留，不迁移为正式发送。
- 操作台真实服务为 Mac 本地 `~/QuantAsiaDesk/app.py`，网页 `web/index.html`、`web/orders.js`，其他后端 `order_records.py`、`model_test.py`、`job_explain.py`；已直接修订本机文件并重载 `com.quantasia.localdesk`，后台实际 Runner 副本 `~/QuantAsiaDesk/repos/runner/ops/m9_formal_ah.py` 与本次公开脚本一致。
- 操作台运行/设置已显示 M1、MR1、M9、M4；M9 正式 TG 配置独立；原 M3 历史读取仍保留。未经用户授权的研究 TG 复选框、研究机器人连接卡及相关后端发消息流程已移除；向旧 M3/M4 请求 `tg_enabled:true` 的实际HTTP接口返回400，不再可能通过历史设置误发研究 TG。
- 用户原 M3 北京时间 **06:00、12:00** 调度值复制至 M9，原两日扫描和 `>=90分钟` 赛前条件沿用原 M3 程序。旧 Mac M3 自动影子任务已停用，其他 M1/MR1 调度未改。**M9 schedule_enabled=false、tg_enabled=false**，因为用户尚未设置新的 M9 正式 Telegram 接收位置；这不是新增选场 Gate。用户在操作台连接设置选定 M9 正式机器人/Chat ID并启用之后才会正式运行，不允许把其他机器人的目的地偷偷当作授权。
- GitHub 中旧 M3 多个研究工作流仍存在，没有擅自删除或重写；静态检查未发现这批 M3 workflow 有研究 Telegram 实际发送调用。不得将旧 Mac M3 调度停用误称云端所有研究工作流已停。

## 已完成验证（真实执行，不是待办计划）

- `tests/test_m9_formal_ah.py` 六项离线测试全部通过：M3 原选择方向的等价性、Crown来源及原始SHA、拒绝非Crown、四分之一盘口结算、TG未知与已确认严格区分、模型身份。
- 额外对真实 M1 历史联赛ID 1的1777场已完赛历史调用原双变量泊松模型拟合，输出比分概率矩阵和AH方向，矩阵概率和1.0。
- Mac操作台 `app.py` 编译、`orders.js` 与内联脚本 JS语法检查通过。launchd服务重载后真实HTTP `/api/status`、`/api/orders?model=m9`、`/api/run` 的 M9离线测试与报告动作均成功；旧研究 TG 重新开启请求HTTP400。
- M9正式派单真实统计在本轮完成时：**已确认正式TG 0、已结0、未结0、净U 0（无订单）、ROI不适用**。无真实Crown新抓单/Telegram正式消息/真账本新增成交；6项离线测试与正常报告不代表实盘链路已验收。
- 已有 Mac本地 `state/settings.json` 的备份 `state/settings.json.before_m9_migration_20261119`，操作台文件保留 `.before_20261119_m9_authorized_tg_only` 备份。所有正式 TG Keychain秘密没有提交公开仓库。

## 交接

下一步由用户在操作台明确选择 M9 正式机器人/Chat ID，并开启其正式 TG 和调度。确认真实 Crown 盘口及Telegram `SENT` 记录以后，再报告 M9 真正正式运行，不提前宣布。独立 M9 研究/正式账本与 M1/MR1、旧 M3 保持身份分开。

本次仅实现用户确定的 M3→M9 改造、正式TG唯一链路和研究TG功能移除；没有添加自造的数量限制、EV选择门槛、联赛范围或策略条件。Mac操作台属于本地工程，具体已安装路径及状态记于本报告，GitHub保存的是 M9核心执行器、独立测试和交接。
