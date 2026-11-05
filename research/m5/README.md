# M5 独立融合研究

**最新收益目标（2026-11-05 用户重启）**：AH、OU 独立研究，任一市场的样本外 ROI ≥3% 即达到收益指标；每个市场仍需至少10,000场真实唯一历史比赛。Crown 优先；缺少可用 Crown 市场报价时允许使用 TotalCorner（TOTAL），两种来源分别标识及统计。下方旧报告中的“两个市场均需 >5%”属于早期目标记录，已被本目标覆盖。

生成时间：2026-11-05 UTC。M5 是独立研究身份；本目录不连接 M1/MR1/M3 的生产预测、订单、账本或 Telegram。当前已有真实概率前推实验、Crown AH/OU 回放和同场 OU quote-time 配对诊断，但尚未完成每市场10,000场 Crown 历史收益验证或 M5 Actions 验收。最新报告与新增 quote-time 诊断见 [M5_PROGRESS_REPORT_20261104.md](M5_PROGRESS_REPORT_20261104.md)，当前 M5 forecast 生成于 `2026-11-04T21:39:54Z` UTC，依赖回放于 `2026-11-04T21:41Z` UTC 重算。

截至 2026-11-05 M5 Crown 回填重启，已按完整 UTC OOS forecast 重建 127,674 个候选；截至 `2026-11-05T17:04:32Z` 私有 Crown 采集 checkpoint 为8,600/127,674处理、8,546个精确响应，AH/OU各7,687场有赛前源事件报价，身份/时间错配0；采集仍在运行，不能把进度当作 ROI。重启前已有验证赛前报价212 AH、212 OU；去重后的同价 MR1 V6 可比 cohort 每市场870场。所有样本均未达到每市场10,000场。GitHub Actions 中现有 `TOTALCORNER_TOKEN` 与 `PRIVATE_REPO_TOKEN` 只确认了 Secret 名称，未读取值；可访问的 private bridge 当前没有 M5 forecast/raw quote 输入。公开仓库已有 M3 专用 Crown 前瞻采集，最新成功 run [41968378899](https://github.com/ljm198964-alt/quant-runner/actions/runs/41968378899) 只增加 9 AH / 9 OU M3 quote commitments，不含价格、EV 或 ROI，也不计入 M5 样本。详见 [M5 Crown archive coverage audit](M5_CROWN_ARCHIVE_COVERAGE_AUDIT_20261105.md)。

新增的 exact same-quote M5/M1 V23 Crown OU 对照使用 `/private/tmp/m1-m5-private` 现有归档：56 场冻结报价 eligible，严格配对 M5 OOS、赛前收据和独立 FT 后保留 23 场。M5 ROI `-8.804348%`，M1 V23 calibrated ROI `-0.543478%`；两者均低于本次 `>=3%` 收益目标，且样本远不足10,000。聚合结果及复现代码见 [same-quote replay](results/m5_m1_v23_crown_ou_comparison.json) 与 [script](m5_m1_v23_crown_ou_comparison.py)。

当前基础快照见 [M5_PROGRESS_REPORT_20261104.md](M5_PROGRESS_REPORT_20261104.md)：133,140 个 partial-scope 完赛候选、127,674 个 UTC 年×联赛 OOS 预测、584 折；forecast SHA `ebc8ae9aa4c873f3d276510533a9961c607cc607614f976a2d2e1147dbdb356a`。重启目标下，Crown 仅在两边均达到10,000唯一样本后才满足样本量要求；旧数据仍不足。近期严格 M5/M1 V23 同价 Crown OU 比较只有23场，M5 ROI -8.804348%、M1 calibrated ROI -0.543478%；未达到新目标。截至 `2026-11-05T17:06:31Z` 的最新 partial Crown-first event-time replay 有7,705场/市场（采集 checkpoint 8,600/127,674、AH/OU各7,687场源事件赛前价；回放时采集仍继续），AH `-98.065U / -1.272745%`、OU `-297.715U / -3.863920%`。AH 全赢/半赢/走水/半输/全输为3121/520/530/550/2984，OU为3179/417/406/542/3161；最大回撤分别144.940U、316.700U（按盘口源事件时间）；bootstrap 95% ROI区间分别-3.275406%至+0.716548%、-5.833809%至-1.886113%。本次有6条记录没有可配对的响应接收时间索引，已排除在7,705场外，需在采集终态再次核验。其余样本响应均在开赛后回取，故仅是回顾性源事件时间模拟ROI，不是赛前真实接收或可执行ROI。训练结束时间早于预测时间，盘口源事件时间位于预测时间与开赛之间；唯一比赛键及比分用于结算。样本只覆盖2026 UTC开赛年，尚差每市场2,295场至10,000，AH/OU全线基准均未达到+3%目标。联赛/时间拆分仅为描述，不筛选。完整聚合及输入哈希见 [2026-11-05T17:06:31Z partial replay receipt](results/m5_source_union_replay_partial_20261105T170631Z.json)。已实现但尚未运行 TotalCorner default (`totalcorner_default_NOT_CROWN`) 缺市场回退采集器；它等待 Crown 回填完成后再请求。当前 Crown 历史报价回填在私有目录运行，见 [`M5_CROWN_ARCHIVE_COVERAGE_AUDIT_20261105.md`](M5_CROWN_ARCHIVE_COVERAGE_AUDIT_20261105.md)。代码与产物：

- [probability_stack_oos.py](probability_stack_oos.py) → [M3 13,234 场逐季前推概率结果](results/m5_probability_stack_oos.json)
- [m1_ou_crown_small_archive_replay.py](m1_ou_crown_small_archive_replay.py) → [M1 冻结 Crown OU 小样本回放](results/m1_ou_crown_small_archive.json)
- [exact_m1_m3_join_audit.py](exact_m1_m3_join_audit.py) → [M1/M3 精确交集覆盖审计](results/m1_m3_exact_join.json)
- [mr1_local_crown_replay.py](mr1_local_crown_replay.py) → [MR1 私有本机存档的安全聚合 Crown 重放](results/mr1_local_crown_replay.json)
- [m3_crown_exact_line_replay.py](m3_crown_exact_line_replay.py) → [M3/M5 OOS 与 MR1 同 Crown 线价对照](results/m3_crown_exact_line_replay.json)
- [m3_grid_crown_replay.py](m3_grid_crown_replay.py) → [同期全比分网格与 Crown 任意主盘探索](results/m3_grid_crown_replay.json)
- [probability_stack_league_oos.py](probability_stack_league_oos.py) → [逐联赛 walk-forward 权重与单模型对照](results/m5_league_local_probability_oos.json)
- [crown_historical_capture.py](crown_historical_capture.py) → 受限速、断点续跑的私有 TotalCorner 历史研究采集器；原始 Crown 响应必须写到公开仓库之外。本机采集进展与数据仍是私有输入，公开报告只保留聚合信息。
- [m5_goal_model_oos.py](m5_goal_model_oos.py) → 独立 Poisson 比分分布候选；读取私有完赛赛程清单，按联赛和 UTC 年份前推，仅输出公开聚合指标，逐场预测留在仓库外。已基于当前 partial 输入生成 127,674 场真实 OOS 概率预测；完整 51 联赛历史范围尚未取得。
- [m5_goal_model_partial_oos.json](results/m5_goal_model_partial_oos.json) → partial scope 下的 584 折 OOS 概率报告，ROI 为 null。
- [m5_goal_model_m3_comparison.py](m5_goal_model_m3_comparison.py) → M5 独立进球模型与 M3 原版三模型在精确相同 fixture 上作 proper-score 对照；本轮 n=7,663，AH 仅为 1X2 概率代理，Crown ROI 不在此报告。
- [m5_goal_model_m3_common_oos.json](results/m5_goal_model_m3_common_oos.json) → 7,663 场同样本 M3/M5 指标与来源哈希。
- [m5_goal_model_oos_blend.py](m5_goal_model_oos_blend.py) → M3 与 M5 概率按 UTC 年嵌套前推拟合融合权重；完整四模型权重回执及 OOS proper score 在 [nested blend result](results/m5_goal_model_nested_blend.json)。AH 1X2 代理、OU2.5 独立拟合，无 Crown ROI。
- [m5_mr1_crown_oos_replay.py](m5_mr1_crown_oos_replay.py) → 只读地把 M5 逐场预测连接到本机 verified Crown/FT archive，并输出 AH/OU 分开的同场 ROI、赛季、联赛及 M3/MR1 可比样本聚合。
- [m5_goal_model_mr1_crown_oos.json](results/m5_goal_model_mr1_crown_oos.json) → partial source scope 内 AH/OU 各 212 个严格 Crown/FT 交集的 M5 OOS 回放；不公开逐场数据。
- [m5_goal_model_totalcorner_crown_partial.json](results/m5_goal_model_totalcorner_crown_partial.json) → TotalCorner Crown endpoint 事件时间来源的独立 212 场/市场 partial 重放；与 MR1 存档样本不混合。
- [m5_crown_factor_audit.py](m5_crown_factor_audit.py) → 对赛前 quote time、盘线/水位变化做不含逐场明细的分位描述；不是策略筛选器。完整汇总见 [factor audit](results/m5_goal_model_crown_factor_audit.json)。
- [m5_m1_same_quote_oos_replay.py](m5_m1_same_quote_oos_replay.py) → M1 V23 的OU预测均值与M5在同一 Crown 盘口/水位/verified FT上的精确 fixture 配对回放；当前 OU n=14（AH无样本），不能外推。结果见 [same-quote report](results/m5_goal_model_m1_same_quote_oos.json)。
- [m5_m1_v23_crown_ou_comparison.py](m5_m1_v23_crown_ou_comparison.py) → 将 M5 年度前推比分网格与私有 `/private/tmp/m1-m5-private` 的 M1 V23 frozen calibrated total 在相同 Crown OU 合约、同一独立 FT 上比较；当前严格共同 n=23，均未达到新目标。报告 [aggregate receipt](results/m5_m1_v23_crown_ou_comparison.json) 不含原始价格、fixture IDs 或逐场记录。

### 2026-11-05 M3/M5 固定合约时间留出复核（研究回放）

新增 [`m5_m3_crown_archive_blend_replay.py`](m5_m3_crown_archive_blend_replay.py)，将 M5 的逐场比分分布与公开 M3 严格 OOS Poisson、Dixon-Coles、Bivariate Poisson 概率在精确相同 fixture 上比较。只评价 M3 原生支持的 Crown AH0 和 OU2.5 合约。训练集截至 2026-08-31；固定 `2026-09-01 UTC` 之后为时间留出期。每市场的 M3/M5 混合权重只用训练集对数损失按0.05步长拟合，再以训练对数损失选模型；留出ROI未用于权重或模型选择。没有EV、联赛或其他投注筛选条件，每个有效fixture每市场模拟1U。

| 市场 | 训练唯一合约 | 训练选择（M5权重） | 留出唯一比赛/注数 | 全赢/半赢/走水/半输/全输 | 净收益 | ROI | 最大回撤 | Log Loss / Brier | ROI bootstrap 95% |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| Crown AH0 | 66 | M3 Dixon-Coles（0%） | 38 | 20 / 0 / 11 / 0 / 7 | +11.650U | +30.657895% | 3.000U | 1.05453363 / 0.63473806 | +6.552632% 至 +53.552632% |
| Crown OU2.5 | 144 | M3 Bivariate Poisson（0%） | 59 | 33 / 0 / 0 / 0 / 26 | +4.790U | +8.118644% | 8.450U | 0.68569524 / 0.49259476 | -16.474576% 至 +33.016949% |

同一留出样本上的 M5 单模型为 AH0 `+9.650U / +25.394737%`（38场），OU2.5 `-0.480U / -0.813559%`（59场）。M3/M5训练期拟合在AH两种、OU Bivariate模型均选择0% M5权重；目前没有证据显示融合优于选中的M3模型。概率模型的选择未依赖留出ROI。AH、OU分别计数；这两条固定合约的半赢、半输均为0。

该阶段性结果数值上两市都超过+3%，但每市场只有38/59场，远未达到既定10,000唯一真实历史比赛目标。所有报价响应都在开赛后回取；预测是按历史训练截止时间重建的walk-forward输出，也不是当时已存档的即时信号。因此这是严格时间顺序的回顾性模拟，不是可执行实收ROI，不能作为 M5 验收完成。训练/留出覆盖：AH0 训练2026-03-01至08-30、留出09-05至11-02；OU2.5训练03-01至08-31、留出09-03至11-01。精确键冲突0，M3赛果与M5赛程分数不一致的26条已排除。只有 M3 覆盖的六个联赛参与此比较；它是模型对照支持范围，不是新增的策略联赛过滤。来源仅 Crown，无 TotalCorner报价参与。聚合结果与输入SHA见 [M3/M5 holdout receipt](results/m5_m3_crown_2026_holdout_20261105T170736Z.json)。

## 可复核数据现状

| 数据 | 唯一赛事/样本 | 能支持什么 | 不能支持什么 |
| --- | ---: | --- | --- |
| M3 penaltyblog 严格赛季前推预测（Football-Data.co.uk 赛果输入） | 最新报告 17,151 个测试比赛，14,806 场有全部三模型评分预测；当前季 121 场与本机 Crown 索引精确连接，AH0/OU2.5 各有 24/36 场有效价 | 全历史概率评分；当季子样本的 Crown ROI 与同价 M3/M5 比较 | Crown 子样本很小、不能代表 14,806 场；仅发布的 1X2/AH0 与 O2.5 概率不支持任意线结算 |
| M3 同期 penaltyblog 全比分网格 | 39 个 provider ID 有三模型网格；18 场有可验证赛前 Crown 报价；其中 17 场与严格 M3 OOS CSV 精确交集 | 用完整比分分布评价 Crown 任意主盘 | 缓存训练输入未封存逐条内容 hash/结果可得时间，属于探索性扩展，不作为无泄漏证明或主要 OOS 样本 |
| MR1 Crown forward 历史快照，经公开 M4 配对报告 | 1,563 个不同 fixture；AH 1,563、OU 1,563 | 已验证 Crown 标签、报价时点早于 kickoff、FT 观察时点晚于 kickoff 的回放结果 | 是 MR1 历史模型选择的回放，不是 M5 独立模型；不足 10,000 场 |
| M1 `data/m1_history_cache` | 60 个 JSON 缓存文件（仅检查文件清单/大小） | M1 既有训练赛果缓存 | 缓存不是 Crown 报价档案；文件数不等于赛事数 |
| TotalCorner `/match/bookmaker_odds/{id}` | 代码已有 Crown 专属接口调用 | 技术上存在 Crown endpoint 与独立采集实现 | 本轮按用户指示复用现有 Crown 授权与本机凭证，采集仅限明确 crown bookmaker endpoint；历史授权档案中的具体书面范围尚未随 M5 公共产物披露，原始数据仍留私有目录 |

M3 报告 `research/m3/results/latest_penaltyblog_oos_report.json` 最新由 Actions run [41864900732](https://github.com/ljm198964-alt/quant-runner/actions/runs/41864900732) 生成于 2026-11-04T16:16:39.480507Z；该 run SUCCESS，源输入指纹/测试身份/模型版本与上一报告完全相同，9 项 penaltyblog 模型-市场比较分数差均为 0，故这次没有新增学习信息。报告列明训练与测试严格按比赛日期/赛季隔离、当日测试结果不用于训练，且明确 `crown_roi: null`。预测 SHA 仍为 `9375bdbb...csv`，有 17,151 个唯一测试行身份，其中 14,806 行有评分预测。同目录多个预测文件是不同运行快照，不能相加来扩大赛事数。

MR1 全量历史旧基准来自公开 GitHub Actions run `41425306084` 聚合 artifact。另对本机现存 MR1 V23 snapshot index 做只读精确连接，匹配 M3 当前季 121 场；公开结果只存聚合/哈希，不公开逐场安全原始记录，故没有把 MR1 私有记录复制到仓库。

## 本机 Crown 存档复核

本机 MR1 现存 snapshot 经严格 verified-Crown、received < kickoff、FT observed > kickoff 和 fixture identity 检查，得到 1,621 场唯一有效比赛。AH -67.655U/-4.1737%，OU -57.985U/-3.5771%，均为逐场每市场 1U。数据与结果均为本地研究 snapshot 聚合，输入 SHA 与 source HEAD 已保存；不包含公开逐场价格、ID、球队或原始账本。它不能与公开 M4 1,563 场报告逐场核对，不能声称是新增 58 场，也不是 M5 业绩或 M5 Actions 验收。

对当前公开仓库与历史工作流的只读检查确认 Actions Secret 名称 `TOTALCORNER_TOKEN`、`PRIVATE_REPO_TOKEN` 存在（只读元数据，未读取值）；未发现 OddsPapi credential、connector 或保存数据。M3 的 Crown 专项探针于 2026-10-21 有六次成功的只读诊断运行，最新 run 为 `39584036612`；该探针使用固定历史 match IDs，没有形成前瞻报价档案。M3 既有定时 forward-EV 工作流调用的是 TotalCorner **default bookmaker** endpoint（代码明确标为 `default_unspecified_NOT_CROWN`），没有将其价格算作 Crown。当前 M3 独立研究最近一次成功 run 为 `41864900732`（2026-11-04 UTC），输出严格日期/赛季前推预测，不含 Crown 报价；该次输入指纹未变，没有新增学习信息。用户已确认继续复用现有 Crown 数据授权，本轮未申请新凭证；原始 quote 仍仅在本地归档做只读配对。更完整的来源、工作流和 ToS 审计见 [M3 Crown audit](../m3/M3_CROWN_STAGE_A_B_AUDIT.md)。

## M3/M5 小样本 Crown OOS 切片

严格精确键连接得 121 场 2026/27 M3 OOS fixture，排除 1 个身份碰撞；verified Crown AH0 双侧报价覆盖 24 场、OU2.5 覆盖 36 场。M5 walk-forward blend：AH +5.91U/+24.625%（24 注，95%按 fixture bootstrap 区间 -5.42% 至 +53.54%）；OU -1.66U/-4.611%（36 注，区间 -36.03% 至 +26.94%）。MR1 保存策略与同 quote line/side price/received timestamp 完全一致且有 MR1 verified FT 的共同样本为 AH 11 场、OU 21 场；同样本 M5 AH +30% 对 MR1 +15.45%，OU M5 -27.38% 对 MR1 -28.43%。均是研究回放，小样本，不能外推。详细 M3 单模型、M5、MR1 结果和分联赛聚合见 JSON。

独立的任意主盘网格探索在严格 M3 OOS CSV 交集 AH/OU 各 17 场，ROI 分别 -1.44% 和 -23.41%。该模型使用历史比分缓存，但未逐 forecast 封存训练输入 hash 与结果可得时间，因此仅作同期预测与 Crown 配对覆盖探索，不视为无泄漏证明。它与 AH0/OU2.5 样本不可直接合并。

## 明确结论

- 公开可核实 M4 聚合为 1,563 场，另有本机 MR1 1,621 场只读回放；公开安全聚合的 M3/M5 同线价 OOS 仅 AH 24 场、OU 36 场，远低于 10,000。
- 17,151 场 M3 OOS 赛果可支持概率研究，但其来源不含 Crown 历史报价；不以其他公司的赔率补值，也不将 M3/MR1/M1 的生产模型输出伪装成 M5 融合策略。
- 用户已确认使用既有合法 Crown 授权，不申请新授权或凭证。当前公开文件不保存授权文书或逐笔报价；Secret 值与私有原始数据未读取/公开，本研究只发布脱敏聚合和哈希。
- 本轮按用户指示复用了已有 Crown 授权与仓库外私有采集记录；没有读取或输出凭证。TotalCorner 历史 movement endpoint 的赛前事件时间不等于赛前接收时间，相关结果与 MR1 verified received-before-kickoff archive 分开报告。
- M3/M5 严格季前推小样本 Crown ROI：AH0 +24.625% / 24 场，区间跨零；OU2.5 -4.611% / 36 场。任意主盘网格探索另为 n=17/市场，AH -1.44%、OU -23.41%，但训练输入时间证据不足，不能用于主 OOS 结论。以上均未达到 10,000 场验证目标。公开 M4 MR1 旧基准 AH -2.8276%、OU -2.9706%（各 1,563 场）不可与本轮小样本直接比较。

## 下一步数据要求

要继续到 10,000 场 M5 Crown 回测，需要至少 10,000 个唯一比赛的精确 UTC kickoff、唯一 fixture 身份、Crown 原始两侧 AH/OU 线价及可信赛前 capture/received UTC、FT 来源/时间。用户已确认复用现有合法 Crown 授权；本研究继续限定在 Crown 专属接口并将原始数据留在仓库外。现有真实赛前历史快照只支持报告中已列明的小样本，不能扩写为更大历史覆盖；新增前瞻采集需保留实际接收时间，不能倒填历史价格。

满足数据条件后，M5 必须先固化一个新的独立基线；按 UTC 日期扩展训练/滚动预测，模型参数仅用已发生赛果，避免同日及未来泄漏。AH/OU 分别输出概率校准、Log Loss、Brier、样本数、赛季拆分及 Crown 覆盖。收益回测采用相同 fixture 集合比较可比模型，并按亚洲盘半赢/半输/走水结算；不通过事后门槛筛选追 ROI。

### 最新采集 / 模型快照（2026-11-04T19:46:15Z）

后续扩展版报告已覆盖 86,064 场候选赛程、82,377 场 UTC 时间前推 OOS 预测 / 375 折，仍是不完整的 51 联赛历史清单（34 联赛已分页、164 已知页缺失）。当前版本 forecast SHA `1112fe6833c1b6c4f9f6c2826a8b2239aa8821c5bd1a2112c9fd0887b6083853`；M3 同场 n=7,663，嵌套融合评估 n=7,252。proper score 不是交易收益。

当前 SHA 上的 Crown 配对：MR1 verified received-before-kickoff + 独立 FT AH/OU 各 212 场，ROI `+1.247642%/-0.360849%`；TotalCorner endpoint historical movement 各 212 场，ROI `+2.766509%/-0.283019%`，但事件时间早于 kickoff 不证明响应当时已收到，不能称为 received-forward 报价。二者不合并。详细覆盖、逐年评分、比分命中、季度因素和哈希见 [最新报告章节](M5_PROGRESS_REPORT_20261104.md)。当前 M1 same-quote OU 精确配对 n=15、AH=0；M5 ROI `+7.566667%`，M1 calibrated `+32.633333%`，样本不足以外推。历史采集进程仍活跃；M5 Actions 未运行、ROI >5% 与 10,000 Crown 样本目标均未达到。

最新 forecast SHA 与完整的 Crown 样本时间分层见 [进度报告](M5_PROGRESS_REPORT_20261104.md) 最后一节；当前 OU M1 同价精确配对为 n=14，AH 为 0。

当前最新 OOS、跨年评分与三类 Crown 时间证据的逐项拆分见进度报告末节（82,377 场 forecast SHA `1112fe6833c1b6c4f9f6c2826a8b2239aa8821c5bd1a2112c9fd0887b6083853`）。

本轮最新配套回放与 AH/OU 结算表见进度报告末节，MR1 verified sample 各 n=212，TotalCorner historical-event sample 各 n=212，M1 OU exact subset n=15。

说明：最后训练输入冻结在 34/51 leagues；报告生成后 schedule collector 又记录 35 leagues complete / 2,745 saved pages（20:07:32Z），尚未纳入该 forecast，须待后续冻结并重训。
- [m5_goal_model_training_support_audit.py](m5_goal_model_training_support_audit.py) → [按先验训练赛数汇总的 OOS proper-score 诊断](results/m5_goal_model_training_support_audit.json)；仅用于研究稀疏历史下的参数收缩，不作为下注筛选。
- [M5 近期赛果加权候选报告](M5_RECENCY_MODEL_CROWN_OOS_20261105.md) → 每联赛只用 2025 赛果选半衰期、2026 逐联赛严格 UTC OOS：10,235 场同场样本 AH 1X2 proper score 小幅改善，OU 略差；最新 MR1 archive snapshot 上每市场 871 场已收 Crown + 独立 FT 的同价样本 ROI 为 AH -1.944891%、OU -3.729621%。再加入 70 个不重叠 TotalCorner event-time Crown fixture-market 后，941 场去重并集 ROI 为 AH -2.859192%、OU -3.506908%；两者均未超过 +5%，bootstrap 区间跨零。[模型分数及联赛结果](results/m5_goal_model_recency_2026_oos.json)、[MR1 Crown/FT 回放](results/m5_goal_model_recency_2026_crown_oos.json)、[按证据优先级去重的双源回放](results/m5_goal_model_recency_2026_crown_source_union.json)。TotalCorner event-time quotes 在赛后回取，不计作赛前已收取快照；候选逐场预测仍在仓库外。
- [M5 两年近期加权稳定性审计](results/m5_recency_two_year_stability.json) → 对 2025 (n=11,967) 和 2026 (n=10,235) 两个逐联赛 UTC OOS 年份复核 baseline/recency proper scores；AH 两年改善，OU 两年恶化；每年 51 折时间边界、fixture 分割和联赛加权分数均已校验。这里是比分概率样本，不是 Crown ROI 样本。
- [M5/MR1 V6 固定投票时间留出](results/m5_crown_model_vote_holdout.json) → AH/OU 同 Crown 870 fixture-market；按 quote UTC 时间切出 265 AH / 264 OU 后段。2-of-3 投票两市场 ROI 均负；strict unanimous 子集也未改善。所有样本此前已用于其他 2026 研究，因此不是 pristine independent confirmation；候选 gate 不用于生产。
- [M5 全局进球率校准 Crown 留出](results/m5_crown_goal_rate_bias_holdout.json) → 按每市场 605 AH / 597 OU 早期唯一赛果 MLE 拟合主客 Poisson rate offset，保留 265 AH / 264 OU 后段同 Crown holdout。结算 proper score 四组都改善，但 ROI 仅 AH recency 由 -2.05% 到 -0.44%，OU recency 反而由 -7.06% 到 -13.54%；不支持盈利目标。参数不用 ROI 拟合，样本已被此前研究复用。

- 2026-11-05 follow-up added 2025 strict OOS recency scores and a 2025-fit/2026-holdout M3/M5 blend with training-end-before-as-of enforcement. The blend did not beat the best single model on either market; its 518-fixture aligned holdout has zero exact-contract Crown overlap, so it has no ROI. See the final sections of [M5_PROGRESS_REPORT_20261104.md](M5_PROGRESS_REPORT_20261104.md) and the sanitized receipts `results/m5_goal_model_recency_2025_oos.json` and `results/m5_recency_m3_walkforward_blend_2025fit_2026test.json`.
- The new MR1 Crown factor audit covers 871 verified received-before-kickoff snapshots per market. AH is -1.944891% ROI, OU -3.729621%; bootstrap intervals include zero. Post-hoc descriptive quantile groups have ties and do not create filters. See `results/m5_mr1_crown_factor_audit.json`. These results are not a deployed M5 stream and remain far below 10,000 fixtures per market.
- Added an EV calibration diagnostic with 606 early train / 3 purged / 262 later holdout fixtures per market. The recency model's larger-EV-side holdout averaged predicted EV +17.69% AH / +14.97% OU, while realized ROI was -1.59% / -7.92%. Training-defined quartiles were nonmonotonic; the lower-EV-side diagnostic returned -4.04% AH / +0.90% OU. This is exploratory on a previously studied 2026 holdout, not an independent strategy or a new bet gate. See [m5_mr1_crown_ev_calibration.py](m5_mr1_crown_ev_calibration.py) and `results/m5_mr1_crown_ev_calibration.json`.
- Added a time-ordered M5/Crown probability-anchor candidate on AH0 (90 full-sample quotes; 28 later holdout) and OU2.5 (168 full-sample quotes; 51 later holdout). Weights were chosen by early-period log loss only. Holdout same-Crown ROI was AH0 +25.11% on 28 fixtures (95% interval -5.96% to +54.82%), OU2.5 +0.73% on 51 (interval -25.57% to +27.24%). The quote period was previously explored and is not an independent untouched test; neither market meets the 10k sample goal. See [m5_crown_market_anchor_oos.py](m5_crown_market_anchor_oos.py) and `results/m5_crown_market_anchor_oos.json`.

此前 317 场 MR1 verified Crown 子集的较低价一侧对照基准来自旧归档指纹（见历史进度报告），不能与当前 871 场回放拼接。该方向只是描述性基准，不是策略门槛。

最新 source-verified Crown 配对为 871 场，覆盖 2026-09-19 至 2026-11-03 UTC；目前仍无跨年验证，不能解释为跨赛季稳定 ROI。

The additional local V26 Crown browser archive has 47 frozen AH observations; 39 pass exact fixture identity, M5 prior-season cutoff, quote-before-kickoff, and independent FT checks as retrospective hindcasts. Their M5 ROI is -23.038462% on the V26 first-locked quote (39 fixtures). All 39 overlapped the then-current V23 317-fixture AH cohort, and the V23 quote event was later on those overlaps; its same-fixture M5 replay was -24.294872%. That archived comparison predates the later 871-fixture MR1 registry refresh and is not a current deduplicated V23/V26 count. V26 adds no OU prices. These forecasts are reconstructed hindcasts rather than contemporaneously archived signals. See [follow-up audit](M5_CROWN_ARCHIVE_COVERAGE_AUDIT_20261105.md) and [V26 replay receipt](results/m5_v26_crown_oos_replay.json). Raw observations and private files remain outside the public repository.

## Chronological M5 Crown temperature holdout

`m5_crown_temperature_holdout.py` tests a bounded score-grid temperature calibration on the latest 871 source-verified, pre-kickoff-received Crown fixtures per market. For each market independently, the temperature is chosen from a preregistered nine-value grid using only the early quote-time partition's Asian settlement-category log loss; ROI does not select it. The later partition starts at the saved UTC quote-event cutoff. A training result is usable only when its verified FT receipt predates that cutoff; 40 AH and 41 OU boundary rows were purged. No identical quote timestamp crosses the split. The held-out results have 262 unique fixtures per market (606 early train, 3 purged, 262 later holdout).

| Market / model | Early train n | Purged | Later holdout n | Temperature | Holdout W/HW/P/HL/L | Net U | ROI | 95% fixture-bootstrap ROI interval | Max DD U | Settlement LL / Brier |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| AH raw grid | 606 | 3 | 262 | 1.00 | 97/18/18/23/106 | -18.105 | -6.9103% | -17.5153% to +3.6622% | 19.125 | 1.038581 / 0.660533 |
| AH temperature tuned on train LL | 606 | 3 | 262 | 1.75 | 97/19/18/22/106 | -16.870 | -6.4389% | -16.9981% to +4.1240% | 17.890 | 1.040498 / 0.657244 |
| OU raw grid | 606 | 3 | 262 | 1.00 | 95/12/13/23/119 | -36.800 | -14.0458% | -25.0592% to -3.1393% | 37.720 | 1.035632 / 0.657164 |
| OU temperature tuned on train LL | 606 | 3 | 262 | 1.25 | 94/13/13/22/120 | -38.100 | -14.5420% | -25.0095% to -3.7290% | 42.570 | 1.008165 / 0.636740 |

This is a 262-fixture later-period holdout, still far below 10,000 and not evidence of stable profitability. AH remains negative with intervals spanning zero. OU is negative with the bootstrap interval below zero; temperature improves proper scores but not ROI. The selected temperatures were chosen only on the earlier settlement log loss, never on holdout ROI. The full sanitized receipt is [`results/m5_crown_temperature_holdout.json`](results/m5_crown_temperature_holdout.json). This research adds no EV gate, filter, order limit, or production change.
- Added an exact same-Crown matched comparison for M5 baseline, M5 recency, and MR1 V6 cross-market forecasts: 870 fixtures per market, 48 leagues. All ROI estimates are negative and bootstrap intervals cross zero; the comparison reuses previously studied 2026 records, so it is not an independent untouched holdout. Aggregate-only receipt: [`m5_mr1_v6_same_crown_oos.json`](results/m5_mr1_v6_same_crown_oos.json); method and detailed results are at the end of [the progress report](M5_PROGRESS_REPORT_20261104.md).
- New OU event-time data expansion replays M5 baseline/recency on M1's saved Crown historical quote events and deduplicates against MR1 V6 receipt-verified Crown quotes. M1 contributes 1,032 valid forecast-time matches; 746 overlap MR1, yielding 1,156 unique fixtures in the mixed-evidence union, with the 286 M1-only additions labeled event-time-only. Union ROI is AH n/a; OU baseline -2.765571%, recency -2.644031%, intervals cross zero. The 2026 event-time source was fetched later and does not prove contemporaneous receipt or execution. See [`m5_m1_mr1_ou_crown_union.json`](results/m5_m1_mr1_ou_crown_union.json) and the final section of the progress report.
- New same-fixture OU quote-time diagnostic compares 732 earlier M1 Crown event-time prices with later MR1 receipt-verified Crown prices on the same M5 forecasts and FT. Baseline ROI moved -2.6291% to -2.6004%; recency -3.0765% to -3.5307%; paired intervals cross zero. The full aggregate was reproduced from current local archives with matching results. No benefit from quote timing is established. See [`m5_m1_mr1_ou_quote_timing_diagnostic.json`](results/m5_m1_mr1_ou_quote_timing_diagnostic.json) and the latest report section.

### 2026-11-06 采集运行状态（非终态）

Crown私有回填仍由单一collector运行。检查点 `2026-11-05T17:21:18.731105Z` 已处理8,800/127,674个forecast候选，8,746个精确Crown响应，AH/OU各7,871场包含至少一条合格赛前源事件报价，54条transport errors，fixture身份/时间错配0。采集进程之后仍写入索引（观察到8,875条响应收据行，最后时间 `2026-11-05T17:28:01.454130Z`），但正在写入的索引行数不等于有效quote覆盖，也不是终态。有效覆盖离10,000/市场各差2,129；回放API响应均赛后取得，仍只支持事件时间回顾模拟。

已存在串行 TotalCorner default fallback 等待器仍在等待Crown `finished_utc`，尚无 fallback progress 或TOTAL请求；启动后会逐市场优先保留Crown，缺口来源会标成 `totalcorner_default_NOT_CROWN` 并单独报告。当前阶段不代表数据源联合10k完成、正ROI目标达成、可执行收益或M5 Actions验收。最新细节见 [PROJECT_HANDOFF.md](../../PROJECT_HANDOFF.md)。

最新运行检查点（2026-11-05T17:30:55Z）：8,900/127,674候选已处理，8,846精确响应，AH/OU各7,960个有效Crown赛前源事件报价；还差2,040/市场。collector和串行等待器仍运行，Crown未终态、TOTAL未启动。详见 [PROJECT_HANDOFF.md](../../PROJECT_HANDOFF.md)。

本机共享TotalCorner离线档案检查发现已存120条只有赛程身份/赛果及线位字段，没有两侧赔率和movement时间；收集摘要标注`market_history_verified=false`，因此不加入M5盘口回放。M5继续等待Crown终态，之后将使用已有合法API接入抓取逐市场缺口。


### 2026-11-05T17:37:23Z 活动档案 partial 回放

逐市场结果和审计边界见 [partial aggregate receipt](results/m5_source_union_replay_partial_20261105T173723.321288Z.json)。本次AH/OU各8,034唯一真实赛事，Crown ROI为-1.553896%/-3.864513%，最大回撤153.520U/321.065U；所有API接收收据在开赛后，6条无效receipt时间行排除。它是活动采集中的源事件时间回顾模拟，不代表赛前实际收到的可执行ROI，未达10,000或+3%目标。源输入SHA、proper scores、五类结算及未筛选描述拆分均在receipt内。

Partial样本中的不筛选描述拆分显示OU 2.25（n=1,411）/2.75（n=1,732）贡献较大净亏损，AH 0.50（n=521）/0.00（n=1,011）亦为较大亏损组；这些分组使用同一活动样本，未用于模型或收益条件选择。durable Crown检查点已进至9,000候选、AH/OU各8,054有效报价，仍未终态。


### M3/M5 Crown 固定合约最新重跑

最新运行以2026-09-01 UTC为留出边界，AH0留出38场，训练期Log Loss选M3 Dixon-Coles（M5权重0%），ROI +30.657895%；OU2.5留出59场，选M3 Bivariate Poisson（训练拟合M5权重20%），ROI +8.118644%。未用holdout ROI选模型或权重，报告含所有候选模型、概率分数、最大回撤和bootstrap区间：[aggregate receipt](results/m5_m3_crown_2026_holdout_20261105T174731Z.json)。样本不足10,000/市场且所有API quote receipts在赛后，故是小样本回顾性比较，不满足收益目标正式验收。


### M5 Crown 2026 temporal goal-rate calibration holdout

Added a single global home/away scoring-rate tilt, fit from M5 OOS score grids and actual results before `2026-09-01 UTC`, then evaluated on later Crown-only fixture-markets. Training and holdout IDs are disjoint (5,950 train / 2,295 test per market). Calibration improved settlement Log Loss and Brier on both AH and OU but ROI remained negative (`AH -0.162092%`, `OU -3.713290%`; raw baselines `+0.244009%/-4.723965%`). Parameters were fitted by prior outcomes, never holdout ROI; no filters were added. All response receipts came after kickoff, so this is source-event-time retrospective evaluation, not execution evidence. Full score/settlement/source audit: [temporal holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T175546Z.json).


### 2026-11-05T17:58Z 活动 Crown partial 回放

全市场每market 8,273场，AH ROI -1.543515%（-127.695U），OU ROI -3.932129%（-325.305U），最大回撤164.805U/331.775U。报价全是Crown，收据全部在赛后，4条receipt时间无效记录排除；仅2026-02-10至11-04 UTC。活动采集中快照，不是终态结果、可执行ROI或达到+3%/10,000场。详情：[aggregate receipt](results/m5_source_union_replay_partial_20261105T175815Z.json).


### Crown checkpoint 9,300：最新 partial 与时间留出校准

检查点处理9,300候选，AH/OU各8,343有效Crown事件报价，collector仍活跃。活动档案全市场回放增至每市场8,346场：AH ROI -1.586509%，OU -3.937215%（所有响应receipt在开赛后，partial不可执行）。同时率校准的2026-09-01 UTC时间留出每市场6,065训练/2,295测试；AH校准ROI -0.162092%，OU -4.060566%，proper scores改善但未达收益目标。两个结果及完整审计见 [all-market replay](results/m5_source_union_replay_partial_20261105T180309Z.json) 和 [temporal holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T180523Z.json).


### Crown checkpoint 9,400 回放

活动采集checkpoint 9,400/127,674候选已处理、AH/OU各8,438场有效Crown报价，完整分市场结果见 [partial receipt](results/m5_source_union_replay_partial_20261105T181254Z.json)。AH ROI -1.671249%，OU -3.952062%，响应全赛后取得，6条无效receipt排除；采集仍运行，结果不是终态或可执行ROI。


率校准在新训练样本上的复核（6,169训练/2,295时间留出每市场）见 [最新校准回执](results/m5_crown_goal_rate_temporal_holdout_20261105T181541Z.json)：AH校准ROI -0.162092%，OU -3.968627%；proper score虽改善，但全未达到+3%，且报价receipt均在开赛后。


### 2026-11-05T18:18Z Crown checkpoint and 9,500-candidate refresh

The private Crown collector checkpoint is `2026-11-05T18:18:35Z`: 9,500/127,674 candidates processed, 9,444 exact responses, 56 transport errors, 8,532 fixture quotes valid for both AH and OU, and zero identity/time mismatches. This is still an active partial archive, not final coverage.

A replay generated `2026-11-05T18:19:34Z` on 8,542 unique fixture-markets per market (all Crown): AH `-139.660U`, ROI `-1.634980%`, maximum event-time drawdown `172.935U`, settlement Log Loss/Brier `1.03356792/0.64981503`; OU `-348.350U`, ROI `-4.078085%`, drawdown `351.850U`, Log Loss/Brier `0.98967251/0.62473892`. Descriptive fixture-bootstrap 95% ROI intervals are AH `-3.501463% to +0.213767%` and OU `-5.979045% to -2.199719%`. The samples cover 2026-02-02 through 2026-11-04 UTC and are each below 10,000. All selected API receipts arrived after kickoff; these event-time replays are retrospective and cannot be represented as executable pregame ROI. Full aggregate and hashes: [partial replay receipt](results/m5_source_union_replay_partial_20261105T181934Z.json).

A separate chronological rate calibration uses 6,266 prior fixtures and 2,295 later holdout fixtures per market, cutoff `2026-09-01T00:00:00Z`; fixture IDs are disjoint. Home/away rate multipliers are 1.035343/1.031832, fit by prior-period goal likelihood rather than ROI. Raw vs calibrated holdout ROI: AH `+0.244009%` to `-0.204793%`; OU `-4.723965%` to `-3.901961%`. Calibration modestly improves both settlement Log Loss/Brier pairs (AH `1.02778536/0.64250851` to `1.02695128/0.64222314`; OU `0.99662474/0.62898185` to `0.99000195/0.62414496`). AH and OU still do not reach the +3% objective; OU remains negative. All API receipts were post-kickoff, so even this time-split result is not execution evidence. Full audit: [temporal holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T182153Z.json).

Neither run completes the 10,000-per-market target or provides contemporaneous receipt evidence. Do not treat event-time replay ROI as verified Crown executable ROI. No filters/gates were introduced and no M5 Actions run was triggered.


### 2026-11-05T18:28Z append-only response-index replay refresh

A read-only replay against the append-only private response index (the collector's progress JSON had not yet refreshed) generated `2026-11-05T18:25:36Z`: 8,596 unique Crown fixture-markets per market. AH `-139.980U / -1.628432%`, settlement LL/Brier `1.03297664/0.64940953`, event-time max DD `172.935U`; OU `-348.570U / -4.055026%`, LL/Brier `0.98905515/0.62437528`, max DD `352.640U`. Six rows lacked a valid receipt timestamp and were excluded. All 8,596 included receipts per market are post-kickoff; this remains retrospective event-time ROI. [Replay receipt](results/m5_source_union_replay_partial_20261105T182536Z.json).

Re-fitting the fixed `2026-09-01 UTC` temporal diagnostic on this response-index snapshot gives 6,318 train / 2,295 holdout fixtures per market, disjoint IDs. Calibration factors (home 1.035241, away 1.029959) are fitted from historical goals, not ROI. AH raw/calibrated ROI `+0.244009% / -0.162092%`; OU `-4.723965% / -3.810022%`. Calibrated LL/Brier are AH `1.02699963/0.64224118`, OU `0.99013928/0.62424450`. All receipts remain post-kickoff and neither market reaches +3%. [Temporal holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T182806Z.json).


### 2026-11-05T18:37Z incremental Crown capture checkpoint

The capture progress file reached 9,700/127,674 candidates at `2026-11-05T18:33:56Z`, with 9,643 exact responses, 57 transport errors, 8,724 valid AH and OU quotes, and zero identity/time mismatches. The process remains active; this is not terminal coverage.

Append-only response replay generated `2026-11-05T18:34:56Z`, with 8,733 unique fixture-markets per side: AH `-150.015U / -1.717795%` (LL/Brier `1.03316151/0.64952653`), OU `-355.045U / -4.065556%` (`0.98873384/0.62409367`). Two invalid-receipt rows were excluded; every included API receipt was after kickoff. This remains retrospective source-event-time ROI. [Replay receipt](results/m5_source_union_replay_partial_20261105T183456Z.json).

Fixed `2026-09-01 UTC` holdout re-fit generated `2026-11-05T18:37:08Z`: 6,454 training / 2,295 holdout fixtures per market, disjoint. The fitted home/away factors are 1.034358/1.033627. Raw/calibrated ROI is AH `+0.244009% / +0.001743%`, OU `-4.723965% / -3.813508%`; calibrated LL/Brier AH `1.02690241/0.64220362`, OU `0.98997095/0.62412352`. All quote API receipts are after kickoff, so this is not executable pregame evidence. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T183708Z.json).


### 2026-11-05T18:46Z incremental Crown capture checkpoint

Formal progress reached 9,800/127,674 candidates at `2026-11-05T18:43:58Z`: 9,742 exact responses, 58 transport errors, 8,818 eligible quotes per market, and zero identity/time mismatches. Capture remained active.

A response-index replay generated `2026-11-05T18:44:47Z`, with 8,825 unique Crown fixtures per market after excluding 14 invalid receipt-time rows. AH: `-154.380U / -1.749348%`, settlement LL/Brier `1.03266377/0.64933585`, event-time max DD `185.140U`; OU: `-350.190U / -3.968159%`, LL/Brier `0.98851743/0.62391176`, max DD `368.980U`. Every included API receipt was post-kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T184447Z.json).

The fixed `2026-09-01 UTC` temporal holdout re-fit generated `2026-11-05T18:46:59Z`: 6,562 train / 2,295 holdout fixtures per market with disjoint IDs. Historical-goal rate factors were home 1.033501 / away 1.035700. Raw/calibrated ROI: AH `+0.244009% / +0.220044%`; OU `-4.723965% / -3.894118%`. Calibrated LL/Brier: AH `1.02685088/0.64218448`, OU `0.98991005/0.62408032`. All quote receipts were post-kickoff, so this remains retrospective model diagnostics, not executable ROI. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T184659Z.json).


