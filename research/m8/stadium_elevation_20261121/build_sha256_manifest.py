#!/usr/bin/env python3
"""Create an auditable SHA256 manifest for the stadium-elevation study."""
from __future__ import annotations
import datetime as dt, hashlib, json, pathlib, subprocess

OUT = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
MANIFEST = OUT / 'SHA256_MANIFEST_20261121.json'
EXTERNAL = [
    pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3'),
    pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl'),
    pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_pregame_info_source_20261117/games.csv.gz'),
    pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_pregame_info_source_20261117/competitions.csv.gz'),
    pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl'),
    ROOT / 'research/m8/venue_environment_20261120/venue_identity_cohort_20261120.jsonl.gz',
    ROOT / 'research/m8/exact_rules_outside_original49_20261120/exact_rule_cross_league_all_complete_paths.jsonl.gz',
]

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

def main():
    local = sorted(p for p in OUT.rglob('*') if p.is_file() and p != MANIFEST)
    outputs = {p.relative_to(ROOT).as_posix(): digest(p) for p in local}
    inputs = {}
    for p in EXTERNAL:
        inputs[str(p)] = digest(p) if p.exists() else None
    payload = {'study': 'M8_STADIUM_ELEVATION_AH_20261121',
        'created_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'repository': 'jimmybusML/quant-runner',
        'branch': subprocess.run(['git', 'branch', '--show-current'], cwd=ROOT, text=True,
                                 capture_output=True, check=True).stdout.strip(),
        'parent_commit_at_manifest_time': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True,
                                 capture_output=True, check=True).stdout.strip(),
        'algorithm': 'SHA-256', 'external_inputs': inputs, 'study_files_and_outputs': outputs,
        'note': 'Manifest excludes itself. Raw Nominatim/SRTM API payload SHA values are also preserved in their response caches/manifests; the Crown verifier preserves each independently checked raw response SHA per FID.'}
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'manifest': str(MANIFEST), 'local_files': len(outputs),
                      'external_inputs': len(inputs), 'crown_sqlite_sha256': inputs[str(EXTERNAL[0])],
                      'branch': payload['branch'], 'parent_commit_at_manifest_time': payload['parent_commit_at_manifest_time']},
                     ensure_ascii=False))

if __name__ == '__main__':
    main()
