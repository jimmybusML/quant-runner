# M8 Crown 采集链只读诊断（2026-11-19）

## 结论

2026-11-14 后没有新增记录的是共享 `crown_quotes.sqlite3` 的 M7 单次前瞻收据路径，不是整套 Crown 采集停止。该 M7 研究 runner 在 11 月 14 日 01:25 UTC 后没有成功窗口；它不是 launchd 管理任务，11 月 17 日最后状态已过期，当前没有进程。实际停止原因没有被 runner 或系统日志记录，不能进一步断言是崩溃、人工终止还是其他原因。

与此同时，MR1 shadow-v23 的独立背景采集仍由 launchd 每 300 秒运行，并把已核验 Crown 收据写入另一套 append-only snapshot store。冻结读取到的索引中，11 月 14 日后有 **1,344 条**快照索引、**568 条**满足真实 Crown AH 及赛前时序条件的收据，覆盖 **176 个 FID**；其中 **174 个 FID** 不在共享 SQLite 的赛前 Crown 收据集合中。所有 1,344 个快照文件 SHA 和 2,459 个保存的原始 HTTP body SHA 均匹配。因此共享库断档主要是采集路径与存储分叉叠加 M7 runner 停止，而非所有采集进程故障或 MR1 收据未落盘。

## 证据范围与方法

本次读取公开仓库最新 `PROJECT_HANDOFF.md`、`M8_PREMATCH_INFORMATION_LIVE_RECEIPT_AUDIT_20261119.md` 及关联脚本/结果；检查本地 Crown SQLite、其 SHA-addressed 成功响应、MR1 snapshot index/快照/HTTP attempts、launchd 与 runner 状态/日志、五季回填日志及脚本配置。MR1 append-only 索引在 2026-11-19 04:56:34 UTC 固定字节边界后解析。诊断脚本只读源数据库和文件，不向 TotalCorner 发请求，不修改源库、调度、生产模型、Telegram 或账本。

逐场证据：

- [1,330 条 NO_CROWN_AH_QUOTES 对应赛事清单](crown_collection_diagnostic_20261119/no_crown_quotes_event_inventory_20261119.jsonl)
- [失败记录按 FID/层/模式清单](crown_collection_diagnostic_20261119/failed_capture_fid_inventory_20261119.jsonl)
- [机器可读全量结果](crown_collection_diagnostic_20261119/CROWN_COLLECTION_DIAGNOSTIC_RESULTS_20261119.json)
- [只读复算脚本](m8_crown_collection_diagnostic_20261119.py)

完整本地原始响应不复制到公开仓库；公开逐场文件提供 FID、赛事名、开球时间、收到时间、响应 SHA、重复次数及后续收据匹配状态。原始响应仍保存在本地原始数据目录，SHA 校验结果可复算。

## 1. 11 月 14 日后共享库为何没有新有效赛前 Crown AH 收据

共享 SQLite 的 `live/summary/prospective_observation=1/QUOTES_SAVED` 最后收据为 **2026-11-14 01:25:02 UTC**，共有 136 次、95 个 FID、272 条两侧报价行。11 月 14 日最后一场目标是 FID `203961671`，开球 01:30 UTC。M7 runner 的 T−55、T−25、T−5 三次窗口都在该场成功写入 `SAVED=1`；窗口状态却是 `WINDOW_FAILED`，因为独立验证器发生 `training_count_mismatch`，不是 Crown 报价请求失败。

其后 runner 记录了 13 个未完成的赛前窗口、涉及 10 个 FID；11 月 15 日恢复检查将已错过窗口跳过。runner 的循环代码虽会等待每日候选刷新，但没有专属 launchd 自动重启/保活；最后状态是 11 月 17 日 `WAITING_FOR_DAILY_REFRESH`，预期下次刷新为 11 月 18 日 00:15 UTC，之后无新状态、无运行进程。当前没有日志能说明它为何退出。其最新候选库存为 279 场，说明候选队列不是空的。

MR1 背景任务证据相反：`com.quantasia.mr1.collect` 仍在每 5 分钟运行，最近 24 小时约 240 次任务、2,728 个 HTTP 请求；审计截止前最近一次完成于 04:55 UTC。其数据写入 `/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23/`，不是共享 Crown SQLite。故“共享库没有新行”不能解读成“没有新 Crown 采集”。

## 2. 843 次 IncompleteRead、82 次限流及其他失败

SQLite `failed_attempt` 是**每个采集作业/FID/数据层仅保存一个终态错误**，列只有 `attempted_at_utc, fixture_id, data_layer, capture_mode, error_code`。它不保存各次 HTTP 重试、HTTP 状态码、响应头或失败 body。因此以下“次数”是失败作业行，不是 HTTP 请求尝试总数。