### 2026-11-05T18:54Z incremental Crown capture checkpoint

Formal progress reached 9,900/127,674 candidates at `2026-11-05T18:51:05Z`: 9,841 exact responses, 59 transport errors, 8,914 valid quotes per market, zero identity/time mismatches; collection remained active.

The response-index replay generated `2026-11-05T18:52:23Z`: 8,919 unique Crown fixtures per market; eight invalid receipt-time rows excluded. AH `-156.440U / -1.754008%` (LL/Brier `1.03282554/0.64948192`, event-time max DD `185.140U`); OU `-337.125U / -3.779852%` (`0.98869150/0.62397048`, max DD `368.980U`). All included API receipts arrived after kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T185223Z.json).

The fixed cutoff holdout generated `2026-11-05T18:54:37Z`: 6,640 training / 2,295 disjoint holdout fixtures per market. Fitted home/away factors: 1.033429 / 1.038167. Raw/calibrated ROI AH `+0.244009% / +0.220479%`; OU `-4.723965% / -3.893246%`. Calibrated LL/Brier AH `1.02679508/0.64216577`, OU `0.98975260/0.62396647`. All API receipts were post-kickoff; this remains a retrospective diagnostic. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T185437Z.json).


### 2026-11-05T19:03Z 10,000-candidate checkpoint

