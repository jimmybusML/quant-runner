#!/usr/bin/env python3
"""Research-only prequential Crown-surprise strength shock and selective AH EV.

Features are updated from completed fixtures only, with an entire Beijing date
held back to avoid uncertain same-day ordering. Historical T1 event-time Crown
quotes are replay prices, not contemporaneous HTTP receipts.
"""
import collections, datetime as dt, gzip, hashlib, json, math
from pathlib import Path
import numpy as np
from scipy.special import ndtr

ROOT=Path(__file__).resolve().parents[3]
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
PATH=WORK/'m8_late_full_path_water_features_20261114.jsonl'
SCORES=WORK/'m8_independent_score_strength_20261114.jsonl'
MEM=WORK/'m8_foundation_20261115/historical_membership.jsonl'
RECEIPTS=ROOT/'research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl'
OUT=ROOT/'research/m8/next_round_20261120'
TZ=dt.timezone(dt.timedelta(hours=8))

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(p):
 with open(p,encoding='utf8') as f:
  for ln in f:
   if ln.strip():yield json.loads(ln)
def settle(line,side,odds,gd):
 z=float(line)*(1 if side=='home' else -1);g=int(gd)*(1 if side=='home' else -1)
 legs=[z] if abs(z*2-round(z*2))<1e-9 else [math.floor(z*2)/2,math.ceil(z*2)/2]
 return sum(float(odds)-1 if g+x>1e-9 else -1. if g+x< -1e-9 else 0. for x in legs)/len(legs)
def state(line,side,gd):
 z=float(line)*(1 if side=='home' else -1);g=int(gd)*(1 if side=='home' else -1)
 legs=[z] if abs(z*2-round(z*2))<1e-9 else [math.floor(z*2)/2,math.ceil(z*2)/2]
 s=''.join('W' if g+x>1e-9 else 'L' if g+x< -1e-9 else 'P' for x in legs)
 return {'WW':'win','W':'win','WP':'half_win','PW':'half_win','PP':'push','P':'push','PL':'half_loss','LP':'half_loss','LL':'loss','L':'loss'}[s]
def stats(rows):
 n=len(rows);u=sum(r['net_u'] for r in rows);daily=collections.defaultdict(float);wk=collections.defaultdict(lambda:[0,0.]);lg=collections.defaultdict(list)
 for r in rows:
  daily[r['kickoff_beijing'][:10]]+=r['net_u'];d=dt.date.fromisoformat(r['kickoff_beijing'][:10]);iy,iw,_=d.isocalendar();wk[f'{iy}-W{iw:02d}'][0]+=1;wk[f'{iy}-W{iw:02d}'][1]+=r['net_u'];lg[r['league']].append(r)
 c=p=dd=0.
 for day in sorted(daily):c+=daily[day];p=max(p,c);dd=max(dd,p-c)
 return {'n':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'mdd_u':round(dd,6),'weekly_mean_orders':round(n/max(len(wk),1),6),'weekly':{k:{'n':v[0],'net_u':round(v[1],6)} for k,v in sorted(wk.items())},'league':{k:{'n':len(v),'net_u':round(sum(x['net_u'] for x in v),6),'roi_pct':round(100*sum(x['net_u'] for x in v)/len(v),6)} for k,v in sorted(lg.items())}}
def features(r):
 vigor=-r['line']+.25*math.log(r['ao']/r['ho'])
 return np.array([1.,vigor,r['line'],math.log(r['ao']/r['ho']),r['elo_diff']/400.,r['shock_home_30']/400.,r['shock_away_30']/400.,r['shock_diff_90']/400.,r['home_matches'],r['away_matches'],r['home_positive_shock_30']/400.,r['home_negative_shock_30']/400.,r['away_positive_shock_30']/400.,r['away_negative_shock_30']/400.],float)
def fit(X,y,ridge=25.):
 mu=X.mean(axis=0);sd=X.std(axis=0);sd[sd<1e-9]=1.;Z=(X-mu)/sd;ym=float(y.mean());beta=np.linalg.solve(Z.T@Z+ridge*np.eye(Z.shape[1]),Z.T@(y-ym));res=y-(Z@beta+ym);sig=max(float(np.std(res)),.8)
 return mu,sd,ym,beta,sig
def pred_margin(x,m):
 mu,sd,ym,b,sig=m;return float(((x-mu)/sd)@b+ym),sig
def payoff_ev(line,odds,side,mu,sig):
 vals=list(range(-16,17));out=0.
 for gd in vals:
  prob=float(ndtr((gd+.5-mu)/sig)-ndtr((gd-.5-mu)/sig))
  out+=prob*settle(line,side,odds,gd)
 return out

