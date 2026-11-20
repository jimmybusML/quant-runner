#!/usr/bin/env python3
"""M8 goalkeeper continuity/defensive-history AH test; historical research only."""
from __future__ import annotations
import bisect, collections, csv, datetime as dt, gzip, hashlib, json, math, pathlib
import numpy as np

OUT=pathlib.Path(__file__).resolve().parent
DATA=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_pregame_info_source_20261117')
APPS=DATA/'appearances.csv.gz'; GAMES=DATA/'games.csv.gz'; LINEUPS=DATA/'game_lineups.csv.gz'
FEATURES=pathlib.Path(__file__).resolve().parents[1]/'player_load_rotation_20261119/m8_player_load_rotation_feature_rows_20261119.jsonl.gz'
FOUNDATION=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
SCORES=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl')
SCHEDULES=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules')
BEIJING=dt.timezone(dt.timedelta(hours=8))
ALPHA=100.0
GK_KEYS=('verified_starts_365','primary_share_365','switch_rate_prev5','unique_keep_prev10',
         'primary_ga90_365','backup_minus_primary_ga90','team_ga90_365','primary_last_seen_days',
         'primary_minutes_365','starts_prev5_same_primary','ga90_recent5')

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def load_jsonl_gz(path):
 with gzip.open(path,'rt',encoding='utf8') as f:return [json.loads(s) for s in f if s.strip()]
def load_jsonl(path):
 with open(path,encoding='utf8') as f:return [json.loads(s) for s in f if s.strip()]
def dord(s):return dt.date.fromisoformat(str(s)[:10]).toordinal()

def reconstruct_keeper_matches():
 games={}; q=collections.Counter()
 with gzip.open(GAMES,'rt',encoding='utf8',newline='') as f:
  for r in csv.DictReader(f):
   try:
    gid=str(r['game_id']);day=dord(r['date']);hg=int(r['home_club_goals']);ag=int(r['away_club_goals'])
    hc=str(r['home_club_id']);ac=str(r['away_club_id'])
    if not gid or not hc or not ac or hg<0 or ag<0:continue
    games[gid]=(day,hc,ac,hg,ag)
   except Exception:q['invalid_or_unfinished_game_row']+=1
 app={}; dupapp=set()
 with gzip.open(APPS,'rt',encoding='utf8',newline='') as f:
  for r in csv.DictReader(f):
   try:
    k=(str(r['game_id']),str(r['player_id']));v=(str(r['player_club_id']),float(r['minutes_played']))
    if k in app:dupapp.add(k)
    else:app[k]=v
   except Exception:q['invalid_appearance_row']+=1
 q['appearance_duplicate_game_player_keys']=len(dupapp)
 gk=collections.defaultdict(list)
 with gzip.open(LINEUPS,'rt',encoding='utf8',newline='') as f:
  for r in csv.DictReader(f):
   if str(r.get('type'))!='starting_lineup' or str(r.get('position','')).strip().lower()!='goalkeeper':continue
   k=(str(r.get('game_id') or ''),str(r.get('club_id') or ''))
   if k[0] and k[1] and r.get('player_id'):gk[k].append(str(r['player_id']))
 q['starting_goalkeeper_team_game_keys']=len(gk)
 clubrows=collections.defaultdict(list)
 for gid,(day,hc,ac,hg,ag) in games.items():
  for club,ga in ((hc,ag),(ac,hg)):
   q['completed_team_games']+=1
   cand=sorted(set(gk.get((gid,club),[])))
   if len(cand)!=1:q['no_or_ambiguous_starting_goalkeeper']+=1;continue
   pid=cand[0];ak=(gid,pid)
   if ak in dupapp or ak not in app:q['goalkeeper_appearance_missing_or_duplicate']+=1;continue
   appclub,mins=app[ak]
   if appclub!=club:q['goalkeeper_club_identity_mismatch']+=1;continue
   if mins<85:q['goalkeeper_not_verified_85min']+=1;continue
   clubrows[club].append((day,pid,mins,float(ga),gid))
   q['verified_keeper_team_games']+=1
 for club,arr in clubrows.items():arr.sort(key=lambda z:(z[0],z[4]))
 return clubrows,dict(q)

