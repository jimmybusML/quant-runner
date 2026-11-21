#!/usr/bin/env python3
"""Build auditable period tables, report, execution record and SHA manifest."""
import collections
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LEDGER = HERE / 'red_card_adjusted_form_per_fixture.jsonl.gz'
SUMMARY = HERE / 'red_card_adjusted_form_summary.json'
RECEIPT_SUMMARY = HERE / 'actual_receipt_reprice_summary.json'
RECEIPT_VERIFY = HERE / 'actual_receipt_independent_verification.json'
MAIN_VERIFY = HERE / 'independent_verification.json'
METHODS = ('market', 'market_plus_raw_form', 'market_plus_red_adjusted_form',
           'market_plus_raw_and_red_context', 'low_price')
METHOD_LABELS = {
    'market': 'Crown + 市场结构基准',
    'market_plus_raw_form': 'Crown + 未调整历史状态',
    'market_plus_red_adjusted_form': 'Crown + 红牌调整状态',
    'market_plus_raw_and_red_context': 'Crown + 原状态 + 红牌调整及红牌上下文',
    'low_price': '低十进制赔率边基准',
}


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl_gz(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def metrics(rows, value_fn):
    if not rows:
        return {'orders': 0, 'net_u': 0.0, 'roi_pct': None, 'mdd_u': 0.0,
                'average_decimal_odds': None, 'settlements': {}}
    net = sum(value_fn(r) for r in rows)
    daily = collections.defaultdict(float)
    states = collections.Counter()
    odds = []
    for row in rows:
        daily[row['date']] += value_fn(row)
        states[row['settlement']] += 1
        odds.append(float(row['odds']))
    cum = peak = mdd = 0.0
    for day in sorted(daily):
        cum += daily[day]
        peak = max(peak, cum)
        mdd = max(mdd, peak-cum)
    return {'orders': len(rows), 'net_u': round(net, 6),
            'roi_pct': round(100*net/len(rows), 6), 'mdd_u': round(mdd, 6),
            'average_decimal_odds': round(sum(odds)/len(odds), 6),
            'settlements': dict(states)}


def render_markdown(summary, periodic, receipt):
    cov = summary['coverage']
    baseline = summary['same_period_frozen_eight']
    lines = [
        '# M8 红牌调整历史状态与 Crown AH 定价研究', '',
        '日期：2026-11-20（北京时间）', '',
        '## 结论', '',
        '没有发现可以作为原八组之外独立盈利来源的红牌调整 AH 机制。'
        '在相同的 24,173 个八组外 FID 上，红牌调整和联合版本均未实现正净U，'
        '且2024、2025、2026三个前推测试年度均为负。模型改善了部分亏损基线，'
        '但没有消除 Crown 实际价格下的负收益。', '',
        '| 方案 | 八组外订单 | 净U | ROI | MDD | 2024净U | 2025净U | 2026净U | 周均单量 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for method in METHODS:
        s = summary['outside_frozen_eight'][method]
        yr = periodic['by_method'][method]['year']
        lines.append(f"| {METHOD_LABELS[method]} | {s['orders']:,} | {s['net_u']:+.3f} | {s['roi_pct']:+.3f}% | {s['mdd_u']:.3f} | {yr['2024']['net_u']:+.3f} | {yr['2025']['net_u']:+.3f} | {yr['2026']['net_u']:+.3f} | {s['active_week_avg']:.3f} |")
    lines += ['',
        f"冻结八组同期基准：{baseline['orders']:,} FID、{baseline['net_u']:+.3f}U。"
        '候选与冻结八组交集为0；每种方案各自按唯一FID合并。即使采用最少亏损的联合红牌上下文方案，'
        f"合并后仍为 {summary['merged_with_frozen_eight']['market_plus_raw_and_red_context']['orders']:,} 场、"
        f"{summary['merged_with_frozen_eight']['market_plus_raw_and_red_context']['net_u']:+.3f}U，"
        f"候选使冻结八组净利减少 {abs(summary['merged_with_frozen_eight']['market_plus_raw_and_red_context']['incremental_net_u']):.3f}U。", '',
        '## 假说及方法', '',
        '假说是历史实际净胜球受到红牌数量优势影响；如果不调整红牌导致的历史表现噪声，'
        '滚动球队状态可能偏离实力，Crown AH 也可能没有充分吸收这一信息。这里估计的是历史相关性，'
        '不作红牌的因果效应解释。该机制不同于单独预测球队/裁判的牌数：本研究使用球队过去比赛的红牌净优势，'
        '修正其近365日净胜球状态，再比较 Crown 实际 AH 结算。', '',
        '- 历史状态使用目标北京时间日期前至少3日完成的比赛，按联赛/球队ID计算过去365日净胜球均值、最近一次净胜球和样本数。',
        '- 红牌净优势缺失保持缺失并附带缺失指示，不把缺记录填成0。调整系数仅用前一年度及更早的 card-complete 历史估计。',
        '- 2024/2025/2026分别以该目标年之前的数据训练；Ridge alpha=100，fold内标准化；标签是实际 Crown 盘口价格下主队与客队净U之差，每场选模型预测收益较大的一边，不加EV门槛。',
        '- quarter-line拆为两条等额腿；赛事使用Crown AH线、双边十进制赔率与可信FT。所有报价均为历史事件回放。',
        '- 五种方案在同一批八组外唯一FID上比较，避免用覆盖差异制造改善。', '',
        '## 数据覆盖与时间边界', '',
        f"目标库存 {cov['combined_unique_target_fids']:,} FID：原49联赛完整路径 {cov['original49_path_fids']:,}，新增15联赛完整T6/T3/T1路径 {cov['expanded15_complete_T6_T3_T1_fids']:,}。"
        f"5,180份已缓存赛程页提供 {cov['target_complete_identity_fids']:,} 个无冲突的完整身份，"
        f"另有 {cov['no_cached_target_identity']:,} 场无可用目标身份。历史比分库有 {cov['full_FT_history_fids']:,} 个FID；"
        f"红牌原始响应扫描91,816份，得到 {cov['raw_history_unique_card_fids']:,} 个无冲突的可核验赛事记录。", '',
        f"实际可评估候选北京时间范围为 {periodic['date_range_beijing'][0][:10]} 至 {periodic['date_range_beijing'][1][:10]}。"
        f"特征行 {cov['feature_rows']:,}；其中 {cov['feature_missing']['no_prior_full_score_history_for_a_side']:,} 场因至少一队缺少此前完整比分历史而未建特征。"
        f"前推预测共 {cov['scored_2024_2026_rows']:,} 场，其中八组外候选 {cov['outside_frozen_unique_candidate_fids']:,} 场；"
        f"候选按来源分组及逐年覆盖见 `red_card_adjusted_form_periodic_results.json`。", '',
        '**关键时间限制：**红牌历史来自赛后保存的比赛数据，没有可靠的首次发布时间或真实接收时间；'
        '本研究不能证明红牌信息当时已可用于下注。2024–2026的FT也已被用于研究设计和本次检验，'
        '故属于历史前推事件回放，不是未见赛果的盲测。真实HTTP Crown收据价格只能审计价格和时间，不能补足红牌特征快照时间。', '',
        '## 年度、周度与联赛结果', '',
        '完整逐年（含每年订单、净U、ROI、MDD和五态结算）、149个ISO活跃周、所有联赛以及来源拆分保存在 '
        '`red_card_adjusted_form_periodic_results.json`。所有候选行、下注方向、Crown盘口/双方赔率、FT及五态结算保存在 '
        '`red_card_adjusted_form_per_fixture.jsonl.gz`。没有按联赛或月份筛除亏损样本。', '',
        '## 实际赛前 Crown HTTP 收据复核', '',
        f"MR1归档包含12,550条收据记录；与八组外测试FID交集为{receipt['candidate_fids_with_any_actual_pregame_Crown_receipt']}场，"
        f"其中T1真实Crown HTTP收据{receipt['candidate_T1_receipt_fids']}场。独立从原始响应复核SHA、FID/联赛/球队、报价内容、报价源事件时间及收件早于目标开球，"
        f"均无不匹配；与事件回放路径同线同水{receipt['candidate_T1_receipt_exact_match_to_event_path_price_fids']}场，另{receipt['candidate_T1_receipt_price_mismatch_fids']}场必须按实收报价重算。"
        f"收据记录的开球元数据有{receipt['receipt_vs_current_schedule_kickoff_metadata_differences']}场与当前赛事表不同，但实际收件仍早于当前比赛开球。", '',
        '| 真实T1报价重算（832场） | 净U | ROI | MDD |',
        '|---|---:|---:|---:|'
    ]
    for method in METHODS:
        s = receipt['metrics_by_method'][method]
        lines.append(f"| {METHOD_LABELS[method]} | {s['net_u']:+.3f} | {s['roi_pct']:+.3f}% | {s['mdd_u']:.3f} |")
    lines += ['',
        '此832场赛果已存在于历史研究库存，且红牌状态输入没有当时快照证据；因此本表是按真实早收Crown价格重放的回顾核算，'
        '不是新样本、不是前瞻验证，也不是正式Telegram订单或实际成交。低赔率边基准的+4.535U只有5个ISO周，不能代表新盈利机制。', '',
        '## 结论与后续信息缺口', '',
        '红牌调整状态较普通状态模型少亏39.175U；红牌及上下文联合版较普通状态模型少亏117.980U。'
        '但每个完整年度仍亏损，全部新增预测仍负ROI，真实T1收据中的两个含红牌模型也亏损。'
        '现有证据最多支持“红牌历史可能改善某些赛季的状态估计”，不支持独立盈利或扩单。', '',
        '要继续验证盈利机制，真正缺少的是带时间戳的赛前纪律事件/处罚信息快照，并在后续未见赛果上前瞻冻结特征和模型。'
        '在此之前，不重复调节红牌系数或测试年分段。', '',
        '## 可复核文件', '',
        '- 主运行脚本：`run_red_card_adjusted_form.py`',
        '- 主历史回放逐场账：`red_card_adjusted_form_per_fixture.jsonl.gz`',
        '- 红牌/赛果原始来源索引：`red_card_history_source_index.jsonl.gz`',
        '- 原始历史数据和 AH 重算独立校验：`verify_red_card_adjusted_form.py`',
        '- 真实T1收据按实收盘口重算：`replay_actual_receipts.py`',
        '- 实收原文、预测和五态独立校验：`verify_actual_receipt_replay.py`',
        '- 年度、ISO周、联赛及赛事来源拆分：`red_card_adjusted_form_periodic_results.json`',
        '- 输入/输出SHA：`SHA256SUMS.txt`', '',
        '本研究仅新增研究文件与交接记录；没有修改冻结原八组、M1/MR1/M9、生产调度、Crown采集链、Telegram或正式账本。'
    ]
    return '\n'.join(lines) + '\n'


def main():
    summary = json.loads(SUMMARY.read_text())
    receipt = json.loads(RECEIPT_SUMMARY.read_text())
    main_verify = json.loads(MAIN_VERIFY.read_text())
    receipt_verify = json.loads(RECEIPT_VERIFY.read_text())
    if not main_verify.get('pass') or not receipt_verify.get('pass'):
        raise SystemExit('independent verification did not pass')
    ledger = [r for r in load_jsonl_gz(LEDGER) if not r['frozen_eight_overlap']]
    if len({r['fid'] for r in ledger}) != len(ledger):
        raise SystemExit('duplicate outside-frozen FID')
    period = {'study': 'M8_RED_CARD_ADJUSTED_FORM', 'outside_frozen_unique_fids': len(ledger),
              'date_range_beijing': [min(x['kickoff_beijing'] for x in ledger), max(x['kickoff_beijing'] for x in ledger)],
              'by_method': {}, 'cross_method_fid_overlap': {a: {b: len({x['fid'] for x in ledger} & {x['fid'] for x in ledger}) for b in METHODS} for a in METHODS},
              'receipt_replay': receipt, 'independent_verification': main_verify,
              'actual_receipt_independent_verification': receipt_verify,
              'frozen_eight_same_period': summary['same_period_frozen_eight'],
              'merged_with_frozen_eight': summary['merged_with_frozen_eight']}
    for method in METHODS:
        groups = {'all': ledger}
        for r in ledger:
            groups.setdefault(str(r['year']), []).append(r)
            groups.setdefault(r['iso_week'], []).append(r)
            groups.setdefault(f"league:{r['league_name']}|{r['league']}", []).append(r)
            groups.setdefault(f"source:{r['source_group']}", []).append(r)
        by_year = {}; by_week = {}; by_league = {}; by_source = {}
        for key, rows in groups.items():
            values = [{'date': r['kickoff_beijing'][:10], 'settlement': r['methods'][method]['settlement'],
                       'odds': r['methods'][method]['odds'], 'net_u': r['methods'][method]['net_u']} for r in rows]
            result = metrics(values, lambda x: float(x['net_u']))
            if key == 'all': all_stats = result
            elif key.isdigit(): by_year[key] = result
            elif key.startswith('league:'): by_league[key[7:]] = result
            elif key.startswith('source:'): by_source[key[7:]] = result
            elif '-W' in key: by_week[key] = {'orders': result['orders'], 'net_u': result['net_u'], 'roi_pct': result['roi_pct']}
        period['by_method'][method] = {'full_period': all_stats, 'year': by_year,
                                      'iso_week': by_week, 'league': by_league,
                                      'source_group': by_source}
    # Cross-method overlap is intentionally based on unique candidate FIDs and is 100%.
    period['cross_method_fid_overlap'] = {a: {b: len(ledger) for b in METHODS} for a in METHODS}
    results_path = HERE / 'red_card_adjusted_form_periodic_results.json'
    results_path.write_text(json.dumps(period, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    report_path = HERE / 'M8_RED_CARD_ADJUSTED_FORM_RESEARCH_20261120.md'
    report_path.write_text(render_markdown(summary, period, receipt))
    files = [
        'M8_RED_CARD_ADJUSTED_FORM_RESEARCH_20261120.md',
        'build_deliverables.py', 'expanded15_t1_path_input.jsonl.gz',
        'red_card_adjusted_form_per_fixture.jsonl.gz', 'red_card_adjusted_form_summary.json',
        'red_card_history_source_index.jsonl.gz', 'run_red_card_adjusted_form.py',
        'schedule_page_sha256_manifest.json', 'verify_red_card_adjusted_form.py',
        'independent_verification.json', 'replay_actual_receipts.py',
        'actual_receipt_reprice_orders.jsonl.gz', 'actual_receipt_reprice_summary.json',
        'verify_actual_receipt_replay.py', 'actual_receipt_independent_verification.json',
        'red_card_adjusted_form_periodic_results.json'
    ]
    inputs = summary['inputs']
    sqlite_db = pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
    cached_page_index = HERE / 'schedule_page_sha256_manifest.json'
    extra_inputs = {str(sqlite_db): sha(sqlite_db), str(cached_page_index): sha(cached_page_index)}
    # Reuse the SHA index over all cached schedule pages rather than recopying private raw pages.
    all_inputs = {**inputs, **extra_inputs}
    input_lines = [f"{digest}  INPUT::{path}" for path, digest in sorted(all_inputs.items())]
    lines = input_lines + [f"{sha(HERE / name)}  OUTPUT::{name}" for name in files]
    (HERE / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n')
    execution = f'''# 执行记录

- 主时间前推研究：`python3 research/m8/red_card_adjusted_form_20261120/run_red_card_adjusted_form.py`，完成。覆盖46,068目标路径，预测30,268场，八组外唯一候选24,173场。
- 实际T1 Crown收据重算：`python3 research/m8/red_card_adjusted_form_20261120/replay_actual_receipts.py`，完成832个候选FID；原始HTTP响应SHA/身份/赛前时序/Crown市场错误均为0，事件回放价格精确匹配449场，383场按实收价格重新结算，当前赛程开球元数据差异6场。
- 独立历史数据/原始Crown/FT/模型前推验证：`python3 research/m8/red_card_adjusted_form_20261120/verify_red_card_adjusted_form.py`，PASS。原始历史card+FT覆盖88,053场；2024/2025/2026前推测试数10,420/11,323/8,525。
- 独立HTTP收据、实收盘口重定价及AH五态结算验证：`python3 research/m8/red_card_adjusted_form_20261120/verify_actual_receipt_replay.py`，PASS。4160条FID×方法记录全部核对通过。
- 统计、报告、执行清单及SHA文件：`python3 research/m8/red_card_adjusted_form_20261120/build_deliverables.py`，完成。
- 历史候选五种方案均负净U；2024–2026各年均负。收据价格中低赔率边基准+4.535U，但仅832场/5个活跃ISO周且结果已知，不是新机制证据；其余四种含Crown模型方案亏损。
- Crown AH报价是历史事件回放或真实归档HTTP报价；红牌/历史特征没有被证明在当时已收到。不是未见赛果的前瞻盲测，也不是正式Telegram订单、真实成交或账本结果。
- 正式Telegram派单0；账本写入0；生产工作流/采集链/调度改动0；冻结原八组改动0。

输入及输出SHA详见`SHA256SUMS.txt`。逐场数据及原始响应不含私密响应body；真实收据独立校验仅在本机已授权归档上执行。
'''
    (HERE / 'EXECUTION_RECORD.md').write_text(execution)
    # Refresh output checksums after the execution record has been created.
    lines = input_lines + [f"{sha(HERE / name)}  OUTPUT::{name}" for name in files + ['EXECUTION_RECORD.md']]
    (HERE / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'report': str(report_path), 'periodic_results': str(results_path),
                      'unique_candidates': len(ledger), 'methods': {m: summary['outside_frozen_eight'][m]['net_u'] for m in METHODS},
                      'receipt_replay': {m: receipt['metrics_by_method'][m]['net_u'] for m in METHODS},
                      'sha_entries': len(lines)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
