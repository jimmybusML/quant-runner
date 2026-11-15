import json,math,collections
from pathlib import Path
import numpy as np
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Same Crown AH/OU aligned data, now independently use OU as settlement target.
exec((P/'m8_score_market_divergence_full_AH_20261114.py').read_text().split('out={}\n')[0])
gids={(r['year'],r['fid']) for r in G[('shape_relation','reverted','agree')]}
prior_ids=set(prior)|gids
rows=[r for r in map(json.loads,(P/'m8_cross_market_aligned_20261114.jsonl').open()) if (r['year'],r['fid']) not in prior_ids]
assert len(rows)==len({(r['year'],r['fid']) for r in rows})
def season(r):return '2025' if r['year']==2025 else 'H1' if r['month']<='2026-06' else 'H2'
def met(v):
 n=len(v);u=float(sum(v));return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
groups=collections.defaultdict(list)
for r in rows:
 s=S[r['fid']];l=r['OU_l1'];o=r['OU_over_odds'];u=r['OU_under_odds']
 r['over_U']=settle_score('OU',l,'over',s['hg'],s['ag'],o)[1]
 r['under_U']=settle_score('OU',l,'under',s['hg'],s['ag'],u)[1]
 sc=lambda a,b: 'up' if a>b+1e-9 else 'down' if a<b-1e-9 else 'same'
 a=sc(r['OU_l3'],r['OU_l0']);b=sc(r['OU_l1'],r['OU_l3'])
 groups[('OU_line_path',a,b)].append(r)
 d=sc(r['OU_l1'],r['OU_l0'])
 if d=='same':d=sc(r['OU_p1'],r['OU_p0'])
 groups[('OU_net_direction',d)].append(r)
def feat(r,kind):
 s=S[r['fid']];l0,l3,l1=[r['OU_l'+k] for k in ('0','3','1')];p0,p3,p1=[r['OU_p'+k] for k in ('0','3','1')]
 f=[1,l0,l3,l1,l1-l0,l3-l0,l1-l3,p0,p3,p1,p1-p0,p3-p0,p1-p3,r['OU_over_odds'],r['OU_under_odds'],(l1-l0)*(p1-p0)]
 if kind!='OU':
  h0,h1=r['start_line'],r['end_line'];a0,a3,a1=[r['AH_p'+k] for k in ('0','3','1')]
  f.extend([h0,h1,abs(h1),h1-h0,a0,a3,a1,a1-a0,a3-a0,a1-a3,(a1-a0)*h1,r['home_price'],r['away_price'],r['line_range'],math.log1p(r['n_line_changes']),math.log1p(r['n_events']),r['end_zero'],(abs(h1)-abs(h0))*(l1-l0)])
 if kind=='OU_AH_score':
  h,a=s['lambda_home_0.025'],s['lambda_away_0.025'];h2,a2=s['lambda_home_0.06'],s['lambda_away_0.06']
  f.extend([h+a,h-a,h2+a2,h2-a2,h+a-l1,(h+a-l1)*(l1-l0),math.log1p(s['history_home_n']),math.log1p(s['history_away_n'])])
 return f
def fit(tr,te,k):
 x=np.array([feat(r,k) for r in tr]);y=np.array([[r['over_U'],r['under_U']] for r in tr])
 mu=x.mean(0);sd=x.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1;x=(x-mu)/sd;reg=np.eye(x.shape[1])*100;reg[0,0]=0
 beta=np.linalg.solve(x.T@x+reg,x.T@y);p=((np.array([feat(r,k) for r in te])-mu)/sd)@beta
 v=np.where(p[:,0]>=p[:,1],[r['over_U'] for r in te],[r['under_U'] for r in te])
 return {'all':met(v),'positive_estimate_comparison':met(v[p.max(1)>0])}
out={'source':'Crown T1 OU, exact eight prior AH research cohort fixtures excluded for distinct opportunity analysis; same joint coverage limited to late 2025 and 2026. Research target separate from AH; not new production or mixing OU identity.','coverage':dict(collections.Counter(season(r) for r in rows)),'models':{},'all_groups':{}}
for target in ('H1','H2'):
 tr=[r for r in rows if season(r)=='2025' or (target=='H2' and season(r)=='H1')];te=[r for r in rows if season(r)==target]
 out['models'][target]={'n_train':len(tr),'all_over':met([r['over_U'] for r in te]),'all_under':met([r['under_U'] for r in te])}|{k:fit(tr,te,k) for k in ('OU','OU_AH','OU_AH_score')}
 print('OU_MODEL',target,out['models'][target],flush=True)
for k,z in sorted(groups.items()):
 res={side:{per:met([r[side] for r in z if season(r)==per]) for per in ('2025','H1','H2')} for side in ('over_U','under_U')}
 out['all_groups']['|'.join(k)]=res
 if any(all(x[p]['ROI'] is not None and x[p]['ROI']>0 for p in ('2025','H1','H2')) for x in res.values()):print('OU_HISTORICAL_POSITIVE',k,res,flush=True)
print('OU_COVERAGE',out['coverage'],flush=True)
(P/'m8_distinct_OU_market_opportunity_20261115.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
