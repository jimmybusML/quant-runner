#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 research/m8_m9_joint_20261120/rebuild_m9_m8_joint.py
python3 research/m8_m9_joint_20261120/audit_sources.py
PYTHONPATH=. python3 research/m8_m9_joint_20261120/summarize_results.py
python3 research/m8_m9_joint_20261120/build_union_ledger.py
python3 - <<'PYCODE'
from pathlib import Path
p=Path("research/m8_m9_joint_20261120/m9_reconstruction_m8_universe.jsonl")
with p.open("rb") as src, p.with_suffix(".jsonl.gz").open("wb") as _:
    pass
import gzip
with p.open("rb") as src, gzip.open(str(p)+".gz","wb",compresslevel=6) as dst:
    while True:
        chunk=src.read(1024*1024)
        if not chunk: break
        dst.write(chunk)
p.unlink()
PYCODE
python3 research/m8_m9_joint_20261120/make_sha256.py
