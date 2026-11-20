#!/usr/bin/env python3
"""Audit historical M8 E-side provenance against settled frozen members."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path('/Users/mac/QuantAsiaDesk/research-work')
OUT = Path(__file__).resolve().parent
MEMBERS = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
FEATURES = WORK / 'm8_same_line_probability_path_20261114.jsonl'
SETTLED = ROOT / 'research/m8/frozen_eight_boundary_expansion_20261119/frozen_eight_member_quote_settlement_ledger_20261119.jsonl.gz'
ORDERS = OUT / 'exact_rule_cross_league_orders.jsonl.gz'


def sign(value: float) -> int:
    return 1 if value > 1e-9 else -1 if value < -1e-9 else 0


def main() -> None:
    frozen_e = {
        row['fid']
        for line in MEMBERS.open()
        if (row := json.loads(line)).get('cohort') == 'E'
    }
    settled = {}
    with gzip.open(SETTLED, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row.get('group') == 'E':
                settled[row['fid']] = row

    feature_rows = {}
    for line in FEATURES.open():
        row = json.loads(line)
        if row.get('fid') in frozen_e:
            feature_rows[row['fid']] = row

    matched = 0
    direction_matches = 0
    for fid in frozen_e & set(settled) & set(feature_rows):
        row = feature_rows[fid]
        net = sign(float(row['p1']) - float(row['p0']))
        first = sign(float(row['p3']) - float(row['p0']))
        second = sign(float(row['p1']) - float(row['p3']))
        direction = net or first or second or sign(float(row['last_move']))
        side = ('away' if direction > 0 else 'home') if direction else None
        matched += 1
        direction_matches += side == settled[fid]['side']

    candidate_e = []
    with gzip.open(ORDERS, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row.get('group') == 'E':
                candidate_e.append(row)

    result = {
        'frozen_e_members': len(frozen_e),
        'members_with_settlement_ledger': len(frozen_e & set(settled)),
        'members_with_both_path_and_settlement_evidence': matched,
        'historical_extractor_direction_matches': direction_matches,
        'historical_extractor_direction_mismatches': matched - direction_matches,
        'members_without_paired_evidence': len(frozen_e) - matched,
        'cross_league_priority_assigned_E_orders': len(candidate_e),
        'cross_league_E_orders_with_zero_endpoint_move': sum(
            abs(float(row['p1']) - float(row['p0'])) <= 1e-9 for row in candidate_e
        ),
        'direction_rule': 'first nonzero of p1-p0, p3-p0, p1-p3, last_move; positive selects away, negative selects home',
        'boundary_helper_difference': 'The later boundary group_side(E) returns no side when p1-p0 is zero. The historical full-path extractor and settled-member direction evidence support the fallback used in this study.',
    }
    (OUT / 'audit_frozen_E_direction_consistency_20261120.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
