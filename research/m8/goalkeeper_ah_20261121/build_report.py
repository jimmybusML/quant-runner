#!/usr/bin/env python3
"""Render the goalkeeper AH report from the reproducible run outputs."""
import json,pathlib

P=pathlib.Path(__file__).resolve().parent
S=json.loads((P/'goalkeeper_ah_summary_20261121.json').read_text())
A=json.loads((P/'goalkeeper_ah_independent_audit_20261121.json').read_text())
V=json.loads((P/'goalkeeper_ah_raw_verified_subset_20261121.json').read_text())
labels={'market_only':'Crown市场基准','keeper_only':'仅门将特征','market_plus_existing_GK_minutes':'Crown + 已有门将负荷控制','market_plus_keeper_continuity':'Crown + 门将连续性/防守历史','market_plus_all_goalkeeper':'Crown + 全部门将特征'}
fmt=lambda x: f"{x:,.3f}" if isinstance(x,(int,float)) else '—'
lines=['# M8 门将连续性与防守历史 AH 研究（2026-11-21）','',
'> 研究用途：历史研究回放。原八组、M1/MR1/M9、Telegram、正式账本、采集链均未改变。本文不提出生产规则。','',
'## 结论','',
'本研究检验球队主要门将身份稳定性、门将更替、门将/替补门将失球率及球队近期失球率能否在 Crown AH 之外提供独立盈利信息。结果为否：对 2024–2026 可用样本进行逐年扩展训练后，五种同样本选边方案在八组外都亏损。市场基准为 −44.690U；加入门将连续性特征后为 −101.470U，较市场基准再差 −56.780U；加入全部门将特征为 −97.830U。2026测试只到 5月24日。',
'',
'完整测试池八组外2,805场，周均22.44场；不是可盈利新增来源。逐场复核按唯一 FID；冻结八组与候选没有重叠计入。历史 Crown 原始响应仅3,493/3,520场可从SQLite、原始HTTP响应SHA、FID、AH线和双方赔率复核；其中八组外2,784场仍亏损。3,493条全部标为 historical 且 `prospective_observation=false`，原始响应收到时间均晚于报价源事件时间；真正 live receipt 中与本样本相交的 FID 为0，具备当时可用门将信息快照的场次也为0。','',
'## 研究与数据边界','',
'### 与既有研究的区别','',
'此前的球员负荷/轮换研究已测试一般球员分钟、整体轮换和门将分钟负荷。本次不重跑这些变量作为新主张，而检验门将**身份连续性与防守结果历史**：近365天主门将占比、近期门将切换率、近10场门将人数、主力与替补的GA/90差、球队GA/90、主门将近期出场间隔、主门将出场分钟、近5场与当前主门将重合次数、近5场GA/90。控制模型单独含先前已用的门将分钟变量。',
'',
'### 输入与时间可靠性','',
'特征来源为本地 Transfermarkt `appearances.csv.gz`、`games.csv.gz`、`game_lineups.csv.gz`。一场历史门将球队比赛必须同时满足：比赛有完场比分；该球会/比赛只有一名首发门将；同一球员有出场记录且 `player_club_id` 对应球队；门将出场不少于85分钟。所有球员按 player ID 与球队 ID 建立历史，不能根据当前效力队倒推。历史特征只使用严格早于目标行 `fixture_date_cutoff_utc`（目标日期前3日）的比赛日期。源记录没有可核验的首次发布/接收时间，因此只是一种保守事件日期回放，不能证明当时掌握这些信息。目标首发、目标赛果和目标比赛之后的 Crown 报价均未用作输入。',
'',
'Crown 输入来自已有特征档案的 T−12h 亚洲盘报价；T−12h按原 source-event 时间判断，所有结果是研究回放而非可执行的当时收盘价。训练目标为历史主队 AH 净收益减客队 AH 净收益，按扩展窗口逐年训练：每个测试年只用早于该年的比赛，Ridge alpha=100；标准化参数也仅从训练集估计。模型在同一候选比赛上预测两侧收益差并选择较高侧，仅作为比较诊断。AH四分之一盘拆成相邻半球线两腿平均结算。冻结成员标记只在预测完成后用于去重。',
'',
'输入覆盖：球员数据源含 appearances 1,894,350行/13字段、games 88,958行/23字段、game_lineups 3,179,016行/10字段；结构化记录含 player/game/club/date/minutes、完场比分和首发位置等字段。赛程身份复核读取本地M5 schedules 5,180个原始页面，整页SHA索引见 `schedule_source_sha256_20261121.json`。逐场特征档案共6,118条有可匹配本地赛程的 FID 且 provider 主客ID匹配；测试期3,520场中3,214场有对应赛程ID核对、306场缺少本地赛程页。测试期两队均有严格截止日前验证的门将历史记录：3,520/3,520。特征档案本身覆盖2024-01-02至2026-05-24，不能将结果称为完整2026年度表现。独立比分源缺失99场；原始 Crown报价与FT链通过3,493场核验，另27场在当前数据库未找到T−12h Crown事件。',
'',
'## 样本与冻结八组对照','',
f"测试目标池：{S['test_population']['all_test_rows_2024_2026']:,}场，其中原八组重叠 {S['test_population']['test_frozen_overlap']:,}场，八组外唯一 FID {S['test_population']['outside_frozen_unique_fids']:,}场；日期 {S['test_population']['first_date']} 至 {S['test_population']['last_date']}，125个日历周。五种方案的FID集合完全相同，任意两方法重叠3,520场。候选与冻结八组的FID交集在增量计算中为0。",
'',
'冻结八组同日期范围对照为5,884场、+166.220U、ROI +2.825%、MDD 58.165U。合并成绩如下；新增候选的独立收益仍单独展示，不用冻结组盈利掩盖亏损。','',
'| 研究方法 | 八组外新增场次 | 八组外净U | 八组外ROI | MDD U | 周均订单 | 与同期冻结组合并场次 | 合并净U | 合并ROI |',
'|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for m,label in labels.items():
 r=S['candidate_models'][m]['incremental_outside_frozen'];c=S['frozen_plus_candidate'][m]
 lines.append(f"| {label} | {r['n']:,} | {r['net_U']:.3f} | {r['ROI_pct']:.3f}% | {r['MDD_U']:.3f} | {r['orders_per_week']:.2f} | {c['n']:,} | {c['net_U']:.3f} | {c['ROI_pct']:.3f}% |")
lines+=['',
'基准新增池2,805场/125周，平均每周22.44场。合并后单量虽然增加，但每种候选均降低总净U：市场基准令同期冻结组合由+166.220U降至+121.530U；Crown+门将连续性后降至+64.750U。','',
'## 年度结果','',
'| 方法 | 年份 | 八组外场次 | 净U | ROI | MDD U | 周均单量* |',
'|---|---:|---:|---:|---:|---:|---:|']
for m,label in labels.items():
 for y,r in S['candidate_models'][m]['incremental_by_year'].items():
  lines.append(f"| {label} | {y}{'†' if y=='2026' else ''} | {r['n']:,} | {r['net_U']:.3f} | {r['ROI_pct']:.3f}% | {r['MDD_U']:.3f} | {r['orders_per_week']:.2f} |")
lines+=['', '* 年内周均为场次除以该年候选首尾日期覆盖的周数；2024/2025各52周，2026只覆盖21周。','', '† 2026数据仅至2026-05-24，不是全年。市场基准2026正收益 +10.015U，但门将独立模型均亏损；按数据边界和单一年份不得视为稳定机制。','',
'## 五态结算及跨年度表现','',
'| 方法 | 全赢 | 半赢 | 走水 | 半输 | 全输 |',
'|---|---:|---:|---:|---:|---:|']
for m,label in labels.items():
 c=S['candidate_models'][m]['incremental_outside_frozen']['settlement_classes']
 lines.append(f"| {label} | {c.get('full_win',0):,} | {c.get('half_win',0):,} | {c.get('push',0):,} | {c.get('half_loss',0):,} | {c.get('full_loss',0):,} |")
lines+=['',
'独立门将模型 keeper_only 在2024、2025、2026均亏损（−13.405U、−32.475U、−43.635U）；Crown+连续性模型三年也均亏损（−30.165U、−39.955U、−31.350U）；全部门将特征模型三年分别−32.175U、−48.380U、−17.275U。故跨年证据否定该方向可作为新增盈利来源。市场-only诊断2026年为正，但2024、2025亏损，且它不是新增的独立门将信息。',
'',
'## 真实 Crown 报价核验与可执行性','',
f"独立验证脚本重新读取 Crown SQLite、逐场原始响应文件、响应SHA、FID、Crown T−12h source-event报价、FT及冻结成员清单。结果：{A['checks']['independent_ah_settlements']:,}笔/五方法的AH结算独立复算全部一致；{A['checks']['Crown_T12_line_and_both_prices_match']:,}场Crown线与双方赔率一致；原始响应SHA/FID/FT和原始响应中的T−12h线水通过 {A['checks']['raw_Crown_T12_match']:,} 场；无问题项。99场缺少独立比分源，27场当前DB无T−12h报价。", 
'',
f"原始报价核验子集有 {V['raw_verified_total_fids']:,} 个FID，其中八组外 {V['raw_verified_outside_frozen_unique_fids']:,} 场、冻结成员 {V['raw_verified_frozen_overlap_fids']:,} 场。八组外可核验子集结果：",
'',
'| 方法 | 可核验新增场次 | 净U | ROI | MDD U |',
'|---|---:|---:|---:|---:|']
for m,label in labels.items():
 r=V['models'][m]['raw_Crown_and_FT_verified_incremental']
 lines.append(f"| {label} | {r['n']:,} | {r['net_U']:.3f} | {r['ROI_pct']:.3f}% | {r['MDD_U']:.3f} |")
lines+=['', '可核验子集逐年（该子集只按原始 Crown 响应通过情况缩减，未据收益改选比赛）：', '',
'| 方法 | 年份 | 场次 | 净U | ROI | MDD U |',
'|---|---:|---:|---:|---:|---:|']
for m,label in labels.items():
 for y,r in V['models'][m]['by_year'].items():
  lines.append(f"| {label} | {y}{'†' if y=='2026' else ''} | {r['n']:,} | {r['net_U']:.3f} | {r['ROI_pct']:.3f}% | {r['MDD_U']:.3f} |")
lines+=['',
'可核验子集的ISO周订单数及周净U完整保留在 `goalkeeper_ah_raw_verified_subset_20261121.json` 的 `weekly` 字段；全测试池周账本在 `goalkeeper_ah_summary_20261121.json` 的各模型 `weekly` 字段。',
'',
'可核验子集中 Crown市场基准−44.140U，Crown+连续性−102.225U，全部门将特征−96.675U。报价链仅证明历史报价和FT来自相同FID且内容可核查；不能证明当时收件或可成交。3,493条均为 `capture_mode=historical`、`prospective_observation=false`，响应收件时间晚于 source-event 时间。测试FID与 live capture 的交集为0。门将源亦无赛前归档时戳，故真正赛前特征与真实赛前 Crown 收据的可核验交集为0。',
'',
'## 联赛拆分','',
'下表列出所有模型的八组外净U（各行样本数在同一联赛内相同，详见 summary JSON）。这只是完整库存诊断，不据此筛选联赛或形成交易限制。','',
'| league_id | 场次 | Crown基准 | 仅门将 | 市场+门将分钟 | 市场+连续性 | 市场+全部门将 |',
'|---:|---:|---:|---:|---:|---:|---:|']
leagues=sorted(S['candidate_models']['market_only']['incremental_by_league'],key=lambda x:int(x))
for league in leagues:
 n=S['candidate_models']['market_only']['incremental_by_league'][league]['n']
 vals=[S['candidate_models'][m]['incremental_by_league'][league]['net_U'] for m in labels]
 lines.append(f"| {league} | {n:,} | "+' | '.join(f'{x:.3f}' for x in vals)+' |')
lines+=['',
'市场基准为正的联赛仅表示各自完整研究样本在历史回放中净额为正，不代表稳定/可前瞻使用。门将连续性方案在league_id 1与51为正，其余11个联赛净额为负；这些事后联赛拆分不是验证成功的依据。',
'',
'## 解释与局限','',
'1. **信号端**：纯门将历史单独选边亏损，加入 Crown 后也未改善。核心连续性变量在多数联赛、且三个年份都未形成跨期正收益。',
'2. **市场定价端**：当前数据不能区分“市场已充分定价”与“门将变量本身信息弱/数据时间不可靠”。结果只表明在已观察到的Crown T−12h赔率下，所测门将机制未产生正增量。',
'3. **数据质量端**：历史门将身份/GA标签可严格按事件日期回建，但无首次公开时间，实际可得时间不明；样本有99场无独立比分源、27场无当前数据库T−12h源事件，名称/赛程映射也不完整。',
'4. **价格成本端**：门将特征模型按实际Crown两侧赔率和AH线结算后亏损；数据不支持水差后新增利润。',
'5. **真实收据端**：没有可用于本研究的真实赛前球员信息快照或live Crown FID，不存在实时/影子交易验证。',
'6. **模型限制**：单一固定Ridge参数和预定义特征组合只代表这组研究方案；没有根据测试年度回调或挑选收益区间。逐周明细与逐场预测全量保留在JSON/JSONL。',
'',
'## 可复现文件与核验','',
'- `run_goalkeeper_ah.py`：重建门将历史特征，训练年度前推预测，逐场按Crown线水结算并导出年度/联赛/周统计。',
'- `verify_goalkeeper_ah.py`：独立读取原始Crown SQLite与HTTP响应，重算quarter AH结算，审计FT、响应SHA、FID、冻结重叠和真实收据类型。',
'- `goalkeeper_ah_all_methods_per_fixture_20261121.jsonl.gz`：五方法全样本逐场特征、预测、方向、Crown价格和结算。',
'- 五个独立 ledger JSONL.GZ：保留每个方法完整场次（含冻结重叠标记）；增量只纳入冻结外FID。',
'- `goalkeeper_ah_summary_20261121.json`：所有年度、逐周、联赛、合并和覆盖结果。',
'- `goalkeeper_ah_independent_audit_20261121.json`、`goalkeeper_ah_raw_quote_link_audit_20261121.jsonl.gz`、`goalkeeper_ah_raw_verified_subset_20261121.json`：原始Crown独立核验及可核验子集统计。',
'- `SHA256SUMS_20261121.txt`：输入/输出哈希和执行时间。',
'',
'原始 Transfermarkt / Crown 数据不复制进公开仓库；仅提交可复核的衍生逐场研究结果、来源路径/哈希、脚本与审计摘要。历史研究结果不等于正式订单、Telegram派单或账本收益。',
'']
(P/'M8_GOALKEEPER_CONTINUITY_AH_RESEARCH_20261121.md').write_text('\n'.join(lines))
print(P/'M8_GOALKEEPER_CONTINUITY_AH_RESEARCH_20261121.md')
'- `goalkeeper_ah_independent_audit_20261121.json`、`goalkeeper_ah_raw_quote_link_audit_20261121.jsonl.gz`、`goalkeeper_ah_raw_verified_subset_20261121.json`：原始Crown独立核验及可核验子集统计。',
'- `schedule_source_sha256_20261121.json`：身份交叉核验读取的5,180份本地M5原始赛程页哈希索引。',
