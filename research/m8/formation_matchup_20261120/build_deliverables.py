#!/usr/bin/env python3
"""Build diagnostic metrics, research report and SHA manifest for formation study."""
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, statistics

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
DATA = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
INPUTS = {
    'Transfermarkt_games.csv.gz': DATA/'m8_pregame_info_source_20261117/games.csv.gz',
    'Crown_full_path.jsonl': DATA/'m8_late_full_path_water_features_20261114.jsonl',
    'Crown_FT_score.jsonl': DATA/'m8_independent_score_strength_20261114.jsonl',
    'frozen_membership.jsonl': DATA/'m8_foundation_20261115/historical_membership.jsonl',
    'expanded_schedule.jsonl': DATA/'crown-drop-expanded-62/schedule_universe.jsonl',
    'Crown_SQLite_read_only': pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3'),
}
LEDGER = OUT/'formation_matchup_per_fixture_20261120.jsonl.gz'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def read_rows():
    with gzip.open(LEDGER,'rt',encoding='utf8') as f:
        for s in f:
            if s.strip():yield json.loads(s)

def metric(rows, key):
    if not rows:return {'n':0}
    residual=[float(r[key])-int(r['gd']) for r in rows]
    return {'n':len(rows),'MAE_home_goals':round(statistics.mean(abs(x) for x in residual),6),
            'RMSE_home_goals':round(math.sqrt(statistics.mean(x*x for x in residual)),6),
            'mean_prediction_error_home_goals':round(statistics.mean(residual),6)}

