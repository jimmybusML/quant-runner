#!/usr/bin/env python3
"""Build report and SHA manifests from the exact frozen-rule ledgers."""
import collections,datetime as dt,gzip,hashlib,json,pathlib,statistics,glob,os
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[3]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work');DATA=pathlib.Path('/Users/mac/QuantAsiaDesk/data')
SUMMARY=json.loads((HERE/'exact_rule_cross_league_summary.json').read_text())
COVERAGE=json.loads((HERE/'exact_rule_cross_league_coverage.json').read_text())
ORDERS=[json.loads(x) for x in gzip.open(HERE/'exact_rule_cross_league_orders.jsonl.gz','rt',encoding='utf-8')]
ALL=[json.loads(x) for x in gzip.open(HERE/'exact_rule_cross_league_all_complete_paths.jsonl.gz','rt',encoding='utf-8')]
def read(p):return [json.loads(x) for x in open(p) if x.strip()]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def fnum(v,n=3):return '—' if v is None else f'{v:.{n}f}'
def metric_rows():
 out=[]
 for g,d in SUMMARY['by_group'].items():
  a=d['all'];raw=SUMMARY['raw_group_hits_before_priority'][g]
  out.append((g,a['orders'],a['net_u'],a['roi_pct'],a['mdd_u'],a['weekly_avg'],a['average_decimal_odds'],raw['orders'],raw['net_u']))
 return out
def league_names():
 names={}
 for r in read(WORK/'crown-drop-expanded-62/schedule_universe.jsonl'):
  lid=str(r['league_id'])
  if r.get('source_league'):names[lid]=r['source_league']
 for r in ALL:
  if r.get('league_name'):names[r['league']]=r['league_name']
 for r in ORDERS:
  if r.get('league_name'):names[r['league']]=r['league_name']
 return names
