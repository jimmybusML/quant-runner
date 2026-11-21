#!/usr/bin/env python3
"""Write input/output SHA-256 manifest for the player-pair cohesion study."""
from __future__ import annotations

import hashlib
from pathlib import Path

OUT = Path(__file__).resolve().parent
WORK = Path('/Users/mac/QuantAsiaDesk/research-work')
ROOT = OUT.parents[2]
inputs = [
    WORK / 'm8_foundation_20261115/historical_membership.jsonl',
    WORK / 'm8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl',
    WORK / 'm8_pregame_info_source_20261117/games.csv.gz',
    WORK / 'm8_pregame_info_source_20261117/game_lineups.csv.gz',
    WORK / 'm8_pregame_info_source_20261117/appearances.csv.gz',
    WORK / 'm8_early_joint_market_inventory_20261115.jsonl',
    WORK / 'm8_prior_manager_turnover_20261117.py',
]
outputs = sorted(
    p for p in OUT.iterdir()
    if p.is_file() and p.name != 'SHA256SUMS_20261121.txt'
)

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

lines = []
for path in inputs:
    lines.append(f'{sha(path)}  {path}')
for path in outputs:
    lines.append(f'{sha(path)}  {path.relative_to(ROOT)}')
(OUT / 'SHA256SUMS_20261121.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'wrote {len(inputs)} input and {len(outputs)} output digests')
