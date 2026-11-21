"""Audit and extend T6 historical Crown fixture inventory with saved new-league raw paths.
Keep every available AH contract, full-time score and frozen membership flag.
No additional admission threshold, no formal trading.
"""
import json,gzip,collections,math,datetime
from pathlib import Path
P=Path(__file__).resolve().parent
S=P.parent/'jack_crown_round1_20261121/unified_quotes.jsonl'
E=P/'source69/research/m8/red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'
F=P/'source67/research/m8_m9_group_independent_20261120/exact_rule_cross_league/group_f_market_mechanism_20261121/f_group_market_mechanism_rows.jsonl.gz'
frozen=set()
for s in open(P.parent/'m8_foundation_20261115/historical_membership.jsonl'):
 try:r=json.loads(s);frozen.add(str(r['fid']))
 except:pass
def settle(line,odds,diff):
 def part(l):
  a=diff+l
  return odds-1 if a>1e-8 else -1 if a < -1e-8 else 0.
 return (part(line-.25)+part(line+.25))/2 if int(round(line*4))%2 else part(line)
old={}
for s in open(S):
 r=json.loads(s)
 if r['T']!=6:continue
 fid=str(r['fid'])
 assert fid not in old
 old[fid]={'fid':fid,'source':'original49','year':r['year'],'league':str(r['league']),
   'ko':r['ko'],'line':float(r['al']),'home_odds':float(r['ah']),
   'away_odds':float(r['aa']),'hg':r['hg'],'ag':r['ag'],
   'home_U':float(r['home_U']),'away_U':float(r['away_U']),
   'is_m8_member':bool(r['is_m8_member']),'source_event_time':r.get('ah_quote_source_at_utc'),
   'capture_mode':r['capture_mode'],'prospective_observation':r['prospective_observation']}
ext={};invalid=[];leagues=collections.Counter()
with gzip.open(E,'rt') as f:
 for s in f:
  r=json.loads(s);fid=str(r['fid'])
  if fid in ext or fid in old:
   invalid.append((fid,'duplicate'));continue
  try:
   line=float(r['start_line']);ho=float(r['start_home_price']);ao=float(r['start_away_price'])
   h=int(r['hg']);a=int(r['ag']);assert 1<ho<10 and 1<ao<10
   assert r['source_event_times'][0] < r['kickoff_utc']
   hu=settle(line,ho,h-a);au=settle(-line,ao,a-h)
   row={'fid':fid,'source':'expanded15','year':int(r['year']),'league':str(r['league']),
        'ko':r['kickoff_utc'],'line':line,'home_odds':ho,'away_odds':ao,
        'hg':h,'ag':a,'home_U':hu,'away_U':au,'is_m8_member':fid in frozen,
        'source_event_time':r['source_event_times'][0],
        'capture_mode':r['capture_modes'][0],
        'prospective_observation':False,'raw_response_sha256':r['source_sha256'][0]}
   ext[fid]=row;leagues[r['league']]+=1
  except Exception as e:
   invalid.append((fid,str(e)))
assert not (set(ext)&set(old))
allrows=list(old.values())+list(ext.values())
with gzip.open(P/'full_priced_T6_original_and_expanded.jsonl.gz','wt') as f:
 for r in allrows:f.write(json.dumps(r)+'\n')
counter=collections.Counter()
for r in allrows:
 counter['total']+=1;counter[r['source']]+=1
 if r['year']>=2024:
  counter['test_total']+=1;counter['test_'+r['source']]+=1
  counter['test_outside']+=not r['is_m8_member']
  counter['test_outside_'+r['source']]+=not r['is_m8_member']
  counter['test_frozen']+=r['is_m8_member']
# F 109 fixed F historical as additional original T6 settlement audit
with gzip.open(F,'rt') as fp:Frows={r['fid']:r for s in fp if (r:=json.loads(s))}
matched=0;fmis=[]
for fid,v in Frows.items():
 if fid not in ext:continue
 matched+=1;x=ext[fid];y=v['T6']
 if (x['line'],x['home_odds'],x['away_odds']) != (y['line_home'],y['home_odds'],y['away_odds']):fmis.append(fid)
report={'counts':dict(counter),'new_league_ids':dict(leagues),'distinct_league_ids':len({r['league'] for r in allrows}),
        'overlap_fid_original_extended':0,'invalid_new_rows':invalid[:30],'invalid_new_n':len(invalid),
        'F_fixed_109_T6_matches':matched,'F_fixed_109_T6_discrepancies':fmis,
        'note':'historical source-event data only; not true pregame HTTP receipt; no new product scope rules'}
(P/'full_priced_T6_inventory_summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
