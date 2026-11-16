import json,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_team_market_residual_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Same histories and weights as R26. Split own goals above market
# expectations from opponent goals conceded above market expectations.
def split_residual(q):
 A=[];D=[]
 for a in q:
  day=orddate(a['date']);v=[]
  for team in (a['home_id'],a['away_id']):
   dd,rr0=idx1.get((a['league'],team),(np.array([]),np.empty((0,2))))
   end=int(np.searchsorted(dd,day-3,side='right'))
   ages=day-dd[:end];r=rr0[:end];z=[]
   for hl in (30,180):
    w=np.exp(-np.log(2)*ages/hl)
    z.extend((w@r/(8+w.sum())).tolist())
   v.extend(z)
  sh,sa,lh,la,sh2,sa2,lh2,la2=v
  al=np.array([lh+lh2,lh-lh2]);ass=np.array([sh+sh2,sh-sh2])
  dl=np.array([la2+la,la2-la]);ds=np.array([sa2+sa,sa2-sa])
  A.append(np.r_[al,ass-al]);D.append(np.r_[dl,ds-dl])
 return np.array(A),np.array(D)
ha,hd=split_residual(H);ra0,rd1=split_residual(R)
assert np.allclose(ha+hd,hf0,rtol=0,atol=1e-12)
assert np.allclose(ra0+rd1,rf0,rtol=0,atol=1e-12)
out={'method':'R28 exact R26 cohort and history, split own scoring residual and opponent concession residual, each long total/margin and short-minus-long total/margin. Same 3 UTC date lag, 30/180 day half-life, shrink8, ridge100; earlier calendar years only, exclude receipt IDs from history and fit. Compare pooled baseline, attack-only, defense-only, unconstrained split; all fixtures and periods retained; no profit-selected samples, no trading gates. Retrospective, not independently forward tested.','coverage':{'historical':int(hm.sum()),'receipt':int(rm.sum())},'models':{}}
for mode in ('pooled','attack','defense','split'):
 def design0(x,a,d):
  b=make_x(x,'static')
  f={'pooled':a+d,'attack':a,'defense':d,'split':np.column_stack((a,d))}[mode]
  return np.column_stack((b,f))
 X=design0(hx,ha,hd);Z=design0(rx,ra0,rd1)
 # Preserve exact baseline floating point path.
 if mode=='pooled':
  X=design(hx,hf0,'team');Z=design(rx,rf0,'team')
 ht,hf=rates(hx);rt0,rf1=rates(rx)
 a,b,c,d=state(hx);ra,rb0,rc0,rd0=state(rx);fits={}
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind;te=HY==yr;re=RY==yr
  ht[te],bt=fit_total(X[tr],hyn[tr],b[tr],X[te],b[te])
  hf[te],bf=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],X[te],d[te])
  if re.any():
   rt0[re],_=fit_total(X[tr],hyn[tr],b[tr],Z[re],rb0[re]);rf1[re],_=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],Z[re],rd0[re])
  fits[str(yr)]={'train_n':int(tr.sum()),'total_coefficients':bt.tolist(),'share_coefficients':bf.tolist()}
 z0={'history_probability':evaluate(H,ht,hf,hm),'receipt_probability':evaluate(R,rt0,rf1,rm),'fit':fits,'markets':{}}
 for market in ('AH','OU'):
  p=pay(H,ht,hf,market);r=pay(R,rt0,rf1,market)
  z0['markets'][market]={'history':score(H,p,hm),'history_disjoint_receipt':score(H,p,hm&history_ind),'receipt':score(R,r,rm),'years':{str(yr):score(H,p,hm&(HY==yr)) for yr in (2024,2025,2026)}}
 if mode=='pooled':
  old=json.loads((P/'m8_team_market_residual_research_20261116.json').read_text())['models']['team']
  for mk in ('AH','OU'):
   for q in ('history','receipt'):assert z0['markets'][mk][q]['U']==old['markets'][mk][q]['U']
 out['models'][mode]=z0
 print(mode,'markets',{k:{'H':slim(v['history']),'R':slim(v['receipt']),'Y':{y:slim(j) for y,j in v['years'].items()}} for k,v in z0['markets'].items()},'prob',z0['history_probability'],z0['receipt_probability'],flush=True)
 print('COEFS',mode,fits,flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_team_attack_defense_residual_20261116.json').write_text(json.dumps(out,indent=2))
