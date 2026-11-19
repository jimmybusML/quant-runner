# M8 独立赛前信息与新增 Crown 实收审计

审计日：2026-11-19（Asia/Shanghai）  
仓库基准：公开 `main`，审计前 HEAD `df9c32aa6fafe50e55141916bc2c48cac1a501b1`。  
范围：只读盘点现有赛前信息与 live Crown receipt；原八组和全部生产/采集规则冻结。

## 结论

**本轮没有发现可支持新盈利订单来源的、带可靠赛前可得时间的独立信息，也没有真正未见且已结算的新 FID。** 因此本轮没有训练新模型或在已有信息上改名重跑失败实验。对本轮新增候选而言，历史回放、真实 Crown receipt 回放、真正新样本均为 0 单；净U、ROI、周均量和回撤不适用，不把“没有可评估订单”写成零收益模型。

本轮在只读 Crown 数据库中核验到 95 个 FID 的 136 次 live summary HTTP 收件，共 272 条 Crown open/close quote 行。136 个原始响应文件全部存在且 SHA256 与数据库记录一致；所有报价记录均在数据库开球时间之前，0 条 quote source time 晚于 HTTP receipt。**这些是较新的报价观察，不是新的比赛结果或独立赛前球队信息**：95/95 FID 已进入既有 M8 receipt/FT 研究库存；其中 89 个也已在旧的独立审核实收档案出现。剩余 6 个不是新比赛，只是旧库存比赛后来多了一条 Crown receipt。此前 FT 锁档对这些 FID 的 score 字段为空，不能据它声称新结算样本。

## 可用赛前信息盘点

表中时间可靠性只指数据本身能否证明“在目标 Crown 报价/下单前已可见”，不把比赛日期、网页更新时间或文件修改时间当成首次发布时间/系统接收时间。

| 数据源 | 库存/覆盖 | 时间证据 | 相对 R1–R65、A–L、M1–M8 的新增价值与本轮结论 |
|---|---:|---|---|
| `appearances.csv.gz` | 1,894,350 行 | 仅赛事日期，无首次发布/接收时间 | 球员分钟及历史表现已在 R63 权重研究使用；不能证明当时信息可见，R63 未支持扩单。 |
| `game_lineups.csv.gz` | 3,179,016 行 | 仅赛事日期，无 lineup 首发公布或本系统接收时间 | R50 已测阵容稳定性；目标阵容记录无法证明赛前，重复检验没有新增信息价值。 |
| `games.csv.gz` | 88,958 行 | 有赛事日期，无数据采集/首次可用时间；目标行含最终比分和赛后字段 | R26–R30、R39–R46 等已覆盖实力、排名、赛程/环境代理；原始表不能建立时序可用性。 |
| `transfers.csv.gz` | 175,165 行 | 有 transfer date，无公告和接收时间；存在晚于数据截止日的日期 | R50 已测转会历史；日期不能证明 Crown 报价前公众已知，数据截至 2026-07-06。 |
| `player_valuations.csv.gz` | 6 列表头，读取中途 EOF | 无可用快照链；gzip 截断损坏 | R50 曾尝试但未使用；无法构造可审计估值变化序列。 |
| Guardian 伤停/球队新闻归档 | R61–R65 已审新闻文章及 2024–26 稀疏归档 | 页面发布时间/修改时间不等于首次公开或本系统收到；事件时间审计只支持极少数明确新事件 | 旧研究已覆盖 injury/news 和球员权重；R62 的小幅总体正收益不稳健，R63 负向，R64/R65 事件不足且缺精确报价时间。无新来源，不重跑。 |
| `m8_espn_cached_performance_verified_20261115.jsonl` | 3,825 个赛后统计记录 | 无目标比赛的赛前首次可见/接收时间 | R27–R30 / R45 类工作已研究；其射门、控球等多为赛后变量，不能作赛前特征。 |
| `m8_independent_score_strength_20261114.jsonl` | 40,277 行；旧报告 Crown join 39,101 行 | 历史比赛 event-time 可排序，但没有当时信息快照/系统接收时间 | Crown/team residual 和普通历史强弱研究已覆盖；不能重复普通盘口/球队 Ridge。 |
| `future_eng_20261121.json`、`future_nor_20261120.json` | 两个未来 fixture 快照 | `news[].published_at` 存在但无 HTTP 接收证明；文件 mtime 不作时序证据 | 快照无对应 live Crown receipt，也无赛果；其 ESPN odds/pickcenter 不属于允许的 Crown/TotalCorner 盘口。不能核算盈利或称新验证。 |
| `past_eng_candidate.json` | 单场历史快照 | 无可靠取得时点 | 不能证明目标信息是赛前且未参与设计；不作样本。 |
| `competitions.csv.gz` | 65 行 | 静态 ID/赛事元数据 | 仅可关联赛事，不能提供独立时变信息。 |

真正尚未研究且有经济解释的字段，只有在补齐原始首次公开时间、系统接收时间及版本历史后才可能成为新特征。本轮没有任何现有团队/阵容/伤停/比赛性质源同时满足时序可证、可按 FID 对齐 Crown 和可测真实结算的条件。与 R1–R65 的差异检查、数据列、样本数、SHA 和失败读取原因见审计 JSON。

