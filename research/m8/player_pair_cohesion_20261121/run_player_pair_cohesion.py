#!/usr/bin/env python3
"""Walk-forward test of historical player-pair cohesion × Crown AH pricing.

Uses only prior completed lineups with a conservative date cutoff. Target-game
lineups, outcomes beyond the target fixture, and later membership are excluded
from features. Research only; no production logic is imported or changed.
"""
from __future__ import annotations
import bisect,collections,csv,datetime as dt,gzip,hashlib,json,math,pathlib,statistics,sys
import numpy as np

OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[2]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
SOURCE=WORK/'m8_pregame_info_source_20261117'
FOUNDATION=WORK/'m8_foundation_20261115/historical_membership.jsonl'
RECEIPTS=WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
GAMES=SOURCE/'games.csv.gz'; LINEUPS=SOURCE/'game_lineups.csv.gz'; APPEARANCES=SOURCE/'appearances.csv.gz'
MARKET=WORK/'m8_early_joint_market_inventory_20261115.jsonl'
MANAGER=WORK/'m8_prior_manager_turnover_20261117.py'
ALPHA=100.0

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def read_jsonl(path):
 with open(path,encoding='utf8') as f:
  for s in f:
   if s.strip(): yield json.loads(s)
def write_gz(path,rows):
 with open(path,'wb') as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
   for r in rows: gz.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
def exec_prefix(path,marker,name):
 src=path.read_text(encoding='utf8'); ns={'__file__':str(path),'__name__':name}
 i=src.index(marker);exec(compile(src[:i],str(path)+'[identity-prefix]','exec'),ns);return ns
def settle(line,side,gd,odds):
 signed=float(line) if side=='home' else -float(line);margin=int(gd) if side=='home' else -int(gd)
 if abs(signed*4-round(signed*4))>1e-8: raise ValueError('AH line outside quarter grid')
 legs=(signed,) if abs(signed*2-round(signed*2))<1e-8 else (math.floor(signed*2)/2,math.ceil(signed*2)/2)
 vals=[]; labs=[]
 for leg in legs:
  d=margin+leg;labs.append('W' if d>1e-9 else 'L' if d< -1e-9 else 'P')
  vals.append(float(odds)-1 if d>1e-9 else -1. if d< -1e-9 else 0.)
 net=sum(vals)/len(vals)
 state='full_win' if all(v=='W' for v in labs) else 'full_loss' if all(v=='L' for v in labs) else 'push' if all(v=='P' for v in labs) else 'half_win' if net>0 else 'half_loss' if net<0 else 'push'
 return state,net
def cdf(x): return .5*(1.+math.erf(x/math.sqrt(2.)))
def margin_dist(mu,sigma):
 sig=max(float(sigma),.35);lo=-12;ps=[max(0.,cdf((k+.5-mu)/sig)-cdf((k-.5-mu)/sig)) for k in range(lo,13)]
 z=sum(ps);return [(lo+i,p/z) for i,p in enumerate(ps)]
def choose(line,ho,ao,mu,sigma):
 d=margin_dist(mu,sigma)
 eh=sum(p*settle(line,'home',g,ho)[1] for g,p in d);ea=sum(p*settle(line,'away',g,ao)[1] for g,p in d)
 side=None if abs(eh-ea)<1e-12 else 'home' if eh>ea else 'away'
 return side,eh,ea
def ridge_fit(X,y):
 X=np.asarray(X,float);y=np.asarray(y,float);m=X.mean(0);s=X.std(0);s=np.where(s<1e-10,1.,s)
 z=(X-m)/s;d=np.column_stack([np.ones(len(z)),z]);p=np.eye(d.shape[1])*ALPHA;p[0,0]=0.
 b=np.linalg.solve(d.T@d+p,d.T@y);res=y-d@b
 return m,s,b,max(.35,float(np.sqrt(np.mean(res*res))))
def predict(fit,x):
 m,s,b,_=fit;return float(np.r_[1.,(np.asarray(x,float)-m)/s]@b)