| 终态错误 | 失败行 / FID | 类型和时间 | 按 FID 后续状态 |
|---|---:|---|---|
| `IncompleteRead` | 843 / 703 | 全部是历史 movement；11 月 8–13 日 | 703 个 FID 最终均有 movement `QUOTES_SAVED`；701 个保存时间晚于最后错误，2 个此前/无后续错误记录。没有当前 movement 数据缺口 |
| `TOO_MANY_REQUEST` | 82 / 81 | 80 历史 movement、2 live summary；11 月 8–13 日 | 67 个之后保存报价，1 个只有之前/非后续保存，13 个最终无 Crown 报价状态 |
| `URLError` | 2 / 2 | 历史 movement | 两个 FID 后续均保存 |
| `RemoteDisconnected` | 1 / 1 | 历史 movement | 后续保存 |

`IncompleteRead` 表示 HTTP 消息体读取不完整，是传输层截断现象；因为历史失败记录没有保留 `IncompleteRead.expected/partial`、状态码、响应头或对应响应体，无法证明触发点在对端、代理还是中间网络。所有相关 FID 后续都有完整 movement 收据，所以它解释的是重试/失败噪声，不解释 11 月 14 日后的共享 live summary 停更。

`TOO_MANY_REQUEST` 有较强根因证据：MR1 持久化的原始 TotalCorner HTTP attempts 返回该业务码，并明确报告账号额度为 **10 秒 5 次请求**（Boost 为每分钟 60 次）。老 SQLite 失败行没有保存 body，故不能把 MR1 的具体文案逐字追溯到旧 82 条，但业务码与供应商额度错误含义一致。

现有客户端分别独立节流，却共用同一 macOS Keychain `QuantAsiaDesk.TOTALCORNER_TOKEN`：共享 collector 默认 5.2 秒；五季回填覆盖 2.1 秒；M7 runner 覆盖 3.0 秒；MR1 单进程最小间隔 2.6 秒。并发客户端的节奏相加可能超过按凭据计的供应商上限。这是 82 次限流最有证据支持的系统性原因，但因旧失败没有逐次请求时间戳，无法证明每条限流都由哪两个进程的具体重叠造成。

## 3. 1,330 条 `NO_CROWN_AH_QUOTES` 是什么

逐条核验全部 **1,330** 个成功响应文件：SHA 与 SQLite 记录 **1,330/1,330 匹配**；JSON 均为 `success=1`、仅含请求 FID 对应比赛、`bookmakers=[]`，且没有 Crown bookmaker 对象。它们不是失败请求、不是数据库漏写；TotalCorner 在那次请求返回了成功的比赛对象，但当时没有返回任何 bookmaker 报价对象。因此准确结论是“请求时无 Crown 报价数据”，不能证明之后或其他时刻从未开出皇冠盘口。

这些请求涉及 **248 场、23 个联赛**，目标开球时间为 11 月 12 日至 30 日。中位请求收件时间比开球早 **316.44 小时（约 13.2 天）**，P10 为 246.35 小时，P90 为 453.97 小时；单个 FID 被请求 1–6 次（153 场 6 次、74 场 5 次）。这说明主要问题是过早或反复检查时市场对象尚未出现，而不是已收到报价却未入库。后续有 9 个 FID 在共享库另一次获得 Crown 报价，有 13 个 FID 在 MR1 于 11 月 14 日以后获得已验证 Crown AH 收据，直接证明部分空响应只是当时无市场对象。

场次清单包含完整 248 个 FID。最高频覆盖联赛包括西甲/英超/意甲各 20 场、法甲/德甲/荷甲各 18 场；完整分布见逐场 JSONL 与结果 JSON。SQLite 没有保存 request start 和 HTTP 状态码；请求 URL/参数由成功响应对应的采集代码还原为 `GET /v1/match/bookmaker_odds/{FID}?bookmaker=crown`。成功原始 body 有保存且哈希已验证。

## 4. W45/W46 覆盖下降：赛事库存、窗口与存储分叉

以下指标分母不同，不能把快照次数当比赛数：

| 指标 | W45 | W46 | W47（截至 11/19 04:56 UTC，部分周） |
|---|---:|---:|---:|
| TotalCorner 注册赛程库存（按开球周，唯一 fixtures） | 782 场 / 100 联赛 | 166 / 36 | 444 / 80 |
| MR1 snapshot index 行（按收件周） | 7,462 | 1,594 | 655 |
| 其中有效赛前 Crown AH 收据行 / 覆盖 FID | 4,042 / 614 | 776 / 135 | 148 / 95 |
| MR1 `MARKET_UNAVAILABLE` / `MISSED_WINDOW` 行 | 1,656 / 1,730 | 610 / 201 | 377 / 130 |
| 共享 SQLite M7 live `QUOTES_SAVED` 唯一 FID | 86 | 9 | 0 |

