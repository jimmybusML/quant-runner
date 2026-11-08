# M5 独立融合研究

## 2026-11-08 canonical Crown 历史 summary 10k+ OOS 复跑

将统一 SQLite 中与冻结 M5 51 联赛候选清单核对过 fixture ID、球队/联赛、UTC kickoff、比分和原始响应 SHA 的 Crown 历史 summary 原件（11,582 场）连接回归档的 M5 独立 score-grid OOS 预测。每个市场只保留一条同 fixture-market 的 Crown 盘口：从 `asian.open/close` 或 `goal.open/close` 中，选择预测 as-of 后、kickoff 前、且源事件时间不晚于实际接收时间的最新报价；每项按模型两侧期望收益较高的一侧模拟 1U，不设 EV 阈值或额外筛选。该次重新采集/入库仍属 `historical`，实际响应收到时间与盘口源事件时间分开验证。

| 市场 | 唯一比赛 / 注数 | 净 U | ROI | W / HW / P / HL / L | 最大回撤 U | 结算 Log Loss / Brier | 95% bootstrap ROI |
| --- | ---: | ---: | ---: | --- | ---: | --- | --- |
| AH | 10,400 | -279.54 | -2.687885% | 4,146 / 725 / 707 / 722 / 4,100 | 307.305 | 1.030758 / 0.648482 | -4.394760% 至 -0.984279% |
| OU | 10,399 | -361.57 | -3.476969% | 4,348 / 558 / 507 / 724 / 4,262 | 381.330 | 0.982684 / 0.620602 | -5.202952% 至 -1.739783% |

2025/2026 kickoff 年 ROI 分别为 AH -7.518800% / -2.106593%、OU -5.662634% / -3.214209%；每条入选报价的原始 API 实际接收均在 kickoff 后，故仍是历史事件时间 OOS 回放，不是可执行 ROI。两市场均覆盖50个联赛，kickoff 范围 `2025-11-15T14:30Z`–`2026-11-04T17:00Z`；预测 as-of 范围 `2025-01-01T00:00Z`–`2026-01-01T00:00Z`；Crown source event 覆盖 AH `2025-11-03T17:55:42Z`–`2026-11-04T16:57:15Z`、OU `2025-11-03T17:55:43Z`–`2026-11-04T16:28:46Z`。provider response 实际接收覆盖 `2026-11-04T17:54:57Z`–`2026-11-06T04:10:50Z`，全部赛后取得。两个市场都达到本轮10,000场历史样本数量，但 ROI 均未达到+3%，bootstrap 区间上界也低于0。可复跑 runner [`m5_canonical_crown_summary_replay.py`](m5_canonical_crown_summary_replay.py)、脱敏聚合回执 [`m5_canonical_crown_summary_replay_20261108.json`](results/m5_canonical_crown_summary_replay_20261108.json)；逐场预测、报价和赛果留在本机私有目录。此处预测来自 M5 自己的 goal-rate score-grid 模型，不代表 M1/MR1/M3；跨模型结果见前述独立对照报告。

## 2026-11-08 统一 Crown 现场采集器接入 M5 前瞻样本

对 2026-11-07 生成的 M5-only forecast（313 场，SHA `ada46761fa4a86a7cf81527ebc1f8ddad128e8d519a52a04fe990ad10a04c20a`），从共享 Crown 采集器中只选择当时尚未开赛的 162 场，使用已确认的 `crown_capture_store.py`、`live/summary` 保存真实响应。采集响应时间为 `2026-11-08T13:04:49Z` 至 `13:19:40Z`，162 条均有赛前接收标记；再以原始响应 SHA、TotalCorner fixture ID、球队/联赛及精确 UTC kickoff 对照预测身份。85 场身份与开赛时间验证通过；75 场响应无 Crown bookmaker，2 场身份或 UTC kickoff 不符而拒绝。对验证通过的响应，AH 有83、OU有82个盘口事件满足 `prediction_asof <= quote_source_time <= response_received < kickoff`。OU 从同一 Crown 原始响应 `goal.open/close` 单独解析；共享采集库的 AH 规范表不被误当作 OU 表。

与同一冻结预测批次原先实收、且赛前有效的 TotalCorner default 报价合并后，按 fixture-market 去重并遵守 Crown 优先：AH 102项（Crown 83、TotalCorner 19），OU 98项（Crown 82、TotalCorner 16），共105场。无 EV/置信度、联赛、时间或投注数量门槛；每项按原 M5 规则模拟1U。结果核验至 `2026-11-08T15:07:51Z` 时，AH 18/102、OU 16/98已结，另有166项待结；已结的34项均来自旧 TotalCorner fallback，新的 Crown live 项仍待赛果。AH 已结净额 +3.5U、已结本金 ROI +19.4444%；OU -1.6375U、-10.234375%。两市场完整 cohort ROI 均为 null，不能把 AH 小样本已结 ROI 当成目标达成；此批远低于每市场10,000场。脱敏聚合回执：[canonical Crown live capture 与结算](results/m5_canonical_crown_live_capture_20261108.json)。逐场身份、score grid、盘口/水位和 raw 响应留在本机权限受限目录。适配器 [`m5_canonical_crown_capture_index.py`](m5_canonical_crown_capture_index.py) 只读取共享 SQLite 的 live response/hash 并验证两市场报价时序，不发请求；网络采集由确认的统一本地程序完成。本次没有修改任何正式模型、生产规则、TG、订单或账本。

## 2026-11-07 M5 基线按 UTC 季度与盘口来源诊断

对 Crown-first、TotalCorner-default 补缺的 11,537 场 all-prior-OOS 留出逐场重新按原规则选边和结算，完整样本按 UTC kickoff 季度及实际报价来源拆分：[聚合诊断和输入哈希](results/m5_quarterly_source_diagnostic_20261107.json)。所有市场项均保留，未把季度/来源子组转成投注筛选规则。

| 市场 | 2025 Q4 | 2026 Q1 | 2026 Q2 | 2026 Q3 | 2026 Q4 | 全样本 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AH ROI (n) | -7.50% (1,311) | -1.96% (2,899) | -2.55% (3,069) | -1.36% (2,820) | -1.17% (1,438) | -2.50% (11,537) |
| OU ROI (n) | -4.87% (1,311) | -2.04% (2,899) | -4.04% (3,069) | -3.44% (2,820) | -5.40% (1,438) | -3.65% (11,537) |

| 市场 | Crown 全样本 | TotalCorner-default 全样本 | 2026 Q3 Crown | 2026 Q3 TotalCorner-default |
| --- | ---: | ---: | ---: | ---: |
| AH | -2.37% (10,433) | -3.79% (1,104) | -1.67% (2,572) | +1.89% (248) |
| OU | -3.65% (10,432) | -3.73% (1,105) | -3.99% (2,572) | +2.24% (248) |

2026 Q3 的 TotalCorner 小子组是可供后续做价格/覆盖质量审计的线索，不构成有效策略成绩：样本每市场仅248项，单季且经过多次探索；其余季度并未复现同一正向点估计。历史报价回执全在开赛后，任何分组收益仍属回顾性 event-time 模拟。全样本 AH/OU 均未达到+3%。

为核查 Q3 的正向点估计是否只是联赛组合差异，新增了“同季度且两种来源都覆盖的联赛”描述比较。2026 Q3 有29个联赛两侧来源均出现；这些共同联赛里的 TOTAL AH 206场/+17.2125U/+8.36%，OU 206场/+6.725U/+3.26%，同联赛支持范围内 Crown 分别1,468场/-49.745U/-3.39%、1,468场/-40.405U/-2.75%。但这不是同场配对：两源覆盖的是不同比赛和不同盘口时点。TOTAL 正收益也高度集中，AH最高单联赛贡献7.1875U，OU最高单联赛贡献5.8375U；29个共同联赛中正收益联赛分别18个和19个，样本量跨度大且多重探索明显。此结果只能触发更细的盘口/数据质量审计，不能支持只取这些联赛或切换来源的交易规则。

新增的[同场 Crown/TOTAL 历史报价重叠审计](results/m5_cross_source_quote_overlap_audit_20261107.json)进一步确认：2026 Q3 AH、OU均无一场在 M5 as-of 后同时有 Crown 和 TOTAL 的有效市场报价；全历史索引的原始有效行交集分别仅 AH 15、OU 14，严格按 M5 as-of 与开赛时间复核后仅 AH 1 场、OU 0 场可配对。唯一 AH 配对同盘口线，但两侧最大价格差0.07，盘口事件时间相差5,284秒；没有同时点的同场双源样本。所有响应仍在开赛后回取。当前无法从这批历史归档分辨 TOTAL 子组收益来自同场价格差还是不同fixture可用性，不能把不同源子组的ROI差异解释为provider价格优势。

## 2026-11-07 M1 / MR1 / M3 / M4 已有大样本对照复核

针对每市场一万多场的数据，汇总现存且可追溯的同一扩展 source-union 研究回放：[完整聚合对照与输入报告哈希](results/m5_m1_mr1_m3_m4_expanded_cohort_comparison_20261107.json)。AH、OU独立核算，每市场扩展集10,568个唯一fixture-market；AH来源为Crown 9,613 / TotalCorner-default 955，OU为Crown 9,612 / TotalCorner-default 956。每个模型选择按1U结算，来源未混淆。

| 市场 | 方案 | 样本 | 净U | ROI |
| --- | --- | ---: | ---: | ---: |
| AH | M1 | 10,568 | -252.745 | -2.3916% |
| AH | MR1 V6 + M3 Bivariate Poisson（9,517场MR1、1,051场M3回退） | 10,568 | -312.5075 | -2.9571% |
| AH | M3 Poisson / Dixon-Coles / Bivariate Poisson | 各10,568 | -320.2475 / -330.5775 / -317.1625 | -3.0304% / -3.1281% / -3.0012% |
| AH | M4现有Pass规则（Poisson / Dixon-Coles / Bivariate输入） | 各10,046 | -337.4825 / -342.9125 / -328.5075 | -3.3594% / -3.4134% / -3.2700% |
| OU | M1 | 10,568 | -333.615 | -3.1568% |
| OU | MR1 V6 + M3 Bivariate Poisson（9,517场MR1、1,051场M3回退） | 10,568 | -225.6725 | -2.1354% |
| OU | M3 Poisson / Dixon-Coles / Bivariate Poisson | 各10,568 | -389.3925 / -382.4025 / -379.8825 | -3.6846% / -3.6185% / -3.5946% |
| OU | M4现有Pass规则（Poisson / Dixon-Coles / Bivariate输入） | 各10,046 | -356.3175 / -346.3875 / -362.0475 | -3.5469% / -3.4480% / -3.6039% |

这纠正了此前把M4的“M3全量基线”误称为M4 Pass结果的汇总问题。M4原有Pass覆盖10,046场；MR1 V6单体严格共同Crown样本为9,517场，ROI为AH -1.5155%、OU -3.7818%；不能把这组较小样本与source-union全量直接当作同样本排名。MR1缺少的1,051场只在明确标记的MR1/M3组合中以M3回退，未复制或伪造MR1预测。历史盘口API回执均赛后取得，所有ROI是回顾性event-time回测，非同期可执行收益；本组任何市场均未达到+3%。

2026-11-07 UTC 对 M1、MR1 V6、M3 Poisson、Dixon–Coles、Bivariate Poisson 又以同一 Crown 合约/赛果交集独立复跑，AH、OU 各 9,517 场，复核回执为[脱敏逐模型重跑报告](results/m5_m1_mr1_m3_same_crown_rerun_20261107.json)。AH ROI 依次为 M1 -2.2044%、MR1 -1.5155%、Poisson -2.9111%、Dixon–Coles -2.9511%、Bivariate -2.8784%；OU 为 M1 -3.1860%、MR1 -3.7818%、Poisson -3.7284%、Dixon–Coles -3.6449%、Bivariate -3.5754%。概率评分方面两市场 MR1 的 settlement Log Loss/Brier 最低，但全部 ROI 为负。逐场输入和报价来源均以 SHA-256 留证，公开回执不含比赛身份；历史 API 回执仍全部在开赛后。

## 2026-11-07 all-prior-OOS calibration: 11,537 场市场级留出

使用 Crown-first、TotalCorner-default 补缺的真实历史档案，对 AH 和 OU 分开训练及评估。截止时间为 `2025-01-01T00:00:00Z`：每市场 105,472 个更早的 M5 OOS 预测/赛果用于拟合概率校准，不使用训练报价；训练 fixture IDs 与测试集互斥。随后在 11,537 个唯一 fixture-market 上比较原始预测、全局校准、score-grid log-loss 校准及联赛收缩校准。训练范围为 2014-01 至 2024-12 UTC，留出开赛范围为 2025-11-15 至 2026-11-04 UTC。

| 市场 / 预测方案 | 留出样本 | ROI | Log Loss / Brier | 最大回撤 (U) | 95% fixture bootstrap ROI |
| --- | ---: | ---: | ---: | ---: | ---: |
| AH 原始 | 11,537 | -2.5031% | 1.03599 / 0.65112 | 315.11 | -4.085% 至 -0.897% |
| AH 全局校准 | 11,537 | **-2.3713%** | 1.03595 / 0.65117 | 293.55 | -4.007% 至 -0.734% |
| AH score-grid 校准 | 11,537 | -2.3713% | 1.03595 / 0.65117 | 293.55 | -3.982% 至 -0.765% |
| AH 联赛收缩校准 | 11,537 | -2.4395% | 1.03688 / 0.65176 | 318.37 | -4.005% 至 -0.810% |
| OU 原始 | 11,537 | -3.6545% | 0.98901 / 0.62413 | 439.11 | -5.281% 至 -2.055% |
| OU 全局校准 | 11,537 | -3.9434% | 0.98804 / 0.62339 | 476.18 | -5.571% 至 -2.330% |
| OU score-grid 校准 | 11,537 | **-3.9273%** | 0.98804 / 0.62339 | 474.32 | -5.536% 至 -2.305% |
| OU 联赛收缩校准 | 11,537 | -4.0564% | 0.98895 / 0.62406 | 486.84 | -5.678% 至 -2.424% |

每行每个唯一 fixture-market 模拟 1U，无筛场、EV 门槛或回测期内调参。全局校准改善 AH 点 ROI，但仍亏损；OU 校准改善 Log Loss/Brier，却没有改善收益。所有 ROI 区间均低于零，任一市场均未达 +3%。留出市场报价来源：AH Crown 10,433、TotalCorner 1,104；OU Crown 10,432、TotalCorner 1,105。盘口事件在预测之后、开赛之前，但所选历史 API receipts 全部在开赛后，因此本结果是回顾性 event-time OOS，不是同期可执行或实际成交 ROI。公开报告只保留聚合指标和哈希：[脱敏回执](results/m5_all_prior_oos_calibration_2025plus_holdout_20261107.json)；逐场数据仍在私有档案。

## 2026-11-07 市场残差参数按 ROI 拟合的时间留出诊断

为检验“训练期收益目标直接选市场残差参数”能否改善 AH 或 OU，分别在 2025 训练样本上对 score-grid 的连续残差倾斜参数 beta 做固定 121 点网格搜索（-3 到 +3），以训练期 1U ROI 选参数；2026 所有 eligible fixture-market 均保留，一场一项，不加 EV 门槛、联赛/时间过滤或数量限制。两年 fixture IDs 不相交。2025 训练各市场 1,311 项；2026 留出各 10,226 项，来源均为 Crown 优先、TotalCorner default 补缺。

| 市场 | beta | 2025 训练 ROI | 2026 beta=0 ROI | 2026 ROI 拟合 beta ROI | 留出净 U / 最大回撤 U | 留出 Log Loss / Brier | 95% fixture bootstrap ROI | 留出来源 Crown / TOTAL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| AH | 0.45 | +0.7921% | -1.8618% | **-4.9097%** | -502.07 / 514.45 | 0.998756 / 0.625154 | -6.584% 至 -3.120% | 9,316 / 910 |
| OU | 0.35 | -2.0370% | -3.4988% | **-4.0521%** | -414.37 / 429.38 | 0.966306 / 0.606989 | -5.819% 至 -2.302% | 9,316 / 910 |

按训练 ROI 选择 beta 未能泛化，两市场 2026 留出都比 beta=0 基线更差。作为对照，按 exact-score Log Loss 选出的 beta 为 AH 0.3324、OU 0.3264，留出 ROI 分别 -2.2812% 和 -4.3549%；proper-score 优化与收益优化仍不一致。2026 已在既有 M5 研究中多次检查，因此本诊断是时间隔离但非未触碰的确认性留出。历史报价事件在 kickoff 前，但 provider API receipts 在 kickoff 后，收益属于回顾性 event-time OOS，非同期执行 ROI。详细分数、结算类别、来源、bootstrap 与输入哈希见[聚合回执](results/m5_market_residual_roi_fit_2025_train_2026_holdout_20261107.json)；可复现实现见[`m5_market_residual_roi_fit_diagnostic.py`](m5_market_residual_roi_fit_diagnostic.py)。不改生产模型或交易规则。

## 2026-11-07T08:14Z M5 前瞻批次报价刷新与结算检查

对同一冻结 M5 forecast（317 个 fixture，generated UTC `2026-11-07T05:49:28.660813Z`）刷新 Crown 捕获，再用 TotalCorner default 仅补缺，并以最新来源索引重新配对。Crown 刷新 UTC `08:10:51Z`：313 次尝试、301 条身份核验响应，AH/OU 合格报价分别49/39；5条赛事/Crown身份错配拒绝，4条身份/API失败，3条传输错误。TotalCorner 回退器 UTC `08:13:53Z` 发现311场已捕获、2场因两市场均有 Crown 而跳过，没有重复请求。

| 市场 | 唯一配对数 | Crown | TotalCorner default | 已结算 | 待结算 | 净 U / ROI |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| AH | 76 | 52 | 24 | 0 | 76 | 0 / null |
| OU | 69 | 39 | 30 | 0 | 69 | 0 / null |

去重后合计145个 fixture-market、87个 fixture；相较前一快照新增 AH22、OU22。每个市场项只保留一个符合 Crown 优先规则的报价。所选报价均在预测 as-of 之后、实际接收时间早于 UTC 开赛，配对器验证 `train_end < prediction_asof <= quote_event <= quote_received < kickoff`。结算核验 UTC `08:14:29Z`：0/145已结，85场未开赛、2场已开赛未完；因此完整队列 ROI 为 null，不能把暂时净0U看作盈亏平衡。脱敏回执见[刷新回执](results/m5_forward_shadow_capture_20261107T0549Z_refresh.json)。逐场身份、概率、盘口和价格继续保留在本机私有档案。

## 2026-11-07T05:49Z M5 前瞻 Crown / TOTAL 配对与结算检查

使用同一份 M5 forecast batch（317 个未来 fixture，generated UTC `2026-11-07T05:49:28.660813Z`），先采 Crown，再仅对 Crown 未覆盖市场回退采 TotalCorner default。Crown 315 次请求中 282 条身份核验成功、6 条赛事/Crown 身份错配拒绝、27 条身份/API 失败；有效合约 AH 12、OU 10。TOTAL 313 次请求中 305 条验证成功、8 条身份错配拒绝；有效补盘 AH 42、OU 37，另有 10 项 AH、8 项 OU 因 Crown 已覆盖而跳过，2 场两个市场都由 Crown 覆盖并跳过 TOTAL。

| 市场 | 唯一配对数 | Crown | TotalCorner default | 已结算 | 待结算 | 净 U / ROI | 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| AH | 54 | 12 | 42 | 0 | 54 | 0 / null | null |
| OU | 47 | 10 | 37 | 0 | 47 | 0 / null | null |

以上两市场合计101个唯一 fixture-market、65场唯一 fixture。全部配对通过 `train_end < prediction_asof <= quote_event <= quote_received < kickoff`；结算核验查询时有64场尚未开赛、1场开赛但未完场，因此全队列净收益暂为0U、ROI保持 null、没有任何已结算样本。这里的0U仅表示尚无结算，不代表盈亏平衡。完整脱敏采集、配对、pending/来源计数和输入哈希见[前瞻回执](results/m5_forward_shadow_capture_20261107T0549Z.json)。逐场身份、盘口线、赔率、预测概率和结果响应仅保存在本机私有归档。

TotalCorner default 前瞻回退器仅对至少一个市场没有合格 Crown 报价的比赛发请求；AH 与 OU 都已有 Crown 报价时直接跳过，减少不必要的接口调用。存在单侧缺口时仍按 fixture-market 保留 Crown 优先、TOTAL 只补缺市场的原规则。测试覆盖两市场均覆盖及任一缺盘四种情形。

## M3 三模型在扩展归档上的独立评分

将公开的 M3 严格赛季前推预测（Poisson、Dixon–Coles、Bivariate Poisson）逐条按联赛、UTC比赛日期及主客队与 M5 候选归档核对。候选清单有 127,674 场；在 M3 支持且预测完整的范围内找到 7,689 场三模型共同预测，26 场比分与候选归档不一致而排除，最终 7,663 场用于三模型同样本 proper-score 比较。该数值不是全量 M5 Crown/TOTAL 盘口样本；剩余比赛没有可验证的 M3 赛前概率，不能把它们当作模型预测评分。

| M3 模型 | AH 1X2 proxy Log Loss / Brier | OU 2.5 Log Loss / Brier |
|---|---:|---:|
| Poisson | 1.01027396 / 0.60390806 | **0.69321624 / 0.24972808** |
| Dixon–Coles | **1.01000095 / 0.60367120** | 0.69322096 / 0.24972945 |
| Bivariate Poisson | 1.01021695 / 0.60372820 | 0.69326355 / 0.24976546 |

AH 的 M3 概率仅能作为三项赛果 proxy，不是亚洲让球合约收益；OU 为 O2.5 概率评分。共同样本无 Crown 价格，因此此比较没有 ROI。历史 Crown 精确线 replay 只有 AH0 5 场、OU2.5 2 场，三个模型的回测数不足以支持收益判断。报告位置：[扩展跨模型回执](results/m5_expanded_cross_model_comparison_20261106.json)；M5 当前覆盖更广的数据源并集回放仍按各自模型/市场结果见下文。

## M1 / MR1 / M3 同步证据覆盖对照

| 模型信息 | AH 覆盖 / ROI | OU 覆盖 / ROI | 可解释范围 |
|---|---:|---:|---|
| M1 历史保存的所有扫描输出 | 1,233 / -6.14% | 1,233 / -3.27% | 逐场最新保存输出；仅覆盖全量源并集的一部分 |
| M1 原有正式候选子集 | 42 / -12.29% | 79 / +5.50% | 原有候选标记；OU 正收益仅79场，不是10k收益证据 |
| M5 baseline 与 MR1_V6 同 Crown/赛果交集 | 870 / -1.73% vs -3.67% | 870 / -3.18% vs -4.74% | 直接同场比较；MR1_V6 本交集两市场均差于M5 baseline |
| M3 三模型严格样本外共同评分 | 7,663 / 仅1X2概率评分 | 7,663 / 仅O2.5概率评分 | 三模型无全线Crown价格/合约配对 |
| M4 独立冻结模型 | 无 | 无 | 当前没有独立M4预测文件；报告中的M4是MR1研究变体 |

