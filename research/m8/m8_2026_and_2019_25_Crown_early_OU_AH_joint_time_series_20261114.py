import json,math,datetime,collections,bisect,hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
HIST=R/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
SCH=R/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl'
IND= P/'data/m5-crown-authorized/crown-response-index.jsonl'
index={str(x['match_id']):x for x in map(json.loads,IND.open())}
WINDOWS=[(24,12),(20,12),(18,12),(12,6),(8,4),(6,1),(4,1),(3,1)]
COUNTS=collections.Counter();groups=collections.defaultdict(lambda:[0,0.0]);data=collections.defaultdict(lambda:[0,0.,0.,set()])
def date(s):return datetime.datetime.fromisoformat(str(s).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def iterate():
 for x in map(json.loads,HIST.open()):
  if datetime.datetime.fromisoformat(x['kickoff_utc']).year>=2026:continue
  yield str(x['fixture_id']),str(x['league_id']),str(x['source_file']),'old',None
 for x in map(json.loads,SCH.open()):
  fid=str(x['fid']);yield fid,str(x['league_id']),str(P/f'data/m5-crown-authorized/crown-responses/{fid}.json'),'2026',index.get(fid,{}).get('response_sha256')
def upd(k,pnl,fid,when):
 v=groups[k];v[0]+=1;v[1]+=pnl
 if when=='2026':
  x=data[k];x[0]+=1;x[1]+=pnl;x[3].add(fid)
for fid,lid,file,s,sha in iterate():
 COUNTS['raw_'+s]+=1
 try:
  p=Path(file)
  if not p.is_file():COUNTS['missing_file']+=1;continue
  b=p.read_bytes()
  if s=='2026' and (not sha or hashlib.sha256(b).hexdigest()!=sha):COUNTS['bad_hash']+=1;continue
  raw=json.loads(b)
  x=next((z for z in raw.get('data',[]) if str(z.get('id'))==fid),None)
  if not x or str(x.get('l_id'))!=lid or x.get('status')!='full':COUNTS['no_valid_fixture']+=1;continue
  home,away=int(x['hg']),int(x['ag']);ko=date(x['start'])
  if s=='2026' and not('2026-01'<=ko.strftime('%Y-%m')<='2026-11'):continue
  book=next((z for z in x['bookmakers'] if z.get('slug')=='crown'),None)
  if book is None:COUNTS['no_crown']+=1;continue
  H=[];O=[]
  for field,to in [('asian_list',H),('goal_list',O)]:
   for z in book.get(field) or []:
    try:
     t=date(z[4]);line=float(z[1]);p1=float(z[2]);p2=float(z[3])
     if t>=ko or not all(math.isfinite(v) for v in (p1,p2,line)) or p1<=1 or p2<=1 or abs(line*4-round(line*4))>1e-7:continue
     to.append((t,line,p1,p2))
    except:pass
  H.sort();O.sort()
  if not O:COUNTS['no_OU_path']+=1;continue
  ot=[z[0] for z in O];ht=[z[0] for z in H]
  vintage='2019-2023' if ko.year<=2023 else '2024-2025' if ko.year<=2025 else '2026'
  for e,l in WINDOWS:
   key=f'{e}->{l}'
   t0=ko-datetime.timedelta(hours=e);t1=ko-datetime.timedelta(hours=l)
   i=bisect.bisect_right(ot,t0)-1;j=bisect.bisect_right(ot,t1)-1
   if i<0 or j<0:COUNTS['missing_OU_cutoff']+=1;continue
   a,b=O[i],O[j];d=b[1]-a[1]
   over=settle_score('OU',b[1],'over',home,away,b[2])[1]
   under=settle_score('OU',b[1],'under',home,away,b[3])[1]
   if d>0:state='OU_line_rise'
   elif d<0:state='OU_line_fall'
   else:state='OU_line_same'
   # Two reference sides for EVERY OU-line state.
   for side,val in [('over',over),('under',under)]:
    upd((key,vintage,state,side),val,fid,s)
   if state=='OU_line_same':
    do=round(b[2]-a[2],5);du=round(b[3]-a[3],5)
    if do!=du:
     high='over' if do>du else 'under'
     low='under' if high=='over' else 'over'
     upd((key,vintage,'same_OU_line_higher_rising_odds_side','high'),over if high=='over' else under,fid,s)
     upd((key,vintage,'same_OU_line_lower_rising_odds_side','low'),over if low=='over' else under,fid,s)
   # AH / OU linkage, AH same over both points
   ai=bisect.bisect_right(ht,t0)-1;aj=bisect.bisect_right(ht,t1)-1
   if ai>=0 and aj>=0 and H[ai][1]==H[aj][1] and H[aj][1]!=0:
    ah=H[aj];fav='home' if ah[1]<0 else 'away';dog='away' if fav=='home' else 'home'
    odds={'home':ah[2],'away':ah[3]}
    dogprofit=settle_score('AH',ah[1],dog,home,away,odds[dog])[1]
    favprofit=settle_score('AH',ah[1],fav,home,away,odds[fav])[1]
    for side,value in [('dog',dogprofit),('fav',favprofit)]:
     upd((key,vintage,'AH_line_same|'+state,side),value,fid,s)
 except Exception as err:
  COUNTS['error_'+type(err).__name__]+=1
  if COUNTS['error_'+type(err).__name__]<3:print('ERROR',fid,repr(err),flush=True)
 if (COUNTS['raw_old']+COUNTS['raw_2026'])%10000==0:print('PROGRESS',COUNTS['raw_old']+COUNTS['raw_2026'],flush=True)
def fmt(a):
 return {'n':a[0],'net_U':round(a[1],3),'ROI_pct':round(a[1]*100/a[0],3) if a[0] else None}
summary={'scope':'All Crown historical OU and cross AH early-window paths; no production changes; observations from historical source events, not actual Telegram orders. Opposite sides and loss groups retained.','counts':dict(COUNTS),'windows':{}}
for w in [f'{a}->{b}' for a,b in WINDOWS]:
 classes={}
 for st in ('OU_line_rise','OU_line_fall','OU_line_same','same_OU_line_higher_rising_odds_side','same_OU_line_lower_rising_odds_side','AH_line_same|OU_line_rise','AH_line_same|OU_line_fall','AH_line_same|OU_line_same'):
  sides=('over','under') if st.startswith('OU_line_') else ('high',) if st.endswith('_side') and 'higher_' in st else ('low',) if st.endswith('_side') else ('dog','fav')
  r={}
  for side in sides:
   record={v:fmt(groups[(w,v,st,side)]) for v in ('2019-2023','2024-2025','2026')}
   if all(record[v]['n']==0 for v in record):continue
   r[side]=record
  if r:classes[st]=r
 summary['windows'][w]=classes
 print('WINDOW',w,'data',json.dumps({k:v for k,v in classes.items() if k in ('OU_line_rise','OU_line_fall','same_OU_line_higher_rising_odds_side','AH_line_same|OU_line_rise')},ensure_ascii=False),flush=True)
(R/'m8_2026_and_2019_25_Crown_early_OU_AH_joint_time_series_20261114.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
