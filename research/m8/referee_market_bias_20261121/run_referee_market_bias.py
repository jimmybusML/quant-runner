#!/usr/bin/env python3
"""Research-only time-forward test of referee history vs Crown AH payout."""
from __future__ import annotations
import bisect, collections, csv, datetime as dt, difflib, gzip, hashlib, json, math, pathlib, re, statistics, unicodedata
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).resolve().parent
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=WORK/'m8_pregame_info_source_20261117'
GAMES=DATA/'games.csv.gz'; APPEAR=DATA/'appearances.csv.gz'
FIXTURES=ROOT/'research/m8/attendance_crowd_pricing_20261121/attendance_crowd_per_fixture_20261121.jsonl.gz'
FOUNDATION=WORK/'m8_foundation_20261115/historical_membership.jsonl'
RECEIPTS=WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
COMP_MAP={'1':'GB1','12':'IT1','14':'ES1','16':'L1','25':'FR1','29':'A1','31':'BE1','35':'TS1','37':'NL1','48':'PL1','51':'PO1','52':'RO1','61':'C1','62':'TR1','66':'SE1','70':'DK1','73':'JAP1','75':'RSK1','88':'NO1','141':'GR1','262':'SC1','290':'SA1','303':'SER1','319':'UKR1','26540':'KR1'}
TARGET_YEARS=(2024,2025,2026)
RIDGE=100.0
SHRINK_N=10.0
LAG_DAYS=3
LOOKBACK_DAYS=730


def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def parse_dt(x):
 t=dt.datetime.fromisoformat(str(x).replace('Z','+00:00').replace(' ','T'))
 if t.tzinfo is None:t=t.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
 return t.astimezone(dt.timezone.utc)
def normalize(s):
 x=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode('ascii').lower()
 x=re.sub(r'\b(fc|cf|sc|afc|ac|club|football|soccer|fk|as)\b',' ',x)
 return re.sub(r'[^a-z0-9]','',x)
def sim(a,b):
 a,b=normalize(a),normalize(b)
 if not a or not b:return 0.0
 if a==b:return 1.0
 if min(len(a),len(b))>=6 and (a in b or b in a):return .91
 return difflib.SequenceMatcher(None,a,b).ratio()
def settle(line,side,hg,ag,odds):
 line=float(line);odds=float(odds)
 if abs(line*4-round(line*4))>1e-7:raise ValueError('invalid AH grid')
 legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 returns=[]
 for leg in legs:
  margin=(hg-ag+leg) if side=='home' else (ag-hg-leg)
  returns.append(odds-1 if margin>1e-9 else -1.0 if margin< -1e-9 else 0.0)
 pnl=sum(returns)/len(returns)
 if all(x>0 for x in returns):state='full_win'
 elif any(x>0 for x in returns):state='half_win'
 elif all(x==0 for x in returns):state='push'
 elif any(x==0 for x in returns):state='half_loss'
 else:state='full_loss'
 return round(pnl,10),state
def load_jsonl_gz(p):
 with gzip.open(p,'rt',encoding='utf8') as f:return [json.loads(x) for x in f if x.strip()]