def club_profile(records,cutoff):
 days=[r[0] for r in records]
 hi=bisect.bisect_left(days,cutoff);lo=bisect.bisect_left(days,cutoff-365)
 win=records[lo:hi]; prior=records[:hi]
 if not win:
  return {k:0. for k in GK_KEYS}|{'has_keeper_history':0.,'primary_id':None,'verified_starts_365':0,'source_records_365':0}
 counts=collections.Counter(r[1] for r in win);last={pid:max(x[0] for x in win if x[1]==pid) for pid in counts}
 primary=sorted(counts,key=lambda p:(-counts[p],-last[p],p))[0]
 n=len(win);primaryrows=[r for r in win if r[1]==primary];altrows=[r for r in win if r[1]!=primary]
 def ga90(rows):
  m=sum(r[2] for r in rows)
  return sum(r[3] for r in rows)*90/m if m>0 else 0.
 recent=prior[-5:];recent10=prior[-10:]
 switches=sum(recent[i][1]!=recent[i-1][1] for i in range(1,len(recent)))
 same=sum(r[1]==primary for r in recent)
 return {
  'verified_starts_365':float(n),'primary_share_365':counts[primary]/n,
  'switch_rate_prev5':switches/max(1,len(recent)-1) if len(recent)>1 else 0.,
  'unique_keep_prev10':float(len({r[1] for r in recent10})),
  'primary_ga90_365':ga90(primaryrows),
  'backup_minus_primary_ga90':ga90(altrows)-ga90(primaryrows) if altrows else 0.,
  'team_ga90_365':ga90(win),
  'primary_last_seen_days':float(cutoff-last[primary]),
  'primary_minutes_365':float(sum(r[2] for r in primaryrows)),
  'starts_prev5_same_primary':float(same),
  'ga90_recent5':ga90(recent),
  'has_keeper_history':1.,'primary_id':primary,'source_records_365':n,
 }

def profile_features(h,a):
 out=[]
 for k in GK_KEYS:
  out.extend((float(h[k])-float(a[k]),float(h[k])+float(a[k])))
 return out

def market_features(r):
 line=float(r['crown_T12_AH_line']);ho=float(r['crown_T12_AH_home_odds']);ao=float(r['crown_T12_AH_away_odds'])
 ph=ao/(ho+ao); over=1/ho+1/ao
 return [line,abs(line),ph,math.log(ho),math.log(ao),math.log(ao/ho),over, line*(ph-.5)]
def settle_ah(line,side,hg,ag,price):
 signed=float(line) if side=='home' else -float(line)
 diff=int(hg)-int(ag) if side=='home' else int(ag)-int(hg)
 if abs(float(line)*4-round(float(line)*4))>1e-8:raise ValueError('AH line outside quarter grid')
 legs=[signed] if abs(signed*2-round(signed*2))<=1e-8 else [math.floor(signed*2)/2,math.ceil(signed*2)/2]
 cash=[float(price)-1 if diff+x>1e-9 else -1. if diff+x< -1e-9 else 0. for x in legs]
 pnl=sum(cash)/len(cash)
 label=('full_win' if all(x>0 for x in cash) else 'half_win' if any(x>0 for x in cash) else
        'push' if all(x==0 for x in cash) else 'half_loss' if any(x==0 for x in cash) else 'full_loss')
 return label,pnl
