#!/usr/bin/env python3
"""R10-C: actual dynamic per-team home/away attack/defense state-space baseline.
Use scalar log-xG Kalman random-walk filters for four venue-specific team
roles. Measurement noise R and process variance Q are estimated only from
the TWO finished seasons before target year, by within-team role first
differences and lag-one differences (no target scores, no ROI fitting).
First fit states on two prior seasons; then predict target games in temporal
order, with same-day updates after all predictions. Every R5 Crown cohort
game included, no betting EV gate or user trading rule.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,hashlib,math
import numpy as np
from scipy.stats import poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r10_xg_observation_bayes_dynamic_20261123'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
R5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
FEATURE=R5/'r5_bayes_bivar_asof_features_20261123.jsonl'
CROWN=R5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
LEDGER=HERE/'r10_asof_dynamic_logxG_Kalman_CrownT12_20261123.jsonl'
OUT=HERE/'r10_asof_dynamic_logxG_Kalman_CrownT12_summary_20261123.json'
EPS=.1
pfeatures={(r['league'],r['fixture_id']):r for r in map(json.loads,FEATURE.open())}
prices=defaultdict(dict)
for r in map(json.loads,CROWN.open()):
    prices[(r['league'],r['fixture_id'])][r['market']]=r
market={(r['league'],r['fid']):r for r in map(json.loads,MARKET.open()) if r['cohort']=='historical_Crown_T12'}
assert len(prices)==len(market)==9908
aud=Counter()
def loadseason(league,y):
    p=DATA/league/str(y)/'fixtures.csv'
    rows=[]
    with p.open(encoding='utf-8-sig') as fd:
        for z in csv.DictReader(fd):
            r=dict(z)
            if z['totals_unreliable'].lower()=='true' or not z['home_published_xg'] or not z['away_published_xg']:
                r['valid_xg']=False
            else:
                r['valid_xg']=True
                r['hxg']=float(z['home_published_xg'])
                r['axg']=float(z['away_published_xg'])
            rows.append(r)
    rows.sort(key=lambda z:z['date'])
    return rows
def histories(rows):
    series=defaultdict(list)
    for r in rows:
        if not r['valid_xg']:continue
        h,a=r['home'],r['away'];x=r['hxg'];y=r['axg']
        series[(h,'home','attack')].append((r['date'],math.log(x+EPS)))
        series[(h,'home','defense')].append((r['date'],math.log(y+EPS)))
        series[(a,'away','attack')].append((r['date'],math.log(y+EPS)))
        series[(a,'away','defense')].append((r['date'],math.log(x+EPS)))
    return series
def estimate_noise(prev):
    series=histories(prev)
    diffs=[];pairs=[]
    for vals in series.values():
        obs=[v for day,v in sorted(vals)]
        ds=np.diff(obs)
        diffs.extend(ds.tolist())
        pairs.extend(list(zip(ds[:-1],ds[1:])))
    assert len(diffs)>1000 and len(pairs)>1000
    var_d=np.var(diffs,ddof=1)
    pair=np.asarray(pairs,dtype=float)
    cov=float(np.cov(pair[:,0],pair[:,1])[0,1])
    R=max(0.,-cov)
    Q=max(0.,var_d+2*cov)
    if R<=0:
        # Can't construct an observable Kalman update with a zero measurement
        # variance. All studied league-years have R>0 in practice.
        raise RuntimeError(('invalid-R',var_d,cov))
    means=[]
    for entries in series.values():
        if len(entries)>=2:
            means.append(float(np.mean([v for dt,v in entries])))
    prior_var=float(np.var(means,ddof=1))
    if prior_var<=0:raise RuntimeError(('invalid-prior-variance',prior_var))
    hx=[r['hxg'] for r in prev if r['valid_xg']]
    ax=[r['axg'] for r in prev if r['valid_xg']]
    lgh=np.mean(hx);lga=np.mean(ax)
    return {'measurement_noise_logxG_R':float(R),
            'process_innovation_Q_per_team_venue_role_match':float(Q),
            'variance_difference_estimate':float(var_d),
            'difference_lag1_covariance':cov,
            'prior_team_role_log_variance':prior_var,
            'prior_league_home_mean_xG':float(lgh),
            'prior_league_away_mean_xG':float(lga),
            'train_games':len(prev),'trained_role_series':len(series),
            'train_diff_observations':len(diffs)}
def baseline(role,meta):
    lgmean=meta['prior_league_home_mean_xG'] if ((role[1]=='home' and role[2]=='attack') or (role[1]=='away' and role[2]=='defense')) else meta['prior_league_away_mean_xG']
    return math.log(lgmean+EPS)
def state_prior(states,key,meta):
    if key not in states:
        return baseline(key,meta),meta['prior_team_role_log_variance']+meta['process_innovation_Q_per_team_venue_role_match']
    mean,var=states[key]
    return mean,var+meta['process_innovation_Q_per_team_venue_role_match']
def val_role(states,key,meta):
    m,p=state_prior(states,key,meta)
    # With observation xG+EPS lognormal, E(log(xG+EPS)) corrected by R/2.
    raw=math.exp(m)-EPS
    # Mathematical positivity of Poisson intensity, not an eligible fixture filter.
    return max(1e-8,raw),p
def update_for_same_date(dayrows,states,meta):
    R=meta['measurement_noise_logxG_R']
    for r in dayrows:
        if not r['valid_xg']:continue
        h,a=r['home'],r['away'];x=r['hxg'];y=r['axg']
        observations=((h,'home','attack',x),(h,'home','defense',y),
                      (a,'away','attack',y),(a,'away','defense',x))
        for team,venue,side,value in observations:
            key=(team,venue,side)
            m,p=state_prior(states,key,meta)
            yy=math.log(value+EPS)+.5*R
            gain=p/(p+R)
            states[key]=(m+gain*(yy-m),(1-gain)*p)
def probs(lh,la):
    N=32
    x=np.arange(N+1,dtype=float)
    ph=poisson.pmf(x,lh);pa=poisson.pmf(x,la)
    ph/=ph.sum();pa/=pa.sum()
    p=np.outer(ph,pa)
    D=x[:,None]-x[None,:]
    return p,D
def pieces(v):
    q=round(float(v)*4)
    assert abs(q/4-float(v))<1e-9
    return [(float(v),1.)] if q%2==0 else [(math.floor(float(v)*2)/2.,.5),(math.ceil(float(v)*2)/2.,.5)]
def ev(p,D,m,quote):
    line=quote['line'];odds=quote['odds']
    T=np.arange(p.shape[0],dtype=float)[:,None]+np.arange(p.shape[1],dtype=float)[None,:]
    w=l=0.
    for leg,weight in pieces(line):
        field=D+leg if m=='AH' else T-leg
        w+=weight*float(p[field>1e-9].sum())
        l+=weight*float(p[field< -1e-9].sum())
    if m=='AH':
        return {'home':(odds['home']-1)*w-l,
                'away':(odds['away']-1)*l-w}
    return {'over':(odds['over']-1)*w-l,
            'under':(odds['under']-1)*l-w}
def cash(m,line,odds,side,score):
    h,a=map(int,score.split('-'))
    value=0.
    for leg,w in pieces(line):
        diff=h-a+leg if side=='home' else a-h-leg if side=='away' else h+a-leg if side=='over' else leg-h-a
        value+=w*((odds-1) if diff>1e-9 else -1 if diff<-1e-9 else 0)
    return value
results=[];params={}
for lg in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
    params[lg]={}
    for year in range(2019,2026):
        train=loadseason(lg,year-2)+loadseason(lg,year-1)
        test=loadseason(lg,year)
        meta=estimate_noise(train)
        meta['train_seasons']=[year-2,year-1]
        params[lg][str(year)]=meta
        states={}
        byday=defaultdict(list)
        for r in train:byday[r['date']].append((r,False))
        for r in test:byday[r['date']].append((r,True))
        for date in sorted(byday):
            day=byday[date]
            for raw,is_target in day:
                if not is_target:continue
                key=(lg,raw['fixture_id'])
                if key not in prices:
                    aud['not_in_old_Crown_9908_cohort']+=1
                    continue
                f=pfeatures[key]
                hh=raw['home'];aa=raw['away']
                atkH,pAH=val_role(states,(hh,'home','attack'),meta)
                defA,pDA=val_role(states,(aa,'away','defense'),meta)
                atkA,pAA=val_role(states,(aa,'away','attack'),meta)
                defH,pDH=val_role(states,(hh,'home','defense'),meta)
                lh=atkH*defA/f['league_mean_home_xg']
                la=atkA*defH/f['league_mean_away_xg']
                matrix,diff=probs(lh,la)
                rawp=[float(matrix[diff>0].sum()),float(matrix[diff==0].sum()),float(matrix[diff<0].sum())]
                hg,ag=map(int,f['score'].split('-'))
                label=0 if hg>ag else 1 if hg==ag else 2
                brier=sum((x-float(j==label))**2 for j,x in enumerate(rawp))
                fid=prices[key]['AH']['fid']
                prevmean=f['candidate_lambda']['bayes_prior_2']
                market_brier=market[(lg,fid)]['models']['market_implied_Poisson']['1X2_brier']
                row={'fixture_id':raw['fixture_id'],'league':lg,'season':year,'date':date,'score':f['score'],
                    'train_R':meta['measurement_noise_logxG_R'],
                    'train_Q':meta['process_innovation_Q_per_team_venue_role_match'],
                    'lambda_home':lh,'lambda_away':la,'p_1x2':rawp,'Brier':brier,
                    'logloss':-math.log(max(rawp[label],1e-15)),
                    'R7_Crown_market_Brier':market_brier,
                    'R5_Bayes_k2_lambda_home':prevmean[0],
                    'R5_Bayes_k2_lambda_away':prevmean[1],
                    'role_state_uncertainties_before_fixture':[pAH,pDA,pAA,pDH],
                    'markets':{}}
                assert prices[key]['AH']['score']==prices[key]['OU']['score']==f['score']
                for mk in ('AH','OU'):
                    q=prices[key][mk]
                    val=ev(matrix,diff,mk,q)
                    chosen=max(val,key=val.get)
                    net=cash(mk,q['line'],q['odds'][chosen],chosen,f['score'])
                    old=q['models']['bayes_prior_2_independent']
                    row['markets'][mk]={'side':chosen,'estimated_EV':val[chosen],
                        'actual_U':net,'R5_Bayes_k2_U':old['net_U'],
                        'R5_Bayes_k2_side':old['side']}
                    aud['market_contracts_processed']+=1
                results.append(row)
                aud['evaluated_fixtures']+=1
            update_for_same_date([rr for rr,flag in day],states,meta)
        print('dynamic filter',lg,year,'R',round(meta['measurement_noise_logxG_R'],4),
             'Q',round(meta['process_innovation_Q_per_team_venue_role_match'],4),flush=True)
assert len(results)==9908,(len(results),aud)
def agg(rows):
    n=len(rows)
    if not n:return {'n':0}
    result={'n':n,'Brier':round(sum(x['Brier'] for x in rows)/n,7),
       'logloss':round(sum(x['logloss'] for x in rows)/n,7),
       'Crown_market_Brier':round(sum(x['R7_Crown_market_Brier'] for x in rows)/n,7),
       'mean_Q':round(sum(x['train_Q'] for x in rows)/n,7),
       'mean_R':round(sum(x['train_R'] for x in rows)/n,7),
       'actual_goal_MSE':round(sum((sum(map(int,x['score'].split('-')))-x['lambda_home']-x['lambda_away'])**2 for x in rows)/n,7),
       'mean_expected_goals':round(sum(x['lambda_home']+x['lambda_away'] for x in rows)/n,7)}
    for mk in ('AH','OU'):
        a=[r['markets'][mk] for r in rows]
        U=sum(x['actual_U'] for x in a)
        result[mk]={'n':n,'net_U':round(U,5),'ROI_pct':round(100*U/n,5),
           'R5_Bayes_k2_U':round(sum(x['R5_Bayes_k2_U'] for x in a),5),
           'paired_delta_v_R5_k2_U':round(sum(x['actual_U']-x['R5_Bayes_k2_U'] for x in a),5),
           'change_of_side_vs_R5_k2':sum(x['side']!=x['R5_Bayes_k2_side'] for x in a)}
    return result
report={'study':'R10_DYNAMIC_TEAM_VENUE_ATTACK_DEFENSE_LOGXG_STATE_SPACE_KALMAN',
  'source_R5_SHA256':hashlib.sha256(FEATURE.read_bytes()).hexdigest(),
  'source_Crown_SHA256':hashlib.sha256(CROWN.read_bytes()).hexdigest(),
  'source_19490_2025_xg_csv_manifest_SHA256':hashlib.sha256((DATA/'source_manifest.json').read_bytes()).hexdigest(),
  'method':'Four dynamic log(xG+0.1) states per club separated by venue and attack/defense. Process Q and measurement R learned from first-difference variance and lag1 covariance of logxG in previous two completed seasons only. Filter state updated AFTER all same-day match predictions; full training seasons filtered first; carry over as-of past team strength. This is an observational hypothesis, NOT a fitted ROI strategy.',
  'model_hypotheses':{'logxg_offset':EPS,'Gaussian_Kalman_random_walk_per_team_role_match':True,
       'process_Q_nonnegative_variance_property':True,'R_pretrained_only':True,
       'starting_club_state_log_league_prior_from_train_years':True},
  'train_hyperparameters_by_league_season':params,'audit':dict(aud),
  'overall':agg(results),
  'by_league':{lg:agg([r for r in results if r['league']==lg]) for lg in sorted({r['league'] for r in results})},
  'by_season':{str(year):agg([r for r in results if r['season']==year]) for year in range(2019,2026)},
  'limitations':['xG historical provider published timestamp unknown; strict prior match-date does not prove price+xG availability.',
   'Kalman log(xG+.1) additive Gaussian observation and per-match Q are model research assumptions, not established football dynamics.',
   'If learned Q<0 at unconstrained moments, Q=0 as valid stochastic-process variance boundary, not fixture filter. Report all.',
   'Crown T12 source-event quote retrieved after games and not known executable; same 9908 repeatedly researched fixtures, not fresh blind trades.',
   'No national teams, no positive EV eligibility filter, no user-approved production changes.']}
with LEDGER.open('w') as f:
    for row in results:f.write(json.dumps(row,ensure_ascii=False)+'\n')
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':report['overall'],
                   'fitted_Q_zero_groups':sum(v['process_innovation_Q_per_team_venue_role_match']==0 for lg,vv in params.items() for v in vv.values()),
                   'audit':dict(aud)},ensure_ascii=False))
