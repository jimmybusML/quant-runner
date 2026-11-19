#!/usr/bin/env python3
"""Build concise overlap and prior-C study audit from full archived ledgers."""
import collections,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];D=ROOT/'research/m8/next_round_20261120'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def gz(p):
 with gzip.open(p,'rt',encoding='utf8') as f:
  for ln in f:
   if ln.strip():yield json.loads(ln)
a=list(gz(D/'strength_shock_per_fixture_20261120.jsonl.gz'));b=list(gz(D/'per_fixture_walkforward_20261120.jsonl.gz'))
maps={}
for x in a:maps.setdefault('A:'+x['model'],{})[x['fid']]=x
for x in b:maps.setdefault('B:'+x['model'],{})[x['fid']]=x
for x in a:
 if max(x['home_EV_U'],x['away_EV_U'])>0:maps.setdefault('A:'+x['model']+':EVpositive',{})[x['fid']]=x
overlap={}
names=sorted(maps)
for i,n in enumerate(names):
 for m in names[i+1:]:
  common=set(maps[n])&set(maps[m]);conf=0
  for fid in common:
   x,y=maps[n][fid],maps[m][fid]
   sx=x.get('direction');sy=y.get('direction')
   if sx is None:sx=x.get('direction')
   if sy is None:sy=y.get('direction')
   if sx and sy and sx!=sy:conf+=1
  overlap[n+'|'+m]={'intersection_fids':len(common),'direction_conflicts':conf,'unique_union_fids':len(set(maps[n])|set(maps[m]))}
# Reuse C's completed time-forward boundary-expansion experiment as a prior,
# rather than rerunning or reselecting its thresholds.
prior=ROOT/'research/m8/frozen_eight_boundary_expansion_20261119/M8_FROZEN_EIGHT_BOUNDARY_EXPANSION_RESULTS_20261119.json';cx=json.load(open(prior))
groups=[]
for group in ('base','A','B','C','D','E','F','G'):
 for variant in ('market_path','market_path_plus_team_history'):
  key=f'{group}|{variant}|q95'
  if key not in cx['candidate_summary']:
   groups.append({'group':group,'variant':variant,'q95_available':False,'reason':'No q95 candidates were emitted in the archived experiment; full q90 outcomes remain in source JSON.'});continue
  v=cx['candidate_summary'][key];c=v['candidate']
  groups.append({'group':group,'variant':variant,'q95_available':True,'n':c['n'],'net_u':c['net_U'],'roi_pct':c['ROI_pct'],'mdd_u':c['max_drawdown_U'],'weekly_mean_orders':c['avg_per_calendar_week'],'overlap_frozen':v.get('fid_overlap_with_frozen',0),'delta_vs_frozen':v.get('delta_net_U_vs_frozen')})
out={'study':'M8 A-D overlap and prior C audit','A_B_candidate_overlap':overlap,'candidate_method_fid_counts':{k:len(v) for k,v in maps.items()},'candidate_unique_fids_by_mechanism':{'A/B shared historical outsiders':len(set(maps['A:pregame_market_surprise_shock'])&set(maps['B:spline_contract'])),'frozen_eight_overlap':0},'C_prior_boundary_expansion':{'source_report':'research/m8/M8_FROZEN_EIGHT_BOUNDARY_EXPANSION_20261119.md','source_results_sha256':sha(prior),'frozen_membership_sha256':cx['frozen_foundation']['frozen_membership_sha256'],'frozen_member_count':cx['frozen_foundation']['frozen_membership_n'],'candidate_union_fids':cx['candidate_overlap']['unique_union_FIDs'],'method_direction_conflicts':len(cx['candidate_overlap']['direction_conflict_FIDs']),'actual_http_receipt_candidate_fids':cx['actual_HTTP_receipt_replay']['_all']['candidate_receipt_boundary_replay_rows'],'q95_by_frozen_group':groups,'reason_not_rerun':'Exact same boundary similarity/q90-q99 mechanism was fully executed on 2026-11-19; rerunning would be a duplicate parameter search, not an independent test.'}}
(D/'A_D_C_OVERLAP_AUDIT_20261120.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'method_fids':out['candidate_method_fid_counts'],'A_B_shared':out['candidate_unique_fids_by_mechanism'],'C':{k:v for k,v in out['C_prior_boundary_expansion'].items() if k!='q95_by_frozen_group'},'C_q95':groups},ensure_ascii=False,indent=2))