def main():
 paths={str(x['fid']):x for x in read(PATH)};scores={str(x['fid']):x for x in read(SCORES)}
 frozen={str(x['fid']) for x in read(MEM)}
 base=[];bad=collections.Counter();score_by_fid=scores
 for fid,p in paths.items():
  s=scores.get(fid)
  if not s:bad['missing_score_join']+=1;continue
  try:
   ko=dt.datetime.fromisoformat(s['ko'].replace('Z','+00:00'));ko=ko.replace(tzinfo=dt.timezone.utc) if ko.tzinfo is None else ko.astimezone(dt.timezone.utc);local=ko.astimezone(TZ)
   if str(p['league'])!=str(s['league']):raise ValueError('league')
   line=float(p['end_line']);ho=float(p['home_price']);ao=float(p['away_price']);gd=int(s['hg'])-int(s['ag'])
   if min(ho,ao)<=1 or abs(line*4-round(line*4))>1e-8:raise ValueError('invalid_quote')
   base.append({'fid':fid,'year':local.year,'kickoff_beijing':local.isoformat(),'date':local.date().isoformat(),'league':str(s['league']),'home':str(s['home']),'away':str(s['away']),'line':line,'ho':ho,'ao':ao,'start_line':float(p.get('start_line') if p.get('start_line') is not None else line),'start_ho':float(p.get('start_home_price') if p.get('start_home_price') else ho),'start_ao':float(p.get('start_away_price') if p.get('start_away_price') else ao),'hg':int(s['hg']),'ag':int(s['ag']),'gd':gd,'ko_utc':ko.isoformat(),'frozen':fid in frozen,'receipt_only':False})
  except Exception as e:bad[str(e)]+=1
 # Add verified Crown receipt rows outside the historical T1 inventory as a
 # separate actual-receipt price replay; do not mix them into history metrics.
 receipts=[];receipt_bad=collections.Counter();receipt_archive=list(read(RECEIPTS)) if RECEIPTS.exists() else [];receipt_by_fid={}
 for rec in receipt_archive:
  fid=str(rec['fid']);old=receipt_by_fid.get(fid)
  if old is None or str(rec.get('received_utc',''))<str(old.get('received_utc','')):receipt_by_fid[fid]=rec
 if RECEIPTS.exists():
  for rec in receipt_by_fid.values():
   fid=str(rec['fid']);s=scores.get(fid)
   try:
    if not s:raise ValueError('score_FID_missing')
    ko=dt.datetime.fromisoformat(str(s['ko']).replace('Z','+00:00'));ko=ko.replace(tzinfo=dt.timezone.utc) if ko.tzinfo is None else ko.astimezone(dt.timezone.utc);local=ko.astimezone(TZ)
    if fid in {x['fid'] for x in base}:raise ValueError('receipt_overlaps_path_inventory')
    line=float(rec['crown_ah_home_line']);ho=float(rec['home_decimal']);ao=float(rec['away_decimal'])
    if min(ho,ao)<=1 or abs(line*4-round(line*4))>1e-8:raise ValueError('invalid_receipt_quote')
    if dt.datetime.fromisoformat(str(rec['ah_source_utc']).replace('Z','+00:00'))>=ko:raise ValueError('quote_event_after_kickoff')
    if dt.datetime.fromisoformat(str(rec['received_utc']).replace('Z','+00:00'))>=ko:raise ValueError('receipt_after_kickoff')
    row={'fid':fid,'year':local.year,'kickoff_beijing':local.isoformat(),'date':local.date().isoformat(),'league':str(s['league']),'home':str(s['home']),'away':str(s['away']),'line':line,'ho':ho,'ao':ao,'hg':int(s['hg']),'ag':int(s['ag']),'gd':int(s['hg'])-int(s['ag']),'ko_utc':ko.isoformat(),'frozen':fid in frozen,'receipt_only':True,'receipt_meta':rec}
    base.append(row);receipts.append(row)
   except Exception as e:receipt_bad[str(e)]+=1
 base.sort(key=lambda r:(r['date'],r['fid']))
 # Sequential Elo-like ratings use Crown-implied expected home margin as the
 # baseline. Only completed prior Beijing dates update ratings.
 rating=collections.defaultdict(float);history=collections.defaultdict(list);bydate=collections.defaultdict(list)
 for r in base:bydate[r['date']].append(r)
 for day in sorted(bydate):
  for r in bydate[day]:
   h=(r['league'],r['home']);a=(r['league'],r['away']);rh=rating[h];ra=rating[a]
   r['elo_diff']=rh-ra
   # Surprise is observed GD minus the contemporaneous market-implied margin
   # proxy, not raw recent form or target-match outcome.
   mkt=-r['line']+.25*math.log(r['ao']/r['ho'])
   surprise=r['gd']-mkt
   r['surprise']=surprise
   for key in (h,a):
    hist=history[key];r['shock_home_30' if key==h else 'shock_away_30']=sum(v for date,v in hist if (dt.date.fromisoformat(day)-dt.date.fromisoformat(date)).days<=30)
   for key,prefix in ((h,'home'),(a,'away')):
    recent=[v for date,v in history[key] if (dt.date.fromisoformat(day)-dt.date.fromisoformat(date)).days<=30]
    r[prefix+'_positive_shock_30']=sum(max(0.,v) for v in recent);r[prefix+'_negative_shock_30']=sum(min(0.,v) for v in recent)
   r['shock_diff_90']=sum(v for date,v in history[h] if (dt.date.fromisoformat(day)-dt.date.fromisoformat(date)).days<=90)-sum(v for date,v in history[a] if (dt.date.fromisoformat(day)-dt.date.fromisoformat(date)).days<=90)
   r['home_matches']=len(history[h]);r['away_matches']=len(history[a])
  # Update after all same-day feature snapshots are taken; avoid same-day leakage.
  for r in bydate[day]:
   h=(r['league'],r['home']);a=(r['league'],r['away']);rd=r['elo_diff'];p=1/(1+10**(-rd/400.));actual=1. if r['gd']>0 else .5 if r['gd']==0 else 0.;innovation=actual-p
   # Fixed K and goal-margin multiplier; all experiments use the same update.
   delta=20.*min(2.5,1.+.25*max(0,abs(r['gd'])-1))*innovation
   rating[h]+=delta;rating[a]-=delta
   history[h].append((day, r['surprise']));history[a].append((day,-r['surprise']))
 # Same-match AH inventory excluding any frozen-eight FID. Fold by Beijing year.
 targets=[r for r in base if r['year'] in (2024,2025,2026) and not r['frozen'] and not r['receipt_only']]
 response_diag={}
 for y in (2024,2025,2026):
  sub=[r for r in targets if r['year']==y]
  shocks=np.asarray([r['shock_diff_90'] for r in sub],float)
  changes=np.asarray([(-r['line']+.25*math.log(r['ao']/r['ho']))-(-r['start_line']+.25*math.log(r['start_ao']/r['start_ho'])) for r in sub],float)
  corr=float(np.corrcoef(shocks,changes)[0,1]) if len(sub)>2 and np.std(shocks)>0 and np.std(changes)>0 else None
  slope=float(np.polyfit(shocks,changes,1)[0]) if len(sub)>2 and np.std(shocks)>0 else None
  response_diag[str(y)]={'n':len(sub),'market_vigor_start_to_end_mean':round(float(changes.mean()),8) if len(sub) else None,'pearson_prior_market_surprise_vs_start_to_end_vigor_change':round(corr,8) if corr is not None else None,'ols_vigor_change_per_surprise_unit':round(slope,8) if slope is not None else None,'causal_or_receipt_time_claim':False}
 allpred=[];folds={};fold_models={}
 for year in (2024,2025,2026):
  train=[r for r in base if r['year']<year and r['year']>=2019];test=[r for r in targets if r['year']==year]
  if not train or not test:continue
  X=np.vstack([features(r) for r in train]);y=np.asarray([r['gd'] for r in train],float)
  # Market-only and shock-added models are fitted on identical target rows.
  market_cols=[0,1,2,3];shock_cols=list(range(10));asym_cols=[0,1,2,3,4,8,9,10,11,12,13]
  mf=fit(X[:,market_cols],y);sf=fit(X[:,shock_cols],y);af=fit(X[:,asym_cols],y)
  fold_models[year]=(mf,sf,af)
  folds[str(year)]={'train_n':len(train),'test_n':len(test),'training_years':sorted({r['year'] for r in train}),'market_sigma':mf[-1],'shock_sigma':sf[-1],'asymmetric_sigma':af[-1],'ridge':25.,'rating_update':'K20; logistic outcome innovation; capped goal-margin multiplier; full Beijing-date embargo'}
  for r in test:
   xm=features(r)[market_cols];xs=features(r)[shock_cols]
   mm,ms=pred_margin(xm,mf);sm,ss=pred_margin(xs,sf)
   am,ass=pred_margin(features(r)[asym_cols],af)
   for name,mu,sig in [('market_baseline',mm,ms),('pregame_market_surprise_shock',sm,ss),('asymmetric_result_shock',am,ass)]:
    evh=payoff_ev(r['line'],r['ho'],'home',mu,sig);eva=payoff_ev(r['line'],r['ao'],'away',mu,sig);side='home' if evh>=eva else 'away';odds=r['ho'] if side=='home' else r['ao'];pnl=settle(r['line'],side,odds,r['gd'])
    row={'fid':r['fid'],'year_beijing':year,'kickoff_beijing':r['kickoff_beijing'],'iso_week':f"{dt.date.fromisoformat(r['date']).isocalendar().year}-W{dt.date.fromisoformat(r['date']).isocalendar().week:02d}",'league':r['league'],'home_team_id':r['home'],'away_team_id':r['away'],'crown_source':'historical_source_event_T1_replay','Crown_home_AH_line':r['line'],'Crown_home_odds':r['ho'],'Crown_away_odds':r['ao'],'model':name,'predicted_home_goal_margin':round(mu,6),'prediction_sigma':round(sig,6),'home_EV_U':round(evh,6),'away_EV_U':round(eva,6),'direction':side,'FT_home':r['hg'],'FT_away':r['ag'],'settlement':state(r['line'],side,r['gd']),'net_u':round(pnl,6),'frozen_eight_overlap':False,'shock_features':{'elo_diff':round(r['elo_diff'],6),'home_surprise_30':round(r['shock_home_30'],6),'away_surprise_30':round(r['shock_away_30'],6),'surprise_diff_90':round(r['shock_diff_90'],6),'prior_home_matches':r['home_matches'],'prior_away_matches':r['away_matches']},'feature_cutoff':'prior completed Beijing dates only; no same-day match updates','actual_HTTP_receipt_asserted':False}
    allpred.append(row)
  print('YEAR',year,'test',len(test),flush=True)
 # Report both always-select (max EV side) and fixed economic no-bet when both
 # estimated side EVs are <=0. No ROI-selected thresholds are used.
 summaries={}
 for model in ('market_baseline','pregame_market_surprise_shock','asymmetric_result_shock'):
  rows=[r for r in allpred if r['model']==model]
  bets=[r for r in rows if max(r['home_EV_U'],r['away_EV_U'])>0]
  summaries[model]={'forced_one_side_all_matches':stats(rows),'predeclared_positive_model_EV_only':stats(bets),'all_five_settlement_counts':dict(collections.Counter(r['settlement'] for r in rows)),'by_year':{str(y):stats([r for r in rows if r['year_beijing']==y]) for y in (2024,2025,2026)},'by_year_EV_positive_only':{str(y):stats([r for r in bets if r['year_beijing']==y]) for y in (2024,2025,2026)}}
 # Frozen base and unions are reported on identical Beijing year windows.
 # Independently score every actual Crown receipt FID using the frozen 2026
 # walk-forward fit; features use only earlier Beijing dates in score history.
 receipt_predictions=[];receipt_models={m:[] for m in ('market_baseline','pregame_market_surprise_shock','asymmetric_result_shock')}
 if 2026 in fold_models:
  mf,sf,af=fold_models[2026]
  for r in receipts:
   if r['year']!=2026:continue
   for name,cols,model in (('market_baseline',[0,1,2,3],mf),('pregame_market_surprise_shock',list(range(10)),sf),('asymmetric_result_shock',[0,1,2,3,4,8,9,10,11,12,13],af)):
    mu,sig=pred_margin(features(r)[cols],model);eh=payoff_ev(r['line'],r['ho'],'home',mu,sig);ea=payoff_ev(r['line'],r['ao'],'away',mu,sig);side='home' if eh>=ea else 'away';odds=r['ho'] if side=='home' else r['ao'];pnl=settle(r['line'],side,odds,r['gd']);meta=r['receipt_meta']
    z={'fid':r['fid'],'year_beijing':2026,'kickoff_beijing':r['kickoff_beijing'],'league':r['league'],'model':name,'receipt_source':'verified MR1 Crown snapshot archive','receipt_received_utc':meta['received_utc'],'quote_event_utc':meta['ah_source_utc'],'snapshot_sha256':meta['snapshot_sha256'],'crown_ah_home_line':r['line'],'crown_home_odds':r['ho'],'crown_away_odds':r['ao'],'direction':side,'FT_home':r['hg'],'FT_away':r['ag'],'settlement':state(r['line'],side,r['gd']),'net_u':round(pnl,6),'model_EV_home_U':round(eh,6),'model_EV_away_U':round(ea,6),'feature_cutoff':'prior completed Beijing dates only; no same-day match updates','actual_HTTP_receipt_price':True,'formal_telegram_order':False}
    receipt_predictions.append(z);receipt_models[name].append(z)
 with gzip.open(OUT/'receipt_replay_per_fixture_20261120.jsonl.gz','wt',encoding='utf8') as f:
  for z in receipt_predictions:f.write(json.dumps(z,ensure_ascii=False,sort_keys=True)+'\n')
 receipt_summary={m:{'all_receipt_quotes':stats(v),'predeclared_positive_model_EV_only':stats([z for z in v if max(z['model_EV_home_U'],z['model_EV_away_U'])>0]),'overlap_frozen_eight':len({z['fid'] for z in v}&frozen),'unique_fids':len({z['fid'] for z in v})} for m,v in receipt_models.items()}
 members=list(read(MEM));base_by_fid={x['fid']:x for x in base};frozen_stats={}
 for y in (2024,2025,2026):
  fr=[]
  for m in members:
   s=base_by_fid.get(str(m['fid']))
   if s and s['year']==y:fr.append({'net_u':float(m['pnl']),'kickoff_beijing':s['kickoff_beijing'],'iso_week':f"{dt.date.fromisoformat(s['date']).isocalendar().year}-W{dt.date.fromisoformat(s['date']).isocalendar().week:02d}",'league':s['league']})
  frozen_stats[str(y)]=stats(fr)
  for model in summaries:
   extra=[r for r in allpred if r['model']==model and r['year_beijing']==y]
   frozen_stats[str(y)]['plus_'+model]=stats(fr+extra)
 OUT.mkdir(parents=True,exist_ok=True)
 with gzip.open(OUT/'strength_shock_per_fixture_20261120.jsonl.gz','wt',encoding='utf8') as f:
  for r in allpred:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 result={'study':'A strength shock, D asymmetric response and predeclared no-bet, plus receipt audit','hypothesis':'A sequential team strength innovation is defined as prior FT outcome minus Crown-implied pregame margin proxy; test whether it improves time-forward AH margin estimates and executable Crown contract payoff. D tests whether Crown reacts differently to unexpected positive versus negative prior outcomes. The no-bet variant uses fixed contract break-even EV > 0.','data':{'path_rows':len(paths),'score_rows':len(scores),'frozen_fids':len(frozen),'historical_joined_fids':len([r for r in base if not r['receipt_only']]),'historical_unique_fids':len({r['fid'] for r in base if not r['receipt_only']}),'outside_eight_target_fids':len(targets),'year_china_counts':dict(collections.Counter(str(r['year']) for r in base if not r['receipt_only'])),'invalid_or_missing':dict(bad),'receipt_snapshot_rows':len(receipt_archive),'receipt_unique_fids':len(receipt_by_fid),'receipt_fids_added':len(receipts),'receipt_exclusion_reasons':dict(receipt_bad),'receipt_score_join_fids':len(receipts),'path_sha256':sha(PATH),'score_sha256':sha(SCORES),'frozen_sha256':sha(MEM),'receipt_archive_sha256':sha(RECEIPTS),'cutoff_timezone':'Asia/Shanghai UTC+08:00'},'folds':folds,'market_response_diagnostic':response_diag,'summaries':summaries,'actual_receipt_replay':receipt_summary,'frozen_eight_and_unfiltered_union_by_year':frozen_stats,'ledger_rows':len(allpred),'unique_test_fids_per_model':{m:len({r['fid'] for r in allpred if r['model']==m}) for m in summaries},'limitations':['Historical Crown quotes are source-event T1 replays, not actual received HTTP quotes.','Start-to-end line/water adjustment is a retrospective event-path diagnostic; it does not identify causal lag or contemporaneous receipt timing.','Receipt price replays require exact-FID joining to team-and-score history; this score archive has no rows for the 176 unique new MR1 receipt FIDs, so candidate applications are zero.','Team ratings are reconstructed from retrospective score history and have no timestamped contemporaneous snapshot.','No target-year tuning or ROI search.','D is a research-only economic asymmetry/abstention experiment, not a production Gate.']}
 (OUT/'strength_shock_results_20261120.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({m:{'all':v['forced_one_side_all_matches']['net_u'],'all_roi':v['forced_one_side_all_matches']['roi_pct'],'ev_only':v['predeclared_positive_model_EV_only']['net_u'],'ev_n':v['predeclared_positive_model_EV_only']['n']} for m,v in summaries.items()},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
