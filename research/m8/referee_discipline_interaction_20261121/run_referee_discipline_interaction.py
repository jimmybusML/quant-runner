#!/usr/bin/env python3
"""Historical walk-forward test of team discipline x referee residual interactions.

Research only. Referee identity is retrospectively archived and has no verified
pregame announcement timestamp; all AH prices are historical Crown event-time.
"""
from __future__ import annotations
import bisect,collections,csv,datetime as dt,gzip,hashlib,importlib.util,json,math,pathlib,statistics,sqlite3
from zoneinfo import ZoneInfo
import numpy as np
import sys

OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[3]))
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
SRC=WORK/'m8_pregame_info_source_20261117'
PATH=WORK/'m8_late_full_path_water_features_20261114.jsonl'
SCORES=WORK/'m8_independent_score_strength_20261114.jsonl'
FOUNDATION=WORK/'m8_foundation_20261115/historical_membership.jsonl'
RECEIPTS=WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
MANAGER=WORK/'m8_prior_manager_turnover_20261117.py'
DISCIPLINE=WORK/'m8_discipline_pregame_market_20261117.py'
REF_ROWS=pathlib.Path(__file__).resolve().parents[1]/'referee_market_residual_20261120/referee_market_residual_per_fixture.jsonl.gz'
DB=pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
BEIJING=ZoneInfo('Asia/Shanghai'); UTC=dt.timezone.utc; ALPHA=100.0
MARKET_FEATURES=('market_margin','line','water_skew')
DISC_N=14
REF_N=2

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def jsonl(path):
 with open(path,encoding='utf8') as f:
  for s in f:
   if s.strip():yield json.loads(s)
def jsonl_gz(path):
 with gzip.open(path,'rt',encoding='utf8') as f:
  for s in f:
   if s.strip():yield json.loads(s)
def date_ord(s):return dt.date.fromisoformat(str(s)[:10]).toordinal()
def parse_utc(s):
 x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00'))
 if x.tzinfo is None:x=x.replace(tzinfo=BEIJING)
 return x.astimezone(UTC)

def load_discipline_features():
 src=DISCIPLINE.read_text(encoding='utf8'); marker="out={'method'"
 ns={'__file__':str(DISCIPLINE),'__name__':'m8_r48_feature_replay_only'}
 exec(compile(src[:src.rindex(marker)],str(DISCIPLINE)+'[feature-prefix]','exec'),ns)
 rows=ns['H']; mat=ns['HF']
 return {str(r['fid']):{'values':np.asarray(mat[i],float).tolist(),'league':str(r['league']),
                           'home_id':str(r['home_id']),'away_id':str(r['away_id']),
                           'date':str(r['date']),'year':int(r['year'])}
         for i,r in enumerate(rows)},ns

def load_identity_bridge():
 src=MANAGER.read_text(encoding='utf8'); marker='# Build historical coach timeline'
 ns={'__file__':str(MANAGER),'__name__':'m8_referee_bridge_readonly'}
 exec(compile(src[:src.index(marker)],str(MANAGER)+'[audited-bridge-prefix]','exec'),ns)
 return ns

