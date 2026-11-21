"""62 priced-league Crown T6 research, no external-feature completeness filter.
Historic results and source-event odds only. Diagnostics not production rules.
"""
import gzip,json,collections
from pathlib import Path
import numpy as np
from xgboost import XGBClassifier,XGBRegressor
P=Path(__file__).resolve().parent
with gzip.open(P/'full_priced_T6_original_and_expanded.jsonl.gz','rt') as f:rows=[json.loads(s) for s in f]
rows.sort(key=lambda x:(x['year'],x['ko'],x['fid']))
leagues=sorted({r['league'] for r in rows});mapidx={x:i for i,x in enumerate(leagues)}
year=np.array([r['year'] for r in rows]);yin=np.array([int((r['hg']-r['ag'])+r['line']>0) for r in rows],dtype=np.int8)
target=np.array([r['home_U']-r['away_U'] for r in rows])
base=np.array([[r['line'],abs(r['line']),r['home_odds'],r['away_odds'],
                r['away_odds']/(r['home_odds']+r['away_odds'])] for r in rows],dtype=np.float32)
withleague=np.concatenate([base,np.eye(len(leagues),dtype=np.float32)[[mapidx[r['league']] for r in rows]]],axis=1)
models={'price_only_binary':(base,'binary'),'price_only_cashflow':(base,'cashflow'),
        'price_league_binary':(withleague,'binary'),'price_league_cashflow':(withleague,'cashflow')}
fitted={};results=collections.defaultdict(lambda:{'n':0,'pnl':0.,'wins_binary':0})
ledger=[]
for m,(X,kind) in models.items():
 for trainmode in ('fixed_2019_23','annual_forward'):
  for yr in [2024,2025,2026]:
   train=year<(2024 if trainmode=='fixed_2019_23' else yr);test=year==yr
   kw=dict(n_estimators=150,max_depth=3,learning_rate=.06,reg_lambda=6,random_state=20261121,n_jobs=2,tree_method='hist')
   est=XGBClassifier(**kw,objective='binary:logistic') if kind=='binary' else XGBRegressor(**kw,objective='reg:squarederror')
   est.fit(X[train],yin[train] if kind=='binary' else target[train])
   sc=est.predict_proba(X[test])[:,1] if kind=='binary' else est.predict(X[test])
   fitted[f'{m}|{trainmode}|{yr}']={'train_n':int(train.sum()),'test_n':int(test.sum()),'feature_n':X.shape[1]}
   for j,v in zip(np.flatnonzero(test),sc):
    r=rows[j];side='home' if float(v)>=(.5 if kind=='binary' else 0) else 'away'; pnl=float(r[side+'_U'])
    hit=int(side=='home')==int(yin[j])
    ledger.append({'fid':r['fid'],'year':yr,'league':r['league'],'source':r['source'],
         'is_m8_member':r['is_m8_member'],'model':m,'training':trainmode,'side':side,
         'score':round(float(v),6),'pnl_U':pnl,
         'quote_not_prospective':True})
    cohort='frozen' if r['is_m8_member'] else ('expanded15' if r['source']=='expanded15' else 'original49_outside')
    for name in (cohort,'outside' if cohort!='frozen' else 'frozen','all'):
     for period in (str(yr),'overall'):
      z=results[(m,trainmode,name,period)];z['n']+=1;z['pnl']+=pnl;z['wins_binary']+=int(hit)
   print('FINISHED',m,trainmode,yr,int(test.sum()),flush=True)
def fmt(z):return {'n':z['n'],'net_U':round(z['pnl'],3),'ROI_pct':round(100*z['pnl']/z['n'],4),
                   'binary_accuracy_pct':round(100*z['wins_binary']/z['n'],4)}
summary={'coverage':{'T6_priced':len(rows),'leagues':len(leagues),
   'T6_2024_26':int((year>=2024).sum()),
   'T6_2024_26_outside':sum(r['year']>=2024 and not r['is_m8_member'] for r in rows)},
   'fit':fitted,'results':{'|'.join(k):fmt(z) for k,z in results.items()},
   'limitations':['Source-event quotes retrieved historically, not contemporaneous receipts',
       'No optional lineup/formation/FT dataset filter; all priced T6 fixtures',
       'Simple market-price and league features; not Jack faithful',
       'Historic explored data; research-only, no new release rules']}
(P/'full62_price_models_summary.json').write_text(json.dumps(summary,indent=2))
with gzip.open(P/'full62_price_models_ledger.jsonl.gz','wt') as fp:
 for r in ledger:fp.write(json.dumps(r)+'\n')
for m in models:
 for tr in ('fixed_2019_23','annual_forward'):
  for cohort in ('outside','expanded15','original49_outside'):
   print('RESULT',m,tr,cohort,fmt(results[(m,tr,cohort,'overall')]),flush=True)
