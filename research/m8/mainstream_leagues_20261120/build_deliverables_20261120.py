#!/usr/bin/env python3
"""Build the M8 mainstream league report, execution record and SHA manifest."""
import datetime as dt, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
D=ROOT/'research/m8/mainstream_leagues_20261120'
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized')
RESULT=D/'M8_MAINSTREAM_LEAGUE_RESULTS_20261120.json'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def pct(x): return '—' if x is None else f'{x:+.3f}%'
def money(x): return f'{x:+.3f}'
def main():
    d=json.loads(RESULT.read_text()); audit=json.loads((D/'independent_audit_20261120.json').read_text())
    outside=d['strategy_results_outside_original_eight']; chosen=outside['league_prior_favorite_vs_underdog']
    fav=outside['universal_crown_favorite_baseline'];dog=outside['universal_crown_underdog_baseline']
    union=d['frozen_eight_union_by_strategy']['league_prior_favorite_vs_underdog']
    receipt=d['actual_http_receipt_replay_outside_original_eight']['league_prior_favorite_vs_underdog']
    receipt_fav=d['actual_http_receipt_replay_outside_original_eight']['universal_crown_favorite_baseline']
    rb=d['frozen_eight_actual_receipt_window_baseline'];ru=d['frozen_eight_actual_receipt_window_union_by_strategy']['league_prior_favorite_vs_underdog']
    paths=d['coverage_by_league']; names={x['league_id']:x for x in paths}
    req=[x for x in paths if x.get('requested_named_scope')]
    strategy=d['league_strategy_results_outside_original_eight']['league_prior_favorite_vs_underdog']
    # The league scope table reports annual quote-path / outside-eight / prior-study / raw / receipt coverage.
    rows=[]
    for x in sorted(req,key=lambda z:z['league_name']):
        yrs=[]
        for y in map(str,range(2022,2027)):
            v=x['by_year'].get(y,{})
            yrs.append(f"{v.get('crown_ah_fids',0)}/{v.get('outside_eight_fids',0)}/{v.get('previous_intensive_target_fids',0)}/{v.get('raw_crown_response_bodies',0)}/{v.get('all_actual_http_receipt_unique_fids',0)}")
        rows.append(f"| {x['league_name']} | {x['league_id']} | {x['cached_schedule_trusted_ft_2022_2026']} | {x['path_crown_ah_fids_2022_2026']} | {x['frozen_eight_fids_2022_2026']} | {x['previous_intensive_target_fids_2024_2026']} | {x['raw_crown_response_body_fids_2022_2026']} | {x['all_actual_http_receipt_unique_fids']} | "+' | '.join(yrs)+' |')
    # Complete tested-league performance table; per-year n/U retained for every league.
    perf=[]; perf_requested=[]
    for lid,v in sorted(strategy.items(),key=lambda kv:kv[1]['league_name'].casefold()):
        o=v['overall_2022_2026']; yr=[]
        for y in map(str,range(2022,2027)):
            z=v['by_year'].get(y,{})
            yr.append('—' if not z.get('n') else f"{z['net_u']:+.3f} ({z['n']})")
        perf.append(f"| {v['league_name']} ({lid}) | {o['n']} | {o['net_u']:+.3f} | {o['roi_pct']:+.3f}% | {o['mdd_u']:.3f} | "+' | '.join(yr)+' |')
    for x in sorted(req,key=lambda z:z['league_name']):
        lid=x['league_id'];v=strategy.get(lid)
        if v and v['overall_2022_2026']['n']:
            o=v['overall_2022_2026'];yr=[]
            for y in map(str,range(2022,2027)):
                z=v['by_year'].get(y,{})
                yr.append('—' if not z.get('n') else f"{z['net_u']:+.3f} ({z['n']})")
            perf_requested.append(f"| {x['league_name']} ({lid}) | {o['n']} | {o['net_u']:+.3f} | {o['roi_pct']:+.3f}% | {o['mdd_u']:.3f} | "+' | '.join(yr)+' |')
        else:
            perf_requested.append(f"| {x['league_name']} ({lid}) | 0 | — | — | — | — | — | — | — | — |")
    prior=json.loads((ROOT/'research/m8/m8_league_market_response_20261117.json').read_text())
    r43=prior['models']['global']['markets']['AH']['league']
    prior_lines=[]
    for lid,label in [('70','Denmark Superligaen'),('14','Spain La Liga'),('177','Wales Premier League')]:
        z=r43.get(lid,{}).get('history',{})
        prior_lines.append(f"- {label}（R43 global AH history）：n={z.get('n')}, {z.get('U')}U / ROI {z.get('ROI')}%。R43 的残差方向和本轮整联赛 favorite/underdog 历史选择不同，不能视为相同策略或同一盘口样本。")
    positives=sorted(((lid,v['league_name'],v['overall_2022_2026']) for lid,v in strategy.items() if v['overall_2022_2026']['n'] and v['overall_2022_2026']['net_u']>0),key=lambda z:-z[2]['net_u'])
    positive_text=', '.join(f"{name} {m['net_u']:+.3f}U/{m['roi_pct']:+.3f}% (n={m['n']})" for _,name,m in positives)
    report=f'''# M8 主流联赛独立盈利机制扩展研究

日期：2026-11-20（北京时间）

状态：历史研究与真实收据复算完成；未部署生产策略。

## 结论

固定的联赛内逐年方向选择规则没有在全部样本中增加利润。2022–2026年，八组外26,436个唯一FID净亏 **{chosen['net_u']:.3f}U**，ROI **{chosen['roi_pct']:.3f}%**，MDD **{chosen['mdd_u']:.3f}U**，244个活跃ISO周平均108.344场/活跃周（按254周日历跨度均值104.079）。它比始终favorite基准额外少赚203.915U。2022–2026每个年度都为负。加上冻结原八组同期8,724场/+223.925U后，严格FID去重并集35,160场、净 **{union['net_u']:.3f}U**、ROI {union['roi_pct']:.3f}%、MDD {union['mdd_u']:.3f}U；相对原八组净利润减少 **764.375U**。

个别联赛的历史结果为正，但不构成可确认的新订单来源。全覆盖48个有Crown AH路径的联赛中，固定实验的正净U共{len(positives)}个：{positive_text}。丹麦和威尔士所选方向在所有有样本的年度都恰为市场 favorite 基线，因而本轮没有发现区别于 favorite 的可归因信号；西甲也一直选favorite，并且在 R43 等既有研究中已做过联赛级检验。多联赛结果属于同一既有赛事库的回顾性前推实验，不是新比赛库存或未见数据。没有经过独立、未参与研究设计的真实前瞻验证。

真实HTTP Crown收据回放中，八组外977个唯一FID所选历史联赛方向为 **+18.245U / +1.867% / MDD 9.080U**，六个ISO周平均162.833场；同期冻结八组324单/+1.830U。去重合并1,301单/+20.075U、ROI+1.543%、MDD12.855U。这个正数是事后研究回放：这些收据和赛果已进入本项目先前研究范围，历史训练字段的首次可见/接收时间也未得到证明，故不能作为盲测或实盘盈利确认。逐周数据保留在JSON与逐场账本。

**最终判断：本轮没有证明一个不同于原八组、可按真实赛前信息稳定增加净利润的联赛机制。**

## 冻结规则与输入

- 冻结原八组清单：10,294个唯一FID，SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`；2022–2026同期8,724场/+223.925U。生产成员和规则未改。
- 输入包括39,101行历史 Crown AH source-event path、40,277行带可信 FT 的分数/赛事索引、5,180份缓存赛程页（78,614个唯一赛事ID）、真实HTTP receipt归档及R43联赛回测结果。路径源按FID与FT核对：39,101/39,101通过；其中36,117还有本地Crown赛程队伍身份复核，2,984没有赛程页但通过精确FID/比分源连接并单列。没有调用API或重建采集链。
- 原 A–D 2024–2026深入目标池21,455个FID全部在本轮路径/FT库中找到（缺失0）。本轮多出2022–2023年4,981个八组外目标FID，但它们来自既有缓存，不是新报价来源。不能将目标池改名为新增数据。
- 2026源数据截至2026-07-06。全部历史报价是 Crown source-event T1回放；报价事件时间不等于HTTP收件时间或可成交时间。

## 覆盖审计

下表每个年份的单元依次为 `Crown AH路径 / 八组外 / 既有2024–26深入目标 / 原始响应含赛前AH / 实际HTTP收据FID`；赛程完整FT、冻结八组、旧目标、原始响应及receipt的总计各自分列。缓存赛程不是该联赛完整赛季分母。

| 联赛 | ID | 缓存赛程FT | 路径FID | 八组FID | 旧深入目标24–26 | 原始响应FID | HTTP收据FID | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

18个建议联赛中，14个在当前保存路径内有Crown AH报价；MLS、巴西甲、阿根廷甲和Liga MX虽有缓存赛程/FT记录，但Crown AH路径为0，因此无法计算Crown收益。14个有价格的范围共有{sum(x['path_crown_ah_fids_2022_2026'] for x in req)}个2022–2026历史FID（与跨联赛全库去重口径不同）；记录并非完整赛季全集。全库共{len(strategy)}个联赛ID在2022–2026年有Crown路径和可结算样本，结果全部保留在JSON。

## 研究规则与时间前推

只测试一个固定的新方向选择机制，并保留两个基准：在每个联赛单独按年度前推；目标年度之前，在同联赛已结历史中比较 favorite 与 underdog 两侧的累计净U，选累计净U较高的一边用于目标年度所有比赛；平手或无历史则默认favorite。没有按目标年筛球队、盘口、赛季阶段或参数，也不使用目标年赛果选边。另报告始终favorite与始终underdog基准。方向规则是研究实验，不是交易Gate。

所有比赛使用历史 Crown 主队AH线、双方十进制赔率和可信 FT；四分之一盘拆成两腿，输出全赢/半赢/走水/半输/全输。统计按北京时间日期和ISO周。三种方法共享同一逐年FID池，不得把它们的单量或收益相加。

## 全库成绩

| 八组外方法 | FID | 净U | ROI | MDD | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 联赛前序收益选favorite/underdog | {chosen['n']} | {chosen['net_u']:+.3f} | {chosen['roi_pct']:+.3f}% | {chosen['mdd_u']:.3f} | {chosen['year']['2022']['net_u']:+.3f}U ({chosen['year']['2022']['n']}) | {chosen['year']['2023']['net_u']:+.3f}U ({chosen['year']['2023']['n']}) | {chosen['year']['2024']['net_u']:+.3f}U ({chosen['year']['2024']['n']}) | {chosen['year']['2025']['net_u']:+.3f}U ({chosen['year']['2025']['n']}) | {chosen['year']['2026']['net_u']:+.3f}U ({chosen['year']['2026']['n']}) |
| 始终 Crown favorite | {fav['n']} | {fav['net_u']:+.3f} | {fav['roi_pct']:+.3f}% | {fav['mdd_u']:.3f} | {fav['year']['2022']['net_u']:+.3f}U | {fav['year']['2023']['net_u']:+.3f}U | {fav['year']['2024']['net_u']:+.3f}U | {fav['year']['2025']['net_u']:+.3f}U | {fav['year']['2026']['net_u']:+.3f}U |
| 始终 Crown underdog | {dog['n']} | {dog['net_u']:+.3f} | {dog['roi_pct']:+.3f}% | {dog['mdd_u']:.3f} | {dog['year']['2022']['net_u']:+.3f}U | {dog['year']['2023']['net_u']:+.3f}U | {dog['year']['2024']['net_u']:+.3f}U | {dog['year']['2025']['net_u']:+.3f}U | {dog['year']['2026']['net_u']:+.3f}U |

选择规则在2022、2023、2024、2025、2026的八组外年度分别为{chosen['year']['2022']['n']}、{chosen['year']['2023']['n']}、{chosen['year']['2024']['n']}、{chosen['year']['2025']['n']}、{chosen['year']['2026']['n']}场，净U持续为负。跨方法覆盖相同、成对FID重合100%，不能拼成额外覆盖。

## 指定18联赛结果

每行年度栏格式为 `净U (FID)`。无Crown AH路径者明确标为未能回测。完整逐年ROI、周/联赛拆分、五态和盘口逐笔详情在结果JSON。

| 联赛 | FID | 净U | ROI | MDD | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(perf_requested)}

用户指定范围有正收益的历史结果：西甲+30.635U、葡超+0.850U、土超+0.465U；葡超和土超接近零且年际不稳定。西甲的实验选择五年均为favorite，等同于无学习的favorite基准，且该联赛已有R43联赛模型研究；不能称为新型独立信号。其他指定联赛净U为负。被动纳入的丹麦、威尔士有较大的favorite基线正数，但属于同一全库筛查发现，须视为多重比较下的候选现象，不视为验证通过。

完整48联赛逐年表现留存于 `M8_MAINSTREAM_LEAGUE_RESULTS_20261120.json`。该研究没有在目标年内挑选条件。丹麦Superliga favorite基线2023–2026为+1.710、+10.480、+23.985、+10.370U（430场，+46.545U），且前推方向五个有结果年度都选favorite；这只是历史结果，市场残差R43在其AH历史池403场为−7.970U，Receipt为24场−7.050U。方法、日期窗口、目标FID覆盖不同，不能直接相减；相反结果说明需要真正新时段前瞻，不能只凭全历史结果宣布新机会。西甲R43 global AH历史774场−16.290U，但其方法同样不同。

### 其他已覆盖联赛全量成绩

以下完整列出2022–2026年全库48个有Crown AH路径的联赛，格式同上；保留全部正负结果。逐周、五态和每个FID仍见JSON/JSONL。

| 联赛 | FID | 净U | ROI | MDD | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(perf)}

## Crown真实HTTP收据复核

- 三个已审来源共读取{d['coverage_sources']['receipt_rows_by_source'] and sum(d['coverage_sources']['receipt_rows_by_source'].values())}条receipt行；M8逐方法审计行3,690条，形成1,230个唯一比赛FID，报价与FT在方法行间一致0冲突；其中253个FID与原八组重叠，八组外977个候选FID。其他来源的全部不同真实receipt FID并集为{d['coverage_sources']['all_receipt_fid_union']}。
- 八组外按冻结的年度联赛选边复算977场：+18.245U、ROI+1.867%、MDD9.080U；2026-W41至W46分别+14.940、−1.080、−4.850、+15.795、−8.460、+1.900U。favorite基线同977场−17.235U/−1.764%。
- 原八组在同一receipt窗口324场/+1.830U；去重合并1301场/+20.075U。receipt候选的正数集中且属于既有研究收据窗口，不是正式Telegram单、成交记录或未见赛果。方向训练输入首次发布时间/系统收件时间没有证明，`history_features_first_seen_timestamp_proven=false`；不得把历史字段说成当时已知的真实实时预测。

## 前序研究去重与解释

R1–R65、A–L及M1–M8已反复覆盖全市场Crown AH残差、方向模型、联赛偏移/响应、球队熟悉度、H2H、球队近期强弱、路径特征和盈利筛选。R43已按联赛报告global/league-level/response模型及实收子集。本轮真正不同的实验规则是以每个联赛之前年度favorite/underdog累计净U作不含目标年度结果的简单方向选择；没有引入新赛程、球队、赔率源或FIDs。2024–2026指定目标21,455 FID全部已在此前深度研究集合中，故模型方向实验有新但数据不是新；2022–2023另4,981 FID是已有路径库较早年份，并非新增采集库存。

本轮对14个可定价的建议联赛和全库48个带AH路径联赛都跑同一固定规则，所有负结果保留。没有根据目标年结果择取联赛。正净U地区在同一库的全库排序与R43、方向基准并列，存在多重比较和旧样本过拟合风险，不能升级生产。

## 逐场与独立核验

- `per_fixture_league_predictions_20261120.jsonl.gz`包含102,843行（3个方向×34,281个FID），逐场保留Crown线、双边赔率、方向、FT、AH五态、净U、league/year/ISO周、训练选边及八组成员标记。
- 新的独立核验器直接重读原始Crown历史path、比分/FT及冻结成员文件，对每个FID的双方AH五态结算独立复算；年度联赛选择用目标年之前同联赛收益重建。102,843预测行、161个训练选择、2024–2026已研究目标21,455个全匹配、26,436个八组外唯一FID及去重合并净U/ROI/MDD均校验通过，见 `independent_audit_20261120.json`（`pass=true`）。
- 收据账本从逐场独立审计输入复核，1,230个独立FID的Crown line、双边价格、FT与实际收件时间一致且未晚于开球；外八组977个按真实收据价格正确结算，独立净U/ROI/MDD吻合。源receipt原始SHA及snapshot SHA保留原始审计值，不重新冒充回读私有HTTP原件。
- 原始Crown HTTP body覆盖只统计本地有效response index的已存文件；不替换历史path，不将缺失raw body称作没有市场。所有实验都不是正式Telegram派单或实际成交。

## 原八组去重合并

| 口径 | 唯一FID | 净U | ROI | MDD | 与仅八组相比 |
|---|---:|---:|---:|---:|---:|
| 冻结原八组2022–26 | {d['frozen_eight_baseline_2022_2026']['n']} | {d['frozen_eight_baseline_2022_2026']['net_u']:+.3f} | {d['frozen_eight_baseline_2022_2026']['roi_pct']:+.3f}% | {d['frozen_eight_baseline_2022_2026']['mdd_u']:.3f} | — |
| 八组外选择法单独 | {chosen['n']} | {chosen['net_u']:+.3f} | {chosen['roi_pct']:+.3f}% | {chosen['mdd_u']:.3f} | −764.375U |
| FID去重合并 | {union['n']} | {union['net_u']:+.3f} | {union['roi_pct']:+.3f}% | {union['mdd_u']:.3f} | 净利润减少764.375U |

## 产物

- 覆盖和全量结果：`M8_MAINSTREAM_LEAGUE_RESULTS_20261120.json`、`coverage_by_league_20261120.jsonl`。
- 逐场Crown path模拟：`per_fixture_league_predictions_20261120.jsonl.gz`。
- 实际HTTP收据复算及来源注册：`actual_receipt_replay_per_fixture_20261120.jsonl.gz`、`actual_receipt_coverage_registry_20261120.jsonl.gz`。
- 主研究：`m8_mainstream_league_expansion_20261120.py`；独立结算审计：`verify_mainstream_expansion_20261120.py`；报告/执行/哈希构建：`build_deliverables_20261120.py`。
- SHA256清单：`SHA256SUMS_20261120.txt`。

无正式策略、M9、M1、MR1、原八组、Telegram、正式账本、Crown采集配置或生产调度变更；没有运行正式GitHub Actions。
'''
    (D/'M8_MAINSTREAM_LEAGUE_EXPANSION_20261120.md').write_text(report)
    commands=[
      'python3 research/m8/mainstream_leagues_20261120/m8_mainstream_league_expansion_20261120.py',
      'python3 research/m8/mainstream_leagues_20261120/verify_mainstream_expansion_20261120.py',
      'python3 research/m8/mainstream_leagues_20261120/build_deliverables_20261120.py',
      'python3 -m py_compile research/m8/mainstream_leagues_20261120/m8_mainstream_league_expansion_20261120.py research/m8/mainstream_leagues_20261120/verify_mainstream_expansion_20261120.py']
    (D/'EXECUTION_RECORD_20261120.md').write_text('# 执行记录\n\n'+'\n'.join(f'- `{c}`：已运行。' for c in commands)+f"\n\n- 主回测输出八组外唯一FID {chosen['n']}，方向选择净U {chosen['net_u']:.3f}U；年度与逐周成绩保留。\n- 独立AH/FT审计 `pass={audit['pass']}`：逐场预测行{audit['prediction_rows_read']}；Crown-path/FT及AH结算不一致{sum(audit['errors'].values())}；2024–2026既有深入样本匹配{d['input_counts']['intensive_2024_26_target_fids_found_in_path_score']}/{d['input_counts']['intensive_2024_26_target_fids_found_in_path_score']}。\n- 真实HTTP receipt：唯一FID{audit['actual_receipt_unique_fids']}，其中外八组{audit['actual_receipt_outside_eight_fids']}；不代表正式订单或未见样本。\n- SHA256输入/输出清单包含于本目录；报告/账本均不含私有Crown raw body。\n- 未运行正式workflow/Actions；正式Telegram派单0、账本回写0、生产采集/调度修改0。\n")
    inputs=[PATHF:=WORK/'m8_late_full_path_water_features_20261114.jsonl',WORK/'m8_independent_score_strength_20261114.jsonl',WORK/'m8_foundation_20261115/historical_membership.jsonl',
        DATA/'crown-response-index.jsonl',ROOT/'research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl',
        WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl',ROOT/'research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl',
        ROOT/'research/m8/next_round_20261120/per_fixture_walkforward_20261120.jsonl.gz',ROOT/'research/m8/m8_league_market_response_20261117.json']
    output=sorted(p for p in D.iterdir() if p.is_file() and p.name!='SHA256SUMS_20261120.txt')
    lines=[f'{sha(p)}  OUTPUT::{p.name}\n' for p in output]
    lines += [f'{sha(p)}  INPUT::{p}\n' for p in inputs if p.exists()]
    (D/'SHA256SUMS_20261120.txt').write_text(''.join(lines))

if __name__=='__main__':main()
