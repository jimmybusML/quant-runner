import json,math,datetime,collections
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_joint_distribution_calibration_20261115.py').read_text()
exec(s[:s.index('out={')]) if False else exec(s[:s.index("out={'method'")])
# Independent past score-only matches, including earlier raw-verified score inventory.
S={}
for r in map(json.loads,(P/'m8_independent_score_strength_20261114.jsonl').open()):
 S[r['fid']]={'fid':r['fid'],'date':r['date'],'league':str(r['league']),'home':r['home'],'away':r['away'],'hg':r['hg'],'ag':r['ag']}
old_count=len(S);conflicts=0
for r in rows:
 q={'fid':r['fid'],'date':r['date'],'league':r['league'],'home':r['home_id'],'away':r['away_id'],'hg':r['hg'],'ag':r['ag']}
 if q['fid'] in S and S[q['fid']]!=q:
  conflicts+=1
  # keep previously checked original record; exclude conflicting ID from both score source and study.
  S[q['fid']]=None
 elif q['fid'] not in S:S[q['fid']]=q
bad={f for f,r in S.items() if r is None}
S=[r for r in S.values() if r and r['home'] and r['away']]
def day(r):return datetime.date.fromisoformat(r['date']).toordinal()
S.sort(key=lambda r:(r['date'],r['fid']))
print('SCORE_HISTORY',old_count,len(S),'conflicting IDs',len(bad),flush=True)
# Score-only online opponent-adjusted form, separate venue residual, decayed when elapsed days.
class Rating:
 def __init__(self):
  self.a={};self.d={};self.v={};self.b={};self.n=collections.Counter()
 def get(self,D,key,t,half=180):
  value,last=D.get(key,(0.,t));return value*2**(-(t-last)/half)
 def pred(self,r,t):
  h=(r['league'],r['home']);a=(r['league'],r['away']);b=self.b.get(r['league'],[math.log(1.45),math.log(1.15)])
  vh=self.get(self.v,(h,'h'),t);va=self.get(self.v,(a,'a'),t)
  x=b[0]+self.get(self.a,h,t)+self.get(self.d,a,t)+vh
  y=b[1]+self.get(self.a,a,t)+self.get(self.d,h,t)+va
  return math.exp(max(-2.5,min(2.3,x))),math.exp(max(-2.5,min(2.3,y)))
 def upd(self,r):
  t=day(r);h=(r['league'],r['home']);a=(r['league'],r['away']);x,y=self.pred(r,t)
  e1=max(-4,min(4,r['hg']-x));e2=max(-4,min(4,r['ag']-y))
  for D,key,e,lr in [(self.a,h,e1,.035),(self.a,a,e2,.035),(self.d,a,e1,.035),(self.d,h,e2,.035),(self.v,(h,'h'),e1,.015),(self.v,(a,'a'),e2,.015)]:
   D[key]=(self.get(D,key,t)+lr*e,t)
  b=self.b.setdefault(r['league'],[math.log(1.45),math.log(1.15)]);b[0]+=.003*e1;b[1]+=.003*e2;self.n[h]+=1;self.n[a]+=1
 def feat(self,r,t):
  q={'league':r['league'],'home':r['home_id'],'away':r['away_id']};h,a=self.pred(q,t)
  return [math.log(h),math.log(a),math.log1p(self.n[(q['league'],q['home'])]),math.log1p(self.n[(q['league'],q['away'])])]
rat=Rating();i=0;features={}
# Prior dates at least 3 UTC calendar days earlier: conservative score-availability proxy across all early horizons, not proof of actual receipts.
for r in sorted({r['fid']:r for r in rows if r['fid'] not in bad}.values(),key=lambda r:(r['date'],r['fid'])):
 t=day(r)
 while i<len(S) and day(S[i])<=t-3:rat.upd(S[i]);i+=1
 if r['home_id'] and r['away_id']:features[r['fid']]=rat.feat(r,t)