Crown progress reached 10,000 candidates at `2026-11-05T18:59:55Z`, but only 9,008 fixtures had valid pre-kickoff event-time AH/OU quotes; this is not the 10,000-per-market target. The append-only replay generated `2026-11-05T19:00:47Z` has 9,015 unique fixture-markets per side (14 invalid receipts excluded). AH is `-161.845U / -1.795286%`, LL/Brier `1.03306914/0.64965941`, event-time max DD `191.810U`. OU is `-339.700U / -3.768164%`, LL/Brier `0.98875161/0.62393692`, max DD `368.980U`. All included API receipts are post-kickoff; these remain retrospective source-event-time results. [Replay receipt](results/m5_source_union_replay_partial_20261105T190047Z.json).

The temporal calibration fit re-generated at `2026-11-05T19:03:05Z` has 6,746 train / 2,295 disjoint holdout per market. Raw/calibrated ROI AH `+0.244009% / +0.220044%`, OU `-4.723965% / -3.977778%`. Calibrated LL/Brier AH `1.02683379/0.64217823`, OU `0.98990909/0.62408015`. Every API receipt is post-kickoff. Neither the sample-size requirement nor ROI criterion has been reached. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T190305Z.json).


### M3/M5 exact Crown-contract blend refresh (2026-11-05T19:05Z)

