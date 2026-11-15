import json,collections,hashlib,datetime,re
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_early_exact_cross_market_consistency_20261115.py').read_text()
exec(src[:src.index('C=collections.Counter();rows=[]')])
P=R
candidates=[v for v in map(json.loads,(P/'m8_espn_additional_cache_candidates_20261115.jsonl').open()) if not v['league_explicit']]
mapping={'116':('China Super League','chn.1'),'12':('Italy Serie A','ita.1'),'141':('Greece Super League 1','gre.1'),'145':('Colombia Primera A','col.1'),'16':('Germany Bundesliga I','ger.1'),'25':('France Ligue 1','fra.1'),'262':('Scotland Premiership','sco.1'),'290':('Saudi Arabia Pro League','ksa.1'),'31':('Belgium First Division A','bel.1'),'37':('Netherlands Eredivisie','ned.1'),'51':('Portugal Primeira Liga','por.1'),'62':('Türkiye Super Lig','tur.1'),'66':('Sweden Allsvenskan','swe.1'),'70':('Denmark Superligaen','den.1'),'73':('Japan J-League','jpn.1'),'88':('Norway Eliteserien','nor.1')}
verified=[];errors=collections.Counter()
for v in candidates:
 try:
  r=v['record'];raw=Path(v['source']).read_bytes();assert hashlib.sha256(raw).hexdigest()==v['sha256']
  e=next(e for e in json.loads(raw)['events'] if str(e['id'])==r['espn_id'])
  codes={m.group(1) for a in e.get('links',[]) if (m:=re.search('/league/([^/?]+)',a.get('href','')))}
  f,sha,lid=jobs[r['fid']];raw2=f.read_bytes();assert not sha or hashlib.sha256(raw2).hexdigest()==sha
  x=next(q for q in json.loads(raw2)['data'] if str(q['id'])==r['fid'])
  name,code=mapping[r['league']]
  assert codes=={code} and str(x['l_id'])==str(lid)==r['league'] and x['l']==name
  assert dt(x['start']).isoformat()==r['ko'] and str(x['h_id'])==r['home'] and str(x['a_id'])==r['away'] and (int(x['hg']),int(x['ag']))==(r['hg'],r['ag']) and x['status']=='full'
  verified.append({**v,'league_explicit':True,'league_evidence':{'crown_name':name,'espn_link_code':code,'espn_uid':e.get('uid')}})
 except Exception as e:errors[type(e).__name__]+=1
assert len({v['record']['fid'] for v in verified})==len(verified)
base=list(map(json.loads,(P/'m8_espn_performance_confirmed_expanded_20261115.jsonl').open()))
assert not {r['fid'] for r in base}&{v['record']['fid'] for v in verified}
allrows=base+[v['record'] for v in verified]
out={'prior_confirmed':len(base),'candidate_n':len(candidates),'new_verified':len(verified),'total_unique':len(allrows),'leagues':dict(collections.Counter(r['league'] for r in allrows)),'years':dict(collections.Counter(r['year'] for r in allrows)),'new_date_min':min(v['record']['date'] for v in verified),'new_date_max':max(v['record']['date'] for v in verified),'errors':dict(errors),'source':'ESPN cached team/player-stat link codes, original Crown league IDs/names, raw identity recheck; no API requests'}
(P/'m8_espn_league_identity_recovery_20261115.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
(P/'m8_espn_league_identity_recovery_20261115.jsonl').write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in verified))
(P/'m8_espn_performance_confirmed_18leagues_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in allrows))
print('IDENTITY',json.dumps(out,ensure_ascii=False),flush=True)
