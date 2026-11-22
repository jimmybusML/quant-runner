#!/usr/bin/env python3
"""Write SHA256SUMS.txt for frozen research inputs and all deliverable artifacts."""
import hashlib,pathlib
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[2]
EXTERNAL={
 '/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl':'frozen membership',
 '/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl':'expanded finished schedule',
 '/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3':'read-only Crown quote SQLite',
 '/Users/mac/QuantAsiaDesk/research-work/m8_frozen_eight_earlier_window_replay_20261116.py':'original 6/3/1 direction and path replay',
 '/Users/mac/QuantAsiaDesk/research-work/m8_raw_capture_unindexed_frozen_replay_20261115.py':'original independent score model and E/F logic',
}
REPO_INPUTS={
 'research/m8/M8_FOUNDATION_MANIFEST_20261115.json':'frozen input manifest',
 'research/m8/m8_frozen_eight_boundary_expansion_20261119.py':'frozen exact classifier and settlement audit code',
}
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
lines=['M8 exact-rule cross-league replay SHA256 manifest','']
for name,label in EXTERNAL.items():
 p=pathlib.Path(name)
 if not p.exists():raise FileNotFoundError(p)
 lines.append(f'INPUT {sha(p)}  {label}  {p}')
for rel,label in REPO_INPUTS.items():
 p=ROOT/rel
 if not p.exists():raise FileNotFoundError(p)
 lines.append(f'INPUT {sha(p)}  {label}  {rel}')
lines.append('')
for p in sorted(OUT.rglob('*')):
 if not p.is_file() or p.name=='SHA256SUMS.txt' or '__pycache__' in p.parts or p.suffix=='.pyc':continue
 lines.append(f'OUTPUT {sha(p)}  {p.relative_to(ROOT)}')
(OUT/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
print('manifest entries',len(lines)-2)
