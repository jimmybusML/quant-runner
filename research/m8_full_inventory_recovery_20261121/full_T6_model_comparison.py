"""Frozen experiment choices: full T6 inventory, 4 model methods, 2 training designs, annual and league diagnostics.
No search over test-year results to define filters or trade constraints.
"""
import gzip,json,collections,math
from pathlib import Path
import numpy as np
from xgboost import XGBClassifier,XGBRegressor
P=Path(__file__).resolve().parent
with gzip.open(P/'all_T6_features.jsonl.gz','rt') as fp: rows=[json.loads(s) for s in fp]
feat=list(rows[0]['features'])
core=['rate_h2h_win','rate_h2h_lose','hcap_mag','n_rest_day_net',
  'rate_seas_win_net','rate_seas_lose_net','scores_net','rank_proxy_season_points_rate_net',
  'rating_seas_proxy_net','rating_hist_net']
market=['hcap_mag','T6_home_odds','T6_away_odds','T6_no_vig_home_share',
        'T6_quote_age_hours','T6_ou_line','T6_ou_odds_over','T6_ou_odds_under',
        'T6_1x2_home','T6_1x2_draw','T6_1x2_away','T6_1x2_missing']
models={'jack10_binary':(core,'class'),'market_binary':(market,'class'),
        'jack10_direct_cashflow':(core,'cashflow'),
        'market_history_direct_cashflow':(feat,'cashflow')}
years=np.array([r['year'] for r in rows])
y=np.array([int((r['hg']-r['ag'])+r['home_line']>0) for r in rows],dtype=int)
cashdiff=np.array([r['home_U']-r['away_U'] for r in rows],dtype=np.float32)
out=collections.defaultdict(lambda:{'n':0,'net_u':0.,'binary_sim180_u':0.,'binary_hit':0})
predrows=[];fitmeta={}
for model,(cols,kind) in models.items():
 X=np.array([[r['features'][k] for k in cols] for r in rows],dtype=np.float32)
 for window in ['fixed_2019_23','annual_forward']:
  for year in (2024,2025,2026):
   test=years==year;train=years<(2024 if window.startswith('fixed') else year)
   args=dict(n_estimators=160,max_depth=3,learning_rate=.05,subsample=1,
             colsample_bytree=1,reg_lambda=5,random_state=20261121,n_jobs=2,tree_method='hist')
   est=XGBClassifier(**args,objective='binary:logistic',eval_metric='logloss') if kind=='class' else XGBRegressor(**args,objective='reg:squarederror')
   est.fit(X[train],y[train] if kind=='class' else cashdiff[train])
   pred=est.predict_proba(X[test])[:,1] if kind=='class' else est.predict(X[test])
   fitmeta[f'{model}|{window}|{year}']={'train_n':int(train.sum()),'test_n':int(test.sum()),'feature_count':len(cols),
     'importances':dict(sorted(zip(cols,map(float,est.feature_importances_)),key=lambda z:-z[1])[:10])}
   kk=np.flatnonzero(test)
   for i,sc in zip(kk,pred):
    r=rows[i];side='home' if float(sc)>=(.5 if kind=='class' else 0.) else 'away'
    pnl=float(r[side+'_U']);hit=(y[i]==int(side=='home'));sim=.8 if hit else -1.
    p={'fid':r['fid'],'year':r['year'],'league':r['league'],'is_m8_member':r['is_m8_member'],
       'model':model,'window':window,'score':round(float(sc),7),'side':side,
       'net_u':pnl,'binary_sim180_u':sim,'home_U':r['home_U'],'away_U':r['away_U'],
       'line':r['home_line'],'home_odds':r['home_odds'],'away_odds':r['away_odds']}
    predrows.append(p)
    for cohort in ('all', 'frozen' if r['is_m8_member'] else 'outside'):
     for group in (str(year),'overall'):
      a=out[(model,window,cohort,group)];a['n']+=1;a['net_u']+=pnl;a['binary_sim180_u']+=sim;a['binary_hit']+=hit
   print('COMPARED',model,window,year,'N',int(test.sum()),flush=True)
def pack(v):return {'n':v['n'],'net_u':round(v['net_u'],3),'ROI_pct':round(100*v['net_u']/v['n'],4),
                       'binary_accuracy_pct':round(100*v['binary_hit']/v['n'],3),
                       'binary_sim180_ROI_pct':round(100*v['binary_sim180_u']/v['n'],4)}
result={'methods':{k:{'features':cols,'type':kind} for k,(cols,kind) in models.items()},
        'method_settings':'Experimental fixed XGBoost settings, not product rule or optimized parameters',
        'cohort_note':'All 41923 T6 Crown quotes retained for features; outside only for reporting. 2024-26 28736 all / 22120 outside.',
        'fit':fitmeta,'results':{'|'.join(k):pack(v) for k,v in out.items()}}
(P/'full_T6_model_comparison_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
with gzip.open(P/'full_T6_model_comparison_ledger.jsonl.gz','wt') as f:
 for r in predrows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
for model in models:
 for window in ('fixed_2019_23','annual_forward'):
  print('RESULT',model,window,'OUTSIDE',result['results']['|'.join((model,window,'outside','overall'))],flush=True)
