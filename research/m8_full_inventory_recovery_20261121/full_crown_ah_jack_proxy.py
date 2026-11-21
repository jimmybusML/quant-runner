"""Full-inventory Crown T-6 AH research. No production writes.
All T6 priced FIDs are retained regardless of optional player/formation features.
Historical FT timing: kickoff+48h *research proxy*, not verified actual receipt.
J1 is a Jack-inspired feature proxy, NOT a faithful 14-feature reproduction.
"""
import json,gzip,collections,math,datetime,hashlib
from pathlib import Path
import numpy as np
from xgboost import XGBClassifier
P=Path(__file__).resolve().parent
SOURCE=P.parent/'jack_crown_round1_20261121'
read=lambda name:[json.loads(s) for s in (SOURCE/name).open()]
def dt(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def write_json(name,obj):(P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
def cash(row,side):
    # Independently split quarter-handicap with correct away sign; compare existing audited cash.
    line=float(row['al'])*(1 if side=='home' else -1)
    goal=(row['hg']-row['ag'])*(1 if side=='home' else -1)
    odds=float(row['ah'] if side=='home' else row['aa'])
    def leg(l):
        diff=goal+l
        return odds-1 if diff>1e-8 else (-1.0 if diff < -1e-8 else 0.0)
    return (leg(line-.25)+leg(line+.25))/2 if int(round(line*4))%2 else leg(line)
def main():
    q=[r for r in read('unified_quotes.jsonl') if r['T']==6]
    history=read('history.jsonl')
    histories=sorted(((dt(x['ko'])+datetime.timedelta(hours=48),x) for x in history),key=lambda z:z[0])
    for r in q:r['_cut']=dt(r['prediction_cutoff_utc'])
    q.sort(key=lambda r:(r['_cut'],r['fid']))
    # Historic FTs only used once their kickoff+48h has passed. This is an explicitly
    # labeled *counterfactual availability assumption*, never a production rule.
    team=collections.defaultdict(lambda:dict(elo=1000.0,n=0,w=0,l=0,gf=0,ga=0,points=0,last=None,form=collections.deque(maxlen=10),seasons={}))
    h2h=collections.defaultdict(lambda:[0,0,0])
    i=0;features=[];stats=collections.Counter()
    for r in q:
        cutoff=r['_cut']
        while i<len(histories) and histories[i][0] <= cutoff:
            _,h=histories[i];i+=1
            a,b=h['home_id'],h['away_id']
            if a==b:continue
            home,away=team[a],team[b];hg,ag=int(h['hg']),int(h['ag'])
            outcome=1 if hg>ag else 0 if hg<ag else .5
            p=1/(1+10**((away['elo']-home['elo'])/400))
            change=24*(outcome-p);home['elo']+=change;away['elo']-=change
            year=dt(h['ko']).year
            for s,gf,ga in ((home,hg,ag),(away,ag,hg)):
                s['n']+=1;s['w']+=gf>ga;s['l']+=gf<ga;s['gf']+=gf;s['ga']+=ga
                s['points']+=3 if gf>ga else 1 if gf==ga else 0
                s['last']=dt(h['ko'])
                s['form'].append((gf-ga,gf,ga))
                ss=s['seasons'].setdefault(year,[0,0,0,0,0,0])
                ss[0]+=1;ss[1]+=gf>ga;ss[2]+=gf<ga;ss[3]+=3 if gf>ga else 1 if gf==ga else 0;ss[4]+=gf;ss[5]+=gf-ga
            z=h2h[a,b];z[0]+=1;z[1]+=hg>ag;z[2]+=hg<ag
            z=h2h[b,a];z[0]+=1;z[1]+=ag>hg;z[2]+=ag<hg
        a,b=team[r['home_id']],team[r['away_id']]
        year=r['year'];sa=a['seasons'].get(year,[0]*6);sb=b['seasons'].get(year,[0]*6)
        hh=h2h[r['home_id'],r['away_id']]
        def avg(seq,j):return sum(x[j] for x in seq)/len(seq) if seq else 0.
        def rest(s):return min(60.,(cutoff-s['last']).total_seconds()/86400) if s['last'] else 0.
        def safe(s,j):return s[j]/s[0] if s[0] else 0.
        # Feature proxies are grounded in past dated results, never target-match FT.
        # No synthetic xG for absent original 4 Poisson features.
        f={
          'rate_h2h_win':safe(hh,1),'rate_h2h_lose':safe(hh,2),
          'hcap_mag':-float(r['al']),
          'n_rest_day_net':rest(a)-rest(b),
          'rate_seas_win_net':safe(sa,1)-safe(sb,1),
          'rate_seas_lose_net':safe(sa,2)-safe(sb,2),
          'scores_net':sa[3]-sb[3],
          'rank_proxy_season_points_rate_net':safe(sa,3)-safe(sb,3),
          'rating_seas_proxy_net':(sa[5]/sa[0] if sa[0] else 0)-(sb[5]/sb[0] if sb[0] else 0),
          'rating_hist_net':a['elo']-b['elo'],
          'past_goal_diff_last10_net':avg(a['form'],0)-avg(b['form'],0),
          'past_goals_for_last10_net':avg(a['form'],1)-avg(b['form'],1),
          'past_goals_against_last10_net':avg(a['form'],2)-avg(b['form'],2),
          'history_count_home':a['n'],'history_count_away':b['n'],
          'season_count_home':sa[0],'season_count_away':sb[0],
          'past_h2h_count':hh[0],
          'T6_home_odds':float(r['ah']),'T6_away_odds':float(r['aa']),
          'T6_no_vig_home_share':r['aa']/(r['ah']+r['aa']),
          'T6_quote_age_hours':float(r['age_ah']),
          'T6_ou_line':float(r['ol']),
          'T6_ou_odds_over':float(r['oo']),
          'T6_ou_odds_under':float(r['ou']),
          'T6_1x2_home':float((r.get('p1x2') or [0.,0.,0.])[0]),
          'T6_1x2_draw':float((r.get('p1x2') or [0.,0.,0.])[1]),
          'T6_1x2_away':float((r.get('p1x2') or [0.,0.,0.])[2]),
          'T6_1x2_missing':int(not bool(r.get('p1x2')))
        }
        row={'fid':r['fid'],'year':year,'league':r['league'],'ko':r['ko'],'cutoff':r['prediction_cutoff_utc'],
             'home_line':r['al'],'home_odds':r['ah'],'away_odds':r['aa'],
             'hg':r['hg'],'ag':r['ag'],'history_ingested_n':i,
             'home_historical_n':a['n'],'away_historical_n':b['n'],
             'is_m8_member':r['is_m8_member'],'features':f}
        # Binary Jack-style direction; push maps away as a *research approximation*
        # distinct from five-state real AH settlement.
        s=(r['hg']-r['ag'])+r['al']
        row['binary_label_home_cover']=1 if s>0 else 0
        row['home_U']=r['home_U'];row['away_U']=r['away_U']
        for side in ('home','away'):
            audited=float(r[side+'_U']); independently=cash(r,side)
            if abs(audited-independently)>1e-7:
                stats['settlement_disagree']+=1
                if stats['settlement_disagree']<=3:print('MISMATCH',r['fid'],side,audited,independently,flush=True)
        features.append(row);stats['quotes']+=1;stats['outside']+=not r['is_m8_member']
    features.sort(key=lambda x:(x['year'],x['ko'],x['fid']))
    with gzip.open(P/'all_T6_features.jsonl.gz','wt') as fp:
        for r in features:fp.write(json.dumps(r,ensure_ascii=False)+'\n')
    print('FEATURES_COMPLETED',len(features),dict(stats),flush=True)
    keys=list(features[0]['features']);X=np.array([[r['features'][k] for k in keys] for r in features],dtype=np.float32)
    y=np.array([r['binary_label_home_cover'] for r in features]);years=np.array([r['year'] for r in features])
    if not np.isfinite(X).all():raise ValueError('non-finite features')
    models={}
    preds={}
    # Two explicit research variants: J1 fixed historic training, and J3 refit
    # annually with prior calendar years only, not production thresholds.
    for variant in ['J1_fixed_2019_23','J3_annual_forward']:
        probs=np.full(len(features),np.nan)
        for year in (2024,2025,2026):
            train=(years< (2024 if variant.startswith('J1') else year))
            test=years==year
            if not train.any():continue
            classifier=XGBClassifier(n_estimators=160,max_depth=3,learning_rate=.05,
              subsample=1,colsample_bytree=1,reg_lambda=5,objective='binary:logistic',
              eval_metric='logloss',random_state=20261121,n_jobs=2,tree_method='hist')
            classifier.fit(X[train],y[train])
            probs[test]=classifier.predict_proba(X[test])[:,1]
            models[f'{variant}_{year}']={'train_n':int(train.sum()),
              'test_n':int(test.sum()),'train_max_year':int(years[train].max()),
              'feature_importances':dict(sorted(zip(keys,map(float,classifier.feature_importances_)),key=lambda z:-z[1])[:12])}
            print('MODEL_DONE',variant,year,'train',int(train.sum()),'test',int(test.sum()),flush=True)
        preds[variant]=probs
    records=[];results={}
    for variant,prob in preds.items():
        d=collections.defaultdict(lambda:dict(n=0,sim180_u=0.,Crown_net_u=0.,Crown_home_u=0.,Crown_away_u=0.,wins_binary=0,disagree_side=0))
        for k,r in enumerate(features):
            if r['year']<2024:continue
            v=float(prob[k]);side='home' if v>=.5 else 'away';lab=r['binary_label_home_cover']==(side=='home')
            pnl=float(r['home_U'] if side=='home' else r['away_U'])
            row={'fid':r['fid'],'year':r['year'],'league':r['league'],'variant':variant,
              'is_m8_member':r['is_m8_member'],'side':side,'prob_home':round(v,7),
              'binary_target_home':r['binary_label_home_cover'],
              'binary_sim180_u':.8 if lab else -1.,'Crown_net_u':pnl,
              'home_U':r['home_U'],'away_U':r['away_U'],
              'line':r['home_line'],'home_odds':r['home_odds'],'away_odds':r['away_odds'],
              'ko':r['ko'],'cutoff':r['cutoff'],'historical_quote_not_live_receipt':True}
            records.append(row)
            for cohort in ('all','outside' if not r['is_m8_member'] else 'frozen'):
                s=d[(cohort,r['year'])];s['n']+=1;s['sim180_u']+=row['binary_sim180_u'];s['Crown_net_u']+=pnl;s['wins_binary']+=lab
            for cohort in ('all','outside' if not r['is_m8_member'] else 'frozen'):
                s=d[(cohort,'overall')];s['n']+=1;s['sim180_u']+=row['binary_sim180_u'];s['Crown_net_u']+=pnl;s['wins_binary']+=lab
        results[variant]={str(k):dict(n=v['n'],
          binary_accuracy_pct=round(100*v['wins_binary']/v['n'],4),
          binary_sim180_U=round(v['sim180_u'],4),
          binary_sim180_ROI_pct=round(100*v['sim180_u']/v['n'],4),
          Crown_net_U=round(v['Crown_net_u'],4),
          Crown_ROI_pct=round(100*v['Crown_net_u']/v['n'],4)) for k,v in d.items()}
    with gzip.open(P/'all_T6_predictions_2024_26.jsonl.gz','wt') as fp:
        for r in records:fp.write(json.dumps(r,ensure_ascii=False)+'\n')
    report={'sample':{'historical_results':len(history),'T6_total':len(features),
       'T6_2024_26':sum(x['year']>=2024 for x in features),
       'T6_2024_26_outside':sum(x['year']>=2024 and not x['is_m8_member'] for x in features),
       'T6_2024_26_frozen':sum(x['year']>=2024 and x['is_m8_member'] for x in features),
       'five_state_disagreements':stats['settlement_disagree']},
       'assumptions':['Jack-inspired proxy, missing 4 Poisson xG features and original exact season/ranking; not faithful Jack J1',
          'kickoff+48h FT availability is a research counterfactual, not verified',
          'Crown historical source-event T6 quotes; not actual pre-kickoff HTTP receipt',
          'Frozen original8 excluded only for separate incremental return, no training gate',
          '2024-26 results explored historically, not untouched OOS'],
       'features':keys,'fits':models,'results':results}
    write_json('full_T6_jack_proxy_summary.json',report)
    print('RESEARCH_COMPLETE',json.dumps(report['sample']),flush=True)
    for variant in results:
        for x in ('outside','all'):
            print('SUMMARY',variant,x,results[variant][str((x,'overall'))],flush=True)
if __name__=='__main__':main()
