#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent raw Crown AH/FT/settlement check for venue-model candidates."""
import collections,datetime as dt,gzip,hashlib,json,math,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];D=ROOT/'research/m8/venue_environment_20261120'
WORK=Path('/Users/mac/QuantAsiaDesk/research-work');RAW=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses');INDEX=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-response-index.jsonl')
TZ=dt.timezone(dt.timedelta(hours=8));UTC=dt.timezone.utc
def sha(b):return hashlib.sha256(b).hexdigest()
def utc(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 if x.tzinfo is None:x=x.replace(tzinfo=TZ)
 return x.astimezone(UTC)
def settle(line,side,odds,hg,ag):
 h=float(line)*(1 if side=='home' else -1);g=(int(hg)-int(ag))*(1 if side=='home' else -1)
 legs=[h] if abs(h*2-round(h*2))<1e-9 else [math.floor(h*2)/2,math.ceil(h*2)/2]
 return sum(float(odds)-1 if g+x>1e-9 else -1. if g+x< -1e-9 else 0. for x in legs)/len(legs)
def state(line,side,gd):
 h=float(line)*(1 if side=='home' else -1);g=int(gd)*(1 if side=='home' else -1)
 legs=[h] if abs(h*2-round(h*2))<1e-9 else [math.floor(h*2)/2,math.ceil(h*2)/2]
 x=['W' if g+z>1e-9 else 'L' if g+z< -1e-9 else 'P' for z in legs]
 return {'W':'full_win','L':'full_loss','P':'push','WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss'}[''.join(x)]
def main():
 idx={str(x['match_id']):x for x in map(json.loads,INDEX.open())}
 sc={str(x['fid']):x for x in map(json.loads,(WORK/'m8_independent_score_strength_20261114.jsonl').open())}
 rows=[]
 for r in map(json.loads,gzip.open(D/'per_fixture_venue_predictions_20261120.jsonl.gz','rt',encoding='utf8')):
  if r['year'] not in (2024,2025,2026):continue
  rows.append(r)
 out=[];fails=collections.Counter();model_n=collections.Counter();fid_seen=set()
 for r in rows:
  fid=str(r['fid']);fid_seen.add(fid);p=RAW/(fid+'.json')
  if not p.exists():fails['raw_body_missing']+=1;continue
  b=p.read_bytes();bodysha=sha(b);want=idx.get(fid,{}).get('response_sha256')
  if want and want!=bodysha:fails['raw_sha_mismatch']+=1;continue
  try:
   doc=json.loads(b);ms=[z for z in doc.get('data',[]) if str(z.get('id'))==fid]
   if len(ms)!=1:raise ValueError('fid_cardinality')
   m=ms[0];s=sc[fid];ko=utc(s['ko']);local=ko.astimezone(TZ)
   if str(m.get('l_id'))!=str(r['league']) or str(m.get('h_id'))!=str(r['home_id']) or str(m.get('a_id'))!=str(r['away_id']):raise ValueError('identity_mismatch')
   if (int(m['hg']),int(m['ag']))!=(int(s['hg']),int(s['ag'])):raise ValueError('ft_mismatch')
   if local.date().isoformat()!=r['date']:raise ValueError('china_date_mismatch')
   crown=[z for z in m.get('bookmakers',[]) if str(z.get('slug','')).lower()=='crown']
   if len(crown)!=1:raise ValueError('crown_cardinality')
   qs=[]
   for q in crown[0].get('asian_list') or []:
    try:
     qt=utc(q[4]);line,ho,ao=map(float,q[1:4])
     if qt<ko and qt<=ko-dt.timedelta(hours=1) and min(ho,ao)>1 and abs(line*4-round(line*4))<1e-8:qs.append((qt,line,ho,ao))
    except Exception:continue
   if not qs:raise ValueError('no_tminus1_quote')
   qt,line,ho,ao=max(qs,key=lambda z:z[0])
   for x,y,n in ((line,r['line'],'line'),(ho,r['home_odds'],'home_odds'),(ao,r['away_odds'],'away_odds')):
    if abs(x-y)>1e-8:raise ValueError(n+'_mismatch')
   for name,pred in r['models'].items():
    pnl=settle(line,pred['direction'],ho if pred['direction']=='home' else ao,s['hg'],s['ag'])
    st=state(line,pred['direction'],int(s['hg'])-int(s['ag']))
    if abs(pnl-pred['net_u'])>1e-8:raise ValueError(name+'_net_u_mismatch')
    if st!=pred['settlement']:raise ValueError(name+'_state_mismatch')
    model_n[name]+=1
    out.append({'fid':fid,'model':name,'raw_sha256':bodysha,'quote_event_utc':qt.isoformat(),'kickoff_utc':ko.isoformat(),'kickoff_beijing':local.isoformat(),
      'line':line,'home_odds':ho,'away_odds':ao,'FT_home':int(s['hg']),'FT_away':int(s['ag']),'direction':pred['direction'],'settlement':st,'net_u_independent':round(pnl,8),
      'formal_order':False,'historical_http_receipt_asserted':False})
  except Exception as e:fails[str(e)]+=1
 result={'candidate_fids':len(fid_seen),'raw_verified_fids':len({x['fid'] for x in out}),'method_settlement_comparisons':len(out),
  'method_comparisons':dict(model_n),'unverified_candidate_fids':len(fid_seen)-len({x['fid'] for x in out}),
  'failures':dict(fails),'quote_rule':'latest Crown asian_list source-event no later than kickoff minus 60 minutes',
  'full_raw_coverage_pass':not fails and len({x['fid'] for x in out})==len(fid_seen)}
 (D/'independent_crown_ft_audit_20261120.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 with (D/'independent_crown_ft_per_fixture_20261120.jsonl.gz').open('wb') as raw:
  with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz:
   with io.TextIOWrapper(gz,encoding='utf8') as f:
    for z in out:f.write(json.dumps(z,ensure_ascii=False,sort_keys=True)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
