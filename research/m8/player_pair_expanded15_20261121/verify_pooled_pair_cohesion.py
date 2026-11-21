#!/usr/bin/env python3
"""Independent Crown raw-response and AH settlement audit for expanded15 pair study."""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
from zoneinfo import ZoneInfo

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[3]
FOUNDATION = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
REPORT_INPUT = OUT / 'pooled_pair_cohesion_summary.json'
PREDICTIONS = OUT / 'pooled_pair_cohesion_predictions.jsonl.gz'
RAW_INDEX = OUT / 'expanded15_T12_candidate_source_audit.jsonl.gz'
TZ = ZoneInfo('Asia/Shanghai')
UTC = dt.timezone.utc


def sha(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: pathlib.Path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def read_gz(path: pathlib.Path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def crown_local(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ)
    return parsed.astimezone(UTC)


def settle(line: float, side: str, hg: int, ag: int, odds: float) -> tuple[float, str]:
    line = float(line)
    if abs(line * 4 - round(line * 4)) > 1e-8:
        raise ValueError(f'AH line is outside quarter grid: {line}')
    if abs(line * 2 - round(line * 2)) < 1e-8:
        legs = [line]
    else:
        legs = [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
    payouts = []
    for leg in legs:
        margin = hg - ag + leg if side == 'home' else ag - hg - leg
        payouts.append(odds - 1 if margin > 1e-9 else -1.0 if margin < -1e-9 else 0.0)
    net = sum(payouts) / len(payouts)
    if all(x > 0 for x in payouts):
        label = 'full_win'
    elif any(x > 0 for x in payouts):
        label = 'half_win'
    elif all(x == 0 for x in payouts):
        label = 'push'
    elif any(x == 0 for x in payouts):
        label = 'half_loss'
    else:
        label = 'full_loss'
    return net, label


def raw_match(body: bytes, fid: str) -> dict:
    payload = json.loads(body)
    matches = payload.get('data') or []
    if isinstance(matches, dict):
        matches = matches.get('matches') or [matches]
    found = [row for row in matches if str(row.get('id')) == fid]
    if len(found) != 1:
        raise ValueError(f'raw response has {len(found)} records for FID {fid}')
    return found[0]


def latest_crown_t12(match: dict, cutoff: dt.datetime) -> tuple[dt.datetime, float, float, float]:
    books = [book for book in match.get('bookmakers') or [] if str(book.get('slug', '')).lower() == 'crown']
    if len(books) != 1:
        raise ValueError(f'raw Crown bookmaker count={len(books)}')
    eligible = []
    for quote in books[0].get('asian_list') or []:
        try:
            line, home, away = float(quote[1]), float(quote[2]), float(quote[3])
            timestamp = crown_local(quote[4])
        except (IndexError, TypeError, ValueError):
            continue
        if (timestamp <= cutoff and home > 1 and away > 1 and
                abs(line * 4 - round(line * 4)) < 1e-7):
            eligible.append((timestamp, line, home, away))
    if not eligible:
        raise ValueError('no valid Crown asian_list event at or before T12')
    return max(eligible, key=lambda row: row[0])


def main() -> None:
    summary = json.loads(REPORT_INPUT.read_text(encoding='utf-8'))
    identity_path = OUT / 'identity_coverage_audit.json'
    identity = json.loads(identity_path.read_text(encoding='utf-8'))
    predictions = list(read_gz(PREDICTIONS))
    source_rows = list(read_gz(RAW_INDEX))
    foundation = list(read_jsonl(FOUNDATION))
    frozen_ids = {str(row['fid']) for row in foundation}
    source_by_fid = {str(row['fid']): row for row in source_rows}
    issues = collections.Counter()
    checked_inputs = 0
    for raw_path, expected_sha in summary.get('inputs_sha256', {}).items():
        path = pathlib.Path(raw_path)
        try:
            if sha(path) != expected_sha:
                issues['study_input_sha_mismatch'] += 1
            checked_inputs += 1
        except OSError:
            issues['study_input_missing'] += 1
    schedule_sha_items = identity.get('inputs_sha256', {}).get('schedule_pages', {})
    for raw_path, expected_sha in schedule_sha_items.items():
        path = pathlib.Path(raw_path)
        try:
            if sha(path) != expected_sha:
                issues['schedule_page_sha_mismatch'] += 1
            checked_inputs += 1
        except OSError:
            issues['schedule_page_missing'] += 1
    raw_checked = set()
    contract_by_fid = {}
    representative_by_fid = {}
    settlement_counts = collections.Counter()
    model_summary = collections.defaultdict(lambda: {'n': 0, 'net_u': 0.0, 'mdd_u': 0.0})
    rows_by_model = collections.defaultdict(list)
    error_by_model = collections.defaultdict(list)

    for row in predictions:
        fid, method = str(row['fid']), str(row['method'])
        if row.get('source') != 'expanded15':
            issues['wrong_target_source'] += 1
        if fid in frozen_ids or row.get('frozen_overlap'):
            issues['frozen_fid_overlap'] += 1
        if row.get('actual_receipt_fid_overlap'):
            issues['receipt_overlap_flagged'] += 1
        if int(row['training_max_year']) >= int(row['year']):
            issues['future_year_in_training'] += 1
        if int(row['training_year_cutoff_exclusive']) != int(row['year']):
            issues['training_cutoff_mismatch'] += 1

        cutoff_date = dt.date.fromisoformat(row['feature_cutoff_date'])
        for side in ('home', 'away'):
            feature = row[f'pair_features_{side}']
            history_date = feature.get('last_history_date')
            if not history_date or dt.date.fromisoformat(history_date) > cutoff_date:
                issues['feature_history_after_cutoff_or_missing'] += 1

        fid_contract = (row['league'], row['home'], row['away'], row['kickoff_utc'],
                        row['hg'], row['ag'], row['line'], row['home_odds'], row['away_odds'],
                        row['Crown_T12_source_event_utc'], row['response_sha256'])
        if fid in contract_by_fid and contract_by_fid[fid] != fid_contract:
            issues['method_contract_disagreement'] += 1
        contract_by_fid[fid] = fid_contract
        representative_by_fid.setdefault(fid, row)

        if fid not in raw_checked:
            source = source_by_fid.get(fid)
            if source is None:
                issues['missing_source_index_row'] += 1
            else:
                representative = representative_by_fid[fid]
                raw_path = pathlib.Path(source['source_file'])
                try:
                    body = raw_path.read_bytes()
                    if hashlib.sha256(body).hexdigest() != source['response_sha256']:
                        issues['raw_response_sha_mismatch'] += 1
                    match = raw_match(body, fid)
                    for key, raw_key in (('league', 'l_id'), ('home_id', 'h_id'), ('away_id', 'a_id')):
                        expected = str(representative[key]) if representative.get(key) is not None else None
                        if expected and str(match.get(raw_key)) != expected:
                            issues[f'raw_{key}_mismatch'] += 1
                    if int(match.get('hg')) != int(representative['hg']) or int(match.get('ag')) != int(representative['ag']):
                        issues['raw_ft_mismatch'] += 1
                    if str(match.get('status')) != 'full':
                        issues['raw_status_not_full'] += 1
                    kickoff = crown_local(match['start'])
                    if kickoff != utc(representative['kickoff_utc']):
                        issues['raw_kickoff_mismatch'] += 1
                    cutoff = utc(representative['T12_cutoff_utc'])
                    timestamp, line, home_odds, away_odds = latest_crown_t12(match, cutoff)
                    if timestamp != utc(source['T12_source_event_utc']):
                        issues['raw_T12_source_time_mismatch'] += 1
                    if (line != float(source['T12_home_line']) or home_odds != float(source['T12_home_odds']) or
                            away_odds != float(source['T12_away_odds'])):
                        issues['raw_T12_contract_mismatch'] += 1
                    if source.get('capture_mode') != 'historical':
                        issues['not_historical_capture'] += 1
                    if utc(source['T12_response_received_utc']) <= utc(source['T12_source_event_utc']):
                        issues['historical_receipt_time_not_later_than_source'] += 1
                except Exception as exc:  # preserve exact failing fixture in audit
                    issues['raw_fixture_audit_exception'] += 1
                    issues[f'raw_error:{fid}:{type(exc).__name__}:{str(exc)[:120]}'] += 1
            raw_checked.add(fid)

        if row.get('chosen_side') not in ('home', 'away'):
            issues['unknown_bet_side'] += 1
            continue
        odds = float(row['home_odds'] if row['chosen_side'] == 'home' else row['away_odds'])
        if abs(odds - float(row['chosen_odds'])) > 1e-9:
            issues['chosen_odds_mismatch'] += 1
        pnl, label = settle(float(row['line']), row['chosen_side'], int(row['hg']), int(row['ag']), odds)
        if label != row['settlement']:
            issues['settlement_label_mismatch'] += 1
        if abs(pnl - float(row['net_u'])) > 1e-8:
            issues['settlement_pnl_mismatch'] += 1
        settlement_counts[label] += 1
        rows_by_model[method].append({**row, 'net_u_recomputed': pnl})
        error_by_model[method].append((float(row['predicted_home_goal_difference']), int(row['gd'])))

    expected_methods = {'market_only', 'pair_only', 'market_plus_pair'}
    if set(row['method'] for row in predictions) != expected_methods:
        issues['method_set_mismatch'] += 1
    for method, rows in rows_by_model.items():
        rows.sort(key=lambda row: (row['date'], row['fid']))
        daily = collections.defaultdict(float)
        for row in rows:
            daily[row['date']] += row['net_u_recomputed']
        total = peak = mdd = 0.0
        for day in sorted(daily):
            total += daily[day]
            peak = max(peak, total)
            mdd = max(mdd, peak - total)
        model_summary[method] = {'n': len(rows), 'unique_fids': len({row['fid'] for row in rows}),
                                 'net_u': round(sum(row['net_u_recomputed'] for row in rows), 6),
                                 'roi_pct': round(sum(row['net_u_recomputed'] for row in rows) / len(rows) * 100, 6) if rows else None,
                                 'mdd_u': round(mdd, 6)}

    if not foundation:
        issues['frozen_membership_empty'] += 1
    frozen_net = sum(float(row['pnl']) for row in foundation)
    if len(frozen_ids) != 10294 or abs(frozen_net - 236.015) > 1e-6:
        issues['frozen_membership_count_or_pnl_mismatch'] += 1
    if sha(FOUNDATION) != '6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665':
        issues['frozen_membership_sha_mismatch'] += 1
    target_dates = [dt.date.fromisoformat(row['date']) for row in representative_by_fid.values()]
    first_date, last_date = min(target_dates), max(target_dates)
    frozen_period = [row for row in foundation if first_date <= dt.date.fromisoformat(str(row['date'])[:10]) <= last_date]
    frozen_period_pnl = sum(float(row['pnl']) for row in frozen_period)
    merged_period = {}
    monthly = {}
    prediction_quality = {}
    span_weeks = (last_date - first_date).days // 7 + 1
    for method, rows in rows_by_model.items():
        merged_dates = collections.defaultdict(float)
        for row in frozen_period:
            merged_dates[str(row['date'])[:10]] += float(row['pnl'])
        for row in rows:
            merged_dates[row['date']] += row['net_u_recomputed']
        total = peak = drawdown = 0.0
        for day in sorted(merged_dates):
            total += merged_dates[day]
            peak = max(peak, total)
            drawdown = max(drawdown, peak - total)
        merged_net = frozen_period_pnl + sum(row['net_u_recomputed'] for row in rows)
        merged_n = len(frozen_period) + len(rows)
        merged_period[method] = {
            'frozen_same_period_n': len(frozen_period),
            'frozen_same_period_net_u': round(frozen_period_pnl, 6),
            'candidate_n': len(rows), 'candidate_net_u': round(sum(row['net_u_recomputed'] for row in rows), 6),
            'unique_fids': len(frozen_period) + len({row['fid'] for row in rows}),
            'net_u': round(merged_net, 6), 'roi_pct': round(merged_net / merged_n * 100, 6),
            'mdd_u': round(drawdown, 6), 'span_weeks': span_weeks,
            'frozen_orders_per_week': round(len(frozen_period) / span_weeks, 6),
            'candidate_orders_per_week': round(len(rows) / span_weeks, 6),
            'combined_orders_per_week': round(merged_n / span_weeks, 6),
        }
        month_groups = collections.defaultdict(list)
        for row in rows:
            month_groups[row['date'][:7]].append(row)
        monthly[method] = {}
        for month, subset in sorted(month_groups.items()):
            month_net = sum(row['net_u_recomputed'] for row in subset)
            monthly[method][month] = {'n': len(subset), 'net_u': round(month_net, 6),
                'roi_pct': round(month_net / len(subset) * 100, 6)}
        errors = error_by_model[method]
        prediction_quality[method] = {
            'n': len(errors),
            'goal_difference_MAE': round(sum(abs(pred - actual) for pred, actual in errors) / len(errors), 8),
            'goal_difference_RMSE': round(math.sqrt(sum((pred - actual) ** 2 for pred, actual in errors) / len(errors)), 8),
            'actual_goal_difference_mean_absolute': round(sum(abs(actual) for _, actual in errors) / len(errors), 8),
        }

    target_ids = set(contract_by_fid)
    expected_count = int(summary['coverage']['expanded15_feature_complete_rows'])
    if len(target_ids) != expected_count:
        issues['candidate_fid_count_mismatch'] += 1
    if target_ids & frozen_ids:
        issues['candidate_frozen_overlap'] += len(target_ids & frozen_ids)
    if len(predictions) != expected_count * len(expected_methods):
        issues['prediction_row_count_mismatch'] += 1
    for method in expected_methods:
        recomputed = model_summary.get(method, {})
        expected = summary['models'][method]['expanded15_incremental']
        for key, audit_key in (('n', 'n'), ('net_U', 'net_u'), ('MDD_U', 'mdd_u')):
            if recomputed.get(audit_key) != expected.get(key):
                issues[f'{method}_{key}_summary_mismatch'] += 1

    audit = {
        'study': 'expanded15 player-pair cohesion independent raw Crown and AH settlement audit',
        'raw_unique_fids_checked': len(raw_checked),
        'study_inputs_sha_checked': checked_inputs,
        'schedule_page_sha_checked': len(schedule_sha_items),
        'expected_candidate_fids': expected_count,
        'prediction_rows_checked': len(predictions),
        'expected_prediction_rows': expected_count * len(expected_methods),
        'frozen_membership_fids': len(frozen_ids),
        'candidate_frozen_overlap_fids': len(target_ids & frozen_ids),
        'training_max_year_le_target_year': all(int(row['training_max_year']) < int(row['year']) for row in predictions),
        'settlements': dict(settlement_counts),
        'models_recomputed': dict(model_summary),
        'market_predictions_evaluation': prediction_quality,
        'frozen_eight_same_period_and_merged': merged_period,
        'monthly_incremental': monthly,
        'errors': dict(issues),
        'verified': not issues and len(raw_checked) == expected_count,
        'input_sha256': {str(path): sha(path) for path in (REPORT_INPUT, PREDICTIONS, RAW_INDEX, FOUNDATION)},
    }
    (OUT / 'independent_raw_crown_settlement_audit.json').write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if issues:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
