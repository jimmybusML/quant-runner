#!/usr/bin/env python3
import hashlib
from pathlib import Path
P=Path(__file__).parent
exclude={'SHA256SUMS.txt','__pycache__'}
files=sorted(p for p in P.iterdir() if p.is_file() and p.name not in exclude)
with (P/'SHA256SUMS.txt').open('w') as w:
 for p in files:
  h=hashlib.sha256(p.read_bytes()).hexdigest()
  w.write(f'{h}  {p.name}\n')
print(f'wrote {len(files)} hashes')
