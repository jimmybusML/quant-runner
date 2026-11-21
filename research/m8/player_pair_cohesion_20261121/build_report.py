#!/usr/bin/env python3
"""Render complete report from locked pair-cohesion replay outputs."""
import json,pathlib
OUT=pathlib.Path(__file__).resolve().parent
s=json.loads((OUT/'pair_cohesion_summary_20261121.json').read_text())
v=json.loads((OUT/'independent_verification_20261121.json').read_text())
labels={'market_only':'Crown市场基线','pair_only':'配对共现单独模型','market_plus_pair':'Crown + 配对共现'}
def table_results():
 lines=['| 方案 | 八组外FID | 净U | ROI | MDD U | 周均单量 | 同期原八组+候选（FID / 净U / ROI） |','|---|---:|---:|---:|---:|---:|---:|']
 for m,n in labels.items():
  x=s['models'][m]['incremental_outside_frozen'];z=s['models'][m]['frozen_plus_candidate_same_period']
  lines.append(f"| {n} | {x['n']:,} | {x['net_U']:+.3f} | {x['ROI_pct']:+.3f}% | {x['MDD_U']:.3f} | {x['orders_per_week']:.3f} | {z['n']:,} / {z['net_U']:+.3f} / {z['ROI_pct']:.3f}% |")
 return '\n'.join(lines)
def table_annual():
 lines=['| 方案 | 年份 | 新增FID | 净U | ROI | MDD U | 周均单量 |','|---|---:|---:|---:|---:|---:|---:|']
 for m,n in labels.items():
  for y,x in s['annual_incremental'][m].items():lines.append(f"| {n} | {y} | {x['n']:,} | {x['net_U']:+.3f} | {x['ROI_pct']:+.3f}% | {x['MDD_U']:.3f} | {x['orders_per_week']:.3f} |")
 return '\n'.join(lines)
def table_leagues():
 ids=sorted(s['league_incremental']['market_only'],key=int)
 lines=['| 联赛ID | 单量 | Crown基线净U | 配对单独净U | Crown+配对净U |','|---:|---:|---:|---:|---:|']
 for lid in ids:
  q=[s['league_incremental'][m][lid] for m in labels]
  lines.append(f"| {lid} | {q[0]['n']} | {q[0]['net_U']:+.3f} | {q[1]['net_U']:+.3f} | {q[2]['net_U']:+.3f} |")
 return '\n'.join(lines)
def table_receipts():
 lines=['| 方案 | 实收价回放八组外FID | 净U | ROI | MDD U | ISO周（单量/净U） |','|---|---:|---:|---:|---:|---|']
 for m,n in labels.items():
  x=s['actual_receipt_replay']['models'][m]['incremental_outside_frozen']
  w=s['actual_receipt_replay']['weekly_incremental'][m]
  weeks='；'.join(f"{k} {r['n']}/{r['net_U']:+.3f}" for k,r in w.items())
  lines.append(f"| {n} | {x['n']} | {x['net_U']:+.3f} | {x['ROI_pct']:+.3f}% | {x['MDD_U']:.3f} | {weeks} |")
 return '\n'.join(lines)
