import json,datetime,math,hashlib,bisect,collections
from pathlib import Path
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
SCOPE=json.loads((R/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.json').read_text())
schedule={r['fid']:r for r in map(json.loads,(R/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl').open())}
index={str(r['match_id']):r for r in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
pre=P/'research-work/m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
WIN=[(24,18),(24,12),(24,6),(20,12),(18,12),(12,6),(12,3),(12,1),(8,4),(6,1)]
ROWS=[];quality=collections.Counter();seen=set()
def dt(s):return datetime.datetime.fromisoformat(str(s).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def loop_fixtures():
 for z in map(json.loads,pre.open()):
  ko=datetime.datetime.fromisoformat(z['kickoff_utc'])
  if ko.year>=2026:continue
  yield str(z['fixture_id']),z['source_file'],str(z['league_id']),'2019-2025',z.get('raw_sha256'),True
 for fid,z in schedule.items():
  yield fid,str(P/f'data/m5-crown-authorized/crown-responses/{fid}.json'),str(z['league_id']),'2026',index.get(fid,{}).get('response_sha256'),False
for fid,path,lid,src,sha,file_wrapped in loop_fixtures():
 quality['input_'+src]+=1
 try:
  p=Path(path)
  if not p.is_file():quality['no_file']+=1;continue
  raw=p.read_bytes()
  if sha:
   if file_wrapped:
    # Historical raw SHA is indexed original raw response, on-disk later normalized JSON; proven in past audit, don't assert bytes here.
    pass
   elif hashlib.sha256(raw).hexdigest()!=sha:quality['SHA_mismatch']+=1;continue
  doc=json.loads(raw)
  a=next((a for a in doc.get('data',[]) if str(a.get('id'))==fid),None)
  if a is None or str(a.get('l_id'))!=lid:quality['match_id_mismatch']+=1;continue
  if str(a.get('status'))!='full':quality['no_ft']+=1;continue
  score=(int(a['hg']),int(a['ag']));ko=dt(a['start'])
  if src=='2026' and not ('2026-01'<=ko.strftime('%Y-%m')<='2026-11'):continue
  book=next((b for b in a['bookmakers'] if b.get('slug')=='crown'),None)
  if book is None:quality['no_crown']+=1;continue
  path=[]
  for v in book.get('asian_list') or []:
   try:
    t=dt(v[4]);line=float(v[1]);h=float(v[2]);away=float(v[3])
    if t>=ko or h<=1 or away<=1 or abs(line*4-round(line*4))>1e-7 or not all(math.isfinite(x) for x in (h,away,line)):continue
    path.append((t,line,h,away))
   except:quality['bad_quote']+=1
  path.sort();ts=[p[0] for p in path]
  if not path:quality['no_path']+=1;continue
  quality['valid_'+src]+=1
  cache={}
  for h in {q for pair in WIN for q in pair}:
   i=bisect.bisect_right(ts,ko-datetime.timedelta(hours=h))-1
   cache[h]=path[i] if i>=0 else None
  for start,end in WIN:
   a0,b=cache[start],cache[end]
   if a0 is None or b is None:quality['missing_cutoff']+=1;continue
   firstline=b[1];line_start=a0[1]
   homep,awayp=b[2],b[3];p0home,p0away=a0[2],a0[3]
   line_same=b[1]==a0[1]
   final_fav='home' if b[1]<0 else 'away' if b[1]>0 else None
   final_dog='away' if final_fav=='home' else 'home' if final_fav=='away' else None
   hU=settle_score('AH',b[1],'home',*score,homep)[1]
   aU=settle_score('AH',b[1],'away',*score,awayp)[1]
   homechange=round(homep-p0home,5);awaychange=round(awayp-p0away,5)
   # For nonzero quote delta, define directional slope without a magnitude cutoff
   priced_rise='home' if homechange>awaychange else 'away' if homechange<awaychange else None
   priced_fall='away' if priced_rise=='home' else 'home' if priced_rise=='away' else None
   favchange=homechange if final_fav=='home' else awaychange if final_fav=='away' else None
   dogchange=awaychange if final_dog=='away' else homechange if final_dog=='home' else None
   mid=[v[1] for v in path if a0[0]<v[0]<b[0]]
   everchanged=any(l!=a0[1] for l in mid)
   record={'fid':fid,'source':src,'year':ko.year,'month':ko.strftime('%Y-%m'),'date':ko.date().isoformat(),'league':lid,'window':f'{start}->{end}','start_h':start,'end_h':end,'line_same':line_same,'line_changed':not line_same,'line_reverted':line_same and everchanged,'end_zero':b[1]==0,'start_line':a0[1],'end_line':b[1],'homechange':homechange,'awaychange':awaychange,'favchange':favchange,'dogchange':dogchange,'start_home_odds':p0home,'end_home_odds':homep,'start_away_odds':p0away,'end_away_odds':awayp,'rise_side':priced_rise,'fall_side':priced_fall,'home_U':hU,'away_U':aU,'favorite_U':hU if final_fav=='home' else aU if final_fav=='away' else None,'underdog_U':aU if final_dog=='away' else hU if final_dog=='home' else None,'rise_side_U':hU if priced_rise=='home' else aU if priced_rise=='away' else None,'fall_side_U':hU if priced_fall=='home' else aU if priced_fall=='away' else None}
   ROWS.append(record)
 except Exception as e:
  quality['error_'+type(e).__name__]+=1
  if quality['error_'+type(e).__name__]<4:print('ERR',fid,repr(e),flush=True)
 if (quality['input_2019-2025']+quality['input_2026'])%5000==0:print('PROGRESS',sum(quality['input_'+src] for src in ('2019-2025','2026')),'rows',len(ROWS),flush=True)
OUT=R/'m8_early_AH_same_line_water_movement_2019to2026_20261114.jsonl'
with OUT.open('w') as f:
 for r in ROWS:f.write(json.dumps(r,ensure_ascii=False)+'\n')
print('TOTAL',len(ROWS),'issues',dict(quality),flush=True)
