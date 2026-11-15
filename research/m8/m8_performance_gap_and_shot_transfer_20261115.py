import json,datetime,collections,hashlib
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_early_joint_distribution_calibration_20261115.py').read_text()
exec(src[:src.index("out={'method'")])
target={r['fid']:r for r in rows if r['T']==12}
ep={r['fid']:r for r in map(json.loads,(P/'m8_espn_performance_confirmed_18leagues_20261115.jsonl').open())}
paths=['m8_performance_batch_probe_20261115.jsonl','m8_performance_cross_year_20261115/verified_new.jsonl','m8_performance_contiguous_20261115/verified_new.jsonl','m8_performance_gap_recovery_20261115/verified_new.jsonl']
tc={r['fid']:r for path in paths for r in map(json.loads,(P/path).open())}
assert len(tc)==409
before={r['fid'] for path in paths[:-1] for r in map(json.loads,(P/path).open())}
gaps={f for f,r in target.items() if r['league']=='25' and '2025-10-29'<=r['date']<='2026-02-01' and f not in before}
assert len(gaps)==9
out={'ESPN':len(ep),'TotalCorner':len(tc),'overlap':len(ep.keys()&tc.keys()),'unique_union':len(ep.keys()|tc.keys()),'gap_total':len(gaps),'gap_recovered':len(gaps&tc.keys()),'gap_remaining':sorted(gaps-tc.keys()),'new':len(tc.keys()-before),'coverage':{},'tests':{},'transfer':{}}
for lid in ('16','25'):
 a=[r for r in tc.values() if r['league']==lid]
 lo,hi=min(r['date'] for r in a),max(r['date'] for r in a)
 t={f for f,r in target.items() if r['league']==lid and lo<=r['date']<=hi}
 out['coverage'][lid]={'min':lo,'max':hi,'n':len(a),'T12_n':len(t),'covered':len(t&tc.keys())}
print('COVERAGE',json.dumps(out),flush=True)
def day(r):return datetime.date.fromisoformat(r['date']).toordinal()
# Source-specific trailing features: shared shot definitions only, no cross-source averaging.
def build(hist):
 hist=sorted(hist,key=lambda r:(r['date'],r['fid']));state={};j=0;features={}
 def get(k,t):
  a,b,last=state.get(k,(0.,0.,t));dec=2**(-(t-last)/180);return a*dec,b*dec
 def add(k,x,t):
  a,b=get(k,t);state[k]=(a+x,b+1,t)
 def avg(k,t,p):
  a,b=get(k,t);return (a+8*p)/(b+8)
 for r in hist:
  t=day(r)
  while j<len(hist) and day(hist[j])<=t-3:
   q=hist[j];tt=day(q);j+=1
   for role,op in [('h','a'),('a','h')]:
    team=(q['league'],q['home'] if role=='h' else q['away'])
    for m in ('shots','sot','g'):
     for direction,key in [('for',role),('against',op)]:add((team,direction,m),q[key+m],tt)
  v=[]
  for team in ((r['league'],r['home']),(r['league'],r['away'])):
   for direction in ('for','against'):
    sh,so,g=[avg((team,direction,k),t,p) for k,p in [('shots',12.),('sot',4.),('g',1.4)]]
    v.extend([sh,so,g,g/max(so,.01)])
  features[r['fid']]=v
 return features
E=list(ep.values());T=[]
for r in tc.values():
 if r['shot_on'] is None or r['shot_off'] is None:continue
 h,a=r['shot_on'];ho,ao=r['shot_off']
 T.append({**r,'year':int(r['date'][:4]),'hshots':h+ho,'ashots':a+ao,'hsot':h,'asot':a})
ef,tf=build(E),build(T)
def data(hist):
 z=[dict(target[r['fid']]) for r in hist];valid=[]
 for j in range(0,len(z),4000):
  v=z[j:j+4000];ol,al=vec(v,'ol'),vec(v,'al');op=vec(v,'ou')/(vec(v,'oo')+vec(v,'ou'));ap=vec(v,'aa')/(vec(v,'ah')+vec(v,'aa'))
  total,ok1,e1=solve(op,.0001,20.,lambda x:ou_share(x,ol));frac,ok2,e2=solve(ap,.00001,.99999,lambda x:ah_share(total,x,al))
  for i,r in enumerate(v):
   if ok1[i] and ok2[i] and e1[i]<1e-5 and e2[i]<1e-5:r['mh']=float(total[i]*frac[i]);r['ma']=float(total[i]*(1-frac[i]));valid.append(r)
 return valid
E=data(E);T=data(T)
def feat(r,F,kind):
 h,a=r['mh'],r['ma'];v=[1,np.log(h),np.log(a),np.log(h+a),np.log1p(r['age_ah']),np.log1p(r['age_ou']),r['al'],r['ol']]
 if kind=='shots':v+=F[r['fid']]
 return v
def pred(tr,te,F,kind):
 X=np.array([feat(r,ef,kind) for r in tr]);Xt=np.array([feat(r,F,kind) for r in te])
 total=goals_predict(X,vec(tr,'hg')+vec(tr,'ag'),np.log(vec(tr,'mh')+vec(tr,'ma')),Xt,np.log(vec(te,'mh')+vec(te,'ma')))
 w,l=ou_wl(total,vec(te,'ol'));eo=w*(vec(te,'oo')-1)-l;eu=l*(vec(te,'ou')-1)-w
 v=np.where(eo>=eu,vec(te,'over_U'),vec(te,'under_U'));return {'all':stat(v),'goal_MAE':round(float(np.abs(total-vec(te,'hg')-vec(te,'ag')).mean()),6)}
for y in (2024,2025,2026):
 tr=[r for r in E if r['year']<y and r['league'] in ('1','14')]
 te=[r for r in E if r['year']==y and r['league'] in ('1','14')]
 out['tests'][str(y)]={k:pred(tr,te,ef,k) for k in ('market','shots')}
 print('ESPN',y,out['tests'][str(y)],flush=True)
# no training on TC matches, use preceding years of ESPN, only distinct IDs from leagues other than training leagues.
for y in sorted({r['year'] for r in T}):
 tr=[r for r in E if r['year']<y and r['league'] in ('1','14')]
 te=[r for r in T if r['year']==y and r['league'] not in ('1','14')]
 if not tr or not te:continue
 out['transfer'][str(y)]={'train_n':len(tr),**{k:pred(tr,te,tf,k) for k in ('market','shots')}}
 print('TRANSFER',y,out['transfer'][str(y)],flush=True)
m=json.load((P/'m8_foundation_20261115/manifest.json').open());out['foundation']={'membership':hashlib.sha256((P/m['historical_membership']['local_file']).read_bytes()).hexdigest()==m['historical_membership']['sha256'],'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['input_sha256'].items()),'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['script_sha256'].items())}
(P/'m8_performance_gap_and_shot_transfer_20261115.json').write_text(json.dumps(out,indent=2))
print('OUTPUT',json.dumps(out),flush=True)
