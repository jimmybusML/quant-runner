# M8 原八组精确跨联赛研究执行记录

- 执行日期：2026-11-22（Asia/Shanghai）。分支：`research/m8-exact-cross-league-expansion`。
- 复用现有独立研究目录和本地数据；当前 Crown SQLite 以只读连接复算，SHA256 为 `292ccbde5afe72490e2978599640e8a06a075d8d73c5210f75b002046414d298`。没有 TotalCorner/Crown 网络请求。
- 实际执行命令及状态：
  - `python3 research/m8/exact_rules_outside_original49_20261120/exact_rule_cross_league_20261120.py` — exit 0。
  - `python3 research/m8/exact_rules_outside_original49_20261120/verify_exact_rule_cross_league_20261120.py` — exit 0；独立重读778个相关TotalCorner缓存页、Crown原始响应SHA、T1合约和FT，1,273/1,273笔通过，错误0，独立重算+5.685U。
  - `python3 research/m8/exact_rules_outside_original49_20261120/actual_receipt_exact_rule_audit_20261120.py` — exit 0；收据FID、T1前收到的完整路径、规则订单均为0。
  - `python3 research/m8/exact_rules_outside_original49_20261120/build_exact_rule_report_20261120.py` — exit 0，刷新报告和SHA清单。
- 研究范围：64联赛扩展赛事中排除冻结原49后的15个联赛；21,096个赛程FID、6,971条完整T6/T3/T1路径。按原base→A→B→C→D→E→F→G优先级归属，得到1,273个八组外唯一FID，+5.685U、ROI +0.447%、MDD 27.755U。380个观察ISO周平均3.350单，252个有单周平均5.052单。
- 分组结果：base 692/+8.080U；A 54/−13.190U；B 218/−6.955U；C 38/+4.710U；D 29/+9.830U；E 52/+2.690U；F 22/+1.120U；G 168/−0.600U。按优先级去重，不能把原始跨组触发收益重复相加。
- 年度新增净值：2019 +5.935、2020 −5.660、2021 −1.880、2022 +1.775、2023 +9.530、2024 +13.310、2025 −9.565、2026 −7.760U；2026可复算路径仅到6月1日。2024–2026合计−4.015U，不支持最近年度稳定扩单盈利。
- 原冻结八组仍为10,294 FID、+236.015U；与新增FID交集0。合并为11,567 FID、+241.700U、ROI 2.090%。五态结算计数：全赢510、半赢136、走水74、半输69、全输484；四分之一盘按两腿拆分。
- 正净值联赛6个、负净值7个、无新增订单2个；逐联赛和逐年细目见 `EXACT_RULE_CROSS_LEAGUE_REPORT.md`。不按本次表现增加任何联赛规则。
- 报告末尾标记为2026-11-22复算；`SHA256SUMS_20261121.txt` 在该研究目录执行 `LC_ALL=C shasum -a 256 -c SHA256SUMS_20261121.txt` 全部通过。输入输出SHA均登记，私人原始HTTP响应和数据库未上传。
- 远端已有PR #68（目标`main`、状态OPEN）。本轮沿用该PR，不另建重复PR、不合并；完成提交后同步PR描述中的旧复算数字。
- 全程仅研究和只读审计：冻结原八组、M9/M1/MR1、生产工作流、Telegram、正式订单/结算账本、采集链和调度均未改；无正式派单、工作流执行或账本写入。