text=f'''# M8 球员对子历史共用经验 × Crown AH 研究

研究性质：历史事件时点回放与真实 Crown 报价复算；不改变冻结原八组或生产。

## 结论

**没有找到新的正净利润订单来源。**配对共现单独模型在八组外4,383个FID上亏损90.880U（ROI −2.073%）；Crown+配对共现亏损153.770U（−3.508%）。配对模型相较同FID Crown基线少亏30.960U，但候选自身仍亏；三个方案覆盖完全相同的候选FID，不能将模型单量相加。

2024、2025、2026三年配对模型都为负。实收Crown报价回放中，122个八组外FID的配对模型也亏损5.815U。另有一个信息时序限制：真实收据目标日期 {s['actual_receipt_replay']['feature_target_date_range'][0]} 至 {s['actual_receipt_replay']['feature_target_date_range'][1]}，可用阵容档案截至 {s['actual_receipt_replay']['formation_archive_latest_date']}；配对历史最新记录距离目标日 {s['actual_receipt_replay']['feature_age_days']['min']}–{s['actual_receipt_replay']['feature_age_days']['max']}天，中位数{s['actual_receipt_replay']['feature_age_days']['median']:.0f}天。阵容记录没有首次发布日期或接收时间，故不能把实际收据价复算称为当时可得的信息优势验证。

## 与既有研究的区别

R50 的前序阵容实验度量相邻两场首发名单中的单人重合和上场间隔；R34测了赛程间隔；球员负荷研究覆盖分钟、首发重合与轮换。本研究的机制是球队过去365日的**球员对子共同首发网络**：成对首发反复次数、重复共现暴露、配对频率熵/集中度，以及最近五套已完成首发中两人组合的既往共用经验。每队输入只来自目标比赛日期前三天之前的已完赛历史完整首发；目标场首发完全未使用。它是对“稳定核心的熟悉组合是否降低执行误差、或频繁拆组是否被AH定价遗漏”的直接检验，不等同于目标首发连续性。

## 数据和方法

- 输入采用已有 Crown T12 AH/FT库存、Transfermarkt `games.csv.gz`、`game_lineups.csv.gz`、`appearances.csv.gz`，具体SHA见`SHA256SUMS_20261121.txt`。Crown原49联赛/新增15联赛的既有源不重采集。
- 41,059个T12候选FID中，10,710个完成双方配对历史特征；2024–2026测试5,502场，含冻结组重叠1,119场；八组外唯一新增4,383场。缺失：联赛/队伍身份映射23,993场；至少一队不足3个有效历史首发6,356场。此类数据缺口不作策略未命中。
- 历史完整性要求：每支队伍—比赛恰有11名不同首发，并且每名首发有同场正分钟appearance；不把缺失名单当作0或“不熟”。共映射33,987场源比赛，验证有效队伍—比赛首发55,371条；4,827条不完整首发和7,776个首发分钟校验失败均被排除（原因类别可能重叠）。
- 固定扩展前推：2024用2019–2023训练，2025用2019–2024，2026用2019–2025；固定Ridge alpha=100、fold内标准化和训练残差标准差。AH方向按模型预测净胜球对应的Crown两侧实际报价期望结算收益较高侧选择；不设EV弃投门槛、不搜参数。
- 所有方法使用同一测试FID；quarter-line 拆成两个相邻半球合约各半注，按Crown双边水位与FT正确结算。MDD按比赛日期合计净U后计算。

## 八组外收益

{table_results()}

### 分年度

{table_annual()}

全测试期从首末合格比赛日期计{round(s['models']['pair_only']['incremental_outside_frozen']['n']/s['models']['pair_only']['incremental_outside_frozen']['orders_per_week'])}个完整日历周。各模型订单均是同一比赛集合的不同方向，独立分析，不作并集加总。

## 联赛拆分

以下展示完整覆盖联赛ID全集，保留所有正负值；不是可据此挑选联赛的策略建议。

{table_leagues()}

ISO周及年×联赛完整明细保存在`pair_cohesion_summary_20261121.json`。

## 原八组合并

`frozen_plus_candidate_same_period` 使用与测试候选首末日期相同窗口内的冻结成员，并对FID去重；`full_frozen_plus_candidate` 作为全部原冻结账本并入本次新增候选的另一口径。无论并集总收益如何，候选独立净U如上表，不能以原八组利润掩盖新候选亏损。冻结成员文件和SHA不变。

## 实收 Crown 报价复核

从既有MR1实收归档选择符合条件且落入2026测试特征队列的收据：157个唯一FID、每模型一行共471条；其中122场位于冻结八组外。只使用实收HTTP报价线和双方赔率结算，不用事件回取报价替代。实际新增结果：

{table_receipts()}

配对历史的时间差说明实收价复放不能证明特征当时可知；并且这些赛果已进入先前研究，不是新的前瞻盲测、正式订单或Telegram实战。

## 独立核验

独立脚本`verify_player_pair_cohesion.py`从原始 Crown HTTP历史响应重新读取全部{v['historical_raw_Crown_contracts_matched']:,}个测试FID的赛事/联赛/球队、FT和T12 AH报价；重新计算{v['historical_rows_verified']:,}行模型结算。对{v['actual_receipt_unique_FIDs']}个收据FID读取原始HTTP envelope及snapshot并核对SHA、Crown身份、线水和收件早于开赛；其FT另由上述历史Crown原始响应独立校验。核验`pass={v['pass']}`，问题数为{len(v['issues'])}。

实收源事件时间、HTTP实际接收时间与比赛时间保存在逐场ledger及`actual_receipt_raw_audit_20261121.jsonl.gz`；历史事件源报价并不表示当时接收或可成交。

## 完整交付与边界

- `run_player_pair_cohesion.py`：复跑历史特征和时间前推AH实验。
- `verify_player_pair_cohesion.py`：独立原始Crown/FT/HTTP收据与亚洲盘结算核验。
- `pair_cohesion_per_fixture_20261121.jsonl.gz`：3个模型的完整FID、特征、方向与结算。
- `pair_cohesion_market_plus_pair_ledger_20261121.jsonl.gz`：联合模型逐场账本。
- `pair_cohesion_actual_receipt_replay_20261121.jsonl.gz`：真实赛前报价分开复算。
- `pair_cohesion_summary_20261121.json`：年度、周、联赛、重叠、合并、收据与覆盖结果。
- `historical_crown_raw_audit_20261121.jsonl.gz`、`actual_receipt_raw_audit_20261121.jsonl.gz`：原始逐FID来源与SHA证据。
- `EXECUTION_RECORD_20261121.md`、`SHA256SUMS_20261121.txt`：实际执行及输入输出审计。

没有生产派单、正式账本写入、采集链改动或正式规则变更。
'''
(OUT/'M8_PLAYER_PAIR_COHESION_RESEARCH_20261121.md').write_text(text,encoding='utf8')
