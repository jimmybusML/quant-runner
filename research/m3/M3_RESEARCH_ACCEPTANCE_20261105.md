# M3 独立 AH / OU 研究验收（2026-11-05）

## 验收结论

M3 已有可复现的 AH 与 OU 真实历史样本外概率评估、每四小时自动更新/重训/评分/留版工作流，且本次 GitHub Actions 成功并写入公开仓库。另以本地已留存的真实 Crown 赛前快照完成了小样本、AH/OU 分开的严格 OOS 概率回放。该回放使用事后生成的历史前推预测，不能代表当时实时预测或实际成交，样本太小且收益区间跨零。

用户已明确要求复用现有授权与合法数据，不申请新授权。本轮确认公开代码里现成的 Actions Secret 名称为 `TOTALCORNER_TOKEN`、`PRIVATE_REPO_TOKEN`，但绝不读取其值；历史 M3 Crown API 探测 run `39584036612` 成功。OddsPapi 凭证/连接器/历史存档均未发现。另有本地 Crown 历史档案，但只作为独立报价/赛果证据使用，不复用 M1/M2/MR1 预测、参数、订单或正式账本。

本轮新增 M3 专属前瞻采集器和每四小时 UTC workflow，限定 `bookmaker=crown`，只读公开 M3 forward ledger，训练截止按 UTC 日期严格早于比赛。TotalCorner 官方文档说明赔率变动列表按时间顺序记录，最后一行表示市场当前是否暂停；因此代码在预测后、开赛前收到 Crown API 响应时，只使用响应中的最后一条仍开放的赛前 AH/OU movement，并分别记录 API 接收 UTC 和供应商更新时间。旧的供应商更新时间不会被伪装成新变价；不设置盘口时效 Gate。文档：[TotalCorner Match Bookmaker Odds](https://www.totalcorner.com/page/api)。公开落库仅包含 HMAC 行/响应承诺、UTC 证据和聚合 EV，不包含凭证、原始响应、source match ID、盘口线或水位。

先前成功 run `41957259557` 捕获了18条 Crown 报价承诺，但旧 forecast 缺比分网格，因而没有精确线级 EV。为修复而新建的 v2 full-score-grid forecast 由 Actions run `41963253358` 产生并落库于 `1447079a`：累计新增3,897条带完整网格事件，原有旧事件未覆盖；run 报告的训练输入 fingerprint 变化来自 forecast 语义/键版本升级，而不代表赛果数据改变。

真实 Crown 前瞻 v2 run `41964509535` 于 `2026-11-05T03:54:47Z` 启动、`04:00:15Z` 成功，收据落库 commit `9bb37798`。检查144条预测；5场具有唯一 TotalCorner 赛程身份，43场因身份缺失/歧义拒绝；本轮写入18条新 Crown-only v2 HMAC 承诺（AH 9、OU 9），另保留18条旧 v1 收据。18条模型市场报价来自3场可用 fixture，3模型 × AH/OU，两方向各作描述性EV计算，未按EV选择投注方向。

| 独立市场/模型 | Crown 当前快照数 | 主队/Over 单位期望收益 | 客队/Under 单位期望收益 |
|---|---:|---:|---:|
| AH / Poisson | 3 | -8.20% | +2.57% |
| AH / Dixon-Coles | 3 | -8.88% | +3.24% |
| AH / Bivariate Poisson | 3 | -8.62% | +3.00% |
| OU / Poisson | 3 | -18.37% | +15.10% |
| OU / Dixon-Coles | 3 | -19.19% | +15.88% |
| OU / Bivariate Poisson | 3 | -17.02% | +13.68% |

该快照报告生成于 `2026-11-05T03:57:08.037581Z`。供应商报价行的更新时间距 API 接收时刻中位数386,745秒（约4.48天）、最大847,462秒（约9.81天）；报价在响应中仍是最新且未暂停的赛前行，因此作为当前 API 快照计算 EV，同时明确其更新时间年龄。5场唯一赛程身份里当前有报价的场次/市场覆盖，将由随后的覆盖报告按 AH 与 OU 分开列示。模型×市场×方向每格 n=3，样本很少；这些是理论期望收益，不是已实现盈利。当前比赛还没有可用结算，ROI、单位利润和最大回撤均为 null。用户已锁定的六联赛范围不变；当前 OpenFootball forward 数据没有 B1 fixture，故 B1 前瞻覆盖仍为0。

覆盖报告实跑 `41965481211` 于 `2026-11-05T04:04:20Z–04:14:08Z` 成功，报告、6条新增quote commitment及数据版本落库 commit `c6a239c0`。本次仍检查144条预测、精确识别5场；AH、OU 分别有3/5场（60%）具有当前 Crown 快照。累计保留42条（v1 18、v2 24）；不把重复报价行数误当作新增fixture数。当前 quote 更新时间年龄中位数121,386秒（约1.40天）、最大832,676秒（约9.64天）。最新每模型、市场、方向单位期望收益如下，n=3：AH Poisson 主/客 -7.69%/+1.22%，Dixon-Coles -8.37%/+1.88%，Bivariate Poisson -8.11%/+1.65%；OU Poisson 大/小 -19.02%/+13.50%，Dixon-Coles -19.76%/+14.29%，Bivariate Poisson -17.66%/+12.12%。这仍是小样本理论 EV，ROI、已实现单位收益和回撤均为空。

UTC 时间字段修复由真实 run `41966789454` 验证成功，branch head `e5974f79`；最终数据/报告持久化 commit `fb4a4f06`。`capture_started_utc=2026-11-05T04:18:00.118853Z`，报告生成 `generated_utc=2026-11-05T04:21:05.359425Z`。之后将每次 API 观察改为独立快照 HMAC 收据；唯一 quote-row fingerprint 单独判断盘口数据是否变化，不会将重复观察误计为新学习信息。

新快照协议与学习信息判定由真实 Actions run `41968378899` 通过，branch head `64e21725`；每次运行的18条 AH/OU 快照收据与新报告持久化于 commit `1bbf1c24`。采集起始 `2026-11-05T04:34:18.971522Z`，报告生成 `2026-11-05T04:37:42.077638Z`。当前统计保留78条收据（v1 18、v2 60），历史唯一 fixture-market-quote HMAC 行8条，本轮当前独立行6条；当轮新增独立 quote row 为0。预测输入与 Crown quote-row fingerprint 均未变化，报告明确 `new_learning_information=false`。AH、OU 当前快照各3/5唯一赛程场次（60%）；每模型/市场/方向 n=3。更新时间年龄中位数122,806秒（约1.42天）、最大834,107秒（约9.65天）。逐项理论 EV 与上表相同，赛后结果尚未出现，ROI仍为空。

## 最新真实历史样本外模型结果

最新严格 OOS Actions run [41956446597](https://github.com/ljm198964-alt/quant-runner/actions/runs/41956446597) 于 `2026-11-05T02:37:40Z–02:41:51Z` 成功；原版 V4、penaltyblog 1.13.1、83/83 M3 单测、严格前推和持久化步骤均通过。报告生成 UTC `2026-11-05T02:41:39.105883Z`，输入 fingerprint `648aa1d7…77cb4e` 与前次相同，报告标记 `data_changed_vs_previous_snapshot=false`。训练数据没有新增，但相同输入重训后 prediction SHA 更新为 `48857e6d…725289a`、parameter SHA 更新为 `4c01d5ff…d8c90`，故本次分数代表新保存模型版本。可用样本 19,218 场、6 个既定联赛（B1、D1、E0、F1、I1、SP1），跨赛季 2017/18 至 2026/27；测试集 17,152 场，评分 14,806 场（86.32%）。

训练隔离按联赛及测试赛季执行：只取更早赛季文件，且训练比赛 UTC 日期早于该测试赛季最早比赛日期；测试日期/赛季结果不用于该 split 拟合。数据只有日历日期，统一作为 UTC 日期解析且整场测试日期均从训练集排除；它不提供实际 kickoff UTC。报告与模型参数快照记录在 `results/latest_penaltyblog_oos_report.json`、`results/latest_penaltyblog_oos_splits.json`、`results/predictions/`、`results/model_parameters/`。

| 独立市场/概率 | 模型 | N | Log Loss | Brier |
|---|---|---:|---:|---:|
| AH0 主队 DNB 三状态 | Poisson | 14,806 | 1.003890 | 0.599400 |
| AH0 主队 DNB 三状态 | Dixon-Coles | 14,806 | 1.003793 | 0.599232 |
| AH0 主队 DNB 三状态 | Bivariate Poisson | 14,806 | 1.003783 | 0.599255 |
| OU Over 2.5 | Poisson | 14,806 | 0.686562 | 0.246557 |
| OU Over 2.5 | Dixon-Coles | 14,806 | 0.686584 | 0.246567 |
| OU Over 2.5 | Bivariate Poisson | 14,806 | 0.686585 | 0.246580 |

AH 数字是 AH0/DNB 三状态 proper score，不是所有让球盘线表现。OU 全样本实际 Over 2.5 率 53.59%；三模型平均预测 51.88%–52.21%，当前表现为约 1.38–1.71 个百分点的低估迹象，需在未来样本核验，不据此修改模型或筛选赛事。现有 report 含分箱校准与逐赛季分数，可复核跨季变化；本轮没有改变样本或统计口径。

## Crown 可核实历史线价回放

聚合结果及方法快照见 [`results/m3_crown_oos_replay_20261105.json`](results/m3_crown_oos_replay_20261105.json)。该次历史 Crown hindcast 回放使用 run `41949912425` 的 OOS forecast；本次最新严格 OOS 模型版本已更新为 `41956446597`，因此该 Crown 回放是旧的 hindcast 版本，尚未按新 prediction SHA 重算。输入为本地留存的、标记 Crown 且具备观测/接收 UTC、精确 fixture 身份、赛前 kickoff 和 kickoff 后独立 FT 的快照归档；此处只用报价与赛果证据，未使用 M1/M2/MR1 的预测、参数、订单或正式账本。没有进行网络/API 请求。原始报价、队名、fixture ID 均未公开。

严格 M3 OOS 预测集合 14,806 场；122 个精确联结候选中排除 1 个身份碰撞，得到 121 个唯一 fixture，其中 76 个有 kickoff 后独立 FT。Crown 有效报价及赛果覆盖：AH0 24 场、OU2.5 36 场，两个市场独立报告；仅 8 场同时覆盖两市场。AH quote event UTC 范围为 2026-10-08 至 2026-11-01，OU 为 2026-10-08 至 2026-11-01。采用每场可用模型中模型隐含收益较高的一侧，单位注额结算，不设 EV 阈值；这是为复现研究回放而固定的评估口径，不是交易规则。

| 市场/模型 | N | W/P/L | 净单位 | ROI | 最大回撤 | Log Loss / Brier | ROI bootstrap 95%描述区间 |
|---|---:|---:|---:|---:|---:|---:|---:|
| AH0 Poisson | 24 | 12/7/5 | +5.91 | +24.63% | 3.00 | 1.076412 / 0.650943 | -6.58% 至 +54.67% |
| AH0 Dixon-Coles | 24 | 12/7/5 | +5.91 | +24.63% | 3.00 | 1.073643 / 0.649483 | -6.58% 至 +54.67% |
| AH0 Bivariate Poisson | 24 | 12/7/5 | +5.91 | +24.63% | 3.00 | 1.072938 / 0.649091 | -6.58% 至 +54.67% |
| OU2.5 Poisson | 36 | 16/0/20 | -5.54 | -15.39% | 10.09 | 0.694815 / 0.250781 | -46.64% 至 +15.72% |
| OU2.5 Dixon-Coles | 36 | 16/0/20 | -5.54 | -15.39% | 10.09 | 0.694818 / 0.250782 | -46.64% 至 +15.72% |
| OU2.5 Bivariate Poisson | 36 | 18/0/18 | -1.66 | -4.61% | 8.26 | 0.694174 / 0.250460 | -36.22% 至 +26.61% |

结果可核实地使用了 Crown 同期赛前线价，但 M3 预测值是从严格赛季前推研究文件事后生成的历史 OOS hindcast，并非当时保存的预测。ROI 是无成交回执的单位注额影子回放，不能称为实际交易 ROI。样本极小，所有收益区间均跨零，不能据此认定 edge。`max_drawdown` 仅对上述有限的单位收益序列计算。

## OU 上游 Football Predictor V4 原版审计

原版来自 `pkotengpoku/football-predictor` 固定上游 commit `2f75be0f26363e26a42aaff34ede68f35635da02`；Actions 按其 V4 入口和特征工程运行，分赛季 walk-forward 指标保存在 `results/latest_v4_original_metrics.csv`。当前仍须注意该检出版本未见明确根许可证文件；M3 不复制其源码，只按既有工作流调用。五个目标模型分别为 LightGBM、Logistic、Market-anchored Logistic、Market-residual Logistic、Market-blend Logistic。

作者原版自带阈值下的 ROI（按其上游赔率/口径，仅还原作者实验，绝非 Crown ROI）跨赛季不稳定。以 2021/22、2022/23、2025/26、2026/27 部分赛季为例，LightGBM 为 -11.33%、-8.08%、+8.17%、-19.81%；Logistic 为 -6.66%、-0.53%、-2.66%、-11.86%；Market-anchored 为 -3.57%、-15.77%、-32.09%、-16.07%；Market-residual 在有报告赛季为 -10.85%、-20.01%；Market-blend 有报告赛季为 -5.43%、-22.80%。2023/24、2024/25 多模型 ROI 留空是上游原结果，不补造。当前季样本每模型 507 场且未完赛。逐季 Log Loss、Brier、校准与其余指标见 CSV。原版阈值没有移植为 M3 交易条件或 Gate。

## 其他成熟开源方案审计

AH/OU 补充候选 `opisthokonta/goalmodel`：当前检视版本 v0.6.4（2024-03-30），`DESCRIPTION` 声明 GPL-3；支持 Poisson、负二项、Conway-Maxwell-Poisson goal marginals、可选 Dixon-Coles 低比分修正、比分联合矩阵与 OU 概率。它没有内置严格前推验证；比分矩阵来自主客进球边际外积，不是共享成分 Bivariate Poisson。方法增量是分布离散度选择，适合后续隔离实验，但维护间隔较长、当前没有独立 M3 实测结果；没有引入生产依赖，也没有把候选表述为已验证方案。

## 自动化、数据追溯与工程边界

- `.github/workflows/m3-independent-research.yml` 维持用户已确认的 `0 */4 * * *` UTC 频率，并可手动运行；最新真实 OOS run `41956446597` 成功，83项 M3 单测通过，同时执行原版 V4、三种 penaltyblog 模型、严格 OOS 评分、输入指纹比较及持久化。当前 run 保存到 `results/latest_penaltyblog_oos_report.json` 与带哈希的预测/参数快照。
- 输入 fingerprint 与前次相同、没有新增结果数据；重复拟合后模型参数/预测文件 SHA 改变，分数仅有微小差异（例如 AH0 Dixon-Coles Log Loss 从上一版 `1.003785` 到当前 `1.003793`）。原因尚未确定，可能与优化过程或序列化有关。比较报告按同一测试集留存差异；不宣称逐字节可复现，需继续审计 penaltyblog 拟合确定性。
- `.github/workflows/m3-crown-forward-capture.yml` 与 `m3_crown_forward_capture.py` 保持四小时 UTC 频率，只请求 Crown。接口响应必须在 forecast 后、kickoff 前；该响应中的最后一条仍开放的赛前 AH/OU movement 用于快照 EV，供应商 quote-update time 与 API receipt time 分开保留。报告按 AH/OU、模型、方向汇总 EV 和按市场覆盖；不设置任何 freshness Gate。公开收据仅保存 HMAC 与聚合值，不保存原始赔率数据。
- v2 完整比分网格由 run `41963253358` 在分支生成并于 commit `1447079a` 持久化；本次新建3,897条预测且不覆盖旧 ledger。首次 v2 Crown run `41964509535` SUCCESS，收据落库 `9bb37798`：检查144条预测、5场唯一 Crown fixture、18条新 v2 quote receipt；3个 fixture 实际有 AH/OU 当前快照，各模型/市场/方向 n=3，EV 分项与更新时间年龄见报告开头。ROI 尚无已结算前瞻样本，保持 null。修复覆盖摘要的 run `41965481211` 执行中，结束后需更新其实际数据与落库 SHA。最新代码本地 M3 suite 为87/87。
- 本次修复 M3 手动 Crown 探测脚本：删除 TotalCorner 默认赔率 fallback；日志不再输出源 match ID、bookmaker 字段形状或报价样例，只报告 Crown 识别状态与行数。没有触碰其他模型 workflow 或任何正式链路，也没有执行该探测 workflow。
- 已检查已有 Crown Secret 名称 `TOTALCORNER_TOKEN`、`PRIVATE_REPO_TOKEN`，从未读取值。发现 2026-10-21 历史固定 ID Crown 探测成功记录；这不是持续前瞻报价存档。OddsPapi 的凭证/连接器/归档未找到。M3 forward-EV 的 TotalCorner default bookmaker 记录严格排除，不代替 Crown。
- TotalCorner API 文档和现行公开条款仍提醒自动化抽取、数据保留/公开派生结果须符合供应商授权。用户已明确指示复用项目现有授权；本实现不索取新权限、不把 Secret 存在视为独立许可证明，也不输出原始价格。公开仓库只保留 HMAC 证据与聚合研究指标。此次功能采用用户确认的现有授权运行；如果实际 Action 因授权/Secret 配置失败，记录脱敏错误状态，绝不回退到其他赔率源。
- 该 workflow 不克隆或写入 M1/MR1 私有仓库，仅读取公开 M3 `shadow_ledger`，并在公开仓库保存 M3 自己的 forward forecast 和 value-free commitment。当前 forward OpenFootball 源仍不含 B1 fixture；B1 仍在六联赛研究范围中，但该采集来源的 B1 覆盖为零，后续须用独立 M3 forecast 源填补。
- 前瞻 Crown ROI 仍未产生：最新捕获的比赛尚无结算。需要继续让四小时任务累积预测前快照并等 OpenFootball 独立赛果；赛后报价行的 HMAC 复核与逐笔单位收益/最大回撤自动汇总器尚未实现，当前不得从快照 EV 推断 ROI。真实快照的 quote-update time 年龄也需跨场次持续报告，但不得据此自动拒绝盘口。

## 完成状态与下一步

已完成：真实历史 AH/OU 样本外预测；独立概率评分；Crown 历史快照小样本概率与 ROI 影子回放；V4 OU 原版评估；另一个开源方案审计；每四小时自动训练、指标比较、哈希追踪及报告留版；M3 探测脚本的 Crown-only 与安全日志修复。

未完成：前瞻样本的赛后 Crown HMAC 复核与实现收益报告；足够长的 AH/OU 前瞻 OOS 与校准；B1 独立 M3 forward forecast；第三方候选 `goalmodel` 的真实独立 OOS 运行；用最新 OOS forecast SHA 重跑本地 Crown hindcast。当前三场有效 Crown 当前快照可估计线级 EV，但每模型/市场/方向 n=3，不足以推断稳定性；没有任何已结算前瞻 ROI。既有历史 Crown 回放 AH0 24 场、OU2.5 36 场仍是较旧版本的严格前推 hindcast，不能称作 contemporaneous 实际收益；其区间宽且跨零。没有扩大或缩小既定联赛范围，也未增加任何 Gate。

最值得继续：推送后立即手动触发 `m3-crown-forward-capture.yml`，检验现有 Secret 在该研究 workflow 中可用、UTC 配对与私密值抑制均成立；记录实际 Actions ID、报告与落库 commit。随后增加按 HMAC 回取 history row 的赛后 evaluator，分 AH/OU 留存公平 EV、Log Loss/Brier、ROI 和有效收益序列；维持每市场独立样本且等待真实数据。此前不加 EV、置信度、数量、时效或联赛 Gate，不自动升版、不启用 Telegram。

## 2026-11-05 main 线上状态复核与自动化故障

本节按最新公开 main `c40a70da7d2eed6f1d749fa4a662ae4d02842631` 和 GitHub Actions 实际记录复核，UTC 查询时间为 `2026-11-05T03:25Z` 附近。它更新运行状态，不改变原先样本口径：

- 独立训练/OOS run [41956446597](https://github.com/ljm198964-alt/quant-runner/actions/runs/41956446597) 在 `2026-11-05T02:37:40Z` 成功；同一 workflow 的 OOS 与 V4 结果确实提交到公开仓库，receipt commit 为 `6a66232`。M3 测试 83/83 通过。输入指纹未变 (`648aa1d7…77cb4e`)，所以没有新增赛果学习信息；重拟合后 parameter/prediction SHA 改变，逐字节拟合确定性仍未解释。
- 最新 Crown 专属前瞻 run [41957259557](https://github.com/ljm198964-alt/quant-runner/actions/runs/41957259557) 在 `2026-11-05T02:50:19Z` 成功，报告和承诺文件已提交公开 main，commit `1f1721f2`。真实输入为 TotalCorner `bookmaker=crown`；144 个 forecast 只映射到 5 个唯一 fixture identity，保留 18 个不含明文价格/盘线/赛事源 ID 的 HMAC 行承诺，AH 9、OU 9；另 43 场因 schedule identity 缺失或歧义被拒绝。forecast 首次指纹没有基线，新增学习信息未知。由于这 5 场命中的仍是旧 forecast，未含 full score grid，线级 EV、真实赛果评分、ROI 和回撤均为 null。18 个承诺不是 18 个已结算样本。
- 同日 `m3-totalcorner-forward-ev.yml` run [41952143472](https://github.com/ljm198964-alt/quant-runner/actions/runs/41952143472) 失败在私有 `totalcorner-research-bridge` 完赛缓存 checkout；GitHub 的 `PRIVATE_REPO_TOKEN` 名称存在，但这次 fetch 未获认证。没有检查 Secret 值。该旧 workflow 读取 M1 完赛缓存，不能代表 M3 Crown-only 前瞻工作流，结果不纳入本报告。TotalCorner Crown workflow 已独立成功，故此次失败没有阻断 Crown 采集；私有缓存依赖仍需有权限的仓库维护者修复。
- AH reverse research workflow 的 run [41958838179](https://github.com/ljm198964-alt/quant-runner/actions/runs/41958838179) `failure` 且零 job。核实为 YAML 把 `with:` 挂在 `run:` 步骤下；本提交删除无效的 `with` 子块，ledger materialize 本身从当前 checkout 的不可变 Git baseline 读取。另将摘要 rebase/push 改为当前 dispatch ref，避免从功能分支手动验收时写入 main。该 reverse audit 明确用 `TotalCorner default NOT Crown` 旧影子数据，不能用于 Crown ROI。
- `m3-totalcorner-auto-shadow.yml` 的 run [41951424819](https://github.com/ljm198964-alt/quant-runner/actions/runs/41951424819) 失败原因是 workflow 未安装 `requests`，而代码导入它。该工作流使用 `default_unspecified_NOT_CROWN` 数据，仅用于独立旧影子审计；本次不把它重标为 Crown，也不将该非 Crown 的 EV/回报记录混入 Crown 研究。
- Secret 名称元数据仅确认 `TOTALCORNER_TOKEN`、`PRIVATE_REPO_TOKEN` 存在；没有读取值。OddsPapi 凭据或已存数据仍未发现。成功的 Crown run 证明当前 Crown capture 路径使用的现有 TotalCorner 凭据可执行该次采集，不构成更宽历史回填或公开原始数据权限证明。依用户明确指示，未索取新授权，也未回退至其它公司赔率。

这次复核没有改 M1、M2、MR1 生产链路，没有 Telegram、模型自动晋升、新交易 gate 或用户冻结的赛事范围变更。

## 2026-11-05 前瞻比分分布版本键修复

定位到旧账本没有比分网格却被当前幂等键视为新版预测的原因：早期 8,430 条 forecast 都缺少 `model_semantic_version`、full score grid 和显式 forecast-key；迁移回退把它们视为当前语义版本，同时 `_forecast_key` 的默认参数在模块载入时固定为旧常量。现在将保存比分网格的前瞻记录标记为 `penaltyblog-goal-distribution-v2`，将缺失语义版本的旧记录固定解释为 v1，并令 forecast-key 在运行时读取语义版本。模型算法、训练样本、旧事件与结算结果不变；仍符合 UTC 日期保护的未来 fixture 将以当前时点追加 v2 forecast 和比分分布，旧 v1 行完整保留，不对已过 fixture 追补预测。

新增回归测试验证：同一 fixture 的旧 v1 行不被覆写或 supersede；v2 会追加同训练输入哈希的 current-as-of full-score-grid 预测；下次相同 v2 输入仍保持幂等。隔离 Python 3.12 环境使用 penaltyblog 1.13.1 全量 M3 单测 85/85 通过。真实 Actions 与 Crown 配对验收尚待本代码变更后的 workflow_dispatch run，届时报告新增 v2 forecast 数、唯一 fixture 数、AH/OU quote commitment 和可计算 EV 计数；预期的收益与样本外结算仍需之后的完赛和独立 FT receipt 才能计算。
