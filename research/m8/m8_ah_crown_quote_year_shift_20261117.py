import json,datetime,collections,hashlib
import numpy as np
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
source=(P/'m8_ah_transfer_2026_decay_diagnostic_20261117.py').read_text()
exec(source[:source.index('months=np.array(')])
# R53: AH only. All precise T24/T12 Crown quotes come from original
# replay/receipt definitions. We compare SAME model decision at both
# stages as ex-post execution sensitivity, NEVER executable T24 signals
# (the chosen side is based in part on T12).
mh=predictions['market']['sign']
th=predictions['8_counts']['sign']
H24=[a for a,b in hist];H12=[b for a,b in hist]
R24=[a for a,b in pairs];R12=[b for a,b in pairs]
ids8=np.array(rf,dtype=bool)  # rf was frozen at R22 before the R52 diagnostic reused ids as integer row indices
assert int(ids8.sum())==977
# Recover baseline AH path side for actual receipt cohort; no TM features.
base=np.array([feature(a,b,'path') for a,b in hist],float)
z=np.array([feature(a,b,'path') for a,b in pairs],float)
ry=np.array([int(a['year']) for a in R12])
rsign=np.zeros(len(R12),bool)
for yr in sorted(set(ry)):
 tr=(HY<yr)&history_ind
 if tr.sum()==0:continue
 mean=base[tr].mean(axis=0)
 std=base[tr].std(axis=0)
 mean[0]=0.;std[0]=1.;std[std<1e-10]=1.
 xt=(base[tr]-mean)/std
 pen=np.eye(base.shape[1])*100.;pen[0,0]=0
 coef=np.linalg.solve(xt.T@xt+pen,xt.T@(ha[tr]-aa[tr]))
 rsign[ry==yr]=(((z[ry==yr]-mean)/std)@coef)>=0
def arr(q,key):
 return np.array([float(v[key]) for v in q],float)
def p_for(q,sign):
 return np.where(sign,arr(q,'home_U'),arr(q,'away_U'))
def quote_stats(q24,q12,sign):
 a_line=arr(q24,'al');b_line=arr(q12,'al')
 a_odds=np.where(sign,arr(q24,'ah'),arr(q24,'aa'))
 b_odds=np.where(sign,arr(q12,'ah'),arr(q12,'aa'))
 a_prob=arr(q24,'aa')/(arr(q24,'ah')+arr(q24,'aa'))
 b_prob=arr(q12,'aa')/(arr(q12,'ah')+arr(q12,'aa'))
 return {'a_line':a_line,'b_line':b_line,'line_delta':b_line-a_line,'line_changed':abs(b_line-a_line)>1e-10,
 'odds_delta':b_odds-a_odds,'odds_changed':abs(b_odds-a_odds)>1e-10,
 'any_change':(abs(b_line-a_line)>1e-10)|(abs(b_odds-a_odds)>1e-10),
 'prob_delta':b_prob-a_prob,
 'a_age':arr(q24,'age_ah'),'b_age':arr(q12,'age_ah'),
 'a_odds':a_odds,'b_odds':b_odds,
 'p24':p_for(q24,sign),'p12':p_for(q12,sign)}
hmark=quote_stats(H24,H12,mh);htrans=quote_stats(H24,H12,th)
rmark=quote_stats(R24,R12,rsign)
leagues=np.array([str(x['league']) for x in H12])
months=np.array([int(x['date'][5:7]) for x in H12])
def values(v):
 v=np.array(v,float)
 if len(v)==0:return None
 return {'mean':round(float(v.mean()),5),'median':round(float(np.median(v)),5),
 'p10':round(float(np.quantile(v,.1)),5),'p90':round(float(np.quantile(v,.9)),5)}
def summarize(mark,ix):
 ix=np.asarray(ix,int)
 if len(ix)==0:return {'n':0}
 m={k:x[ix] for k,x in mark.items()}
 n=len(ix)
 line=m['line_changed'];same=~line
 full_delta=m['p12']-m['p24']
 # For unchanged line this difference is only odds/settlement, but for
 # changed line this includes handicap payout effect.
 out={'n':n,'AH_line_change_n':int(line.sum()),'AH_line_change_pct':round(100*float(line.mean()),3),
  'any_selected_contract_change_pct':round(100*float(m['any_change'].mean()),3),
  'selected_odds_change_pct':round(100*float(m['odds_changed'].mean()),3),
  'selected_odds_gain_pct':round(100*float((m['odds_delta']>1e-10).mean()),3),
  'selected_odds_loss_pct':round(100*float((m['odds_delta']<-1e-10).mean()),3),
  'selected_odds_delta_mean':values(m['odds_delta']),
  'AH_line_delta_mean':values(m['line_delta']),
  'implied_home_prob_delta_mean':values(m['prob_delta']),
  'T24_source_age_hours':values(m['a_age']),
  'T12_source_age_hours':values(m['b_age']),
  'T12_selected_odds':values(m['b_odds']),
  'AH_T12_line':values(m['b_line']),
  'payoff_T12':{'n':n,'U':round(float(m['p12'].sum()),3),'ROI':round(100*float(m['p12'].mean()),3)},
  'payoff_T24_same_future_side_NONEXECUTABLE':{'n':n,'U':round(float(m['p24'].sum()),3),'ROI':round(100*float(m['p24'].mean()),3)},
  'T12_minus_T24_same_future_side_U':round(float(full_delta.sum()),3),
  'T12_minus_T24_same_future_side_pp':round(100*float(full_delta.mean()),3),
  'same_AH_line_n':int(same.sum()),
  'same_AH_line_odds_only_T12_minus_T24_U':round(float(full_delta[same].sum()),3),
  'same_AH_line_odds_only_T12_minus_T24_ROI_pp_over_all_fixtures':round(100*float(full_delta[same].sum())/n,3),
  'line_changed_T12_minus_T24_U':round(float(full_delta[line].sum()),3),
 }
 return out
