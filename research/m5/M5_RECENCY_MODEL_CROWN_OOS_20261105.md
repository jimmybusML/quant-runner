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

## Crown 收益回放（前一份存档快照，已由下方刷新结果取代）

| 市场 / 模型 | 去重 forecast fixtures | Crown 有效 fixture | 模拟下注 / 已结算 | 全赢 / 半赢 / 走水 / 半输 / 全输 | 净收益 | ROI | 最大回撤 |
|---|---:|---:|---:|---|---:|---:|---:|
| AH M5 无衰减基线 | 10,235 | 317 | 317 / 317 | 124 / 20 / 25 / 20 / 128 | -12.960U | -4.088328% | 25.790U |
| AH 近期加权候选 | 10,235 | 317 | 317 / 317 | 127 / 20 / 25 / 20 / 125 | -6.765U | -2.134069% | 20.495U |
| OU M5 无衰减基线 | 10,235 | 317 | 317 / 317 | 139 / 19 / 18 / 23 / 118 | +7.100U | +2.239748% | 20.090U |
| OU 近期加权候选 | 10,235 | 317 | 317 / 317 | 135 / 20 / 18 / 22 / 122 | -0.355U | -0.111987% | 22.760U |

在完全相同 Crown 报价上，近期加权使 AH 点估计提高 1.954 个百分点，但仍为负；OU 点估计下降 2.352 个百分点，也转为轻微负值。两个市场均未达到严格大于 5% 的目标。每市场只有 317 场，不足以作为稳定盈利结论或正式模型替换依据。

相同 Crown 样本的 settlement Log Loss / Brier：AH 基线 `1.05273941 / 0.65440920`、候选 `1.04382035 / 0.64828452`；OU 基线 `1.00331741 / 0.63152205`、候选 `1.01106287 / 0.63711699`。这再次显示 AH 小幅改善、OU 变差。

## TotalCorner 事件时间样本去重扩展（前一份存档快照，已由下方刷新结果取代）

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


## 2026-11-05 MR1 Crown 档案刷新：871 verified + 70 event-time

使用已授权的本地只读 MR1 存档 the already authorized local MR1 repository archive 重放。上一份 317/483 结果使用较早的 MR1 fixture-registry/snapshot-index 指纹；本次严格保留新输入指纹，不把两个版本的行数相加。最新输出生成于 `2026-11-04T23:23:10.323370Z`，fixture registry SHA `891a1092095f8ced9cadaae613457233dd7986501ebf92a81ad06f47d3ea79ca`，snapshot index SHA `107f1635b7642dd2d4057500ea7105df2355934a00590bd3f6daeb3355e45a8a`，基线/候选预测 SHA 仍为 `ebc8ae9aa4c873f3d276510533a9961c607cc607614f976a2d2e1147dbdb356a` / `fc2abf89b2ac80eb2ba72bf9e992f25eeda11502f2e87cd2bd965b921843d26d`。

每市场有 871 个 MR1 Crown quote received-before-kickoff 且有独立 FT 的唯一 fixture，覆盖 48 个联赛；TotalCorner endpoint 共 212 个 event-time fixture，与 MR1 按规范化联赛、UTC日期、主客身份重合 142 个，补充 70 个不重叠场，最终 source-priority union 为 941 fixture-market、49 个联赛。AH/OU 独立统计，同一 fixture-market 只结算一次。TotalCorner 的 event timestamp 早于开赛，但 endpoint 与嵌入比分在赛后取得，仍不算赛前收到的历史报价。

| 市场 / 证据样本 | 模型 | 场数 | W/HW/P/HL/L | 净 U / ROI | 最大回撤 U | 95% fixture-bootstrap ROI 区间 | Settlement LL / Brier |
|---|---|---:|---|---:|---:|---|---|
| AH MR1 received | M5 基线 | 871 | 354/55/56/66/340 | -17.825 / -2.046498% | 28.900 | -7.756028% 至 +3.767509% | 1.03171136 / 0.64617416 |
| AH MR1 received | 近期加权 | 871 | 352/60/56/61/342 | -16.940 / -1.944891% | 24.555 | -7.652124% 至 +3.848450% | 1.03004581 / 0.64562197 |
| AH union | M5 基线 | 941 | 384/57/61/68/371 | -21.010 / -2.232731% | 28.900 | -7.866100% 至 +3.393199% | 1.03068920 / 0.64490442 |
| AH union | 近期加权 | 941 | 379/61/61/64/376 | -26.905 / -2.859192% | 27.810 | -8.352816% 至 +2.919766% | 1.02985212 / 0.64521313 |
| OU MR1 received | M5 基线 | 871 | 358/51/45/63/354 | -31.075 / -3.567738% | 51.600 | -9.388634% 至 +2.369690% | 1.01610124 / 0.64262006 |
| OU MR1 received | 近期加权 | 871 | 357/53/45/61/355 | -32.485 / -3.729621% | 51.505 | -9.669346% 至 +2.159587% | 1.02220923 / 0.64711209 |
| OU union | M5 基线 | 941 | 388/55/49/71/378 | -28.900 / -3.071201% | 50.325 | -8.730606% 至 +2.583953% | 1.01371083 / 0.64033632 |
| OU union | 近期加权 | 941 | 386/56/49/70/380 | -33.000 / -3.506908% | 55.495 | -9.216791% 至 +2.138151% | 1.02090617 / 0.64582477 |

