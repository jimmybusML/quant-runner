#!/usr/bin/env python3
"""Strictly audit whether expanded-15 Crown fixtures have pregame venue identity data."""
from __future__ import annotations
import collections, csv, datetime as dt, gzip, hashlib, json, pathlib, re, unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
PATHS = ROOT / 'research/m8/exact_rules_outside_original49_20261120/exact_rule_cross_league_all_complete_paths.jsonl.gz'
DATA = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_pregame_info_source_20261117')
COORDS = OUT / 'venue_coordinates_20261121.jsonl'
ELEV = OUT / 'srtm90m_manifest_20261121.jsonl'
TARGET_LEAGUES = {10, 33, 85, 129, 314, 378, 670, 779, 8293, 10714, 11498, 19290, 27388, 27389, 27390}

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

def norm(value):
    x = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', x)

def readj(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def main():
    comps = {}
    with gzip.open(DATA / 'competitions.csv.gz', 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f): comps[str(r['competition_id'])] = r
    games = []
    by_pair_score = collections.defaultdict(list)
    by_club = collections.defaultdict(list)
    with gzip.open(DATA / 'games.csv.gz', 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                day = dt.date.fromisoformat(r['date'])
                hg, ag = int(r['home_club_goals']), int(r['away_club_goals'])
            except Exception:
                continue
            row = {'date': day.isoformat(), 'day': day, 'competition_id': str(r['competition_id']),
                   'home_club_id': str(r['home_club_id']), 'away_club_id': str(r['away_club_id']),
                   'home_club_name': r['home_club_name'], 'away_club_name': r['away_club_name'],
                   'stadium': (r.get('stadium') or '').strip(), 'hg': hg, 'ag': ag,
                   'game_id': str(r['game_id'])}
            games.append(row)
            by_pair_score[(norm(row['home_club_name']), norm(row['away_club_name']), hg, ag)].append(row)
            if row['stadium']:
                by_club[row['home_club_id']].append(row)
    coords = {(r['venue'], r['country_query']): r for r in readj(COORDS)}
    elevations = {}
    for r in readj(ELEV):
        if r.get('status') == 'success':
            for v in r['results']:
                elevations[v['coordinate_id']] = v.get('elevation_m')
    rows = []
    reasons = collections.Counter()
    for p in readj(PATHS):
        if int(p['year']) not in (2024, 2025, 2026) or int(p['league']) not in TARGET_LEAGUES:
            continue
        target_day = dt.date.fromisoformat(p['date'])
        key = (norm(p['home']), norm(p['away']), int(p['hg']), int(p['ag']))
        candidate = [g for g in by_pair_score.get(key, [])
                     if abs((g['day'] - target_day).days) <= 1]
        status = 'unmatched'
        selected = None
        if len(candidate) == 1:
            status, selected = 'unique_exact_team_ft_date_match', candidate[0]
        elif len(candidate) > 1:
            status = 'ambiguous_exact_team_ft_date_matches'
        reasons[status] += 1
        result = {'fid': str(p['fid']), 'year': int(p['year']), 'date_beijing': p['date'],
                  'provider_league_id': str(p['league']), 'home': p['home'], 'away': p['away'],
                  'ft_home': int(p['hg']), 'ft_away': int(p['ag']),
                  'identity_join_status': status, 'transfermarkt_game_id': None,
                  'transfermarkt_competition_id': None, 'transfermarkt_country': None,
                  'target_stadium_postmatch_diagnostic': None,
                  'home_prior_ground': None, 'away_prior_home_ground': None,
                  'home_prior_ground_tie': False, 'away_prior_ground_tie': False,
                  'home_elevation_m': None, 'away_elevation_m': None}
        if selected:
            result.update({'transfermarkt_game_id': selected['game_id'],
                           'transfermarkt_competition_id': selected['competition_id'],
                           'transfermarkt_country': comps.get(selected['competition_id'], {}).get('country_name'),
                           'target_stadium_postmatch_diagnostic': selected['stadium']})
            cutoff = target_day - dt.timedelta(days=3)
            earliest = cutoff - dt.timedelta(days=365)
            def prior_mode(club):
                prior = [g for g in by_club[str(club)] if earliest <= g['day'] < cutoff]
                if not prior: return None, False
                cnt = collections.Counter(g['stadium'] for g in prior)
                top = max(cnt.values())
                modes = sorted(s for s, n in cnt.items() if n == top)
                return (modes[0] if len(modes) == 1 else None), len(modes) > 1
            home_v, home_tie = prior_mode(selected['home_club_id'])
            away_v, away_tie = prior_mode(selected['away_club_id'])
            result.update({'home_prior_ground': home_v, 'away_prior_home_ground': away_v,
                           'home_prior_ground_tie': home_tie, 'away_prior_ground_tie': away_tie,
                           'prior_window_cutoff_exclusive': cutoff.isoformat()})
            country = result['transfermarkt_country']
            hcoord = coords.get((home_v, country)) if home_v and country else None
            acoord = coords.get((away_v, country)) if away_v and country else None
            result['home_coordinate_cached'] = bool(hcoord)
            result['away_coordinate_cached'] = bool(acoord)
            if hcoord: result['home_elevation_m'] = elevations.get(f"{float(hcoord['latitude']):.6f},{float(hcoord['longitude']):.6f}")
            if acoord: result['away_elevation_m'] = elevations.get(f"{float(acoord['latitude']):.6f},{float(acoord['longitude']):.6f}")
            result['both_prior_grounds_unique'] = bool(home_v and away_v and not home_tie and not away_tie)
            result['both_elevations_available'] = result['home_elevation_m'] is not None and result['away_elevation_m'] is not None
        rows.append(result)
    by_league = {}
    for league in sorted(TARGET_LEAGUES):
        sub = [r for r in rows if int(r['provider_league_id']) == league]
        by_league[str(league)] = {'complete_path_targets': len(sub),
            'unique_exact_identity_ft_date_match': sum(r['identity_join_status'] == 'unique_exact_team_ft_date_match' for r in sub),
            'both_unique_prior_grounds': sum(bool(r.get('both_prior_grounds_unique')) for r in sub),
            'both_elevations_available': sum(bool(r.get('both_elevations_available')) for r in sub)}
    summary = {'study': 'Expanded-15 strict Transfermarkt venue linkage coverage audit',
        'target_years': [2024, 2025, 2026], 'target_provider_league_ids': sorted(TARGET_LEAGUES),
        'target_complete_path_fids': len(rows), 'identity_match_status_counts': dict(reasons),
        'unique_exact_identity_ft_date_match': sum(r['identity_join_status'] == 'unique_exact_team_ft_date_match' for r in rows),
        'both_unique_prior_grounds': sum(bool(r.get('both_prior_grounds_unique')) for r in rows),
        'both_elevations_available': sum(bool(r.get('both_elevations_available')) for r in rows),
        'by_provider_league': by_league,
        'strict_join_definition': 'Accent/punctuation-normalized exact home/away names + exact FT + Transfermarkt match date within one day; require one unique row. Prior venue mode uses target date minus 3 days through 365-day lookback; tied mode is missing.',
        'input_sha256': {str(PATHS): sha(PATHS), str(DATA / 'games.csv.gz'): sha(DATA / 'games.csv.gz'),
                         str(DATA / 'competitions.csv.gz'): sha(DATA / 'competitions.csv.gz'),
                         str(COORDS): sha(COORDS), str(ELEV): sha(ELEV)}}
    (OUT / 'expanded15_venue_linkage_audit_20261121.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    with gzip.open(OUT / 'expanded15_venue_linkage_by_fid_20261121.jsonl.gz', 'wt', encoding='utf-8') as f:
        for r in sorted(rows, key=lambda x: (x['date_beijing'], x['fid'])):
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    print(json.dumps({k: summary[k] for k in ('target_complete_path_fids', 'identity_match_status_counts',
          'unique_exact_identity_ft_date_match', 'both_unique_prior_grounds', 'both_elevations_available', 'by_provider_league')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
