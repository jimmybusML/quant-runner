#!/usr/bin/env python3
"""Walk-forward test of prior referee-specific Crown AH residuals.

The target referee assignment comes from a retrospective Transfermarkt archive;
its original announcement/receipt time is unavailable. All results are
historical event-time research, not live execution evidence.
"""
from __future__ import annotations
import bisect, collections, csv, datetime as dt, gzip, hashlib, json, math, pathlib, re, sys, io
from zoneinfo import ZoneInfo
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[3]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
SRC=WORK/'m8_pregame_info_source_20261117'
sys.path.insert(0,str(ROOT))
OUT=ROOT/'research/m8/referee_market_residual_20261120'
PATH=WORK/'m8_late_full_path_water_features_20261114.jsonl'
SCORES=WORK/'m8_independent_score_strength_20261114.jsonl'
FOUNDATION=WORK/'m8_foundation_20261115/historical_membership.jsonl'
RECEIPTS=WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
MANAGER_SCRIPT=ROOT/'research/m8/m8_prior_manager_turnover_20261117.py'
RIDGE=100.0
LAG_DAYS=3
WINDOW_DAYS=365
PRIOR_STRENGTH=5.0


def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def read(path):
 with open(path,encoding='utf-8') as f:
  for line in f:
   if line.strip():yield json.loads(line)

def parse_utc(value):
 x=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
 if x.tzinfo is None:x=x.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
 return x.astimezone(dt.timezone.utc)

def ref_norm(value):
 import unicodedata
 s=unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]','',s)

def settle(line,side,gd,odds):
 line=float(line);odds=float(odds)
 if abs(line*4-round(line*4))>1e-8:raise ValueError(f'unsupported AH line {line}')
 handicap=line if side=='home' else -line
 margin=int(gd) if side=='home' else -int(gd)
 q=round(handicap*4)
 legs=(math.floor(handicap*2)/2,math.floor(handicap*2)/2+.5) if q%2 else (handicap,)
 outcomes=[]
 for leg in legs:
  adj=margin+leg
  outcomes.append(odds-1 if adj>1e-9 else -1. if adj< -1e-9 else 0.)
 net=sum(outcomes)/len(outcomes)
 labels=[]
 for x in outcomes:labels.append('W' if x>0 else 'L' if x<0 else 'P')
 state=('full_'+('win' if net>0 else 'loss') if 'P' not in labels else 'push' if net==0 else 'half_'+('win' if net>0 else 'loss'))
 return state,net

def normal_cdf(x):return .5*(1+math.erf(x/math.sqrt(2)))
def margin_pmf(mu,sigma,lo=-12,hi=12):
 sigma=max(float(sigma),.35)
 p=[max(0.,normal_cdf((k+.5-mu)/sigma)-normal_cdf((k-.5-mu)/sigma)) for k in range(lo,hi+1)]
 sm=sum(p)
 return [(lo+i,v/sm) for i,v in enumerate(p)]
def ev_pair(line,ho,ao,mu,sigma):
 dist=margin_pmf(mu,sigma)
 eh=sum(p*settle(line,'home',gd,ho)[1] for gd,p in dist)
 ea=sum(p*settle(line,'away',gd,ao)[1] for gd,p in dist)
 if abs(eh-ea)<1e-12:return None,eh,ea
 return ('home' if eh>ea else 'away'),eh,ea

def fit_ridge(x,y,alpha=RIDGE):
 x=np.asarray(x,float);y=np.asarray(y,float)
 mean=x.mean(axis=0);scale=x.std(axis=0);scale=np.where(scale<1e-10,1.,scale)
 z=(x-mean)/scale
 design=np.column_stack([np.ones(len(z)),z]);pen=np.eye(design.shape[1])*alpha;pen[0,0]=0.
 coef=np.linalg.solve(design.T@design+pen,design.T@y)
 pred=design@coef
 sigma=float(np.sqrt(np.mean((y-pred)**2)))
 return {'mean':mean,'scale':scale,'coef':coef,'sigma':max(.35,sigma),'n':len(y),'alpha':alpha}
def predict(model,x):
 z=(np.asarray(x,float)-model['mean'])/model['scale']
 return float(np.r_[1.,z]@model['coef'])

