# M8 原八组精确规则跨联赛扩展｜2026-11-22 稳定快照复算

## 执行范围

- 仓库分支：`research/m8-exact-cross-league-expansion`；既有 PR #68，目标 `main`，未合并。
- 本次只做历史研究。没有修改冻结八组、M9/M1/MR1、生产模型、Telegram、正式账本、采集链或调度。
- 目标为扩展赛事清单64个provider联赛ID排除原49后的15个联赛；按原规则base→A→B→C→D→E→F→G精确复算，FID唯一归属。
- 数据库回填驱动仍在对共享 SQLite 写入。为避免复算期间读到多版本数据，通过SQLite在线备份接口获取固定快照，不停止或修改该既有任务。
- 快照：`/private/tmp/m8_cross_league_crown_snapshot_20261122.sqlite3`；生成时间约`2026-11-22T00:18:13Z`；SHA256 `28e0f1aa4ed69205c8933950f270c1805e831d9314d22622191fb5029d44592a`。完整数据库不入仓；输入SHA和逐场可审计资料入仓。

## 实际执行

- `M8_CROSS_LEAGUE_DB=/private/tmp/m8_cross_league_crown_snapshot_20261122.sqlite3 python3 research/m8/exact_rules_outside_original49_20261120/exact_rule_cross_league_20261120.py` — exit 0。
- 同快照运行`verify_exact_rule_cross_league_20261120.py` — exit 0；从Crown原始响应SHA、原始T1 AH合约及独立TotalCorner赛事身份/FT复核1,303/1,303单，错误0，重算−1.505U；正确拆分四分之一盘口。
- 同快照运行`actual_receipt_exact_rule_audit_20261120.py` — exit 0；15个目标联赛真实HTTP赛前收据0、T1前完整路径0、精确订单0。
- `compare_cross_league_snapshot_replays_20261122.py` — 对比前次已发布提交`37328888`。完整路径增加86个FID；前次6,982条路径全部保持相同T6/T3/T1及规则特征。新增27笔订单净值−7.850U；原有1,276笔订单方向、盘口、组别及收益均未变化。此前+6.345U变为本快照−1.505U，差额完全来自新增覆盖。
- `build_exact_rule_report_20261120.py` — 刷新完整报告及2026-11-22输入/输出SHA清单。

## 当前快照结果

- 21,096个赛程FID；7,211场保存movement报价，7,209场含赛前source-event报价；7,068场完整T6/T3/T1路径。缺口：11,277场采集记录无AH报价、2,608场无movement采集、141场缺T6、2场没有有效赛前报价。
- 原冻结10,294 FID、+236.015U，未变。新增FID与冻结成员交集0。
- 精确规则优先级去重新增1,303单，−1.505U，ROI −0.116%，MDD 34.200U；380个观察ISO周平均3.429单，254个有单周平均5.130单。合并为11,597单、+234.510U、ROI 2.022%。
- 分组：base 716/−0.450U；A 55/−12.170U；B 221/−6.665U；C 39/+3.710U；D 29/+9.830U；E 52/+2.690U；F 22/+1.120U；G 169/+0.430U。结果为优先级分配账本，不把多组命中重复计数。G用原独立比分Poisson模型和EV方向，没有以M9代替。
- 分年新增：2019 +5.935U；2020 −5.660U；2021 −1.880U；2022 +1.775U；2023 +9.530U；2024 +13.310U；2025 −9.565U；2026 −14.950U。当前2026样本仍为非全年覆盖；逐年路径区间、逐组成绩和逐联赛成绩以结果JSON及报告为准。没有跨年度稳定盈利证据。
- 全部都是历史source-event回放；不代表实际赛前收据、可成交单、Telegram订单或正式实战。

## 交付

- 报告：`EXACT_RULE_CROSS_LEAGUE_REPORT.md`
- 逐场新增订单：`exact_rule_cross_league_orders.jsonl.gz`
- 完整路径和覆盖清单：`exact_rule_cross_league_all_complete_paths.jsonl.gz`、`exact_rule_cross_league_coverage_by_fid.jsonl.gz`
- 汇总：`exact_rule_cross_league_summary.json`、`exact_rule_cross_league_coverage.json`
- 独立逐场结算验证：`independent_settlement_verification_20261122.json`及JSONL
- 真实收据审计：`actual_receipt_exact_rule_audit_20261122.json`、订单JSONL
- 变化归因：`snapshot_delta_audit_20261122.json`
- 输入/输出哈希：`input_sha256_manifest_20261122.json`、`output_sha256_manifest_20261122.json`、`SHA256SUMS_20261122.txt`
