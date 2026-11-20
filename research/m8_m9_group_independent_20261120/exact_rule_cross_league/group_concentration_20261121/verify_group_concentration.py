#!/usr/bin/env python3
"""Independent reconciliation of group-concentration output against source ledger."""
import collections,gzip,hashlib,json,pathlib
P=pathlib.Path(__file__).resolve().parent
SOURCE=P.parent/'exact_rule_cross_league_orders.jsonl.gz'
FROZEN=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
OUT=json.loads((P/'group_concentration_results.json').read_text())
rows=[json.loads(s) for s in gzip.open(SOURCE,'rt',encoding='utf-8') if s.strip()]
errs=[]
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=OUT['source_sha256']:errs.append('source_sha_mismatch')
if hashlib.sha256(FROZEN.read_bytes()).hexdigest()!=OUT['frozen_sha256']:errs.append('frozen_sha_mismatch')
frozen={str(x.get('fid') or x.get('match_id')) for x in map(json.loads,FROZEN.open()) if x}
ids=[str(x['fid']) for x in rows]
if len(set(ids))!=len(ids):errs.append('duplicate_union_fid')
if frozen.intersection(ids):errs.append('frozen_overlap')
if len(rows)!=OUT['union']['n'] or round(sum(float(r['net_u']) for r in rows),6)!=OUT['union']['net_U']:errs.append('union_mismatch')
for g,d in OUT['groups'].items():
 subset=[r for r in rows if r['group']==g]
 if len(subset)!=d['assigned_unique_orders']['n'] or round(sum(float(r['net_u']) for r in subset),6)!=d['assigned_unique_orders']['net_U']:errs.append('group_'+g+'_mismatch')
 for dim,key_field in [('annual','year'),('league','league_id')]:
  for key,expected in d[dim].items():
   part=[r for r in subset if str(r[key_field])==str(key)]
   if len(part)!=expected['n'] or round(sum(float(r['net_u']) for r in part),6)!=expected['net_U']:
    errs.append(f'{g}_{dim}_{key}_mismatch')
part_n=sum(d['assigned_unique_orders']['n'] for d in OUT['groups'].values())
part_u=round(sum(d['assigned_unique_orders']['net_U'] for d in OUT['groups'].values()),6)
if part_n!=OUT['union']['n'] or part_u!=OUT['union']['net_U']:errs.append('partition_mismatch')
result={'pass':not errs,'issues':errs,'source_rows':len(rows),'unique_fids':len(set(ids)),'groups':len(OUT['groups']),'frozen_fids':len(frozen),'frozen_intersection':len(frozen.intersection(ids)),'union_net_U':round(sum(float(r['net_u']) for r in rows),6),'verified_league_year_cells':sum(len(d['league'])+len(d['annual']) for d in OUT['groups'].values())}
(P/'group_concentration_verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if errs:raise SystemExit(1)
