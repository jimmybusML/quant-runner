#!/usr/bin/env python3
"""Independent AH settlement and ledger integrity check."""
import collections,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];D=ROOT/'research/m8/next_round_20261120'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def classify(line,side,gd):
 signed=float(line) if side=='home' else -float(line);diff=int(gd) if side=='home' else -int(gd)
 if abs(signed*2-round(signed*2))<1e-9:legs=(signed,signed)
 else:legs=(math.floor(signed*2)/2,math.ceil(signed*2)/2)
 states=[]
 for hcap in legs:
  out=diff+hcap;states.append('W' if out>1e-9 else 'L' if out< -1e-9 else 'P')
 return {'WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss','W':'full_win','L':'full_loss','P':'push'}.get(''.join(states),states[0])
def settle(line,side,odds,gd):
 signed=float(line)*(1 if side=='home' else -1);diff=int(gd)*(1 if side=='home' else -1)
 # Independently split quarter contracts into adjacent half-goal legs.
 if abs(signed*2-round(signed*2))<1e-9:legs=(signed,signed)
 else:legs=(math.floor(signed*2)/2,math.ceil(signed*2)/2)
 ret=[]
 for hcap in legs:
  outcome=diff+hcap
  ret.append(float(odds)-1 if outcome>1e-9 else -1.0 if outcome< -1e-9 else 0.0)
 return sum(ret)/2
rows=[]
with gzip.open(D/'per_fixture_walkforward_20261120.jsonl.gz','rt') as f:
 for line in f:
  if not line.strip():continue
  x=json.loads(line);side=x['direction'];odds=x['crown_home_odds'] if side=='home' else x['crown_away_odds']
  p=settle(x['crown_ah_line_home'],side,odds,x['goal_difference_home'])
  assert abs(p-x['net_u'])<1e-8,(x['fid'],p,x['net_u'])
  assert classify(x['crown_ah_line_home'],side,x['goal_difference_home'])==x['settlement'],(x['fid'],x['settlement'])
  assert x['FT_home']-x['FT_away']==x['goal_difference_home']
  if side=='home':base=settle(x['crown_ah_line_home'],'home',x['crown_home_odds'],x['goal_difference_home'])
  else:base=settle(x['crown_ah_line_home'],'away',x['crown_away_odds'],x['goal_difference_home'])
  assert abs(base-x['net_u'])<1e-8
  rows.append(x)
by=collections.defaultdict(list)
for x in rows:by[x['model']].append(x)
assert all(len({x['fid'] for x in v})==len(v) for v in by.values())
assert set(by)=={'market_contract','linear','spline_contract'}
expected=3*21455
assert len(rows)==expected,(len(rows),expected)
res={'ledger_rows':len(rows),'distinct_fids_per_method':{k:len({x['fid'] for x in v}) for k,v in by.items()},'independent_ah_settlements_recomputed':len(rows),'net_u_matches':True,'ft_margin_matches':True,'input_ledger_sha256':sha(D/'per_fixture_walkforward_20261120.jsonl.gz'),'five_state_counts':{k:dict(collections.Counter(x['settlement'] for x in v)) for k,v in by.items()},'model_year_profit_recomputed':{k:{str(y):round(sum(x['net_u'] for x in v if x['year']==y),6) for y in sorted({x['year'] for x in v})} for k,v in by.items()}}
(D/'independent_settlement_audit_20261120.json').write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps(res,indent=2))
