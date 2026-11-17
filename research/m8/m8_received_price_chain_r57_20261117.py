import json,collections,hashlib,datetime,numpy as np
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_early_leading_price_mechanism_20261117.py').read_text()
exec(src[:src.rindex("out={'method'")])
assert len(pairs)==len(R)==1230 and len(h12)==38846
def dt(s):
 return datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
def local(s):
 return datetime.datetime.fromisoformat(str(s).replace(' ','T')+'+08:00').astimezone(datetime.timezone.utc)
def digest(b):return hashlib.sha256(b).hexdigest()
def verify(row,expected,err):
 try:
  f=str(row['fixture_id']); ko=dt(row['kickoff_utc']);received=dt(row['received_utc'])
  assert ko>received,'non_pregame_received'
  assert f==expected['fid'] and str(row['league_id'])==expected['league'],'receipt_match_id'
  p=Path(row['source_file'])
  a=json.loads(p.read_bytes())
  raw=a['raw_response']
  assert digest(raw.encode())==a['raw_sha256']==row['raw_sha256'],'raw_sha'
  assert dt(a['received_at'])==received and a['classification']=='SNAPSHOT_OK' and a['http_status']==200,'attempt_identity'
  b=(p.parent.parent/'snapshot.json').read_bytes()
  snap=json.loads(b)
  assert digest(b)==row['snapshot_sha256'],'snapshot_sha'
  assert str(snap['match_id'])==f and dt(snap['kickoff_at'])==ko and dt(snap['received_at'])==received,'snapshot_identity'
  assert snap['source_bookmaker']=='crown' and snap['source_bookmaker_verified'] is True,'snapshot_source'
  raw_obj=json.loads(raw)
  match=next(v for v in raw_obj['data'] if str(v['id'])==f)
  assert str(match['l_id'])==row['league_id'] and local(match['start'])==ko,'fixture_utc'
  assert str(match['h_id'])==expected['home_id'] and str(match['a_id'])==expected['away_id'],'team_ids'
  assert ko.date().isoformat()==expected['date'],'UTC_date'
  crown=next(v for v in match['bookmakers'] if v['slug']=='crown')
  for market,key,aa,bb in [('AH','asian','home','away'),('OU','goal','over','under')]:
   close=crown[key]['close'];q=row['markets'][market]
   when=local(close['time'])
   assert when<=received,'source_time_after_receipt'
   assert when==dt(q['source_event_utc']),'source_time'
   assert float(close['line'])==float(q['line']),'line'
   assert float(close[aa])==float(q['odds'][aa]) and float(close[bb])==float(q['odds'][bb]),'odds'
   assert min(float(close[aa]),float(close[bb]))>1,'invalid_price'
  return {'record':row,'when_received':received,'source_event':dt(row['markets']['AH']['source_event_utc']),
     'line':float(row['markets']['AH']['line']),
     'home_odds':float(row['markets']['AH']['odds']['home']),
     'away_odds':float(row['markets']['AH']['odds']['away']),
     'hours_before_kickoff':(ko-received).total_seconds()/3600,
     'snapshot_split':row['snapshot_split']}
 except Exception as exc:
  why=str(exc.args[0]) if isinstance(exc,AssertionError) and exc.args else type(exc).__name__
  err[why]+=1
  return None