Re-ran the existing strict M3/M5 chronological comparator against the current Crown archive, using exact common fixture identity and fixed AH0 / OU2.5 contracts. Weights were selected only on earlier-period log loss, never holdout ROI. Training pairs: AH 97, OU 210; later holdout: AH 38, OU 59; no identity-key collisions.

AH holdout ROI: M5 25.394737% (+9.65U), selected M3/M5 Poisson blend 26.052632% (+9.90U), M3 bivariate/ Dixon-Coles 30.657895% (+11.65U). OU holdout: M5 -0.813559% (-0.48U); training-selected M3/M5 bivariate blend -0.627119% (-0.37U); M3 bivariate Poisson 8.118644% (+4.79U); M3 Dixon-Coles and Poisson 5.033898% (+2.97U). The M3 OU models' descriptive bootstrap intervals are broad: bivariate `-16.677966% to +31.779661%`, Dixon-Coles `-19.474576% to +29.457627%`. The selected OU blend improved proper scores over M5 (LL/Brier `0.69900917/0.50513803` vs `0.70600004/0.51143449`) but holdout ROI is negative.

This fixed-contract cohort is far below 10,000 fixtures and is not an untouched sample: current 2026 data has been examined in prior studies. Every Crown API receipt was post-kickoff (AH 38/38, OU 59/59), although quote source-event times were between joint forecast as-of and kickoff. The ROI figures are retrospective event-time simulations, not executable pregame records. This is a descriptive M3 complement diagnostic, not a selected production rule. Full aggregate audit and hashes: [M3/M5 blend receipt](results/m5_m3_crown_archive_blend_20261105T190544Z.json).


