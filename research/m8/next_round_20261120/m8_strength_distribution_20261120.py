#!/usr/bin/env python3
"""M8 continuous Crown-implied strength-gap distribution study (research only).
All development data are local historical Crown source-event replays, not proof
of historical HTTP receipt. AH only; quarter lines settle as two half stakes.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, math
from pathlib import Path
import numpy as np
from scipy.special import ndtr
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parents[3]
DATA=Path('/Users/mac/QuantAsiaDesk/research-work')
FEATS=DATA/'m8_late_full_path_water_features_20261114.jsonl'
MEM=DATA/'m8_foundation_20261115/historical_membership.jsonl'
OUT=ROOT/'research/m8/next_round_20261120'

def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def settle(line, side, odds, gd):
 # return for 1U stake, correctly split quarter lines
 ln=float(line) if side=='home' else -float(line)
 g=int(gd) if side=='home' else -int(gd)
 legs=[ln] if abs(ln*2-round(ln*2))<1e-9 else [math.floor(ln*2)/2,math.ceil(ln*2)/2]
 vals=[]
 for leg in legs:
  z=g+leg; vals.append(float(odds)-1 if z>1e-9 else -1. if z< -1e-9 else 0.)
 return sum(vals)/len(vals)
def state_ah(line,side,gd):
 ln=float(line) if side=='home' else -float(line);g=int(gd) if side=='home' else -int(gd)
 legs=[ln] if abs(ln*2-round(ln*2))<1e-9 else [math.floor(ln*2)/2,math.ceil(ln*2)/2]
 vals=[]
 for leg in legs:
  z=g+leg;vals.append('W' if z>1e-9 else 'L' if z< -1e-9 else 'P')
 return {'WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss','W':'full_win','L':'full_loss','P':'push'}.get(''.join(vals),vals[0])
def cdf_score(mu,sig,y):
 # Discretized normal margin distribution, scored with ranked probability score.
 edges=np.arange(-15.5,16.5,1)
 c=ndtr((edges-mu)/sig); obs=(edges>=y).astype(float)
 return float(np.mean((c-obs)**2))
def design(line, home_odds, away_odds, knots, nonlinear):
 # Continuous market-strength index: signed AH handicap plus no-vig log price ratio.
 # Positive means home-favored. Not an observed team rating or ex-post rank.
 vigor=-float(line)+0.25*math.log(float(away_odds)/float(home_odds))
 x=[1.,vigor]
 if nonlinear:
  for k in knots: x.append(max(0.,vigor-k)**3)
  # Contract interaction lets the mapping from strength gap vary by contract size.
  x += [vigor*abs(float(line)), float(line)*abs(float(line))]
 return np.array(x,dtype=float)
def fit_margin(X,y,scale=1.0):
 # Gaussian location-scale likelihood with fixed ridge penalty on mean coefficients.
 n,p=X.shape
 def obj(b):
  beta=b[:p]; logs=max(-1.,min(2.,b[p])); sig=np.exp(logs)
  z=(y-X@beta)/sig
  return n*logs+0.5*np.dot(z,z)+0.5*scale*np.dot(beta[1:],beta[1:])
 init=np.r_[np.linalg.lstsq(X,y,rcond=None)[0],np.log(max(np.std(y-X@np.linalg.lstsq(X,y,rcond=None)[0]),1.0))]
 res=minimize(obj,init,method='L-BFGS-B',bounds=[(None,None)]*p+[(-1,2)],options={'maxiter':500,'ftol':1e-11})
 if not res.success and not np.isfinite(res.fun):raise RuntimeError(res.message)
 return res.x[:p],float(np.exp(res.x[p]))
def predict_distribution(row,beta,sig):
 x=design(row['line'],row['home_price'],row['away_price'],row['knots'],row['nonlinear'])
 mu=float(x@beta)
 # Discrete margin probabilities from continuous normal CDF, tails collapsed at +/-15.
 probs=[]
 for g in range(-14,15): probs.append(float(ndtr((g+0.5-mu)/sig)-ndtr((g-0.5-mu)/sig)))
 probs=[float(ndtr((-14.5-mu)/sig))]+probs+[float(1-ndtr((14.5-mu)/sig))]
 vals=list(range(-15,16)); z=sum(probs); probs=[max(0.,p/z) for p in probs]
 return mu,sig,vals,probs
def expected_ah(line,odds,side,vals,probs):
 return sum(p*settle(line,side,odds,g) for p,g in zip(probs,vals))
def stats(rows):
 n=len(rows);u=sum(x['net_u'] for x in rows)
 d=collections.defaultdict(float);w=collections.defaultdict(lambda:[0,0.])
 for x in rows:
  d[x['date']]+=x['net_u']; iso=dt.date.fromisoformat(x['date']).isocalendar();wk=f'{iso.year}-W{iso.week:02d}';w[wk][0]+=1;w[wk][1]+=x['net_u']
 eq=peak=mdd=0.
 for day,v in sorted(d.items()):eq+=v;peak=max(peak,eq);mdd=max(mdd,peak-eq)
 return {'n':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'mdd_u':round(mdd,6),'weeks':{k:{'n':int(v[0]),'net_u':round(v[1],6)} for k,v in sorted(w.items())}}
def main():
 members=[json.loads(l) for l in MEM.open() if l.strip()];frozen={str(x['fid']) for x in members}; assert len(frozen)==10294
 scores={str(z['fid']):z for z in map(json.loads,(DATA/'m8_independent_score_strength_20261114.jsonl').open())}
 rows=[];bad=collections.Counter()
 for s in FEATS.open():
  x=json.loads(s);fid=str(x['fid'])
  if fid in frozen:continue
  try:
   if int(x['year'])<2023:continue
   line=float(x['end_line']);ho=float(x['home_price']);ao=float(x['away_price'])
   sc=scores.get(fid)
   if not sc: raise ValueError('verified score row missing')
   ko=dt.datetime.fromisoformat(str(sc['ko']).replace('Z','+00:00'))
   ko=ko.replace(tzinfo=dt.timezone.utc) if ko.tzinfo is None else ko.astimezone(dt.timezone.utc)
   beijing=ko.astimezone(dt.timezone(dt.timedelta(hours=8)));y=beijing.year
   hg=int(sc['hg']);ag=int(sc['ag']);gd=hg-ag
   if not (ho>1 and ao>1 and math.isfinite(line)):raise ValueError()
   rows.append({'fid':fid,'year':y,'date':beijing.date().isoformat(),'ko_utc':ko.isoformat(),'kickoff_beijing':beijing.isoformat(),'league':str(x['league']),'line':line,'home_price':ho,'away_price':ao,'gd':gd,'hg':hg,'ag':ag,'source':'historical_crown_event_time_replay','frozen_eight':False})
  except Exception:bad['missing_or_invalid_ft_quote']+=1
 # Source may hold outcomes in a separate score table; fail explicitly if not present.
 if not rows or not any('gd' in r for r in rows):raise RuntimeError('No FT in Crown feature rows; attach the verified score ledger by FID before running.')
 if len({r['fid'] for r in rows})!=len(rows):raise RuntimeError('duplicate FID in feature input')
 fhash=sha(FEATS);mhash=sha(MEM)
 # Fixed controls: market-only contract expected-return direction; linear location+scale;
 # nonlinear cubic spline location and contract interaction. Knots are training quintiles.
 ledgers=[];folds={};all_metrics={}
 for target_year in (2024,2025,2026):
  train=[r for r in rows if r['year']<target_year and r['year']>=2019]
  test=[r for r in rows if r['year']==target_year]
  if not train or not test:continue
  vig=np.array([-r['line']+0.25*math.log(r['away_price']/r['home_price']) for r in train])
  knots=np.quantile(vig,[.2,.4,.6,.8]).tolist()
  preds={}
  for model,nonlinear in [('linear',False),('spline_contract',True)]:
   xx=[];yy=[]
   for r in train:
    x=dict(r,knots=knots,nonlinear=nonlinear);xx.append(design(r['line'],r['home_price'],r['away_price'],knots,nonlinear));yy.append(r['gd'])
   beta,sig=fit_margin(np.asarray(xx),np.asarray(yy,dtype=float),scale=1.0)
   preds[model]=(beta,sig)
  modelrows={k:[] for k in ('market_contract','linear','spline_contract')}
  foldpred=[]
  for r in test:
   base=dict(r,knots=knots,nonlinear=False)
   # Crown contract market benchmark: home cover probability from price ratio, push ignored;
   # for AH expected net U use the two-side market probabilities directly.
   qh=1/r['home_price'];qa=1/r['away_price'];ph=qh/(qh+qa);pa=1-ph
   mu_l,sig_l,v_l,p_l=predict_distribution(dict(base,nonlinear=False),*preds['linear'])
   mu_s,sig_s,v_s,p_s=predict_distribution(dict(base,nonlinear=True),*preds['spline_contract'])
   eh=expected_ah(r['line'],r['home_price'],'home',v_s,p_s);ea=expected_ah(r['line'],r['away_price'],'away',v_s,p_s)
   direction='home' if eh>=ea else 'away';odds=r['home_price'] if direction=='home' else r['away_price']
   pnl=settle(r['line'],direction,odds,r['gd'])
   # Two market-side implied mean payoff scores provide reference action, with push mass absent.
   mh=sum(p*settle(r['line'],'home',r['home_price'],g) for p,g in zip(p_s,v_s))
   ma=sum(p*settle(r['line'],'away',r['away_price'],g) for p,g in zip(p_s,v_s))
   # linear model prediction and market benchmark direction from fair cover approximation.
   l_eh=expected_ah(r['line'],r['home_price'],'home',v_l,p_l);l_ea=expected_ah(r['line'],r['away_price'],'away',v_l,p_l)
   ld='home' if l_eh>=l_ea else 'away';lo=r['home_price'] if ld=='home' else r['away_price']
   lp=settle(r['line'],ld,lo,r['gd'])
   # Market-only chooses the lower decimal price side (favorite), pre-defined baseline.
   md='home' if r['home_price']<=r['away_price'] else 'away';mo=r['home_price'] if md=='home' else r['away_price'];mp=settle(r['line'],md,mo,r['gd'])
   common={'fid':r['fid'],'year':r['year'],'date':r['date'],'iso_week':f"{dt.date.fromisoformat(r['date']).isocalendar().year}-W{dt.date.fromisoformat(r['date']).isocalendar().week:02d}",'league':r['league'],'crown_ah_line_home':r['line'],'crown_home_odds':r['home_price'],'crown_away_odds':r['away_price'],'direction':direction,'FT_home':r['hg'],'FT_away':r['ag'],'goal_difference_home':r['gd'],'settlement':state_ah(r['line'],direction,r['gd']),'net_u':pnl,'source_type':r['source'],'feature_cutoff':'T1 historical event-time quote; actual HTTP receipt not asserted','spline_mu':round(mu_s,6),'spline_sigma':round(sig_s,6),'spline_home_ev':round(eh,6),'spline_away_ev':round(ea,6),'predicted_net_margin_mu':round(mu_s,6),'observed_goal_diff':r['gd'],'linear_side':ld,'linear_net_u':round(lp,6),'linear_settlement':state_ah(r['line'],ld,r['gd']),'market_side':md,'market_net_u':round(mp,6),'market_settlement':state_ah(r['line'],md,r['gd']),'market_implied_home_share':round(ph,8),'probability_rps_linear':round(float(np.mean([(ndtr((k+0.5-mu_l)/sig_l)-(1 if r['gd']<=k else 0))**2 for k in range(-15,16)])),8),'probability_rps_spline':round(float(np.mean([(ndtr((k+0.5-mu_s)/sig_s)-(1 if r['gd']<=k else 0))**2 for k in range(-15,16)])),8)}
   foldpred.append(common)
   for k,rr in [('spline_contract',common),('linear',dict(common,direction=ld,net_u=lp,settlement=state_ah(r['line'],ld,r['gd']))),('market_contract',dict(common,direction=md,net_u=mp,settlement=state_ah(r['line'],md,r['gd'])))]:modelrows[k].append(rr)
  # Save fixed-knot fold training info and evaluation for all predictions.
  folds[str(target_year)]={'train_n':len(train),'test_n':len(test),'train_year_max':max(x['year'] for x in train),'knots_training_vigor_q20_q40_q60_q80':[round(float(x),8) for x in knots],'models':{k:{'beta':v[0].tolist(),'sigma':v[1]} for k,v in preds.items()}}
  for k,rr in modelrows.items():
   all_metrics.setdefault(k,{})[str(target_year)]=stats(rr)
   for z in rr:
    z['model']=k;ledgers.append(z)
  print('YEAR',target_year,{k:(v[str(target_year)]['n'],v[str(target_year)]['net_u'],v[str(target_year)]['roi_pct']) for k,v in all_metrics.items() if str(target_year) in v},flush=True)
 # Full league/week decomposition and unique-FID comparison against frozen eight.
 bygroup={}
 for model in ('market_contract','linear','spline_contract'):
  bygroup[model]={'league':{},'iso_week':{}}
  chosen=[x for x in ledgers if x['model']==model]
  for key in sorted({x['league'] for x in chosen}):bygroup[model]['league'][key]=stats([x for x in chosen if x['league']==key])
  for key in sorted({x['iso_week'] for x in chosen}):bygroup[model]['iso_week'][key]=stats([x for x in chosen if x['iso_week']==key])
 frozen_byyear=collections.defaultdict(list)
 for x in members:
  sc=scores.get(str(x['fid']))
  if sc:
   ko=dt.datetime.fromisoformat(str(sc['ko']).replace('Z','+00:00'));ko=ko.replace(tzinfo=dt.timezone.utc) if ko.tzinfo is None else ko.astimezone(dt.timezone.utc);local=ko.astimezone(dt.timezone(dt.timedelta(hours=8)))
   if 2024<=local.year<=2026:frozen_byyear[str(local.year)].append({'net_u':float(x['pnl']),'date':local.date().isoformat()})
 frozen_stats={y:stats(v) for y,v in sorted(frozen_byyear.items())}
 for y,base in frozen_stats.items():
  for model in ('market_contract','linear','spline_contract'):
   cand=all_metrics[model].get(y,{'n':0,'net_u':0.})
   base['plus_'+model]={'unique_fid_n':base['n']+cand['n'],'net_u':round(base['net_u']+cand['net_u'],6),'roi_pct':round(100*(base['net_u']+cand['net_u'])/(base['n']+cand['n']),6)}
 aggregate={m:stats([r for r in ledgers if r['model']==m and r['year']>=2024]) for m in ('market_contract','linear','spline_contract')}
 merged={}
 frozen_all=[]
 for z in members:
  sc=scores.get(str(z['fid']))
  if sc:
   ko=dt.datetime.fromisoformat(str(sc['ko']).replace('Z','+00:00'));ko=ko.replace(tzinfo=dt.timezone.utc) if ko.tzinfo is None else ko.astimezone(dt.timezone.utc);local=ko.astimezone(dt.timezone(dt.timedelta(hours=8)))
   if 2024<=local.year<=2026:frozen_all.append({'date':local.date().isoformat(),'net_u':float(z['pnl'])})
 for m in ('market_contract','linear','spline_contract'):
  merged[m]=stats(frozen_all+[{'date':r['date'],'net_u':r['net_u']} for r in ledgers if r['model']==m and r['year']>=2024])
 calibration={}
 for m in ('linear','spline_contract'):
  calibration[m]={}
  for y in (2024,2025,2026):
   sub=[r for r in ledgers if r['model']==m and r['year']==y];n=len(sub);key='probability_rps_linear' if m=='linear' else 'probability_rps_spline'
   calibration[m][str(y)]={'n':n,'margin_mae':round(sum(abs(r['predicted_net_margin_mu']-r['observed_goal_diff']) for r in sub)/n,8),'mean_cdf_rps_per_threshold':round(sum(r[key] for r in sub)/n,10),'mean_predicted_margin':round(sum(r['predicted_net_margin_mu'] for r in sub)/n,8),'mean_observed_margin':round(sum(r['observed_goal_diff'] for r in sub)/n,8)}
  sub=[r for r in ledgers if r['model']==m and r['year']>=2024];n=len(sub);key='probability_rps_linear' if m=='linear' else 'probability_rps_spline'
  calibration[m]['2024_2026']={'n':n,'margin_mae':round(sum(abs(r['predicted_net_margin_mu']-r['observed_goal_diff']) for r in sub)/n,8),'mean_cdf_rps_per_threshold':round(sum(r[key] for r in sub)/n,10),'mean_predicted_margin':round(sum(r['predicted_net_margin_mu'] for r in sub)/n,8),'mean_observed_margin':round(sum(r['observed_goal_diff'] for r in sub)/n,8)}
 # Write artifacts.
 OUT.mkdir(parents=True,exist_ok=True)
 with gzip.open(OUT/'per_fixture_walkforward_20261120.jsonl.gz','wt',encoding='utf8') as f:
  for r in ledgers:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 result={'study':'continuous Crown AH contract-strength gap; time-forward discrete-margin distribution calibration','as_of_beijing':dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),'scope':'AH only; original eight FIDs removed by unique FID; no production or formal orders','hypotheses':{'B':'Continuous market-implied strength gap may map nonlinearly to FT margin; asymmetric-tail calibration and handicap contract interaction may reveal errors not captured by linear residual Ridge.','D':'Special competition-stage labels not available in current match-time schema; no stage proxy used.','A':'No independent timestamped strength shock field; transfer/news/lineup/recent-performance proxies already covered.','C':'No future membership identities used; prior mechanism attribution and boundary expansion overlap this family.'},'data':{'path_feature_fids':39101,'frozen_eight_unique_fids_removed':len(frozen),'candidate_rows':len(rows),'years':{str(y):sum(r['year']==y for r in rows) for y in sorted(set(r['year'] for r in rows))},'missing':dict(bad),'feature_sha256':fhash,'frozen_sha256':mhash,'FT_source':'m8_independent_score_strength_20261114.jsonl; exact FID join; quote-source event time is not receipt time.'},'training_folds':folds,'metrics':all_metrics,'aggregate_2024_2026':aggregate,'merged_2024_2026':merged,'calibration_metrics':calibration,'by_league_and_iso_week':bygroup,'frozen_eight_and_single_candidate_union_by_year':frozen_stats,'candidate_fid_set_differences':{k:{'candidate_unique_fids':sum(z['n'] for z in v.values()),'overlap_frozen_eight':0,'added_unique_fids':sum(z['n'] for z in v.values())} for k,v in all_metrics.items()},'candidate_counts':{k:sum(v['n'] for v in yrs.values()) for k,yrs in all_metrics.items()},'limits':['Historical source-event path rows were retrieved after outcomes; not actual HTTP receipt.','Full candidate action uses model expected net U on AH contract; calibration improvements are not profitability.','FT joined by unique FID from the existing score-strength ledger; original Crown source response linkage is not asserted by the score feature itself.','No ROI-based thresholds, year splits, league or order filters.']}
 (OUT/'calibration_metrics_20261120.json').write_text(json.dumps(calibration,ensure_ascii=False,indent=2)+'\n')
 (OUT/'M8_NEXT_ROUND_RESULTS_20261120.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('RESULT',json.dumps({k:{y:(v['net_u'],v['roi_pct']) for y,v in vv.items()} for k,vv in all_metrics.items()},ensure_ascii=False))
if __name__=='__main__':main()