def load_schedule_metadata():
 out={};conflict=set()
 for page in sorted(SCHEDULES.glob('*/page-*.raw.json')):
  try:matches=json.loads(page.read_bytes())['data']['matches']
  except Exception:continue
  for z in matches:
   fid=str(z.get('id') or '')
   if not fid:continue
   v={'home':str(z.get('h') or ''),'away':str(z.get('a') or ''),'home_id':str(z.get('h_id') or ''),
      'away_id':str(z.get('a_id') or ''),'league_id':str(z.get('l_id') or ''),'kickoff_local':str(z.get('start') or ''),
      'FT_home':str(z.get('hg') or ''),'FT_away':str(z.get('ag') or '')}
   if fid in out and out[fid]!=v:conflict.add(fid)
   else:out[fid]=v
 for fid in conflict:out.pop(fid,None)
 return out,len(conflict)

def fit_predict(train_x,train_y,test_x):
 mu=train_x.mean(axis=0); sd=train_x.std(axis=0); sd[sd<1e-8]=1.
 z=(train_x-mu)/sd;zt=(test_x-mu)/sd;ybar=float(train_y.mean());yc=train_y-ybar
 beta=np.linalg.solve(z.T@z+ALPHA*np.eye(z.shape[1]),z.T@yc)
 return ybar+zt@beta

def day_mdd(rows):
 days=collections.defaultdict(float)
 for r in rows:days[r['date']]+=r['net_u']
 total=peak=mdd=0.
 for d in sorted(days):total+=days[d];peak=max(peak,total);mdd=max(mdd,peak-total)
 return round(mdd,6)
def stat(rows,full_weeks=None):
 n=len(rows);u=sum(r['net_u'] for r in rows)
 if not n:return {'n':0,'net_U':0.,'ROI_pct':None,'MDD_U':0.,'weeks_span':0,'orders_per_week':0.}
 d0=min(dord(r['date']) for r in rows);d1=max(dord(r['date']) for r in rows);weeks=(d1-d0)//7+1
 pos=sum(r['net_u']>1e-10 for r in rows);neg=sum(r['net_u']< -1e-10 for r in rows)
 return {'n':n,'net_U':round(u,6),'ROI_pct':round(100*u/n,6),'MDD_U':day_mdd(rows),
         'weeks_span':weeks,'orders_per_week':round(n/(full_weeks or weeks),6),
         'positive_orders':pos,'negative_orders':neg,'push_or_zero_orders':n-pos-neg,
         'settlement_classes':dict(collections.Counter(r.get('settlement','not_recorded') for r in rows))}
def weekly(rows):
 out=collections.defaultdict(lambda:[0,0.])
 for r in rows:
  z=dt.date.fromisoformat(r['date']).isocalendar();k=f'{z.year}-W{z.week:02d}'
  out[k][0]+=1;out[k][1]+=r['net_u']
 return {k:{'n':v[0],'net_U':round(v[1],6)} for k,v in sorted(out.items())}
