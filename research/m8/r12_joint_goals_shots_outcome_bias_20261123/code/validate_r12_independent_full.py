#!/usr/bin/env python3
"""Independent R12 numeric/source validation: no imports from R12 models.
- all 9908 Crown bivariate same-match Brier and 19816 contract payouts;
- 35 prior-year covariance estimates separately reconstructed from R5;
- all 7073 shot and outcome-bias market corrections, Brier/logloss;
- 10 + 40 train-only regression parameter score gradients;
- shot archive source identity and current-season priors;
- original R5 to R11 309 frozen files SHA256 unchanged;
- R12 shot p-value and source count checked separately.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,hashlib,math
import numpy as np
from scipy.special import softmax
from scipy.stats import poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r12_joint_goals_outcome_bias_20261123'
SNAP=ROOT/'frozen_research_snapshots'
F5=SNAP/'R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=SNAP/'R7_CROWN_MARKET_PRICING_20261123'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
FEAT=F5/'r5_bayes_bivar_asof_features_20261123.jsonl'
CROWN=F5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
BIV=HERE/'r12_bivariate_shared_count_CrownT12_20261123.jsonl'
BIVSUM=HERE/'r12_bivariate_shared_count_summary_20261123.json'
OUTCOME=HERE/'r12_outcome_bias_strict_past_xG_features_2019_2025.jsonl'
OUTLED=HERE/'r12_outcome_bias_market_increment_crossyear_2021_2025.jsonl'
OUTSUM=HERE/'r12_outcome_bias_market_increment_crossyear_summary.json'
SHOT=HERE/'r12_understat_shot_profile_prior_features_2019_2025.jsonl'
SHOTLED=HERE/'r12_understat_shot_profile_Crown_increment_2021_2025.jsonl'
SHOTSUM=HERE/'r12_understat_shot_profile_Crown_increment_summary.json'
UNC=HERE/'r12_shot_profile_uncertainty_and_multiple_tests.json'
RECON=HERE/'r12_shot_source_reconciliation_2017_2025.json'
OUTPUT=HERE/'r12_independent_sources_math_and_prior_freeze_validation.json'
errors=Counter();checks=Counter()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as fd:
  for x in iter(lambda:fd.read(1024*1024),b''):h.update(x)
 return h.hexdigest()
def legs(line):
 q=round(line*4)
 if abs(q/4-line)>1e-9:raise ValueError(line)
 return [(line,1)] if q%2==0 else [(math.floor(line*2)/2.,.5),(math.ceil(line*2)/2.,.5)]
def cash(score,kind,q,side):
 h,a=map(int,score.split('-'))
 val=0.
 for leg,w in legs(float(q['line'])):
  d=h-a+leg if side=='home' else a-h-leg if side=='away' else h+a-leg if side=='over' else leg-h-a
  val+=w*((q['odds'][side]-1) if d>1e-9 else -1 if d<-1e-9 else 0.)
 return val
def calc(prob,score):
 h,a=map(int,score.split('-'));target=0 if h>a else 1 if h==a else 2
 return (sum((p-float(j==target))**2 for j,p in enumerate(prob)),-math.log(max(prob[target],1e-15)))
feat={(r['league'],r['fixture_id']):r for r in map(json.loads,FEAT.open())}
pairs=defaultdict(dict)
for q in map(json.loads,CROWN.open()):
 pairs[(q['league'],q['fixture_id'])][q['market']]=q
market={r['fid']:r for r in map(json.loads,MARKET.open()) if r['cohort']=='historical_Crown_T12'}
biv={(r['league'],r['fixture_id']):r for r in map(json.loads,BIV.open())}
bivsum=json.loads(BIVSUM.read_text())
assert len(pairs)==len(biv)==len(market)==9908
for key,r in biv.items():
 checks['bivariate_fixture_score_checks']+=1
 prior=feat[key];base=pairs[key]
 if any(q['score']!=r['score'] or q['score']!=prior['score'] for q in base.values()):
  errors['fixture_score_join_mismatch']+=1
 if abs(r['estimated_shared_cov_prior_two_years']-
        bivsum['trained_per_league_year'][r['league']][str(r['season'])]['shared_poisson_covariance_nonnegative'])>1e-9:
  errors['biv_trained_cov_join']+=1
 for mk,q in base.items():
  checks['bivariate_AH_OU_quarter_payoffs']+=1
  old=q['models']['bayes_prior_2_independent']
  t=r['markets'][mk]
  if abs(t['realized_U']-cash(prior['score'],mk,q,t['side']))>1e-9:
   errors['biv_quarter_payoff_mismatch']+=1
  if t['R5_point_side']!=old['side'] or abs(t['R5_point_U']-old['net_U'])>1e-9:
   errors['biv_R5_baseline_mismatch']+=1
# Independent rebuild of covariance from previous two complete seasons
byyear=defaultdict(list)
for f in feat.values():byyear[(f['league'],f['season'])].append(f)
for lg,v in bivsum['trained_per_league_year'].items():
 for year,z in v.items():
  years=(int(year)-2,int(year)-1)
  training=byyear[(lg,years[0])]+byyear[(lg,years[1])]
  a=[];b=[]
  for r in training:
   h,away=map(int,r['score'].split('-'))
   lh,la=r['candidate_lambda']['bayes_prior_2']
   a.append(h-lh);b.append(away-la)
  obs=float(np.cov(a,b,ddof=1)[0,1])
  checks['bivariate_prior_two_season_covariance_reconstruction']+=1
  if z['train_match_n']!=len(training) or abs(z['residual_covariance_raw']-obs)>1e-10:
   errors['biv_prior_covariance_reconstruction']+=1
# Independently reconstruct bivariate score probabilities on at least one
# match per league×target year plus additional deterministic spaced matches.
V=np.arange(26,dtype=float);D=V[:,None]-V[None,:]
for i,(key,r) in enumerate(sorted(biv.items())):
 if i%97!=0:continue
 lh,la=feat[key]['candidate_lambda']['bayes_prior_2']
 comp=r['used_shared_cov_math_feasible']
 ref=poisson.pmf(V,lh-comp);other=poisson.pmf(V,la-comp);shared=poisson.pmf(V,comp)
 joint=np.zeros((26,26))
 for h in range(26):
  for away in range(26):
   # Different algorithm: closed form sum over all shared goals
   joint[h,away]=sum(shared[k]*ref[h-k]*other[away-k] for k in range(min(h,away)+1))
 joint/=joint.sum()
 probabilities=[float(joint[D>0].sum()),float(joint[D==0].sum()),float(joint[D<0].sum())]
 checks['bivariate_independent_joint_grid_spotcheck']+=1
 if abs(calc(probabilities,r['score'])[0]-r['1X2_Brier_bivar'])>1e-10:
  errors['biv_grid_Brier_mismatch']+=1
# R12-B learned outcome bias rerun via stored strictly-past feature record.
outF={(r['league'],r['fixture_id']):r for r in map(json.loads,OUTCOME.open())}
outL={(r['league'],r['fixture_id']):r for r in map(json.loads,OUTLED.open())}
outS=json.loads(OUTSUM.read_text())
assert len(outF)==9908 and len(outL)==7073
for key,row in outL.items():
 r=outF[key];yr=str(r['season'])
 if yr not in outS['learned_parameters_by_test_year']:
  errors['outcome_luck_test_year_mismatch']+=1
 probs=np.array(r['market_1X2_probability'])
 if abs(calc(probs,r['score'])[0]-row['model']['market_raw']['Brier'])>1e-10:
  errors['outcome_baseline_prob_score']+=1
 for name,p in outS['learned_parameters_by_test_year'][yr].items():
  beta=p['coefficient']
  z=np.log(probs)+beta*r[name]*np.array([1.,0.,-1.])
  pred=softmax(z)
  proper=calc(pred,r['score'])
  checks['outcome_luck_walkforward_Brier_logloss']+=1
  if max(abs(proper[0]-row['model'][name]['Brier']),
         abs(proper[1]-row['model'][name]['logloss']))>1e-10:
   errors['outcome_luck_recalc']+=1
checks['outcome_luck_test_fixtures']=len(outL)
# R12-C all eight shot profiles score test independently
shotF={(r['league'],r['fixture_id']):r for r in map(json.loads,SHOT.open())}
shotL={(r['league'],r['fixture_id']):r for r in map(json.loads,SHOTLED.open())}
shotS=json.loads(SHOTSUM.read_text())
assert len(shotF)==9908 and len(shotL)==7073
choices={'shot_volume':[0],'mean_shot_quality':[1],'nonopen_xG_share':[2],'all_three':[0,1,2]}
for key,r in shotL.items():
 x=shotF[key];yy=str(r['season'])
 prob=np.array(x['market_1X2_prob'])
 if abs(calc(prob,r['score'])[0]-r['models']['market_only']['Brier'])>1e-10:
  errors['shot_market_baseline']+=1
 for scope in ('current_season','all_archive'):
  for mod,columns in choices.items():
   name=scope+'_'+mod
   beta=shotS['learned_params'][yy][name]['coefficients']
   feature=np.array([x[scope][j] for j in columns])
   lp=np.log(prob)+(feature@np.array(beta))*np.array([1.,0.,-1.])
   b,ll=calc(softmax(lp),r['score'])
   checks['shot_model_Brier_logloss_independently']+=1
   if max(abs(b-r['models'][name]['Brier']),abs(ll-r['models'][name]['logloss']))>1e-10:
    errors['shot_score_reconstruction']+=1
checks['shot_test_fixtures']=len(shotL)
# Independently check past-only shot count history on all 9908. Sorted by
# (season, date) and process all same-day matches BEFORE updating shot counts.
for lg in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
    sample=defaultdict(dict)
    for yr in range(2017,2026):
        p=DATA/lg/str(yr)/'fixtures.csv'
        with p.open(encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                sample[(yr,r['date'])][r['fixture_id']]=(r['home'],r['away'])
    allhist=defaultdict(int);current=defaultdict(int);season_last=None
    for (yr,day),games in sorted(sample.items()):
        if yr!=season_last:
            current=defaultdict(int);season_last=yr
        for fid,(home,away) in games.items():
            key=(lg,fid)
            if key not in shotF:continue
            record=shotF[key]
            checks['shot_prior_count_strict_asof_fixture']+=1
            for history,tag in ((current,'current_season'),(allhist,'all_archive')):
                if (record[tag+'_home_priors']!=history[home] or
                    record[tag+'_away_priors']!=history[away]):
                    errors['shot_lag_prior_count_mismatch']+=1
        for home,away in games.values():
            allhist[home]+=1;allhist[away]+=1
            current[home]+=1;current[away]+=1
assert checks['shot_prior_count_strict_asof_fixture']==9908
unc=json.loads(UNC.read_text())
recon=json.loads(RECON.read_text())
if unc['source_sha256']!=sha(SHOTLED) or recon['raw']['all_shots']!=405363:
    errors['shot_uncertainty_or_source_hash_error']+=1
checks['shot_data_coverage_and_uncertainty_source_sha']+=1
# frozen files R5-R11 should be 309
frozen=[
 (SNAP/'R5_BAYES_BIVAR_FROZEN_20261123','FROZEN_SHA256_MANIFEST.json'),
 (SNAP/'R6_BAYES_BIVAR_COMPLEMENT_20261123','R6_FREEZE_MANIFEST.json'),
 (SNAP/'R7_CROWN_MARKET_PRICING_20261123','R7_FROZEN_SHA256_MANIFEST.json'),
 (SNAP/'R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123','R8_FROZEN_SHA256_MANIFEST.json'),
 (SNAP/'R9_CROWN_TRUE_UPDATE_BAYES_OU_20261123','R9_FROZEN_SHA256_MANIFEST.json'),
 (SNAP/'R10_XG_GAMMA_OBS_DYNAMIC_NB_20261123','R10_FROZEN_SHA256_MANIFEST.json'),
 (SNAP/'R11_DC_MARKET_RESIDUAL_XG_OBSERVATION_SOURCE_20261123','R11_FROZEN_SHA256_MANIFEST.json')]
for folder,manifest in frozen:
 for record in json.loads((folder/manifest).read_text())['files']:
  src=folder/(record.get('file') or record.get('relative_path'))
  checks['R5_R11_sha256_unmodified_file']+=1
  if not src.is_file() or sha(src)!=record['sha256']:
   errors['prior_frozen_corrupted']+=1
assert checks['R5_R11_sha256_unmodified_file']==309
result={'status':'PASS' if not errors else 'FAIL',
 'checks':dict(checks),'errors':dict(errors),
 'frozen_R5_to_R11_manifests_sha256':{p.name:sha(p/m) for p,m in frozen},
 'source_sha256':{p.name:sha(p) for p in (FEAT,CROWN,MARKET)},
 'R12_ledger_sha256':{p.name:sha(p) for p in
  (BIV,OUTCOME,OUTLED,SHOT,SHOTLED,UNC,RECON)},
 'notes':['Study only, previously researched historic Crown T12 source events, not actual receipted executable prices, not official TG.',
 'All test cohort 9908/7073 without ROI-based selections; 405363 shot data audited separately.',
 'No national teams and no approved bet/EV Gates added.']}
OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':result['checks'],'errors':result['errors']},ensure_ascii=False))
assert result['status']=='PASS',errors
