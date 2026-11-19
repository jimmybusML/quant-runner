#!/usr/bin/env python3
"""M8 competition-goal value research against Crown AH.

Research-only. Reconstructs target-date season tables from prior completed
Transfermarkt fixtures, maps Crown FIDs using the already-audited R49 identity
bridge, uses Crown AH quotes only, and settles exact Asian handicap cashflows.
No network calls or production writes.
"""
from __future__ import annotations

import bisect
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import re
import statistics
import sys
import unicodedata

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
SRC = WORK / 'm8_pregame_info_source_20261117'
OUT = ROOT / 'research/m8/competition_objective_20261119'
OUT.mkdir(parents=True, exist_ok=True)
DATA_CUTOFF = dt.date(2026, 7, 6)
TEST_YEARS = (2024, 2025, 2026)
RIDGE = 100.0
LAG_DAYS = 3


def sha(path: pathlib.Path | str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


# Reuse only the verified, read-only R49 Crown/TM fixture identity bridge and
# Crown T12 AH/FT cohort builder. This prefix ends before any prior experiment
# constructs features or writes its output.
prior_path = ROOT / 'research/m8/m8_prior_manager_turnover_20261117.py'
prior_text = prior_path.read_text()
bridge_ns: dict = {}
exec(compile(prior_text[:prior_text.index('# Build historical coach timeline')],
              str(prior_path) + '[read-only identity prefix]', 'exec'), bridge_ns)
H = bridge_ns['H']
R = bridge_ns['R']
teammap = bridge_ns['teammap']
allft = bridge_ns['allft']
cm = bridge_ns['cm']
assert len(H) == 38846 and len(R) == 1230 and len(teammap) == 453

# The frozen membership is used only after predictions for de-duplicated
# incremental reporting. It is never a model feature or a training selector.
foundation_dir = WORK / 'm8_foundation_20261115'
foundation = json.loads((foundation_dir / 'manifest.json').read_text())
members_path = WORK / foundation['historical_membership']['local_file']
member_sha = sha(members_path)
assert member_sha == foundation['historical_membership']['sha256']
members = {}
for line in members_path.open():
    r = json.loads(line)
    members[str(r['fid'])] = r
assert len(members) == 10294

# Team IDs are globally unambiguous across the R49 bridge. Keep the original
# league-keyed links and refuse any conflicting global reuse.
team_values: dict[str, set[str]] = collections.defaultdict(set)
for (league_id, crown_team_id), tm_team_id in teammap.items():
    team_values[str(crown_team_id)].add(str(tm_team_id))
global_teammap = {k: next(iter(v)) for k, v in team_values.items() if len(v) == 1}
assert len(global_teammap) == len(team_values) == 453


def parse_day(s: str) -> dt.date:
    return dt.date.fromisoformat(str(s)[:10])


def norm_name(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(fc|cf|sc|afc|ac|club|football|soccer|fk|as|sv|sk)\b', ' ', s)
    return re.sub(r'[^a-z0-9]', '', s)


def lineup_name_match(a: str, b: str) -> float:
    a, b = norm_name(a), norm_name(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if min(len(a), len(b)) >= 6 and (a in b or b in a):
        return 0.91
    # Use the same conservative string comparison family as the audited R49
    # crosswalk, without adding a new team identity to the bridge.
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio()


# Rebuild the Crown fixture identity inventory from saved schedule responses.
# These rows supply names/date/FT only for joining; target scores are not sent
# to the feature builder below.
crown_fixtures: dict[str, dict] = {}
schedule_pages = 0
schedule_errors = collections.Counter()
for page in sorted((WORK.parent / 'data/m5-crown-authorized/schedules').glob('*/page-*.raw.json')):
    try:
        body = json.loads(page.read_bytes())
        schedule_pages += 1
        for z in body.get('data', {}).get('matches', []):
            if z.get('status') != 'full':
                continue
            fid = str(z.get('id') or '')
            if not fid:
                continue
            start = dt.datetime.fromisoformat(str(z['start']).replace(' ', 'T'))
            if start.tzinfo is None:
                start = start.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
            day_utc = start.astimezone(dt.timezone.utc).date()
            row = {
                'fid': fid, 'league': str(z.get('l_id')), 'date': day_utc.isoformat(),
                'home_id': str(z.get('h_id')), 'away_id': str(z.get('a_id')),
                'home_name': str(z.get('h') or ''), 'away_name': str(z.get('a') or ''),
                'hg': int(z['hg']), 'ag': int(z['ag']),
            }
            old = crown_fixtures.get(fid)
            if old is None:
                crown_fixtures[fid] = row
            elif old != row:
                schedule_errors['conflicting_fid'] += 1
                crown_fixtures.pop(fid, None)
    except Exception as e:
        schedule_errors[type(e).__name__] += 1

# Load all saved completed fixtures and build an exact team/score/date lookup.
games_path = SRC / 'games.csv.gz'
games_sha = sha(games_path)
games = pd.read_csv(
    games_path, compression='gzip',
    usecols=['game_id', 'competition_id', 'season', 'round', 'date',
             'home_club_id', 'away_club_id', 'home_club_goals', 'away_club_goals',
             'home_club_position', 'away_club_position', 'competition_type',
             'home_club_name', 'away_club_name', 'aggregate'],
    dtype={'game_id': 'string', 'competition_id': 'string', 'season': 'Int64',
           'home_club_id': 'string', 'away_club_id': 'string'},
)
games['date'] = pd.to_datetime(games['date'], errors='coerce').dt.date
games = games[games.date.notna()].copy()
games['home_club_id'] = games.home_club_id.astype(str)
games['away_club_id'] = games.away_club_id.astype(str)
games['competition_id'] = games.competition_id.astype(str)
games['season'] = games.season.astype('Int64')
games_by_pair_score: dict[tuple, list] = collections.defaultdict(list)
game_rows = {}
for z in games.itertuples(index=False):
    if pd.isna(z.home_club_goals) or pd.isna(z.away_club_goals):
        continue
    row = {
        'game_id': str(z.game_id), 'competition_id': str(z.competition_id),
        'season': int(z.season) if not pd.isna(z.season) else None,
        'round': str(z.round or ''), 'date': z.date,
        'home_club_id': str(z.home_club_id), 'away_club_id': str(z.away_club_id),
        'hg': int(z.home_club_goals), 'ag': int(z.away_club_goals),
        'home_position_source': None if pd.isna(z.home_club_position) else float(z.home_club_position),
        'away_position_source': None if pd.isna(z.away_club_position) else float(z.away_club_position),
        'competition_type': str(z.competition_type or ''),
        'home_name': str(z.home_club_name or ''), 'away_name': str(z.away_club_name or ''),
    }
    game_rows[row['game_id']] = row
    key = (row['home_club_id'], row['away_club_id'], row['hg'], row['ag'])
    games_by_pair_score[key].append(row)

# Match FIDs to the actual Transfermarkt competition-season record. The target
# FT is only a deterministic entity join key; the target outcome is withheld
# from standings and model features. Ambiguous joins stay missing.
target_rows = []
join_qc = collections.Counter()
for h in H:
    fid = str(h['fid'])
    cf = crown_fixtures.get(fid)
    if cf is None:
        join_qc['no_saved_Crown_fixture_identity'] += 1
        continue
    identity = (cf['league'], cf['home_id'], cf['away_id'], cf['hg'], cf['ag'], cf['date'])
    expected = (str(h['league']), str(h['home_id']), str(h['away_id']), int(h['hg']), int(h['ag']), str(h['date']))
    if identity != expected:
        join_qc['Crown_identity_or_FT_mismatch'] += 1
        continue
    tmh = global_teammap.get(cf['home_id'])
    tma = global_teammap.get(cf['away_id'])
    if not tmh or not tma:
        join_qc['team_not_in_verified_R49_bridge'] += 1
        continue
    key = (tmh, tma, int(h['hg']), int(h['ag']))
    cand = []
    d0 = parse_day(h['date'])
    for g in games_by_pair_score.get(key, []):
        if abs((g['date'] - d0).days) > 1:
            continue
        s1 = lineup_name_match(cf['home_name'], g['home_name'])
        s2 = lineup_name_match(cf['away_name'], g['away_name'])
        if min(s1, s2) < 0.85:
            continue
        cand.append((abs((g['date'] - d0).days), -min(s1, s2), g))
    cand.sort(key=lambda v: (v[0], v[1], v[2]['game_id']))
    if not cand:
        join_qc['no_unique_TM_game'] += 1
        continue
    if len(cand) > 1 and cand[0][:2] == cand[1][:2]:
        # A repeated home/away result in more than one competition is not
        # resolved by guessing a tournament identity.
        join_qc['ambiguous_TM_game'] += 1
        continue
    g = cand[0][2]
    join_qc['matched_unique_TM_game'] += 1
    target_rows.append({
        'fid': fid, 'year': int(h['year']), 'date': str(h['date']),
        'league': str(h['league']), 'tm_game_id': g['game_id'],
        'tm_competition_id': g['competition_id'], 'tm_season': g['season'],
        'tm_round': g['round'], 'tm_competition_type': g['competition_type'],
        'home_tm_id': tmh, 'away_tm_id': tma,
        'home_id': str(h['home_id']), 'away_id': str(h['away_id']),
        'home_name': cf['home_name'], 'away_name': cf['away_name'],
        'hg': int(h['hg']), 'ag': int(h['ag']),
        'AH_line': float(h['al']), 'AH_home_odds': float(h['ah']), 'AH_away_odds': float(h['aa']),
        'home_U': float(h['home_U']), 'away_U': float(h['away_U']),
        'target_result_used_for_identity_join_only': True,
        'target_result_used_as_pregame_feature': False,
        'source_home_position_validation_only': g['home_position_source'],
        'source_away_position_validation_only': g['away_position_source'],
    })

# Completed results are restricted to same Transfermarkt competition+season.
season_games: dict[tuple[str, int], list[dict]] = collections.defaultdict(list)
for g in game_rows.values():
    if g['season'] is None:
        continue
    season_games[(g['competition_id'], int(g['season']))].append(g)
for k in season_games:
    season_games[k].sort(key=lambda g: (g['date'], g['game_id']))


def standings_add(state: dict[str, list[int]], g: dict, sign: int = 1) -> None:
    # state[club] = [played, points, goals_for, goals_against]
    h, a = g['home_club_id'], g['away_club_id']
    state.setdefault(h, [0, 0, 0, 0])
    state.setdefault(a, [0, 0, 0, 0])
    hg, ag = g['hg'], g['ag']
    hp = 3 if hg > ag else 1 if hg == ag else 0
    ap = 3 if ag > hg else 1 if hg == ag else 0
    state[h][0] += sign; state[h][1] += sign * hp; state[h][2] += sign * hg; state[h][3] += sign * ag
    state[a][0] += sign; state[a][1] += sign * ap; state[a][2] += sign * ag; state[a][3] += sign * hg


def ordered_table(state: dict[str, list[int]], target_clubs: tuple[str, str]) -> tuple[list, dict]:
    for club in target_clubs:
        state.setdefault(club, [0, 0, 0, 0])
    tab = sorted(state.items(), key=lambda kv: (-kv[1][1], -(kv[1][2] - kv[1][3]), -kv[1][2], kv[0]))
    ranks = {club: i + 1 for i, (club, _) in enumerate(tab)}
    return tab, ranks


def prior_capacity(comp: str, season: int, target_date: dt.date) -> tuple[float | None, int | None, dict]:
    eligible = []
    for (c, s), rows in season_games.items():
        if c != comp or s >= season:
            continue
        max_day = max(g['date'] for g in rows)
        if max_day >= target_date - dt.timedelta(days=LAG_DAYS):
            continue
        counts = collections.Counter()
        for g in rows:
            counts[g['home_club_id']] += 1; counts[g['away_club_id']] += 1
        if counts:
            eligible.append((s, statistics.median(counts.values()), max(counts.values()), len(counts)))
    eligible.sort()
    last3 = eligible[-3:]
    if not last3:
        return None, None, {'prior_seasons': []}
    expected = float(statistics.median(x[1] for x in last3))
    max_round = int(round(statistics.median(x[2] for x in last3)))
    return expected, max_round, {'prior_seasons': [x[0] for x in last3]}


def phase_flags(round_text: str, comp_type: str) -> dict[str, float]:
    t = round_text.lower()
    is_cup = float('cup' in comp_type.lower() or 'cup' in t or 'pokal' in t)
    is_ko = float(any(w in t for w in ('round of', 'quarter', 'semi-final', 'semifinal', 'final', 'play-off', 'playoff', 'qualifying')))
    return {
        'is_cup_competition': is_cup,
        'is_knockout_or_playoff_round': is_ko,
        'is_qualifying_round': float('qualif' in t),
        'is_round_of_16': float('round of 16' in t or 'last 16' in t),
        'is_quarter_final': float('quarter' in t),
        'is_semi_final': float('semi' in t),
        'is_final': float(t.strip() == 'final' or t.endswith(' final')),
        'is_championship_phase': float('championship' in t),
        'is_relegation_phase': float('relegation' in t),
        'is_playoff_phase': float('play-off' in t or 'playoff' in t),
    }


def rank_from_state(state: dict[str, list[int]], club: str) -> int:
    # deterministic Pts/GD/GF ordering; not a claim about each league's official
    # head-to-head tiebreak rule.
    return ordered_table(state, (club, club))[1][club]


# Prepare knockout/tie chronology using only prior events in the same
# competition-season. `aggregate` from the target fixture is never read.
prior_ko_events: dict[tuple[str, int, frozenset[str]], list[dict]] = collections.defaultdict(list)
for (comp, season), rows in season_games.items():
    for g in rows:
        phase = phase_flags(g['round'], g['competition_type'])
        if phase['is_knockout_or_playoff_round'] and not phase['is_championship_phase'] and not phase['is_relegation_phase']:
            prior_ko_events[(comp, season, frozenset((g['home_club_id'], g['away_club_id'])))].append(g)
for k in prior_ko_events:
    prior_ko_events[k].sort(key=lambda g: (g['date'], g['game_id']))

# Sweep each competition-season up to the conservative T-3 day cutoff. No
# target match, same-day score, future final table or target-row position enters.
features = []
table_qc = collections.Counter()
position_validation = collections.Counter()
grouped_targets: dict[tuple[str, int], list[dict]] = collections.defaultdict(list)
for r in target_rows:
    if r['tm_season'] is None:
        table_qc['missing_target_season_id'] += 1
        continue
    grouped_targets[(r['tm_competition_id'], int(r['tm_season']))].append(r)

target_base_features: dict[str, dict] = {}
for (comp, season), targets in grouped_targets.items():
    rows = season_games.get((comp, season), [])
    state: dict[str, list[int]] = {}
    ix = 0
    targets.sort(key=lambda r: (r['date'], r['fid']))
    for r in targets:
        day = parse_day(r['date'])
        cutoff = day - dt.timedelta(days=LAG_DAYS)
        while ix < len(rows) and rows[ix]['date'] <= cutoff:
            standings_add(state, rows[ix], 1)
            ix += 1
        phase = phase_flags(r['tm_round'], r['tm_competition_type'])
        comp_type = r['tm_competition_type'].lower()
        # Table is a league table only for domestic_league cohorts. A separate
        # playoff/knockout competition has no reliable inherited-points rule in
        # the archived data; do not fabricate its seed.
        can_table = comp_type == 'domestic_league'
        if can_table:
            tab, ranks = ordered_table(state, (r['home_tm_id'], r['away_tm_id']))
            expected, max_round, cap_meta = prior_capacity(comp, season, day)
            hstat = state.get(r['home_tm_id'], [0, 0, 0, 0])
            astat = state.get(r['away_tm_id'], [0, 0, 0, 0])
            nteams = max(1, len(tab))
            leader_pts = max((v[1] for _, v in tab), default=0)
            hrank, arank = ranks[r['home_tm_id']], ranks[r['away_tm_id']]
            hp, ap = hstat[1], astat[1]
            hplayed, aplayed = hstat[0], astat[0]
            hrem = max(0.0, expected - hplayed) if expected is not None else None
            arem = max(0.0, expected - aplayed) if expected is not None else None
            hreach = max(0.0, leader_pts - hp) / max(3.0 * hrem, 1.0) if hrem is not None else None
            areach = max(0.0, leader_pts - ap) / max(3.0 * arem, 1.0) if arem is not None else None
            # Generic prior-season positional bands only. Available data do not
            # encode UEFA slots or league-specific relegation counts.
            htop = float(hrank <= min(4, nteams)); atop = float(arank <= min(4, nteams))
            hlow = float(hrank > max(0, nteams - 3)); alow = float(arank > max(0, nteams - 3))
            hprogress = min(1.5, hplayed / expected) if expected else None
            aprogress = min(1.5, aplayed / expected) if expected else None
            hgd = hstat[2] - hstat[3]; agd = astat[2] - astat[3]
            # Point-value features are pre-match state changes only: possible
            # home win/draw/away win movement in the direct table points gap.
            point_gap = hp - ap
            hwin_gap = point_gap + 3
            draw_gap = point_gap
            awin_gap = point_gap - 3
            feat = {
                'h_points': float(hp), 'a_points': float(ap), 'points_gap_home_minus_away': float(point_gap),
                'h_points_per_game': float(hp / hplayed) if hplayed else 0.0,
                'a_points_per_game': float(ap / aplayed) if aplayed else 0.0,
                'h_goal_diff_per_game': float(hgd / hplayed) if hplayed else 0.0,
                'a_goal_diff_per_game': float(agd / aplayed) if aplayed else 0.0,
                'h_rank_pct': float((hrank - 1) / max(nteams - 1, 1)),
                'a_rank_pct': float((arank - 1) / max(nteams - 1, 1)),
                'h_rank': float(hrank), 'a_rank': float(arank),
                'h_points_gap_leader': float(leader_pts - hp), 'a_points_gap_leader': float(leader_pts - ap),
                'h_title_gap_remaining_ratio': float(hreach if hreach is not None else 0.0),
                'a_title_gap_remaining_ratio': float(areach if areach is not None else 0.0),
                'h_remaining_matches_est': float(hrem if hrem is not None else 0.0),
                'a_remaining_matches_est': float(arem if arem is not None else 0.0),
                'h_season_progress': float(hprogress if hprogress is not None else 0.0),
                'a_season_progress': float(aprogress if aprogress is not None else 0.0),
                'h_top4_position_proxy': htop, 'a_top4_position_proxy': atop,
                'h_bottom3_position_proxy': hlow, 'a_bottom3_position_proxy': alow,
                'both_top4_proxy': float(htop and atop), 'both_bottom3_proxy': float(hlow and alow),
                'upper_zone_asymmetry': float(htop != atop), 'lower_zone_asymmetry': float(hlow != alow),
                'same_competitive_band': float((htop == atop) and (hlow == alow)),
                'win_changes_direct_points_gap': float(hwin_gap - point_gap),
                'draw_changes_direct_points_gap': float(draw_gap - point_gap),
                'away_win_changes_direct_points_gap': float(awin_gap - point_gap),
                'point_gap_if_home_win': float(hwin_gap), 'point_gap_if_draw': float(draw_gap),
                'point_gap_if_away_win': float(awin_gap),
                'target_league_table_available': 1.0,
                'expected_season_matches_prior_seasons': float(expected or 0.0),
                'expected_round_count_prior_seasons': float(max_round or 0),
            }
            round_match = re.search(r'(\d+)\s*\.??\s*matchday', r['tm_round'].lower())
            matchday = float(round_match.group(1)) if round_match else 0.0
            feat['round_number'] = matchday
            feat['round_progress'] = matchday / max_round if max_round else 0.0
            feat.update(phase)
            target_base_features[r['fid']] = feat
            table_qc['domestic_league_target_features'] += 1
            table_qc['prior_round_capacity_missing'] += int(expected is None)
            # Source positions are held out as a validation-only field. The
            # calculated table must not be copied from the target match row.
            if r['source_home_position_validation_only'] is not None:
                position_validation['source_position_present'] += 1
                position_validation['home_rank_exact'] += int(abs(hrank - r['source_home_position_validation_only']) < 1e-8)
            if r['source_away_position_validation_only'] is not None:
                position_validation['source_position_present'] += 1
                position_validation['away_rank_exact'] += int(abs(arank - r['source_away_position_validation_only']) < 1e-8)
        else:
            feat = {k: 0.0 for k in [
                'h_points','a_points','points_gap_home_minus_away','h_points_per_game','a_points_per_game',
                'h_goal_diff_per_game','a_goal_diff_per_game','h_rank_pct','a_rank_pct','h_rank','a_rank',
                'h_points_gap_leader','a_points_gap_leader','h_title_gap_remaining_ratio','a_title_gap_remaining_ratio',
                'h_remaining_matches_est','a_remaining_matches_est','h_season_progress','a_season_progress',
                'h_top4_position_proxy','a_top4_position_proxy','h_bottom3_position_proxy','a_bottom3_position_proxy',
                'both_top4_proxy','both_bottom3_proxy','upper_zone_asymmetry','lower_zone_asymmetry',
                'same_competitive_band','win_changes_direct_points_gap','draw_changes_direct_points_gap',
                'away_win_changes_direct_points_gap','point_gap_if_home_win','point_gap_if_draw',
                'point_gap_if_away_win','expected_season_matches_prior_seasons','expected_round_count_prior_seasons',
                'round_number','round_progress',
            ]}
            feat.update(phase)
            feat['target_league_table_available'] = 0.0
            target_base_features[r['fid']] = feat
            if phase['is_cup_competition']:
                table_qc['cup_target_rows'] += 1
            if phase['is_knockout_or_playoff_round']:
                table_qc['knockout_or_playoff_target_rows'] += 1

# Add pre-match prior-leg aggregate information. Require an earlier same-pair
# knockout fixture; absence is not treated as proof the target is a first leg.
tie_qc = collections.Counter()
for r in target_rows:
    feat = target_base_features.get(r['fid'])
    if feat is None:
        continue
    comp, season = r['tm_competition_id'], r['tm_season']
    if season is None:
        continue
    pair = frozenset((r['home_tm_id'], r['away_tm_id']))
    hist = prior_ko_events.get((comp, int(season), pair), [])
    cutoff = parse_day(r['date']) - dt.timedelta(days=LAG_DAYS)
    prior = [g for g in hist if g['date'] <= cutoff]
    feat['prior_same_pair_knockout_meetings'] = float(len(prior))
    feat['prior_tie_aggregate_known'] = float(bool(prior))
    feat['prior_tie_home_goal_diff'] = 0.0
    feat['prior_tie_total_goals'] = 0.0
    if prior:
        hgd = htg = atg = 0
        for g in prior:
            if g['home_club_id'] == r['home_tm_id']:
                hgd += g['hg'] - g['ag']; htg += g['hg']; atg += g['ag']
            else:
                hgd += g['ag'] - g['hg']; htg += g['ag']; atg += g['hg']
        feat['prior_tie_home_goal_diff'] = float(hgd)
        feat['prior_tie_total_goals'] = float(htg + atg)
        tie_qc['prior_tie_known'] += 1
    if phase_flags(r['tm_round'], r['tm_competition_type'])['is_cup_competition']:
        tie_qc['cup_row'] += 1

# Keep a single complete support for all model variants; do not impute missing
# competitive-table state. AH market baseline is evaluated on the exact same
# rows as every added-information model.
rows = []
rejects = collections.Counter()
for r in target_rows:
    # Keep all pre-2024 rows as historical training data. Only predictions
    # and economic evaluation are restricted to TEST_YEARS below.
    if r['year'] > max(TEST_YEARS) or parse_day(r['date']) > DATA_CUTOFF:
        continue
    f = target_base_features.get(r['fid'])
    if not f:
        rejects['no_pregame_feature'] += 1
        continue
    if f['target_league_table_available'] != 1:
        rejects['no_reconstructed_domestic_table'] += 1
        continue
    if not f['expected_round_count_prior_seasons'] or not f['expected_season_matches_prior_seasons']:
        rejects['no_prior_season_schedule_capacity'] += 1
        continue
    if any(not math.isfinite(float(v)) for v in f.values()):
        rejects['nonfinite_feature'] += 1
        continue
    rows.append({**r, **f})
rows.sort(key=lambda r: (r['date'], r['fid']))
row_fids = [r['fid'] for r in rows]
assert len(row_fids) == len(set(row_fids))

MARKET_NAMES = ['line','favorite_share','overround','side_price_skew','abs_line','line_price_interaction']
TABLE_NAMES = [
    'h_points_per_game','a_points_per_game','h_goal_diff_per_game','a_goal_diff_per_game',
    'h_rank_pct','a_rank_pct','h_points_gap_leader','a_points_gap_leader',
    'h_title_gap_remaining_ratio','a_title_gap_remaining_ratio',
    'h_remaining_matches_est','a_remaining_matches_est','h_season_progress','a_season_progress',
    'h_top4_position_proxy','a_top4_position_proxy','h_bottom3_position_proxy','a_bottom3_position_proxy',
    'both_top4_proxy','both_bottom3_proxy','upper_zone_asymmetry','lower_zone_asymmetry',
    'same_competitive_band','points_gap_home_minus_away','win_changes_direct_points_gap',
    'point_gap_if_home_win','point_gap_if_draw','point_gap_if_away_win',
]
STAGE_NAMES = ['round_progress','round_number','is_cup_competition','is_knockout_or_playoff_round',
               'is_qualifying_round','is_round_of_16','is_quarter_final','is_semi_final','is_final',
               'is_championship_phase','is_relegation_phase','is_playoff_phase']
TIE_NAMES = ['prior_same_pair_knockout_meetings','prior_tie_aggregate_known',
             'prior_tie_home_goal_diff','prior_tie_total_goals']


def market_vec(r: dict) -> np.ndarray:
    inv_h, inv_a = 1.0 / r['AH_home_odds'], 1.0 / r['AH_away_odds']
    s = inv_h + inv_a
    skew = (inv_h - inv_a) / s
    return np.array([r['AH_line'], inv_h / s, s - 1.0, skew,
                     abs(r['AH_line']), r['AH_line'] * skew], dtype=float)


def vec(r: dict, keys: list[str]) -> np.ndarray:
    return np.array([float(r[k]) for k in keys], dtype=float)


def design(r: dict, model: str) -> np.ndarray:
    m = market_vec(r)
    t = vec(r, TABLE_NAMES)
    s = vec(r, STAGE_NAMES)
    k = vec(r, TIE_NAMES)
    if model == 'A_market_only': return m
    if model == 'B_market_plus_season_table': return np.r_[m, t]
    if model == 'C_market_plus_competitive_value':
        ix = [TABLE_NAMES.index(x) for x in ['h_title_gap_remaining_ratio','a_title_gap_remaining_ratio',
             'h_top4_position_proxy','a_top4_position_proxy','h_bottom3_position_proxy','a_bottom3_position_proxy',
             'both_top4_proxy','both_bottom3_proxy','upper_zone_asymmetry','lower_zone_asymmetry',
             'points_gap_home_minus_away','point_gap_if_home_win','point_gap_if_draw','point_gap_if_away_win']]
        return np.r_[m, t[ix]]
    if model == 'D_market_plus_season_stage': return np.r_[m, s]
    if model == 'E_market_plus_table_stage_interactions':
        # Only interact AH contract depth/price skew with pre-match table-state
        # variables; all thresholds and coefficients are walk-forward fitted.
        return np.r_[m, t, s, t * m[0], t * m[3]]
    if model == 'F_market_plus_table_stage_and_prior_tie': return np.r_[m, t, s, k]
    if model == 'G_competition_information_only': return np.r_[t, s, k]
    raise KeyError(model)


def settlement_detail(line: float, side: str, hg: int, ag: int, odds: float) -> tuple[float, str]:
    line = float(line); odds = float(odds)
    if abs(line * 4 - round(line * 4)) > 1e-8:
        raise ValueError(f'AH line outside quarter grid: {line}')
    twice = round(line * 2)
    legs = [line] if abs(twice / 2 - line) < 1e-8 else [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
    legs_pnl = []
    for leg in legs:
        adj = hg - ag + leg if side == 'home' else ag - hg - leg
        legs_pnl.append(odds - 1.0 if adj > 1e-9 else -1.0 if adj < -1e-9 else 0.0)
    pnl = sum(legs_pnl) / len(legs_pnl)
    if all(v > 0 for v in legs_pnl): label = 'full_win'
    elif any(v > 0 for v in legs_pnl): label = 'half_win'
    elif all(v == 0 for v in legs_pnl): label = 'push'
    elif any(v == 0 for v in legs_pnl): label = 'half_loss'
    else: label = 'full_loss'
    return pnl, label


def metrics(records: list[dict]) -> dict:
    if not records:
        return {'n':0,'net_U':0.0,'ROI_pct':None,'max_drawdown_U':0.0,
                'weeks':0,'active_weeks':0,'avg_per_calendar_week':0.0,'weekly':{}}
    daily = collections.defaultdict(float); week = collections.defaultdict(lambda: {'n':0,'U':0.0})
    for r in records:
        daily[r['date']] += r['actual_side_U']
        iso = dt.date.fromisoformat(r['date']).isocalendar()
        wk = f'{iso.year}-W{iso.week:02}'
        week[wk]['n'] += 1; week[wk]['U'] += r['actual_side_U']
    c = peak = mdd = 0.0
    for day in sorted(daily):
        c += daily[day]; peak = max(peak, c); mdd = max(mdd, peak - c)
    n = len(records); u = sum(r['actual_side_U'] for r in records)
    d0, d1 = dt.date.fromisoformat(min(r['date'] for r in records)), dt.date.fromisoformat(max(r['date'] for r in records))
    calendar_weeks = (d1 - d0).days // 7 + 1
    return {
        'n': n, 'net_U': round(u, 6), 'ROI_pct': round(100*u/n, 6),
        'max_drawdown_U': round(mdd, 6), 'weeks': len(week),
        'calendar_weeks': calendar_weeks, 'active_weeks': len(week),
        'avg_per_calendar_week': round(n / calendar_weeks, 6),
        'positive_weeks': sum(v['U'] > 1e-10 for v in week.values()),
        'negative_weeks': sum(v['U'] < -1e-10 for v in week.values()),
        'weekly': {k:{'n':v['n'],'net_U':round(v['U'],6)} for k,v in sorted(week.items())},
    }


models = [
    'A_market_only','B_market_plus_season_table','C_market_plus_competitive_value',
    'D_market_plus_season_stage','E_market_plus_table_stage_interactions',
    'F_market_plus_table_stage_and_prior_tie','G_competition_information_only',
]
predictions: dict[str, list[dict]] = {m: [] for m in models}
fit_records = {}
for year in TEST_YEARS:
    train = [r for r in rows if int(r['year']) < year]
    test = [r for r in rows if int(r['year']) == year]
    if not train or not test:
        fit_records[str(year)] = {'train_n':len(train),'test_n':len(test),'status':'empty'}
        continue
    fit_records[str(year)] = {'train_n':len(train),'test_n':len(test),'models':{}}
    for model in models:
        X = np.vstack([design(r, model) for r in train])
        Z = np.vstack([design(r, model) for r in test])
        y = np.array([r['home_U'] - r['away_U'] for r in train], dtype=float)
        mu, sd = X.mean(0), X.std(0)
        mu[0] = 0.0; sd[0] = 1.0; sd[sd < 1e-10] = 1.0
        xs, zs = (X-mu)/sd, (Z-mu)/sd
        penalty = np.eye(X.shape[1]) * RIDGE; penalty[0,0] = 0.0
        beta = np.linalg.solve(xs.T @ xs + penalty, xs.T @ y)
        yhat = zs @ beta
        fit_records[str(year)]['models'][model] = {
            'feature_count':int(X.shape[1]),'ridge_alpha':RIDGE,
            'train_min_year':min(int(r['year']) for r in train),
            'train_max_year':max(int(r['year']) for r in train),
            'train_n':len(train),'test_n':len(test),'coefficients':beta.tolist(),
        }
        for r, score in zip(test, yhat):
            side = 'home' if score >= 0 else 'away'
            odds = r['AH_home_odds'] if side == 'home' else r['AH_away_odds']
            pnl, result_class = settlement_detail(r['AH_line'], side, r['hg'], r['ag'], odds)
            predictions[model].append({
                'fid':r['fid'],'year':r['year'],'date':r['date'],'league_id':r['league'],
                'tm_competition_id':r['tm_competition_id'],'tm_season':r['tm_season'],
                'tm_round':r['tm_round'],'competition_type':r['tm_competition_type'],
                'home_name':r['home_name'],'away_name':r['away_name'],
                'AH_line_home':r['AH_line'],'AH_home_odds':r['AH_home_odds'],'AH_away_odds':r['AH_away_odds'],
                'prediction_home_minus_away_netU':float(score),'direction':side,
                'FT_home':r['hg'],'FT_away':r['ag'],'settlement_class':result_class,'actual_side_U':pnl,
                'feature_data_cutoff_date':(parse_day(r['date'])-dt.timedelta(days=LAG_DAYS)).isoformat(),
                'source_utc_date_minus_3_lag':LAG_DAYS,
                'frozen_eight_overlap_posthoc':r['fid'] in members,
                'features':{k:float(r[k]) for k in TABLE_NAMES+STAGE_NAMES+TIE_NAMES},
            })

# No target-year outcomes influence the model parameters or definitions.
# Frozen membership is applied only now, to calculate unique incremental PnL.
frozen_window = [r for r in members.values()
                 if 2024 <= int(r['year']) <= 2026 and r['date'] <= DATA_CUTOFF.isoformat()]
frozen_by_year = {str(y): [r for r in frozen_window if int(r['year']) == y] for y in TEST_YEARS}
summary_models = {}
pair_overlap = {}
all_fids_by_model = {}
for model, ledger in predictions.items():
    fids = {r['fid'] for r in ledger}
    all_fids_by_model[model] = fids
    inc = [r for r in ledger if not r['frozen_eight_overlap_posthoc']]
    annual = {}
    combined_annual = {}
    for y in TEST_YEARS:
        yy = [r for r in inc if int(r['year']) == y]
        annual[str(y)] = metrics(yy)
        base = frozen_by_year[str(y)]
        base_fids = {str(r['fid']) for r in base}
        combined = [{'date':r['date'],'actual_side_U':float(r['pnl'])} for r in base]
        combined += [{'date':r['date'],'actual_side_U':r['actual_side_U']} for r in yy if r['fid'] not in base_fids]
        combined_annual[str(y)] = metrics(combined)
    comb = [{'date':r['date'],'actual_side_U':float(r['pnl'])} for r in frozen_window]
    frozen_fids = {str(r['fid']) for r in frozen_window}
    comb += [{'date':r['date'],'actual_side_U':r['actual_side_U']} for r in inc if r['fid'] not in frozen_fids]
    result_counts = collections.Counter(r['settlement_class'] for r in inc)
    by_goal = {}
    for name in ['h_top4_position_proxy','a_top4_position_proxy','h_bottom3_position_proxy','a_bottom3_position_proxy',
                 'both_top4_proxy','both_bottom3_proxy','upper_zone_asymmetry','lower_zone_asymmetry',
                 'is_playoff_phase','is_relegation_phase','is_championship_phase','is_knockout_or_playoff_round',
                 'prior_tie_aggregate_known']:
        group = [r for r in inc if r['features'][name] == 1.0]
        if group:
            by_goal[name] = metrics(group)
    summary_models[model] = {
        'all_test_fids':len(fids), 'frozen_overlap_fids':len(fids & set(members)),
        'incremental_unique_fids':len(inc), 'incremental':metrics(inc),
        'incremental_annual':annual, 'settlement_classes_incremental':dict(result_counts),
        'descriptive_non_gate_groups':by_goal,
        'frozen_eight_same_period':metrics([{'date':r['date'],'actual_side_U':float(r['pnl'])} for r in frozen_window]),
        'combined_frozen_plus_incremental_annual':combined_annual,
        'combined_frozen_plus_incremental':metrics(comb),
        'incremental_profit_delta_vs_frozen_U':round(sum(r['actual_side_U'] for r in inc),6),
    }
for a in models:
    pair_overlap[a] = {}
    for b in models:
        pair_overlap[a][b] = len(all_fids_by_model[a] & all_fids_by_model[b])

# Receipt audit: the actual M8 Crown receipt cohort is all post-source-cutoff.
receipt_fids_after_cutoff = sum(parse_day(r['date']) > DATA_CUTOFF for r in R)
receipt_feature_fids = sum(str(r['fid']) in target_base_features for r in R)

# Position field is validation only. Count exact agreement among mapped rows.
source_pos_n = position_validation['source_position_present']
position_validation_out = {
    **dict(position_validation),
    'exact_agreement_rate_over_positions': round(
        (position_validation['home_rank_exact']+position_validation['away_rank_exact'])/source_pos_n,6
    ) if source_pos_n else None,
    'target_row_positions_used_as_predictors':False,
}

# Feature rows retain all field-level diagnostics; prediction ledger retains
# all directions and the quarter-line result class for each model/FID.
with gzip.open(OUT/'m8_competitive_objective_feature_rows_20261119.jsonl.gz','wt',encoding='utf-8') as f:
    for r in rows:
        f.write(json.dumps({k:v for k,v in r.items() if k not in ('source_home_position_validation_only','source_away_position_validation_only')},ensure_ascii=False,separators=(',',':'))+'\n')
with gzip.open(OUT/'m8_competitive_objective_prediction_ledger_20261119.jsonl.gz','wt',encoding='utf-8') as f:
    for model, ledger in predictions.items():
        for r in ledger:
            f.write(json.dumps({'model':model,**r},ensure_ascii=False,separators=(',',':'))+'\n')

summary = {
    'study':'M8_COMPETITIVE_OBJECTIVE_POINTS_VALUE_CROWN_AH_20261119',
    'research_only':True,'production_models_telegram_ledger_collection_unchanged':True,
    'time_forward':'test 2024 uses all earlier-year rows; test 2025 uses only years <2025; test 2026 uses only years <2026 and is cut at 2026-07-06. Feature results use only same competition-season completed games on dates <= target UTC date minus 3 days.',
    'prior_research_dedup':{
        'R44':'R44 tested 365/90-day rolling points, goal difference, ranks and recent momentum; this run uses explicit competition-season keys and reconstructs a date-specific table. No rolling-window feature is reused.',
        'R43':'R43 tested league-level market response calibration; not repeated.',
        'R46':'R46 tested UTC kickoff calendar interactions; not reused.',
        'R49':'The already audited 453-team one-to-one team identity bridge is reused as a join only.',
    },
    'input_audit':{
        'games_path':str(games_path),'games_sha256':games_sha,'games_rows':len(games),
        'games_date_min':min(games.date).isoformat(),'games_date_max':max(games.date).isoformat(),
        'competitions_sha256':sha(SRC/'competitions.csv.gz'),
        'frozen_membership_sha256':member_sha,'frozen_membership_n':len(members),
        'prior_manager_bootstrap_sha256':sha(prior_path),
        'Crown_history_H_rows':len(H),'Crown_receipt_R_rows':len(R),
        'Crown_schedule_pages_read':schedule_pages,'Crown_fid_inventory':len(crown_fixtures),
        'schedule_conflicts':dict(schedule_errors),
        'team_crosswalk_league_keyed':len(teammap),'globally_unique_team_ids':len(global_teammap),
    },
    'coverage':{
        'H_total':len(H),'target_to_TM_identity_join':dict(join_qc),
        'matched_target_rows':len(target_rows),'matched_target_competition_types':dict(collections.Counter(r['tm_competition_type'] for r in target_rows)),
        'matched_target_competition_ids':dict(collections.Counter(r['tm_competition_id'] for r in target_rows)),
        'target_year_counts':{str(y):sum(r['year']==y for r in target_rows) for y in TEST_YEARS},
        'target_data_cutoff':DATA_CUTOFF.isoformat(),'feature_rows_all_years_for_training_and_test':len(rows),
        'training_rows_by_year':{str(y):sum(r['year']==y for r in rows if r['year'] not in TEST_YEARS) for y in sorted({r['year'] for r in rows if r['year'] not in TEST_YEARS})},
        'feature_rows_common':sum(r['year'] in TEST_YEARS for r in rows),
        'feature_rows_by_year':{str(y):sum(r['year']==y for r in rows) for y in TEST_YEARS},
        'feature_rejections':dict(rejects),'table_audit':dict(table_qc),
        'prior_season_position_validation':position_validation_out,
        'knockout_tie_audit':dict(tie_qc),
        'actual_receipt_FIDs':len(R),'actual_receipt_FIDs_after_games_source_cutoff':receipt_fids_after_cutoff,
        'actual_receipt_FIDs_with_target_feature_rows':receipt_feature_fids,
        'receipt_profit_claim':'No contemporaneous receipt-versioned standings snapshots exist in the source. Historical current-table features are not represented as real-time receipt information; do not call this live-receipt ROI.',
    },
    'model_parameters':{'models':models,'ridge_alpha':RIDGE,'target':'Crown AH home_U minus away_U','training':'expanding earlier calendar years only; standardize on training rows; keep same test cohort for every model; no target-year tuning.','bet_direction':'per fixture choose the side with higher predicted Crown netU; no production gate or candidate threshold.'},
    'walkforward_fits':fit_records,
    'models':summary_models,'pairwise_test_fid_overlap':pair_overlap,
    'frozen_eight_AH_same_period':summary_models[models[0]]['frozen_eight_same_period'],
    'all_research_parameters_nonproduction':True,
}
(OUT/'M8_COMPETITIVE_OBJECTIVE_RESULTS_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'coverage':summary['coverage'],'models':{k:{'incremental':v['incremental'],'annual':v['incremental_annual'],'combined':v['combined_frozen_plus_incremental']} for k,v in summary_models.items()}},ensure_ascii=False),flush=True)
