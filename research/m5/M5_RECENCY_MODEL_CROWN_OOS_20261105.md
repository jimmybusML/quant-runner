# M5 近期赛果加权候选：2026 样本外回测

生成时间：2026-11-04 UTC。此实验只用于历史研究，不改变任何现有正式模型或交易规则。

## 研究问题

现有 M5 独立 Poisson 模型对训练历史中的旧比赛和新比赛赋予相同似然权重。本实验检验近期比赛指数加权是否改善未来赛季概率预测及真实 Crown 盘口收益。AH 与 OU 仍分开评估；没有增加 EV、价格、时间、联赛或注数门槛。

## 数据与时间隔离

- 来源为当前固定 M1 一级联赛范围的 51 个联赛 ID、TotalCorner 赛程/真实 FT，以及既有 M5 全量严格 UTC 年度前推预测。私有 partial manifest 有 133,140 个去重完赛候选，已生成 127,674 个唯一 OOS forecast；来源覆盖仍不完整：51 个联赛均有 page-1，但 4,789 个已知赛程页只有 4,660 个保存，129 页缺失。不得将候选或预测数量解释为 Crown 报价数量。
- 本次只评价 2026 年同一组 **10,235 场** M5 OOS 比赛，覆盖 51 个联赛。逐场候选预测保存在仓库外；公开收据只存聚合分数和输入/输出哈希。
- 每联赛分别在已有 M5 2026 fold 的正则化参数下，对候选衰减半衰期 `{0.5, 1, 2, 3, 5, 10 年, 不衰减}` 做比较。参数只依据 2025 年精确比分 Log Loss 选择；之后用 2026-01-01 UTC 前全部真实比赛重新拟合，再评估 2026 赛果。正则化参数沿用原 M5 fold 的同一 2025 验证选择程序。训练、验证和目标年的 fixture ID 边界均有断言；2026 结果没有参与选参。
- Crown 收益重放使用既有 MR1 V23 **已验证 Crown 赛前快照和独立赛后 FT**。AH、OU 分别每个唯一 fixture-market 取一个最近有效 Crown 报价；每场均选择 M5 预测期望收益较高的一侧，每注 1U，按实际盘口结算四分之一线。未使用其他公司赔率，也没有 EV 门槛。候选与 M5 基线的 Crown 快照索引、fixture registry、FT 收据及报价 hash 集全部相同，证明对比使用同一 317 场、同一 Crown 合约样本。

输入凭据：partial manifest SHA-256 `258702e669bd5c1569b16bc191ce66e7117a368f409c3028572de5fd9186d0bf`；原 M5 基线预测 SHA-256 `ebc8ae9aa4c873f3d276510533a9961c607cc607614f976a2d2e1147dbdb356a`；候选预测 SHA-256 记录于汇总 JSON。此 manifest 明确不是完整赛程 universe。

## 2026 同场概率质量

| 指标 | M5 无衰减基线 | 近期加权候选 | 变化 |
|---|---:|---:|---:|
| 比赛数 | 10,235 | 10,235 | 同一组比赛 |
| AH 1X2 代理 Log Loss | 1.01468342 | 1.01113451 | 改善 0.00354891 |
| AH 1X2 代理 Brier | 0.60639134 | 0.60433461 | 改善 0.00205672 |
| OU O2.5 Log Loss | 0.69029008 | 0.69157802 | 恶化 0.00128794 |
| OU O2.5 Brier | 0.24823206 | 0.24883453 | 恶化 0.00060246 |
| 精确比分 Log Loss | 2.99609365 | 2.99040238 | 改善 0.00569126 |

逐联赛半衰期计数和各联赛样本外 proper scores 在 [`m5_goal_model_recency_2026_oos.json`](results/m5_goal_model_recency_2026_oos.json)。AH 的概率质量有小幅改善，OU 略差；这些 proper scores 不是 ROI。

## Crown 收益回放

| 市场 / 模型 | 去重 forecast fixtures | Crown 有效 fixture | 模拟下注 / 已结算 | 全赢 / 半赢 / 走水 / 半输 / 全输 | 净收益 | ROI | 最大回撤 |
|---|---:|---:|---:|---|---:|---:|---:|
| AH M5 无衰减基线 | 10,235 | 317 | 317 / 317 | 124 / 20 / 25 / 20 / 128 | -12.960U | -4.088328% | 25.790U |
| AH 近期加权候选 | 10,235 | 317 | 317 / 317 | 127 / 20 / 25 / 20 / 125 | -6.765U | -2.134069% | 20.495U |
| OU M5 无衰减基线 | 10,235 | 317 | 317 / 317 | 139 / 19 / 18 / 23 / 118 | +7.100U | +2.239748% | 20.090U |
| OU 近期加权候选 | 10,235 | 317 | 317 / 317 | 135 / 20 / 18 / 22 / 122 | -0.355U | -0.111987% | 22.760U |

在完全相同 Crown 报价上，近期加权使 AH 点估计提高 1.954 个百分点，但仍为负；OU 点估计下降 2.352 个百分点，也转为轻微负值。两个市场均未达到严格大于 5% 的目标。每市场只有 317 场，不足以作为稳定盈利结论或正式模型替换依据。

相同 Crown 样本的 settlement Log Loss / Brier：AH 基线 `1.05273941 / 0.65440920`、候选 `1.04382035 / 0.64828452`；OU 基线 `1.00331741 / 0.63152205`、候选 `1.01106287 / 0.63711699`。这再次显示 AH 小幅改善、OU 变差。

## TotalCorner 事件时间样本去重扩展

