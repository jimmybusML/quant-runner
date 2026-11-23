#!/usr/bin/env python3
"""R12 supplementary independent coverage and reconciliation of 405363 raw
Understat shots vs 16111 match-level xG totals. No filtering of test cohort,
no change to asof research models. Distinguish shot sums from published xG.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,hashlib,statistics,math
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r12_joint_goals_outcome_bias_20261123'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
OUT=HERE/'r12_shot_source_reconciliation_2017_2025.json'
audit=Counter();byseason=defaultdict(Counter)
deltas=[];filehash=hashlib.sha256()
for lg in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
 for yr in range(2017,2026):
  folder=DATA/lg/str(yr)
  sp=folder/'shots.csv';fp=folder/'fixtures.csv'
  shot=defaultdict(lambda:[0.,0.,0,0])
  filehash.update(sp.relative_to(DATA).as_posix().encode())
  filehash.update(hashlib.sha256(sp.read_bytes()).digest())
  with sp.open(encoding='utf-8-sig') as f:
   for r in csv.DictReader(f):
    k=r['fixture_id'];side=0 if r['side']=='h' else 1
    shot[k][side]+=float(r['understat_xg'])
    shot[k][2+side]+=1
    audit['all_shots']+=1
    byseason[(lg,str(yr))]['shots']+=1
  with fp.open(encoding='utf-8-sig') as f:
   for r in csv.DictReader(f):
    audit['all_fixtures']+=1
    byseason[(lg,str(yr))]['fixtures']+=1
    value=shot[r['fixture_id']]
    if value[2]+value[3]==0:
        audit['fixtures_with_zero_shot_records']+=1
    if r['totals_unreliable'].lower()=='true' or not r['home_published_xg'] or not r['away_published_xg']:
        audit['unreliable_or_missing_published_xG_fixture']+=1;continue
    audit['valid_published_xG_fixture']+=1
    for side,column in enumerate(('home_published_xg','away_published_xg')):
      diff=value[side]-float(r[column])
      delta=abs(diff)
      deltas.append(delta)
      if delta>.01:audit['team_side_abs_diff_gt_0p01']+=1
      if delta>.1:
        audit['team_side_abs_diff_gt_0p1']+=1
        byseason[(lg,str(yr))]['team_side_abs_diff_gt_0p1']+=1
      if delta>.5:audit['team_side_abs_diff_gt_0p5']+=1
      if delta>1.:audit['team_side_abs_diff_gt_1']+=1
audit['total_published_xG_team_sides']=len(deltas)
assert audit['all_shots']==405363
assert audit['all_fixtures']==16111
assert audit['total_published_xG_team_sides']==32214
summary={'study':'R12_INDEPENDENT_UNDERSTAT_SHOT_XG_AGGREGATE_RECONCILIATION',
 'source_shots_file_list_hash_SHA256':filehash.hexdigest(),
 'raw':dict(audit),
 'team_side_abs_difference_quantiles':{p:round(float(sorted(deltas)[int((len(deltas)-1)*q)]),6) for p,q in
 [ ('p50',.5),('p75',.75),('p90',.9),('p95',.95),('p99',.99),('max',1.)]},
 'per_league_year':{lg+'_'+yy:dict(z) for (lg,yy),z in sorted(byseason.items())},
 'notes':['Shot-level xG summed and compared to separately published fixture-level match xG. Differences beyond 0.1 on some team-sides mean that one cannot silently substitute shot sums for published match xG.',
 'The R12 shot-profile study uses PREVIOUS raw shot counts and raw shot situation xG; it does NOT assert raw shots equal published xG.',
 'Exact reasons for discrepancy (revision, rounding, other shot definitions, incomplete shot events) not proven by this audit.',
 'This is a READ-ONLY historic quality audit, not a goal or financial order filter.']}
OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'raw':summary['raw'],'quantiles':summary['team_side_abs_difference_quantiles']},ensure_ascii=False))
