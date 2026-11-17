import json,collections,hashlib,datetime
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_ah_transfer_independent_deepdive_20261117.py').read_text()
exec(s[:s.index("out={'research_id'")])
def recalc(mode):
 X=model_features[mode](hist,HF)
 outcome=np.zeros(len(H));decision=np.zeros(len(H),int)
 cv={}
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind&hv;te=(HY==yr)&hv
  mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
  pen=np.eye(X.shape[1])*100;pen[0,0]=0
  beta=np.linalg.solve(((X[tr]-mu)/sd).T@((X[tr]-mu)/sd)+pen,((X[tr]-mu)/sd).T@(ha[tr]-aa[tr]))
  decision[te]=((((X[te]-mu)/sd)@beta)>=0).astype(int)
  cv[str(yr)]={'coefficients':beta.tolist(),'train_n':int(tr.sum())}
 outcome=np.where(decision==1,ha,aa)
 return decision,outcome,cv
bm,bp,_=recalc('market_path')
variants={}
for mode in ('market_8_count','market_4_diff','market_90_365d_net'):
 choice,pnl,coefs=recalc(mode)
 variants[mode]=(choice,pnl,coefs)
rng=np.random.default_rng(51)
def day_ci(ids, values, repeats=2000):
 # Cluster by fixture calendar date, so same day's multi-match dependence
 # is not mistaken for independent, i.i.d. match outcomes.
 b=collections.defaultdict(list)
 for i in ids:b[H[i]['date']].append(float(values[i]))
 if not b:return {'n':0}
 totals=np.array([sum(x) for x in b.values()])
 lengths=np.array([len(x) for x in b.values()])
 k=len(totals)
 draws=rng.integers(k,size=(repeats,k))
 sim=100*(totals[draws].sum(axis=1)/lengths[draws].sum(axis=1))
 return {'n':len(ids),'n_days':k,'roi':round(100*totals.sum()/lengths.sum(),4),'bootstrap95':[round(float(a),4) for a in np.quantile(sim,[.025,.975])],'bootstrap2000_draws_seed':51}
masks={
 'all_AH_eligible':(HY>=2024)&(HY<=2026)&hv,
 'outside_original_eight':(HY>=2024)&(HY<=2026)&hv&foundation,
 'previous_narrow_with_OU_exclusions':(HY>=2024)&(HY<=2026)&hv&foundation&other,
}
output={'method':'R51 AH-only same-fixture reliability: two candidate directions compared to prior-year Crown path baseline; no OU strategy requirement. Profit uncertainty via 2000 resamples of whole UTC date clusters (not independent matches). Stats and diagnostic partitions are post-hoc descriptions only, not trading conditions. Do not select profitable league/month in production. Historical after-the-fact market quote and Transfermarkt backfilled effective dates, actual prospective 0.','groups':{},'models':{}}
for scope,m in masks.items():
 ids=np.flatnonzero(m)
 g={'n':len(ids),'history_price_baseline':day_ci(ids,bp),'variants':{},'years':{},'leagues':{}}
 for year in ('2024','2025','2026'):
  sub=np.array([i for i in ids if HY[i]==int(year)],int)
  g['years'][year]={'n':len(sub),'price_baseline':day_ci(sub,bp),'variants':{}}
 for mode,(decision,pnl,coef) in variants.items():
  changed=decision!=bm;delta=pnl-bp
  z={'standalone':day_ci(ids,pnl),'paired_delta':day_ci(ids,delta),
     'changed_n':int((m&changed).sum()),'changed_share':round(100*float((m&changed).sum())/len(ids),3),
     'changed_pnl_baseline':round(float(bp[m&changed].sum()),3),'changed_pnl_variant':round(float(pnl[m&changed].sum()),3),
     'same_pnl':round(float(pnl[m&~changed].sum()),3),
     'coefficients':coef}
  g['variants'][mode]=z
  for yr in ('2024','2025','2026'):
   sub=np.array([i for i in ids if HY[i]==int(yr)],int)
   zz={'standalone':day_ci(sub,pnl),'paired_delta':day_ci(sub,delta),'changed_n':int(changed[sub].sum()),
       'changed_delta_units':round(float(delta[sub].sum()),3),'pnl_units':round(float(pnl[sub].sum()),3)}
   g['years'][yr]['variants'][mode]=zz
 output['groups'][scope]=g
 print('COHORT',scope,len(ids),'market',g['history_price_baseline'],'models',
       {x:{'standalone':v['standalone'],'paired_delta':v['paired_delta'],'changed_n':v['changed_n']} for x,v in g['variants'].items()},flush=True)
 print('YEAR',scope,[(yr,{mode:{'pnl':z['pnl_units'],'delta':z['changed_delta_units'],'ci':z['standalone']['bootstrap95'],'changed':z['changed_n']} for mode,z in r['variants'].items()}) for yr,r in g['years'].items()],flush=True)
# Fixed 2019-2025 training and 2026 held-out path are the same
# prior-year fit already done above. No hyperparameter selection on 2026.
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
output['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(output['foundation'].values())
(P/'m8_ah_transfer_reliability_20261117.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
