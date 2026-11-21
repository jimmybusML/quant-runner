"""Attribution of pair vs formation disagreement to each model's market-only
direction flip, using existing per-FID historic predictions at T12. Not a filter.
"""
import gzip,json,collections,math,statistics
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
R=Path('/Users/mac/.codex/worktrees/m8-discipline-referee/quant-runner-m8-goalkeeper/research/m8')
q={r['fid']:r for s in gzip.open(P/'full_priced_T6_original_and_expanded.jsonl.gz','rt') if (r:=json.loads(s))['year']>=2024}
methods=collections.defaultdict(dict)
for label,p in [('pair',R/'player_pair_cohesion_20261121/pair_cohesion_per_fixture_20261121.jsonl.gz'),('formation',R/'prior_formation_market_20261121/formation_market_per_fixture_20261121.jsonl.gz')]:
 for s in gzip.open(p,'rt'):
  r=json.loads(s)
  if not r['frozen_overlap']:methods[str(r['fid'])][label+'.'+r['method']]=r
basic=[]
for fid,methods0 in methods.items():
 if fid not in q or len(methods0)!=6:continue
 a=methods0['pair.market_plus_pair'];b=methods0['formation.market_plus_formation']
 conflict=a['chosen_side']!=b['chosen_side']
 r={'fid':fid,'year':int(a['year']),'league':str(a['league']),'conflict':conflict}
 for name in ['pair','formation']:
  base=methods0[name+'.market_only'];co=methods0[name+'.market_plus_'+name]
  if name=='formation':co=methods0['formation.market_plus_formation']
  r[name+'_market_only_side']=base['chosen_side']
  r[name+'_combined_side']=co['chosen_side']
  r[name+'_flip_market_to_combined']=base['chosen_side']!=co['chosen_side']
  r[name+'_market_net_T12']=base['net_u']
  r[name+'_combined_net_T12']=co['net_u']
  r[name+'_combined_minus_market_net_T12']=co['net_u']-base['net_u']
  r[name+'_evgap_market_T12']=base['home_EV_U']-base['away_EV_U']
  r[name+'_evgap_combined_T12']=co['home_EV_U']-co['away_EV_U']
  r[name+'_pred_homeGD_market']=base['predicted_home_goal_difference']
  r[name+'_pred_homeGD_combined']=co['predicted_home_goal_difference']
 r['abs_forecast_GD_gap_between_pair_formation']=abs(a['predicted_home_goal_difference']-b['predicted_home_goal_difference'])
 basic.append(r)
assert len(basic)==3949
groups=collections.defaultdict(list)
for r in basic:
 for k in [('year',r['year']),('year_type',r['year'],'conflict' if r['conflict'] else 'agree')]:
  groups[k].append(r)
def summary(v):
 n=len(v);results={'n':n}
 for name in ('pair','formation'):
  z=[r for r in v if r[name+'_flip_market_to_combined']]
  results[name]={
   'flip_n':len(z),'flip_share_pct':round(100*len(z)/n,3),
   'market_T12_net':round(sum(r[name+'_market_net_T12'] for r in v),3),
   'combined_T12_net':round(sum(r[name+'_combined_net_T12'] for r in v),3),
   'delta_T12_net':round(sum(r[name+'_combined_minus_market_net_T12'] for r in v),3),
   'delta_net_only_changed':round(sum(r[name+'_combined_minus_market_net_T12'] for r in z),3),
   'flip_combined_side_home_n':sum(r[name+'_combined_side']=='home' for r in z),
   'abs_evgap_market_median':round(statistics.median(abs(r[name+'_evgap_market_T12']) for r in v),5),
   'abs_evgap_combined_median':round(statistics.median(abs(r[name+'_evgap_combined_T12']) for r in v),5),
   'abs_forecast_delta_on_flips_median':round(statistics.median(abs(r[name+'_pred_homeGD_combined']-r[name+'_pred_homeGD_market']) for r in z),5) if z else None
  }
 results['abs_pair_formation_pred_GD_gap_median']=round(statistics.median(r['abs_forecast_GD_gap_between_pair_formation'] for r in v),5)
 return results
out={'samples':{'both_models':len(basic),'conflicts':sum(r['conflict'] for r in basic)},
 'groups':{'|'.join(map(str,k)):summary(v) for k,v in groups.items()},
 'notes':['Original saved model choice as-of historical T12; no T12 live HTTP receipt proof',
 'Market-only models have distinct original training pools','No selection gates or production changes']}
(P/'conflict_model_flip_summary_20261121.json').write_text(json.dumps(out,indent=2))
with gzip.open(P/'conflict_model_flip_ledger_20261121.jsonl.gz','wt') as f:
 for r in basic:f.write(json.dumps(r)+'\n')
for y in (2024,2025,2026):print(y,out['groups'][f'year_type|{y}|conflict'],flush=True)
