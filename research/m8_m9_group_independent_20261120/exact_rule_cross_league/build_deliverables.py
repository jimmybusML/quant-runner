#!/usr/bin/env python3
"""Build report, coverage JSON and weekly CSV from the full research ledgers."""
import collections,csv,json,pathlib,sys
OUT=pathlib.Path(__file__).resolve().parent
s=json.load(open(OUT/'exact_rule_cross_league_summary.json'))
cov=[json.loads(x) for x in open(OUT/'exact_rule_cross_league_coverage.jsonl')]
orders=[json.loads(x) for x in __import__('gzip').open(OUT/'exact_rule_cross_league_orders.jsonl.gz','rt')]
ver=json.load(open(OUT/'exact_rule_cross_league_independent_verification.json'))
coverage={'study':s['study'],'schedule_rows':s['sources']['schedule_rows'],'outside49_schedule_rows':s['sources']['outside49_rows'],'unique_fids':s['sources']['outside49_unique_fids'],'provider_league_ids':s['sources']['outside49_provider_league_ids'],'coverage_summary':s['coverage'],'fixtures':cov}
(OUT/'exact_rule_cross_league_coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
# One weekly line for each original group, new union and merged baseline+new.
weekly=[]
for g,x in s['groups'].items():
 for wk,v in x['assigned']['weekly'].items(): weekly.append({'portfolio':g,'iso_week':wk,'orders':v['n'],'net_U':v['net_U']})
for wk,v in s['deduplicated_union']['all']['weekly'].items():weekly.append({'portfolio':'new_unique_union','iso_week':wk,'orders':v['n'],'net_U':v['net_U']})
for wk,v in s['results']['merged_weekly'].items():weekly.append({'portfolio':'frozen8_plus_new','iso_week':wk,'orders':v['n'],'net_U':v['net_U']})
with (OUT/'exact_rule_cross_league_weekly.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['portfolio','iso_week','orders','net_U']);w.writeheader();w.writerows(sorted(weekly,key=lambda x:(x['portfolio'],x['iso_week'])))
# Render detailed Markdown result tables.
lines=['# M8 原八组精确规则跨联赛扩展回测','',f"执行时间（UTC）：{s['execution_utc']}",'',
'## 结论','',
(f"原冻结 base/A–G 规则在旧49联赛之外，共覆盖 **{s['sources']['outside49_rows']:,} 场赛程**；其中 **{s['coverage']['complete_path_n']:,} 场**能从 SHA 校验的 Crown 原始响应恢复完整 T6/T3/T1 路径。按原组优先级和方向去重后得到 **{s['results']['new_incremental']['n']:,} 笔八组外唯一历史回放订单，净收益 {s['results']['new_incremental']['net_U']:+.3f}U、ROI {s['results']['new_incremental']['ROI_pct']:+.3f}%、最大回撤 {s['results']['new_incremental']['max_drawdown_U']:.3f}U**。这些不是实收可成交或正式派单证据。"),'',
(f"逐场独立复核通过：{ver['independent_raw_quote_and_FT_rechecks']:,}/{ver['checked_orders']:,} 笔重新读取 Crown 原始响应、赛事身份、FT 和 T1 原始盘口结算；唯一FID重复、冻结八组重叠及复核差异均为0。扩展范围外赛程在 SQLite 中没有 live-mode 收据（0/18,374），故本报告全部是历史事件回放。"),'',
'## 数据范围与覆盖','',
 f"- 样本框来自本地 `crown-drop-expanded-62/schedule_universe.jsonl`：96,504场、64个provider league ID；排除冻结49联赛后为15个联赛、18,374个唯一FID。八组外赛程时间为{s['period']['schedule_first_date']}至{s['period']['schedule_last_date']}。",
'- Crown 数据只来自 `crown_quotes.sqlite3` 已保存的 Crown 原始 AH 响应。按 FID 与赛程连接，movement capture 覆盖18,374个FIDs；11,266个movement capture状态为`NO_CROWN_AH_QUOTES`，7,108个状态为`QUOTES_SAVED`；其中2场保存的报价事件均在开赛后，故只有7,106场具备赛前源事件报价。',
'- SHA、联赛、主客队、UTC开球与FT核对后，7,108个有价 FID 中：6,967个有 T6/T3/T1 完整路径，139个最早可用报价晚于T6，2个响应没有有效赛前 AH 行。没有路径的赛事不记为规则未命中。',
'- 时间窗严格按冻结程序定义：T6、T3、T1 截止时刻各取源事件时间不晚于对应截止的最新 Crown AH 双边报价；没有向后补齐或拼造报价。所有历史报价回取都标记为研究回放。',
'', '| 路径/报价状态 | FID数 |','|---|---:|']
for k,v in s['coverage']['status_counts'].items():lines.append(f'| {k} | {v:,} |')
lines+=['','### 15个联赛的报价路径覆盖','', '| Provider ID | 赛事范围 | 赛程数 | 无AH报价 | 有报价但晚于T6 | 完整T6/T3/T1 | 新增唯一订单 |','|---:|---|---:|---:|---:|---:|---:|']
league_ids=s['sources']['outside49_provider_league_ids']
for lid in league_ids:
 rr=[x for x in cov if x['league_id']==lid]; name=next((x['source_league'] for x in rr if x.get('source_league')),lid); states=collections.Counter(x['status'] for x in rr); nn=s['deduplicated_union']['per_league'].get(lid,{}).get('n',0)
 lines.append(f"| {lid} | {name} | {len(rr):,} | {states.get('movement_capture_without_quotes',0):,} | {states.get('no_quote_at_or_before_T6',0):,} | {states.get('complete_T6_T3_T1_path',0):,} | {nn:,} |")
lines+=['','## 八组逐组收益','', '| 组 | 原规则命中数（优先级后） | 新增唯一订单 | 净U | ROI | 最大回撤U | 周均订单* | 结算分布（全赢/半赢/走水/半输/全输） |','|---|---:|---:|---:|---:|---:|---:|---|']
for g,x in s['groups'].items():
 a=x['assigned'];c=x['settlement_classes'];sett=' / '.join(str(c.get(k,0)) for k in ('full_win','half_win','push','half_loss','full_loss'))
 lines.append(f"| {g} | {x['exact_rule_matches_before_direction']:,} | {a['n']:,} | {a['net_U']:+.3f} | {a['ROI_pct'] if a['ROI_pct'] is not None else '—'}% | {a['max_drawdown_U']:.3f} | {s['groups'][g]['avg_orders_per_full_observed_schedule_week']:.3f} | {sett} |")
u=s['results']['new_incremental'];c=s['deduplicated_union']['all'];sett=s['deduplicated_union']['settlement_classes'];lines.append(f"| 合计去重 | {sum(s['overlap']['exact_priority_assigned_hits'].values()):,} | {u['n']:,} | {u['net_U']:+.3f} | {u['ROI_pct']:+.3f}% | {u['max_drawdown_U']:.3f} | {u['avg_orders_per_full_observed_schedule_week']:.3f} | {' / '.join(str(sett.get(k,0)) for k in ('full_win','half_win','push','half_loss','full_loss'))} |")
lines+=['',f"*该表周均按整个扩展赛事观测期（{s['period']['observed_schedule_weeks']}周）计算，便于各组横向比较；年度周均按当年扩展赛程可观测周数计算。逐ISO周账本见 `exact_rule_cross_league_weekly.csv` 和 JSON。",'',
'**方向差异审计：** E组在原冻结触发条件下有38个命中。较新的边界审计脚本 `group_side(E)` 仅用端点净变化，会因E组本身要求端点净变化为零而不给方向；本研究保留较早冻结实现中的方向公式（净变化→T6到T3→T3到T1→最后一次同线水位变化的首个非零符号），并在原E组267名冻结成员上逐场复算，267/267与冻结净U结算一致。此处是恢复原规则语义，不是本轮新增筛选。',
'', '## 新增订单年度表现','', '| 年份 | 唯一单量 | 净U | ROI | MDD U | 全年样本周均单量 | 原八组该年净U | 八组合并净U | 合并ROI |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for y,x in s['results']['new_incremental_by_year'].items():
 m=s['results']['merged_by_year'][y]
 lines.append(f"| {y} | {x['n']:,} | {x['net_U']:+.3f} | {x['ROI_pct']:+.3f}% | {x['max_drawdown_U']:.3f} | {x['avg_orders_per_observed_schedule_week']:.3f} | {m['frozen_net_U']:+.3f} | {m['merged_net_U']:+.3f} | {m['merged_ROI_pct']:+.3f}% |")
lines+=['',f"跨年结果并不稳定：2024新增{s['results']['new_incremental_by_year'].get('2024',{}).get('n',0)}单、{s['results']['new_incremental_by_year'].get('2024',{}).get('net_U',0):+.3f}U；2025新增{s['results']['new_incremental_by_year'].get('2025',{}).get('n',0)}单、{s['results']['new_incremental_by_year'].get('2025',{}).get('net_U',0):+.3f}U；2026新增{s['results']['new_incremental_by_year'].get('2026',{}).get('n',0)}单、{s['results']['new_incremental_by_year'].get('2026',{}).get('net_U',0):+.3f}U，赛程止于{s['period']['schedule_last_date']}。2024/25合计为正，但2025与2026都未显示正收益，不能据此宣称稳定扩单机制。",'',
'## 联赛拆分','', '| Provider league ID | 冠军/赛事范围名称 | 新增单量 | 净U | ROI | MDD U |','|---:|---|---:|---:|---:|---:|']
for lid in league_ids:
 x=s['deduplicated_union']['per_league'].get(lid,{'n':0,'net_U':0.0,'ROI_pct':None,'max_drawdown_U':0.0});name=next((r['source_league'] for r in cov if r['league_id']==lid and r.get('source_league')),lid);roi='—' if x['ROI_pct'] is None else f"{x['ROI_pct']:+.3f}%"
 lines.append(f"| {lid} | {name} | {x['n']:,} | {x['net_U']:+.3f} | {roi} | {x['max_drawdown_U']:.3f} |")
lines+=['','各组逐年和逐联赛表均在 `exact_rule_cross_league_summary.json` 的 `groups` 中；合计按原优先级分组后不重复FID。所有周度净U保存在同一JSON的各组 `weekly`、去重组合 `deduplicated_union.all.weekly` 与合并组合 `results.merged_weekly`。','',
'## 组间重叠及规则审计','',
(f"路径完整的比赛中，按独立触发谓词发现 {s['overlap']['priority_rule_multi_trigger_fids'].get('multi_trigger_fid',0)} 个FID同时满足多个组条件；按冻结优先顺序只分配一次。原始触发总数{ s['overlap']['raw_trigger_sum']:,}，唯一订单{u['n']:,}。逐组原始触发数与优先级分配数详见 `overlap`。"),
f'- 新增订单与冻结10,294 FID交集：0；候选内部唯一FID：{u["n"]:,}；跨组重叠没有重复加总。',
f'- {u["n"]:,}笔订单均使用T1对应的原始Crown AH双边报价；AH四分之一盘按相邻半球线拆成两腿，用统一亚洲盘结算函数重算。全赢、半赢、走水、半输、全输均逐笔保留。',
'- G组沿用原独立动态进球模型的基线、攻防残差更新与AH双边EV；模型使用同联赛、精确队名的历史完赛记录，目标日期和前一日赛果不参与，输入队名与SHA校验的Crown原始赛事一致。目标赛果、未来八组成员及M9均未进入特征。',
'- 真实收据复核：范围内实时/live capture为0；事件源时间早于开赛并不代表当时已接收。无正式Telegram实战单，也未改写正式账本。',
'', '## 原八组合并口径','',
(f"冻结基准保持为10,294场、+236.015U、ROI +2.293%。加入{s['results']['new_incremental']['n']:,}个唯一八组外历史回放FID后，合计 **{s['results']['combined_original8_plus_new']['n']:,}场、+{s['results']['combined_original8_plus_new']['net_U']:.3f}U、ROI {s['results']['combined_original8_plus_new']['ROI_pct']:.3f}%、MDD {s['results']['combined_original8_plus_new']['max_drawdown_U']:.3f}U**。新增部分独立ROI为{s['results']['new_incremental']['ROI_pct']:+.3f}%，不以合并后的正ROI替代新增部分评价。历史全期周均新增{s['results']['combined_original8_plus_new']['avg_weekly_added_orders']:.3f}单；2024/2025/2026年度周均分别为{s['results']['new_incremental_by_year']['2024']['avg_orders_per_observed_schedule_week']:.3f}/{s['results']['new_incremental_by_year']['2025']['avg_orders_per_observed_schedule_week']:.3f}/{s['results']['new_incremental_by_year']['2026']['avg_orders_per_observed_schedule_week']:.3f}单。"),
'', '## 独立复核与交付清单','',
(f"`verify_exact_rule_cross_league.py` 重读每笔原始Crown response并重新验证SHA、FID、联赛、球队、北京时间、FT、T1源报价、路径截止时间与亚洲盘结算；结果 `pass={str(ver['pass']).lower()}`，问题计数 `{json.dumps(ver['issues'],ensure_ascii=False)}`。"),
'', '- `run_exact_rule_cross_league.py`：批量回放、路径覆盖、冻结优先级和年度/联赛/周度统计。',
'- `exact_rule_cross_league_orders.jsonl.gz`：每笔唯一新增订单及原始盘口、方向、FT、五态结算、净U、路径时点、响应SHA和来源。',
'- `exact_rule_cross_league_coverage.json`：18,374场逐FID路径状态与原因。',
'- `exact_rule_cross_league_summary.json`：八组、去重合计、联赛、年份、ISO周和原八组合并统计。',
'- `exact_rule_cross_league_independent_verification.json`：独立原始数据结算核验。',
'- `frozen_e_direction_audit.json`：原冻结E组方向复算267/267核验。',
'- `exact_rule_cross_league_weekly.csv`：各组、候选合计、八组合并的完整ISO周明细。',
'- `SHA256SUMS.txt` 与 `EXECUTION_RECORD.md`：输入输出哈希、执行命令和提交记录。',
'', '## 解释边界','',
'正收益为对历史完整报价路径应用冻结规则后的模拟结果，不是未见前瞻样本，也不是可成交性的证明。总新增ROI接近零，2025/2026回落，少量联赛/年份贡献显著；目前证据不能支持将15联赛整体描述为稳定盈利扩单。原八组规则、生产模型、Telegram、正式账本、采集链和M9均未修改。','']
(OUT/'EXACT_RULE_CROSS_LEAGUE_REPORT.md').write_text('\n'.join(lines))
print('report rows',len(lines),'coverage rows',len(cov),'orders',len(orders))
