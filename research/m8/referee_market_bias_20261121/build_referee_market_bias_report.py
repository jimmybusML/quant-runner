# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Build complete M8 referee-history diagnostic report from saved results."""
import json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
S=json.loads((HERE/'referee_market_bias_summary.json').read_text())
V=json.loads((HERE/'referee_market_bias_independent_verification.json').read_text())
C=S['coverage']; M=S['models']; lines=[]
lines += ['# M8 裁判历史偏差与 Crown AH 定价增量研究','',f"执行时间（UTC）：{S['execution_utc']}",'','## 结论','',
'本研究检查了一个与 R48 球队纪律率不同的假说：**同一联赛中某裁判过去的 Crown AH 实际净胜球残差，能否预测他执法下一场时的 AH 超额收益。**按年份前推，裁判历史特征加入 Crown 线与归一化价格后，八组外候选较 Crown-only 基准少亏16.010U；但5,874笔八组外候选仍合计亏损−83.530U/−1.422%，2024、2025、2026三个测试年度都亏损。当前数据没有裁判字段的首次发布时间或当时收到快照，因此这只是历史机制线索，不是已证明赛前可用的盈利方法。','',
'本轮**没有发现正净U的新盈利来源**。合并八组后总账仍为正，来自冻结八组原有收益，不能抵消候选自己的亏损。没有修改冻结组、生产模型、派单、账本或采集流程。','',
'## 与既有研究的区别','',
'R48 已研究球队自身此前的黄牌、红牌率，并指出没有可核验的裁判赛前快照。本轮不再使用球队纪律率；新变量是**目标裁判的历史执法赛事中，主队实际进球差相对 Crown AH 线的偏差**，并按同一 Transfermarkt 竞赛内裁判历史与竞赛均值作对照。裁判当前场次姓名来自赛后归档，是否在开赛前已公布没有证据；所以它只能检验条件关联，不能证明实际可用信息。','',
'## 数据覆盖与核验','',
f"- 输入 M8 T12 Crown 原始事件库存：{C['source_Crown_T12_rows']:,}个FID。赛事/球队映射唯一后，{C['strict_fixture_join_and_raw_quote_validated']:,}场在{C['unique_competitions']}个竞赛代码内找到唯一 Transfermarkt 比赛及裁判记录；区间为2019-08-02至2026-07-06，共{C['unique_referees']}名标准化裁判。",
f"- 原始 T12 Crown JSON 的 SHA、FID、联赛、球队、开球时间、FT、T12 线/双方水位和五态 AH 结算，对{V['raw_response_hash_ft_identity_T12_and_AH_settlement_checked']:,}/{V['feature_rows']:,}行独立复核通过；逐场响应 SHA 保存在行账本。",
f"- 完整测试期有{V['test_unique_fids']:,}个唯一FID，其中与原八组交集{V['frozen_eight_overlap_fids']:,}场；八组外独立候选{V['outside_frozen_eight_unique_fids']:,}场。没有把原八组重叠重复计为增量。",
f"- 2024–2026各年可复算场次（全样本/八组外）：2024 {C['test_years']['2024']['all_joined']:,}/{C['test_years']['2024']['outside_frozen_eight']:,}；2025 {C['test_years']['2025']['all_joined']:,}/{C['test_years']['2025']['outside_frozen_eight']:,}；2026 {C['test_years']['2026']['all_joined']:,}/{C['test_years']['2026']['outside_frozen_eight']:,}。2026数据只到7月6日，不代表完整年度。",
f"- 冻结原八组同期比较基准为6,873场、+197.765U（2024–2026已保存T12研究基准）。裁判数据与 MR1 实收归档交集为{C['MR1_receipt_archive_fid_intersection']}场，具有可核验赛前裁判信息快照的场次为0。",
'- 映射缺失并未作为策略未命中：24,556行缺竞赛/球队交叉表，3,755行无法找到唯一赛事，4行没有裁判姓名；这些原因均保存在 summary 中。匹配赛事的 `appearances` 记录只有10,191/12,744至少出现一行，另2,553场缺记录，故球员牌数没有作为模型特征。该实验只覆盖原49联赛中已有的25个显式 Transfermarkt 竞赛映射，不代表新增15联赛研究。','',
'## 前推方法','',
'- 固定研究特征：目标裁判在同一竞赛过去730日内的 Crown AH 主队净胜球残差均值、裁判样本数；残差为 `主队进球−客队进球+主队让球线`。以过去同竞赛均值作中心化，并使用固定10场伪计数收缩。球队当场表现、目标FT、未来八组成员身份不作特征。',
'- 日期只有日级时，目标比赛当天及之前两天不进入历史特征。对2024/2025/2026分别以前一年及更早数据训练，固定岭惩罚100；目标年结果不参与该年训练或参数选择。预测目标为同一 Crown 合同下主队1U收益减客队1U收益，选预测收益差较高的一侧；每个有效FID均出一侧，不设EV或ROI筛选。',
'- Crown-only 使用盘口线、双方赔率归一化后的主队隐含份额及竞赛控制；Ref-only 使用裁判历史特征及竞赛控制；Crown+Ref 使用两者；Crown低水方是同样本简单市场方向控制。所有方案相同测试样本，彼此不相加。',
'- AH quarter-line 逐拆两腿、每场等额1U。历史 Crown event-time 报价与实收必须区分；本研究没有实收裁判快照，也没有可称为实盘的回测。','',
'## 八组外候选收益','',
'| 方法 | 新增单量 | 净U | ROI | 最大回撤U | 周均单量 | 正收益联赛/负收益联赛 |','|---|---:|---:|---:|---:|---:|---:|']
for m in ('Crown only','Ref only','Crown + referee','Crown lower-odds side'):
 q=M[m]['outside_frozen_eight'];by=M[m]['outside_by_league'];pos=sum(v['net_U']>0 for v in by.values());neg=sum(v['net_U']<0 for v in by.values())
 lines.append(f"| {m} | {q['n']:,} | {q['net_U']:+.3f} | {q['ROI_pct']:+.3f}% | {q['MDD_U']:.3f} | {q['avg_orders_per_calendar_week']:.3f} | {pos}/{neg} |")
