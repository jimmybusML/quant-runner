import json,collections,datetime,hashlib,math
import numpy as np
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_ah_transfer_independent_deepdive_20261117.py').read_text()
exec(src[:src.index("out={'research_id'")])
# Same previously frozen feature definitions and outcome payouts, AH only.
# Reconstruct paired decisions via no-future-information expanding year fits.
def design(mode):
 b=np.array([feature(a,c,'path') for a,c in hist])
 if mode=='market':return b
 if mode=='8_counts':return np.column_stack((b,HF[:,[0,1,6,7,12,13,18,19]]))
 if mode=='4_diff':return np.column_stack((b,HF[:,[0,1,6,7]]))
 raise ValueError(mode)
def fit_predict(mode,train_end_year,targets=None):
 X=design(mode)
 tr=(HY<train_end_year)&history_ind&hv
 if targets is None:targets=np.flatnonzero((HY==train_end_year)&hv)
 mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 xx=(X[tr]-mu)/sd
 penalty=np.eye(X.shape[1])*100;penalty[0,0]=0
 coef=np.linalg.solve(xx.T@xx+penalty,xx.T@(ha[tr]-aa[tr]))
 pred=((X[targets]-mu)/sd)@coef
 return targets,pred,coef,{"n_train":int(tr.sum()),"n_target":len(targets)}
predictions={}
for mode in ('market','8_counts','4_diff'):
 score_arr=np.full(len(H),np.nan);sign=np.zeros(len(H),bool);coefs={}
 for y in (2024,2025,2026):
  ids,v,c,info=fit_predict(mode,y)
  score_arr[ids]=v;sign[ids]=v>=0
  coefs[str(y)]={'coefficients':c.tolist(),**info}
 p=np.where(sign,ha,aa)
 predictions[mode]={'sign':sign,'score':score_arr,'p':p,'fits':coefs}
# FIXED 2025-year model applied to the exact 2026 target cohort, without using
# 2026 results. Used only as a sensitivity analysis, not a new live policy.
fixed={}
for mode in predictions:
 ids=np.flatnonzero((HY==2026)&hv)
 _,v,c,info=fit_predict(mode,2025,targets=ids)
 fixed[mode]={'sign':v>=0,'p':np.where(v>=0,ha[ids],aa[ids]),'scores':v,'coefficients':c.tolist(),'n':len(ids)}
