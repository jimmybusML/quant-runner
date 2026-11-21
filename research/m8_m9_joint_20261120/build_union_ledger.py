#!/usr/bin/env python3
"""Build one row per FID in M8 frozen membership union historical M9 predictions."""
import collections, gzip, json
from pathlib import Path

P=Path(__file__).parent
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
mem=[json.loads(x) for x in (ROOT/'m8_foundation_20261115/historical_membership.jsonl').open()]
features={}
for name in ('m8_independent_score_strength_20261114.jsonl','m8_late_full_path_water_features_20261114.jsonl','m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
 p=ROOT/name
 if not p.exists(): continue
 for line in p.open():
  obj=json.loads(line); obj={**obj,**(obj.get('score_row') or {})}; fid=str(obj.get('fid',''))
  if fid: features.setdefault(fid,{}).update(obj)
m8={}
for m in mem:
 f=features.get(str(m['fid']),{})
 if not f: raise RuntimeError(f"missing frozen M8 feature for {m['fid']}")
 m8[str(m['fid'])]={**m,**{k:f.get(k) for k in ('ko','league','home','away','hg','ag','end_line','home_price','away_price')},'source':'m8_frozen_original_eight'}
m9={json.loads(x)['fid']:json.loads(x) for x in (P/'m9_reconstruction_m8_universe.jsonl').open()}
out=P/'m8_m9_unique_fid_union.jsonl.gz'; counts=collections.Counter()
with gzip.open(out,'wt',encoding='utf-8',compresslevel=6) as w:
 for fid in sorted(set(m8)|set(m9),key=lambda x:( (m9.get(x) or {}).get('kickoff_utc') or (m8.get(x) or {}).get('date',''),x)):
  a=m8.get(fid); b=m9.get(fid)
  row={'fid':fid,'kickoff_utc':(b or {}).get('kickoff_utc') or (a or {}).get('ko') or (a or {}).get('date'),'league_id':(b or {}).get('league_id') or (a or {}).get('league'),'m8_member':bool(a),'m8_cohort':(a or {}).get('cohort'),'m8_side':(b or {}).get('m8_side'),'m8_recorded_pnl':(b or {}).get('m8_recorded_pnl') if b else (a or {}).get('pnl'),'m8_line':(a or {}).get('end_line'),'m8_home_odds':(a or {}).get('home_price'),'m8_away_odds':(a or {}).get('away_price'),'m8_ft_home':(a or {}).get('hg'),'m8_ft_away':(a or {}).get('ag'),'m9_prediction_available':bool(b),'m9':b}
  counts['both' if a and b else 'm8_only' if a else 'm9_only']+=1
  w.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'rows':sum(counts.values()),'counts':dict(counts),'output':out.name},indent=2))
