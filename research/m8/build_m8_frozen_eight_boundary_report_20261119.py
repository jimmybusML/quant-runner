#!/usr/bin/env python3
"""Build the auditable M8 frozen-eight boundary report and manifests."""
import collections, datetime as dt, gzip, hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
OUT=ROOT/'research/m8/frozen_eight_boundary_expansion_20261119'
RESULT=OUT/'M8_FROZEN_EIGHT_BOUNDARY_EXPANSION_RESULTS_20261119.json'
MEM=WORK/'m8_foundation_20261115/historical_membership.jsonl'

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def metrics(rows):
    if not rows:return {'n':0,'net_U':0.0,'ROI_pct':None,'max_drawdown_U':0.0,'calendar_weeks':0,'avg_per_calendar_week':0.0,'weekly':{}}
    daily=collections.defaultdict(float); weekly=collections.defaultdict(lambda:{'n':0,'net_U':0.0})
    for x in rows:
        day=dt.date.fromisoformat(str(x['date'])[:10]); daily[day]+=float(x['pnl'])
        iso=day.isocalendar(); k=f'{iso.year}-W{iso.week:02d}';weekly[k]['n']+=1;weekly[k]['net_U']+=float(x['pnl'])
    cum=peak=dd=0.0
    for day in sorted(daily):cum+=daily[day];peak=max(peak,cum);dd=max(dd,peak-cum)
    n=len(rows); net=sum(float(x['pnl']) for x in rows)
    d0=min(dt.date.fromisoformat(str(x['date'])[:10]) for x in rows);d1=max(dt.date.fromisoformat(str(x['date'])[:10]) for x in rows)
    weeks=(d1-d0).days//7+1
    return {'n':n,'net_U':round(net,6),'ROI_pct':round(100*net/n,6),'max_drawdown_U':round(dd,6),
        'calendar_weeks':weeks,'avg_per_calendar_week':round(n/weeks,6),
        'active_weeks':len(weekly),'positive_weeks':sum(v['net_U']>1e-10 for v in weekly.values()),
        'negative_weeks':sum(v['net_U']<-1e-10 for v in weekly.values()),
        'weekly':{k:{'n':v['n'],'net_U':round(v['net_U'],6)} for k,v in sorted(weekly.items())}}

data=json.loads(RESULT.read_text())
members=[json.loads(x) for x in MEM.open()]
# Keep source hashes auditable without publishing this workstation's absolute
# user directory paths.
safe_inputs={}
for path,meta in data.get('input_audit',{}).get('inputs_sha256',{}).items():
    p=pathlib.Path(path)
    try:key='repo/'+str(p.resolve().relative_to(ROOT.resolve()))
    except Exception:key='local_research_work/'+p.name
    safe_inputs[key]=meta
if safe_inputs:data['input_audit']['inputs_sha256']=safe_inputs
bygroup=collections.defaultdict(list)
for x in members:bygroup[str(x['cohort'])].append({'fid':str(x['fid']),'year':int(x['year']),'date':x['date'],'league':str(x['league']),'pnl':float(x['pnl'])})
for g,rows in bygroup.items():
    p=data['frozen_group_profiles'][g]
    p['frozen_full_period']=metrics(rows)
    p['frozen_annual']={str(y):metrics([r for r in rows if r['year']==y]) for y in sorted({r['year'] for r in rows})}
    p['frozen_weekly']=p['frozen_full_period']['weekly']
    if 'full_period' in p:p['quote_FT_reconstructed_subsample']=p.pop('full_period')
    if 'annual' in p:p['quote_FT_reconstructed_annual_subsample']=p.pop('annual')
    if 'settlement_classes' in p:p['quote_FT_reconstructed_settlement_classes']=p.pop('settlement_classes')

archive=[json.loads(x) for x in (WORK/'m8_extra_inventory_frozen_eight_20261115.jsonl').open()]
archive_selected=[x for x in archive if x.get('cohort')]
frozen_ids={str(x['fid']) for x in members}
archive_overlap=collections.Counter(str(x['cohort']) for x in archive_selected if str(x['fid']) in frozen_ids)
archive_outside=collections.Counter(str(x['cohort']) for x in archive_selected if str(x['fid']) not in frozen_ids)
data['input_audit']['previously_audited_archive_rule_hits_total']=len(archive_selected)
data['input_audit']['previously_audited_archive_rule_hits_by_group']=dict(archive_overlap)
data['input_audit']['previously_audited_archive_rule_hits_already_in_frozen_membership']=sum(archive_overlap.values())
data['input_audit']['previously_audited_archive_rule_hits_outside_frozen_membership']=sum(archive_outside.values())
data['input_audit']['previously_audited_archive_rule_hits_outside_by_group']=dict(archive_outside)
data['input_audit']['frozen_membership_full_quote_FT_or_authoritative_PnL_n']=len(members)
data['input_audit']['frozen_membership_authoritative_net_U']=round(sum(float(x['pnl']) for x in members),6)
audit=json.loads((OUT/'independent_raw_crown_settlement_audit_20261119.json').read_text())
data['independent_raw_crown_settlement_audit']=audit
RESULT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

