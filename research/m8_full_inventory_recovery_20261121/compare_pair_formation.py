import gzip,json,collections
from pathlib import Path
p=Path('/Users/mac/.codex/worktrees/m8-discipline-referee/quant-runner-m8-goalkeeper/research/m8')
out=Path(__file__).resolve().parent
files={'pair':p/'player_pair_cohesion_20261121/pair_cohesion_per_fixture_20261121.jsonl.gz','formation':p/'prior_formation_market_20261121/formation_market_per_fixture_20261121.jsonl.gz','expanded_pair':p/'player_pair_expanded15_20261121/pooled_pair_cohesion_market_plus_pair_ledger.jsonl.gz'}
groups={}
for name,path in files.items():
 d=collections.defaultdict(dict)
 with gzip.open(path,'rt') as f:
  for line in f:
   r=json.loads(line)
   if r.get('frozen_overlap'):continue
   d[str(r['fid'])][r['method']]=r
 groups[name]=d
 print(name,'FID',len(d),'METHODS',collections.Counter(tuple(sorted(v)) for v in d.values()).most_common(3))
for name,d in groups.items():
 print(name,'example',next(iter(d.values())).keys())
a,b=groups['pair'],groups['formation']
common=set(a)&set(b)
print('OVERLAP',len(common),'pair',len(a),'formation',len(b),'expanded_vs_pair',len(set(groups['expanded_pair'])&set(a)),'expanded_vs_formation',len(set(groups['expanded_pair'])&set(b)))
res={'source_files':{k:str(v) for k,v in files.items()},'counts':{'pair':len(a),'formation':len(b),'common':len(common),'expanded_pair':len(groups['expanded_pair'])},'year':{}}
for year in [2024,2025,2026]:
 ids=[i for i in common if next(iter(a[i].values()))['year']==year]
 z={'n':len(ids),'methods':{}}
 for src,methods in [('pair',['market_only','pair_only','market_plus_pair']),('formation',['market_only','formation_only','market_plus_formation'])]:
  for m in methods:
   rows=[(a if src=='pair' else b)[i].get(m) for i in ids]
   rows=[r for r in rows if r]
   z['methods'][src+':'+m]={'n':len(rows),'net_u':round(sum(r['net_u'] for r in rows),3),'ROI_pct':round(100*sum(r['net_u'] for r in rows)/len(rows),3) if rows else None}
 res['year'][year]=z
print(json.dumps(res,indent=2))
(out/'pair_formation_same_fid_audit.json').write_text(json.dumps(res,indent=2))

def settle(r,side):
 line=float(r['T12_AH_home_line'])*(1 if side=='home' else -1)
 odds=float(r['T12_home_odds'] if side=='home' else r['T12_away_odds'])
 margin=(int(r['hg'])-int(r['ag']))*(1 if side=='home' else -1)
 def leg(v):
  x=margin+v
  return odds-1 if x>1e-9 else -1.0 if x< -1e-9 else 0.0
 q=round(line*4)
 return (leg(line-.25)+leg(line+.25))/2 if abs(q)%2 else leg(line)
combined=[]
for fid in sorted(common):
 pr=a[fid]['market_plus_pair'];fr=b[fid]['market_plus_formation']
 # Only compare when underlying AH contract is identical.
 fields=['T12_AH_home_line','T12_home_odds','T12_away_odds','hg','ag']
 if any(pr[k]!=fr[k] for k in fields):continue
 eh=(float(pr['home_EV_U'])+float(fr['home_EV_U']))/2
 ea=(float(pr['away_EV_U'])+float(fr['away_EV_U']))/2
 side='home' if eh>=ea else 'away'
 combined.append({'fid':fid,'year':pr['year'],'side':side,'net_u':settle(pr,side),'pair_side':pr['chosen_side'],'formation_side':fr['chosen_side'],'pair_net_u':pr['net_u'],'formation_net_u':fr['net_u']})
print('COMBINED_CONTRACT_IDENTICAL',len(combined),'excluded',len(common)-len(combined))
for y in [2024,2025,2026]:
 rows=[r for r in combined if r['year']==y];same=sum(r['pair_side']==r['formation_side'] for r in rows)
 print('COMBINED',y,'n',len(rows),'net',round(sum(r['net_u'] for r in rows),3),'roi',round(100*sum(r['net_u'] for r in rows)/len(rows),3) if rows else None,'agree',same)
print('COMBINED_TOTAL',len(combined),round(sum(r['net_u'] for r in combined),3),'AGREEMENT',sum(r['pair_side']==r['formation_side'] for r in combined))
with (out/'pair_formation_fixed_equal_EV_ledger.jsonl').open('w') as f:
 for r in combined:f.write(json.dumps(r)+'\\n')
res['fixed_equal_EV']={'n':len(combined),'net_u':round(sum(r['net_u'] for r in combined),3),'agreement_n':sum(r['pair_side']==r['formation_side'] for r in combined),'by_year':{str(y):{'n':sum(r['year']==y for r in combined),'net_u':round(sum(r['net_u'] for r in combined if r['year']==y),3)} for y in [2024,2025,2026]}}
(out/'pair_formation_same_fid_audit.json').write_text(json.dumps(res,indent=2))
