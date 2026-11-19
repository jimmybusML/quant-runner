#!/usr/bin/env python3
"""Independent raw Crown AH and FT settlement verification for microstructure ledgers."""
import collections, datetime as dt, gzip, hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
D=ROOT/'research/m8/crown_market_microstructure_20261120'
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
RESP=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses')
INDEX=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-response-index.jsonl')
LEDGER=D/'per_fixture_event_replay_20261120.jsonl.gz'
SCORES={str(x['fid']):x for x in map(json.loads,(WORK/'m8_independent_score_strength_20261114.jsonl').open())}
FEATURES={str(x['fid']):x for x in map(json.loads,(WORK/'m8_late_full_path_water_features_20261114.jsonl').open())}
INDEXES={str(x['match_id']):x for x in map(json.loads,INDEX.open())}
TZ=dt.timezone(dt.timedelta(hours=8))
def digest(b): return hashlib.sha256(b).hexdigest()
def utc(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 return (x.replace(tzinfo=TZ) if x.tzinfo is None else x).astimezone(dt.timezone.utc)
def settle(line,side,odds,hg,ag):
 ln=float(line)*(1 if side=='home' else -1);gd=(int(hg)-int(ag))*(1 if side=='home' else -1)
 legs=[ln] if abs(ln*2-round(ln*2))<1e-9 else [math.floor(ln*2)/2,math.ceil(ln*2)/2]
 return sum(float(odds)-1 if gd+x>1e-9 else -1. if gd+x< -1e-9 else 0. for x in legs)/len(legs)
def state(line,side,hg,ag):
 ln=float(line)*(1 if side=='home' else -1);gd=(int(hg)-int(ag))*(1 if side=='home' else -1)
 legs=[ln] if abs(ln*2-round(ln*2))<1e-9 else [math.floor(ln*2)/2,math.ceil(ln*2)/2]
 vals=['W' if gd+x>1e-9 else 'L' if gd+x< -1e-9 else 'P' for x in legs]
 return {'W':'full_win','L':'full_loss','P':'push','WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss'}[''.join(vals)]
def main():
 checks=[];fail=collections.Counter();rows=0;fids=set();method_n=collections.Counter()
 for r in map(json.loads,gzip.open(LEDGER,'rt',encoding='utf8')):
  rows+=1;fid=str(r['fid']);fids.add(fid)
  path=RESP/(fid+'.json')
  if not path.exists():fail['raw_body_missing']+=1;continue
  body=path.read_bytes(); body_sha=digest(body)
  expected=INDEXES.get(fid,{}).get('response_sha256')
  if expected and expected!=body_sha:fail['raw_sha_mismatch']+=1;continue
  try:
   doc=json.loads(body);ms=[m for m in doc.get('data',[]) if str(m.get('id'))==fid]
   if len(ms)!=1:raise ValueError('fid_cardinality')
   m=ms[0]; sc=SCORES[fid]; f=FEATURES[fid]
   if (int(m['hg']),int(m['ag']))!=(int(sc['hg']),int(sc['ag'])):raise ValueError('FT_mismatch')
   if str(m['l_id'])!=str(f['league']):raise ValueError('league_mismatch')
   local=utc(m['start']).astimezone(TZ)
   if local.date().isoformat()!=r['date']:raise ValueError('beijing_date_mismatch')
   crown=[b for b in m.get('bookmakers',[]) if str(b.get('slug','')).lower()=='crown']
   if len(crown)!=1:raise ValueError('crown_cardinality')
   # Reconstruct exact latest source quote at or before kickoff minus 60 minutes.
   ko=utc(m['start']); qs=[]
   for q in crown[0].get('asian_list') or []:
    try:
     qt=utc(q[4]);ln,ho,ao=map(float,q[1:4])
     if qt<ko and qt<=ko-dt.timedelta(hours=1) and min(ho,ao)>1 and abs(ln*4-round(ln*4))<1e-8:qs.append((qt,ln,ho,ao))
    except Exception:continue
   if not qs:raise ValueError('no_Tminus1_quote')
   qt,ln,ho,ao=max(qs,key=lambda x:x[0])
   for x,y,n in ((ln,r['line'],'line'),(ho,r['ho'],'home_odds'),(ao,r['ao'],'away_odds')):
    if abs(x-y)>1e-8:raise ValueError(n+'_mismatch')
   pnl=settle(ln,r['direction'],ho if r['direction']=='home' else ao,sc['hg'],sc['ag'])
   if abs(pnl-r['net_u'])>1e-8:raise ValueError('pnl_mismatch')
   if state(ln,r['direction'],sc['hg'],sc['ag'])!=r['settlement']:raise ValueError('state_mismatch')
   checks.append({'fid':fid,'model':r['method'],'raw_sha256':body_sha,'quote_event_utc':qt.isoformat()+'Z','kickoff_utc':ko.isoformat()+'Z','kickoff_beijing':local.isoformat(),
                  'crown_line':ln,'home_odds':ho,'away_odds':ao,'FT_home':int(sc['hg']),'FT_away':int(sc['ag']),'net_u_independent':round(pnl,8),
                  'historical_http_receipt_claimed':False,'formal_order':False})
   method_n[r['method']]+=1
  except Exception as e:fail[str(e)]+=1
 out={'ledger_rows':rows,'unique_fids':len(fids),'raw_verified_rows':len(checks),'raw_verified_unique_fids':len({x['fid'] for x in checks}),
      'independent_settlement_comparisons':len(checks),'methods_verified':dict(method_n),'failures':dict(fail),
      'all_pass':not fail and len(checks)==rows,'quote_policy':'latest Crown asian_list source event no later than kickoff minus 60 minutes','http_receipt_claimed':False}
 (D/'raw_crown_settlement_audit_20261120.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 with gzip.open(D/'raw_crown_settlement_audit_per_fixture_20261120.jsonl.gz','wt',encoding='utf8') as f:
  for x in checks:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