lines=[]
lines += ['# M8 冻结原八组盈利边界扩展研究（2026-11-19）','',
 '## 结论摘要','',
 '本轮按原八组分别训练“历史盘路画像相似度”，只在原八组规则均未触发的比赛中做研究性候选；每个年度只用此前年度训练，q90/q95/q99 分界只由更早年度 OOF 相似度分布确定。AH 与原组方向保持一致，按 Crown T1 原始亚洲盘线/赔率和 FT 结算。该结果是历史报价事件回放，不是 HTTP 收据实战。', '',
 '**未找到能稳健确认的第九类盈利来源。** q95 有效组合里只有 base 的两版本略正，其余亏损；q99 两个尾部分位组合的盈利存在明显跨年波动。真实 HTTP 收据候选回放为 0 场。', '',
 '所有阈值、模型和分位仅为研究实验；无任何正式 Gate 或生产修改。', '',
 '## 原八组冻结基准','',
 '冻结清单 SHA256：`'+data['frozen_foundation']['frozen_membership_sha256']+'`；唯一成员 `10,294` 场，冻结历史净收益 `+236.015U`。下表收益来自完整冻结成员表；原始报价重建子样本另行审计。', '',
 '| 组 | 场次 | 净U | ROI | MDD U | 周均单量 |', '|---|---:|---:|---:|---:|---:|']
for g in ('base','A','B','C','D','E','F','G'):
    m=data['frozen_group_profiles'][g]['frozen_full_period']
    lines.append(f"| {g} | {m['n']} | {m['net_U']:.3f} | {m['ROI_pct']:.3f}% | {m['max_drawdown_U']:.3f} | {m['avg_per_calendar_week']:.2f} |")