def write_jsonl_gz(path,rows):
 with open(path,'wb') as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
   for row in rows:gz.write((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf8'))

def main():
 for p in (APPS,GAMES,LINEUPS,FEATURES,FOUNDATION,SCORES):
  if not p.exists():raise FileNotFoundError(p)
 print('INPUTS',json.dumps({p.name:sha(p) for p in (APPS,GAMES,LINEUPS,FEATURES,FOUNDATION,SCORES)},ensure_ascii=False),flush=True)
 teams,qc=reconstruct_keeper_matches();rows=load_jsonl_gz(FEATURES);schedule,schedule_conflicts=load_schedule_metadata()
 frozen={str(r['fid']) for r in load_jsonl(FOUNDATION)}
 scores={str(r['fid']):r for r in load_jsonl(SCORES)}
 cache={};byfid={};coverage=collections.Counter()
 for r in rows:
  fid=str(r['fid']);cut=dord(r['fixture_date_cutoff_utc']);hclub=str(r['home_tm_club_id']);aclub=str(r['away_tm_club_id'])
  hk=(hclub,cut);ak=(aclub,cut)
  if hk not in cache:cache[hk]=club_profile(teams.get(hclub,[]),cut)
  if ak not in cache:cache[ak]=club_profile(teams.get(aclub,[]),cut)
  h=cache[hk];a=cache[ak]
  both=int(h['has_keeper_history']>0 and a['has_keeper_history']>0)
  coverage['both_sides_have_verified_pre_cutoff_keeper_games']+=both
  z={'fid':fid,'year':int(r['year']),'date':str(r['date']),'iso_week':dt.date.fromisoformat(str(r['date'])).isocalendar().year.__str__()+'-W'+f"{dt.date.fromisoformat(str(r['date'])).isocalendar().week:02d}",
     'league_id':str(r['league']),'home_id':str(r['home_id']),'away_id':str(r['away_id']),
     'home_tm_club_id':hclub,'away_tm_club_id':aclub,'home':schedule.get(fid,{}).get('home',''),'away':schedule.get(fid,{}).get('away',''),
     'home_provider_id':schedule.get(fid,{}).get('home_id',''),'away_provider_id':schedule.get(fid,{}).get('away_id',''),
     'kickoff_beijing':schedule.get(fid,{}).get('kickoff_local',''),
     'schedule_team_id_match':bool(schedule.get(fid) and str(schedule[fid].get('home_id'))==str(r['home_id']) and str(schedule[fid].get('away_id'))==str(r['away_id'])),
     'kickoff_cutoff_date':str(r['fixture_date_cutoff_utc']),'frozen_overlap_posthoc':fid in frozen,
     'line_home':float(r['crown_T12_AH_line']),'home_odds':float(r['crown_T12_AH_home_odds']),'away_odds':float(r['crown_T12_AH_away_odds']),
     'FT_home':int(r['FT_home']),'FT_away':int(r['FT_away']),'home_U':float(r['AH_home_U']),'away_U':float(r['AH_away_U']),
     'market_features':market_features(r),'keeper_features':profile_features(h,a),'keeper_home':h,'keeper_away':a,
     'existing_gk_minutes':[float(r['h_GK_minutes_42']),float(r['a_GK_minutes_42']),float(r['h_GK_minutes_365']),float(r['a_GK_minutes_365'])],
     'market_target_home_minus_away_U':float(r['AH_home_U'])-float(r['AH_away_U']),
     'score_source_FT_match': bool(fid in scores and int(scores[fid].get('hg',-9))==int(r['FT_home']) and int(scores[fid].get('ag',-9))==int(r['FT_away']))}
  byfid[fid]=z
  if h['has_keeper_history'] and a['has_keeper_history']:coverage['both_sides_history_record_available']+=1
  else:coverage['one_or_both_sides_history_missing']+=1
  coverage['score_source_FT_match']+=int(z['score_source_FT_match'])
 # Distinct feature sets; all forecasts are generated before applying the frozen-FID exclusion.
 feature_names={
  'market_only':('market',),
  'keeper_only':('keeper',),
  'market_plus_existing_GK_minutes':('market','minutes'),
  'market_plus_keeper_continuity':('market','keeper'),
  'market_plus_all_goalkeeper':('market','keeper','minutes'),
 }
 models={k:[] for k in feature_names};year_coverage={}
 for year in (2024,2025,2026):
  train=[r for r in rows if int(r['year'])<year];test=[r for r in rows if int(r['year'])==year]
  if not train or not test:continue
  ytr=np.asarray([byfid[str(r['fid'])]['market_target_home_minus_away_U'] for r in train],float)
  yte=np.asarray([byfid[str(r['fid'])]['market_target_home_minus_away_U'] for r in test],float)
  year_coverage[str(year)]={'train_rows':len(train),'test_rows':len(test),'train_through_year':max(int(r['year']) for r in train)}
  for model,parts in feature_names.items():
   def build(r):
    z=byfid[str(r['fid'])];vals=[]
    if 'market' in parts:vals+=z['market_features']
    if 'keeper' in parts:vals+=z['keeper_features']
    if 'minutes' in parts:
     m=z['existing_gk_minutes'];vals.extend((m[0]-m[1],m[0]+m[1],m[2]-m[3],m[2]+m[3]))
    return vals
   Xtr=np.asarray([build(r) for r in train],float);Xte=np.asarray([build(r) for r in test],float)
   pred=fit_predict(Xtr,ytr,Xte)
   for r,pred_delta,y in zip(test,pred,yte):
    z=byfid[str(r['fid'])];side='home' if float(pred_delta)>=0 else 'away'
    u=z['home_U'] if side=='home' else z['away_U'];price=z['home_odds'] if side=='home' else z['away_odds']
    settlement,settled_u=settle_ah(z['line_home'],side,z['FT_home'],z['FT_away'],price)
    if abs(settled_u-u)>1e-8:raise AssertionError(f'feature settlement mismatch {z["fid"]} {model}')
    models[model].append({**z,'model':model,'predicted_home_minus_away_U':float(pred_delta),'chosen_side':side,'net_u':float(u),'settlement':settlement,
                          'source_type':'historical Crown T12 source-event replay; retrospective, not actual pregame HTTP receipt',
                          'stake_units':1.0,'training_year_cutoff_exclusive':year})
 # Only 2024–26 candidates; keep frozen overlaps in full predictions but exclude from incremental totals.
 test_rows=[x for x in byfid.values() if 2024<=x['year']<=2026]
 dates=[dt.date.fromisoformat(x['date']) for x in test_rows]
 period_weeks=(max(dates)-min(dates)).days//7+1
 results={}
 for model,arr in models.items():
  outsiders=[x for x in arr if not x['frozen_overlap_posthoc']]
  results[model]={
   'all_scored':stat(arr),
   'incremental_outside_frozen':stat(outsiders,period_weeks),
   'incremental_by_year':{str(y):stat([x for x in outsiders if x['year']==y]) for y in (2024,2025,2026)},
   'incremental_by_league':{lid:stat([x for x in outsiders if x['league_id']==lid]) for lid in sorted({x['league_id'] for x in outsiders})},
   'weekly':weekly(outsiders),
   'mean_predicted_edge':round(float(np.mean([abs(x['predicted_home_minus_away_U']) for x in outsiders])),6) if outsiders else None,
   'oos_mse_U2':round(float(np.mean([(x['predicted_home_minus_away_U']-x['market_target_home_minus_away_U'])**2 for x in outsiders])),6) if outsiders else None,
  }
 # Frozen baseline over the same candidate time horizon (all original frozen FIDs in 2024–26 through last test date).
 frozen_rows=load_jsonl(FOUNDATION);last_date=max(dates).isoformat();fbase=[]
 for r in frozen_rows:
  day=str(r.get('date') or r.get('kickoff_beijing') or '')[:10]
  try:y=int(r['year']);date=dt.date.fromisoformat(day)
  except Exception:continue
  if y in (2024,2025,2026) and day<=last_date:
   fbase.append({'fid':str(r['fid']),'year':y,'date':day,'league_id':str(r.get('league') or ''),'net_u':float(r['pnl'])})
 frozen_stats=stat(fbase,period_weeks)
 merged={}
 for model,arr in models.items():
  outsider=[x for x in arr if not x['frozen_overlap_posthoc']]
  allp=[*fbase,*outsider]
  merged[model]={'n':len(allp),'net_U':round(sum(x['net_u'] for x in allp),6),'ROI_pct':round(100*sum(x['net_u'] for x in allp)/len(allp),6) if allp else None,
                 'MDD_U':day_mdd(allp),'avg_candidate_orders_per_week':round(len(outsider)/period_weeks,6),
                 'candidate_incremental_net_U':round(sum(x['net_u'] for x in outsider),6),'baseline_n':len(fbase),'baseline_net_U':round(sum(x['net_u'] for x in fbase),6)}
 summary={'study':'M8_GOALKEEPER_CONTINUITY_AND_DEFENSIVE_HISTORY_AH','execution_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
  'data_cutoff_note':'Transfermarkt historical data has no archived first-publication or receipt timestamp. Historical feature availability is reconstructed only from games dated strictly earlier than target cutoff date; no actual live receipt proof.',
  'frozen_membership':{'n':len(frozen),'sha256':sha(FOUNDATION),'posthoc_overlap_in_test_rows':sum(x['frozen_overlap_posthoc'] for x in test_rows)},
  'input_sha256':{p.name:sha(p) for p in (APPS,GAMES,LINEUPS,FEATURES,FOUNDATION,SCORES)},
  'keeper_reconstruction_quality':qc,'feature_coverage':dict(coverage),'year_forward_folds':year_coverage,
  'schedule_metadata':{'matched_fixture_FIDs':sum(bool(schedule.get(str(r['fid']))) for r in rows),'team_ids_match':sum(bool(schedule.get(str(r['fid'])) and str(schedule[str(r['fid'])].get('home_id'))==str(r['home_id']) and str(schedule[str(r['fid'])].get('away_id'))==str(r['away_id'])) for r in rows),'conflicting_FIDs':schedule_conflicts,'schedule_root':str(SCHEDULES)},
  'test_population':{'all_test_rows_2024_2026':len(test_rows),'test_frozen_overlap':sum(x['frozen_overlap_posthoc'] for x in test_rows),
                     'outside_frozen_unique_fids':len({x['fid'] for x in test_rows if not x['frozen_overlap_posthoc']}),
                     'first_date':min(dates).isoformat(),'last_date':last_date,'calendar_weeks':period_weeks,
                     'both_sides_have_keeper_history':sum(x['keeper_home']['has_keeper_history'] and x['keeper_away']['has_keeper_history'] for x in test_rows),
                     'real_live_receipt_player_snapshot_verified':0},
  'feature_definition':{'target_cutoff':'feature archive fixture_date_cutoff_utc = target date minus 3 days; only Transfermarkt game dates strictly before this cutoff are included',
   'verified_goalkeeper_game':'completed historical game, exactly one starting-lineup position Goalkeeper for club, matching player_club_id appearance, and goalkeeper appearance minutes >=85',
   'primary_goalkeeper':'most frequent verified starter in prior 365 days; ties broken by most recent verified appearance, then player ID',
   'features':list(GK_KEYS),'ridge_alpha':ALPHA,'training':'expanding Beijing-year; each test year uses target rows from earlier calendar years only; no target lineup, result, future M8 membership or post-target Crown quote is a feature',
   'direction':'select side with greater model-predicted home-minus-away AH payout; one-unit diagnostic on each same candidate fixture',
   'lineup_data_limit':'player lineup/appearance data has no first-publication or receipt timestamp; this is historical event-time reconstruction only'},
  'candidate_models':results,'frozen_baseline_same_period':frozen_stats,'frozen_plus_candidate':merged,
  'candidate_overlap':{'pairwise_method_fid_overlap':{a:{b:len(set(x['fid'] for x in models[a])&set(x['fid'] for x in models[b])) for b in models} for a in models},
                       'incremental_unique_fids_per_method':{m:len({x['fid'] for x in arr if not x['frozen_overlap_posthoc']}) for m,arr in models.items()},
                       'frozen_fid_overlap_incremental':0}}
 for model,arr in models.items():
  write_jsonl_gz(OUT/f'goalkeeper_ah_{model}_ledger_20261121.jsonl.gz',sorted(arr,key=lambda q:(q['date'],q['fid'])))
 # Unified ledgers preserve each method and all scored rows (including frozen overlaps).
 write_jsonl_gz(OUT/'goalkeeper_ah_all_methods_per_fixture_20261121.jsonl.gz',
                [x for model in models for x in sorted(models[model],key=lambda q:(q['date'],q['fid']))])
 (OUT/'goalkeeper_ah_summary_20261121.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'population':summary['test_population'],'coverage':summary['feature_coverage'],'models':{k:v['incremental_outside_frozen'] for k,v in results.items()},'merged':merged},ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
