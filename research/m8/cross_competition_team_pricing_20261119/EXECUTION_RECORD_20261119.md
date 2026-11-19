# M8 跨赛事球队定价迁移研究执行记录

执行日期：2026-11-19（Asia/Shanghai）

## 输入冻结

- Crown历史AH路径：`m8_late_full_path_water_features_20261114.jsonl`
- Crown历史球队/FT身份库存：`m8_independent_score_strength_20261114.jsonl`
- 原始冻结八组会员：`m8_foundation_20261115/historical_membership.jsonl`，SHA-256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`
- 权威逐场冻结会员账本：`frozen_eight_full_authoritative_membership_ledger_20261119.jsonl.gz`
- Crown—Transfermarkt球队身份桥源：`m8_pregame_info_source_20261117/games.csv.gz`，SHA-256 `142561989017d379bcf9e72bad0b87e0996bae0e7b710ebb3def9255f464c741`
- 实收价源：`m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl`

脚本运行时验证原冻结会员和权威账本均为10,294个唯一FID，会员组别和PnL逐FID相同。身份映射仅用球队身份匹配；未把Transfermarkt结果变量作为预测输入。

## 实际命令及结果

1. `python3 research/m8/m8_cross_competition_team_pricing_20261119.py` — **exit 0**。构建39,101条配对历史池、统一北京时间、训练年度前推、五个固定研究方案、逐FID账本、周汇总、冻结八组合并和实际收据重估。
2. `python3 research/m8/verify_m8_cross_competition_team_pricing_20261119.py` — **exit 0**。从原始Crown报价响应重新核对21,455个唯一FID、球队/联赛/开赛日、FT、T−1 Crown双边AH线价，并对每FID五种方向独立结算；107,275次方法结算全部吻合，失败0。
3. `python3 research/m8/verify_m8_cross_competition_receipts_20261119.py` — **exit 0**。重新读取873个真实收据原始HTTP响应与snapshot，核对body SHA、snapshot SHA、接收/报价/开球时间顺序及原始Crown `asian_list`，4,365次AH方法结算全部吻合，失败0。

## 覆盖和结果复核

- 时间前推八组外测试：2024 7,191 FID；2025 7,794；2026 6,470；合计21,455。没有跨测试方案重复叠加订单；所有方法同一FID池。
- 跨联赛球队交叉桥：11,714个命名锚点，362个单一联赛球队键映射至362个唯一俱乐部。没有一个2024–26目标FID的任一边有已映射跨联赛先前Crown AH记录。
- 同联赛历史Crown收益模型最好的全期控制结果为−511.650U/−2.385%；并入原八组后为28,329唯一FID/−314.385U/−1.110%。
- 实收报价重估873个原八组外唯一FID、5个ISO周；同联赛模型−29.110U/−3.334%。这批模型历史特征缺少目标时点的接收时间证明，不作实时盲测或正式订单声明。

## 执行边界

- 仅执行研究脚本及独立审计，不运行GitHub Actions/生产工作流。
- 未修改原八组、M9、M1、MR1、正式生产模型、采集频率、Telegram、正式账本或交易规则。
- 没有正式派单、订单成交、账本回写或部署。
- 研究脚本、结果和交接待本次版本化提交到用户指定公开仓库`ljm198964-alt/quant-runner`。