lines += ['', '逐组年度和 ISO 周成绩、球队/联赛/盘口/报价分布见结果 JSON；逐场可复核的报价与结算记录见压缩账本。', '',
 '## 研究定义与防止重复','',
 '- 原八组定义、方向和成员均冻结；旧 R32 的 D/E/F 通用边界及 R33 的 base/A/B/C 路径划分不重做。',
 '- 冻结定义（按现存原脚本/清单复核）：base=T−6至T−1期间主让球盘口线朝主队让得更深时押T1受让侧；A=6/3/1路径`deepen_weaken`、押受让侧；B=`weaken_same`、押受让侧；C=非零盘口且路径震荡、押T1盘口优势侧；D=零盘口往返且主客时间均价相对条件成立、按原规则押客侧；E=零盘口不变、价格份额先后双向变化并回到起点、押原全程变化方向的反侧；F=零盘口不变且价格份额单向、第一段中性、后段沿单向变化、按原规则方向；G=往返盘口且独立比分模型EV方向与相对市场价格变化一致、原定义押模型相反方向。精确触发、方向和冻结FID仍以冻结清单/原脚本为权威，本研究不改写会员或生产规则。',
 '- 以每个原组的历史触发作为标签，按 Crown 盘口线/水位路径、路径形状及联赛拟合组别画像；附加版本只加入严格滞后的球队角色/既往组别结算信息。',
 '- 固定逻辑回归 L2=0.01、年内标准化与训练集类别编码；每个验证年只用更早年份训练。q90/q95/q99 是更早年度 OOF 规则外比赛相似度的经验分位数，不用目标年收益选阈值。所有版本及分数逐场保留。',
 '- 历史研究期是 2019–2026；特征库存包括核心 39,101 行及已审计扩展 5,842 行，去重 44,943 FID。2026 特征库存截止日期继承历史报价库。',
 '- 已审计的 1,337 条新增库存命中与冻结成员逐FID交叉核对，已在冻结会员集合中，不被再次作为新单；记录于结果 JSON 的输入审计。',
 '- 多个研究方法对同一 FID 有重叠，且有方向冲突；所有个别方法独立列账，不把不同模型的候选利润相加。', '',
 '## 新增候选排行榜：q95 主参考','',
 '下表是固定 q95 敏感性参考结果，并非交易阈值。增量收益独立于原八组；合并栏按原冻结成员+该单一候选版本计算，不含其他候选模型。', '',
 '| 原组画像 | 模型 | 唯一新增 | 净U | ROI | MDD U | 周均新增 | 2024 U | 2025 U | 2026 U | 合并净U | 合并ROI |',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
q95=[]
for k,v in data['candidate_summary'].items():
    if '|q95' not in k:continue
    group,model,q=k.split('|');m=v['candidate'];ys=v['candidate_annual'];cm=v['frozen_plus_candidate']
    q95.append((m['net_U'],k,v))
for _,k,v in sorted(q95,reverse=True):
    g,model,_=k.split('|');m=v['candidate'];ys=v['candidate_annual'];cm=v['frozen_plus_candidate']
    label='market + lagged team history' if model.endswith('team_history') else 'market path only'
    y24=ys.get('2024',{}).get('net_U',0);y25=ys.get('2025',{}).get('net_U',0);y26=ys.get('2026',{}).get('net_U',0)
    lines.append(f"| {g} | {label} | {m['n']} | {m['net_U']:.3f} | {m['ROI_pct']:.3f}% | {m['max_drawdown_U']:.3f} | {m['avg_per_calendar_week']:.2f} | {y24:+.3f} | {y25:+.3f} | {y26:+.3f} | {cm['net_U']:.3f} | {cm['ROI_pct']:.3f}% |")
lines += ['', f"本次可计算 q95 组合为 {len(q95)} 个（G 组因历史训练/阈值不可用未生成 q95 结果），其中只有 base 的两版本正值；其余亏损。base q95 在 2025 为负、2026 仅小幅正。q90、q99 的全部模型/年份指标保存在结果 JSON 与逐场候选账本中，不隐藏负结果。可计算 q99 组合中，2 个正结果（A+team history +7.865U；D+team history +7.810U）属于多重探索敏感结果，且年份表现不一致，不能视为已确认扩单机制。q99 正结果逐年拆分：", '',
 '| 方法 | 新增数 | 净U | ROI | MDD U | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for k,v in sorted(data['candidate_summary'].items()):
    if '|q99' not in k or v['candidate']['net_U']<=0:continue
    m=v['candidate'];ys=v['candidate_annual'];
    annual=' | '.join(f"{ys.get(str(y),{}).get('net_U',0):+.2f}" for y in range(2021,2027))
    lines.append(f"| {k.replace('|',' / ')} | {m['n']} | {m['net_U']:.3f} | {m['ROI_pct']:.3f}% | {m['max_drawdown_U']:.3f} | {annual} |")
lines += ['', '这两条 q99 正值不是稳定逐年盈利：A+team 在 2024、2026 分别 -6.700U、-8.330U；D+team 在 2023、2025 分别 -3.120U、-4.950U。其正值只能作为待独立前瞻验证的研究观察。', '',
 '## 真实 HTTP 收据与历史报价事件','',
 f"本研究候选要求 T1 盘口路径字段，既有可核验赛前 HTTP 收据库存与该 T1 特征时点不兼容，因此**候选边界模型真实收据回放为 0 场**；没有用历史取回盘口替代实际收到盘口。既有原八组历史收据档案 306 行，其中可结算信号 50 场、净 `+3.640U`，属于对历史赛前收据的回溯重放，不等于实际 Telegram 下单或实战收益。逐组收据数字见 JSON。", '',
 '## 独立核验','',
 f"独立核验脚本重新读取 Crown 原始响应，核对 FID/联赛/主客ID/开球时间/FT、SHA 可用性、开球前 T−1 最新 Crown `asian_list` 报价，并重新拆分四分之一盘口双腿结算。已复核 `{audit['raw_Crown_rows_verified']}` 个预测唯一 FID、`{audit['settlement_checks']}` 笔方向选择，收益一致性：`{audit['all_verified_selections_match']}`；失败分类：`{json.dumps(audit['failures'],ensure_ascii=False)}`。盘口事件时间不是 HTTP 收件时间。", '',
 '## 逐组覆盖与限制','',
 f"研究特征抽取本身连接到 `{data['input_audit']['frozen_detail_quotes_and_FT_joined']}` 个冻结FID；对完整冻结成员，独立审计另行重读原始 Crown 响应，`{audit['frozen_members_raw_quote_FT_and_PnL_reproduced_n']}/{audit['frozen_member_n']}` 全部核对到 T−1 报价、FT，且至少一侧结算复现冻结净U。`{audit['frozen_member_unique_original_side_n']}` 个方向可由冻结净U唯一识别；其余 `{audit['frozen_member_n']-audit['frozen_member_unique_original_side_n']}` 个方向存在相同结算现金流而无法从利润唯一识别，逐笔记录两侧结算类别，不臆测原始方向。", '',
 '候选池与原八组按唯一 FID 去重。跨画像候选去重并集为 `'+str(data['candidate_overlap']['unique_union_FIDs'])+'` 个 FID；不同方法间方向冲突 `'+str(data['candidate_overlap']['direction_conflict_FIDs_n'])+'` 个 FID。没有自动仲裁或合并所有候选的方法。', '',
 '## 结论','',
 '基于当前历史 Crown 路径库存，组别画像相似度没有给出可确认、可跨期稳定增加净利润的订单来源。base q95 两模型只是小幅历史正收益且目标年份不稳；A、D q99 组合的正值来自多个尝试的极端尾部分位，样本量与逐年波动不支持将其称为发现。其余候选多数增加亏损单量，q90 尤其如此。独立原始 Crown/FT/AH 核验通过，但这不能弥补数据复用和非前瞻样本的问题；真实收据新候选样本为零。原八组与所有生产系统保持不变。', '',
 '## 复算文件','',
 '- `m8_frozen_eight_boundary_expansion_20261119.py`：主研究，包含固定组别标签复算、时间前推拟合、相似度敏感性阈值、逐场账本。',
 '- `verify_m8_frozen_eight_boundary_20261119.py`：独立重读原始 Crown 响应及 FT、盘口、方向结算。',
 '- `build_m8_frozen_eight_boundary_report_20261119.py`：冻结全成员年度/逐周统计、报告与 SHA 清单构建。',
 '- 目录内 JSON 和 gzip JSONL：完整模型审计、逐场方向/赔率/FT/U、全部评分与阈值、独立原始盘口核验、完整冻结八组逐FID Crown报价/FT/双侧结算及原冻结PnL匹配。',
 '- `SHA256SUMS_20261119.txt`、`EXECUTION_RECORD_20261119.md`：输入/输出摘要与实际执行记录。', '']
report=ROOT/'research/m8/M8_FROZEN_EIGHT_BOUNDARY_EXPANSION_20261119.md'
report.write_text('\n'.join(lines),encoding='utf-8')

# Full frozen membership ledger, including rows whose current quote join is absent.
with gzip.open(OUT/'frozen_eight_full_authoritative_membership_ledger_20261119.jsonl.gz','wt',encoding='utf-8') as f:
    for x in sorted(members,key=lambda z:(z['date'],z['fid'])):
        f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')

record=OUT/'EXECUTION_RECORD_20261119.md'
record.write_text(f"""# Execution record — M8 frozen-eight boundary expansion\n\n- Started/finished: 2026-11-19 local run; research data archive as of source coverage cutoff (2026-11-04 for core).\n- Repository input commit: `eb61fbe428ce9f341c1aea07a447be7c1ad523f4` (workspace/origin main at start).\n- Frozen membership FIDs: {len(members)}; manifest SHA: `{data['frozen_foundation']['frozen_membership_sha256']}`.\n- Feature inventory: 39,101 core + 5,842 previously audited expansion rows; 44,943 unique FIDs.\n- Commands: `python3 -m py_compile research/m8/m8_frozen_eight_boundary_expansion_20261119.py`; `python3 research/m8/m8_frozen_eight_boundary_expansion_20261119.py`; `python3 research/m8/verify_m8_frozen_eight_boundary_20261119.py`; `python3 research/m8/build_m8_frozen_eight_boundary_report_20261119.py`.\n- Reproduction outcome: 68,060 candidate selection rows across 11,357 unique FIDs; independent raw Crown response audit verified all 11,357 FIDs and 68,060 selections with no quote, identity, FT or settlement mismatch.\n- Actual-receipt candidate replay: 0 rows because the existing HTTP receipt archive does not provide the compatible T1 path feature horizon. The 50 settled original-eight receipt signals are separately retained as retrospective archive replay.\n- Feature join limitation: 76 frozen members lacked the extracted row’s FT/unique-side detail. The independent raw-body audit recovered Crown T1 quote/FT and reproduced frozen PnL for all {audit['frozen_members_raw_quote_FT_and_PnL_reproduced_n']}/{len(members)} members; {audit['frozen_member_n']-audit['frozen_member_unique_original_side_n']} have side ambiguity because both side cashflows match the frozen outcome. No side was guessed.\n- Historical source-event replay is not actual placement, Telegram dispatch, nor independent prospective validation.\n- Production models, M9, Telegram, ledger, settlement, collection workflows and rules were not modified by this study.\n""",encoding='utf-8')
outputs=[p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS_20261119.txt']+[report,
    ROOT/'research/m8/m8_frozen_eight_boundary_expansion_20261119.py',
    ROOT/'research/m8/verify_m8_frozen_eight_boundary_20261119.py',
    ROOT/'research/m8/build_m8_frozen_eight_boundary_report_20261119.py']
with (OUT/'SHA256SUMS_20261119.txt').open('w') as f:
    for p in sorted(outputs):f.write(f"{sha(p)}  {p.relative_to(ROOT)}\n")
print(json.dumps({'report':str(report),'sha_manifest':str(OUT/'SHA256SUMS_20261119.txt'),
    'archive_prior_hits':len(archive_selected),'archive_overlap_frozen':sum(archive_overlap.values()),
    'raw_audit':audit,'q95_rows':len(q95)},ensure_ascii=False,indent=2))
