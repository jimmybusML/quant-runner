#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retrospective venue effects and strict-history venue-stability AH study.

Venue rows are linked without using target scores (score is used only after the
fixture match to validate identity). Target stadium labels have no vintage
timestamp, so they are descriptive exposure labels, not claimed live inputs.
"""
from __future__ import annotations
import collections, csv, datetime as dt, difflib, gzip, hashlib, json, math, re, unicodedata
from pathlib import Path
import numpy as np
from scipy.special import ndtr

ROOT=Path(__file__).resolve().parents[3]
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=WORK/'m8_pregame_info_source_20261117'
SCHEDULE=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules')
RAW_CROWN=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses')
PATH=WORK/'m8_late_full_path_water_features_20261114.jsonl'
SCORES=WORK/'m8_independent_score_strength_20261114.jsonl'
MEM=WORK/'m8_foundation_20261115/historical_membership.jsonl'
RECEIPTS=ROOT/'research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl'
OUT=ROOT/'research/m8/venue_environment_20261120'
TZ=dt.timezone(dt.timedelta(hours=8)); UTC=dt.timezone.utc
COMP={'1':'GB1','12':'IT1','14':'ES1','16':'L1','25':'FR1','29':'A1','31':'BE1','35':'TS1','37':'NL1','48':'PL1','51':'PO1','52':'RO1','61':'C1','62':'TR1','66':'SE1','70':'DK1','73':'JAP1','75':'RSK1','88':'NO1','141':'GR1','262':'SC1','290':'SA1','303':'SER1','319':'UKR1','26540':'KR1'}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def readj(p):
 with open(p,encoding='utf8') as f:
  for line in f:
   if line.strip():yield json.loads(line)
def norm(s):
 x=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 x=re.sub(r'\b(fc|cf|sc|afc|ac|club|football|soccer|fk|as)\b',' ',x)
 return re.sub(r'[^a-z0-9]','',x)
def similarity(a,b):
 a,b=norm(a),norm(b)
 if not a or not b:return 0.
 if a==b:return 1.
 if min(len(a),len(b))>=6 and (a in b or b in a):return .91
 return difflib.SequenceMatcher(None,a,b).ratio()
def parseutc(v):
 z=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 if z.tzinfo is None:z=z.replace(tzinfo=UTC)
 return z.astimezone(UTC)
def qline(line,side,odds,gd):
 h=float(line)*(1 if side=='home' else -1);g=int(gd)*(1 if side=='home' else -1)
 legs=[h] if abs(h*2-round(h*2))<1e-9 else [math.floor(h*2)/2,math.ceil(h*2)/2]
 return sum(float(odds)-1 if g+x>1e-9 else -1. if g+x< -1e-9 else 0. for x in legs)/len(legs)
def qstate(line,side,gd):
 h=float(line)*(1 if side=='home' else -1);g=int(gd)*(1 if side=='home' else -1)
 legs=[h] if abs(h*2-round(h*2))<1e-9 else [math.floor(h*2)/2,math.ceil(h*2)/2]
 xs=['W' if g+x>1e-9 else 'L' if g+x< -1e-9 else 'P' for x in legs]
 return {'W':'full_win','L':'full_loss','P':'push','WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss'}[''.join(xs)]

def load_matches():
 scores={str(x['fid']):x for x in readj(SCORES)}
 paths={str(x['fid']):x for x in readj(PATH)}
 frozen={str(x['fid']):x for x in readj(MEM)}
 sched=collections.defaultdict(list)
 schedule_files=sorted(SCHEDULE.glob('*/page-*.raw.json'))
 for p in schedule_files:
  try:doc=json.loads(p.read_bytes())
  except Exception:continue
  for m in doc.get('data',{}).get('matches',[]):
   fid=str(m.get('id',''))
   if fid and str(m.get('l_id')) in COMP:sched[fid].append(m)
 # Conservative exact Crown schedule FID/team ID join, independent of the FT.
 fixtures=[];issues=collections.Counter()
 for fid,p in paths.items():
  sc=scores.get(fid)
  if not sc:issues['path_without_score']+=1;continue
  ko=parseutc(sc['ko']);local=ko.astimezone(TZ);day=local.date();year=day.year
  if year<2019 or year>2026:continue
  opts=sched.get(fid,[])
  if not opts:issues['no_saved_schedule_fid']+=1;continue
  # De-duplicate identical schedule records; conflicting copies are not guessed.
  unique={json.dumps({k:m.get(k) for k in ('id','l_id','h_id','a_id','start','hg','ag','h','a')},sort_keys=True):m for m in opts}
  if len(unique)!=1:issues['duplicate_conflicting_schedule']+=1;continue
  m=next(iter(unique.values()))
  if str(m.get('h_id'))!=str(sc['home']) or str(m.get('a_id'))!=str(sc['away']):issues['schedule_team_id_mismatch']+=1;continue
  if (int(m.get('hg') or -99),int(m.get('ag') or -99))!=(int(sc['hg']),int(sc['ag'])):issues['schedule_ft_mismatch']+=1;continue
  fixtures.append({'fid':fid,'year':year,'date':day.isoformat(),'ko_utc':ko.isoformat(),'kickoff_beijing':local.isoformat(),
                   'league':str(m['l_id']),'home_id':str(sc['home']),'away_id':str(sc['away']),'home':str(m.get('h','')),'away':str(m.get('a','')),
                   'hg':int(sc['hg']),'ag':int(sc['ag']),'gd':int(sc['hg'])-int(sc['ag']),
                   'line':float(p['end_line']),'home_odds':float(p['home_price']),'away_odds':float(p['away_price']),
                   'frozen':fid in frozen,'frozen_pnl':float(frozen[fid]['pnl']) if fid in frozen else None,
                   'quote_source':'historical Crown source-event T1; not HTTP receipt'})
 # Build Transfermarkt competition/date index.
 tm_path=DATA/'games.csv.gz'; tm_by_comp_date=collections.defaultdict(list);tm_games=[]
 for z in csv.DictReader(gzip.open(tm_path,'rt',encoding='utf8')):
  try:
   d=dt.date.fromisoformat(z['date']); rec={**z,'_date':d,'_home':str(z['home_club_id']),'_away':str(z['away_club_id']),
         '_hg':int(z['home_club_goals']),'_ag':int(z['away_club_goals']),'_stadium':str(z.get('stadium','')).strip()}
   tm_games.append(rec)
   if z.get('competition_id') in set(COMP.values()):tm_by_comp_date[(z['competition_id'],d)].append(rec)
  except Exception:continue
 # Link venue rows using competition, date and ordered team-name similarity.
 mapped=[]
 for r in fixtures:
  comp=COMP.get(r['league'])
  if not comp:issues['tm_competition_unmapped']+=1;continue
  day=dt.date.fromisoformat(r['date']);candidates=[]
  for d in (day,day-dt.timedelta(days=1),day+dt.timedelta(days=1)):
   for t in tm_by_comp_date.get((comp,d),[]):
    sh=similarity(r['home'],t['home_club_name']);sa=similarity(r['away'],t['away_club_name'])
    if min(sh,sa)>=.85:candidates.append((min(sh,sa),sh,sa,t))
  candidates.sort(key=lambda x:(-x[0],x[3]['game_id']))
  if not candidates:issues['tm_no_ordered_team_date_match']+=1;continue
  if len(candidates)>1 and candidates[0][0]-candidates[1][0]<=.05:issues['tm_ambiguous_match']+=1;continue
  best=candidates[0]; t=best[3]
  # Score is checked only after identity match; it never selects the match or
  # enters a feature.
  if (t['_hg'],t['_ag'])!=(r['hg'],r['ag']):issues['tm_postlink_ft_mismatch']+=1;continue
  if not t['_stadium']:issues['tm_stadium_missing']+=1;continue
  mapped.append({**r,'tm_game_id':str(t['game_id']),'tm_home_club_id':t['_home'],'tm_away_club_id':t['_away'],
                 'tm_date':t['_date'].isoformat(),'stadium':t['_stadium'],'stadium_key':norm(t['_stadium']),
                 'home_name_similarity':best[1],'away_name_similarity':best[2],'identity_ft_verified':True})
 # Reusable prior-only venue history indexed by club and match date.
 home_history=collections.defaultdict(list);any_history=collections.defaultdict(list)
 for t in tm_games:
  if not t['_stadium']:continue
  home_history[t['_home']].append((t['_date'],norm(t['_stadium']),t['_stadium']))
  any_history[t['_home']].append((t['_date'],norm(t['_stadium']),t['_stadium']))
  any_history[t['_away']].append((t['_date'],norm(t['_stadium']),t['_stadium']))
 for key in home_history:home_history[key].sort()
 for key in any_history:any_history[key].sort()
 def prior_stats(club,site,target_day,home_only):
  arr=home_history[str(club)] if home_only else any_history[str(club)]
  cutoff=target_day-dt.timedelta(days=1)
  prior=[x for x in arr if x[0]<cutoff]
  if not prior:return {'n':0,'site_n':0,'site_share':None,'top_share':None,'n_sites':0,'entropy':None,'modal_site':None}
  counts=collections.Counter(x[1] for x in prior); n=len(prior);site_n=counts.get(site,0)
  probs=[v/n for v in counts.values()]
  entropy=-sum(x*math.log(x) for x in probs)
  modal=sorted(counts.items(),key=lambda kv:(-kv[1],kv[0]))[0][0]
  return {'n':n,'site_n':site_n,'site_share':site_n/n,'top_share':max(probs),'n_sites':len(counts),'entropy':entropy,'modal_site':modal}
 for r in mapped:
  target_day=dt.date.fromisoformat(r['date']);site=r['stadium_key']
  hh=prior_stats(r['tm_home_club_id'],site,target_day,True)
  ah=prior_stats(r['tm_away_club_id'],site,target_day,True)
  ha=prior_stats(r['tm_home_club_id'],site,target_day,False)
  aa=prior_stats(r['tm_away_club_id'],site,target_day,False)
  r['pregame_venue_history']={'home_prior_home_matches':hh['n'],'away_prior_home_matches':ah['n'],
      'home_prior_site_share':hh['site_share'],'away_prior_site_share':ah['site_share'],
      'home_prior_top_site_share':hh['top_share'],'away_prior_top_site_share':ah['top_share'],
      'home_prior_site_count':hh['n_sites'],'away_prior_site_count':ah['n_sites'],
      'home_prior_site_entropy':hh['entropy'],'away_prior_site_entropy':ah['entropy'],
      'home_prior_any_site_share':ha['site_share'],'away_prior_any_site_share':aa['site_share'],
      'site_familiarity_gap':None if hh['site_share'] is None or ah['site_share'] is None else hh['site_share']-ah['site_share'],
      'home_actual_ground_change_label':None if hh['modal_site'] is None else site!=hh['modal_site'],
      'away_club_site_match_prior':None if ah['site_share'] is None else ah['site_share']>0,
      'both_teams_prior_home_exposure_known':hh['n']>0 and ah['n']>0,
      'actual_site_unfamiliar_to_both_proxy':None if hh['n']==0 or ah['n']==0 else hh['site_n']==0 and ah['site_n']==0,
      'actual_ground_label_timestamp_verified':False}
 return fixtures,mapped,issues,tm_games,scores,paths,frozen,sched,tm_path

def build_team_features(fixtures, scores, paths):
 # Crown team-role margin residuals are controls only; snapshots taken before
 # target Beijing date minus 3 days, whole same-day group updates after scoring.
 rows=[]
 for fid,s in scores.items():
  p=paths.get(fid)
  if not p:continue
  ko=parseutc(s['ko']);day=ko.astimezone(TZ).date()
  rows.append({'fid':fid,'day':day,'home':str(s['home']),'away':str(s['away']),
               'hg':int(s['hg']),'ag':int(s['ag']),'line':float(p['end_line'])})
 rows.sort(key=lambda x:(x['day'],x['fid']))
 hist=collections.defaultdict(list); bydate=collections.defaultdict(list)
 for z in rows:bydate[z['day']].append(z)
 targets={x['fid']:x for x in fixtures}; team_out={}
 for day in sorted(bydate):
  snap=day-dt.timedelta(days=3)
  def get(team,role):
   a=[x for x in hist[(team,role)] if x[0]<snap]
   if not a:return None,0,None,0
   recent=[x for x in a if (snap-x[0]).days<=365]
   vals=[x[1] for x in recent]; last=[x[1] for x in a[-5:]]
   return sum(vals)/(len(vals)+5),len(vals),sum(last)/(len(last)+5),len(a)
  for z in bydate[day]:
   if z['fid'] in targets:
    h=get(z['home'],'H');a=get(z['away'],'A')
    team_out[z['fid']]={'home_market_adjusted_prior365':h[0],'home_market_prior365_n':h[1],
       'home_market_adjusted_last5':h[2],'home_market_prior_all_n':h[3],
       'away_market_adjusted_prior365':a[0],'away_market_prior365_n':a[1],
       'away_market_adjusted_last5':a[2],'away_market_prior_all_n':a[3]}
  # Use only settled matches on earlier dates; whole date is embargoed.
  for z in bydate[day]:
   residual=(z['hg']-z['ag'])-(-z['line'])
   hist[(z['home'],'H')].append((day,residual));hist[(z['away'],'A')].append((day,-residual))
 return team_out

def norm_feature(v):return 0.0 if v is None else float(v)
def design(r, mode='market_team_history'):
 tf=r['team_history'];v=r['pregame_venue_history']
 market=[1.,-r['line'],abs(r['line']),math.log(r['away_odds']/r['home_odds'])]
 team=[norm_feature(tf['home_market_adjusted_prior365']),norm_feature(tf['away_market_adjusted_prior365']),
    norm_feature(tf['home_market_adjusted_last5']),norm_feature(tf['away_market_adjusted_last5']),
    math.log1p(tf['home_market_prior365_n']),math.log1p(tf['away_market_prior365_n'])]
 x=market if mode=='market_only' else market+team
 if mode=='market_team_plus_prior_venue_stability':
  # Strictly prior records only; target venue string itself is not used as a
  # predictive feature, because its historical record lacks an as-of receipt.
  x += [norm_feature(v['home_prior_top_site_share']),norm_feature(v['away_prior_top_site_share']),
        math.log1p(v['home_prior_site_count']),math.log1p(v['away_prior_site_count']),
        norm_feature(v['home_prior_site_entropy']),norm_feature(v['away_prior_site_entropy']),
        float(v['home_prior_home_matches']==0),float(v['away_prior_home_matches']==0)]
 return np.asarray(x,dtype=float)
def fit(X,y,alpha=20.):
 mu=X.mean(0);sd=X.std(0);sd[sd<1e-10]=1.
 Z=(X-mu)/sd;Ym=float(y.mean());b=np.linalg.solve(Z.T@Z+alpha*np.eye(Z.shape[1]),Z.T@(y-Ym));return mu,sd,Ym,b
def predict(x,model):
 mu,sd,ym,b=model;return float(((x-mu)/sd)@b+ym)
def dist(mu,sigma):
 vals=list(range(-15,16)); ps=[]
 for gd in vals:ps.append(float(ndtr((gd+.5-mu)/sigma)-ndtr((gd-.5-mu)/sigma)))
 ps[0]=float(ndtr((-14.5-mu)/sigma));ps[-1]=float(1-ndtr((14.5-mu)/sigma));z=sum(ps);return vals,[max(0,p/z) for p in ps]
def ev(line,odds,side,vals,ps):return sum(p*qline(line,side,odds,g) for p,g in zip(ps,vals))
def stats(rows):
 rows=list(rows);n=len(rows);u=sum(x['net_u'] for x in rows);daily=collections.defaultdict(float);wk=collections.defaultdict(lambda:[0,0.]);states=collections.Counter();leagues=collections.defaultdict(list);odds=[]
 for x in rows:
  daily[x['date']]+=x['net_u'];d=dt.date.fromisoformat(x['date']);iso=d.isocalendar();w=f'{iso.year}-W{iso.week:02d}';wk[w][0]+=1;wk[w][1]+=x['net_u'];states[x['settlement']]+=1;leagues[x['league']].append(x);odds.append(x['odds'])
 eq=peak=mdd=0.
 for d,z in sorted(daily.items()):eq+=z;peak=max(peak,eq);mdd=max(mdd,peak-eq)
 return {'n':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'max_drawdown_u':round(mdd,6),
  'average_odds':round(sum(odds)/n,6) if n else None,'settlements':dict(states),
  'weekly_mean_n':round(n/len(wk),6) if wk else None,'weekly_mean_net_u':round(u/len(wk),6) if wk else None,
  'weekly':{k:{'n':v[0],'net_u':round(v[1],6)} for k,v in sorted(wk.items())},
  'by_league':{k:{'n':len(v),'net_u':round(sum(z['net_u'] for z in v),6),'roi_pct':round(100*sum(z['net_u'] for z in v)/len(v),6)} for k,v in sorted(leagues.items())}}
def predictive_metrics(rows):
 rows=list(rows)
 if not rows:return {'n':0}
 err=np.asarray([x['predicted_home_margin']-x['gd'] for x in rows],float)
 nll=[];rps=[]
 for x in rows:
  vals,ps=dist(x['predicted_home_margin'],x['residual_sigma']);y=int(x['gd'])
  yi=max(-15,min(15,y));nll.append(-math.log(max(ps[yi+15],1e-12)))
  cf=0.;score=0.
  for g,p in zip(vals,ps):
   cf+=p;score+=(cf-(1.0 if y<=g else 0.0))**2
  rps.append(score/len(vals))
 return {'n':len(rows),'margin_rmse':round(float(np.sqrt(np.mean(err**2))),6),'margin_mae':round(float(np.mean(np.abs(err))),6),
         'margin_bias_pred_minus_actual':round(float(err.mean()),6),'discrete_margin_nll':round(float(np.mean(nll)),6),
         'discrete_margin_rps':round(float(np.mean(rps)),8)}

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 fixtures,mapped,issues,tm_games,scores,paths,frozen,sched,tm_path=load_matches()
 teamf=build_team_features(fixtures,scores,paths)
 for r in mapped:r['team_history']=teamf.get(r['fid'],{})
 # Strictly score only mapped fixtures with complete prior history records.
 mapped=[r for r in mapped if r['fid'] in teamf]
 candidates=[r for r in mapped if r['year'] in (2024,2025,2026) and not r['frozen']]
 candidates.sort(key=lambda x:(x['date'],x['fid']))
 preds=[];folds={};model_yr=collections.defaultdict(list)
 for year in (2024,2025,2026):
  tr=[r for r in mapped if r['year']<year and r['year']>=2019]
  te=[r for r in candidates if r['year']==year]
  if not tr or not te:folds[str(year)]={'train_n':len(tr),'test_n':len(te),'status':'insufficient'};continue
  yy=np.asarray([r['gd'] for r in tr],float); specs={}
  for name in ('market_only','market_team_history','market_team_plus_prior_venue_stability'):
   X=np.vstack([design(r,name) for r in tr]);model=fit(X,yy,alpha=20.)
   resid=yy-np.asarray([predict(design(r,name),model) for r in tr]);sigma=max(.75,float(np.std(resid,ddof=1)))
   specs[name]=(model,sigma)
  folds[str(year)]={'train_n':len(tr),'test_n':len(te),'train_years':sorted({r['year'] for r in tr}),'ridge_alpha':20.,
   'market_only_feature_count':4,'team_history_feature_count_added':6,'venue_history_feature_count_added':8,'target_year_not_used_for_fit':True}
  for r in te:
   out={k:r[k] for k in ('fid','year','date','ko_utc','kickoff_beijing','league','home_id','away_id','home','away','tm_game_id','tm_home_club_id','tm_away_club_id','tm_date','stadium','line','home_odds','away_odds','hg','ag','gd','quote_source','frozen')}
   out['actual_venue_labels']=r['pregame_venue_history'];out['strictly_prior_team_history']=r['team_history'];out['models']={}
   for name,(model,sigma) in specs.items():
    mu=predict(design(r,name),model);vals,ps=dist(mu,sigma)
    eh=ev(r['line'],r['home_odds'],'home',vals,ps);ea=ev(r['line'],r['away_odds'],'away',vals,ps);side='home' if eh>=ea else 'away';odds=r['home_odds'] if side=='home' else r['away_odds']
    pnl=qline(r['line'],side,odds,r['gd']);label=qstate(r['line'],side,r['gd'])
    pred={'predicted_home_margin':round(mu,6),'residual_sigma':round(sigma,6),'home_EV_U':round(eh,6),'away_EV_U':round(ea,6),
          'direction':side,'odds':odds,'settlement':label,'net_u':round(pnl,6),'model_ev_direction':max(eh,ea)}
    out['models'][name]=pred
    z={**out,**pred,'model':name,'source':'historical_crown_event_time_replay','actual_http_receipt':False,'formal_order':False}
    model_yr[name].append(z)
   # Prediction metrics from same model distributions are recomputed for file-level audit.
   preds.append(out)
 # Frozen original eight baseline and unique union by FID, China time.
 fr=[]
 for fid,m in frozen.items():
  s=scores.get(fid)
  if not s:continue
  ko=parseutc(s['ko']).astimezone(TZ)
  if ko.year in (2024,2025,2026):fr.append({'fid':fid,'year':ko.year,'date':ko.date().isoformat(),'league':str(s['league']),'net_u':float(m['pnl']),'odds':1.9,'settlement':'frozen_original_member'})
 results={};by_year={};models={}
 for name,rr in model_yr.items():
  models[name]=stats(rr);by_year[name]={str(y):stats(x for x in rr if x['year']==y) for y in (2024,2025,2026)}
  dedup={x['fid']:x for x in fr}
  for x in rr:dedup[x['fid']]=x
  models[name]['merged_with_frozen_2024_2026']=stats(dedup.values())
  results[name]=rr
 # Descriptive environment labels: not model filters; include all matches.
 desc={}
 cats=[('home_target_site_prior_share_positive',lambda r:None if r['pregame_venue_history']['home_prior_site_share'] is None else r['pregame_venue_history']['home_prior_site_share']>0),
       ('home_target_site_is_not_prior_modal',lambda r:r['pregame_venue_history']['home_actual_ground_change_label']),
       ('away_club_previously_homed_at_target_site',lambda r:r['pregame_venue_history']['away_club_site_match_prior']),
       ('target_site_unfamiliar_to_both_prior_home_teams_proxy',lambda r:r['pregame_venue_history']['actual_site_unfamiliar_to_both_proxy'])]
 for label,fn in cats:
  desc[label]={}
  vals={fn(r) for r in candidates}
  for value in sorted(vals,key=lambda x:(x is None,str(x))):
   subset=[r for r in candidates if fn(r)==value];base=[]
   for r in subset:
    side='home' if r['home_odds']<=r['away_odds'] else 'away';odds=r['home_odds'] if side=='home' else r['away_odds'];pnl=qline(r['line'],side,odds,r['gd'])
    base.append({'fid':r['fid'],'date':r['date'],'league':r['league'],'odds':odds,'settlement':qstate(r['line'],side,r['gd']),'net_u':pnl})
   desc[label][str(value)]={'n':len(subset),'favorite_result':stats(base),
      'annual_n':{str(y):sum(r['year']==y for r in subset) for y in (2024,2025,2026)},
      'annual_favorite_net_u':{str(y):round(sum(x['net_u'] for x in base if dt.date.fromisoformat(x['date']).year==y),6) for y in (2024,2025,2026)},
      'label_is_retrospective_not_pregame_gate':True}
 # True actual receipt overlap: verified archives already contain receipt time and Crown prices.
 candids={r['fid'] for r in candidates};recids=collections.Counter()
 receipt_sources=[ROOT/'research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl',
                 WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl',RECEIPTS]
 recrows=0
 for p in receipt_sources:
  if not p.exists():continue
  for x in readj(p):
   fid=str(x.get('fid',x.get('fixture_id','')));recrows+=1
   if fid and fid in candids:recids[fid]+=1
 receipt_audit={'sources':[{'path':str(p),'sha256':sha(p)} for p in receipt_sources if p.exists()],
                'receipt_rows_read':recrows,'unique_candidate_fids_with_verified_receipts':len(recids),
                'candidate_fids_overlap':sorted(recids),'model_replay_n':0,
                'reason':'No pregame-vintage venue snapshot is available for receipt FIDs; historical games.csv stadium data has no source/received timestamp.'}
 # Per-method overall and annual summary, weekly/league/settlement details in JSON.
 coverage={'crown_path_rows':len(paths),'score_rows':len(scores),'saved_crown_schedule_ids':len(sched),
  'schedule_files':len(list(SCHEDULE.glob('*/page-*.raw.json'))),'schedule_verified_fids':sum(1 for fid in paths if fid in sched),
  'venue_identity_join_rows_all_years':len(mapped),'venue_unique_names':len({r['stadium_key'] for r in mapped}),
  'tm_games_rows':len(tm_games),'tm_stadium_nonempty_rows':sum(bool(r['_stadium']) for r in tm_games),'tm_stadium_missing_rows':sum(not r['_stadium'] for r in tm_games),
  'tm_game_date_range':[min(r['_date'] for r in tm_games).isoformat(),max(r['_date'] for r in tm_games).isoformat()],
  'candidate_target_year_counts':{str(y):sum(r['year']==y for r in candidates) for y in (2024,2025,2026)},
  'venue_join_target_year_counts_including_frozen':{str(y):sum(r['year']==y for r in mapped) for y in (2024,2025,2026)},
  'frozen_fids_with_venue_join_2024_2026':sum(r['year'] in (2024,2025,2026) and r['frozen'] for r in mapped),
  'candidate_fids':len(candidates),'candidate_frozen_overlap':0,'frozen_eight_unique':len(frozen),
  'venue_join_issues':dict(issues),'link_method':'schedule FID + Crown home/away IDs/FT; then Transfermarkt competition/date +/- 1 day and ordered team-name match (score checked only after match); target score never selects identity.',
  'venue_source_sha256':sha(DATA/'games.csv.gz'),'crown_path_sha256':sha(PATH),'crown_score_sha256':sha(SCORES),'frozen_sha256':sha(MEM)}
 pred_metrics={name:{'all_test_years':predictive_metrics(rr),'by_year':{str(y):predictive_metrics(x for x in rr if x['year']==y) for y in (2024,2025,2026)}} for name,rr in model_yr.items()}
 result={'study':'M8 venue and away-environment pricing bias, AH only, research only','coverage':coverage,'walkforward_folds':folds,
  'models':models,'model_by_year':by_year,'prediction_metrics':pred_metrics,'retrospective_environment_diagnostics':desc,'actual_receipt_audit':receipt_audit,
  'limits':['No venue coordinates or elevation data in current inputs; no defensible distance, timezone shift, or altitude calculation.','No independently timestamped temporary-ground/neutral-site status; target stadium label is taken from retrospective Transfermarkt game row and used only for explanatory exposure diagnostics.','No stadium announcement-vintage snapshot, so the venue-stability model only uses dated prior-game history and is not a verified live receipt test.','2026 Transfermarkt games end 2026-07-06; later 2026 fixtures have no venue row.','Only mapped competitions and score/date/name-verified Transfermarkt games are in analysis; no other bookmaker prices.','No target-year tuning, venue-group ROI threshold selection, or production gate.'],
  'all_fixture_rows':preds}
 (OUT/'results_20261120.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 # Main full candidate ledger contains forecast price/side/FT and every environment label.
 with gzip.open(OUT/'per_fixture_venue_predictions_20261120.jsonl.gz','wt',encoding='utf8') as f:
  for x in preds:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
 # Separate full venue identity/FT cohort ledger, including frozen overlaps.
 with gzip.open(OUT/'venue_identity_cohort_20261120.jsonl.gz','wt',encoding='utf8') as f:
  for x in mapped:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
 print(json.dumps({'coverage':coverage,'models':{k:{'n':v['n'],'net_u':v['net_u'],'roi_pct':v['roi_pct'],'mdd':v['max_drawdown_u']} for k,v in models.items()},'receipt':receipt_audit},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
