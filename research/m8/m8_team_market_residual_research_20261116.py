import json,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_market_response_calibration_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# New signal: prior team goals scored/conceded minus the prior match's
# Crown-implied goals. Opponent and venue expectations are already in the quote.
# Use a three UTC-date lag and 30/180-day exponential decay, shrink toward zero.
# All test matches retained, even where the history feature is zero.
from bisect import bisect_right
assert len(H)==38846 and len(R)==1230
orddate=lambda x:datetime.date.fromisoformat(x).toordinal()
idx0=collections.defaultdict(list)
for a,xx,ok in zip(H,hx,history_ind):
 if not ok:continue
 t1,d1=xx[1],xx[3];h0=(t1+d1)/2;a0=(t1-d1)/2
 hres=a['hg']-h0;ares=a['ag']-a0
 for team,fr,ag in [(a['home_id'],hres,ares),(a['away_id'],ares,hres)]:
  if team:idx0[(a['league'],team)].append((orddate(a['date']),a['fid'],fr,ag))
for k in idx0:
 idx0[k].sort()
idx1={k:(np.array([a[0] for a in v]),np.array([a[2:] for a in v])) for k,v in idx0.items()}
def tf(q):
 F=[];N=[]
 for a in q:
  day=orddate(a['date']);vals=[];ns=[]
  for team in (a['home_id'],a['away_id']):
   dd,rr=idx1.get((a['league'],team),(np.array([]),np.empty((0,2))))
   end=int(np.searchsorted(dd,day-3,side='right'));ns.append(end)
   ds=day-dd[:end];v=rr[:end]
   x=[]
   for hl in (30,180):
    w=np.exp(-np.log(2)*ds/hl);x.extend((w@v/(8+w.sum())).tolist())
   vals.extend(x)
  sh,sa,lh,la,sh2,sa2,lh2,la2=vals
  # Own attacking residual plus opponent conceding residual; home/away symmetrized.
  short_h=sh+sa2;short_a=sh2+sa
  long_h=lh+la2;long_a=lh2+la
  F.append([long_h+long_a,long_h-long_a,(short_h+short_a)-(long_h+long_a),(short_h-short_a)-(long_h-long_a)])
  N.append(ns)
 return np.array(F),np.array(N)
hf0,hn=tf(H);rf0,rn=tf(R)
print('COVERAGE',len(idx1),int((hn[hm].min(1)>0).sum()),int((rn[rm].min(1)>0).sum()),flush=True)
def design(x,ff,mode):
 base=make_x(x,'static')
 if mode=='static':return base
 if mode=='response':return make_x(x,'response')
 if mode=='team':return np.column_stack((base,ff))
 if mode=='joint':return np.column_stack((make_x(x,'response'),ff))
 raise ValueError(mode)
out={'method':'R26 prior team scoring/conceding residual versus prior Crown implied goals, same-league team histories at least three UTC dates earlier, 30/180-day exponential half-lives and shrinkage8 inherited scale; no prior history -> zero shrinkage. Prior receipt FIDs excluded from feature history and fit. Earlier calendar year training, identical T24/T12 matching and whole test sets, static/market-response/team/joint comparison. All matches and complete cycles retained; no trading rule or parameter selection by ROI. Historical data already explored, not independent forward evaluation.','coverage':{'history':int(hm.sum()),'receipt':int(rm.sum()),'teams_with_history':len(idx1),'history_both_prior':int((hn[hm].min(1)>0).sum()),'receipt_both_prior':int((rn[rm].min(1)>0).sum())},'models':{}}
for mode in ('static','response','team','joint'):
 ht,hf=rates(hx);rt0,rf1=rates(rx);X=design(hx,hf0,mode);Z=design(rx,rf0,mode)
 a,b,c,d=state(hx);ra,rb0,rc,rd0=state(rx);fits={}
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
 if mode in ('static','response'):
  old=json.loads((P/'m8_early_market_response_calibration_20261116.json').read_text())['models'][mode]
  for market in ('AH','OU'):
   for q in ('history','receipt'):assert a['markets'][market][q]['U']==old['markets'][market][q]['U']
 out['models'][mode]=a
 print(mode,'Hprob',a['history_probability'],'Rprob',a['receipt_probability'],'markets',{k:{'H':slim(v['history']),'R':slim(v['receipt']),'Y':{y:slim(j) for y,j in v['years'].items()}} for k,v in a['markets'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_team_market_residual_research_20261116.json').write_text(json.dumps(out,indent=2))
