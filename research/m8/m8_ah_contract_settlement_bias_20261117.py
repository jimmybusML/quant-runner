import json, collections, datetime, hashlib, math
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_joint_path_incremental_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# AH-only. Same-year AH performance analyzed on original8-excluded
# 2024-26 quote-paired archive; NO exclusion from OU candidate membership.
hmask=(HY>=2024)&(HY<=2026)&foundation
rmask=rf
assert int(hmask.sum())==19954 and int(rmask.sum())==977
h_m=np.array([float(q['al']) for q in H]);r_m=np.array([float(q['al']) for q in R])
hm24=np.array([float(a['al']) for a,b in hist]);rm24=np.array([float(a['al']) for a,b in pairs])
home=vec(H,'home_U');away=vec(H,'away_U')
rhome=vec(R,'home_U');raway=vec(R,'away_U')
def split(p,mask,q):
 if not mask.any():return {'n':0}
 t=score(q,p,mask)
 return {k:v for k,v in t.items() if k!='weekly_counts'}
def basis(p):
 a,b=p;ln=float(b['al']);pre=float(a['al'])
 u=float(b['ah']);v=float(b['aa'])
 q=float(a['ah']);r=float(a['aa'])
 vig=1/u+1/v-1
 m=abs(ln);mw=abs(pre)
 p_home=v/(u+v);dp=p_home-r/(q+r)
 phase=round(m*4)%4
 # Named empirical contract features, not accepted trading rules.
 shape=[np.sign(ln),m,min(m,1),min(max(m-1,0),1),min(max(m-2,0),1),
  float(ln==0),float(phase==0),float(phase==1),float(phase==2),float(phase==3),
  float(ln<=-0.5),float(ln>=0.5),vig,
  p_home-0.5,abs(p_home-.5),p_home-.5+dp,dp,
  m*(p_home-0.5),np.sign(ln)*(p_home-0.5),
  abs(float(ln-pre)),np.sign(ln-pre),vig*(p_home-.5),
  (u-v),(u-v)*np.sign(ln),abs(u-v)]
 return np.asarray(shape,float)
def interaction(p):
 a,b=p;arr=basis(p)
 ah=float(b['al']);ph=float(b['aa'])/(float(b['ah'])+float(b['aa']))
 dh=float(b['ah'])-float(a['ah']);da=float(b['aa'])-float(a['aa'])
 line_delta=float(b['al'])-float(a['al'])
 return np.r_[arr,[line_delta,dh,da,
  ah*dh,ah*da,ah*line_delta,abs(ah)*dh,abs(ah)*da,
  (ph-.5)*dh,(ph-.5)*da,
  np.sign(ah)*dh,np.sign(ah)*da,
  float(abs(ah)%1==.25)*dh,float(abs(ah)%1==.5)*dh,
  float(abs(ah)%1==.75)*dh]]
B=np.array([feature(a,b,'path') for a,b in hist])
BR=np.array([feature(a,b,'path') for a,b in pairs])
C=np.array([feature(a,b,'current') for a,b in hist])
CR=np.array([feature(a,b,'current') for a,b in pairs])
E=np.array([basis(p) for p in hist])
ER=np.array([basis(p) for p in pairs])
I=np.array([interaction(p) for p in hist])
IR=np.array([interaction(p) for p in pairs])
features={
 'R22_current':(C,CR,100),
 'R22_path':(B,BR,100),
 'AH_contract_only':(np.column_stack((np.ones(len(H)),E)),np.column_stack((np.ones(len(R)),ER)),100),
 'AH_path_plus_shape':(np.column_stack((B,E)),np.column_stack((BR,ER)),100),
 'AH_path_plus_shape_ridge300':(np.column_stack((B,E)),np.column_stack((BR,ER)),300),
 'AH_path_plus_quote_interaction':(np.column_stack((B,I)),np.column_stack((BR,IR)),100),
}
# Pure AH at both T24 and T12. No OU data used even as a model feature.
def ah_path_only(pair):
 a,b=pair
 a_l,b_l=float(a['al']),float(b['al'])
 ah,aa=float(a['ah']),float(a['aa'])
 bh,ba=float(b['ah']),float(b['aa'])
 pa=aa/(ah+aa)
 pb=ba/(bh+ba)
 return np.r_[1.,basis(pair),
    [a_l,ah,aa,pa,1/ah+1/aa-1,
     b_l-a_l,bh-ah,ba-aa,pb-pa,
     abs(b_l-a_l),np.sign(b_l-a_l),
     np.log1p(float(a['age_ah'])),
     np.log1p(float(b['age_ah'])),
     (bh-ah)*np.sign(b_l),
     (ba-aa)*np.sign(b_l)]]