def market_resid(z):
 # Lagged team deviations from same-horizon market implied goal rates; no current result in features.
 state={};j=0;ordered=sorted(z,key=lambda r:(r['date'],r['fid']))
 def get(key,t):
  a,b,last=state.get(key,(0.,0.,t));dec=2**(-(t-last)/120);return a*dec,b*dec
 def add(key,e,t):
  a,b=get(key,t);state[key]=(a+max(-4,min(4,e)),b+1,t)
 def keys(r):
  h=(r['league'],r['home_id']);a=(r['league'],r['away_id'])
  return [(h,'attack'),(a,'defense'),(h,'home_attack'),(a,'away_defense'),(a,'attack'),(h,'defense'),(a,'away_attack'),(h,'home_defense')]
 for r in ordered:
  t=day(r)
  while j<len(ordered) and day(ordered[j])<=t-3:
   q=ordered[j];tt=day(q);e1=q['hg']-q['mh'];e2=q['ag']-q['ma']
   for k in keys(q)[:4]:add(k,e1,tt)
   for k in keys(q)[4:]:add(k,e2,tt)
   j+=1
  vals=[get(k,t) for k in keys(r)]
  r['resid']=[a/(b+8) for a,b in vals]
def ev_eval(z,h,a):
 total=h+a;frac=h/total;out={}
 for m,l,pa,pb,sa,sb in [('AH','al','ah','aa','home_U','away_U'),('OU','ol','oo','ou','over_U','under_U')]:
  w,ls=ah_wl(total,frac,vec(z,l)) if m=='AH' else ou_wl(total,vec(z,l))
  ea=w*(vec(z,pa)-1)-ls;eb=ls*(vec(z,pb)-1)-w
  v=np.where(ea>=eb,vec(z,sa),vec(z,sb));mx=np.maximum(ea,eb)
  out[m]={'all':stat(v),'positive_estimate_diagnostic':stat(v[mx>1e-9])}
 out['NLL_no_factorial']=round(float(np.mean(h-vec(z,'hg')*np.log(h)+a-vec(z,'ag')*np.log(a))),6)
 return out
out={'score_history_n':len(S),'previous_score_history_n':old_count,'conflict_IDs':len(bad),'availability_proxy':'prior >=3 UTC calendar dates, no actual receipt guarantee','horizons':{}}
for T in (24,12,6):
 z=[r for r in rows if r['T']==T and r['fid'] in features];valid=[]
 for st in range(0,len(z),4000):
  v=z[st:st+4000];ol,al=vec(v,'ol'),vec(v,'al');op=vec(v,'ou')/(vec(v,'oo')+vec(v,'ou'));ap=vec(v,'aa')/(vec(v,'ah')+vec(v,'aa'))
  total,ok1,e1=solve(op,.0001,20.,lambda x:ou_share(x,ol));frac,ok2,e2=solve(ap,.00001,.99999,lambda x:ah_share(total,x,al))
  for j,r in enumerate(v):
   if ok1[j] and ok2[j] and e1[j]<1e-5 and e2[j]<1e-5:r['mh']=float(total[j]*frac[j]);r['ma']=float(total[j]*(1-frac[j]));valid.append(r)
 z=valid;market_resid(z)
 def feat(r,kind):
  h,a=r['mh'],r['ma'];x=[1,np.log(h),np.log(a),np.log(h+a),np.log1p(r['age_ah']),np.log1p(r['age_ou']),r['al'],r['ol']]
  if kind!='market':x+=features[r['fid']]
  if kind=='market_score_residual':x+=r['resid']
  return x
 rec={'n':len(z),'year_counts':dict(collections.Counter(r['year'] for r in z)),'years':{}}
 for y in (2024,2025,2026):
  tr=[r for r in z if r['year']<y];te=[r for r in z if r['year']==y];hh,aa=vec(te,'mh'),vec(te,'ma')
  f=np.array([features[r['fid']] for r in te])
  oo={'n':len(te),'score_only':ev_eval(te,np.exp(f[:,0]),np.exp(f[:,1]))}
  for kind in ('market','market_score','market_score_residual'):
   X=np.array([feat(r,kind) for r in tr]);Xt=np.array([feat(r,kind) for r in te])
   h=goals_predict(X,vec(tr,'hg'),np.log(vec(tr,'mh')),Xt,np.log(hh));a=goals_predict(X,vec(tr,'ag'),np.log(vec(tr,'ma')),Xt,np.log(aa))
   oo[kind]=ev_eval(te,h,a)
  rec['years'][str(y)]=oo;print('RESULT',T,y,json.dumps(oo),flush=True)
 out['horizons'][str(T)]=rec
(P/'m8_early_independent_team_market_residual_20261115.json').write_text(json.dumps(out,indent=2))