MR1 同 Crown 交集覆盖全量源并集的 7.518%；各模型按相同盘口、价格和赛果独立模拟一注，bootstrap 区间均包含零。历史赔率响应均为赛后回取，按赛前盘口事件时间回放，不构成同期实收 ROI。完整模型定义、样本量、结算数、回撤及区间以[扩展跨模型回执](results/m5_expanded_cross_model_comparison_20261106.json)为准。

## MR1 与 M3 概率融合：2025训练、2026留出

用严格共同的 Crown 合约样本（全期 AH/OU 各9,517项）把 M3 各自比分网格转换为合约五分类概率，再与 MR1 V6 已选边五分类分布按同一市场线和双方价格融合；AH、OU 分开训练。2025各市场各1,005项用于拟合，2026各8,512项冻结留出，赛事ID两段不相交。比较固定50% MR1等权融合，以及只按2025结算类别Log Loss在MR1权重0–1、步长0.01网格择权重的方案。没有增加 EV 门槛或比赛筛选。

| 市场/方案 | MR1权重 | 2026场数 | ROI | Settlement Log Loss / Brier |
|---|---:|---:|---:|---:|
| AH：MR1 V6 | 1.00 | 8,512 | **-1.1201%** | **0.98819 / 0.61784** |
| AH：M3单模型 | 0.00 | 8,512 | -2.1516% 至 -2.2787% | 1.03194–1.03386 / 0.64652–0.64746 |
| AH：M3/MR1等权 | 0.50 | 8,512 | -2.2766% 至 -2.3323% | 0.99773–0.99780 / 0.62518–0.62523 |
| AH：2025 Log Loss择权重 | **1.00** | 8,512 | -1.1201% | 与MR1相同（训练择权重退回纯MR1） |
| OU：MR1 V6 | 1.00 | 8,512 | -4.0273% | 0.97433 / 0.61393 |
| OU：M3单模型 | 0.00 | 8,512 | -3.2839% 至 -3.4732% | 0.98678–0.98685 / 0.62279–0.62291 |
| OU：M3/MR1等权 | 0.50 | 8,512 | **-2.2113% 至 -2.2844%** | 0.97446–0.97450 / 0.61398–0.61401 |
| OU：2025 Log Loss择权重 | **0.84** | 8,512 | -2.9788% 至 -3.0104% | **0.97315–0.97317 / 0.61299–0.61301** |

OU等权混合在本次固定候选中减少了相对亏损，但ROI仍为负、95% bootstrap区间仍全负；它的 proper score略差于 MR1 单模。OU按2025 proper score择出的0.84权重改善了测试Log Loss/Brier，却没有获得等权方案的ROI。AH融合没有胜过MR1。由此可见概率校准改善和收益改善并不等价；两市场均未达到+3%。共同MR1/M3队列总量9,517，也低于每市场10,000；这与M5独立模型已有更大样本的评估是不同的比较口径。全部Crown历史接口回执在开赛后取得；事件时间赛前，只能作回顾性 event-time OOS。2026也已在此前研究中查看，不是未触碰最终确认集。

脱敏分市场报告、输入SHA、权重、结算类别、最大回撤与fixture bootstrap见[MR1/M3 时间留出融合回执](results/m5_mr1_m3_2025fit_2026holdout_blend_20261106.json)；运行器为[`m5_mr1_m3_temporal_probability_blend.py`](m5_mr1_m3_temporal_probability_blend.py)。

2026-11-06T13:54Z 对本机当前 M1 replay archive 重跑审计，读取203份扫描manifest。每市场有10,758条通过赛前时间及盘口/结果配对的模型输出记录，但按赛事去重后只有AH 1,233、OU 1,233场；不能把重复扫描记录数当作不同比赛数，也不能据此说M1已在全量万场数据上重训。完整脱敏回执[M1归档复核](results/m5_m1_expanded_archive_reaudit_20261106.json)还记录了无匹配赛事、无可用方向、正式候选子集及输入哈希。M1 Crown报价实际接收时刻未独立保存，复核沿用扫描归档完成时间作为接收上界；因此它仍是有限历史存档评估。

## Crown 与 TotalCorner 来源拆分

使用来源单独回放以及 Crown-first 去重并集，分别检查 baseline 与 recency 模型。Crown-only 达到每市场 10,000 场门槛；TOTAL-only 目前只有约1,100场；组合并集每市场超过11,500场。所有来源的历史回执时间都在开赛后，所以这些数据只能作为盘口事件时间回顾性样本外回放。

| 盘口来源 / 模型 | AH 场数 / ROI | OU 场数 / ROI |
|---|---:|---:|
| Crown-only baseline | 10,433 / -2.37% | 10,432 / -3.65% |
| Crown-only recency | 10,433 / -2.68% | 10,432 / -3.39% |
| TotalCorner-only baseline | 1,141 / -3.91% | 1,141 / -3.52% |
| TotalCorner-only recency | 1,105 / -5.54% | 1,105 / -3.95% |
| Crown-first + TOTAL缺项回退 baseline | 11,573 / -2.51% | 11,573 / -3.63% |
| Crown-first + TOTAL缺项回退 recency | 11,537 / -2.95% | 11,537 / -3.44% |

Crown-only 的 10k+ 样本没有任一市场达到 +3%；TotalCorner-only 尚未达到每市场10k且目前亏损。来源和 recency 变化均没有反转结论。完整结算类别、净U、最大回撤、bootstrap、UTC开赛年份覆盖、来源哈希和时间限制见[来源分离回执](results/m5_source_separated_performance_comparison_20261106.json)；可用 [`m5_source_performance_comparison.py`](m5_source_performance_comparison.py) 从六份冻结聚合回执重新生成，输出不含逐场身份、比分、盘口价格或原始响应。

### 盘口事件时间领先开赛分层

对 Crown-only、TotalCorner-only 和 Crown-first 去重并集重跑后，baseline 的 OU 盘口事件时间领先开赛 6–24 小时组在 Crown-only 全期汇总为 248 场、净 +8.185U、ROI +3.30%；但其中 2025 仅32场/+9.27%，2026有216场/+2.42%。把同一 Crown-only 报价与结果换成 recency 预测后，该组仍是248场，但ROI变为 -3.75%（2025 32场/-9.31%，2026 216场/-2.92%）。Crown-first并集的2026 baseline同分层为319场、净+0.5325U、ROI+0.17%；其中TotalCorner 2026子组103场、净-4.6875U、ROI-4.55%。因此3.30%的正结果既未达到万场，也不跨模型保持，且2026未达+3%，只是研究发现，不是已验证策略或新增时间门槛。

AH Crown-only 6–24小时组的2025为17场/-15.68%，2026为108场/-2.53%。来源、盘口时间和开赛年份交叉汇总见[Crown](results/m5_crown_quote_lead_year_20261106.json)、[TotalCorner](results/m5_totalcorner_quote_lead_year_20261106.json)、[Crown-first并集](results/m5_crown_first_quote_lead_year_20261106.json)。所有入选历史API实际回执均晚于开赛，领先时间来自盘口事件时间，仅可回顾研究。
AH Crown-only baseline 6–24小时组的2025为17场/-15.68%，2026为108场/-2.53%。各来源 baseline 的事件时间/年份交叉汇总见[Crown](results/m5_crown_quote_lead_year_20261106.json)、[TotalCorner](results/m5_totalcorner_quote_lead_year_20261106.json)、[Crown-first并集](results/m5_crown_first_quote_lead_year_20261106.json)；Crown recency 复跑见[recency Crown报告](results/m5_crown_recency_quote_lead_year_20261106.json)。所有入选历史API实际回执均晚于开赛，领先时间来自盘口事件时间，仅可回顾研究。

当前最接近改善的 walk-forward 方向诊断，是按 2025 各联赛训练样本 ROI 在 higher-EV / favorite / underdog 中选方向，冻结后跑 2026 全部场次；每市场 10,161 场，AH ROI `-1.373019%`、OU `-3.019732%`，分别较同一2026 higher-EV基准 `-1.855920%`、`-3.418906%` 改善约0.48/0.40个百分点，但仍然亏损。AH 2026 有21/51联赛为正、OU有15/51为正；按训练选择的三种策略类别分别汇总后，AH favorite/underdog/higher-EV均为负（n=2,721/957/6,483，ROI -1.24%/-0.68%/-1.53%），OU也均为负（n=2,353/920/6,888，ROI -2.75%/-4.23%/-2.95%）。代码现为每个测试市场输出这些策略组的场数、净U、ROI、正负联赛数及完全匹配的higher-EV基准结果。

该方向选择对2025每联赛样本有最低20场要求，并因多个方向择优而有明显选择偏差；它不筛除任何2026比赛，只作研究诊断。其2026来源事件时回放ROI没有达成+3%，历史响应回执赛后取得，且该聚合报告没有逐场顺序，不能据此报告最大回撤。[walk-forward 回执](results/m5_league_direction_2025_train_2026_oos_20261106.json)。

## 前瞻赛果结算器

`m5_forward_shadow_settlement.py` 读取不可变的私有赛前预测/报价配对，只在开赛后向 TotalCorner 核验 FT 身份、精确 UTC 开球时间及比分，原始响应与逐场结算留在仓库外；公开摘要只写汇总、输入哈希和计数。AH、OU 独立各按每个配对 1U 模拟，ROI 在整组投注结算前保持 null，并另列已结算本金上的暂计 ROI。工具不产生正式订单或 Telegram 消息。单元测试覆盖身份/时间校验、盘口结算和未开赛样本；实际前瞻批次尚未产生可结算赛果。

### 2026-11-07T09:43Z M5 前瞻报价采集与结算

从缓存赛程生成313场M5-only预测，训练截止/预测as-of/UTC开赛顺序通过；按Crown优先采集后，本批Crown查询305场身份验证通过、6场赛事身份错配拒绝、2次传输错误，合格AH/OU均为0。对相同冻结批次执行TotalCorner default回退，305场响应验证通过、6场身份错配、2次传输错误，获得AH21和OU18个有实际赛前接收证据的报价。逐场配对满足 `train_end < prediction_asof <= quote_event <= quote_received < kickoff`，AH/OU来源分别全为 `TotalCorner_default`，无重复fixture-market。配对后核验赛果：AH 18/21已结、净+3.5U、全赢/半赢/走水/半输/全输=`9/3/0/0/6`；OU 16/18已结、净-1.6375U、=`6/2/0/0/8`。AH尚3项、OU尚2项pending，因此完整队列ROI均保持null；只列已结本金比例时AH +19.4444%、OU -10.2344%，这些34项结算不能满足每市场10,000场目标或证明3%完整队列收益。脱敏采集/配对/结算汇总见[前瞻批次回执](results/m5_forward_shadow_capture_20261107T0942Z.json)，身份、比分、盘口价格、逐场预测和原始响应均未公开。

采集实现审计说明：本批Crown请求由既有M5专用runner执行，未经过2026-11-08确认的统一本地 `crown_capture_store.py` 缓存入口；本批无合格Crown报价，也未将其作为Crown配对使用。后续Crown现场采集按本机已确认的统一缓存方法执行，保留源报价时间与本机实际接收UTC时间；不改变M5策略或交易规则。

## 2026-11-06 05:02Z 扩展 Crown / TotalCorner 历史盘口后重放

在既有 127,674 场严格 UTC M5 OOS forecast / FT 冻结样本上扩展 Crown 历史候选：新增 500 个请求尝试，497 条响应通过身份核验、3 条传输失败；累计 Crown source-event 合格 AH 10,447、OU 10,446。随后对 Crown 缺市场作 51 次 TotalCorner default 回退，51 条身份核验通过。抓取索引中的 TOTAL 合格计数是在采集时预测版本上生成；本次总回放对原始 TOTAL 响应按当前冻结 forecast 的逐场 as-of 时间戳重新校验，并应用 Crown 优先，最终补入 AH 1,140、OU 1,141 个 fixture-market。两种来源严格分开，按每场/市场去重。

| 模型/方向 | AH 全 OOS 场数 / ROI | AH 2026 留出 ROI | OU 全 OOS 场数 / ROI | OU 2026 留出 ROI |
|---|---:|---:|---:|---:|
| M5 baseline，高模型 EV 方向 | 11,573 / -2.51% | -1.86% (10,226) | 11,573 / -3.63% | -3.50% (10,226) |
| M5 recency 加权，高 EV 方向 | 11,537 / -2.95% | -2.79% (10,226) | 11,537 / -3.44% | -3.38% (10,226) |
| 固定盘口热门方向 | 11,573 / -4.22% | -4.43% | 11,573 / -3.18% | **-3.33% (OU 2026 方向比较最好)** |
| 固定盘口冷门方向 | 11,573 / -2.07% | **-1.79% (AH 2026 方向比较最好)** | 11,573 / -4.29% | -4.08% |
| 2025 ROI 训练逐联赛择方向、冻结到 2026 | — | -3.48% | — | -4.04% |

固定方向均为研究诊断，不做联赛或比赛筛选；逐联赛候选每个市场在 2025 的训练段分别有 1,311 场，2026 留出均为 10,226 场，逐场仍一注。新增盘口后，先前逐联赛方案的 AH ROI 从旧报告的 -1.37% 变为 -3.48%，显示方向选择结果对样本覆盖敏感，不能认为该方案稳定优于 baseline。当前扩展数据下，2026 的固定冷门 AH -1.79% 仅比 higher-EV AH -1.86% 高约 0.08 个百分点；OU 固定热门 -3.33% 比 higher-EV -3.50% 高约 0.17 个百分点，均不能证明统计优势。完整样本中，AH ROI 最好的固定方向仍为冷门（-2.07%），OU 为热门（-3.18%）；两者都亏损，且所有候选市场都未达 +3%。

Baseline 结算记录：AH 净 -290.4675U、最大回撤 315.1075U；OU 净 -420.5525U、最大回撤 439.1050U。所有回放盘口 API 实际回执都发生在开赛后；赔率行的事件时间在赛前只支持回顾性 event-time OOS 回放，不能称为同期接收或可执行 ROI。校准分数、结算数、bootstrap 区间、UTC 覆盖、各年结果与来源数见 [扩展 baseline 回执](results/m5_source_union_expanded_oos_20261106.json)、[recency 回执](results/m5_source_union_recency_expanded_oos_20261106.json) 和[同样本方向比较](results/m5_source_union_expanded_side_policy_comparison_20261106.json)；采集量与哈希见[历史扩样回执](results/m5_historical_crown_totalcorner_expansion_20261106.json)。

本轮只给历史采集器加每次运行的 `--max-requests` 断点批次上限，默认采集口径不变。原始比赛身份、预测、价格和接口响应仍在私有目录；没有新增交易 Gate、改动生产模型或启用 Telegram。

## 2026-11-06 03:21Z 前瞻 Crown-first / TotalCorner default 采集

在既有 02:18Z 的 361 场 M5 独立预测批次上，先检查 Crown：本批次没有符合预测后、赛前实际接收约束的 Crown AH/OU 报价；因此按既定来源优先级采集 TotalCorner default 回退报价。15 场沿用小批试采，其余 346 场请求中 344 场通过 fixture/API 身份校验，2 场错配拒绝，0 场传输失败。最终仅配对 AH 13 场、OU 11 场，时间顺序满足 `train_end < prediction_asof <= quote_event <= actual_receipt < kickoff`。来源标记为 TotalCorner default，绝不计作 Crown 价格。

这些比赛尚未结算，所以 ROI、最大回撤均为 `null`；本批次也远低于每市场 10,000 场目标。完整原始报价、比赛身份、预测和逐场配对保留在本机既有私有授权归档，公开报告只保存脱敏汇总与哈希：[前瞻采集回执](results/m5_forward_shadow_totalcorner_capture_20261106T0321Z.json)。该采集用既有本机授权路径，没有打印或公开凭证；不改 M1/M2/MR1/M3/M4 生产流程，不启用 Telegram，也没有新增交易 Gate 或模型自动晋升。仓库没有 M5 Actions workflow，本轮无 Actions run。

## 2026-11-06 02:18Z M5 前瞻 Crown 批次

按当前 UTC 对固定范围缓存赛程重新训练并生成 361 场 M5 独立预测（预测输入/逐场 ID 保留在本机私有归档）。使用既有本机授权路径完成 361 次 Crown endpoint 尝试：357 条 fixture/Crown 身份校验成功、3 条身份/Crown 校验失败、1 条传输失败。capture 运行终止于 `2026-11-06T02:46:24.606468Z`。严格要求 `prediction_asof <= quote_event <= actual_receipt < kickoff` 后，AH、OU 均为 0 个有效报价；独立配对审计同样为 0 场、0 注、无 ROI。接口成功响应数不能解释为盘口覆盖。

脱敏回执：[forward capture aggregate](results/m5_forward_shadow_capture_20261106T0218Z.json)。回执只含时间、计数和哈希，不含逐场身份、价格、原始响应或密钥。历史 Crown/TOTAL 样本仍各有超过 10,000 场 Crown-first 并集，但接收都在开赛后；新的前瞻采集尚未产生可结算样本。M5 收益目标仍未达到。

## 2026-11-06: 全样本 EV 与按联赛方向 walk-forward 候选

扩展的 Crown-first/TOTAL-default 回放为 AH、OU 各 11,071 场唯一 fixture-market：AH Crown 9,987 + TotalCorner default 1,084，OU Crown 9,986 + TotalCorner default 1,085。原样本无重复；每场每市场固定一注 1U。所有历史 API 回执均晚于开赛，故只能解释为按来源盘口事件时间的回顾性回放。

研究阈值诊断预先固定 EV 候选 0、1、2、5、10、15、20 个百分点，并保留每个市场全部 11,071 场研究母样本。2025 的 874 场训练窗中，各正 EV 子集仍亏损；训练期 ROI 最好的检查点为 AH EV≥20%：322 注、-8.187112%，OU EV≥10%：382 注、-6.743455%。冻结这些阈值后看 2026 留出：AH 3,429 注、-3.043890%；OU 4,655 注、-1.992320%。2026 各枚举阈值 ROI 均为负，候选被否决，不形成交易 Gate。

来源分层也没有显示可直接放大的 TOTAL 优势：2026 AH Crown n=9,260 ROI `-1.763283%`、TOTAL n=901 `-2.807991%`；OU Crown n=9,260 `-3.352268%`、TOTAL n=901 `-4.103774%`。2025 训练窗 AH Crown n=727 `-9.437414%`、TOTAL n=147 `-15.170068%`；OU Crown n=726 `-6.420110%`、TOTAL n=148 `+0.582770%`。这些都是分层描述，不据小样本来源表现挑选来源或改写优先规则。

另按每个市场/联赛在 2025 ROI 最高的预设方向（模型较高期望回报、盘口热门、盘口冷门）训练择向：每联赛 2025 至少 20 场才允许择向，较小组沿用模型高 EV 方向；规则冻结到 2026，未过滤任何比赛，维持 AH/OU 各 10,161 注。训练期合计 874 场。2026 AH ROI `-1.373019%`（基线 `-1.855920%`），OU ROI `-3.019732%`（基线 `-3.418906%`）；方向在训练表现的逐联赛选择有多重比较/过拟合风险，收益目标均未达 +3%。对照回执：[全方向/按联赛年度分层](results/m5_source_union_league_year_diagnostic_20261106.json)、[热门方向](results/m5_source_union_favorite_league_year_diagnostic_20261106.json)、[冷门方向](results/m5_source_union_underdog_league_year_diagnostic_20261106.json)、[阈值诊断](results/m5_source_union_ev_threshold_diagnostic_20261106.json)、[冻结联赛方向留出](results/m5_league_direction_2025_train_2026_oos_20261106.json)。候选方向选择复现代码为 [m5_league_direction_walkforward.py](m5_league_direction_walkforward.py)。所有新方案仅供 M5 研究，没有写入生产策略。

数据时序与模型融合边界：M5 历史概率严格满足 `train_end < prediction_asof < kickoff`；盘口源事件位于预测时间至开赛之间，唯一比赛用最终比分结算。接收时间另行审计；本节所有历史报价 API 回执均在开赛后。此前 M3 AH0/OU2.5 严格 Crown 配对留出只有 38/59 场，虽然 2026 event-time ROI 有局部正值，远低于 10,000 场且回执均为赛后回取；不得用这类小样本替代全样本验收。M1 完整观察档案中唯一完整 FT challenge cohort 为 52 场，M5-M1 OU 严格同价结算配对仅 23 场；MR1/M3 的可比合约同样是局部小 cohort，均不足以解释全市场 10k 结果。具体匹配、身份排除和 proper-score 结果沿用下列各专题回执。

## 2026-11-06 本地 Crown / TotalCorner 全历史 M5 OOS 回放续审

本机已完成的 M5 Crown 历史回填进度摘要为 11,149 个已处理候选、11,085 个精确身份 Crown 响应；逐场源优先回放实际使用 Crown AH 9,987 / OU 9,986 场，TotalCorner default 仅补 Crown 缺失项 AH 1,084 / OU 1,085 场。来源合并后不重复计数，基础全历史 OOS 每市场 11,071 场，覆盖 2015-01-01 至 2026-11-04 UTC。另有固定范围赛程清单 51 联赛、1,530 场；Crown 历史候选 manifest 127,674 场。TotalCorner fallback 1,100 条索引中 1,094 条为 verified response、6 条 transport error；所有原始请求及预测仍留私有目录，凭证未读取或公开。

同一历史价格选择规则下（预测截止早于 as-of，报价事件在 as-of 与 kickoff 之间；每场/市场一注 1U，按实际 AH/OU 线价分数结算）基准及固定方向对照如下：

| Forecast / side policy | AH 唯一场数 / ROI | OU 唯一场数 / ROI |
|---|---:|---:|
| M5 baseline，高期望回报方向 | 11,071 / -2.539766% | 11,071 / -3.541505% |
| 按报价低赔率侧 favorite | 11,071 / -4.279898% | 11,071 / -3.051757% |
| 按报价高赔率侧 underdog | 11,071 / -2.071245% | 11,071 / -4.391970% |
| 近期加权 M5 | 11,035 / -3.052424% | 11,035 / -3.423629% |
| Bivariate Poisson | 10,125 / -3.014000% | 10,125 / -3.385481% |

Baseline AH 全赢/半赢/走水/半输/全输 `4,421/758/769/764/4,359`，净 `-281.1775U`，最大回撤 `303.8325U`；OU `4,591/625/551/775/4,529`，净 `-392.0800U`，最大回撤 `414.8125U`。Bivariate AH `4,012/715/696/676/4,026`，净 `-305.1675U`；OU `4,214/561/503/712/4,135`，净 `-342.7800U`。每市场 ROI bootstrap 95% 区间均完全低于 0；全部候选策略均未达 +3%。逐年结果、概率评分、联赛/盘口来源拆分在对应 JSON 回执中。

