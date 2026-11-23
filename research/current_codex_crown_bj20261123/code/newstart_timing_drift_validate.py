#!/usr/bin/env python3
"""Independent newstart audit only active Codex source+current derived ledger.
Cross-check quote-source event vs actual kickoff and receipt for all derived
open/close baseline records. Explore bookmaker line/price revision direction,
reported descriptively, not a trading rule, using exact same paired fixtures.
"""
from pathlib import Path
from collections import defaultdict,Counter
import sqlite3,json,datetime,math
P=Path('/Users/mac/QuantAsiaDesk/research-work/newstart_20261123_codex_only')
DB='/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3'
B=json.loads((P/'newstart_crown_market_baseline_summary.json').read_text())
quote=[json.loads(s) for s in (P/'newstart_fixture_quote_baseline.jsonl').open()]
schedule={str(r['match_id']):r for r in map(json.loads,open('/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl'))}
cn=sqlite3.connect('file:'+DB+'?mode=ro',uri=True,timeout=30)
cn.execute('PRAGMA query_only=ON')
kick=defaultdict(set)
for fid,utc in cn.execute('SELECT fixture_id,kickoff_at_utc FROM capture WHERE rowid<=? AND kickoff_at_utc IS NOT NULL',(B['rowid_fences']['capture'],)):
 kick[str(fid)].add(utc)
for fid,utc in cn.execute('SELECT fixture_id,kickoff_at_utc FROM crown_ou_source WHERE rowid<=? AND kickoff_at_utc IS NOT NULL',(B['rowid_fences']['crown_ou_source'],)):
 kick[str(fid)].add(utc)
def parse(x):
 try:return datetime.datetime.fromisoformat(str(x).replace('Z','+00:00'))
 except Exception:return None
def legs(line):
 q=round(4*line)
 return [(line,1.)] if q%2==0 else [(math.floor(2*line)/2.,.5),(math.ceil(2*line)/2.,.5)]
def cash(x,side):
 h,a=x['home_goals'],x['away_goals']
 l=x['line'];o=x['decimal_1'] if side==0 else x['decimal_2']
 result=0
 for part,w in legs(l):
  if x['market']=='AH':
   difference=h-a+part if side==0 else a-h-part
  else:
   difference=h+a-part if side==0 else part-h-a
  result+=w*((o-1) if difference>1e-10 else -1. if difference< -1e-10 else 0.)
 return result
qa=Counter()
for row in quote:
 if row['fixture_id'] not in schedule:qa['outside_schedule']+=1
 if abs(row['side1_U']-cash(row,0))>1e-10 or abs(row['side2_U']-cash(row,1))>1e-10:
  qa['independent_cash_mismatch']+=1
 qa['settlement_sides_audited']+=2
 times=kick.get(row['fixture_id'],set())
 qa['quote_records_total']+=1
 if not times:qa['no_kickoff_utc_record']+=1;continue
 if len(times)>1:qa['conflicting_kickoff_utc']+=1
 when=parse(row['source_event_at_utc']);recv=parse(row['received_at_utc'])
 epochs=[parse(x) for x in times]
 if when is None:qa['bad_source_utc']+=1;continue
 if all(when<k for k in epochs):qa['source_event_before_every_recorded_kickoff']+=1
 elif any(when>=k for k in epochs):qa['source_event_at_or_after_kickoff']+=1
 if recv is None:qa['bad_received_utc']+=1;continue
 if all(recv<k for k in epochs):qa['actual_response_before_every_kickoff']+=1
 elif all(recv>=k for k in epochs):qa['actual_response_after_every_kickoff']+=1
 else:qa['response_straddles_conflicting_kickoffs']+=1
