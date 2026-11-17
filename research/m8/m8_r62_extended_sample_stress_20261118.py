import json,collections,hashlib
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
early=json.loads((P/'m8_r62_full_season_absence_ah_replay_20261118.json').read_text())
actual=json.loads((P/'m8_r61_reported_absence_ah_pilot_20261118.json').read_text())
old=json.loads((P/'m8_r61_prior_year_news_stress_20261118.json').read_text())
assert early['discovery']['source_pages_found']==22 and actual['coverage']['R22_T24_T12_verified_FT_AH_reconciled']==46
members={r['fid'] for r in map(json.loads,(P/'m8_foundation_20261115/historical_membership.jsonl').open())}
items=[]
for a in early['fixtures']:
 if a['research_more_absent_side'] is None:continue
 items.append({'fid':a['fid'],'year':a['year'],'day':a['UTC_date'],
 'more':a['more_PnL'],'less':a['less_PnL'],'underdog':a['underdog_PnL'],
 'home':a['Crown_home_PnL'],'away':a['Crown_away_PnL'],
 'original8_posthoc':a['future_T1_frozen_eight_POSTHOC']})
for a in actual['reconciled_fixtures']:
 if a['research_diagnostic_side'] is None:continue
 favored='home' if a['T12_Crown_AH_line']<0 else 'away' if a['T12_Crown_AH_line']>0 else (
  'home' if a['T12_Crown_AH_home_decimal']<a['T12_Crown_AH_away_decimal'] else 'away')
 items.append({'fid':a['fid'],'year':2026,'day':a['kickoff_utc'][:10],
 'more':a['Crown_T12_away_AH_profit'] if a['research_diagnostic_side']=='home' else a['Crown_T12_home_AH_profit'],
 'less':a['research_diagnostic_PnL'],
 'underdog':a['Crown_T12_away_AH_profit'] if favored=='home' else a['Crown_T12_home_AH_profit'],
 'home':a['Crown_T12_home_AH_profit'],'away':a['Crown_T12_away_AH_profit'],
 'original8_posthoc':a['fid'] in members})
assert len(items)==208 and len({z['fid'] for z in items})==208
def stat(vals):
 z=np.array(vals,float)
 return {'n':len(z),'U':round(float(z.sum()),3),'ROI':round(100*float(z.mean()),3) if len(z) else None}
def group(items):
 return {'reported_more_unavailable':stat([z['more'] for z in items]),
 'reported_less_unavailable':stat([z['less'] for z in items]),
 'unconditional_AH_underdog':stat([z['underdog'] for z in items]),
 'unconditional_home':stat([z['home'] for z in items]),
 'more_minus_underdog':stat([z['more']-z['underdog'] for z in items]),
 'outside_original8_T1_POSTHOC':stat([z['more'] for z in items if not z['original8_posthoc']])}
data={'study':'M8_R62_PARTIAL_EXPANSION_COUNTING_AH_SAMPLE',
 'method':'Combine complete reverified local R62 2024/25 saved pre-match article issues (17 in 2024, 5 in 2025) with 5 R61 real 2026 issues; genuine cross-event ID set, unweighted reported injured+suspended winner direction from R61. Compare equal fixtures unconditional AH underdog/home and posthoc original eight only as attribution, NEVER future membership live selection. 2024/25 market prices post-retrieved, 2026 actual received; all evaluated after model research and outcomes. Not 2024/25 full season because remote HTTP proxy outage interrupted discovery; not truly out-of-sample. Not a new formal rule.',
 'source':{'R62_2024_news_issues':17,'R62_2025_news_issues':5,'R61_2026_news_issues':5,
 'R62_complete_season_discovery':False,'new_2024_matches':91},
 'overall':group(items),'by_year':{},'new_2024_only':{},'utc_day_bootstrap':{},'foundation':{}}
for yr in (2024,2025,2026):
 data['by_year'][str(yr)]=group([z for z in items if z['year']==yr])
oldids={z['fid'] for z in old['fixtures']}
new=[z for z in items if z['year']==2024 and z['fid'] not in oldids]
assert len(new)==91
data['new_2024_only']=group(new)
day=collections.defaultdict(list)
for r in items:day[r['day']].append(r)
D=np.array([[sum(z['more'] for z in v),sum(z['more']-z['underdog'] for z in v),len(v)] for v in day.values()])
rng=np.random.default_rng(6200)
ix=rng.integers(len(D),size=(10000,len(D)))
for key,j in [('more',0),('more_minus_underdog',1)]:
 v=100*D[ix,j].sum(1)/D[ix,2].sum(1)
 data['utc_day_bootstrap'][key]={'n_unique_kickoff_dates':len(D),
  'ROI_or_pp_95pct':[round(float(t),3) for t in np.quantile(v,[.025,.975])]}
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
digest=lambda f:hashlib.sha256((P/f).read_bytes()).hexdigest()
data['foundation']={'membership':digest(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(digest(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(digest(k)==v for k,v in manifest['script_sha256'].items())}
assert all(data['foundation'].values())
(P/'m8_r62_extended_sample_stress_20261118.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
print('RESULT',data['source'],data['overall'])
print('YEAR',data['by_year'],'NEW2024',data['new_2024_only'])
print('DAY_BOOTSTRAP',data['utc_day_bootstrap'])
