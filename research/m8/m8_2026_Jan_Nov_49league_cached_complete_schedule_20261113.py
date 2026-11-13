import json,glob,collections,sqlite3,os,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk')
scope={str(z['league_id']) for z in map(json.loads,(P/'research-work/m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl').open())}
cand={};rawrows=0;parseerrors=0
for lid in sorted(scope):
 for filename in sorted(glob.glob(str(P/f'data/m5-crown-authorized/schedules/{lid}/page-*.raw.json'))):
  try:
   x=json.load(open(filename))
   for match in (x.get('data',{}).get('matches') or []):
    if str(match.get('l_id'))!=lid:continue
    when=str(match.get('start',''))
    if not when.startswith('2026-') or when[:7]>'2026-11':continue
    fid=str(match.get('id'))
    if not fid:continue
    rawrows+=1
    if fid not in cand:cand[fid]={'fid':fid,'league_id':lid,'month':when[:7],'kickoff_source_local':when,'status':match.get('status'),'home_goals':match.get('hc'),'away_goals':match.get('ac'),'source_file':filename}
  except Exception:parseerrors+=1
by=collections.defaultdict(list)
for f,r in cand.items():by[r['month']].append(r)
db=sqlite3.connect('file:'+str(P/'data/crown_quote_store/crown_quotes.sqlite3')+'?mode=ro',uri=True)
recorded={str(r[0]):r[1] for r in db.execute("SELECT fixture_id,status FROM capture WHERE capture_mode='historical' AND data_layer='movement' ORDER BY processed_at_utc")}
rpt={'scope_leagues':len(scope),'unique_2026_jan_to_nov_schedule':len(cand),'duplicate_page_rows':rawrows-len(cand),'parse_errors':parseerrors,'months':{}}
for month,items in sorted(by.items()):
 has=[z for z in items if z['fid'] in recorded]
 ft=[z for z in items if z['status']=='full' and z['home_goals'] is not None and z['away_goals'] is not None]
 rpt['months'][month]={'schedule_count':len(items),'status_full_with_scores':len(ft),'historical_movement_captured':len(has),'quote_saved':sum(recorded[z['fid']]=='QUOTES_SAVED' for z in has),'not_captured':len(items)-len(has)}
 print(month,rpt['months'][month],flush=True)
print('TOTAL',len(cand),'rawrows',rawrows,'errors',parseerrors,flush=True)
out=P/'research-work/m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.json'
out.write_text(json.dumps(rpt,ensure_ascii=False,indent=2))
(P/'research-work/m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl').write_text(''.join(json.dumps(z,ensure_ascii=False)+'\n' for z in cand.values()))