def map_all_crown_paths(bridge):
 paths={str(r['fid']):r for r in jsonl(PATH)}
 scores={str(r['fid']):r for r in jsonl(SCORES)}
 allft=bridge['allft'];teammap=bridge['teammap'];compdate=bridge['compdate'];tmrec=bridge['tmrec'];cm=bridge['cm']
 issues=collections.Counter(); mapped=[]
 for fid,p in paths.items():
  s=scores.get(fid);ft=allft.get(fid)
  if not s or ft is None:issues['score_or_cached_FT_missing']+=1;continue
  lid,hid,aid,hn,an,hg,ag,_=ft
  if (str(lid),str(hid),str(aid),str(hg),str(ag))!=(str(s['league']),str(s['home']),str(s['away']),str(s['hg']),str(s['ag'])):
   issues['fixture_identity_conflict']+=1;continue
  htm=teammap.get((str(lid),str(hid)));atm=teammap.get((str(lid),str(aid)));comp=cm.get(str(lid))
  if not htm or not atm or not comp:issues['unmapped_team_or_competition']+=1;continue
  ko=parse_utc(s['ko']);local=ko.astimezone(BEIJING);day=local.date();candidates=[]
  for ordinal in (day.toordinal()-1,day.toordinal(),day.toordinal()+1):
   for t in compdate.get((comp,ordinal),[]):
    if t[2]==htm and t[3]==atm and t[4]==int(s['hg']) and t[5]==int(s['ag']):candidates.append(t)
  if len(candidates)!=1:issues['tm_'+('unmatched' if not candidates else 'ambiguous')]+=1;continue
  tm=tmrec[candidates[0][-1]];ref=str(tm.get('referee') or '').strip()
  if not ref:issues['missing_target_referee']+=1;continue
  try:
   line=float(p['end_line']);ho=float(p['home_price']);ao=float(p['away_price'])
   if min(ho,ao)<=1 or abs(line*4-round(line*4))>1e-8:raise ValueError
  except Exception:issues['invalid_T1_market_contract']+=1;continue
  mapped.append({'fid':fid,'year':local.year,'date':local.date().isoformat(),
   'iso_week':f'{local.isocalendar().year}-W{local.isocalendar().week:02d}',
   'kickoff_beijing':local.isoformat(),'league':str(lid),'home_id':str(hid),'away_id':str(aid),
   'home_tm_id':htm,'away_tm_id':atm,'tm_game_id':str(tm['game_id']),'referee':ref,
   'referee_norm':normalize_referee(ref),'referee_key':f'{lid}:{normalize_referee(ref)}','hg':int(s['hg']),'ag':int(s['ag']),'gd':int(s['hg'])-int(s['ag']),
   'line':line,'home_odds':ho,'away_odds':ao,'frozen_overlap':False,
   'source_type':'historical Crown T1 source-event replay; not actual pregame HTTP receipt',
   'referee_time_limit':'retrospective Transfermarkt target referee; announcement/receipt timestamp unavailable'})
 mapped.sort(key=lambda x:(x['date'],x['fid']))
 return mapped,dict(issues),paths,scores

def normalize_referee(s):
 import re,unicodedata
 x=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]','',x)

def add_ref_features(rows):
 byday=collections.defaultdict(list)
 for r in rows:byday[r['date']].append(r)
 rh=collections.defaultdict(list); ch=collections.defaultdict(list)
 for day in sorted(byday):
  current=byday[day];d=dt.date.fromisoformat(day);cut=d-dt.timedelta(days=3);start=cut-dt.timedelta(days=365)
  for r in current:
   rv=[x for x in rh[r['referee_key']] if start<=dt.date.fromisoformat(x[0])<cut]
   cv=[x for x in ch[r['league']] if start<=dt.date.fromisoformat(x[0])<cut]
   rn=len(rv);cn=len(cv);rm=sum(x[1] for x in rv)/rn if rn else 0.;cm=sum(x[1] for x in cv)/cn if cn else 0.
   r['ref_prior_n_365']=rn;r['comp_prior_n_365']=cn
   r['ref_residual_mean_365']=rm if rn else 0.
   r['comp_residual_mean_365']=cm if cn else 0.
   r['ref_centered_residual_365_shrunk']=rn/(rn+5.)*(rm-cm) if rn else 0.
   r['ref_prior_max_date_365']=max((x[0] for x in rv),default=None)
   r['history_cutoff']='previous Beijing dates at least 3 days before target; trailing 365 days'
  for r in current:
   market_margin=-r['line']+.25*math.log(r['away_odds']/r['home_odds'])
   residual=r['gd']-market_margin
   rh[r['referee_key']].append((day,residual));ch[r['league']].append((day,residual))

def settle(line,side,gd,price):
 line=float(line);gd=int(gd);price=float(price)
 signed=line if side=='home' else -line
 margin=gd if side=='home' else -gd
 if abs(line*4-round(line*4))>1e-8:raise ValueError('AH line outside quarter grid')
 legs=(signed,) if abs(signed*2-round(signed*2))<1e-8 else (math.floor(signed*2)/2,math.ceil(signed*2)/2)
 vals=[price-1 if margin+x>1e-9 else -1. if margin+x< -1e-9 else 0. for x in legs]
 net=sum(vals)/len(vals)
 label=('full_win' if all(x>0 for x in vals) else 'half_win' if any(x>0 for x in vals) else
        'push' if all(x==0 for x in vals) else 'half_loss' if any(x==0 for x in vals) else 'full_loss')
 return label,net
