# 执行记录

日期：2026-11-20（Asia/Shanghai）

## 可行性与查重

- 读取 `PROJECT_HANDOFF.md` 当前 M8 最新交接段及本轮指定的七份 M8 研究报告。另核对 `M8_COMPETITIVE_OBJECTIVE_RESEARCH_20261119.md` 交接内容：赛季积分/阶段/淘汰赛已研究，七模型八组外新单均负，杯赛/淘汰赛样本极少；不重复执行。
- 检索 R1–R65、A–L、M1–M8 报告和脚本。A 的实力变化代理（转会、阵容、伤停、近期表现）已有研究，新的独立时戳字段库存未见；C 的冻结组机制归因/边界迁移已研究；旅行负担 D 没有队伍地理坐标/旅行轨迹字段，估计FID=0，不造数据。
- 可执行研究聚焦 B：连续 Crown AH 市场实力差→FT净胜球分布的线性与非线性校准及合同交互，比较同样本简单市场方向。

## 输入及口径

- Crown AH full-path event-time 特征：`/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl`，39,101 FID，SHA256 `f21d4d49621df503efdb607b72b08882c1f1365c3178cce13e696d9aad4b697e`。
- FT 特征：`/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl`，按唯一 FID 连接。
- 冻结八组：`/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl`，10,294 FID，SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`。
- 测试样本：2024 7,194、2025 7,793、2026 6,467，共21,454八组外唯一FID。前推训练截止年分别2023、2024、2025。AH-only，quarter line 两腿结算。历史报价是事后取回的 source-event 数据，不是当时HTTP收据。

## 执行

1. `python3 -m py_compile research/m8/next_round_20261120/m8_strength_distribution_20261120.py research/m8/next_round_20261120/verify_m8_strength_distribution_settlement_20261120.py`：通过。
2. `python3 research/m8/next_round_20261120/m8_strength_distribution_20261120.py`：完成。三种方法各21,454个FID；市场简单基准 -529.705U，线性分布校准 -796.040U，样条/合同交互 -828.650U；均逐年为负。
3. `python3 research/m8/next_round_20261120/verify_m8_strength_distribution_settlement_20261120.py`：通过。独立重结算64,362条FID-模型行，净U与五态结算一致，FT净胜球一致，差异0。
4. `python3 research/m8/next_round_20261120/verify_m8_strength_distribution_crown_ft_20261120.py`：完成。21,454/21,454目标FID读取本地原始响应并核对FID、Crown联赛/球队ID、开球日期、FT及T−1h或更早最新AH报价；线和双方赔率完全匹配，失败0。原始响应SHA/逐FID结果见gzip清单。
5. 所有产物按FID保存；结果含年度、ISO周、联赛、ROI、MDD、训练折参数、校准统计、去重和八组并入比较。

## 边界

未匹配真实HTTP receipt模型报价重估：receipt时点与T1输入不同，不能冒用其他时点报价。未做真实下单/成交/TG/账本核验，也没有运行任何正式工作流。未修改M9、M1、MR1、冻结原八组、生产采集或规则。工作区原有 M9 改动与缓存保持不动、未纳入本轮。