AH/OU 分市场概率融合仅用 2025 OOS 样本拟合，2026 的 10,235 个 baseline/recency OOS 预测作 holdout。AH exact-score proper loss 权重为 baseline/recency/Bivariate `0.327964/0.559322/0.112713`；OU total-goals proper loss 权重为 baseline/recency `0.623921/0.376079`（Bivariate 权重0）。对 2026 Crown-first+TOTAL 样本 10,161 场，AH 融合 ROI `-2.215874%`，OU `-3.285700%`，均没有改善至盈利。模型缺少 Bivariate 预测的比赛保留，用两个可用 M5 模型重归一权重；样本不按结果筛选。

**证据边界：** 真实历史 fixture、FT、盘口事件时间都经过配对校验，严格无重复；但 11,071 条历史 API receipt 全部在开赛后取得。event time 早于 kickoff 不等于报价当时已接收，更不等于可成交。因此这些值是可核查的赛后回取历史盘口 event-time OOS 回放，不是赛前实收、执行 ROI 或实战成绩；不能据此声称收益目标已经通过。TotalCorner default 仍独立标记，不冒充 Crown。当前真正赛前收到 Crown 样本仍远低于 10,000。

回执：[baseline 全 OOS](results/m5_source_union_higher_ev_all_oos.json)、[favorite](results/m5_source_union_favorite_side_all_oos.json)、[underdog](results/m5_source_union_underdog_side_all_oos.json)、[recency 全 OOS](results/m5_source_union_recency_all_oos.json)、[Bivariate 全 OOS](results/m5_source_union_bivariate_all_oos.json)、[2025 拟合的 AH/OU 融合权重及 proper scores](results/m5_goal_model_grid_ensemble_2025_train_2026_oos.json)、[AH 融合回放](results/m5_source_union_market_blend_2025fit_ah_grid_2026_oos.json)、[OU 融合回放](results/m5_source_union_market_blend_2025fit_ou_grid_2026_oos.json)。

各模型全历史样本不是同一集合：baseline n=11,071（2015年36、2025年874、2026年10,161）；recency n=11,035（2025年874、2026年10,161）；Bivariate n=10,125（2025年785、2026年9,340，训练期未见队伍导致预测覆盖较少）。不得将这些指标按样本量直接相加或视为完全配对比较。其训练/预测 UTC 先后关系均通过逐场校验；ROI 分母为一场一注的 1U 本金。完整正确比分 Log Loss / OU 总进球 Log Loss 及模型匹配覆盖写在相应报告里。

## 2026-11-06：10k样本回放与新模型/校准对照

本轮冻结 M5 候选范围内的 2026 UTC 年度留出，penaltyblog Bivariate Poisson 新增 20,596 个严格按 UTC 年前推的 OOS 全比分网格（2025: 11,187；2026: 9,409），51 个联赛、102/102 个联赛-年份折成功，1,606 场因训练期未见队伍而无预测；训练截止严格早于目标年 1 月 1 日，训练/目标 fixture ID 不相交。`penaltyblog==1.13.1`、固定默认拟合，无按目标期 ROI 或结果选参。它与 M5 既有基础/近期加权模型在 10,125 个完全相同的 Crown-first / TotalCorner-default fixture-market 上比较：

| 模型 | AH ROI / LL / Brier | OU ROI / LL / Brier |
|---|---:|---:|
| 基础 M5 | -2.461704% / 1.03262740 / 0.64914976 | -3.378222% / 0.98760091 / 0.62329791 |
| 近期加权 M5 | -3.050914% / 1.02802253 / 0.64615411 | -3.435852% / 0.98850025 / 0.62421681 |
| 新增 Bivariate Poisson | -3.014000% / 1.03939273 / 0.65061921 | -3.385481% / 0.98915584 / 0.62417022 |

另以 2025 年 11,967 个 OOS 赛果拟合固定三种 score-grid 校准（全局 rate、精确比分 Log Loss tilt、固定等效 100 场联赛收缩），2026 年 10,235 个基础模型 OOS forecast 作严格未触碰 holdout；校准未使用 ROI/盘口或 holdout 赛果拟合。前两种的回放结果相同（数值差异仅在最末位），AH ROI -1.831365%、LL/Brier 1.03527174/0.65061678；OU -3.533264%、0.98740118/0.62266518。固定联赛收缩方案 AH -2.704458%、1.03593176/0.65101905；OU -4.275391%、0.99106094/0.62544291。每方案均有 10,161 场/市场，AH 和 OU 独立计数。三者均未达 +3%，其中每个市场的 fixture-bootstrap 95% 区间均完全低于零。

该 10,161 样本的来源组成是 Crown 9,260 + TotalCorner default 901（只填 Crown 缺口，绝非其他公司交易盘替代），覆盖 2026-01-01 至 2026-11-04 UTC；每一条所选历史 API receipt 都在 kickoff 后收到。盘口 source-event 时间虽然严格早于 kickoff 且不早于 forecast as-of，但不证明赛前已收到或可执行成交。因此上述 ROI 只是事后回取报价上的 event-time 研究回放；有效赛前收到的 Crown 历史覆盖仍不足以支持 10k 场可执行 ROI 验收。最大回撤等序列仅作为历史模拟描述，不作为真实账本表现。

新模型评估报告：[Bivariate Poisson OOS 聚合](results/m5_goal_model_penaltyblog_bivariate_oos_20261106.json)；三组匹配回放：[基础](results/m5_source_union_baseline_penaltyblog_matched_20261106T010824Z.json)、[近期加权](results/m5_source_union_recency_penaltyblog_matched_20261106T010824Z.json)、[Bivariate Poisson](results/m5_source_union_penaltyblog_bivariate_replay_20261106T010509Z.json)。校准拟合及边界：[2025→2026校准审计](results/m5_goal_model_calibration_2025_train_2026_oos_20261106.json)；对应[全局rate回放](results/m5_source_union_calibrated_2025_global_rate_2026_oos.json)、[score-grid Log Loss回放](results/m5_source_union_calibrated_2025_scoregrid_logloss_2026_oos.json)、[固定联赛收缩回放](results/m5_source_union_calibrated_2025_shrunk_league_2026_oos.json)。私有逐场预测、fixture 身份和原始 quote 保留在仓库外。

**最新收益目标（2026-11-05 用户重启）**：AH、OU 独立研究，任一市场的样本外 ROI ≥3% 即达到收益指标；每个市场仍需至少10,000场真实唯一历史比赛。Crown 优先；缺少可用 Crown 市场报价时允许使用 TotalCorner（TOTAL），两种来源分别标识及统计。下方旧报告中的“两个市场均需 >5%”属于早期目标记录，已被本目标覆盖。

生成时间：2026-11-05 UTC。M5 是独立研究身份；本目录不连接 M1/MR1/M3 的生产预测、订单、账本或 Telegram。当前已有真实概率前推实验、Crown AH/OU回放和同场OU quote-time配对诊断。Crown-first加TotalCorner default的事件时间样本已超过每市场10,000场，但Crown-only不足10,000场，且全部API历史回执在kickoff之后；因此不构成赛前已收到盘口的收益验证。M5 Actions尚未验收。最新报告与新增 quote-time 诊断见 [M5_PROGRESS_REPORT_20261104.md](M5_PROGRESS_REPORT_20261104.md)，当前 M5 forecast 生成于 `2026-11-04T21:39:54Z` UTC，依赖回放于 `2026-11-04T21:41Z` UTC 重算。

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


### 2026-11-05T20:04Z incremental Crown capture checkpoint

Formal progress `2026-11-05T20:00:12Z`: 10,700 candidates, 10,638 exact responses, 62 transport errors, 9,635 valid quotes per market, zero identity/time mismatches.

Replay `2026-11-05T20:01:49Z`: AH n=9,636 / OU n=9,635, both below 10,000. UTC coverage: 376 AH / 375 OU fixtures in 2025 and 9,260 per market in 2026. AH `-187.205U / -1.942767%` (LL/Brier `1.03145914/0.64871897`, max DD `216.300U`); OU `-326.105U / -3.384587%` (`0.98884507/0.62380850`, max DD `368.980U`). Eight invalid receipt-time rows excluded; all selected receipts post-kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T200149Z.json).

Temporal holdout `2026-11-05T20:04:11Z`: 7,359 AH / 7,358 OU train and 2,295 disjoint holdout each. Raw/calibrated ROI AH `+0.244009% / +0.077996%`, OU `-4.723965% / -3.930501%`. Calibrated LL/Brier AH `1.02689426/0.64219581`, OU `0.99071639/0.62467157`. All holdout API receipts post-kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T200411Z.json).


### 2026-11-05T20:13Z incremental Crown capture checkpoint

Formal progress `2026-11-05T20:10:01Z`: 10,800 candidates, 10,738 exact responses, 62 transport errors, 9,709 valid quotes per market.

Replay `2026-11-05T20:11:05Z`: AH 9,705 / OU 9,704, below the 10,000 target. UTC coverage: AH 445 in 2025 / 9,260 in 2026; OU 444 / 9,260. AH `-194.565U / -2.004791%` (LL/Brier `1.03162908/0.64887789`, max DD `222.715U`); OU `-340.485U / -3.508708%` (`0.98866252/0.62371967`, max DD `368.980U`). Ten invalid receipt-time rows were excluded; all included API receipts were post-kickoff. [Replay receipt](results/m5_source_union_replay_partial_20261105T201105Z.json).

Temporal holdout `2026-11-05T20:13:23Z`: 7,435 AH / 7,434 OU training fixtures and 2,295 disjoint holdout fixtures each. Raw/calibrated ROI AH `+0.244009% / +0.204139%`, OU `-4.723965% / -4.106100%`. Calibrated LL/Brier AH `1.02690861/0.64220055`, OU `0.99084732/0.62476734`. All API receipts post-kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T201323Z.json).


### 2026-11-05T20:19Z incremental Crown capture checkpoint

Formal progress `2026-11-05T20:15:34Z`: 10,900 candidates, 10,837 exact responses, 63 transport errors, 9,787 valid AH/OU quotes.

Replay `2026-11-05T20:17:01Z`: AH n=9,788 / OU n=9,787 (18 invalid receipt-time records excluded), below 10,000. AH `-201.660U / -2.060278%` (LL/Brier `1.03199300/0.64903922`, max DD `225.955U`); OU `-342.230U / -3.496781%` (`0.98842490/0.62369804`, max DD `368.980U`). All selected receipts were post-kickoff. UTC coverage includes 528 AH / 527 OU in 2025 and 9,260 each in 2026. [Replay receipt](results/m5_source_union_replay_partial_20261105T201701Z.json).

Temporal holdout `2026-11-05T20:19:22Z`: AH 7,511 / OU 7,510 train and 2,295 disjoint holdout each. Raw/calibrated ROI AH `+0.244009% / +0.302179%`, OU `-4.723965% / -3.930501%`; calibrated LL/Brier AH `1.02692203/0.64220440`, OU `0.99072444/0.62467648`. All API receipts post-kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T201922Z.json).


### 2026-11-05T20:28Z incremental Crown capture checkpoint

Formal progress `2026-11-05T20:24:47Z`: 11,000 candidates, 10,936 exact responses, 64 transport errors, 9,869 valid AH/OU quotes.

Replay `2026-11-05T20:26:20Z`: AH n=9,869 / OU n=9,868, still below 10,000. AH `-216.450U / -2.193231%` (LL/Brier `1.03197119/0.64920843`, max DD `240.745U`); OU `-342.360U / -3.469396%` (`0.98829192/0.62362335`, max DD `368.980U`). Sixteen invalid receipt times excluded; all included response receipts post-kickoff. UTC coverage: 609 AH / 608 OU in 2025 and 9,260 in 2026. [Replay receipt](results/m5_source_union_replay_partial_20261105T202620Z.json).

Temporal holdout `2026-11-05T20:28:39Z`: train 7,607 AH / 7,606 OU; 2,295 disjoint holdout each. Raw/calibrated ROI AH `+0.244009% / +0.253159%`, OU `-4.723965% / -4.106100%`. Calibrated LL/Brier AH `1.02692309/0.64220479`, OU `0.99083882/0.62476054`. All API receipts post-kickoff. [Holdout receipt](results/m5_crown_goal_rate_temporal_holdout_20261105T202839Z.json).


## Crown capture terminal snapshot (2026-11-05T20:36:44Z)

The collector stopped at 11,149 processed candidates, 11,085 exact responses, 64 transport errors, and 10,001 valid source-time AH quotes / 10,000 OU quotes; identity/time mismatches were zero. The append-only final replay (`2026-11-05T20:38:51Z`) excludes 13 AH and 14 OU rows with missing/invalid API receipt timestamps, leaving 9,987 AH and 9,986 OU settled event-time fixtures. All included API receipts arrived after kickoff. AH `-231.890U / -2.321918%` (LL/Brier `1.03256301/0.64947509`, event-time max DD `257.135U`, bootstrap 95% `-4.050916% to -0.567938%`); OU `-357.030U / -3.575305%` (`0.98836723/0.62366227`, DD `368.980U`, bootstrap `-5.298318% to -1.840777%`). Kickoff span `2025-11-30` through `2026-11-04` UTC. This meets the 10k source-event capture count, but not 10k rows with a valid receipt-time index; neither market ROI is positive, much less +3%. [Crown terminal replay](results/m5_crown_terminal_replay_20261105T203851Z.json).

Final temporal holdout (`2026-11-05T20:41:14Z`) uses 7,692 AH / 7,691 OU training IDs and 2,295 disjoint test IDs each. Calibrated ROI is AH `+0.385839%`, OU `-4.017647%`; proper scores improve modestly, but every API quote receipt is post-kickoff. [Crown terminal holdout](results/m5_crown_terminal_temporal_holdout_20261105T204114Z.json).

The private TOTAL fallback diagnostic uncovered a parser mismatch: 75 exact-identity `/match/odds` responses contain historical 7-column odds rows (AH and OU), while the initial parser required the 8-column form and therefore marked every row unusable. TotalCorner's current public API specification documents the first five fields as minute, line, both prices, and source time, with score and `closed` appended in the 8-column example. The parser now accepts a 7-column row only when its minute field is empty and all line, price, timestamp, forecast-as-of, and kickoff checks pass; if an 8-column row is supplied, the `closed` flag must still be open. No receipt timestamp is inferred from a source event timestamp.

## 2026-11-05 TotalCorner 7-column parser correction and Crown-first replay

Generated `2026-11-05T21:35:07Z`, source code run locally on 2026-11-06 UTC. 75 exact-identity TOTAL responses yielded 75 eligible fixture-markets in each market after per-row strict UTC checks; all their API receipts occurred after kickoff. Crown remains first choice per fixture-market, so merged samples are AH 10,062 (9,987 Crown + 75 TOTAL default) and OU 10,061 (9,986 Crown + 75 TOTAL default). This clears the 10,000 unique fixture-market count, but not the contemporaneous receipt-time requirement: this is event-time retrospective replay only.

AH: `-234.390U / -2.329457%`, settlement log loss `1.03406769`, Brier `0.65026565`, event-time max drawdown `257.135U`. By UTC kickoff year: 2025 n=727 ROI `-9.437414%`; 2026 n=9,335 ROI `-1.775897%`.

OU: `-365.0925U / -3.628789%`, settlement log loss `0.98845404`, Brier `0.62366511`, event-time max drawdown `380.2125U`. By UTC kickoff year: 2025 n=726 ROI `-6.420110%`; 2026 n=9,335 ROI `-3.411703%`.

Neither market reaches the +3% target. The historical archive contains source-event timestamps before kickoff, but API receipt timestamps are after kickoff for every selected row; ROI is not executable or prospective performance. No record is categorized as Crown when its source is TotalCorner default. Machine-readable aggregate report: [7-column parser Crown-first replay](results/m5_source_union_replay_7col_checkpoint_20261105T213507Z.json). Private raw responses remain outside the repository.

## 2026-11-05 continued TOTAL capture and source-stratified replay

The corrected collector resumed using the existing Keychain authorization; no new credential was requested. At this replay snapshot (`2026-11-05T21:43:05Z`), 108 fixture-markets per side were filled by TotalCorner default where Crown was unavailable. Source-separated: Crown AH 9,987, `-231.890U / -2.321918%`; TOTAL AH 108, `+1.7625U / +1.631944%`. Crown OU 9,986, `-357.030U / -3.575305%`; TOTAL OU 108, `-4.225U / -3.912037%`. The TOTAL subgroups are descriptive and far smaller than the 10,000-fixture objective; do not select a model or market rule from them.

Merged AH has 10,095 unique fixture-markets, `-230.1275U / -2.279619%`, settlement LL/Brier `1.03346167 / 0.64989846`, event-time max DD `257.135U`. Merged OU has 10,094, `-361.255U / -3.578908%`, LL/Brier `0.98830774 / 0.62355109`, DD `376.375U`. All selected response receipts remain post-kickoff. Neither market reaches +3%. Capture continued after this checkpoint. [Source-stratified replay receipt](results/m5_source_union_replay_live_20261105T214305Z.json).

Follow-on replay (`2026-11-05T21:45:56Z`) after continued TOTAL capture: Crown counts remain AH 9,987 / OU 9,986; TOTAL default fills 158 fixture-markets per market. TOTAL-only descriptive ROI is AH `-5.458861%`, OU `-9.390823%`, reversing the earlier 108-row AH positive point estimate. Merged AH n=10,145 ROI `-2.370774%`, net `-240.515U`, LL/Brier `1.03396708 / 0.65017038`, DD `261.170U`; OU n=10,144 ROI `-3.665886%`, net `-371.8675U`, LL/Brier `0.98872434 / 0.62387802`, DD `386.9875U`. By UTC kickoff year: AH 2025 n=727 `-9.437414%`, 2026 n=9,418 `-1.825281%`; OU 2025 n=726 `-6.420110%`, 2026 n=9,418 `-3.453573%`. Every response receipt remains post-kickoff, so this remains event-time retrospective analysis. [Follow-on source-stratified receipt](results/m5_source_union_replay_live_20261105T214556Z.json).

Third snapshot (`2026-11-05T21:51:20Z`): TOTAL default contribution reached 245 unique fixture-markets in each market. TOTAL-only ROI is AH `-4.556122%`, OU `-5.959184%`. Merged AH n=10,232 ROI `-2.375415%`, `-243.0525U`, LL/Brier `1.03444063 / 0.65051435`, event-time max DD `263.7075U`; OU n=10,231 ROI `-3.632392%`, `-371.6300U`, LL/Brier `0.98927955 / 0.62418989`, DD `386.7500U`. UTC-year splits: AH 2025 n=727 `-9.437414%`, 2026 n=9,505 `-1.835271%`; OU 2025 n=726 `-6.420110%`, 2026 n=9,505 `-3.419463%`. All receipts are post-kickoff. The 10k count remains met, but neither ROI target is met and results are event-time only. [Third source-stratified receipt](results/m5_source_union_replay_live_20261105T215120Z.json).

Fourth snapshot (`2026-11-05T21:55:43Z`): TOTAL default n=280 per market. AH TOTAL-only `-0.388393%`; OU TOTAL-only `-7.062500%`. Merged AH n=10,267, `-232.9775U / -2.269188%`, LL/Brier `1.03423246 / 0.65036647`, event-time DD `256.085U`; OU n=10,266, `-376.805U / -3.670417%`, LL/Brier `0.98917425 / 0.62414509`, DD `391.925U`. All included API receipts post-kickoff. UTC-year splits: AH 2025 n=727 `-9.437414%`, 2026 n=9,540 `-1.722930%`; OU 2025 n=726 `-6.420110%`, 2026 n=9,540 `-3.461164%`. Neither target met. [Fourth source-stratified receipt](results/m5_source_union_replay_live_20261105T215543Z.json).

## Crown-first/TOTAL-fill temporal rate-calibration holdout

Generated `2026-11-05T22:00:58Z`, fixed UTC cutoff `2026-09-01T00:00:00Z`. The same per-fixture-market Crown-first/TOTAL-only-if-Crown-absent contract source logic is used on both periods. AH: 7,773 training markets (7,692 Crown + 81 TOTAL) and 2,570 disjoint holdout markets (2,295 Crown + 275 TOTAL). OU: 7,772 training (7,691 Crown + 81 TOTAL) and 2,570 disjoint holdout (2,295 Crown + 275 TOTAL). M5 annual walk-forward forecasts remain the base probabilities; train-only separate home/away rate factors are fitted from training score-grid expected goals versus prior actual goals, without ROI optimization or additional selections.

AH raw holdout: 2,570 bets, 1U each, W/HW/P/HL/L `1083/147/178/186/976`, net `+5.1625U`, ROI `+0.200875%`, max drawdown `40.0975U`, LL/Brier `1.03491701 / 0.64661616`, bootstrap 95% ROI `-3.190370% to +3.613813%`. Calibrated holdout: same 2,570 bets, `1084/144/178/189/975`, `+3.6075U`, ROI `+0.140370%`, DD `39.3175U`, LL/Brier `1.03428630 / 0.64642354`, interval `-3.314494% to +3.537938%`.

OU raw holdout: 2,570 bets, W/HW/P/HL/L `1048/144/131/171/1076`, `-125.9900U`, ROI `-4.902335%`, DD `146.110U`, LL/Brier `0.99851295 / 0.63005996`, interval `-8.489397% to -1.464689%`. Calibrated: `1052/147/131/168/1072`, `-114.6500U`, ROI `-4.461089%`, DD `147.505U`, LL/Brier `0.99332170 / 0.62625257`, interval `-7.878016% to -0.988327%`.

Calibration improves proper scores for both markets and modestly reduces OU losses, but does not approach +3%; AH point ROI stays near zero and its intervals cross zero. Training and holdout fixture IDs are disjoint. Every API receipt in each holdout occurred after kickoff; historical source event times are between model as-of and kickoff, so the ROI remains event-time retrospective rather than executable. Report and source audit: [Crown-first/TOTAL temporal holdout](results/m5_source_union_goal_rate_temporal_holdout_20261105T220058Z.json); reproduction script: [m5_source_union_goal_rate_temporal_holdout.py](m5_source_union_goal_rate_temporal_holdout.py).

The temporal holdout execution overlapped live capture; its input snapshot selected 356 TOTAL fixture-markets per side. A later full source-union replay (`2026-11-05T22:04:02Z`) read 396 TOTAL additions per side and confirms no goal crossing: AH 10,383 unique fixture-markets, `-236.040U / -2.273331%`, W/HW/P/HL/L `4161/705/717/726/4074`, DD `256.695U`, LL/Brier `1.03421496 / 0.65032033`; OU 10,382, `-369.8425U / -3.562343%`, `4311/567/521/734/4249`, DD `384.9625U`, LL/Brier `0.98854595 / 0.62378627`. Source split: Crown AH 9,987 `-2.321918%`, TOTAL AH 396 `-1.047980%`; Crown OU 9,986 `-3.575305%`, TOTAL OU 396 `-3.235480%`. All selected receipts are after kickoff. [Post-holdout full replay](results/m5_source_union_replay_live_20261105T220402Z.json).

### Exact-score proper-loss calibration experiment (same temporal cutoff)