def mdd(rows):
 day=collections.defaultdict(float)
 for r in rows:day[r['date']]+=float(r['net_u'])
 c=peak=dd=0.
 for k in sorted(day):c+=day[k];peak=max(peak,c);dd=max(dd,peak-c)
 return round(dd,6)
def stats(rows,span=None):
 n=len(rows);u=sum(float(r['net_u']) for r in rows)
 if not n:return {'n':0,'net_U':0.,'ROI_pct':None,'MDD_U':0.,'orders_per_week':0.,'five_state':{}}
 dates=[dt.date.fromisoformat(r['date']) for r in rows];weeks=span or (max(dates)-min(dates)).days//7+1
 return {'n':n,'net_U':round(u,6),'ROI_pct':round(100*u/n,6),'MDD_U':mdd(rows),'orders_per_week':round(n/weeks,6),
         'five_state':dict(collections.Counter(r['settlement'] for r in rows))}
def grouped(rows,key):
 d=collections.defaultdict(list)
 for r in rows:d[r[key]].append(r)
 return {str(k):stats(v) for k,v in sorted(d.items(),key=lambda z:str(z[0]))}
def pairs(x):
 y=sorted(set(map(str,x)))
 return [(y[i],y[j]) for i in range(len(y)) for j in range(i+1,len(y))]

def load_team_history(teammap,cm):
 invcomp={v:k for k,v in cm.items()};invteam=collections.defaultdict(dict)
 for (lid,crown_tid),club in teammap.items(): invteam[str(lid)][str(club)]=str(crown_tid)
 relevant={};audit=collections.Counter()
 with gzip.open(GAMES,'rt',encoding='utf8') as f:
  for g in csv.DictReader(f):
   lid=invcomp.get(str(g.get('competition_id')))
   if not lid:continue
   h=str(g.get('home_club_id') or '');a=str(g.get('away_club_id') or '')
   ht=invteam[lid].get(h);at=invteam[lid].get(a)
   if not ht or not at:continue
   try:d=dt.date.fromisoformat(g['date'])
   except Exception:audit['bad_game_date']+=1;continue
   gid=str(g['game_id']);relevant[gid]={'date':d,'league':lid,'home_club':h,'away_club':a,'home_tid':ht,'away_tid':at}
 audit['mapped_games']=len(relevant)
 starts=collections.defaultdict(lambda:collections.defaultdict(list))
 with gzip.open(LINEUPS,'rt',encoding='utf8') as f:
  for x in csv.DictReader(f):
   gid=str(x.get('game_id') or '');g=relevant.get(gid)
   if not g or x.get('type')!='starting_lineup':continue
   club=str(x.get('club_id') or '')
   if club not in (g['home_club'],g['away_club']):audit['lineup_club_mismatch']+=1;continue
   starts[gid][club].append(str(x.get('player_id') or ''))
 apps=collections.defaultdict(set)
 with gzip.open(APPEARANCES,'rt',encoding='utf8') as f:
  for x in csv.DictReader(f):
   gid=str(x.get('game_id') or '');g=relevant.get(gid)
   if not g:continue
   club=str(x.get('player_club_id') or '')
   if club not in (g['home_club'],g['away_club']):continue
   try:mins=float(x.get('minutes_played') or 0)
   except Exception:continue
   if mins>0:apps[(gid,club)].add(str(x.get('player_id') or ''))
 hist=collections.defaultdict(list)
 for gid,g in relevant.items():
  for side in ('home','away'):
   club=g[side+'_club'];tid=g[side+'_tid'];xi=starts[gid].get(club,[])
   if len(xi)!=11 or len(set(xi))!=11:audit['incomplete_starting_eleven']+=1;continue
   if not set(xi)<=apps.get((gid,club),set()):audit['starter_without_positive_appearance']+=1;continue
   hist[(g['league'],tid)].append((g['date'],tuple(sorted(xi)),gid))
   audit['valid_team_match_lineups']+=1
 for k in hist:hist[k].sort(key=lambda z:(z[0],z[2]))
 return hist,audit