scope=((HY>=2024)&(HY<=2026)&hv&foundation)
def annual(mask,mark):
 return {str(y):summarize(mark,np.flatnonzero(mask&(HY==y))) for y in (2024,2025,2026)}
out={'study_id':'M8_R53_AH_QUOTE_CHANGE','method':'R53 independent AH diagnostics: same original-eight-excluded retrospective transfer research cohort 6929 history, no OU exclusions, year calendar matching Jan-May. Crown T24/T12 AH source market prices and actual payoff. Compare T12-selected side vs T24 same future side only as NONEXECUTABLE hindsight payout sensitivity; the side was determined from later T12, not a valid T24 prior signal. Sum exactly over same fixtures; no league/month selection, gate, cap or strategy change. Actual received quote archive analysed separately without transfer source, not independent precommitted trading, no TG or realized fill. Quantify quote line shifts, selected-side odds shifts, price age, line-invariant odds-only payoff attribution vs line-changed payoff. The observations cannot establish the causal cause of 2026 profit decay.','source':{'historical_pairs':len(H24),'verified_actual_receipt_pairs':len(R24),'transfer_feature_valid_all':int(hv.sum()),'history_outside_original_eight':int(scope.sum()),'actual_receipt_outside_original_eight':int(ids8.sum()),'dates_actual':[min(x['date'] for x in R12),max(x['date'] for x in R12)]},'models':{},'diagnostics':{}}
for name,mark in [('market',hmark),('market_plus_transfers',htrans)]:
 z0={'all':summarize(mark,np.flatnonzero(scope)),
 'by_year':annual(scope,mark),
 'Jan_May':{str(y):summarize(mark,np.flatnonzero(scope&(HY==y)&(months<=5))) for y in (2024,2025,2026)},
 'each_league':{}}
 for league in sorted(set(leagues[scope])):
  z0['each_league'][str(league)]={str(y):summarize(mark,np.flatnonzero(scope&(HY==y)&(leagues==league)&(months<=5))) for y in (2025,2026)}
 out['models'][name]=z0
 print('HIST',name,'overall',z0['all'],'janmay',{y:{k:v for k,v in q.items() if k in ['n','payoff_T12','payoff_T24_same_future_side_NONEXECUTABLE','T12_minus_T24_same_future_side_U','same_AH_line_odds_only_T12_minus_T24_U','AH_line_change_pct','selected_odds_gain_pct','selected_odds_loss_pct','T24_source_age_hours','T12_source_age_hours']} for y,q in z0['Jan_May'].items()},flush=True)
 # Direct arithmetic price deterioration Jan-May same future side
 a=z0['Jan_May']['2025'];b=z0['Jan_May']['2026']
 out['diagnostics'][name+'_JanMay_2025_vs_2026']={
 'T12_roi_shift_pp':round(b['payoff_T12']['ROI']-a['payoff_T12']['ROI'],3),
 'T24_counterfactual_roi_shift_pp':round(b['payoff_T24_same_future_side_NONEXECUTABLE']['ROI']-a['payoff_T24_same_future_side_NONEXECUTABLE']['ROI'],3),
 'change_in_T12_minus_T24_execution_sensitivity_pp':round(b['T12_minus_T24_same_future_side_pp']-a['T12_minus_T24_same_future_side_pp'],3),
 'same_line_odds_component_shift_pp':round(b['same_AH_line_odds_only_T12_minus_T24_ROI_pp_over_all_fixtures']-a['same_AH_line_odds_only_T12_minus_T24_ROI_pp_over_all_fixtures'],3)}
r_scope=np.ones(len(R24),bool)
for name,mask in [('actual_receipt_all',r_scope),('actual_receipt_outside_eight',ids8)]:
 z0=summarize(rmark,np.flatnonzero(mask))
 out['models'][name]={'result':z0}
 print('RECEIPT',name,z0,flush=True)
# Source-age distribution may differ between retrieved historical & actual.
# Follow-up no new real-time availability claims: older mark was observed at
# a historical source timestamp, not necessarily received by T24/T12.
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_ah_crown_quote_year_shift_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