Second holdout snapshot generated `2026-11-05T22:08:54Z`, cutoff still `2026-09-01T00:00:00Z`. Continued capture raised training TOTAL coverage to 153 fixture-markets per market (Crown AH/OU 7,692/7,691); holdout remains 2,570 per market (2,295 Crown + 275 TOTAL), disjoint and all API receipts post-kickoff. I independently fitted the same two-parameter score-grid exponential tilt by exact-score negative log likelihood on each prior-period training set, then applied it to the same unchanged holdout side-selection rule. Fitted multipliers were essentially identical to the previous expected-goal matching MLE: AH home/away `1.026969/1.031078` vs `1.026969/1.031078`; OU `1.026999/1.031192` vs `1.026999/1.031192`.

AH exact-score-loss calibration holdout ROI `+0.114494%` (raw `+0.200875%`), net `+2.9425U` on 2,570 bets; LL/Brier `1.03429493 / 0.64642876`, DD `39.0675U`, interval `-3.258560% to +3.512840%`. OU calibrated ROI `-4.304864%` (raw `-4.902335%`), `-110.635U`, LL/Brier `0.99319643 / 0.62615866`, DD `143.490U`, interval `-7.717510% to -0.890467%`. The second fitting objective reproduces the same calibration to numerical precision and adds no ROI uplift. Neither market approaches +3%. [Exact-score calibration report](results/m5_source_union_goal_rate_temporal_holdout_scoregrid_20261105T220854Z.json).

Full source-union replay generated `2026-11-05T22:09:59Z`, after the score-grid holdout snapshot: AH n=10,431, Crown 9,987 + TOTAL 444, `-245.440U / -2.352986%`, W/HW/P/HL/L `4176/708/721/730/4096`, event-time DD `266.095U`, LL/Brier `1.03454798 / 0.65057468`; OU n=10,430, Crown 9,986 + TOTAL 444, `-358.9675U / -3.441683%`, `4337/569/526/738/4260`, DD `374.0875U`, LL/Brier `0.98837331 / 0.62359838`. Source ROIs: Crown AH `-2.321918%`, TOTAL AH `-3.051802%`; Crown OU `-3.575305%`, TOTAL OU `-0.436374%`. All API receipts are post-kickoff. Neither merged market meets +3%. [Latest full replay](results/m5_source_union_replay_live_20261105T220959Z.json).

## 2026-11-06 live-archive catch-up replay

Replayed the private Crown-first archive again at `2026-11-05T22:15:08.959431Z` (the API receipt timestamp is UTC; execution was inspected on 2026-11-06 local time). The replay re-read 127,674 candidate manifest entries and 127,674 OOS forecast rows and applies the same per-fixture/market identity, event-time (`asof <= quote < kickoff`), settlement and Crown-first fallback rules. It now finds AH 10,493 (9,987 Crown + 506 TotalCorner default) and OU 10,492 (9,986 Crown + 506 TotalCorner default). AH net `-250.8025U`, ROI `-2.390189%`, log loss `1.03458156`, Brier `0.65067752`, event-time max drawdown `271.4575U`; OU net `-366.4925U`, ROI `-3.493066%`, log loss `0.98876378`, Brier `0.62383461`, drawdown `381.6125U`. 2025 and 2026 splits remain negative in both markets. Every archive API receipt is post-kickoff. This is historical source-event replay, not executable Crown ROI or prospective performance. Report: [live-archive replay](results/m5_source_union_replay_live_20261106T105500Z.json).

An archive index recount at the same inspection found 539 TotalCorner request rows (537 verified, 2 transport errors) and 458 rows with at least one parser-counted pregame AH/OU movement. This is not a market coverage count: replay source assignment is performed against M5 forecast as-of, kickoff, exact fixture identity and Crown presence. The progress checkpoint was written after 400 attempts and is expected to lag the append-only response index. Do not compare its cumulative counters directly to later replay snapshots.

## 2026-11-06 expanded archive replay and loss diagnostics

A second replay against the growing private archive was generated at `2026-11-05T22:18:23.881502Z`; output: [expanded source-union replay](results/m5_source_union_replay_live_20261106T111000Z.json). It validates 127,674 candidate fixtures and OOS forecast rows, with unique fixture-markets (no cross-source duplication): AH 10,529 and OU 10,528. Every included quote satisfied the model as-of/source-event/kickoff ordering and exact fixture identity; every response receipt was after kickoff, so outcomes remain retrospective event-time simulations.

| Market | Bets / settled | Crown | TotalCorner default | Net U / ROI | Max event-time DD | Settlement LL / Brier | Bootstrap 95% ROI |
|---|---:|---:|---:|---:|---:|---:|---:|
| AH | 10,529 | 9,987 | 542 | -247.615 / -2.351743% | 268.270 | 1.03463516 / 0.65071765 | -4.024527% to -0.640374% |
| OU | 10,528 | 9,986 | 542 | -371.0425 / -3.524340% | 386.1625 | 0.98904496 / 0.62402889 | -5.227204% to -1.872625% |

Each simulation stakes 1U per unique fixture-market, so ROI denominator equals settled bets. AH settlement: 4,216 full wins / 714 half wins / 730 pushes / 734 half losses / 4,135 full losses. OU: 4,371 / 579 / 531 / 742 / 4,305. UTC kickoff coverage is 2025-11-30 through 2026-11-04. Both 2025 and 2026 annual ROI are negative for both markets. By source, AH Crown is -2.321918% (n=9,987) and TotalCorner default -2.901292% (n=542); OU Crown -3.575305% (n=9,986) and TotalCorner default -2.585332% (n=542). The fallback source reduces total-sample loss slightly on OU relative to a Crown-only point estimate, but its own returns remain negative and source receipts are all post-kickoff.

Descriptive diagnosis (no selection rule applied): 48 leagues have at least 100 AH fixtures. Some league/hour/line cells have positive point ROI, but many have tiny samples and the report has no multiplicity correction or pristine prospective validation. These are hypotheses only; no league/time/line gate is introduced. Forecasts were almost all issued more than 24h before kickoff (AH 10,523; OU 10,522); this coarse split does not reveal a viable subset. Source-event timing also varies, but historical response receipt was post-kickoff in all cases. The fixed AH0 / OU2.5 M3 complement study remains only n=38/n=59 holdout and must not be blended into this 10k full-contract result.

## 2026-11-06 continued TOTAL expansion checkpoint

The live archive replay at UTC `2026-11-05T22:22:45.188968Z` includes AH 10,564 and OU 10,563 unique fixture-markets, with Crown-first source assignments of AH 9,987 Crown + 577 TotalCorner default and OU 9,986 + 577. AH net `-248.4525U`, ROI `-2.351879%`, max event-time drawdown `269.1075U`, settlement LL/Brier `1.03481846/0.65081882`, fixture-bootstrap 95% ROI interval `[-4.034244%,-0.646251%]`. OU net `-386.2175U`, ROI `-3.656324%`, drawdown `401.3375U`, LL/Brier `0.98942987/0.62431006`, interval `[-5.384053%,-1.950937%]`. All 10,564/10,563 response receipts are post-kickoff. Source-event replay remains retrospective. Report: [continued replay](results/m5_source_union_replay_live_20261106T113000Z.json).

## 2026-11-06 refreshed temporal calibration holdout

Re-ran the fixed-cutoff Crown-first/TOTAL-fallback study against the expanded archive; output: [refreshed temporal holdout](results/m5_source_union_goal_rate_temporal_holdout_refresh_20261106T120000Z.json), generated UTC `2026-11-05T22:26:44.229235Z`. The UTC cutoff remains 2026-09-01; AH and OU are fitted separately on prior-period fixture IDs (AH 8,018; OU 8,017) and evaluated on disjoint 2,570-fixture holdouts each. Training uses 7,692/7,691 Crown plus 326 TotalCorner default fixtures; holdout is 2,295 Crown + 275 TotalCorner per market. Parameters minimize past expected-goal or exact-score log loss, never ROI. This is a repeated, previously inspected 2026 research holdout, not a pristine untouched prospective test.

Raw versus calibrated holdout: AH raw `+0.200875%` (+5.1625U), calibrated `-0.065856%` (-1.6925U); calibrated LL/Brier improve from `1.03491701/0.64661616` to `1.03435546/0.64644738`, but ROI interval spans zero (`-3.492704% to +3.365078%`). OU raw `-4.902335%` (-125.99U), calibrated `-4.597276%` (-118.15U); LL/Brier improve `0.99851295/0.63005996` to `0.99352233/0.62639662`, while ROI interval remains fully negative (`-8.013521% to -1.161187%`). Bootstrap uses 10,000 fixture resamples. Every selected historical API receipt is post-kickoff. Calibration helps proper scores (and OU ROI modestly), but neither market reaches +3%; no selection or deployment gate was added.

## 2026-11-06 latest source-union replay

Replayed the private archive at generated UTC `2026-11-05T22:28:04.640546Z`; report: [latest replay](results/m5_source_union_replay_live_20261106T123000Z.json). AH 10,607 (9,987 Crown + 620 TotalCorner default), net `-253.140U`, ROI `-2.386537%`, DD `273.795U`, LL/Brier `1.03468985/0.65075769`, bootstrap 95% ROI `[-4.013906%,-0.727279%]`; settlements 4,247 win / 721 half-win / 732 push / 737 half-loss / 4,170 loss. OU 10,606 (9,986 + 620), net `-395.930U`, ROI `-3.733076%`, DD `411.050U`, LL/Brier `0.98960459/0.62443280`, bootstrap `[-5.447695%,-2.042782%]`; settlements 4,390 / 585 / 535 / 751 / 4,345. All selected response receipts remain post-kickoff. 2025 and 2026 are negative for both markets. This update does not establish a positive source or model direction.

## 2026-11-06 archive replay checkpoint 13:00

Generated UTC `2026-11-05T22:31:07.291232Z`, report [checkpoint 13:00](results/m5_source_union_replay_live_20261106T130000Z.json). The source-union set now contains AH 10,642 unique fixture-markets (9,987 Crown + 655 TotalCorner default) and OU 10,641 (9,986 + 655). AH `-246.540U / -2.316670%`, max event-time DD `267.195U`, LL/Brier `1.03420430/0.65050596`, bootstrap 95% ROI `[-3.989640%,-0.613559%]`; settlements W/HW/P/HL/L `4267/721/735/737/4182`. OU `-399.8425U / -3.757565%`, DD `414.9625U`, LL/Brier `0.98951189/0.62439968`, interval `[-5.446810%,-2.060521%]`; settlements `4404/587/536/753/4361`. All API receipts post-kickoff; event-time replay only. Both years (2025 and 2026) remain negative by market.

## 2026-11-06 archive replay checkpoint 13:00 UTC label

Latest replay report generated UTC `2026-11-05T22:31:07.291232Z`: [source-union checkpoint](results/m5_source_union_replay_live_20261106T130000Z.json). AH 10,642 unique fixture-markets, 1U each, net `-246.540U` / ROI `-2.316670%`; OU 10,641, net `-399.8425U` / ROI `-3.757565%`. Source splits, settlement categories, proper scores, drawdown, year splits and bootstrap intervals are recorded in the JSON. Crown and TotalCorner remain distinct; every selected historical API response was received after kickoff. Current source sample increase still does not meet +3%.

## Shrunk league calibration research candidate (fixed UTC holdout)

Extended `m5_source_union_goal_rate_temporal_holdout.py` with a league-aware calibration diagnostic. Each league's home/away log-rate correction is partially pooled toward the global prior-period correction using a fixed 100-fixture shrinkage scale; no ROI is used to fit parameters, and there is no league exclusion or market-selection gate. `py_compile` passed and the full private archive replay in the calibration script completed. Report: [shrunk league calibration holdout](results/m5_source_union_league_calibration_holdout_20261106T140000Z.json), generated UTC `2026-11-05T22:36:59.841687Z`. The train period is before 2026-09-01; each holdout has 2,570 disjoint fixture IDs and source composition of 2,295 Crown + 275 TotalCorner default. This holdout was previously inspected and every selected API receipt was post-kickoff.

| Market | Raw ROI | Global calibration ROI | Fixed-shrinkage league calibration ROI | League-calibrated LL / Brier | ROI bootstrap 95% |
|---|---:|---:|---:|---:|---:|
| AH | +0.200875% | +0.046595% | +1.169358% | 1.03464075 / 0.64671316 | -2.271304% to +4.497763% |
| OU | -4.902335% | -4.709339% | -2.870331% | 0.99056481 / 0.62448302 | -6.256323% to +0.588035% |

This candidate improves the point ROI on both markets relative to raw selection but does not reach +3%; both intervals include zero, and AH proper scores worsen slightly relative to raw (LL/Brier 1.03491701/0.64661616). Treat as an exploratory calibration result requiring a fresh future-season test, not evidence of executable profitability. The method and all fitted league coefficients are archived for reproducibility. The latest independent full archive source-union replay at UTC `2026-11-05T22:38:01.235333Z` is [here](results/m5_source_union_replay_live_20261106T143000Z.json): AH n=10,718 ROI -2.255925%; OU n=10,717 ROI -3.683563%. Every API receipt remains post-kickoff.

## M5 baseline vs recency on receipt-verified Crown and deduplicated Crown-source union

Ran the existing cross-source identity audit against MR1 V23 prospectively received Crown snapshots plus the M5 historical TotalCorner Crown-source archive, using the independent M5 baseline and recency score grids. Output: [latest M5 Crown OOS source-union report](results/m5_crown_oos_source_union_latest_20261106.json), generated UTC `2026-11-05T22:50:27.855381Z`. The M5 prediction variants—not MR1 predictions—drive side choice. Both AH and OU are kept separate, one unit per unique fixture-market. Source identity is deduplicated by normalized league, UTC kickoff date and ordered teams. MR1 Crown overlap with TotalCorner: 861; each market has 871 receipt-verified Crown rows plus 8,399 unique event-time-only TotalCorner additions, 9,270 unique union fixtures. This cohort does not reach the 10,000 minimum and the union's TotalCorner additions are retrospective, so only the 871 Crown rows have contemporaneous receipt evidence.

| Market/cohort | Model | n | Net U / ROI | Log Loss / Brier | Max DD | Bootstrap 95% ROI |
|---|---|---:|---:|---:|---:|---:|
| AH MR1 received Crown | baseline | 871 | -17.825 / -2.046498% | 1.03171136 / 0.64617416 | 28.900 | -8.024684% to +3.812859% |
| AH MR1 received Crown | recency | 871 | -16.940 / -1.944891% | 1.03004581 / 0.64562197 | 24.555 | -7.904707% to +3.876005% |
| AH deduplicated union | baseline | 9,270 | -176.680 / -1.905933% | 1.03203240 / 0.64902290 | 199.750 | -3.661758% to -0.140669% |
| AH deduplicated union | recency | 9,270 | -238.970 / -2.577886% | 1.02721575 / 0.64603767 | 258.575 | -4.371791% to -0.794229% |
| OU MR1 received Crown | baseline | 871 | -31.075 / -3.567738% | 1.01610124 / 0.64262006 | 51.600 | -9.452354% to +2.356487% |
| OU MR1 received Crown | recency | 871 | -32.485 / -3.729621% | 1.02220923 / 0.64711209 | 51.505 | -9.738232% to +2.025258% |
| OU deduplicated union | baseline | 9,270 | -306.165 / -3.302751% | 0.98806322 / 0.62346620 | 362.335 | -5.129935% to -1.470550% |
| OU deduplicated union | recency | 9,270 | -298.955 / -3.224973% | 0.98838178 / 0.62392913 | 362.270 | -4.999838% to -1.386192% |

This comparison finds small, inconsistent recency changes: it slightly improves AH on the 871-row Crown tier, worsens AH on the larger retrospective union, slightly improves OU ROI on the union while worsening its proper scores, and worsens OU on the receipt-verified Crown tier. No market reaches +3%. The 2026 outcomes and holdout have been examined repeatedly; this is not a pristine test or prospective M5 execution. `m5_crown_oos_source_union.py` bootstrap was vectorized with NumPy to preserve 10,000 fixture-resamples while eliminating a slow Python-level nested resampling loop; `py_compile` passed and the run completed.

## 2026-11-06 live TotalCorner archive replay (15:30 checkpoint)

Generated UTC `2026-11-05T22:52:44.426654Z`; [machine-readable replay](results/m5_source_union_replay_live_20261106T153000Z.json). Crown-first, per fixture-market deduplicated coverage has AH n=10,880 (9,987 Crown + 893 TotalCorner default), net `-257.190U`, ROI `-2.363879%`, event-time DD `277.845U`, settlement LL/Brier `1.03604863/0.65119720`, bootstrap 95% ROI `[-4.053424%,-0.696714%]`; settlement W/HW/P/HL/L `4352/747/757/751/4273`. OU n=10,879 (9,986 Crown + 893 TotalCorner default), net `-398.480U`, ROI `-3.662837%`, DD `414.8125U`, LL/Brier `0.98990169/0.62459870`, interval `[-5.317400%,-1.976698%]`; settlement `4507/605/546/767/4454`. Every included TotalCorner response receipt followed kickoff. 2025 and 2026 year splits are negative in both markets. This is retrospective source-event replay, not executable performance.

## M5 forward shadow cohort started

Added a private, offline forecast generator and a read-only Crown pairing auditor: `m5_forward_shadow_forecasts.py` fits only the M5 independent goal-rate model to completed fixtures from the frozen private candidate manifest; `m5_forward_shadow_crown_pairing.py` scans MR1's Crown snapshot index/registry but does not consume MR1 predictions, orders, settlement ledger or FT results. It accepts a quote only if `prediction_asof_utc <= quote_event_utc <= quote_received_utc < kickoff_utc`, and verifies normalized fixture identity and kickoff. No API call or production change is made by these scripts. Per-fixture grid, team names, IDs, Crown prices, and snapshot hashes remain in the private archive.

First forecast was generated UTC `2026-11-05T22:56:35.144159Z`; after an API placeholder correction and normalized-identity deduplication, a refreshed fixed cohort was generated UTC `2026-11-05T22:59:49.604793Z`. It contains 361 unique fixture IDs and 361 normalized fixture identities, no conflicts, across upcoming UTC kickoffs `2026-11-06T11:00:00Z` through `2026-11-23T20:00:00Z`. Every M5 training cutoff predates its forecast timestamp, and every forecast timestamp predates kickoff. Public aggregate audit: [forward shadow start](results/m5_forward_shadow_start_20261106.json). The private forecast file is append-immutable by filename and must not be committed.

The first Crown pairing scan found **0** qualified future quotes in either market. The MR1 snapshot index had 551 entries for forecast IDs; 353 entries were not successful snapshots, 195 receipts were outside the forecast-to-kickoff window, and 3 failed fixture/kickoff identity checks. These counts are diagnostic, not proof of missing future Crown access: later snapshots may qualify. Re-run the pairing script against the same private forecast cohort as new MR1 Crown snapshots arrive, then settle only with independent FT outcomes after matches finish. No realized forward ROI is available yet; the M5 objective is not complete.

## 2026-11-06 expanded TotalCorner replay and forward cohort recheck

The index replay generated UTC `2026-11-05T23:03:57.976392Z`: [live replay 16:00 checkpoint](results/m5_source_union_replay_live_20261106T160000Z.json). AH n=11,038 (9,987 Crown + 1,051 TotalCorner default), net `-279.465U`, ROI `-2.531845%`, max event-time DD `301.345U`, settlement LL/Brier `1.03627716/0.65129488`, 95% fixture-bootstrap ROI `[-4.219764%,-0.865193%]`; W/HW/P/HL/L `4410/753/767/763/4345`. OU n=11,038 (9,986 Crown + 1,052 TotalCorner default), net `-393.0425U`, ROI `-3.560813%`, DD `414.8125U`, LL/Brier `0.98998577/0.62468298`, interval `[-5.229140%,-1.877084%]`; settlements `4576/622/551/774/4515`. Every receipt followed kickoff; annual splits are negative in material 2025/2026 cohorts. TotalCorner index at post-run check: 1,081 requests, 1,075 verified, 6 transport errors.

Re-ran the forward Crown pairing auditor on the same fixed M5 forecast cohort after new MR1 index growth. It remains 0 qualified Crown quotes for AH and OU under `forecast_asof <= quote_event <= receipt < kickoff`. Existing index matches are not sufficient if the quote was received before M5 forecast-as-of, the snapshot is non-OK, or fixture identity fails. No prospective ROI is claimed.

## 2026-11-06 M5 forward Crown endpoint audit

Added `m5_forward_shadow_crown_capture.py`, which reads the frozen M5 forecast cohort and uses the existing local TotalCorner Keychain credential to request the explicit `bookmaker=crown` endpoint. The collector rate-limits requests to one every 3.1 seconds, validates fixture/Crown identity, records response receipt time immediately after reading the HTTP body, and stores raw responses, IDs, event rows and prices outside this repository. `m5_forward_shadow_crown_pairing.py --capture-index` pairs M5-only forecasts to that private index without reading MR1 when `--mr1-root` is omitted. The collector and pairing auditor do not touch production paths, Telegram, or user-defined trading rules.

Run generated UTC `2026-11-05T23:41:13.935623Z` for the forecast frozen at `2026-11-05T22:59:49.604793Z`: 361 Crown requests attempted, 355 fixture/Crown responses passed identity validation, 3 were rejected for fixture/kickoff identity mismatch, and 3 had transport errors. Among verified responses, 199 fixtures per market had at least one syntactically valid pregame event row, but all such rows predated the frozen forecast as-of: AH 626 event rows, OU 529. Qualifying post-as-of, pre-kickoff Crown fixture-markets were **0 AH / 0 OU**. This is real endpoint access and private data capture, not qualifying OOS odds, EV, or ROI. Do not count these retrospective movement rows as M5 forward results. Sanitized aggregate receipt: [M5 Crown capture audit](results/m5_forward_shadow_crown_capture_20261106.json); forecast and response-set SHA-256 values are in that artifact. No GitHub Actions run was involved in this one-off local execution.

Verification: the new two-test unit suite passed, covering the quote time/open-market boundary and pairing receipt-time boundary; all three changed Python modules passed `py_compile`; `git diff --check` passed. The remaining research action is to run a scheduled M5-only Crown snapshot collector across future intervals, retain actual event and receipt timestamps, then evaluate only after forecasts are frozen and FT outcomes arrive. This capture run itself did not add future learning information and the +3% objective remains unmet.

### 2026-11-06 M5 event-time replay refresh and M1 Crown archive audit

The latest full source-union replay is [`m5_source_union_replay_live_20261106T000200Z.json`](results/m5_source_union_replay_live_20261106T000200Z.json), generated `2026-11-06T00:03:37.125312Z`. It contains 11,071 AH and 11,071 OU unique fixture-markets (AH Crown 9,987 + TotalCorner-default 1,084; OU Crown 9,986 + TotalCorner-default 1,085). At 1U per fixture-market, AH returned -2.539766% (net -281.1775U; LL/Brier 1.03632539/0.65135857; max event-time drawdown 303.8325U); OU returned -3.541505% (-392.08U; 0.98966445/0.62450794; drawdown 414.8125U). The resampled ROI intervals are wholly negative for both markets. All included API response receipts were after kickoff, so these are historical quote-event replays, not pregame received Crown ROI. No market meets +3%.