idx={(x['fixture_id'],x['market'],x['kind']):x for x in quote}
agg=defaultdict(lambda:Counter())
mov=[]
for market in ('AH','OU'):
 for fid in {r['fixture_id'] for r in quote if r['market']==market}:
  start=idx.get((fid,market,'open'));end=idx.get((fid,market,'close'))
  if not start or not end:continue
  delta=end['line']-start['line']
  if delta>1e-9:
   direction='line_up'
   favored=1 if market=='AH' else 0
  elif delta<-1e-9:
   direction='line_down'
   favored=0 if market=='AH' else 1
  else:
   o0=1/start['decimal_1'];o1=1/end['decimal_1']
   p0=1/start['decimal_2'];p1=1/end['decimal_2']
   # Odds shorten / implied probability rises on side1 => interest toward side1.
   # If conflicting movements, retain "other" group, no forced label.
   if o1>o0+1e-9 and p1<p0-1e-9:
    direction='same_line_side1_shortens';favored=0
   elif o1<o0-1e-9 and p1>p0+1e-9:
    direction='same_line_side2_shortens';favored=1
   elif abs(o1-o0)<1e-9 and abs(p1-p0)<1e-9:
    direction='unchanged_quote';favored=None
   else:direction='same_line_mixed_odds';favored=None
  t=agg[(market,end['year'],direction)]
  t['n']+=1
  t['home_or_over_U']+=end['side1_U']
  t['away_or_under_U']+=end['side2_U']
  if favored is not None:
   t['market_movement_favored_U']+=(end['side1_U'] if favored==0 else end['side2_U'])
   t['market_movement_opposed_U']+=(end['side2_U'] if favored==0 else end['side1_U'])
  mov.append({'fid':fid,'market':market,'year':end['year'],
   'movement_category':direction,'open_line':start['line'],'close_line':end['line'],
   'open_odd1':start['decimal_1'],'close_odd1':end['decimal_1'],
   'open_odd2':start['decimal_2'],'close_odd2':end['decimal_2'],
   'movement_side_index':favored,'movement_side_close_U':None if favored is None else end['side1_U'] if favored==0 else end['side2_U'],
   'opposite_side_close_U':None if favored is None else end['side2_U'] if favored==0 else end['side1_U'],
   'open_recv_utc':start['received_at_utc'],'close_recv_utc':end['received_at_utc'],
   'open_event_utc':start['source_event_at_utc'],'close_event_utc':end['source_event_at_utc']})
summ={}
for (m,y,cat),t in sorted(agg.items()):
 n=t['n'];s={'n':n,'category':cat,
   'home_or_over_close_ROI_pct':round(100*t['home_or_over_U']/n,5),
   'away_or_under_close_ROI_pct':round(100*t['away_or_under_U']/n,5)}
 if 'market_movement_favored_U' in t:
  s['movement_follow_close_ROI_pct']=round(100*t['market_movement_favored_U']/n,5)
  s['movement_against_close_ROI_pct']=round(100*t['market_movement_opposed_U']/n,5)
 summ[f'{y}_{m}_{cat}']=s
overall={}
for m in ('AH','OU'):
 for cat in sorted({z['movement_category'] for z in mov if z['market']==m}):
  rr=[z for z in mov if z['market']==m and z['movement_category']==cat]
  n=len(rr)
  s={'n':n}
  good=[z for z in rr if z['movement_side_close_U'] is not None]
  if good:
   s['favored_close_ROI_pct']=round(100*sum(z['movement_side_close_U'] for z in good)/len(good),5)
   s['opposed_close_ROI_pct']=round(100*sum(z['opposite_side_close_U'] for z in good)/len(good),5)
  overall[f'{m}_{cat}']=s
out={'name':'NEWSTART_BJ_20261123_CODEX_CROWN_SOURCE_TIME_AND_PRICE_DRIFT',
 'source':'Only current Codex SQLite, schedule and the newstart derived quote ledger.',
 'input_quote_role_baseline_source_rowids':B['rowid_fences'],
 'independent_settlement_and_kickoff_checks':dict(qa),
 'combined_role_fixture_total':len(quote),
 'paired_open_close_movement_fixtures':len(mov),
 'movement_overall':overall,
 'movement_by_year':summ,
 'notes':['Source timestamps before kickoff do not imply quotes were actually received before kickoff.',
  'Movement direction calculated from SOURCE HISTORICAL opening to closing events and only usable as retrospective description, NOT a live signal or user-approved betting rule.',
  'All movements and unchanged categories retained, no historical group models, no new EV gates.',
  'Same-price close/open selections were deterministic event-time extrema; source ties had no contradictory prices in this snapshot.']}
(P/'newstart_Crown_market_movement_by_fixture.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in mov))
(P/'newstart_Crown_market_timing_and_drift_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'audit':dict(qa),'drift':overall},ensure_ascii=False))
