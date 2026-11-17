import json,hashlib,collections,datetime
from pathlib import Path
import numpy as np
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_r59_early_precursor_repricing_20261117.py').read_text()
exec(src[:src.index('for name,data in X.items():')])
assert len(R)==1230 and len(h6)==38846
historical_script=str(P/'m8_r59_early_precursor_repricing_20261117.py')
data=X['T24_T12_AH_path']
train=np.flatnonzero((years<2026)&excluded_receipts)
trside=np.flatnonzero((years<2026)&excluded_receipts&valid_side)
_,ptrain,params=fit(data,membership,train,train)
_,_,sideparams=fit(data,side,trside,trside)
def predict(arr,params):
 mean,sd,beta=params
 return np.clip((arr-mean)/sd,-8,8)@beta
threshold=float(np.quantile(ptrain,.75))
recv_score=predict(actual_X['T24_T12_AH_path'],params)
recv_home=predict(actual_X['T24_T12_AH_path'],sideparams)>=.5
recv_pnl=np.where(recv_home,actual_H,actual_A)
recv_sel=recv_score>threshold
assert recv_sel.sum()==375 and abs(recv_pnl[recv_sel].sum()-15.595)<1e-5
dates=np.array([r['date'] for r in R])
months=np.array([r['date'][:7] for r in R])
leagues=np.array([str(r['league']) for r in R])
line=np.array([float(r['al']) for r in R])
prices=np.array([float(r['ah'] if home else r['aa']) for r,home in zip(R,recv_home)])
age=np.array([float(r['age_ah']) for r in R])
vig=np.array([1/float(r['ah'])+1/float(r['aa'])-1 for r in R])
reprice=np.array(['line_changed' if a['al']!=b['al'] else 'odds_changed' if a['ah']!=b['ah'] or a['aa']!=b['aa'] else 'no_change' for a,b in pairs])
# Exactly decompose Asian handicap payoff into fractional won and lost stakes.
stake_win=np.zeros(len(R));stake_loss=np.zeros(len(R))
for i,(row,bhome) in enumerate(zip(R,recv_home)):
 path='home' if bhome else 'away'
 p2=settle_score('AH',float(row['al']),path,int(row['hg']),int(row['ag']),2.)[1]
 p3=settle_score('AH',float(row['al']),path,int(row['hg']),int(row['ag']),3.)[1]
 stake_win[i]=p3-p2;stake_loss[i]=stake_win[i]-p2
assert np.max(abs(recv_pnl-(stake_win*(prices-1)-stake_loss)))<1e-7
out={'study':'M8_R60_AH_PROFIT_DECAY_MARKET_VS_OUTCOME',
 'method':'R59 exact frozen training score p75 (not a new rule) and T24/T12 AH early-path model, unchanged coefficients. Analyze WHY 2026-10 actual received Crown quote replay profitable but 2026-11 loses via identity-preserving full cohort October/November, Asian-quarter fractional-win/loss times selected odds decomposition, league-mix Kitagawa decomposition for common leagues, event-mix and source-event age. Also compute 2024/2025 full natural Oct/Nov historical roll-forward to avoid using latest actual receipts as sole evidence. All quotes from actual received R22 verified source; historic events post-retrieved. Ex-post time periods, leagues, line types cannot be selected as new trading filters. Report no true independent post-lock R59 prospective validation and no TG. No production change, OU candidate irrelevant.',
 'source':{'actual_R22_received_pairs':len(R),'selected':int(recv_sel.sum()),'dates':[str(min(dates)),str(max(dates))],'training_n':len(train),'side_training_n':len(trside),
  'p75_training_threshold':round(threshold,7)},'history':{},'actual':{},'decomposition':{},'foundation':{}}
def stats(v):
 v=np.asarray(v,float);return {'n':int(len(v)),'U':round(float(v.sum()),3),'ROI':round(100*float(v.mean()),3) if len(v) else None,
  'wins':int((v>1e-10).sum()),'losses':int((v<-1e-10).sum()),'pushes':int((abs(v)<=1e-10).sum())}
def quant(v):
 v=np.asarray(v,float)
 return {'mean':round(float(v.mean()),5),'median':round(float(np.median(v)),5),
 'q10':round(float(np.quantile(v,.1)),5),'q90':round(float(np.quantile(v,.9)),5)} if len(v) else None
