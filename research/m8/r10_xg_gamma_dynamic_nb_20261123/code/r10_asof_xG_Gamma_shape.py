#!/usr/bin/env python3
"""R10-1: estimate xG observation Gamma shape from PREVIOUS two complete
seasons within each domestic club league. No win/ROI used; no target season
statistic used in the target season's shape estimate.
This is a measurement-model research hypothesis, NOT a trading Gate.
"""
from collections import defaultdict,Counter
from pathlib import Path
import csv,json,hashlib,math,statistics
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r10_xg_observation_bayes_dynamic_20261123'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
OUT=HERE/'r10_prior_two_season_xg_Gamma_shape.json'
season=defaultdict(list);audit=Counter()
fpaths=[]
for league in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
    for path in sorted((DATA/league).glob('*/fixtures.csv')):
        yr=int(path.parent.name)
        fpaths.append(path)
        with path.open(encoding='utf-8-sig') as fd:
            for r in csv.DictReader(fd):
                if r['totals_unreliable'].lower()=='true':
                    audit['historical_fixture_xg_unreliable']+=1;continue
                if not r['home_published_xg'] or not r['away_published_xg']:
                    audit['historical_fixture_xg_missing']+=1;continue
                xh=float(r['home_published_xg']);xa=float(r['away_published_xg'])
                if xh<0 or xa<0:
                    audit['historical_negative_xG']+=1;continue
                season[(league,yr)].append({
                    'home':r['home'],'away':r['away'],'home_xg':xh,'away_xg':xa,
                    'day':r['date'],'fid':r['fixture_id']})
                audit['historical_fixture_xG_valid']+=1
def estimate(rows):
    observations=defaultdict(list)
    for r in rows:
        h,a=r['home'],r['away'];x,y=r['home_xg'],r['away_xg']
        observations[(h,'home','attack')].append(x)
        observations[(h,'home','defense')].append(y)
        observations[(a,'away','attack')].append(y)
        observations[(a,'away','defense')].append(x)
    den=num=0.
    n_groups=n_obs=0
    # Method-of-moments Gamma(shape=v): Var(X|theta)=theta²/shape.
    # Within-team/role observations isolate a fixed team-role average approx,
    # but club-strength drift is still mixed with measurement variance.
    for key,x in observations.items():
        if len(x)<2:continue
        m=sum(x)/len(x)
        den+=(len(x)-1)*m*m
        num+=sum((z-m)**2 for z in x)
        n_groups+=1
        n_obs+=len(x)
    if den<=0 or num<=0:raise RuntimeError(('Cannot estimate Gamma shape',den,num))
    var_ratio=num/den
    return {'shape':den/num,'variance_over_mean_sq':var_ratio,
       'team_venue_role_groups':n_groups,
       'xG_observations_in_groups':n_obs,
       'trained_match_count':len(rows),
       'estimator':'Pooled Gamma variance-over-team-venue-role-mean-squared, using only two PRIOR seasons. No outcome scores or ROI.'}
res={}
for lg in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
    res[lg]={}
    for yy in range(2019,2026):
        train=season[(lg,yy-2)]+season[(lg,yy-1)]
        assert len(train)>500,(lg,yy,len(train))
        v=estimate(train)
        v['train_seasons']=[yy-2,yy-1]
        v['evaluation_season']=yy
        res[lg][str(yy)]=v
ranges=[v['shape'] for lg in res.values() for v in lg.values()]
file_sha=hashlib.sha256()
for fp in fpaths:
    file_sha.update(fp.relative_to(DATA).as_posix().encode())
    file_sha.update(hashlib.sha256(fp.read_bytes()).digest())
out={'study':'R10_XG_GAMMA_OBSERVATION_SHAPE_PREVIOUS_TWO_SEASONS',
 'source_archive_manifest_SHA256':hashlib.sha256((DATA/'source_manifest.json').read_bytes()).hexdigest(),
 'input_fixture_listed_sha256':file_sha.hexdigest(),
 'scope':'Five domestic European club leagues; target seasons 2019-2025. Zero national teams.',
 'methodology':'Observations xG conditional on true latent team-venue attack/defense mean are Gamma(shape r, scale mean/r). Fit dispersion r from within-team same venue role xG fluctuations in the TWO completed seasons prior to each target season. Match score and betting profit NEVER enter dispersion training.',
 'by_league_season':res,'all_estimates':{'n':len(ranges),'min':min(ranges),'max':max(ranges),'mean':sum(ranges)/len(ranges)},
 'audit':dict(audit),
 'limitations':['Per-team role averages from two seasons are only approximate latent-strength controls, can confound drift/lineup with xG measurement error.',
 'Understat historical match xG publishing exact timestamps unverified; strict prior seasons do not guarantee historical API availability.',
 'Research-estimated gamma shape is a model hypothesis, not a new EV or volume Gate or official model setting.']}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'shape_range':out['all_estimates'],
  'by_league_first_last':{lg:{y:round(z['shape'],4) for y,z in d.items()} for lg,d in res.items()},
  'audit':dict(audit)},ensure_ascii=False))
