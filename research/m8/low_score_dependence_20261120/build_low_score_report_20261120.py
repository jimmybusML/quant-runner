#!/usr/bin/env python3
"""Add frozen-eight combined accounting and render the research report."""
import collections,datetime as dt,gzip,json
from pathlib import Path
import math
HERE=Path(__file__).resolve().parent
S=HERE/'m8_low_score_dependence_summary_20261120.json'; V=HERE/'independent_verification_20261120.json'
FROZEN=Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
def read(p):return [json.loads(x) for x in open(p,encoding='utf-8') if x.strip()]
def metric(rows):
 n=len(rows);u=sum(float(x['u']) for x in rows);daily=collections.defaultdict(float);years=collections.defaultdict(lambda:[0,0.]);weeks=collections.defaultdict(lambda:[0,0.])
 for x in rows:daily[x['date']]+=float(x['u']);years[int(x['year'])][0]+=1;years[int(x['year'])][1]+=float(x['u']);weeks[x['week']][0]+=1;weeks[x['week']][1]+=float(x['u'])
 run=peak=mdd=0.
 for day,v in sorted(daily.items()):run+=v;peak=max(peak,run);mdd=max(mdd,peak-run)
 if rows:
  lo=dt.date.fromisoformat(min(x['date'] for x in rows));hi=dt.date.fromisoformat(max(x['date'] for x in rows));lo=lo-dt.timedelta(days=lo.weekday());hi=hi-dt.timedelta(days=hi.weekday());nw=(hi-lo).days//7+1
 else:nw=0
 return {'orders':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'mdd_u':round(mdd,6),'calendar_iso_weeks':nw,'orders_per_calendar_week':round(n/nw,6) if nw else 0.,'by_year':{str(y):{'orders':n0,'net_u':round(u0,6),'roi_pct':round(100*u0/n0,6) if n0 else None} for y,(n0,u0) in sorted(years.items())},'by_iso_week':{w:{'orders':n0,'net_u':round(u0,6)} for w,(n0,u0) in sorted(weeks.items())}}
