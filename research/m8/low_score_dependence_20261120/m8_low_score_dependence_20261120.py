#!/usr/bin/env python3
"""Time-forward test of team/league low-score dependence for Crown AH.

Research only. Uses exact Crown T1/event-time contracts and frozen eight FIDs
only for overlap accounting. Historical replays are not live receipts.
"""
import collections, datetime as dt, gzip, hashlib, json, math
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax
from scipy.stats import poisson, skellam

OUT=Path(__file__).resolve().parent
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
SCORE=WORK/'m8_independent_score_strength_20261114.jsonl'
MARKET=WORK/'m8_late_full_path_water_features_20261114.jsonl'
M5=WORK/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl'
SCHEDULE=WORK/'crown-drop-expanded-62/schedule_universe.jsonl'
EXTRA=Path(__file__).resolve().parents[1]/'exact_rules_outside_original49_20261120/exact_rule_cross_league_all_complete_paths.jsonl.gz'
FROZEN=WORK/'m8_foundation_20261115/historical_membership.jsonl'
LEDGER=OUT/'m8_low_score_dependence_orders_20261120.jsonl.gz'
SUMMARY=OUT/'m8_low_score_dependence_summary_20261120.json'
UTC=dt.timezone.utc; CN=dt.timezone(dt.timedelta(hours=8))
STATES=('full_loss','half_loss','push','half_win','full_win'); SI={s:i for i,s in enumerate(STATES)}
METHODS=('CROWN_ONLY','CROWN_PLUS_POISSON','CROWN_PLUS_POOLED_DC','CROWN_PLUS_LEAGUE_DC','CROWN_PLUS_TEAM_DC')
YEARS=(2024,2025,2026); TEAM_PRIOR=20.; L2=1.
DIFFS=np.arange(-50,51)

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def read(p): return [json.loads(x) for x in open(p,encoding='utf-8') if x.strip()]
def utc(x):
 t=dt.datetime.fromisoformat(str(x).replace('Z','+00:00'))
 return t.replace(tzinfo=UTC) if t.tzinfo is None else t.astimezone(UTC)
def week(s):
 i=dt.date.fromisoformat(s).isocalendar(); return f'{i.year}-W{i.week:02d}'
def state(line,diff):
 line=float(line)
 legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 z=[diff+x for x in legs]
 if all(x>1e-9 for x in z): return 'full_win'
 if any(x>1e-9 for x in z): return 'half_win'
 if all(abs(x)<=1e-9 for x in z): return 'push'
 if any(abs(x)<=1e-9 for x in z): return 'half_loss'
 return 'full_loss'
def settle(line,side,hg,ag,odds):
 line=float(line); legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 pnl=[]
 for leg in legs:
  margin=hg-ag+leg if side=='home' else ag-hg-leg
  pnl.append(float(odds)-1 if margin>1e-9 else -1. if margin<-1e-9 else 0.)
 label='full_win' if all(x>0 for x in pnl) else 'half_win' if any(x>0 for x in pnl) else 'push' if all(x==0 for x in pnl) else 'half_loss' if any(x==0 for x in pnl) else 'full_loss'
 return sum(pnl)/len(pnl),label
def returns(odds,side):
 full={'full_loss':-1.,'half_loss':-.5,'push':0.,'half_win':(odds-1)/2,'full_win':odds-1}
 if side=='home': return np.array([full[x] for x in STATES])
 mirror={'full_loss':'full_win','half_loss':'half_win','push':'push','half_win':'half_loss','full_win':'full_loss'}
 return np.array([full[mirror[x]] for x in STATES])
def dc_score_info(h,a,hg,ag):
 p00=math.exp(-h-a);p01=p00*a;p10=p00*h;p11=p00*h*a
 score=-(h*a) if (hg,ag)==(0,0) else h if (hg,ag)==(0,1) else a if (hg,ag)==(1,0) else -1. if (hg,ag)==(1,1) else 0.
 info=p00*(h*a)**2+p01*h*h+p10*a*a+p11
 return score,info
