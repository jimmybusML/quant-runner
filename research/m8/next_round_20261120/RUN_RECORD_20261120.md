# M8 A–D 批量研究执行记录

日期：2026-11-20（Asia/Shanghai）

## 研究输入

- `PROJECT_HANDOFF.md`、M8 批量索引、R1–R65/A–L/M1–M8 相关机制研究与失败结果；原八组边界与市场路径报告。
- `/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl`：39,101 FID，SHA256 `f21d4d49621df503efdb607b72b08882c1f1365c3178cce13e696d9aad4b697e`。
- `/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl`：40,277 FID，SHA256 `e8cf152c821725139b5492746faa32fe46889886c3971878ee9cb6473e3662f8`。
- 冻结会员10,294唯一 FID，SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`。
- MR1 verified receipt snapshots 561行 / 176唯一 FID；对M8球队赛果输入做精确FID连接，176个FID均无匹配行，未以其他报价/赛果补齐。

## 完成命令与实际状态

1. `python3 research/m8/next_round_20261120/m8_strength_shock_breakthrough_20261120.py`：A市场惊讶、A市场价对照、D正负惊讶拆分和固定正EV不下注批量重放完成；每个全量模型21,455个八组外FID，含年/ISO周/联赛账本与收据FID连接审计。结果分别为 -729.850U、-618.005U、-722.965U；正EV选择子集也全部为负。实际收据模型FID数为0。
2. `python3 research/m8/next_round_20261120/m8_strength_distribution_20261120.py`：B校正北京时间年/周后完成；2024 7,191、2025 7,794、2026 6,470场，共21,455唯一FID；市场简单对照 -528.905U，线性分布 -797.590U，非线性/合约交互 -823.690U。模型每年均亏。
3. `python3 research/m8/next_round_20261120/verify_m8_strength_distribution_settlement_20261120.py`：64,365个FID×B模型独立 quarter-line 结算；五态结算、FT净胜球与净U一致，失败0。
4. `python3 research/m8/verify_m8_cross_competition_team_pricing_20261119.py`：再次读取本地原始Crown响应并完成21,455唯一FID核验，失败0。
5. `python3 research/m8/next_round_20261120/verify_breakthrough_raw_quote_bridge_20261120.py`：将A/B全部6种方法共128,730个选边结算逐FID桥接到独立原始Crown/FT核验；FID、北京时间开赛日、AH线、双方价、FT、结算均一致，失败0。
6. `python3 research/m8/next_round_20261120/build_breakthrough_audit_20261120.py`：候选间重叠和旧C方向审计完成；A/B/D全量候选是相同21,455 FID，不可加总；与冻结原八组重叠0。
7. 对本轮新增 Python 研究/核验脚本运行 `python3 -m py_compile ...`，语法编译通过。

## C 方向复用依据

C 不重跑边界相似度/q90–q99：该研究在 2026-11-19 已对 base+A–G 全组完整时间前推、正负分支及原始 Crown 结算。读取报告及 JSON SHA `c65d20248814fce7e48051e5c4eccd68fcd3e595c861535425cd0745dff3e5d2`，确认14个q95组合仅base两版本略正，其余亏损；q90全部亏损，q99少数极端尾部正值年度不稳；11,357唯一候选FID并集、3,998方向冲突、真实收据候选0。全结果仍留原档，不挑选盈利片段。

## 执行边界

所有本轮新模型是历史 Crown 源事件回放或不下注实验，不是正式信号、TG订单、实战成交或账本记录。没有启动生产工作流、没有更新正式采集配置，未改原八组、M1/MR1/M9、Telegram、账本或任何正式交易规则。研究结论不构成Gate。
