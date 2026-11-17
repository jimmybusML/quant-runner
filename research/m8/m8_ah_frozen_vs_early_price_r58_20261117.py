import json,collections,hashlib
import numpy as np
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
source=(P/'m8_received_price_chain_r57_20261117.py').read_text()
exec(source[:source.index("out={'research_id'")])
member={r['fid']:r for r in map(json.loads,(P/'m8_foundation_20261115/historical_membership.jsonl').open())}
t1={}
for file in ('m8_late_full_path_water_features_20261114.jsonl',
'm8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
 for r in map(json.loads,(P/file).open()):
  assert r['fid'] not in t1
  t1[r['fid']]=r
assert len(t1)==44956 and len(member)==10294
def stats(z):
 if not z:return {'n':0}
 z=np.asarray(z,float)
 return {'n':len(z),'U':round(float(z.sum()),3),'ROI':round(100*float(z.mean()),3)}
cohorts=collections.defaultdict(list)
qc=collections.Counter()
for i,(a,b,pre,later) in enumerate(chosen):
 f=b['fid']
 if f not in member:continue
 m=member[f];q=t1[f]
 cand=[side for side,price in [('home',q['end_home_U']),('away',q['end_away_U'])] if abs(float(price)-m['pnl'])<1e-8]
 if len(cand)!=1:
  qc['ambiguous_side']+=1;continue
 side=cand[0]
 original_home=side=='home'
 early_home=bool(buy_home[i])
 # The original8 membership side was only knowable from later T1,
 # hence early matching is a descriptive backward overlap.
 data={'fid':f,'cohort':m['cohort'],'early_side_agrees':original_home==early_home,
  'early_prediction_side_pnl':float(base_pnl[i]),
  'frozen_T1_historically_retrieved_pnl':float(m['pnl']),
  'frozen_side_at_T12_lookahead_NONEXECUTABLE':float(b['home_U'] if original_home else b['away_U']),
  'actual_T1_received':False}
 if 'T1' in later:
  from research.m3.probabilities import settle_score
  v=later['T1']
  data['actual_T1_received']=True
  data['frozen_side_at_actual_T1_RECEIPT_counterfactual']=settle_score('AH',v['line'],side,b['hg'],b['ag'],
    v['home_odds'] if original_home else v['away_odds'])[1]
  data['early_side_at_actual_T1_RECEIPT_counterfactual']=settle_score('AH',v['line'],'home' if early_home else 'away',
    b['hg'],b['ag'],v['home_odds'] if early_home else v['away_odds'])[1]
  qc['matched_T1_actual']+=1
 qc['matched']=qc['matched']+1
 cohorts['all'].append(data)
 cohorts[m['cohort']].append(data)
for name,group in cohorts.items():
 # Keep ALL eight cohorts, even tiny samples; no sample-size reporting filter.
 z={
 'n':len(group),
 'early_matches_frozen_T1_side_n':sum(r['early_side_agrees'] for r in group),
 'early_matches_frozen_T1_side_pct':round(100*sum(r['early_side_agrees'] for r in group)/len(group),3),
 'price_model_early_side_at_T12':stats([r['early_prediction_side_pnl'] for r in group]),
 'frozen_T1_historical_postretrieved':stats([r['frozen_T1_historically_retrieved_pnl'] for r in group]),
 'frozen_T1_SIDE_PRICED_AT_T12_LOOKAHEAD':stats([r['frozen_side_at_T12_lookahead_NONEXECUTABLE'] for r in group]),
 'frozen_T1_side_at_real_T1_quote':stats([r['frozen_side_at_actual_T1_RECEIPT_counterfactual'] for r in group if r['actual_T1_received']]),
 'frozen_T1_side_at_T12_quote_when_T1_also_received_LOOKAHEAD':stats([r['frozen_side_at_T12_lookahead_NONEXECUTABLE'] for r in group if r['actual_T1_received']]),
 'early_price_side_at_T12_quote_when_T1_also_received':stats([r['early_prediction_side_pnl'] for r in group if r['actual_T1_received']]),
 'early_price_side_at_real_T1_quote':stats([r['early_side_at_actual_T1_RECEIPT_counterfactual'] for r in group if r['actual_T1_received']])}
 cohorts[name]=z
 print('COMPARE',name,z,flush=True)
out={'method':'R58 independent descriptive side alignment: infer frozen T1 side solely from historical settled original-eight membership and original T1 home/away exact payout; skip ambiguous same-settlement sides. Compare its later T1-only signal with R56 T12 price-chasing side. T1 side unavailable at T12; hindsight T12 payout of frozen side is explicitly NONEXECUTABLE. Real received T1 Crown quote is verified by R57 prefix, priced as counterfactual not formal TG fill. Matching the selected fixture set conditioned on frozen T1 membership is retrospective, not realtime eligibility or proof of an early side. No new strategy or gate.','qc':dict(qc),
 'cohorts':{k:v for k,v in cohorts.items() if isinstance(v,dict)},'foundation':{}}
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_ah_frozen_vs_early_price_r58_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
