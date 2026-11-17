import json,collections,datetime,math
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
historic=json.loads((P/'m8_r61_prior_year_news_stress_20261118.json').read_text())
realtime=json.loads((P/'m8_r61_reported_absence_ah_pilot_20261118.json').read_text())
assert realtime['coverage']['R22_T24_T12_verified_FT_AH_reconciled']==46
rows=[]
for z in historic['fixtures']:
 side=z['research_fewer_absences_side']
 rows.append({'year':z['year'],'fid':z['fid'],'date':z['kickoff_utc'][:10],
  'news_week':z['news_source_date'],'quote_type':'RETROSPECTIVE_Crown_event',
  'h':z['home'],'a':z['away'],'line':float(z['Crown_T12_line']),
  'home_price':float(z['home_price']),'away_price':float(z['away_price']),
  'home_pnl':z['fewer_absences_AH_Crown_T12_PnL'] if side=='home' else z['more_absences_AH_Crown_T12_PnL'] if side=='away' else None,
  'away_pnl':z['more_absences_AH_Crown_T12_PnL'] if side=='home' else z['fewer_absences_AH_Crown_T12_PnL'] if side=='away' else None,
  'fewer_absences_side':side,
  'home_absences':int(z['reported_unavailable_home']),'away_absences':int(z['reported_unavailable_away'])})
for z in realtime['reconciled_fixtures']:
 rows.append({'year':2026,'fid':z['fid'],'date':z['kickoff_utc'][:10],'news_week':z['source_date'],
  'quote_type':'ACTUAL_RECEIVED_Crown_T12',
  'h':z['home'],'a':z['away'],'line':float(z['T12_Crown_AH_line']),
  'home_price':float(z['T12_Crown_AH_home_decimal']),
  'away_price':float(z['T12_Crown_AH_away_decimal']),
  'home_pnl':z['Crown_T12_home_AH_profit'],'away_pnl':z['Crown_T12_away_AH_profit'],
  'fewer_absences_side':z['research_diagnostic_side'],
  'home_absences':int(z['home_reported_unavailable']),'away_absences':int(z['away_reported_unavailable'])})
# fix historical equal absence rows where original research did not compute
# individual side returns. They are included as no-hypothesis-count audit,
# not infer an outcome and do not count as candidate bets.
def calc(v):
 v=np.asarray(v,dtype=float);return {'n':int(len(v)),
  'U':round(float(v.sum()),3),'ROI':round(100*float(v.mean()),3) if len(v) else None,
  'wins':int((v>1e-8).sum()),'losses':int((v<-1e-8).sum()),'push':int((abs(v)<=1e-8).sum())}
for row in rows:
 side=row['fewer_absences_side']
 # AH sign interpreted per existing home handicap: negative home gives
 # handicap; away favored with positive home line.
 fav='home' if row['line']<0 else 'away' if row['line']>0 else (
  'home' if row['home_price']<row['away_price'] else 'away')
 row['market_favorite_side']=fav
 row['AH_zero_handicap']=(row['line']==0)
 if side is not None:
  more='away' if side=='home' else 'home'
  row['more_absences_side']=more
  assert row['home_pnl'] is not None and row['away_pnl'] is not None
  row['more_absences_PnL']=float(row[f'{more}_pnl'])
  row['market_favorite_PnL']=float(row[f'{fav}_pnl'])
  row['less_absences_PnL']=float(row[f'{side}_pnl'])
  row['more_absences_is_favorite']=more==fav
 # Original news-report counts cannot directly equate key lineup
 # losses; not necessarily first announced at source.
