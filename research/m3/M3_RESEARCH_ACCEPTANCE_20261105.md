# M3 独立 AH / OU 研究验收（2026-11-05）

## 验收结论

M3 已有可复现的 AH 与 OU 真实历史样本外概率评估、每四小时自动更新/重训/评分/留版工作流，且本次 GitHub Actions 成功并写入公开仓库。另以本地已留存的真实 Crown 赛前快照完成了小样本、AH/OU 分开的严格 OOS 概率回放。该回放使用事后生成的历史前推预测，不能代表当时实时预测或实际成交，样本太小且收益区间跨零。

尚未满足“实时前瞻 Crown 配对采集已运行”的验收项。已有 TotalCorner Token Secret 名称和历史探测成功记录，但仓库没有可追溯的提供方书面许可引用/范围；这不证明用户没有既有许可。遵照用户指示不申请新授权、不重复申请；在可核实的既有许可范围尚未找到前，不发起新 API 请求或建立自动采集。不会披露凭证值、私有逐场数据或报价。

## 最新真实历史样本外模型结果

GitHub Actions run [41943100635](https://github.com/ljm198964-alt/quant-runner/actions/runs/41943100635) 于 2026-11-05 成功。报告生成 UTC `2026-11-05T00:44:41.469266Z`；输入指纹 `648aa1d7…77cb4e`，与前版不同；严格 OOS 预测 CSV SHA-256 `48857e6d…725289a`。Football-Data.co.uk 的赛果 CSV 只读取日期、主客队和全场进球，未读取文件内赔率。可用样本 19,218 场、6 个既定联赛（B1、D1、E0、F1、I1、SP1），跨赛季 2017/18 至 2026/27；测试集 17,152 场，模型成功评分 14,806 场（86.32%）。

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

聚合结果及方法快照见 [`results/m3_crown_oos_replay_20261105.json`](results/m3_crown_oos_replay_20261105.json)。输入为本地留存的、标记 Crown 且具备观测/接收 UTC、精确 fixture 身份、赛前 kickoff 和 kickoff 后独立 FT 的快照归档；此处只用报价与赛果证据，未使用 M1/M2/MR1 的预测、参数、订单或正式账本。没有进行网络/API 请求。原始报价、队名、fixture ID 均未公开。

严格 M3 OOS 预测集合 14,806 场；122 个精确联结候选中排除 1 个身份碰撞，得到 121 个唯一 fixture，其中 76 个有 kickoff 后独立 FT。Crown 有效报价及赛果覆盖：AH0 24 场、OU2.5 36 场，两个市场独立报告；仅 8 场同时覆盖两市场。AH quote event UTC 范围为 2026-10-08 至 2026-11-01，OU 为 2026-10-08 至 2026-11-01。采用每场可用模型中模型隐含收益较高的一侧，单位注额结算，不设 EV 阈值；这是为复现研究回放而固定的评估口径，不是交易规则。

| 市场/模型 | N | W/P/L | 净单位 | ROI | 最大回撤 | Log Loss / Brier | ROI bootstrap 95%描述区间 |
|---|---:|---:|---:|---:|---:|---:|---:|
| AH0 Poisson | 24 | 12/7/5 | +5.91 | +24.63% | 3.00 | 1.076413 / 0.650943 | -6.92% 至 +53.13% |
| AH0 Dixon-Coles | 24 | 12/7/5 | +5.91 | +24.63% | 3.00 | 1.073640 / 0.649481 | -6.92% 至 +53.13% |
| AH0 Bivariate Poisson | 24 | 12/7/5 | +5.91 | +24.63% | 3.00 | 1.072940 / 0.649093 | -6.92% 至 +53.13% |
| OU2.5 Poisson | 36 | 16/0/20 | -5.54 | -15.39% | 10.09 | 0.694815 / 0.250781 | -46.72% 至 +15.97% |
| OU2.5 Dixon-Coles | 36 | 16/0/20 | -5.54 | -15.39% | 10.09 | 0.694818 / 0.250782 | -46.72% 至 +15.97% |
| OU2.5 Bivariate Poisson | 36 | 18/0/18 | -1.66 | -4.61% | 8.26 | 0.694174 / 0.250460 | -36.03% 至 +26.53% |

结果可核实地使用了 Crown 同期赛前线价，但 M3 预测值是从严格赛季前推研究文件事后生成的历史 OOS hindcast，并非当时保存的预测。ROI 是无成交回执的单位注额影子回放，不能称为实际交易 ROI。样本极小，所有收益区间均跨零，不能据此认定 edge。`max_drawdown` 仅对上述有限的单位收益序列计算。

## OU 上游 Football Predictor V4 原版审计

原版来自 `pkotengpoku/football-predictor` 固定上游 commit `2f75be0f26363e26a42aaff34ede68f35635da02`；Actions 按其 V4 入口和特征工程运行，分赛季 walk-forward 指标保存在 `results/latest_v4_original_metrics.csv`。当前仍须注意该检出版本未见明确根许可证文件；M3 不复制其源码，只按既有工作流调用。五个目标模型分别为 LightGBM、Logistic、Market-anchored Logistic、Market-residual Logistic、Market-blend Logistic。

作者原版自带阈值下的 ROI（按其上游赔率/口径，仅还原作者实验，绝非 Crown ROI）跨赛季不稳定。以 2021/22、2022/23、2025/26、2026/27 部分赛季为例，LightGBM 为 -11.33%、-8.08%、+8.17%、-19.81%；Logistic 为 -6.66%、-0.53%、-2.66%、-11.86%；Market-anchored 为 -3.57%、-15.77%、-32.09%、-16.07%；Market-residual 在有报告赛季为 -10.85%、-20.01%；Market-blend 有报告赛季为 -5.43%、-22.80%。2023/24、2024/25 多模型 ROI 留空是上游原结果，不补造。当前季样本每模型 507 场且未完赛。逐季 Log Loss、Brier、校准与其余指标见 CSV。原版阈值没有移植为 M3 交易条件或 Gate。

## 其他成熟开源方案审计

AH/OU 补充候选 `opisthokonta/goalmodel`：当前检视版本 v0.6.4（2024-03-30），`DESCRIPTION` 声明 GPL-3；支持 Poisson、负二项、Conway-Maxwell-Poisson goal marginals、可选 Dixon-Coles 低比分修正、比分联合矩阵与 OU 概率。它没有内置严格前推验证；比分矩阵来自主客进球边际外积，不是共享成分 Bivariate Poisson。方法增量是分布离散度选择，适合后续隔离实验，但维护间隔较长、当前没有独立 M3 实测结果；没有引入生产依赖，也没有把候选表述为已验证方案。

## 自动化、数据追溯与工程边界

- `.github/workflows/m3-independent-research.yml` 维持用户已确认的 `0 */4 * * *` UTC 频率，并可手动运行；本次 run `41943100635` 成功，执行原版 V4 和三种 penaltyblog 模型、严格 OOS 评分、输入指纹比较及持久化。模型数、参数哈希、预测哈希、run ID、UTC 生成时间与历史版本均留存。
- 本次输入 fingerprint 相对前版变化，代表有新增/更新的数据输入；若后续不变，工作流应记录无新增学习信息，不人为制造优化。
- run 结束成功并不代表 Crown collector 已运行。M3 自动流程当前不采集 Crown。
- 本次修复 M3 手动 Crown 探测脚本：删除 TotalCorner 默认赔率 fallback；日志不再输出源 match ID、bookmaker 字段形状或报价样例，只报告 Crown 识别状态与行数。没有触碰其他模型 workflow 或任何正式链路，也没有执行该探测 workflow。
- 已检查已有 Crown Secret 名称 `TOTALCORNER_TOKEN`、`PRIVATE_REPO_TOKEN`，从未读取值。发现 2026-10-21 历史固定 ID Crown 探测成功记录；这不是持续前瞻报价存档。OddsPapi 的凭证/连接器/归档未找到。M3 forward-EV 的 TotalCorner default bookmaker 记录严格排除，不代替 Crown。
- 官方 TotalCorner 资料列出 Crown AH/goal 赔率移动 API；现行公开条款提到自动抽取需要事前书面许可。公开仓库未发现可追溯的既有许可引用，无法确认现有许可具体覆盖 unattended API、M3 research、留存和发布哪些聚合字段。用户明确要求复用既有授权且不重复申请；此处不请求新的授权。当前精确缺项是**可在既有获准记录中定位的授权范围证据**。不会基于 Secret 存在或过去探测推断权限。
- 公开 Actions runner 没有 M3 专属、可验证的私有持久化报价仓库与独立加密密钥记录。不得把含原始报价的 artifact 或 commit 公开。前瞻采集仍需在既有授权证据可定位后，用 M3 独立隔离存储/密钥和可审计的 UTC 观测/接收时间做配对；不可复用 M1/MR1 预测或正式 ledger。

## 完成状态与下一步

已完成：真实历史 AH/OU 样本外预测；独立概率评分；Crown 历史快照小样本概率与 ROI 影子回放；V4 OU 原版评估；另一个开源方案审计；每四小时自动训练、指标比较、哈希追踪及报告留版；M3 探测脚本的 Crown-only 与安全日志修复。

未完成：前瞻 M3 原始预测与新 Crown 报价的同时采集、可持续的 M3 专属私有 quote store、长期 Crown OOS ROI 以及第三方候选 `goalmodel` 的真实独立 OOS 运行。其当前阻碍分别是既有授权范围缺少可追溯证据、专属私有持久化/密钥未配置、历史有效样本只有 24 AH/36 OU、尚未建立可复现 R 运行环境。没有扩大或缩小既定联赛范围。

最值得继续：在能核实既有授权和安全持久化后，开始 M3 专属前瞻配对；比较长期概率校准、跨季 Log Loss/Brier 和 Crown 同期 quote ROI，逐市场分别积累。此前不加 EV、置信度、数量、时效或联赛 Gate，不自动升版、不启用 Telegram。