为检查现有 TotalCorner historical endpoint movement 是否能补充独立市场样本，新增 [`m5_crown_oos_source_union.py`](m5_crown_oos_source_union.py)。它按规范化 `(联赛, UTC 比赛日, 主队, 客队)` fixture identity × market 合并两个 Crown 证据层：有赛前 `received < kickoff` 及独立 FT 的 MR1 V23 报价优先；只对 MR1 中缺席的 fixture-market 加入 TotalCorner Crown 历史 movement（其 source event < kickoff，但 endpoint 和比分是在赛后回取）。该规则在两个模型间完全相同，同一场同一市场最多一注，不把两个报价来源重复累计。

每个市场均有 MR1 317 场、TotalCorner event-time 212 场。按赛事 ID 和 `(规范化联赛, UTC 比赛日, 规范化主队, 规范化客队)` 两种核对，重叠均为 46 场；两个来源内部也都没有规范化 identity 重复。合并新增 166 场，得到 **483 个去重 fixture-market**。MR1 317 场上方表保持不变；TotalCorner 独有 166 场及去重并集如下：

| 市场 / 样本 | 基线 n / 净收益 / ROI / 最大回撤 | 近期加权 n / 净收益 / ROI / 最大回撤 |
|---|---|---|
| AH：TotalCorner 独有 event-time | 166 / -4.875U / -2.936747% / 9.620U | 166 / -20.425U / -12.304217% / 23.750U |
| AH：优先 MR1 后的去重并集 | 483 / -17.835U / -3.692547% / 25.790U | 483 / -27.190U / -5.629400% / 27.665U |
| OU：TotalCorner 独有 event-time | 166 / -2.065U / -1.243976% / 11.645U | 166 / -3.870U / -2.331325% / 10.760U |
| OU：优先 MR1 后的去重并集 | 483 / +5.035U / +1.042443% / 24.105U | 483 / -4.225U / -0.874741% / 26.600U |

去重并集的 AH 全赢/半赢/走水/半输/全输：基线 `191/26/44/28/194`，近期加权 `187/24/44/30/198`；OU：基线 `206/31/26/39/181`，候选 `200/34/26/36/187`。两个市场仍均未达到 +5%。TotalCorner event-time-only 记录并非赛前系统已收取的报价；此处单独给出，以免与 MR1 证据强度混淆。它只增加 166 个去重 fixture-market，不把 212 行与 317 行直接相加。

去重并集的 settlement Log Loss/Brier：AH 基线 `1.05750641 / 0.65658957`、近期加权 `1.05570593 / 0.65652276`；OU 基线 `1.00746797 / 0.63355740`、近期加权 `1.01732877 / 0.64124413`。概率质量虽有极小差异，实际 ROI 均未支持近期加权策略，尤其 AH 独有 event-time 子样本表现明显较差。

最大回撤按相同 Crown quote event 时间批次累计，避免对同时刻报价用赛事 ID 任意排序。逐联赛 Crown 结算汇总尚未从本次本地可用的归档重建；公开 union 收据目前只含市场和证据子组聚合。更新后的逐源与去重结果在 [`m5_goal_model_recency_2026_crown_source_union.json`](results/m5_goal_model_recency_2026_crown_source_union.json)。

与 M1、MR1 保存选择及 M3 原始模型的同价同时间 ROI 对照，在本次 317 场上没有可用的三方共同决策样本；当前回放的 `same_quote_saved_MR1_selection` 与 M3 精确盘口栏为空。之前已发表的 M1/M3 小样本或其他盘口时点不并入本实验，也不拿来证明优势。

## 限制与下一步

- Crown 配对覆盖为 317 / 10,235 个 2026 forecast（约 3.10%），距离每市场 10,000 个不重复、有效 Crown 报价及赛后结果样本还差很远。AH 与 OU 分开统计，不叠加市场行数。
- 当前 317 Crown 样本集中于 2026-Q4，缺少跨年/跨赛季 Crown ROI 稳定性证据。TotalCorner 原历史 endpoint movement 回放属于不同事件时间口径，不能并入本次已收取的 V23 快照 cohort。
- 这次不是对所有半衰期、联赛策略或回测规则的穷举搜索；没有根据 Crown ROI 选参。2025 参数选择样本仍然有限，2026 Crown 收益区间可能很宽，不能将点估计视为可靠盈利率。
- 要验证目标，最优先工作仍是补齐固定 51 联赛缺失赛程页，并获得至少每市场 10,000 场有 Crown 赛前 line/双边 price、可信 quote event/receipt UTC、独立 FT 的不重复样本。当前本地无 TotalCorner token，尚未发起新请求；不在公开仓库存储原始 Crown 价格、身份或令牌。

## 可复现文件

- [`m5_goal_model_recency_oos.py`](m5_goal_model_recency_oos.py)：2025 参数选择及 2026 近期加权逐联赛前推模型；逐场输出要求保存在私有目录。
- [`m5_goal_model_recency_2026_oos.json`](results/m5_goal_model_recency_2026_oos.json)：聚合 proper scores、逐联赛结果、半衰期分布及数据哈希。
- [`m5_goal_model_recency_2026_crown_oos.json`](results/m5_goal_model_recency_2026_crown_oos.json)：同一 MR1 V23 Crown/FT 样本上的 AH、OU 实际结算结果和来源哈希。
- [`m5_crown_oos_source_union.py`](m5_crown_oos_source_union.py) 与 [`m5_goal_model_recency_2026_crown_source_union.json`](results/m5_goal_model_recency_2026_crown_source_union.json)：MR1 优先、TotalCorner 仅补充非重叠 fixture-market 的去重回放。
