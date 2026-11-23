#!/usr/bin/env python3
"""R12-D: uncertainty about tiny shot-volume improvements beyond market.
Only pre-existing R12 7073 target-year held out predictions used. Tests:
  * independent fixture-pair bootstrap
  * whole league-season cluster bootstrap
  * whole year cluster bootstrap
  * sign-flip randomization of paired losses for all 8 pre-specified
    shot-feature research variants with max-statistic multiplicity check.
No filters, EV gates, trades or claims of ROI. Methods are diagnostics only.
"""
from pathlib import Path
from collections import defaultdict
import hashlib,json
import numpy as np
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r12_joint_goals_outcome_bias_20261123'
SOURCE=HERE/'r12_understat_shot_profile_Crown_increment_2021_2025.jsonl'
OUT=HERE/'r12_shot_profile_uncertainty_and_multiple_tests.json'
rows=[json.loads(s) for s in SOURCE.open()]
assert len(rows)==7073
models=[k for k in rows[0]['models'] if k!='market_only']
labels=[(r['season'],r['league']) for r in rows]
cluster_map=defaultdict(list)
year_map=defaultdict(list)
for i,key in enumerate(labels):
 cluster_map[key].append(i);year_map[key[0]].append(i)
market=np.array([r['models']['market_only']['Brier'] for r in rows])
D=np.array([[r['models']['market_only']['Brier']-r['models'][m]['Brier'] for m in models] for r in rows])
D_ll=np.array([[r['models']['market_only']['logloss']-r['models'][m]['logloss'] for m in models] for r in rows])
rng=np.random.default_rng(20261123)
target=models.index('current_season_shot_volume')
def interval(x):
 return [round(float(y),8) for y in np.quantile(x,[.025,.975])]
# Use analytical normal fixture cluster? Bootstrap mean with fixture-resampling.
n=len(rows)
n_boot=10000
means=np.empty(n_boot)
ll=np.empty(n_boot)
for k in range(n_boot):
 ix=rng.integers(0,n,n)
 means[k]=D[ix,target].mean()
 ll[k]=D_ll[ix,target].mean()
# whole cluster bootstraps reweight group-level mean and group size
def boot_block(groups,reps=10000):
 count=np.array([len(v) for v in groups],float)
 gain=np.array([D[ix,target].sum() for ix in groups],float)
 val=np.empty(reps)
 for i in range(reps):
  ids=rng.integers(0,len(groups),len(groups))
  val[i]=gain[ids].sum()/count[ids].sum()
 return val
season_values=boot_block(list(year_map.values()))
leagueyear_values=boot_block(list(cluster_map.values()))
# Paired randomization tests for models simultaneously:
# flip all model loss differences for the entire fixture under exchangeability.
# Not proof, and goals correlated across teams/season; an additional
# conservative grouped sign-flip grouped by league-season is also computed.
observed=D.mean(axis=0)
num=12000
null=np.empty((num,len(models)))
for i in range(0,num,240):
 batch=min(240,num-i)
 signs=rng.choice(np.array([-1.,1.]),size=(batch,n))
 null[i:i+batch,:]=signs@D/n
single_p=float((np.sum(null[:,target]>=observed[target])+1)/(num+1))
max_p=float((np.sum(null.max(axis=1)>=observed[target])+1)/(num+1))
cluster_values=np.array([D[x].sum(axis=0) for x in cluster_map.values()])
cn=len(cluster_values)
cluster_null=np.empty((num,len(models)))
for i in range(0,num,240):
 batch=min(240,num-i)
 signs=rng.choice(np.array([-1.,1.]),size=(batch,cn))
 cluster_null[i:i+batch,:]=signs@cluster_values/n
cluster_single=float((np.sum(cluster_null[:,target]>=observed[target])+1)/(num+1))
cluster_max=float((np.sum(cluster_null.max(axis=1)>=observed[target])+1)/(num+1))
result={'study':'R12_SHOT_VOLUME_OBSERVED_BRIER_IMPROVEMENT_UNCERTAINTY_AND_MULTIPLE_RESEARCH_VARIANTS',
 'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'full_heldout_n':n,'model_variants_tested':models,
 'models_count':len(models),
 'selected_for_diagnostic':'current_season_shot_volume',
 'selected_model_is_not_user_approved':True,
 'observed_market_minus_model_Brier':round(float(observed[target]),9),
 'observed_market_minus_model_logloss':round(float(D_ll[:,target].mean()),9),
 'fixture_bootstrap_10000_95pct_Brier_gain':interval(means),
 'fixture_bootstrap_10000_95pct_logloss_gain':interval(ll),
 'league_season_25_cluster_bootstrap_10000_95pct_Brier_gain':interval(leagueyear_values),
 'season_5_cluster_bootstrap_10000_95pct_Brier_gain':interval(season_values),
 'signflip_12000_single_volume_one_sided_p':round(single_p,6),
 'signflip_12000_best_of_8_familywise_p':round(max_p,6),
 'league_season_25_signflip_single_volume_p':round(cluster_single,6),
 'league_season_25_signflip_best_of_8_p':round(cluster_max,6),
 'all_8_variants_Brier_gain':{model:round(float(observed[i]),9) for i,model in enumerate(models)},
 'methodology':'Paired same-fixture Brier differences. Repeated 10000 resamples independently at fixture, 25 league-season clusters, 5 full seasons. 12000 paired sign-flips across all 8 variants test maximum observed gain as post-selection multiple-model sanity check. No ROI, no monetary betting simulation; purely descriptive uncertainty.',
 'limitations':['User-requested open-minded exploration: eight research variants now observed and only one tiny aggregate positive; selection-after-looking means claimed single p-value is not an honest discovery rate.',
   'Fixture signflip may be anti-conservative for correlated league/season data; present 25-cluster check and year-bootstrap too.',
   'All training and test are historical Crown T12 source-event prices retrieved after the games; this is not real receipted executable blind testing.',
   'Historical Understat shot arrival/publishing times unknown; strict match date prior does not independently prove pregame observable data.',
   'Five season-block bootstrap contains only five blocks, so interval is unstable and not a proof of transportability.',
   'No new betting Gates, no profitability claims; no national teams.']}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