### 2026-11-05T19:11Z incremental Crown capture checkpoint

Formal progress `2026-11-05T19:08:34Z`: 10,100/127,674 candidates, 10,040 exact responses, 60 transport errors, 9,105 valid AH and OU fixtures, zero identity/time mismatches.

Response-index replay at `2026-11-05T19:09:26Z` contains 9,108 fixtures/market; six invalid receipt-time rows excluded. AH `-168.225U / -1.847003%` (LL/Brier `1.03267656/0.64932759`, max event-time DD `195.725U`); OU `-330.615U / -3.629941%` (`0.98874492/0.62384540`, DD `368.980U`). All receipts post-kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T190926Z.json).

Temporal holdout re-fit `2026-11-05T19:11:40Z`: 6,827 training / 2,295 disjoint holdout per market; historical goal-rate factors home 1.034194, away 1.036082. Raw/calibrated ROI AH `+0.244009% / +0.057952%`; OU `-4.723965% / -3.975599%`. Calibrated LL/Brier AH `1.02684339/0.64218266`, OU `0.98982137/0.62401544`. The holdout's 2,295 receipts per market are all after kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T191140Z.json).


### 2026-11-05T19:19Z incremental Crown capture checkpoint

Formal progress `2026-11-05T19:15:50Z`: 10,200/127,674 processed; 10,140 exact responses; 60 transport errors; 9,204 valid quotes per market; zero identity/time mismatches.

