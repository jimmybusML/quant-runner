#!/usr/bin/env python3
"""Point-in-time head-to-head (H2H) handicap residual experiment.

Uses only prior completed same-league meetings between the target clubs. This
is a historical event replay, not proof the historical Crown quotes were
actually received at the time. No production state is read or written.
"""
from __future__ import annotations
import collections, datetime as dt, hashlib, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
DATA = Path('/Users/mac/QuantAsiaDesk/research-work')
PATH_FILE = DATA/'m8_late_full_path_water_features_20261114.jsonl'
SCORE_FILE = DATA/'m8_independent_score_strength_20261114.jsonl'
MEMBERS = DATA/'m8_foundation_20261115/historical_membership.jsonl'
RECEIPT_AUDIT = ROOT/'research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl'
DECOMP = ROOT/'research/m8/selective_decomposition_20261120/M8_SELECTIVE_DECOMPOSITION_RESULTS_20261120.json'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def jlines(p):
 with p.open() as f:
  for l in f:
   if l.strip(): yield json.loads(l)
def settle(line,odds,diff):
 q=round(float(line)*4)/4
 d=q*2
 legs=[q] if abs(d-round(d))<1e-9 else [math.floor(d)/2,math.ceil(d)/2]
 r=[]
 for leg in legs:
  x=diff+leg
  r.append(float(odds)-1 if x>1e-9 else (-1.0 if x< -1e-9 else 0.0))
 return sum(r)/len(r)
