#!/usr/bin/env python3
"""Rebuild M9 bivariate-Poisson forecasts on frozen M8 FIDs; read-only research."""
import collections, datetime as dt, hashlib, json, math, sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from research.m3.openfootball_shadow import MODELS, _serialize_score_probability_grid
from research.m3.probabilities import settle_score

ROOT=Path('/Users/mac/QuantAsiaDesk')
MEM=ROOT/'research-work/m8_foundation_20261115/historical_membership.jsonl'
FEAT=ROOT/'research-work/m8_independent_score_strength_20261114.jsonl'
PATHS=ROOT/'research-work/m8_late_full_path_water_features_20261114.jsonl'
CACHE=ROOT/'repos/m1/data/m1_history_cache'
DB=ROOT/'data/crown_quote_store/crown_quotes.sqlite3'
OUT=Path(__file__).parent
UTC=dt.timezone.utc
CACHE_HASHES={}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def parse(s):
 x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00'))
 if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
 return x.astimezone(UTC)
def load_hist():
 grouped={}; counts=collections.Counter()
 for f in sorted(CACHE.glob('*.json')):
  try:
   raw=f.read_bytes();CACHE_HASHES[f.name]=hashlib.sha256(raw).hexdigest();d=json.loads(raw)
  except Exception:counts['cache_unreadable']+=1;continue
  lid=str(d.get('league_id','')); arr=[]
  for r in d.get('rows',[]):
   if r.get('status')!='full':continue
   try:
    t=parse(r['start']); h,a=str(r['h_id']),str(r['a_id']);hg,ag=int(r['hg']),int(r['ag'])
    if not h.isdigit() or not a.isdigit() or h==a or min(hg,ag)<0:continue
    arr.append((str(r['id']),t,h,a,hg,ag))
   except Exception:continue
  grouped[lid]=list({r[0]:r for r in arr}.values())
 counts['leagues']=len(grouped);counts['full_rows']=sum(map(len,grouped.values()))
 return grouped,dict(counts)
def outcome(matrix,line,side,decimal):
 probs=collections.Counter();
 for h,row in enumerate(matrix):
  for a,p in enumerate(row):
   if p<=0:continue
   state,_=settle_score('AH',line,side,h,a,decimal)
   probs[state]+=p
 return dict(probs)
def get_crown(ids):
 cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True)
 sql='''select q.fixture_id,q.quote_kind,q.handicap_home,q.home_decimal,q.away_decimal,q.quote_source_at_utc,q.response_received_at_utc,q.prospective_observation,c.capture_mode,c.response_sha256,c.source_file
 from asian_quote q join capture c using(capture_key) where q.quote_kind in ('movement','close')'''
 wanted=set(ids); out=collections.defaultdict(list)
 for row in cx.execute(sql):
  fid=row[0]
  if fid in wanted:out[fid].append(row[1:])
 cx.close();return out

