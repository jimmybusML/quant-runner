# M5 独立融合研究进度与真实历史回放

报告时间：2026-11-04 UTC。M5 保持独立研究身份。本报告没有修改 M1/MR1/M3 生产策略、订单、结算账本、Telegram 或自动任务；没有使用 M1/MR1/M3 正式派单执行 M5 策略。所有收益按 1U 单注、Crown 盘口回放或已有 Crown-only 汇总计算。

## 结论摘要

- 已在 **13,234 场不重复真实比赛**上，对严格按赛季/时间外推得到的 M3 Poisson、Dixon-Coles、Bivariate Poisson 预测做了逐赛季前推概率融合研究。AH0 与 OU2.5 分开统计。权重每一测试季只用更早测试季的 OOS 预测训练。13,234 场宽口径概率集合不含逐场 Crown 线价；本轮另从 MR1 本机历史归档精确配对出小型 2026/27 Crown OOS 子样本，详见 M5-D。
- 在现有冻结 M1 Crown OU 小型档案里，56 场符合原协议的首次赛前观察，52 场有已验证 FT，4 场仍待赛果。固定 M1 校准模型在 52 场上的简单选边回放为 **+2.05U / 52 = +3.94%**，未超过 5%；区间很宽，且本轮复算的选边/模拟下注口径没有作为独立预注册策略冻结，不能当作 M5 已验证 OOS ROI。
- M1 校准版在上述小样本表现最好，但其逐比赛日 Bootstrap ROI 95% 描述区间为 **-19.40% 至 +27.40%**。没有可靠证据证明长期正收益。
- 公开 M4 最新 MR1 Crown 旧回放为 AH **-2.8276% / 1,563 场**，OU **-2.9706% / 1,563 场**。这是 MR1 已保存 forward 选择的回放，不是 M5。
- M5-D 的初步同场 Crown OOS 子样本 AH 24 场、OU 36 场，尚远低于“10,000 场带真实 Crown 赛前线价、可结算收益”的要求；13,234 场概率样本不可替代 Crown 样本。
- 另完成一项限于有保存全比分分布的同期 M3 预测的任意亚洲线探索：17 场同时有 M3 当季严格 OOS 行、同期 verified Crown AH/OU 报价和三模型赛前比分网格。AH / OU 各 17 注分别为 -1.44% / -23.41%。比分网格的训练输入未留存逐行历史快照哈希，故此扩展回放不作为无泄漏证明或主要 OOS 成绩。

## 范围、模型和资料审计

M1 公开研究副本中的 `research/m3/reference/m1_runtime_policy.py` 有 59 个国内顶级联赛名称规则及 3 个显式允许的国际赛事规则；MR1 的 `mr1_competition_scope.json` 有 56 个国家 token 与 117 个排除竞赛 token。公开 M3 当前概率 OOS 输入来自 Football-Data.co.uk 六个联赛代码（B1、D1、E0、F1、I1、SP1），属于现有范围内有公开历史数据的子集，**不是更改正式赛事范围**。

- **M1 AH**：正式 M1 使用自己的 Crown AH 选单和账本。已读 handoff 的真实正式结果（截止 2026-11-03 历史快照）不能与研究回放混合。公开 M1 私有副本中的 Crown OU 档案不提供 10k 比赛价格记录。
- **M1 OU 研究**：V23 固定五种预测方法：Crown 市场 Poisson、M1 原始、M1 校准，以及两种 75% 市场锚定 + 25% M1 预测。校准训练描述为 2023/24 英超与德甲 505 条观察；测试档案的协议冻结时点为 2026-10-08T16:02:34Z。
- **MR1 AH**：既有模型从 Crown 1X2 去水拟合比分分布，对 Crown AH 合约评估并保留真实正式订单；生产账本与研究回放分开。不能从已聚合 M4 文件恢复逐场 MR1 概率来重训 M5。
- **M3**：严格赛季前推的 penaltyblog 原版 Poisson、Dixon-Coles、Bivariate Poisson；输入仅 Football-Data.co.uk 日期、主客队和 FT 比分，不读取该站赔率。AH 输出是 AH0/DNB 三状态概率，OU 输出是 O2.5 概率。M3 报告确认整赛季测试集按更早赛季训练，测试日期的结果不参与拟合。

M1 与 M3 的现存资料仅有 **2 场**通过精确“联赛代码 + UTC 日期 + 主客队规范化名称”键与 M1 冻结版 Crown OU 合格样本连接。两场不足以做跨模型融合收益结论；也不能用模糊队名匹配扩样本。

## M5-A：13,234 场概率堆叠前推

脚本：[`probability_stack_oos.py`](probability_stack_oos.py)。输入来自 M3 最新严格前推 CSV，源报告生成于 2026-11-04T11:59:53.779Z。源文件包含 17,151 场唯一测试赛事，其中 14,806 场三模型都生成有效预测；第一次可训练历史权重的 OOS 季为 2019/20，因此留出该最早预测季后，逐赛季评估共有 **13,234 场**。唯一赛事键为联赛、UTC 日期、主队、客队。所有三个模型行均核对赛果/赛季一致、概率向量归一化且唯一。

