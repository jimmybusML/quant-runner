#!/usr/bin/env python3
"""Independent raw Crown response and quarter-line settlement verifier."""
import collections,datetime as dt,gzip,hashlib,json,math,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
OUT=ROOT/'research/m8/cross_competition_team_pricing_20261119'
LEDGER=OUT/'cross_competition_team_pricing_predictions_20261119.jsonl.gz'
FEATURE=WORK/'m8_late_full_path_water_features_20261114.jsonl'
def sha(b):return hashlib.sha256(b).hexdigest()
def utc(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 return x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc) if x.tzinfo is None else x.astimezone(dt.timezone.utc)
def settle(line,side,hg,ag,odds):
 line=float(line);odds=float(odds)
 if abs(line*4-round(line*4))>1e-8:raise ValueError('non-quarter-line')
 legs=[line] if abs(round(line*2)/2-line)<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 values=[]
 for x in legs:
  margin=int(hg)-int(ag)+x if side=='home' else int(ag)-int(hg)-x
  values.append(odds-1 if margin>1e-9 else -1. if margin < -1e-9 else 0.)
 return sum(values)/len(values)
features={str(x['fid']):x for x in map(json.loads,FEATURE.open())}
loc={}
for name in ('m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1733Z.jsonl','m7_original49_historical_Crown_T30_2h_movement_inventory_20261114.jsonl'):
 p=WORK/'m7'/name
 if p.exists():
  for x in map(json.loads,p.open()):
   fid=str(x['fixture_id'])
   if x.get('source_file'):loc.setdefault(fid,{'path':x['source_file'],'sha':x.get('raw_sha256')})
for name in ('m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
 p=WORK/name
 if p.exists():
  for x in map(json.loads,p.open()):
   fid=str(x['fid'])
   if x.get('source_file'):loc.setdefault(fid,{'path':x['source_file'],'sha':x.get('raw_sha256')})
idxp=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-response-index.jsonl')
idx={str(x['match_id']):x for x in map(json.loads,idxp.open())}
for fid,f in features.items():
 if int(f['year'])==2026:
  loc[fid]={'path':str(pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses')/(fid+'.json')),'sha':idx.get(fid,{}).get('response_sha256')}
checks=[];fail=collections.Counter();settle_n=0;ledger_n=0;ledger_fids=set()
for line in gzip.open(LEDGER,'rt',encoding='utf-8'):
 r=json.loads(line);ledger_n+=1;fid=str(r['fid']);ledger_fids.add(fid);f=features.get(fid);source=loc.get(fid)
 if not f:fail['feature_row_missing']+=1;continue
 if not source or not pathlib.Path(source['path']).is_file():fail['raw_body_missing']+=1;continue
 body=pathlib.Path(source['path']).read_bytes();bodysha=sha(body)
 if source.get('sha') and bodysha!=source['sha']:fail['raw_sha_mismatch']+=1;continue
 try:doc=json.loads(body)
 except Exception:fail['bad_json']+=1;continue
 data=doc.get('data');matches=data if isinstance(data,list) else [data] if isinstance(data,dict) else []
 match=[x for x in matches if str(x.get('id'))==fid]
 if len(match)!=1:fail['raw_fid_cardinality']+=1;continue
 m=match[0]
 try:
  ko=utc(m['start']);hg=int(m['hg']);ag=int(m['ag'])
  if str(m.get('l_id'))!=str(r['league']) or str(m.get('h_id'))!=str(r['home_team_id']) or str(m.get('a_id'))!=str(r['away_team_id']):raise ValueError('identity')
  if (hg,ag)!=(int(r['FT_home']),int(r['FT_away'])):raise ValueError('FT')
  ko_cn=ko.astimezone(dt.timezone(dt.timedelta(hours=8)))
  if ko_cn.date().isoformat()!=str(r['date']):raise ValueError('kickoff-China-date')
  crown=[x for x in m.get('bookmakers',[]) if str(x.get('slug','')).lower()=='crown']
  if len(crown)!=1:raise ValueError('Crown cardinality')
  quotes=[]
  for x in crown[0].get('asian_list') or []:
   try:
    qt=utc(x[4]);ln,ho,ao=map(float,x[1:4])
    if qt<ko and qt<=ko-dt.timedelta(hours=1) and min(ho,ao)>1 and abs(ln*4-round(ln*4))<1e-8:quotes.append((qt,ln,ho,ao))
   except Exception:continue
  if not quotes:raise ValueError('no valid T-1 Crown quote')
  qt,ln,ho,ao=sorted(quotes,key=lambda x:x[0])[-1]
  if any(abs(a-b)>1e-8 for a,b in ((ln,float(r['AH_home_line'])),(ho,float(r['AH_home_odds'])),(ao,float(r['AH_away_odds'])))):raise ValueError('quote mismatch')
  for name,p in r['methods'].items():
   side=p['selected_side'];odds=ho if side=='home' else ao;actual=settle(ln,side,hg,ag,odds)
   if abs(actual-float(p['pnl']))>1e-7:raise ValueError('payout mismatch '+name)
  settle_n+=len(r['methods'])
  checks.append({'fid':fid,'year':r['year'],'raw_body_sha256':bodysha,'quote_event_utc':qt.isoformat(),'kickoff_utc':ko.isoformat(),'kickoff_china':ko_cn.isoformat(),'AH_home_line':ln,'AH_home_odds':ho,'AH_away_odds':ao,'FT_home':hg,'FT_away':ag,'all_methods_reproduced':True,'source_event_time_is_not_http_receipt_time':True})
 except Exception as e:fail[str(e)]+=1
summary={'study':'M8_CROSS_COMPETITION_TEAM_PRICING_RAW_CROWN_AH_INDEPENDENT_VERIFICATION_20261119','ledger_rows':ledger_n,'ledger_unique_fids':len(ledger_fids),'raw_Crown_and_FT_verified_fids':len(checks),'failures':dict(fail),'settlement_comparisons':settle_n,'all_verified_method_settlements_match':settle_n==len(checks)*5,'method':'Independent reread of archived raw Crown response body; verify body SHA when indexed, FID/league/team IDs, Beijing-time kickoff, trusted FT, exact latest Crown asian_list quote no later than T-1 hour, and quarter-line side payoff for every model. Event quote timestamps do not establish HTTP receipt time.'}
(OUT/'INDEPENDENT_RAW_CROWN_SETTLEMENT_AUDIT_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with gzip.open(OUT/'independent_raw_crown_audit_20261119.jsonl.gz','wt',encoding='utf-8') as f:
 for x in checks:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