Replay at `2026-11-05T19:17:42Z`: 9,217 unique fixture-markets per side, two invalid receipt-time rows excluded. AH `-164.505U / -1.784800%` (LL/Brier `1.03195550/0.64889098`, max DD `195.900U`); OU `-302.910U / -3.286427%` (`0.98787868/0.62322958`, max DD `368.980U`). Every included API receipt followed kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T191742Z.json).

Temporal holdout re-fit at `2026-11-05T19:19:58Z`: 6,931 train / 2,295 disjoint holdout per market; fitted home/away factors 1.032254 / 1.037426. Raw/calibrated ROI AH `+0.244009% / +0.220479%`, OU `-4.723965% / -4.142484%`. Calibrated LL/Brier AH `1.02681065/0.64217012`, OU `0.98990848/0.62408047`. All holdout receipts post-kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T191958Z.json).


### 2026-11-05T19:29Z incremental Crown capture checkpoint

Formal progress `2026-11-05T19:26:36Z`: 10,300 candidates, 10,239 exact responses, 61 transport errors, 9,302 valid AH and OU quotes, zero identity/time mismatches.

Replay `2026-11-05T19:27:19Z` now spans 9,293 unique fixture-markets per market, including 33 from UTC kickoff year 2025 and 9,260 from 2026. Fourteen invalid receipt times were excluded. AH `-164.985U / -1.775369%` (LL/Brier `1.03171631/0.64871043`, max DD `195.900U`); OU `-315.860U / -3.398902%` (`0.98810240/0.62344654`, max DD `368.980U`). All selected receipts were obtained after kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T192719Z.json).

