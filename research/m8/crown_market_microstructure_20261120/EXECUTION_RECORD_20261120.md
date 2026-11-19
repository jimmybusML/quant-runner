# 执行记录

- 主研究：`python3 research/m8/crown_market_microstructure_20261120/m8_crown_microstructure_20261120.py`，完成；21,455八组外唯一 FID。
- 原始 Crown/FT/五态结算独立校验：`python3 research/m8/crown_market_microstructure_20261120/verify_crown_microstructure_raw_20261120.py`，完成；7327/21455 FID raw 覆盖、36635行净U和结算标签复算匹配，另有70640个方法行因原始JSON缺失未能核验；因此全池 raw audit 未通过覆盖验收。
- 实收对齐：`python3 research/m8/crown_market_microstructure_20261120/audit_receipts_overlap_20261120.py`，561实收快照/176FID，精确交集0，回放0场。
- 结果包括全年度、ISO周、联赛、盘深及五态结算；所有方法同一FID集合，候选之间100%重叠。
- 本轮只执行研究模拟；0正式 Telegram 订单、0正式账本回写、0生产工作流/采集变更。
- 输入、脚本、报告、逐场结果和审计文件SHA见 `SHA256SUMS_20261120.txt`。