def stats(rows):
 rows=[r for r in rows if r.get('pnl') is not None]
 n=len(rows); u=sum(r['pnl'] for r in rows)
 days=collections.defaultdict(float)
 for r in rows: days[r['date']]+=r['pnl']
 eq=hi=dd=0.0
 for day,v in sorted(days.items()):
  eq+=v; hi=max(hi,eq); dd=max(dd,hi-eq)
 weeks=sorted({dt.date.fromisoformat(r['date']).strftime('%G-W%V') for r in rows})
 wspan=0
 if rows:
  a=dt.date.fromisoformat(min(r['date'] for r in rows)); b=dt.date.fromisoformat(max(r['date'] for r in rows))
  wa=a.isocalendar(); wb=b.isocalendar()
  wspan=((dt.date.fromisocalendar(wb.year,wb.week,1)-dt.date.fromisocalendar(wa.year,wa.week,1)).days//7)+1
 weekly={w:{'n':0,'net_u':0.0} for w in weeks}
 for r in rows:
  w=dt.date.fromisoformat(r['date']).strftime('%G-W%V'); weekly[w]['n']+=1; weekly[w]['net_u']+=r['pnl']
 return {'n':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'week_span':wspan,'orders_per_week':round(n/wspan,6) if wspan else None,'weeks_with_orders':len(weeks),'max_drawdown_u':round(dd,6),'weekly':{k:{'n':v['n'],'net_u':round(v['net_u'],6)} for k,v in weekly.items()}}

# Keep archived historical Crown close-line quotes and teams, plus independently
# indexed fixture FT. Reject missing/conflicting IDs rather than fuzzy matching.
path={str(r['fid']):r for r in jlines(PATH_FILE)}
scores={str(r['fid']):r for r in jlines(SCORE_FILE)}
member_rows=list(jlines(MEMBERS))
member={str(r['fid']) for r in member_rows}
rows=[]; missing=[]
for fid,p in path.items():
 z=scores.get(fid)
 if not z: continue
 try:
  if str(p['league'])!=str(z['league']) or str(p['date'])!=str(z['date']):
   missing.append({'fid':fid,'reason':'fixture identity mismatch'}); continue
  kickoff=dt.datetime.fromisoformat(z['ko'].replace('Z','+00:00'))
  hg,ag=int(z['hg']),int(z['ag'])
  line=float(p['end_line']); oh,oa=float(p['home_price']),float(p['away_price'])
 except (TypeError,ValueError,KeyError): continue
 if not (math.isfinite(line) and math.isfinite(oh) and math.isfinite(oa) and oh>1 and oa>1): continue
 rows.append({'fid':fid,'date':kickoff.date().isoformat(),'kickoff':kickoff.isoformat(),'year':kickoff.year,'league':str(z['league']),'home':str(z['home']),'away':str(z['away']),'hg':hg,'ag':ag,'line':line,'odds_home':oh,'odds_away':oa,'frozen_member':fid in member})
rows.sort(key=lambda r:(r['kickoff'],r['fid']))
# Build prior same-league H2H outcomes, target-home-team-relative, strictly
# earlier kickoff and never use same-time fixtures.
by_league=collections.defaultdict(list)
results=[]
h2h_prior_by_fid={}
rows_by_fid={r['fid']:r for r in rows}
for r in rows:
 prior=[]
 for old in by_league[r['league']]:
  if old['kickoff']>=r['kickoff']: continue
  if {old['home'],old['away']} != {r['home'],r['away']}: continue
  if old['home']==r['home']:
   residual=(old['hg']-old['ag'])+old['line']
   previous_side='home'
  else:
   residual=(old['ag']-old['hg'])-old['line']
   previous_side='away'
  prior.append({'fid':old['fid'],'date':old['date'],'side_of_target_home':previous_side,'handicap_cover_margin':round(residual,6)})
 if prior:
  avg=sum(x['handicap_cover_margin'] for x in prior)/len(prior)
  last=prior[-1]['handicap_cover_margin']
  h2h_prior_by_fid[r['fid']]={'prior_h2h_n':len(prior),'h2h_mean_cover_margin':round(avg,6),'h2h_last_cover_margin':round(last,6),'selected_side':'home' if avg>1e-9 else ('away' if avg< -1e-9 else None)}
  if r['frozen_member']:
   by_league[r['league']].append(r)
   continue
  # The market line determines the market-favorite role; for level line use
  # lower Crown price. This is a comparator, not a candidate rule.
  fav='home' if r['line']<0 else ('away' if r['line']>0 else ('home' if r['odds_home']<r['odds_away'] else 'away'))
  goals=r['hg']-r['ag']
  for variant,sig in [('all_prior_mean',avg),('last_prior_only',last)]:
   side='home' if sig>1e-9 else ('away' if sig< -1e-9 else None)
   pnl=settle(r['line'] if side=='home' else -r['line'],r['odds_home'] if side=='home' else r['odds_away'],goals if side=='home' else -goals) if side else None
   market_pnl=settle(r['line'] if fav=='home' else -r['line'],r['odds_home'] if fav=='home' else r['odds_away'],goals if fav=='home' else -goals)
   results.append({**r,'method':variant,'prior_h2h_n':len(prior),'h2h_mean_cover_margin':round(avg,6),'h2h_last_cover_margin':round(last,6),'h2h_signal':round(sig,6),'selected_side':side,'pnl':round(pnl,6) if pnl is not None else None,'market_favorite_side':fav,'market_favorite_pnl':round(market_pnl,6),'prior_h2h':prior})
 by_league[r['league']].append(r)

# Actual receipt replay: collapse the independently audited 1,230-FID archive,
# reject any known quote-mismatch FID, require pre-kickoff receipt and verified FT,
# and use its exact received Crown contract rather than the historical close.
receipt_rows=collections.defaultdict(list)
for rr in jlines(RECEIPT_AUDIT):
 if rr.get('source_type')=='actual_http_receipt': receipt_rows[str(rr['fid'])].append(rr)
dec=json.loads(DECOMP.read_text())
mismatch_fids={str(x['fid']) for x in dec.get('mismatch_audit_note',{}).get('examples',[])}
h2h_by_fid={}
for r in results:
 if r['method']=='all_prior_mean': h2h_by_fid[r['fid']]=r
receipt_orders=[]; receipt_exclusions=collections.Counter()
for fid,rs in receipt_rows.items():
 if fid in mismatch_fids:
  receipt_exclusions['known_quote_mismatch_fid']+=1; continue
 # the archive repeats each receipt across method rows; verify the captured
 # contract itself is identical before reducing to one unique fixture.
 contracts={(float(x['line_home']),float(x['odds_home']),float(x['odds_away']),x.get('received_utc'),x.get('kickoff_utc'),x.get('ft')) for x in rs}
 if len(contracts)!=1:
  receipt_exclusions['inconsistent_repeated_receipt_rows']+=1; continue
 rr=rs[0]
 try:
  received=dt.datetime.fromisoformat(rr['received_utc'].replace('Z','+00:00'))
  kickoff=dt.datetime.fromisoformat(rr['kickoff_utc'].replace('Z','+00:00'))
  hh,aa=map(int,str(rr['ft']).split('-'))
  line=float(rr['line_home']); oh=float(rr['odds_home']); oa=float(rr['odds_away'])
 except Exception:
  receipt_exclusions['missing_receipt_or_ft']+=1; continue
 if received>=kickoff:
  receipt_exclusions['not_pregame_receipt']+=1; continue
 if not rr.get('ft_source') or not rr.get('raw_sha256') or not rr.get('snapshot_sha256'):
  receipt_exclusions['missing_provenance']+=1; continue
 if fid not in rows_by_fid:
  receipt_exclusions['no_historical_fixture_identity_or_score_row']+=1; continue
 if rows_by_fid[fid]['frozen_member']:
  receipt_exclusions['frozen_eight_overlap']+=1; continue
 base=h2h_prior_by_fid.get(fid)
 if base is None:
  receipt_exclusions['no_prior_same_league_h2h']+=1; continue
 side=base['selected_side']
 if side is None:
  receipt_exclusions['no_h2h_direction']+=1; continue
 selected_line=line if side=='home' else -line
 selected_odds=oh if side=='home' else oa
 gd=hh-aa if side=='home' else aa-hh
 pnl=settle(selected_line,selected_odds,gd)
 favorite='home' if line<0 else ('away' if line>0 else ('home' if oh<oa else 'away'))
 fav_line=line if favorite=='home' else -line
 fav_odds=oh if favorite=='home' else oa
 fav_gd=hh-aa if favorite=='home' else aa-hh
 favorite_pnl=settle(fav_line,fav_odds,fav_gd)
 receipt_orders.append({'fid':fid,'date':rr['date'],'kickoff_utc':rr['kickoff_utc'],'received_utc':rr['received_utc'],'raw_sha256':rr['raw_sha256'],'snapshot_sha256':rr['snapshot_sha256'],'ft_source':rr['ft_source'],'ft':rr['ft'],'line_home':line,'odds_home':oh,'odds_away':oa,'h2h_prior_count':base['prior_h2h_n'],'h2h_mean_cover_margin':base['h2h_mean_cover_margin'],'side':side,'net_u':round(pnl,6),'market_favorite_side':favorite,'market_favorite_net_u':round(favorite_pnl,6),'known_quote_match_mismatch_excluded':False})
with (OUT/'h2h_actual_receipt_orders.jsonl').open('w') as f:
 for r in receipt_orders: f.write(json.dumps(r,ensure_ascii=False)+'\n')
receipt_summary={'unique_receipt_fids':len(receipt_rows),'known_mismatch_fids_excluded':len(mismatch_fids),'qualifying_unique_fids':len(receipt_orders),'exclusions':dict(receipt_exclusions),'results':stats([{'date':r['date'],'pnl':r['net_u']} for r in receipt_orders]),'same_fid_market_favorite_comparator':stats([{'date':r['date'],'pnl':r['market_favorite_net_u']} for r in receipt_orders]),'by_year':{},'by_week':stats([{'date':r['date'],'pnl':r['net_u']} for r in receipt_orders])['weekly'],'orders_file':'h2h_actual_receipt_orders.jsonl','note':'Unique FIDs, pre-kickoff actual HTTP receipt, raw and snapshot SHA present, verified FT source; known mismatch FIDs removed. Historical H2H only used events before target kickoff. This is an out-of-sample replay on an already-designed receipt archive, not a live locked strategy.'}
for y in sorted({r['date'][:4] for r in receipt_orders}): receipt_summary['by_year'][y]=stats([{'date':r['date'],'pnl':r['net_u']} for r in receipt_orders if r['date'].startswith(y)])

summary={'study':'same-league prior H2H Crown AH cover-margin transfer','research_only':True,'hypothesis':'A target home club may retain matchup-specific performance versus the same opponent beyond its historical Crown handicap, including when venue reverses. Signal is cumulative prior H2H spread residual; no target or future data are used.','temporal_rule':'strictly earlier kickoff UTC, same exact league ID and same two team IDs; equal kickoff excluded','quote_source':'historical Crown close quote event replay; not a verified pregame HTTP receipt unless separately marked','settlement':'correct AH one-unit return, quarter lines split into two equal stakes','input_sha256':{str(p):sha(p) for p in [PATH_FILE,SCORE_FILE,MEMBERS]},'coverage':{'path_rows':len(path),'score_rows':len(scores),'joined_fixture_rows':len(rows),'frozen_member_fids':len(member),'frozen_member_join_rows':sum(1 for r in rows if r['frozen_member']),'outside_foundation_join_rows':sum(1 for r in rows if not r['frozen_member']),'fixture_identity_mismatches':missing[:100],'joined_unique_fids':len({r['fid'] for r in rows})},'methods':{},'all_history_rows':len(results),'candidate_rows_file':'h2h_candidate_orders.jsonl','actual_receipt_replay':receipt_summary,'receipt_input_sha256':sha(RECEIPT_AUDIT),'decomposition_input_sha256':sha(DECOMP)}
for method in ['all_prior_mean','last_prior_only']:
 xs=[r for r in results if r['method']==method]
 cands=[r for r in xs if r['selected_side'] is not None]
 summary['methods'][method]={'covered_repeat_pair_fids':len(xs),'unique_bet_fids':len(cands),'no_signal_or_exact_push':len(xs)-len(cands),'results':stats(cands),'market_favorite_same_bet_fids':stats([{**r,'pnl':r['market_favorite_pnl']} for r in cands]),'market_favorite_all_repeat_pair_fids':stats([{**r,'pnl':r['market_favorite_pnl']} for r in xs]),'by_year':{str(y):stats([r for r in cands if r['year']==y]) for y in sorted({r['year'] for r in cands})},'by_year_market_favorite':{str(y):stats([{**r,'pnl':r['market_favorite_pnl']} for r in xs if r['year']==y]) for y in sorted({r['year'] for r in xs})}}
# Union with the immutable original eight, by unique FID and year.
h2h_orders=[r for r in results if r['method']=='all_prior_mean' and r['selected_side'] is not None]
combined_by_year={}
for y in (2024,2025,2026):
 frozen=[{'fid':str(r['fid']),'date':str(r['date']),'pnl':float(r['pnl'])} for r in member_rows if int(r['year'])==y]
 added=[{'fid':r['fid'],'date':r['date'],'pnl':r['pnl']} for r in h2h_orders if r['year']==y]
 combo={r['fid']:r for r in frozen}
 for r in added:
  if r['fid'] in combo: raise RuntimeError('H2H incremental FID overlaps frozen eight')
  combo[r['fid']]=r
 combined_by_year[str(y)]={'frozen_eight':stats(frozen),'h2h_increment':stats(added),'merged_unique_fids':stats(list(combo.values())),'incremental_fids':len(added)}
summary_union={'by_year':combined_by_year,'h2h_2024_2026':stats([{'date':r['date'],'pnl':r['pnl']} for r in h2h_orders if r['year'] in (2024,2025,2026)]),'frozen_eight_2024_2026':stats([{'date':str(r['date']),'pnl':float(r['pnl'])} for r in member_rows if int(r['year']) in (2024,2025,2026)])}
# Variant overlap is descriptive only; no arbitration or additive union.
method_rows={}
for r in results:
 if r['selected_side'] is not None: method_rows.setdefault(r['fid'],{})[r['method']]=r['selected_side']
both={f:d for f,d in method_rows.items() if d.get('all_prior_mean') and d.get('last_prior_only')}
summary_overlap={'all_prior_mean_fids':sum(bool(d.get('all_prior_mean')) for d in method_rows.values()),'last_prior_only_fids':sum(bool(d.get('last_prior_only')) for d in method_rows.values()),'overlap_fids':len(both),'union_fids':sum(bool(d.get('all_prior_mean') or d.get('last_prior_only')) for d in method_rows.values()),'direction_conflict_fids':sum(d['all_prior_mean']!=d['last_prior_only'] for d in both.values())}
summary['frozen_eight_union']=summary_union
summary['method_overlap']=summary_overlap
with (OUT/'h2h_candidate_orders.jsonl').open('w') as f:
 for r in results: f.write(json.dumps(r,ensure_ascii=False)+'\n')
(OUT/'h2h_results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print('coverage',summary['coverage'],'joined',summary['coverage']['joined_unique_fids'],'rows',summary['all_history_rows'])
for method,x in summary['methods'].items():
 print(method,'covered',x['covered_repeat_pair_fids'],'bets',x['unique_bet_fids'],'net/ROI/MDD',x['results']['net_u'],x['results']['roi_pct'],x['results']['max_drawdown_u'])
 print('years',{y:{k:x['by_year'][y][k] for k in ['n','net_u','roi_pct','orders_per_week','max_drawdown_u']} for y in x['by_year']})
 print('market_same_bets', {k:x['market_favorite_same_bet_fids'][k] for k in ['n','net_u','roi_pct','orders_per_week','max_drawdown_u']})