def main():
 member=[json.loads(x) for x in MEM.open()]
 member_map={x['fid']:x for x in member}
 feat={json.loads(x)['fid']:json.loads(x) for x in FEAT.open()}
 paths={json.loads(x)['fid']:json.loads(x) for x in PATHS.open()}
 for name in ('m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
  p=ROOT/'research-work'/name
  if p.exists():
   for line in p.open():
    row=json.loads(line); fid=str(row.get('fid',''))
    if fid: paths[fid]={**paths.get(fid,{}),**row}
 history,hcov=load_hist()
 quotes=get_crown(feat.keys())
 # Group by league and UTC target month. Each vintage is fit at the first
 # target kickoff in that league/month using all complete results before it.
 targets=[]; audit=collections.Counter(); results=[]
 for fid,score in feat.items():
  f={**paths.get(fid,{}),**score}
  m=member_map.get(fid)
  if not f or f.get('hg') is None or f.get('ag') is None or not f.get('ko'):
   audit['missing_fixture_meta']+=1;continue
  qrows=quotes.get(fid,[])
  # Use a Crown quote no later than the M8 T-1h information cutoff and require
  # the same home handicap line recorded by the frozen M8 replay.
  ko=parse(f['ko'])
  clean=[]
  for q in qrows:
   kind,line,ho,ao,src,recv,pros,mode,rsha,path=q
   try: st=parse(src)
   except Exception:continue
   if line is None or ho is None or ao is None or float(ho)<=1 or float(ao)<=1:continue
   clean.append((st,float(line),float(ho),float(ao),src,recv,int(pros or 0),mode,rsha,path,kind))
  cutoff_quote=ko-dt.timedelta(hours=1)
  pre=[q for q in clean if q[0]<=cutoff_quote]
  latest_pre=max(pre,key=lambda q:q[0]) if pre else None
  if not pre:audit['missing_crown_pregame_event_quote']+=1;quote=None
  elif abs(latest_pre[1]-float(f.get('end_line',999)))>=1e-8:audit['Tminus1_latest_line_differs_from_M8_reference']+=1;quote=None
  else:quote=latest_pre
  league=history.get(str(f['league']),[])
  h,a=str(f.get('home') or ''),str(f.get('away') or '')
  if not h.isdigit() or not a.isdigit():audit['missing_team_ids']+=1;continue
  if not any(h in r[2:4] for r in league) or not any(a in r[2:4] for r in league):audit['missing_team_training_history']+=1;continue
  targets.append((m,f,ko,league,h,a,quote))
 # Cache model by league and target date; training rows strictly earlier than target's UTC day.
 by=collections.defaultdict(list)
 for t in targets:by[(str(t[1]['league']),t[2].strftime('%Y-%m'))].append(t)
 modelcache={}
 for (lid,target_month),batch in sorted(by.items(),key=lambda x:(x[0][1],x[0][0])):
  cutoff=min(z[2] for z in batch)
  train=[r for r in history.get(lid,[]) if r[1]<cutoff]
  if len(train)<2:
   audit['insufficient_pretarget_training']+=len(batch);continue
  key=(lid,target_month)
  try:
   frame=pd.DataFrame([{'home_team':r[2],'away_team':r[3],'home_goals':r[4],'away_goals':r[5]} for r in train])
   model=MODELS['bivariate_poisson'](frame.home_goals,frame.away_goals,frame.home_team,frame.away_team);model.fit()
  except Exception:
   audit['model_fit_failed']+=len(batch);continue
  for m,f,ko,league,h,a,quote in batch:
   try:matrix=_serialize_score_probability_grid(model.predict(h,a))
   except Exception:audit['prediction_failed']+=1;continue
   if not quote:audit['missing_crown_or_same_line_quote_prediction']+=1;continue
   _,line,homeodd,awayodd,src,recv,pros,mode,rsha,path,kind=quote
   home_states=outcome(matrix,line,'home',homeodd)
   away_states=outcome(matrix,line,'away',awayodd)
   neutral_home_states=outcome(matrix,line,'home',2.0)
   neutral_away_states=outcome(matrix,line,'away',2.0)
   # direction maximizing expected return at the paired Crown prices
   def expected(st,odd):return st.get('FULL_WIN',0)*(odd-1)+st.get('HALF_WIN',0)*(odd-1)/2-st.get('HALF_LOSS',0)/2-st.get('FULL_LOSS',0)
   evh=expected(home_states,homeodd)
   eva=expected(away_states,awayodd)
   neutral_evh=expected(neutral_home_states,2.0)
   neutral_eva=expected(neutral_away_states,2.0)
   side='home' if neutral_evh>=neutral_eva else 'away'; odd=homeodd if side=='home' else awayodd
   state,pnl=settle_score('AH',line,side,int(f['hg']),int(f['ag']),odd)
   m8side='home' if m and abs(float(m['pnl'])-float(f['end_home_U']))<1e-7 else 'away' if m and abs(float(m['pnl'])-float(f['end_away_U']))<1e-7 else None
   if m and not m8side:audit['m8_direction_ambiguous']+=1
   m8state,m8actual=settle_score('AH',line,m8side,int(f['hg']),int(f['ag']),homeodd if m8side=='home' else awayodd) if m8side else (None,None)
   results.append({'fid':f['fid'],'league_id':str(f['league']),'kickoff_utc':ko.isoformat(),'season_year':ko.year,'is_m8_member':bool(m),'m8_cohort':m['cohort'] if m else None,'m8_side':m8side,'m8_state':m8state,'m8_pnl_repriced_same_Crown_contract':m8actual,'m8_recorded_pnl':float(m['pnl']) if m else None,'home_team_id':h,'away_team_id':a,'ft_home':int(f['hg']),'ft_away':int(f['ag']),'training_n':len(train),'training_cutoff_utc':cutoff.isoformat(),'training_max_event_utc':max(r[1] for r in train).isoformat(),'prediction_type':'historical_reconstruction_not_formal_m9_receipt','score_grid':matrix,'crown_line_home':line,'crown_home_decimal':homeodd,'crown_away_decimal':awayodd,'crown_source_event_utc':src,'crown_http_received_at_utc':recv,'crown_capture_mode':mode,'crown_prospective_observation':pros,'crown_quote_age_hours_at_Tminus1':(ko-dt.timedelta(hours=1)-quote[0]).total_seconds()/3600,'crown_raw_response_sha256':rsha,'crown_quote_kind':kind,'m9_home_expected_unit_return_at_crown_price':evh,'m9_away_expected_unit_return_at_crown_price':eva,'m9_neutral_home_score':neutral_evh,'m9_neutral_away_score':neutral_eva,'m9_home_settlement_probabilities':home_states,'m9_away_settlement_probabilities':away_states,'m9_neutral_home_settlement_probabilities':neutral_home_states,'m9_neutral_away_settlement_probabilities':neutral_away_states,'m9_side':side,'m9_state':state,'m9_pnl':pnl})
  audit['date_models_fit']+=1
 # Preserve results with no training or no quote in coverage audit only.
 (OUT/'m9_reconstruction_m8_universe.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in results))
 ledger=ROOT/'state/m9_formal_events.jsonl';formal_counts=collections.Counter()
 for line in ledger.open():
  try:formal_counts[json.loads(line).get('kind','')]+=1
  except Exception:pass
 meta={'membership_n':len(member),'feature_n':len(feat),'path_feature_n':len(paths),'predictions_with_crown':len(results),'audit_counts':dict(audit),'history_coverage':hcov,'membership_sha256':sha(MEM),'features_sha256':sha(FEAT),'path_features_sha256':sha(PATHS),'training_cache_hashes_used':CACHE_HASHES,'m9_formal_code_sha256':sha(Path(__file__).resolve().parents[2]/'ops/m9_formal_ah.py'),'crown_sqlite_sha256_at_completion':sha(DB),'formal_m9_event_counts_at_completion':dict(formal_counts),'formal_m9_ledger_sha256_at_completion':sha(ledger)}
 (OUT/'coverage_audit.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