def metric(rows,method):
 bets=[r for r in rows if r['methods'][method]['side'] is not None]
 n=len(bets);u=sum(r['methods'][method]['net_u'] for r in bets)
 daily=collections.defaultdict(float);weekly=collections.defaultdict(lambda:[0,0.]);league=collections.defaultdict(lambda:[0,0.]);settles=collections.Counter()
 for r in bets:
  m=r['methods'][method];daily[r['date']]+=m['net_u'];weekly[r['iso_week']][0]+=1;weekly[r['iso_week']][1]+=m['net_u'];league[r['league']][0]+=1;league[r['league']][1]+=m['net_u'];settles[m['settlement']]+=1
 cum=peak=mdd=0.
 for day in sorted(daily):cum+=daily[day];peak=max(peak,cum);mdd=max(mdd,peak-cum)
 dates=[r['date'] for r in rows];span=(dt.date.fromisoformat(max(dates))-dt.date.fromisoformat(min(dates))).days//7+1 if dates else 0
 return {'orders':n,'no_bet':len(rows)-n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'mdd_u':round(mdd,6),'avg_orders_per_calendar_week':round(n/span,6) if span else 0,'calendar_weeks':span,'settlements':dict(settles),'weekly':{k:{'n':v[0],'net_u':round(v[1],6)} for k,v in sorted(weekly.items())},'league':{k:{'n':v[0],'net_u':round(v[1],6),'roi_pct':round(100*v[1]/v[0],6)} for k,v in sorted(league.items())}}
