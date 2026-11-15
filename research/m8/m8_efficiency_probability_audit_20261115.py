import json,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_efficiency_model_agreement_20261115.py').read_text()
exec(s[:s.rindex("out={'method'")])
def corr(a,b):
 return round(float(np.corrcoef(a,b)[0,1]),6)
def probstats(te,total):
 y=vec(te,'hg')+vec(te,'ag');line=vec(te,'ol')
 c=pmf(total).cumsum(axis=1)
 # Equal weight for two half-lines, including push as its own outcome.
 bs=[];ls=[];bias=[]
 for q in halves(line):
  w=1-cdf_at(c,np.floor(q)[:,None])[:,0];l=cdf_at(c,(np.ceil(q)-1)[:,None])[:,0];p=np.maximum(0,1-w-l)
  obs=np.column_stack([y>q,y==q,y<q]);pr=np.column_stack([w,p,l])
  assert np.allclose(pr.sum(1),1)
  bs.append(np.sum((pr-obs)**2,axis=1));ls.append(-np.log(np.maximum((pr*obs).sum(1),1e-15)));bias.append(w-(y>q))
 ret={'n':len(te),'line_brier':round(float(np.mean(bs)),6),'line_logloss':round(float(np.mean(ls)),6),'over_bias':round(float(np.mean(bias)),6),'mean_goal_bias':round(float(np.mean(total-y)),6)}
 for q in (1.5,2.5,3.5):
  w=1-cdf_at(c,np.full((len(y),1),int(q)))[:,0];o=y>q
  ret[str(q)]={'brier':round(float(np.mean((w-o)**2)),6),'pred':round(float(w.mean()),6),'actual':round(float(o.mean()),6)}
 return ret
def assess_corr(te,ps):
 y=vec(te,'hg')+vec(te,'ag');market=vec(te,'mh')+vec(te,'ma')
 pairs={}
 for i,a in enumerate(names):
  for b in names[i+1:]:
   x=ps[a][0];v=ps[b][0]
   pairs[a+'|'+b]={'residual_corr':corr(x-y,v-y),'market_correction_corr':corr(x-market,v-market),'mean_abs_goal_diff':round(float(np.mean(abs(x-v))),6),'side_agreement':round(float(np.mean(ps[a][1]==ps[b][1])),6)}
 return pairs
out={'method':'Predictive diagnostic only: existing T12 fixtures, identical previously tested forecasts, multiclass Brier and log loss averaged across Asian half-lines including pushes; fixed total thresholds and correlation of residuals and market-relative goal corrections. No model selection or policy change.','years':{}}
allte=[]; pooled={}
old=json.loads((P/'m8_efficiency_model_agreement_20261115.json').read_text())
for y in (2024,2025,2026):
 te=[r for r in z if r['year']==y];tr=[r for r in z if r['year']<y]
 ps={'market':make_pred(te,vec(te,'mh')+vec(te,'ma')),'annual_legacy':fit(tr,te,'shared')}
 for k in names:ps[k]=predict(y,te,variants[k])[0]
 ps['mean_goals']=make_pred(te,np.mean([ps[k][0] for k in names],axis=0))
 for k in ('annual_legacy',*names,'mean_goals'):assert stat(ps[k][2])['U']==old['years'][str(y)]['all'][k]['U']
 rec={'metrics':{k:probstats(te,p[0]) for k,p in ps.items()},'correlation':assess_corr(te,ps)}
 out['years'][str(y)]=rec
 print('YEAR',y,json.dumps(rec),flush=True)
 allte+=te
 for k,p in ps.items():pooled.setdefault(k,[]).append(p)
pooled={k:tuple(np.concatenate([p[j] for p in v]) for j in range(3)) for k,v in pooled.items()}
out['all']={'metrics':{k:probstats(allte,p[0]) for k,p in pooled.items()},'correlation':assess_corr(allte,pooled)}
# Archive inventory only: receipt candidates do not prove availability of pregame performance.
confirmed={r['fid']:r for r in ep.values()}
candidate={r['record']['fid'] for r in map(json.loads,(P/'m8_espn_additional_cache_candidates_20261115.jsonl').open())}
testids={r['fid'] for r in allte}
archive=list(map(json.loads,(P/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl').open()))
eligible={str(r['fixture_id']) for r in archive if r['received_minutes_to_kickoff']>=720 and 'OU' in r['markets'] and 'AH' in r['markets']}
out['archive_inventory']={'confirmed_ESPN':len(confirmed),'TC':len(tc),'union':len(set(confirmed)|set(tc)),'ESPN_unconfirmed_cached_candidates':len(candidate-set(confirmed)),'latest_ESPN_date':max(r['date'] for r in confirmed.values()),'latest_TC_date':max(r['date'] for r in tc.values()),'MR1_archived_rows':len(archive),'MR1_AH_OU_received_at_least_12h_unique':len(eligible),'same_id_in_test_sample':len(eligible&testids),'same_id_in_confirmed_ESPN':len(eligible&set(confirmed)),'same_id_in_TC':len(eligible&set(tc)),'notes':'Receipt archive is historical and from MR1, used only to inspect coverage; no model or order mixing. Same ID does not verify quote/feature equivalence. No fresh API.'}
print('ARCHIVE',out['archive_inventory'],flush=True)
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':hashlib.sha256((P/m['historical_membership']['local_file']).read_bytes()).hexdigest()==m['historical_membership']['sha256'],'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['input_sha256'].items()),'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_efficiency_probability_audit_20261115.json').write_text(json.dumps(out,indent=2))
print('ALL',json.dumps(out['all']),flush=True)
print('FOUNDATION',out['foundation'],flush=True)
