import json,collections,math
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=[json.loads(l) for l in (P/'m8_same_line_probability_path_20261114.jsonl').open()]
def era(r):return '2019-23' if r['year']<=2023 else '2024-25' if r['year']<=2025 else '2026'
def sign(x):return 1 if x>1e-9 else -1 if x<-1e-9 else 0
def stat(z,field='pnl'):
 v=[r[field] for r in z];n=len(v);u=sum(v);return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
def periods(z,field='pnl'):
 return {p:stat([r for r in z if era(r)==p],field) for p in ('2019-23','2024-25','2026')}|{'2026_H1':stat([r for r in z if r['year']==2026 and r['month']<='2026-06'],field),'2026_H2':stat([r for r in z if r['year']==2026 and r['month']>='2026-07'],field)}
groups=collections.defaultdict(list)
for r in rows:
 a,b=sign(r['p3']-r['p0']),sign(r['p1']-r['p3']);net=sign(r['p1']-r['p0'])
 if not r['n_price_moves']:shape='no_move'
 elif not r['up_moves'] or not r['down_moves']:shape='monotonic'
 elif not net:shape='return_to_start'
 else:shape='mixed'
 # Relative roles: when net flat, use first segment's direction; if flat, last segment's direction; last actual change if all endpoints flat
 s=net or a or b or sign(r['last_move'])
 final=sign(r['end_line'])
 favdir=-final
 if s:
  strength_side='home' if s>0 else 'away'
  r['strength_U']=r['end_'+strength_side+'_U']
  r['weak_U']=r['end_'+('away' if s>0 else 'home')+'_U']
  regime=f'{a*s},{b*s}'
  role='zero' if not final else 'fav' if s==favdir else 'dog'
  groups[('shape',shape,role)].append(r)
  groups[('phases',regime,role)].append(r)
  # final vs time average, relative market strengthening/weakening
  groups[('relative_mean',str(sign((r['p1']-r['pmean'])*s)),role)].append(r)
  groups[('shape_phases',shape,regime,role)].append(r)
 else:groups[('no_direction',shape,'zero' if not final else 'nonzero')].append(r)
 r['shape']=shape
 r['net']=net
 r['phase1']=a;r['phase2']=b
 r['reference_side']=s
 r['role']=None if not s else role
result={'scope':'Same AH handicap throughout T6 to T1; normalized implied side share = away odds / sum both odds, not true win probability; all source events up to T1; no production rule.','coverage':{p:len([r for r in rows if era(r)==p]) for p in ('2019-23','2024-25','2026')},'groups':{}}
for key,z in sorted(groups.items()):
 fields=('end_home_U','end_away_U') if key[0]=='no_direction' else ('strength_U','weak_U')
 ans={f:periods(z,f) for f in fields};result['groups']['|'.join(key)]=ans
 for f,a in ans.items():
  if all(a[p]['ROI'] is not None and a[p]['ROI']>0 for p in ('2019-23','2024-25','2026')):
   print('POSITIVE','|'.join(key),f,a,flush=True)
 if key[0]=='shape': print('SHAPE','|'.join(key), {f:a['2026'] for f,a in ans.items()},flush=True)
# A genuinely chronological regression comparison (older years fit; subsequent years report). All matches, two predicted settlement returns.
def feat(r):
 p0,p3,p1,mean,low,high,sd=[r[k] for k in ('p0','p3','p1','pmean','pmin','pmax','pstd')]
 d1=p3-p0;d2=p1-p3;move=p1-p0;vr=r['variation'];l=r['end_line'];lh=r['home_price'];la=r['away_price']
 return [1,l,abs(l),p0,p1,mean,d1,d2,move,high-low,p1-mean,p1-low,high-p1,sd,vr,math.log1p(r['n_price_moves']),r['last_move'],r['up_moves']/(1+r['n_price_moves']),lh,la,move*l,d2*l,move*abs(l),(p1-mean)*l,move**2,d1*d2,(p1-.5)*move, math.sin((int(r['month'][-2:])-1)*math.pi/6),math.cos((int(r['month'][-2:])-1)*math.pi/6)]
train=[r for r in rows if r['year']<=2023];valid=[r for r in rows if 2024<=r['year']<=2025];test=[r for r in rows if r['year']==2026]
def model(with_league):
 def f(r):
  a=feat(r)
  if with_league:a.extend(float(r['league']==x) for x in leagues)
  return a
 leagues=sorted(set(r['league'] for r in train))
 x=np.asarray([f(r) for r in train]);y=np.array([[r['end_home_U'],r['end_away_U']] for r in train])
 mu=x.mean(0);std=x.std(0);mu[0]=0;std[0]=1;std[std<1e-10]=1
 x=(x-mu)/std;reg=np.eye(x.shape[1])*100;reg[0,0]=0
 coef=np.linalg.solve(x.T@x+reg,x.T@y)
 out={}
 for label,z in [('2019-23',train),('2024-25',valid),('2026',test)]:
  pr=((np.asarray([f(r) for r in z])-mu)/std)@coef
  pnl=np.where(pr[:,0]>=pr[:,1], [r['end_home_U'] for r in z],[r['end_away_U'] for r in z]);est=pr.max(axis=1)
  a=[{**r,'pnl':float(v)} for r,v in zip(z,pnl)];rank=np.argsort(-est)
  total=stat(a)
  # descriptive ranking experiments, not rules
  total['top_ranked_experiments']={str(q):stat([a[i] for i in rank[:int(len(z)*q)]]) for q in (.1,.25,.5)}
  total['positive_estimate_research']=stat([a[i] for i in range(len(a)) if est[i]>0])
  total['nonzero_only']=stat([r for r in a if not r['end_zero']])
  out[label]=total
 print('MODEL',with_league,out,flush=True)
 return out
result['model_price_path']=model(False)
result['model_price_path_league']=model(True)
result['team_id_coverage']={'nonempty_both':sum(bool(r['home_team'] and r['away_team']) for r in rows),'total':len(rows)}
print('COVERAGE',result['coverage'],result['team_id_coverage'])
(P/'m8_same_line_probability_research_20261114.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
