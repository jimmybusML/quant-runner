#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
D=ROOT/'research/m8/crown_market_microstructure_20261120'
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 r=json.load((D/'results_20261120.json').open());raw=json.load((D/'raw_crown_settlement_audit_20261120.json').open());receipt=json.load((D/'receipt_overlap_audit_20261120.json').open())
 labels={
 'A':'实力变化与 Crown 定价滞后', 'B':'实力层级与 Crown 合约非对称定价',
 'C':'原八组盈利机制的路径迁移', 'D':'自由探索：线变动与水位补偿交互'}
 bodies={
 'A':'''既有实力变化方向包括 Crown 之外的信息变化与市场变化之间的时滞。历史路径可观察 Crown 报价 source-event 顺序，却没有独立实力冲击的首次公开时间/接收时刻，也没有每条报价的 HTTP 到达时刻，因此不能建立“实力先变、Crown 后反应”的先后证据。用同一 Crown 低价边作为可执行 AH 价格控制，八组外 21,455 场为 -528.905U；方向与纯市场基准完全相同。过去已执行的强度 shock/价格路径实验（见交接与 bold-breakthrough 报告）也未证明稳定价格滞后。本轮没有重复搜索新闻或参数阈值，结论是数据时序和独立冲击来源不足，现有收益代理不支持盈利。''',
 'B':'''按比赛前 Crown AH 线绝对值固定分为接近均势(<0.5)、中间盘(0.5–<1.5)和深盘(≥1.5)，不使用事后排名。低价边同场收益依次为 9,027 场/-217.600U/-2.411%，10,205场/-249.185U/-2.442%，2,223场/-62.120U/-2.794%；反向边三个区间也全部亏损。完整非线性“相邻盘口阶梯”无法复建：原始列表是单一合约随时间的异步更新，不是同时多盘口；全路径共有174,253次线变化。现有测试只支持按合约深度描述实际收益，未发现任何固定实力差层级具备正净利润。''',
 'C':'''冻结八组成员、规则及结算全保留。八组外完整测试池与冻结成员按 FID 交集为0。市场低价边在不同事件路径形态均未显示可迁移机制：never_changed -466.030U/18,532，one_way -51.170U/1,581，oscillating -8.400U/128，reverted -3.305U/1,214。仅30场的 weaken_weaken 描述分组为 +4.815U，来自全路径后验分类，未事前定义为候选、无跨期选择验证、无实收验证，保留为失败/不可用分支，不据此挑选交易。按完整预设路径反转淡化策略为21,455场/-601.300U；与可桥接同期原八组合并为27,884场/-380.385U，候选贡献仍负。''',
 'D':'''独立假说：AH线调整时，双方水位补偿不对称，可能留下价格方向信息。固定机制用狗方相对热门方的水位变化符号选择一方，不按测试盈利搜阈值；八组外21,455场净-488.720U、ROI -2.278%、MDD 552.610U，年度为-135.885/-241.655/-111.180U。比固定低价边少亏40.185U，但全年负，不能抵消Crown成本。该实验使用当前归档完整路径的终态变量，缺逐场HTTP收件时刻，不能声称是真实赛前可执行规则或增加了已验证订单。相同方向与原八组合并后27,884场/-267.805U。'''}
 for k,title in labels.items():
  method={'A':'A_favorite_line_steam','B':'market_favorite','C':'D_late_stable_reversal_fade','D':'C_line_water_elasticity'}[k]
  m=r['methods'][method]
  text=f"# {k}｜{title}\n\n日期：2026-11-20。研究结果，非生产策略。\n\n{bodies[k]}\n\n## 复算成绩\n\n- 年度净U："+ ' / '.join(f"{y} {v['net_u']}U ({v['roi_pct']}%)" for y,v in r['by_year'][method].items())+f"\n- 全期：{m['n']}场，0场未结算，{m['net_u']}U，ROI {m['roi_pct']}%，MDD {m['mdd_u']}U，平均赔率 {m['average_odds']}。五态（全赢/半赢/走水/半输/全输）：{m['settlements'].get('full_win',0)}/{m['settlements'].get('half_win',0)}/{m['settlements'].get('push',0)}/{m['settlements'].get('half_loss',0)}/{m['settlements'].get('full_loss',0)}。\n- 历史平均周单量：{m['weekly_mean_n']}；平均每活跃ISO周净U：{m['weekly_mean_net_u']}。\n- 与冻结八组交集：0 FID；唯一新增：{m['n']} FID。候选与其他方法共享同一测试FID全集，不得将方法间收益相加。\n- ISO周/联赛/五态详细账：`results_20261120.json`；逐场账：`per_fixture_event_replay_20261120.jsonl.gz`。\n- raw Crown独立复核覆盖 {raw['raw_verified_unique_fids']}/{raw['unique_fids']} 个FID；剩余原始响应缺失，不能宣称全样本raw复核。\n- 真实赛前HTTP收据与可连接FT/微结构库存交集：{receipt['receipt_fids_with_microstructure_and_ft']}；真实收据模型回放0场。\n"
  (D/f'M8_{k}_DIRECTION_REPORT_20261120.md').write_text(text)
 # report raw audit truth in machine result
 r['independent_raw_audit']={k:raw[k] for k in ('ledger_rows','unique_fids','raw_verified_rows','raw_verified_unique_fids','failures','all_pass')}
 r['verified_receipt_overlap']={k:receipt[k] for k in ('verified_receipt_snapshot_rows','receipt_unique_fids','receipt_fids_with_microstructure_and_ft','valid_pre_kickoff_receipts_with_joined_features_ft')}
 (D/'results_20261120.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 # File-level SHA manifest, excluding itself so it is reproducible.
 files=sorted(p for p in D.iterdir() if p.is_file() and p.name!='SHA256SUMS_20261120.txt')
 input_files=[WORK/'m8_late_full_path_water_features_20261114.jsonl',WORK/'m8_independent_score_strength_20261114.jsonl',WORK/'m8_foundation_20261115/historical_membership.jsonl',ROOT/'research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl',ROOT/'PROJECT_HANDOFF.md']
 manifest=[f'{sha(p)}  OUTPUT::{p.name}\n' for p in files]
 manifest += [f'{sha(p)}  INPUT::{p}\n' for p in input_files]
 (D/'SHA256SUMS_20261120.txt').write_text(''.join(manifest))
 # Execution record includes actual executable commands and evidence coverage.
 (D/'EXECUTION_RECORD_20261120.md').write_text(f'''# 执行记录\n\n- 主研究：`python3 research/m8/crown_market_microstructure_20261120/m8_crown_microstructure_20261120.py`，完成；21,455八组外唯一 FID。\n- 原始 Crown/FT/五态结算独立校验：`python3 research/m8/crown_market_microstructure_20261120/verify_crown_microstructure_raw_20261120.py`，完成；{raw['raw_verified_unique_fids']}/{raw['unique_fids']} FID raw 覆盖、{raw['raw_verified_rows']}行净U和结算标签复算匹配，另有{raw['failures'].get('raw_body_missing',0)}个方法行因原始JSON缺失未能核验；因此全池 raw audit 未通过覆盖验收。\n- 实收对齐：`python3 research/m8/crown_market_microstructure_20261120/audit_receipts_overlap_20261120.py`，561实收快照/176FID，精确交集0，回放0场。\n- 结果包括全年度、ISO周、联赛、盘深及五态结算；所有方法同一FID集合，候选之间100%重叠。\n- 本轮只执行研究模拟；0正式 Telegram 订单、0正式账本回写、0生产工作流/采集变更。\n- 输入、脚本、报告、逐场结果和审计文件SHA见 `SHA256SUMS_20261120.txt`。\n''')
if __name__=='__main__':main()
