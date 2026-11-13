import json,math,datetime,collections,bisect,statistics
from pathlib import Path
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=P/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
wins=[(24,12),(20,12),(18,12),(12,6),(8,4),(6,1),(4,1),(3,1),(2,1)]
C=collections.Counter();groups=collections.defaultdict(list)
def todt(s):return datetime.datetime.fromisoformat(str(s).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
for idx,line in enumerate(src.open(),1):
 r=json.loads(line);fid=str(r['fixture_id'])
 try:
  x=json.load(open(r['source_file']))['data'][0]
  if str(x.get('id'))!=fid or str(x.get('l_id'))!=str(r['league_id']):C['id_mismatch']+=1;continue
  if x['status']!='full':C['not_full']+=1;continue
  hg,ag=int(x['hg']),int(x['ag'])
  ko=todt(x['start'])
  book=next((b for b in x['bookmakers'] if b['slug']=='crown'),None)
  if not book:C['missing_crown']+=1;continue
  path=[]
  for q in book.get('asian_list') or []:
   try:
    t=todt(q[4]);p=float(q[1]);h=float(q[2]);a=float(q[3])
    if t<ko and math.isfinite(p) and math.isfinite(h) and math.isfinite(a) and h>1 and a>1 and abs(p*4-round(p*4))<1e-6:path.append((t,p,h,a))
   except:pass
  path.sort();ts=[a[0] for a in path]
  if not path:C['no_AH_path']+=1;continue
  C['market_ok']+=1
  for early,late in wins:
   k=f'{early}->{late}';t1=ko-datetime.timedelta(hours=early);t2=ko-datetime.timedelta(hours=late)
   i=bisect.bisect_right(ts,t1)-1;j=bisect.bisect_right(ts,t2)-1
   if i<0 or j<0:C['missing_'+k]+=1;continue
   a,b=path[i],path[j]
   if b[1]==0:C['zero_'+k]+=1;continue
   sh=b[1]-a[1]
   mode='deepen' if sh*b[1]>0 else 'weaken' if sh*b[1]<0 else 'unchanged'
   fav='home' if b[1]<0 else 'away';dog='away' if fav=='home' else 'home'
   odds={'home':b[2],'away':b[3]}
   groups[k].append({'fid':fid,'year':ko.year,'market_state':mode,'dog_U':settle_score('AH',b[1],dog,hg,ag,odds[dog])[1],'fav_U':settle_score('AH',b[1],fav,hg,ag,odds[fav])[1]})
 except Exception as e:
  C['exception_'+type(e).__name__]+=1
  if C['exception_'+type(e).__name__]<3:print('ERROR',fid,repr(e),flush=True)
 if idx%5000==0:print('PROGRESS',idx,'ok',C['market_ok'],flush=True)
def calc(items,key='dog_U'):
 n=len(items);s=sum(v[key] for v in items);return {'n':n,'net_U':round(s,3),'ROI_pct':round(s*100/n,3) if n else None}
out={'source':'older 34714 fixtures original49 Crown historical archive (retrieved in 2026), not independent from M5 2026: show pre-2026 separately','n_input':idx,'count':dict(C),'windows':{}}
for e,l in wins:
 k=f'{e}->{l}';arr=groups[k];m={}
 for mode in ('deepen','weaken','unchanged'):
  x=[z for z in arr if z['market_state']==mode]
  m[mode]={'all_dog':calc(x),'all_fav':calc(x,'fav_U'),'pre2026_dog':calc([z for z in x if z['year']<2026]),'pre2026_fav':calc([z for z in x if z['year']<2026],'fav_U'),'2019_2023_dog':calc([z for z in x if z['year']<=2023]),'2024_2025_dog':calc([z for z in x if 2024<=z['year']<=2025]),'2026_partial_dog':calc([z for z in x if z['year']==2026]),'years':{str(y):calc([z for z in x if z['year']==y]) for y in sorted({z['year'] for z in x})}}
 out['windows'][k]={'eligible':len(arr),'states':m}
 print('OLD',k,'eligible',len(arr),'deepen_pre2026',m['deepen']['pre2026_dog'],'deepen_2019-23',m['deepen']['2019_2023_dog'],'deepen_2024-25',m['deepen']['2024_2025_dog'],'deepen_2026partial',m['deepen']['2026_partial_dog'],flush=True)
P.joinpath('m8_2019_2026_Crown_early_window_crossyear_20261114.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
