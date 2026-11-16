import json,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_team_market_residual_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Mixed verified performance archive, prefer TC for duplicate fixture as in earlier research.
# Shot history only from preceding matches; zero deviation from prior if absent.
perf={**E,**history}
perf={k:v for k,v in perf.items() if k not in receiptids}
ii=histindex(perf)
si={}
for k,rr0 in ii.items():
 rr0=sorted(rr0,key=lambda v:v[0])
 si[k]=(np.array([x[0].toordinal() for x in rr0]),np.array([[x[2][:2],x[3][:2]] for x in rr0],float).reshape(-1,2,2))
def shots(q):
 F=[];N=[]
 for a in q:
  day=orddate(a['date']);vv=[];nn=[]
  for team in (a['home_id'],a['away_id']):
   dd,rr0=si.get((a['league'],team),(np.array([]),np.empty((0,2,2))))
   end=int(np.searchsorted(dd,day-3,side='right'));nn.append(end)
   ages=day-dd[:end];v=rr0[:end]
   h=[]
   for hl in (30,180):
    w=np.exp2(-ages/hl)
    h.append((np.einsum('i,ijk->jk',w,v)+8*np.array([[12.,4.],[12.,4.]]))/(8+w.sum()))
   vv.append(h)
  def combine(h):
   x,y=vv[0][h],vv[1][h]
   # Attack and opponent concessions, home-away difference and total.
   hp=(x[0]+y[1])/2;ap=(y[0]+x[1])/2
   return np.r_[hp+ap-np.array([24.,8.]),hp-ap]
  l=combine(1);sh=combine(0)
  F.append(np.r_[l,sh-l]);N.append(nn)
 return np.array(F),np.array(N)
hs,hsn=shots(H);rs,rsn=shots(R)
hc=hsn.min(1)>0;rc=rsn.min(1)>0
print('SHOT_COVERAGE',len(perf),int((hm&hc).sum()),int((rm&rc).sum()),flush=True)
out={'method':'R27 full R26 cohort; mix verified ESPN and normalized TC performance, dedup by FID TC priority, exclude receipt archive FIDs from fit and history; prior league/team shot and SOT attack/conceded 30/180 day features with same three UTC date lag and prior shrink8. Earlier-year score likelihood fits, fixed ridge100, compare R26 goal residual, separate shot features, joint. All fixtures retained including no history, matched subset descriptive only. Repeated retrospective samples, no independent forward validation.','coverage':{'history_n':int(hm.sum()),'receipt_n':int(rm.sum()),'perf_records_excluding_receipt':len(perf),'history_both_shot_prior':int((hm&hc).sum()),'receipt_both_shot_prior':int((rm&rc).sum())},'models':{}}
for mode in ('team','shots','team_shots'):
 def dx(x,r,s):
  a=make_x(x,'static')
  if mode=='team':return np.column_stack((a,r))
  if mode=='shots':return np.column_stack((a,s))
  return np.column_stack((a,r,s))
 X=dx(hx,hf0,hs);Z=dx(rx,rf0,rs);ht,hf=rates(hx);rt0,rf1=rates(rx)
 a,b,c,d=state(hx);ra,rb0,rc0,rd0=state(rx)
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind;te=HY==yr;re=RY==yr
  ht[te],_=fit_total(X[tr],hyn[tr],b[tr],X[te],b[te])
  hf[te],_=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],X[te],d[te])
  if re.any():
   rt0[re],_=fit_total(X[tr],hyn[tr],b[tr],Z[re],rb0[re]);rf1[re],_=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],Z[re],rd0[re])
 a={'history_probability':evaluate(H,ht,hf,hm),'receipt_probability':evaluate(R,rt0,rf1,rm),'markets':{}}
 for market in ('AH','OU'):
  p=pay(H,ht,hf,market);r=pay(R,rt0,rf1,market)
  a['markets'][market]={'history':score(H,p,hm),'receipt':score(R,r,rm),'history_matched':score(H,p,hm&hc),'receipt_matched':score(R,r,rm&rc),'history_disjoint_receipt':score(H,p,hm&history_ind),'years':{str(yr):score(H,p,hm&(HY==yr)) for yr in (2024,2025,2026)}}
 if mode=='team':
  old=json.loads((P/'m8_team_market_residual_research_20261116.json').read_text())['models']['team']
  for m0 in ('AH','OU'):
   for q0 in ('history','receipt'):assert a['markets'][m0][q0]['U']==old['markets'][m0][q0]['U']
 out['models'][mode]=a
 print(mode,{k:{j:slim(v[j]) for j in ('history','receipt','history_matched','receipt_matched')} | {'years':{y:slim(x) for y,x in v['years'].items()}} for k,v in a['markets'].items()},'prob',a['history_probability'],a['receipt_probability'],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_team_shot_residual_research_20261116.json').write_text(json.dumps(out,indent=2))