def team_cohesion(hist,key,day):
 cutoff=day-dt.timedelta(days=3);lo=cutoff-dt.timedelta(days=365)
 z=[x for x in hist.get(key,[]) if lo<x[0]<=cutoff]
 if len(z)<3:return None
 exposure=collections.Counter();last5=z[-5:]
 for _,xi,_ in z:
  exposure.update(pairs(xi))
 all_n=sum(exposure.values());uniq=len(exposure)
 if not all_n or not uniq:return None
 repeated=sum(v for v in exposure.values() if v>=2)/all_n
 triples=sum(v for v in exposure.values() if v>=3)/all_n
 probs=[v/all_n for v in exposure.values()]
 entropy=-sum(p*math.log(p) for p in probs if p>0)/(math.log(uniq) if uniq>1 else 1.)
 top_share=sum(v for v in sorted(exposure.values(),reverse=True)[:max(1,math.ceil(.1*uniq))])/all_n
 # Cohesion in the team's last five completed XI records, measured only by
 # co-start repetitions that occurred earlier than each of those matches.
 recent_repeat=[];recent_prior=[];recent_dates=[]
 for j,(d,xi,_) in enumerate(last5):
  prior=collections.Counter()
  for pd,pxi,_ in z[:len(z)-len(last5)+j]:
   if d-dt.timedelta(days=365)<pd<d:prior.update(pairs(pxi))
  pp=pairs(xi);recent_repeat.append(sum(prior[q]>=2 for q in pp)/len(pp));recent_prior.append(statistics.mean(prior[q] for q in pp));recent_dates.append(d)
 # Distribution of distinct pair supports and trend, not an eligibility gate.
 return {'n_team_matches_365':len(z),'unique_pair_count_365':uniq,
  'repeat_pair_exposure_share_365':repeated,'triple_plus_pair_exposure_share_365':triples,
  'normalized_pair_entropy_365':entropy,'top_decile_pair_exposure_share_365':top_share,
  'last5_preexisting_repeat_pair_share':statistics.mean(recent_repeat),
  'last5_mean_prior_pair_costarts':statistics.mean(recent_prior),
  'last5_recent_repeat_minus_old':statistics.mean(recent_repeat[-2:])-statistics.mean(recent_repeat[:2]) if len(recent_repeat)>=4 else 0.,
  'last_history_date':max(recent_dates).isoformat()}
def pair_features(h,a):
 keys=('repeat_pair_exposure_share_365','triple_plus_pair_exposure_share_365','normalized_pair_entropy_365',
       'top_decile_pair_exposure_share_365','last5_preexisting_repeat_pair_share','last5_mean_prior_pair_costarts',
       'last5_recent_repeat_minus_old')
 out=[]
 for k in keys:out.extend((h[k]+a[k],h[k]-a[k]))
 return out

