#!/usr/bin/env python3
"""Research only: original49 Crown history; candidate comparisons, not rules."""
import json, math, hashlib, collections, datetime, statistics
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from research.m3.probabilities import settle_score

BASE=Path('/Users/mac/QuantAsiaDesk')
R=BASE/'research-work'
SRC=BASE/'data/m5-crown-authorized/crown-responses'
SCOPE=R/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl'
INDEX=BASE/'data/m5-crown-authorized/crown-response-index.jsonl'
# Independent exploratory time pairs; each is (earlier cutoff hours, later cutoff hours).
WINDOWS=[
 (24,18),(24,12),(24,6),(24,1),(20,12),(20,6),(20,1),
 (18,12),(18,6),(16,10),(16,6),(12,8),(12,6),(12,3),(12,1),
 (10,6),(8,4),(8,2),(8,1),(6,4),(6,3),(6,2),(6,1),
 (4,2),(4,1),(3,2),(3,1),(2,1),
]
CHECKPOINTS=sorted(set(h for a,b in WINDOWS for h in (a,b)),reverse=True)
O=collections.Counter()
I={str(x['match_id']):x for x in map(json.loads,INDEX.open())}
S={str(x['fid']):x for x in map(json.loads,SCOPE.open())}
BYWIN=collections.defaultdict(list)
BYFIXTURE=collections.defaultdict(dict)
def localtime(raw):
 return datetime.datetime.fromisoformat(str(raw).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def dtlabel(d):
 return d.astimezone(datetime.timezone.utc).date().isoformat()
for i,(fid,sch) in enumerate(S.items()):
 O['schedule_fixtures']+=1
 file=SRC/(fid+'.json')
 if not file.exists() or fid not in I:O['missing_raw_or_index']+=1; continue
 try:
  databytes=file.read_bytes()
  if hashlib.sha256(databytes).hexdigest()!=I[fid]['response_sha256']:
   O['raw_sha_mismatch']+=1;continue
  raw=json.loads(databytes)
  if raw.get('success')!=1:O['not_success']+=1;continue
  allm=raw.get('data') or []
  match=next((x for x in allm if str(x.get('id'))==fid),None)
  if not match or str(match.get('l_id'))!=str(sch['league_id']):
   O['match_or_league_mismatch']+=1;continue
  if str(match.get('status'))!='full':O['not_full']+=1;continue
  hg,ag=int(match['hg']),int(match['ag'])
  kickoff=localtime(match['start'])
  # As in prior Jan-Nov study: use kickoff UTC calendar year, not stored local date
  if not('2026-01'<=kickoff.strftime('%Y-%m')<='2026-11'):
   O['utc_outside_calendar']+=1;continue
  book=next((b for b in match.get('bookmakers',[]) if b.get('slug')=='crown'),None)
  if book is None:O['no_crown']+=1;continue
  items=[]
  for q in book.get('asian_list') or []:
   try:
    if len(q)<5:continue
    t=localtime(q[4]);line=float(q[1]);home=float(q[2]);away=float(q[3])
    if not(t<kickoff and math.isfinite(line) and math.isfinite(home) and math.isfinite(away) and home>1 and away>1 and abs(line*4-round(line*4))<1e-7):
     continue
    items.append((t,line,home,away))
   except Exception:
    O['invalid_quote_rows']+=1
  if not items:O['no_AH_path']+=1;continue
  items.sort(key=lambda x:x[0])
  bycut={}
  for h in CHECKPOINTS:
   t=kickoff-datetime.timedelta(hours=h)
   eligible=[z for z in items if z[0]<=t]
   bycut[h]=eligible[-1] if eligible else None
  O['full_with_valid_AH_path']+=1
  matched=[]
  for start,end in WINDOWS:
   a,b=bycut[start],bycut[end]
   key=f'T-{start}h→T-{end}h'
   if a is None or b is None:
    O['window_quote_absence_'+key]+=1;continue
   if b[1]==0:
    O['window_final_zero_'+key]+=1;continue
   finalfav='home' if b[1]<0 else 'away'
   dog='away' if finalfav=='home' else 'home'
   shift=b[1]-a[1]
   state='deepen' if shift*b[1]>0 else 'weaken' if shift*b[1]<0 else 'unchanged'
   w={'fid':fid,'league_id':sch['league_id'],'month':kickoff.strftime('%Y-%m'),'date':dtlabel(kickoff),'kickoff_utc':kickoff.isoformat(),'start_h':start,'end_h':end,'window':key,'state':state,'start_line':a[1],'end_line':b[1],'move_abs':abs(shift),'start_event_utc':a[0].isoformat(),'end_event_utc':b[0].isoformat(),'end_event_staleness_hours':round((kickoff-datetime.timedelta(hours=end)-b[0]).total_seconds()/3600,3),'end_dog_side':dog,'end_dog_decimal':b[2] if dog=='home' else b[3],'end_fav_decimal':b[2] if finalfav=='home' else b[3],'dog_U':settle_score('AH',b[1],dog,hg,ag,b[2] if dog=='home' else b[3])[1],'fav_U':settle_score('AH',b[1],finalfav,hg,ag,b[2] if finalfav=='home' else b[3])[1]}
   BYWIN[key].append(w)
   if state=='deepen':
    matched.append(w)
  if matched:BYFIXTURE[fid]={'fid':fid,'signals':matched}
 except Exception as e:
  O['exception_'+type(e).__name__]+=1
  if O['exception_'+type(e).__name__]<3:print('ERROR',fid,repr(e),flush=True)
 if i and i%1500==0:print('PROGRESS',i,'valid',O['full_with_valid_AH_path'],flush=True)
def stats(items,field='dog_U'):
 n=len(items);v=sum(a[field] for a in items)
 return {'n':n,'net_U':round(v,3),'ROI_pct':round(v/n*100,3) if n else None}
def periodic(v):
 a=[x for x in v if x['month']<='2026-06']
 b=[x for x in v if x['month']>='2026-07']
 m=collections.defaultdict(list)
 for x in v:m[x['month']].append(x)
 return {'Jan-Jun':stats(a),'Jul-Nov':stats(b),'monthly':{k:stats(z) for k,z in sorted(m.items())}}
def weekly(v):
 by=collections.Counter()
 for r in v:
  dt=datetime.date.fromisoformat(r['date']);iso=dt.isocalendar();by[f'{iso.year}-W{iso.week:02}']+=1
 return {'weeks_present':len(by),'max_per_week':max(by.values()) if by else None,'median_per_week':statistics.median(by.values()) if by else None,'month_avg_per_week':round(len(v)/((datetime.date(2026,11,14)-datetime.date(2026,1,1)).days/7),3),'weeks':dict(sorted(by.items()))}
def dayCI(v):
 if not v:return None
 day=collections.defaultdict(float)
 for r in v:day[r['date']]+=r['dog_U']
 vals=np.array(list(day.values()));n=len(v)
 rng=np.random.default_rng(260010)
 res=np.array([vals[rng.integers(len(vals),size=len(vals))].sum()*100/n for _ in range(2400)])
 return [round(float(s),3) for s in np.percentile(res,[2.5,97.5])]
summary={'built_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event_type':'historical Crown bookmaker asian_list source events; retrieved later; research simulation not real received orders','window_definitions':WINDOWS,'count':dict(O),'windows':{},'unions':{}}
for a,b in WINDOWS:
 key=f'T-{a}h→T-{b}h';x=BYWIN[key]
 sig=[r for r in x if r['state']=='deepen']
 other=collections.Counter(r['state'] for r in x)
 known={r['fid'] for r in sig}
 earlier=[r for r in sig if key!='T-6h→T-1h']
 summary['windows'][key]={'valid_nonzero_AH':len(x),'classification':dict(other),'deepen_dog':stats(sig),'deepen_fav':stats(sig,'fav_U'),'deepen_periods':periodic(sig),'deepen_weekly':weekly(sig),'deepen_day_bootstrap95_roi':dayCI(sig)}
 print('WIN',key,'eligible',len(x),'deepen',stats(sig),'first',stats([r for r in sig if r['month']<='2026-06']),'later',stats([r for r in sig if r['month']>='2026-07']),'CI',summary['windows'][key]['deepen_day_bootstrap95_roi'],flush=True)
baseline={r['fid']:r for r in BYWIN['T-6h→T-1h'] if r['state']=='deepen'}
assert len(baseline)==1182,(len(baseline),O)
assert abs(sum(r['dog_U'] for r in baseline.values())-38.955)<1e-5
# Earlier signal windows ending at least 6h before kickoff.
earlier_keys=[f'T-{a}h→T-{b}h' for a,b in WINDOWS if b>=6]
# one signal per match, choose the earliest end-time at which eligible from pre-defined windows,
# then earliest start within that end to avoid any postresult optimization.
early_set=collections.defaultdict(list)
for key in earlier_keys:
 for r in BYWIN[key]:
  if r['state']=='deepen':early_set[r['fid']].append(r)
def earliest(v):return sorted(v,key=lambda r:(-r['end_h'],-r['start_h'],r['window']))[0]
selected={fid:earliest(v) for fid,v in early_set.items()}
extra={fid:r for fid,r in selected.items() if fid not in baseline}
union={**baseline,**extra}
summary['unions']={'early_candidates_any_window_end_at_or_before_T6':stats(list(selected.values())),'earliest_window_selection_definition':'sort by end_h descending (earliest event timing); start_h descending to break ties, no outcome selection; research capacity illustration only','early_extra_vs_T6_to_T1':stats(list(extra.values())),'early_overlap_with_base':len(set(selected)&set(baseline)),'baseline_6_to_1':stats(list(baseline.values())),'combined_unique':stats(list(union.values())),'extra_periods':periodic(list(extra.values())),'extra_weekly':weekly(list(extra.values())),'combined_weekly':weekly(list(union.values())),'combined_periods':periodic(list(union.values())),'extra_day_CI':dayCI(list(extra.values()))}
print('UNIONS',json.dumps({k:v for k,v in summary['unions'].items() if k!='extra_weekly' and k!='combined_weekly' and k!='combined_periods' and k!='extra_periods'},ensure_ascii=False),flush=True)
(R/'m8_2026_Crown_early_AH_24h_to_1h_window_study_20261114_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
# preserve every comparison, losing/unchanged states included
with (R/'m8_2026_Crown_early_AH_24h_to_1h_window_study_20261114.jsonl').open('w') as f:
 for w in BYWIN.values():
  for r in w:f.write(json.dumps(r,ensure_ascii=False)+'\n')
(R/'m8_2026_Crown_early_AH_24h_to_1h_union_20261114.jsonl').write_text(''.join(json.dumps({'kind':'early_additive' if fid in extra else 'original_baseline',**r},ensure_ascii=False)+'\n' for fid,r in union.items()))
