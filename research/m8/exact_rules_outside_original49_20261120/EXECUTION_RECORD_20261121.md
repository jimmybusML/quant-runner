# M8 原八组精确规则跨联赛复算记录

- 执行日期：2026-11-21（本地时区 Asia/Shanghai）。
- 执行仓库分支：`research/m8-exact-cross-league-expansion`；复用公开 PR #68，未创建重复 PR。
- 复算范围：扩展赛程 64 联赛中冻结原 49 之外的 15 个联赛；冻结成员 10,294 FID、原规则、优先级与生产行为均未修改。
- 数据来源：本地只读 Crown SQLite、已有扩展赛程、目标联赛 TotalCorner 原始赛程缓存和冻结八组历史文件。未发起 TotalCorner 或 Crown 网络请求。
- 当前 Crown SQLite SHA256：`292ccbde5afe72490e2978599640e8a06a075d8d73c5210f75b002046414d298`。此前结果记录的 SQLite SHA 为 `7401078708d56a122987fde6231ae4b8cf296020d7fae54048437e73462c8a3f`，故按当前库完整复算，保留先前提交结果供历史比较。
- 当前样本：21,096 个赛事 FID；有已保存 movement AH 行 7,112 场，其中赛前报价 7,110 场；完整 T6/T3/T1 路径 6,971 场；G 所需比分强度齐全 6,971 场。数据缺失分别登记为 capture 有但无报价 11,266、无 movement capture 2,718、缺 T6 139、无有效赛前价 2。
- 精确规则命中：base 692/+8.080U；A 54/−13.190U；B 218/−6.955U；C 38/+4.710U；D 29/+9.830U；E 52/+2.690U；F 22/+1.120U；G 168/−0.600U。按冻结优先级 `base → A → B → C → D → E → F → G` 去重后 1,273 个八组外唯一 FID，净值 +5.685U、ROI +0.447%、MDD 27.755U、完整观察跨度周均 3.350 单。
- 原冻结八组仍为 10,294 FID/+236.015U。与 1,273 个新增 FID 交集为 0；合并 11,567 FID、+241.700U、ROI 2.090%。新增年度净值 2019 +5.935、2020 −5.660、2021 −1.880、2022 +1.775、2023 +9.530、2024 +13.310、2025 −9.565、2026（完整报价到 6 月 1 日）−7.760U；不是跨年稳定的正增量。
- 联赛总计 6 个正、7 个负、2 个无新增单；正值联赛为 International Match、USA MLS、Gulf Cup、Mexico Liga MX、Albania Championship、Argentina Liga Profesional。所有联赛数据仅是诊断结果，没有据此增加过滤条件。
- 首次以旧扩展赛程单一来源独立核对时，两笔新增订单没有独立 FT 行。加入主研究脚本实际读取的目标联赛原始 TotalCorner schedule cache 后，明确按 FID 核对联赛、主客队、开球和 FT；最终 1,273/1,273 笔通过 Crown 原始响应 SHA、T1 合约和 AH 五态/四分之一盘拆腿结算校验，错误 0，重算 +5.685U。验证器报告目标联赛赛程缓存页数量及 SHA；完整逐笔输出另存 JSONL。
- 当前真实赛前 Crown 收据审计：目标 15 联赛有效 FID 0，T1 前收到的完整路径 0，实收规则订单 0。1,273 笔均属历史 source-event 回放，不能解释为当时收到、可成交、Telegram 或正式账本订单。
- 复算命令：
  - `python3 research/m8/exact_rules_outside_original49_20261120/exact_rule_cross_league_20261120.py`
  - `python3 research/m8/exact_rules_outside_original49_20261120/verify_exact_rule_cross_league_20261120.py`
  - `python3 research/m8/exact_rules_outside_original49_20261120/actual_receipt_exact_rule_audit_20261120.py`
  - `python3 research/m8/exact_rules_outside_original49_20261120/build_exact_rule_report_20261120.py`
- 当前逐场报告、JSON、压缩 JSONL 和验证账本见本目录；SHA 文件为 `SHA256SUMS_20261121.txt`，并保留原 2026-11-20 提交历史。
- 工程边界：只改研究代码、报告、结果及交接；未改 M8/M9/M1/MR1 生产策略、Telegram、正式账本、结算、Crown 采集或调度。
