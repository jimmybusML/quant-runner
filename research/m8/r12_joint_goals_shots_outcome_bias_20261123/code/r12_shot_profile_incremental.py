#!/usr/bin/env python3
"""R12-C: shot composition as-of from Understat shots, studied as new
information beyond Crown AH+OU implied 1X2 market, strict prior game date.
All raw shots from 2017-2025 five domestic club leagues; current-season
and all-prior-archive research features: shot volume/game, mean xG/shot,
share of xG from non-open play (situation != OpenPlay).
Train single-variable/3-variate softmax market correction on previous TWO
completed years; test 2021-25 full five-year 7073 fixture cohort.
No target-shot data in features, no ROI gates. Goal is incremental information.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,hashlib,math
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r12_joint_goals_outcome_bias_20261123'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
F5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
CROWN=F5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
M=R7/'r7_market_implied_2market_20261123.jsonl'
ROW=HERE/'r12_understat_shot_profile_prior_features_2019_2025.jsonl'
LEDGER=HERE/'r12_understat_shot_profile_Crown_increment_2021_2025.jsonl'
SUMMARY=HERE/'r12_understat_shot_profile_Crown_increment_summary.json'
quote={(r['league'],r['fixture_id']):r['fid'] for r in map(json.loads,CROWN.open()) if r['market']=='AH'}
market={r['fid']:r for r in map(json.loads,M.open()) if r['cohort']=='historical_Crown_T12'}
assert len(quote)==len(market)==9908
audit=Counter()
shot_fingerprint=hashlib.sha256()
source_file_count=0
team_features=[]
# State [played, shot_count, xG_all, xG_nonopen]
def fea(x):
 n,s,allx,nonx=x
 return [s/n if n else 0., allx/s if s else 0., nonx/allx if allx else 0.]
def compare(home,away):
 return [a-b for a,b in zip(fea(home),fea(away))]
for league in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
    games=[]
    for season in range(2017,2026):
        p=DATA/league/str(season)/'fixtures.csv'
        shots=DATA/league/str(season)/'shots.csv'
        shot_fingerprint.update(shots.relative_to(DATA).as_posix().encode())
        shot_fingerprint.update(hashlib.sha256(shots.read_bytes()).digest())
        source_file_count+=1
        agg=defaultdict(lambda:[[0.,0.,0.],[0.,0.,0.]])
        with shots.open(encoding='utf-8-sig') as fd:
            for s in csv.DictReader(fd):
                side=0 if s['side']=='h' else 1
                value=float(s['understat_xg'])
                if value<0:raise ValueError('negative shot xG')
                current=agg[s['fixture_id']][side]
                current[0]+=1
                current[1]+=value
                if s['situation']!='OpenPlay':current[2]+=value
                audit['raw_understat_shots']+=1
        with p.open(encoding='utf-8-sig') as fd:
            for raw in csv.DictReader(fd):
                k=(league,raw['fixture_id'])
                z={'league':league,'season':season,'date':raw['date'],
                    'fixture_id':raw['fixture_id'],'home':raw['home'],'away':raw['away'],
                    'score':raw['score'],'team_shots':agg[raw['fixture_id']]}
                if raw['home_published_xg'] and raw['away_published_xg'] and raw['totals_unreliable'].lower()!='true':
                    for side,v in ((0,float(raw['home_published_xg'])),(1,float(raw['away_published_xg']))):
                        discrepancy=abs(v-agg[raw['fixture_id']][side][1])
                        if discrepancy>.1:audit['published_xg_shots_difference_over_0p1']+=1
                        if discrepancy>.01:audit['published_xg_shots_difference_over_0p01']+=1
                        audit['published_xG_comparable_team_sides']+=1
                else:audit['match_xG_unreliable_source']+=1
                if k in quote:z['market_fid']=quote[k]
                games.append(z)
    days=defaultdict(list)
    for r in games:days[(r['season'],r['date'])].append(r)
    archive=defaultdict(lambda:[0.,0.,0.,0.])
    current=defaultdict(lambda:[0.,0.,0.,0.])
    lastseason=None
    for (season,date),group in sorted(days.items()):
        if lastseason!=season:
            current=defaultdict(lambda:[0.,0.,0.,0.])
            lastseason=season
        for game in group:
            if 'market_fid' not in game:continue
            h,a=game['home'],game['away']
            key=(league,game['fixture_id'])
            oldmarket=market[game['market_fid']]
            if oldmarket['score']!=game['score']:raise ValueError(('score mismatch',key))
            prob=oldmarket['models']['market_implied_Poisson']
            pm=[prob['1X2_p_home'],prob['1X2_p_draw'],prob['1X2_p_away']]
            hg,ag=map(int,game['score'].split('-'))
            y=0 if hg>ag else 1 if hg==ag else 2
            team_features.append({'league':league,'season':season,'fixture_id':game['fixture_id'],
              'date':date,'score':game['score'],'outcome':y,
              'market_1X2_prob':pm,
              'current_season':compare(current[h],current[a]),
              'all_archive':compare(archive[h],archive[a]),
              'current_season_home_priors':current[h][0],
              'current_season_away_priors':current[a][0],
              'all_archive_home_priors':archive[h][0],
              'all_archive_away_priors':archive[a][0]})
        # After all same-day outcomes have been forecast, update shot profile
        for game in group:
            for team,side in ((game['home'],0),(game['away'],1)):
                shots,xg,nonopen=game['team_shots'][side]
                for state in (current,archive):
                    state[team][0]+=1
                    state[team][1]+=shots
                    state[team][2]+=xg
                    state[team][3]+=nonopen
assert len(team_features)==9908
with ROW.open('w') as f:
    for r in team_features:f.write(json.dumps(r,ensure_ascii=False)+'\n')
byyear=defaultdict(list)
for r in team_features:byyear[r['season']].append(r)
feature_names=['volume_shots_per_match','quality_xg_per_shot','nonopen_xg_share']
def makeX(rows,scope,cols):
    return np.asarray([[r[scope][i] for i in cols] for r in rows],float)
def fit(rows,scope,cols):
    m=np.array([r['market_1X2_prob'] for r in rows])
    logm=np.log(np.maximum(m,1e-15))
    y=np.array([r['outcome'] for r in rows],dtype=int)
    X=makeX(rows,scope,cols)
    model_diff=np.array([1.,0.,-1.])
    def objective(beta):
        score=logm+(X@beta)[:,None]*model_diff
        logp=score-logsumexp(score,axis=1,keepdims=True)
        prob=np.exp(logp)
        loss=-logp[np.arange(len(rows)),y].mean()
        residual=np.sum((prob-np.eye(3)[y])*model_diff,axis=1)
        grad=(X.T@residual)/len(rows)
        return float(loss),grad
    start=np.zeros(len(cols))
    sol=minimize(objective,start,jac=True,method='BFGS',options={'gtol':1e-9,'maxiter':600})
    obj,grad=objective(sol.x)
    if np.max(np.abs(grad))>1e-5 or not np.all(np.isfinite(sol.x)):
        raise RuntimeError((scope,cols,sol.message,grad))
    return {'coefficients':sol.x.tolist(),'train_n':len(rows),
        'train_years':sorted({r['season'] for r in rows}),
        'train_logloss':obj,'grad_inf':float(np.max(np.abs(grad))),
        'feature_columns':[feature_names[i] for i in cols]}
def pred(row,scope,cols,coeff):
    x=np.array([row[scope][i] for i in cols])
    marketlog=np.log(np.maximum(row['market_1X2_prob'],1e-15))
    z=marketlog+float(x@np.asarray(coeff))*np.array([1.,0.,-1.])
    return np.exp(z-logsumexp(z))
def score(p,y):
    return {'Brier':float(sum((v-(j==y))**2 for j,v in enumerate(p))),
        'logloss':-math.log(max(p[y],1e-15))}
mods={f'{scope}_{name}':(scope,cols) for scope in ('current_season','all_archive')
      for name,cols in [('shot_volume',[0]),('mean_shot_quality',[1]),('nonopen_xG_share',[2]),
                        ('all_three',[0,1,2])]}
params={};results=[]
for year in range(2021,2026):
    train=byyear[year-2]+byyear[year-1]
    test=byyear[year]
    if len(test)<1300:raise RuntimeError('incomplete test season')
    params[str(year)]={}
    for k,(scope,cols) in mods.items():params[str(year)][k]=fit(train,scope,cols)
    for r in test:
        o={'league':r['league'],'season':r['season'],'fixture_id':r['fixture_id'],'score':r['score'],
           'models':{'market_only':score(r['market_1X2_prob'],r['outcome'])}}
        for k,(scope,cols) in mods.items():
            p=pred(r,scope,cols,params[str(year)][k]['coefficients'])
            o['models'][k]=score(p,r['outcome'])
        results.append(o)
assert len(results)==7073
def agg(rows):
    n=len(rows)
    if n==0:return {'n':0}
    out={'n':n}
    for label in results[0]['models']:
        a=[r['models'][label] for r in rows]
        out[label]={'Brier':round(sum(x['Brier'] for x in a)/n,7),
                    'logloss':round(sum(x['logloss'] for x in a)/n,7)}
    return out
report={'study':'R12_ASOF_UNDERSTAT_SHOT_COMPOSITION_VS_CROWN_MARKET_RESIDUAL',
 'data_source':'5 major European domestic club leagues, all 45 league seasons Understat shots 2017-2025. Shot situation, count and understat xG built into strictly previous-date features.',
 'original_Crown_quote_SHA256':hashlib.sha256(CROWN.read_bytes()).hexdigest(),
 'shot_files_listed_SHA256':shot_fingerprint.hexdigest(),
 'source_shot_file_count':source_file_count,
 'feature_definitions':feature_names,
 'method':'On each fixture use home team minus away team prior per-match shot count, mean shot xG, and non-open-play xG share (separately current season and all prior archive). On each date process all score predictions before updating any team shot profile. Fit scalar or three-component market multinomial residual correction on two fully previous seasons, optimize proper multiclass logloss, test all 2021-2025 fixtures, no trade ROI or selection gates.',
 'overall':agg(results),
 'by_season':{str(y):agg([r for r in results if r['season']==y]) for y in range(2021,2026)},
 'by_league':{lg:agg([r for r in results if r['league']==lg]) for lg in sorted({r['league'] for r in results})},
 'learned_params':params,'audit':dict(audit),
 'limitations':['Per-shot data likely published following each game; match-date asof alone does not prove original data were available before following match at original Crown T12 time.',
   'Goal count in target fixture never used in past features. However underlying old historical Crown odds were collected after result, not true pregame receipts.',
   'Shot profile averages may confound opponent, game-state, injuries, pace, and lineups, and are not full game-state adjusted xG or the current 2026 paper replication.',
   'Crown probability benchmark is derived from its original AH/OU prices, not independent exchange 1X2 price.',
   'All 9908 match forecast features scored, test 7073 full seasons; no venue/league filters or trading rules; national teams excluded.']}
with LEDGER.open('w') as f:
    for r in results:f.write(json.dumps(r,ensure_ascii=False)+'\n')
SUMMARY.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':report['overall'],'audit':report['audit'],
   'by_year_selected':{y:{n:round(x[n]['Brier']-x['market_only']['Brier'],7) for n in
       ('current_season_all_three','all_archive_all_three')} for y,x in report['by_season'].items()}},ensure_ascii=False))
