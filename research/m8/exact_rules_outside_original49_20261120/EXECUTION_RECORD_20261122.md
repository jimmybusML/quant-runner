# M8 原八组精确跨联赛研究执行记录

- 执行日期：2026-11-22（Asia/Shanghai）。分支：`research/m8-exact-cross-league-expansion`。
- 复用当前公开研究分支已有数据与独立研究目录；未触碰同一工作区外的未提交文件。当前 SQLite 只读打开，SHA256 `292ccbde5afe72490e2978599640e8a06a075d8d73c5210f75b002046414d298`。本轮没有 TotalCorner/Crown 网络请求。
- 实际执行命令：
  - `python3 research/m8/exact_rules_outside_original49_20261120/exact_rule_cross_league_20261120.py` — exit 0。
  - `python3 research/m8/exact_rules_outside_original49_20261120/verify_exact_rule_cross_league_20261120.py` — exit 0。
  - `python3 research/m8/exact_rules_outside_original49_20261120/actual_receipt_exact_rule_audit_20261120.py` — exit 0。
  - `python3 research/m8/exact_rules_outside_original49_20261120/build_exact_rule_report_20261120.py` — exit 0。
- 主研究核算：64联赛扩展赛程中排除冻结原49后15个目标联赛；赛程21,096 FID，完整T6/T3/T1路径6,971。按原base→A→B→C→D→E→F→G优先级产生1,273个新增唯一FID，+5.685U、ROI +0.447%、MDD 27.755U；观察期380个ISO周，平均3.350单/周。冻结原八组10,294 FID、+236.015U未改；新增与冻结交集0；并集合计11,567 FID、+241.700U、ROI 2.090%。
- 分组去重净值：base 692/+8.080U；A 54/−13.190U；B 218/−6.955U；C 38/+4.710U；D 29/+9.830U；E 52/+2.690U；F 22/+1.120U；G 168/−0.600U。年度新增净值2019 +5.935、2020 −5.660、2021 −1.880、2022 +1.775、2023 +9.530、2024 +13.310、2025 −9.565、2026 −7.760U（2026完整路径仅至6月1日）。最近三年合计为负。
- 独立核验器重新读取Crown响应SHA、T1合约、TotalCorner赛程身份与FT，并独立拆结算四分之一盘：1,273/1,273匹配、错误0、重算+5.685U。五态计数：全赢510、半赢136、走水74、半输69、全输484。真实赛前Crown receipt有效FID/完整路径/精确规则订单均为0；回测全部是历史source-event研究回放。
- 运行报告生成器后，`SHA256SUMS_20261121.txt` 对目录内列示文件执行 `LC_ALL=C shasum -a 256 -c SHA256SUMS_20261121.txt` 全部通过。完整逐组、逐年、逐联赛及数据覆盖信息见 `EXACT_RULE_CROSS_LEAGUE_REPORT.md`。
- 远端分支已包含前次研究内容；PR #68目标`main`、状态OPEN，head此前核对为`fa9319c4202ea5031230e173d7daf60ea87317ab`。本次复核仍在该PR分支，不另建重复PR、不合并main；新增执行证据将在本分支提交。
- 全程仅研究和只读审计：未改冻结八组、M9/M1/MR1、生产工作流、Telegram、正式订单/结算账本或采集链；无正式派单、工作流运行或账本写入。
