#!/usr/bin/env python3
# coding: utf-8
"""MR1 AH formal-Telegram read-only M4 Pass counterfactual.

Only study the two leagues the user explicitly confirmed. No production
integration, no Telegram sending, no changed MR1 model or selector.
"""
import argparse
import collections
import datetime
import json
from pathlib import Path

STUDY_LEAGUES = frozenset(('Türkiye Super Lig', 'Japan J-League'))
STUDY_CUTOFF_UTC = '2026-10-29T00:00:00Z'  # research comparison, not a rule


def time(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))


def summary(rows):
    pnl = sum(float(x['realized_pnl']) for x in rows)
    return {'orders': len(rows), 'unique_matches': len(set(str(x['match_id']) for x in rows)),
            'pnl_units': round(pnl, 6), 'roi': round(pnl / len(rows), 8) if rows else None}


def analyze(ledger, cutoff=STUDY_CUTOFF_UTC):
    orders = list(ledger['entries'].values())
    baseline = summary(orders)
    skipped = [x for x in orders if x['league'] in STUDY_LEAGUES]
    retained = [x for x in orders if x['league'] not in STUDY_LEAGUES]
    cutoff_dt = time(cutoff)
    known_at_cutoff = [x for x in orders if time(x['settled_at']) <= cutoff_dt]
    after_cutoff = [x for x in orders if time(x['sent_at']) > cutoff_dt]
    after_skipped = [x for x in after_cutoff if x['league'] in STUDY_LEAGUES]
    after_retained = [x for x in after_cutoff if x['league'] not in STUDY_LEAGUES]
    leagues = {}
    for league in sorted(STUDY_LEAGUES):
        matches = [x for x in skipped if x['league'] == league]
        prior = [x for x in known_at_cutoff if x['league'] == league]
        later = [x for x in after_cutoff if x['league'] == league]
        leagues[league] = {'all': summary(matches),
                           'settled_by_cutoff': summary(prior),
                           'sent_after_cutoff': summary(later),
                           'settlement_states': dict(collections.Counter(x['settlement'] for x in matches))}
    return {'protocol': 'M4_MR1_AH_TWO_LEAGUE_PASS_STUDY_V1',
            'ledger_generated_at': ledger.get('generated_at'),
            'research_only': True, 'production_change': False,
            'study_leagues': sorted(STUDY_LEAGUES),
            'all_history': {'original': baseline, 'excluded': summary(skipped), 'pass_study': summary(retained)},
            'cutoff_study': {'cutoff_utc': cutoff, 'historically_known': summary(known_at_cutoff),
                             'original_after': summary(after_cutoff), 'excluded_after': summary(after_skipped),
                             'pass_study_after': summary(after_retained)},
            'league_detail': leagues,
            'interpretation': ('Retrospective conditional exclusion, not independent selection-validation: '
                               'the two leagues were selected after seeing past outcomes. No live Pass enabled.')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('settled_json', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    ledger = json.loads(args.settled_json.read_text(encoding='utf-8'))
    result = analyze(ledger)
    report = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    print(report, end='')


if __name__ == '__main__':
    main()