The fixed `2026-09-01T00:00:00Z` temporal calibration receipt [`m5_source_union_goal_rate_temporal_holdout_20261106T000600Z.json`](results/m5_source_union_goal_rate_temporal_holdout_20261106T000600Z.json) was generated `2026-11-06T00:08:51.266935Z`. It has 8,501 training and 2,570 disjoint holdout fixture-markets per market; the holdout includes 2,295 Crown and 275 TotalCorner-default rows. Training outcomes alone fit global and score-grid likelihood calibration; holdout ROI did not choose parameters. Raw/global-calibrated/shrunk-league ROI is AH `+0.200875%/-0.195428%/+0.920136%`, OU `-4.902335%/-4.658949%/-2.755739%`. All intervals include zero except calibrated OU, whose upper endpoint is still below zero. Proper scores do not establish positive returns; all source response receipts postdate kickoff.

M1's pre-existing Crown OU history was separately rejoined to M5 baseline and recency forecasts in [`m5_m1_ou_crown_eventtime_refresh_20261106T001000Z.json`](results/m5_m1_ou_crown_eventtime_refresh_20261106T001000Z.json), generated `2026-11-06T00:11:25.788167Z`. Of 1,705 observations, 1,397 exact M5 IDs were joined; 1,032 unique OU fixture-markets passed identity, timestamp, and independent FT checks, with strict order `M5 train_end < M5 forecast_asof <= Crown event < kickoff`. Baseline ROI was -2.138081%; recency ROI -1.971415%. The source archive explicitly says it was fetched later; these are event-time retrospective comparisons, not receipt-verified quotes. A same-fixture audit found 1,021 rows overlap M5's existing Crown sample, 11 additional M1-only fixture-markets, and zero overlap with the TotalCorner-default fallback. Of the 1,021 Crown overlaps, 7 had matching event timestamps, 560 matching lines, and 28 matching two-sided prices. This archive therefore cannot materially expand the unique M5 sample and remains separately labeled.

The current M5 forward-shadow Crown cohort remains the earlier frozen forecast set, with 0 qualifying forecast-to-receipt-to-kickoff Crown fixture-markets. The paired-source capture was not started in this refresh. There is still no M5 Actions workflow validation for this collector, no receipt-verified forward ROI, and no +3% result. Raw quote rows, match IDs, and prices remain in the private archive.


### 2026-11-06 genuine forward Crown capture

A fresh M5-only forecast cohort was generated at `2026-11-06T00:17:24.085673Z`: 361 unique scheduled fixtures, 51 leagues, zero identity conflicts, and prior-result training cutoffs before forecast time. The private forecast SHA is recorded in the sanitized [capture receipt](results/m5_forward_shadow_capture_20261106T001724Z.json). Crown's bookmaker-specific endpoint was queried after forecast generation, with actual API receive timestamps retained privately. Of 361 requests, 357 responses passed fixture/Crown identity checks, three failed identity/Crown validation, and one had a transport error.

The final strict pairing audit at `2026-11-06T00:48:45.750648Z` found zero AH and zero OU usable fixture-markets under `prediction_asof_utc <= quote_event_utc <= quote_received_utc < kickoff_utc`. This is not evidence of zero live Crown prices everywhere: it means no returned movement row in this capture passed the documented event-time condition. No EV or ROI is estimable, and no TotalCorner-default comparison was collected for this forward cohort. The API response receipt by itself was not promoted to a quote event. These outcomes are kept distinct from the 11,071-market retrospective event-time replay above. The collector run was local; it did not run through GitHub Actions.


### 2026-11-06 same-quote baseline vs recency replay

为恢复 M5 数据源并检验模型改进，在完全相同的 11,035 个唯一 fixture-market 上分别重放 M5 baseline 与 2025/2026 recency walk-forward forecasts。预测 ID 与赛程、比分逐项核验一致；两套预测各自满足 `train_end < prediction_asof < kickoff`。同一 Crown-first / TotalCorner-default（仅当 Crown 市场报价缺失时补位）盘口、1U 每场和亚洲盘结算规则用于两模型。公共回执：[baseline matched sample](results/m5_source_union_baseline_matched_20261106T005454Z.json)、[recency model](results/m5_source_union_recency_replay_20261106T005234Z.json)。样本包括 2025 年 874 场与 2026 年 10,161 场；每场按市场去重。

| Market / model | Unique, simulated, settled | Crown / TotalCorner-default | W/HW/P/HL/L | Net U | ROI | Max DD U | Settlement LL / Brier | 95% fixture bootstrap ROI |
|---|---:|---:|---|---:|---:|---:|---|---|
| AH baseline | 11,035 | 9,987 / 1,048 | 4,410/752/766/762/4,345 | -279.490 | -2.532759% | 301.345 | 1.03621020 / 0.65125357 | -4.200997% to -0.854667% |
| AH recency | 11,035 | 9,987 / 1,048 | 4,380/752/766/762/4,375 | -336.835 | -3.052424% | 344.9925 | 1.03091615 / 0.64778398 | -4.721749% to -1.363095% |
| OU baseline | 11,035 | 9,986 / 1,049 | 4,575/622/550/774/4,514 | -393.1425 | -3.562687% | 414.8125 | 0.99000926 / 0.62469853 | -5.216810% to -1.889941% |
| OU recency | 11,035 | 9,986 / 1,049 | 4,568/659/551/737/4,521 | -377.7975 | -3.423629% | 418.450 | 0.99046806 / 0.62531568 | -5.074422% to -1.798369% |

Recency improves AH proper scores but worsens AH ROI by 0.519665 percentage points. OU recency improves ROI by 0.139058 points while slightly worsening both proper scores. Neither model reaches +3%. Crown source-only and TotalCorner-default subgroups are also negative in both markets and both models. The bootstrap intervals are wholly negative. This is still a retrospective source-event-time replay: all 11,035 selected historical API receipts per market occurred after kickoff. It does not establish executable ROI.

Added `--forecast-path` and `--side-policy` to the aggregate replay so alternate M5 OOS forecasts can be reproduced without copying private fixture rows into the repository. The default `higher_ev` policy retains the existing side-selection method. A fixed `lower_ev` direction diagnostic on the same matched sample returned AH -4.167127% and OU -3.982125%; it also fails, with no filters or gates. See [`m5_source_union_baseline_lower_ev_20261106T005735Z.json`](results/m5_source_union_baseline_lower_ev_20261106T005735Z.json).

The `/private/tmp/m1-m5-private` directory was rechecked and still contains only the M1 observation/FT files, not an M5 forecast archive. The M5 historical archive is the existing `/Users/mac/QuantAsiaDesk/data/m5-crown-authorized` dataset. Its Crown capture and TotalCorner-default fallback checkpoints are terminal; the M5 source-union history already exceeds 10,000 unique fixture-markets per market when separately labeled sources are deduplicated. Receipt-time evidence remains post-kickoff. No new TotalCorner historical requests were needed for this same-source model comparison.

## 2026-11-06: 2025-fitted settlement-temperature calibration (2026 holdout)

Added a market-specific power-temperature calibration over the five Asian settlement categories. It selects the side using the raw M5 expected-return forecast, then fits temperature on 2025 settlement-category log loss only; it does not optimize ROI. Training used 874 unique fixtures per market (AH Crown 727 + TotalCorner default 147; OU Crown 726 + default 148). Temperatures: AH 3.9999998743 (at the search upper bound, a stability concern), OU 2.6518026983. Training settlement log loss changed AH 1.04850539→0.99545749 and OU 0.99577203→0.97798339.

The untouched 2026 UTC kickoff-year replay contains 10,161 unique fixtures per market (Crown 9,260 + TotalCorner default 901), from 2026-01-01 through 2026-11-04. AH ROI is -3.845635% (-390.755U), settlement LL/Brier 0.99674875/0.62373094 and event-time drawdown 399.455U. OU ROI is -3.785159% (-384.610U), LL/Brier 0.97630762/0.61373902 and event-time drawdown 436.405U. Fixture bootstrap 95% ROI intervals are [-5.580358%, -2.109118%] AH and [-5.540572%, -2.055728%] OU. The proper scores improve versus the uncalibrated forecasts, but ROI worsens; neither market meets the +3% target.

Temporal evidence remains limiting: all 10,161 selected historical API receipts per market were received after kickoff. This is a retrospective event-time replay only, not proof of pregame receipt, execution, or realizable Crown ROI. TotalCorner is separately marked and fills only absent Crown fixture-market entries. Reports: [2025 fit](results/m5_market_settlement_temperature_2025_train.json) and [2025-fit/2026-holdout replay](results/m5_source_union_market_temperature_2025fit_2026_oos.json). The fit used 2025 outcomes; the 2026 period was not used for parameter fitting. M5 remains independent; no production strategy, Telegram, model promotion, or trade gates changed.
# Cross-model replay on the expanded match archive (2026-11-06)

The 11,573-per-market source-union archive was joined against saved forecasts from M1, MR1 V6, and the three M3 models. This is a coverage audit and replay, not a claim that every model was retrained or forecast all 11,573 matches. Aggregate results and input hashes are recorded in [cross-model comparison](results/m5_expanded_cross_model_comparison_20261106.json); sanitized model receipts are [M1](results/m5_m1_expanded_archive_replay_20261106.json) and [M3 Crown exact-contract replay](results/m5_m3_expanded_crown_exact_20261106.json).

| Model output | AH sample and result | OU sample and result | Evidence boundary |
| --- | --- | --- | --- |
| M1 saved scan output | 1,233; -6.1444% ROI | 1,233; -3.2729% ROI | Latest saved pre-kickoff Crown scan per fixture; scan archive completion also precedes kickoff. Full output includes statuses outside M1's formal decision window. Existing formal-candidate subset: AH 42, -12.2857%; OU 79, +5.5000%. |
| MR1 V6 | 870; -3.6695% ROI | 870; -4.7391% ROI | Exact shared pre-kickoff Crown quotes and FT results; compared on the same 870 fixtures with M5 baseline and recency models. |
| M3 Poisson / Dixon-Coles / Bivariate Poisson | AH0: 5, each +2.8% event-time ROI | OU2.5: 2, each -100% event-time ROI | Too few exact Crown contracts for an ROI conclusion. Separate strict common OOS proper scores cover 7,663 fixtures without Crown prices. |
| M4 research variants | Not run on expanded cohort | Not run on expanded cohort | No standalone frozen M4 forecast file exists. Existing MR1-based experiments are separate 497-order studies and are not an M4-vs-other-model comparison on this archive. |

All historical Crown and TotalCorner responses in the expanded capture were received after kickoff. M1's saved scan quote/decision timestamps and MR1's saved forward quote receipts are pre-kickoff, but M1/MR1 do not cover the entire expanded fixture set. The M3 Crown contracts use source event times after each model's training cutoff and before kickoff, while the API response receipts were post-kickoff. These ROI figures are retrospective model diagnostics, not executable historical Crown ROI. No M1, MR1, M3, or M4 production path changed; no Telegram messages, new gates, or automatic model promotions were added.

### Direct rerun requested for the expanded match archive (2026-11-06 10:43Z)

The three original penaltyblog implementations were independently re-fitted and run again against the frozen 51-league result archive and the selected Crown-first/TotalCorner-default prices. The run used strict UTC-year-forward training and excluded target fixtures from training. There were 10,568 complete, shared M3 forecast fixtures out of 11,573 quoted fixture-markets per market; 969 rows lacked teams known to the earlier-year training fold and 36 had no prior training rows. This was a real rerun, not just a replay of the previous report. The sanitized run receipt is [M3 three-model rerun](results/m5_three_penaltyblog_expanded_oos_20261106_rerun.json); fixture-level grids remain in the private M5 archive.

| M3 model | AH n=10,568 ROI | OU n=10,568 ROI | AH / OU Crown; TotalCorner default |
| --- | ---: | ---: | --- |
| Poisson | -3.0304% | -3.6846% | 9,613 / 9,612; 955 / 956 |
| Dixon–Coles | -3.1281% | -3.6185% | 9,613 / 9,612; 955 / 956 |
| Bivariate Poisson | -3.0012% | -3.5946% | 9,613 / 9,612; 955 / 956 |

All three M3 models remain below the +3% objective in both markets. Every historical provider response receipt was post-kickoff, so these are retrospective event-time results and not executable ROI. The M1 values in the crosswalk remain saved-output coverage (1,233 per market), MR1 V6 remains an exact pre-kickoff shared Crown cohort (870 per market), and M4 remains a historical MR1-based Pass study rather than a standalone predictor. They cannot honestly be presented as four models retrained over all 11,573 fixtures. The M4 artifact is [`research/m4/M4_MR1_TWO_LEAGUE_PASS_RESULT_20261103.json`](../m4/M4_MR1_TWO_LEAGUE_PASS_RESULT_20261103.json): 497 historical MR1 orders/344 unique matches and a selected post-cutoff 149-order pass subset; no M4 model probabilities exist for the expanded archive.

## 2026-11-06 refreshed comparison on the collected archive

Following the clarification that the models should be evaluated against the newly collected 11,573 fixture-markets, the latest strict M3 OOS artifact was joined again and replayed separately by Poisson, Dixon–Coles, and Bivariate Poisson. The source union contains 11,573 unique fixture-markets per side: AH has 10,433 Crown + 1,140 TotalCorner default; OU has 10,432 Crown + 1,141 TotalCorner default. Each selected historical provider response was actually received after kickoff.

The complete sanitized crosswalk is [refreshed cross-model comparison](results/m5_expanded_cross_model_comparison_20261106_refreshed.json). M3's current strict season-forward file has 14,807 predictions per model over 17,152 six-league test matches. Its full strict OOS probability scores are:

| M3 model | AH 1X2 proxy LL / Brier | OU 2.5 LL / Brier |
| --- | --- | --- |
| Poisson | 1.003886 / 0.599398 | 0.686555 / 0.246554 |
| Dixon–Coles | 1.003791 / 0.599230 | 0.686577 / 0.246564 |
| Bivariate Poisson | 1.003779 / 0.599253 | 0.686578 / 0.246577 |

These scores are on M3's Football-Data.co.uk OOS cohort, not the entire expanded M5 price archive. In the expanded archive, a same-quote M3/M5 comparison additionally required an M5 prediction-as-of time, a valid M3 training cutoff, and an exact AH0 or OU2.5 contract. This leaves 179 AH and 348 OU fixture-markets; Crown supplies all 179 AH and 346 OU, with TotalCorner default filling 2 OU contracts. The same quote is applied to each model, one unit per fixture-market, with no EV threshold:

| Model | AH n=179 ROI | OU n=348 ROI |
| --- | ---: | ---: |
| M3 Poisson | +1.2793% | -6.0460% |
| M3 Dixon–Coles | +2.2570% | -6.0460% |
| M3 Bivariate Poisson | +2.2570% | -4.5115% |
| M5 recency | +0.0168% | -3.4052% |
| M3/M5 blend (weights fit on 2025 proper-score log loss) | +0.0168% | -4.3707% |

The blend used 541 common 2025 fixtures to fit weights and an untouched set of 518 common 2026 fixtures for proper-score holdout evaluation; the exact-contract quote subset is smaller. The blend did not improve the AH point ROI over the best M3 single models; in OU it improved log loss slightly versus M5 recency but had lower ROI. All historical Crown/TotalCorner receipts for these exact-contract matches were post-kickoff, and all fixture-bootstrap intervals are wide and cross zero.

| Other model evidence | AH | OU | Cohort boundary |
| --- | ---: | ---: | --- |
| M1 saved scan outputs | n=1,233, -6.1444% | n=1,233, -3.2729% | Existing saved forecasts only; formal-candidate subset is AH n=42, -12.2857%, OU n=79, +5.5000%. |
| MR1 V6 saved selections | n=870, -3.6695% | n=870, -4.7391% | Same pre-kickoff Crown prices and FT within MR1/M5; not a full archive replay. |
| M4 | No standalone result | No standalone result | No uniquely versioned M4 predictor/forecast file exists; M4 research variants are MR1-based. |

On the full expanded M5 source union, the baseline remains AH n=11,573 at -2.5099% and OU n=11,573 at -3.6339%. The 2025-fit/2026-forward recency run is AH n=11,537 at -2.9488% and OU n=11,537 at -3.4401%. Crown-only baseline is AH -2.3666% / OU -3.6461%; TotalCorner-default-only is AH -3.9056% / OU -3.5221%. The source-specific cohorts and input hashes are in [source policy comparison](results/m5_source_policy_comparison_20261106.json). No model-market reaches +3% on the 10,000+ source-union cohort. These full-cohort event-time replays cannot establish executable ROI because every historical receipt followed kickoff.

Artifacts: [M3 Crown-first/TotalCorner exact-contract replay](results/m5_m3_expanded_source_union_contract_replay_20261106.json), [M3/M5 common 2026 source-archive replay](results/m5_m3_m5_blend_source_union_replay_20261106.json), and [2025-fit/2026-holdout blend fit](results/m5_recency_m3_walkforward_blend_2025fit_2026test_refreshed_20261106.json). M1, MR1, M3, and M4 do not have compatible saved forecasts across all 11,573 fixture-markets; their sample sizes above must not be ranked as if they were one shared cohort. No formal strategy, production model, Telegram route, or trade gate changed.


## 2026-11-06 07:01Z 新 M5 前瞻 Crown / TotalCorner 配对队列

以现有 361 场未来赛程和 M5 独立 goal-rate Poisson 网格生成新 cohort，预测 as-of 为 `2026-11-06T07:01:42.001976Z`，forecast SHA-256 为 `80dc6581fefa190cddeaa95ba75a9210e647ea5996456e9c1d08a64aaffb91b7`；51 个联赛有训练记录，身份冲突 0。先查 Crown 专属接口，随后只在 Crown 没有本次预测后、赛前实际接收报价的 fixture-market 上调用 TotalCorner default。

| 市场 | 唯一配对 fixture-market | Crown | TotalCorner default | 模拟 1U | 已结算 | 待赛 | 净收益 / ROI | 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| AH | 17 | 1 | 16 | 17 | 0 | 17 | 未结算 / null | null |
| OU | 11 | 1 | 10 | 11 | 0 | 11 | 未结算 / null | null |

所有配对均校验 `train_end_utc < prediction_asof_utc <= quote_event_utc <= quote_received_utc < kickoff_utc`，每个 fixture-market 最多一行。单注选择按 M5 在实际盘口线与双方赔率的预期收益较高方向，不加 EV 或置信度条件。赛事 kickoff 覆盖 `2026-11-06T15:00Z` 至 `2026-11-08T18:00Z`；生成本回执时全部未赛，不能报告收益。这个队列与 11k+ 历史 event-time 回放完全分开，AH/OU 均远未达到每市场 10,000 场要求。

Crown 采集 361 次，357 条身份验证成功、3 条身份/盘口源错配、1 条传输错误；其中合格报价 AH/OU 各 1。TotalCorner default 采集 361 次，356 条身份验证成功、3 条错配、2 条传输错误；对 Crown 已覆盖的各 1 个市场跳过，补出 AH 16 / OU 10 个合格市场。另有 5 个比赛没有可验证的 TotalCorner response。详细哈希和审计计数见[脱敏前瞻采集回执](results/m5_forward_shadow_capture_20261106T0701Z.json)；逐场预测、身份、line、赔率、grid 与 raw API response 继续留在仓库外私有目录。

本批通过实时 TotalCorner authorized path 真实采集并配对，但样本规模过小且未结算，不能支持 ROI≥3% 结论。M5 历史 11,573/market event-time baseline 仍是回顾性研究，AH -2.51%、OU -3.63%，所有响应均赛后取得。两者均不可混作可执行收益或拼成 10,000 场样本。

## 2026-11-06 M3 三种 penaltyblog 模型重跑 M5 11k 历史盘口样本

按用户要求，将 Poisson、Dixon–Coles、Bivariate Poisson 三个 M3 所用的 penaltyblog 原版实现，独立应用到刚采集的 M5 Crown-first / TotalCorner-default 历史归档。候选训练/赛果清单有 127,674 场；每个市场的去重盘口归档有 11,573 个 fixture-market。模型训练使用同一冻结 51 联赛赛果输入，按 UTC 年逐联赛前推：目标年只用该联赛目标年前的赛果拟合，拟合截止早于 1 月 1 日 UTC，目标 fixture ID 不进训练集。训练与预测时间检查通过。三模型都能生成完整预测的共同盘口配对样本为 10,568 场/市场；另外 969 场因目标队伍在训练历史中未出现，36 场没有更早赛季的训练数据，未伪造预测或结果。

三模型在完全相同的 10,568 场/市场上各自每场模拟 1U，按对应实际 AH / OU 盘口线和两侧价格选择预期收益较高的一侧；不设 EV 门槛。AH 赔率来源为 Crown 9,613、TotalCorner default 955；OU 为 Crown 9,612、TotalCorner default 956。全体配对报价的 API 回执均在开赛后取得，故 ROI 是严格按模型样本外预测和盘口事件时间进行的回顾性回放，不能作为可执行实战收益。

| 市场 | 模型 | 有预测且盘口可结算 | W / HW / P / HL / L | 净 U / ROI | 最大回撤 U | 结算类别 Log Loss / Brier | ROI bootstrap 95% |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| AH | Poisson | 10,568 | 4,190 / 745 / 722 / 706 / 4,205 | -320.2475 / -3.030351% | 347.2425 | 1.036984 / 0.649529 | -4.738% 至 -1.404% |
| AH | Dixon–Coles | 10,568 | 4,181 / 753 / 722 / 698 / 4,214 | -330.5775 / -3.128099% | 352.6125 | 1.037381 / 0.649771 | -4.818% 至 -1.458% |
| AH | Bivariate Poisson | 10,568 | 4,191 / 748 / 722 / 703 / 4,204 | -317.1625 / -3.001159% | 341.2225 | 1.039158 / 0.650563 | -4.710% 至 -1.340% |
| OU | Poisson | 10,568 | 4,394 / 570 / 526 / 745 / 4,333 | -389.3925 / -3.684638% | 407.3575 | 0.988362 / 0.623672 | -5.368% 至 -1.933% |
| OU | Dixon–Coles | 10,568 | 4,398 / 569 / 526 / 746 / 4,329 | -382.4025 / -3.618495% | 400.3675 | 0.988471 / 0.623694 | -5.355% 至 -1.907% |
| OU | Bivariate Poisson | 10,568 | 4,394 / 580 / 526 / 735 / 4,333 | -379.8825 / -3.594649% | 393.8275 | 0.988429 / 0.623760 | -5.298% 至 -1.882% |

此轮在 AH 上 Bivariate Poisson ROI 点估计最高，但仍为 -3.00%；OU 上 Bivariate Poisson ROI 点估计最高，为 -3.59%。Log Loss / Brier 的领先模型不完全一致，且所有 ROI bootstrap 区间均低于 0。没有一个模型在 10,000+ 场样本上达到 +3%。报告 [脱敏聚合回执](results/m5_three_penaltyblog_expanded_oos_20261106.json) 含逐年训练折、模型覆盖、结算、来源拆分和输入指纹；[重跑脚本](m5_three_penaltyblog_expanded_oos.py) 可复现。逐场模型网格、身份、赔率和原始响应均保留在本机权限 0600 的私有归档，不提交 GitHub。该实验在 M5 研究范围应用三个 penaltyblog 实现，不替换 M3 现有范围、模型或生产工作流。