def verify_raw(r,cache):
 p=pathlib.Path(r['market_raw_path']); b=cache.get(str(p))
 if b is None:b=p.read_bytes();cache[str(p)]=b
 if sha_bytes(b)!=r['market_raw_sha256']:raise ValueError('raw response SHA mismatch')
 payload=json.loads(b);fid=str(r['fid']);fx=next((x for x in payload.get('data',[]) if str(x.get('id'))==fid),None)
 if fx is None:raise ValueError('FID absent in raw response')
 if str(fx.get('h_id'))!=str(r['home_id']) or str(fx.get('a_id'))!=str(r['away_id']):raise ValueError('team id mismatch')
 if int(fx.get('hg'))!=int(r['ft'][0]) or int(fx.get('ag'))!=int(r['ft'][1]):raise ValueError('FT mismatch')
 if str(fx.get('l_id'))!=str(r['league_id']):raise ValueError('league mismatch')
 kick=parse_dt(fx['start']);cut=kick-dt.timedelta(hours=12)
 crown=next(x for x in fx.get('bookmakers',[]) if x.get('slug')=='crown');qs=[]
 for i,q in enumerate(crown.get('asian_list') or []):
  try:
   when=parse_dt(q[4]);line,h,a=map(float,q[1:4])
   if when<kick and when<=cut and h>1 and a>1 and abs(line*4-round(line*4))<1e-7:qs.append((when,1,i,line,h,a,'movement'))
  except Exception:pass
 for kind in ('open','close'):
  q=(crown.get('asian') or {}).get(kind)
  if isinstance(q,dict):
   try:
    when=parse_dt(q['time']);line=float(q['line']);h=float(q['home']);a=float(q['away'])
    if when<kick and when<=cut and h>1 and a>1 and abs(line*4-round(line*4))<1e-7:qs.append((when,0,kind,line,h,a,kind))
   except Exception:pass
 if not qs:raise ValueError('no raw Crown T12-or-earlier quote')
 q=max(qs,key=lambda z:(z[0],z[1],z[2] if isinstance(z[2],int) else -1))
 if abs(q[3]-r['crown_t12_line_home'])>1e-8 or abs(q[4]-r['crown_t12_home_decimal'])>1e-8 or abs(q[5]-r['crown_t12_away_decimal'])>1e-8:raise ValueError('T12 price mismatch')
 return fx,q

def calc(rows):
 if not rows:return {'n':0,'net_U':0.0,'ROI_pct':None,'MDD_U':0.0,'settlement':{},'weekly':{}}
 byday=collections.defaultdict(float);weeks=collections.defaultdict(lambda:[0,0.]);st=collections.Counter()
 for r in rows:
  byday[r['date']]+=r['net_u'];weeks[r['iso_week']][0]+=1;weeks[r['iso_week']][1]+=r['net_u'];st[r['settlement']]+=1
 bal=peak=mdd=0.0
 for day,v in sorted(byday.items()):bal+=v;peak=max(peak,bal);mdd=max(mdd,peak-bal)
 n=len(rows);u=round(sum(x['net_u'] for x in rows),6)
 d0=dt.date.fromisoformat(min(byday));d1=dt.date.fromisoformat(max(byday));calendar_weeks=(d1-d0).days//7+1
 return {'n':n,'net_U':u,'ROI_pct':round(100*u/n,6),'MDD_U':round(mdd,6),'calendar_weeks':calendar_weeks,'avg_orders_per_calendar_week':round(n/calendar_weeks,6),'active_weeks':len(weeks),'positive_weeks':sum(x[1]>1e-9 for x in weeks.values()),'negative_weeks':sum(x[1]<-1e-9 for x in weeks.values()),'settlement':dict(st),'weekly':{k:{'n':v[0],'net_U':round(v[1],6)} for k,v in sorted(weeks.items())}}
def design(rows,method,leagues):
 X=[]
 for r in rows:
  market=[1.0,r['line_home'],r['home_normalized_implied']]
  ref=[r['ref_bias_730'],r['ref_resid_raw_730'],math.log1p(r['ref_n_730']),r['ref_missing_history']]
  one=[1.0 if r['league_id']==l else 0.0 for l in leagues[1:]]
  if method=='Crown only':z=market+one
  elif method=='Ref only':z=[1.0]+ref+one
  else:z=market+ref+one
  X.append(z)
 return np.asarray(X,float)
def predict_fold(train,test,method,leagues):
 Xtr=design(train,method,leagues);Xte=design(test,method,leagues)
 if len(train)==0 or len(test)==0:return np.zeros(len(test)),{'train_n':len(train),'test_n':len(test),'status':'empty fold'}
 y=np.array([r['home_return']-r['away_return'] for r in train],float)
 mu=Xtr.mean(0);sd=Xtr.std(0);sd[sd<1e-12]=1.;mu[0]=0.;sd[0]=1.;A=(Xtr-mu)/sd;B=(Xte-mu)/sd
 if method=='Crown only':pen=RIDGE
 elif method=='Ref only':pen=RIDGE
 else:pen=RIDGE
 P=np.eye(A.shape[1])*pen;P[0,0]=0
 beta=np.linalg.solve(A.T@A+P,A.T@y)
 return B@beta,{'train_n':len(train),'test_n':len(test),'features':Xtr.shape[1],'ridge_alpha':pen,'coef':beta.tolist()}