out={'study':'M8_R61_REPORTED_MORE_ABSENT_VS_CROWN_MARKET_FAVORITE',
 'method':'Post-hoc alternative direction from R61 less-absences hypothesis: compare MORE reported injured+suspended team to the pre-existing Crown AH handicap-market favorite on EXACT same unmatched/deduped fixtures, without filtering favorites out. Handicap 0 uses lower offered decimal odds as an explicit research tiebreaker (NOT a production rule), and separately reports strict handicap-nonzero subset. This controls first-order favorite selection confounding but cannot control match ability and squad valuation. 2024/25 Crown historic pregame source-event odds fetched retrospectively; 2026 AH priced at truly received Crown T12. News page timestamps audited and editorial, not confirmed original public injury first disclosure. Hypothesis invented after observing 2026 and prior-year stressed after discovery; not pre-registered independent prospective. Do not treat findings as production profitable or user-confirmed Gate.',
 'source':{'prior_year_files':len(historic['sources']),'2026_news_files':len(realtime['source_pages']),
  '2024_historical_match':sum(z['year']==2024 for z in rows),
  '2025_historical_match':sum(z['year']==2025 for z in rows),
  '2026_received_match':sum(z['year']==2026 for z in rows)},
 'comparison':{},'fixtures':rows}
sel=[z for z in rows if z['fewer_absences_side']]
assert len({z['fid'] for z in sel})==len(sel)
def compare(data):
 if not data:return {'n':0}
 more=np.array([z['more_absences_PnL'] for z in data])
 fav=np.array([z['market_favorite_PnL'] for z in data])
 less=np.array([z['less_absences_PnL'] for z in data])
 diff=more-fav
 return {'n':len(data),'more_reported_absences':calc(more),
  'less_reported_absences':calc(less),
  'Crown_handicap_market_favorite_same_fixtures':calc(fav),
  'more_absences_minus_favorite_totalU':round(float(diff.sum()),3),
  'more_absences_minus_favorite_roi_pp':round(float(100*diff.mean()),3),
  'more_absences_side_already_favorite_n':sum(z['more_absences_is_favorite'] for z in data),
  'more_absences_side_already_favorite_pct':round(100*np.mean([z['more_absences_is_favorite'] for z in data]),3),
  'AH_zero_handicap_n':sum(z['AH_zero_handicap'] for z in data),
  'more_absences_count_diff_mean':round(float(np.mean([abs(z['home_absences']-z['away_absences']) for z in data])),3)}
out['comparison']['all']=compare(sel)
for y in (2024,2025,2026):
 sub=[z for z in sel if z['year']==y]
 out['comparison'][str(y)]=compare(sub)
out['comparison']['line_nonzero_all']=compare([z for z in sel if not z['AH_zero_handicap']])
out['comparison']['market_favorite_but_more_absences']=compare([z for z in sel if z['more_absences_is_favorite']])
out['comparison']['market_underdog_but_more_absences']=compare([z for z in sel if not z['more_absences_is_favorite']])
out['comparison']['by_week']={}
for week in sorted({z['news_week'] for z in sel}):
 out['comparison']['by_week'][week]=compare([z for z in sel if z['news_week']==week])
# Bootstrap whole match-days for variance, 15 dated news weeks and match-days
# are not independent season-year cohorts. Does not correct model choice.
buckets=collections.defaultdict(list)
for z in sel:buckets[z['date']].append(z)
N=np.array([len(v) for v in buckets.values()],int)
U=np.array([sum(z['more_absences_PnL'] for z in v) for v in buckets.values()],float)
F=np.array([sum(z['market_favorite_PnL'] for z in v) for v in buckets.values()],float)
rng=np.random.default_rng(611);indexes=rng.integers(len(N),size=(6000,len(N)))
r=100*U[indexes].sum(1)/N[indexes].sum(1)
d=100*(U[indexes]-F[indexes]).sum(1)/N[indexes].sum(1)
out['comparison']['day_cluster_ROI_95percent']=[round(float(x),3) for x in np.quantile(r,[.025,.975])]
out['comparison']['day_cluster_more_minus_favorite_95percent_pp']=[round(float(x),3) for x in np.quantile(d,[.025,.975])]
out['comparison']['days_in_bootstrap']=len(N)
(P/'m8_r61_absence_vs_market_favorite_20261118.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('COVERAGE',out['source'],flush=True)
for k,v in out['comparison'].items():
 if k=='by_week':
  print('BY_WEEK',[(day,z['n'],z['more_reported_absences']['ROI'],z['Crown_handicap_market_favorite_same_fixtures']['ROI']) for day,z in v.items()],flush=True)
 else:print('COMPARE',k,v,flush=True)