A=np.array([ah_path_only(p) for p in hist])
AR=np.array([ah_path_only(p) for p in pairs])
features['AH_only_T24_T12_path']=(A,AR,100)
features['AH_only_T24_T12_path_ridge300']=(A,AR,300)

def annual(p,mask,years,q):
 return {str(y):split(p,mask&(years==y),q) for y in (2024,2025,2026)}
out={'method':'R54 AH-only source-exact T24/T12 Crown contract pricing and settlement. Compare all same fixtures with simple previous-year OH side payout difference prediction from line sign, sign/absolute and quarter-handicap shapes, normalized AH prices, vig, AH quote movement and interactions, against inherited R22 current/path. Always choose one AH side per fixture, no selective skip, no league/month profitability filter, no OU membership exclusion or production rule. Ridge 100/300 are explicit model experiments, not user-confirmed rule. Training uses earlier calendar years only and excludes all verified actual receipt FIDs; exact quarter settlement from upstream. Receipt replay not an independently precommitted forward test and not a formal TG ledger. Retrospective source-event timestamp not actual historical receipt. Features need T12 so cannot be traded at T24. Fixed original8 excluded only to compute historical incremental research, not real-time eligible status.','counts':{'historical_pairs':len(H),'original8_excluded_history':int(hmask.sum()),'actual_verified_pairs':len(R),'actual_excluding8':int(rmask.sum()),'historical_years':{str(y):int((hmask&(HY==y)).sum()) for y in (2024,2025,2026)}},'models':{},'unconditional_legs':{},'contract_diagnostics':{}}
for name,(X,Z,ridge) in features.items():
 hp=np.zeros(len(H));rp=np.zeros(len(R));pred=np.zeros(len(H));meta={}
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind;te=(HY==yr);re=(RY==yr)
  mu=X[tr].mean(0);sd=X[tr].std(0)
  mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
  xx=(X[tr]-mu)/sd
  pen=np.eye(X.shape[1])*ridge;pen[0,0]=0
  coef=np.linalg.solve(xx.T@xx+pen,xx.T@(home[tr]-away[tr]))
  pred[te]=((X[te]-mu)/sd)@coef
  if re.any():rp[re]=((Z[re]-mu)/sd)@coef
  meta[str(yr)]={'train_n':int(tr.sum()),'features':X.shape[1],'ridge':ridge}
 pnl=np.where(pred>=0,home,away)
 r_pnl=np.where(rp>=0,rhome,raway)
 z={'historical':split(pnl,hmask,H),'actual':split(r_pnl,rmask,R),
    'historical_disjoint_actual':split(pnl,hmask&history_ind,H),
    'year':annual(pnl,hmask,HY,H),
    'year_jan_may':{str(y):split(pnl,hmask&(HY==y)&np.array([int(v['date'][5:7])<=5 for v in H]),H) for y in (2024,2025,2026)},
    'training':meta,
    'flip_from_R22_path_count':None}
 out['models'][name]=z
 print('MODEL',name,'H',z['historical'],'R',z['actual'],'years',{y:(v['n'],v.get('ROI')) for y,v in z['year'].items()},flush=True)
 # Baseline predictions retained for next cross model change comparisons.
 if name=='R22_path':
  base_decision=pred>=0;base_p=pnl
 else:
  if 'base_decision' in locals():
   changed=(pred>=0)!=base_decision
   z['flip_from_R22_path_count']=int((hmask&changed).sum())
   z['flip_changed_leg_profit_delta_U']=round(float((pnl-base_p)[hmask&changed].sum()),3)
