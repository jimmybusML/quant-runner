#!/usr/bin/env python3
import hashlib,pathlib
root=pathlib.Path(__file__).resolve().parent
manifest=root/'SHA256SUMS_20261121.txt'
files=sorted(p for p in root.iterdir() if p.is_file() and p.name!=manifest.name)
lines=[]
for p in files:
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 lines.append(f'{h}  {p.name}')
manifest.write_text('\n'.join(lines)+'\n',encoding='utf8')
print(f'wrote {manifest} with {len(lines)} file hashes')