raw_rows=[json.loads(s) for s in (P/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl').open()]
raw_map=collections.defaultdict(dict)
for rec in raw_rows:
 fid=str(rec['fixture_id']);h=rec['snapshot_horizon']
 assert h not in raw_map[fid]
 raw_map[fid][h]=rec
cohorts=collections.Counter()
for f,rr in raw_map.items():
 for h,r in rr.items():cohorts[h]+=1
errors=collections.Counter();chosen=[];partial=collections.Counter()
# Strict exact R22 receipt pairs: reconstruct the R22 chosen T12 receipt.
for a,b in pairs:
 f=b['fid'];rr=raw_map[f]
 candidates=[]
 for row in rr.values():
  delta=(dt(row['kickoff_utc'])-dt(row['received_utc'])).total_seconds()/3600
  if 12<=delta<24:candidates.append(row)
 candidates.sort(key=lambda row:dt(row['received_utc']),reverse=True)
 if not candidates:partial['selected_R22_T12_receipt_missing']+=1;continue
 current=None
 for r in candidates:
  v=verify(r,b,errors)
  if v is not None:
   current=v;break
 if current is None:partial['R22_T12_source_verify_failed']+=1;continue
 # R22 study's chosen source must match this verified row exactly.
 assert (current['line'],current['home_odds'],current['away_odds'])==(b['al'],b['ah'],b['aa']),'R22_quote_disagreement'
 assert abs((dt(current['record']['kickoff_utc'])-datetime.timedelta(hours=12)-current['source_event']).total_seconds()/3600-b['age_ah'])<1e-5,'R22_AH_event_age_disagreement'
 later={}
 for horizon in ('T6','T3','T1'):
  record=rr.get(horizon)
  if record is None:
   partial[f'missing_{horizon}']+=1;continue
  v=verify(record,b,errors)
  if v is None:
   partial[f'invalid_{horizon}']+=1;continue
  if v['when_received']<=current['when_received']:
   partial[f'non_ascending_{horizon}']+=1;continue
  later[horizon]=v
 chosen.append((a,b,current,later))
print('ARCHIVE',len(raw_rows),'unique_matches',len(raw_map),'hor_counts',dict(cohorts),'selected',len(chosen),
 'error',dict(errors),'partial',dict(partial),flush=True)
# Reproduce R56 price model fitted on prior years only. All predictions based
# on T24/T12 price only. Actual future horizons are NEVER training features.
hist_data=D['T12']
x=hist_data['X'];y=hist_data['y'];yr=hist_data['year'];ind=hist_data['disjoint']
train=(yr<2026)&ind
model_x=np.array([features(a,b,'T12') for a,b,c,d in chosen])
pred,beta=regression(x[train],y[train],model_x)
buy_home=pred[:,0]>=pred[:,1]
forecast_best=pred.max(1)
base_pnl=np.array([float(b['home_U'] if h else b['away_U']) for (a,b,c,d),h in zip(chosen,buy_home)])
positive=forecast_best>0
replay_original=np.array([features(a,b,'T12') for a,b in pairs])
orig,_=regression(x[train],y[train],replay_original)
orig_b=orig[:,0]>=orig[:,1]
orig_stake=np.array([b['home_U'] if h else b['away_U'] for (a,b),h in zip(pairs,orig_b)])
assert abs(orig_stake.sum()+85.485)<.0011,(orig_stake.sum())
assert int((orig.max(1)>0).sum())==856
receipt_by_kind=collections.Counter(z[2]['record']['snapshot_horizon'] for z in chosen)
from research.m3.probabilities import settle_score
def pnl(v,side,b):
 return settle_score('AH',v['line'],'home' if side else 'away',int(b['hg']),int(b['ag']),v['home_odds'] if side else v['away_odds'])[1]
def res(vals):
 vals=np.asarray(vals,float)
 return {'n':len(vals),'U':round(float(vals.sum()),3),
  'ROI':round(float(vals.mean()*100),3) if len(vals) else None,
  'wins':int((vals>1e-8).sum()),'losses':int((vals<-1e-8).sum()),
  'push':int((abs(vals)<=1e-8).sum())}
out={'research_id':'M8_R57_REAL_RECEIVED_PRICE_CHAIN','method':'Correct R56 statement: raw archive DOES have verified later T6/T3/T1 snapshots. Independently reverify original attempt raw_sha, snapshot_sha, actual receipt and source_event timestamp, Crown bookmaker, exact fixture UTC and league/team identity against R22 verified FT. Use R56 fixed previous-year T24/T12->T6 same-line price-shortening prediction to choose AH sides; actual T6/T3/T1 snapshots used solely as FUTURE LABEL and same-side ex-post price comparison. All current T12 base stakes priced at ACTUALLY RECEIVED quotes, not claims of executable at nominal T12 cutoff. Future AH line changes produce incomparable odds values and null, not zero CLV. New quote freshness is separate. Original8 exclusion only hindsight attribution; no OU selection. No new production Gate, no actual fills, no TG or prospective trading claims. Receipt archive includes LOCKED_EVALUATION and DEVELOPMENT splits; results reported by source and do not relabel retrospective study as locked forward. No API requests.','coverage':{'archive_rows':len(raw_rows),'archive_unique_fixtures':len(raw_map),'by_horizon':dict(cohorts),
  'R22_verified_T24_T12_with_FT':len(pairs),'R22_pair_source_verified':len(chosen),
  'current_source_horizon':dict(receipt_by_kind),'partial':dict(partial),'verification_errors':dict(errors)},
  'prediction':{'prior_year_training_n':int(train.sum()),'coefficients':beta.tolist(),
   'previous_R56_all_receipts_model_return':res(orig_stake),
   'previous_R56_all_receipts_opportunities':res(orig_stake[orig.max(1)>0])},
  'results':{},'foundation':{}}
def subgroup(data,condition,market):
 ix=np.asarray([i for i,z in enumerate(chosen) if condition(i,z)],int)
 z={'n':len(ix),'selected':res(base_pnl[ix]),'opportunity':res(base_pnl[ix[positive[ix]]]),
  'predicted_same_line_shortening_mean':round(float(forecast_best[ix].mean()),6) if len(ix) else None}
 if not len(ix):return z
 line_same=[];quote_advance=[];improved=[];unchanged=[];worsened=[]
 comparable_changes=[];fresh=[];fresh_gain=[];time_gaps=[];market_pnls=[];current_pnls=[];source_time_deltas=[]
 q_types=collections.Counter()
 for i in ix:
  _,b,current,later=chosen[i]
  if market not in later:continue
  v=later[market]
  time_gaps.append((v['when_received']-current['when_received']).total_seconds()/3600)
  q_types[v['snapshot_split']]+=1
  same=current['line']==v['line']
  line_same.append(same)
  source_move=(v['source_event']-current['source_event']).total_seconds()/3600
  source_time_deltas.append(source_move)
  quote_advance.append(source_move>1e-8)
  market_pnls.append(pnl(v,buy_home[i],b))
  current_pnls.append(base_pnl[i])
  if same:
   previous_price=current['home_odds'] if buy_home[i] else current['away_odds']
   future_price=v['home_odds'] if buy_home[i] else v['away_odds']
   difference=previous_price-future_price
   comparable_changes.append(difference)
   improved.append(difference>1e-10)
   unchanged.append(abs(difference)<=1e-10)
   worsened.append(difference<-1e-10)
   if source_move>1e-8:
    fresh.append(difference)
    fresh_gain.append(difference>1e-10)
 z['future_receipt_n']=len(time_gaps)
 z['future_receipt_splits']=dict(q_types)
 z['later_receipt_gap_hours_mean']=round(float(np.mean(time_gaps)),4) if time_gaps else None
 z['future_source_event_advanced_n']=sum(quote_advance)
 z['future_source_event_advanced_pct']=round(100*float(np.mean(quote_advance)),3) if quote_advance else None
 z['source_event_hours_delta_mean']=round(float(np.mean(source_time_deltas)),3) if source_time_deltas else None
 z['same_AH_line_n']=sum(line_same)
 z['AH_line_changed_n']=len(line_same)-sum(line_same)
 z['same_AH_line_shortened_n']=sum(improved)
 z['same_AH_line_unchanged_n']=sum(unchanged)
 z['same_AH_line_lengthened_n']=sum(worsened)
 z['same_AH_line_shortened_pct']=round(100*float(np.mean(improved)),3) if improved else None
 z['same_line_odds_shortening_mean']=round(float(np.mean(comparable_changes)),6) if comparable_changes else None
 z['fresh_same_line_n']=len(fresh)
 z['fresh_same_line_shortened_n']=sum(fresh_gain)
 z['fresh_same_line_odds_shortening_mean']=round(float(np.mean(fresh)),6) if fresh else None
 z['T12_original_receipt_result_when_later_exists']=res(current_pnls)
 z['future_same_side_at_later_RECEIPT_counterfactual']=res(market_pnls)
 return z
for market in ('T6','T3','T1'):
 out['results'][market]={}
 for name,filter_fn in [
  ('all_received',lambda i,z:True),
  ('outside_original_eight_RETROSPECTIVE',lambda i,z:z[1]['fid'] not in ids),
  ('research_price_opportunity',lambda i,z:positive[i]),
  ('research_price_NOT_opportunity',lambda i,z:not positive[i]),
  ('research_price_opportunity_outside_eight_RETROSPECTIVE',lambda i,z:positive[i] and z[1]['fid'] not in ids),
  ('research_price_NOT_opportunity_outside_eight_RETROSPECTIVE',lambda i,z:not positive[i] and z[1]['fid'] not in ids)]:
  a=subgroup(chosen,filter_fn,market)
  out['results'][market][name]=a
  print('RESULT',market,name, {k:v for k,v in a.items() if k in ('n','future_receipt_n','selected','opportunity','same_AH_line_n','AH_line_changed_n','same_AH_line_shortened_n','same_AH_line_shortened_pct','same_line_odds_shortening_mean','future_source_event_advanced_n','fresh_same_line_n','fresh_same_line_shortened_n','fresh_same_line_odds_shortening_mean','T12_original_receipt_result_when_later_exists','future_same_side_at_later_RECEIPT_counterfactual')},flush=True)
# Report actual receipt horizon split, no laundering locked evaluation as preregistered.
out['source_splits']=collections.Counter(z[2]['snapshot_split'] for z in chosen)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
out['source_splits']=dict(out['source_splits'])
(P/'m8_received_price_chain_r57_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('SAVED',out['coverage'],flush=True)
