#!/usr/bin/env python3
"""2026-11-23 reset: only Codex active Crown 64-league SQLite and schedule.
Open and close price baselines, both opposing sides, 1U nominal; no old
models or historical group assumptions, no strategy or production mutations.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json,sqlite3,datetime,math,hashlib
P=Path('/Users/mac/QuantAsiaDesk/research-work/newstart_20261123_codex_only')
D=Path('/private/tmp/quant-runner-history-backfill/research/data_recovery_2019_2026/ou_unification')
DB=Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
SCH=Path('/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl')
coverage=json.loads((D/'crown_64_coverage_latest.json').read_text())
allowed={str(x) for x in coverage['approved_league_ids']}
sc={}
for line in SCH.open():
 r=json.loads(line)
 if str(r['league_id']) in allowed and 2023<=int(r['season_year'])<=2026:
  key=str(r['match_id'])
  if key in sc:raise RuntimeError(('duplicate Codex fixture',key))
  sc[key]=r
assert len(sc)==coverage['schedule_fids']==48102
print('Codex source schedule',len(sc),flush=True)
con=sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True,timeout=20)
con.execute('PRAGMA query_only=ON')
fences={table:con.execute('SELECT MAX(rowid) FROM '+table).fetchone()[0]
        for table in ('capture','crown_ou_source','asian_quote','crown_ou_quote')}
print('ROWID_FENCES',fences,flush=True)
def date(t):
 try:return datetime.datetime.fromisoformat(str(t).replace('Z','+00:00'))
 except (TypeError,ValueError):return None
chosen={};count=Counter();flags=Counter()
for m,table,linecol,one,two in [
 ('AH','asian_quote','handicap_home','home_decimal','away_decimal'),
 ('OU','crown_ou_quote','total_line','over_decimal','under_decimal')]:
 sql=f'''SELECT fixture_id,quote_kind,{linecol},{one},{two},
  quote_source_at_utc,response_received_at_utc,prospective_observation,quote_before_kickoff
  FROM {table} WHERE rowid<=? AND quote_kind IN ('open','close')'''
 for fid,role,lin,a,b,src,rec,pros,pre in con.execute(sql,(fences[table],)):
  count[m+'_raw_openclose']+=1
  if str(fid) not in sc:count[m+'_outside_codex_scope']+=1;continue
  count[m+'_in_scope']+=1
  if pre!=1:count[m+'_not_source_before_kickoff']+=1;continue
  if lin is None or a is None or b is None:count[m+'_null_price']+=1;continue
  lin,a,b=float(lin),float(a),float(b)
  if not all(map(math.isfinite,(lin,a,b))) or min(a,b)<=1 or abs(lin-round(lin*4)/4)>1e-8:
   count[m+'_invalid_asian_contract']+=1;continue
  when=date(src)
  if when is None:count[m+'_missing_source_event_time']+=1;continue
  key=(str(fid),m,role)
  prior=chosen.get(key)
  pack=(lin,a,b)
  new={'lin':lin,'a':a,'b':b,'when':when,'src':src,'recv':rec,
       'pros':int(bool(pros)),'alternatives':{pack}}
  if prior is None or (role=='open' and when<prior['when']) or (role=='close' and when>prior['when']):
   chosen[key]=new
  elif when==prior['when']:
   prior['alternatives'].add(pack)
   prior['pros']=max(prior['pros'],int(bool(pros)))
 print('MARKET_READ',m,count[m+'_raw_openclose'],count[m+'_in_scope'],flush=True)
con.close()
def split(l):
 k=round(l*4)
 if k%2==0:return [(l,1.)]
 return [(math.floor(l*2)/2.,.5),(math.ceil(l*2)/2.,.5)]
def pay(m,side,l,od,h,a):
 z=0
 for line,w in split(l):
  if m=='AH':dif=h-a+line if side==0 else a-h-line
  else:dif=h+a-line if side==0 else line-h-a
  z+=w*((od-1) if dif>1e-9 else -1 if dif<-1e-9 else 0)
 return z
ledger=[];tot=defaultdict(lambda:Counter())
for (fid,m,role),q in chosen.items():
 r=sc[fid]
 if r['home_goals'] is None or r['away_goals'] is None:count['missing_score']+=1;continue
 h,a=int(r['home_goals']),int(r['away_goals'])
 p1=pay(m,0,q['lin'],q['a'],h,a);p2=pay(m,1,q['lin'],q['b'],h,a)
 vig=1/q['a']+1/q['b']-1
 year=int(r['season_year']);t=tot[(year,m,role)]
 t['n']+=1;t['p1']+=p1;t['p2']+=p2;t['vig']+=vig;t['pros']+=q['pros']
 t['ambig']+=len(q['alternatives'])>1
 rec_dt=date(q['recv'])
 t['real_received_before_kickoff']+=q['pros']
 ledger.append({'fixture_id':fid,'league_id':str(r['league_id']),'year':year,
    'market':m,'kind':role,'home_goals':h,'away_goals':a,
    'line':q['lin'],'decimal_1':q['a'],'decimal_2':q['b'],
    'side1_U':p1,'side2_U':p2,'overround':vig,
    'source_event_at_utc':q['src'],'received_at_utc':q['recv'],
    'prospective_receipt':bool(q['pros']),
    'same_source_event_price_alternatives':sorted(map(list,q['alternatives']))})
def aggregate(rows):
 n=len(rows)
 if not n:return {'n':0}
 return {'n':n,
 'side1_roi_pct':round(100*sum(z['side1_U'] for z in rows)/n,5),
 'side2_roi_pct':round(100*sum(z['side2_U'] for z in rows)/n,5),
 'side1_net_U':round(sum(z['side1_U'] for z in rows),5),
 'side2_net_U':round(sum(z['side2_U'] for z in rows),5),
 'mean_overround_pct':round(100*sum(z['overround'] for z in rows)/n,5),
 'actual_pregame_received_n':sum(z['prospective_receipt'] for z in rows),
 'same_event_multiple_prices_n':sum(len(z['same_source_event_price_alternatives'])>1 for z in rows)}
overall={f'{m}_{kind}':aggregate([r for r in ledger if r['market']==m and r['kind']==kind])
 for m in ('AH','OU') for kind in ('open','close')}
byyear={f'{yr}_{m}_{kind}':aggregate([r for r in ledger if r['year']==yr and r['market']==m and r['kind']==kind])
 for yr in (2023,2024,2025,2026) for m in ('AH','OU') for kind in ('open','close')}
index={(r['fixture_id'],r['market'],r['kind']):r for r in ledger}
paired={}
for m in ('AH','OU'):
 pairs=[(index[(fid,m,'open')],index[(fid,m,'close')])
   for fid in sc if (fid,m,'open') in index and (fid,m,'close') in index]
 paired[m]={'paired_n':len(pairs),
    'line_up_n':sum(b['line']>a['line'] for a,b in pairs),
    'line_down_n':sum(b['line']<a['line'] for a,b in pairs),
    'line_same_n':sum(b['line']==a['line'] for a,b in pairs),
    'open_side1_ROI_pct':round(100*sum(a['side1_U'] for a,b in pairs)/len(pairs),5) if pairs else None,
    'close_side1_ROI_pct':round(100*sum(b['side1_U'] for a,b in pairs)/len(pairs),5) if pairs else None,
    'open_side2_ROI_pct':round(100*sum(a['side2_U'] for a,b in pairs)/len(pairs),5) if pairs else None,
    'close_side2_ROI_pct':round(100*sum(b['side2_U'] for a,b in pairs)/len(pairs),5) if pairs else None}
report={'name':'NEWSTART_BJ_20261123_CODEX_CROWN_MARKET_BASE',
 'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source':'ONLY current Codex collection crown_quotes.sqlite3 and crown-drop-expanded-62/schedule_universe.jsonl',
 'codex_scope':'Configured Codex 64 league ID universe and season_year 2023–2026, verified 48,102 fixtures; matches source config, not newly chosen league filter.',
 'schedule_fixtures':len(sc),'rowid_fences':fences,
 'collector_coverage_snapshot_utc':coverage['snapshot_at_utc'],
 'raw_count':dict(count),'overall':overall,'by_year':byyear,'paired_open_close':paired,
 'identity':'For open take earliest source quote event; for close latest source quote event. Same-time contradictory prices retained and counted, first encountered used for cash result. Quote_before_kickoff flag only establishes source event before kickoff, not HTTP receipt.',
 'contract':'Both opposing sides, 1U each, Asian quarter lines split equally, no EV cutoff, no strategic side selection. All source-price math historical and not executed.',
 'limitations':['Historic odds were usually fetched AFTER the match, even though source event time predates kickoff. Retrospective 1U outcomes are not actual tradable orders.',
  'Only prospective_receipt=1 signifies actual pregame receiver status, not placed bet or verified executable price.',
  'Same source-event conflicting prices need dedicated sensitivity review before strategy inference.',
  'Results use current Codex schedule scores and have not been independently verified externally.',
  'Each table read by bounded rowid from live SQLite with separate WAL transactions: no single atomic cross-table snapshot.',
  'No earlier historical grouped strategies, R5-R12 models or other raw data used; no production/collector changes or rules added.']}
with (P/'newstart_fixture_quote_baseline.jsonl').open('w') as f:
 for r in ledger:f.write(json.dumps(r,ensure_ascii=False)+'\n')
(P/'newstart_crown_market_baseline_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':overall,'by_year_close':{k:v for k,v in byyear.items() if k.endswith('_close')},
 'paired':paired,'raw':dict(count)},ensure_ascii=False),flush=True)
