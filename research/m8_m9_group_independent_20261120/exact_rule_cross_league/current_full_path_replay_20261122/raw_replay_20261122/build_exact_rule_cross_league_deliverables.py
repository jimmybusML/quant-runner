from pathlib import Path
import collections,csv,datetime as dt,gzip,hashlib,json,math
from zoneinfo import ZoneInfo
P=Path('/private/tmp/quant-runner-m8-m9-groups-task/research/m8_m9_group_independent_20261120/exact_rule_cross_league/current_full_path_replay_20261122/raw_replay_20261122')
ROOT=Path('/private/tmp/quant-runner-m8-m9-groups-task')
PRIOR=P.parent
read=lambda p:[json.loads(l) for l in gzip.open(p,'rt',encoding='utf-8')]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def fmt(n): return f'{n:+.3f}'
def jsonlines(p): return [json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
def tbl(headers, rows):
 return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(x) for x in row)+' |' for row in rows])
s=json.load(open(P/'exact_rule_cross_league_summary.json'))
orders=read(P/'exact_rule_cross_league_orders.jsonl.gz')
features=read(P/'exact_rule_cross_league_features.jsonl.gz')
coverage=[json.loads(l) for l in open(P/'exact_rule_cross_league_coverage.jsonl')]
verification=json.load(open(P/'exact_rule_cross_league_independent_verification.json'))
helper_audit=json.load(open(P/'exact_rule_frozen_helper_audit.json'))
assert verification['pass'] and verification['checked_orders']==len(orders)==1273
assert len({x['fid'] for x in orders})==len(orders)
assert len(coverage)==18374 and len(features)==6967
bygroup=collections.defaultdict(list); byleague=collections.defaultdict(list)
for r in orders: bygroup[r['group']].append(r); byleague[(str(r['league_id']),str(r['league']))].append(r)
# Exact denominator: ISO calendar weeks that contain at least one target fixture;
# also retain the full first-to-last week span as a separate diagnostic.
weeks_by_calendar_year=collections.defaultdict(set); all_fixture_weeks=set(); fixture_dates=[]
for row in coverage:
 d=dt.date.fromisoformat(row['kickoff_beijing'][:10]); iso=d.isocalendar(); key=f'{iso.year}-W{iso.week:02d}'
 weeks_by_calendar_year[d.year].add(key); all_fixture_weeks.add(key); fixture_dates.append(d)
weeks=sorted(all_fixture_weeks)
start=min(fixture_dates);end=max(fixture_dates)
span_weeks=(end-dt.timedelta(days=end.weekday())-(start-dt.timedelta(days=start.weekday()))).days//7+1
weekly={w:collections.defaultdict(float) for w in weeks}
s['period']['unique_iso_weeks_with_target_fixtures']=len(weeks)
s['period']['calendar_span_iso_weeks']=span_weeks
s['period']['previous_elapsed_week_denominator']=s['period'].get('observed_schedule_weeks')
s['period']['observed_schedule_weeks']=len(weeks)
s['results']['new_incremental']['avg_orders_per_full_observed_schedule_week']=round(len(orders)/len(weeks),6)
s['results']['new_incremental']['calendar_span_avg_orders_per_week']=round(len(orders)/span_weeks,6)
s['results']['combined_original8_plus_new']['avg_weekly_added_orders']=round(len(orders)/len(weeks),6)
s['results']['combined_original8_plus_new']['calendar_span_avg_added_orders_per_week']=round(len(orders)/span_weeks,6)
s['results']['combined_original8_plus_new']['observed_schedule_weeks']=len(weeks)
s['results']['combined_original8_plus_new']['calendar_span_iso_weeks']=span_weeks
for g,v in s['groups'].items():
 v['avg_orders_per_full_observed_schedule_week']=round(v['assigned']['n']/len(weeks),6)