def netmetrics(rows):
 n=len(rows);u=sum(float(r['net_u']) for r in rows);daily=collections.defaultdict(float)
 for r in rows:daily[r['date']]+=float(r['net_u'])
 cum=peak=mdd=0.
 for day in sorted(daily):cum+=daily[day];peak=max(peak,cum);mdd=max(mdd,peak-cum)
 span=(dt.date.fromisoformat(max(r['date'] for r in rows))-dt.date.fromisoformat(min(r['date'] for r in rows))).days//7+1 if rows else 0
 return {'orders':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'mdd_u':round(mdd,6),'avg_orders_per_calendar_week':round(n/span,6) if span else 0,'calendar_weeks':span}

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 # Reuse the already audited Crown<->Transfermarkt identity bridge. Execute
 # only the manager script prefix that constructs H/R/teammap/allft/tmrec;
 # no coach features or outputs are executed.
 src=MANAGER_SCRIPT.read_text();marker='# Build historical coach timeline'
 if marker not in src:raise RuntimeError('audited bridge marker missing')
 ns={'__file__':str(MANAGER_SCRIPT),'__name__':'m8_referee_bridge_readonly'}
 exec(compile(src[:src.index(marker)],str(MANAGER_SCRIPT)+'[audited bridge prefix]','exec'),ns)
 teammap=ns['teammap'];allft=ns['allft'];cm=ns['cm'];compdate=ns['compdate'];tmrec=ns['tmrec']
 paths={str(r['fid']):r for r in read(PATH)};scores={str(r['fid']):r for r in read(SCORES)}
 frozen={str(r['fid']):r for r in read(FOUNDATION)};receipt_ids={str(r['fixture_id']) for r in read(RECEIPTS)}
 issues=collections.Counter();games=[]
 for fid,p in paths.items():
  s=scores.get(fid);ft=allft.get(fid)
  if not s or ft is None:issues['missing_score_or_cached_ft_identity']+=1;continue
  lid,hid,aid,hn,an,hg,ag,source_day=ft
  if (str(lid),str(hid),str(aid),str(hg),str(ag))!=(str(s['league']),str(s['home']),str(s['away']),str(s['hg']),str(s['ag'])):issues['fixture_identity_conflict']+=1;continue
  home_tm=teammap.get((str(lid),str(hid)));away_tm=teammap.get((str(lid),str(aid)));comp=cm.get(str(lid))
  if not home_tm or not away_tm or not comp:issues['unmapped_team_or_competition']+=1;continue
  ko=parse_utc(s['ko']);local=ko.astimezone(ZoneInfo('Asia/Shanghai'));target_date=local.date();candidates=[]
  for ordinal in (target_date.toordinal()-1,target_date.toordinal(),target_date.toordinal()+1):
   for t in compdate.get((comp,ordinal),[]):
    if t[2]==home_tm and t[3]==away_tm and t[4]==int(s['hg']) and t[5]==int(s['ag']):candidates.append(t)
  if len(candidates)!=1:issues['tm_target_'+('unmatched' if not candidates else 'ambiguous')]+=1;continue
  tm=tmrec[candidates[0][-1]];ref=str(tm.get('referee') or '').strip()
  if not ref:issues['missing_target_referee']+=1;continue
  line=float(p['end_line']);ho=float(p['home_price']);ao=float(p['away_price']);gd=int(s['hg'])-int(s['ag'])
  _,check_home=settle(line,'home',gd,ho);_,check_away=settle(line,'away',gd,ao)
  if abs(check_home-float(p['end_home_U']))>1e-8 or abs(check_away-float(p['end_away_U']))>1e-8:issues['path_ah_settlement_mismatch']+=1;continue
  market_margin=-line+.25*math.log(ao/ho)
  refkey=(str(lid),ref_norm(ref))
  if not refkey[1]:issues['invalid_referee_name']+=1;continue
  iso=local.date().isocalendar();iso_week=f'{iso.year}-W{iso.week:02d}'
  games.append({'fid':fid,'year':local.year,'date':local.date().isoformat(),'iso_week':iso_week,'kickoff_beijing':local.isoformat(),'league':str(lid),'league_name':str(p['league']),'home':str(s['home']),'away':str(s['away']),'home_tm_id':home_tm,'away_tm_id':away_tm,'tm_game_id':str(tm['game_id']),'referee':ref,'referee_key':refkey,'hg':int(s['hg']),'ag':int(s['ag']),'gd':gd,'line':line,'home_odds':ho,'away_odds':ao,'market_margin':market_margin,'raw_market_residual':gd-market_margin,'frozen_eight_overlap':fid in frozen,'receipt_archive_fid_overlap':fid in receipt_ids,'source_type':'historical Crown source-event T1 quote; retrospective replay','referee_source':'Transfermarkt historical game row; target referee announcement/receipt time unavailable'})
 games.sort(key=lambda x:(x['date'],x['fid']))
 # Build strictly prior (>=3 Beijing-day embargo) ref-specific residual features.
 refhist=collections.defaultdict(list);comphist=collections.defaultdict(list);daily=collections.defaultdict(list)
 for r in games:daily[r['date']].append(r)
 feature_rows=[]
 for day in sorted(daily):
  current=daily[day];daydate=dt.date.fromisoformat(day)
  cutoff=daydate-dt.timedelta(days=LAG_DAYS);window=cutoff-dt.timedelta(days=WINDOW_DAYS)
  for r in current:
   rh=[x for x in refhist[r['referee_key']] if window<=dt.date.fromisoformat(x[0])<cutoff]
   ch=[x for x in comphist[r['league']] if window<=dt.date.fromisoformat(x[0])<cutoff]
   rn=len(rh);cn=len(ch);refmean=sum(x[1] for x in rh)/rn if rn else 0.;compmean=sum(x[1] for x in ch)/cn if cn else 0.
   effect=rn/(rn+PRIOR_STRENGTH)*(refmean-compmean) if rn else 0.
   r['ref_prior_n_365']=rn;r['comp_prior_n_365']=cn;r['ref_prior_max_date_365']=max((x[0] for x in rh),default=None);r['comp_prior_max_date_365']=max((x[0] for x in ch),default=None);r['ref_prior_mean_market_residual_365']=round(refmean,8) if rn else None
   r['comp_prior_mean_market_residual_365']=round(compmean,8) if cn else None;r['ref_centered_residual_365_shrunk']=round(effect,8)
   r['feature_cutoff']='previous Beijing dates at least 3 days before target; trailing 365 days only'
   r['methods']={};feature_rows.append(r)
  # Apply all same-date result updates only after every date's features are frozen.
  for r in current:
   item=(day,r['raw_market_residual'])
   refhist[r['referee_key']].append(item);comphist[r['league']].append(item)
 methods=['low_price','market_model','market_plus_ref','ref_only','market_plus_ref_positive_ev']
 predictions=[];folds={};fold_rows={}
 for year in (2024,2025,2026):
  train=[r for r in games if r['year']<year and r['year']>=2019]
  test=[r for r in games if r['year']==year]
  if not train or not test:continue
  def market_features(r):return [r['market_margin'],r['line'],.25*math.log(r['away_odds']/r['home_odds'])]
  def combined_features(r):return market_features(r)+[r['ref_centered_residual_365_shrunk'],math.log1p(r['ref_prior_n_365'])]
  def ref_features(r):return [r['ref_centered_residual_365_shrunk'],math.log1p(r['ref_prior_n_365'])]
  models={'market_model':fit_ridge([market_features(r) for r in train],[r['gd'] for r in train]),'market_plus_ref':fit_ridge([combined_features(r) for r in train],[r['gd'] for r in train]),'ref_only':fit_ridge([ref_features(r) for r in train],[r['gd'] for r in train])}
  folds[str(year)]={'train_n':len(train),'test_n':len(test),'training_years':sorted({r['year'] for r in train}),'ridge_alpha':RIDGE,'prior_ref_window_days':WINDOW_DAYS,'same_comp_prior_shrinkage_strength':PRIOR_STRENGTH,'prior_ref_min_lag_days':LAG_DAYS,'model_sigma':{m:round(mod['sigma'],8) for m,mod in models.items()},'model_n':{m:mod['n'] for m,mod in models.items()},'model_fit':{m:{'feature_mean':np.round(mod['mean'],8).tolist(),'feature_scale':np.round(mod['scale'],8).tolist(),'standardized_coefficients_intercept_first':np.round(mod['coef'],8).tolist()} for m,mod in models.items()}}
  for r in test:
   sides={};predm={}
   for name,feat in [('market_model',market_features),('market_plus_ref',combined_features),('ref_only',ref_features)]:
    mu=predict(models[name],feat(r));predm[name]=mu
    side,eh,ea=ev_pair(r['line'],r['home_odds'],r['away_odds'],mu,models[name]['sigma'])
    sides[name]={'side':side,'predicted_home_margin':round(mu,8),'ev_home_u':round(eh,8),'ev_away_u':round(ea,8),'sigma':round(models[name]['sigma'],8)}
   low='home' if r['home_odds']<=r['away_odds'] else 'away'
   sides['low_price']={'side':low}
   ev=sides['market_plus_ref']['ev_home_u'],sides['market_plus_ref']['ev_away_u']
   best=max(ev)
   sides['market_plus_ref_positive_ev']={'side':sides['market_plus_ref']['side'] if best>0 else None,'best_predicted_ev_u':round(best,8)}
   for name,m in sides.items():
    side=m['side']
    if side is None:m.update({'settlement':'no_bet','net_u':0.});continue
    odds=r['home_odds'] if side=='home' else r['away_odds'];state,u=settle(r['line'],side,r['gd'],odds)
    m.update({'settlement':state,'net_u':round(u,10)})
   r['fold_train_n']=len(train);r['model_predictions']=predm;r['methods']=sides
   predictions.append(r)
  fold_rows[year]=test
 predictions.sort(key=lambda r:(r['date'],r['fid']))
 incr=[r for r in predictions if not r['frozen_eight_overlap']]
 results={'same_matched_cohort_all':{},'outside_frozen_eight':{},'outside_by_year':{},'by_year':{}}
 prediction_quality={}
 for y in (2024,2025,2026):
  cohort=[r for r in predictions if r['year']==y and not r['frozen_eight_overlap']]
  if cohort:
   prediction_quality[str(y)]={}
   for name in ('market_model','market_plus_ref','ref_only'):
    err=np.array([r['gd']-r['model_predictions'][name] for r in cohort],float)
    prediction_quality[str(y)][name]={'n':len(cohort),'mae':round(float(np.mean(np.abs(err))),8),'rmse':round(float(np.sqrt(np.mean(err**2))),8)}
 for m in methods:
  results['same_matched_cohort_all'][m]=metric(predictions,m);results['outside_frozen_eight'][m]=metric(incr,m)
 for y in (2024,2025,2026):
  cohort=[r for r in predictions if r['year']==y];outside=[r for r in cohort if not r['frozen_eight_overlap']]
  if cohort:results['by_year'][str(y)]={m:metric(cohort,m) for m in methods};results['outside_by_year'][str(y)]={m:metric(outside,m) for m in methods}
 # FID union against synchronous frozen eight-year cohort; each fixture counted once.
 frozen_target=[]
 for fid,r in frozen.items():
  y=int(r['year'])
  if y not in (2024,2025,2026):continue
  frozen_target.append({'fid':fid,'date':str(r['date'])[:10],'year':y,'net_u':float(r['pnl'])})
 union={m:None for m in methods}
 for m in methods:
  selected=[{'fid':r['fid'],'date':r['date'],'year':r['year'],'net_u':r['methods'][m]['net_u']} for r in incr if r['methods'][m]['side'] is not None]
  merged={r['fid']:r for r in frozen_target}
  for r in selected:
   if r['fid'] in merged:raise AssertionError('incremental FID overlap frozen')
   merged[r['fid']]=r
  union[m]={'frozen_target':netmetrics(frozen_target),'incremental_outside_frozen':netmetrics(selected),'merged_unique_fid':netmetrics(list(merged.values())),'candidate_overlap_frozen':len(set(r['fid'] for r in selected)&set(r['fid'] for r in frozen_target))}
 # Separate actual HTTP receipt intersection, without claiming source features were received then.
 receipt_rows=list(read(RECEIPTS));receipt_fids={str(r['fixture_id']) for r in receipt_rows}
 receipt_overlap=sorted({r['fid'] for r in games if r['fid'] in receipt_fids})
 joined_ref_ids={r['fid'] for r in games}
 summary={'study':'Historical referee-specific Crown AH market-residual test; referees from retrospective archive, target assignment first-known time unavailable.','data':{'path_rows':len(paths),'score_rows':len(scores),'mapped_referee_rows':len(games),'prediction_rows_2024_2026':len(predictions),'unique_fids':len({r['fid'] for r in predictions}),'outside_frozen_2024_2026':len({r['fid'] for r in incr if r['year']>=2024}),'receipt_archive_total_rows':len(receipt_rows),'receipt_archive_fid_intersection_with_referee_history':len(receipt_overlap),'receipt_archive_joined_model_predictions':sum(r['fid'] in receipt_fids for r in predictions),'coverage_issues':dict(issues),'mapped_years':dict(collections.Counter(r['year'] for r in games)),'mapped_leagues':dict(collections.Counter(r['league_name'] for r in games)),'referee_count':len({r['referee_key'] for r in games})},'inputs':{str(p):sha(p) for p in (PATH,SCORES,FOUNDATION,RECEIPTS,SRC/'games.csv.gz',MANAGER_SCRIPT)},'methodology':{'identity':'Reuse the audited R49 team/competition bridge from m8_prior_manager_turnover_20261117.py. Target TM fixture requires same competition, mapped home/away club IDs, FT, and date within +/-1 day; ambiguous matches are excluded. Referee names are normalized exact strings, no fuzzy referee matching.','feature':'For each referee and competition, trailing 365-day mean of earlier Crown AH actual goal-difference minus Crown-implied home margin; subtract trailing same-competition residual mean and shrink by n/(n+5). Use only matches ending at least 3 Beijing calendar days before target. Same-day features snapshot before any same-day updates.','target':'Target outcome is home goal difference. Crown-implied home margin = -AH_home_line + 0.25*ln(away_odds/home_odds).','models':'Expanding years: train 2019 through year-before; fixed Ridge alpha 100 after training-fold feature standardization; market-only [market margin, line, water adjustment], market+ref adds shrunken referee residual and log prior-ref sample count; ref-only diagnostic.','AH_EV':'Predicted goal-margin normal distribution discretized to integer margins -12..12 with training residual RMSE as sigma; choose side with larger expected Crown AH settlement. Also report no-bet diagnostic when both predicted sides EV<=0; it is experimental evaluation only.','leakage':'No target score enters its features/model. Referee histories update only after the full Beijing date. The target referee name is drawn from the retrospective game archive and has no verified pregame announcement/receipt timestamp; this is not a verified contemporaneous prediction.'},'folds':folds,'prediction_quality_outside_frozen_2024_2026':prediction_quality,'results':results,'merged_with_frozen_eight_2024_2026':union,'receipt_fid_overlap_sample':receipt_overlap,'production_changes':False,'formal_orders':0,'formal_ledger_writes':0}
 (OUT/'referee_market_residual_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 with io.TextIOWrapper(gzip.GzipFile(filename=str(OUT/'referee_market_residual_per_fixture.jsonl.gz'),mode='wb',compresslevel=9,mtime=0),encoding='utf-8') as f:
  for r in predictions:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 print(json.dumps({'data':summary['data'],'outside_2024_2026':{m:{k:v.get(k) for k in ('orders','no_bet','net_u','roi_pct','mdd_u','avg_orders_per_calendar_week','calendar_weeks')} for m,v in results['outside_frozen_eight'].items()},'annual':{y:{m:{k:v.get(k) for k in ('orders','net_u','roi_pct','mdd_u','avg_orders_per_calendar_week')} for m,v in d.items()} for y,d in results['outside_by_year'].items()},'merged':{m:{k:{q:v[k].get(q) for q in ('orders','net_u','roi_pct')} for k in ('incremental_outside_frozen','merged_unique_fid')} for m,v in union.items()}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