# No model-selection rules: completely unconditional sign payoff diagnostics.
unconditional={
 'home':(home,rhome),
 'away':(away,raway),
 'market_home_favorite_if_negative_else_away':(np.where(h_m<0,home,away),np.where(r_m<0,rhome,raway)),
 'market_underdog_home_if_positive_else_away':(np.where(h_m>0,home,away),np.where(r_m>0,rhome,raway)),
}
for name,(p,rp) in unconditional.items():
 out['unconditional_legs'][name]={'historical':split(p,hmask,H),
 'actual':split(rp,rmask,R),'annual':annual(p,hmask,HY,H)}
 print('SIDE',name,'H',out['unconditional_legs'][name]['historical'],'R',out['unconditional_legs'][name]['actual'],
 'annual',{k:(v['n'],v.get('ROI')) for k,v in out['unconditional_legs'][name]['annual'].items()},flush=True)
def diag(mask,p,q,years,lines,ages):
 ret={'n':int(mask.sum())}
 if not mask.any():return ret
 x=lines[mask];v=p[mask]
 for label,group in [('home_favorite',x<0),('away_favorite',x>0),('pickem',x==0),
  ('integer',np.isclose(np.mod(abs(x),1),0)),('quarter',np.isclose(np.mod(abs(x),1),.25)),
  ('half',np.isclose(np.mod(abs(x),1),.5)),('three_quarter',np.isclose(np.mod(abs(x),1),.75))]:
  ret[label]={'n':int(group.sum()),'roi':round(100*float(v[group].mean()),3) if group.any() else None}
 ret['line_abs_mean']=round(float(abs(x).mean()),3)
 ret['home_favored_fraction']=round(float((x<0).mean()),3)
 ret['AH_source_age_hours_median']=round(float(np.median(ages[mask])),3)
 return ret
ages=np.array([float(v['age_ah']) for v in H])
rage=np.array([float(v['age_ah']) for v in R])
hb=out['models']['R22_path']['year']
# Need baseline decisions precisely reconstructed for market_path model.
ref=np.array([feature(a,b,'path') for a,b in hist])
refZ=np.array([feature(a,b,'path') for a,b in pairs])
baseh=np.zeros(len(H),bool);baser=np.zeros(len(R),bool)
for yr in (2024,2025,2026):
 tr=(HY<yr)&history_ind;te=HY==yr;re=RY==yr
 mu=ref[tr].mean(0);sd=ref[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 a=(ref[tr]-mu)/sd;pen=np.eye(ref.shape[1])*100;pen[0,0]=0
 coef=np.linalg.solve(a.T@a+pen,a.T@(home[tr]-away[tr]))
 baseh[te]=((ref[te]-mu)/sd)@coef>=0
 baser[re]=((refZ[re]-mu)/sd)@coef>=0
hp=np.where(baseh,home,away);rp=np.where(baser,rhome,raway)
for yr in (2024,2025,2026):
 mask=hmask&(HY==yr)
 m1=mask&np.array([int(v['date'][5:7])<=5 for v in H],bool)
 out['contract_diagnostics'][str(yr)+'_full']=diag(mask,hp,H,HY,h_m,ages)
 out['contract_diagnostics'][str(yr)+'_jan_may']=diag(m1,hp,H,HY,h_m,ages)
out['contract_diagnostics']['actual_outside_eight']=diag(rmask,rp,R,RY,r_m,rage)
print('DIAG',out['contract_diagnostics'],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_ah_contract_settlement_bias_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
