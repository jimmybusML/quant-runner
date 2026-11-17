import json,collections,hashlib
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
prior=json.loads((P/'m8_r61_absence_vs_market_favorite_20261118.json').read_text())
members={r['fid'] for r in map(json.loads,(P/'m8_foundation_20261115/historical_membership.jsonl').open())}
rows=[r for r in prior['fixtures'] if r.get('more_absences_side')]
assert len(rows)==117 and len(set(r['fid'] for r in rows))==117
def pnl(row,side):
 return float(row['home_pnl'] if side=='home' else row['away_pnl'])
def other(side):return 'away' if side=='home' else 'home'
def stat(a):
 v=np.array(a,float)
 return {'n':len(v),'U':round(float(v.sum()),3),'ROI':round(100*float(v.mean()),3) if len(v) else None}
for row in rows:
 row['unconditional_Crown_AH_underdog_side']=other(row['market_favorite_side'])
 row['unconditional_Crown_AH_underdog_pnl']=pnl(row,row['unconditional_Crown_AH_underdog_side'])
 row['already_frozen_eight_T1_MEMBER_POSTHOC']=row['fid'] in members
 out1=row['more_absences_PnL']
 row['more_absences_minus_underdog_pnl']=round(out1-row['unconditional_Crown_AH_underdog_pnl'],4)
out={'study':'M8_R61_BETWEEN_MODEL_CONTROLS',
 'explanation':'Posthoc research; baseline always underdog and archived original eight membership compared on EXACT same 117 fixtures. Existing original-eight signal identity is FUTURE/T1 and CANNOT be used as T12 real-time exclusion. More absent-side was derived after seeing 2026 data, not a precommitted 2024-26 forward strategy. Day bootstrap does not correct selection bias or reportage representativeness. Production unchanged.',
 'all':{},'years':{},'original_eight_posthoc':{},'ci':{},'coverage':{}}
def report(rs):
 return {'more_absences_side':stat([r['more_absences_PnL'] for r in rs]),
         'unconditional_underdog':stat([r['unconditional_Crown_AH_underdog_pnl'] for r in rs]),
         'more_minus_underdog':stat([r['more_absences_minus_underdog_pnl'] for r in rs]),
         'market_favorite':stat([r['market_favorite_PnL'] for r in rs]),
         'unconditional_home':stat([r['home_pnl'] for r in rs]),
         'unconditional_away':stat([r['away_pnl'] for r in rs])}
out['all']=report(rows)
for yr in (2024,2025,2026):out['years'][str(yr)]=report([r for r in rows if r['year']==yr])
for yr in (2024,2025,2026):
 group=[r for r in rows if r['year']==yr]
 inside=[r for r in group if r['already_frozen_eight_T1_MEMBER_POSTHOC']]
 outside=[r for r in group if not r['already_frozen_eight_T1_MEMBER_POSTHOC']]
 out['original_eight_posthoc'][str(yr)]={
  'all_unequal_absences':len(group),'inside_T1_frozen':len(inside),'outside_T1_frozen':len(outside),
  'outside_more_absences_AH':stat([r['more_absences_PnL'] for r in outside]),
  'inside_more_absences_AH':stat([r['more_absences_PnL'] for r in inside]),
  'outside_underdog':stat([r['unconditional_Crown_AH_underdog_pnl'] for r in outside])}
dates=collections.defaultdict(list)
for row in rows:dates[row['date']].append(row)
blocks=np.array([(sum(r['more_absences_minus_underdog_pnl'] for r in rr),len(rr)) for rr in dates.values()])
rng=np.random.default_rng(61117);ids=rng.integers(len(blocks),size=(8000,len(blocks)))
boots=100*blocks[ids,0].sum(axis=1)/blocks[ids,1].sum(axis=1)
out['ci']={'UTC_day_cluster_more_minus_underdog_95pct_pp':[round(float(v),3) for v in np.quantile(boots,[.025,.975])],
 'UTC_days':len(blocks),'resamples':8000}
out['coverage']={'unique_fixture_ids':len(rows),'historical_Crown_postretrieved':sum(r['year']<2026 for r in rows),
 '2026_actual_Crown_receipts':sum(r['year']==2026 for r in rows)}
P.joinpath('m8_r61_incremental_confounds_20261118.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('CONTROL',out)