def build_md():
 s=SUMMARY;names=league_names();lines=[]
 delta=json.loads((HERE/'snapshot_delta_audit_20261122.json').read_text()) if (HERE/'snapshot_delta_audit_20261122.json').exists() else None
 coverage=s['coverage'];inc=s['unique_incremental'];obs_weeks=inc['observation_iso_weeks']
 year_spans={}
 for y in range(2019,2027):
  ds=[x['date'] for x in ALL if x['year']==y]
  year_spans[y]=(min(ds),max(ds)) if ds else ('—','—')
 focus=[]
 for y in (2024,2025,2026):
  a=s['incremental_by_year'][str(y)];c=s['combined_by_year'][str(y)]
  focus.append(f"{y} {a['orders']}单/{a['net_u']:+.3f}U/{fnum(a['roi_pct'])}%（合并净值{c['net_u']:+.3f}U）")
 positive_groups=[g for g,v in s['by_group'].items() if v['all']['net_u']>0]
 negative_groups=[g for g,v in s['by_group'].items() if v['all']['net_u']<0]
 lines += ['# M8 原八组精确规则跨联赛回测（原 49 联赛之外）','',
  '> 历史研究回放，不是 Crown 实际赛前收据，不是正式 Telegram 订单。原八组与生产规则均未改动。全部时间按中国时区统计，底层 Crown source-event 以 UTC 保存。','',
  '## 样本与覆盖','',
  f"- 目标：扩展赛程 64 个联赛 ID 中，排除冻结原 49 后的 15 个联赛。原扩展清单有 18,374 个目标 FID；与原始 TotalCorner 赛程页按 FID 对账，交集 18,373、原清单独有 1、赛程页独有 2,722，去重后为 **{s['schedule_universe']:,} 场**。交集 18,373 场的联赛、球队、FT 和开赛时刻均无冲突。", 
  f"- 原 49 组冻结基准：{s['frozen_baseline']['n']:,} 个 FID，{s['frozen_baseline']['U']:+.3f}U，ROI {s['frozen_baseline']['ROI_pct']:.3f}%。冻结成员 SHA 见 SHA 清单。",
  f"- 固定只读 SQLite 在线备份快照中有 movement 报价的赛事 {coverage['quote_saved_fids']:,} 场，其中有开赛前报价 {coverage['valid_pregame_quote_fids']:,} 场；完整 T6/T3/T1 路径 **{coverage['complete_T6_T3_T1']:,} 场**，G 所需赛前比分强度可用 {coverage['complete_paths_with_G_score_rates']:,} 场。触发候选经原优先级去重后为 **{inc['orders']:,} 个新增 FID**。",
  f"- 无法复算原因：{s['missing_reasons'].get('movement_capture_no_quotes',0):,} 场有 movement capture 但未保存 Crown AH 报价；{s['missing_reasons'].get('no_movement_capture',0):,} 场无 movement capture 记录；{s['missing_reasons'].get('missing_T6',0):,} 场缺 T6；{s['missing_reasons'].get('no_valid_pregame_quote',0):,} 场没有有效赛前报价。上述均是数据缺失，不计为策略未命中。",
  f"- 2026 可完整复算路径覆盖 {year_spans[2026][0]} 至 {year_spans[2026][1]}；属于部分年度，不可视为全年成绩。",
  '', '### 按年度数据覆盖','',
  '| 年 | 赛程 FID | 完整 T6/T3/T1 | 完整路径无信号 | 完整路径有信号 | 有赛前报价但缺 T6 | 无赛前报价 | 有采集无报价 | 无采集 | 完整路径日期范围 |',
  '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
 covrows=[json.loads(x) for x in gzip.open(HERE/'exact_rule_cross_league_coverage_by_fid.jsonl.gz','rt',encoding='utf-8')]
 for y in range(2019,2027):
  z=[x for x in covrows if x['year']==y];c=collections.Counter(x['status'] for x in z);dates=[x['date'] for x in z if x['status'].startswith('complete_path')]
  lines.append(f"| {y} | {len(z)} | {c['complete_path_no_signal']+c['complete_path_with_signal']} | {c['complete_path_no_signal']} | {c['complete_path_with_signal']} | {c['missing_T6']} | {c['no_valid_pregame_quote']} | {c['movement_capture_no_quotes']} | {c['no_movement_capture']} | {min(dates) if dates else '—'} – {max(dates) if dates else '—'} |")
 lines += ['', '## 各组逐笔收益（按冻结优先级归属）','',
  '原规则优先级为 base → A → B → C → D → E → F → G。若多个规则同时触发，仅按该顺序把唯一 FID 归属一组；另保留原始组命中账本与交集。ROI = 净 U / 唯一订单数。回撤按中国日期逐日聚合。','',
  f"base/A–F 使用原 6/3/1 触发及方向。G 使用原独立比分 Poisson 强度结构（学习率 0.025、同一衰减/更新式）与 AH 期望收益方向：只用该目标新联赛在目标日之前至少两天结束的 FT 逐步训练；{coverage['complete_paths_with_G_score_rates']:,} 个完整路径均有比分强度值，无缺失替代；没有用 M9 替代，也没有对本次目标年度调参。",'',
  '| 组 | 新增唯一单 | 净 U | ROI | MDD U | 周均单* | 平均赔率 | 原始触发（未优先去重） | 原始触发净 U |',
  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for g,n,u,roi,mdd,w,odds,rn,ru in metric_rows():lines.append(f'| {g} | {n} | {u:+.3f} | {roi:+.3f}% | {mdd:.3f} | {w:.3f} | {odds:.3f} | {rn} | {ru:+.3f} |')
 inc=s['unique_incremental'];lines.append(f"| **合计去重** | **{inc['orders']}** | **{inc['net_u']:+.3f}** | **{inc['roi_pct']:+.3f}%** | **{inc['mdd_u']:.3f}** | **{inc['weekly_avg']:.3f}** | **{inc['average_decimal_odds']:.3f}** | **{s['overlap']['raw_hit_fids']} FID** | — |")
 lines += ['', f"*“周均单”以完整可判定样本从首个到末个 ISO 周（共 {obs_weeks} 周）为分母；其中 {inc['active_iso_weeks']} 周有新增订单，活跃周均 {inc['active_week_avg']:.3f} 单。逐年使用该年度完整路径覆盖周数。",'',
  f"原始命中交叉：{s['overlap']['fids_with_multiple_group_hits']} 个 FID 同时触发多组。交叉对数："+', '.join(f'{k} {v}' for k,v in sorted(s['overlap']['overlapping_group_pairs'].items()))+f"。优先级去重后组别订单数总和等于 {inc['orders']:,}；不将原始重叠收益重复相加。",'',
  '## 逐年新增及合并表现','',
  '| 年 | 新增唯一单 | 新增净 U | 新增 ROI | 新增 MDD U | 新增周均单 | 原八组单 | 原八组 U | 合并单 | 合并净 U | 合并 ROI | 合并 MDD U |',
  '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 frozen=read(WORK/'m8_foundation_20261115/historical_membership.jsonl')
 for y in range(2019,2027):
  a=s['incremental_by_year'][str(y)];c=s['combined_by_year'][str(y)];base=[x for x in frozen if int(x['year'])==y]
  lines.append(f"| {y} | {a['orders']} | {a['net_u']:+.3f} | {fnum(a['roi_pct'])}% | {a['mdd_u']:.3f} | {a['weekly_avg']:.3f} | {len(base)} | {sum(x['pnl'] for x in base):+.3f} | {c['orders']} | {c['net_u']:+.3f} | {c['roi_pct']:+.3f}% | {c['mdd_u']:.3f} |")
 c=s['combined_with_frozen_baseline']
 lines += ['', f"**全期合并：** {c['orders']:,} 单、{c['net_u']:+.3f}U、ROI {c['roi_pct']:.3f}%、MDD {c['mdd_u']:.3f}U；相对冻结八组增加 {c['incremental_orders']:,} 个唯一 FID、净利润 **{c['increment_vs_frozen_u']:+.3f}U**。原八组总数和规则未改。", '',
  '2024–2026重点：'+'；'.join(focus)+'。各年新增成绩按目标年完整路径覆盖计算。','',
  '## 各组年度成绩（新增唯一订单）','',
  '| 组 | 2019 n/U/ROI | 2020 n/U/ROI | 2021 n/U/ROI | 2022 n/U/ROI | 2023 n/U/ROI | 2024 n/U/ROI | 2025 n/U/ROI | 2026 n/U/ROI |',
  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for g,v in s['by_group'].items():
  vals=[]
  for y in range(2019,2027):
   x=v['by_year'][str(y)];vals.append(f"{x['orders']} / {x['net_u']:+.2f} / {fnum(x['roi_pct'])}%")
  lines.append('| '+g+' | '+' | '.join(vals)+' |')
 lines += ['', '## 联赛分布','',
  '| 联赛 ID | 联赛 | 赛程 | 完整路径 | 新增订单 | 净 U | ROI |',
  '|---:|---|---:|---:|---:|---:|---:|']
 order_by=collections.defaultdict(list)
 for x in ORDERS:order_by[x['league']].append(x)
 for lid in sorted({x['league'] for x in covrows},key=int):
  cov=[x for x in covrows if x['league']==lid];os=order_by[lid];n=len(os);u=sum(x['net_u'] for x in os);roi=u/n*100 if n else None
  nm=names.get(lid) or next((x.get('league_name') for x in ALL if x['league']==lid and x.get('league_name')),'unknown')
  lines.append(f"| {lid} | {nm} | {len(cov)} | {sum(x['status'].startswith('complete_path') for x in cov)} | {n} | {u:+.3f} | {fnum(roi)}% |")
 league_totals=[]
 for lid in sorted({x['league'] for x in covrows},key=int):
  z=order_by[lid];league_totals.append(sum(x['net_u'] for x in z))
 lines.append('')
 lines.append(f"15 个目标联赛中，{sum(v>0 for v in league_totals)} 个联赛历史新增净值为正、{sum(v<0 for v in league_totals)} 个为负、{sum(v==0 for v in league_totals)} 个没有新增订单。这里的联赛结果为研究诊断，不作为过滤条件。")
 # actual HTTP receipt block
 rec=json.loads((HERE/'actual_receipt_exact_rule_audit_20261122.json').read_text())
 lines += ['', '## 真实赛前 Crown 收据','',
  f"复核的 forward-shadow Crown 原始 HTTP 索引、MR1 实收档案、M8 实收档案及 SQLite live capture。15 个目标联赛在这些来源的有效 Crown 实收 FID 为 **{rec['unique_fids']}**，T1 前收到且可还原完整 T6/T3/T1 的为 **{rec['complete_T6_T3_T1_fids']}**，按精确规则得到真实收据订单 **{rec['exact_rule_receipt_orders']}**。因此本次 {inc['orders']:,} 单全部是历史 source-event 回放，不能称作实收验证或 Telegram 实战。", '',
  '## 结论','',
  f"原八组精确触发逻辑在15个新联赛完整路径上产生 {inc['orders']:,} 个新增唯一 FID，历史 Crown 报价结算净值 {inc['net_u']:+.3f}U（ROI {inc['roi_pct']:+.3f}%），合并冻结八组后 {c['orders']:,} 单、{c['net_u']:+.3f}U、ROI {c['roi_pct']:.3f}%。新增组合按组归属结果为正：{'、'.join(positive_groups)}；为负：{'、'.join(negative_groups)}。不同年度方向不一致，且没有新联赛真实赛前收据支持可执行性，不能证明稳定跨年度扩单盈利。",'',
  '本报告不新增 Gate、过滤、限额或上线规则；所有结果仅供研究。', '',
  '## 原始精确方向实现核对', '',
  '复核发现，2026-11-19 边界研究脚本的 `group_side(\'E\')` 与较早的完整路径提取器对 E 组方向处理不同：边界脚本只看 `p1-p0`，当端点概率相等时返回无方向；原完整路径提取器在 E 组中途概率同时上、下变动且端点净变化为零时，使用 `net or p0→p3 or p3→p1 or last_move` 的首个非零方向确定一侧。本研究采用原完整路径提取器方向实现（同原始库存恢复代码），不是新增方向规则。冻结 E 成员中161个可配对路径和 Crown 结算记录的方向全部吻合；另有106个成员缺少可同时核验的路径特征或报价结算记录。', '',
  '此次跨联赛逐场账本中52个优先级归属 E 的候选均为端点概率净变化为零，因此 E 方向依赖上述原提取器的中间路径回退方向。独立 Crown 原始报价/FT 结算审计逐场复核这些订单及其余候选。该说明用于解释历史实现来源差异，不重定义冻结组或生产规则。', '',
  '## 2026-11-22 复算记录', '',
  f"2026-11-22基于固定 SQLite 备份快照复算：赛事库存 {s['schedule_universe']:,} 场、完整路径 {coverage['complete_T6_T3_T1']:,} 条、新增订单 {inc['orders']:,} 笔、{inc['net_u']:+.3f}U。独立校验读取原始 Crown 响应 SHA、独立 TotalCorner FT/身份来源和同一快照；验证摘要见 `independent_settlement_verification_20261122.json`，快照 SHA256 为 `{s['inputs']['sqlite_sha256']}`。复核原八组 10,294 FID 与新增账本交集为0。当前真实赛前收据审计订单仍为 {rec['exact_rule_receipt_orders']}。"]
 if delta:
  q=delta['complete_paths'];o=delta['orders']
  lines += ['', '## 与上一已发布快照的变化', '',
   f"相较提交 `{delta['previous_commit']}`：完整路径由 {q['previous']:,} 增至 {q['current']:,}（新增 {q['new_fids']:,} 个 FID）；原有 {q['common_fids']:,} 路径特征没有变化。精确规则新增订单由 {o['previous']:,} 增至 {o['current']:,}，增加 {o['new_order_fids']:,} 单；原有 {o['common_order_fids']:,} 个订单的组别、方向、盘口合约及结算均无变化。新增恢复订单净值 {o['new_order_net_u']:+.3f}U，使总增量由 {o['previous_net_u']:+.3f}U 变为 {o['current_net_u']:+.3f}U。这个变化来自数据恢复覆盖，不是规则或参数调整。", '']
 (HERE/'EXACT_RULE_CROSS_LEAGUE_REPORT.md').write_text('\n'.join(lines).rstrip()+'\n')

def main():
 build_md()
 target_pages=[]
 for lid in SUMMARY['target_league_ids']:
  target_pages += glob.glob(f'/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules/{lid}/page-*.raw.json')
 target_set={str(x) for x in SUMMARY['target_league_ids']}
 target_pages += [p for p in glob.glob('/Users/mac/QuantAsiaDesk/research-work/m7/m7_future_schedule_refresh_daily_20261111/2026-*/raw/*.json') if pathlib.Path(p).name.split('-',1)[0] in target_set]
 external_inputs=[WORK/'crown-drop-expanded-62/schedule_universe.jsonl',WORK/'m8_foundation_20261115/historical_membership.jsonl',WORK/'m8_foundation_20261115/manifest.json',WORK/'m8_late_full_path_water_features_20261114.jsonl',WORK/'m8_extra_inventory_frozen_eight_20261115.jsonl',WORK/'m8_raw_capture_unindexed_frozen_replay_20261115.jsonl',WORK/'m8_independent_score_strength_20261114.jsonl',pathlib.Path(os.environ.get('M8_CROSS_LEAGUE_DB',str(DATA/'crown_quote_store/crown_quotes.sqlite3'))),DATA/'m5-crown-authorized/forward-shadow/crown-capture-index.jsonl',
  ROOT/'research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl',WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl',ROOT/'research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl',
  ROOT/'research/m8/m8_frozen_eight_earlier_window_replay_20261116.py',ROOT/'research/m8/m8_raw_capture_unindexed_frozen_replay_20261115.py',ROOT/'research/m8/m8_frozen_eight_boundary_expansion_20261119.py',HERE/'exact_rule_cross_league_20261120.py',HERE/'verify_exact_rule_cross_league_20261120.py',HERE/'actual_receipt_exact_rule_audit_20261120.py',HERE/'build_exact_rule_report_20261120.py']
 # Hash every cached schedule page actually read from target leagues.
 inputs={'direct_files':{str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in external_inputs if p.exists()},
  'target_schedule_pages':{str(pathlib.Path(p)):sha(p) for p in sorted(set(target_pages))},
  'target_schedule_page_count':len(set(target_pages)),
  'execution_scope':{'expanded_league_ids':64,'original49_ids':49,'outside_original49_ids':len(SUMMARY['target_league_ids']),'outside_ids':SUMMARY['target_league_ids']}}
 external_inputs.append(HERE/'compare_cross_league_snapshot_replays_20261122.py')
 inputs['direct_files'][str(HERE/'compare_cross_league_snapshot_replays_20261122.py')]={'sha256':sha(HERE/'compare_cross_league_snapshot_replays_20261122.py'),'bytes':(HERE/'compare_cross_league_snapshot_replays_20261122.py').stat().st_size}
 (HERE/'input_sha256_manifest_20261122.json').write_text(json.dumps(inputs,indent=2))
 outputs={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ('output_sha256_manifest_20261122.json','SHA256SUMS_20261122.txt')}
 (HERE/'output_sha256_manifest_20261122.json').write_text(json.dumps(outputs,indent=2))
 outputs_for_sums=dict(outputs);outputs_for_sums['output_sha256_manifest_20261122.json']=sha(HERE/'output_sha256_manifest_20261122.json')
 with open(HERE/'SHA256SUMS_20261122.txt','w') as f:
  for name,digest in sorted(outputs_for_sums.items()):f.write(f'{digest}  {name}\n')
 print(json.dumps({'report':str(HERE/'EXACT_RULE_CROSS_LEAGUE_REPORT.md'),'target_page_count':len(set(target_pages)),'outputs':outputs_for_sums},ensure_ascii=False))
if __name__=='__main__':main()