def rho_features(history,targets):
 events=[]
 for r in history:
  s,i=dc_score_info(r['lh'],r['la'],r['hg'],r['ag'])
  events.append((r['ko'].date(),r['league'],r['home'],r['away'],s,i))
 events.sort(key=lambda x:x[0]); targets_by_day=collections.defaultdict(list)
 for r in targets: targets_by_day[r['ko'].date()].append(r)
 pooled=[0.,0.,0.]; leagues=collections.defaultdict(lambda:[0.,0.,0.]); teams=collections.defaultdict(lambda:[0.,0.,0.])
 byday=collections.defaultdict(list)
 for e in events: byday[e[0]].append(e)
 result={}; days=sorted(targets_by_day); di=0
 for day in days:
  cutoff=day-dt.timedelta(days=2)
  while di<len(events) and events[di][0]<=cutoff:
   eday=events[di][0]
   while di<len(events) and events[di][0]==eday:
    _,l,h,a,s,i=events[di]
    for acc in (pooled,leagues[l],teams[(l,h)],teams[(l,a)]): acc[0]+=s;acc[1]+=i;acc[2]+=1
    di+=1
  for r in targets_by_day[day]:
   l=r['league'];g=leagues[l];rp=pooled[0]/pooled[1] if pooled[1]>0 else 0.;rl=g[0]/g[1] if g[1]>0 else rp
   prior=TEAM_PRIOR*(g[1]/g[2] if g[2] else 0.)
   vals=[]
   for team in (r['home'],r['away']):
    z=teams[(l,team)];vals.append((z[0]+prior*rl)/(z[1]+prior) if z[1]+prior>0 else rl)
   result[r['fid']]={'rho_pooled':float(np.clip(rp,-.5,.5)),'rho_league':float(np.clip(rl,-.5,.5)),'rho_team':float(np.clip(sum(vals)/2,-.5,.5)),
    'league_history_n':int(g[2]),'home_team_history_n':int(teams[(l,r['home'])][2]),'away_team_history_n':int(teams[(l,r['away'])][2])}
 return result
def forecast_extra15():
 """Generate pre-match goal means for the extra league inventory, two-day embargo."""
 with gzip.open(EXTRA,'rt',encoding='utf-8') as f: paths=[json.loads(x) for x in f if x.strip()]
 league_ids={str(x['league']) for x in paths}; byday=collections.defaultdict(list)
 for x in read(SCHEDULE):
  if str(x.get('league_id')) not in league_ids:continue
  try:
   ko=dt.datetime.strptime(x['kickoff_source_local'],'%Y-%m-%d %H:%M:%S').replace(tzinfo=CN).astimezone(UTC)
   r={'fid':str(x['match_id']),'league':str(x['league_id']),'home':str(x['home']),'away':str(x['away']),'hg':int(x['home_goals']),'ag':int(x['away_goals']),'ko':ko}
   byday[ko.date()].append(r)
  except Exception:continue
 state0={'attack':collections.defaultdict(float),'defense':collections.defaultdict(float),'base':collections.defaultdict(lambda:[math.log(1.45),math.log(1.15)])}
 def pred(st,r):
  l=r['league'];h=(l,r['home']);a=(l,r['away']);b=st['base'][l]
  return math.exp(float(np.clip(b[0]+st['attack'][h]+st['defense'][a],-2.5,2.3))),math.exp(float(np.clip(b[1]+st['attack'][a]+st['defense'][h],-2.5,2.3)))
 def update(st,rows):
  for r in sorted(rows,key=lambda x:x['fid']):
   l=r['league'];h=(l,r['home']);a=(l,r['away']);lh=r['lh'];la=r['la'];eh=float(np.clip(r['hg']-lh,-4,4));ea=float(np.clip(r['ag']-la,-4,4))
   st['attack'][h]=.997*st['attack'][h]+.025*eh;st['attack'][a]=.997*st['attack'][a]+.025*ea
   st['defense'][a]=.997*st['defense'][a]+.025*eh;st['defense'][h]=.997*st['defense'][h]+.025*ea
   st['base'][l][0]+=.003*eh;st['base'][l][1]+=.003*ea
 days=sorted(byday);pending=[];pi=0;out={}
 for day in days:
  cutoff=day-dt.timedelta(days=2)
  while pi<len(pending) and pending[pi]['ko'].date()<=cutoff:
   od=pending[pi]['ko'].date();j=pi+1
   while j<len(pending) and pending[j]['ko'].date()==od:j+=1
   update(state0,pending[pi:j]);pi=j
  todays=sorted(byday[day],key=lambda x:x['fid'])
  for r in todays:r['lh'],r['la']=pred(state0,r);out[r['fid']]=r
  pending.extend(todays)
 return out,{'path_fids':len(paths),'history_fixtures':sum(map(len,byday.values())),'forecast_fids':len(out),'league_ids':len(league_ids),'time_cutoff':'two UTC calendar days; same-day forecasts generated before any same-day FT updates'}