for y in range(2019,2027):
 key=str(y); nweeks=len(weeks_by_calendar_year.get(y,set()))
 if key in s['results']['new_incremental_by_year']:
  q=s['results']['new_incremental_by_year'][key];q['previous_elapsed_week_denominator']=q['observed_schedule_weeks'];q['observed_schedule_weeks']=nweeks
  q['avg_orders_per_observed_schedule_week']=round(q['n']/nweeks,6) if nweeks else 0.0
 if key in s['results']['annual_incremental_orders']:
  q=s['results']['annual_incremental_orders'][key];q['previous_elapsed_week_denominator']=q.get('observed_schedule_weeks');q['observed_schedule_weeks']=nweeks
  q['avg_per_observed_schedule_week']=round(q['n']/nweeks,6) if nweeks else 0.0
 if key in s['results']['merged_by_year']:
  q=s['results']['merged_by_year'][key];q['previous_elapsed_week_denominator']=q.get('observed_schedule_weeks');q['observed_schedule_weeks']=nweeks
  q['new_avg_orders_per_observed_schedule_week']=round(q['new_n']/nweeks,6) if nweeks else 0.0
(P/'exact_rule_cross_league_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
for r in orders:
 w=r['iso_week'];weekly[w][r['group']+'_n']+=1;weekly[w][r['group']+'_u']+=float(r['net_u']);weekly[w]['total_n']+=1;weekly[w]['total_u']+=float(r['net_u'])
with (P/'exact_rule_cross_league_weekly.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['iso_week']+sum(([g+'_orders',g+'_net_u'] for g in ('base','A','B','C','D','E','F','G')),[])+['total_orders','total_net_u'])
 for wk in weeks:
  vals=weekly[wk];row=[wk]
  for g in ('base','A','B','C','D','E','F','G'):row.extend([int(vals[g+'_n']),round(vals[g+'_u'],6)])
  row.extend([int(vals['total_n']),round(vals['total_u'],6)]);w.writerow(row)
status=collections.Counter(x['status'] for x in coverage)
by_l=collections.defaultdict(collections.Counter);by_y=collections.defaultdict(collections.Counter);league_names={}
for c in coverage:
 lid=str(c['league_id']);by_l[lid][c['status']]+=1;by_y[str(c.get('year'))][c['status']]+=1;league_names[lid]=c.get('source_league') or ''
coverage_doc={'scope':'original schedule_universe outside frozen49','generated_at_local':dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'source_rows':len(coverage),'unique_fids':len({x['fid'] for x in coverage}),'iso_weeks_with_target_fixtures':len(weeks),'calendar_span_iso_weeks':span_weeks,'weeks_by_calendar_year':{str(y):len(v) for y,v in sorted(weeks_by_calendar_year.items())},'provider_leagues':sorted(by_l,key=lambda z:int(z)),'status_counts':dict(status),'pregame_source_event_quote_fids':sum(status[k] for k in ('complete_T6_T3_T1_path','no_quote_at_or_before_T6')),'complete_T6_T3_T1_fids':sum(status[k] for k in ('complete_T6_T3_T1_path',)),'candidate_orders':len(orders),'no_exact_rule_signal_among_complete_paths':len([x for x in jsonlines(P/'exact_rule_cross_league_no_rule.jsonl') if x['status']=='no_exact_rule_match']),'by_league':{lid:{'league':league_names.get(lid,''),'total_fids':sum(by_l[lid].values()),'statuses':dict(by_l[lid])} for lid in sorted(by_l,key=lambda z:int(z))},'by_year':{y:dict(v) for y,v in sorted(by_y.items())},'live_receipt_fids':verification['live_capture_fids'],'evidence':'Only verified raw historical Crown movement response rows are classified as having pregame source-event AH quotes; this is not an actual pregame HTTP receipt.'}
(P/'exact_rule_cross_league_coverage.json').write_text(json.dumps(coverage_doc,ensure_ascii=False,indent=2)+'\n')
# Group/annual/league rows
order_groups=[]
for g in ('base','A','B','C','D','E','F','G'):
 rows=bygroup[g]; st=s['groups'][g]['assigned']; order_groups.append([g,st['n'],fmt(st['net_U']),f"{st['ROI_pct']:+.3f}%",f"{st['max_drawdown_U']:.3f}",f"{len(rows)/len(weeks):.3f}",f"{sum(float(x['selected_odds']) for x in rows)/len(rows):.3f}" if rows else '—'])
order_groups.append(['合计（按优先级去重）',len(orders),fmt(s['results']['new_incremental']['net_U']),f"{s['results']['new_incremental']['ROI_pct']:+.3f}%",f"{s['results']['new_incremental']['max_drawdown_U']:.3f}",f"{len(orders)/len(weeks):.3f}",f"{sum(float(x['selected_odds']) for x in orders)/len(orders):.3f}"])
annual_rows=[]
for y,v in s['results']['new_incremental_by_year'].items():
 m=s['results']['merged_by_year'][y]
 annual_rows.append([y,v['n'],fmt(v['net_U']),f"{v['ROI_pct']:+.3f}%",f"{v['max_drawdown_U']:.3f}",v['observed_schedule_weeks'],f"{v['avg_orders_per_observed_schedule_week']:.3f}",f"{m['frozen_n']} / {fmt(m['frozen_net_U'])}",f"{m['merged_n']} / {fmt(m['merged_net_U'])} / {m['merged_ROI_pct']:.3f}%"])
league_rows=[]
for (lid,name),rows in sorted(byleague.items(),key=lambda x:int(x[0][0])):
 n=len(rows);u=sum(float(x['net_u']) for x in rows);roi=100*u/n if n else None
 league_rows.append([lid,name,n,fmt(u),f'{roi:+.3f}%' if roi is not None else '—'])
bygroupyear=[]
for g in ('base','A','B','C','D','E','F','G'):
 cells=[]
 for y in range(2019,2027):
  x=s['groups'][g]['per_year'].get(str(y),{'n':0,'net_U':0.0});cells.append(f"{x['n']} / {fmt(x['net_U'])}")
 bygroupyear.append([g]+cells)
# every group x league result remains in JSON; compact markdown shows only aggregate by league
sett=s['deduplicated_union']['settlement_classes']
# prior replay reconciliation; do not discard previous outputs
newmap={x['fid']:x for x in orders}
prior_current=read(PRIOR/'exact_rule_cross_league_current_scope_orders.jsonl.gz')
prior_map={x['fid']:x for x in prior_current}
new_only=sorted(set(newmap)-set(prior_map));old_only=sorted(set(prior_map)-set(newmap))
shared=set(newmap)&set(prior_map)
changed=[f for f in shared if (newmap[f]['group'],newmap[f]['side'],round(float(newmap[f]['net_u']),6))!=(prior_map[f]['group'],prior_map[f]['side'],round(float(prior_map[f]['net_u']),6))]
features_by={x['fid']:x for x in features}
prior_paths={x['fid']:x for x in read(PRIOR/'full_union_complete_paths_20261122.jsonl.gz')}
recon={'prior_current_full_path_snapshot':{'orders':len(prior_map),'net_u':sum(float(x['net_u']) for x in prior_current),'roi_pct':100*sum(float(x['net_u']) for x in prior_current)/len(prior_current)},'current_direct_raw_snapshot':{'orders':len(newmap),'net_u':sum(float(x['net_u']) for x in orders),'roi_pct':s['results']['new_incremental']['ROI_pct']},'new_order_fids':new_only,'prior_only_fids':old_only,'shared_fids':len(shared),'shared_group_direction_net_changes':changed,'new_net_u_delta':round(sum(float(x['net_u']) for x in orders)-sum(float(x['net_u']) for x in prior_current),6),'changed_rows':[],'note':'All changed order FIDs have identical SHA-anchored raw Crown response bodies across the two archives. The changed classifications are in G; prior stored score_rates differ from the direct schedule-history reconstruction. This is retained as a model-rate provenance discrepancy; results are not silently merged.'}
for fid in sorted(set(new_only)|set(old_only)):
 a=newmap.get(fid);b=prior_map.get(fid);f=features_by.get(fid);po=prior_paths.get(fid)
 recon['changed_rows'].append({'fid':fid,'current':({'group':a['group'],'side':a['side'],'net_u':a['net_u'],'response_sha256':a['response_sha256'],'model_rates':a.get('model_rates')} if a else None),'prior':({'group':b['group'],'side':b['side'],'net_u':b['net_u']} if b else {'group':po.get('group'),'side':po.get('side'),'net_u':po.get('net_u'),'model_rates':po.get('score_rates'),'source_sha256':po.get('source_sha256',[None])[0]}),'same_raw_response_sha':bool(a and po and a['response_sha256']==po.get('source_sha256',[None])[0]),'current_model_rates':f.get('score_rates') if f else None})
(P/'snapshot_delta_audit.json').write_text(json.dumps(recon,ensure_ascii=False,indent=2)+'\n')
# Report annual counts and groups
report=f'''# M8 原八组精确规则跨联赛回测（当前只读 Crown 快照）

## 结论摘要

按原 `schedule_universe.jsonl` 的49联赛外范围，使用 T−6/T−3/T−1 检查点和 T−6 至 T−1 全部已保存 Crown 报价事件，直接重建原 base/A–G 规则并按冻结优先级去重后，得到 **{len(orders):,} 个八组外唯一 FID、{fmt(s['results']['new_incremental']['net_U'])}U、ROI {s['results']['new_incremental']['ROI_pct']:+.3f}%**。这只是历史报价源事件回放，实际赛前 Crown HTTP receipt 为 **0**，不能作为实盘或 Telegram 成绩。

新增订单按目标库存实际出现的 {len(weeks)} 个 ISO 周计算，新增平均 **{len(orders)/len(weeks):.3f} 单/周**；按首末赛事之间完整日历跨度的 {span_weeks} 个 ISO 周（含无目标赛事周）计算为 **{len(orders)/span_weeks:.3f} 单/周**。新增段的正收益不稳定：2024 +{s['results']['new_incremental_by_year']['2024']['net_U']:.3f}U，2025 {fmt(s['results']['new_incremental_by_year']['2025']['net_U'])}U，2026截至6月1日 {fmt(s['results']['new_incremental_by_year']['2026']['net_U'])}U。

| 组别 | 新增唯一订单 | 净U | ROI | MDD U | 每个有目标赛事 ISO 周均 | 平均选中赔率 |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join('| '+' | '.join(str(c) for c in r)+' |' for r in order_groups)}

## 输入、范围与规则执行

- 扩展赛程：{s['sources']['schedule_rows']:,} 场、{s['frozen_rules']['old49_count']}个冻结范围联赛；范围外 **{s['sources']['outside49_unique_fids']:,} 唯一FID / 15个联赛**。开赛日期 {s['period']['schedule_first_date']} 至 {s['period']['schedule_last_date']}。
- 冻结原八组名单 SHA256 `{s['frozen_rules']['frozen_membership_sha256']}`：{s['frozen_rules']['frozen_membership_n']:,} FID、+236.015U；新订单与冻结成员交集 **0**。
- 原 T6/T3/T1 检查点按开赛时间之前最近的有效 Crown 亚洲盘报价恢复；同时在 T6 到 T1 间保留每个实际盘口变动事件，以还原原规则的路径形态、价格移动次数和 D 组时间加权价格差。没有补造缺失报价。
- base/A/B/C/D/E/F 的优先级按 `base → A → B → C → D → E → F → G`。G 使用原独立动态攻防与联赛基线比分率更新公式，并按原双边AH EV方向逻辑；只使用同一联赛目标日前至少2个中国日已经结束的历史赛事。没有使用 M9。输入赛事身份采用扩展赛程队名且在目标场经 SHA 锚定 Crown 原始响应核对。
- 通过冻结 helper 的完整路径行 {helper_audit['full_path_fids_checked']:,}；组别与方向不一致为0。E组有 {helper_audit['E_endpoint_tie_directions_recovered_from_original_path_rule']} 个 `p1-p0` 端点平手，沿用被冻结 E 规则的全程价格方向确定侧，未猜方向。

## 报价与赛果覆盖

| 覆盖类别 | FID |
|---|---:|
| 目标范围赛事库存 | {len(coverage):,} |
| 有开赛前 Crown source-event AH 报价 | {coverage_doc['pregame_source_event_quote_fids']:,} |
| 完整 T6/T3/T1 且有可审计全路径 | {coverage_doc['complete_T6_T3_T1_fids']:,} |
| 有赛前报价但缺 T6（不计算规则命中） | {status.get('no_quote_at_or_before_T6',0):,} |
| 原始报价内没有可用赛前AH行 | {status.get('verified_raw_no_pregame_AH',0):,} |
| movement capture 明确无报价 | {status.get('movement_capture_without_quotes',0):,} |
| 完整路径、无冻结规则信号 | {coverage_doc['no_exact_rule_signal_among_complete_paths']:,} |
| 优先级去重的新订单 | {len(orders):,} |
| 可验证真实赛前 HTTP receipt | {verification['live_capture_fids']:,} |

NO_QUOTES、缺T6及无赛前AH行均作为数据覆盖不足保留，不被算作规则未命中。完整的逐FID状态、联赛、年度原因见 `exact_rule_cross_league_coverage.json` 和 `exact_rule_cross_league_coverage.jsonl`。

## 年度新增与合并结果

{tbl(['年份','新增单','新增净U','新增ROI','新增MDD U','库存周','新增单/周','冻结八组 单/U','合并 单/净U/ROI'],annual_rows)}

2024–2026新增净额合计 **{sum(s['results']['new_incremental_by_year'][str(y)]['net_U'] for y in (2024,2025,2026)):+.3f}U**；其中2026是仅截至6月1日的部分年度。

## 各组分年度订单与净U

{tbl(['组别']+[str(y) for y in range(2019,2027)],bygroupyear)}

各组按联赛的详细订单、净U、ROI已保存在 `exact_rule_cross_league_summary.json` 的 `groups.*.per_league`。整体联赛贡献：

{tbl(['Provider联赛ID','联赛','新增单','净U','ROI'],league_rows)}

订单方向重复交集按被冻结优先级只结算一次。原始组触发 1,450 次，176个 FID 触发多个组，最后为1,273笔唯一订单。组间触发对：`{json.dumps(s['overlap']['priority_rule_multi_trigger_fids'],ensure_ascii=False)}`。

AH四分之一盘拆成相邻两条半球盘分别结算，五态合计为：全赢 {sett.get('full_win',0)}、半赢 {sett.get('half_win',0)}、走水 {sett.get('push',0)}、半输 {sett.get('half_loss',0)}、全输 {sett.get('full_loss',0)}。ROI=净U/1U下注本金总额；MDD按逐日累计净U计算。

## 原八组合并

- 冻结原八组：{s['frozen_rules']['frozen_membership_n']:,} 单，+236.015U，ROI +2.293%。
- 49联赛外新增：{len(orders):,} 单，{fmt(s['results']['new_incremental']['net_U'])}U，ROI {s['results']['new_incremental']['ROI_pct']:+.3f}%，MDD {s['results']['new_incremental']['max_drawdown_U']:.3f}U。
- 按FID唯一合并：{s['results']['combined_original8_plus_new']['n']:,} 单，{fmt(s['results']['combined_original8_plus_new']['net_U'])}U，ROI {s['results']['combined_original8_plus_new']['ROI_pct']:.3f}%，MDD {s['results']['combined_original8_plus_new']['max_drawdown_U']:.3f}U；相对冻结原组历史净额增加 {fmt(s['results']['new_incremental']['net_U'])}U。

合并数值不掩盖新增订单段独立成绩。历史回放、实收收据和正式 Telegram 订单是不同状态；本报告中正式 Telegram订单和正式账本写入均为0。

## 完整 ISO 周结果

`exact_rule_cross_league_weekly.csv` 保留目标库存中实际出现的 {len(weeks)} 个 ISO 周，包括有赛事但零订单的周，并按组和合计列出订单数及净U。该周均以完整目标赛事库存跨度为分母，不以活跃周挑选。

## 复核与历史结果差异

独立校验器重新读取每笔订单的 Crown 原始响应及其 SHA、FID/联赛/球队/开赛时间、开赛前 T1 Crown AH 线和双边水位、可信 FT，并从头重算 AH 五态和四分之一盘拆腿结算：**{verification['independent_raw_quote_and_FT_rechecks']:,}/{verification['checked_orders']:,} 通过，问题数0**。扩展范围 live-mode Crown 收据 FID 为0。

早期 checkpoint-only（只以三个时点形成路径）的账本1,160单/+10.890U继续保存在父目录，未覆盖。本次全路径直接重建采用每个实际报价事件，不能把两份结果相加。另与11月22日先前全路径快照（1,271单/+7.185U）逐FID比较：当前新增3个G单并未复现其中1个G单，净差 +3.565U；四个差异FID的原始 Crown response SHA完全相同，而旧、新比分率存在差异。完整差异和 rates 在 `snapshot_delta_audit.json`。因此G组前推比分率的历史训练输入与旧全路径产物有可复核版本差异；本次报告按当前指定96,504赛程的直接重建列账，旧快照仍保留，读者不应把其与当前值合并成单一证据。

## 可复跑与限制

- 主研究：`run_exact_rule_cross_league_from_snapshot.py`。设置 `CROWN_SQLITE_PATH` 指向本机 Crown SQLite 或其一致性备份；备份用 `CROWN_SQLITE_IMMUTABLE=1`。脚本只读数据库、只写本目录结果。
- 独立验证：`verify_exact_rule_cross_league_from_snapshot.py`，从原始 Crown 响应/FT核对逐笔；使用相同环境变量。
- Crown一致性备份 SHA256 `{s['sources']['crown_sqlite_sha256']}`；扩展赛程 SHA256 `{s['sources']['schedule_sha256']}`；原八组 SHA256 `{s['frozen_rules']['frozen_membership_sha256']}`。
- 采集是历史回取，HTTP实际接收时间在赛后；7,106个 source-event pregame quotes 不等于7,106个实际赛前收到报价。结果不是实时可成交验证。
- 原八组、M9/M1/MR1、生产模型、Telegram、正式账本、Crown采集工作流及调度全部未改。
'''
(P/'EXACT_RULE_CROSS_LEAGUE_REPORT.md').write_text(report,encoding='utf-8')
# input manifest (sensitive DB and schedule remain private; only their hashes are published)
inputs={
 'expanded_schedule_universe':{'path':s['sources']['schedule_path'],'sha256':s['sources']['schedule_sha256'],'rows':s['sources']['schedule_rows'],'scope_rows':s['sources']['outside49_unique_fids']},
 'crown_sqlite_consistent_snapshot':{'path':s['sources']['crown_sqlite_path'],'sha256':s['sources']['crown_sqlite_sha256'],'included_in_public_repo':False},
 'frozen_membership':{'path':'/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl','sha256':s['frozen_rules']['frozen_membership_sha256'],'unique_fids':s['frozen_rules']['frozen_membership_n']},
 'frozen_rule_helpers':{'path':'research/m8/m8_frozen_eight_boundary_expansion_20261119.py','sha256':sha(ROOT/'research/m8/m8_frozen_eight_boundary_expansion_20261119.py')},
 'original_G_model_source':{'path':'research/m8/m8_raw_capture_unindexed_frozen_replay_20261115.py','sha256':sha(ROOT/'research/m8/m8_raw_capture_unindexed_frozen_replay_20261115.py')},
 'source_snapshot_note':'SQLite online backup made at a consistent point while the source database was active; raw Crown response files are SHA checked. The private database and raw responses are not copied to the repository.'}
(P/'INPUT_SHA256_MANIFEST.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2)+'\n')
# output SHA list excludes itself and output-manifest to avoid circularity
paths=sorted(x for x in P.iterdir() if x.is_file() and x.name not in {'SHA256SUMS.txt','OUTPUT_SHA256_MANIFEST.json'})
out={x.name:sha(x) for x in paths}
(P/'OUTPUT_SHA256_MANIFEST.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
paths=sorted(x for x in P.iterdir() if x.is_file() and x.name!='SHA256SUMS.txt')
(P/'SHA256SUMS.txt').write_text(''.join(f'{sha(x)}  {x.name}\n' for x in paths))
print(json.dumps({'report':str(P/'EXACT_RULE_CROSS_LEAGUE_REPORT.md'),'orders':len(orders),'new_net_u':s['results']['new_incremental']['net_U'],'combined':s['results']['combined_original8_plus_new'],'coverage':status,'output_files':len(list(P.iterdir()))},ensure_ascii=False,indent=2))
