#!/usr/bin/env python3
"""Audit exact-name Transfermarkt identity anchors for the expanded 15 leagues.

No fuzzy name matching is used. Crown team IDs are mapped only through unique
same-side fixture anchors matching normalized full names, date +/- one day and
the final score; a team mapping requires repeated independent fixture anchors
and a one-to-one reverse mapping.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
DATA = Path('/Users/mac/QuantAsiaDesk/data')
WORK = Path('/Users/mac/QuantAsiaDesk/research-work')
TM_PATH = WORK / 'm8_pregame_info_source_20261117/games.csv.gz'
EXPANDED_PATH = ROOT / 'research/m8/red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'
SCHEDULE_DIR = DATA / 'm5-crown-authorized/schedules'
OUT = Path(__file__).resolve().parent
CN = ZoneInfo('Asia/Shanghai')
TARGET_LEAGUES = {
    '10', '33', '85', '129', '314', '378', '670', '779', '8293',
    '10714', '11498', '19290', '27388', '27389', '27390',
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def norm(value: object) -> str:
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    tokens = re.findall(r'[a-z0-9]+', value)
    # Strip only generic club-form tokens, never a fuzzy prefix/substring.
    generic = {'fc', 'cf', 'sc', 'afc', 'ac', 'club', 'clube', 'football',
               'futbol', 'futebol', 'soccer'}
    return ''.join(token for token in tokens if token not in generic)


def crown_local_date(value: object) -> dt.date:
    raw = str(value).replace('Z', '+00:00').replace(' ', 'T')
    x = dt.datetime.fromisoformat(raw)
    if x.tzinfo is None:
        x = x.replace(tzinfo=CN)
    return x.astimezone(CN).date()


def main() -> None:
    tm_by_anchor: dict[tuple[dt.date, int, int, str, str], list[dict]] = collections.defaultdict(list)
    tm_team_names: dict[str, dict[str, set[str]]] = collections.defaultdict(lambda: collections.defaultdict(set))
    tm_games = 0
    with gzip.open(TM_PATH, 'rt', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            try:
                day = dt.date.fromisoformat(row['date'])
                hg = int(row['home_club_goals'])
                ag = int(row['away_club_goals'])
            except (ValueError, KeyError, TypeError):
                continue
            comp = str(row.get('competition_id') or '')
            hi, ai = str(row.get('home_club_id') or ''), str(row.get('away_club_id') or '')
            hn, an = norm(row.get('home_club_name')), norm(row.get('away_club_name'))
            if not comp or not hi or not ai or not hn or not an:
                continue
            item = {'competition_id': comp, 'game_id': str(row.get('game_id') or ''),
                    'date': day.isoformat(), 'home_id': hi, 'away_id': ai,
                    'home_name': row.get('home_club_name'), 'away_name': row.get('away_club_name'),
                    'hg': hg, 'ag': ag}
            tm_by_anchor[(day, hg, ag, hn, an)].append(item)
            tm_team_names[comp][hn].add(hi)
            tm_games += 1

    crown_by_league: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    league_names: dict[str, set[str]] = collections.defaultdict(set)
    schedule_files = []
    for league in sorted(TARGET_LEAGUES, key=int):
        for page in sorted((SCHEDULE_DIR / league).glob('page-*.raw.json')):
            schedule_files.append(page)
            try:
                blob = json.loads(page.read_bytes())
            except (OSError, json.JSONDecodeError):
                continue
            matches = (blob.get('data') or {}).get('matches') or []
            for row in matches:
                if str(row.get('l_id')) != league or row.get('status') != 'full':
                    continue
                fid = str(row.get('id') or '')
                hi, ai = str(row.get('h_id') or ''), str(row.get('a_id') or '')
                hn, an = norm(row.get('h')), norm(row.get('a'))
                if not fid or not hi or not ai or not hn or not an:
                    continue
                rec = {'fid': fid, 'league': league, 'home_id': hi, 'away_id': ai,
                       'home_name': row.get('h'), 'away_name': row.get('a'),
                       'home_norm': hn, 'away_norm': an,
                       'date': crown_local_date(row.get('start')).isoformat(),
                       'hg': int(row['hg']), 'ag': int(row['ag'])}
                prior = crown_by_league[league].get(fid)
                if prior and prior != rec:
                    raise ValueError(f'Crown schedule conflict for FID {fid}: {prior} vs {rec}')
                crown_by_league[league][fid] = rec
                league_names[league].update((hn, an))

    # Exact unique team-name overlaps rank likely provider-to-TM competitions.
    ranking: dict[str, list[dict]] = {}
    for league, names in league_names.items():
        candidates = []
        for comp, names_map in tm_team_names.items():
            common = sorted(name for name in names if len(names_map.get(name, ())) == 1)
            crown_id_aliases = collections.defaultdict(set)
            for fixture in crown_by_league[league].values():
                crown_id_aliases[fixture['home_id']].add(fixture['home_norm'])
                crown_id_aliases[fixture['away_id']].add(fixture['away_norm'])
            common_pairs = set()
            for crown_id, aliases in crown_id_aliases.items():
                tm_ids = {next(iter(names_map[n])) for n in aliases if n in common and len(names_map[n]) == 1}
                if len(tm_ids) == 1:
                    common_pairs.add((crown_id, next(iter(tm_ids))))
            candidates.append({'competition_id': comp, 'exact_unique_team_id_pairs': len(common_pairs),
                               'exact_unique_name_values': len(common), 'tm_teams': len(names_map)})
        ranking[league] = sorted(candidates, key=lambda x: (-x['exact_unique_team_id_pairs'], -x['exact_unique_name_values'], x['competition_id']))

    # Fixture anchors require full exact normalized names, same home/away order,
    # exact FT, and date within one calendar day. Duplicates stay ambiguous.
    anchor_rows = []
    anchor_ambiguous = collections.Counter()
    for league, fixtures in crown_by_league.items():
        for fixture in fixtures.values():
            day = dt.date.fromisoformat(fixture['date'])
            found = []
            for delta in (-1, 0, 1):
                found.extend(tm_by_anchor.get((day + dt.timedelta(days=delta), fixture['hg'], fixture['ag'],
                                               fixture['home_norm'], fixture['away_norm']), []))
            unique = {(x['competition_id'], x['game_id'], x['home_id'], x['away_id']) for x in found}
            if len(unique) == 1:
                match = found[0]
                anchor_rows.append({'fid': fixture['fid'], 'league': league,
                    'competition_id': match['competition_id'], 'tm_game_id': match['game_id'],
                    'home_crown_id': fixture['home_id'], 'away_crown_id': fixture['away_id'],
                    'home_tm_id': match['home_id'], 'away_tm_id': match['away_id'],
                    'date_crown': fixture['date'], 'date_tm': match['date'],
                    'home_name': fixture['home_name'], 'away_name': fixture['away_name'],
                    'hg': fixture['hg'], 'ag': fixture['ag']})
            elif unique:
                anchor_ambiguous[league] += 1

    # Keep only clear league crosswalks: a single top competition with at least
    # one exact match anchor. This is identity evidence, not a betting filter.
    anchors_by_league_comp = collections.Counter((r['league'], r['competition_id']) for r in anchor_rows)
    comp_crosswalk = {}
    for league, ranks in ranking.items():
        anchor_ranks = sorted(
            [{'competition_id': x['competition_id'], 'anchors': anchors_by_league_comp[(league, x['competition_id'])],
              'team_pairs': x['exact_unique_team_id_pairs'], 'name_values': x['exact_unique_name_values']}
             for x in ranks], key=lambda z: (-z['anchors'], -z['team_pairs'], -z['name_values'], z['competition_id']))
        if anchor_ranks and anchor_ranks[0]['anchors'] > 0 and (
            len(anchor_ranks) == 1 or (anchor_ranks[0]['anchors'], anchor_ranks[0]['team_pairs']) >
            (anchor_ranks[1]['anchors'], anchor_ranks[1]['team_pairs'])
        ):
            comp_crosswalk[league] = anchor_ranks[0]['competition_id']

    filtered = [r for r in anchor_rows if comp_crosswalk.get(r['league']) == r['competition_id']]
    links: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    rev: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    evidence: dict[tuple[str, str, str], set[str]] = collections.defaultdict(set)
    for r in filtered:
        for side in ('home', 'away'):
            crown_id = r[f'{side}_crown_id']
            tm_id = r[f'{side}_tm_id']
            links[(r['league'], crown_id)].add(tm_id)
            rev[(r['league'], tm_id)].add(crown_id)
            evidence[(r['league'], crown_id, tm_id)].add(r['fid'])
    verified_team_map = {}
    for (league, crown_id), tm_ids in links.items():
        if len(tm_ids) != 1:
            continue
        tm_id = next(iter(tm_ids))
        if (len(rev[(league, tm_id)]) == 1 and
                len(evidence[(league, crown_id, tm_id)]) >= 2):
            verified_team_map[f'{league}|{crown_id}'] = tm_id

    # Feature-ready full-path rows require both teams in the verified mapping.
    expanded_rows = []
    with gzip.open(EXPANDED_PATH, 'rt', encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                expanded_rows.append(row)
    feature_ready_counts = collections.Counter()
    feature_ready_year = collections.Counter()
    mapped_fids_by_league = collections.Counter()
    for row in expanded_rows:
        league = str(row['league'])
        # Recover Crown team IDs from the FID schedule record.
        schedule = crown_by_league.get(league, {}).get(str(row['fid']))
        if not schedule:
            continue
        mapped_fids_by_league[league] += 1
        if (f'{league}|{schedule["home_id"]}' in verified_team_map and
                f'{league}|{schedule["away_id"]}' in verified_team_map):
            feature_ready_counts[league] += 1
            feature_ready_year[(league, str(row['year']))] += 1

    out = {
        'study': 'exact-name identity coverage audit for Transfermarkt historical lineup features on the expanded 15 leagues',
        'inputs_sha256': {str(TM_PATH): sha(TM_PATH), str(EXPANDED_PATH): sha(EXPANDED_PATH),
                          'schedule_pages': {str(path): sha(path) for path in schedule_files}},
        'coverage': {'target_leagues': sorted(TARGET_LEAGUES, key=int), 'expanded15_complete_T6_T3_T1_fids': len(expanded_rows),
                     'transfermarkt_games': tm_games, 'transfermarkt_competitions': len(tm_team_names),
                     'Crown_schedule_full_FIDs': sum(map(len, crown_by_league.values())),
                     'unique_exact_fixture_anchors': len(anchor_rows), 'ambiguous_fixture_fids': dict(anchor_ambiguous),
                     'clear_competition_crosswalks': comp_crosswalk,
                     'unique_bijective_team_mappings_with_2plus_anchors': len(verified_team_map),
                     'full_path_fids_found_in_Crown_schedule': dict(mapped_fids_by_league),
                     'full_path_fids_with_both_teams_verified': dict(feature_ready_counts),
                     'feature_ready_by_league_year': {f'{l}|{y}': n for (l, y), n in sorted(feature_ready_year.items())}},
        'competition_ranking_by_league': ranking,
        'team_mappings': verified_team_map,
        'anchor_rows': anchor_rows,
        'identity_method': 'Unicode accent/case/punctuation normalization and removal of generic club-form tokens (FC, CF, SC, AFC, AC, Club, Clube, Football, Futbol, Futebol, Soccer); exact remaining whole team-name equality; same home/away order; same FT; TotalCorner local date +/- 1; unique TM game candidate; repeated >=2 independent FIDs per club; one-to-one Crown/TM team-ID mapping. No fuzzy similarity or outcome-derived model feature.'
    }
    (OUT / 'identity_coverage_audit.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with gzip.open(OUT / 'exact_fixture_identity_anchors.jsonl.gz', 'wt', encoding='utf-8') as gz:
        for row in sorted(anchor_rows, key=lambda x: (int(x['league']), x['date_crown'], x['fid'])):
            gz.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(json.dumps(out['coverage'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