def dc_valid(r,h,a):
 lo=max(-.999/max(h,1e-9),-.999/max(a,1e-9));hi=min(.999/max(h*a,1e-9),.999)
 return float(np.clip(r,lo,hi))
def state_probs(line,h,a,rho=0.):
 # The difference Skellam distribution supplies the independent-Poisson base;
 # Dixon-Coles adjusts only the four 0/1 goal cells.
 pmf=skellam.pmf(DIFFS,h,a); out=np.zeros(5)
 ix={int(d):SI[state(line,int(d))] for d in DIFFS}
 for d,p in zip(DIFFS,pmf): out[ix[int(d)]]+=float(p)
 r=dc_valid(rho,h,a)
 for gh,ga,m in ((0,0,-h*a),(0,1,h),(1,0,a),(1,1,-1.)):
  p=float(poisson.pmf(gh,h)*poisson.pmf(ga,a));out[ix[gh-ga]]+=p*m*r
 if abs(out.sum()-1)>1e-6 or out.min()<-1e-8: raise ValueError(f'invalid state probabilities {out} line={line} lambdas={h,a} rho={rho}')
 out=np.maximum(out,0);return out/out.sum(),r
def market_x(r):
 h=float(r['ho']);a=float(r['ao']);q=(1/h)/(1/h+1/a);over=1/h+1/a-1
 return np.array([float(r['line']),q,over])
def fit_softmax(x,y):
 x=np.asarray(x,float);y=np.asarray(y,int);mu=x.mean(0);sd=x.std(0);sd=np.where(sd<1e-9,1.,sd)
 z=np.column_stack([np.ones(len(x)),(x-mu)/sd]);k=5;p=z.shape[1]
 if len(set(y))<k: raise ValueError(f'training classes missing: {np.bincount(y,minlength=k).tolist()}')
 def fg(wv):
  w=wv.reshape(k,p);logits=z@w.T;pr=softmax(logits,axis=1)
  loss=(logsumexp(logits,axis=1)-logits[np.arange(len(y)),y]).mean()+.5*L2*(w[:,1:]**2).sum()
  pr[np.arange(len(y)),y]-=1;grad=pr.T@z/len(y);grad[:,1:]+=L2*w[:,1:]
  return loss,grad.ravel()
 opt=minimize(fg,np.zeros(k*p),jac=True,method='L-BFGS-B',options={'maxiter':400,'ftol':1e-9})
 return {'w':opt.x.reshape(k,p),'mu':mu,'sd':sd,'train_n':len(y),'classes':np.bincount(y,minlength=k).tolist(),'converged':bool(opt.success)}
def predict(f,x):
 z=np.column_stack([np.ones(len(x)),(np.asarray(x)-f['mu'])/f['sd']]);return softmax(z@f['w'].T,axis=1)
def features(r):
 m=market_x(r);return {'CROWN_ONLY':m,'CROWN_PLUS_POISSON':np.r_[m,r['p_ind']],
  'CROWN_PLUS_POOLED_DC':np.r_[m,r['p_pooled']],
  'CROWN_PLUS_LEAGUE_DC':np.r_[m,r['p_league']],'CROWN_PLUS_TEAM_DC':np.r_[m,r['p_team']]}
