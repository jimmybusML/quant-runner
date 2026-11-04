#!/usr/bin/env python3
"""Nested UTC-year walk-forward probability blend of M3 and independent M5 OOS.

Weights are learned only on earlier common OOS predictions/outcomes. AH's
three-way 1X2 probability proxy and OU2.5 remain separate. This is probability
research; it does not use odds, Crown ROI, bets, M1/MR1 predictions, or ledgers.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,unicodedata
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

LEAGUE_CODES={"England Premier League":"E0","Italy Serie A":"I1","Spain La Liga":"SP1","France Ligue 1":"F1","Germany Bundesliga":"D1","Belgium First Division A":"B1","Belgium Jupiler Pro League":"B1"}
MODELS=("poisson","dixon_coles","bivariate_poisson","m5_independent_goal_rates")
EPS=1e-12

def sha(raw):return hashlib.sha256(raw).hexdigest()
def norm(x):return re.sub(r"[^a-z0-9]+","",unicodedata.normalize("NFKD",str(x or "")).encode("ascii","ignore").decode().lower())
def soft_score(p,y):
 p=np.clip(np.asarray(p,dtype=float),EPS,1.0);p=p/p.sum(axis=1,keepdims=True)
 return float(-np.log(p[np.arange(len(y)),y]).mean())
def binary_scores(p,y):
 p=np.clip(np.asarray(p,dtype=float),EPS,1-EPS);y=np.asarray(y,dtype=float)
 return float(-(y*np.log(p)+(1-y)*np.log(1-p)).mean()),float(np.square(p-y).mean())
def fit_weights(p,y):
 if len(y)==0:return np.ones(p.shape[1])/p.shape[1]
 def objective(w):return soft_score(np.einsum('nmk,m->nk',p,w),y)
 res=minimize(objective,np.ones(p.shape[1])/p.shape[1],method="SLSQP",bounds=[(0,1)]*p.shape[1],constraints=[{"type":"eq","fun":lambda w:np.sum(w)-1}],options={"maxiter":500,"ftol":1e-12})
 if not res.success or not np.all(np.isfinite(res.x)):raise RuntimeError("walk-forward simplex weight fit failed")
 w=np.maximum(res.x,0);return w/w.sum()
def read():
 ap=argparse.ArgumentParser();ap.add_argument('--m3-csv',type=Path,required=True);ap.add_argument('--m5-forecasts',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 m3raw=args.m3_csv.read_bytes();m5raw=args.m5_forecasts.read_bytes()
 m3=defaultdict(dict)
 for row in csv.DictReader(m3raw.decode().splitlines()):
  k=(row['league'],row['match_date_utc'][:10],norm(row['home_team']),norm(row['away_team']))
  m3[k][row['model']]=row
 records={}
 for line in m5raw.decode().splitlines():
  try:
   x=json.loads(line);code=LEAGUE_CODES.get(x['league']);
   if code:
    k=(code,x['kickoff'][:10],norm(x['home']),norm(x['away']))
    if k in records:records.pop(k)
    else:records[k]=x
  except Exception:continue
 common=[];result_mismatch=0;incomplete=0
 for k,x in records.items():
  by=m3.get(k,{})
  if any(m not in by for m in MODELS[:3]):continue
  if any(not by[m].get(a) for m in MODELS[:3] for a in ('p_home','p_draw','p_away','ou_p_over_2_5')):incomplete+=1;continue
  h,a=int(x['home_goals']),int(x['away_goals'])
  if any((int(by[m]['actual_home_goals']),int(by[m]['actual_away_goals']))!=(h,a) for m in MODELS[:3]):result_mismatch+=1;continue
  ah=[]
  for m in MODELS[:3]:ah.append([float(by[m]['p_home']),float(by[m]['p_draw']),float(by[m]['p_away'])])
  pp=x['prediction'];ah.append([float(pp['p_home']),float(pp['p_draw']),float(pp['p_away'])])
  ou=[float(by[m]['ou_p_over_2_5']) for m in MODELS[:3]]+[float(sum(pp['grid'][i][j] for i in range(15) for j in range(15) if i+j>2))]
  common.append({'key':k,'year':int(x['kickoff'][:4]),'home':h,'away':a,'ah':ah,'ou':ou})
 return args,m3raw,m5raw,common,result_mismatch,incomplete

def main():
 args,m3raw,m5raw,rows,result_mismatch,incomplete=read()
 byyear=defaultdict(list)
 for r in rows:byyear[r['year']].append(r)
 scores={'AH_1X2_probability_proxy':{},'OU_O2_5':{}}
 all_ah=[];all_ou=[];weights={};folds=[]
 for year in sorted(byyear):
  test=byyear[year];train=[r for r in rows if r['year']<year]
  if not train:continue
  ahp=np.array([r['ah'] for r in train]);ahy=np.array([0 if r['home']>r['away'] else 1 if r['home']==r['away'] else 2 for r in train])
  oup=np.array([r['ou'] for r in train]);ouy=np.array([int(r['home']+r['away']>2) for r in train])
  wa=fit_weights(ahp,ahy);wo=fit_weights(np.stack([oup,1-oup],axis=2),ouy)
  test_ah=np.array([r['ah'] for r in test]); test_y=np.array([0 if r['home']>r['away'] else 1 if r['home']==r['away'] else 2 for r in test])
  blend_ah=np.einsum('nmk,m->nk',test_ah,wa); test_ou=np.array([r['ou'] for r in test]);test_oy=np.array([int(r['home']+r['away']>2) for r in test]);blend_ou=test_ou@wo
  weights[str(year)]={'AH':{m:round(float(w),8) for m,w in zip(MODELS,wa)},'OU':{m:round(float(w),8) for m,w in zip(MODELS,wo)},'train_fixtures':len(train),'test_fixtures':len(test),'train_years':sorted({r['year'] for r in train})}
  ahby={m:[] for m in MODELS};ouby={m:[] for m in MODELS}
  for j,r in enumerate(test):
   ahby['m5_independent_goal_rates'].append((test_ah[j,3],test_y[j]))
   for idx,m in enumerate(MODELS[:3]):ahby[m].append((test_ah[j,idx],test_y[j]))
   for idx,m in enumerate(MODELS):ouby[m].append((test_ou[j,idx],test_oy[j]))
  for market,blended,actual,baseline,y in [('AH_1X2_probability_proxy',blend_ah,test_y,ahby,None),('OU_O2_5',blend_ou,test_oy,ouby,None)]:
   if market.startswith('AH'):
    row={name:{'log_loss':round(soft_score(np.array([v[0] for v in vals]),np.array([v[1] for v in vals])),8),'brier':round(float(np.square(np.array([v[0] for v in vals])-np.eye(3)[np.array([v[1] for v in vals])]).sum(axis=1).mean()),8)} for name,vals in baseline.items()}
    row['m5_walk_forward_blend']={'log_loss':round(soft_score(blended,actual),8),'brier':round(float(np.square(blended-np.eye(3)[actual]).sum(axis=1).mean()),8)}
    scores[market][str(year)]={'fixtures':len(test),'models':row}
   else:
    row={name:{'log_loss':round(binary_scores(np.array([v[0] for v in vals]),np.array([v[1] for v in vals]))[0],8),'brier':round(binary_scores(np.array([v[0] for v in vals]),np.array([v[1] for v in vals]))[1],8)} for name,vals in baseline.items()}
    row['m5_walk_forward_blend']={'log_loss':round(binary_scores(blended,actual)[0],8),'brier':round(binary_scores(blended,actual)[1],8)}
    scores[market][str(year)]={'fixtures':len(test),'models':row}
  folds.append({'test_year':year,'train_fixtures':len(train),'test_fixtures':len(test),'train_test_fixture_keys_disjoint':True})
  all_ah.extend((test_ah,test_y)) if False else None
 # pool only test folds that were actually scored
 summary={}
 for market in scores:
  names=list(MODELS)+['m5_walk_forward_blend'];summary[market]={}
  for name in names:
   pairs=[(year,d) for year,d in scores[market].items()]
   n=sum(d['fixtures'] for _,d in pairs)
   ll=sum(d['models'][name]['log_loss']*d['fixtures'] for _,d in pairs)/n if n else None
   br=sum(d['models'][name]['brier']*d['fixtures'] for _,d in pairs)/n if n else None
   summary[market][name]={'fixtures':n,'fixture_weighted_log_loss':round(ll,8) if ll is not None else None,'fixture_weighted_brier':round(br,8) if br is not None else None}
 report={'protocol':'M5_M3_GOAL_MODEL_NESTED_UTC_YEAR_BLEND_V1','generated_utc':datetime.now(timezone.utc).isoformat(),'m3_predictions_sha256':sha(m3raw),'m5_private_forecasts_sha256':sha(m5raw),'common_strict_oos_fixtures':len(rows),'result_identity_mismatches_excluded':result_mismatch,'incomplete_prediction_rows_excluded':incomplete,'markets':summary,'yearly':scores,'walk_forward_weights':weights,'fold_receipts':folds,'roi':None,'crown_prices_used':False,'method':'For each test UTC year, fit non-negative sum-to-one probability weights only on prior common OOS fixture predictions and outcomes. No same-year result informs weights. AH 1X2 probability proxy and OU2.5 are fitted separately. The resulting report is probability score research only, not Crown ROI.'}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'common_fixtures':len(rows),'scores':summary,'output':str(args.output)},sort_keys=True))
if __name__=='__main__':main()