def normal_cdf(x):return .5*(1.+math.erf(x/math.sqrt(2.)))
def margin_dist(mu,sigma,lo=-12,hi=12):
 sigma=max(float(sigma),.35)
 p=[max(0.,normal_cdf((k+.5-mu)/sigma)-normal_cdf((k-.5-mu)/sigma)) for k in range(lo,hi+1)]
 sm=sum(p);return [(lo+i,v/sm) for i,v in enumerate(p)]
def ev_pair(line,ho,ao,mu,sigma):
 dist=margin_dist(mu,sigma)
 eh=sum(p*settle(line,'home',m,ho)[1] for m,p in dist)
 ea=sum(p*settle(line,'away',m,ao)[1] for m,p in dist)
 if abs(eh-ea)<1e-12:return None,eh,ea
 return ('home' if eh>ea else 'away'),eh,ea
def fit_ridge(X,y):
 x=np.asarray(X,float);y=np.asarray(y,float);mean=x.mean(0);scale=x.std(0);scale=np.where(scale<1e-10,1.,scale)
 z=(x-mean)/scale;design=np.column_stack([np.ones(len(z)),z]);pen=np.eye(design.shape[1])*ALPHA;pen[0,0]=0.
 coef=np.linalg.solve(design.T@design+pen,design.T@y);train=design@coef
 return {'mean':mean,'scale':scale,'coef':coef,'sigma':max(.35,float(np.sqrt(np.mean((y-train)**2)))),'train_n':len(y)}
def predict(model,x):return float(np.r_[1.,(np.asarray(x,float)-model['mean'])/model['scale']]@model['coef'])
def model_features(r,method):
 m=[r['market_margin'],r['line'],r['water_skew']];d=r['discipline'];ref=[r['ref_centered_residual_365_shrunk'],math.log1p(r['ref_prior_n_365'])]
 if method=='market_only':return m
 if method=='discipline_only':return d
 if method=='market_plus_discipline':return m+d
 if method=='market_plus_referee':return m+ref
 if method=='market_plus_referee_discipline_additive':return m+ref+d
 if method=='market_plus_referee_discipline_interaction':
  # The two fixed interaction terms test whether referee-specific residual
  # interacts with historic team yellow-card asymmetry or red-card asymmetry.
  return m+ref+d+[d[0]*ref[0],d[2]*ref[0]]
 raise KeyError(method)
def daily_mdd(rows,field='net_u'):
 daily=collections.defaultdict(float)
 for r in rows:daily[r['date']]+=float(r[field])
 total=peak=mdd=0.
 for day in sorted(daily):total+=daily[day];peak=max(peak,total);mdd=max(mdd,peak-total)
 return round(mdd,6)
def stats(rows,weeks_den=None):
 n=len(rows);u=sum(float(r['net_u']) for r in rows)
 pos=sum(r['net_u']>1e-10 for r in rows);neg=sum(r['net_u']< -1e-10 for r in rows)
 if not n:return {'n':0,'net_U':0.,'ROI_pct':None,'MDD_U':0.,'orders_per_week':0.,'settlement_classes':{}}
 span=(date_ord(max(r['date'] for r in rows))-date_ord(min(r['date'] for r in rows)))//7+1
 return {'n':n,'net_U':round(u,6),'ROI_pct':round(100*u/n,6),'MDD_U':daily_mdd(rows),
  'orders_per_week':round(n/(weeks_den or span),6),'positive_orders':pos,'negative_orders':neg,
  'zero_orders':n-pos-neg,'settlement_classes':dict(collections.Counter(r.get('settlement','not_recorded') for r in rows))}
def weekly(rows):
 z=collections.defaultdict(lambda:[0,0.])
 for r in rows:
  q=dt.date.fromisoformat(r['date']).isocalendar();key=f'{q.year}-W{q.week:02d}';z[key][0]+=1;z[key][1]+=r['net_u']
 return {k:{'n':v[0],'net_U':round(v[1],6)} for k,v in sorted(z.items())}

