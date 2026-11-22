#!/usr/bin/env python3
"""Descriptive influence audit of frozen base/A-G cross-league replay orders."""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[4]
HERE=pathlib.Path(__file__).resolve().parent
SOURCE=ROOT/'research/m8_m9_group_independent_20261120/exact_rule_cross_league/exact_rule_cross_league_orders.jsonl.gz'
FROZEN=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
GROUPS=['base','A','B','C','D','E','F','G']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
 with gzip.open(path,'rt',encoding='utf-8') as f:return [json.loads(x) for x in f if x.strip()]
def mdd(rows):
 bydate=collections.defaultdict(float)
 for r in rows:bydate[str(r['kickoff_beijing'])[:10]]+=float(r['net_u'])
 bal=peak=dd=0.
 for d in sorted(bydate):
  bal+=bydate[d]; peak=max(peak,bal); dd=max(dd,peak-bal)
 return round(dd,6)
def stats(rows):
 n=len(rows); pnl=round(sum(float(r['net_u']) for r in rows),6)
 weeks=collections.defaultdict(lambda:[0,0.])
 for r in rows:
  w=weeks[r['iso_week']];w[0]+=1;w[1]+=float(r['net_u'])
 return {'n':n,'net_U':pnl,'ROI_pct':round(pnl/n*100,6) if n else None,'MDD_U':mdd(rows),
         'active_weeks':len(weeks),'positive_weeks':sum(v[1]>1e-9 for v in weeks.values()),
         'negative_weeks':sum(v[1]<-1e-9 for v in weeks.values()),
         'flat_weeks':sum(abs(v[1])<=1e-9 for v in weeks.values()),
         'weekly':{k:{'n':v[0],'net_U':round(v[1],6)} for k,v in sorted(weeks.items())}}
def main():
 rows=load(SOURCE);fids=[str(x['fid']) for x in rows]
 if len(fids)!=len(set(fids)):raise SystemExit('duplicate FID in union ledger')
 if any(x.get('frozen_10294_overlap') for x in rows):raise SystemExit('candidate intersects frozen flag')
 frozen={str((json.loads(line).get('fid') or json.loads(line).get('match_id'))) for line in FROZEN.open() if line.strip()}
 if frozen.intersection(fids):raise SystemExit('candidate intersects frozen membership IDs')
 overlap=collections.Counter()
 for r in rows:
  gs=sorted(set(r.get('trigger_groups') or [r['group']]))
  for i,a in enumerate(gs):
   for b in gs[i+1:]:overlap[f'{a}|{b}']+=1
 result={'study':'M8 frozen base/A-G exact cross-league replay group-level concentration audit',
  'status':'descriptive historical source-event replay diagnostics; no rule or member changed',
  'source_sha256':sha(SOURCE),'frozen_sha256':sha(FROZEN),'union':stats(rows),
  'union_unique_fids':len(set(fids)),'frozen_unique_fids':len(frozen),'frozen_overlap':len(set(fids)&frozen),
  'source_type_counts':dict(collections.Counter(r.get('capture_mode','unknown') for r in rows)),
  'actual_http_pregame_receipts':sum(bool(r.get('pregame_http_receipt_verified')) for r in rows),
  'raw_trigger_overlap_pair_counts':dict(sorted(overlap.items())),
  'groups':{},'all_years':sorted({int(r['year']) for r in rows})}
 for g in GROUPS:
  gr=[r for r in rows if r['group']==g]
  byleague={l:stats([r for r in gr if r['league_id']==l]) for l in sorted({r['league_id'] for r in gr})}
  byyear={str(y):stats([r for r in gr if int(r['year'])==y]) for y in result['all_years'] if any(int(r['year'])==y for r in gr)}
  positive=sorted(((s['net_U'],l) for l,s in byleague.items() if s['net_U']>0),reverse=True)
  lead=positive[0][1] if positive else None
  yr_positive=sorted(((s['net_U'],int(y)) for y,s in byyear.items() if s['net_U']>0),reverse=True)
  leadyear=yr_positive[0][1] if yr_positive else None
  leave_league={l:round(stats([r for r in gr if r['league_id']!=l])['net_U'],6) for l in sorted(byleague)}
  leave_year={y:round(stats([r for r in gr if str(r['year'])!=y])['net_U'],6) for y in sorted(byyear)}
  result['groups'][g]={'assigned_unique_orders':stats(gr),'league':byleague,'annual':byyear,
    'positive_leagues':sum(s['net_U']>0 for s in byleague.values()),'negative_leagues':sum(s['net_U']<0 for s in byleague.values()),
    'top_positive_league_by_net_U':lead,'net_after_removing_top_positive_league':leave_league.get(lead) if lead else stats(gr)['net_U'],
    'leave_one_league_out_net_U':leave_league,'positive_years':sum(s['net_U']>0 for s in byyear.values()),
    'negative_years':sum(s['net_U']<0 for s in byyear.values()),'top_positive_year_by_net_U':leadyear,
    'net_after_removing_top_positive_year':leave_year.get(str(leadyear)) if leadyear else stats(gr)['net_U'],
    'leave_one_year_out_net_U':leave_year}
 # Check group partitions exactly reproduce union; all outputs refer to same single assigned group per FID.
 assigned=sum(x['assigned_unique_orders']['n'] for x in result['groups'].values())
 pnl=round(sum(x['assigned_unique_orders']['net_U'] for x in result['groups'].values()),6)
 if assigned!=len(rows) or pnl!=result['union']['net_U']:raise SystemExit('group partition does not reconcile')
 result['group_partition_reconciles']={'n':assigned,'net_U':pnl,'pass':True}
 result['execution_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
 (HERE/'group_concentration_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 # Compact complete group x league/year CSVs.
 import csv
 with (HERE/'group_league_year.csv').open('w',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['group','dimension','key','n','net_U','ROI_pct','MDD_U','active_weeks'])
  for g,x in result['groups'].items():
   for l,s in x['league'].items():w.writerow([g,'league',l,s['n'],s['net_U'],s['ROI_pct'],s['MDD_U'],s['active_weeks']])
   for y,s in x['annual'].items():w.writerow([g,'year',y,s['n'],s['net_U'],s['ROI_pct'],s['MDD_U'],s['active_weeks']])
 print(json.dumps({'union':result['union'],'groups':{g:{'n':x['assigned_unique_orders']['n'],'net_U':x['assigned_unique_orders']['net_U'],'ROI_pct':x['assigned_unique_orders']['ROI_pct'],'MDD_U':x['assigned_unique_orders']['MDD_U'],'lead_positive_league':x['top_positive_league_by_net_U'],'net_without_lead_league':x['net_after_removing_top_positive_league'],'positive_years':x['positive_years'],'negative_years':x['negative_years']} for g,x in result['groups'].items()},'frozen_overlap':result['frozen_overlap'],'trigger_overlaps':result['raw_trigger_overlap_pair_counts']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
