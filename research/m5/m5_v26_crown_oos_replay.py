#!/usr/bin/env python3
"""Join V26's frozen Crown AH research quotes to strict M5 historical OOS.

Forecasts are deterministically reconstructed from prior-season results, so
the backtest is a hindcast, not a contemporaneously archived M5 signal. The
training cutoff and forecast-as-of must still precede the observed/received
Crown quote and kickoff. Public output contains only aggregates and hashes.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,unicodedata
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

def sha(raw):return hashlib.sha256(raw).hexdigest()
def dt(x):
 try:
  d=datetime.fromisoformat(str(x).replace('Z','+00:00'))
  return d.astimezone(timezone.utc) if d.tzinfo else None
 except Exception:return None
def norm(x):return re.sub(r'[^a-z0-9]+','',unicodedata.normalize('NFKD',str(x or '')).encode('ascii','ignore').decode().lower())

def pnl_summary(rows,decision='M5'):
 from research.m5.m3_grid_crown_replay import expected_return,legs_result,payout
 units=[];cats=Counter();scores=[]
 for r in rows:
  grid=r['forecast']['prediction']['grid'];line=r['line'];prices=r['prices']
  sides=('home','away') if r['market']=='AH' else ('over','under')
  if decision=='M5':
   ev=[expected_return(grid,r['market'],s,line,p) for s,p in zip(sides,prices)]
   i=0 if ev[0]>=ev[1] else 1;side=sides[i];price=prices[i]
  else:
   side=r['ai_side'];price=prices[sides.index(side)]
  h,a=r['home_goals'],r['away_goals'];legs,cat=legs_result(r['market'],side,line,h,a);u=payout(legs,price)
  cats[cat]+=1;units.append((r['observed'],str(r['mid']),u))
  dist=Counter()
  for gh,gr in enumerate(grid):
   for ga,p in enumerate(gr):
    _,c=legs_result(r['market'],side,line,gh,ga);dist[c]+=float(p)
  if decision=='M5':
   prob=max(dist[cat],1e-15);scores.append((-math.log(prob),sum((dist[k]-(1.0 if k==cat else 0.0))**2 for k in ('win','half_win','push','half_loss','loss'))))
 units.sort();equity=peak=dd=0.0
 for _,_,u in units:equity+=u;peak=max(peak,equity);dd=max(dd,peak-equity)
 n=len(units);net=sum(x[2] for x in units)
 return {'unique_fixtures':n,'simulated_bets':n,'settled_bets':n,'full_win':cats['win'],'half_win':cats['half_win'],'push':cats['push'],'half_loss':cats['half_loss'],'full_loss':cats['loss'],'net_units':round(net,6),'roi_pct':round(100*net/n,6) if n else None,'max_drawdown_units_by_quote_event':round(dd,6) if n else None,'settlement_log_loss':round(sum(x[0] for x in scores)/len(scores),8) if scores else None,'settlement_brier':round(sum(x[1] for x in scores)/len(scores),8) if scores else None}

def run(mr1_root:Path,v26_root:Path,forecast_path:Path,output:Path):
 from research.m5.m3_grid_crown_replay import expected_return,legs_result,payout
 forecast_raw=forecast_path.read_bytes();forecasts={}
 for line in forecast_raw.decode().splitlines():
  try:
   f=json.loads(line);forecasts[str(f['match_id'])]=f
  except Exception:pass
 # Independent post-kickoff FT receipts from the MR1 read-only archive.
 ft_dir=mr1_root/'data/strategy-shadow-ledger/results';fts={};ft_hashes={};ft_stats={}
 for p in ft_dir.glob('*.json'):
  try:
   raw=p.read_bytes();x=json.loads(raw)
   if x.get('status')=='FT' and str(x.get('match_id'))==p.stem and isinstance(x.get('home_goals'),int) and isinstance(x.get('away_goals'),int):
    fts[p.stem]=x;ft_hashes[p.stem]=sha(raw);ft_stats[p]=(len(raw),p.stat().st_mtime_ns)
  except Exception:pass
 # Load V23 source-verified, received-before-kickoff snapshots with same M5 identity.
 v23base=mr1_root/'data/prospective-market/shadow-v23';idx_raw=(v23base/'snapshot-index.jsonl').read_bytes();reg_raw=(v23base/'fixtures.json').read_bytes();registry=json.loads(reg_raw)
 v23_rows={};v23_hashes=set();snapshot_stats={}
 for line in idx_raw.decode().splitlines():
  try:e=json.loads(line)
  except Exception:continue
  mid=str(e.get('match_id') or '');f=forecasts.get(mid)
  if not f or e.get('classification')!='SNAPSHOT_OK':continue
  path=v23base/str(e.get('snapshot_path') or '')
  try:raw=path.read_bytes();s=json.loads(raw)
  except Exception:continue
  reg=registry.get(mid,{})
  if s.get('match_id')!=mid or reg.get('match_id')!=mid or any(reg.get(k)!=f.get(k) for k in ('league','home','away')):continue
  ko=dt(f.get('kickoff'))
  if not ko or dt(s.get('kickoff_at'))!=ko or dt(reg.get('kickoff_at'))!=ko:continue
  ft=fts.get(mid)
  if not ft or (int(ft.get('home_goals',-1)),int(ft.get('away_goals',-1)))!=(int(f['home_goals']),int(f['away_goals'])) or not dt(ft.get('observed_at')) or dt(ft['observed_at'])<=ko:continue
  received=dt(s.get('received_at'));asof=dt(f.get('prediction_asof_utc'))
  if not received or received>=ko or not asof or received<asof:continue
  if s.get('source_bookmaker')!='crown' or s.get('source_bookmaker_verified') is not True or s.get('prematch_valid') is not True:continue
  v23_hashes.add(sha(raw));snapshot_stats[path]=(path.stat().st_size,path.stat().st_mtime_ns)
  for market in ('AH','OU'):
   q=s.get(market) or {};observed=dt(q.get('observed_at_utc') or q.get('observed_at'))
   if not observed or observed>=ko or observed>received or observed<asof or q.get('closed') is True:continue
   try:
    line_value=float(q['line']);prices=(float(q['home_price']),float(q['away_price'])) if market=='AH' else (float(q['over_price']),float(q['under_price']))
   except Exception:continue
   if any(not math.isfinite(p) or p<=1 for p in prices) or abs(line_value*4-round(line_value*4))>1e-8:continue
   r={'mid':mid,'market':market,'observed':observed,'received':received,'line':line_value,'prices':prices,'forecast':f,'home_goals':int(f['home_goals']),'away_goals':int(f['away_goals']),'source':'V23','source_sha256':sha(raw),'ft_sha256':ft_hashes[mid]}
   key=(mid,market)
   if key not in v23_rows or (observed,received)>(v23_rows[key]['observed'],v23_rows[key]['received']):v23_rows[key]=r
 # V26 snapshot data already has a first locked observation and its exact Crown request metadata.
 v26obs=v26_root/'crown-market-benchmark-v26/forward/observations.jsonl';v26summary=v26_root/'crown-market-benchmark-v26/forward/summary.json';v26protocol=v26_root/'crown-market-benchmark-v26/protocol.json'
 obs_raw=v26obs.read_bytes();summary_raw=v26summary.read_bytes();protocol_raw=v26protocol.read_bytes();protocol=json.loads(protocol_raw)
 if protocol.get('source_bookmaker')!='crown':raise ValueError('V26 protocol does not identify Crown as the sole source')
 v26_rows={};v26_quote_hashes=set();stats=Counter()
 for line in obs_raw.decode().splitlines():
  try:o=json.loads(line)
  except Exception:continue
  if o.get('status')!='LOCKED_CROWN_PREMATCH':continue
  stats['protocol_locked']+=1;mid=str(o.get('match_id') or '');f=forecasts.get(mid)
  if not f:stats['no_forecast_id']+=1;continue
  qpath=v26_root/'market-resolution/latest'/f'{mid}.json'
  try:raw=qpath.read_bytes();qrec=json.loads(raw)
  except Exception:stats['missing_quote_payload']+=1;continue
  q=qrec.get('quote') or {};fixture=qrec.get('fixture') or {};ko=dt(f.get('kickoff'));observed=dt(q.get('observed_at'));requested=dt(q.get('requested_at'));received=dt(q.get('received_at'));first=dt(o.get('first_seen_at'))
  if q.get('bookmaker')!='crown' or q.get('bookmaker_source_verified') is not True:stats['unverified_bookmaker']+=1;continue
  if not ko or (fixture.get('home'),fixture.get('away'),fixture.get('league'))!=(f.get('home'),f.get('away'),f.get('league')) or dt(fixture.get('kickoff_at'))!=ko:stats['fixture_mismatch']+=1;continue
  asof=dt(f.get('prediction_asof_utc'));training_end=dt(f.get('train_end_utc'))
  if not observed or not requested or not received or not first or not asof or not training_end:stats['missing_timestamps']+=1;continue
  if not (training_end<asof<=observed<=received<ko and requested<=received):stats['chronology_failure']+=1;continue
  if (ko-first).total_seconds()<0 or (ko-first).total_seconds()>float(protocol['max_first_seen_lead_hours'])*3600:stats['first_seen_lead_failure']+=1;continue
  if (requested-first).total_seconds()<0 or (requested-first).total_seconds()>float(protocol['max_capture_to_quote_minutes'])*60:stats['capture_delay_failure']+=1;continue
  if (received-observed).total_seconds()<0 or (received-observed).total_seconds()>float(protocol['max_market_quote_age_minutes'])*60:stats['quote_age_failure']+=1;continue
  try:
   signal=str(o.get('signal_key') or '').split('|');ai_line=float(signal[3]);ai_side=signal[2]
   home_line=float(q['home_line']);prices=(float(q['home_price']),float(q['away_price']))
  except Exception:stats['invalid_contract']+=1;continue
  if abs(home_line-ai_line)>1e-9 or abs(home_line*4-round(home_line*4))>1e-8 or any(not math.isfinite(p) or p<=1 for p in prices):stats['invalid_contract']+=1;continue
  if ai_side not in ('home','away'):stats['AI_contract_mismatch']+=1;continue
  ft=fts.get(mid)
  if not ft or (int(ft.get('home_goals',-1)),int(ft.get('away_goals',-1)))!=(int(f['home_goals']),int(f['away_goals'])) or not dt(ft.get('observed_at')) or dt(ft['observed_at'])<=ko:stats['missing_independent_ft']+=1;continue
  stats['verified_historical_oos_pairs']+=1;v26_quote_hashes.add(sha(raw))
  v26_rows[(mid,'AH')]={'mid':mid,'market':'AH','observed':observed,'received':received,'line':home_line,'prices':prices,'forecast':f,'home_goals':int(f['home_goals']),'away_goals':int(f['away_goals']),'ai_side':ai_side,'source':'V26','source_sha256':sha(raw),'ft_sha256':ft_hashes[mid]}
 # Source-specific V26 only, V23, and union by fixture-market picking newest source event.
 v26market=[r for r in v26_rows.values()]
 v23ah=[r for r in v23_rows.values() if r['market']=='AH'];v23ou=[r for r in v23_rows.values() if r['market']=='OU']
 merged=dict(v23_rows)
 overlap=0;overlap_quote_order=Counter()
 for k,r in v26_rows.items():
  if k in merged:
   overlap+=1
   if (r['observed'],r['received'])>(merged[k]['observed'],merged[k]['received']):overlap_quote_order['V26_newer']+=1
   elif (r['observed'],r['received'])<(merged[k]['observed'],merged[k]['received']):overlap_quote_order['V23_newer']+=1
   else:overlap_quote_order['same_timestamp']+=1
  if k not in merged or (r['observed'],r['received'])>(merged[k]['observed'],merged[k]['received']):merged[k]=r
 mergedah=[r for (mid,mkt),r in merged.items() if mkt=='AH'];mergedou=[r for (mid,mkt),r in merged.items() if mkt=='OU']
 v23onv26=[v23_rows[k] for k in v26_rows if k in v23_rows and k[1]=='AH']
 out={
  'protocol':'M5_V26_CROWN_STRICT_OOS_HINDCAST_V1',
  'generated_utc':datetime.now(timezone.utc).isoformat(),
  'forecast_sha256':sha(forecast_raw),
  'V23_index_sha256':sha(idx_raw),
  'V23_fixture_registry_sha256':sha(reg_raw),
  'V23_quote_snapshot_count':len(v23_hashes),
  'V23_quote_snapshot_hash_set_sha256':sha('\n'.join(sorted(v23_hashes)).encode()),
  'V26_observations_sha256':sha(obs_raw),
  'V26_summary_sha256':sha(summary_raw),
  'V26_protocol_sha256':sha(protocol_raw),
  'V26_quote_payload_count':len(v26_quote_hashes),
  'V26_quote_payload_hash_set_sha256':sha('\n'.join(sorted(v26_quote_hashes)).encode()),
  'V26_FT_receipt_hash_set_sha256':sha('\n'.join(sorted({r['ft_sha256'] for r in v26_rows.values()})).encode()),
  'V26_audit_counts':dict(stats),
  'unique_fixture_market_overlap_V23_V26':overlap,
  'overlap_quote_time_order':dict(overlap_quote_order),
  'markets':{
   'AH':{'V23_only':pnl_summary(v23ah),'V26_first_locked_quote_hindcast':pnl_summary(v26market),'V26_MR1_AI_direction_same_quote_baseline':pnl_summary(v26market,'MR1_AI'),'V23_later_quote_on_same_V26_fixtures':pnl_summary(v23onv26),'merged_unique_latest_quote':pnl_summary(mergedah)},
   'OU':{'V23_only':pnl_summary(v23ou),'V26_only':{'unique_fixtures':0,'simulated_bets':0,'settled_bets':0,'roi_pct':None},'merged_unique_latest_quote':pnl_summary(mergedou)}},
  'deduplication':'One record per exact match_id and market. Where V23 and V26 both have eligible data, retain the later Crown quote event timestamp, then later receipt timestamp. No fixture can be counted twice in a market.',
  'method':'M5 score-grid probabilities are retrospectively reconstructed using strict annual UTC walk-forward training on prior-year results. Require training_end < prediction_asof <= Crown event <= received < kickoff, exact fixture identity, source-verified Crown AH contract, and separate post-kickoff FT receipt. Select the side with higher M5 expected return at the exact Crown line and price; no EV gate; one unit; quarter-line settlement. This is a historical hindcast, not an archived live M5 signal.',
  'scope_note':'Crown AH only in V26; no OU data in this archive. No non-Crown prices, private row values, IDs, team names, or credentials are published.'}
 # Stable-read guard for all source files used above.
 if (v26obs.read_bytes()!=obs_raw or v26summary.read_bytes()!=summary_raw or v26protocol.read_bytes()!=protocol_raw or (v23base/'snapshot-index.jsonl').read_bytes()!=idx_raw or (v23base/'fixtures.json').read_bytes()!=reg_raw):raise RuntimeError('source index/archive changed during replay')
 for p,(size,mtime) in {**snapshot_stats,**ft_stats}.items():
  if p.stat().st_size!=size or p.stat().st_mtime_ns!=mtime:raise RuntimeError('quote or FT receipt changed during replay')
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps({'output':str(output),'V26_audit_counts':dict(stats),'overlap':overlap,'markets':{m:{k:v for k,v in d.items() if k in ('V23_only','V26_only','merged_unique_latest_quote','V26_first_locked_quote_hindcast','V26_MR1_AI_direction_same_quote_baseline','V23_later_quote_on_same_V26_fixtures')} for m,d in out['markets'].items()}},indent=2))

def main():
 p=argparse.ArgumentParser();p.add_argument('--mr1-root',type=Path,required=True);p.add_argument('--v26-root',type=Path,required=True);p.add_argument('--forecasts',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.mr1_root,a.v26_root,a.forecasts,a.output)
if __name__=='__main__':main()
