# M5 独立融合研究

生成时间：2026-11-05 UTC。M5 是独立研究身份；本目录不连接 M1/MR1/M3 的生产预测、订单、账本或 Telegram。当前已有真实概率前推实验和 M3/M5 的 Crown AH/OU 小样本 OOS 回放，但尚未完成每市场10,000场 Crown 历史收益验证或 M5 Actions 验收。最新完整报告见 [M5_PROGRESS_REPORT_20261104.md](M5_PROGRESS_REPORT_20261104.md)，当前 M5 forecast 生成于 `2026-11-04T21:39:54Z` UTC，依赖回放于 `2026-11-04T21:41Z` UTC 重算。

当前权威快照见 [M5_PROGRESS_REPORT_20261104.md](M5_PROGRESS_REPORT_20261104.md) 末节：133,140 个 partial-scope 完赛候选、127,674 个 UTC 年×联赛 OOS 预测、584 折；forecast SHA `ebc8ae9aa4c873f3d276510533a9961c607cc607614f976a2d2e1147dbdb356a`。M3 精确共同 OOS 为 7,663 场，嵌套评估 7,252 场；MR1 verified Crown receipt-before-kickoff + 独立 FT AH/OU 各 317 场，TotalCorner endpoint historical movement AH/OU 各 212 场（response/FT 在赛后，不能算赛前收到）。所有 ROI 均是部分样本描述值；两个市场的 OOS ROI >5% 与每市场 10,000 场合法 Crown 证据目标都未达到，M5 Actions workflow 当前不存在。代码与产物：

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
