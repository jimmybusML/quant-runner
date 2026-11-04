# M5 独立融合研究

生成时间：2026-11-04 UTC。M5 是独立研究身份；本目录不连接 M1/MR1/M3 的生产预测、订单、账本或 Telegram。当前已有真实概率前推实验和小样本 Crown OU 回放，但尚未完成 10,000 场 Crown 历史收益验证。

当前综合进度见 [M5_PROGRESS_REPORT_20261104.md](M5_PROGRESS_REPORT_20261104.md)。代码与产物：

- [probability_stack_oos.py](probability_stack_oos.py) → [M3 13,234 场逐季前推概率结果](results/m5_probability_stack_oos.json)
- [m1_ou_crown_small_archive_replay.py](m1_ou_crown_small_archive_replay.py) → [M1 冻结 Crown OU 小样本回放](results/m1_ou_crown_small_archive.json)
- [exact_m1_m3_join_audit.py](exact_m1_m3_join_audit.py) → [M1/M3 精确交集覆盖审计](results/m1_m3_exact_join.json)

## 可复核数据现状

| 数据 | 唯一赛事/样本 | 能支持什么 | 不能支持什么 |
| --- | ---: | --- | --- |
| M3 penaltyblog 严格赛季前推预测（Football-Data.co.uk 赛果输入） | 最新报告 17,151 个测试比赛，14,806 场获得分数预测；独立键为联赛、日期、主客队 | 可复核的 AH0 / OU2.5 概率诊断与赛果；训练测试按赛季、日期隔离 | 没有逐场 Crown 报价连接，不可计算 Crown EV/ROI；也不是 M5 的新融合模型 |
| MR1 Crown forward 历史快照，经公开 M4 配对报告 | 1,563 个不同 fixture；AH 1,563、OU 1,563 | 已验证 Crown 标签、报价时点早于 kickoff、FT 观察时点晚于 kickoff 的回放结果 | 是 MR1 历史模型选择的回放，不是 M5 独立模型；不足 10,000 场 |
| M1 `data/m1_history_cache` | 60 个 JSON 缓存文件（仅检查文件清单/大小） | M1 既有训练赛果缓存 | 缓存不是 Crown 报价档案；文件数不等于赛事数 |
| TotalCorner `/match/bookmaker_odds/{id}` | 代码已有 Crown 专属接口调用 | 技术上存在 Crown endpoint 与独立采集实现 | 当前项目文件缺少覆盖 M5 自动采集、保留和公开研究的书面授权范围；本次未发带凭证请求 |

M3 报告 `research/m3/results/latest_penaltyblog_oos_report.json` 由 2026-11-04T11:59:53.779352Z 生成；报告列明训练与测试严格按比赛日期/赛季隔离、当日测试结果不用于训练，且明确 `crown_roi: null`。同目录多个预测文件是不同运行快照，不能相加来扩大赛事数。最新预测文件 `9375bdbb...csv` 有 17,151 个唯一测试行身份，但其中只有 14,806 行有评分预测。

MR1 配对数据由公开 GitHub Actions run `41425306084` 保存的 M4 聚合 artifact 检查；artifact 报告将多时点快照与唯一 fixture 区分，最终每 fixture/market 仅取一个可验证赛前 Crown 报价。它没有可用于独立训练 M5 的公开逐场安全记录，因此 M5 无法在公开仓库独立复算 MR1 私有数据。

## 明确结论

- 当前已核实的公开可用 Crown 历史样本为 1,563 场，AH 与 OU 分开各 1,563 场，明显低于用户要求的 10,000 场 Crown 结算样本。
- 17,151 场 M3 OOS 赛果可支持概率研究，但其来源不含 Crown 历史报价；不以其他公司的赔率补值，也不将 M3/MR1/M1 的生产模型输出伪装成 M5 融合策略。
- 此仓库已有 M1 缓存与 MR1 Crown snapshots 通过私有仓库/Actions 使用过。当前公开文件并未包含允许 M5 拷贝、公开逐笔历史报价的授权记录。本审计未请求新授权、未读取或显示 token，也未复制私有原始报价。
- TotalCorner API 对无 token 的只读接口探测返回 `TOKEN_ERROR`。未执行带凭证请求、未发起批量历史采集，也未修改生产工作流。
- 因此本轮不能诚实地报告 M5 的 Crown ROI、EV 命中收益、10k Crown OOS 结果或“ROI >5%”结果。当前 Crown 可核验的独立基准回放是公开 M4 的 AH -2.8276% 与 OU -2.9706%（各 1,563 场、非 M5、非正式账本），只能说明已有旧模型回放并非达到目标；不是新 M5 表现。

## 下一步数据要求（不需要新 token，但需要既有授权证据）

要继续到 10,000 场 M5 Crown 回测，需在既有授权记录中确认允许：该现有 TotalCorner token 的自动查询范围、历史 Crown AH/OU 数据的本地留存、衍生统计公开发布、以及 M5 研究使用；同时需要至少 10,000 个唯一比赛的精确 UTC kickoff、唯一 fixture 身份、Crown 原始两侧 AH/OU 线价及其可信赛前 capture/received UTC、和 FT 来源/时间。若没有具备报价时间证据的历史数据，只能先以已许可的未来采集逐步建立前瞻影子数据，不能倒填历史价格。

满足数据条件后，M5 必须先固化一个新的独立基线；按 UTC 日期扩展训练/滚动预测，模型参数仅用已发生赛果，避免同日及未来泄漏。AH/OU 分别输出概率校准、Log Loss、Brier、样本数、赛季拆分及 Crown 覆盖。收益回测采用相同 fixture 集合比较可比模型，并按亚洲盘半赢/半输/走水结算；不通过事后门槛筛选追 ROI。