def main():
    rows=list(read_rows())
    outside=[r for r in rows if not r['frozen_member']]
    years=sorted({str(r['year']) for r in outside})
    paired={}
    for name,part in [('all_outside_frozen',outside)]+[(y,[r for r in outside if str(r['year'])==y]) for y in years]:
        switch=sum(r['market_chosen_side']!=r['market_plus_formation_chosen_side'] for r in part)
        paired[name]={
            'n_unique_FID':len({r['fid'] for r in part}),
            'market_margin':metric(part,'market_predicted_home_margin'),
            'market_plus_formation_margin':metric(part,'market_plus_formation_predicted_home_margin'),
            'chosen_side_agreement_n':len(part)-switch,
            'chosen_side_switch_n':switch,
            'chosen_side_switch_pct':round(100*switch/len(part),6) if part else None,
            'market_forced_net_U':round(sum(float(r['market_pnl_always_U']) for r in part),6),
            'formation_forced_net_U':round(sum(float(r['market_plus_formation_pnl_always_U']) for r in part),6),
            'paired_pnl_change_U':round(sum(float(r['market_plus_formation_pnl_always_U'])-float(r['market_pnl_always_U']) for r in part),6),
        }
    sample_form={
        'mapped_target_rows':len(rows),
        'both_sides_at_least_one_prior_365d_match':sum(r['home_prior_games_365d']>0 and r['away_prior_games_365d']>0 for r in rows),
        'either_side_has_no_prior_365d_match':sum(r['home_prior_games_365d']==0 or r['away_prior_games_365d']==0 for r in rows),
        'target_formation_used_as_feature':False,
        'method_note':'The target fixture formation is recorded only for leakage audit and is never used by model vectors.'}
    metrics={'study':'M8_CROWN_AH_FORMATION_MATCHUP_DIAGNOSTICS','paired_prediction_metrics':paired,
             'target_history_coverage':sample_form,
             'scope_note':'Metrics include the 2024-2026 out-of-frozen sample and are diagnostic; they do not select a production threshold.'}
    (OUT/'paired_model_diagnostics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')

    result=json.loads((OUT/'formation_matchup_results.json').read_text())
    scope=result['scope']
    scope['Transfermarkt_archive_formation_completeness_all_archive_rows']=scope.pop('target_formation_completeness',{})
    scope['mapped_target_prior_formation_coverage']=sample_form
    result['paired_model_diagnostics']=metrics
    (OUT/'formation_matchup_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')

    methods=result['results']; annual={m:{y:{k:v[k] for k in ('n','net_U','ROI_pct','max_drawdown_U','avg_orders_per_calendar_week')} for y,v in d['per_year'].items()} for m,d in methods.items()}
    # Extract the most informative compact outputs; the full weekly and league books remain in JSON.
    lines=['# M8 AH 赛前球队阵型风格差异研究（回顾实验）','',
      f"执行时间（UTC）：{result['created_utc']}",'',
      '## 结论','',
      '加入双方历史阵型风格画像后，固定时间前推模型在八组外 6,960 场上把强制选边的历史净亏损从 Crown 市场基准的 −299.435U 降至 −197.220U（相对改善 +102.215U），但新增候选仍为负收益，ROI −2.834%，最大回撤 207.420U。它不是盈利新订单来源。EV>0 研究变体同样亏损：Crown-only 为 1,291 笔、−21.140U；加入阵型后 2,823 笔、−122.060U。所有阈值仅用于事前固定的模型诊断，不是生产 Gate。','',
      '真实赛前可用性没有证据：Transfermarkt 形成数据是事后下载的历史汇总，没有形成信息的首次发布时间/实际收到时间；真实 Crown 收据 FID 与该实验交集为0。因而只能报告历史事件回放。','',
      '## 数据范围与时间边界','',
      f"- 原49联赛已有Crown完整路径：{scope['Crown_path_rows_original_inventory']:,} FID。另对扩展15范围中有明确 Transfermarkt 联赛映射的巴西、阿根廷、墨西哥、MLS，只从现存 Crown SQLite 历史 movement 行重建 T−1 报价；有效5,471场、无有效报价5,084场、同一最新事件冲突2场。研究未请求 Crown API。",
      f"- 合并历史T−1价格行：{scope['Crown_path_and_T1_rows_combined']:,}；Transfermarkt赛事映射与FT匹配成功：{scope['mapped_targets']:,}；2024–2026测试池 {scope['test_rows_2024_2026']:,}，其中冻结成员1,715、八组外唯一候选{scope['test_rows_outside_frozen']:,}。",
      f"- 跨源赛事身份用联赛、北京比赛日±1天、主客队名称相似度映射；先锁定身份，再独立核对FT。75场匹配记录FT不一致并排除；不使用目标比赛阵型、首发或赛果作为特征。身份覆盖/未映射原因见JSON。",
      '- 目标特征截止：比赛北京时间日期减3天；只用此前365日内、最多最近10场完成比赛。逐场模型训练为 expanding year：2024用2019–2023，2025用2019–2024，2026用2019–2025；固定 Ridge α=100。Crown-only 与 Crown+formation 使用相同测试比赛与价格。AH 四分之一盘按两腿结算，每笔1U。',
      '- 来源报价是 Crown 历史事件价格，不是收件时点报价。形成信息无可核验发布日期，故没有宣称这些特征当时可获取。',
      '', '## 主要收益结果','',
      '| 方案 | 八组外订单 | 净U | ROI | MDD U | 周均订单 |',
      '|---|---:|---:|---:|---:|---:|']
    labels={'market':'Crown-only 强制选边','market_plus_formation':'Crown+阵型 强制选边','market_ev_positive':'Crown-only 模型EV>0诊断','market_plus_formation_ev_positive':'Crown+阵型 模型EV>0诊断'}
    for m,d in methods.items():
        s=d['overall']; lines.append(f"| {labels[m]} | {s['n']:,} | {s['net_U']:+.3f} | {s['ROI_pct']:+.3f}% | {s['max_drawdown_U']:.3f} | {s['avg_orders_per_calendar_week']:.3f} |")
    lines += ['', '### 强制模型年度结果','', '| 方案 | 年份 | 单量 | 净U | ROI | MDD U |','|---|---:|---:|---:|---:|---:|']
    for m in ('market','market_plus_formation','market_ev_positive','market_plus_formation_ev_positive'):
        for y,v in annual[m].items():
            if v:lines.append(f"| {labels[m]} | {y} | {v['n']:,} | {v['net_U']:+.3f} | {v['ROI_pct']:+.3f}% | {v['max_drawdown_U']:.3f} |")
    lines += ['', '## 预测力与方向变化诊断','',
      '误差以主队净胜球预测减实际主队净胜球计算。模型误差改善不等于投注收益改善。详见 `paired_model_diagnostics.json`。','',
      '| 样本 | Crown-only MAE | Crown+阵型 MAE | Crown-only RMSE | Crown+阵型 RMSE | 选边改变 | PnL变化 |','|---|---:|---:|---:|---:|---:|---:|']
    for key,title in [('all_outside_frozen','2024–2026八组外')]+[(y,y) for y in years]:
        d=paired[key]; lines.append(f"| {title} | {d['market_margin']['MAE_home_goals']:.4f} | {d['market_plus_formation_margin']['MAE_home_goals']:.4f} | {d['market_margin']['RMSE_home_goals']:.4f} | {d['market_plus_formation_margin']['RMSE_home_goals']:.4f} | {d['chosen_side_switch_n']:,} ({d['chosen_side_switch_pct']:.2f}%) | {d['paired_pnl_change_U']:+.3f}U |")
    lines += ['', '## 与原八组合并（同期诊断）','',
      f"2024–2026冻结八组基准为 {result['frozen_baseline_2024_2026']['n']:,} 场、{result['frozen_baseline_2024_2026']['net_U']:+.3f}U、ROI {result['frozen_baseline_2024_2026']['ROI_pct']:.3f}%。Crown+阵型强制模型加入6,960个唯一八组外FID后合并为 {result['merged_with_frozen']['market_plus_formation']['n']:,} 场、{result['merged_with_frozen']['market_plus_formation']['net_U']:+.3f}U、ROI {result['merged_with_frozen']['market_plus_formation']['ROI_pct']:.3f}%；相比冻结八组单独净U下降197.220U。不能用仍为正的合并总额掩盖新增候选亏损。",
      '', '## Crown 与结算独立复核','',
      '独立验证器从只读 Crown SQLite 重取每笔 T−1 movement 报价，对线、双方水位、报价事件时间、历史 capture 模式、schedule身份、FT 与AH四分之一盘结算进行重核。结果见 `independent_verification.json`。验证通过只说明账本与来源一致，不代表模型盈利。真实live收据 FID 为0；正式订单、正式账本写入、生产修改、Crown API 请求均为0。',
      '', '## 覆盖、损失和解释限制','',
      '- 17,375场有Crown路径但无法按映射联赛与日期找到候选Transfermarkt赛程；8,440场属于没有明确联赛桥接的赛事；5,129场缺少可匹配比分/赛程；另75场身份候选的FT与目标不一致。覆盖缺口不记为模型未命中。',
      '- 形成策略全部年度强制选边为负；基于预测EV的拒投版本亦未转正。盈利改善属于损失减少，不足以抵消Crown水差。',
      '- league breakdown 全量留在 `formation_matchup_results.json`，不据个别联赛历史正收益追加规则；ISO周、逐场方向、报价线/双方赔率、FT与结算留在压缩逐场账本。',
      '- 因阵型字段没有时间戳、覆盖仅限29个已映射联赛，无法回答Crown是否充分计价一个当时可见的阵型信息信号；本实验没有证实八组外新增正利润，也不能主张跨联赛、跨年稳定性。',
      '', '## 可复现产物','',
      '- `run_formation_matchup.py`：时间前推训练与逐场账本。',
      '- `formation_matchup_per_fixture_20261120.jsonl.gz`：8,675场逐场输入、预测、Crown价格、FT与结算。',
      '- `formation_matchup_orders_20261120.jsonl.gz`：各研究方案下注账本。',
      '- `verify_formation_matchup.py`：原始报价、赛程、FT、AH独立复核。',
      '- `formation_matchup_results.json`、`paired_model_diagnostics.json`：年度、ISO周、联赛、去重、合并及模型对照。',
      '- `SHA256SUMS.txt`：输入/输出执行清单。',
      '', '研究用途。未修改冻结八组、M1/MR1/M9、生产工作流、Telegram、正式账本或 Crown 采集配置。','']
    (OUT/'M8_FORMATION_MATCHUP_20261120.md').write_text('\n'.join(lines),encoding='utf8')

    manifest=[]
    for name,path in INPUTS.items():
        manifest.append(f"{sha(path)}  INPUT {name}  {path}")
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name not in ('SHA256SUMS.txt',):
            manifest.append(f"{sha(path)}  OUTPUT {path.name}")
    (OUT/'SHA256SUMS.txt').write_text('\n'.join(manifest)+'\n',encoding='utf8')

if __name__=='__main__':main()