def main():
 for p in (PATH,SCORES,FOUNDATION,RECEIPTS,SRC/'appearances.csv.gz',SRC/'games.csv.gz',SRC/'game_lineups.csv.gz',DB):
  if not p.exists():raise FileNotFoundError(p)
 print('INPUT_SHA',json.dumps({str(p):sha(p) for p in (PATH,SCORES,FOUNDATION,RECEIPTS,SRC/'appearances.csv.gz',SRC/'games.csv.gz',SRC/'game_lineups.csv.gz',DB)},ensure_ascii=False),flush=True)
 disc,disc_ns=load_discipline_features();bridge=load_identity_bridge();games,map_issues,paths,scores=map_all_crown_paths(bridge);add_ref_features(games)
 # Reconcile the reconstructed referee/quote/FT rows to the published PR #69
 # OOS ledger before any new interaction model is fit.
 published={str(x['fid']):x for x in jsonl_gz(REF_ROWS)};recon={str(x['fid']):x for x in games}
 ref_audit=collections.Counter()
 for fid,x in published.items():
  y=recon.get(fid)
  if y is None:ref_audit['published_referee_fid_missing_from_reconstruction']+=1;continue
  if (str(y['home_tm_id']),str(y['away_tm_id']),str(y['referee_norm']),int(y['hg']),int(y['ag']))!=(str(x['home_tm_id']),str(x['away_tm_id']),str(x['referee_key'][1]),int(x['hg']),int(x['ag'])):
   ref_audit['published_referee_identity_mismatch']+=1
  for a,b in (('line','line'),('home_odds','home_odds'),('away_odds','away_odds'),('ref_centered_residual_365_shrunk','ref_centered_residual_365_shrunk')):
   if abs(float(y[a])-float(x[b]))>1e-7:ref_audit['field_mismatch_'+a]+=1
  ref_audit['published_referee_fid_reconciled']+=1
 if ref_audit.get('published_referee_fid_missing_from_reconstruction',0) or ref_audit.get('published_referee_identity_mismatch',0) or any(ref_audit.get(f'field_mismatch_{a}',0) for a in ('line','home_odds','away_odds','ref_centered_residual_365_shrunk')):
  raise AssertionError(f'PR #69 referee bridge identity/quote reconciliation failed: {dict(ref_audit)}')
 frozen={str(r['fid']) for r in jsonl(FOUNDATION)};receipts={str(r['fixture_id']) for r in jsonl(RECEIPTS)}
 by_fid={str(r['fid']):r for r in games}
 coverage=collections.Counter();rows=[]
 for fid,r in by_fid.items():
  d=disc.get(fid)
  if not d:coverage['no_discipline_FID']+=1;continue
  if d['league']!=r['league'] or d['home_id']!=r['home_id'] or d['away_id']!=r['away_id']:coverage['discipline_identity_conflict']+=1;continue
  if not all(math.isfinite(float(v)) for v in d['values']):coverage['incomplete_team_discipline_history']+=1;continue
  p=paths[fid];r['market_margin']=-r['line']+.25*math.log(r['away_odds']/r['home_odds'])
  r['water_skew']=.25*math.log(r['away_odds']/r['home_odds'])
  r['discipline']=[float(v) for v in d['values']]
  r['frozen_overlap']=fid in frozen;r['receipt_archive_fid_overlap']=fid in receipts
  r['discipline_cutoff']='source feature archive: prior TotalCorner completed matches at least 3 UTC calendar days before target; 90/365-day rates'
  r['T1_home_odds']=r['home_odds'];r['T1_away_odds']=r['away_odds'];r['T1_AH_home_line']=r['line']
  rows.append(r);coverage['common_referee_and_discipline_rows']+=1
  coverage['frozen_overlap']+=int(r['frozen_overlap']);coverage['receipt_overlap']+=int(r['receipt_archive_fid_overlap'])
 rows.sort(key=lambda r:(r['date'],r['fid']))
 if not rows:raise RuntimeError('no common fixture sample')
 # A common FID pool is used for every forecast specification. Baselines and
 # all combined models therefore differ only by information features.
 methods=['market_only','discipline_only','market_plus_discipline','market_plus_referee',
          'market_plus_referee_discipline_additive','market_plus_referee_discipline_interaction']
 preds={m:[] for m in methods};folds={};year_coverage={}
 for year in (2024,2025,2026):
  train=[r for r in rows if 2019<=r['year']<year and not r['receipt_archive_fid_overlap']]
  test=[r for r in rows if r['year']==year]
  if not train or not test:continue
  y=np.asarray([r['gd'] for r in train],float)
  folds[str(year)]={'train_rows':len(train),'test_rows':len(test),'train_years':sorted({r['year'] for r in train}),
                    'train_max_year':max(r['year'] for r in train),'ridge_alpha':ALPHA,
                    'training_excludes_receipt_archive_fids':True}
  for method in methods:
   X=np.asarray([model_features(r,method) for r in train],float)
   Xt=np.asarray([model_features(r,method) for r in test],float)
   model=fit_ridge(X,y);folds[str(year)].setdefault('models',{})[method]={'n_features':X.shape[1],'sigma':round(model['sigma'],8)}
   for r,x in zip(test,Xt):
    mu=predict(model,x);side,eh,ea=ev_pair(r['line'],r['home_odds'],r['away_odds'],mu,model['sigma'])
    if side is None:state='no_side_tie';net=0.;price=None
    else:price=r['home_odds'] if side=='home' else r['away_odds'];state,net=settle(r['line'],side,r['gd'],price)
    preds[method].append({**r,'method':method,'predicted_home_goal_difference':round(mu,8),
                          'predicted_sigma':round(model['sigma'],8),'home_EV_U':round(eh,8),'away_EV_U':round(ea,8),
                          'chosen_side':side,'chosen_odds':price,'settlement':state,'net_u':round(net,8),
                          'training_year_cutoff_exclusive':year,'source_type':'historical Crown T1 source-event replay; retrospective'})
  year_coverage[str(year)]={'train_rows':len(train),'test_rows':len(test),'test_frozen_overlap':sum(r['frozen_overlap'] for r in test),
                             'test_outside_frozen':sum(not r['frozen_overlap'] for r in test)}
 # Evaluate only out-of-frozen FIDs for incremental measures; never use frozen
 # membership in any forecast feature or training selection.
 testrows=[r for r in rows if 2024<=r['year']<=2026]
 dates=[dt.date.fromisoformat(r['date']) for r in testrows];period_weeks=(max(dates)-min(dates)).days//7+1
 result={};year_result={};league_result={};merged={};full_merged={}
 frozen_rows=[];frozen_all_rows=[]
 for x in jsonl(FOUNDATION):
  try:y=int(x['year']);d=str(x['date'])[:10]
  except Exception:continue
  frozen_all_rows.append({'fid':str(x['fid']),'date':d,'net_u':float(x['pnl'])})
  if y in (2024,2025,2026) and d<=max(r['date'] for r in testrows):frozen_rows.append({'fid':str(x['fid']),'date':d,'net_u':float(x['pnl'])})
 base=stats(frozen_rows,period_weeks)
 for method in methods:
  arr=preds[method];incr=[r for r in arr if not r['frozen_overlap']]
  result[method]={'all_test':stats(arr),'incremental_outside_frozen':stats(incr,period_weeks),'weekly':weekly(incr)}
  year_result[method]={str(y):stats([r for r in incr if r['year']==y]) for y in (2024,2025,2026)}
  league_result[method]={lid:stats([r for r in incr if r['league']==lid]) for lid in sorted({r['league'] for r in incr})}
  allrows=frozen_rows+incr;merged[method]={'n':len(allrows),'net_U':round(sum(r['net_u'] for r in allrows),6),
   'ROI_pct':round(100*sum(r['net_u'] for r in allrows)/len(allrows),6) if allrows else None,
   'MDD_U':daily_mdd(allrows),'candidate_incremental_net_U':round(sum(r['net_u'] for r in incr),6),
   'candidate_incremental_n':len(incr),'baseline_n':len(frozen_rows),'baseline_net_U':round(sum(r['net_u'] for r in frozen_rows),6),
   'avg_candidate_orders_per_week':round(len(incr)/period_weeks,6)}
  fullrows=frozen_all_rows+incr;full_merged[method]={'n':len(fullrows),'net_U':round(sum(r['net_u'] for r in fullrows),6),
   'ROI_pct':round(100*sum(r['net_u'] for r in fullrows)/len(fullrows),6) if fullrows else None,
   'MDD_U':daily_mdd(fullrows),'candidate_incremental_net_U':round(sum(r['net_u'] for r in incr),6),
   'candidate_incremental_n':len(incr),'baseline_n':len(frozen_all_rows),'baseline_net_U':round(sum(r['net_u'] for r in frozen_all_rows),6),
   'avg_candidate_orders_per_week':round(len(incr)/period_weeks,6)}
 write=OUT/f'referee_discipline_interaction_{method}_ledger_20261121.jsonl.gz'
 with open(write,'wb') as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
   for r in sorted(arr,key=lambda x:(x['date'],x['fid'])):gz.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 per_fixture=[r for m in methods for r in sorted(preds[m],key=lambda x:(x['date'],x['fid']))]
 with open(OUT/'referee_discipline_interaction_per_fixture_20261121.jsonl.gz','wb') as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
   for r in per_fixture:gz.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 summary={'study':'M8 AH team-discipline × referee-specific historical residual interaction; historical event-time research only',
  'execution_utc':dt.datetime.now(UTC).isoformat(),'inputs_sha256':{str(p):sha(p) for p in (PATH,SCORES,FOUNDATION,RECEIPTS,SRC/'appearances.csv.gz',SRC/'games.csv.gz',SRC/'game_lineups.csv.gz',DB,REF_ROWS)},
  'coverage':{'crown_T1_path_rows':len(paths),'referee_and_ft_mapped_rows':len(games),'referee_mapping_issues':map_issues,
   'published_PR69_referee_rows':len(published),'published_PR69_referee_bridge_quote_FT_feature_reconciliation':dict(ref_audit),
   'discipline_history_fids':len(disc),'discipline_history_valid_rows':sum(all(math.isfinite(float(v)) for v in x['values']) for x in disc.values()),
   'common_valid_rows':len(rows),'test_2024_2026_rows':len(testrows),'test_frozen_overlap':sum(r['frozen_overlap'] for r in testrows),
   'test_outside_frozen_unique_FIDs':len({r['fid'] for r in testrows if not r['frozen_overlap']}),
   'test_receipt_archive_overlap':sum(r['receipt_archive_fid_overlap'] for r in testrows),
   'live_Crown_receipt_verified_FIDs':0,'referee_pregame_assignment_timestamp_verified_FIDs':0,
   'discipline_match_history_actual_source':'M5 cached completed TotalCorner fixtures; 90/365-day team YC/RC features, UTC-date cutoff lag 3 days',
   'common_row_audit':dict(coverage)},
  'methodology':{'prediction_target':'home goals minus away goals','Crown_contract':'T1 Crown AH line and paired decimal prices; source-event time, not received-time executable quote',
   'time_forward':'for each test year 2024/2025/2026, train only 2019 through prior calendar year; all train/test FIDs share the common valid feature cohort; receipt-archive FIDs excluded from model training',
   'discipline_features':'The exact 14 pregame yellow/red rate main and team-side interaction features from R48; generated from prior completed M5 schedule matches only, at least 3 UTC calendar days before target; no target cards used.',
   'referee_feature':'Referee/competition centered historical Crown AH goal-difference residual over previous 365 Beijing dates, 3-day lag, shrink n/(n+5); target assignment from retrospective Transfermarkt games archive with no verified pregame announcement timestamp.',
   'interaction':'Two fixed products: 365-day team yellow-card home-away rate difference × referee centered/shrunk AH residual; 365-day team red-card rate difference × the same referee residual. No parameter sweep or target-year tuning.',
   'estimators':'Ridge alpha=100, standardization fitted within each expanding training fold, Gaussian integer-margin approximation using training RMSE; choose side with higher expected net AH return at actual Crown odds. No EV abstention threshold.',
   'settlement':'Quarter AH split into adjacent half-goal legs and average per-leg stake return.'},
  'year_forward_folds':folds,'test_coverage_by_year':year_coverage,'frozen_baseline_same_period':base,
  'models':result,'annual_incremental':year_result,'league_incremental':league_result,'frozen_plus_candidate_same_period':merged,
  'frozen_plus_candidate_full_frozen_union':full_merged,
  'pairwise_candidate_fid_overlap':{a:{b:len({x['fid'] for x in preds[a]}&{x['fid'] for x in preds[b]}) for b in methods} for a in methods},
  'formal_orders':0,'formal_ledger_writes':0,'production_changes':False}
 (OUT/'referee_discipline_interaction_summary_20261121.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'coverage':summary['coverage'],'models':{m:v['incremental_outside_frozen'] for m,v in result.items()},'annual':year_result,'merged':merged},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
