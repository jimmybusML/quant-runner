import json,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_team_market_residual_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Separate venue-specific team residuals from league-wide home-field residual.
# All features are derived from past matches only; exact same cohort and comparison.
# Inherit shrinkage8, 30/180-day half-life, 3-date lag, ridge100.
vi0=collections.defaultdict(list);li0=collections.defaultdict(list)
for q,x,ok in zip(H,hx,history_ind):
 if not ok:continue
 t,d=x[1],x[3];hr=q['hg']-(t+d)/2;ar=q['ag']-(t-d)/2
 day=orddate(q['date']);l=q['league']
 li0[l].append((day,q['fid'],hr,ar))
 for team,role,f,a in [(q['home_id'],'H',hr,ar),(q['away_id'],'A',ar,hr)]:
  if team:vi0[(l,team,role)].append((day,q['fid'],f,a))
def mkidx(kvs):
 return {k:(np.array([v[0] for v in sorted(rows)]),np.array([v[2:] for v in sorted(rows)])) for k,rows in kvs.items()}
vi=mkidx(vi0);li=mkidx(li0)
empty=(np.array([]),np.empty((0,2)))
def prior(index,key,day):
 dd,rr=index.get(key,empty);end=int(np.searchsorted(dd,day-3,side='right'))
 age=day-dd[:end];v=rr[:end];arr=[]
 for hl in (30,180):
  w=np.exp2(-age/hl);arr.append(w@v/(8+w.sum()))
 return np.asarray(arr),end
def combine(x,y):
 sh,lh=x;sa,la=y
 short=np.array([sh[0]+sa[1],sa[0]+sh[1]])
 long=np.array([lh[0]+la[1],la[0]+lh[1]])
 return np.array([long.sum(),long[0]-long[1],(short-long).sum(),(short[0]-short[1])-(long[0]-long[1])])
def features(q):
 f=[];lc=[];n=[]
 for a in q:
  day=orddate(a['date']);l=a['league']
  x,n1=prior(vi,(l,a['home_id'],'H'),day);y,n2=prior(vi,(l,a['away_id'],'A'),day)
  f.append(combine(x,y));n.append([n1,n2])
  z,_=prior(li,l,day);short,long=z
  lc.append([long.sum(),long[0]-long[1],(short-long).sum(),(short[0]-short[1])-(long[0]-long[1])])
 return np.array(f),np.array(lc),np.array(n)
hv0,hl0,hvn=features(H);rv0,rl0,rvn=features(R)
print('VENUE_COVERAGE',len(vi),len(li),int(((hvn.min(1)>0)&hm).sum()),int(((rvn.min(1)>0)&rm).sum()),flush=True)
out={'method':'R30 venue-specific team and league home-field market residuals; unaltered R26 test set; 3 UTC-date lag, 30/180 half-lives, shrink8 and ridge100 inherited. Compare pooled reference, venue-only, pooled plus venue-specific deviation, league-wide home/away calibration with pooled. Full forecast and settlement; no retrospective selection or rule changes; previously explored historical/receipt data, not independent forward.','coverage':{'history':int(hm.sum()),'receipt':int(rm.sum()),'venue_keys':len(vi),'leagues':len(li),'both_venue_history':int(((hvn.min(1)>0)&hm).sum()),'both_venue_receipt':int(((rvn.min(1)>0)&rm).sum())},'models':{}}
def dx(x,p,v,l,mode):
 base=make_x(x,'static')
 if mode=='pooled':return np.column_stack((base,p))
 if mode=='venue':return np.column_stack((base,v))
 if mode=='venue_delta':return np.column_stack((base,p,v-p))
 if mode=='league_home':return np.column_stack((base,p,l))
 raise ValueError(mode)
for mode in ('pooled','venue','venue_delta','league_home'):
 X=dx(hx,hf0,hv0,hl0,mode);Z=dx(rx,rf0,rv0,rl0,mode);ht,hf=rates(hx);rt0,rf1=rates(rx)
 a,b,c,d=state(hx);ra,rb0,rc0,rd0=state(rx);fits={}
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind;te=HY==yr;re=RY==yr
  ht[te],bt=fit_total(X[tr],hyn[tr],b[tr],X[te],b[te])
  hf[te],bf=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],X[te],d[te])
  if re.any():
   rt0[re],_=fit_total(X[tr],hyn[tr],b[tr],Z[re],rb0[re]);rf1[re],_=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],Z[re],rd0[re])
  fits[str(yr)]={'train_n':int(tr.sum()),'total_coefficients':bt.tolist(),'share_coefficients':bf.tolist()}
 a={'history_probability':evaluate(H,ht,hf,hm),'receipt_probability':evaluate(R,rt0,rf1,rm),'fit':fits,'markets':{}}
 for market in ('AH','OU'):
  p=pay(H,ht,hf,market);r=pay(R,rt0,rf1,market)
  a['markets'][market]={'history':score(H,p,hm),'history_disjoint_receipt':score(H,p,hm&history_ind),'receipt':score(R,r,rm),'years':{str(yr):score(H,p,hm&(HY==yr)) for yr in (2024,2025,2026)}}
 if mode=='pooled':
  old=json.loads((P/'m8_team_market_residual_research_20261116.json').read_text())['models']['team']
  for mk in ('AH','OU'):
   for k in ('history','receipt'):assert a['markets'][mk][k]['U']==old['markets'][mk][k]['U']
 out['models'][mode]=a
 print(mode,'prob',a['history_probability'],a['receipt_probability'],'markets',{m:{'H':slim(v['history']),'D':slim(v['history_disjoint_receipt']),'R':slim(v['receipt']),'Y':{k:slim(j) for k,j in v['years'].items()}} for m,v in a['markets'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_team_venue_pricing_20261116.json').write_text(json.dumps(out,indent=2))
