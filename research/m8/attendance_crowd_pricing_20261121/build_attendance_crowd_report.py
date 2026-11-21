#!/usr/bin/env python3
"""Build the human-readable report and compact annual/weekly/league extracts."""
from __future__ import annotations
import csv, gzip, json
from pathlib import Path
OUT=Path(__file__).resolve().parent
summary=json.loads((OUT/'attendance_crowd_summary_20261121.json').read_text())
methods=summary['models']
labels={'market_only_ridge':'Crown-only baseline','attendance_only_ridge':'Attendance-only','crown_plus_attendance_ridge':'Crown + attendance'}
# Detailed annual and ISO-week output preserves every observed week and model.
with (OUT/'attendance_crowd_weekly_20261121.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator='\n'); w.writerow(['method','year','iso_week','orders','net_U'])
 for m,data in methods.items():
  for year,st in data['annual'].items():
   for week,v in st['weekly'].items(): w.writerow([m,year,week,v['n'],v['net_U']])
with (OUT/'attendance_crowd_league_20261121.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator='\n'); w.writerow(['method','league_id','orders','net_U','ROI_pct','MDD_U'])
 for m,data in methods.items():
  for league,st in sorted(data['league'].items()): w.writerow([m,league,st['n'],st['net_U'],st['ROI_pct'],st['MDD_U']])
lines=[]
lines += ['# M8 上一主场到场人数与 Crown AH 定价信息研究','',
'执行日：2026-11-21。状态：研究回放完成，结论为未发现新增盈利机制。所有原八组、M1/MR1/M9、生产派单、账本与采集链保持不变。', '',
'## 结论','',
'这项测试没有发现到场人数/主场观众信息能够在 Crown 亚洲让球价格之外增加净利润。三种方法在同一批 6,861 个八组外唯一 FID 上评估：Crown-only 基准为 −63.280U（ROI −0.922%）；attendance-only 为 −154.615U（−2.254%）；Crown+attendance 为 −210.915U（−3.074%）。后两种 crowd 模型在 2024、2025、2026 每一年都为负。候选与冻结八组无 FID 交集；但既然候选本身为负，不应将八组合并后仍为正误称为新增利润。', '',
'以原冻结八组 10,294 场、+236.015U、ROI +2.293% 为固定基准，按 2024–2026 同期样本去重合并后，Crown-only 总体 +134.485U，attendance-only +43.150U，Crown+attendance −13.150U。三种模型的候选都各自约增加 48.7 场/周（6,861 场 / 141 个观测年度周），但该数量仅为全量实验模型的回放单数，不是建议单量；新增候选净收益仍为负。', '',
'## 方法与时间边界','',
'- 使用已保存 Transfermarkt `games.csv.gz` 的球队此前主场比赛上座人数；每队需要至少 3 条有效历史主场观众记录，向前看 730 天，并排除目标日前 3 天内记录。特征包括最近 3 场对数平均观众、最近一次观众、365 天比赛数、最近 3 场球场重复率、双方差/和；完整计算变量见逐场 JSONL。目标比赛上座人数不作特征。',
'- 测试年度采用逐年扩展训练：2024 只用 2024 前数据训练，2025 使用 2025 前数据，2026 使用 2026 前数据。训练目标为 Crown T−12 AH 主队净结算收益减客队净结算收益。固定 Ridge α=100；无测试年阈值搜索。每个特征完整的测试样本选模型预测净收益更高的一方，只用于比较信息方向，不代表“不下注”生产建议。',
'- Crown-only 对照与两个 attendance 模型使用同一完整特征样本。AH 按原始皇冠盘口及赔率结算，四分之一盘拆为两腿。',
'- Transfermarkt 为事后批量快照，无逐行首发发布/接收时间。该文件没有证明观众信息在历史比赛的投注时点已可获得。因此即使模型是日期前推，仍只能称为按比赛日期构造的历史信息回放，不能称为严格前瞻信息验证。',
'- 2026 数据可用到 2026-11-04 的 Crown T−12 库存，但到场档案截至 2026-07-06。2026 完整特征样本的最近可用主场上座特征中位年龄：主队 27 天、客队 20 天；90 分位分别 168、169 天。',
'', '## 样本与覆盖审计','',
'- Transfermarkt 比赛行 88,958；其中 78,155 行有 attendance；源数据最大日期 2026-07-06。',
'- Crown T−12 库存行 41,059；41,059/41,059 均由原始 Crown 响应重新核对比赛ID、联赛ID、主客队、FT、报价源事件时间、盘口线及双方赔率。Crown 报价历史回取不是实际收件时点证明。',
'- 在八组外 2024–2026 目标池中 21,492 个 fixture；6,861 个有完整的双方 attendance 特征并进入三个模型。完整样本 0 个与冻结八组 FID 重叠。测试年度未映射/数据不足分别为 2024：4,410/721；2025：4,713/150；2026：4,566/71。其余样本保留在逐场 coverage 文件中，不被视作模型未命中。',
'- 身份映射范围为显式的 25 个 Transfermarkt competition 映射。968 个 Crown 球队键中 389 个通过唯一一对一名称匹配；未映射联赛 387、无名称匹配 175、歧义 3、非一对一剔除 14。匹配均值 0.965985、最小分数 0.91。此覆盖损失限制结论外推。',
'- M8/MR1 真实 Crown 收据档案共 1,607 个 FID，其中 1,206 个与 T−12 库存交集；attendance 可用档案未带比赛前的逐条时间戳，故真实收据条件下的 crowd 模型复算数为 0。没有用赛后 Transfermarkt 快照替代实时信息。',
'', '## 收益结果','',
'### 总体及年度表现','',
'| 模型 | 年份 | 唯一订单 | 净U | ROI | 最大回撤U | 观测周 |', '|---|---:|---:|---:|---:|---:|---:|']
for m,data in methods.items():
 for year,st in data['annual'].items(): lines.append(f"| {labels[m]} | {year} | {st['n']:,} | {st['net_U']:+.3f} | {st['ROI_pct']:+.3f}% | {st['MDD_U']:.3f} | {st['weekly_n']} |")
 st=data['all_test']; lines.append(f"| {labels[m]} | 合计 | {st['n']:,} | {st['net_U']:+.3f} | {st['ROI_pct']:+.3f}% | {st['MDD_U']:.3f} | {st['weekly_n']} |")
lines += ['', '订单周均量以有样本的库存周为分母：2024 为 53 周、2025 为 53 周、2026 为 45 周。每种方法相同，分别为 35.43、51.77、49.76 场/周。模型总体共有 133 个有单 ISO 周；完整逐周 U 与订单数见 `attendance_crowd_weekly_20261121.csv` 和 summary JSON。', '',
'### 八组同期合并','',
'| 模型 | 期间 | 候选新增单 | 候选净U | 合并唯一FID | 合并净U | 合并ROI | 合并MDD U |', '|---|---|---:|---:|---:|---:|---:|---:|']
for m,years in summary['merged_with_frozen'].items():
 for year,st in years.items(): lines.append(f"| {labels[m]} | {year} | {st['new_n']:,} | {st['new_net_U']:+.3f} | {st['merged_n']:,} | {st['merged_net_U']:+.3f} | {st['merged_ROI_pct']:+.3f}% | {st['merged_MDD_U']:.3f} |")
lines += ['', '冻结八组在 2024–2026 的唯一成员数为 6,873、净收益 +197.765U。合并表的 2024–2026 结果使用每个方法各自候选加冻结成员 FID 并集；候选亏损单独展示，不能靠基准盈利掩盖。', '', '### 联赛分布','',
'下表完整列出本实验 25 个可映射联赛ID的结果。联赛拆分为事后诊断，不用于按联赛挑选或定义交易条件。具体联赛身份映射见脚本中的 `COMPETITION_MAP`。','']
for m,data in methods.items():
 lines += [f'#### {labels[m]}','', '| 联赛ID | 唯一订单 | 净U | ROI | MDD U |','|---:|---:|---:|---:|---:|']
 for league,st in sorted(data['league'].items(),key=lambda kv:int(kv[0])): lines.append(f"| {league} | {st['n']:,} | {st['net_U']:+.3f} | {st['ROI_pct']:+.3f}% | {st['MDD_U']:.3f} |")
 lines.append('')
lines += ['## 结算和独立验证','',
'逐场模型预测、方向、原始 Crown T−12 线/赔率、FT、两边正确 AH 收益及五态结果保存在 `attendance_crowd_per_fixture_20261121.jsonl.gz`；每个模型的试算单保存在 `attendance_crowd_orders_20261121.jsonl.gz`。原始 Crown 响应 SHA 随每场记录保存。',
'独立核验脚本重新读取逐场记录引用的原始 Crown 响应、重新解析报价时间、T−12 盘口和 FT，并独立拆算四分之一盘：41,059/41,059 合约和赛果核验通过；三个模型各 6,861 单，逐笔账本净U与摘要一致；冻结FID交集 0；错误 0。详细结果在 `attendance_crowd_independent_verification_20261121.json`。', '',
'本回放是研究模拟，不是正式实战或 Telegram 订单，也不是实际 HTTP 收件时点回放。', '',
'## 交付文件','',
'- `run_attendance_crowd_research.py`：主实验与 Crown 原始盘口/FT/特征构造。',
'- `verify_attendance_crowd_research.py`：独立原始报价、身份、赛果及 AH 收益复核。',
'- `build_attendance_crowd_report.py`：生成本报告及周/联赛 CSV。',
'- `attendance_crowd_summary_20261121.json`：年度、周度、联赛、收据和合并结果。',
'- `attendance_crowd_per_fixture_20261121.jsonl.gz`、`attendance_crowd_orders_20261121.jsonl.gz`：逐场证据与试算账本。',
'- `attendance_crowd_coverage_20261121.json`：从逐场记录汇总的覆盖状态。',
'- `attendance_crowd_execution_20261121.json`、`attendance_crowd_sha256_20261121.txt`：执行和哈希清单。', '',
'## 研究判断','',
'历史数据不支持“主场观众到场/氛围能补充 Crown AH 并产生新增盈利”这一机制：attendance-only 与加入 Crown 后表现都比同样本 Crown-only 更差，且三个测试年度候选均亏损。Crown+attendance 候选为 −210.915U，实际削减冻结八组合计盈利，合并后 2024–2026 为 −13.150U。市场模型自身在该样本也亏损 −63.280U，故不能把这一组结果单独解释为attendance变量因果性地造成损失；但当前实验没有任何正收益证据。',
'若未来重启这一假说，必要的新证据是带有可信赛前发布时间的逐场 attendance/售票/场馆容量快照及更可靠的广泛球队身份映射；没有该类时间证据，就不能声称这是可交易的独立赛前信息。以上仅是研究缺口，不是采集部署请求或生产条件。']
(OUT/'ATTENDANCE_CROWD_PRICING_RESEARCH_20261121.md').write_text('\n'.join(lines)+'\n')
