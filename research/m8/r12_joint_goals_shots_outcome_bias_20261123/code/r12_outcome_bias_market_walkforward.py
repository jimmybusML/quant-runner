#!/usr/bin/env python3
"""R12-B: Test outcome-bias hypothesis, versus Crown AH+OU implied 1X2 market.
Construct pre-match TEAM performance 'luck' = (actual goal difference -
xG goal difference) per prior match. Two feature histories:
(1) current season; (2) all prior matches in original Understat 2017+.
Build feature day by day using only strictly EARLIER dates, never target score
or target xG. Fit multinomial market logit correction using exact TWO prior
complete seasons 2019/20-2024/25 and evaluate full target year 2021-25.
No assumed threshold from literature, no ROI training, no new orders.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,hashlib,math
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import logsumexp
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r12_joint_goals_outcome_bias_20261123'
F5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
CROWN=F5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
FEATURES=HERE/'r12_outcome_bias_strict_past_xG_features_2019_2025.jsonl'
LEDGER=HERE/'r12_outcome_bias_market_increment_crossyear_2021_2025.jsonl'
SUM=HERE/'r12_outcome_bias_market_increment_crossyear_summary.json'
quotes={(r['league'],r['fixture_id']):r['fid'] for r in map(json.loads,CROWN.open()) if r['market']=='AH'}
market={r['fid']:r for r in map(json.loads,MARKET.open()) if r['cohort']=='historical_Crown_T12'}
assert len(quotes)==len(market)==9908
audit=Counter()
# each team accumulates all scored-conceded vs xG goal difference residuals;
# test features are known before the match, including prior current season games.
def prev_feature(net):
    count,amount=net
    return amount/count if count>0 else 0.  # zero-centered prior, not a selection Gate
rows=[]
for lg in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
    all_rows=[]
    for yr in range(2017,2026):
        p=DATA/lg/str(yr)/'fixtures.csv'
        with p.open(encoding='utf-8-sig') as fd:
            for r in csv.DictReader(fd):
                z={'league':lg,'season':yr,'date':r['date'],
                    'fixture_id':r['fixture_id'],'home':r['home'],'away':r['away'],
                    'score':r['score'],'xg_ok':r['totals_unreliable'].lower()!='true'
                       and bool(r['home_published_xg']) and bool(r['away_published_xg'])}
                if z['xg_ok']:
                    z['xg_h']=float(r['home_published_xg']);z['xg_a']=float(r['away_published_xg'])
                all_rows.append(z)
    all_rows.sort(key=lambda r:(r['date'],r['fixture_id']))
    history=defaultdict(lambda:[0,0.])
    season_history=defaultdict(lambda:[0,0.])
    last_season=None;groups=defaultdict(list)
    for row in all_rows:groups[(row['season'],row['date'])].append(row)
    for (season,date),group in sorted(groups.items()):
        if season!=last_season:
            season_history=defaultdict(lambda:[0,0.])
            last_season=season
        # compute ALL same-day match features before any same-day update
        for r in group:
            key=(lg,r['fixture_id'])
            home=r['home'];away=r['away']
            for prefix,hist in (('current_season',season_history),('full_archive',history)):
                a=prev_feature(hist[home]);b=prev_feature(hist[away])
                r[prefix+'_home_luck']=a
                r[prefix+'_away_luck']=b
                r[prefix+'_home_minus_away_luck']=a-b
                r[prefix+'_home_prior_xG_n']=hist[home][0]
                r[prefix+'_away_prior_xG_n']=hist[away][0]
            if key in quotes:
                assert key in quotes
                quote=market[quotes[key]]
                assert quote['score']==r['score'],(lg,r['fixture_id'])
                p=quote['models']['market_implied_Poisson']
                probabilities=[p['1X2_p_home'],p['1X2_p_draw'],p['1X2_p_away']]
                h,a=map(int,r['score'].split('-'))
                result=0 if h>a else 1 if h==a else 2
                rows.append({k:r[k] for k in ('fixture_id','league','season','date',
                     'score','current_season_home_luck','current_season_away_luck',
                     'current_season_home_minus_away_luck',
                     'current_season_home_prior_xG_n','current_season_away_prior_xG_n',
                     'full_archive_home_luck','full_archive_away_luck',
                     'full_archive_home_minus_away_luck',
                     'full_archive_home_prior_xG_n','full_archive_away_prior_xG_n')}|
                    {'market_1X2_probability':probabilities,'outcome':result})
                audit['Crown_join_fixture']+=1
        for r in group:
            if not r['xg_ok']:
                audit['source_fixture_invalid_xG_not_used_to_update_history']+=1
                continue
            h,a=map(int,r['score'].split('-'))
            d=(h-a)-(r['xg_h']-r['xg_a'])
            for hist in (history,season_history):
                hist[r['home']][0]+=1;hist[r['home']][1]+=d
                hist[r['away']][0]+=1;hist[r['away']][1]-=d
assert len(rows)==9908 and audit['Crown_join_fixture']==9908
with FEATURES.open('w') as f:
    for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
by_year=defaultdict(list)
for row in rows:by_year[row['season']].append(row)
def fit(rs,feature):
    # centered multinomial correction (+beta*x,0,-beta*x) around market logits
    prob=np.asarray([r['market_1X2_probability'] for r in rs])
    lpm=np.log(np.maximum(prob,1e-15))
    luck=np.asarray([r[feature] for r in rs],dtype=float)
    labels=np.asarray([r['outcome'] for r in rs],dtype=int)
    base=np.array([1.,0.,-1.])[None,:]
    def obj(b):
        logits=lpm+b*luck[:,None]*base
        logp=logits-logsumexp(logits,axis=1,keepdims=True)
        return float(-logp[np.arange(len(rs)),labels].mean())
    res=minimize_scalar(obj,method='brent',bracket=(-.4,0,.4),
       options={'xtol':1e-10,'maxiter':500})
    if not res.success or not math.isfinite(res.x):raise RuntimeError((feature,res))
    return {'coefficient':float(res.x),'train_n':len(rs),
            'train_logloss':float(res.fun),'train_seasons':sorted({r['season'] for r in rs}),
            'research_feature':feature}
def predict(row,feature,beta):
    luck=row[feature]
    logp=np.log(np.maximum(row['market_1X2_probability'],1e-15))
    logits=logp+beta*luck*np.array([1.,0.,-1.])
    return np.exp(logits-logsumexp(logits))
def score(prob,y):
    return {'Brier':float(sum((v-float(j==y))**2 for j,v in enumerate(prob))),
            'logloss':float(-math.log(max(prob[y],1e-15)))}
params={};results=[]
features=['current_season_home_minus_away_luck','full_archive_home_minus_away_luck']
for yr in range(2021,2026):
    train=by_year[yr-2]+by_year[yr-1]
    test=by_year[yr]
    params[str(yr)]={f:fit(train,f) for f in features}
    for row in test:
        z={'league':row['league'],'fixture_id':row['fixture_id'],'season':yr,
           'score':row['score'],'outcome':row['outcome'],
           'model':{'market_raw':score(row['market_1X2_probability'],row['outcome'])}}
        for f in features:
            ff=predict(row,f,params[str(yr)][f]['coefficient'])
            z['model'][f]=score(ff,row['outcome'])
            z['model'][f]['asof_feature']=row[f]
        results.append(z)
        audit['walkforward_test_fixture']+=1
assert len(results)==7073
def aggregate(sub):
    n=len(sub)
    if n==0:return {'n':0}
    d={'n':n}
    for label in ('market_raw',*features):
        v=[r['model'][label] for r in sub]
        d[label]={'Brier':round(sum(x['Brier'] for x in v)/n,7),
                  'logloss':round(sum(x['logloss'] for x in v)/n,7)}
        if label!='market_raw':
            d[label]['Brier_gain_vs_market']=round(d['market_raw']['Brier']-d[label]['Brier'],7)
    return d
summary={'study':'R12_OUTCOME_BIAS_TEAM_GOAL_DIFFERENCE_MINUS_XG_GOAL_DIFFERENCE_VS_CROWN',
 'source_SHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (CROWN,MARKET)},
 'feature':'Team actual goal difference minus xG goal difference per prior match, relative home versus away. Two research history definitions: current domestic season prior games and all archive since 2017. Source xG reliability enforced only for history update; all current 9908 target quotes evaluated, with no ROI/EV gate.',
 'method':'Each target date uses prior strictly EARLIER calendar dates, no target/same-day actual score or xG in feature. Fit one scalar market multinomial logit residual coefficient beta using only previous two completed seasons, optimize multiclass logloss, then predict all games in each target 2021–2025 season. Never fit ROI or choose betting cutoff.',
 'learned_parameters_by_test_year':params,
 'overall':aggregate(results),
 'by_year':{str(yr):aggregate([r for r in results if r['season']==yr]) for yr in range(2021,2026)},
 'by_league':{lg:aggregate([r for r in results if r['league']==lg]) for lg in sorted({r['league'] for r in results})},
 'audit':dict(audit),
 'limitations':['Hypothesis inspired by Flepp et al (2024) outcome bias in betting markets, but this simplified fortune feature and Crown-derived 1X2 markets are not their historical Matchbook exchange price specification, so this is NOT a direct paper replication.',
 'xG timing unknown, so strict prior match date does not prove the information was available before each historic quote.',
 'Crown historic T12 source event collected AFTER each match, not actual receipted odds, not tradable validation.',
 'Training and evaluation repeated historically known seasons, thus not newly blinded, no new bet strategy or order constraints.']}
with LEDGER.open('w') as f:
    for r in results:f.write(json.dumps(r,ensure_ascii=False)+'\n')
SUM.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':summary['overall'],
  'year_scores':{y:{k:round(v[k]['Brier_gain_vs_market'],7) for k in features} for y,v in summary['by_year'].items()},
  'coeffs':{y:{k:round(v['coefficient'],6) for k,v in p.items()} for y,p in params.items()},
  'audit':dict(audit)},ensure_ascii=False))
