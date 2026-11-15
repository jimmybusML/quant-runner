import json,hashlib,datetime,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_receipt_robustness_20261115.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Keep the fixed trained models. Neutral performance values are a diagnostic, not a new candidate.
lids=sorted({r['league'] for r in te})
sa=[r for r in te if r['league']=='290']
assert len(sa)==26
F=featuremaps['TC']
neutral={r['fid']:[12.,4.,50.,1.4,.35]*4 for r in sa}
pp={'market_implied':g['make_pred'](sa,vec(sa,'mh')+vec(sa,'ma'))}
for k in ('market','full','full_shot_efficiency'):pp[k]=g['forecast'](tr,sa,F,k)
pp['neutral_history_diagnostic']=g['forecast'](tr,sa,neutral,'full_shot_efficiency')
assert g['stat'](pp['full_shot_efficiency'][2])['U']==-10.94
y=vec(sa,'hg')+vec(sa,'ag')
def describe(r,p):
 total,side,pnl=p
 return {**g['stat'](pnl),**g['probstats'](r,total),'avg_pred_total':round(float(total.mean()),3),'actual_avg_total':round(float(np.mean(vec(r,'hg')+vec(r,'ag'))),3),'over_n':int(side.sum()),'under_n':int((~side).sum()),'over':g['stat'](pnl[side]),'under':g['stat'](pnl[~side])}
d={k:describe(sa,p) for k,p in pp.items()}
base=pp['market_implied'];cand=pp['full_shot_efficiency'];sw=base[1]!=cand[1]
d['switch_diagnostic']={'n':int(sw.sum()),'market_on_switch':g['stat'](base[2][sw]),'candidate_on_switch':g['stat'](cand[2][sw]),'same_direction':g['stat'](cand[2][~sw]),'avg_model_minus_market_goals':round(float(np.mean(cand[0]-base[0])),4)}
old_sa=[r for r in g['tcvalid'] if r['league']=='290' and r['year']==2026]
op=g['forecast'](tr,old_sa,g['tcfeat'],'full_shot_efficiency')
# Existing earlier test archive is separate, not added to the actual receipt replay.
d['earlier_archive']=describe(old_sa,op)
# Independently count all confirmed schedule rows and available complete performance in both local caches.
coverage={}
for l in lids:
 files=list((P.parent/'data/m5-crown-authorized/schedules'/l).glob('*.raw.json'))+list((P.parent/'data/m5-crown-authorized-refresh-20261105/schedules'/l).glob('*.raw.json'))
 sched={};perf=set();raw_fields=collections.Counter()
 for f in files:
  for r in json.loads(f.read_bytes())['data']['matches']:
   if r.get('status')!='full':continue
   fid=str(r['id']);sched[fid]=str(r['start'])[:10]
   for k in ('shot_on','shot_off','possess'):raw_fields[k]+=int(k in r)
   if all(isinstance(r.get(k),list) and len(r[k])==2 and all(v is not None for v in r[k]) for k in ('shot_on','shot_off','possess')):perf.add(fid)
 hist=[r for r in T.values() if str(r['league'])==l]
 test=[r for r in te if r['league']==l]
 years=collections.Counter(r['date'][:4] for r in hist);ys=collections.Counter(v[:4] for v in sched.values())
 coverage[l]={'name':next(r['name'] for r in items if r['league']==l),'schedule_cached_unique_FT':len(sched),'schedule_cache_complete_performance':len(perf),'schedule_year_counts':dict(sorted(ys.items())),'TC_confirmed_complete':len(hist),'TC_dates':[min(r['date'] for r in hist),max(r['date'] for r in hist)],'TC_year_counts':dict(sorted(years.items())),'TC_matched_schedule':sum(r['fid'] in sched for r in hist),'test_n':len(test),'median_min_prior_effective':round(float(np.median([min(r['source_features']['TC']['effective']) for r in test])),3)}
# Use same archived Saudi FT cohort only; no new trading rule.
q=[r for r in read('m8_performance_gap_recovery_20261115/requests.jsonl')] if False else load('m8_performance_gap_recovery_20261115/requests.jsonl')
out={'method':'Fixed model replay and coverage inventory; neutral history counterfactual only. No new forecast strategy or exclusion. Earlier TC archive kept separate from actual receipt sample. No API call; last observed quota not current status.','coverage':coverage,'saudi':d,'last_quota_observation':q[-1]['remaining'],'last_quota_observed_utc':q[-1]['received_utc'],'new_independent_samples':0}
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':digest((P/m['historical_membership']['local_file']).read_bytes())==m['historical_membership']['sha256'],'inputs':all(digest((P/k).read_bytes())==v for k,v in m['input_sha256'].items()),'scripts':all(digest((P/k).read_bytes())==v for k,v in m['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_coverage_saudi_audit_20261115.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
print('COVERAGE',json.dumps(coverage,ensure_ascii=False),flush=True)
print('SAUDI',json.dumps(d,ensure_ascii=False),flush=True)
print('FOUNDATION',out['foundation'],flush=True)
