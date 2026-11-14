import json,collections,math,datetime,statistics
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=[json.loads(l) for l in (P/'m8_cross_market_aligned_20261114.jsonl').open()]
assert len(rows)==9645
def s(x):return 'up' if x>1e-9 else 'down' if x<-1e-9 else 'flat'
def part(r):return '2025' if r['year']==2025 else '2026_H1' if r['month']<='2026-06' else '2026_H2'
def stats(z):
 n=len(z);v=sum(z);return {'n':n,'U':round(v,3),'ROI':round(100*v/n,3) if n else None}
def summarize(z,field):
 out={p:stats([r[field] for r in z if part(r)==p]) for p in ('2025','2026_H1','2026_H2')}
 out['2026']=stats([r[field] for r in z if r['year']==2026])
 return out
remaining=[r for r in rows if not r['prior']]
g=collections.defaultdict(list)
for r in remaining:
 if r['end_zero']:continue
 # For OU directional variation, line has precedence; if same line compare normalized over share.
 ou0,ou1=r['OU_l0'],r['OU_l1'];up0,up1=r['OU_p0'],r['OU_p1']
 ou=s(ou1-ou0) if ou1!=ou0 else s(up1-up0)
 ah0,ah1=r['start_line'],r['end_line'];ap0,ap1=r['AH_p0'],r['AH_p1'];favsign=-1 if ah1>0 else 1
 # AH direction judged relative to final favorite; same line price share changes only.
 ah=s((abs(ah1)-favsign*(-ah0))) if ah0!=ah1 else s((ap1-ap0)*favsign)
 # For fixed nonzero AH line across all five hours, separate pure odds interaction.
 if r['path_shape']=='never_changed':
  g[('fixed_AH',ah,ou)].append(r)
  ou_level='line_moved' if ou1!=ou0 else 'line_same'
  g[('fixed_AH_'+ou_level,ah,ou)].append(r)
 # simple joint partition of all remaining nonzero fixtures
 g[('all_nonzero',ah,ou)].append(r)
 # AH three-point path and OU line only (not a filter for production)
 g[('phase',r['path_6_3_1'],s(ou1-ou0))].append(r)
out={'coverage_remaining_by_month':dict(collections.Counter(r['month'] for r in remaining)),'global':{'AH_home':summarize(remaining,'end_home_U'),'AH_away':summarize(remaining,'end_away_U')},'groups':{},'models':{}}
for k,z in sorted(g.items()):
 res={side:summarize(z,side) for side in ('end_dog_U','end_fav_U')}
 out['groups']['|'.join(k)]=res
 if k[0]=='fixed_AH':
  print('FIXED',k,{side:{p:v[p] for p in ('2025','2026_H1','2026_H2','2026')} for side,v in res.items()},flush=True)
 for side,v in res.items():
  if all(v[p]['ROI'] is not None and v[p]['ROI']>0 for p in ('2025','2026_H1','2026_H2')):print('POSITIVE_ALL',k,side,v,flush=True)
# Fit only historical prior periods, use same matched dataset, compare features with/without OU/opening odds.
# Each model separately tests all available remaining matches; opening comparison uses same known-opening subset.
def feat(r,market):
 l0,l1=r['start_line'],r['end_line'];p0,p3,p1=r['AH_p0'],r['AH_p3'],r['AH_p1']
 f=[1,l0,l1,abs(l1),l1-l0,p0,p3,p1,p1-p0,p3-p0,p1-p3,(p1-p0)*l1,r['home_price'],r['away_price'],r['line_range'],math.log1p(r['n_line_changes']),math.log1p(r['n_events']),r['end_zero']]
 if market in ('AH_OU','AH_OU_open1X2'):
  u0,u3,u1=[r['OU_l'+h] for h in ('0','3','1')];o0,o3,o1=[r['OU_p'+h] for h in ('0','3','1')]
  f.extend([u0,u3,u1,u1-u0,u3-u0,u1-u3,o0,o3,o1,o1-o0,o3-o0,o1-o3,r['OU_over_odds'],r['OU_under_odds'],l1*u1,(l1-l0)*(u1-u0),(p1-p0)*(o1-o0),l1*(u1-u0),l1*(o1-o0)])
 if market=='AH_OU_open1X2':
  h,d,a=r['open_1x2'];f.extend([h,d,a,h-a,(h-a)*l1,(h-a)*(l1-l0),d*u1,d*(u1-u0)])
 return f
def evaluate(train,test,market):
 X=np.array([feat(r,market) for r in train],float);Y=np.array([[r['end_home_U'],r['end_away_U']] for r in train])
 mu=X.mean(axis=0);sd=X.std(axis=0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 X=(X-mu)/sd;reg=np.eye(X.shape[1])*100;reg[0,0]=0
 m=np.linalg.solve(X.T@X+reg,X.T@Y)
 p=((np.array([feat(r,market) for r in test])-mu)/sd)@m
 ret=np.where(p[:,0]>=p[:,1],[r['end_home_U'] for r in test],[r['end_away_U'] for r in test]);highest=p.max(axis=1)
 ans={'train_n':len(train),'all':stats(ret.tolist()),'positive_estimate_research':stats(ret[highest>0].tolist())}
 return ans
for name,universe,markets in [('all_joint',remaining,['AH','AH_OU']),('common_open_1X2',[r for r in remaining if r.get('open_1x2')],['AH','AH_OU','AH_OU_open1X2'])]:
 for target in ('2026_H1','2026_H2'):
  train=[r for r in universe if part(r)=='2025' or (target=='2026_H2' and part(r)=='2026_H1')]
  test=[r for r in universe if part(r)==target]
  out['models'][name+'|'+target]={m:evaluate(train,test,m) for m in markets}
  print('MODEL',name,target,out['models'][name+'|'+target],flush=True)
# A fixed same-handicap two-market partition; learn higher-return side on only 2025; test 2026 H1/H2.
selected=[]
for k,z in g.items():
 if k[0]!='fixed_AH':continue
 a=[r for r in z if r['year']==2025]
 if not a:continue
 side=max(('end_dog_U','end_fav_U'),key=lambda f:sum(r[f] for r in a))
 # Research diagnostic comparing group choice with training sign; not a trading requirement.
 avg=sum(r[side] for r in a)/len(a)
 selected.extend({**r,'pnl':r[side],'train_mean':avg} for r in z)
out['group_choice_all']=summarize(selected,'pnl')
out['group_choice_positive_training_comparison']=summarize([r for r in selected if r['train_mean']>0],'pnl')
print('PARTITION_FIT',out['group_choice_all'],out['group_choice_positive_training_comparison'],flush=True)
print('MONTHS',out['coverage_remaining_by_month'],flush=True)
(P/'m8_cross_market_research_20261114.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
