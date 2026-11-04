#!/usr/bin/env python3
"""Chronological Crown-only temperature calibration experiment for M5.

A single predetermined 70/30 quote-time split is used. AH and OU tune
separately. The temperature is selected by training-set Asian-settlement log
loss, never by ROI. Every held-out fixture is simulated at its observed Crown
price without an EV threshold. Public output is aggregate-only.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,unicodedata,random
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

TEMPERATURES=(0.60,0.75,0.90,1.00,1.10,1.25,1.50,1.75,2.00)
CATS=("win","half_win","push","half_loss","loss")

def sha(b):return hashlib.sha256(b).hexdigest()
def dt(x):
 try:
  d=datetime.fromisoformat(str(x).replace('Z','+00:00'))
  return d.astimezone(timezone.utc) if d.tzinfo else None
 except Exception:return None

def load_rows(mr1_root,forecast_path):
 from research.m5.m3_grid_crown_replay import expected_return,legs_result,payout
 base=mr1_root/'data/prospective-market/shadow-v23'
 idx_raw=(base/'snapshot-index.jsonl').read_bytes(); reg_raw=(base/'fixtures.json').read_bytes();registry=json.loads(reg_raw)
 forecast_raw=forecast_path.read_bytes(); forecasts={}
 for s in forecast_raw.decode().splitlines():
  try:r=json.loads(s);forecasts[str(r['match_id'])]=r
  except Exception:pass
 ft_dir=mr1_root/'data/strategy-shadow-ledger/results';fts={};ft_hash_by_id={};ft_stats={}
 for p in ft_dir.glob('*.json'):
  try:
   r=json.loads(p.read_text())
   if r.get('status')=='FT' and str(r.get('match_id'))==p.stem and isinstance(r.get('home_goals'),int) and isinstance(r.get('away_goals'),int):
    raw_ft=p.read_bytes();fts[p.stem]=r;ft_hash_by_id[p.stem]=sha(raw_ft);ft_stats[p]=(len(raw_ft),p.stat().st_mtime_ns)
  except Exception:pass
 selected={};snapshots={}
 for line in idx_raw.decode().splitlines():
  try:e=json.loads(line)
  except Exception:continue
  mid=str(e.get('match_id') or '');f=forecasts.get(mid)
  if not f or e.get('classification')!='SNAPSHOT_OK':continue
  path=base/str(e.get('snapshot_path') or '')
  try:raw=path.read_bytes();s=json.loads(raw)
  except Exception:continue
  reg=registry.get(mid,{})
  if s.get('match_id')!=mid or reg.get('match_id')!=mid or any(reg.get(k)!=f.get(k) for k in ('league','home','away')):continue
  ko=dt(f.get('kickoff'));sko=dt(s.get('kickoff_at'));rko=dt(reg.get('kickoff_at'))
  if not ko or sko!=ko or rko!=ko:continue
  ft=fts.get(mid)
  if not ft or (int(ft['home_goals']),int(ft['away_goals']))!=(int(f['home_goals']),int(f['away_goals'])):continue
  if dt(ft.get('observed_at')) is None or dt(ft.get('observed_at'))<=ko:continue
  received=dt(s.get('received_at'));asof=dt(f.get('prediction_asof_utc'))
  if not received or received>=ko or not asof or received<asof:continue
  if s.get('source_bookmaker')!='crown' or s.get('source_bookmaker_verified') is not True or s.get('prematch_valid') is not True:continue
  for market in ('AH','OU'):
   q=s.get(market) or {}; observed=dt(q.get('observed_at_utc') or q.get('observed_at'))
   if not observed or observed>=ko or observed>received or observed<asof or q.get('closed') is True:continue
   try:
    contract=float(q['line']);prices=(float(q['home_price']),float(q['away_price'])) if market=='AH' else (float(q['over_price']),float(q['under_price']))
   except Exception:continue
   if any(not math.isfinite(p) or p<=1 for p in prices) or abs(contract*4-round(contract*4))>1e-8:continue
   key=(mid,market)
   row={'observed':observed,'received':received,'kickoff':ko,'ft_observed':dt(ft.get('observed_at')),'forecast':f,'ft':ft,'market':market,'line':contract,'prices':prices,'snapshot_sha256':sha(raw),'ft_sha256':ft_hash_by_id[mid]}
   if key not in selected or (observed,received)>(selected[key]['observed'],selected[key]['received']):selected[key]=row
   snapshots[path]=(path.stat().st_size,path.stat().st_mtime_ns)
 # Source stability guard.
 if (base/'snapshot-index.jsonl').read_bytes()!=idx_raw or (base/'fixtures.json').read_bytes()!=reg_raw:raise RuntimeError('MR1 archive index changed during read')
 for p,(size,mtime) in snapshots.items():
  if p.stat().st_size!=size or p.stat().st_mtime_ns!=mtime:raise RuntimeError('Crown snapshot changed during read')
 for p,(size,mtime) in ft_stats.items():
  if p.stat().st_size!=size or p.stat().st_mtime_ns!=mtime:raise RuntimeError('verified FT receipt changed during read')
 rows={'AH':[],'OU':[]}
 for row in selected.values():
  rows[row['market']].append(row)
 for market in rows:rows[market].sort(key=lambda r:(r['observed'],str(r['forecast']['match_id'])))
 return rows,forecast_raw,idx_raw,reg_raw

def transformed(grid,temp):
 vals=[]
 for row in grid:
  vals.append([max(float(p),1e-300)**(1.0/temp) for p in row])
 z=sum(sum(r) for r in vals)
 return [[p/z for p in r] for r in vals]

def evaluate(row,temp):
 from research.m5.m3_grid_crown_replay import expected_return,legs_result,payout
 market=row['market'];grid=transformed(row['forecast']['prediction']['grid'],temp);line=row['line'];prices=row['prices']
 sides=('home','away') if market=='AH' else ('over','under')
 ev=[expected_return(grid,market,s,line,p) for s,p in zip(sides,prices)]
 i=0 if ev[0]>=ev[1] else 1; side=sides[i];price=prices[i]
 hg,ag=int(row['ft']['home_goals']),int(row['ft']['away_goals'])
 legs,cat=legs_result(market,side,line,hg,ag);units=payout(legs,price)
 distribution=Counter()
 for h,gr in enumerate(grid):
  for a,p in enumerate(gr):
   _,c=legs_result(market,side,line,h,a);distribution[c]+=p
 ll=-math.log(max(distribution[cat],1e-15))
 brier=sum((distribution[c]-(1.0 if c==cat else 0.0))**2 for c in CATS)
 return {'units':units,'category':cat,'log_loss':ll,'brier':brier,'ev':ev[i]}

def summarize(rows,temp):
 out=[evaluate(r,temp) for r in rows];n=len(out);net=sum(x['units'] for x in out);counts=Counter(x['category'] for x in out)
 equity=peak=dd=0.0
 for row,x in sorted(zip(rows,out),key=lambda z:(z[0]['observed'],str(z[0]['forecast']['match_id']))):
  equity+=x['units'];peak=max(peak,equity);dd=max(dd,peak-equity)
 ci=None
 if n:
  rng=random.Random(20261105);boot=[]
  values=[x['units'] for x in out]
  for _ in range(10000):boot.append(100*sum(values[rng.randrange(n)] for _ in range(n))/n)
  boot.sort();ci={'lower_2_5_pct':round(boot[249],6),'upper_97_5_pct':round(boot[9749],6),'resamples':len(boot),'seed':20261105}
 return {'fixtures':n,'bets':n,'settled':n,'settlements':{c:counts[c] for c in CATS},'net_units':round(net,6),'roi_pct':round(100*net/n,6) if n else None,'roi_fixture_bootstrap_95pct_interval':ci,'max_drawdown_units_quote_time':round(dd,6) if n else None,'settlement_log_loss':round(sum(x['log_loss'] for x in out)/n,8) if n else None,'settlement_brier':round(sum(x['brier'] for x in out)/n,8) if n else None}

def chronological_split(events, train_fraction=0.70):
 if not 0 < train_fraction < 1 or len(events)<2:raise ValueError('invalid chronological split request')
 times=sorted({r['observed'] for r in events})
 target=max(1,min(len(times)-1,math.floor(len(events)*train_fraction)))
 seen=0;cutoff=times[0]
 for t in times:
  n=sum(r['observed']==t for r in events)
  if seen+n>target:
   cutoff=t;break
  seen+=n;cutoff=t
 pre=[r for r in events if r['observed']<cutoff]
 test=[r for r in events if r['observed']>=cutoff]
 train=[r for r in pre if r.get('ft_observed') and r['ft_observed']<cutoff]
 return train,test,cutoff,len(pre)-len(train)

def run(mr1_root,forecasts,output):
 rows,forecast_raw,idx_raw,reg_raw=load_rows(mr1_root,forecasts);markets={};
 for market,events in rows.items():
  if len(events)<10:markets[market]={'fixtures':len(events),'status':'insufficient_for_70_30_holdout'};continue
  # Labels used to fit temperature must already have been received before the
  # first held-out quote timestamp; fixture kickoff alone is not enough.
  train,test,cutoff,purged=chronological_split(events)
  if not train or not test:raise RuntimeError('chronological split yielded empty partition')
  train_scores={}
  for temp in TEMPERATURES:
   scored=[evaluate(r,temp) for r in train]
   train_scores[temp]=sum(x['log_loss'] for x in scored)/len(scored)
  best=min(TEMPERATURES,key=lambda t:(train_scores[t],abs(math.log(t))))
  if any(r['ft_observed']>=cutoff for r in train):raise RuntimeError('training FT receipt crosses the first holdout quote boundary')
  if any(r['observed']<cutoff for r in test):raise RuntimeError('holdout quote crosses chronological boundary')
  markets[market]={'source_verified_quotes':len(events),'chronological_train_fixtures_with_pre_holdout_FT':len(train),'purged_pre_cutoff_fixtures_without_pre_holdout_FT':purged,'untouched_later_holdout_fixtures':len(test),'quote_time_cutoff_utc':cutoff.isoformat().replace('+00:00','Z'),'train_quote_time_range_utc':[min(r['observed'] for r in train).isoformat().replace('+00:00','Z'),max(r['observed'] for r in train).isoformat().replace('+00:00','Z')],'train_FT_receipt_latest_utc':max(r['ft_observed'] for r in train).isoformat().replace('+00:00','Z'),'holdout_quote_time_range_utc':[min(r['observed'] for r in test).isoformat().replace('+00:00','Z'),events[-1]['observed'].isoformat().replace('+00:00','Z')],'candidate_temperatures':list(TEMPERATURES),'train_settlement_log_loss_by_temperature':{str(t):round(v,8) for t,v in train_scores.items()},'selected_temperature_by_train_log_loss':best,'train_baseline_temperature_1':summarize(train,1.0),'train_calibrated':summarize(train,best),'holdout_baseline_temperature_1':summarize(test,1.0),'holdout_calibrated':summarize(test,best),'selection_target':'minimum training-period settlement-category log loss; ROI is not used to select temperature','roi_gate_used':False}
 snapshot_hashes=sorted({r['snapshot_sha256'] for rs in rows.values() for r in rs})
 ft_hashes=sorted({r['ft_sha256'] for rs in rows.values() for r in rs})
 report={'protocol':'M5_CROWN_CHRONOLOGICAL_TEMPERATURE_CALIBRATION_V1','generated_utc':datetime.now(timezone.utc).isoformat(),'forecast_sha256':sha(forecast_raw),'MR1_snapshot_index_sha256':sha(idx_raw),'MR1_fixture_registry_sha256':sha(reg_raw),'verified_Crown_snapshot_count':len(snapshot_hashes),'verified_Crown_snapshot_hash_set_sha256':sha('\n'.join(snapshot_hashes).encode()),'verified_FT_receipt_count':len(ft_hashes),'verified_FT_receipt_hash_set_sha256':sha('\n'.join(ft_hashes).encode()),'markets':markets,'split':'Per market, sort unique source Crown quote event instants; train on early ~70% and test on later ~30%. No identical quote timestamp crosses the boundary. Training FT receipt must predate the first held-out quote; pre-boundary rows with later FT receipts are purged.','scope_note':'MR1 source-verified Crown snapshots joined to independent M5 OOS score grids and post-kickoff verified FT. Temperature selected only on earlier Crown settlement log loss; later holdout is not used for selection. No minimum EV or other bet gate. AH and OU fit/test independently. Aggregate only; no fixture IDs, teams, odds, or raw response values. Research-only; not a formal strategy or deployment.'}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps({'output':str(output),'markets':{m:{k:v for k,v in x.items() if k in ('source_verified_quotes','chronological_train_fixtures','untouched_later_holdout_fixtures','selected_temperature_by_train_log_loss','holdout_baseline_temperature_1','holdout_calibrated')} for m,x in markets.items()}},indent=2))

def main():
 p=argparse.ArgumentParser();p.add_argument('--mr1-root',type=Path,required=True);p.add_argument('--forecasts',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.mr1_root,a.forecasts,a.output)
if __name__=='__main__':main()
