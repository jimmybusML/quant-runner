# 执行记录

- 主时间前推研究：`python3 research/m8/red_card_adjusted_form_20261120/run_red_card_adjusted_form.py`，完成。覆盖46,068目标路径，预测30,268场，八组外唯一候选24,173场。
- 实际T1 Crown收据重算：`python3 research/m8/red_card_adjusted_form_20261120/replay_actual_receipts.py`，完成832个候选FID；原始HTTP响应SHA/身份/赛前时序/Crown市场错误均为0，事件回放价格精确匹配449场，383场按实收价格重新结算，当前赛程开球元数据差异6场。
- 独立历史数据/原始Crown/FT/模型前推验证：`python3 research/m8/red_card_adjusted_form_20261120/verify_red_card_adjusted_form.py`，PASS。原始历史card+FT覆盖88,053场；2024/2025/2026前推测试数10,420/11,323/8,525。
- 独立HTTP收据、实收盘口重定价及AH五态结算验证：`python3 research/m8/red_card_adjusted_form_20261120/verify_actual_receipt_replay.py`，PASS。4160条FID×方法记录全部核对通过。
- 统计、报告、执行清单及SHA文件：`python3 research/m8/red_card_adjusted_form_20261120/build_deliverables.py`，完成。
- 历史候选五种方案均负净U；2024–2026各年均负。收据价格中低赔率边基准+4.535U，但仅832场/5个活跃ISO周且结果已知，不是新机制证据；其余四种含Crown模型方案亏损。
- Crown AH报价是历史事件回放或真实归档HTTP报价；红牌/历史特征没有被证明在当时已收到。不是未见赛果的前瞻盲测，也不是正式Telegram订单、真实成交或账本结果。
- 正式Telegram派单0；账本写入0；生产工作流/采集链/调度改动0；冻结原八组改动0。

输入及输出SHA详见`SHA256SUMS.txt`。逐场数据及原始响应不含私密响应body；真实收据独立校验仅在本机已授权归档上执行。