def diag(mask):
 idx=np.flatnonzero(mask)
 if not len(idx):return {'AH_result':stats([])}
 by_event={k:{'n':int(sum(reprice[idx]==k)),'pnl':stats(recv_pnl[idx[reprice[idx]==k]])} for k in ('line_changed','odds_changed','no_change')}
 return {'AH_result':stats(recv_pnl[idx]),'league_n':len(set(leagues[idx])),
  'month_counts':dict(collections.Counter(months[idx])),
  'future_T1_member_posthoc':int(true_R_membership[idx].sum()),
  'prediction_score':quant(recv_score[idx]),'T12_source_age_hours':quant(age[idx]),
  'selected_decimal_price':quant(prices[idx]),'Crown_AH_margin_proxy':quant(vig[idx]),
  'AH_abs_line':quant(abs(line[idx])),
  'home_side_percent':round(100*float(recv_home[idx].mean()),3),
  'won_stake_fraction':quant(stake_win[idx]),'lost_stake_fraction':quant(stake_loss[idx]),
  'reprice_before_T12':by_event}
for name,m in [('all',np.ones(len(R),bool)),('R59_path_p75',recv_sel),
 ('R59_path_p90',recv_score>np.quantile(ptrain,.90)),
 ('R59_path_p75_no_future_T1_member_POSTHOC',recv_sel&~true_R_membership)]:
 out['actual'][name]={mo:diag(m&(months==mo)) for mo in ('2026-10','2026-11')}
 out['actual'][name]['all']=diag(m)
 print('REAL',name,{m0:r['AH_result'] for m0,r in out['actual'][name].items()},flush=True)
# Exact finite-sample arithmetic decomposition of Oct->Nov average net AH return.
# ROI = E[win]*(E[odds]-1) - E[loss] + Cov(win,odds).
months_select={}
for mo in ('2026-10','2026-11'):
 idx=np.flatnonzero(recv_sel&(months==mo))
 w=stake_win[idx];l=stake_loss[idx];p=prices[idx]
 c=float(np.mean((w-w.mean())*(p-p.mean())))
 months_select[mo]={'n':len(idx),'mean_win':float(w.mean()),'mean_loss':float(l.mean()),
  'mean_price':float(p.mean()),'cov_win_price':c,
  'ROI':float(100*recv_pnl[idx].mean())}
v0,v1=months_select['2026-10'],months_select['2026-11']
dprice=v1['mean_price']-v0['mean_price']
dw=v1['mean_win']-v0['mean_win']
dl=v1['mean_loss']-v0['mean_loss']
dc=v1['cov_win_price']-v0['cov_win_price']
avgw=.5*(v0['mean_win']+v1['mean_win'])
avgprice=.5*(v0['mean_price']+v1['mean_price'])
parts={'selected_price_shift_pp':100*avgw*dprice,
  'winning_stake_fraction_shift_pp':100*(avgprice-1)*dw,
  'losing_stake_fraction_shift_pp':-100*dl,
  'win_price_covariance_shift_pp':100*dc}
assert abs(sum(parts.values())-(v1['ROI']-v0['ROI']))<1e-8
out['decomposition']['exact_AH_payout_oct_to_nov']={'months':months_select,
 'oct_to_nov_roi_pp':round(v1['ROI']-v0['ROI'],5),
 'price_vs_realized_stake_contribution_pp':{k:round(v,5) for k,v in parts.items()}}
print('PAYOFF_DECOMP',out['decomposition']['exact_AH_payout_oct_to_nov'],flush=True)
# Same league cohort common support Kitagawa (exact decomposition within normalized
# common-league subpopulation). Non-common ligue coverage accounted separately.
m0=recv_sel&(months=='2026-10');m1=recv_sel&(months=='2026-11')
ls0=set(leagues[m0]);ls1=set(leagues[m1]);common=sorted(ls0&ls1)
only0=sorted(ls0-ls1);only1=sorted(ls1-ls0)
mc0=m0&np.isin(leagues,common);mc1=m1&np.isin(leagues,common)
kk={}
w0=[];w1=[];r0=[];r1=[]
for l in common:
 a0=recv_pnl[mc0&(leagues==l)];a1=recv_pnl[mc1&(leagues==l)]
 w0.append(len(a0)/int(mc0.sum()));w1.append(len(a1)/int(mc1.sum()))
 r0.append(float(a0.mean()));r1.append(float(a1.mean()))
 kk[l]={'oct':stats(a0),'nov':stats(a1)}
