import json,hashlib,collections,datetime,math,statistics
from pathlib import Path
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk')
R=P/'research-work'
sched={x['fid']:x for x in map(json.loads,(R/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl').open())}
idx={str(x['match_id']):x for x in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
old={x['fid']:x for x in map(json.loads,(R/'m8_Crown_Tminus6_to_Tminus1_fixed_information_cutoffs_20261113.jsonl').open()) if x['year']==2026}
C=collections.Counter();records=[];sample_issue=collections.defaultdict(list)
def date_local(t):
 return datetime.datetime.fromisoformat(str(t).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def addissue(name,fid):
 C[name]+=1
 if len(sample_issue[name])<4:sample_issue[name].append(fid)
for i,(fid,z) in enumerate(sched.items(),1):
 C['schedule_2026_original49']+=1
 p=P/f'data/m5-crown-authorized/crown-responses/{fid}.json'
 if not p.is_file():
  addissue('no_M5_Crown_response_file',fid);continue
 try:
  rawbytes=p.read_bytes()
  if fid not in idx or hashlib.sha256(rawbytes).hexdigest()!=idx[fid]['response_sha256']:
   addissue('SHA256_index_mismatch_or_missing',fid);continue
  doc=json.loads(rawbytes)
  if doc.get('success')!=1 or not doc.get('data'):
   addissue('Crown_response_no_data',fid);continue
  x=next((r for r in doc['data'] if str(r.get('id'))==fid),None)
  if not x or str(x.get('l_id'))!=z['league_id']:
   addissue('provider_ID_or_league_mismatch',fid);continue
  if str(x.get('status'))!='full':
   addissue('not_full_in_Crown_response',fid);continue
  try:home,away=int(x['hg']),int(x['ag'])
  except:addissue('missing_verified_goal_score_hg_ag',fid);continue
  if home<0 or away<0:addissue('negative_goals',fid);continue
  kickoff=date_local(x['start'])
  if z['kickoff_source_local']!=x['start']:C['schedule_vs_odds_start_versions_mismatch']+=1
  bookmaker=next((b for b in x.get('bookmakers',[]) if b.get('slug')=='crown'),None)
  if not bookmaker:addissue('missing_crown_bookmaker',fid);continue
  arr=bookmaker.get('asian_list') or []
  pts=[]
  for q in arr:
   try:
    t=date_local(q[4]);line=float(q[1]);h=float(q[2]);a=float(q[3])
    if t>=kickoff or h<=1 or a<=1 or not all(math.isfinite(k) for k in (line,h,a)) or abs(line*4-round(line*4))>1e-7:continue
    pts.append((t,line,h,a))
   except:C['invalid_individual_AH_quote_events']+=1
  pts.sort(key=lambda q:q[0])
  if not pts:addissue('no_valid_Crown_pregame_AH_path',fid);continue
  t6=kickoff-datetime.timedelta(hours=6);t1=kickoff-datetime.timedelta(hours=1)
  q6=next((q for q in reversed(pts) if q[0]<=t6),None)
  q1=next((q for q in reversed(pts) if q[0]<=t1),None)
  if not q6 or not q1:
   addissue('no_AH_asof_T6_or_T1',fid);continue
  line=q1[1];base=q6[1];diff=line-base
  if line==0:
   C['final_AH_zero_role_not_defined']+=1
   continue
  fav='home' if line<0 else 'away';dog='away' if line<0 else 'home'
  cls='deepen' if diff*line>0 else 'weaken' if diff*line<0 else 'unchanged'
  odds={'home':q1[2],'away':q1[3]}
  result={'fid':fid,'year':kickoff.year,'month':kickoff.strftime('%Y-%m'),'date':kickoff.date().isoformat(),'league_id':z['league_id'],'home':x['h'],'away':x['a'],'score_goals':f'{home}-{away}','snapshot_historical_received_at':idx[fid]['captured_at_utc'],'prospective_observation':False,'source_raw_SHA256':idx[fid]['response_sha256'],'original_schedule_start':z['kickoff_source_local'],'raw_odds_start':x['start'],'kickoff_version_changed_since_schedule':z['kickoff_source_local']!=x['start'],'AH_t6_line':base,'AH_t1_line':line,'AH_t1_odds_home':q1[2],'AH_t1_odds_away':q1[3],'direction':cls,'AH_t6_source_event_utc':q6[0].isoformat(),'AH_t1_source_event_utc':q1[0].isoformat(),'AH_t6_event_age_hours':round((t6-q6[0]).total_seconds()/3600,3),'AH_t1_event_age_hours':round((t1-q1[0]).total_seconds()/3600,3),'dog_side':dog,'dog_U':settle_score('AH',line,dog,home,away,odds[dog])[1],'fav_U':settle_score('AH',line,fav,home,away,odds[fav])[1],'home_U':settle_score('AH',line,'home',home,away,odds['home'])[1],'away_U':settle_score('AH',line,'away',home,away,odds['away'])[1]}
  records.append(result);C['good_role_market_and_FT']+=1
 except Exception as e:
  addissue('exception_'+type(e).__name__,fid)
 if i%2000==0:print('PROGRESS',i,'valid',len(records),'errors',C['exception_KeyError'],flush=True)
def stats(v,key):
 vals=[x[key] for x in v];n=len(vals);p=sum(vals)
 return {'n':n,'net_U':round(p,3),'ROI_pct':round(100*p/n,3) if n else None}
ms=collections.defaultdict(list)
for r in records:ms[r['month']].append(r)
monthly={}
for mo,z in sorted(ms.items()):
 zz=[r for r in z if r['direction']=='deepen']
 monthly[mo]={'all_valid_AH_nonzero':len(z),'deepen':stats(zz,'dog_U'),'deepen_fav':stats(zz,'fav_U'),'other_direction_counts':dict(collections.Counter(r['direction'] for r in z)),'source_event_T1_age_median_h':round(statistics.median(r['AH_t1_event_age_hours'] for r in zz),2) if zz else None}
 print('MONTH',mo,monthly[mo],flush=True)
overlap=[r for r in records if r['fid'] in old]
diff=0
for r in overlap:
 o=old[r['fid']]
 if o['signal']!=r['direction'] or abs(o['dog_U']-r['dog_U'])>1e-8 or r['AH_t1_line']!=o['tminus_1_line']:
  diff+=1
print('OVERLAP',len(overlap),'DIFFERENT_SAVED_OLD',diff,flush=True)
print('QUALITY',dict(C),flush=True)
summary={'coverage':'Cached M5 2026 historical Crown response archive, original 49 league provider IDs, source event as-of Tminus6 and Tminus1, final 1h source price, FT goal counts hg/ag NOT corner hc/ac. Historical responses received Nov 2026, NOT actual old HTTP reception!','Jan_to_Nov_scope_schedule':len(sched),'valid_role_market_FT':len(records),'quality':dict(C),'issues_examples':dict(sample_issue),'months':monthly,'overlap_with_older_M8_2026':len(overlap),'overlap_results_changed':diff,'source_index_SHA256_checked':True,'old_comparable_2026_Jan_May_only':True,'no_new_rules':True}
(R/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(R/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl').write_text(''.join(json.dumps(z,ensure_ascii=False)+'\n' for z in records))
