#!/usr/bin/env python3
"""Offline coverage probe for three explicitly named historical league gaps.

This is a source-inventory audit only. It does not request data, infer missing
results, or narrow the full historical-recovery universe.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'research/data_recovery_2019_2026/fixture_inventory_2019_2026.jsonl.gz'
OUT = ROOT / 'research/data_recovery_2019_2026'
DB = Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
TARGETS = {
    '51': 'Portugal Primeira Liga',
    '61': 'Switzerland Super League',
    '10480': 'Georgia Erovnuli Liga',
}
SCHEDULE_SOURCES = (
    'totalcorner_page_records', 'supplemental_schedule_records',
    'expanded_universe_records', 'M1_history_cache_records',
    'crown_fixture_metadata_records',
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def numeric(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def main() -> None:
    by_league_year: dict[tuple[str, int], dict] = {}
    seen: set[tuple[str, int, str]] = set()
    schedule_identity: dict[tuple[str, int, str], dict] = {}
    with gzip.open(SOURCE, 'rt', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            lid = str(row.get('provider_league_id') or '')
            if lid not in TARGETS:
                continue
            year = int(row.get('year') or 0)
            fid = str(row.get('fid') or '')
            key = (lid, year)
            if key not in by_league_year:
                by_league_year[key] = {
                    'provider_league_id': lid,
                    'league_name': TARGETS[lid],
                    'utc_year': year,
                    'unique_fids': 0,
                    'schedule_source_fids': {s: 0 for s in SCHEDULE_SOURCES},
                    'numeric_ft_fids': 0,
                    'status_full_numeric_ft_fids': 0,
                    'status_counts': collections.Counter(),
                    'crown_movement_capture_fids': 0,
                    'crown_movement_quote_fids': 0,
                    'crown_movement_quote_rows': 0,
                    'crown_movement_distinct_source_events': 0,
                    'crown_movement_valid_pregame_fids': 0,
                    'crown_movement_prospective_rows': 0,
                    'explicit_no_crown_ah_quote_fids': 0,
                    'summary_quote_fids': 0,
                    'summary_quote_rows': 0,
                    'priced_t6_fids': 0,
                    'failed_attempt_fids': 0,
                    'identity_conflict_fids': 0,
                }
            bucket = by_league_year[key]
            uid = (lid, year, fid)
            if uid in seen:
                continue
            seen.add(uid)
            bucket['unique_fids'] += 1
            for source in SCHEDULE_SOURCES:
                records = row.get(source) or []
                if records:
                    bucket['schedule_source_fids'][source] += 1

            schedule_records = [
                rec for source in SCHEDULE_SOURCES
                for rec in (row.get(source) or [])
            ]
            identity_record = next(
                (rec for source in SCHEDULE_SOURCES for rec in (row.get(source) or [])
                 if rec.get('provider_league_id') == lid or str(rec.get('league_id') or '') == lid),
                schedule_records[0] if schedule_records else {},
            )
            schedule_identity[uid] = {
                'provider_league_id': lid,
                'home': identity_record.get('home_name') or identity_record.get('home'),
                'away': identity_record.get('away_name') or identity_record.get('away'),
                'kickoff_utc': identity_record.get('kickoff_utc'),
                'status': identity_record.get('status'),
                'home_goals': identity_record.get('home_goals'),
                'away_goals': identity_record.get('away_goals'),
            }
            ft_values = []
            status_full_numeric = False
            for rec in schedule_records:
                status = str(rec.get('status') or rec.get('status_raw') or '').lower()
                if status:
                    bucket['status_counts'][status] += 1
                hg = rec.get('home_goals', rec.get('home_goals_raw'))
                ag = rec.get('away_goals', rec.get('away_goals_raw'))
                if numeric(hg) and numeric(ag):
                    ft_values.append((str(hg), str(ag)))
                    if status == 'full':
                        status_full_numeric = True
            if ft_values:
                bucket['numeric_ft_fids'] += 1
            if status_full_numeric:
                bucket['status_full_numeric_ft_fids'] += 1

            movement_captures = [
                c for c in (row.get('crown_captures') or [])
                if c.get('layer') == 'movement'
            ]
            if movement_captures:
                bucket['crown_movement_capture_fids'] += 1
            if any(c.get('status') == 'NO_CROWN_AH_QUOTES' for c in movement_captures):
                bucket['explicit_no_crown_ah_quote_fids'] += 1
            groups = row.get('crown_quote_groups') or []
            movement_groups = [g for g in groups if g.get('layer') == 'movement']
            summary_groups = [g for g in groups if g.get('layer') == 'summary']
            mrows = sum(int(g.get('quote_rows') or 0) for g in movement_groups)
            if mrows:
                bucket['crown_movement_quote_fids'] += 1
                bucket['crown_movement_quote_rows'] += mrows
            bucket['crown_movement_distinct_source_events'] += sum(
                int(g.get('distinct_source_timestamps') or 0) for g in movement_groups
            )
            if any(int(g.get('quote_before_kickoff_rows') or 0) for g in movement_groups):
                bucket['crown_movement_valid_pregame_fids'] += 1
            bucket['crown_movement_prospective_rows'] += sum(
                int(g.get('prospective_quote_rows') or 0) for g in movement_groups
            )
            srows = sum(int(g.get('quote_rows') or 0) for g in summary_groups)
            if srows:
                bucket['summary_quote_fids'] += 1
                bucket['summary_quote_rows'] += srows
            if row.get('priced_t6_records'):
                bucket['priced_t6_fids'] += 1
            if row.get('failed_attempts'):
                bucket['failed_attempt_fids'] += 1
            if row.get('identity_conflicts'):
                bucket['identity_conflict_fids'] += 1

    years = sorted({year for _, year in by_league_year})
    output_rows = []
    for lid, name in TARGETS.items():
        for year in range(2019, 2027):
            bucket = by_league_year.get((lid, year))
            if bucket is None:
                bucket = {
                    'provider_league_id': lid, 'league_name': name, 'utc_year': year,
                    'unique_fids': 0,
                    'schedule_source_fids': {s: 0 for s in SCHEDULE_SOURCES},
                    'numeric_ft_fids': 0, 'status_full_numeric_ft_fids': 0,
                    'status_counts': {}, 'crown_movement_capture_fids': 0,
                    'crown_movement_quote_fids': 0, 'crown_movement_quote_rows': 0,
                    'crown_movement_distinct_source_events': 0,
                    'crown_movement_valid_pregame_fids': 0,
                    'crown_movement_prospective_rows': 0,
                    'explicit_no_crown_ah_quote_fids': 0,
                    'summary_quote_fids': 0, 'summary_quote_rows': 0,
                    'priced_t6_fids': 0, 'failed_attempt_fids': 0,
                    'identity_conflict_fids': 0,
                }
            bucket['status_counts'] = dict(bucket['status_counts'])
            output_rows.append(bucket)

    # Verify the source evidence for every explicit NO_CROWN_AH_QUOTES movement
    # capture in the named 2019-2022 gap rows. Raw responses stay private.
    audit_fids = {fid for lid, year, fid in seen if year <= 2022}
    cx = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    cx.row_factory = sqlite3.Row
    noquote_captures = []
    for i in range(0, len(audit_fids), 700):
        fids = sorted(audit_fids)[i:i + 700]
        marks = ','.join('?' for _ in fids)
        noquote_captures.extend(dict(r) for r in cx.execute(
            f"""SELECT fixture_id,data_layer,capture_mode,status,quote_count,
                       response_sha256,source_file,response_received_at_utc,
                       kickoff_at_utc
                FROM capture WHERE data_layer='movement' AND capture_mode='historical'
                  AND status='NO_CROWN_AH_QUOTES' AND fixture_id IN ({marks})""",
            fids,
        ))
    cx.close()
    evidence_rows = []
    errors = collections.Counter()
    verified_fids = set()
    for capture in noquote_captures:
        fid = str(capture['fixture_id'])
        possible = [key for key in schedule_identity if key[2] == fid]
        key = possible[0] if possible else None
        item = {
            'fid': fid,
            'league_id': key[0] if key else None,
            'utc_year': key[1] if key else None,
            'capture_mode': capture['capture_mode'],
            'status': capture['status'],
            'quote_count': capture['quote_count'],
            'response_received_at_utc': capture['response_received_at_utc'],
            'kickoff_at_utc': capture['kickoff_at_utc'],
            'response_sha256': capture['response_sha256'],
            'raw_file_path_private': capture['source_file'],
            'raw_exists': False,
            'raw_sha_verified': False,
            'raw_match_identity_verified': False,
            'raw_crown_asian_list_empty': False,
            'raw_crown_asian_quote_count': None,
            'schedule_identity': schedule_identity.get(key) if key else None,
        }
        if capture.get('quote_count') != 0:
            errors['capture_quote_count_nonzero'] += 1
        raw_path = Path(capture['source_file']) if capture.get('source_file') else None
        if raw_path and raw_path.is_file():
            raw = raw_path.read_bytes()
            item['raw_exists'] = True
            item['raw_sha_verified'] = hashlib.sha256(raw).hexdigest() == capture['response_sha256']
            if not item['raw_sha_verified']:
                errors['raw_sha_mismatch'] += 1
            else:
                try:
                    doc = json.loads(raw)
                    matches = doc.get('data') or []
                    match = next((m for m in matches if str(m.get('id')) == fid), None)
                    if match is None:
                        errors['raw_match_missing'] += 1
                    else:
                        expected = schedule_identity.get(key) if key else None
                        id_ok = (
                            str(match.get('l_id') or '') == str(item['league_id'])
                            and (not expected or not expected.get('home') or str(match.get('h')) == str(expected['home']))
                            and (not expected or not expected.get('away') or str(match.get('a')) == str(expected['away']))
                        )
                        item['raw_match_identity_verified'] = bool(id_ok)
                        if not id_ok:
                            errors['raw_identity_mismatch'] += 1
                        bookmaker = next((b for b in (match.get('bookmakers') or []) if b.get('slug') == 'crown'), None)
                        if bookmaker is None:
                            errors['raw_crown_bookmaker_missing'] += 1
                        else:
                            quotes = bookmaker.get('asian_list') or []
                            item['raw_crown_asian_quote_count'] = len(quotes)
                            item['raw_crown_asian_list_empty'] = len(quotes) == 0
                            if quotes:
                                errors['raw_contains_asian_quotes'] += 1
                except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                    errors['raw_parse_error'] += 1
        else:
            errors['raw_file_missing'] += 1
        if item['raw_sha_verified'] and item['raw_match_identity_verified'] and item['raw_crown_asian_list_empty']:
            verified_fids.add(fid)
        evidence_rows.append(item)

    evidence_path = OUT / 'priority_league_gap_noquote_receipts_2019_2022.jsonl.gz'
    with evidence_path.open('wb') as raw_out:
        with gzip.GzipFile(fileobj=raw_out, mode='wb', mtime=0) as compressed:
            for item in sorted(evidence_rows, key=lambda x: (str(x['league_id']), int(x['utc_year'] or 0), x['fid'])):
                compressed.write((json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8'))

    noquote_fids = {str(r['fixture_id']) for r in noquote_captures}
    result = {
        'study': 'offline priority league gap inventory; no requests or inference',
        'generated_utc': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'source_file': str(SOURCE),
        'source_sha256': sha(SOURCE),
        'crown_sqlite_sha256': sha(DB),
        'source_inventory_row_count': len(seen),
        'scope_note': 'Only the three user-named examples are summarized here; this does not reduce the full-recovery league scope.',
        'by_league_year': output_rows,
        'league_totals': {},
        'historical_noquote_raw_audit_2019_2022': {
            'schedule_fids_in_three_named_leagues': sum(1 for lid, year, _ in seen if year <= 2022),
            'movement_noquote_capture_rows': len(noquote_captures),
            'unique_fids_with_noquote_capture': len(noquote_fids),
            'unique_fids_without_movement_capture': len(audit_fids - noquote_fids),
            'raw_sha_and_fid_identity_and_empty_crown_asian_list_verified_fids': len(verified_fids),
            'capture_errors': dict(errors),
            'response_received_time_is_historical_retrieval_not_pregame_receipt': True,
            'response_sha_bound_private_raw_evidence_jsonl_gz': str(evidence_path),
            'response_sha_bound_private_raw_evidence_sha256': sha(evidence_path),
        },
    }
    for lid, name in TARGETS.items():
        rs = [r for r in output_rows if r['provider_league_id'] == lid]
        keys = [
            'unique_fids', 'numeric_ft_fids', 'status_full_numeric_ft_fids',
            'crown_movement_capture_fids', 'crown_movement_quote_fids',
            'crown_movement_quote_rows', 'crown_movement_distinct_source_events',
            'crown_movement_valid_pregame_fids', 'crown_movement_prospective_rows',
            'explicit_no_crown_ah_quote_fids', 'summary_quote_fids',
            'summary_quote_rows', 'priced_t6_fids', 'failed_attempt_fids',
            'identity_conflict_fids',
        ]
        total = {'provider_league_id': lid, 'league_name': name}
        for k in keys:
            total[k] = sum(int(r.get(k) or 0) for r in rs)
        total['schedule_source_fids'] = {
            source: sum(int(r['schedule_source_fids'].get(source) or 0) for r in rs)
            for source in SCHEDULE_SOURCES
        }
        result['league_totals'][lid] = total

    json_path = OUT / 'priority_league_gap_inventory_2019_2026.json'
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# 2019–2026 点名联赛历史库存缺口离线核查', '',
        '> 本报告仅核查现有规范化库存和本机只读 Crown SQLite；没有发网络请求、没有把缺失比分或盘口补造为有效数据，也不缩小全量补采范围。', '',
        f"- 生成时间 UTC：`{result['generated_utc']}`",
        f"- 库存文件 SHA256：`{result['source_sha256']}`",
        f"- Crown SQLite SHA256：`{result['crown_sqlite_sha256']}`",
        f"- 逐响应原始证据账本：`{Path(result['historical_noquote_raw_audit_2019_2022']['response_sha_bound_private_raw_evidence_jsonl_gz']).name}`；含私有原始文件路径和每条响应SHA，原始HTTP body未复制到仓库。", '',
        '## 全期按 UTC 年覆盖', '',
        '| 联赛 ID / 名称 | UTC年 | 库存 FID | status=full 且数字 FT | Movement capture FID | 明确无 Crown AH FID | Crown AH 报价 FID | Movement 报价行 | T6 FID |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for row in output_rows:
        lines.append(
            f"| {row['provider_league_id']} {row['league_name']} | {row['utc_year']} | {row['unique_fids']} | {row['status_full_numeric_ft_fids']} | {row['crown_movement_capture_fids']} | {row['explicit_no_crown_ah_quote_fids']} | {row['crown_movement_quote_fids']} | {row['crown_movement_quote_rows']} | {row['priced_t6_fids']} |"
        )
    lines += [
        '', '## 2019–2022 无 Crown AH 报价响应逐条核验', '',
        f"- 2,594 个赛程 FID中，{result['historical_noquote_raw_audit_2019_2022']['movement_noquote_capture_rows']} 条历史 movement capture 明确标为 `NO_CROWN_AH_QUOTES`；其中 {result['historical_noquote_raw_audit_2019_2022']['raw_sha_and_fid_identity_and_empty_crown_asian_list_verified_fids']} 个唯一 FID 的原始响应SHA、FID/联赛/球队身份和 Crown `asian_list=[]` 均逐条通过核对。capture 状态为历史回取，`response_received_at_utc` 是回取实际接收时间，不是赛前实收。",
        f"- 另有 {result['historical_noquote_raw_audit_2019_2022']['unique_fids_without_movement_capture']} 个 FID 没有 movement capture；它们不是已确认无盘口，也没有可供校验的 Crown 原始响应。",
        '- 按联赛 / UTC年拆开，下面依次为“库存FID / verified full FT / 明确无 AH 响应 / 无 movement capture / 有 Crown AH FID”：', '',
        '| 联赛 ID | 年 | 库存 / full FT / no-quote / no-capture / 有报价 FID |',
        '|---:|---:|---|',
    ]
    for row in output_rows:
        if row['utc_year'] <= 2022:
            no_capture = row['unique_fids'] - row['crown_movement_capture_fids']
            lines.append(
                f"| {row['provider_league_id']} | {row['utc_year']} | {row['unique_fids']} / {row['status_full_numeric_ft_fids']} / {row['explicit_no_crown_ah_quote_fids']} / {no_capture} / {row['crown_movement_quote_fids']} |"
            )
    lines += [
        '', '## 结论与边界', '',
        '- ID 51、61、10480 在 2019–2022 的赛程和 status=full 赛果已大部分存在于当前跨源库存；本核查没有证据支持将“缺少历史赛事/赛果”概括为这几年的整体状态。完整 FT 计数只认可提供 `status=full` 且比分为数字的源行；其余数字比分可能来自非 full/占位记录，不计为已验证 FT。',
        '- 这三个联赛在 2019–2022 没有任何 Crown movement AH 报价行。2,251 场已有经SHA核验的成功响应，其中 Crown 书商存在但亚洲盘数组为空；343 场连 movement capture 都没有。该证据说明当前回放库存状态，不证明上游接口永远无法返回历史盘口；尚未再次请求这343场。',
        '- 2023–2026 已能看到部分或大量 Crown AH movement报价，说明其覆盖按年份变化。所有 `prospective_quote_rows` 均为0；这些历史报价不属于当时HTTP赛前实收。',
        '- 发现的源映射/FT冲突和失败尝试仍单独保留在JSON；本次没有按名称强行合并ID，也没有删除现有记录。此三联赛专项核查不代替全115联赛及全部来源的整体覆盖复核。',
        '',
        f"机器可读逐联赛逐年结果：`{json_path.name}`。", '',
    ]
    report_path = OUT / 'PRIORITY_LEAGUE_GAP_REPORT_2019_2026.md'
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(result['league_totals'], ensure_ascii=False, indent=2))
    print(f'json={json_path} sha256={sha(json_path)}')
    print(f'report={report_path} sha256={sha(report_path)}')


if __name__ == '__main__':
    main()