def metric(rows):
 get_u=lambda x:float(x.get('u',x.get('net_u',0.)))
 n=len(rows);u=sum(get_u(x) for x in rows);daily=collections.defaultdict(float);weeks=collections.Counter();byyear=collections.defaultdict(list);byleague=collections.defaultdict(list);states=collections.Counter()
 for x in rows: daily[x['date']]+=get_u(x);weeks[x['week']]+=1;byyear[str(x['year'])].append(x);byleague[x['league']].append(x);states[x['state']]+=1
 run=peak=mdd=0.
 for _,v in sorted(daily.items()):run+=v;peak=max(peak,run);mdd=max(mdd,peak-run)
 if rows:
  lo=dt.date.fromisoformat(min(x['date'] for x in rows));hi=dt.date.fromisoformat(max(x['date'] for x in rows));a=lo-dt.timedelta(days=lo.weekday());b=hi-dt.timedelta(days=hi.weekday());nw=(b-a).days//7+1
 else:nw=0
 def sub(z):
  n=len(z);u=sum(get_u(x) for x in z);return {'orders':n,'net_u':round(u,6),'roi_pct':round(u/n*100,6) if n else None}
 return {'orders':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'mdd_u':round(mdd,6),'calendar_iso_weeks':nw,'orders_per_calendar_week':round(n/nw,6) if nw else 0.,'active_iso_weeks':len(weeks),'settlements':dict(states),'by_year':{k:sub(v) for k,v in sorted(byyear.items())},'by_league':{k:sub(v) for k,v in sorted(byleague.items())},'by_iso_week':{k:sub([x for x in rows if x['week']==k]) for k in sorted(weeks)}}