lines += ['', '全部方法都对5,874个八组外唯一FID出单；每周数量只是历史匹配库存下的研究单量。完整25竞赛净U及ROI见 `referee_market_bias_by_league.csv`，全 ISO 周净U与订单见 `referee_market_bias_by_week.csv`。裁判特征从未筛选联赛或订单。','',
'## 按年度前推（八组外）','', '| 方法 | 年份 | 唯一订单 | 净U | ROI | MDD U | 周均单量 |','|---|---:|---:|---:|---:|---:|---:|']
for m in ('Crown only','Ref only','Crown + referee','Crown lower-odds side'):
 for y,q in M[m]['outside_annual'].items():lines.append(f"| {m} | {y} | {q['n']:,} | {q['net_U']:+.3f} | {q['ROI_pct']:+.3f}% | {q['MDD_U']:.3f} | {q['avg_orders_per_calendar_week']:.3f} |")
lines += ['', 'Crown+Ref 在三个年度均亏损：2024 −25.855U、2025 −31.115U、2026截至7月6日 −26.560U。市场模型相同样本为−99.540U；裁判信息让回放少亏16.010U，但没有抵消价格成本。Ref-only也持续亏损，不能把相对表现改善描述为正收益。','',
'## 原八组合并结果（单独列示候选亏损）','', '| 方法 | 原八组基准 | 候选八组外增量 | 唯一FID合计 | 合并净U | 合并ROI |','|---|---:|---:|---:|---:|---:|']
for m in ('Crown only','Ref only','Crown + referee','Crown lower-odds side'):
 q=M[m]['combined_with_frozen_eight_same_2024_2026'];lines.append(f"| {m} | {q['frozen_n']:,}/{q['frozen_net_U']:+.3f}U | {q['candidate_added_n']:,}/{q['candidate_added_net_U']:+.3f}U | {q['unique_total_n']:,} | {q['total_net_U']:+.3f}U | {q['ROI_pct']:+.3f}% |")
lines += ['', '冻结八组合并后仍有正净U的行来自冻结基准盈利；候选净U均为负。不可用合并后结果称裁判模型盈利。','',
'## 时间可信度、缺口与结论','',
'Transfermarkt `games.csv` 的 referee 姓名与赛果/出场数据是后续下载归档，没有裁判任命首次发布或实际接收时间。目标比赛所使用的裁判姓名虽来自比赛记录，但目前无法证明下注决策时已知。MR1 实收归档与测试FID交集为0，真实赛前信息回放为0；历史source-event报价也不是原样实收证明。球员出场数据在匹配裁判游戏中存在缺行，因此未把缺失出场或牌数当作零，也没有把球员牌数加入模型。','',
'当前证据表明：裁判过去相对 Crown AH 的比赛残差，在本数据映射样本中与盈利方向存在小幅前推增量，但收益仍为负，三个年度未盈利；裁判字段时序未经验证，新增15联赛没有本轮信号回测。还缺裁判任命历史首次公开/收到时间及同步 Crown 赛前收据，才能判断此关联是否是可操作的真实信息优势。现阶段不构成独立正收益来源。','',
'## 文件与独立复核','',
'- `run_referee_market_bias.py`：身份映射、原始 Crown T12 校验、时序历史特征构造与2024–26逐年扩展训练。',
'- `verify_referee_market_bias.py`：独立重读12,744条逐场Crown原响应，复算赛事身份、T12合同、AH逐腿结算、裁判730日特征、冻结FID交集及年度/合计收益。',
'- `referee_market_bias_fixture_features.jsonl.gz`：完整12,744场时序特征和原始SHA。',
'- `referee_market_bias_predictions.jsonl.gz`：30,096条方法×场次预测/方向/盘口/赔率/FT/五态结算/净U。',
'- `referee_market_bias_summary.json`、年度/联赛/周度明细、`EXECUTION_RECORD.json`、`SHA256SUMS.txt`。',
f"独立复核：`pass={str(V['pass']).lower()}`，issues={V['issues']}。研究回放订单不是Telegram派单；正式订单、正式账本回写及生产模型修改均为0。"]
(HERE/'REFEREE_MARKET_BIAS_RESEARCH_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