## Crown live receipt 审计

| 状态 | capture 数 | FID 数 | quote 行 | 本轮处理 |
|---|---:|---:|---:|---|
| `QUOTES_SAVED`, prospective=1 | 136 | 95 | 272（136 open + 136 close） | 真正赛前收件；逐文件 SHA 全通过；每条报价早于开球；无可评估新候选。 |
| `QUOTES_SAVED`, prospective=0 | 3 | 3 | 6（3 open + 3 close） | 非前瞻收件，排除。 |
| `NO_CROWN_AH_QUOTES`, prospective=1 | 1,330 | 248 | 0 | 有 HTTP 响应但无 Crown AH 报价，不能当下注或替代盘口。 |

前瞻报价的 source-event 时间范围为 2026-10-25 22:47:20Z 至 2026-11-14 01:15:54Z；HTTP 收件时间为 2026-11-08 13:04:49Z 至 2026-11-14 01:25:02Z。95 个 FID 全部与既有 `m8_new_receipt_frozen_eight_FT_20261115.jsonl` 交集；截至本轮没有收到此后新的 live Crown capture。失败尝试记录另有 928 条（`IncompleteRead` 843、`TOO_MANY_REQUEST` 82、`URLError` 2、`RemoteDisconnected` 1）；本轮只记录既存状态，不改采集流程。

前瞻报价观测按 HTTP 收件 ISO 周分布为 W45：106 次 capture、86 个唯一 FID；W46：30 次 capture、9 个唯一 FID。它是**报价观测覆盖周分布**，不是订单数、盈利周或收益曲线；没有本轮候选，故新候选的周净U、ROI 与回撤均不适用。

额外报价不等于新赛果。89 个 FID 与既有 1,230 条实际 HTTP receipt 审核档案重合；另外 6 个 FID 为 `202812905`、`202816371`、`202816384`、`203961667`、`203961671`、`204010286`，也全部在此前 M8 研究/receipt-FT 库存出现。故它们可用于既有 FID 上的报价观察，不能视为 6 场新独立测试。没有新信息预测、模型冻结阈值或未见 FID 可在本轮回放。

## 研究结果口径

| 样本类型 | 本轮新候选单量 | 净U / ROI | 周分布 / 回撤 | 说明 |
|---|---:|---|---|---|
| 历史 TotalCorner/Crown 回放 | 0 | 不适用 | 不适用 | 没有符合新机制条件的信息变量；不重跑已失败的熟悉度、H2H、普通 Crown Ridge、q80 或其他同义实验。 |
| 真正赛前 Crown receipt | 0 | 不适用 | 不适用 | 95 个 FID 是报价观察量，不是本轮候选信号；旧 1,230 收据池及旧盈利/亏损已在 prior reports 里核算，不能冒充本轮盲测。 |
| 真正未见且已有可信 FT 的新样本 | 0 | 不适用 | 不适用 | 95/95 live receipt FID 与旧 M8 库存重合；两条未来 ESPN fixture 无 Crown receipt、无赛果。 |

“0 单”表示没有新的可验证候选，并不代表模型净U为 0。已有独立信息候选的历史损益只作为查重背景：前轮熟悉度方向八组外 3,028 场、−89.620U、ROI −2.960%；直接交锋 AH 残差方向 17,126 场、−590.860U、ROI −3.450%；报价新鲜度是描述诊断，无独立选边信号。原八组仍冻结，2024–26 基准 6,873 场、+197.765U，具体口径见前轮报告；本轮没有新增单可合并，因此八组贡献不变。

历史表现按 Crown AH 真实线/赔率与正确 quarter-line settlement 计算；本轮没有候选订单，所以无新的 AH 结算。真实收据结果不得称为正式 Telegram 实战。没有使用 TotalCorner 以外赔率，也没有用替代市场填补无报价行。

## 可复现与提交清单

- 审计脚本：`research/m8/m8_prematch_information_live_receipt_audit_20261119.py`。只读 Crown SQLite、只读本地数据源；逐项记录行数/字段/源文件 SHA，核验 136 个原始响应 SHA，输出 95 FID provenance 行。
- 机器可读汇总及来源清单：`research/m8/prematch_information_audit_20261119/M8_PREMATCH_INFORMATION_LIVE_RECEIPT_AUDIT_20261119.json`；执行manifest：同目录 `execution_manifest_20261119.json`。
- 逐 FID 时间、哈希与旧研究交集：`research/m8/prematch_information_audit_20261119/crown_live_fid_provenance_20261119.jsonl`。
- 运行命令：`python3 research/m8/m8_prematch_information_live_receipt_audit_20261119.py`；输出包含执行UTC时间、输入SHA、失败响应状态及逐FID evidence。
- 未修改原八组、生产模型、Telegram、正式账本、数据采集或结算流程；无新 Gate、筛选门槛、限制或自动化条件。
- 需要未来验证的证据缺口：带不可变 source timestamp 与本系统 received timestamp 的球队/阵容/伤停/比赛性质历史快照；同一 FID、同一时间真实 Crown receipt；以及未进入既有研究设计且有可信 FT 的独立新 FID。成交/拒单/滑点记录仍缺失，不能证明理论价可执行。
