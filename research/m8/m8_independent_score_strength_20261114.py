import json,math,datetime,collections,hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
old=R/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
sch=R/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl'
idx={str(r['match_id']):r for r in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
def inputs():
 for r in map(json.loads,old.open()):
  if datetime.datetime.fromisoformat(r['kickoff_utc']).year<2026:yield str(r['fixture_id']),Path(r['source_file']),None,'old'
 for r in map(json.loads,sch.open()):
  f=str(r['fid']);yield f,P/f'data/m5-crown-authorized/crown-responses/{f}.json',idx.get(f,{}).get('response_sha256'),'2026'
def dt(s):return datetime.datetime.fromisoformat(str(s).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
scores={};issues=collections.Counter()
for f,p,sha,src in inputs():
 try:
  if not p.exists():issues['missing_raw']+=1;continue
  raw=p.read_bytes()
  if src=='2026' and (not sha or hashlib.sha256(raw).hexdigest()!=sha):issues['sha_missing_or_mismatch']+=1;continue
  x=next(z for z in json.loads(raw)['data'] if str(z['id'])==f)
  if x.get('status')!='full':issues['not_full']+=1;continue
  ko=dt(x['start'])
  if (src=='old' and ko.year>=2026) or (src=='2026' and ko.year!=2026):issues['outside_year']+=1;continue
  h,a=int(x['hg']),int(x['ag'])
  if h<0 or a<0 or not x.get('h_id') or not x.get('a_id'):issues['missing_score_or_team']+=1;continue
  rec={'fid':f,'year':ko.year,'month':ko.strftime('%Y-%m'),'date':ko.date().isoformat(),'ko':ko.isoformat(),'league':str(x['l_id']),'home':str(x['h_id']),'away':str(x['a_id']),'hg':h,'ag':a}
  if f in scores and scores[f]!=rec:raise ValueError('conflicting score fixture '+f)
  scores[f]=rec
 except Exception as e:
  issues['error_'+type(e).__name__]+=1
  if issues['error_'+type(e).__name__]<3:print('ERROR',f,repr(e))
rows=sorted(scores.values(),key=lambda r:(r['ko'],r['fid']))
# online score-only ratings: league-specific baseline and opponent-adjusted attacking / defensive strengths.
# Each new match prediction uses only past matches at least two UTC calendar days earlier.
# Numerical learning rates are experimental parameters, not trading rules. Compare two speeds, no selection on results.
models={}
for lr in (.025,.06):
 attack=collections.defaultdict(float);defense=collections.defaultdict(float)
 baseline=collections.defaultdict(lambda:[math.log(1.45),math.log(1.15)])
 counts=collections.Counter();q=0
 def predict(r):
  h=(r['league'],r['home']);a=(r['league'],r['away']);b=baseline[r['league']]
  x=np.clip(b[0]+attack[h]+defense[a],-2.5,2.3);y=np.clip(b[1]+attack[a]+defense[h],-2.5,2.3)
  return float(np.exp(x)),float(np.exp(y))
 def update(r):
  h=(r['league'],r['home']);a=(r['league'],r['away']);b=baseline[r['league']]
  x,y=predict(r);e1=r['hg']-x;e2=r['ag']-y
  # decay parameter is numerical stabilization. No current result used before this prediction.
  for k,e in [(h,e1),(a,e2)]:attack[k]=.997*attack[k]+lr*float(np.clip(e,-4,4))
  for k,e in [(a,e1),(h,e2)]:defense[k]=.997*defense[k]+lr*float(np.clip(e,-4,4))
  b[0]+=.003*float(np.clip(e1,-4,4));b[1]+=.003*float(np.clip(e2,-4,4))
  counts[h]+=1;counts[a]+=1
 for r in rows:
  current=datetime.date.fromisoformat(r['date'])
  while q<len(rows) and (current-datetime.date.fromisoformat(rows[q]['date'])).days>=2:
   update(rows[q]);q+=1
  h,a=predict(r);tag=str(lr)
  r['lambda_home_'+tag]=h;r['lambda_away_'+tag]=a
  r['history_home_n']=counts[(r['league'],r['home'])];r['history_away_n']=counts[(r['league'],r['away'])]
print('SCORE_UNIVERSE',len(rows),dict(collections.Counter(r['year'] for r in rows)),dict(issues),flush=True)
(R/'m8_independent_score_strength_20261114.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
(R/'m8_independent_score_strength_coverage_20261114.json').write_text(json.dumps({'n':len(rows),'years':dict(collections.Counter(r['year'] for r in rows)),'issues':dict(issues)},indent=2))