w0=np.array(w0);w1=np.array(w1);r0=np.array(r0);r1=np.array(r1)
within=100*float(np.sum(.5*(w0+w1)*(r1-r0)))
compo=100*float(np.sum(.5*(r0+r1)*(w1-w0)))
diff=100*(float(recv_pnl[mc1].mean())-float(recv_pnl[mc0].mean()))
assert abs(within+compo-diff)<1e-8
# Bootstrap whole kickoff UTC days, not each matched event independently;
# this is descriptive within the previously examined R59 receipt archive.
def byday_difference(mask0,mask1,reps=5000,seed=600):
 rng=np.random.default_rng(seed)
 def groups(m):
  aggregate=collections.defaultdict(list)
  for i in np.flatnonzero(m):aggregate[dates[i]].append(float(recv_pnl[i]))
  return np.array([(sum(v),len(v)) for v in aggregate.values()],float)
 a0=groups(mask0);a1=groups(mask1)
 rr0=rng.integers(len(a0),size=(reps,len(a0)))
 rr1=rng.integers(len(a1),size=(reps,len(a1)))
 r0=100*a0[rr0,0].sum(1)/a0[rr0,1].sum(1)
 r1=100*a1[rr1,0].sum(1)/a1[rr1,1].sum(1)
 return {'Oct_unique_days':len(a0),'Nov_unique_days':len(a1),
  'ROI_gap_Nov_minus_Oct_pp_95pct':list(map(lambda x:round(float(x),3),np.quantile(r1-r0,[.025,.975]))),
  'method':'independent resampling of complete UTC kickoff days within each month; descriptive, not a prospective model validation'}
out['decomposition']['UTC_day_cluster_uncertainty']=byday_difference(m0,m1)
print('DAILY_CI',out['decomposition']['UTC_day_cluster_uncertainty'],flush=True)
out['decomposition']['same_leagues_oct_nov']={
 'common_leagues':len(common),'Oct_only_leagues':len(only0),'Nov_only_leagues':len(only1),
 'Oct_common_games':int(mc0.sum()),'Nov_common_games':int(mc1.sum()),
 'Oct_noncommon_games':int((m0&~mc0).sum()),'Nov_noncommon_games':int((m1&~mc1).sum()),
 'Oct_common_ROI_pct':round(float(100*recv_pnl[mc0].mean()),5),
 'Nov_common_ROI_pct':round(float(100*recv_pnl[mc1].mean()),5),
 'Nov_minus_Oct_same_league_pp':round(diff,5),
 'within_league_contribution_pp':round(within,5),
 'league_weight_contribution_pp':round(compo,5),
 'league_details':kk}
print('LEAGUE_DECOMP',{k:v for k,v in out['decomposition']['same_leagues_oct_nov'].items() if k!='league_details'},flush=True)
# League-standardized October/November payoff on fixed OCT side and mean
# quote odds, with actual Nov win/loss stakes. Provides an exact ex post
# payout counterfactual only, not executable Oct quotes on Nov fixtures.
ix0=np.flatnonzero(m0);ix1=np.flatnonzero(m1)
p0=float(prices[ix0].mean())
out['decomposition']['Nov_with_Oct_mean_price_counterfactual']={
 'Oct_mean_price':round(p0,5),'Nov_actual_mean_price':round(float(prices[ix1].mean()),5),
 'Nov_if_all_given_Oct_mean_price_ROI_pct':round(float(100*np.mean(stake_win[ix1]*(p0-1)-stake_loss[ix1])),5),
 'caveat':'Not executable: quote price from Oct fixtures substituted for Nov matches, which have different handicaps, teams and odds distributions.'}
# R59 historical 2024-26 natural Oct-Nov same-time archived fixtures;
# training on strictly earlier years and excl. actual-receipt FIDs.
for year in (2024,2025,2026):
 tr=np.flatnonzero((years<year)&excluded_receipts)
 trside=np.flatnonzero((years<year)&excluded_receipts&valid_side)
 _,train_pr,mp=fit(data,membership,tr,tr)
 _,_,sp=fit(data,side,trside,trside)
 pred=predict(data,mp);home=predict(data,sp)>=.5
 chosen=pred>np.quantile(train_pr,.75)
 payoff=np.where(home,H,A)
 out['history'][str(year)]={}
 for mo in ('10','11'):
  use=(years==year)&(np.array([z[1]['date'][-2:] for z in h6])==mo)
  # Intentional: matches already in receipt archive can overlap historical.
  no_actual=use&excluded_receipts
  out['history'][str(year)][mo]={
   'all_test':stats(payoff[use&chosen]),
   'disjoint_actual_receipts':stats(payoff[no_actual&chosen]),
   'cohort_test_n':int(use.sum()),
   'train_sample_n':int(tr.size)}
 print('HISTORY',year,out['history'][str(year)],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_r60_profit_decay_oct_nov_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('R60_SAVED',flush=True)
