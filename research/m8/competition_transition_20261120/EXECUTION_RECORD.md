# 执行记录

- 运行 `python3 research/m8/competition_transition_20261120/audit_competition_transition.py`：完成；重验缓存5,180页SHA，0差异。
- 运行 `python3 research/m8/competition_transition_20261120/build_report.py`：完成；生成报告与SHA清单。
- 目标库存46,068个历史路径FID；43,084个有完整赛事身份；缓存内已完成比赛148,158个唯一FID，身份冲突0；同国家、同队名、不同国内联赛且目标联赛无同期历史的候选0FID。
- 没有候选订单，未计算/伪造净U、ROI、MDD或周均单量；没有运行市场利润回测或实收回放。
- 仅使用已缓存TotalCorner赛程/赛事ID作身份和赛前历史覆盖审计。目标赛果不进入特征；历史AH路径仅定义目标库存，不读取其它公司价格。
- 冻结八组、生产模型、Telegram、账本、Crown采集链、调度均未修改；0派单、0账本写入。

可复算命令：

```sh
python3 research/m8/competition_transition_20261120/audit_competition_transition.py
python3 research/m8/competition_transition_20261120/build_report.py
```
