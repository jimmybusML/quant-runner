# 2026-11-03 Mac 上 MR1 AI 自动开浏览器停用、四模型手动运行故障分析与修复

## 用户明确要求

- MR1 AI 不再自动打开本机 Chrome 并访问 TotalCorner AI Picks。停止该浏览器自动化和独立后台采集，不删除历史数据、GitHub 仓库或本机量化控制台。
- Mac 量化控制台 M1、MR1、M3、M4 手动运行失败需要定位并修复。禁止自行改变盘口来源、策略 Gate、数量范围或正式 TG 模型身份。原 GitHub 18 个 TG 自动派单工作流保持停用。本机 TG 是否派单只由用户自身开关决定。

## MR1 AI 本机自动浏览器（已暂停、源码已修）

- 已确认原 `~/Library/LaunchAgents/com.mr1.ai.extension-bridge.plist` 以 `RunAtLoad=true,KeepAlive=true` 运行，Node bridge `mr1-ai-extension-bridge.js` 正从 Chrome 的 MR1 TotalCorner AI 扩展收卡；原 `com.mr1.shadow-market-collector.plist` 每300秒运行独立市场采集。两个 LaunchAgent 已执行 `launchctl bootout` 并移至 `~/QuantAsiaDesk/state/paused-background-agents/`，核实 `launchctl list` 无 MR1 后台任务，bridge 旧 pid 643 已结束。`com.quantasia.localdesk` 保留运行。
- **真正加载在 Chrome Default/Secure Preferences 的 MR1 AI Unpacked 扩展** ID `peplalmabefbpaihaeehmbncibfgopnf`，实际路径 `~/Desktop/mr1-ai/`。其 `background.js` 含 `chrome.tabs.create` 两个 TotalCorner AI Picks 标签及 `chrome.alarms.create` 每60分钟自动开页，另会在挑战时激活标签；这与用户所述行为完全对应。
- 已备份 `~/Desktop/mr1-ai/background.js` 到 `~/QuantAsiaDesk/state/paused-background-agents/mr1-ai-ACTIVE-chrome-extension-backup.js`，并**实际改写桌面扩展的后台脚本**：删除自动开页函数以及 onInstalled/onStartup 的周期任务创建，改为仅清除旧 alarm，保留手动捕获处理。不再拥有 `chrome.tabs.create`/`chrome.alarms.create` 调用；`node --check` 通过。同步停止并修改了源仓库 `~/Documents/mr1-shadow-display-registry/chrome-extension/mr1-ai/background.js`，原副本备份保留。
- 重要边界：Chrome 已打开的旧 Manifest V3 service worker 可能仍缓存先前的周期回调，必须在**扩展重新加载/Chrome 重新启动**后才能验证旧 alarm 彻底清除；不能仅因编辑源码宣称实时 Chrome alarm 已必然失效。没有杀掉用户 Chrome、其他标签或控制台。

## 手动运行真实结果

- **M1** 失败日志 `20261103T105013Z-49dfa17`：独立预览入口 `ModuleNotFoundError: m1_live_scan`，现已将真实 M1 仓库目录加入本机预览脚本 import path；纯离线模拟验证可运行。正式开 TG 时，日志 `20261103T105035Z-cb1dd61`：原 `m1_notification.claim_key()` 只接受 `GITHUB_RUN_ID/GITHUB_RUN_ATTEMPT`，已改 Mac 本机 worker 对每次手动运行提供唯一真实运行时间身份，保留原 claim/dispatch/持久化防重机制；隔离子进程模拟验证环境值正确。未实际重新发送 M1 正式 TG 单，不能宣称实际 TG 恢复验收。
- **MR1** 原运行 `20261103T105050Z-d2e568a` **真实成功**：采集3条原快照，V6 计算、原结算557单、17待结且新增0单，`persist-github-state.js` 返回 `STATE_PERSISTED`。本机 MR1 TG 开关关闭，无正式 TG 新消息。
- **M4** 运行 `20261103T105058Z-b86a001` **真实成功**：已有 MR1 已结单的历史联赛研究正常运行，M4 无独立正式单。
- **M3** 旧日志 `20261103T105057Z-7c849f3` 在 TotalCorner 赛程 API `json.load` 因 `http.client.IncompleteRead` 失败；仅重试相同页仍不成功。本机用与 M1 相同的 HTTP 客户端 `requests.get` 对原 `/match/schedule` 使用用户自己已保存的本地 Token 进行独立安全验证，实际返回 HTTP 200、完整 JSON、success=1、30条赛程。已据此将 `research/m3/totalcorner_schedule_discovery.py` 替换为相同已验证传输，保留原 rate-limit 处理、source identity、时间逻辑、盘口规则；并对网络截断重试相同页。原 `totalcorner_shadow_settle.py` 的比分 `/match/view` 同样改成 requests 传输，比分、单场身份验证和赔率结算逻辑完全不变。GitHub 对应 M3 workflow 显式安装 `requests`，防止 CI 环境依赖缺失。
- 本机 M3 全流程重试 `20261103T110041Z-2b1fd85` 赛程44页完整取得，首次修复后已成功推进至步骤5历史前瞻，步骤6生成42笔**新影子模拟订单**，步骤7完成状态检查，后进入步骤8赛果采集。完整运行状态必须根据最新 `/api/status` 核实；没有 TG 发送。**若尚在运行，不得报告 M3 整轮成功**。
- 控制台日志页面还增加中文当前阶段提示，隐藏原始失败痕迹中对用户无意义的堆栈，不混淆状态；原日志仍可展开查看。

## 凭证与运行范围

- 最新本机 `~/QuantAsiaDesk` Keychain `/api/status` 已确认 `TOTALCORNER_TOKEN`、M1/MR1 TG、研究 TG 项全部显示已经配置，且 M1/MR1/M3/M4 `schedule_enabled=false`。这比上一份交接记录“全部缺少凭证”的旧快照更新；**切勿再向用户索取已经配置过的 Token**。之前 4 个 TG 测试消息已存在真实确认回执（只属于 TEST_ONLY）；正式账本不得混进测试。
- M1 `tg_enabled=true` 是用户当时自己的选择，其余模型 `false`；本轮没有更改开关和调度。真实正式 TG 发送只发生在用户下一次明确手动运行且原模型产生新有效单时，不自动触发，不用假消息冒充。


### M3 完整运行最终实测结果（后续更新）

2026-11-03T11:20:08Z 原本停在步骤8的本机真实 run `20261103T110041Z-2b1fd85` 已全部执行10步骤并在控制台标为 `succeeded`。已验证 44 页赛程、42 新影子模拟单、444 新结算、整轮已持久化并更新战绩。正式 TG 发单0笔。M3 去重影子账本新结果：发1572、结1494、待78，合计 -30.6375U，时间戳 `2026-11-03T11:20:08.827138+00:00`。本轮新结算444笔来自旧订单补录，不应归咎于新42笔；原 +0.275U 为结算不完整的旧快照。

### M1 真实 API 预览最终验证（后续更新）

用户原 M1 执行失败的模块导入问题已通过真实网络扫描复核：本机独立不发 TG 预览脚本 `scripts/m1_preview.py` 使用已存在的 TotalCorner Keychain 凭证，完整运行退出码0，7联赛采集成功，新候选1、错误0、TG发送0、正式 ledger 写入0。用户 M1 TG 开关仍 true，没有代替用户按键发送正式投注单；`GITHUB_RUN_ID/GITHUB_RUN_ATTEMPT` 的本机兼容由隔离单测通过，但正式 TG 链路仍待实际派单及回执写回验证。