在相同 871 个 MR1 Crown 合约上，近期加权相对基线 AH ROI 差 `+0.101607` 个百分点、OU `-0.161883` 个百分点；fixture-paired bootstrap 95% 区间分别为 `[-3.739380,+3.794489]` 与 `[-3.873708,+3.504592]`。在 941 场 union 上差值为 AH `-0.626461pp`（区间 `[-4.393199,+3.121679]`）、OU `-0.435707pp`（`[-4.044633,+3.148778]`）。这些区间都跨零；没有证据证明近期加权提升 Crown 收益。两个市场的完整逐联赛 W/HW/P/HL/L、净 U 与 ROI 在 [`m5_goal_model_recency_2026_crown_source_union.json`](results/m5_goal_model_recency_2026_crown_source_union.json)，49 联赛结果仅为描述性分布，不作联赛过滤。

同一最新 MR1 归档上的独立时间留出：每市场 871 个 source-verified quote fixture，以报价事件 UTC 时间排序；训练集 606 个且对应独立 FT receipt 早于首个测试报价，另有 3 个前边界 quote 因 FT receipt 太晚而 purged；之后 262 场严格留出。AH 截点 `2026-10-22T13:59:01Z`，OU 截点 `2026-10-22T11:20:39Z`。只在各自早期训练集上用 settlement log loss 选温度，AH=1.75、OU=1.25；未用 ROI 选温度。测试集：AH 原始网格 `-6.910305%`（97/18/18/23/106 W/HW/P/HL/L），校准 `-6.438931%`（97/19/18/22/106），95% bootstrap 区间 `[-16.998092,+4.124046]%`；OU 原始 `-14.045802%`（95/12/13/23/119），校准 `-14.541985%`（94/13/13/22/120），校准后 settlement LL/Brier 有改善至 `1.00816505/0.63673964`，但 ROI 更差，95% 区间 `[-25.009542,-3.729008]%`。此严格时间测试不支持达到 +5% 目标；它不是新的投注规则或模型上线建议。完整分割、训练分数、bootstrap、来源 hash 在 [`m5_crown_temperature_holdout.json`](results/m5_crown_temperature_holdout.json)。其 MR1 registry SHA 与 union 输入一致，为 `891a1092…`。

## 限制与下一步

- 最新 verified MR1 Crown 覆盖为 871 / 10,235 个 2026 forecast（AH、OU分别计数，市场间不叠加）；含 70 个 TotalCorner-only event-time 增量的并集为每市场 941 场。两者都远低于每市场 10,000 个不重复样本。
- 当前 871 场 received-before-kickoff Crown 样本集中在 2026-09-19 至 2026-11-03；没有跨年/跨赛季 ROI 稳定性证据。TotalCorner 赛后回取 movement 仍单独列为较弱 event-time cohort。
- 这次不是对所有半衰期、联赛策略或回测规则的穷举搜索；没有根据 Crown ROI 选参。2025 参数选择样本仍然有限，2026 Crown 收益区间可能很宽，不能将点估计视为可靠盈利率。
- 要验证目标，最优先工作仍是补齐固定 51 联赛缺失赛程页，并获得至少每市场 10,000 场有 Crown 赛前 line/双边 price、可信 quote event/receipt UTC、独立 FT 的不重复样本。当前本地无 TotalCorner token，尚未发起新请求；不在公开仓库存储原始 Crown 价格、身份或令牌。

## 可复现文件

- [`m5_goal_model_recency_oos.py`](m5_goal_model_recency_oos.py)：2025 参数选择及 2026 近期加权逐联赛前推模型；逐场输出要求保存在私有目录。
- [`m5_goal_model_recency_2026_oos.json`](results/m5_goal_model_recency_2026_oos.json)：聚合 proper scores、逐联赛结果、半衰期分布及数据哈希。
- [`m5_goal_model_recency_2026_crown_oos.json`](results/m5_goal_model_recency_2026_crown_oos.json)：同一 MR1 V23 Crown/FT 样本上的 AH、OU 实际结算结果和来源哈希。
- [`m5_crown_oos_source_union.py`](m5_crown_oos_source_union.py) 与 [`m5_goal_model_recency_2026_crown_source_union.json`](results/m5_goal_model_recency_2026_crown_source_union.json)：MR1 优先、TotalCorner 仅补充非重叠 fixture-market 的去重回放。