逐年及盘口来源分组均基于同一模型完整预测子集（每市场2025年1,168场、2026年9,400场），不是独立重采样；所有分组计数、净U与ROI可在上述JSON逐模型核验。每个模型在2025、2026两个测试年均为负；Crown 与 TotalCorner default 子组也都为负：

| 市场 | 模型 | 2025 ROI | 2026 ROI | Crown ROI | TotalCorner default ROI |
| --- | --- | ---: | ---: | ---: | ---: |
| AH | Poisson | -8.982663% | -2.290745% | -3.051181% | -2.820681% |
| AH | Dixon–Coles | -8.830265% | -2.419574% | -3.089202% | -3.519634% |
| AH | Bivariate Poisson | -9.163313% | -2.235479% | -3.018829% | -2.823298% |
| OU | Poisson | -5.280608% | -3.486330% | -3.706877% | -3.461036% |
| OU | Dixon–Coles | -5.379923% | -3.399628% | -3.604245% | -3.761768% |
| OU | Bivariate Poisson | -5.253211% | -3.388564% | -3.533292% | -4.211559% |

## 2025 概率评分选模型 → 2026 留出验证

为检查 M3 三模型之间是否有可利用的互补优势，另做固定方法的时间前推研究：AH、OU 分开处理，按联赛在 2025 OOS 结算概率 Log Loss 选模型；对 2026 所有可完整预测且有源盘口的比赛应用选择，不过滤联赛、不加投注门槛。该规则未使用 2026 的比赛结果，所有比较使用同一 9,400 场 2026 fixture-market holdout；2025 选择样本每市场1,168场。

| 市场 | 2025训练选择 | 2026模型选择结果 | 2026固定最佳单模型 | 比较 |
| --- | --- | ---: | ---: | --- |
| AH | 按联赛 Log Loss；无2025行时用全局 Poisson（29联赛选Poisson、17选Dixon–Coles、5选Bivariate） | n=9,400；-216.52U / -2.303404%；DD 241.885U | Bivariate Poisson：-2.235479% | 选择器略差，未改善 |
| OU | 按联赛 Log Loss；无2025行时用全局 Bivariate（26联赛选Bivariate、18选Dixon–Coles、7选Poisson） | n=9,400；-290.63U / -3.091809%；DD 347.3975U | Bivariate Poisson：-3.388564% | 改善约0.297个百分点，仍亏损 |

AH 结算 W/HW/P/HL/L 为 3,742/687/644/623/3,704，结算类别 Log Loss/Brier 为 1.036882/0.648903；OU 为 3,931/509/475/661/3,824，Log Loss/Brier 为 0.987924/0.623317。两个市场来源均为 Crown 8,607、TotalCorner default 793；本归档的历史 API 回执均晚于开赛，仍是 event-time retrospective 结果。虽然 OU 有样本外改善，但留出样本只有9,400场，且ROI仍为负；因此不满足10,000场与ROI≥3%的M5目标，也不据此改正式模型。完整脱敏回执见[2025选择 / 2026留出报告](results/m5_penaltyblog_2025_logloss_selector_2026_holdout_20261106.json)；复现工具为[m5_penaltyblog_prior_year_selector.py](m5_penaltyblog_prior_year_selector.py)。

## M3 选择器 vs M5 模型：完全相同的 2026 报价样本

把 2025 按联赛 Log Loss 选出的 M3 模型、三个固定 M3 模型、M5 baseline 与 M5 recency 放在同一组 2026 完整预测样本、相同 Crown-first / TotalCorner-default 盘口、相同 AH/OU盘口线及两侧赔率上重放。M5 forecast ID、队伍、比赛时间和比分均与 M3 fixture 精确匹配；M5 的 `train_end < prediction_asof < source quote event < kickoff` 逐场校验通过。

| 市场 | M3 2025选择器 | M3 Poisson | M3 Dixon–Coles | M3 Bivariate | M5 baseline | M5 recency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AH ROI | -2.303404% | -2.290745% | -2.419574% | -2.235479% | **-1.701330%** | -2.701090% |
| OU ROI | **-3.091809%** | -3.486330% | -3.399628% | -3.388564% | -3.327739% | -3.330160% |

每个模型每市场均为同样的9,400注；两市场来源都是 Crown 8,607 + TotalCorner default 793。M5 baseline 是该 holdout 上 AH 点 ROI 最好，M3 选择器是 OU 点 ROI 最好；两者仍分别为 -1.70% 和 -3.09%。M5 recency 的概率评分较好但收益弱于 M5 baseline，说明在此子样本上概率分数与结算收益排序不完全一致。所有 M5 / M3 历史 API receipt 均赛后，且 holdout 低于 10,000 场，不能作为目标验收或可执行 ROI。详细结算、最大回撤、概率评分与哈希见[同价同场对比回执](results/m5_m3_selector_same_quote_m5_comparison_20261106.json)；重放代码为[m5_m3_selector_same_quote_m5_comparison.py](m5_m3_selector_same_quote_m5_comparison.py)。

## M3 选择器结算概率校准：2025拟合 / 2026留出

在上面的 M3 逐联赛选择器基础上，仅用2025结算 Log Loss 从温度 `0.50` 至 `2.00`、步长 `0.01` 选择全局市场温度；2026原样留作holdout，依旧每个fixture-market下注1U并按校准后预期收益较高的一侧选边，不设EV门槛。两市场选中的温度都是搜索区间上界 `2.00`，因此该参数需要未来独立时间样本复验。

| 市场 | 样本 | 2025拟合温度 | 2026未校准 ROI / LL / Brier | 2026校准 ROI / 净U / DD / LL / Brier | 结果 |
| --- | ---: | ---: | --- | --- | --- |
| AH | 1,168拟合；9,400留出 | 2.00 | -2.303404% / 1.036882 / 0.648903 | -2.140798% / -201.235U / 232.7025U / 1.002394 / 0.627491 | ROI改善0.163个百分点，仍亏损 |
| OU | 1,168拟合；9,400留出 | 2.00 | -3.091809% / 0.987924 / 0.623317 | -3.496862% / -328.705U / 364.515U / 0.974358 / 0.612994 | 概率分数改善，但ROI恶化0.405个百分点 |

AH校准后W/HW/P/HL/L为3,591/981/644/329/3,855；OU为3,693/919/475/251/4,062。来源仍是Crown 8,607 + TotalCorner default 793，历史receipt皆赛后。概率 Log Loss / Brier 两市场都有改善，但收益没有同步改善；AH/OU ROI仍未达到+3%，2026留出也低于10,000场，不能视为M5验收。报告[温度校准回执](results/m5_m3_selector_settlement_calibration_2025fit_2026holdout_20261106.json)；工具[m5_m3_selector_settlement_calibration.py](m5_m3_selector_settlement_calibration.py)。

## 2026-11-06 10:01Z 同一前瞻队列的 Crown 报价刷新

对 07:01Z 冻结的 361 场 M5 预测队列继续采集 Crown 报价，并与原先 TotalCorner default 回退响应重新按 fixture-market 配对。新增 127 条经身份校验的 Crown 响应，响应哈希集合为 `f89dcd24ef34ad923d4ae262185172584121c0c4a9614505b1fa65f84ab485d3`。最新配对从 AH 17、OU 11 提升到 AH 41、OU 30：AH Crown 34、TotalCorner default 7；OU Crown 24、TotalCorner default 6。每场/市场去重，Crown 优先，TOTAL 只填 Crown 没有合格报价的市场。

所有配对继续满足 `train_end_utc < prediction_asof_utc <= quote_event_utc <= quote_received_utc < kickoff_utc`；独立核验没有重复 fixture-market 或时间顺序错误。报告生成时 71 个市场项全部未开赛/未结算，因此净收益、ROI、最大回撤均为 null。该真实前瞻队列仍远小于每市场 10,000 场；历史 11k+ 回测与本前瞻队列没有混合。脱敏回执：[前瞻刷新聚合报告](results/m5_forward_shadow_refresh_20261106T1001Z.json)，配对哈希 `3f78e9692cda76c869b7c15a75c83c810a49703276319c0e752e9eb4cf2e52bd`。逐场预测、赔率、赛事身份和原始响应仍留在本机私有授权归档，没有发布凭证或逐场资料。

