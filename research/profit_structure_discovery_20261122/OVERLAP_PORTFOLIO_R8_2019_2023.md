# R8｜2019—2023年27个五年正收益结构：逐场重叠与组合审核

用户同意研究27个结构之间的重叠、同向/反向关系、去重组合收益。**仅使用2019—2023数据，未使用2024—2026。**

## 信号与覆盖

- 候选结构：27；信号总命中：4465；FID去重：2527；多信号FID：1207；相反方向FID：268；多数投票平票FID：119。

## 四种研究性组合核算

每个FID最多计1U总风险；最早窗口单信号、方向一致、投票三种情景取对应盘口历史赔率。等权分数收益在同场反向时是理论收益混合，不是可执行的一笔下注。所有方案均为研究情景，不是用户批准的生产规则。

| 情景 | 2019 | 2020 | 2021 | 2022 | 2023 | 合计场数 | 净U | ROI | 最大回撤U | 亏损月份 |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| earliest_one_signal | 278场/+37.305U | 526场/+51.765U | 483场/+56.950U | 318场/+48.140U | 922场/+59.155U | 2527 | +253.315 | +10.0243% | 23.795 | 14 |
| equal_signal_fractional_blend | 278场/+37.173U | 526场/+49.651U | 483场/+58.273U | 318场/+54.176U | 922场/+39.571U | 2527 | +238.845 | +9.4517% | 26.047 | 12 |
| unanimous_same_side | 256场/+37.425U | 459场/+51.450U | 437场/+55.280U | 279场/+52.260U | 828场/+46.550U | 2259 | +242.965 | +10.7554% | 24.145 | 13 |
| majority_vote | 271场/+37.355U | 493场/+49.145U | 467场/+63.255U | 303场/+58.195U | 874场/+34.920U | 2408 | +242.870 | +10.0860% | 28.320 | 13 |

## 重叠最严重的候选对

完整137组有重叠的候选对详见 overlap_portfolio_r8_pairwise.csv。

| 候选A | 候选B | 同场 | 同方向 | 反方向 |
|---|---|---:|---:|---:|
| T6|price,momentum|price=4;momentum=2|underdog | T6|price|price=4|underdog | 313 | 313 | 0 |
| T24|line,price,momentum|line=3;price=1;momentum=2|underdog | T24|line,price|line=3;price=1|underdog | 308 | 308 | 0 |
| T6|line,price|line=1;price=4|away | T6|line,price|line=1;price=4|underdog | 227 | 206 | 21 |
| T6|line,price|line=1;price=4|away | T6|price|price=4|underdog | 227 | 206 | 21 |
| T6|line,price|line=1;price=4|underdog | T6|price|price=4|underdog | 227 | 227 | 0 |
| T12|line,momentum|line=2;momentum=3|favorite | T12|line,price,momentum|line=2;price=1;momentum=3|favorite | 179 | 179 | 0 |
| T6|line,price|line=1;price=4|away | T6|price,momentum|price=4;momentum=2|underdog | 167 | 149 | 18 |
| T6|line,price|line=1;price=4|underdog | T6|price,momentum|price=4;momentum=2|underdog | 167 | 167 | 0 |
| T6|price,momentum|price=4;momentum=1|away | T6|price|price=4|underdog | 107 | 71 | 36 |
| T12|line,momentum|line=2;momentum=3|favorite | T12|price,momentum|price=2;momentum=3|away | 60 | 33 | 27 |
| T6|line,price|line=1;price=4|away | T6|price,momentum|price=4;momentum=1|away | 59 | 59 | 0 |
| T6|line,price|line=1;price=4|underdog | T6|price,momentum|price=4;momentum=1|away | 59 | 56 | 3 |

## 审核与方法限制

- 27个候选先依据2019—2023每年正盈利筛出，再在**同一五年**内组合。因此组合五年全正仍是样本内挑选偏差，不能当作独立前推验证。
- 多个候选同场命中高度相关，不能把信号当成独立订单；不同时间窗口的报价可能不同，最早窗口与多数投票是比较情景而非用户规则。
- 每月、每年以及最大回撤完整结果在 overlap_portfolio_r8_results.json；回撤按开赛时间的1U等额模拟收益累计。
- 研究尚未测试时间因果的动态权重，也没有验证真实可成交盘口。历史Crown报价为2026赛后回取的源事件时间。
- 27个结构和4种组合方案均待用户审核，未修改M8冻结八组、正式Telegram派单或结算。

## 下一步建议（未批准为规则）

先让用户审核结构重复、方向冲突和四个组合情景，再研究是否应在2019—2023内部按时间逐年前推更新权重，或扩展独立机制。不得擅自把一致性投票设为出单Gate。