Temporal holdout `2026-11-05T19:29:35Z`: 7,032 training / 2,295 disjoint holdout fixtures per market; training now begins `2025-12-27 UTC`. Fitted home/away goal-rate factors 1.030806 / 1.037342. Raw/calibrated ROI AH `+0.244009% / +0.263399%`, OU `-4.723965% / -4.061874%`. Calibrated LL/Brier AH `1.02681261/0.64217023`, OU `0.99004727/0.62418241`. All receipts remain post-kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T192935Z.json).


### 2026-11-05T19:36Z incremental Crown capture checkpoint

Formal progress `2026-11-05T19:32:57Z`: 10,400 candidates, 10,339 exact responses, 61 transport errors, 9,393 valid AH and OU quotes, zero identity/time mismatches.

Event-time replay generated `2026-11-05T19:34:16Z` has 9,387 unique fixture-markets per market (127 UTC-2025, 9,260 UTC-2026); two invalid receipt-time rows were excluded. AH `-176.615U / -1.881485%` (LL/Brier `1.03144922/0.64858799`, max DD `200.910U`); OU `-313.640U / -3.341217%` (`0.98847434/0.62368418`, max DD `368.980U`). All receipts after kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T193416Z.json).

Temporal holdout generated `2026-11-05T19:36:32Z`: AH 7,103 train / 2,295 disjoint holdout; OU 7,102 / 2,295 (one additional missing timestamp on OU). Rates home/away AH 1.029703/1.036237, OU 1.029736/1.036365. Raw/calibrated ROI AH `+0.244009% / +0.218083%`, OU `-4.723965% / -4.025708%`; calibrated LL/Brier AH `1.02683692/0.64217767`, OU `0.99021321/0.62430363`. All holdout quote receipts post-kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T193632Z.json).