随后 Actions run [41864900732](https://github.com/ljm198964-alt/quant-runner/actions/runs/41864900732) 于 `2026-11-04T16:16:39.480507Z` 再训练和比较，输入 fingerprint、测试身份及 penaltyblog 版本均未变，9 个模型/市场 score comparison 的差异均为 0，确认此次运行没有新增学习信息。预测文件 SHA 保持 `9375bdbb…`，因此下面的 OOS 堆叠及 Crown replay 输入仍对应同一预测集合。

每个测试赛季的融合权重由更早赛季的 OOS 预测和实际赛果拟合，非负且和为 1；同季行不进入拟合。没有依 ROI 选权重，没有调 Crown 赔率门槛。多分类 1X2/AH0 Brier 使用三类平方误差和；OU Brier 使用二元 O2.5 平方误差。

| 独立市场/指标 | M3 Poisson | M3 Dixon-Coles | M3 Bivariate | M5 逐季前推融合 |
| --- | ---: | ---: | ---: | ---: |
| AH0/DNB Log Loss（13,234 场） | 1.003715 | **1.003325** | 1.003611 | 1.003577 |
| AH0/DNB Brier | 0.599302 | **0.598974** | 0.599194 | 0.599221 |
| OU O2.5 Log Loss（13,234 场） | 0.746987 | 0.746969 | **0.745797** | **0.745797** |
| OU O2.5 Brier | **0.245943** | 0.245949 | 0.245948 | 0.245948 |
| Crown 收益/ROI | 无 | 无 | 无 | **无价格，不可计算** |

观察：1X2 权重堆叠未超过 Dixon-Coles 单模型；OU 的时间前推权重每季最终全部给 Bivariate Poisson，因而融合等同于选择该单模型，未带来可测提升。虽然 Log Loss 小幅领先其他 OU 单模型，但 Brier 几乎持平。这里 AH0 与 1X2 的三状态概率是同一个比分概率事件映射，统计样本独立按 AH 市场解释，不与 OU 混合。

详细每赛季权重、训练量、测试量、分数、源输入 SHA 与训练切分在 [`results/m5_probability_stack_oos.json`](results/m5_probability_stack_oos.json)。

## M5-B：M1 冻结 Crown OU 小型回放

脚本：[`m1_ou_crown_small_archive_replay.py`](m1_ou_crown_small_archive_replay.py)。它只读 M1 私有仓库中的已冻结 V23 首次观察和 FT 汇总；私有输入仅在本机临时目录处理。公开结果仅保留 SHA、聚合数字和每联赛聚合，不包含队名、fixture ID、线价、赔率、原始盘口或账本行。

样本审计：原始研究档案 1,705 个不同顶级联赛 fixture；有 Crown 行情事件的 1,331 场，其中 1,275 场被冻结协议按报价年龄拒绝、374 场缺 Crown OU 线、56 场符合原冻结观察资格；52 场已通过 M1 verified FT receipt 或 TotalCorner FT 验证并结算，4 场无本报告可用 FT。时间核对要求扫描开始 < 扫描结束 < kickoff，Crown 事件时间 < kickoff 且不晚于扫描结束、Crown 证据 hash 存在、quote age ≤180 分钟。所有时间均解析成 UTC。

| 冻结模型候选 / 研究选边 | 模拟下注（含待结） | 已结 | 未结 | 净收益 | ROI | 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Crown 市场 Poisson，全部合格样本取 EV 较高侧 | 56 | 52 | 4 | -0.600U | -1.15% | 6.590U |
| M1 校准，全部合格样本取 EV 较高侧 | 56 | 52 | 4 | +2.050U | **+3.94%** | 9.525U |
| M1 原始，全部合格样本取 EV 较高侧 | 56 | 52 | 4 | -3.785U | -7.28% | 11.395U |
| 75% 市场 + 25% 校准，全部合格样本 | 56 | 52 | 4 | +2.050U | +3.94% | 9.525U |
| 75% 市场 + 25% 原始，全部合格样本 | 56 | 52 | 4 | -3.785U | -7.28% | 11.395U |

一个独立研究变量是“只下注预测 EV>0 的模型侧”：M1 校准为 41 已结 / -0.790U / -1.93%；75%市场+25%原始为 19 已结 / +0.910U / +4.79%，仍未达 5%。该变量是本轮候选分析，**不是用户确认的生产规则，也没有独立时间留出**；不得将 +4.79% 当成可靠模型成绩。

最佳固定预测候选 M1 calibrated 的结算为全赢 22、半赢 5、全输 19、半输 3、走水 3。按 fixture 重采样 5,000 次的 ROI 95% 描述区间为 -19.40% 至 +27.40%，包含大幅亏损和盈利。报价源档案没有逐笔 bookmaker API receipt 的独立时间，扫描结束是保守时间上界；因此这里是依据赛前保存的 Crown 标注报价与 FT 的模拟收益，不是已成交账单收益。

全部模型与 Gate 候选结果、按联赛收益、最大回撤、数据 SHA 在 [`results/m1_ou_crown_small_archive.json`](results/m1_ou_crown_small_archive.json)。小样本的每联赛数值高度不稳定，不据此增删联赛或新增门槛。

## MR1 Crown 回放基准与可比性

公开 M4 Actions run [`41425306084`](https://github.com/ljm198964-alt/quant-runner/actions/runs/41425306084) 保存的 `m4_paired_research.json` 生成于 2026-11-02T10:02:50Z。以每场每市场一个最新有效赛前 Crown 快照回放，严格验证 FT 在开赛后，AH 和 OU 各 1,563 场：

| 市场 | 唯一比赛 / 模拟单 | 全赢 | 半赢 | 全输 | 半输 | 走水 | 净收益 | ROI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AH（MR1 历史选择，非 M5） | 1,563 / 1,563 | 614 | 141 | 637 | 76 | 95 | -44.195U | -2.8276% |
| OU（MR1 历史选择，非 M5） | 1,563 / 1,563 | 647 | 111 | 646 | 94 | 65 | -46.430U | -2.9706% |

该回放是统一规则的 MR1 反事实历史快照，不是正式 Telegram 结算成绩。公开 Artifact 只保留按市场/联赛聚合，不含逐场价格和顺序，因此本报告不为它虚报最大回撤。其比赛范围/日期与 M1 的 52 场 Crown OU 不相同，ROI 不能直接当模型优劣比较。

## M5-C：本机 MR1 存档的 Crown 赛前快照回放（新增只读复核）

脚本 [`mr1_local_crown_replay.py`](mr1_local_crown_replay.py) 只读复核本机现存 MR1 forward 记录，并以 MR1 已冻结的竞赛范围和逐场 FT 结果做重放。生成时间 `2026-11-04T15:21:50.351807Z`；输入代码 HEAD `245dec16bd56a3e71081e106b9543592e61bd644`；范围配置 SHA-256 `6c4fc5654162e93a29c8233ade09df710959a9ff378b9ae5a9a62de7b9ecd7bb`；所读 source snapshot 清单 SHA-256 `48327b9e3dea24371c2fb034f1cd7061c0605bd30663de156f026344cacdbaf6`。只将汇总、时间范围和哈希写入公开仓库，不公开私有逐场数据。

输入盘点为 18,607 个 forward 文件、2,182 个 verified FT 文件；12,349 个 Crown 标注快照同时满足 verified Crown、quote received 严格早于 kickoff、FT observed 严格晚于 kickoff、fixture identity 一致，并且全部位于 MR1 已配置范围。多时点快照去重后得到 **1,621 场**唯一比赛，覆盖 104 个输入联赛名（所选有效样本覆盖 91 个联赛）。Kickoff 范围 `2026-10-08T12:30:00Z`–`2026-11-03T23:20:00Z`；报价接收范围 `2026-10-08T11:34:05Z`–`2026-11-03T10:51:33Z`。这比公开 M4 Actions 报告的 1,563 场数目更多，但两边没有逐场公开清单可用于证明集合包含关系或准确差额归因；应作为独立本机快照报告，不能冒称 M4 新 Actions 验收或“新增 58 场”。

每场每市场选取最后一条 MR1 已保存、经过验证且严格赛前的 Crown 合约，每笔固定 1U，按亚洲盘全赢/半赢/走水/半输/全输结算；AH 和 OU 完全分开。结果：

| 市场 | 唯一比赛/已结 | 全赢 | 半赢 | 全输 | 半输 | 走水 | 净收益 | ROI | 最大回撤* |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AH（MR1 历史选择，非 M5） | 1,621 | 626 | 144 | 670 | 82 | 99 | -67.655U | -4.1737% | 71.295U |
| OU（MR1 历史选择，非 M5） | 1,621 | 666 | 112 | 674 | 97 | 72 | -57.985U | -3.5771% | 73.825U |

\* 最大回撤按相同 Crown quote-received UTC 时间视作同时事件计算；同时间事件内部排序不影响回撤。不是实际成交或正式账本回撤。

诊断字段显示：AH 平均保存模型 EV +0.220%，实际 ROI -4.174%；OU 平均保存模型 EV +5.657%，实际 ROI -3.577%，OU 实际收益减平均 EV 为 -9.234 个百分点。OU 选择 Under 1,500/1,621 场，Under ROI -3.912%；Over 仅 121 场，ROI +0.574%。AH 平均报价年龄 151.5 分钟、OU 220.4 分钟。方向、quote age、horizon 分组均为**事后描述**，不证明因果，不是新门槛；尤其报价年龄是保存元数据口径，不能替代独立成交证明。详细联赛/方向/时距/年龄聚合在 [`results/mr1_local_crown_replay.json`](results/mr1_local_crown_replay.json)。

这仍是 MR1 历史模型选择的重放，**不是 M5 样本外预测或 M5 ROI**。该快照仅约四周，且 MR1 保存方向和逐场训练样本无法在公开数据中重新拟合；结果不应外推长期收益。私有仓库未改、未访问网络或凭证、没有写入 M1/MR1/M3 正式链路、账本或 Telegram。

## M5-D：M3/M5 2026/27 样本外预测与 Crown 精确盘口回放

脚本 [`m3_crown_exact_line_replay.py`](m3_crown_exact_line_replay.py) 把公开 M3 最新严格赛季前推预测与 MR1 本机 V23 已保存快照按“联赛代码 + UTC 开球日期 + 规范化主客队”精确连接。取 M3 唯一输出概率支持的 **AH0** 和 **OU 2.5** Crown 报价；每个 fixture/market 选最后一条 quote observed 时间，且同时要求 Crown 验证标记为真、`observed_at <= received_at < kickoff`。所有 121 个连接比赛都属于 2026/27 OOS 季；M3 每模型训练截至时间严格早于 kickoff，模型间赛果/赛季/训练截止一致。对实际结算使用 M3 保存的真实赛果；公开 M3 OOS 报告的来源为 Football-Data.co.uk 真实比赛 FT。

生成 UTC `2026-11-04T15:42:09.893870Z`。M3 输入预测 CSV SHA-256 `9375bdbbb60e7b3c9e71d13bdc7f9e0d6ec57649579a4c2e4a14b9cbf4de8cc0`，源 M3 OOS 报告生成于 `2026-11-04T11:59:53.779352Z`。候选精确连接 122，因 1 个 MR1 身份键碰撞排除后为 **121 场**，开球时段 `2026-10-09T18:45:00Z`–`2026-11-02T20:00:00Z`。Crown 目标线覆盖：AH0 **24 场**，OU2.5 **36 场**，两市场均有的 8 场。也就是在 121 个精确连接 fixture 中，AH0 Crown 双侧完整报价覆盖 19.8%，OU2.5 覆盖 29.8%。其余比赛不能用其他 AH/OU 线替代，因为 M3 发布预测文件没有完整比分矩阵。

所用 AH0 Crown 报价观测范围 `2026-10-08T20:53:12Z`–`2026-11-01T15:15:06Z`，接收范围 `2026-10-09T15:09:38Z`–`2026-11-01T15:41:43Z`；OU2.5 观测 `2026-10-08T07:17:10Z`–`2026-11-01T19:08:24Z`，接收 `2026-10-09T18:20:48Z`–`2026-11-01T19:10:46Z`。所有匹配价格严格早于对应开球。每个可用 fixture/market 均模拟一笔 1U：在两边中选择模型期望收益较高的一边，**无 EV 正值门槛**；AH0 按全赢/走水/全输，OU2.5 按赢/输结算。没有同场重复计数。

M5 的 AH 权重只用 2018/19–2025/26 的逐季 OOS 预测训练（14,329 场），应用于 2026/27；权重为 Poisson 24.50%、Dixon-Coles 51.91%、Bivariate Poisson 23.59%。OU 权重由相同此前赛季 OOS 训练结果给出 Bivariate Poisson 100%，其余为零，所以该 OU M5 仍等同 Bivariate Poisson 单模型。权重不是在当前 Crown 测试集调参。

### M3 各模型与 M5：M3 真实赛果 + Crown 精确线回放

| 市场 / 策略 | 比赛 / 注 / 已结 | 全赢 | 全输 | 走水 | 净收益 | ROI | 95% fixture bootstrap ROI 区间 | Log Loss | Brier | 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AH0 Poisson | 24 / 24 / 24 | 12 | 5 | 7 | +5.910U | +24.625% | -5.42%–+53.54% | 1.076412 | 0.650943 | 3.000U |
| AH0 Dixon-Coles | 24 / 24 / 24 | 12 | 5 | 7 | +5.910U | +24.625% | -5.42%–+53.54% | 1.073643 | 0.649483 | 3.000U |
| AH0 Bivariate Poisson | 24 / 24 / 24 | 12 | 5 | 7 | +5.910U | +24.625% | -5.42%–+53.54% | **1.072938** | **0.649091** | 3.000U |
| AH0 M5 walk-forward blend | 24 / 24 / 24 | 12 | 5 | 7 | +5.910U | +24.625% | -5.42%–+53.54% | 1.074093 | 0.649717 | 3.000U |
| OU2.5 Poisson | 36 / 36 / 36 | 16 | 20 | 0 | -5.540U | -15.389% | -46.61%–+16.42% | 0.694815 | 0.250781 | 10.090U |
| OU2.5 Dixon-Coles | 36 / 36 / 36 | 16 | 20 | 0 | -5.540U | -15.389% | -46.61%–+16.42% | 0.694818 | 0.250782 | 10.090U |
| OU2.5 Bivariate Poisson | 36 / 36 / 36 | 18 | 18 | 0 | -1.660U | -4.611% | -36.03%–+26.94% | **0.694174** | **0.250460** | 8.260U |
| OU2.5 M5 walk-forward blend | 36 / 36 / 36 | 18 | 18 | 0 | -1.660U | -4.611% | -36.03%–+26.94% | **0.694174** | **0.250460** | 8.260U |

上表是小型、真正同价 Crown 回放。AH 名义 ROI 虽高于 5%，但 n=24 的 10,000 次按 fixture 有放回重采样区间仍跨过零；不能称为已经达成 10,000 场盈利目标。OU 未达到 5%。三种 AH 模型在这 24 场选择了完全相同的方向，因此收益完全相同；微小 proper score 差异不构成融合带来收益提升的证据。

### MR1 与 M3/M5 同一 Crown 盘口、同一接收时点对照

在 24 个 AH0 / 35 个 OU2.5 的 M3 与 MR1 保存选择盘口线、所选侧价格、接收时间完全吻合 fixture 中，MR1 独立 verified FT 文件覆盖分别为 **11 场 AH、21 场 OU**。仅在此严格相同报价与 MR1 verified FT 子样本对比：

| 市场 / 策略 | 去重比赛 / 注 | 净收益 | ROI | 95% bootstrap ROI 区间 | Log Loss | Brier | 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AH0 M5 walk-forward blend | 11 / 11 | +3.300U | +30.00% | -14.45%–+71.45% | 1.054758 | 0.633163 | 1.000U |
| AH0 MR1 保存选择 | 11 / 11 | +1.700U | +15.45% | -31.91%–+60.91% | 不适用 | 不适用 | 2.000U |
| AH0 M3 Poisson / Dixon-Coles / Bivariate（同向） | 11 / 11，各 | +3.300U | +30.00% | -14.45%–+71.45% | 1.054925 / 1.055229 / 1.053761 | 0.633231 / 0.633477 / 0.632527 | 1.000U |
| OU2.5 M5 Bivariate blend | 21 / 21 | -5.750U | -27.38% | -64.19%–+11.24% | 0.722651 | 0.264496 | 7.310U |
| OU2.5 MR1 保存选择 | 21 / 21 | -5.970U | -28.43% | -64.67%–+8.48% | 不适用 | 不适用 | 7.000U |
| OU2.5 M3 Poisson / Dixon-Coles（同向） | 21 / 21，各 | -5.740U / -5.740U | -27.33% / -27.33% | -64.33%–+11.38% | 0.720292 / 0.720335 | 0.263369 / 0.263390 | 8.090U / 8.090U |

这张表是目前唯一将 MR1 与 M3/M5 放在完全相同 Crown 合约、时点和实际 FT 上的直接对照，样本很小，置信区间很宽。M1 的旧 Crown OU 样本与该日期范围没有可用的相同盘口时点连接；现有精确 M1/M3 重叠总数仍只有 2 场，不能作 M1 同口径 ROI 比较。MR1 这里是保存的研究选择，不是正式 TG 实战成绩。

M5 按联赛的描述性分布（只显示该小型报价样本，禁止事后筛联赛）：AH：B1 n=1 +0.79U；E0 n=8 +1.75U；F1 n=6 +3.74U；I1 n=8 -0.37U；SP1 n=1 0U；D1 本样本无 AH0 线。OU：B1 n=2 +0.03U；E0 n=9 -1.46U；F1 n=8 -2.49U；I1 n=15 +0.25U；SP1 n=2 +2.01U；D1 无 OU2.5 线。样本稀疏且仅为六个 M3 支持联赛中的五个，不能据此冻结联赛规则。

完整逐季 OOS 与融合权重报告仍见 [`results/m5_probability_stack_oos.json`](results/m5_probability_stack_oos.json)；本轮 Crown 精确线回放的代码、逐市场/模型及联赛安全聚合、引导区间和输入哈希见 [`results/m3_crown_exact_line_replay.json`](results/m3_crown_exact_line_replay.json)。私有 source 行、队名、赔率和 fixture identity 未公开。

## M5-E：同期全比分网格与 Crown 任意主盘探索（非主要 OOS 证据）

脚本 [`m3_grid_crown_replay.py`](m3_grid_crown_replay.py) 读取公开 M3 `M3_TOTALCORNER_FORWARD_FORECAST_V1` 网格账本，与只读 MR1 本机 V23 verified Crown 快照以 TotalCorner fixture ID、球队身份及注册表中的 UTC kickoff 连接。修正了 provider 本地日期与 UTC kickoff 日期可跨日的问题：日期差异只记录为审计计数，fixture 身份以 provider ID、两队和已注册 UTC kickoff 核验。全账本 2,932 条网格的 `score_grid_sha256` 均可重算；本回放中 39 个 fixture ID 有完整三模型网格，其中 18 个有赛前 Crown 主盘快照及三模型网格；再与 M3 严格赛季 OOS CSV 交叉后有 17 场。每个盘口使用最晚有效的赛前 Crown quote，且所用模型网格生成时间不晚于该 quote 的 `observed_at`。每场市场 1U、选择预测期望收益较高的一侧，没有 EV 门槛。AH 与 OU 分开结算。

此网格账本来自 M3 penaltyblog 模型及只读历史比分缓存，不是 M1 预测、参数、订单或账本；训练源缓存没有随网格逐条封存历史内容哈希和结果可得时间。因此 forecast UTC 早于目标比赛、训练比赛开赛早于拟合时间这些时间字段仍不足以独立证明训练输入当时已完整可用。本节只是同期预测覆盖扩展，**不替代严格 OOS 主结果**。M5 权重仅从此前严格 M3 OOS 赛季拟合后转用至此数据，属于探索性迁移。

生成 UTC `2026-11-04T16:04:48.417796Z`。样本开球范围、引用输入 hash 及按模型汇总均见 [`results/m3_grid_crown_replay.json`](results/m3_grid_crown_replay.json)。五种模型在当前小样本选边相同，因此收益一致：

| 市场 | 注数 | AH 全赢/半赢/走水/半输/全输 | OU 全赢/半赢/走水/半输/全输 | 净收益 | ROI | 95% fixture bootstrap ROI 区间 | M5 最大回撤 |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| Crown AH 任意主盘 | 17 | 7 / 1 / 1 / 1 / 7 | — | -0.245U | -1.44% | -44.50%–+42.12% | 3.90U |
| Crown OU 任意主盘 | 17 | — | 6 / 0 / 1 / 1 / 9 | -3.980U | -23.41% | -63.47%–+19.29% | 7.63U |

本结果仅适用于全比分网格允许的任意 mainline，不能和 AH0/OU2.5 的 24/36 场结果拼接为更大样本；两者有重叠 fixture，输出概率协议和报价选择亦不同。另有 18 场全网格 Crown 覆盖（含一场不在严格 OOS CSV 的比赛），但上述统一表只报告 17 场严格 M3 CSV 交集。所有报价均来自验证为 Crown 的快照，未用其他公司价格。队名、报价、fixture ID 和网格未公开。

## 当前交付指标与剩余缺口

| 要求 | 当前证据 | 状态 |
| --- | --- | --- |
| ≥10,000 场真实去重比赛 | Partial manifest 47,496 场候选、45,240 场真实 OOS；Crown endpoint AH/OU各212，MR1 archive各327 | 概率达标；有效 Crown 价样本未达标 |
| AH / OU 独立评价 | AH 1X2代理、OU2.5 proper score分别统计；Crown AH/OU 分源回放 | 已有部分真实 OOS；Crown样本小且仅2026一年 |
| M1/MR1/M3 同场同价比较 | M3严格 OOS概率共同样本7,057；M1冻结Crown OU同价/FT配对n=6；MR1精确saved selection匹配0 | AH/OU同价交集仍很小 |
| 样本外 ROI >5% | TotalCorner AH +2.7665% (n212)、OU -0.2830%；MR1 AH +0.3440% (n327)、OU -6.5076% | AH/OU均未达到 >5% |
| 当前范围完整覆盖 | 冻结模型manifest时固定51个 M1 scope IDs 中19个已有 page-1；已知1,871页保存1,676、缺195 | 未完成 |
| 自动训练和版本比较 | 本地真实模型及新旧模型评估已运行；没有 M5 Actions运行/成功/结果落库 | 未验收 |
| 研究数据追溯与系统隔离 | 公布聚合和输入哈希；逐场forecast/赔率留在仓库外 | 已做到；不代表Actions可复跑 |

M5 尚未达到完成标准。要完成目标，仍需在既定赛事范围内继续获取并验证历史赛程与 Crown AH/OU 同期报价，达到每市场 10,000 个独立可结算 OOS fixture；独立 OU ROI 仍须超过5%。本报告的本地研究回执不构成 M5 Actions 验收。

# 2026-11-04/05 M5 逐联赛概率融合与历史 Crown 覆盖扩展

## 逐联赛权重：严格赛季前推结果

新增 `probability_stack_league_oos.py`，在同一 M3 三模型、同一唯一赛事 OOS 样本上比较：此前 OOS 季节训练的全局融合、仅用该联赛此前 OOS 预测训练的联赛局部融合、以及用此前该联赛 OOS proper score 选出的单模型。每个测试赛季的训练只使用更早赛季，AH 1X2 与 OU O2.5 独立拟合；训练/测试比赛键隔离，完整输入 hash、逐季权重与逐联赛分数见 [`m5_league_local_probability_oos.json`](results/m5_league_local_probability_oos.json)。这仍是概率评分研究，不含 Crown 价格、模拟下注或 ROI。

| 市场 | 方法 | 严格 OOS 比赛 | Log Loss | Brier |
| --- | --- | ---: | ---: | ---: |
| 1X2（AH 概率代理） | 全局融合 | 13,234 | 1.00357664 | 0.59922137 |
| 1X2（AH 概率代理） | 逐联赛融合 | 13,234 | **1.00336120** | **0.59908628** |
| 1X2（AH 概率代理） | 逐联赛前史最佳单模型 | 13,234 | 1.00342791 | 0.59913180 |
| OU O2.5 | 全局融合 | 13,234 | **0.74579735** | 0.24594767 |
| OU O2.5 | 逐联赛融合 | 13,234 | 0.74590343 | **0.24587484** |
| OU O2.5 | 逐联赛前史最佳单模型 | 13,234 | 0.74590343 | 0.24587484 |

逐联赛融合让 1X2 OOS Log Loss 降低 0.00021544；OU Log Loss 比全局融合高 0.00010608，且与局部最佳单模型完全相同。变化非常小，没有 Crown 收益验证，不能据此声称盈利能力或达到 ROI 目标。AH 的 1X2 三分类分数只作为 AH 概率代理；结算 ROI 仍须以真实 Crown AH 线价和独立亚洲盘结算计算。

## 历史 Crown 数据扩展状态

额外只读审计发现本机 MR1 V23 有 32,866 条快照记录、17,422 条有明确 Crown 标签及 AH/OU 时间线字段，但涉及 3,699 个登记 fixture；其中只读模型/赛果回放严格通过赛前 Crown 与赛后 FT 验证的有效唯一样本仍为 AH/OU 各 1,621，而不是 17,422 场。M1 正式一级联赛策略范围的现有本机 TotalCorner schedule ID 去重后只有 8,140 场，单靠本地已存赛程无法满足 10,000 场要求。

为保持 M1 现有正式范围不变，新增一次性私有采集器 [`crown_historical_capture.py`](crown_historical_capture.py)，只调用 TotalCorner League Schedule 与明确 `bookmaker=crown` 的 `match/bookmaker_odds` 端点，固定使用 M1 正式一级联赛白名单，按 3.1 秒串行请求、断点续跑，并强制将原始响应写到仓库外的私有目录。单条历史 Crown movement API 探针成功返回 AH/OU 时间线；历史原始赔率及身份仍不公开。初查来自历史批次的 37 个 M1 scope 联赛 ID 时分页约 3,274 页；随后从 MR1 V23 fixture registry 又核实出 14 个此前未在历史批次映射中的 M1 正式范围 league ID，目前私有采集清单已校正为 **51 个**，新增 14 个的分页数仍待请求，全范围总页数尚未最终确定。全量分页与后续 Crown AH/OU 覆盖回填尚在运行中，尚无可报告的历史回填样本数或 ROI。

官方接口说明列出 `match/bookmaker_odds/{match_id}` 可按 `bookmaker=crown` 返回 asian/goal movement，行内含比赛分钟、盘口、双方水位、来源本地时间及 closed 标记；接口限速为每分钟 30 次且按 10 秒窗口计数。官方条款注明自动抽取需要 prior written consent。用户已明确要求复用现有授权；本轮未申请新授权、未输出凭证或赔率。实际回填严格串行低于公开限速。工作流/Actions 尚未创建或触发，采集是单次本地研究执行，不涉及生产运行。

## 2026-11-05 续跑检查与独立进球模型候选

本轮只对公开 M5 研究文件做修改；没有写 M1/MR1/M3 生产仓库、正式账本或 Telegram。由 MR1 V23 registry 校正出的 51 个 M1 一级联赛 ID 清单在本机私有目录，API 历史分页恢复执行。截至最终私有磁盘扫描，10 个联赛已有 page-1 元数据，其已知总分页 1,032 页，已保存 822 页、缺 210 页，共解析 24,570 条 schedule rows；本地条件筛出的完赛候选 ID 约 23,763 个（非 Crown 验证数）。停止进程前 checkpoint 为处理 400 页、11,937 行；累计错误 9 次 `TOO_MANY_REQUEST`、1 次 `URLError`、3 次 `SSLError`。由于分页未完成、报价和逐场身份尚未逐项 Crown 核验，候选数不能视作最终覆盖。

新增 [`m5_goal_model_oos.py`](m5_goal_model_oos.py)，为完全独立的主客进球率 Poisson 候选：每联赛按 UTC 日历年 walk-forward，ridge 只由紧邻的更早验证年选择，产出 15x15 比分分布和 AH/OU 概率；逐场输出强制在仓库外，公开端仅含输入哈希与聚合 proper score。验证了未见球队按队独立采用中性回退，以及预测网格概率总和为 1。已完成语法编译和 40 场合成拟合/概率质量核对；**没有真实历史 OOS 模型结果**，因为 51 联赛候选 manifest 尚未生成。

本地长请求期间出现 TLS 握手挂起，当前前台分页过程已停止。采集器可从已保存页恢复；网络稳定后应先跑完全部 51 个 league 的 schedule 分页、重试缺页，再从完赛 fixture 精确回填 Crown AH/OU movement 并校对球队、联赛、UTC kickoff 与 FT，最后按严格时间切分生成预测并与赛前报价配对。**本轮没有完成 Crown backfill、真实 M5 ROI、真实 OOS 训练、GitHub Actions run 或 M5 Actions 落库验收；现有 M3/M5-Crown 小样本 n=24/36 仍为最新可报告回放。**

## 2026-11-05 M5 独立 Poisson OOS 与 M3 同场评分对照（扩样版）

由本机私有 partial manifest 重训 M5 独立主客进球率 Poisson：固定 M1 正式一级联赛范围共51个 league IDs，19个已有 page-1，1,871个已知 schedule 页中保存1,676、缺195。partial manifest 有 **47,496 场唯一完赛候选**；按联赛、UTC比赛日、规范化主客队识别并排除2组共4行重复身份。赛程覆盖不完整，manifest SHA-256 `87d5c5d7560aa740a6209ae8c91851dfa653f6517af6b6e06a6b232df24e3215`，明确 `complete_historical_universe=false`。

模型对每联赛按 UTC 日历年逐年 walk-forward；只用早年完赛赛果训练，前一历史年选择正则化参数，训练最晚 kickoff 早于所有测试 kickoff。输出 **45,240 场真实历史 OOS 预测，190 折**，预测逐场文件在本机私有目录，SHA-256 `8b36e7753c5ae55814f7878411cc4c5befeaeb1fc394bd1bb3a1ce58ff31f9f3`。汇总结果生成于 `2026-11-04T18:43:17.185979Z`：AH 1X2 三分类代理 Log Loss/Brier **1.00484221/0.59932383**；OU O2.5 **0.69396022/0.24954746**；精确比分 Log Loss **2.95909737**。这些是 proper scores，不是 Crown ROI。

按 M3 原版严格 OOS CSV（SHA 与文件路径见结果 JSON）、日期、联赛、主客队及比分精确连接，共 **7,057 场**。同场 AH 1X2 代理：M3 Dixon-Coles LL/Brier **1.01136529/0.60459202**，M5 **1.01452728/0.60678202**；OU2.5：M3 Poisson **0.69355265/0.24987741**，M5 **0.69240841/0.24940439**。独立 M5 Poisson 的 AH 代理未胜 M3 最佳，OU proper score 则略胜 M3 Poisson。按此前共同 OOS 预测逐 UTC 年拟合后评估 6,698 场：M3+M5 融合 AH LL/Brier **1.01148357/0.60479312**，略胜单模型；OU **0.69157433/0.24902346**，权重退化至 M5 单模型。以上是 proper-score 变化，不是 Crown ROI。

详细逐年、逐联赛指标、切分/训练回执、输入哈希分别见 [`results/m5_goal_model_partial_oos.json`](results/m5_goal_model_partial_oos.json)、[`results/m5_goal_model_m3_common_oos.json`](results/m5_goal_model_m3_common_oos.json)、[`results/m5_goal_model_nested_blend.json`](results/m5_goal_model_nested_blend.json)。

### Crown 报价时点、赔率与盘线变化因素（探索性描述）

新增 [`m5_crown_factor_audit.py`](m5_crown_factor_audit.py) 与 [`results/m5_goal_model_crown_factor_audit.json`](results/m5_goal_model_crown_factor_audit.json)。最新 OOS forecast SHA 更新后，TotalCorner Crown endpoint 有效配对仍为 AH/OU 各 212 场。按 quote-to-kickoff 年龄、模型择侧价位、首个 forecast 后有效盘线到最新线的绝对变化、择侧水位变化作样本内四分位描述；并列线值使分组数不等。AH 各时间组 ROI -8.42% 至 +17.18%，OU -16.21% 至 +15.98%；AH 价位组 -8.88% 至 +16.70%，OU -20.76% 至 +25.83%。OU 最大盘线变化组仅18场，+59.97%，是极小事后子组。这里没有冻结或加入盘口/时间/水位 Gate，也未作为独立样本外策略。

### Crown OOS 回放指标（AH、OU 独立统计）

以下两个 quote source cohort **分开列示、不合并**。每行“预测池比赛数”是当前forecast内该市场可能被覆盖的唯一 OOS fixture 数；有效 Crown 样本也是实际模拟下注与结算数。没有EV过滤，命中一个有效预测×报价×FT即在该市场模拟1U。TotalCorner source 回放赛果来自同一 endpoint response；MR1 cohort另有独立赛后 verified FT receipt。

| 来源 / 市场 | 预测池唯一比赛 | 有效 Crown / 模拟 / 已结 | 全赢 | 半赢 | 全输 | 半输 | 走水 | 净收益 | ROI = OOS ROI | 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| TotalCorner historical Crown AH | 45,240 | 212 / 212 / 212 | 91 | 10 | 80 | 9 | 22 | +5.865U | +2.7665% | 9.620U |
| TotalCorner historical Crown OU | 45,240 | 212 / 212 / 212 | 88 | 15 | 81 | 19 | 9 | -0.600U | -0.2830% | 16.060U |
| MR1 verified Crown + FT AH | 45,240 | 327 / 327 / 327 | 134 | 22 | 123 | 23 | 25 | +1.125U | +0.3440% | 13.405U |
| MR1 verified Crown + FT OU | 45,240 | 327 / 327 / 327 | 132 | 19 | 138 | 27 | 11 | -21.280U | -6.5076% | 28.420U |

各 cohort 均只覆盖到2026 OOS年，ROI来自已结算投注，故样本OOS ROI与该 cohort ROI相同；AH与OU同一 fixture可各计一次，但各市场内部不重复。Crown报价样本远低于45,240场预测池，也远低于每市场10,000场要求；AH、OU均未超过5%。

#### Crown 来源与时序证据分级

| 类别 | 本轮证据 | 可支持的结论 | 不可支持的结论 |
| --- | --- | --- | --- |
| 实时 Crown API 诊断 | M3 固定历史 match ID 的六次 probe（最新 run `39584036612`）；不构成连续前瞻采集 | 证明既有 Crown 专属接口曾成功返回报价市场数据 | 不能证明完整赛前快照覆盖或 M3 当时已记录预测/报价配对 |
| TotalCorner Crown 历史 movement | M5 AH/OU 各 212 场；movement 自带 source event UTC 早于 kickoff，批量 response 是赛后回取，FT 与 movement 同响应 | 按历史事件时间做 Crown-only 研究回放；AH +2.7665%，OU -0.2830% | 不能称为 M3 系统赛前已收到的快照或真实成交；该 cohort 的 FT receipt 不独立于 quote response |
| MR1 V23 档案中的 Crown 快照 | 与 M5 OOS 预测精确配对 AH/OU 各 327 场；`observed_at <= received_at < kickoff`，FT receipt 在 kickoff 后，fixture identity 精确匹配 | 赛前有时间证据的历史 Crown 快照回放；AH +0.3440%，OU -6.5076% | 不能与 TotalCorner endpoint cohort 合并；不是当时 M5 已发出的预测或正式投注成绩 |
| M1 V23 同价子集 | OU 6 场，同一 Crown 合约及验证 FT，quote event 在 M5 年度 forecast as-of 与 kickoff 之间 | 仅作小样本同价算法对照 | 不代表 M1 正式账本，也不能外推模型胜负 |

所有 ROI 均是固定一单位的历史影子回放，模型用时间前推的留出赛季概率；预测本身不是当时归档的 M5 单据，故不得表述为真实成交或当时生效的 M5 OOS 信号。只允许 Crown 作为交易赔率来源；公开文件不含逐场价、球队或 fixture ID。

### M1 V23 与 M5 同 Crown 合约配对（OU；前版结果）

新增 [`m5_m1_same_quote_oos_replay.py`](m5_m1_same_quote_oos_replay.py) 与 [`results/m5_goal_model_m1_same_quote_oos.json`](results/m5_goal_model_m1_same_quote_oos.json)。M1 V23 有56场冻结 Crown OU eligible observation；其中6场通过 TotalCorner fixture ID、球队、kickoff、Crown OU盘口/双方水位、quote event 位于 M5 UTC OOS forecast as-of 之后且 kickoff 之前，以及 M1 verified FT receipt 的精确连接。六场使用同一 Crown 合约、每模型一注：M5 Poisson +2.025U/+33.75%；M1 frozen `crown_market_poisson` +2.055U/+34.25%；M1 calibrated +1.150U/+19.17%；M1 raw -2.500U/-41.67%；两个既有 market-blend 分别与对应 calibrated/raw 结果相同。M1 expected-total 按原 sanitized replay 方案转换为 Poisson count 分布。n=6，不能据此选择策略或外推 ROI；不代表 M1 正式账本成绩。M3 同 Crown 的可比子样本来自另一 MR1 quote archive，只有 OU n=9、AH n=5，未与 M1 六场拼接。

| 相同 Crown 合约的配对研究 | 市场 | 配对场 | M5 | 可比模型结果 |
| --- | --- | ---: | ---: | --- |
| M1 V23 frozen archive | OU | 6 | +2.025U / +33.75% | M1 Crown-market Poisson +2.055U/+34.25%；calibrated +1.150U/+19.17%；raw -2.500U/-41.67% |
| MR1 archive + M3 strict OOS | AH0 | 5 | +2.880U / +57.60% | M3 Poisson、DC、Bivariate 各+2.880U/+57.60% |
| MR1 archive + M3 strict OOS | OU2.5 | 9 | -3.490U / -38.78% | M3 Bivariate -1.660U/-18.44%；Poisson/DC 各-5.330U/-59.22% |

这些对照用了各自 cohort 的完全相同 Crown line/price/event与 FT；cohort 互不合并，样本量都不足以判断稳定优劣。

### 本轮 Crown 接口实证与回填配对修正

针对本地已存完赛比赛执行了一次明确 `bookmaker=crown` 的单场历史端点请求，HTTP 200，返回 exact match 1 条、Crown book 1 条、AH/OU movement 分别 94/57 行；响应未保存为公开文件。修正报价回填候选筛选：只对与 M5 样本外预测按唯一 fixture ID、球队、联赛、UTC kickoff 和 FT 全一致的比赛发请求；已运行的第一轮发现先前抓取的 70 个早期训练赛响应与 OOS 预测交集为 0，随后停止，不计作预测覆盖。

第二轮仅包含 23,812 个 M5 OOS fixtures 的 Crown-only 请求按 ≥3.1 秒串行；回填原始 JSON 在仓库外、目录权限 0700/文件 0600。代码要求来源报价时间不早于预测有效时间、不晚于 kickoff，且模型比分分布与对应线价使用相同合同进行 AH/OU 拆腿结算。该采集仍未完成，过程 checkpoint 见下节；也没有触发 M5 Actions。可从本机原始文件和 `quote-progress.json` 续跑。

## 历史基线（早期 23,812 / 34,322 / 39,574 场 forecast 版本，已由 45,240 场回执更新）

以下过程记录保留以审计版本演进；不得与最新 45,240 场 forecast 的分母或回放数字混用。

## 早期 Crown OOS 回放记录（已由 45,240 场 forecast 版本更新）

本文件早期段落记录 n=153 MR1 和 n=135 endpoint 的上一版预测回放，仅用于审计历史版本。后续重放在最新 45,240 场预测 SHA 上得到当前成绩，应以本报告前述“扩样版”及结果 JSON 为准，切勿混用各版本的分母和 ROI。

## 2026-11-05 最新复核：扩样后的 OOS 与 Crown 证据分层

本节覆盖此前报告中的 45,240 场版本；其旧报告和哈希仍保留供历史审计，所有比较应以本节及同名最新 JSON 为准。数据冻结时间 `2026-11-04T19:04:37.678707Z`。固定的 M1 正式范围为 51 个联赛，本轮有 page-1 的 23 个，已知 schedule 页 2,244 个、已保存 2,087 个、缺 157 个；59,398 场唯一完赛候选，赛程宇宙明确不完整。manifest SHA-256 `31e102f1d7e725180426c083bfd41c1ac8779d200b52a4b3cd399c3e3ebaabc5`。

M5 独立 Poisson 按联赛和 UTC 日历年严格前推，训练截止早于每场测试 kickoff，共 56,688 场、245 个联赛×年份折；逐场预测私有文件 SHA-256 `4fb9799d59e5a856248a00d04343e29e0cce83e9e0780c7ef57d4d6dca84c201`。AH 1X2 代理 Log Loss/Brier `1.00110378/0.59645491`，OU2.5 `0.69574444/0.24993771`，精确比分 Log Loss `2.96542764`。这些评分不使用 Crown 价格且 ROI 为 null。

与 M3 最新严格 OOS 预测精确同场为 7,611 场。AH 1X2 代理，M3 Dixon-Coles LL/Brier `1.01027079/0.60383377`，M5 `1.01344007/0.60606501`；OU2.5，M3 Poisson `0.69287590/0.24956476`，M5 `0.69260889/0.24948956`。嵌套前推融合在 7,611 场上 AH `1.01026866/0.60395241`，OU `0.69183147/0.24913458`；AH 轻微改善，OU 未胜单独 M3 Poisson（`0.69171096/0.24904839`）。详见对应 JSON 的逐年记录和 SHA。

### Crown 数据证据等级与独立结果

| 来源 | AH / OU 唯一样本 | 时间证据及用途 | 独立结论 |
| --- | ---: | --- | --- |
| 公开 M3 固定 ID live probe | 6 次诊断运行 | 实时只读探针，不是历史样本或赛前预测配对 | 最新 run `39584036612`；不计算 ROI |
| TotalCorner Crown 历史 movement endpoint | 212 / 212 | movement 源事件时间早于 kickoff，但响应在赛后取得，且 FT 同响应；作为历史 movement 回放，不能证明当时已收到报价 | AH `+5.865U / +2.766509%`；OU `-0.600U / -0.283019%`；不冒充同时接收的赛前快照 |
| MR1 V23 verified Crown 存档 | 387 / 387 | `observed_at <= received_at < kickoff` 且独立 verified FT 收据在 kickoff 后、fixture identity 精确；是有赛前接收时间证据的历史快照 | AH `-18.780U / -4.852713%`，最大回撤 `20.24U`；OU `-32.845U / -8.487080%`，最大回撤 `39.63U` |
| M1 V23 同价配对子样本 | AH 0；OU 7 | 精确同 Crown 合约、水位、M5 forecast 时间及 M1 verified FT | M5 `+1.025U / +14.642857%`；样本极小，不能外推 |

MR1 样本的结算分类 AH W/HW/L/HL/P=`151/24/157/28/27`，OU=`151/23/165/33/15`。另有 M3 在同一 MR1 报价上的 AH 5 场、OU 10 场小样本比较（AH `+2.88U/+57.6%`；OU Poisson/DC `-6.33U/-63.3%`、bivariate `-2.66U/-26.6%`），只作对照，不和其他来源 cohort 合并。所有收益按每场每市场 1U、亚洲盘拆腿结算；没有新增 EV、置信度、赛事或时效 Gate，也不是实际下注或当时已记录的 M5 预测。

### M1 同报价比较与自动化状态

M1 V23 和 M5 在相同 Crown OU 合约、双方水位与 verified FT 的精确交集为 7 场。M5 独立 Poisson `+1.025U/+14.642857%`；M1 market Poisson `+2.915U/+41.642857%`、calibrated `+2.010U/+28.714286%`、raw `-1.640U/-23.428571%`。其余混合方法对应既有 calibrated/raw 结果。n=7 不支持模型选择或泛化。

M3 每 4 小时 workflow 仍按原授权频率运行。最新可核实 run `41864900732` 于 `2026-11-04T16:16:39.480507Z` 成功（12/12 tasks）；严格 OOS CSV 有 17,151 个唯一测试行身份、14,806 行具有完整评分预测。该次源输入指纹及测试身份未变，9 项模型/市场比较分差均为零，故没有新增学习信息。M5 本轮没有 GitHub Actions run，不能把 M3 run 当作 M5 自动训练/落库验收。schedule pagination 本地进程仍在运行；本节冻结结果仅覆盖当时保存的数据，不把后续新增数据倒灌到该模型版本。

### 更新后的未完成项

- 51 个固定联赛中仅 23 个已有分页记录，历史赛程 universe 不完整。
- 没有每市场 10,000 场、具合法同期 Crown 价格和独立赛后 FT 的样本；没有达到 AH 与 OU 分别 ROI >5% 的验证目标。
- TotalCorner endpoint cohort 的源事件时间早于开赛，但响应后取且 FT 同响应；不得称为 received-forward Crown 快照。MR1 verified archive 虽有接收时间证据，但只覆盖 387 场/市场，历史模型选择背景也须单独说明。
- M5 Actions 自动重训/比较/持久化尚未触发验证。当前分支的公开代码/报告提交不等于 Actions 成功。
- Crown Factor audit 为描述性事后分组，不是筛选策略。原始 Crown 响应、逐场预测和凭证继续留在仓库外。

## 2026-11-05 后续采集增量：63,091 场版本（当前最新）

本节取代本报告前面 56,688 场、245 折那一节的“当前最新”身份；前版保留作历史快照。采集进程在用户既有授权下继续请求赛程页，本轮没有启动第二个并发采集器。冻结数据生成于 `2026-11-04T19:18:23.607999Z`：固定 51 个范围联赛中 26 个已有 page-1，已知 2,493 页、已保存 2,320、缺 173；66,094 场唯一 FT 候选，排除 2 个重复身份组。历史 universe 仍不完整。manifest SHA-256 `67af2a975ac20216312fe464ccd4fd58793e5b3092f351bca86495b406857f45`。

M5 独立 Poisson 严格 UTC 年×联赛前推 **63,091 场 / 275 折**，覆盖测试年 2015–2026；逐场 forecast 留在私有目录，SHA-256 `8bd28cfd85e08f005ca9a547b89f722fbd78ff8c232bf5387ed041d854c5c431`。AH 1X2 概率代理 LL/Brier `1.00244361/0.59755777`；OU2.5 `0.69492663/0.24955853`；精确比分 LL `2.95858364`。66,094 个候选中 3,003 个未进入可评分 OOS fold；不得将候选数当成 OOS 数。逐 UTC 年指标详见 `m5_goal_model_partial_oos.json`，不同年份评分有波动，并非稳定盈利证据。

与 M3 最新严格预测的精确同场比较为 **7,663 场**：AH 代理 LL/Brier，M3 Dixon-Coles `1.01000095/0.60367120`，M5 `1.01223291/0.60523473`；OU2.5，M3 Poisson `0.69321624/0.24972808`，M5 `0.69266069/0.24953371`。M5 AH 弱于 M3 最佳 proper score，OU 略优。嵌套权重选择后，在 7,252 场样本上 M3+M5 AH LL/Brier `1.00991517/0.60370237`，优于此评估样本内单模型；OU 权重退化到 M5 独立 Poisson，LL/Brier `0.69147091/0.24898142`。融合评估也属历史研究 OOS 分数，不等于 Crown 收益。

### 以当前 forecast SHA 重算 Crown 样本

| Crown 来源 | AH 有效赛/注 | AH 净收益 / ROI | AH 最大回撤 | OU 有效赛/注 | OU 净收益 / ROI | OU 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MR1 V23 verified Crown + 独立赛后 FT | 161 | `-5.385U / -3.344720%` | `11.920U` | 161 | `-8.300U / -5.155280%` | `16.945U` |
| TotalCorner Crown endpoint historical movement | 212 | `+5.865U / +2.766509%` | `9.620U` | 212 | `-0.600U / -0.283019%` | `16.060U` |

MR1 cohort 结算 AH W/HW/L/HL/P=`63/10/64/10/14`，OU=`64/10/65/12/10`；两市场都仅 2026 OOS 年。AH/OU 分别只有 161 个严格快照与 FT 样本，ROI 均未超过 +5%。TotalCorner 212 场的报价是 response 内 source-time movement，响应在赛后取回且 FT 同响应；仍不是当时接收的 pre-kickoff snapshot。两 cohort 不合并。当前回放只有每个预测 fixture-market 一注，不设 EV 阈值；这只是研究回放，不是实际下注。

同 MR1 Crown 合约上可精确连接 M3 预测的极小样本为 AH 4 场（M3 三个模型及 M5 均 `+2.02U/+50.5%`）、OU 5 场（M3 bivariate `+0.50U/+10%`，M3 Poisson/DC 与 M5 `-1.33U/-26.6%`）。样本太小且这不是全体 Crown 回测。M1 同价比较已在本轮重新运行：AH 无样本；OU 当前版本精确配对 n=9。M5 `+0.925U/+10.277778%`；M1 Crown market Poisson `+2.805U/+31.166667%`、calibrated `+3.800U/+42.222222%`、raw `-3.640U/-40.444444%`；两种既有 blend 分别等于其 calibrated/raw 对应项。仅9场，不应外推。

Crown 因素分位分析按当前预测 SHA 重算。AH 时间四分位 ROI 依次 `-6.44/-8.42/+8.75/+17.18%`，OU `+3.19/-4.09/-16.21/+15.98%`；盘线变化、价格分位也有大幅反转。每格约 47–113 场，分组为事后描述且使用了 TotalCorner historical movement 时间，受样本稀疏、响应时间限制与多重比较影响，不能据此创建交易 Gate 或宣称可复现优势。

### 本轮运行与后续

- 当前冻结 manifest 和 63,091 场 forecast 均留在私有路径，公开仓库仅保存汇总、时间分层和 SHA。
- 原有 schedule discovery 进程 PID 1267 在本节生成时仍存活，并持有 TotalCorner HTTPS 连接；不要启动第二个 schedule/quote 请求。下一次训练应先再次冻结 manifest，以便输入版本与结果哈希一致。
- M3 Actions 最新成功 `41864900732`；M5 Actions 仍未运行，不构成 M5 自动化验收。此分支代码/结果推送也不等于 Actions 成功。
- 当前最好实测收益仍是 TotalCorner endpoint AH `+2.766509%`，不足 +5%；MR1 verified cohort AH `-3.344720%`、OU `-5.155280%`。没有市场达到目标。每市场 10,000 个 received-before-kickoff Crown+FT 样本、全 51 联赛历史赛程、当前版本 M1 同价对照和 M5 自动回测仍未完成。


### 当前 M1 同价回执补充（2026-11-04T19:30:16Z）

在最新 forecast SHA `8bd28cfd85e08f005ca9a547b89f722fbd78ff8c232bf5387ed041d854c5c431` 上重跑 M1 V23 OU exact quote / verified FT 配对，冻结档案 56 个 eligible fixture 中有 9 场通过 fixture ID、球队、UTC kickoff、Crown OU line/双水位、报价 event 在模型 as-of 后且 kickoff 前、独立 verified FT 的全部精确检查。AH 没有该协议的可比样本。每算法每场 1U：M5 `+0.925U/+10.277778%`，M1 market Poisson `+2.805U/+31.166667%`，calibrated `+3.800U/+42.222222%`，raw `-3.640U/-40.444444%`；市场校准 blend/raw blend 分别等于对应基模型。9 场各模型结算 W/HW/L/HL/P 分类（M5 `4/1/3/0/1`；M1 market Poisson `5/1/2/0/1`；calibrated `6/0/1/1/1`；raw `2/0/5/1/1`）。样本太小，分数不能说明模型泛化或超越 >5% 目标；这不是 M1 production ledger。完整输入哈希只在脱敏 JSON 留存。

## 2026-11-05 再扩样快照：69,171 场 OOS（当前最新）

这是本轮当前权威版本，覆盖前述 63,091 场版本。schedule discovery 持续运行时另冻结快照，UTC `2026-11-04T19:31:40.785863Z`：固定 51 个联赛中 29 个已有 page-1，2,777 个已知页面、2,543 已保存、234 缺失；72,446 个去重 FT 候选，2 组重复身份被排除。manifest SHA-256 `ab5346c7513fa3551c1bd18791e218ec7c557ad91b9b16afadbb66fd5251dfd8`。这是明确的 partial universe。

M5 独立 Poisson 按联赛和 UTC 日历年 walk-forward，产出 **69,171 unique OOS fixture / 309 folds**，2015–2026 各年都有 OOS 预测。逐场文件保存在私有目录，SHA-256 `817370d18a9d60b835d553c15b9d7fcc11bb8cd4c5fc1a1390ccb9ca8760f5a7`；72,446 候选中的 3,275 场未进入可评分 OOS 样本。总体 AH 1X2 代理 Log Loss/Brier `1.00227780/0.59749566`，OU2.5 `0.69502139/0.24967156`，exact score Log Loss `2.95770164`。按 OOS 年切分的 AH/OU Log Loss、Brier 如下；跨年波动存在，不足以证明某一策略稳定盈利。

| UTC 测试年 | OOS 场数 | AH LL | AH Brier | OU LL | OU Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2015 | 4,966 | 1.03563 | 0.61968 | 0.73929 | 0.26399 |
| 2016 | 4,978 | 0.99841 | 0.59620 | 0.70593 | 0.25526 |
| 2017 | 5,151 | 0.97670 | 0.58063 | 0.68660 | 0.24620 |
| 2018 | 5,288 | 0.98887 | 0.58922 | 0.69346 | 0.24955 |
| 2019 | 5,439 | 1.00168 | 0.59185 | 0.69201 | 0.24820 |
| 2020 | 4,664 | 1.00901 | 0.60278 | 0.69615 | 0.24974 |
| 2021 | 6,589 | 1.00926 | 0.60302 | 0.69039 | 0.24814 |
| 2022 | 6,034 | 0.99173 | 0.59118 | 0.69479 | 0.25012 |
| 2023 | 7,000 | 1.00546 | 0.59850 | 0.69333 | 0.24940 |
| 2024 | 6,631 | 0.99474 | 0.59333 | 0.68488 | 0.24569 |
| 2025 | 6,661 | 1.00570 | 0.60114 | 0.68466 | 0.24565 |
| 2026 | 5,770 | 1.01105 | 0.60286 | 0.68958 | 0.24788 |

当前 M3 对照仍是同一 7,663 个严格共同 fixture；新 OOS 池扩大的 fixture 不在 M3 CSV 内，故这个交集未变。AH M3 Dixon-Coles `1.01000095/0.60367120`、M5 `1.01223291/0.60523473`；OU M3 Poisson `0.69321624/0.24972808`、M5 `0.69266069/0.24953371`。嵌套权重测试 n=7,252；AH blend `1.00991517/0.60370237`，OU 权重退化为 M5 `0.69147091/0.24898142`。

### 当前 forecast SHA 上的独立 Crown/同价结果

| 样本证据 | AH 比赛 / 模拟注 / 已结算 | AH W/HW/L/HL/P | AH 净收益 / ROI / 最大回撤 | OU 比赛 / 模拟注 / 已结算 | OU W/HW/L/HL/P | OU 净收益 / ROI / 最大回撤 |
| --- | ---: | --- | --- | ---: | --- | --- |
| MR1 verified Crown 接收时间赛前 + 独立赛后 FT | 176 / 176 / 176 | 72/10/67/11/16 | `-0.875U / -0.497159% / 12.855U` | 176 / 176 / 176 | 71/11/71/13/10 | `-8.225U / -4.673295% / 19.330U` |
| TotalCorner endpoint historical movement（响应赛后取回，FT 同响应） | 212 / 212 / 212 | 91/10/80/9/22 | `+5.865U / +2.766509% / 9.620U` | 212 / 212 / 212 | 88/15/81/19/9 | `-0.600U / -0.283019% / 16.060U` |
| M1 V23 exact same-Crown OU quote + verified FT | AH 无同协议样本 | — | — | 12 / 12 / 12 | 各模型单独列在下文 | M5 `+0.335U / +2.791667%` |

MR1 176 场回放的 quote receipt 在 kickoff 前，FT receipt 在 kickoff 后，fixture identity 精确；它是历史预测回放，不是当时保存的 M5 forecast 或真实投注。M3 在完全相同 Crown 合约的交集 AH n=4，M5 和 M3 各模型均 `+2.02U/+50.5%`；OU n=5，M5 与 M3 Poisson/DC `-1.33U/-26.6%`，M3 bivariate `+0.50U/+10%`。小样本不作为获利证据。

M1 OU 的 12 场同价配对 W/HW/L/HL/P、净收益/ROI 分别是：M5 `5/1/4/1/1`, `+0.335U/+2.791667%`; M1 market Poisson `6/2/3/0/1`, `+3.170U/+26.416667%`; M1 calibrated `8/1/1/1/1`, `+6.015U/+50.125%`; M1 raw `4/0/5/2/1`, `-2.380U/-19.833333%`。两个旧 market-blend 在这 12 场分别复制其 calibrated/raw 对照。样本仅 12 场，且不是 M1 正式账本。

TotalCorner Crown movement 仍然只能作为“source event timestamp 在 kickoff 前的历史报价轨迹”使用，响应发生在赛后，不构成 contemporaneous received-before-kickoff snapshot。它和 MR1 verified received archive 不合并。当前严格 receipt-verified cohort 每市场 176 场、每市场 10,000 场目标仍相差约两个数量级。AH/OU 都没有稳健、独立验证的 >5% ROI；在 12 场 M1 exact subset 的 M1 calibrated +50.125% 也不能外推。

### 当前自动采集状态

schedule discovery PID 1267 在本节生成时仍运行；本地下一次快照应再次核对 51-liga scope 的页数并明确冻结新 manifest，然后重训和复跑所有依赖 forecast SHA 的报告。不得把不同 manifest 版本的候选数、预测数和 Crown ROI 合并。当前 M5 结果已本地生成但尚待本次提交推送；M5 GitHub Actions 没有触发/成功证据。M3 Actions 成功 `41864900732` 仍只属于 M3。生产链路、Telegram、自动模型升级均未触碰。

## 2026-11-05 当前最新快照：73,204 场 OOS / 324 folds

覆盖前面的 69,171 场版本。冻结 manifest UTC `2026-11-04T19:40:31.683513Z`：固定 51 联赛范围已有 30 个 page-1；已知 2,905 页、保存 2,688、缺 217；72,446 个唯一 FT 候选，2 个 identity duplicate groups 被排除；complete historical universe=false。manifest SHA `753c285ffed5cf26fc1900eb9eb9b89ea547f59f54335aca87f90a828bbec949`。

独立 M5 Poisson OOS 预测 **73,204 场 / 324 联赛×UTC 年折**，2015–2026；forecast 仅存本地私有目录，SHA `3ea8adac0d9e5e580c9914370f4f96e8f904889966cc1593a41824db8f3f1469`。AH 1X2 proxy LL/Brier `1.00127342/0.59684815`，OU2.5 `0.69471781/0.24957950`，exact score LL `2.95779534`。候选中 3,465 场无可评分 OOS fold。逐年结果：

| UTC 测试年 | OOS 场数 | AH LL | AH Brier | OU LL | OU Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2015 | 5,206 | 1.03187 | 0.61728 | 0.73808 | 0.26372 |
| 2016 | 5,216 | 0.99837 | 0.59621 | 0.70606 | 0.25536 |
| 2017 | 5,393 | 0.97514 | 0.57960 | 0.68682 | 0.24633 |
| 2018 | 5,552 | 0.99158 | 0.59114 | 0.69285 | 0.24928 |
| 2019 | 5,723 | 0.99909 | 0.59020 | 0.69184 | 0.24818 |
| 2020 | 4,891 | 1.00802 | 0.60207 | 0.69650 | 0.25000 |
| 2021 | 6,924 | 1.00657 | 0.60135 | 0.69126 | 0.24859 |
| 2022 | 6,281 | 0.99156 | 0.59103 | 0.69478 | 0.25014 |
| 2023 | 7,296 | 1.00431 | 0.59774 | 0.69338 | 0.24946 |
| 2024 | 7,226 | 0.99171 | 0.59108 | 0.68518 | 0.24578 |
| 2025 | 7,245 | 1.00657 | 0.60169 | 0.68315 | 0.24494 |
| 2026 | 6,251 | 1.01136 | 0.60319 | 0.68861 | 0.24747 |

M3 同期严格 OOS 共同集不随额外 M5 私有比赛增加，仍为 7,663 场：M3 Dixon-Coles AH proxy `1.01000095/0.60367120`，M5 `1.01223291/0.60523473`；M3 Poisson OU2.5 `0.69321624/0.24972808`，M5 `0.69266069/0.24953371`。嵌套权重验证集 7,252 场；AH blend LL/Brier `1.00991517/0.60370237`，OU 权重退化到 M5 独立模型 `0.69147091/0.24898142`。

### 当前 forecast SHA 对应收益结果

| 样本证据 | AH 赛事/下注/结算 | AH W/HW/L/HL/P | AH 净收益 / ROI / 最大回撤 | OU 赛事/下注/结算 | OU W/HW/L/HL/P | OU 净收益 / ROI / 最大回撤 |
| --- | ---: | --- | --- | ---: | --- | --- |
| MR1 verified Crown received-before-kickoff + independent FT | 194/194/194 | 84/12/70/11/17 | `+8.375U / +4.317010% / 12.505U` | 194/194/194 | 81/12/78/13/10 | `-5.455U / -2.811856% / 20.200U` |
| TotalCorner Crown historical movement (response after FT) | 212/212/212 | 91/10/80/9/22 | `+5.865U / +2.766509% / 9.620U` | 212/212/212 | 88/15/81/19/9 | `-0.600U / -0.283019% / 16.060U` |
| M1 V23 exact same Crown OU quote + verified FT | AH 不适用 | — | — | 14/14/14 | 按每个模型单列 | M5 `-1.665U / -11.892857%` |

MR1 verified 194 场均在 kickoff 前收到报价，有独立赛后 FT 和唯一身份；这是当前真正带接收时间证据的 Crown 回放。AH 4.317% 未超过目标，OU 为负。TotalCorner 两边报价仅源 event timestamp 在开赛前，但接口响应赛后取得且 FT 同响应；不能把它标记成 pre-match received snapshot。两批不能合并。两市场仍远未达到各 10,000 样本。

M1 current exact quote OU n=14，W/HW/L/HL/P 和净收益/ROI：M5 `5/1/6/1/1`, `-1.665U/-11.892857%`; M1 market Poisson `7/2/4/0/1`, `+3.050U/+21.785714%`; M1 calibrated `9/1/2/1/1`, `+5.895U/+42.107143%`; M1 raw `5/0/6/2/1`, `-2.500U/-17.857143%`。既有两个 blend 与对应 calibrated/raw 结果相同。AH 无符合此 M1 同报价协议样本。14 场比较为描述，不作策略选择依据。

本次所有 M5派生回放 JSON 中的 forecast SHA 均为 `3ea8adac0d9e5e580c9914370f4f96e8f904889966cc1593a41824db8f3f1469`。M3/M5 proper scores、MR1、M1及TotalCorner相互比较时分别遵守同场和时间证据口径；没有跨版本或跨来源合并。

## 2026-11-05 当前最新：77,765 场样本外预测

本节更新 73,204 场版本。UTC `2026-11-04T19:50:03.593127Z` 冻结的 partial schedule manifest：51 个固定范围中 31 个有 page-1；2,989 个已知页、2,852 已保存、137 缺失；候选 81,467 个唯一 FT fixture；重复身份组 2。完整历史范围仍未取得。manifest SHA `1c2ea9423f2907c385395e90c238059ab23e6ee3e4aaeb0ec53caa4aa58eaee5`。

M5 独立 Poisson 的 UTC 联赛×年份前推共 **77,765 unique OOS fixtures / 343 folds**，测试年 2015–2026；私有预测 SHA `f2aa532032479a378310d098c30d8395672c10fe9fa8c7e389a10d6e4ac7383e`。AH 1X2 概率代理 Log Loss/Brier `1.00059520/0.59651861`，OU2.5 `0.69412468/0.24934720`，exact-score LL `2.96197982`。81,467 个候选中 3,702 场未进入可评分 fold。年度评分：

| UTC 测试年 | OOS 场数 | AH LL | AH Brier | OU LL | OU Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2015 | 5,510 | 1.02937 | 0.61573 | 0.73755 | 0.26385 |
| 2016 | 5,521 | 0.99856 | 0.59651 | 0.70503 | 0.25489 |
| 2017 | 5,904 | 0.97492 | 0.57957 | 0.68794 | 0.24689 |
| 2018 | 6,042 | 0.98940 | 0.58959 | 0.69150 | 0.24867 |
| 2019 | 6,223 | 0.99677 | 0.58901 | 0.68962 | 0.24722 |
| 2020 | 5,275 | 1.00541 | 0.60030 | 0.69580 | 0.24976 |
| 2021 | 7,467 | 1.00488 | 0.60029 | 0.69004 | 0.24803 |
| 2022 | 6,731 | 0.99340 | 0.59232 | 0.69301 | 0.24931 |
| 2023 | 7,833 | 1.00474 | 0.59827 | 0.69225 | 0.24888 |
| 2024 | 7,397 | 0.99223 | 0.59180 | 0.68475 | 0.24565 |
| 2025 | 7,450 | 1.00636 | 0.60152 | 0.68438 | 0.24551 |
| 2026 | 6,412 | 1.01203 | 0.60383 | 0.68894 | 0.24760 |

M3 exact common OOS 7,663 场及 nested blend 7,252 场不变，因为增加的 M5 scope 没有新增 M3 原始严格 OOS 身份。AH 单体 M5 仍低于 M3 Dixon-Coles；OU 单体 M5 优于 M3 Poisson；嵌套 AH blend 的 LL/Brier 为 `1.00991517/0.60370237`，OU 权重退化到 M5 独立模型 `0.69147091/0.24898142`。它们是 proper scores，不是盈利证明。

### 当前 forecast SHA 的 Crown 收益和同价对照

| 样本 | AH 唯一赛/注/结算 | AH W/HW/L/HL/P | AH 净收益 / ROI / DD | OU 唯一赛/注/结算 | OU W/HW/L/HL/P | OU 净收益 / ROI / DD |
| --- | ---: | --- | --- | ---: | --- | --- |
| MR1 verified Crown receipt before kickoff + independent FT | 198/198/198 | 84/11/73/12/18 | `+4.665U / +2.356061% / 12.505U` | 198/198/198 | 85/12/78/13/10 | `-1.905U / -0.962121% / 20.200U` |
| TotalCorner endpoint source-time movement (response after FT) | 212/212/212 | 91/10/80/9/22 | `+5.865U / +2.766509% / 9.620U` | 212/212/212 | 88/15/81/19/9 | `-0.600U / -0.283019% / 16.060U` |
| M1 V23 exact OU quote/verified FT intersection | AH 无同协议配对 | — | — | 15/15/15 | model-specific below | M5 `+1.135U / +7.566667%` |

MR1 198 场报价有赛前 receive 时间、独立赛后 FT 和精确身份匹配，是当前主要可核实历史 Crown ROI cohort。AH、OU ROI 都未超过 5%；样本远未达到各 10,000 场。TotalCorner endpoint 的历史运动记录源事件时间虽早于 kickoff，但响应赛后取得且 FT 同响应，必须继续单独标注，不能当作赛前已收到的历史快照。

M1 OU n=15 的净收益/ROI：M5 `+1.135U/+7.566667%`，M1 Crown market Poisson `+2.050U/+13.666667%`，M1 calibrated `+4.895U/+32.633333%`，M1 raw `-3.500U/-23.333333%`；两个既有 blend 与对应 calibrated/raw 结果相同。M5 W/HW/L/HL/P=`7/1/5/1/1`。这是 15 场精确同盘口子集，不代表市场整体 ROI，也不是 M1 正式账本；AH 无样本。

本轮逐场 forecast 与所有 M5 派生回放均指向 SHA `f2aa532032479a378310d098c30d8395672c10fe9fa8c7e389a10d6e4ac7383e`。任务没有启用任何新的投注门槛或按结果过滤。采集进程仍可能产生更多 schedule pages；不同冻结输入版本不得混合计数或收益。

## 2026-11-05 当前最新：82,377 场 OOS / 375 folds

覆盖前版 77,765 场快照。UTC `2026-11-04T19:58:57.686538Z` 冻结的赛程清单：51 个固定联赛中 34 个已有 page-1；3,184 个已知页、3,020 已保存、164 缺页；候选 86,064 个唯一 FT fixture；6 组重复 fixture identity 被排除；historical universe incomplete。manifest SHA-256 `95d4b4377bf7acef390459cee2db0687c192d9a297899e3b39530529004681c0`。

M5 独立 Poisson 按 UTC 联赛×年份 walk-forward，生成 **82,377 unique OOS / 375 folds**，测试年 2015–2026；预测留在仓库外，SHA `1112fe6833c1b6c4f9f6c2826a8b2239aa8821c5bd1a2112c9fd0887b6083853`。AH 1X2 proxy LL/Brier `1.00254101/0.59730136`，OU2.5 `0.69555459/0.24975617`，exact-score LL `2.96373911`。候选中 3,687 场未进入 OOS folds。随赛程扩样，整体分数会随样本变化；不能把不同冻结版本的 aggregate score 当作配对比较。年度表现：

| UTC 测试年 | OOS 场数 | AH LL | AH Brier | OU LL | OU Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2015 | 5,905 | 1.03377 | 0.61731 | 0.73870 | 0.26447 |
| 2016 | 5,912 | 1.00282 | 0.59883 | 0.70385 | 0.25435 |
| 2017 | 6,097 | 0.97419 | 0.57909 | 0.68829 | 0.24707 |
| 2018 | 6,289 | 0.99131 | 0.59054 | 0.69047 | 0.24816 |
| 2019 | 6,489 | 1.00238 | 0.59240 | 0.69127 | 0.24799 |
| 2020 | 5,525 | 1.00611 | 0.60076 | 0.69604 | 0.24992 |
| 2021 | 7,905 | 1.01625 | 0.60445 | 0.70136 | 0.25060 |
| 2022 | 7,193 | 0.99264 | 0.59188 | 0.69216 | 0.24893 |
| 2023 | 8,305 | 1.00249 | 0.59670 | 0.69223 | 0.24890 |
| 2024 | 7,916 | 0.99229 | 0.59176 | 0.68450 | 0.24555 |
| 2025 | 7,954 | 1.00569 | 0.60088 | 0.68642 | 0.24647 |
| 2026 | 6,887 | 1.01099 | 0.60339 | 0.69030 | 0.24812 |

M3 精确共同 OOS 仍 n=7,663；nesting assessment n=7,252。M3 DC AH proxy `1.01000095/0.60367120` vs M5 `1.01223291/0.60523473`；M3 Poisson OU `0.69321624/0.24972808` vs M5 `0.69266069/0.24953371`。AH 单模型仍是 M3 proper score 较好，OU M5 略好。Nested AH blend `1.00991517/0.60370237`，OU 权重退化为 M5 single `0.69147091/0.24898142`。这些分数不表示 ROI。

### 按同一 forecast SHA 结算的 Crown 样本

| 来源 | AH 比赛/下注/结算 | AH W/HW/L/HL/P | AH 净收益 / ROI / DD | OU 比赛/下注/结算 | OU W/HW/L/HL/P | OU 净收益 / ROI / DD |
| --- | ---: | --- | --- | ---: | --- | --- |
| MR1 verified Crown receipt before kickoff + independent FT | 212/212/212 | 88/11/77/15/21 | `+2.645U / +1.247642% / 16.005U` | 212/212/212 | 91/13/82/14/12 | `-0.765U / -0.360849% / 20.300U` |
| TotalCorner endpoint historical movement (response/FT after kickoff) | 212/212/212 | 91/10/80/9/22 | `+5.865U / +2.766509% / 9.620U` | 212/212/212 | 88/15/81/19/9 | `-0.600U / -0.283019% / 16.060U` |
| M1 V23 exact same-Crown OU quote + verified FT | AH 无协议样本 | — | — | 15/15/15 | model-specific below | M5 `+1.135U / +7.566667%` |

MR1 verified archive现以 AH/OU各212个唯一fixture提供当前有接收时间证明的 Crown+FT 回放。AH ROI `+1.248%`，OU `-0.361%`，均未超过 5%。TotalCorner 的 212 场虽有 source movement pre-kickoff 时间戳，但没有 contemporaneous received-at 证据，响应和 FT 同属赛后 response，因此单独列示。

M1 OU 精确报价交集 n=15 的 M5/M1 净收益和 ROI仍为：M5 `+1.135U/+7.566667%`，M1 market Poisson `+2.050U/+13.666667%`，calibrated `+4.895U/+32.633333%`，raw `-3.500U/-23.333333%`；两种历史 blend 等于相应 calibrated/raw 结果。该 n=15 是选择和配对后极小回放，不用于宣称广泛样本外盈利。AH无可比的 M1 exact quote subset。

当前严格 received-before-kickoff Crown 样本每市场 212，离 10,000 仍差甚远；全 51 联赛历史 schedule 未补全。虽然 M1 子集 M5 ROI超过 5%，本目标要求的全体 AH/OU 独立大样本 OOS ROI 尚未达成。M5 自动工作流尚无本轮 Actions 验收。

### 冻结之后的 schedule collector 状态

本报告当前模型输入冻结在 `19:58:57Z`、34/51 leagues。随后 schedule collector 已更新其私有进度收据至 `20:07:32Z`（35 leagues complete、2,745 saved pages），并仍处于运行状态；这批后续保存页尚未写入当前模型 manifest，也未进入 82,377 场 forecast。下一轮应在单个 schedule collector 完成或确认稳定后重新冻结、核验去重，再重训和重跑派生结果。不要把 collector 进度页数直接换算为新的预测比赛数。


## 2026-11-05 当前冻结：91,636 候选 / 87,588 场 OOS / 402 折

本节覆盖此前 82,377 场版本。私有 partial schedule manifest 于 `2026-11-04T20:10:10.780680Z` UTC 冻结：固定范围 51 个联赛，其中 36 个取得 page-1；3,373 个已知页中 3,220 已保存、153 缺失；91,636 个唯一完赛候选，排除 6 组/12 行重复身份；完整历史总体仍为 false。manifest SHA-256 `06f712fc747e67e5661c77cc07cee9a771d64a77ee4352c5ad25d9b993c9a2dc`。

独立 Poisson 进球率模型按联赛及 UTC 年滚动训练，仅使用目标比赛开赛前已完赛数据；每折的正则化仅由此前 UTC 年验证选择。预测留在仓库外，SHA-256 `cbfee8bbf5e59599f476d722b03550876c9b56e07ce1f8c8e304b625033224a3`。共有 **87,588 唯一 OOS 比赛 / 402 折**，2015–2026；4,048 候选未能进入有足够训练数据的评分折。AH 以 1X2 概率代理评估，Log Loss/Brier `1.00519601/0.59916515`；OU2.5 `0.69595984/0.24979692`；exact-score Log Loss `2.96181127`。没有用 Crown 价格，ROI 为 null。逐年评分：

| UTC 测试年 | OOS 场数 | AH 1X2 LL | AH Brier | OU2.5 LL | OU Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2015 | 6,148 | 1.03906816 | 0.61686452 | 0.75580077 | 0.26639437 |
| 2016 | 6,122 | 1.00295771 | 0.59831564 | 0.70492136 | 0.25473126 |
| 2017 | 6,379 | 0.97735842 | 0.58089594 | 0.68905141 | 0.24742488 |
| 2018 | 6,917 | 0.99651187 | 0.59418574 | 0.69068340 | 0.24829808 |
| 2019 | 7,102 | 1.00445969 | 0.59422330 | 0.69321145 | 0.24897098 |
| 2020 | 6,046 | 1.01040549 | 0.60397500 | 0.69532614 | 0.24966716 |
| 2021 | 8,369 | 1.01137919 | 0.60471197 | 0.69072887 | 0.24829099 |
| 2022 | 7,603 | 0.99677472 | 0.59448836 | 0.69181641 | 0.24879252 |
| 2023 | 8,798 | 1.00620942 | 0.59957899 | 0.69152443 | 0.24858717 |
| 2024 | 8,377 | 0.99716663 | 0.59500862 | 0.68541239 | 0.24598295 |
| 2025 | 8,434 | 1.00899347 | 0.60317060 | 0.68675132 | 0.24666066 |
| 2026 | 7,293 | 1.01279678 | 0.60463838 | 0.69067747 | 0.24831385 |

M3 严格 OOS 完整模型预测与 M5 仅精确共同匹配 7,663 场，AH 为 1X2 proxy、OU 为 O2.5。AH：M3 Dixon-Coles `1.01000095/0.60367120`，M5 `1.01223291/0.60523473`（LL/Brier）；OU：M3 Poisson `0.69321624/0.24972808`，M5 `0.69266069/0.24953371`。嵌套前推评估在 7,252 场上：AH M5 walk-forward blend `1.00991517/0.60370237`；OU 权重选择退化为 M5 单模型 `0.69147091/0.24898142`。这只是 proper-score 比较，不是 ROI，也不能据此自动升级模型。

### Crown 证据分层与结算

| Crown 证据 | AH 唯一场 / ROI / 最大回撤 | OU 唯一场 / ROI / 最大回撤 | 解释 |
| --- | --- | --- | --- |
| MR1 verified Crown received-before-kickoff + 独立 FT | 223 / `+0.710762%` / `18.285U` | 223 / `-1.387892%` / `20.070U` | 有赛前接收时间证据；独立 FT 配对；部分捕获样本 |
| TotalCorner Crown movement endpoint | 212 / `+2.766509%` / `9.620U` | 212 / `-0.283019%` / `16.060U` | movement source event time 早于开赛，但接口响应在赛后且 FT 同响应；不视为赛前已收到报价 |
| M1 同一 Crown 报价与 FT 精确交集 | 0 | 15 / M5 `+7.566667%` | OU 模型配对样本过小，AH 无精确匹配；描述性对照，不作外推 |

MR1 verified archive 的 market quote rows 各有 1,679 条候选 snapshot，因 kickoff mismatch 41、没有匹配 verified FT 34 等原因，最终每市场仅覆盖 223 场；相对于 87,588 个 forecast fixtures，覆盖率约 0.255%。TotalCorner endpoint 仅覆盖 212 场/市场，约 0.242%。AH/OU 必须分开解释；没有把 event time 当成 receive time，也没有合并两类 Crown 样本。现有可验证 Crown ROI 均未达到用户目标的两个市场分别 >5%，也没有市场达到每市场 10,000 个有效赛前 Crown 价格与 FT 样本。

M5 含未来功能的自动化验收仍未完成：远端不存在 `m5-independent-research.yml`，本轮没有对应 M5 Actions run，因此不能称为云端自动训练、版本比较或结果落库成功。已有本地训练命令和派生报告可重跑；报告绑定 manifest、forecast 与模型来源 SHA。schedule discovery PID 1267 在本报告检查时仍在运行；后续新增页没有进入本冻结版，须等待单一采集进程稳定后再冻结及重训。未改动 M1/M2/MR1 生产链路、Telegram、任何 Gate 或正式模型选择。

## OOS 历史支持度诊断

对当前 forecast SHA 做事后分组，AH 使用 1X2 概率代理，OU 使用 O2.5 概率；分组变量仅为每个 OOS 折此前实际训练赛数，不参与下注筛选或模型权重选择。仅有 126 场预测落在训练历史少于 20 场的组，但该组评分显著较差：AH LL/Brier `1.92165/0.80607`，OU `1.80664/0.41598`；训练赛数至少 250 的 78,205 场组分别为 AH `1.00155/0.59757`、OU `0.69003/0.24808`。此差异提示极稀疏训练折的 team effect 方差可能过高，值得后续测试层级/跨联赛先验收缩；这只是诊断，不是新门槛，也不是 Crown 盈利证据。可用 [support audit script](m5_goal_model_training_support_audit.py) 和 [aggregate output](results/m5_goal_model_training_support_audit.json) 重现。


## 2026-11-05 当前最新：127,674 场 OOS / 584 折

本节覆盖 87,588 场版本。partial schedule manifest 于 UTC `2026-11-04T21:29:25.511926Z` 冻结：固定范围 51 个联赛全部取得 page-1；4,789 个已知历史页中 4,660 个已保存，129 个缺页；133,140 个唯一 FT 候选，6 组/12 行重复身份排除；完整历史 universe 仍未取得。manifest SHA-256 `258702e669bd5c1569b16bc191ce66e7117a368f409c3028572de5fd9186d0bf`。采集器结束时有 11 个 page errors；这不改变缺页清单，不能标为完整。

M5 独立 Poisson 的 UTC league-year 前推得到 **127,674 unique OOS fixtures / 584 folds**，2014–2026 测试年份。私有 forecast SHA-256 `ebc8ae9aa4c873f3d276510533a9961c607cc607614f976a2d2e1147dbdb356a`。AH 1X2 proxy Log Loss/Brier `1.01485592/0.60611273`；OU2.5 `0.69625130/0.25025289`；exact-score Log Loss `2.95638939`。133,140 个候选中 5,466 场未进入可评分 OOS fold。无 Crown 价格参与概率评分，概率报告 ROI 为 null。逐年表现：

| UTC 测试年 | OOS 场数 | AH LL | AH Brier | OU LL | OU Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2014 | 160 | 1.33995961 | 0.82009650 | 0.84622783 | 0.31531609 |
| 2015 | 9,576 | 1.04901238 | 0.62547553 | 0.74345090 | 0.26475551 |
| 2016 | 9,482 | 1.01039303 | 0.60357074 | 0.70530363 | 0.25499591 |
| 2017 | 9,941 | 1.00305533 | 0.59838170 | 0.69543292 | 0.25040074 |
| 2018 | 10,099 | 0.99810125 | 0.59499989 | 0.69296595 | 0.24932807 |
| 2019 | 10,383 | 1.00602852 | 0.59726971 | 0.69243995 | 0.24879001 |
| 2020 | 8,860 | 1.02106749 | 0.61132911 | 0.69379638 | 0.24927370 |
| 2021 | 12,022 | 1.02156709 | 0.61163259 | 0.69106336 | 0.24849659 |
| 2022 | 10,840 | 1.00715076 | 0.60191600 | 0.69047532 | 0.24822803 |
| 2023 | 12,182 | 1.01231651 | 0.60399463 | 0.69091741 | 0.24841213 |
| 2024 | 11,927 | 1.01447329 | 0.60650784 | 0.68799596 | 0.24726023 |
| 2025 | 11,967 | 1.01706697 | 0.60916296 | 0.68708088 | 0.24685505 |
| 2026 | 10,235 | 1.01468342 | 0.60639134 | 0.69029008 | 0.24823206 |

M3 精确同 fixture 的共同 OOS 仍为 7,663 场，因新增赛程历史没有同身份的额外 M3 预测。AH 1X2 proxy：M3 Dixon-Coles LL/Brier `1.01000095/0.60367120`，M5 `1.01223291/0.60523473`；OU2.5：M3 Poisson `0.69321624/0.24972808`，M5 `0.69266069/0.24953371`。嵌套前推在 7,252 场上 AH blend 为 `1.00991517/0.60370237`，OU 权重落在 M5 单模型 `0.69147091/0.24898142`。这是概率分数对照，不能推出 Crown ROI。

### 按当前 forecast SHA 结算的 Crown 样本

| Crown 证据 | AH 赛 / 注 / 结算 | AH W/HW/L/HL/P | AH 净收益 / ROI / 最大回撤 | OU 赛 / 注 / 结算 | OU W/HW/L/HL/P | OU 净收益 / ROI / 最大回撤 |
| --- | ---: | --- | --- | ---: | --- | --- |
| MR1 verified Crown receipt-before-kickoff + 独立 FT | 317/317/317 | 124/20/128/20/25 | `-12.960U / -4.088328% / 25.790U` | 317/317/317 | 139/19/118/23/18 | `+7.100U / +2.239748% / 20.090U` |
| TotalCorner Crown movement endpoint | 212/212/212 | 91/10/80/9/22 | `+5.865U / +2.766509% / 9.620U` | 212/212/212 | 88/15/81/19/9 | `-0.600U / -0.283019% / 16.060U` |
| M1 expected-total OU same quote / verified FT | AH 不适用 | — | — | 23/23/23 | M5 W/HW/L/HL/P `9/1/9/3/1` | M5 `-2.025U / -8.804348%`；M1 crown-market Poisson `+9.043478%` |
| Crown 同一盘口较低价一侧基准（非模型方向） | 317/317/317 | 139/23/113/17/25 | `+7.220U / +2.277603% / 19.085U` | 317/317/317 | 129/22/128/20/18 | `-18.590U / -5.864353% / 22.815U` |

MR1 verified Crown 样本有赛前收到时点、独立赛后 FT 和精确身份匹配；每市场 317 场、相对于 127,674 个 forecast fixtures 的覆盖约 0.248%。AH 与 OU 分开结算；当前 AH ROI `-4.088%`、OU `+2.240%`，两者均未严格超过 5%。M1 same-quote OU 是 23 场精确小交集，M5 为负、M1 的同口径子模型有正有负，不外推。同一 317 场、同一 Crown 盘口和结算顺序下，较低价一侧基准 AH `+2.278%`、OU `-5.864%`；M5 相对该基准在 AH 低约 6.37 个百分点、OU 高约 8.10 个百分点。两边都未达到 ROI 目标。这个方向基准不使用 M5 概率，每场各下注一次，只用于同样本增量比较；不是拟议的正式规则，也不代表大样本结果。按 Crown 报价 UTC 季度再拆：AH 316/317 注发生于 2026-Q4，Q3 仅 1 注且为走水；OU 317 注全部发生于 Q4。因此没有足够的季度或跨年分散度来检验稳定性，317 场汇总不能当作跨季节验证。季度结算详情已写入 Crown OOS JSON。

TotalCorner movement 的 212 场/市场，其源事件时间早于开赛，但 endpoint 响应与 FT 在赛后取得；仅为独立的 historical-event 时间组，不能与 MR1 receipt-verified 快照合并，也不能据此声称赛前收到。当前每市场有效 Crown 赛前 receipt OOS 远少于 10,000 场。

### 最新冻结后的采集状态与后续工作

后续单一 schedule collector 已处理固定范围 51/51 联赛，累计 4,235 个已保存页和 126,455 个 schedule fixture ID；11 个 page errors。最新冻结清单仍有 129 个已知缺页，因此 `complete_historical_universe=false`。这些页数不是已完赛候选数或 OOS 预测数。本轮训练已用稳定冻结 manifest 生成新 SHA；所有同版本 M3、nested、MR1 Crown、M1 exact quote、TotalCorner movement 和训练支持度回放均应检查 SHA 后再引用。

M5 Actions workflow 仍未存在/运行；本次训练是本地显式执行，没有 Actions 成功或云端落库证据。没有改动生产策略、订单、Telegram 或自动模型升级。M5 当前还没有完成目标；下一步重点是在固定赛事范围内扩充具备可信赛前接收时间的 Crown 记录，并研究低训练支持折的层级收缩，但不得把支持度诊断变成投注 gate。

## 2026-11-05 M5 Crown temperature calibration: quote-time holdout

This experiment uses only the existing source-verified MR1 V23 Crown snapshots, independent FT receipts and M5 OOS full-score forecasts. The forecast SHA remains `ebc8ae9aa4c873f3d276510533a9961c607cc607614f976a2d2e1147dbdb356a`; the quote archive is outside the public repository. Each market independently selects a score-grid temperature from `(0.60, 0.75, 0.90, 1.00, 1.10, 1.25, 1.50, 1.75, 2.00)` by minimum early-period Asian settlement-category log loss. ROI is not used for hyperparameter selection.

The split is by exact Crown quote event timestamp, with same-instant quotes kept in the same partition. The later holdout begins at the split timestamp. To prevent outcome leakage, a pre-cutoff quote enters calibration only when the separate FT receipt was already recorded before the first holdout quote; otherwise it is purged. AH has 181 calibration fixtures, 40 purged rows and 96 holdout fixtures. OU has 180 calibration fixtures, 41 purged and 96 holdout. Every held-out quote is strictly later than the calibration quote boundary and each calibration FT receipt predates that boundary. Every fixture-market has one Crown contract and one independent settlement.

| Market / variant | Train n | Purged | Holdout bets | Win / half-win / push / half-loss / loss | Net U | ROI | Bootstrap 95% fixture interval | Max drawdown | Settlement LL / Brier |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| AH raw temperature 1.0 | 181 | 40 | 96 | 46 / 5 / 4 / 8 / 33 | +7.970 | +8.302083% | -9.395833% to +25.802083% | 4.500U | 0.98216803 / 0.61146520 |
| AH train-LL calibrated, T=2.0 | 181 | 40 | 96 | 45 / 6 / 4 / 7 / 34 | +7.390 | +7.697917% | -10.083333% to +25.354167% | 4.810U | 0.98153317 / 0.61062180 |
| OU raw temperature 1.0 | 180 | 41 | 96 | 34 / 6 / 6 / 5 / 45 | -12.390 | -12.906250% | -30.796875% to +5.166667% | 19.720U | 1.03158858 / 0.65813756 |
| OU train-LL calibrated, T=1.25 | 180 | 41 | 96 | 36 / 6 / 6 / 5 / 43 | -8.260 | -8.604167% | -26.640625% to +9.161458% | 18.245U | 1.00160794 / 0.63412896 |

Temperature selection improves the held-out settlement log loss and Brier for both markets, but the ROI conclusions do not meet the research goal. AH's point estimate is above 5% on this 96-fixture single-period holdout, but its 95% bootstrap interval includes material loss and T=2.0 is at the top of the tested candidate grid, so the optimum is boundary-censored. OU remains negative after calibration. Results are short-period and retrospective, not an independently archived live M5 prediction stream. Full sanitized receipt: `results/m5_crown_temperature_holdout.json`; implementation: `m5_crown_temperature_holdout.py`.

The experiment does not add a bet filter, EV floor, or production rule. No Crown API calls, credential reads, Telegram activity, or production writes occurred. It does not raise the full-cohort snapshot result (AH 317 bets / -4.088328%; OU 317 / +2.239748%) and does not satisfy the 10,000-quote-per-market requirement.

The aggregate report was generated at `2026-11-04T22:10:26.936674Z`. It records forecast SHA `ebc8ae9aa4c873f3d276510533a9961c607cc607614f976a2d2e1147dbdb356a`, MR1 snapshot-index SHA `c38af559b487a07c518c65a2fd8333d9494925a6605c11a206f37ad8820cda74`, fixture-registry SHA `7d64bc4c437f8bd5958225104f15e39880df32db96d5e31f8d97e9fce57c299f`, Crown snapshot hash-set SHA `938ee37c144f9988eefd0aa138889c21b310e90a5c17ea783dcaf3f21e93f7f6`, and verified FT receipt hash-set SHA `bb31aaedb5102a123a7c12145c2297d596cf42396c0ab7f4710c2e09e882bd3c`. It contains only aggregate outputs and hashes, not fixture identities or price values.

## 2026-11-05 M5 per-league recency weighting experiment

Added `m5_goal_model_recency_oos.py` and a separate [research report](M5_RECENCY_MODEL_CROWN_OOS_20261105.md). The experiment uses the current frozen partial M1-scope manifest (133,140 unique finished candidates; 51/51 leagues have page-1, 4,660/4,789 known pages saved, 129 missing; `complete_historical_universe=false`). Per league, an exponential history half-life is selected from 0.5, 1, 2, 3, 5, 10 years and no decay using 2025 exact-score log loss only; the 2026 fold's existing regularization-selection procedure is retained. The model is refit using matches strictly before 2026-01-01 UTC and evaluated on exactly the same 10,235 2026 OOS fixture identities as the baseline across 51 leagues. Identity and cutoff guards passed with zero baseline/manifest identity conflicts. No 2026 outcome informed tuning.

On the 10,235 common 2026 forecasts, AH 1X2 proxy Log Loss/Brier changed from `1.01468342/0.60639134` to `1.01113451/0.60433461`; exact-score Log Loss changed `2.99609365` to `2.99040238`. OU O2.5 changed from `0.69029008/0.24823206` to `0.69157802/0.24883453`, slightly worse. These are proper-score results, not ROI.

The candidate's private 2026 forecast was replayed against the same verified MR1 V23 Crown snapshot, fixture-registry and independent FT receipt hash sets as the 127,674-row baseline report. Each market has 317 exact same Crown fixture-contract samples, one 1U bet per fixture, no EV gate. AH W/HW/P/HL/L `127/20/25/20/125`, `-6.765U`, ROI `-2.134069%`, quote-time-batched drawdown `20.495U`, settlement LL/Brier `1.04382035/0.64828452` (baseline `124/20/25/20/128`, `-12.960U/-4.088328%`, DD `25.790U`, LL/Brier `1.05273941/0.65440920`). OU `135/20/18/22/122`, `-0.355U`, ROI `-0.111987%`, DD `22.760U`, LL/Brier `1.01106287/0.63711699` (baseline `139/19/18/23/118`, `+7.100U/+2.239748%`, DD `20.090U`, LL/Brier `1.00331741/0.63152205`). AH improved but remains negative; OU worsened. Neither exceeds +5%, and 317 Crown pairs per market remains far below 10,000.

Sanitized aggregate receipts are `results/m5_goal_model_recency_2026_oos.json` and `results/m5_goal_model_recency_2026_crown_oos.json`; candidate fixture predictions stay private. Inputs are pinned by manifest SHA `258702e669bd5c1569b16bc191ce66e7117a368f409c3028572de5fd9186d0bf` and baseline forecast SHA `ebc8ae9aa4c873f3d276510533a9961c607cc607614f976a2d2e1147dbdb356a`; private candidate forecast SHA `fc2abf89b2ac80eb2ba72bf9e992f25eeda11502f2e87cd2bd965b921843d26d`. Model source compiled, replay completed, aggregate sensitive-field scan found none, and `git diff --check` passed. This is local research; no M5 Actions run, API request, production write, Telegram, or strategy Gate change.

## 2026-11-05 Crown source-union expansion and drawdown correction

Read-only set audit found 212 TotalCorner event-time fixtures per market and 317 MR1 V23 received-before-kickoff Crown+independent-FT fixtures per market; exactly 46 overlap both by source fixture ID and by normalized `(league, UTC date, home, away)` identity, with no internal normalized identity duplicates. The new `m5_crown_oos_source_union.py` deduplicates by normalized `(league, UTC kickoff date, home, away)` identity × market and prefers the stronger MR1 evidence for overlaps and adds only the 166 TotalCorner-only fixture-markets, producing 483 unique AH and 483 unique OU fixtures rather than the incorrect row sum 529. The quote response set matches the prior TotalCorner replay SHA `8b8b35e0a18de0a861c37f94553e085abd4221ea6a24c477be3d8b18423a933b`; these TotalCorner source-event times predate kickoff, but the endpoint response and embedded score arrived post-match. They remain a distinct weaker evidence stratum and are never double-counted.

On the 483-row deduplicated union, baseline AH is `-17.835U/-3.692547%`, candidate AH `-27.190U/-5.629400%`; baseline OU is `+5.035U/+1.042443%`, candidate OU `-4.225U/-0.874741%`. Candidate AH/OU settlement counts W/HW/P/HL/L are `187/24/44/30/198` and `200/34/26/36/187`; baseline counts are `191/26/44/28/194` and `206/31/26/39/181`. Neither passes +5%, and the recency candidate underperforms on the union.

Drawdown calculation in `m5_mr1_crown_oos_replay.py` and `crown_historical_capture.py` now batches bets sharing the same quote-event instant before updating equity, avoiding arbitrary fixture-ID order for simultaneous quotes. The recency AH drawdown on the MR1 317-row cohort consequently corrects from `21.495U` to `20.495U`; net, ROI and settlement counts do not change. New deduplicated output: `results/m5_goal_model_recency_2026_crown_source_union.json`. The M5 suite passes 6 tests, including simultaneous-time drawdown batching, normalized fixture-market uniqueness and temporal holdout checks. That attempted replay used an incorrect parent path; a later audit located the archive under the already authorized local MR1 repository archive, re-ran the larger source union, and added league-level aggregates. See the later archive-refresh section.

## 2026-11-05 V26 strict historical M5/Crown hindcast correction

The earlier local V26 audit required a contemporaneous saved M5 probability-grid receipt and therefore classified the 39 exact fixture joins as zero M5 ROI observations. That was too strict for the requested *historical backtest*: strict information-time isolation, rather than a live forecast archival receipt, is the essential condition. Reconstructing each M5 grid from the existing annual UTC walk-forward artifact is valid here because every training end is before the Jan-1 forecast-as-of, which is before the verified Crown event/receipt and kickoff; the target match outcome is excluded from training. These are retrospective hindcasts, not live M5 signals.

The V26-only archive contains 47 locked Crown AH observations. Seven have no M5 forecast ID and one fails exact fixture identity. The remaining 39 pass `train_end < prediction_asof <= quote event <= received < kickoff`, Crown source verification, exact canonical home-line contract, paired Crown prices, and a separate FT receipt after kickoff matching the fixture identity and score. Replay selects the higher M5 grid expected-return side at the exact line and exact two-sided Crown prices, one 1U per fixture, with no EV cutoff. It handles split lines with the shared settlement implementation.

| Same 39 fixtures / quote source | Bets | W / HW / P / HL / L | Net U | ROI | Max DD U | Settlement LL / Brier |
|---|---:|---|---:|---:|---:|---|
| V26 first-locked Crown quote, M5 hindcast | 39 | 8 / 5 / 6 / 3 / 17 | -8.985 | -23.038462% | 12.695 | 1.16726241 / 0.73294132 |
| Same V26 contract, browser AI direction side (descriptive comparator) | 39 | 18 / 4 / 6 / 4 / 7 | +9.815 | +25.166667% | 2.000 | Not scored as an AI probability forecast |
| V23 later Crown quote on the same fixtures, M5 hindcast | 39 | 8 / 4 / 6 / 4 / 17 | -9.475 | -24.294872% | 12.555 | 1.18903297 / 0.75018100 |

All 39 V23 quote-event timestamps are later than the V26 first-locked timestamps. The combined V23/V26 archive therefore remains **317 unique AH fixture-markets**, not 356; the merged latest-quote replay remains the existing 317-fixture result, -4.088328%. V26 has no OU quotes; OU remains 317 at +2.239748%. The 39-row V26 comparison is same-fixture temporal-price sensitivity, not incremental unique sample and not cross-cohort evidence. The M5 point ROI is negative at both V26 and later V23 quote times; the positive browser-AI direction baseline is a small descriptive comparator, not an M5 model, not a calibrated probability, and not a formal MR1 model result.

Reproducible implementation and sanitized result: `m5_v26_crown_oos_replay.py` and `results/m5_v26_crown_oos_replay.json`. No private row, quote, identity, or token value is included. Unit test `test_m5_v26_crown_replay.py` checks exact OU-side mapping and settlement. No API request, production write, or Telegram action occurred. A resumable Crown backfill attempt stopped before HTTP because no local token environment variable or Keychain entry was available; the existing GitHub Secret value was not accessed.


## 2026-11-05 MR1 archive refresh and larger chronological holdout

A follow-up audit located the local MR1 archive at the already authorized local MR1 repository archive (the earlier attempted parent path was incorrect). It is separate from the private M5 forecast/capture directory. Re-running against the current frozen M5 candidate and baseline produced a later MR1 source snapshot: snapshot-index SHA `107f1635b7642dd2d4057500ea7105df2355934a00590bd3f6daeb3355e45a8a`, fixture-registry SHA `891a1092095f8ced9cadaae613457233dd7986501ebf92a81ad06f47d3ea79ca`. The previous 317/483 aggregates refer to earlier archive hashes and are superseded, not additive.

Per market, 871 unique forecast fixture-markets have verified Crown quotes received before kickoff and independent post-kickoff FT across 48 leagues. TotalCorner has 212 event-time fixtures; 142 normalized fixture-market identities overlap, leaving 70 weaker non-overlapping additions. Source-priority union is 941 fixture-markets across 49 leagues. TotalCorner response/score retrieval remains post-match and is not represented as a contemporaneously received quote. AH and OU are separate; each fixture-market is counted once.

On the strict 871-row MR1 cohort, recency candidate AH is `-1.944891%` vs baseline `-2.046498%`; OU is `-3.729621%` vs baseline `-3.567738%`. Paired fixture-bootstrap intervals for candidate-minus-baseline ROI difference are `[-3.739380,+3.794489]pp` AH and `[-3.873708,+3.504592]pp` OU. On 941-row source-priority union candidate ROI is AH `-2.859192%` vs baseline `-2.232731%`, OU `-3.506908%` vs baseline `-3.071201%`; both paired 95% intervals cross zero. The per-market per-league settlement results and individual 95% fixture-bootstrap ROI intervals are saved only as aggregate rows in `results/m5_goal_model_recency_2026_crown_source_union.json`; no fixture identities or prices are published.

A separate chronological temperature calibration was re-run on the same 871-row MR1 snapshot. Each market has 606 early training fixtures, 3 pre-cutoff rows purged because their FT receipt was late, and 262 later untouched fixtures. The split uses quote-event UTC timestamps, groups identical timestamps, and requires every training FT receipt before the holdout quote cutoff. AH train-LL temperature 1.75 gives later ROI `-6.438931%` (raw `-6.910305%`); OU temperature 1.25 gives `-14.541985%` (raw `-14.045802%`), while improving OU settlement LL/Brier but worsening its holdout ROI. No market comes close to +5%; the OU bootstrap interval remains below zero. Full details and hashes are in `results/m5_crown_temperature_holdout.json`.

Both source-union and temperature reports now reference the same index and fixture-registry hashes. The existing M5 test suite, compilation, aggregate sensitive-key scan, chronological split invariants and `git diff --check` are re-run before publication. This remains below 10,000 Crown fixtures per market and does not meet the profitability goal.