注册赛事库存 W45→W46 下降 **78.8%**，W47 回升，因此覆盖下降有显著的真实赛程库存变化成分，不是可以简单归因于数据库损坏或 Crown API 故障。与此同时 MR1 的窗口漏采和 `MARKET_UNAVAILABLE` 仍然存在，说明工作流的排程命中率、市场尚未发布/无报价也有影响。MR1 有效收据不是“所有注册赛事均可报价”的分母：多条时间 horizon 对同一 FID 会形成多条 snapshot，且市场缺失和错过窗口分别记录。

共享 SQLite 的 M7 任务在 W45/W46 仅覆盖 86/9 个 FID，远低于 MR1 的 614/135 个有效收据 FID；这是未汇入同一 SQLite 的独立存储以及 M7 runner 停止所致。对 MR1 来说，索引行、快照文件和 raw body 均通过 SHA 核验（截止 11 月 19 日 04:56 UTC 分别 1,344/1,344、2,459/2,459），没有发现该段已登记数据的存储不完整。

## 5. 当前采集工作流、来源与正式运行依赖

| 工作流 | 作用和来源 | 已确认运行节奏 | 存储/依赖 |
|---|---|---|---|
| 共享 `crown_capture_store.py` | `GET /v1/match/bookmaker_odds/{FID}?bookmaker=crown`；历史 movement 可加 `columns=asianList`；Keychain token | CLI 默认请求间隔 5.2 秒、40 秒 timeout、最多 4 次尝试；其他客户端请求也应共享节流 | `/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3` 与 SHA-addressed raw success bodies |
| 五季历史回填 | 复用 Crown collector，历史 movement | 回填 coordinator 明确覆盖到 2.1 秒间隔；本轮日志显示最终任务完成，launchd 最近退出码 0 | 同一共享 SQLite；不是每 5 分钟正式派单链 |
| M7 T−55/T−25/T−5 前瞻研究 runner | 每日候选刷新后按三时点采集 summary Crown 行 | 单次 runner 代码路径，间隔 3 秒；当前无进程、无专属 launchd | 共享 SQLite。窗口状态还受另一个模型验证器影响，但失败状态不代表报价未写库 |
| MR1 shadow-v23 背景观察 | 先 `/match/view/{FID}` 确认身份，再读取 `/match/bookmaker_odds/{FID}?bookmaker=crown` 及列出的 market；保存 HTTP attempts、源码时间、收件时间和 Crown source verification | `com.quantasia.mr1.collect` 每 300 秒调度；配置每 5 分钟，最小请求间隔 2.6 秒、30 秒 timeout、单次运行最多 180 秒/16 snapshots；T72 至 T0.5 多个 horizon | 独立 `shadow-v23` snapshot index 与 snapshots；使用同一 TotalCorner Keychain token，但**不写共享 Crown SQLite**、不直接派发 Telegram |

Crown 来源要求是 TotalCorner 的 Crown bookmaker 路径；`/match/odds` 默认赔率来源不能替代 Crown。需要区分事件报价 `source/observed_at` 与本机实际 HTTP 收件时间，并要求收件早于 kickoff。该要求由采集方案和 MR1 时序校验实现。现状下 MR1 的采集输出不自动成为共享 M8 SQLite 的数据；任何合并应保留 FID、实际收件时间、来源报价时间、AH 线/双边水位、原始 SHA 和 receipt 分类。

## 6. 可行修复（仅供用户确认；本轮未实施）

1. **按凭据统一节流**：为所有 TotalCorner 客户端共享 token 级互斥/限流器；将 2.1/2.6/3.0 秒各自节奏纳入同一个全局配额预算，并基于真实供应商额度实现退避。此项会改变请求行为，需用户确认后才可部署。
2. **统一读取或汇入收据**：让 M8 只读 MR1 的已验证 snapshot store，或设计经过审核的导入流程到共享研究库；不额外重复请求，保留原始收件与来源时序。会改变研究数据读取/存储路径，先确认方案。
3. **监督 M7 研究 runner**：若仍需要 T−55/T−25/T−5 专用记录，为其加入可观测的运行监督/恢复和清晰的退出记录；任何 launchd/调度改动均待确认。
4. **收敛过早空盘口重试**：按已有 horizon，在合理的后续观察时点再检查，而不是在开赛前 13–20 天短时间重复无盘口请求。它会改变频率/窗口，需确认。
5. **扩展错误遥测**：保留每次失败 attempt 的请求开始/结束时间、状态、响应码、重试序号及截断响应的字节长度/安全摘要，以识别 IncompleteRead 的确切原因。避免记录 token 等敏感信息。此项会改变采集日志格式，待确认。

本报告未修改采集间隔、HTTP 重试、请求方式、AH 策略、原八组、生产运行链、Telegram 或正式账本。采集链的依赖关系和上述修复均为诊断/建议，不构成正式交易规则。
