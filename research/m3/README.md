# M3 独立 AH / OU 研究

## 最新验收（2026-11-05）

- [M3 AH/OU 与 Crown 样本外验收报告](M3_RESEARCH_ACCEPTANCE_20261105.md)：记录最新严格 OOS Actions run `41956446597`、19,218 场可用历史赛果、14,806 场严格前推评分，以及 AH/OU 独立 Crown 历史快照影子回放（回放基于前一预测版本）。现有8,430条保存的forecast均缺完整比分网格；下一条新建预测才会记录比分分布，可用于 arbitrary Crown线EV。
- [Crown 回放的脱敏聚合数据](results/m3_crown_oos_replay_20261105.json)：不包含队名、fixture ID、赔率或密钥。
- 当前 OOS 原始可复核报告及预测/参数版本仍在下方既有 results 路径。
- 新增 [M3 Crown 前瞻采集器](m3_crown_forward_capture.py) 与 [每四小时 UTC workflow](../../.github/workflows/m3-crown-forward-capture.yml)。collector 只请求 `bookmaker=crown`，按 UTC 配对 M3 已记录预测和开赛前 AH/OU 报价；公开收据保存带密钥 HMAC 与汇总 EV，不保存盘口、水位或原响应。须待 workflow 首次成功运行后才能报告真实前瞻覆盖。
- 本地全量 M3 验证为 84/84 单测通过。修复后真实 Actions [41957259557](https://github.com/ljm198964-alt/quant-runner/actions/runs/41957259557) 成功，报告与 receipts 持久化于 commit `1f1721f2`：144 forecasts / 5 unique Crown identities / 18 quote commitments（AH 9、OU 9）/ exact-line EV 0 / ROI null。旧 forecast 缺比分网格，不能声称本批已有EV；新 forecast 已保存比分网格供后续实际报价计算。
- Secret 名称 `TOTALCORNER_TOKEN`、`PRIVATE_REPO_TOKEN` 只从公开 workflow 引用确认，未读取任何值。历史 Crown 源探测 run `39584036612` 成功；OddsPapi 的凭证、连接器和历史存档未找到。
- Crown 前瞻输入沿用 OpenFootball M3 forecast 账本，现有来源缺少 B1 前瞻 fixtures；研究固定范围仍为六联赛，B1 覆盖缺口如实保留。手动 Crown probe 已移除非 Crown fallback 并避免输出 ID/赔率字段。

M3 是独立研究模型，不读取 M1、M2、MR1 的预测、订单、参数或账本。当前流程不产生正式交易信号、不发 Telegram、不自动提升模型，也没有增加交易 Gate。

## 研究入口与结果

- [完整研究验收报告](M3_RESEARCH_REPORT.md)
- [Crown 存档线级审计](M3_CROWN_STAGE_A_B_AUDIT.md)
- [Crown 离线证据录入契约](crown_evidence_contract.md)
- [Crown TotalCorner 已授权响应离线导入规范](crown_totalcorner_import_contract.md)
- [M3 Crown 私有影子账本写入器](crown_shadow_ledger.py)（按模型可支持线计算五状态概率/理论 EV；不支持线明确留空，ROI 保持不可用）
- [M3 Crown 覆盖及配对状态](results/crown/latest_pairing_status.json)
- [最新 Crown 前瞻采集汇总](results/crown/latest_forward_capture_report.json)
- [追加式 Crown 前瞻承诺账本](results/crown/forward_quote_commitments.jsonl)（仅 HMAC 与 UTC 来源证据，不含原始价格）
- [最新 penaltyblog OOS 报告](results/latest_penaltyblog_oos_report.json)
- [最新时间切分清单](results/latest_penaltyblog_oos_splits.json)
- [最新 V4 原版指标](results/latest_v4_original_metrics.csv)
- [OpenFootball 无盘口影子 OOS 报告](results/openfootball/latest_oos_report.json)
- [OpenFootball 配对样本跨季稳定性审计](results/openfootball/latest_oos_stability.json)
- [稳定性审计复算器](openfootball_stability.py)
- [无重训稳定性 Actions 工作流](../../.github/workflows/m3-oos-stability.yml)
- [OpenFootball 影子运行收据](results/openfootball/latest_shadow_run.json)
- [OpenFootball 预测/结算追加式账本](results/openfootball/shadow_ledger.jsonl)
- [OpenFootball forward-only shadow 校准报告](results/openfootball/latest_shadow_performance.json)
- [Forward shadow calibration 复算器](openfootball_shadow_performance.py)
- 历史报告、预测 CSV 与参数快照在 `results/history/`、`results/predictions/`、`results/model_parameters/`。

稳定性工作流在 PR 分支完成 Actions run [39419131182](https://github.com/ljm198964-alt/quant-runner/actions/runs/39419131182) 与 [39419363464](https://github.com/ljm198964-alt/quant-runner/actions/runs/39419363464)：两次均运行现有产物分析和完整 M3 单元测试，不执行模型拟合；结果按 SHA 变化持久化。PR #51 已合并；默认分支每四小时 UTC schedule 已启用，合并后复核见 [39430911655](https://github.com/ljm198964-alt/quant-runner/actions/runs/39430911655)。

GitHub Actions 工作流 `.github/workflows/m3-independent-research.yml` 保持每 4 小时 UTC 运行，下载开源 Football Predictor V4 数据，按原项目流程执行 OU 模型，并对 penaltyblog 的 Poisson、Dixon-Coles、Bivariate Poisson 执行严格赛季前推 AH / OU 评估。每次运行记录输入文件 SHA-256、来源 commit、模型参数、预测文件哈希、时间切分、分数与前次报告比较；输入哈希相同会明确记录没有新增数据变化。

独立工作流 `.github/workflows/m3-openfootball-shadow.yml` 也配置为每 4 小时、手动和代码变更触发，使用 OpenFootball CC0 赛果/赛程分别运行三种 penaltyblog 进球模型，持久化严格赛季前推预测、逐次模型参数快照、运行历史与无盘口影子账本。它不下载或读取 Crown 报价，也不写正式账本。OpenFootball 日期没有文档化时区：具体开赛时间被忽略，影子预测只接纳源日历日期至少晚于运行 UTC 日期 3 天的 fixture。B1 在此数据源缺席。该 workflow 已随 PR #51 合入默认分支；合并后 Actions run `39430911655` 成功验收，四小时定时 schedule 当前已在默认分支启用。

## 重要口径

Football-Data.co.uk 历史赛果仅提供日期（无精确开赛时间），训练集排除测试赛季首场比赛所在的整个 UTC 日期；训练仅使用更早赛季文件且比赛日期严格早于测试截止。该数据源文件中的赔率列不会被 penaltyblog 流程读取。未知训练球队不生成伪预测，而记录为未覆盖。

penaltyblog 目前的 AH 评价为 AH 0.0（主队 DNB）三状态概率；OU 评价为固定 O2.5。由于当前没有 Crown 的同期有效盘线和双边水位，二者只是模型概率诊断，不是具体 Crown 下注结果，ROI、收益和回撤均为空。其他来源的赔率不能代替 Crown。

Football Predictor V4 的 ROI 列只还原其上游研究阈值和原数据赔率，不能称作 Crown ROI，也不能作为 M3 正式交易规则。该上游仓库当前检出版本未发现显式许可证文件；M3 不复制其源代码，工作流按原项目入口运行，并将许可限制记录在报告中。

OpenFootball 评估的 AH 只报告 AH0/DNB 三状态概率，OU 报告固定 O2.5；目前影子账本尚无 Crown 盘口、EV、ROI 或可计算回撤。原始 OpenFootball 日期键不代表精确 kickoff UTC。

稳定性 JSON 对同一 OOS 集按模型、赛季、联赛和联赛×赛季列出 AH0 三类与 O2.5 的 `(预测均值−实际发生率)`，用于观察概率误差集中在哪些子组。当前 O2.5 全量低估约 2.09–2.40 pp；D1 低估 5.15–5.35 pp，I1 与 SP1 接近零。2026/27 部分赛季 n=199 时低估约 10 pp，样本不足以支持稳定结论。此诊断不进行事后概率修正或交易筛选。

逐组误差扩展在 Actions run [39420905826](https://github.com/ljm198964-alt/quant-runner/actions/runs/39420905826) 验收成功，33 项测试通过并将 JSON 保存到公开分支提交 `a28d0b0`。原输入 fingerprint 与 source OOS report 时间未变，workflow 只复算保存的预测，没有重新拟合。

账本 append-only，保留了首次版本身份实现造成的重复预测历史行；随后 4,215 条以 `FORECAST_DUPLICATE_SUPERSEDED` 标记为重复。报告按唯一 forecast key 计有效预测，账本不会把 superseded 行再次计分/结算。修复后的重复 Actions run 已验证新预测、结算、重复修正均为 0，ledger SHA 不变；详情见完整验收报告。

`openfootball_shadow_audit.py` 在不拟合、不结算的情况下校验逻辑 forecast 键唯一、supersession 引用、UTC 预测时间和日期 guard、概率归一化、无 Crown 时 EV/ROI 为空及无正式单/TG。`openfootball_shadow_performance.py` 只读 canonical forward 预测和 FT settlement，按模型、源日历月/周、league×season报告AH0/DNB三状态及OU O2.5 Log Loss、Brier、校准分箱和同 fixture 模型配对差异；不作模型选择/参数调优，不混入 hindcast，不算 financial ROI。源fixture日期没有时区语义，按日历键聚合且不称作UTC kickoff。当前 ledger 有 8,430 条原始 FORECAST 行，其中 4,215 条明确 superseded，折为 4,215 条有效逻辑预测；零结算、零 Crown 快照、零 EV/ROI。该审计随 Saved OOS Stability 工作流每四小时运行并持久化 `results/openfootball/latest_shadow_ledger_audit.json`，且验证 ledger SHA 与当时账本一致。Actions run [39420305676](https://github.com/ljm198964-alt/quant-runner/actions/runs/39420305676) 于 2026-10-20 SUCCESS，33 项测试通过，上传 artifact 与仓库审计 JSON 一致。该 workflow 只读既存 OOS 产物及 ledger，不重新训练。

最新无盘口 shadow run [39421816230](https://github.com/ljm198964-alt/quant-runner/actions/runs/39421816230) 于 2026-10-20 UTC 成功，40 项测试通过。输入/赛程指纹均未变；日期保护范围内 1,405 个 fixture 全已有 canonical forecast，故新预测、结算和重复修正均为0，账本 SHA 不变。Crown quote=0，EV/ROI/最大回撤不可计算；本次没有新增学习信息。

随后在当前 PR HEAD `e6104abed2fa340994a397cbf95c6d9651887a32` 手动验收 [shadow run 39423160751](https://github.com/ljm198964-alt/quant-runner/actions/runs/39423160751) 与 [saved OOS stability run 39423493743](https://github.com/ljm198964-alt/quant-runner/actions/runs/39423493743)。两者均通过 40/40 M3 tests；shadow receipt `generated_utc=2026-10-20T12:34:05.833328Z`。结果输入 fingerprint `93e0b8b91722f9c967e608ad63ae88d4c8d8b4c466de92948673438704697c8e` 与赛程 fingerprint `2db32fe59ae637841be2d3ad7abc1d410e0aa5ea543bca2fe7af61096322f526` 未变。1,405 个日期保护范围内 fixture 已有唯一逻辑预测，故 forecast/settlement/supersession 均新增0；无新学习或新结算。稳定性复核对每模型 11,254 个配对评分样本、33,762 条训练 cutoff 再验证；Crown quotes used=false。稳定性 artifact 与分支 JSON 字节一致，账本仍 4,215 canonical forecasts、0 settlements、0 Crown/EV/ROI、0 formal order/TG。状态未变化，workflow 未制造结果落库 commit。

已审计一个近期历史盘口候选 OddsPapi：供应商将 `singbet` 称作 Crown in Asia，文档提供 UTC historical snapshots 与 AH/总进球市场，历史可用范围从 2026-01 起。但另一盘口供应商将 Crown 和 SingBet 分列；未获赔率源一手身份映射，也未核实公开研究许可，因此 `singbet` 仍标为未验证候选，**不计入**当前 Crown 数据覆盖。未注册账户、未调用API。TotalCorner 官方 API 文档明确列出 VIP 下的 `bookmaker=crown` AH/goal-line endpoint 及限速；现行 ToS 同时将 API 纳入 Service 并要求自动化提取的 prior written consent，未明确 API 请求是否豁免，也未明确公开留存/分发权限。公开项目中没有可追溯的许可范围证明，本轮未新增 Crown 请求。细节见 [Crown archive audit](M3_CROWN_STAGE_A_B_AUDIT.md)。

已有 `crown_totalcorner_import.py` 可在离线环境验证操作者提供的 TotalCorner Crown API 响应；它要求书面授权引用、IANA 时区证据、精确队伍身份与独立 UTC kickoff，过滤非赛前/暂停的报价，并拒绝 DST 歧义及未定义复合线。该 adapter 不联网、不写公开价格、不计算 EV/ROI；合成测试不增加真实 Crown 覆盖。它的代码提交 `feb6f4dfabb19653bbedaaba2a212644e86a85d0` 已由 Actions [39421816343](https://github.com/ljm198964-alt/quant-runner/actions/runs/39421816343) 验收。当前可追溯授权范围与账户时区证据仍未核实，因此未执行新 Crown 请求。

既有 `probabilities.py` 包含由进球概率网格计算 AH/OU 单位 EV 的功能；现补充给定实际比分的 AH/OU 结算及从 full/half settlement probabilities 汇总 EV 的纯函数，覆盖全赢、半赢、走水、半输、全输和 quarter-line。它不抓数据、不选择下注方向、不充当来源验证或交易 Gate。真实数据在调用前必须先经过 Crown 盘口身份、授权和 UTC 时序校验。当前单场已归档 Crown 样本的线级 EV 和反事实单位结算见 [M3 Crown Stage A/B audit](M3_CROWN_STAGE_A_B_AUDIT.md)；样本太少，不报告策略 ROI、累计收益或回撤。

运行单元测试：

```bash
python -m unittest discover -s research/m3 -p 'test_*.py' -v
```

新增 OpenFootball 前瞻预测会保留 penaltyblog 1.13.1 原生归一化精确比分矩阵（行=主队进球、列=客队进球），并由账本审计验证矩阵形状、有限概率、总质量和方向语义。现有历史 forecast 不回填比分矩阵；已有 AH0 / OU2.5 字段不变。私有 Crown writer 可消费新预测矩阵，对经过独立授权、身份与 UTC 时序验证的确切 Crown AH/OU 线计算五状态概率和条件 EV。报价缺失时 EV/ROI 仍为空。OpenFootball 赛程没有精确 UTC kickoff，因此比分矩阵能力本身不构成 Crown 市场配对。