def main():
 sys.path.insert(0,str(ROOT))
 bridge=exec_prefix(MANAGER,'# Build historical coach timeline','m8_pair_cohesion_identity')
 teammap=bridge['teammap'];cm=bridge['cm']
 hist,audit=load_team_history(teammap,cm)
 foundation={str(r['fid']):r for r in read_jsonl(FOUNDATION)}
 receipt_ids={str(r['fixture_id']) for r in read_jsonl(RECEIPTS)}
 allrows=[r for r in read_jsonl(MARKET) if int(r['T'])==12]
 if len({str(r['fid']) for r in allrows})!=len(allrows): raise AssertionError('T12 inventory contains duplicate FIDs')
 feature_cache={}
 targets=[];miss=collections.Counter()
 for r in allrows:
  fid=str(r['fid']);day=dt.date.fromisoformat(r['date']);lid=str(r['league'])
  ht=teammap.get((lid,str(r['home_id'])));at=teammap.get((lid,str(r['away_id'])))
  if not ht or not at:miss['unmapped_target_team']+=1;continue
  kh=(lid,str(r['home_id']),day);ka=(lid,str(r['away_id']),day)
  if kh not in feature_cache:feature_cache[kh]=team_cohesion(hist,(lid,str(r['home_id'])),day)
  if ka not in feature_cache:feature_cache[ka]=team_cohesion(hist,(lid,str(r['away_id'])),day)
  fh=feature_cache[kh];fa=feature_cache[ka]
  if fh is None or fa is None:miss['insufficient_complete_prior_lineups']+=1;continue
  line=float(r['al']);ho=float(r['ah']);ao=float(r['aa'])
  if min(ho,ao)<=1 or abs(line*4-round(line*4))>1e-7:miss['invalid_Crown_contract']+=1;continue
  d=dt.date.fromisoformat(r['date']);features=pair_features(fh,fa)
  targets.append({'fid':fid,'year':int(r['year']),'date':str(r['date']),'iso_week':f'{d.isocalendar().year}-W{d.isocalendar().week:02d}',
   'league':lid,'home_id':str(r['home_id']),'away_id':str(r['away_id']),'home_tm_club_id':str(ht),'away_tm_club_id':str(at),
   'hg':int(r['hg']),'ag':int(r['ag']),'gd':int(r['hg'])-int(r['ag']),'T12_AH_home_line':line,'T12_home_odds':ho,'T12_away_odds':ao,
   'pair_features_home':fh,'pair_features_away':fa,'pair_features':features,
   'cohesion_cutoff':(d-dt.timedelta(days=3)).isoformat(),'formation_source':'verified complete past starting XI + positive appearance minutes; no publication timestamp',
   'frozen_overlap':fid in foundation,'actual_receipt_fid_overlap':fid in receipt_ids})
 targets.sort(key=lambda x:(x['date'],x['fid']))
 years=(2024,2025,2026);methods=('market_only','pair_only','market_plus_pair');pred={m:[] for m in methods};folds={};annual={};weekly={};league={}
 receipt_rows={r['fid']:r for r in (json.loads(x) for x in gzip.open(ROOT/'research/m8/prior_formation_market_20261121/formation_market_actual_receipt_replay_20261121.jsonl.gz','rt')) if r['method']=='market_only'}
 receipt_quotes={fid:r['receipt_quote'] for fid,r in receipt_rows.items()}
 fit2026={}
 for year in years:
  train=[r for r in targets if 2019<=r['year']<year and r['fid'] not in receipt_ids]
  test=[r for r in targets if r['year']==year]
  if not train or not test:continue
  fits={}
  for m in methods:
   def xof(r):
    market=[-r['T12_AH_home_line']+.25*math.log(r['T12_away_odds']/r['T12_home_odds']),r['T12_AH_home_line'],.25*math.log(r['T12_away_odds']/r['T12_home_odds'])]
    return market if m=='market_only' else r['pair_features'] if m=='pair_only' else market+r['pair_features']
   fit=ridge_fit([xof(r) for r in train],[r['gd'] for r in train]);fits[m]=fit
   if year==2026:fit2026[m]=fit
   for r in test:
    mu=predict(fit,xof(r));side,eh,ea=choose(r['T12_AH_home_line'],r['T12_home_odds'],r['T12_away_odds'],mu,fit[3])
    if side is None:state='push';net=0.;price=None
    else:price=r['T12_home_odds'] if side=='home' else r['T12_away_odds'];state,net=settle(r['T12_AH_home_line'],side,r['gd'],price)
    pred[m].append({**r,'method':m,'predicted_home_goal_difference':round(mu,8),'predicted_sigma':round(fit[3],8),
       'home_EV_U':round(eh,8),'away_EV_U':round(ea,8),'chosen_side':side,'chosen_odds':price,'settlement':state,'net_u':round(net,8),
       'training_year_cutoff_exclusive':year})
  folds[str(year)]={'train_n':len(train),'train_years':sorted({r['year'] for r in train}),'train_max_year':max(r['year'] for r in train),'test_n':len(test),
   'receipt_ids_excluded_from_training':True,'ridge_alpha':ALPHA,'model_features':{m:3 if m=='market_only' else len(test[0]['pair_features']) if m=='pair_only' else 3+len(test[0]['pair_features']) for m in methods},
   'sigma':{m:round(fits[m][3],8) for m in methods}}
 for m,arr in pred.items():
  inc=[r for r in arr if not r['frozen_overlap']]
  annual[m]={str(y):stats([r for r in inc if r['year']==y]) for y in years}
  weekly[m]=grouped(inc,'iso_week');league[m]=grouped(inc,'league')
  arr.sort(key=lambda r:(r['date'],r['fid']))
 testdates=[dt.date.fromisoformat(r['date']) for r in targets if r['year'] in years]
 span=(max(testdates)-min(testdates)).days//7+1 if testdates else 0
 results={}
 frozen_rows=[]
 for f in read_jsonl(FOUNDATION):
  if f.get('date'):
   try:frozen_rows.append({'fid':str(f['fid']),'date':str(f['date'])[:10],'net_u':float(f['pnl'])})
   except Exception:pass
 same_window_frozen=[f for f in frozen_rows if testdates and min(testdates).isoformat()<=f['date']<=max(testdates).isoformat()]
 for m,arr in pred.items():
  inc=[r for r in arr if not r['frozen_overlap']];res=stats(inc,span)
  merge_same=same_window_frozen+inc;net_same=sum(x['net_u'] for x in merge_same)
  merge_full=frozen_rows+inc;net_full=sum(x['net_u'] for x in merge_full)
  results[m]={'all_test':stats(arr,span),'incremental_outside_frozen':res,
    'test_date_range':[min(testdates).isoformat(),max(testdates).isoformat()] if testdates else [],
    'frozen_plus_candidate_same_period':{'frozen_n':len(same_window_frozen),'candidate_n':len(inc),'n':len(merge_same),
      'net_U':round(net_same,6),'ROI_pct':round(100*net_same/len(merge_same),6),'MDD_U':mdd(merge_same),'candidate_net_U':round(sum(x['net_u'] for x in inc),6)},
    'full_frozen_plus_candidate':{'frozen_n':len(frozen_rows),'candidate_n':len(inc),'n':len(merge_full),
      'net_U':round(net_full,6),'ROI_pct':round(100*net_full/len(merge_full),6),'MDD_U':mdd(merge_full),'candidate_net_U':round(sum(x['net_u'] for x in inc),6)}}
 # Actual pre-kickoff price replay for intersecting 2026 FIDs; use 2026 forward-trained coefficients.
 receipt_pred={m:[] for m in methods};target26={r['fid']:r for r in targets if r['year']==2026}
 for fid,q in receipt_quotes.items():
  r=target26.get(fid)
  if not r:continue
  for m in methods:
   fit=fit2026.get(m)
   if fit is None:continue
   sk=.25*math.log(q['away_odds']/q['home_odds']);market=[-q['line']+sk,q['line'],sk]
   x=market if m=='market_only' else r['pair_features'] if m=='pair_only' else market+r['pair_features']
   mu=predict(fit,x);side,eh,ea=choose(q['line'],q['home_odds'],q['away_odds'],mu,fit[3])
   if side is None:state='push';net=0.;price=None
   else:price=q['home_odds'] if side=='home' else q['away_odds'];state,net=settle(q['line'],side,r['gd'],price)
   receipt_pred[m].append({**r,'method':m,'receipt_quote':q,'predicted_home_goal_difference':round(mu,8),'predicted_sigma':round(fit[3],8),
    'home_EV_U':round(eh,8),'away_EV_U':round(ea,8),'chosen_side':side,'chosen_odds':price,'settlement':state,'net_u':round(net,8),
    'source_type':'actual pregame Crown price; feature history has no first-publication timestamp and is stale for 2026 receipts'})
 receipt_summary={};receipt_weekly={}
 for m,arr in receipt_pred.items():
  inc=[r for r in arr if not r['frozen_overlap']];receipt_summary[m]={'all_receipts':stats(arr),'incremental_outside_frozen':stats(inc)};receipt_weekly[m]=grouped(inc,'iso_week')
 all_test={m:sorted(rows,key=lambda r:(r['date'],r['fid'])) for m,rows in pred.items()}
 write_gz(OUT/'pair_cohesion_per_fixture_20261121.jsonl.gz',[r for m in methods for r in all_test[m]])
 write_gz(OUT/'pair_cohesion_market_plus_pair_ledger_20261121.jsonl.gz',all_test['market_plus_pair'])
 write_gz(OUT/'pair_cohesion_actual_receipt_replay_20261121.jsonl.gz',[r for m in methods for r in receipt_pred[m]])
 daylags=[]
 for fid,r in target26.items():
  if fid not in receipt_quotes:continue
  last=max(dt.date.fromisoformat(r['pair_features_home']['last_history_date']),dt.date.fromisoformat(r['pair_features_away']['last_history_date']))
  daylags.append((dt.date.fromisoformat(r['date'])-last).days)
 summary={'study':'M8 historical player-pair co-appearance cohesion vs Crown AH','execution_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
  'inputs_sha256':{str(p):sha(p) for p in (FOUNDATION,RECEIPTS,GAMES,LINEUPS,APPEARANCES,MARKET)},
  'source_games_max_date':max((x[0] for v in hist.values() for x in v)).isoformat() if hist else None,
  'coverage':{'all_Crown_T12_FIDs':len(allrows),'complete_pair_cohesion_FIDs':len(targets),'valid_train_and_test_rows':len(targets),
   'test_FIDs_2024_2026':sum(r['year'] in years for r in targets),'test_outside_frozen_FIDs':len({r['fid'] for m in methods for r in pred[m] if not r['frozen_overlap']}),
   'frozen_overlap_test_FIDs':len({r['fid'] for r in pred['market_only'] if r['frozen_overlap']}),'missing_reasons':dict(miss),
   'history_audit':dict(audit),'actual_receipt_FID_overlap':sum(r['actual_receipt_fid_overlap'] for r in targets if r['year'] in years)},
  'methodology':{'feature':'prior 365-day co-start pair recurrence, >=2/3 co-start exposure, normalized pair entropy, top-decile pair concentration, last-five lineup pair pre-existing co-start familiarity and recent-vs-old change; per target date cutoff target date-3d; each team must have >=3 complete prior XI records.',
   'independent_difference':'R50 measured player-level overlap between previous two starting lineups. This experiment measures recurrence of player pairs across the trailing 365-day lineup network; it does not use target lineup.',
   'model':'fixed Ridge alpha 100, expanding year training, fold-local standardization, Gaussian integer goal difference using train residual RMSE; choose side with higher expected Crown AH net return; no EV/no-bet gate, no parameter search.',
   'settlement':'Crown T12 AH line and two decimal odds; quarter-lines split into two adjacent half-goal legs, half stakes.'},
  'training_folds':folds,'models':results,'annual_incremental':annual,'weekly_incremental':weekly,'league_incremental':league,
  'actual_receipt_replay':{'common_receipt_FIDs':len(receipt_quotes),'models':receipt_summary,'weekly_incremental':receipt_weekly,
    'feature_target_date_range':[min((r['date'] for r in receipt_pred['pair_only']),default=''),max((r['date'] for r in receipt_pred['pair_only']),default='')],
    'formation_archive_latest_date':max((x[0] for v in hist.values() for x in v)).isoformat() if hist else None,
    'feature_age_days':{'min':min(daylags) if daylags else None,'median':float(np.median(daylags)) if daylags else None,'max':max(daylags) if daylags else None},
    'feature_timestamp_status':'retrospective game lineups have event dates but no first-publication/receipt timestamps; 2026 receipt feature age is itemized above'},
  'formal_orders':0,'formal_ledger_writes':0,'production_changes':False}
 (OUT/'pair_cohesion_summary_20261121.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'coverage':summary['coverage'],'models':{m:v['incremental_outside_frozen'] for m,v in results.items()},'annual':annual,'receipt':receipt_summary,'receipt_feature_age':summary['actual_receipt_replay']['feature_age_days']},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__': main()
