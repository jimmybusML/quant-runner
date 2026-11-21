# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Build F-group mechanism report and full comparator time-series extracts."""
import csv,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[4]
S=json.loads((HERE/'f_group_market_mechanism_summary.json').read_text())
P=json.loads((ROOT/'research/m8_m9_group_independent_20261120/exact_rule_cross_league/exact_rule_cross_league_summary.json').read_text())
rows=[json.loads(x) for x in __import__('gzip').open(HERE/'f_group_market_mechanism_rows.jsonl.gz','rt',encoding='utf-8')]
labels={'F_selected':'F冻结方向','T1_favorite':'T1低水方','T1_underdog':'T1高水方','opposite_F':'F方向反选'}
with (HERE/'f_group_comparisons_weekly.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['comparison','iso_week','n','net_U'])
 for k,key in [('F_selected','selected_net_U'),('T1_favorite','T1_favorite_side_net_U'),('T1_underdog','T1_underdog_side_net_U'),('opposite_F','opposite_side_net_U_same_T1_quote')]:
  v={}
  for r in rows:
   week=r['iso_week'];q=v.setdefault(week,[0,0.]);q[0]+=1;q[1]+=r[key]
  for week,q in sorted(v.items()):w.writerow([k,week,q[0],round(q[1],6)])
with (HERE/'f_group_comparisons_monthly.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['comparison','month','n','net_U'])
 for k,key in [('F_selected','selected_net_U'),('T1_favorite','T1_favorite_side_net_U'),('T1_underdog','T1_underdog_side_net_U'),('opposite_F','opposite_side_net_U_same_T1_quote')]:
  v={}
  for r in rows:
   month=r['kickoff_beijing'][:7];q=v.setdefault(month,[0,0.]);q[0]+=1;q[1]+=r[key]
  for month,q in sorted(v.items()):w.writerow([k,month,q[0],round(q[1],6)])
lines=['# M8 冻结 F 组跨联赛报价方向机制复核','',f"执行时间（UTC）：{S['execution_utc']}",'','## 结论','',
'本研究固定使用冻结原规则已经分派给 F 组的109个原49联赛之外唯一FID；没有重新挑选比赛、调阈值或改方向。结果显示一个值得保留的解释性线索：AH盘口在T6/T3/T1三个样本时点均为0，T6到T3的规范化主胜隐含概率不变、T3到T1发生单向变化时，冻结F方向在这109个历史样本中+12.180U/+11.174% ROI。相同FID如果改为T1低水方，合计−4.430U；改为相反的F方向，−16.290U。',
'这不是新的独立模型，也不是前瞻/实收证据：它逐场沿用原八组F组规则，历史跨联赛候选在设计前提下有目的地受原规则选择；市场路径中的同时间段反复波动也很常见。不能将此结果称作新第九组或正式盈利机制。', '',
'## F冻结方向如何作用','',
'在T6、T3、T1按原定义各取开赛前最新Crown AH报价，F规则先要求三点采样盘口均为平手（0），T6→T3主队规范化隐含份额不变，T3→T1发生变化且端点变化方向一致。原规则中的比例 `away_decimal_odds / (home_decimal_odds + away_decimal_odds)` 数学上等于按双方倒数赔率归一化的主队隐含概率。若该主队概率上涨，F选择主队；下降则选择客队。该章节是在解释原冻结逻辑，不创建新条件。',
'完整 raw `asian_list` 重建发现：109个FID的T6/T3/T1事件时间、样本盘口线与T1双方赔率重建均通过；全路径T6至T1中位数有6次隐含概率变动，87/109条完整报价路径在端点间出现过上涨和下跌；3/109曾有盘线变动但在固定三个采样点仍为平手。这表示“端点方向”不等于持续单边价格运动，且很依赖报价观察时点。',
'## 同FID基准对照','',
'| 固定同场方法 | 场次 | 净U | ROI | MDD U | 全赢 | 走水 | 全输 |', '|---|---:|---:|---:|---:|---:|---:|---:|']
for name,key in [('F冻结方向','cohort'),('T1低水方','T1_market_favorite_same_fids'),('T1高水方','T1_market_underdog_same_fids'),('F方向反选','opposite_of_frozen_F_side_same_fids')]:
 st=S['cohort'] if key=='cohort' else S['fixed_cohort_comparators'][key]
 sett=st['settlement'];lines.append(f"| {name} | {st['n']} | {st['net_U']:+.3f} | {st['ROI_pct']:+.3f}% | {st['MDD_U']:.3f} | {sett.get('full_win',0)} | {sett.get('push',0)} | {sett.get('full_loss',0)} |")
lines += ['', 'F方向109场结算为46全赢、32走水、31全输。冻结F方向中59场与T1低水方相同（+4.510U），50场反着T1低水方向、即T1高水方（+7.670U）。对照组是同一FID上的事后反事实核算，不用于训练、过滤或上线条件。F方向较同场T1低水方多+16.610U；较相反方向多+28.470U。', '', '## 年度与周度表现','', '| 年份 | 扩展赛程观测周 | F单量 | 周均单量 | F净U | F ROI | T1低水方净U | T1高水方净U | F反向净U |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for y,z in S['annual_comparators'].items():
 weeks=P['results']['new_incremental_by_year'][y]['observed_schedule_weeks'];f=z['F_selected']
 lines.append(f"| {y} | {weeks} | {f['n']} | {f['n']/weeks:.3f} | {f['net_U']:+.3f} | {f['ROI_pct']:+.3f}% | {z['T1_favorite']['net_U']:+.3f} | {z['T1_underdog']['net_U']:+.3f} | {z['opposite_F']['net_U']:+.3f} |")
lines += ['',"全期按扩展赛程387周计算，109笔相当于每周0.282笔；F的盈利周35、亏损周26、其他周为走水/净零。2024/25共81笔、+5.830U（两年各自都正），2026截至6月1日只有2笔、−0.160U；因此没有足够2026样本判断能否延续。全部逐周/逐月结果及同场对照在 `f_group_comparisons_weekly.csv`、`f_group_comparisons_monthly.csv` 和 summary JSON。", '', '## 完整区间路径的事后分层诊断','', '本节只按已知完整报价路径是否在T6至T1间同时发生涨、跌拆分这109场，属于固定样本事后描述，不是预测条件，也没有用于选择或排除订单。87场路径曾双向波动，合计+11.060U（ROI +12.713%）；其余22场合计+1.120U（ROI +5.091%）。双向波动组的年度结果为2019 +0.940U/4、2020 −1.100U/3、2021 +0.960U/2、2022 +0.020U/3、2023 +4.840U/13、2024 +2.100U/32、2025 +3.300U/30；非双向波动组2023 +0.850U/1、2024 +0.760U/5、2025 −0.330U/14、2026 −0.160U/2。此拆分依赖整个赛前报价区间的路径，不能在T1时作为已知特征，也未显示稳定的机制边界。', '', '## 联赛拆分','', '| 联赛 | F场次 | 净U | ROI |','|---|---:|---:|---:|']
for league,st in S['league'].items():lines.append(f"| {league} | {st['n']} | {st['net_U']:+.3f} | {st['ROI_pct']:+.3f}% |")
lines += ['', '6个联赛为正收益，3个为负，1个为零。正收益主要有 Brazil Serie A +3.630U/21、USA MLS +3.070U/36、Egypt +2.590U/14、Argentina +1.610U/17；Bosnia +1.640U只有2场。International Match −0.060U/2、Albania −0.160U/2、UEFA Nations League B −1.000U/1，均稀疏。联赛分布为描述性，不形成联赛过滤。', '', '## 原八组去重及组合影响','',
'冻结八组10,294个FID与这109场交集0。把109笔F组扩展回放单独并入冻结八组，则10,403个唯一FID、+248.195U；组合ROI为2.386%（按原报告冻结基准收益+236.015U计算）。这只是对历史基准的算术并集，不是正式生产账本/实收表现。F属于原八组冻结规则的跨联赛迁移，而不是独立于F的新机制。', '',
'## 数据时点及风险','',
'报价是经SHA核对的Crown原始历史响应中的 `asian_list` source-event，真实HTTP收到时间为历史响应回取时间；109场真实赛前Crown receipt验证数为0，不能称为可执行实收。完整样本先于同一场FT逐场结算，四分之一盘结算程序独立拆腿；F样本AH线均为0，结算由T1双方赔率支付或走水。',
'仅2024/25两个样本年度连续为正，2026只有2单，且周内路径在大多数比赛发生过方向反复。正差比较可能是原F规则及多次既有研究选择的结果，不是对全池预注册验证；不能把这些比较升级成交易条件。无正式Telegram派单、正式账本回写、生产规则修改或采集链变更。', '', '## 可复现交付','',
'- `audit_f_market_mechanism.py`：在固定F组已分派的109个FID上重建 raw Crown T6/T3/T1、完整区间报价路径、五态结算及固定同FID对照。',
'- `verify_f_market_mechanism.py`：独立读源订单、重新载入逐场原始Crown响应，复核SHA、赛事身份、FT、报价时点、冻结方向和结算。',
'- `f_group_market_mechanism_rows.jsonl.gz`：109场原始时点报价、两侧收益、样本内完整路径诊断及响应SHA。',
'- `f_group_market_mechanism_summary.json`：年度、联赛、ISO周、月份和反事实比较。',
'- `f_group_market_mechanism_independent_verification.json`：独立核验结果。',
'- `SHA256SUMS.txt` / `EXECUTION_RECORD.json`：输入和输出哈希、执行记录。', '',
'## 研究判断','',
'这一结果提出一个值得继续观察的解释：平手盘合约不动时，T3→T1的归一化价格重新分配可能含有比“最终低水方”更多的方向信息；此固定样本里候选侧累计胜过最终低水方。但这是对冻结F组机制的事后解释，且实际赛事间价格路径经常反复。是否能成为可新增盈利来源仍缺少真正赛前HTTP收据以及全64联赛/未参与模型设计的持出FID复算。当前证据不足以新增规则、筛选条件或宣称稳定可部署利润。']
(HERE/'F_GROUP_MARKET_MECHANISM_REPORT.md').write_text('\n'.join(lines)+'\n')
