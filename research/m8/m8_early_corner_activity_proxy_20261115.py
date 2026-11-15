import json,math,collections,datetime,hashlib
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Exact existing T12 market dataset and validated pricing helpers.
s=(P/'m8_early_joint_distribution_calibration_20261115.py').read_text()
exec(s[:s.index("out={'method'")])
# Read the previously defined archived source population; avoid changing existing files.
p=(P/'m8_early_exact_cross_market_consistency_20261115.py').read_text()
exec(p[:p.index('C=collections.Counter();rows=[]')])
archive=[]
for f,(file,sha,lid) in jobs.items():
 try:
  raw=file.read_bytes()
  if sha and hashlib.sha256(raw).hexdigest()!=sha:continue
  x=next(q for q in json.loads(raw)['data'] if str(q['id'])==f)
  if str(x['l_id'])!=str(lid) or x.get('status')!='full':continue
  h,a=str(x['h_id']),str(x['a_id']);k=dt(x['start'])
  ch,ca,chh,cah=map(int,[x['hc'],x['ac'],x['hf_hc'],x['hf_ac']])
  if not h or not a or min(ch,ca,chh,cah)<0 or ch+ca==0 or chh>ch or cah>ca:continue
  archive.append((k.date().toordinal(),f,str(lid),h,a,ch,ca,chh,cah))
 except Exception:continue
archive.sort()
# Prior matches only: use score-independent corner counts as the activity proxy; no current-match corners.
# Shrunk decayed averages, opponent-adjusted via league role means. Parameters are research-only.
state={};baseline={};features={}
def get(k,t,D=state):
 a,b,last=D.get(k,(0.,0.,t));dec=2**(-(t-last)/180);return a*dec,b*dec
def add(k,v,t,D=state):
 a,b=get(k,t,D);D[k]=(a+v,b+1,t)
def mean(k,t,prior=0,shrink=8,D=state):
 a,b=get(k,t,D);return (a+shrink*prior)/(b+shrink)
j=0;z=sorted([r for r in rows if r['T']==12],key=lambda r:(r['date'],r['fid']))
for r in z:
 t=datetime.date.fromisoformat(r['date']).toordinal()
 while j<len(archive) and archive[j][0]<=t-3:
  tt,f,l,h,a,ch,ca,chh,cah=archive[j];j+=1
  bh=mean((l,'home'),tt,5,20,baseline);ba=mean((l,'away'),tt,4.5,20,baseline)
  for key,val in [((l,h,'for'),ch-bh),((l,h,'against'),ca-ba),((l,a,'for'),ca-ba),((l,a,'against'),ch-bh),((l,h,'home_for'),ch-bh),((l,a,'away_for'),ca-ba),((l,h,'ht_for'),chh-bh/2),((l,a,'ht_for'),cah-ba/2)]:add(key,val,tt)
  add((l,'home'),ch,tt,baseline);add((l,'away'),ca,tt,baseline)
 l,h,a=r['league'],r['home_id'],r['away_id']
 features[r['fid']]=[mean((l,team,k),t) for team in (h,a) for k in ('for','against','home_for','away_for','ht_for')]
print('CORNER_HISTORY',len(archive),'T12',len(z),flush=True)
valid=[]
for st in range(0,len(z),4000):
 v=z[st:st+4000];ol,al=vec(v,'ol'),vec(v,'al');op=vec(v,'ou')/(vec(v,'oo')+vec(v,'ou'));ap=vec(v,'aa')/(vec(v,'ah')+vec(v,'aa'))
 total,ok1,e1=solve(op,.0001,20.,lambda x:ou_share(x,ol));frac,ok2,e2=solve(ap,.00001,.99999,lambda x:ah_share(total,x,al))
 for i,r in enumerate(v):
  if ok1[i] and ok2[i] and e1[i]<1e-5 and e2[i]<1e-5:r['mh']=float(total[i]*frac[i]);r['ma']=float(total[i]*(1-frac[i]));valid.append(r)
def feat(r,kind):
 h,a=r['mh'],r['ma'];x=[1,np.log(h),np.log(a),np.log(h+a),np.log1p(r['age_ah']),np.log1p(r['age_ou']),r['al'],r['ol']]
 if kind=='market_corner':x+=features[r['fid']]
 return x
out={'source_corner_history':len(archive),'T12_n':len(valid),'historical_availability_proxy':'three prior UTC dates; backfilled historic stats, not observed receipt','years':{}}
for y in (2024,2025,2026):
 tr=[r for r in valid if r['year']<y];te=[r for r in valid if r['year']==y];res={}
 for kind in ('market','market_corner'):
  X=np.array([feat(r,kind) for r in tr]);Xt=np.array([feat(r,kind) for r in te])
  h=goals_predict(X,vec(tr,'hg'),np.log(vec(tr,'mh')),Xt,np.log(vec(te,'mh')))
  a=goals_predict(X,vec(tr,'ag'),np.log(vec(tr,'ma')),Xt,np.log(vec(te,'ma')))
  res[kind]=evaluate(te,h,a)
 out['years'][str(y)]=res;print('YEAR',y,json.dumps(res),flush=True)
(R/'m8_early_corner_activity_proxy_20261115.json').write_text(json.dumps(out,indent=2))
