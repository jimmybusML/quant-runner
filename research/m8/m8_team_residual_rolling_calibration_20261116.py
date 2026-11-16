import json,collections,hashlib,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_team_market_residual_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Experimental comparison only; same features, payout and test IDs.
# Monthly cutoffs use three UTC-date lag. The 12-month window is a
# research alternative to isolate the effect of removing old observations.
X=design(hx,hf0,'team');Z=design(rx,rf0,'team')
a,b,c,d=state(hx);ra,rb0,rc0,rd0=state(rx)
hdays=np.array([orddate(r['date']) for r in H]);rdates=np.array([r['date'][:7] for r in R])
hdates=np.array([r['date'][:7] for r in H])
months=sorted(set(hdates[HY>=2024])|set(rdates[RY>=2024]))
out={'method':'R29 same R26 pooled residual, historical and archived-receipt test IDs, features, penalty and settlement; compare annual expanding, annual expanding with 3 UTC-date lag, monthly expanding with 3-date lag, monthly trailing 12-calendar-month with same lag. Windows are experimental, not additional rules. All training records before cutoff, receipt archive IDs excluded. All outcomes and complete periods retained. Historical archives already explored; no independent forward evaluation.','coverage':{'historical':int(hm.sum()),'receipt':int(rm.sum()),'months':len(months)},'models':{}}
for mode in ('annual','annual_lag','monthly_expanding','monthly_12m'):
 ht,hf=rates(hx);rt0,rf1=rates(rx);fits={};covered=np.zeros(len(H),bool);rcovered=np.zeros(len(R),bool)
 periods=[str(y) for y in (2024,2025,2026)] if mode.startswith('annual') else months
 for k in periods:
  start=datetime.date.fromisoformat(k+('-01-01' if len(k)==4 else '-01'))
  cutoff=start if mode=='annual' else start-datetime.timedelta(days=3)
  tr=(hdays<cutoff.toordinal())&history_ind
  if mode=='monthly_12m':
   lower=start.replace(year=start.year-1);tr &= hdays>=lower.toordinal()
  if len(k)==4:te=HY==int(k);re=RY==int(k)
  else:te=hdates==k;re=rdates==k
  assert tr.any() and not (tr&te).any() and hdays[tr].max()<cutoff.toordinal()
  # Fit once for historical and actual-receipt quotes on the same period.
  xx=np.concatenate([X[te],Z[re]],axis=0);oo=np.r_[b[te],rb0[re]];os=np.r_[d[te],rd0[re]]
  pt,bt=fit_total(X[tr],hyn[tr],b[tr],xx,oo);pf,bf=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],xx,os)
  nn=int(te.sum());ht[te]=pt[:nn];hf[te]=pf[:nn];rt0[re]=pt[nn:];rf1[re]=pf[nn:]
  covered|=te;rcovered|=re
  fits[k]={'train_n':int(tr.sum()),'train_first':datetime.date.fromordinal(int(hdays[tr].min())).isoformat(),'train_last':datetime.date.fromordinal(int(hdays[tr].max())).isoformat(),'cutoff_exclusive':cutoff.isoformat(),'total_coefficients':bt.tolist(),'share_coefficients':bf.tolist()}
 assert covered[hm].all() and rcovered[rm].all()
 z0={'history_probability':evaluate(H,ht,hf,hm),'receipt_probability':evaluate(R,rt0,rf1,rm),'fit':fits,'markets':{}}
 for market in ('AH','OU'):
  p=pay(H,ht,hf,market);r=pay(R,rt0,rf1,market)
  z0['markets'][market]={'history':score(H,p,hm),'history_disjoint_receipt':score(H,p,hm&history_ind),'receipt':score(R,r,rm),'years':{str(yr):score(H,p,hm&(HY==yr)) for yr in (2024,2025,2026)},'months':{k:score(H,p,hm&(hdates==k)) for k in months},'receipt_months':{k:score(R,r,rm&(rdates==k)) for k in sorted(set(rdates[rm]))}}
 if mode=='annual':
  old=json.loads((P/'m8_team_market_residual_research_20261116.json').read_text())['models']['team']
  for mk in ('AH','OU'):
   for k in ('history','receipt'):assert z0['markets'][mk][k]['U']==old['markets'][mk][k]['U']
 out['models'][mode]=z0
 print(mode,'prob',z0['history_probability'],z0['receipt_probability'],'markets',{m:{'H':slim(v['history']),'D':slim(v['history_disjoint_receipt']),'R':slim(v['receipt']),'Y':{k:slim(j) for k,j in v['years'].items()}} for m,v in z0['markets'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_team_residual_rolling_calibration_20261116.json').write_text(json.dumps(out,indent=2))