### 2026-11-05T19:45Z incremental Crown capture checkpoint

Formal progress `2026-11-05T19:41:57Z`: 10,500 candidates, 10,439 exact responses, 61 transport errors, 9,477 eligible quotes per market, zero identity/time mismatches.

Replay `2026-11-05T19:43:24Z`: AH n=9,470, OU n=9,469 (one OU row fewer because a quote receipt is invalid/missing); both are below 10,000. Kickoff coverage includes 210 AH and 209 OU fixtures in 2025 and 9,260 per market in 2026. AH `-171.035U / -1.806072%` (LL/Brier `1.03141609/0.64862968`, max DD `202.510U`); OU `-309.550U / -3.269089%` (`0.98881980/0.62378989`, max DD `368.980U`). Six receipt-time-invalid rows were excluded; every included API receipt was post-kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T194324Z.json).

Temporal holdout `2026-11-05T19:45:41Z`: AH 7,188 train / 2,295 disjoint holdout, OU 7,187 / 2,295; rate multipliers AH home/away 1.026980/1.034452, OU 1.027013/1.034578. Raw/calibrated ROI AH `+0.244009% / +0.117865%`, OU `-4.723965% / -3.931373%`; calibrated LL/Brier AH `1.02687843/0.64219074`, OU `0.99059610/0.62458368`. All holdout receipts post-kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T194541Z.json).


### 2026-11-05T19:58Z incremental Crown capture checkpoint

Formal progress `2026-11-05T19:54:27Z`: 10,600 candidates, 10,538 exact responses, 62 transport errors, 9,555 eligible quotes per market, zero identity/time mismatches.

Replay `2026-11-05T19:56:01Z`: AH 9,551 / OU 9,550 (one quote-receipt difference), below 10,000. UTC kickoff coverage: AH 291 in 2025 / 9,260 in 2026; OU 290 / 9,260. AH `-187.635U / -1.964559%` (LL/Brier `1.03184427/0.64888956`, max DD `213.430U`); OU `-307.235U / -3.217120%` (`0.98863673/0.62364481`, max DD `368.980U`). Fourteen invalid receipt timestamps excluded; every included response post-kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T195601Z.json).

Temporal holdout `2026-11-05T19:58:17Z`: AH 7,281 train / 2,295 disjoint holdout, OU 7,280 / 2,295. Rates AH home/away 1.025977/1.035353, OU 1.026009/1.035478. Raw/calibrated ROI AH `+0.244009% / +0.052941%`, OU `-4.723965% / -3.843355%`; calibrated LL/Brier AH `1.02686221/0.64218640`, OU `0.99062939/0.62460881`. Every holdout API receipt was post-kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T195817Z.json).
