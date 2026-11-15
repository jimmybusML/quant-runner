import json,collections,hashlib,statistics,math
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
ep={r['fid']:r for r in map(json.loads,(P/'m8_espn_performance_confirmed_18leagues_20261115.jsonl').open())}
tc={};duplicates=[];sources={}
for path in [P/'m8_performance_batch_probe_20261115.jsonl',P/'m8_performance_cross_year_20261115/verified_new.jsonl',P/'m8_performance_contiguous_20261115/verified_new.jsonl']:
 if not path.exists():continue
 for r in map(json.loads,path.open()):
  f=r['fid']
  if f in tc:duplicates.append(f);continue
  tc[f]=r;sources[f]=str(path.relative_to(P))
def compare(f):
 a,b=ep[f],tc[f]
 assert all(str(a[k])==str(b[k]) for k in ('league','home','away','hg','ag','date'))
 assert a['ko']==b['kickoff_utc']
 v={'fid':f,'league':a['league'],'date':a['date']}
 for key,ev,tv in [('shots',[a['hshots'],a['ashots']],None if b['shot_on'] is None or b['shot_off'] is None else [x+y for x,y in zip(b['shot_on'],b['shot_off'])]),('sot',[a['hsot'],a['asot']],b['shot_on']),('possession',[a['hposs'],a['aposs']],b['possess'])]:
  if tv is not None:v[key]=[x-y for x,y in zip(ev,tv)]
 return v
overlap=[compare(f) for f in sorted(ep.keys()&tc.keys())]
def fieldstat(rows,key):
 vals=[v[key] for v in rows if key in v];d=[x for a in vals for x in a]
 return {'available_fixtures':len(vals),'exact_both':sum(all(abs(x)<1e-9 for x in a) for a in vals),'within_1_both':sum(all(abs(x)<=1 for x in a) for a in vals),'mean_abs_difference_per_team':round(statistics.mean(abs(x) for x in d),4) if d else None,'max_abs_difference':max(map(abs,d)) if d else None,'mean_signed_ESPN_minus_TotalCorner':round(statistics.mean(d),4) if d else None}
targets={r['fid']:r for r in map(json.loads,(P/'m8_early_joint_market_inventory_20261115.jsonl').open()) if r['T']==12}
coverage={}
for name,lid in [('Bundesliga','16'),('Ligue1','25')]:
 v=sorted([r for r in tc.values() if r['league']==lid and sources[r['fid']]!='m8_performance_batch_probe_20261115.jsonl'],key=lambda x:x['date'])
 if v:
  a,b=v[0]['date'],v[-1]['date'];q={r['fid'] for r in targets.values() if r['league']==lid and a<=r['date']<=b}
  coverage[name]={'date_min':a,'date_max':b,'TC_verified':len(v),'T12_in_range':len(q),'T12_with_TC':len(q&tc.keys()),'uncovered':len(q-tc.keys()),'year_counts':dict(collections.Counter(r['date'][:4] for r in v))}
m=json.load((P/'m8_foundation_20261115/manifest.json').open())
check={'membership':hashlib.sha256((P/m['historical_membership']['local_file']).read_bytes()).hexdigest()==m['historical_membership']['sha256'],'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['input_sha256'].items()),'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['script_sha256'].items())}
out={'ESPN_n':len(ep),'TotalCorner_n':len(tc),'TC_duplicate_ids':len(duplicates),'cross_source_overlap':len(overlap),'unique_union':len(ep.keys()|tc.keys()),'overlap_by_league':dict(collections.Counter(r['league'] for r in overlap)),'field_comparison':{k:fieldstat(overlap,k) for k in ('shots','sot','possession')},'field_comparison_by_league':{l:{k:fieldstat([r for r in overlap if r['league']==l],k) for k in ('shots','sot','possession')} for l in sorted({r['league'] for r in overlap})},'TC_fields_nonzero':{k:sum(r.get(k) is not None and sum(r[k])>0 for r in tc.values()) for k in ('shot_on','shot_off','attacks','dang_attacks','possess','xg')},'TC_counts_by_league_year':{l:dict(collections.Counter(r['date'][:4] for r in tc.values() if r['league']==l)) for l in sorted({r['league'] for r in tc.values()})},'contiguous_T12_coverage':coverage,'foundation_sha_check':check,'notes':'ESPN totalShots versus TotalCorner shot_on+shot_off is an empirical comparison only; differing definitions not assumed equivalent. Preserve sources, not an averaged dataset or a new model.'}
(P/'m8_performance_cross_source_audit_20261115.json').write_text(json.dumps(out,indent=2))
(P/'m8_performance_cross_source_audit_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in overlap))
print(json.dumps(out),flush=True)
