# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""M8 batch expansion reconciliation for unique fixture IDs; research only."""
from __future__ import annotations
import collections, datetime as dt, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; M8=ROOT/'research/m8'
BASE=Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
FILES=[M8/'m8_batch_ad_orders_20261118.jsonl',M8/'m8_batch_eh_orders_20261118.jsonl',M8/'m8_batch_il_orders_20261118.jsonl']
AUDIT=M8/'m8_batch_actual_receipt_independently_audited_20261118.jsonl'
OUT=M8/'m8_batch_union_20261118.json'; REPORT=M8/'M8_BATCH_INCREMENTAL_UNION_20261118.md'
def read(p): return [json.loads(s) for s in p.open() if s.strip()]
def dte(r): return str(r.get('date') or (r.get('kickoff_utc') or '')[:10])[:10]
def metrics(rs):
 rs=[r for r in rs if dte(r) and dte(r)[:4] in {'2024','2025','2026'}]
 if not rs:return {'orders':0,'net_u':0.0,'roi_pct':None,'weeks_elapsed':0,'active_weeks':0,'avg_orders_per_week':None,'max_drawdown_u_daily_close':0.0}
 day=collections.defaultdict(float); wk=collections.Counter(); total=sum(float(r['pnl_u']) for r in rs)
 for r in rs:
  date=dte(r); day[date]+=float(r['pnl_u']); dd=dt.date.fromisoformat(date); iso=dd.isocalendar();wk[(iso.year,iso.week)]+=1
 peak=bal=mdd=0.
 for date in sorted(day):
  bal+=day[date];peak=max(peak,bal);mdd=max(mdd,peak-bal)
 first=min(dt.date.fromisoformat(dte(r)) for r in rs);last=max(dt.date.fromisoformat(dte(r)) for r in rs)
 weeks=((last-dt.timedelta(days=last.weekday()))-(first-dt.timedelta(days=first.weekday()))).days//7+1
 return {'orders':len(rs),'net_u':round(total,6),'roi_pct':round(total/len(rs)*100,6),'weeks_elapsed':weeks,'active_weeks':len(wk),'avg_orders_per_week':round(len(rs)/weeks,6),'avg_orders_per_active_week':round(len(rs)/len(wk),6),'max_drawdown_u_daily_close':round(mdd,6),'weekly':{f'{y}-W{w:02}':n for (y,w),n in sorted(wk.items())}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base_rows=read(BASE); base={str(r['fid']):{'fid':str(r['fid']),'date':r['date'],'pnl_u':float(r['pnl']),'method':'frozen_original_eight','source_type':'foundation'} for r in base_rows}
# Actual audited E/F/H rows replace their original model ledger PnL and carry exact receipt time / verified FT.
audited=read(AUDIT); aud={(r['method'],str(r['fid'])):r for r in audited}
allrows=[]
for p in FILES:
 for r in read(p):
  r['fid']=str(r['fid']);r['date']=dte(r)
  if r.get('source_type')=='actual_http_receipt' and (r['method'],r['fid']) in aud:
   a=aud[(r['method'],r['fid'])];r.update({'pnl_u':a['audit_pnl_u'],'signal_time_utc':a['signal_time_utc'],'verified_receipt_horizon':a['verified_receipt_horizon'],'received_utc':a['received_utc'],'raw_sha256':a['raw_sha256'],'snapshot_sha256':a['snapshot_sha256'],'ft':a['ft'],'ft_source':a['ft_source']})
  allrows.append(r)
methods=sorted({r['method'] for r in allrows}); per={}; hist_fids={}; actual_fids={}
for m in methods:
 rs=[r for r in allrows if r['method']==m]; h=[r for r in rs if r.get('source_type')!='actual_http_receipt' and r['date'][:4] in {'2024','2025','2026'}]; a=[r for r in rs if r.get('source_type')=='actual_http_receipt']
 # enforce one order per method+FID; report duplicate keys instead of quietly stacking.
 def unique_rows(xs):
  dic={}
  for r in xs:dic.setdefault(r['fid'],r)
  return list(dic.values())
 h=unique_rows(h);a=unique_rows(a);hn=[r for r in h if r['fid'] not in base]; an=[r for r in a if r['fid'] not in base]
 hist_fids[m]={r['fid'] for r in h};actual_fids[m]={r['fid'] for r in a}
 combined=list(base.values())+hn; combined_actual=[r for r in base.values() if r['date'][:4]=='2026']+an
 annual={}
 for y in ('2024','2025','2026'):
  annual[y]={'candidate_outside_frozen':metrics([r for r in hn if r['date'][:4]==y]),'foundation_plus_candidate':metrics([r for r in base.values() if r['date'][:4]==y]+[r for r in hn if r['date'][:4]==y])}
 per[m]={'historical_candidate_all_2024_2026':metrics(h),'historical_increment_outside_frozen':metrics(hn),'historical_by_year':annual,'foundation_plus_candidate':metrics(combined),'actual_receipts_all':metrics(a),'actual_receipts_increment_outside_frozen':metrics(an),'foundation_2026_plus_actual_receipt_increment':metrics(combined_actual),'frozen_overlap_historical':len(hist_fids[m]&base.keys()),'frozen_overlap_actual':len(actual_fids[m]&base.keys()),'historical_fids':sorted(hist_fids[m]),'actual_fids':sorted(actual_fids[m])}
# Pair overlaps, with candidate vs candidate, split by replay type.
pair={}; pairs=[]
for i,x in enumerate(methods):
 for y in methods[i+1:]:
  ov=len(hist_fids[x]&hist_fids[y]); aov=len(actual_fids[x]&actual_fids[y]);pair[f'{x} × {y}']={'historical_fids':ov,'actual_receipt_fids':aov}
  if ov or aov:pairs.append((ov,aov,x,y))
pairs.sort(reverse=True)
# Unique fixture universe is coverage only; PnL for a cross-method union is not uniquely defined.
uniq_hist=set().union(*hist_fids.values());uniq_actual=set().union(*actual_fids.values())
base24={y:metrics([r for r in base.values() if r['date'][:4]==y]) for y in ('2024','2025','2026')}
result={'study':'M8_BATCH_EXPANSION_A_TO_L_20261118','historical_replay_period':'2024-01-01 through latest candidate date by method; report per-year and observed week span','frozen_eight':{'fixtures':len(base),'sha256':sha(BASE),'by_year':base24,'all_2024_2026':metrics(list(base.values()))},'candidate_rows':len(allrows),'unique_candidate_historical_fids_including_frozen_overlap':len(uniq_hist),'unique_candidate_historical_fids_outside_frozen':len(uniq_hist-base.keys()),'unique_candidate_actual_receipt_fids_including_frozen_overlap':len(uniq_actual),'unique_candidate_actual_receipt_fids_outside_frozen':len(uniq_actual-base.keys()),'candidate_method_count':len(methods),'pairwise_overlap':pair,'methods':per,'all_candidate_union_pnl':'Not assigned: overlapping methods can select different sides/quotes for the same FID; no user-approved arbitration rule exists. Coverage is deduplicated by FID, while combined PnL is shown per method.'}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
lines=['# M8 A–L 新增订单与原八组合并｜2026-11-18','', '本报告按唯一 FID 复核候选，历史 source-event 回放与真实赛前 HTTP 收据分开。候选在原八组中的重叠仅作事后归属，命中原八组时保留冻结会员原方向、原 PnL，不把候选再计为新增订单。每个方法的“合并”是原八组 + 该方法独有 FID；跨方法总 PnL 不虚构仲裁，方法相互选边时无法得到唯一的一注/场结果。','',f"冻结八组：{len(base)} 个唯一 FID；SHA256 `{sha(BASE)}`。候选方法 {len(methods)} 个，历史候选并集 {len(uniq_hist)} FID，其中八组外 {len(uniq_hist-base.keys())} FID；真实收据候选并集 {len(uniq_actual)} FID，其中八组外 {len(uniq_actual-base.keys())} FID。","",'## 冻结八组基线','', '| 年度 | 场次 | 净U | ROI | 平均单/周 | 日末最大回撤 |','|---|---:|---:|---:|---:|---:|']
for y,x in base24.items(): lines.append(f"| {y} | {x['orders']} | {x['net_u']:+.3f} | {x['roi_pct']:.3f}% | {x['avg_orders_per_week']:.2f} | {x['max_drawdown_u_daily_close']:.3f}U |")
x=metrics(list(base.values()));lines.append(f"| 2024–26 | {x['orders']} | {x['net_u']:+.3f} | {x['roi_pct']:.3f}% | {x['avg_orders_per_week']:.2f} | {x['max_drawdown_u_daily_close']:.3f}U |")
lines += ['', '## 新增盈利机会排行榜（历史增量，2024–2026）','', '排名先按净U降序展示；同一唯一比赛不会在单方法中重复。所有方法是否“增加盈利订单”看净U与 ROI：正场次不代表盈利订单池。周均按每个方法的首末实际候选日期覆盖周数计算，MDD 为按比赛日期聚合的日末累计净值回撤。','', '| 方法 | 新增场次 | 单/周 | 净U | ROI | MDD | 2024 U/ROI | 2025 U/ROI | 2026 U/ROI | 冻结重叠 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for m,v in sorted(((m,v) for m,v in per.items() if v['historical_increment_outside_frozen']['orders']),key=lambda kv:(kv[1]['historical_increment_outside_frozen']['net_u'],kv[1]['historical_increment_outside_frozen']['orders']),reverse=True):
 x=v['historical_increment_outside_frozen']; yrs=[v['historical_by_year'][y]['candidate_outside_frozen'] for y in ('2024','2025','2026')]
 yrstr=lambda z:'—' if not z['orders'] else f"{z['orders']}/{z['net_u']:+.1f}/{(z['roi_pct'] or 0):+.2f}%"
 lines.append(f"| {m} | {x['orders']} | {(x.get('avg_orders_per_week') or 0):.2f} | {x['net_u']:+.3f} | {(x['roi_pct'] or 0):+.3f}% | {x['max_drawdown_u_daily_close']:.3f}U | {yrstr(yrs[0])} | {yrstr(yrs[1])} | {yrstr(yrs[2])} | {v['frozen_overlap_historical']} |")
lines += ['', '## 各方法 + 原八组（历史 2024–2026）','', '| 方法 | 合并场次 | 单/周 | 合并净U | 合并 ROI | MDD | 新增场次 | 新增净U |','|---|---:|---:|---:|---:|---:|---:|']
for m,v in sorted(((m,v) for m,v in per.items() if v['historical_increment_outside_frozen']['orders']),key=lambda kv:kv[1]['historical_increment_outside_frozen']['net_u'],reverse=True):
 x=v['foundation_plus_candidate']; n=v['historical_increment_outside_frozen']; lines.append(f"| {m} | {x['orders']} | {(x.get('avg_orders_per_week') or 0):.2f} | {x['net_u']:+.3f} | {x['roi_pct']:.3f}% | {x['max_drawdown_u_daily_close']:.3f}U | {n['orders']} | {n['net_u']:+.3f} |")
lines += ['', '### 原八组 + 单一方法：年度合并结果','', '| 方法 | 年度 | 合并场次 | 净U | ROI | 周均单量 | 日末 MDD |','|---|---:|---:|---:|---:|---:|---:|']
for m,v in sorted(((m,v) for m,v in per.items() if v['historical_increment_outside_frozen']['orders']),key=lambda kv:kv[1]['historical_increment_outside_frozen']['net_u'],reverse=True):
 for y in ('2024','2025','2026'):
  x=v['historical_by_year'][y]['foundation_plus_candidate']; lines.append(f"| {m} | {y} | {x['orders']} | {x['net_u']:+.3f} | {x['roi_pct']:.3f}% | {x['avg_orders_per_week']:.2f} | {x['max_drawdown_u_daily_close']:.3f}U |")
lines += ['', '## 真正赛前 Crown 收据回放（单列；2026）','', 'E–H 独立审计使用逐行 HTTP 收件时刻和真实 snapshot horizon 精确匹配 Crown 快照，验证原始 SHA、快照 SHA、赛前时刻及独立 FT 来源；AH quarter-line 分腿重算。该实收样本是事后选题后的回顾性模型重放，不是前瞻性下注。其他方向使用各自真实收据来源；不可把历史 event-time 与收到的价混在一起。7 个方向只有真实收据覆盖、没有完整历史候选池；其历史表格不报零场伪装为负结果，以下按真实收据实测样本呈现。','', '| 方法 | 实收样本 n/U/ROI | 八组外实收增量 n/U/ROI | 原八组 + 实收增量 n/U/ROI | 周均新增 | MDD 增量回放 | 重叠八组 |','|---|---:|---:|---:|---:|---:|---:|']
for m,v in sorted(per.items(),key=lambda kv:kv[1]['actual_receipts_increment_outside_frozen']['net_u'],reverse=True):
 a=v['actual_receipts_all'];n=v['actual_receipts_increment_outside_frozen'];c=v['foundation_2026_plus_actual_receipt_increment']; f=lambda z:f"{z['orders']}/{z['net_u']:+.2f}/{(z['roi_pct'] or 0):+.2f}%" if z['orders'] else '0/—/—';lines.append(f"| {m} | {f(a)} | {f(n)} | {f(c)} | {(n.get('avg_orders_per_week') or 0):.2f} | {n['max_drawdown_u_daily_close']:.2f}U | {v['frozen_overlap_actual']} |")
lines += ['', '## 方法重叠','',f"候选历史并集 {len(uniq_hist)} 个 FID、真实收据并集 {len(uniq_actual)} 个 FID；方法各自的逐场记录与完整两两交集计数均保存在 `{OUT.name}` 的 `methods` / `pairwise_overlap`。以下列出历史重叠最多的组合：",'', '| 方法组合 | 历史相同 FID | 实收相同 FID |','|---|---:|---:|']
for ov,aov,x,y in pairs[:20]: lines.append(f'| {x} × {y} | {ov} | {aov} |')
lines += ['', '## 排名解读与审计边界','', '- A–L 本轮没有形成可确认的跨年新增盈利机制：历史年度方向分布、原八组结合表现、真实收据回放和 D 的路径状态子组均按原始方法保留，详细方向差异见 `M8_BATCH_EXPANSION_INDEX_20261118.md`。','- D 的 `multi_reversal` 是一个后验汇总子组：2024、2025、2026 全池约 +4.700U、-17.350U、+20.295U；原八组外 128 FID 累计仅 +0.530U，2025 为负。该分组与 R33 重叠，不能称独立盈利扩单。','- E–H 初始版曾因 away AH margin 错误给出正收益，已作废并保留审计记录；正确分腿结算后历史年和实收均为负。见 `m8_batch_eh_invalidated_run_20261118.json`。','- 没有 A–L 跨方法统一合并收益：方法在重复 FID 上会选不同方向，任何择一规则都会是新仲裁研究参数。报告提供每个方法各自与冻结八组合并的完整净U、ROI、周均订单和 MDD，且不给重叠订单虚增计数。','- 历史时间戳缺失的事件回放保留空时间，不从日期伪造精确 UTC；按年度完整留存 2024/25/26 的 PnL、ROI、场次、周分布、MDD 和周均。真实收据行保留 HTTP 收件与 FT provenance。','- 真实实收相对历史模型训练数据可能重叠，所有实收结果均是这批收据已存在后设计的策略回放，不等于未来 OOS。']
REPORT.write_text('\n'.join(lines)+'\n')
print(json.dumps({'summary':str(OUT),'report':str(REPORT),'methods':len(methods),'candidate_rows':len(allrows),'unique_historical_fids':len(uniq_hist),'unique_receipt_fids':len(uniq_actual)},ensure_ascii=False))