def main():
 s=json.loads(S.read_text());v=json.loads(V.read_text());assert v['pass']
 frozen_rows=read(FROZEN);pnl={str(x['fid']):x for x in frozen_rows}
 ledger=[json.loads(x) for x in gzip.open(HERE/'m8_low_score_dependence_orders_20261120.jsonl.gz','rt',encoding='utf-8')]
 state_names=('full_loss','half_loss','push','half_win','full_win')
 probability_quality={}
 for method in s['models']:
  rr=[x for x in ledger if x['method']==method]
  def quality(z):
   n=len(z);nll=brier=0.
   for x in z:
    p=[max(1e-15,float(x['predicted_state_probs'][q])) for q in state_names];y=state_names.index(x['state']);nll-=math.log(p[y]);brier+=sum((p[i]-(1. if i==y else 0.))**2 for i in range(5))
   return {'n':n,'nll':round(nll/n,8) if n else None,'multiclass_brier_sum':round(brier/n,8) if n else None}
  probability_quality[method]={'all_test':quality(rr),'by_year':{str(y):quality([x for x in rr if int(x['year'])==y]) for y in (2024,2025,2026)},'outside_eight':quality([x for x in rr if not x['frozen']])}
 combined={}
 for method in s['models']:
  rows=[x for x in ledger if x['method']==method]
  target_ids={str(x['fid']) for x in rows}
  inc=[{'date':x['date'],'year':int(x['year']),'week':x['week'],'u':float(x['net_u']),'league':x['league']} for x in rows if not x['frozen']]
  same=[]
  for x in rows:
   fid=str(x['fid'])
   if x['frozen']:
    z=pnl[fid];same.append({'date':x['date'],'year':int(x['year']),'week':x['week'],'u':float(z['pnl']),'league':x['league']})
  all_frozen=[{'date':x['date'],'year':int(x['year']),'week':dt.date.fromisoformat(x['date']).isocalendar().year.__str__()+'-W'+f"{dt.date.fromisoformat(x['date']).isocalendar().week:02d}",'u':float(x['pnl']),'league':str(x['league'])} for x in frozen_rows]
  combined[method]={'frozen_eight_same_test_fids':metric(same),'candidate_incremental':metric(inc),'merged_same_test_fids':metric(same+inc),'full_frozen_eight_plus_candidate':metric(all_frozen+inc),'frozen_overlap_fids':len(target_ids & set(pnl)),'candidate_overlap_fids':len({x['fid'] for x in rows if not x['frozen']} & set(pnl))}
 s['merged_with_frozen_eight']=combined;s['probability_quality']=probability_quality;S.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
 lines=['# M8 低比分依赖信息与 Crown AH 赛前结算概率研究','',
 '> 探索性历史回放；不属于真实实收或正式交易。冻结原八组、生产链、Telegram 和正式账本均未修改。测试年度曾被此前 M8 研究观察过，因此本轮是按时间前推的研究复核，不是盲态新样本。','',
 '## 研究问题与方法','',
 '固定已有赛前独立 Poisson 攻防强度后，检验先前比赛中低比分相关性是否能为 Crown AH 五态结算概率提供增量信息。与此前只用 pooled Dixon–Coles 的研究不同，本轮比较 pooled、联赛、球队收缩估计；与球队动态 Elo、连续净胜球均值模型不同，模型目标直接为实际 Crown AH 合同结算状态。',
 '预测状态为全输、半输、走水、半赢、全赢。使用 Crown AH 线、无水隐含主队概率、overround；依次加入独立 Poisson 状态概率、Dixon–Coles pooled/league/team 依赖修正。DC 参数由此前比分在独立 Poisson 下的似然得分与 Fisher 信息估计；球队项以20场等价先验向联赛参数收缩。仅使用目标 UTC 日期至少两天前的比赛；目标年模型只用此前北京时间年度数据训练，训练标准化只拟合训练集，softmax 固定 L2=1。未按测试结果搜索参数。','',
 '每场按模型预测的主、客方净收益择较高者；另做独立的正预测净 EV 才下单、否则不下注的研究诊断。两者均是研究决策方案，不是 Gate。四分之一盘口拆为相邻半盘分别结算。',
 '## 数据覆盖','',
 f"- 唯一研究库存：{s['scope']['target_unique_fids']:,} 场；可生成概率特征：{s['scope']['scored']:,} 场。北京年度分布：{s['scope']['year_counts']}。",
 f"- 2024–2026测试集：原49联赛分别为 {s['scope']['test_by_segment_year']['original49']}；新增完整路径的13个联赛分别为 {s['scope']['test_by_segment_year']['additional15']}。新增15名义范围中只有13个联赛有完整 T6/T3/T1 路径；其赛前比分强度由既有 TotalCorner 赛程 FT 前推生成，13联赛共 {s['scope']['additional15_forecast_coverage']['history_fixtures']:,} 场历史，UTC两日 embargo。",
 f"- M5 2026档案 {s['scope']['m5_rows']:,} 行；其中 {s['scope']['m5_rows_without_score_mapping']} 两个 FID 无比分模型映射，被排除在概率评估外。M5 HTTP 响应晚于历史开球，不是实际赛前收据。",
 f"- 冻结八组 {s['scope']['frozen_eight_fids']:,} FID，SHA256 `{s['scope']['frozen_sha256']}`。全部测试目标 {s['scope']['target_unique_fids']:,} FID 唯一；新增候选按冻结名单剔除。",'',
 '## 八组外唯一新增 AH 结果','',
 '| 方案 | 唯一新增场次 | 净U | ROI | MDD U | 周均新增 | 2024 U | 2025 U | 2026 U |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for name,x in s['models'].items():
  m=x['unique_outside_frozen_eight']; y=m['by_year'];lines.append(f"| {name} | {m['orders']:,} | {m['net_u']:+.3f} | {m['roi_pct']:+.3f}% | {m['mdd_u']:.3f} | {m['orders_per_calendar_week']:.2f} | {y.get('2024',{}).get('net_u',0):+.3f} | {y.get('2025',{}).get('net_u',0):+.3f} | {y.get('2026',{}).get('net_u',0):+.3f} |")
 lines+=['','每个方案的新增 FID 均为24,919（2024–2026），候选池交集相同，不能把模型版本相加。所有方案逐年均为负净U。具体分段、联赛及每个 ISO 周净值保存在汇总 JSON。','',
 '### 新增联赛分段（逐年）','',
 '| 方案 | 范围 | 2024 n/U | 2025 n/U | 2026 n/U |',
 '|---|---|---:|---:|---:|']
 for name,x in s['models'].items():
  for seg,sm in x['incremental_by_segment'].items():
   y=sm['by_year'];lines.append(f"| {name} | {seg} | {y.get('2024',{}).get('orders',0)} / {y.get('2024',{}).get('net_u',0):+.3f} | {y.get('2025',{}).get('orders',0)} / {y.get('2025',{}).get('net_u',0):+.3f} | {y.get('2026',{}).get('orders',0)} / {y.get('2026',{}).get('net_u',0):+.3f} |")
 lines+=['',
 '## 允许不下注的 EV 诊断','',
 '| 方案 | 新增下注 | 净U | ROI | MDD U | 2024 / 2025 / 2026净U |',
 '|---|---:|---:|---:|---:|---|']
 for name,x in s['models'].items():
  m=x['ev_positive_no_bet_diagnostic'];y=m['by_year'];lines.append(f"| {name} | {m['orders']:,} | {m['net_u']:+.3f} | {m['roi_pct']:+.3f}% | {m['mdd_u']:.3f} | {y.get('2024',{}).get('net_u',0):+.3f} / {y.get('2025',{}).get('net_u',0):+.3f} / {y.get('2026',{}).get('net_u',0):+.3f} |")
 lines+=['','正预测 EV 子集也全部亏损。它减少了下注数，但没有找到覆盖 Crown 水差后的利润来源。','',
 '## 与冻结原八组合并','',
 '| 方案 | 冻结八组同测试 FID | 同测试合并净U | 同测试合并 ROI | 全部原八组 + 候选净U | 候选新增净U |',
 '|---|---:|---:|---:|---:|---:|']
 for name,x in s['merged_with_frozen_eight'].items():
  a=x['frozen_eight_same_test_fids'];b=x['merged_same_test_fids'];c=x['full_frozen_eight_plus_candidate'];d=x['candidate_incremental'];lines.append(f"| {name} | {a['orders']:,} / {a['net_u']:+.3f}U | {b['net_u']:+.3f}U | {b['roi_pct']:+.3f}% | {c['net_u']:+.3f}U | {d['net_u']:+.3f}U |")
 lines+=['','原八组与候选按唯一 FID 去重；合并后的正值不能掩盖候选自身均亏。每种方案均独立合并，没有相加不同模型。','',
 '## 概率质量诊断','',
 '| 方案 | 2024 NLL / Brier | 2025 NLL / Brier | 2026 NLL / Brier |',
 '|---|---:|---:|---:|']
 for name,x in probability_quality.items():
  y=x['by_year'];lines.append(f"| {name} | {y['2024']['nll']:.6f} / {y['2024']['multiclass_brier_sum']:.6f} | {y['2025']['nll']:.6f} / {y['2025']['multiclass_brier_sum']:.6f} | {y['2026']['nll']:.6f} / {y['2026']['multiclass_brier_sum']:.6f} |")
 lines+=['','NLL 和 multiclass Brier 越低表示状态概率质量较好；概率评分改善并不替代实际 Crown AH 收益。','',
 '## 解释与结论','',
 '1. 低比分依赖修正没有增加 AH 净利润。团队级收缩 DC 的全池表现比 Crown+独立 Poisson 更差；联赛级、pooled 也没有改善。',
 '2. 允许不下注后，五种方案仍为负；“模型预测净 EV>0”不能抵消估计误差和 Crown 价格成本。',
 '3. 原49之外13个新增联赛中，四种模型均亏损；新增15联赛2026仅74个路径 FID，样本太少且是部分年度。没有跨年度盈利迹象。',
 '4. 本轮无实际赛前 HTTP Crown receipt 作为策略验证；全部为历史源事件/缓存回放。没有正式 Telegram 派单或账本写入。',
 '5. 该结果是探索性前推复核：虽然训练严格早于测试年，2024–2026目标数据已在既往研究中被观察，不能当作未见前瞻检验。未生成正式交易规则或候选组。','',
 '## 独立核验及复现','',
 f"独立校验器核验 {v['independent_ledger_rows_checked']:,} 条（5个方案×31,203测试FID），逐笔对照原始研究输入的 Crown 盘口/赔率、FT、重新拆腿结算、冻结成员标记及 EV 诊断；错误数 {sum(v['errors'].values())}，通过 `{v['pass']}`。这是输入档案对账及结算重算，不等于缺失 raw response 的全量原始 HTTP 内容审计。",
 '', '复跑命令：', '', '```bash', 'python3 research/m8/low_score_dependence_20261120/m8_low_score_dependence_20261120.py', 'python3 research/m8/low_score_dependence_20261120/verify_m8_low_score_dependence_20261120.py', 'python3 research/m8/low_score_dependence_20261120/build_low_score_report_20261120.py', '```','',
 '机器可读逐场账本包含每个方法的 Crown 线/两边赔率、FT、预测五态概率、方向、五态结算、净U、训练年份、rho、团队历史覆盖、来源类别及冻结重叠。关键输入 SHA256 已写入汇总 JSON。','']
 (HERE/'M8_LOW_SCORE_DEPENDENCE_RESEARCH_20261120.md').write_text('\n'.join(lines),encoding='utf-8')
 print('wrote report; independent verifier:',v['pass'])
if __name__=='__main__':main()