def main():
 scores=read(SCORE);scoremap={str(x['fid']):x for x in scores};frozen={str(x['fid']) for x in read(FROZEN)}
 assert len(frozen)==10294
 market=read(MARKET); mkt={str(x['fid']):x for x in market}
 # 2019-2025 T1 event-time history. 2026 is replaced by the existing M5 archive.
 targets=[];lambda_by_fid={str(s['fid']):(float(s['lambda_home_0.025']),float(s['lambda_away_0.025'])) for s in scores}
 for fid,r in mkt.items():
  if fid not in scoremap: continue
  s=scoremap[fid];ko=utc(s['ko']);local=ko.astimezone(CN)
  if local.year>=2026: continue
  targets.append({'fid':fid,'segment':'original49','league':str(r['league']),'home':str(s['home']),'away':str(s['away']),'hg':int(s['hg']),'ag':int(s['ag']),'ko':ko,'date':local.date().isoformat(),'year':local.year,'line':float(r['end_line']),'ho':float(r['home_price']),'ao':float(r['away_price']),'quote_source':'historical Crown T1 event-time replay'})
 m5=read(M5); m5raw_n=0; m5score_missing=[]
 for r in m5:
  fid=str(r['fid']);s=scoremap.get(fid)
  if s is None:m5score_missing.append(fid);continue
  ko=utc(s['ko']);local=ko.astimezone(CN)
  if local.year!=2026: continue
  hg,ag=map(int,str(r['score_goals']).split('-'))
  if (hg,ag)!=(int(s['hg']),int(s['ag'])):raise AssertionError(f'FT mismatch {fid}')
  targets.append({'fid':fid,'segment':'original49','league':str(r['league_id']),'home':str(s['home']),'away':str(s['away']),'hg':hg,'ag':ag,'ko':ko,'date':local.date().isoformat(),'year':2026,'line':float(r['AH_t1_line']),'ho':float(r['AH_t1_odds_home']),'ao':float(r['AH_t1_odds_away']),'quote_source':'M5 cached Crown historical replay; HTTP response post-kickoff','prospective_observation':False})
 extra_lambdas,extra_coverage=forecast_extra15()
 with gzip.open(EXTRA,'rt',encoding='utf-8') as f: extra_paths=[json.loads(x) for x in f if x.strip()]
 for r in extra_paths:
  fid=str(r['fid']);ko=utc(r['kickoff_utc']);local=ko.astimezone(CN)
  targets.append({'fid':fid,'segment':'additional15','league':str(r['league']),'home':str(r['home']),'away':str(r['away']),'hg':int(r['hg']),'ag':int(r['ag']),'ko':ko,'date':local.date().isoformat(),'year':local.year,'line':float(r['end_line']),'ho':float(r['home_price']),'ao':float(r['away_price']),'quote_source':'historical Crown complete-path event-time replay'})
 for fid,r in extra_lambdas.items():lambda_by_fid[fid]=(float(r['lh']),float(r['la']))
 ids=[x['fid'] for x in targets];assert len(ids)==len(set(ids)), 'duplicate FIDs in study target inventory'
 # Build history score rates from the existing time-forward independent score model.
 hist=[]
 for s in scores:
  hist.append({'fid':str(s['fid']),'league':str(s['league']),'home':str(s['home']),'away':str(s['away']),'hg':int(s['hg']),'ag':int(s['ag']),'ko':utc(s['ko']),'lh':float(s['lambda_home_0.025']),'la':float(s['lambda_away_0.025'])})
 for r in extra_lambdas.values():hist.append(r)
 rho=rho_features(hist,targets)
 usable=[];missing=[];clips=0
 for r in targets:
  rates=lambda_by_fid.get(r['fid'])
  if rates is None:missing.append(r['fid']);continue
  lh,la=rates;rr=rho[r['fid']]
  p0,_=state_probs(r['line'],lh,la,0.);pp,_=state_probs(r['line'],lh,la,rr['rho_pooled'])
  pl,rl=state_probs(r['line'],lh,la,rr['rho_league']);pt,rt=state_probs(r['line'],lh,la,rr['rho_team'])
  if abs(rl-rr['rho_league'])>1e-10 or abs(rt-rr['rho_team'])>1e-10:clips+=1
  x=dict(r,lh=lh,la=la,rho=rr,p_ind=p0.tolist(),p_pooled=pp.tolist(),p_league=pl.tolist(),p_team=pt.tolist(),state=state(r['line'],r['hg']-r['ag']),frozen=(r['fid'] in frozen),week=week(r['date']))
  x['features']=features(x);usable.append(x)
 # Each target year is evaluated using only earlier China-time years.
 byyear=collections.defaultdict(list)
 for r in usable:byyear[r['year']].append(r)
 ledger=[];fits={}
 for year in YEARS:
  train=[r for y,rs in byyear.items() if y<year for r in rs];test=byyear.get(year,[])
  if not train or not test:continue
  y=np.array([SI[r['state']] for r in train])
  for method in METHODS:
   fit=fit_softmax(np.vstack([r['features'][method] for r in train]),y);fits[f'{year}:{method}']={'train_years':[min(r['year'] for r in train),max(r['year'] for r in train)],'train_n':len(train),'train_classes':fit['classes'],'converged':fit['converged']}
   pp=predict(fit,np.vstack([r['features'][method] for r in test]))
   for r,p in zip(test,pp):
    evh=float(p@returns(r['ho'],'home'));eva=float(p@returns(r['ao'],'away'));side='home' if evh>=eva else 'away'
    u,label=settle(r['line'],side,r['hg'],r['ag'],r['ho'] if side=='home' else r['ao'])
    evside=side if max(evh,eva)>0 else None
    eu,el=settle(r['line'],evside,r['hg'],r['ag'],r['ho'] if evside=='home' else r['ao']) if evside else (0.,'no_bet')
    row={k:v for k,v in r.items() if k!='features'}
    row.update({'method':method,'train_years':fits[f'{year}:{method}']['train_years'],'predicted_state_probs':{s:float(p[i]) for i,s in enumerate(STATES)},'predicted_home_ev_u':evh,'predicted_away_ev_u':eva,'selected_side':side,'selected_price':r['ho'] if side=='home' else r['ao'],'settlement':label,'net_u':u,'ev_positive_side':evside,'ev_positive_settlement':el,'ev_positive_net_u':eu,'actual_http_receipt':False})
    ledger.append(row)
 summaries={}
 for method in METHODS:
  rr=[x for x in ledger if x['method']==method];inc=[x for x in rr if not x['frozen']]
  full=[dict(x,u=x['net_u'],state=x['settlement']) for x in inc]
  ev=[dict(x,u=x['ev_positive_net_u'],state=x['ev_positive_settlement']) for x in inc if x['ev_positive_side']]
  summaries[method]={'all_test_fids':metric(rr),'unique_outside_frozen_eight':metric(full),'incremental_by_segment':{seg:metric([x for x in full if x['segment']==seg]) for seg in ('original49','additional15')},'ev_positive_no_bet_diagnostic':metric(ev),'ev_positive_no_bet_by_segment':{seg:metric([x for x in ev if x['segment']==seg]) for seg in ('original49','additional15')},'ev_positive_no_bet_count':len(inc)-len(ev),'unique_incremental_fids':len(inc)}
 with gzip.open(LEDGER,'wt',encoding='utf-8') as f:
  for x in ledger:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'),default=lambda z:z.isoformat() if isinstance(z,(dt.datetime,dt.date)) else str(z))+'\n')
 summary={'study':'Time-forward AH settlement probability calibration with independent Poisson and prior team/league Dixon-Coles dependence; research only','scope':{'target_unique_fids':len(targets),'scored':len(usable),'missing_score_join':missing,'year_counts':dict(collections.Counter(str(x['year']) for x in targets)),'test_year_counts':{str(y):len(byyear.get(y,[])) for y in YEARS},'test_by_segment_year':{seg:{str(y):sum(1 for x in byyear.get(y,[]) if x['segment']==seg) for y in YEARS} for seg in ('original49','additional15')},'frozen_eight_fids':len(frozen),'frozen_sha256':sha(FROZEN),'m5_rows':len(m5),'m5_rows_without_score_mapping':m5score_missing,'m5_post_kick_receipt_rows':len(m5)-len(m5score_missing),'additional15_forecast_coverage':extra_coverage,'rho_clipped_fixtures':clips},'inputs_sha256':{'score_history':sha(SCORE),'historical_crown_paths':sha(MARKET),'m5_archive':sha(M5),'additional15_paths':sha(EXTRA),'schedule_universe':sha(SCHEDULE),'frozen_membership':sha(FROZEN)},'method':{'strength':'Original49 uses existing pregame Poisson lambda 0.025; additional15 lambdas generated from existing schedule FT with initial league rates 1.45/1.15, fixed online attack/defense updates and two-day UTC embargo','rho':'Dixon-Coles one-step score/Fisher estimate from prior target-independent Poisson residuals; pooled, league and team estimates; each team shrunk to league rho by 20 prior-match equivalents','time_embargo':'Only matches at least two UTC calendar days before target; target-year models are expanding by Beijing kick-off year','probability_model':'Multinomial softmax, prior years only, train-only standardization, fixed L2=1.0; fixed parameter across years','features':'Crown line, no-vig implied home share, overround; plus five-state settlement probabilities from independent Poisson, pooled DC, league DC or team-shrunk DC','decision_diagnostics':'Choose side with higher predicted net U for all-cover result; separate predicted EV-positive only if positive, else abstain. Research diagnostics only','settlement':'Crown line and both Crown prices; quarter AH split into two half-stake lines','receipt_status':'All historical quote paths, including M5 2026 post-kick HTTP-received cache, are historical replay not contemporaneous receipts'},'models':summaries,'fit_diagnostics':fits,'outputs':{'ledger':LEDGER.name,'summary':SUMMARY.name},'production_changes':False,'formal_telegram_orders':0,'formal_ledger_writes':0}
 SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'target_fids':len(targets),'scored':len(usable),'outside_eight':{k:{'orders':v['unique_outside_frozen_eight']['orders'],'net_u':v['unique_outside_frozen_eight']['net_u'],'roi_pct':v['unique_outside_frozen_eight']['roi_pct'],'mdd_u':v['unique_outside_frozen_eight']['mdd_u'],'ev_positive_orders':v['ev_positive_no_bet_diagnostic']['orders'],'ev_positive_net_u':v['ev_positive_no_bet_diagnostic']['net_u']} for k,v in summaries.items()}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
