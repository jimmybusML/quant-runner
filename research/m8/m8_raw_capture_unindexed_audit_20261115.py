import json,sqlite3,hashlib,collections,datetime,math
from pathlib import Path
from zoneinfo import ZoneInfo
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
known={r['fid'] for f in ('m8_late_full_path_water_features_20261114.jsonl','m8_extra_inventory_frozen_eight_20261115.jsonl') for r in map(json.loads,(R/f).open())}
scope={r['league'] for r in map(json.loads,(R/'m8_late_full_path_water_features_20261114.jsonl').open())}
schedule={str(r['match_id']):r for r in map(json.loads,(R/'crown-drop-expanded-62/schedule_universe.jsonl').open()) if str(r['league_id']) in scope}
assert len(known)==44943 and len(scope)==49
cx=sqlite3.connect(f'file:{P}/data/crown_quote_store/crown_quotes.sqlite3?mode=ro',uri=True)
caps=collections.defaultdict(list)
for fid,layer,src,sha,rec,proc,status in cx.execute("select fixture_id,data_layer,source_file,response_sha256,response_received_at_utc,processed_at_utc,status from capture where capture_mode='historical' and data_layer in ('movement','summary') order by processed_at_utc desc,capture_key desc"):
 if fid in schedule and fid not in known:caps[fid].append((layer,src,sha,rec,proc,status))
cx.close()
print('candidates',len(caps),'captures',sum(map(len,caps.values())),flush=True)
def dt(s):return datetime.datetime.fromisoformat(str(s).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
C=collections.Counter();sources={};details=[]
for fid,c in caps.items():
 reasons=collections.Counter()
 for layer,src,sha,rec,proc,status in c:
  try:
   raw=Path(src).read_bytes()
   if hashlib.sha256(raw).hexdigest()!=sha:reasons['bad_sha']+=1;continue
   x=next((q for q in json.loads(raw).get('data',[]) if str(q.get('id'))==fid),None)
   sch=schedule[fid]
   if not x or str(x.get('l_id'))!=str(sch['league_id']) or x.get('status')!='full':reasons['identity_or_not_full']+=1;continue
   ko=dt(x['start'])
   if not 2019<=ko.year<=2026:reasons['outside_prior_years']+=1;continue
   # Scores and times from raw, as in previous M8; record schedule discrepancies, no outcome selection.
   hg,ag=int(x['hg']),int(x['ag'])
   b=next((q for q in x.get('bookmakers',[]) if q.get('slug')=='crown'),None)
   if not b:reasons['no_crown']+=1;continue
   path=[]
   for q in b.get('asian_list') or []:
    try:
     t=dt(q[4]);l,h,a=map(float,q[1:4])
     if t<ko and h>1 and a>1 and all(math.isfinite(v) for v in (l,h,a)) and abs(l*4-round(l*4))<1e-7:path.append(t)
    except:continue
   if not path:reasons['no_valid_pregame_list']+=1;continue
   if min(path)>ko-datetime.timedelta(hours=6):reasons['first_quote_after_T6']+=1;continue
   sources[fid]=[fid,str(x['l_id']),src,sha,'extra']
   reasons['valid']+=1
   C['schedule_kickoff_difference_in_recovered']+=dt(sch['kickoff_source_local'])!=ko
   break
  except Exception as e:reasons['error_'+type(e).__name__]+=1
 C['examined']+=1
 if fid in sources:C['recovered']+=1
 else:
  # mutually exclusive reason, in order reflecting furthest verified coverage
  reason=next((k for k in ('first_quote_after_T6','no_valid_pregame_list','no_crown','outside_prior_years','identity_or_not_full','bad_sha') if reasons[k]),'other')
  C[reason]+=1
 if C['examined']%10000==0:print(dict(C),flush=True)
 details.append({'fid':fid,'reasons':dict(reasons),'recovered':fid in sources})
out={'schedule_unique':len(schedule),'schedule_not_in_M8_T6T1':len(set(schedule)-known),'candidate_fixtures_with_capture':len(caps),'candidate_captures':sum(map(len,caps.values())),'counts':dict(C)}
(R/'m8_raw_capture_unindexed_audit_20261115.json').write_text(json.dumps(out,indent=2))
(R/'m8_raw_capture_unindexed_sources_20261115.json').write_text(json.dumps(sources))
(R/'m8_raw_capture_unindexed_audit_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in details))
print('DONE',out,flush=True)
