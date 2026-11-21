"""Explain 2025 pair/formation disagreement without introducing any selection rule."""
import gzip,json,collections,math,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=Path('/Users/mac/.codex/worktrees/m8-discipline-referee/quant-runner-m8-goalkeeper/research/m8')
def read(p):
 with gzip.open(p,'rt') as f:
  for line in f:yield json.loads(line)
F={r['fid']:r for r in read(P/'pair_formation_reprice_sameFID.jsonl.gz')}
B={r['fid']:r for r in read(P/'full_pool_market_paired.jsonl.gz')}
pools={}
for short,path in [
 ('pair',ROOT/'player_pair_cohesion_20261121/pair_cohesion_per_fixture_20261121.jsonl.gz'),
 ('formation',ROOT/'prior_formation_market_20261121/formation_market_per_fixture_20261121.jsonl.gz')]:
 groups=collections.defaultdict(dict)
 for r in read(path):
  if r['fid'] not in F:continue
  groups[str(r['fid'])][r['method']]=r
 pools[short]=groups
rows=[]
for r in F.values():
 q=B[r['fid']]
 methods={**{'pair.'+k:v for k,v in pools['pair'][r['fid']].items()},
          **{'formation.'+k:v for k,v in pools['formation'][r['fid']].items()}}
 assert len(methods)==6,(r['fid'],list(methods))
 z=dict(r)
 z['T6_all_home_U']=q['home_u'];z['T6_all_away_U']=q['away_u']
 z['T6_low_odds_U']=q['lower_odds_net_u']
 for name,m in methods.items():
  z[name+'.net_U_T12']=m['net_u']
  z[name+'.side']=m['chosen_side']
  z[name+'.net_U_T6']=q['home_u'] if m['chosen_side']=='home' else q['away_u']
 rows.append(z)
conf=collections.defaultdict(list)
for r in rows:
 if not r['conflict']:continue
 conf[r['year']].append(r)
fields=['T6_all_home_U','T6_all_away_U','T6_low_odds_U',
 'pair.market_only.net_U_T12','pair.pair_only.net_U_T12','pair.market_plus_pair.net_U_T12',
 'formation.market_only.net_U_T12','formation.formation_only.net_U_T12','formation.market_plus_formation.net_U_T12',
 'pair.market_only.net_U_T6','pair.pair_only.net_U_T6','pair.market_plus_pair.net_U_T6',
 'formation.market_only.net_U_T6','formation.formation_only.net_U_T6','formation.market_plus_formation.net_U_T6']
summary={'coverage':{'full_priced_outside':26523,'optional_both_FID':len(rows),
 'conflict_total':sum(len(x) for x in conf.values())},
 'annual_conflict':{},'2025_conflict_leagues':{},'caveats':[
 '2025 conflict sample was discovered retrospectively; no untouched OOS or family-wise corrected inference',
 'Pair pipeline and formation pipeline market_only models use different training universes',
 'T6 repricing uses T12 model directions; features not shown to be historically accessible at real betting time',
 'No rule change; all priced FIDs stay in research inventory']}
for year,items in sorted(conf.items()):
 n=len(items)
 v={key:round(sum(float(r[key]) for r in items),3) for key in fields}
 summary['annual_conflict'][str(year)]={'n':n,'net_U':v,
 'ROI_pct':{k:round(100*x/n,3) for k,x in v.items()},
 'formation_home_n':sum(r['formation_side']=='home' for r in items),
 'formation_lower_odds_n':sum(r['T6_price_formation']<r['T6_price_pair'] for r in items),
 'line_changed_T12_to_T6_n':sum(r['T6_line_home']!=r['T12_line_home'] for r in items)}
 if year==2025:
  groups=collections.defaultdict(list)
  for r in items:groups[r['league']].append(r)
  summary['2025_conflict_leagues']={str(l):{'n':len(v),
    'formation_T6_U':round(sum(x['T6_formation_u'] for x in v),3),
    'pair_T6_U':round(sum(x['T6_pair_u'] for x in v),3),
    'delta_U':round(sum(x['T6_delta_formation_minus_pair'] for x in v),3),
    'formation_home_n':sum(x['formation_side']=='home' for x in v)}
    for l,v in sorted(groups.items(),key=lambda x:-len(x[1]))}
(P/'conflict_explanation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
with gzip.open(P/'six_method_conflict_sameFID.jsonl.gz','wt') as f:
 for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
print(json.dumps({'n':summary['coverage'],'annual':summary['annual_conflict'],
 '2025_top_leagues':summary['2025_conflict_leagues']},ensure_ascii=False,indent=2),flush=True)