months=np.array([str(z['date'])[:7] for z in H])
qtrs=np.array([str(z['date'])[:4]+'Q'+str((int(str(z['date'])[5:7])-1)//3+1) for z in H])
month_num=np.array([int(str(z['date'])[5:7]) for z in H])
leagues=np.array([str(r['league']) for r in H])
# Rate functions are simple finite returns per every 1U AH bet in the same
# target cohort. No subset constitutes an approved trading rule.
def result(ids,p):
 v=np.asarray(p)[ids]
 return {'n':len(v),'U':round(float(v.sum()),3),'ROI':round(100*float(v.mean()),3) if len(v) else None,
 'wins':int((v>1e-10).sum()),'losses':int((v<-1e-10).sum()),'push':int((abs(v)<=1e-10).sum())}
scope=ind&foundation
idx=np.flatnonzero(scope)
b=predictions['market'];c=predictions['8_counts'];d=predictions['4_diff']
z={'scope':'R52 AH-only on R51 original-eight-disjoint retrospective event cohort, 6929 matches, no OU exclusions. Compare 2024, 2025 and partial 2026 like-for-like Jan-May; decompose 2026 performance into market baseline and transfer model changes. 2026-07-06 external TM cutoff, no live valid actual receipt. League/year diagnostic NOT training feature nor trading whitelist. 2025 fitted model projected onto 2026 unchanged dates is additional sensitivity only; 2026 is research holdout, not independently precommitted. Earlier-year fit excludes receipt target IDs. No production rules changed.','scope_n':int(scope.sum()),'models':{},'market_source':'Crown archived T12 AH, date-correct source events (back-retrieved historic), independent TM historical transfer effective dates with no verified publication timestamp','diagnostics':{},'coverage':{}}
for mode,o in predictions.items():
 p=o['p']
 z['models'][mode]={'overall':result(idx,p),'years':{},'like_for_like_months':{},'train':o['fits']}
 for y in (2024,2025,2026):
  mask=scope&(HY==y)
  z['models'][mode]['years'][str(y)]=result(np.flatnonzero(mask),p)
  for monthspec, m in [('Jan-May',month_num<=5),('Jan-Jun',month_num<=6),('Jul-Dec',month_num>=7),('Jan-Feb',month_num<=2),('Mar-May',(month_num>=3)&(month_num<=5))]:
   z['models'][mode]['like_for_like_months'][str(y)+'_'+monthspec]=result(np.flatnonzero(mask&m),p)
 print('OVERALL',mode,z['models'][mode]['overall'],'ANNUAL',{y:k['ROI'] for y,k in z['models'][mode]['years'].items()},'JANMAY',{y:z['models'][mode]['like_for_like_months'][y+'_Jan-May'] for y in ['2024','2025','2026']},flush=True)
for y in (2024,2025,2026):
 ys=scope&(HY==y)
 for key,m in [('whole',ys),('Jan-May',ys&(month_num<=5)),('Jan-Feb',ys&(month_num<=2)),('Mar-May',ys&((month_num>=3)&(month_num<=5)))]:
  ids=np.flatnonzero(m)
  diff=c['p']-b['p']
  flip=(c['sign']!=b['sign'])
  changed=ids[flip[ids]]
  unch=ids[~flip[ids]]
  # Underlying absolute transfer activity input is not complete official
  # transactions universe, only events observable in this backfilled table.
  d90=(HF[ids,0]+HF[ids,1]+HF[ids,12]+HF[ids,13])/2
  d365=(HF[ids,6]+HF[ids,7]+HF[ids,18]+HF[ids,19])/2
  arr=HF[ids]
  active=np.flatnonzero(d90>0)
  rows={
   'model':result(ids,c['p']),'market':result(ids,b['p']),'model_vs_market':result(ids,diff),
   'flipped_market':result(changed,b['p']),'flipped_transfer':result(changed,c['p']),
   'same':result(unch,c['p']),
   'transfer_events_90_total_mean':round(float(d90.mean()),3) if len(ids) else None,
   'transfer_events_365_total_mean':round(float(d365.mean()),3) if len(ids) else None,
   'share_any_transfers_90':round(float((d90>0).mean())*100,2) if len(ids) else None,
   'transfer_features_mean':np.round(arr.mean(axis=0),3).tolist() if len(ids) else [],
  }
  z['diagnostics'][str(y)+'_'+key]=rows
  print('PAIRED',y,key,'n',len(ids),'delta',rows['model_vs_market'],'changed',len(changed),
        '90events',rows['transfer_events_90_total_mean'],'365events',rows['transfer_events_365_total_mean'],flush=True)
# Year-on-year decomposition: changes in league exposure vs within-league ROI,
# using only leagues appearing in both Jan-May 2025 and Jan-May 2026;
# no hindsight selection for trading, simply algebraic attribution.
for ym in ('whole','Jan-May'):
 a=scope&(HY==2025);aa0=scope&(HY==2026)
 if ym=='Jan-May':a&=(month_num<=5);aa0&=(month_num<=5)
 for mode,o in predictions.items():
  res={}
  for league in sorted(set(leagues[a])|set(leagues[aa0])):
   r={}
   for year,mask in [(2025,a),(2026,aa0)]:
    ids=np.flatnonzero(mask&(leagues==league))
    r[str(year)]=result(ids,o['p'])
   res[league]=r
  active=[k for k,v in res.items() if v['2025']['n']>0 and v['2026']['n']>0]
  n25=sum(res[k]['2025']['n'] for k in active)
  n26=sum(res[k]['2026']['n'] for k in active)
  within=composition=0
  for k in active:
   w25=res[k]['2025']['n']/n25;w26=res[k]['2026']['n']/n26
   r25=res[k]['2025']['ROI'];r26=res[k]['2026']['ROI']
   within+=(w25+w26)/2*(r26-r25)
   composition+=(r25+r26)/2*(w26-w25)
  total25=sum(res[k]['2025']['U'] for k in active)/n25*100
  total26=sum(res[k]['2026']['U'] for k in active)/n26*100
  decomposition={'common_leagues':len(active),'n2025':n25,'n2026':n26,'roi2025':round(total25,4),'roi2026':round(total26,4),
    'within_league_shift_pp':round(within,4),'league_composition_shift_pp':round(composition,4),
    'total_change_pp':round(total26-total25,4),'by_league':res}
  assert abs(within+composition-(total26-total25))<.015
  z['diagnostics']['league_decomp_'+mode+'_'+ym]=decomposition
  print('DECOMP',mode,ym,{k:v for k,v in decomposition.items() if k!='by_league'},flush=True)
# Fixed prior-year versus expanding model for identical 2026 dates.
for mode,o in predictions.items():
 ids=np.flatnonzero(scope&(HY==2026))
 all_ids=np.flatnonzero((HY==2026)&hv)
 indmap={id_:i for i,id_ in enumerate(all_ids)}
 fp=np.array([fixed[mode]['p'][indmap[id_]] for id_ in ids])
 actual=o['p'][ids]
 z['diagnostics']['2026_train_stability_'+mode]={
  'retrained_previous_all_years':result(np.arange(len(ids)),actual),
  'frozen_pre2025_training':result(np.arange(len(ids)),fp),
  'fixed_minus_retrained_units':round(float((fp-actual).sum()),3),
  'direction_changes':int(((fp!=actual)&(abs(fp-actual)>1e-10)).sum()),
  'full_coefficient_norm_pre2025':round(float(np.linalg.norm(fixed[mode]['coefficients'])),4),
  'full_coefficient_norm_pre2026':round(float(np.linalg.norm(predictions[mode]['fits']['2026']['coefficients'])),4),
 }
 print('FIT_SHIFT',mode,z['diagnostics']['2026_train_stability_'+mode],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
z['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(z['foundation'].values())
(P/'m8_ah_transfer_2026_decay_diagnostic_20261117.json').write_text(json.dumps(z,ensure_ascii=False,indent=2))
