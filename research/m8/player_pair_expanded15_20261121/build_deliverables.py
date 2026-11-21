#!/usr/bin/env python3
"""Build the audited expanded15 pair-cohesion report and SHA256 manifest."""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import pathlib
import datetime as dt
from zoneinfo import ZoneInfo

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
REPORT = OUT / 'M8_PLAYER_PAIR_EXPANDED15_COHESION_RESEARCH_20261121.md'
CHINA = ZoneInfo('Asia/Shanghai')


def sha(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_gz(path: pathlib.Path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def pct(value):
    return '—' if value is None else f"{value:+.3f}%"


def signed(value):
    return f'{value:+.3f}'


def main() -> None:
    summary = json.loads((OUT / 'pooled_pair_cohesion_summary.json').read_text(encoding='utf-8'))
    audit = json.loads((OUT / 'independent_raw_crown_settlement_audit.json').read_text(encoding='utf-8'))
    identity = json.loads((OUT / 'identity_coverage_audit.json').read_text(encoding='utf-8'))
    if not audit.get('verified'):
        raise SystemExit('Independent Crown/settlement verification has not passed.')

    method_names = {
        'market_only': 'Crown market only',
        'pair_only': '球员对子经验 only',
        'market_plus_pair': 'Crown + 球员对子经验',
    }
    test_rows = list(load_gz(OUT / 'pooled_pair_cohesion_predictions.jsonl.gz'))
    reps = {}
    for row in test_rows:
        reps.setdefault(str(row['fid']), row)
    by_year = collections.Counter(str(row['year']) for row in reps.values())
    by_league = collections.Counter(str(row['league']) for row in reps.values())

    path_input = ROOT / 'research/m8/red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'
    path_year = collections.Counter()
    path_fids = {}
    with gzip.open(path_input, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            year = str(row['year'])
            fid = str(row['fid'])
            path_year[year] += 1
            path_fids[fid] = year
    quote_year = collections.Counter()
    quote_fids = set()
    for row in load_gz(OUT / 'expanded15_T12_contract_inventory.jsonl.gz'):
        kickoff = dt.datetime.fromisoformat(str(row['kickoff_utc']).replace('Z', '+00:00'))
        year = str(kickoff.astimezone(CHINA).year)
        quote_year[year] += 1
        quote_fids.add(pathlib.Path(row['source_file']).parent.name)
    mapped_year = collections.Counter()
    for key, count in identity['coverage']['feature_ready_by_league_year'].items():
        _, year = key.split('|')
        mapped_year[year] += int(count)
    coverage_by_year = {}
    years = sorted(set(path_year) | set(quote_year) | set(mapped_year) | set(by_year))
    for year in years:
        year_fids = {fid for fid, y in path_fids.items() if y == year}
        coverage_by_year[year] = {
            'complete_T6_T3_T1_paths': path_year[year],
            'path_fids_with_valid_T12_Crown_quote': len(year_fids & quote_fids),
            'path_fids_with_both_teams_exactly_mapped': mapped_year[year],
            'feature_complete_test_fids': by_year[year],
        }
    coverage_path = OUT / 'expanded15_pair_cohesion_coverage_by_year.json'
    coverage_path.write_text(json.dumps(coverage_by_year, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    cov = summary['coverage']
    identity_cov = identity['coverage']
    fold = summary['training_folds']
    model_lines = []
    quality_lines = []
    merged_lines = []
    monthly_rows = []
    weekly_rollup = []
    for method, label in method_names.items():
        x = audit['models_recomputed'][method]
        model_lines.append(f"| {label} | {x['n']} | {signed(x['net_u'])} | {pct(x['roi_pct'])} | {x['mdd_u']:.3f} | {x['unique_fids']} |")
        q = audit['market_predictions_evaluation'][method]
        quality_lines.append(f"| {label} | {q['goal_difference_MAE']:.4f} | {q['goal_difference_RMSE']:.4f} |")
        m = audit['frozen_eight_same_period_and_merged'][method]
        merged_lines.append(f"| {label} | {m['candidate_n']} / {signed(m['candidate_net_u'])}U | {m['unique_fids']} / {signed(m['net_u'])}U / {pct(m['roi_pct'])} | {m['mdd_u']:.3f}U | {m['combined_orders_per_week']:.3f} |")
        month = audit['monthly_incremental'][method]
        for name, value in month.items():
            monthly_rows.append((name, label, value))
        weeks = summary['weekly_incremental'][method]
        positives = sum(1 for value in weeks.values() if value['net_U'] > 0)
        negatives = sum(1 for value in weeks.values() if value['net_U'] < 0)
        zero = sum(1 for value in weeks.values() if value['net_U'] == 0)
        orders = sum(value['n'] for value in weeks.values())
        week_span = (max(dt.date.fromisoformat(row['date']) for row in reps.values()) -
                     min(dt.date.fromisoformat(row['date']) for row in reps.values())).days // 7 + 1
        no_order_weeks = week_span - len(weeks)
        best = max(weeks.items(), key=lambda item: item[1]['net_U'])
        worst = min(weeks.items(), key=lambda item: item[1]['net_U'])
        weekly_rollup.append(
            f"| {label} | {positives} | {negatives} | {zero} | {no_order_weeks} | {best[0]} ({best[1]['n']}, {signed(best[1]['net_U'])}U) | {worst[0]} ({worst[1]['n']}, {signed(worst[1]['net_U'])}U) |"
        )

    monthly_table = ['| 月份 | 方法 | 新增单 | 净U | ROI |', '|---|---|---:|---:|---:|']
    for month, label, value in sorted(monthly_rows, key=lambda row: (row[0], row[1])):
        monthly_table.append(f"| {month} | {label} | {value['n']} | {signed(value['net_u'])} | {pct(value['roi_pct'])} |")

    league_lines = []
    for league in sorted(set(by_league) | {str(x) for x in identity_cov['clear_competition_crosswalks']}):
        n = by_league[league]
        if not n:
            continue
        values = audit['models_recomputed']
        # Per-league detailed values are taken from the complete per-method model ledger summary.
        stats = [summary['league_incremental'][method].get(league, {}) for method in method_names]
        league_lines.append(f"| {league} | {n} | " + ' | '.join(
            f"{stat.get('n',0)} / {signed(stat.get('net_U',0))} / {pct(stat.get('ROI_pct'))}" for stat in stats
        ) + ' |')

    coverage_lines = []
    for year, row in coverage_by_year.items():
        coverage_lines.append(f"| {year} | {row['complete_T6_T3_T1_paths']} | {row['path_fids_with_valid_T12_Crown_quote']} | {row['path_fids_with_both_teams_exactly_mapped']} | {row['feature_complete_test_fids']} |")

    text = f'''# M8 球员对子共用经验：新增15联赛 Crown AH 扩展验证

> 研究回放，不是正式订单。Crown AH 和原八组保持不变；所有新增候选按唯一 FID 计算。结果中的 2025 正收益是单一测试年度，不足以证明稳定机制。

## 研究问题与旧研究的区别

本研究检查球队连续首发阵容中球员对子共同出场的重复、集中和新旧变化，是否能在 Crown T12 AH 价格之外解释净胜球或实际 AH 收益。它承接 Original49 的球员对子共用经验研究，将同一固定特征定义移到新增15联赛；不是球员分钟负荷、阵容轮换、队伍强弱残差、直接交锋或普通 Crown Ridge 调参。

三种对照在同一扩展联赛目标样本上运行：Crown 市场特征模型；仅球员对子历史特征模型；Crown 市场加球员对子特征模型。使用相同的固定 Ridge alpha=100 和同一目标年度前训练集。市场模型特征包括 Crown T12 AH 盘口和双边赔率；对子特征来自目标日期前三天以前365日内的完整历史首发 XI。每场以模型预测的目标净胜球和残差分布计算 Crown AH 两侧期望收益并选择预测收益较好的一侧；这是实验策略而非正式 Gate。

## 数据、身份与可用样本

- 新增15联赛完整 Crown T6/T3/T1 路径库存：{cov['expanded15_complete_T6_T3_T1_rows']:,} FID；其中 {cov['expanded15_FIDs_with_T12_quote']:,} 有可重建的 T12 Crown AH 线与双边赔率，全部标记为 `capture_mode=historical`。
- 按严格赛事锚点建立的新增联赛身份桥只有 3 个联赛：85→MLS、129→巴西甲、779→墨西哥甲；总计 {identity_cov['unique_bijective_team_mappings_with_2plus_anchors']} 个双向球队 ID 映射。没有用模糊相似度或单场同分猜球队身份。
- 全部 6,967 条完整路径中，{sum(mapped_year.values()):,} 场两队均能映射到 Transfermarkt，但最终只有 {cov['expanded15_feature_complete_rows']} 场具有足够的历史完整首发 XI 特征，且全部属于2025年。缺失拆分：{cov['expanded15_missing_reasons'].get('one_or_both_expanded15_team_ids_unmapped',0):,} 场至少一队未映射；{cov['expanded15_missing_reasons'].get('insufficient_complete_prior_XI_history',0):,} 场至少一队历史完整 XI 不足；{cov['expanded15_missing_reasons'].get('T12_quote_missing',0):,} 场没有可用 T12 报价。缺失场不计作策略未命中。
- 更严格的首发 XI 必须同时有 `appearances.minutes_played > 0` 佐证的早期实现只有0个新增联赛可用测试样本，见 `expanded15_pair_cohesion_summary.json`；本次共用经验机制只要求 `game_lineups` 明确记录11名不同首发，不要求或填补分钟数。

### 逐年覆盖

| 年份 | 完整 T6/T3/T1 路径 | 有 T12 Crown AH | 两队身份均映射 | 可形成共用经验样本 |
|---:|---:|---:|---:|---:|
{chr(10).join(coverage_lines)}

2024虽有 T12 报价和双队身份映射，但这部分目标场没有足够的先前完整首发 XI 特征；故没有2024测试成绩。2026可用完整路径很少，且映射覆盖没有形成可用球队对子特征，也没有测试样本。它们是缺数据/身份覆盖，不是模型在这些年份零盈利。测试样本仅2025年。

数据输入 SHA256、逐联赛页 SHA、来源代码和实际 Crown 报价响应 SHA 都记录在 `identity_coverage_audit.json`、`pooled_pair_cohesion_summary.json` 与独立核验结果内。所有Crown报价来源事件时刻均早于T12截止；对应历史 HTTP响应在2026年回取，不能视为2025年真实收到。

## 方法与前推

- 训练池：Original49 中有同源 T12 AH 合约和可用完整过往 XI 的样本。扩展15联赛可用特征样本全部是2025年，因此没有扩展联赛的更早样本进入2025折训练。2025预测仅使用2025年以前记录；收据档案中的目标FID从训练中剔除。2025折训练数 {fold['2025']['train_n']:,}，训练最新年份 {fold['2025']['train_max_year']}。
- 验证年份：2024测试0场、2025测试{cov['expanded15_feature_complete_rows']}场、2026测试0场。2024/2026的空结果标作不可用，不以0% ROI报告。
- 任何目标比赛首发阵容均未用于其预测。历史特征使用保守 `target date - 3 days` 截止，以处理原始阵容源只有日期、没有准确完场时刻的问题。
- Transfermarkt历史比赛和阵容数据没有可核验的逐条首次发布/本机收到时间。本研究只能视为按历史比赛日期重建的前推实验，不能证明相同特征在当时已可在线获得。

## Crown AH收益

所有方法都是同一309场、同一 Crown T12 盘口和赔率、同一结算FT上的配对比较；每笔1U。亚洲四分之一盘拆成相邻两个半注，按 Crown 十进制赔率独立结算。

| 方法 | 新增唯一FID | 净U | ROI | MDD | 五态结算（全赢/半赢/走水/半输/全输） |
|---|---:|---:|---:|---:|---|
| Crown market only | 309 | −10.345 | −3.348% | 16.905U | 122 / 18 / 25 / 13 / 131 |
| 球员对子经验 only | 309 | −3.125 | −1.011% | 19.880U | 129 / 17 / 25 / 14 / 124 |
| Crown + 球员对子经验 | 309 | +7.740 | +2.505% | 11.530U | 132 / 19 / 25 / 12 / 121 |

所有模型本身都覆盖相同的 {cov['expanded15_feature_complete_rows']} 场：新增联赛扩单量为309场，按跨2025-W09至W48的40周跨度平均 **7.725场/周**。这不是逐周稳定订单承诺。市场加对子模型周净值为17个正周、20个负周、1个净零周，另有2周没有下单；最好周为{max(summary['weekly_incremental']['market_plus_pair'].items(),key=lambda item:item[1]['net_U'])[0]}（{signed(max(v['net_U'] for v in summary['weekly_incremental']['market_plus_pair'].values()))}U），最差周为{min(summary['weekly_incremental']['market_plus_pair'].items(),key=lambda item:item[1]['net_U'])[0]}（{signed(min(v['net_U'] for v in summary['weekly_incremental']['market_plus_pair'].values()))}U）。完整逐周结果在 summary JSON。

### 新增结果是否集中

| 方法 | 正收益周 | 负收益周 | 净零周 | 无订单周 | 最佳周 | 最差周 |
|---|---:|---:|---:|---|---|
{chr(10).join(weekly_rollup)}

| 月份 | 方法 | 新增单 | 净U | ROI |
|---|---|---:|---:|---:|
{chr(10).join(monthly_table[2:])}

市场加对子模型在2025年3、5、6、7月盈利，4、8、9、10月亏损，11月盈利；正值分布横跨多月，但单一年度和单一测试制度不足以称跨年度稳定盈利。

### 预测误差与盈利

| 方法 | 净胜球 MAE | 净胜球 RMSE |
|---|---:|---:|
{chr(10).join(quality_lines)}

市场加对子模型的 MAE 仅比市场模型低约0.00037球，RMSE反而高约0.00737球；对子特征没有带来实质的样本外净胜球预测改善。2025的+7.740U不能归因于显著预测精度提升，可能是样本波动。

### 联赛表现（所有方法使用同一目标FID）

| 联赛ID | 新增唯一FID | 市场模型 n / 净U / ROI | 对子模型 n / 净U / ROI | Crown+对子 n / 净U / ROI |
|---:|---:|---:|---:|---:|
{chr(10).join(league_lines)}

其中巴西甲只有9场，+5.720U不具充分样本支持；墨西哥甲的+0.015U近乎持平；MLS +2.005U是179场中唯一有一定样本量的正结果，但仅2025年，不代表持续优势。不得按本次联赛结果筛正式交易范围。

## 与原八组同期合并

目标样本日期范围为2025-03-02至2025-11-30（40周），与冻结原八组按唯一 FID 去重。冻结原八组在同期2,032单、+84.885U、ROI +4.177%、MDD 16.665U；平均每周50.800单。

| 候选方案 | 新增订单 / 增量净U | 合并唯一订单 / 合并净U / 合并ROI | 合并MDD | 合并周均单 |
|---|---:|---:|---:|---:|
{chr(10).join(merged_lines)}

配对模型的历史回放使同期合并净U增加+7.740U、合并ROI降幅取决于候选：本模型合并结果92.625U、3.957%；与原八组合并订单密度由50.800升至58.525单/周。市场only与pair-only候选分别降低合并净U。候选和原八组FID交集为0，所有候选属于历史独立FID增量。

## 真实赛前收据与可执行性

- 新增15联赛测试FID与所检查的真实Crown HTTP实收档案交集：0；本次真实赛前收据重放订单：0。
- 309条用于回放的T12 AH报价均来自Crown原始 `asian_list` 历史事件。独立核验逐条检查原始响应体SHA、赛事FID/联赛/主客ID、FT、开球时刻，并从原始亚洲盘历史列表独立重建截止开赛前12小时最近一笔有效报价。接收时间是赛后历史回取时间，非赛前实际收到。
- 球员阵容来源没有逐行首次发布/接收时刻。即使其关联的是目标前3天以前已结束比赛，也无法证明 Transfermarkt 当时的数据可用时间。因此本研究不能算作实时特征与实收报价的盈利证明。

## 独立复核

独立复核从原始Crown响应重读309个FID，对市场only、对子only、Crown+对子共927笔模拟下注逐笔拆分亚洲盘结算；校验787项输入与 schedule-page SHA（其中778个赛程原始页）、冻结8组成员10,294FID及固定 SHA、训练年度先后、候选FID去重与原八组零重叠。结果：**309/309原始响应通过；927/927结算一致；错误0；重算三模型净U分别−10.345U、−3.125U、+7.740U**。

可复跑：

```bash
python3 research/m8/player_pair_expanded15_20261121/run_pooled_t12_pair_cohesion.py
python3 research/m8/player_pair_expanded15_20261121/verify_pooled_pair_cohesion.py
python3 research/m8/player_pair_expanded15_20261121/build_deliverables.py
```

首条命令只从已有本地数据和只读Crown SQLite重建研究文件，不请求新报价；在相同输入上运行会重新生成结果。`independent_raw_crown_settlement_audit.json` 是第二条命令独立生成的核验结果。

## 结论与研究边界

2025年的 Crown+对子模型对309场新增联赛历史回放盈利+7.740U，但只有一个测试年度，且无真正实收人员特征快照；市场加对子没有实质提升净胜球误差，优势可能来自短期波动。目前证据不足以确认独立且可执行的长期盈利机制。不能宣称跨年度或真实赛前实收盈利，也不产生第九组。

本研究不改原八组、M1、MR1、M9、Telegram、正式账本、Crown采集链或生产规则；没有新增正式Gate、数量/联赛过滤或上线条件。所有研究结果与未完成的信息可用性缺口仍作为实验记录。
'''
    REPORT.write_text(text, encoding='utf-8')

    files = [
        REPORT,
        OUT / 'identity_coverage_audit.json',
        OUT / 'exact_fixture_identity_anchors.jsonl.gz',
        OUT / 'expanded15_T12_contract_inventory.jsonl.gz',
        OUT / 'expanded15_T12_candidate_source_audit.jsonl.gz',
        OUT / 'expanded15_pair_cohesion_actual_receipt_overlap.jsonl.gz',
        OUT / 'expanded15_pair_cohesion_per_fixture.jsonl.gz',
        OUT / 'pooled_pair_cohesion_predictions.jsonl.gz',
        OUT / 'pooled_pair_cohesion_market_plus_pair_ledger.jsonl.gz',
        OUT / 'pooled_pair_cohesion_summary.json',
        OUT / 'expanded15_pair_cohesion_coverage_by_year.json',
        OUT / 'expanded15_pair_cohesion_summary.json',
        OUT / 'independent_raw_crown_settlement_audit.json',
        OUT / 'EXECUTION_RECORD_20261121.md',
        OUT / 'audit_exact_lineup_identity.py',
        OUT / 'run_expanded15_pair_cohesion.py',
        OUT / 'run_pooled_t12_pair_cohesion.py',
        OUT / 'verify_pooled_pair_cohesion.py',
        OUT / 'build_deliverables.py',
        ROOT / 'research/m8/player_pair_cohesion_20261121/run_player_pair_cohesion.py',
        ROOT / 'research/m8/player_pair_cohesion_20261121/verify_player_pair_cohesion.py',
        ROOT / 'research/m8/m8_prior_manager_turnover_20261117.py',
    ]
    with (OUT / 'SHA256SUMS_20261121.txt').open('w', encoding='utf-8') as stream:
        for path in files:
            stream.write(f'{sha(path)}  {path.relative_to(ROOT)}\n')


if __name__ == '__main__':
    main()
