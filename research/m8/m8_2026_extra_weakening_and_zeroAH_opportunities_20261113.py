import json,collections,datetime,statistics
from pathlib import Path
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk')
R=P/'research-work'
raw=[json.loads(z) for z in (R/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl').open() if '"month": "2026-' in z]
raw=[r for r in raw if '2026-01'<=r['month']<='2026-11']
def nstat(vals):
 n=len(vals);p=sum(vals);return {'n':n,'net_U':round(p,3),'ROI_pct':round(p/n*100,3) if n else None}
def month_stats(rr,k):
 by=collections.defaultdict(list)
 for z in rr:by[z['month']].append(z[k])
 return {m:nstat(v) for m,v in sorted(by.items())}
base=[r for r in raw if r['direction']=='deepen']
extra=[r for r in raw if r['direction']=='weaken' and .75<=abs(r['AH_t1_line'])<=1]
# original selected vs add alternative, also explore 0 line no dog/fav defined using real home/away side:
idx={str(x['match_id']):x for x in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
sched=[x for x in map(json.loads,(R/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl').open())]
def ts(v):return datetime.datetime.fromisoformat(str(v).replace(' ','T')).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8))).astimezone(datetime.timezone.utc)
zerorows=[];issues=collections.Counter()
for z in sched:
 fid=z['fid'];path=P/f'data/m5-crown-authorized/crown-responses/{fid}.json'
 if not path.exists() or fid not in idx:continue
 try:
  d=json.load(open(path))
  if not d.get('data'):continue
  x=next((x for x in d['data'] if str(x.get('id'))==fid),None)
  if x is None or str(x.get('status'))!='full':continue
  hg,ag=int(x['hg']),int(x['ag'])
  book=next((b for b in x['bookmakers'] if b.get('slug')=='crown'),None)
  if not book:continue
  k=ts(x['start']);q=[]
  for a in book.get('asian_list') or []:
   try:
    t=ts(a[4]);line=float(a[1]);home=float(a[2]);away=float(a[3])
    if t>=k or home<=1 or away<=1 or abs(line*4-round(line*4))>1e-7:continue
    q.append((t,line,home,away))
   except:pass
  if not q:continue
  q.sort()
  early=[a for a in q if a[0]<=k-datetime.timedelta(hours=6)]
  late=[a for a in q if a[0]<=k-datetime.timedelta(hours=1)]
  if not early or not late:continue
  q6,q1=early[-1],late[-1]
  if q1[1]!=0:continue
  if not ('2026-01'<=k.strftime('%Y-%m')<='2026-11'):continue
  row={'fid':fid,'month':k.strftime('%Y-%m'),'date':k.strftime('%Y-%m-%d'),'line_T6':q6[1],'line_T1':q1[1],'home_price':q1[2],'away_price':q1[3],'home_U':settle_score('AH',0,'home',hg,ag,q1[2])[1],'away_U':settle_score('AH',0,'away',hg,ag,q1[3])[1],'moved_to_zero':q6[1]!=0,'T6_favored_side':('home' if q6[1]<0 else 'away' if q6[1]>0 else None)}
  zerorows.append(row)
 except Exception as e:issues[type(e).__name__]+=1
def groupzero(a):
 x={'count':len(a),'home':nstat([r['home_U'] for r in a]),'away':nstat([r['away_U'] for r in a])}
 moved=[r for r in a if r['T6_favored_side']]
 if moved:
  x['prior_favorite']=nstat([r['home_U'] if r['T6_favored_side']=='home' else r['away_U'] for r in moved])
  x['prior_underdog']=nstat([r['away_U'] if r['T6_favored_side']=='home' else r['home_U'] for r in moved])
 return x
combo=base+extra
combined={'base':nstat([r['dog_U'] for r in base]),'additive_weakening_0.75_to_1':nstat([r['dog_U'] for r in extra]),'distinct_combined':nstat([r['dog_U'] for r in combo]),'overlap_fixture_ids':len({r['fid'] for r in base}&{r['fid'] for r in extra}),'monthly':month_stats(combo,'dog_U'),'early_Jan_Jun':nstat([r['dog_U'] for r in combo if r['month']<='2026-06']),'later_Jul_Nov':nstat([r['dog_U'] for r in combo if r['month']>='2026-07']),'zero_AH_cases':{'all':groupzero(zerorows),'unchanged_0_to_0':groupzero([r for r in zerorows if not r['moved_to_zero']]),'moved_from_nonzero_to_zero':groupzero([r for r in zerorows if r['moved_to_zero']])},'issues':dict(issues)}
print('CANDIDATES',json.dumps({k:v for k,v in combined.items() if k not in ('monthly','zero_AH_cases')},ensure_ascii=False),flush=True)
print('MONTH',json.dumps(combined['monthly'],ensure_ascii=False),flush=True)
print('ZERO',json.dumps(combined['zero_AH_cases'],ensure_ascii=False),flush=True)
(R/'m8_2026_extra_weakening_and_zeroAH_opportunities_20261113.json').write_text(json.dumps(combined,ensure_ascii=False,indent=2))
(R/'m8_2026_zeroAH_asof_T1_all_20261113.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in zerorows))