def main():
 rows0=load_jsonl_gz(FIXTURES);games=list(csv.DictReader(gzip.open(GAMES,'rt',encoding='utf8')))
 comp_games=collections.defaultdict(list);team_names=collections.defaultdict(lambda:collections.defaultdict(set))
 for g in games:
  c=str(g.get('competition_id') or '')
  if c not in set(COMP_MAP.values()):continue
  comp_games[c].append(g)
  for side in ('home','away'):
   cid=str(g.get(side+'_club_id') or '');name=str(g.get(side+'_club_name') or '').strip()
   if cid and name:team_names[c][cid].add(name)
 # Build the same explicit league/team crosswalk used in the prior M8 attendance audit.
 crown_names=collections.defaultdict(set)
 for r in rows0:
  if r.get('home_crowd_source_club_id'):crown_names[(str(r['league_id']),str(r['home_crowd_source_club_id']))].add(r['home_name'])
  if r.get('away_crowd_source_club_id'):crown_names[(str(r['league_id']),str(r['away_crowd_source_club_id']))].add(r['away_name'])
 candidate={};map_reason=collections.Counter()
 for (lid,cid),names in crown_names.items():
  comp=COMP_MAP.get(lid)
  if not comp:continue
  scores=sorted(((max((sim(a,b) for a in names for b in vals),default=0),tmid) for tmid,vals in team_names[comp].items()),reverse=True)
  if not scores or scores[0][0]<.91:map_reason['no_strong_name_match']+=1;continue
  best=scores[0];second=scores[1] if len(scores)>1 else (0,'')
  if best[0]-second[0]<.04:map_reason['ambiguous']+=1;continue
  candidate[(lid,cid)]=best[1]
 rev=collections.Counter(candidate.values());team_map={k:v for k,v in candidate.items() if rev[v]==1}
 map_reason['non_bijective_excluded']=len(candidate)-len(team_map)
 # Exact provider-team pair and date join. Dates within +/- one day support UTC/local midnight rollover; duplicates are excluded.
 game_index=collections.defaultdict(list)
 for comp,gs in comp_games.items():
  for g in gs:
   if g.get('home_club_id') and g.get('away_club_id'):
    game_index[(comp,str(g['home_club_id']),str(g['away_club_id']))].append(g)
 joined=[];join_reasons=collections.Counter();raw_cache={};raw_errors=collections.Counter()
 for r in rows0:
  lid=str(r['league_id']);comp=COMP_MAP.get(lid)
  hm=team_map.get((lid,str(r.get('home_crowd_source_club_id') or '')));am=team_map.get((lid,str(r.get('away_crowd_source_club_id') or '')))
  if not comp or not hm or not am:join_reasons['missing_comp_or_team_crosswalk']+=1;continue
  ds=dt.date.fromisoformat(str(r['date']));cands=game_index.get((comp,hm,am),[])
  near=[g for g in cands if abs((dt.date.fromisoformat(g['date'])-ds).days)<=1]
  if len(near)!=1:join_reasons['no_match' if not near else 'ambiguous_match']+=1;continue
  g=near[0];ref=str(g.get('referee') or '').strip()
  if not ref:join_reasons['missing_referee']+=1;continue
  try:fx,q=verify_raw(r,raw_cache)
  except Exception as e:raw_errors[type(e).__name__+':'+str(e)]+=1;continue
  line=float(q[3]);ho=float(q[4]);ao=float(q[5]);hg=int(fx['hg']);ag=int(fx['ag'])
  hu,hc=settle(line,'home',hg,ag,ho);au,ac=settle(line,'away',hg,ag,ao)
  kick=parse_dt(fx['start']);date=kick.date().isoformat();iso=kick.date().isocalendar();league_id=str(r['league_id'])
  joined.append({'fid':str(r['fid']),'league_id':league_id,'league':str(fx.get('l') or r.get('league_id')),'tm_competition':comp,'tm_game_id':str(g['game_id']),'home_tm_id':hm,'away_tm_id':am,'referee':ref,'date':date,'kickoff_utc':kick.isoformat(),'iso_week':f'{iso.year}-W{iso.week:02d}','year':kick.year,'home':str(fx.get('h') or ''),'away':str(fx.get('a') or ''),'FT':[hg,ag],'line_home':line,'home_odds':ho,'away_odds':ao,'source_event_utc':q[0].isoformat(),'response_sha256':r['market_raw_sha256'],'source_file':r['market_raw_path'],'home_return':hu,'home_settlement':hc,'away_return':au,'away_settlement':ac,'net_u_favorite':hu if ho<=ao else au,'favorite_side':'home' if ho<=ao else 'away','market_margin_residual':hg-ag+line,'home_normalized_implied':(1/ho)/(1/ho+1/ao),'frozen_eight_overlap':bool(r.get('frozen_eight_overlap'))})
  join_reasons['raw_verified']=join_reasons.get('raw_verified',0)+1
 # Referee exposure features use prior Crown AH residuals only; incomplete per-player appearances are audited separately and excluded.
 joined.sort(key=lambda r:(r['date'],r['fid']))
 hist_rows=joined
 for r in hist_rows:
  r['market_margin_residual']=r['FT'][0]-r['FT'][1]+r['line_home']
 # Recompute non-leaking features from outcome history with same 3-day date embargo.
 refhist=collections.defaultdict(list);leaghist=collections.defaultdict(list)
 for r in hist_rows:
  day=dt.date.fromisoformat(r['date']).toordinal();cut=day-LAG_DAYS;rk=(r['tm_competition'],normalize(r['referee']))
  rh=refhist[rk];lh=leaghist[r['tm_competition']]
  rhdays=[x[0] for x in rh];lhdays=[x[0] for x in lh]
  i0=bisect.bisect_left(rhdays,cut-LOOKBACK_DAYS);i1=bisect.bisect_left(rhdays,cut)
  j0=bisect.bisect_left(lhdays,cut-LOOKBACK_DAYS);j1=bisect.bisect_left(lhdays,cut)
  h=[x[1] for x in rh[i0:i1]];l=[x[1] for x in lh[j0:j1]];n=len(h);lm=lambda col:(sum(x[col] for x in l)/len(l) if l else 0.)
  rm=lambda col:(sum(x[col] for x in h)/n if n else lm(col))
  r['ref_n_730']=n;r['ref_resid_raw_730']=rm('market_margin_residual')
  r['ref_bias_730']=(n/(n+SHRINK_N))*(rm('market_margin_residual')-lm('market_margin_residual')) if n else 0.
  r['ref_missing_history']=1.0 if not n else 0.
  rh.append((day,r));lh.append((day,r))
 # Make walk-forward predictions. No target-year outcomes enter that year's fit.
 target=[r for r in hist_rows if r['year'] in TARGET_YEARS]
 league_levels=sorted({r['league_id'] for r in hist_rows})
 forecast=[];training_meta={}
 for year in TARGET_YEARS:
  tr=[r for r in hist_rows if r['year']<year];te=[r for r in target if r['year']==year]
  for method in ('Crown only','Ref only','Crown + referee'):
   pred,meta=predict_fold(tr,te,method,league_levels);training_meta[f'{year}|{method}']=meta
   for r,s in zip(te,pred):
    side='home' if s>=0 else 'away';pnl=r['home_return'] if side=='home' else r['away_return'];state=r['home_settlement'] if side=='home' else r['away_settlement']
    forecast.append({**r,'method':method,'score_return_difference':float(s),'selected_side':side,'selected_odds':r['home_odds'] if side=='home' else r['away_odds'],'net_u':pnl,'settlement':state})
  for r in te:
   forecast.append({**r,'method':'Crown lower-odds side','score_return_difference':None,'selected_side':r['favorite_side'],'selected_odds':r['home_odds'] if r['favorite_side']=='home' else r['away_odds'],'net_u':r['net_u_favorite'],'settlement':r['home_settlement'] if r['favorite_side']=='home' else r['away_settlement']})
 # summarize full and truly outside frozen eight, keep each method separate.
 methods={}
 for method in ('Crown only','Ref only','Crown + referee','Crown lower-odds side'):
  mr=[r for r in forecast if r['method']==method]
  inc=[r for r in mr if not r['frozen_eight_overlap']]
  methods[method]={'all_matched_test':calc(mr),'outside_frozen_eight':calc(inc),'overlap_rows':sum(r['frozen_eight_overlap'] for r in mr),'annual':{},'outside_annual':{},'outside_by_league':{}}
  for y in TARGET_YEARS:
   q=[r for r in mr if r['year']==y]; qi=[r for r in q if not r['frozen_eight_overlap']]
   methods[method]['annual'][str(y)]=calc(q);methods[method]['outside_annual'][str(y)]=calc(qi)
  for l in sorted({r['league'] for r in inc}):methods[method]['outside_by_league'][l]=calc([r for r in inc if r['league']==l])
 # Same-horizon frozen base + unique outside-method earnings; baseline from prior verified T12 study cohort.
 base={'n':6873,'net_U':197.765}
 for method,s in methods.items():
  q=s['outside_frozen_eight'];s['combined_with_frozen_eight_same_2024_2026']={'frozen_n':base['n'],'frozen_net_U':base['net_U'],'candidate_added_n':q['n'],'candidate_added_net_U':q['net_U'],'unique_total_n':base['n']+q['n'],'total_net_U':round(base['net_U']+q['net_U'],6),'ROI_pct':round(100*(base['net_U']+q['net_U'])/(base['n']+q['n']),6)}
 frozen_ids={str(json.loads(x)['fid']) for x in FOUNDATION.open() if x.strip()}
 overlap_ids=sorted({r['fid'] for r in hist_rows if r['year'] in TARGET_YEARS and r['fid'] in frozen_ids})
 # Appearance rows are source-quality audit only. Missing match appearance data are not interpreted as zero cards.
 appearance_game_ids=set();matched_tm_game_ids={r['tm_game_id'] for r in hist_rows}
 with gzip.open(APPEAR,'rt',encoding='utf8') as af:
  for ar in csv.DictReader(af):
   gid=str(ar.get('game_id') or '')
   if gid in matched_tm_game_ids:appearance_game_ids.add(gid)
 # receipt inventory is only a FID join; the historical referee table has no first-seen receipt timestamp.
 receipt_ids=set()
 if RECEIPTS.exists():
  with RECEIPTS.open(encoding='utf8') as f:
   for line in f:
    try:
     q=json.loads(line);fid=str(q.get('fixture_id') or q.get('fid') or q.get('match_id') or '')
     if fid:receipt_ids.add(fid)
    except Exception:pass
 summary={'study':'M8 referee assignment history vs Crown T12 AH payout; historical only','execution_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'walk-forward retrospective; referee data first-known time unverified; not a production candidate','source_files':{'games':str(GAMES),'appearances':str(APPEAR),'Crown_source_ledger':str(FIXTURES),'frozen_membership':str(FOUNDATION)},'input_sha256':{str(p):sha_file(p) for p in (GAMES,APPEAR,FIXTURES,FOUNDATION)},'coverage':{'source_Crown_T12_rows':len(rows0),'unique_Crown_FIDs':len({r['fid'] for r in rows0}),'team_crosswalk_keys':len(crown_names),'mapped_team_keys':len(team_map),'provider_team_bijective_coverage':dict(map_reason),'strict_fixture_join_and_raw_quote_validated':len(joined),'join_and_raw_counts':dict(join_reasons),'raw_response_cache_files':len(raw_cache),'raw_integrity_errors':dict(raw_errors),'unique_competitions':len({r['tm_competition'] for r in joined}),'unique_referees':len({normalize(r['referee']) for r in joined}),'by_year_joined':dict(collections.Counter(str(r['year']) for r in joined)),'test_years':{str(y):{'all_joined':sum(r['year']==y for r in joined),'outside_frozen_eight':sum(r['year']==y and not r['frozen_eight_overlap'] for r in joined),'ref_history_present':sum(r['year']==y and r['ref_n_730']>0 for r in joined)} for y in TARGET_YEARS},'frozen_overlap_test_unique_fids':len(overlap_ids),'MR1_receipt_archive_fid_intersection':len({r['fid'] for r in joined if r['fid'] in receipt_ids}),'appearance_games_with_any_player_rows':len(appearance_game_ids),'appearance_games_missing_rows':len({r['tm_game_id'] for r in hist_rows})-len(appearance_game_ids),'referee_as_received_snapshot_proven':0,'receipt_fids_with_referee_snapshot':0},'method':{'target':'home AH unit return minus away AH unit return under same Crown T12 line and prices','features':'Crown market line and normalized home implied probability; prior same-competition referee-vs-Crown margin residual and history count, 730-day lookback; target date and previous two calendar dates excluded. Incomplete player-appearance/card records were audited and excluded from model features','feature_time_lag_days':LAG_DAYS,'lookback_days':LOOKBACK_DAYS,'shrinkage_pseudocount':SHRINK_N,'train':'expanding all prior years, separate calendar-year folds 2024/2025/2026; fixed ridge alpha=100; no target-year labels or future M8 membership in features','models':list(methods),'frozen_baseline_2024_2026_T12':base},'models':methods,'training_meta':training_meta,'outside15_scope_note':'Current Transfermarkt referee/team archive maps to the 25 explicit M8 competition codes only. No 15-league event-time AH outcome cohort was produced by this experiment; new-league receipts/signals are not represented and this limitation is preserved.'}
 # Save the complete dated feature/outcome cohort so the independent verifier can rebuild each prior-referee window.
 feature_fields=('fid','league_id','league','tm_competition','tm_game_id','referee','date','kickoff_utc','year','iso_week','home','away','FT','line_home','home_odds','away_odds','source_event_utc','response_sha256','source_file','home_return','home_settlement','away_return','away_settlement','market_margin_residual','home_normalized_implied','ref_n_730','ref_resid_raw_730','ref_bias_730','ref_missing_history','frozen_eight_overlap')
 with gzip.open(OUT/'referee_market_bias_fixture_features.jsonl.gz','wt',encoding='utf8') as ff:
  for r in hist_rows:ff.write(json.dumps({k:r[k] for k in feature_fields},ensure_ascii=False,separators=(',',':'))+'\n')
 # output row ledger: every model prediction as separate record; quoted raw SHA and source-event time retained.
 with gzip.open(OUT/'referee_market_bias_predictions.jsonl.gz','wt',encoding='utf8') as f:
  for r in forecast:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
 (OUT/'referee_market_bias_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 with (OUT/'referee_market_bias_by_league.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['method','league','n','net_U','ROI_pct','MDD_U','avg_orders_per_calendar_week'])
  for m,s in methods.items():
   for l,q in s['outside_by_league'].items():w.writerow([m,l,q['n'],q['net_U'],q['ROI_pct'],q['MDD_U'],q['avg_orders_per_calendar_week']])
 with (OUT/'referee_market_bias_by_week.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['method','iso_week','n','net_U','outside_frozen_eight_n','outside_net_U'])
  for m in methods:
   rr=[x for x in forecast if x['method']==m]
   weeks=sorted({x['iso_week'] for x in rr})
   for week in weeks:
    q=[x for x in rr if x['iso_week']==week];qi=[x for x in q if not x['frozen_eight_overlap']]
    w.writerow([m,week,len(q),round(sum(x['net_u'] for x in q),6),len(qi),round(sum(x['net_u'] for x in qi),6)])
 print(json.dumps({'coverage':{k:summary['coverage'][k] for k in ('strict_fixture_join_and_raw_quote_validated','by_year_joined','frozen_overlap_test_unique_fids','MR1_receipt_archive_fid_intersection','referee_as_received_snapshot_proven')},'models':{m:{'outside':{k:x['outside_frozen_eight'].get(k) for k in ('n','net_U','ROI_pct','MDD_U','avg_orders_per_calendar_week')},'annual':{y:{k:q.get(k) for k in ('n','net_U','ROI_pct','MDD_U')} for y,q in x['outside_annual'].items()}} for m,x in methods.items()}},ensure_ascii=False))
if __name__=='__main__':main()
