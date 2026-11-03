# Mac 本机四模型测试按钮、凭证配置与 TG 控制 | 2026-11-03

## 用户最新明确要求

用户希望以后本机手动操控，每模型有一个「测试」按钮，是否发 TG 由用户自行勾选，并要求协助把已有的 Token/密钥配置到 Mac。用户不懂终端，不希望为已有项目另建仓库、擅自新增 Gate、改模型或让测试数据混进正式实战。

## 已实际完成

1. Mac `~/QuantAsiaDesk` 的运行页给 **M1 AH、MR1 AH、M3、M4 四模型各加一个可点击「测试」按钮及 TG 复选框**。每个开关改动立即按用户交互保存。TG 未勾选：仅执行本机离线核心测试，不发 TG；已勾选：在模型测试之外尝试发送一条清晰标注「测试消息，非投注单」的 TG 消息，前提是本机已保存相应 Bot Token / Chat ID。只接收到 Telegram 实际 `message_id` 才记测试发送成功。
2. 新增 `model_test.py` 隔离执行真实模型代码：M1 `test_m1_formal_runtime.py` **12 项通过**、MR1 `test-v6-ah-formal.js`+`test-crown-source.js` **6 项通过**、M3 `test_m3_segmented_ledger.py` **2 项通过**、M4 `mr1_two_league_pass_study.py` 真实读取 **557 笔**既有 MR1 结算单并生成反事实研究报告，`research_only=true`/`production_change=false`。这四项均为离线独立验证，不表示赛事 API、Crown 实时取价或正式 TG 发单链路已验证。
3. 测试 TG 回执单独只追加保存为本机 `state/manual_test_telegram_receipts.jsonl`，标明 `kind=TEST_ONLY`、SENT/REJECTED/UNKNOWN 和 `message_id`。任何测试消息均不混入 M1/MR1 正式收据、M3 影子订单或 M4 研究统计；超时/状态不明不自动重发。
4. 修正原 `security add-generic-password -w` 会卡住的凭证保存方式；新增 `mac_keychain.py` 使用 macOS 原生 Security.framework 直接保存/读取，**不用命令行参数传入明文、不会写入 GitHub 或日志**。已在用户授权 Mac 上以临时无敏感测试值实际验证写入、读取、覆盖、删除，测试记录已清理。旧的 `QuantAsiaDesk.<KEY>` Keychain 服务名保持兼容，用户无需终端。
5. “设置→连接设置”改成四组独立配置：TotalCorner 数据 Token、M1 TG 的 Bot Token/Chat ID、MR1 TG 的 Bot Token/Chat ID、M3/M4 研究 TG 的 Bot Token/Chat ID。可整组保存，显示未设置/部分保存/已保存。新加「找接收位置」可在**用户保存机器人 Token 后**只读查询 Telegram 最近更新中的聊天 ID，列出选择项；不会读取聊天正文或自动选接收位置。用模拟响应验证可去重且不回传正文。若机器人正在使用 webhook，可能无法自动查找，此时需要原 Chat ID。BotFather 官方入口链接在折叠区，便于用户找回已有 Bot Token。
6. 已用实际浏览器 Chrome/Playwright 在 1440、980、680、390、320px 检查四个「测试」按钮、TG 复选框、四组连接设置、三组「找接收位置」，全部无水平遮挡、无 JS 错误；点击 MR1 测试后页面正确显示中文离线结果。新 `tests/test_connections.py` **5 项通过**，Telegram 发送模拟、聊天寻找模拟、凭证批量参数校验均无真实外部发送。

## 截至本次实测未完成的外部连接

- GitHub Secrets 已核实存在**名称**：公开 `quant-runner` 的 `TOTALCORNER_TOKEN` / `M1_TELEGRAM_BOT_TOKEN` / `M1_TELEGRAM_CHAT_ID` / `MR1_TG_BOT_TOKEN` / `MR1_TG_CHAT_ID`；旧私有两仓库也有对应 Secrets。但 **GitHub Actions 加密 Secrets 不允许任何 API 读取原文**，用户现有 Mac 原 `QuantAsiaDesk` Keychain 对应项全部未配置；因此**不能安全直接迁移这些明文**。不能绕过此前阻止的私钥/Token 提取。使用者需要在 Mac 本地页面输入一次原有服务值（不能贴入聊天），TG Chat ID 可通过自带查找辅助配置。
- 当前本机 `schedule_enabled=false` 四条链路保持不变；用户此前保存的 `m1.tg_enabled=true` 仍为 true，其他3个 TG false，没有擅自改变。测试 M1 的离线程序成功但 Telegram 因缺本机 Bot/Chat 凭证标注「部分完成，未发送」；MR1/M3/M4 TG 关闭，离线测试成功、没发 TG。
- 上轮用户批准停用的 GitHub 18 个 TG 发单入口不重新启用，仓库和历史订单账本保留。完成本机 Keychain 配置后仍须**由用户主动点模型「测试」**验证 TG 真实 `message_id`，再按用户选择手动运行；本轮尚无可确认的本机正式实盘派单。

源：`ops/localdesk/app.py`、`mac_keychain.py`、`model_test.py`、`web/index.html`、`web/orders.js`、`web/orders.css`、`tests/test_connections.py`。

- 连接页直达入口：`http://127.0.0.1:8765/#connections`，Mac Chrome 实际验证自动展开连接表单（四组）且无浏览器 JS 错误。
