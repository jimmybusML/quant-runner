#!/usr/bin/env python3
"""Build the public M8 research execution and SHA256 inventory manifest."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTDIR = ROOT / 'research/m8/independent_info_20261119'
MANIFEST = ROOT / 'research/m8/M8_INDEPENDENT_INFORMATION_EXPANSION_EXECUTION_20261119.json'
INPUTS = [
    Path('/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl'),
    Path('/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl'),
    Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl'),
    ROOT / 'research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl',
    ROOT / 'research/m8/selective_decomposition_20261120/M8_SELECTIVE_DECOMPOSITION_RESULTS_20261120.json',
    Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3'),
]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    inputs = {}
    for path in INPUTS:
        if path.exists():
            inputs[str(path)] = {'bytes': path.stat().st_size, 'sha256': digest(path),
                                 'included_in_public_commit': False}
        else:
            inputs[str(path)] = {'available': False, 'included_in_public_commit': False}
    outputs = {}
    handoff = ROOT / 'PROJECT_HANDOFF.md'
    if handoff.exists():
        outputs[str(handoff.relative_to(ROOT))] = {'bytes': handoff.stat().st_size,
                                                  'sha256': digest(handoff)}
    for path in sorted((ROOT / 'research/m8').glob('M8_INDEPENDENT_INFORMATION_EXPANSION_20261119.md')):
        outputs[str(path.relative_to(ROOT))] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
    for path in sorted(OUTDIR.rglob('*')):
        if path.is_file():
            outputs[str(path.relative_to(ROOT))] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
    data = {
        'study': 'M8 independent pregame information and expansion research',
        'executed_at_local': '2026-11-19 Asia/Shanghai',
        'repository': 'jimmybusML/quant-runner',
        'base_public_main_commit': 'e42750e0e727102a4fff005623b56220115a7d5d',
        'research_only': True,
        'production_models_telegram_ledger_frozen': True,
        'frozen_eight_sha256': '6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665',
        'commands': [
            'python3 research/m8/independent_info_20261119/team/run_team_familiarity.py',
            'python3 research/m8/independent_info_20261119/context/h2h_mechanism.py',
            'python3 research/m8/independent_info_20261119/execution/analyze_receipt_quote_freshness.py',
            'python3 research/m8/independent_info_20261119/integrate_overlap_union.py',
            'python3 research/m8/independent_info_20261119/build_execution_manifest.py',
            'git diff --check',
        ],
        'input_artifacts': inputs,
        'output_sha256_and_bytes': outputs,
        'integrity_notes': {
            'ah_settlement': 'Quarter lines split into two half-stake legs; away margin reverses the home line; verified FT and actual Crown prices retained.',
            'historical_vs_receipt': 'Historical event-time replay and verified pre-kickoff HTTP receipts are separately labeled; no substitute odds used.',
            'production': 'No production, Telegram, formal ledger, frozen-eight, or ingestion changes.',
        },
    }
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(f'wrote {MANIFEST.relative_to(ROOT)} with {len(inputs)} inputs and {len(outputs)} outputs')


if __name__ == '__main__':
    main()