本轮 M5 全量单元测试 42/42 通过。刷新结果提交 `12df5b2904789b6686746f0822310d551e0b6d62` 与交接更新 `6bd977909bb72533a6db8b12b8cfb369e6c1d94e` 分别出现既有 `.github/workflows/m3-ah-reverse-research.yml` runs [42200117028](https://github.com/ljm198964-alt/quant-runner/actions/runs/42200117028) 和 [42200250710](https://github.com/ljm198964-alt/quant-runner/actions/runs/42200250710)，均为 `failure` 且 `jobs=[]`；它们不是 M5 runs，也没有执行 M5 研究验收。仓库仍无 M5 Actions workflow。本次没有改动 M1/MR1/M3/M4 生产策略、订单、TG、账本或 Gate。

## 2026-11-06 10:14Z 同一前瞻队列的再次 Crown 刷新

对前一版已有报价的 47 个唯一 fixture 再调用 Crown 专属盘口接口：47 次尝试、46 条身份验证成功、1 次传输错误。随后从同一 07:01Z 冻结预测重新配对，AH 仍为 41 场（Crown 34、TotalCorner default 7），OU 增至 31 场（Crown 25、TotalCorner default 6）。71 个已有配对中有4个市场项的盘口条款/事件时间更新；另增加1个OU报价；模型按更新赔率选择的下注方向没有变化。

截至 `2026-11-06T10:14:11Z`，72个 fixture-market 全部待赛，ROI、净收益和最大回撤为 null。时间、来源优先级与去重检查均通过。脱敏回执：[10:14Z前瞻刷新汇总](results/m5_forward_shadow_refresh_20261106T1014Z.json)。预测、赛事身份、盘口价格和原始响应继续保存在本机私有归档；该样本不与历史赛后回取数据混合，也不能证明正收益。

该结果已以提交 `503de2693e75eed2ab305a961e6176837a79916a` 推送。对应 Actions run [42201498776](https://github.com/ljm198964-alt/quant-runner/actions/runs/42201498776) 是旧 M3-only workflow，`failure` 且 `jobs=[]`，不代表 M5 工作流验收。

## 2026-11-06 M5 按盘口线收缩校准：2025拟合 / 2026留出

为检验不同 AH/OU 盘口线的结算概率是否有系统性偏差，新增研究脚本对每场保留一注、不增加任何盘口线筛选。先在 2025 OOS 样本中按原始 M5 expected-return 选边，拟合每个市场的全局结算温度；再对各 quarter-line 拟合收缩至该市场全局温度的线条件温度，收缩强度固定为25。2026全部可配对样本保留为时间留出，不用于温度拟合。训练段各市场 n=1,311；留出 AH、OU 各 n=10,226，来源均为 Crown 9,316 + TotalCorner default 910。26个AH与13个OU训练盘口线组可拟合；留出新线沿用全局温度，不排除比赛。

| 市场 | 方法 | 2025拟合段 ROI（重代入诊断） | 2026留出 ROI / 净U | 2026留出 Log Loss / Brier | 2026最大回撤 U |
|---|---|---:|---:|---:|---:|
| AH | 未校准 | -7.504958% | **-1.861823% / -190.390** | 1.03493458 / 0.65024630 | 215.6125 |
| AH | 全局温度 4.00 | -3.274600% | -3.982007% / -407.200 | 0.99649463 / 0.62370516 | 415.9000 |
| AH | 盘口线收缩温度 | -3.412662% | -4.036182% / -412.740 | **0.99637882 / 0.62362415** | 421.4400 |
| OU | 未校准 | -4.868802% | **-3.498778% / -357.785** | 0.98906036 / 0.62401208 | 420.2025 |
| OU | 全局温度 2.231659 | -6.896644% | -3.679445% / -376.260 | 0.97555550 / 0.61341294 | 418.6850 |
| OU | 盘口线收缩温度 | -6.553013% | -3.967803% / -405.7475 | **0.97537326 / 0.61327349** | 444.9525 |

本实验显示校准改善 proper score 并未带来收益改善：相较全局校准，线条件校准的 2026 Log Loss/Brier 仅小幅改善，但 ROI 在 AH、OU 都更差；相较未校准，高温校准在两个市场均显著恶化 ROI。AH 全局温度落在搜索上界附近，需视为参数不稳定。2026留出上无任何方法达到 +3%，该候选不进入 M5 生产或任何交易规则。

所有 20,452 个 2026 市场回执都在开赛后取得；报价事件时间位于模型 as-of 与开赛之间，因此这是严格 OOS 的 event-time 回顾性 ROI，不是可执行收益。结算类别、来源/时间审计、训练重代入与留出回执见[脱敏校准结果](results/m5_line_conditional_settlement_calibration_2025fit_2026holdout_20261106.json)；脚本为[`m5_line_conditional_settlement_calibration.py`](m5_line_conditional_settlement_calibration.py)，单元测试覆盖概率归一、温度收缩与留出隔离。

代码与报告已推送在提交 `aedcd6c7713c556464e85c03d0f4f2822e818659`。对应 Actions run [42203113817](https://github.com/ljm198964-alt/quant-runner/actions/runs/42203113817) 来自既有 M3 AH workflow，状态为 `failure`、`jobs=[]`；它没有执行 M5 验收。

## 2026-11-06 MR1 V6 万场级重跑与 M4 配对回放

M5 Crown response 同时保存 1X2 `odds.open/close`。严格身份和 UTC 时间筛选后，9,517 场拥有 M3 严格 OOS 预测及 Crown AH、OU、1X2 三类有效盘口事件，且各事件时间都在预测 as-of 后、kickoff 前。实际调用本机 MR1 V6 原始 cross-market 核心重跑了全部 9,517 场；模型分布/选边不使用赛果。公共批次准备器输出只写私有目录，MR1 公共适配器导入本机原核心，并记录源仓库提交和源码哈希。结果：[MR1 V6 扩展 Crown 回执](results/m5_mr1_v6_cross_market_expanded_crown_20261106.json)、[私有批次准备脚本](m5_mr1_v6_prepare_expanded_crown.py)、[MR1 核心适配器](m5_mr1_v6_expanded_crown_oos.mjs)。

| 模型 | 市场 | 唯一比赛 / 已结算 | 净 U | ROI | 最大回撤 U | Log Loss / Brier |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| MR1 V6 cross-market | AH | 9,517 / 9,517 | -144.230 | -1.5155% | 209.275 | 0.98734780 / 0.61738791 |
| MR1 V6 cross-market | OU | 9,517 / 9,517 | -359.915 | -3.7818% | 373.400 | 0.97330859 / 0.61316344 |

AH W/HW/P/HL/L 为 3,791/783/650/522/3,771；OU 为 3,900/630/480/538/3,969。全部报价来源为 Crown。所有 provider response receipts 均在 kickoff 后取得，因此是 event-time 回顾模拟，不是同期实收或可执行 ROI。2025/2026 分年结果见报告。

另将已有 M4 “Japan J-League、Türkiye Super Lig Pass”规则作为探索性反事实，配对应用到 M3 同一批 10,568 场预测和相同报价。过滤后每市场 10,046 场；AH（Poisson / Dixon–Coles / Bivariate Poisson）ROI 为 -3.3594% / -3.4134% / -3.2700%，OU 为 -3.5469% / -3.4480% / -3.6039%，没有达到 +3%。M4 是 MR1 账本联赛跳过研究，不是独立预测器；两个联赛是看过既往结果后选的，因此此处仍属探索分析，不是未触碰的前瞻验证。回执和脚本：[M4 规则配对回放](results/m5_m4_pass_rule_m3_expanded_oos_20261106.json)、[回放代码](m5_m4_pass_rule_m3_expanded_oos.py)。

当前可执行覆盖对比：M1 仅有每市场 1,233 场保存预测；MR1 V6 本次实际重跑每市场 9,517 场；M3 三模型本次实际重跑每市场 10,568 场（9,612/9,613 Crown，余下 955/956 明确标记 TotalCorner default）；M4 没有独立模型预测，只能运行上述规则反事实。M1 没有其余比赛的冻结预测或可追溯特征快照，不能合法补造 11,573 场输出。可用模型的万场级 ROI 均未达到 AH/OU +3% 目标。

### MR1 与三种 M3 的严格同场比较

为避免把不同覆盖样本横向硬比，使用 MR1 与 M3 完全共有的 9,517 场，所有模型共享 Crown AH/OU 盘口线、双方价格与实际比分。MR1 逐场选择来自本次实际 V6 运行；M3 逐场选择由三个严格 OOS 分数网格在同盘口上重新计算。完整汇总：[同 Crown 同场对比](results/m5_mr1_m3_same_crown_cohort_20261106.json)；MR1逐场轨迹只保存在本机私有授权目录。

| 市场 | 模型 | 唯一比赛 / 已结算 | 净 U | ROI | Log Loss / Brier | 与 MR1 选边一致 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| AH | MR1 V6 | 9,517 / 9,517 | -144.230 | **-1.5155%** | **0.98734780 / 0.61738791** | — |
| AH | M3 Bivariate Poisson | 9,517 / 9,517 | -273.935 | -2.8784% | 1.03510561 / 0.64884847 | 62.82% |
| AH | M3 Poisson | 9,517 / 9,517 | -277.045 | -2.9111% | 1.03309261 / 0.64784279 | 62.57% |
| AH | M3 Dixon–Coles | 9,517 / 9,517 | -280.860 | -2.9511% | 1.03345840 / 0.64806062 | 63.30% |
| OU | M3 Bivariate Poisson | 9,517 / 9,517 | -340.275 | **-3.5754%** | 0.98671203 / 0.62285988 | 64.20% |
| OU | M3 Dixon–Coles | 9,517 / 9,517 | -346.885 | -3.6449% | 0.98677438 / 0.62280564 | 62.72% |
| OU | M3 Poisson | 9,517 / 9,517 | -354.830 | -3.7284% | 0.98670585 / 0.62279713 | 62.77% |
| OU | MR1 V6 | 9,517 / 9,517 | -359.915 | -3.7818% | **0.97330859 / 0.61316344** | — |

在该严格配对样本中，MR1 V6 的 AH 点 ROI 最好，M3 Bivariate Poisson 的 OU 点 ROI 最好；两者仍均为负，没有达到 +3%。proper scores按每个模型实际选中边的五分类结算概率计算。所有9,517场响应收据均赛后取得，所以依旧是回顾性 event-time 比较，不是实收 ROI。M1 只覆盖该档案的一部分保存预测，M4 为Pass研究规则，不能将二者冒充该9,517场全量模型预测。

## M5 市场残差比分网格：2025 拟合 / 2026 留出

复用已完成的私有 Crown/TOTAL 档案，新增独立比分网格市场残差模型。AH 与 OU 分开；2025 只按精确比分 log loss 拟合赔率去水侧概率与 M5 对应盘口结算概率之间的 logit 残差系数，2026 全部可用比赛留出，逐场在同一报价上选择较高模型期望回报侧、每场1U，不加 EV 门槛或其他过滤。除混合训练系数外也分别用 Crown、TotalCorner default 训练系数作敏感性比较。回执：[市场残差 OOS 汇总](results/m5_market_residual_scoregrid_2025fit_2026holdout_20261106.json)，代码与单测：[残差模型](m5_market_residual_scoregrid_2025fit_2026holdout.py)、[测试](test_m5_market_residual_scoregrid.py)。

| 市场 | 2025训练 / 2026留出 | 2026基准 ROI / LL / Brier | 市场残差 pooled ROI / LL / Brier | Crown 单独拟合系数 ROI | TOTAL 单独拟合系数 ROI |
|---|---:|---:|---:|---:|---:|
| AH | 1,311 / 10,226 | -1.8618% / 1.03493458 / 0.65024630 | -2.2812% / 0.98834531 / 0.61792915 | -2.3063% | -2.0481% |
| OU | 1,311 / 10,226 | -3.4988% / 0.98906036 / 0.62401208 | -4.3549% / 0.96592595 / 0.60667412 | -3.8881% | -4.0134% |

2026 去重并集每市场含 Crown 9,316、TotalCorner default 910；来源独立拟合的训练量分别为 AH Crown 1,117/TOTAL 194、OU Crown 1,116/TOTAL 195。残差方法显著改善结算概率 proper scores，但三种拟合在 AH、OU 的 ROI 都低于同场原始 M5 基准；最佳也仅 AH TOTAL 单独拟合 -2.0481%，并未达到 +3%。95% fixture bootstrap 区间全部低于0（pooled AH -4.03%至-0.55%；pooled OU -6.24%至-2.73%）。这说明概率校准提升不等于正收益。

所有历史 API response receipt 均为赛后取得；时间验证只证明盘口事件发生在预测 as-of 后、开赛前，因此仍属回顾性 event-time ROI，不是实收或可执行 ROI。2026 留出已在更早 M5 研究中多次查看，本实验是新方法评估，不是未触碰的确认集。没有任何正式策略、模型、Telegram、订单、账本或 Gate 改动。

## Crown 1X2 交叉市场残差：2025 拟合 / 2026 留出

新增 Crown 的 MR1 风格跨市场特征检验：从每场 Crown 响应的 `odds.open/close` 选出事件时间处于 M5 forecast-as-of 后、开赛前且不晚于实际 response receipt 的最近一组 1X2 水位，去水后作为 M5 比分网格结果概率残差。AH 与 OU 分别在 2025 Crown 样本按精确比分 Log Loss 拟合一个系数；2026 对整个 Crown-first/TOTAL-default 并集每场回放。只有有合格 Crown 1X2 事件的 Crown 行应用调整；Crown 缺失1X2与 TotalCorner default 全部保留基准概率并计入完整分母。复现代码：[Crown 1X2 残差模型](m5_crown_1x2_residual_scoregrid.py)，测试：[时序与概率不变量](test_m5_crown_1x2_residual_scoregrid.py)，报告：[2025 fit / 2026 holdout](results/m5_crown_1x2_residual_scoregrid_2025fit_2026holdout_20261106.json)。

| 市场 | 训练 Crown 1X2 | 2026 全并集样本 | 基准 ROI / LL / Brier | 1X2残差+缺项基准 ROI / LL / Brier | 95% ROI区间 |
|---|---:|---:|---:|---:|---:|
| AH | 1,117 | 10,226 | -1.8618% / 1.03493458 / 0.65024630 | -2.7431% / 1.00364585 / 0.62746631 | -4.4399% 至 -1.0750% |
| OU | 1,116 | 10,226 | -3.4988% / 0.98906036 / 0.62401208 | -3.0855% / 0.98768523 / 0.62308364 | -4.8114% 至 -1.3900% |

2026 有 9,316 Crown AH/OU 报价和 910 TotalCorner default；其中9,203场有合格 Crown 1X2 事件，113场 Crown 与全部910场 TOTAL 保留基准分布。按盘口来源分拆后，AH Crown ROI -2.7483%、TOTAL -2.6896%；OU Crown -3.0010%、TOTAL -3.9505%。OU 相比基准提高约0.41个百分点，但整体及分来源均负收益；AH明显恶化。两市场95% bootstrap区间都全负，因此目标 ROI ≥3% 未达到。

训练和留出赛事 ID 严格不交叉；Crown 1X2、AH/OU盘口和比分均由相同精确赛事关系核验。所有1X2响应回执均在开赛后，故依旧是按盘口事件时间的回顾模拟，不是开赛前实际收取/执行ROI。1X2价格特征来自Crown，不使用或读取MR1预测、参数、订单或账本；TOTAL盘口及其来源仍单独保留。2026留出已经在此前工作中多次查看，非未触碰确认集。

## 联合盘口线 + Crown 1X2 残差：2025拟合 / 2026留出

为检验两个此前独立研究的特征是否互补，新增联合比分网格模型：每个市场分别用2025全部可用 fixture-market 的精确比分 NLL 联合拟合一个 Asian-line 残差系数和一个 Crown 1X2 残差系数；1X2缺失时该特征贡献为零，行仍保留。基准、单特征和联合方法都在完全相同的2026留出队列每场模拟1U。没有按 ROI 选参、筛选赛事或新增 Gate。代码、测试和回执分别见 [`m5_joint_market_1x2_residual_scoregrid.py`](m5_joint_market_1x2_residual_scoregrid.py)、[`test_m5_joint_market_1x2_residual_scoregrid.py`](test_m5_joint_market_1x2_residual_scoregrid.py)、[联合残差报告](results/m5_joint_market_1x2_residual_2025fit_2026holdout_20261106.json)。

| 市场 | 2025训练 / 2026留出 | 方法 | 2026净U / ROI | 最大回撤U | 结算 Log Loss / Brier | ROI bootstrap 95% |
|---|---:|---|---:|---:|---:|---:|
| AH | 1,311 / 10,226 | M5 baseline | -190.390 / -1.8618% | 215.6125 | 1.03493458 / 0.65024630 | -3.5826% 至 -0.1625% |
| AH | 同上 | 盘口线残差 | -231.3125 / -2.2620% | 282.4950 | 0.98834534 / 0.61792917 | -3.9435% 至 -0.5369% |
| AH | 同上 | Crown 1X2残差 | -280.505 / -2.7431% | 320.5400 | 1.00364582 / 0.62746629 | -4.4667% 至 -1.0284% |
| AH | 同上 | 联合残差 | -396.210 / -3.8745% | 405.6425 | **0.98925089 / 0.61865464** | -5.5449% 至 -2.2237% |
| OU | 1,311 / 10,226 | M5 baseline | -357.785 / -3.4988% | 420.2025 | 0.98906036 / 0.62401208 | -5.2045% 至 -1.8330% |
| OU | 同上 | 盘口线残差 | -445.3325 / -4.3549% | 465.6100 | 0.96592595 / 0.60667412 | -6.1483% 至 -2.6401% |
| OU | 同上 | Crown 1X2残差 | -315.520 / -3.0855% | 374.3875 | 0.98768523 / 0.62308365 | -4.7769% 至 -1.3744% |
| OU | 同上 | 联合残差 | -492.5575 / -4.8167% | 502.3375 | **0.96774686 / 0.60821848** | -6.6340% 至 -3.1501% |

联合模型虽优于未校准基准的结算 Log Loss / Brier，但其 AH、OU ROI 都比基准和各自单特征模型更差；没有市场达到 +3%。这再次显示较好的概率评分不必然转化为收益。2026留出每市场来源均为 Crown 9,316 + TotalCorner default 910；其中9,203行有可用赛前事件时间 Crown 1X2 特征，其余1,023行仍保留基准 1X2 分量。模型特征只使用 Crown 1X2，不将 TotalCorner 报价当作该特征。

模型训练截止、预测 as-of、盘口事件时间和开赛顺序均经过现有输入校验；2025与2026赛事 ID 不交叉。但历史 API 收据均为开赛后回取，故 ROI 仅为 event-time 回顾性模拟，不是赛前收据验证或可执行收益；2026已在此前研究中多次检视，也不是未触碰确认集。新增实验未改生产策略、Gate、TG、正式订单或账本。

新增 GitHub Actions [`M5 Research Validation`](../../.github/workflows/m5-research-validation.yml) 会对公开 M5 研究代码运行全套单测，并校验联合模型、M1扩展归档复核、前瞻报价刷新、MR1/M3概率融合、配对和全部前瞻结算回执。MR1/M3 blend commit `601cbd72841c23c9b1310e25421b822e69d9f430` 对应 push run [42235718038](https://github.com/ljm198964-alt/quant-runner/actions/runs/42235718038)，于 `2026-11-06T14:39Z` 成功；67项测试及所有回执验证通过。该工作流不读取 secrets、不访问逐场私有数据，也不重训；自动数据更新与重训还需要把 M5 私有归档安全接入 Actions，当前 private bridge 文件清单未见 M5 数据。

## 2026-11-06T13:39Z 前瞻 Crown 刷新与 TotalCorner default 配对

复用用户已授权的本机 TotalCorner 接口和 2026-11-06T07:01Z 生成的 M5 独立预测队列（361场，51个联赛），仅刷新开赛尚未到来的赛事。Crown 查询队列按 UTC 开赛时间升序，实际运行 `2026-11-06T12:47Z` 至 `13:36Z`，358次请求：340条响应身份核验通过、3条赛事/Crown身份错配、14条身份/API失败、1条传输失败；其中新本轮新增合格盘口事件 AH 49 / OU 44。响应回执与原始响应均保留在本机私有目录，未读取、输出或提交 Token。

随后用现有 TotalCorner default 响应仅补 Crown 缺失的 fixture-market，完成唯一身份和严格时间配对。脱敏回执生成器 [代码](m5_forward_shadow_public_receipt.py) 和[测试](test_m5_forward_shadow_public_receipt.py)验证私有索引后，只输出聚合数与输入/运行器哈希。[前瞻刷新 13:39Z 报告](results/m5_forward_shadow_refresh_20261106T1336Z.json)生成于 `2026-11-06T13:41:03.763943Z`；私有配对输入哈希与事件/回执时间检查均在回执中。AH 配对 60 场（Crown 53、TotalCorner default 7），OU 54 场（Crown 49、TotalCorner default 5），两市场不混算、同场同市场不重复。每条均通过 `train_end < prediction_asof <= quote_event <= quote_received < kickoff`；全体配对的响应实际在各自开赛前收到。

这是概率预测与盘口的前瞻配对，不代表实际下单或已结算投注。此时尚未执行赛果结算，净U、ROI与回撤均为 null；不得将盘口配对数量当作下注数量或收益。样本远低于每市场10,000，M5 ROI≥3%目标尚未验证。已有报告验证工作流在本次新增的前瞻回执上也会检查脱敏、来源分母和未结算字段；全量报告运行记录稍后补录。没有新增交易门槛，也没有修改任何生产链路、正式派单、TG或账本。

### 2026-11-06T13:46Z 前瞻样本首次赛果核验

对上述同一份114项前瞻配对只查询已开赛赛事，按开赛后实际收据验证 TotalCorner `/match/view` 的比赛身份、精确 UTC 开赛时间、完场状态和比分；逐场结果继续保留在本机私有目录。13:46Z 时已验证完场2场（覆盖3个fixture-market：AH 1、OU 2），另1场查询时尚未全场结束，67场未开赛。已结算的 AH 1场与 OU 2场均为走水，净U均为0；暂结算本金ROI为0%，但每市场大部分样本仍待结算，所以整组 ROI 保持 null，最大回撤仅为0的初始局部值、不具判断价值。

| 市场 | 配对项 | 已结算 | 待核验 | 结算类别 W/HW/P/HL/L | 暂结净U | 整组 ROI |
|---|---:|---:|---:|---|---:|---:|
| AH | 60 | 1 | 59 | 0/0/1/0/0 | 0.0 | null |
| OU | 54 | 2 | 52 | 0/0/2/0/0 | 0.0 | null |

脱敏结算回执：[13:46Z 前瞻结算](results/m5_forward_shadow_settlement_20261106T1346Z.json)。它绑定本轮 pairing SHA，且仅含聚合计数、收益和结果响应哈希，不含逐场身份或盘口数据。小样本全走水不构成 ROI 证据，预测样本仍远小于10,000/市场，≥3%目标未达；待后续比赛结束后可对相同私有配对文件增量结算。没有新增交易门槛、实际订单或 Telegram 通知。

### 2026-11-06T13:55Z 前瞻结算增量刷新

对同一不可变配对继续核验已开赛赛事。至 `13:55:55Z`，累计70场已查询fixture中 verified FT 对应5个市场行，109个市场行仍待结算。AH 已结2/60，净 `-1.00U`、暂结ROI `-50.00%`；OU 已结3/54，净 `+0.35U`、暂结ROI `+11.67%`。由于AH尚有58项、OU尚有51项未结算，两市场完整队列 ROI 均保持 null；OU 的短期正数不是已实现全样本收益，不能据此宣称达到+3%。目前已结样本均为 Crown 报价来源，尚未结算的队列来源构成仍为 AH Crown53/TOTAL default7、OU Crown49/TOTAL default5。分市场最大回撤按已结算行暂列，样本过少不具判断力。

脱敏增量回执：[13:55Z 前瞻结算](results/m5_forward_shadow_settlement_20261106T1355Z.json)，绑定同一配对 SHA，公开字段只有分市场计数、收益与哈希。GitHub Actions 对所有前瞻结算回执执行输入哈希、分母、来源计数、结算分类和隐私字段检查。没有下单、Telegram 或生产改动。

### 2026-11-06T14:17Z 前瞻 Crown 报价刷新

先按开赛顺序刷新20场，再对同一冻结预测下的47场未充分覆盖目标刷新；目标身份、训练截止、预测as-of和UTC开赛均与原始07:01Z预测完全一致。第二批中43场在请求时仍未开赛，37条Crown响应通过身份核验，2条身份/API失败、4条传输失败；有效赛前Crown盘口事件覆盖AH26、OU27。两批索引一起重放后，AH仍为60个唯一fixture-market（Crown53、TotalCorner default7），OU仍为54个（Crown50、TotalCorner default4）；对比13:36Z的旧队列，唯一市场项新增0、移除0，报价来源变化1项。已配对共同市场中，赔率对变化30项、盘口线变化5项、盘口事件时间变化35项、实际receipt时间变化61项。这说明刷新更新了已配对报价，但没有制造新的唯一比赛样本。

公开脱敏比较回执：[14:17Z 报价刷新对比](results/m5_forward_shadow_refresh_20261106T1417Z.json)。它绑定目标批次、Crown capture receipt、旧/新pair SHA及输入预测哈希，不含fixture身份、球队、价格或原始响应。所有pair仍满足 `train_end < prediction_asof <= quote_event <= quote_received < kickoff`；该回执不包含已结算收益或ROI。新增刷新回执检查和测试，不更改训练或下注规则。

### 2026-11-06T15:05Z MR1/M3 固定融合与三模型等权集成扩展到完整 M3 报价队列

为检验 MR1 对 M3 是否有全覆盖互补价值，将同一固定 50/50 概率融合扩展到 M3 已完整预测并匹配盘口的所有 10,568 场；只在 MR1 的赛事身份、UTC 开赛、盘口线、盘口事件时间及已选边价格均与同一 Crown 合约精确相符时使用 MR1，其余 fixture-market 保留 M3 原概率。因此 AH、OU 每市场都是同一 10,568 场、每场一注，MR1 精确覆盖 9,517，M3 单模回退 1,051；Crown/TOTAL 来源沿用原合约，AH 9,613/955、OU 9,612/956。Poisson、Dixon–Coles、Bivariate Poisson分别计算，另加入三模型概率等权集成及其MR1融合，没有筛选比赛或按结果删除样本。

| 市场 | 模型 | M3 单模 ROI | MR1/M3 固定融合 ROI | 融合净U | Log Loss / Brier | 最大回撤U |
|---|---|---:|---:|---:|---:|---:|
| AH | Poisson | -3.0304% | -2.9740% | -314.2925 | 1.00528615 / 0.62944913 | 341.1875 |
| AH | Dixon–Coles | -3.1281% | -3.0760% | -325.0675 | 1.00542656 / 0.62955867 | 357.2375 |
| AH | Bivariate Poisson | -3.0012% | -2.9571% | -312.5075 | 1.00592105 / 0.62979555 | 339.4025 |
| AH | M3 三模型等权集成 | -3.1177% | -3.0709% | -324.5325 | 1.00551651 / 0.62958745 | 349.4675 |
| OU | Poisson | -3.6846% | -2.2934% | -242.3675 | 0.97666645 / 0.61530829 | 266.0925 |
| OU | Dixon–Coles | -3.6185% | -2.3634% | -249.7675 | 0.97668951 / 0.61530181 | 275.4025 |
| OU | Bivariate Poisson | -3.5946% | **-2.1354%** | -225.6725 | 0.97689218 / 0.61548186 | 247.4475 |
| OU | M3 三模型等权集成 | -3.4688% | -2.1476% | -226.9625 | 0.97673137 / 0.61535326 | 250.6875 |

该融合降低了所有M3单模组合的回测亏损；但把三种M3概率先等权集成，再与MR1融合，并未优于最佳单一M3融合（OU -2.1476% vs Bivariate Poisson -2.1354%）。OU最佳点估计仍为负，未达到 +3%。2026 单独时间段每市场 9,400 场，未达到10,000：最佳 OU 融合 ROI -2.1941%，AH最佳融合 ROI -2.2955%。2025/2026 预测本身按 M3 UTC 年份前推，但固定等权候选已在重叠的2026队列研究过，因此不得将本报告当作新的未触碰确认集。所有10,568条历史盘口 API receipt 均晚于开赛；这些都是源事件时间回顾模拟，不是实收/可执行 ROI。各模型分市场逐年 W/HW/P/HL/L、ROI、LL、Brier、DD、来源计数和bootstrap见[脱敏聚合回执](results/m5_mr1_m3_source_union_blend_20261106.json)，复算代码为[m5_mr1_m3_source_union_blend.py](m5_mr1_m3_source_union_blend.py)。

另在 `2026-11-06T14:47:03Z` 用同一前瞻配对队列增量核验 TotalCorner FT：70个fixture中仅3个已有 verified FT、1个在收据时尚未完场、66个尚未开赛；AH已结2/60（净-1U），OU已结3/54（净+0.35U），其余109个市场项待结，因此全队列 ROI 仍为 null。最新核验回执为[14:47Z settlement snapshot](results/m5_forward_shadow_settlement_20261106T1445Z.json)；它没有新增完场样本，不应用 settled-only 短期百分比替代全样本目标。

### 2026-11-06 M1 在完整 M3 队列上的重建回放及 M1/MR1/M3 同 Crown 对照

按用户要求，将 M1 补跑到与 M3 三模型相同的扩展 OOS 队列。公开 runner [M1 完整队列回放](m5_m1_full_cohort_replay.py)调用本机只读 M1 当前模型模块及其冻结参数快照，不改 M1 仓库。每个联赛按 UTC 年份分折，在 2025/2026 年初 as-of 训练动态球队强弱；历史比分日期采用 M1 代码注明的两日回溯可用性缓冲。M1 固定校准截止为 `2024-06-01`，共享收缩先验截止为 `2023-11-01`，均早于测试折。93个联赛-年度拟合覆盖同一批 M3 完整预测及盘口配对的 10,568 场。逐场输入/赔率/比分继续留在本机私有目录；GitHub 只保存不含逐场标识和盘口值的聚合回执。

| 市场 | 模型 | 场数 | 净U | ROI | 最大回撤U | 结算 Log Loss / Brier |
|---|---|---:|---:|---:|---:|---:|
| AH | M1 | 10,568 | -252.7450 | **-2.3916%** | 270.5350 | 1.016127 / 0.638436 |
| AH | M3 Poisson | 10,568 | -320.2475 | -3.0304% | 347.2425 | 1.036984 / 0.649529 |
| AH | M3 Dixon–Coles | 10,568 | -330.5775 | -3.1281% | 352.6125 | 1.037381 / 0.649771 |
| AH | M3 Bivariate Poisson | 10,568 | -317.1625 | -3.0012% | 341.2225 | 1.039158 / 0.650563 |
| OU | M1 | 10,568 | -333.6150 | **-3.1568%** | 347.6650 | 0.982166 / 0.619733 |
| OU | M3 Poisson | 10,568 | -389.3925 | -3.6846% | 407.3575 | 0.988362 / 0.623672 |
| OU | M3 Dixon–Coles | 10,568 | -382.4025 | -3.6185% | 400.3675 | 0.988471 / 0.623694 |
| OU | M3 Bivariate Poisson | 10,568 | -379.8825 | -3.5946% | 393.8275 | 0.988429 / 0.623760 |

上表 M3 精确净U、回撤及 M1 的年度/来源拆分见 [M1 全量 OOS 回执](results/m5_m1_full_cohort_oos_20261106.json) 与 [M3 三模型全量回执](results/m5_three_penaltyblog_expanded_oos_20261106_rerun.json)。在相同 10,568 场的 Crown-first + TotalCorner-default 队列上，M1 两市场点估计都比每一个 M3 单模少亏，但 ROI 仍为负；两市场 bootstrap 95% 区间也全部低于0。M1 全量 AH Crown 9,613 / TOTAL 955，OU Crown 9,612 / TOTAL 956。这里的预测在 UTC 年度折的年初生成，盘口取该预测 as-of 之后、开赛之前的同一来源事件快照。

进一步将 M1 与 MR1 V6、三个 M3 模型限制到**完全相同的 Crown 合约**（逐场核验来源、盘口事件时间、盘口线、双方赔率、UTC kickoff、MR1 被选边价格），AH/OU各 9,517 场，零合同错配：

| 市场 | 模型 | 净U | ROI | 最大回撤U | 结算 Log Loss / Brier |
|---|---|---:|---:|---:|---:|
| AH | M1 | -209.790 | -2.2044% | 227.590 | 1.015194 / 0.637808 |
| AH | MR1 V6 | -144.230 | **-1.5155%** | 209.275 | **0.987348 / 0.617388** |
| AH | M3 Poisson | -277.045 | -2.9111% | 295.465 | 1.033093 / 0.647843 |
| AH | M3 Dixon–Coles | -280.860 | -2.9511% | 300.220 | 1.033459 / 0.648061 |
| AH | M3 Bivariate Poisson | -273.935 | -2.8784% | 291.065 | 1.035106 / 0.648848 |
| OU | M1 | -303.210 | **-3.1860%** | 318.500 | 0.980626 / 0.618746 |
| OU | MR1 V6 | -359.915 | -3.7818% | 373.400 | **0.973309 / 0.613163** |
| OU | M3 Poisson | -354.830 | -3.7284% | 370.500 | 0.986706 / 0.622797 |
| OU | M3 Dixon–Coles | -346.885 | -3.6449% | 362.555 | 0.986774 / 0.622806 |
| OU | M3 Bivariate Poisson | -340.275 | -3.5754% | 353.845 | 0.986712 / 0.622860 |

严格同场结果中，MR1 的 AH ROI 最好；M1 的 OU ROI 最好（即亏损最少）。MR1 在两市场的结算概率评分更好；ROI 排序与 proper score 排序并不相同。完整报告为 [M1/MR1/M3 Crown 同场比较](results/m5_mr1_m1_m3_same_crown_cohort_20261106.json)。

这些都是历史盘口事件时间回放：本批所有 10,568 行来源响应，以及严格 Crown 队列内全部 19,034 个市场响应，实际 receipt 均晚于开赛。两日历史比分缓冲是 M1 代码写明的回溯可用性假设，并非逐行结果采集时间证明。故这批同场 ROI 可用于研究比较，不能宣称赛前实收或可执行收益。无模型达到任一市场 +3%；没有改生产策略、Gate、TG、订单或账本。

### 2026-11-06 M1/MR1/M3 五模型融合（2025拟合、2026留出）

为检验 M1 加入后是否改善 MR1/M3，新增 [融合实验运行器](m5_m1_mr1_m3_learned_blend_oos.py)。在 AH、OU 各自的 Crown 同合同9,517场中，2025年1,005场用于分别学习五模型凸概率权重，2026年8,512场冻结留出；模型概率同场、同方向、同线融合后按双方实际价格选期望回报较高的一侧，每场1U。实验同时比较2025 settlement Log Loss 拟合权重、2025 ROI 拟合权重、五模型等权及单模型，不筛除比赛、不设 EV 或下注量门槛。所有模型在该 cohort 的盘口合同精确一致，AH/OU每场集不重复，跨年比赛ID无交叉。

| 市场 | 2025选择方式 | 冻结权重（非零项） | 2026 ROI / 净U | Log Loss / Brier | bootstrap 95% ROI |
|---|---|---|---:|---:|---:|
| AH | Log Loss | MR1 100% | -1.1201% / -95.345 | 0.988186 / 0.617843 | -3.0296% 至 +0.6944% |
| AH | ROI | M1 100% | -2.3531% / -200.295 | 1.014824 / 0.637530 | -4.2199% 至 -0.4590% |
| AH | 五模型等权 | 各20% | -1.5579% / -132.610 | 1.007571 / 0.632427 | -3.5003% 至 +0.3544% |
| OU | Log Loss | M1 32.6042%；MR1 67.3958% | -3.8546% / -328.100 | **0.969156 / 0.609826** | -5.7899% 至 -1.9688% |
| OU | ROI | M1 50%；MR1 50% | -3.2239% / -274.415 | 0.969245 / 0.609864 | -5.1806% 至 -1.3220% |
| OU | 五模型等权 | 各20% | -3.3315% / -283.580 | 0.975317 / 0.614584 | -5.1997% 至 -1.4748% |

AH 的2025 Log Loss最优权重退化为MR1单模；OU的概率融合改善了 proper score，但其 ROI 比 M1 单模 -3.1272% 更差，展示了概率拟合改善不等于盈利改善。直接按2025 ROI拟合也未在2026获利。以上候选没有任一市场达到+3%；AH两个融合候选的置信区间仍跨零，OU则完全低于零。逐模型完整训练/留出表、2025拟合诊断、类别、drawdown、来源、置信区间及全部输入哈希见[脱敏报告](results/m5_m1_mr1_m3_learned_blend_20261106.json)。

时间顺序为 UTC 年度折，M1 使用截至其冻结参数截止日的校准和动态前缀；2025/2026 prediction probabilities 在各自目标期前生成，quote event 在开赛前。历史供应商 API receipts 全部在开赛后，因此 2026 ROI 是回顾性 event-time OOS，不是同期可执行实收。2026此前已在 M5其他方向中观察，不是全新 untouched confirmation set。研究未改生产模型、交易门槛、TG或正式账本。

## 2026-11-06 M5恢复运行：按来源重新回放 AH / OU

恢复已授权的本机 TotalCorner Keychain 凭证接入后，调用既有断点续采程序检查 11,652 个 M5候选。所有符合目标的赛事ID此前均已有 Crown 或 TotalCorner响应，因此此次没有新请求、没有新增盘口数据。随后以同一份冻结 M5 OOS 预测与本地原始报价重跑 Crown-only、TotalCorner-only 和按赛事-市场 Crown-first 的三种独立来源策略；每市场每场1U，源并集按唯一赛事-市场计数，不重复计数，不加EV门槛。

| 来源策略 | 市场 | 唯一场数 / 模拟投注 | Crown / TotalCorner | 净U / ROI | 最大回撤U | Log Loss / Brier | 95% fixture bootstrap ROI |
|---|---|---:|---:|---:|---:|---:|---:|
| Crown-only | AH | 10,433 | 10,433 / 0 | -246.905 / -2.3666% | 275.545 | 1.033032 / 0.649833 | -4.029% 至 -0.659% |
| Crown-only | OU | 10,432 | 10,432 / 0 | -380.365 / -3.6461% | 395.610 | 0.986955 / 0.622854 | -5.338% 至 -1.945% |
| TotalCorner-only | AH | 1,141 | 0 / 1,141 | -44.5625 / -3.9056% | 61.2875 | 1.064032 / 0.663789 | -8.957% 至 +1.043% |
| TotalCorner-only | OU | 1,141 | 0 / 1,141 | -40.1875 / -3.5221% | 53.775 | 1.004476 / 0.633917 | -8.635% 至 +1.631% |
| Crown-first去重并集 | AH | 11,573 | 10,433 / 1,140 | -290.4675 / -2.5099% | 315.1075 | 1.036104 / 0.651223 | -4.108% 至 -0.903% |
| Crown-first去重并集 | OU | 11,573 | 10,432 / 1,141 | -420.5525 / -3.6339% | 439.105 | 0.988682 / 0.623945 | -5.261% 至 -2.004% |

并集按UTC kickoff年份的ROI：AH 2015 `n=36/-4.6875%`、2025 `n=1,311/-7.5050%`、2026 `n=10,226/-1.8618%`；OU 2015 `n=36/+2.9514%`、2025 `n=1,311/-4.8688%`、2026 `n=10,226/-3.4988%`。单年小样本不能单独视为稳定收益。AH结算 W/HW/P/HL/L 为 `4,623/798/798/799/4,555`；OU为 `4,798/648/580/803/4,744`。两市场所有入选报价实际 API receipt 都在开赛后；事件时间报价早于开赛但只支持回顾性 event-time 回放，不代表可成交收益。TotalCorner-only未达到10,000场，Crown-first并集达到但两市场均未达到+3%，95%区间均为负。冻结2026数据此前已经查看，不是未触碰最终确认集。

可核验脱敏结果、输入哈希、逐市场来源构成、年度结果与时间限制见[恢复运行回执](results/m5_totalcorner_restart_source_replay_20261106.json)。回执不含逐场身份、价格、比分或凭证；原始档案保留在本机私有目录。此次未改变模型、交易规则或生产链路。

## 前瞻 shadow 队列增量结算（2026-11-06T16:20Z）

对冻结且具有实际赛前预测、Crown/TOTAL报价事件和赛前接收证据的70场队列（AH60、OU54）重新用 TotalCorner 核验 FT。新增1场verified FT，新增两项fixture-market结算；累计已结7项、待结107项。AH已结3（全输2、走水1），净-2U；OU已结4（全赢1、半赢1、走水2），净+1.37U。未结的AH57、OU50仍在全组分母内，因此两市场 full-cohort ROI 都是null；已结子集比例仅描述早期小样本，不代表目标收益。配对来源为AH Crown53/TOTAL7、OU Crown50/TOTAL4，当前7项已结价格都来自Crown。比分由开赛后核实，原始行级结果、价格、身份仍在私有目录；公共聚合回执[前瞻增量结算](results/m5_forward_shadow_settlement_20261106T1620Z.json)绑定既有pair hash。该真实前瞻队列规模仍小，不能替代每市场10,000场历史目标或改变历史event-time ROI结论。

### 2026-11-06T16:27Z Crown 当前报价刷新

同一冻结预测批次中最早的20场未开赛fixture再次请求 Crown 专用盘口端点，20/20身份通过，AH和OU各有18场返回合格报价。与14:17Z pair比较仍是114项（AH60、OU54），没有新增或移除赛事市场；共同项目中28项赔率对、10项盘口线、30项盘口事件时间、36项receipt时间更新，来源构成不变。新pair所有114项均满足 `train_end < prediction_asof ≤ quote_event ≤ quote_received < kickoff`。7项已结、107项待结，AH净-2U、OU净+1.37U，完整队列两市场ROI均为null。它证明当前可用的赛前Crown收价流程能够写入真实receipt时间，但样本规模太小，不能证明收益目标。脱敏汇总及代码/输入哈希见[Crown刷新回执](results/m5_forward_shadow_crown_refresh_20261106T1627Z.json)；逐场原始报价仍在私有归档。

### 2026-11-06T16:44Z Crown 覆盖扩展

从同一冻结预测的未开赛目标中再抓取40场Crown报价，40/40身份响应通过，AH/OU各18场有合格报价。重配对后唯一fixture-market从114增至120：新增AH3、OU3，均来自Crown；本批不是用TOTAL填补这些新增项。新队列来源为AH Crown56/TOTAL7、OU Crown53/TOTAL4。旧114项共同样本中15项赔率对、6项盘口线、17项报价事件时间、30项实际receipt时间更新。新队列120/120均满足严格 UTC 时间顺序并在开赛前收到。增量结算未发现新FT：AH已结3/63、净-2U，OU已结4/57、净+1.37U；其余113项待结，所以全队列ROI均为null。它实际扩大了前瞻影子覆盖，但离每市场10,000场及收益目标仍远。报告见[16:44Z Crown刷新与覆盖回执](results/m5_forward_shadow_crown_refresh_20261106T1644Z.json)，身份及逐场价位继续留在私有档案。

### 2026-11-06T16:54Z 前瞻覆盖与 FT 增量

再对下一批40场未开赛目标请求Crown：40/40身份通过，AH/OU各11场有合格报价。配对从AH63/OU57扩至AH68/OU61，新增9个唯一fixture-markets（AH5、OU4），均为Crown；TOTAL来源仍AH7/OU4。120个旧项中，6项赔率对、1项盘口线、6项盘口事件时间、13项实际接收时间更新。完整新队列129项全部满足 `train_end < prediction_asof ≤ quote_event ≤ quote_received < kickoff`。新发生结算的赛果使累计AH结算5/68、净-0.36U、W/HW/P/HL/L=`2/0/1/0/2`；OU结算6/61、净+1.37U、`2/1/2/0/1`。pending合计118，全队列ROI仍null。数据是赛前实收的前瞻shadow样本，但量级与10k收益目标仍相距很大。见[16:54Z Crown/结算扩展回执](results/m5_forward_shadow_crown_refresh_20261106T1654Z.json)。

### 2026-11-06T17:03Z 前瞻 Crown 刷新

下一批20个未开赛目标中19个响应身份通过，1个 Crown/fixture 身份不匹配被排除。AH有5、OU有3个市场返回合格赛前报价。配对由AH68/OU61扩至AH71/OU64，新增6项均来自Crown。队列135项全部满足严格UTC时间顺序；AH已结5/71、净-0.36U，OU已结6/64、净+1.37U，pending 124，两市场完整队列ROI均null。只有19/20响应有效且只有8项在盘口层合格；本次不表示预测成功或达到历史收益目标。详见[17:03Z刷新回执](results/m5_forward_shadow_crown_refresh_20261106T1703Z.json)。

### 2026-11-06T17:21Z 前瞻 shadow 结算复核

使用带时间戳的最新 17:03Z 配对文件（pair SHA `665ced85c5d608a59544aff683bfa35d935efb4f99f38c4cd0a94b00a48cf851`）重新核验 TotalCorner FT。结算请求本轮完成 6 个既有已验证 fixture 的复用、9 个 fixture 当时尚未完场、71 个 fixture 尚未开赛；没有新增 verified FT。最新冻结队列仍为 AH 5/71 已结、净 -0.36U，OU 6/64 已结、净 +1.37U；待结分别 66、58，全队列 ROI 仍为 null。已结价格均为 Crown；完整配对来源 AH Crown64/TOTAL default7、OU Crown60/TOTAL default4。旧别名 `m5_forward_pairs_latest.jsonl` 指向 16:54Z 的旧队列，复核时明确使用时间戳文件。脱敏结果见[17:21Z结算回执](results/m5_forward_shadow_settlement_20261106T1721Z.json)。这次没有新增学习信息或可计算的完整队列ROI。

## 2026-11-07T05:40Z 新 M5 前瞻 Crown / TotalCorner 队列

使用 M5 自有模型重新拟合 40 个有历史训练数据的联赛，在 UTC `2026-11-06T17:27:12Z` 为 345 场未来赛事生成逐场比分网格；训练截止时间均早于预测 as-of，赛事身份冲突为0。随后按开赛时间顺序采集 Crown，345次尝试中331条身份验证通过、2条赛事/Crown身份错配、10条API/身份失败、2条传输失败；只有 AH 3、OU 1 场取得预测后、赛前有效 Crown 盘口。对 Crown 缺盘项继续调用 TotalCorner default，343次请求中334条身份核验通过、9条赛事/API身份错配；Crown优先去重后补得 AH 27、OU 20 个 TOTAL 市场项。

配对最终为 AH 30（Crown 3、TotalCorner default 27），OU 21（Crown 1、TotalCorner default 20），共51个唯一 fixture-market；盘口覆盖率为 AH 30/345 forecast、OU 21/345 forecast。各项均满足 `train_end < prediction_asof <= quote_event <= quote_received < kickoff`。接收时间都在开赛前；逐场身份、比分网格、盘口线、赔率、原始响应继续仅存私有目录。脱敏收据：[05:39Z 前瞻配对](results/m5_forward_shadow_capture_20261107T0539Z.json)。

截至结算检查 `2026-11-07T05:40:32Z`，38场 fixture 中16个市场项已有 verified FT、35项待结；本轮尚有1个fixture在查收时未完场、27个fixture未开赛。AH已结9/30，净 -1.50U，结算 W/HW/P/HL/L=`3/1/0/1/4`，已结子集ROI -16.67%；OU已结7/21，净 -2.75U，结算=`2/0/0/1/4`，已结子集ROI -39.29%。AH/OU剩余待结21/14项，因此全队列ROI均为 null，不能用已结子集宣称收益达标。当前已结赔率都来自 TotalCorner default；完整队列保持来源分离。脱敏结算回执：[05:40Z前瞻结算](results/m5_forward_shadow_settlement_20261107T0540Z.json)。

## 2026-11-07T05:49Z M5 forecast-only batch

重新读取固定 M5 历史 manifest 与 TotalCorner 赛程缓存并按当前 UTC 重新拟合。共 317 条未来 schedule / forecast，39 个有训练历史的联赛分别拟合；0 identity conflict、0 league without training。所有逐场行满足 `train_end < prediction_asof < kickoff`。训练截止范围 `2026-10-24T07:30:00Z` 至 `2026-11-04T17:00:00Z`，目标开赛时间范围 `2026-11-07T06:00:00Z` 至 `2026-11-23T20:00:00Z`。forecast SHA `5508b8ac2ee95893698598812449a55c83a0bc316e84f472d776fc51a7382a48`，历史 manifest SHA `55f96d4b3ba5fefb7aec82578dea8090d8a26e36b1350ea49eecf4751223b960`。脱敏聚合回执：[05:49Z forecast receipt](results/m5_forward_forecast_20261107T0549Z.json)。

这份回执只证明模型批次可追溯，不含盘口、下注或ROI。模型输出及赛事身份留在私有目录。生成后发现用户侧 M3 TotalCorner schedule audit PID 33622 仍运行并持有接口代理连接；为避免与共享 API 限速冲突，M5 新批次的 Crown 与 TotalCorner 采集待该进程结束后顺序执行。

## 2026-11-08 M1 / MR1 / M3 / M4 在新增 Crown 万场回执上的逐模型复跑

新增 [统一 Crown 样本逐模型对照报告](results/m5_model_family_canonical_crown_comparison_20261108.json) 和可复跑程序 [`m5_model_family_canonical_crown_comparison.py`](m5_model_family_canonical_crown_comparison.py)。输入是截至本轮离线补齐的规范 Crown summary 历史缓存，并连接各系统既有逐场 OOS 预测档案。AH 10,400、OU 10,399 个唯一 Crown fixture-market；全部盘口 source 为 Crown，且历史 API response receipt 均在开赛后，所以这里只能称为按赛前 source-event 盘口做的回顾性 OOS 回放，不能视为当时已收到或可执行收益。

M3 的 Poisson、Dixon–Coles、Bivariate Poisson 保存了完整比分网格，按本轮 Crown 的实际盘口线和双方价格重新选边、计算 settlement probabilities 并结算；有效覆盖 AH 9,591 / OU 9,590。M1 与 MR1 V6 只保存旧合约线上的五类结算概率；严格要求预测档案存在、原盘口线与本轮 Crown 线精确相同且预测事件不晚于本轮 quote event。可用覆盖 AH：M1 8,191、MR1 8,129；OU：M1 8,300、MR1 8,237。其余不跨盘口线套用概率。报告另列五方案完全相同 fixture-market 的共同样本：AH 8,129、OU 8,237，作为模型间最公平的同场比较。MR1 单体未补齐缺失场次。M4 仅是现有 Japan J-League / Türkiye Super Lig Pass 研究规则应用于 M3；同时报告其全覆盖与共同样本结果，并明确该 Pass 是事后研究，不是独立模型或未触碰留出。

全样本可用行的 ROI 均为负。严格共同样本 ROI：AH MR1 -0.95%、M1 -2.15%、M3 Bivariate -2.74%、M3 Poisson -2.85%、M3 Dixon–Coles -2.95%；OU M1 -2.73%、M3 Bivariate -3.31%、M3 Dixon–Coles -3.35%、M3 Poisson -3.44%、MR1 -3.52%。共同样本 proper scores、逐年、最大回撤、结算分布及重抽样区间均见 JSON 回执。M4共同样本两市场也为负。没有任何方案达到 +3%。逐场输入/输出仅留本机私有目录；公开回执只包含聚合指标和文件哈希。

## 2026-11-09 M3 penaltyblog 原版在新 Crown 万场上的重新前推训练

为扩展 M3 对新归档的覆盖，新增 [`m5_canonical_crown_penaltyblog_refit.py`](m5_canonical_crown_penaltyblog_refit.py) 与脱敏聚合报告 [逐年重新拟合结果](results/m5_canonical_crown_penaltyblog_refit_20261109.json)。训练只使用冻结 51 联赛候选赛果清单里同联赛、目标 UTC 年 1 月 1 日之前完赛的比赛；分别拟合 penaltyblog 默认 Poisson、Dixon–Coles 和 Bivariate Poisson。各测试场次按 ID/联赛/UTC kickoff/赛果与清单核验，训练截止严格早于该年 1 月 1 日，再用 Crown quote event（event < kickoff）及双方真实价格独立选边结算。仅 Crown，不使用 TotalCorner。AH 新队列 10,400，OU 10,399；完整的三套原版模型可预测 9,591 / 9,590 场。缺少的 809 场是年初训练集中的未知队伍，原版严格结果不作填补。

另做了明确标记的 `LeagueAvgFallback` 研究版本：仅当对应原版模型不能识别参赛队时，用同联赛、同年初训练集主客场均进球率构造独立 Poisson 分布。该版本完整覆盖 AH 10,400 / OU 10,399 场，仍是一场一项、1U结算，没有投注数量或 EV 条件。AH ROI：严格原版 Bivariate -3.067%、Poisson -3.095%、Dixon–Coles -3.241%；联赛平均回退版分别 -3.335%、-3.361%、-3.495%。OU 严格原版分别 -3.684%、-3.748%、-3.820%；回退版分别 -3.924%、-3.983%、-4.050%。回退还使 Log Loss/Brier 变差；全部 95% bootstrap ROI 区间上界仍低于0。2025单独子样本各模型约 -6% 至 -9%，2026亦均为负。此轮成功达到三模型每市场万场覆盖，不满足 ROI ≥3% 目标。

报价 source event 为赛前，但 Crown 历史响应实际接收范围在 2026-11-04 至 2026-11-06，均晚于比赛 kickoff；因此结果是严格按训练截止与盘口事件前推的 retrospective OOS，不是同期可执行收益。91 个联赛/UTC年训练折，目标队伍不在训练集的场次只进入显式回退对照，输入/模型/赔率/赛果逐场结果保存在机密目录。报告含候选清单和 quote 输入 SHA、运行器 SHA、逐年覆盖和校准/收益指标，不含 fixture identity 或价格。

### 2026-11-08T16:24:54Z Crown-first 前瞻队列结算刷新

使用冻结的 M5 前瞻配对队列（AH 102、OU 98；唯一 fixture 105）再次查询 TotalCorner FT。沿用已核验结果21场；本轮新核验18场 FT，33场查询时未完赛，32场尚未开赛，另1场接口/身份核验错误留待重试。累计已结唯一 fixture-market 70，待结130。公开脱敏回执：[前瞻结算刷新](results/m5_forward_shadow_settlement_canonical_crown_20261109.json)。配对输入SHA为 `8374dceff535fd6e605bf05a27f916947902c475810f46939a177f1d8dc31132`；逐场 fixture、概率、盘口、比分及原始响应留在私有目录。

| 市场 | 来源配对（Crown / TotalCorner default） | 已结 / 待结 | 已结胜/半胜/走水/半输/负 | 已结净U | 已结子集ROI | 全队列ROI |
|---|---:|---:|---:|---:|---:|---:|
| AH | 83 / 19 | 36 / 66 | 16 / 3 / 1 / 1 / 15 | +0.42 | +1.1667% | 未计算（仍有未结） |
| OU | 82 / 16 | 34 / 64 | 15 / 3 / 0 / 1 / 15 | -0.4275 | -1.2574% | 未计算（仍有未结） |

AH、OU均未完成本队列结算，故已结子集 ROI 不代表最终队列收益，也不满足 M5 历史样本规模或 ROI 目标。所有预测后取得的 Crown/TotalCorner 盘口均在 UTC 开赛前真实接收；FT 则由赛后带身份与 kickoff 校验的 TotalCorner 响应确认。来源始终分开记录。全量原始回执留存私有，公开结果只含汇总与哈希；没有生产模型、Gate、TG、订单或账本变更。

### 2026-11-08T16:37Z M5 新前瞻预测批次

从现有 M5 私有历史 manifest 与已缓存的范围内 TotalCorner schedule 生成独立 M5 预测，没有读取 M1/MR1 预测、盘口、订单或账本。共生成 106 个唯一未来 fixture，覆盖 24 个有历史训练数据的联赛；identity conflict 0、无训练记录联赛 0。每联赛训练行数 695–4,833（中位数 3,551），训练赛果截止 `2026-11-01T13:00:00Z` 至 `2026-11-04T17:00:00Z`，预测 as-of `2026-11-08T16:37:08.219144Z`，目标 kickoff 范围 `2026-11-08T17:00:00Z` 至 `2026-11-23T20:00:00Z`。逐场比分网格和赛事身份留在私有目录；脱敏批次回执见[forecast receipt](results/m5_forward_forecast_20261108T1637Z.json)，forecast SHA `f74db0cafec6ca6b361410aa85a638a468982541db0c157236760b7aaaf4cd9d`，历史 manifest SHA `55f96d4b3ba5fefb7aec82578dea8090d8a26e36b1350ea49eecf4751223b960`。

该文件目前只证明预测批次可追溯，尚未配对赛前 Crown 或 TotalCorner 盘口，也未结算或计算 ROI。发现已有 M3 historical movement collector 正在使用共享 TotalCorner 接口，因此此批次暂缓采价，避免并发占用接口。M5 收益与每市场10,000场目标均未达到；未改生产策略或任何交易规则。

### 2026-11-08T17:45Z M5 前瞻预测刷新

对仍未开赛的 M5 目标按冻结 M5 历史 manifest 重新拟合并生成当前 UTC 的94场独立 score-grid forecast，覆盖19个有训练样本的联赛；ID冲突0，缺历史训练联赛0。每联赛训练样本1,603–4,833（中位数3,412），训练截止 UTC 范围 `2026-11-01T13:00:00Z`–`2026-11-04T17:00:00Z`，新预测 as-of `2026-11-08T17:45:33.556981Z`。manifest SHA 与前一批相同，没有新增训练赛果，因此此次是更新预测时点，不代表新增学习信息。逐场预测留在私有目录，脱敏回执见[17:45Z forecast receipt](results/m5_forward_forecast_20261108T1745Z.json)。

采价前的严格配对核验显示：截至 `2026-11-08T17:44Z` 有94场未开赛；Crown有93个赛事身份匹配，但 AH/OU 都没有同时满足预测后报价事件、开赛前实际接收的有效市场项；新 forecast SHA 下尚无 TotalCorner 回执。故本批尚无盘口配对、结算或 ROI。共享 TotalCorner API 当时仍被另一采集进程使用，因此未并发请求。该预测批次不构成下注或收益证据，未改生产策略。

### 2026-11-08T17:18Z Crown 移动盘口离线回放

对 M5 已有逐场样本外预测和本地已存 Crown 历史响应做离线匹配，不发起新 API 请求。只保留精确响应 SHA、赛事身份、比分及 UTC kickoff 一致的样本，并要求预测训练截止时间早于预测时点、Crown 报价事件时点早于 kickoff；实际响应接收均发生在 kickoff 后，因此只能称为按盘口事件时间回放，不能称为赛前实收成交。2025–2026 预测与已存 Crown movement 交集共4,890场；AH有4,876条有效盘口，OU有4,875条，分别有14/15条无合格 movement 盘口。AH每场一笔1U回放净亏135.21U、ROI -2.7730%、最大回撤152.68U；OU净亏152.945U、ROI -3.1373%、最大回撤166.54U。用同赛事最新 open/close summary 报价回放分别为AH -2.8561%、OU -3.1899%。逐场 movement 相对 summary 的配对ROI差异95%区间均跨过0，暂未显示稳定优势。AH/OU分别独立核算，报告不包含逐场身份、精确盘口或比分，见[脱敏结果](results/m5_canonical_crown_movement_replay_20261109.json)。这是既有预测/赛果上的探索性分析，不是新独立留出集；不改变任何生产模型、订单、TG、Gate或账本。

### 2026-11-08T17:30Z Crown movement 新增采集复核

在共享 TotalCorner 采集器仍运行时仅做 SQLite read-only 离线刷新，没有发起网络请求。movement 库持续增加记录，但当前 M5 2025–2026 OOS forecast 对应的精确响应集合未改变：forecast匹配仍4,890，AH/OU合格报价仍4,876/4,875，输入M5索引和响应SHA均与17:18Z报告相同；净值/ROI也不变。故这轮底层库采集没有给当前 M5 OOS 队列增加新学习信息。刷新回执为[17:30Z聚合报告](results/m5_canonical_crown_movement_replay_refresh_20261108T1729Z.json)。
