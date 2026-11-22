#!/usr/bin/env python3
"""Create a consistent private read-only SQLite backup for the M8 replay."""
from __future__ import annotations
import argparse, hashlib, pathlib, sqlite3, time, json

def digest(path: pathlib.Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',default='/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    src_path=pathlib.Path(args.source); out_path=pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True,exist_ok=True)
    if out_path.exists(): out_path.unlink()
    src=sqlite3.connect(f'file:{src_path}?mode=ro',uri=True,timeout=60)
    dst=sqlite3.connect(out_path)
    t=time.monotonic(); src.backup(dst,pages=20000,sleep=0.05)
    check=dst.execute('PRAGMA quick_check').fetchone()[0]
    if check!='ok': raise RuntimeError(f'quick_check={check}')
    dst.close(); src.close()
    print(json.dumps({'source':str(src_path),'snapshot':str(out_path),'quick_check':check,
      'size_bytes':out_path.stat().st_size,'sha256':digest(out_path),'elapsed_seconds':round(time.monotonic()-t,2)},indent=2))
if __name__=='__main__': main()
