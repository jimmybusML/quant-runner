# M5 独立融合研究

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
