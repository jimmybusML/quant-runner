# M5 独立融合研究

生成时间：2026-11-04 UTC。M5 是独立研究身份；本目录不连接 M1/MR1/M3 的生产预测、订单、账本或 Telegram。当前已有真实概率前推实验和 M3/M5 的 Crown AH/OU 小样本 OOS 回放，但尚未完成 10,000 场 Crown 历史收益验证。

当前综合进度见 [M5_PROGRESS_REPORT_20261104.md](M5_PROGRESS_REPORT_20261104.md)。Crown 研究包括 MR1 历史快照回放、严格赛季 OOS 的 AH0/OU2.5 精确线回放（n=24/36），以及另行标注的全比分网格任意主盘探索（严格 M3 OOS CSV 交集 n=17/17）。当前 ROI 均是小样本描述值，10,000 场目标远未达到。代码与产物：

- [probability_stack_oos.py](probability_stack_oos.py) → [M3 13,234 场逐季前推概率结果](results/m5_probability_stack_oos.json)
- [m1_ou_crown_small_archive_replay.py](m1_ou_crown_small_archive_replay.py) → [M1 冻结 Crown OU 小样本回放](results/m1_ou_crown_small_archive.json)
- [exact_m1_m3_join_audit.py](exact_m1_m3_join_audit.py) → [M1/M3 精确交集覆盖审计](results/m1_m3_exact_join.json)
- [mr1_local_crown_replay.py](mr1_local_crown_replay.py) → [MR1 私有本机存档的安全聚合 Crown 重放](results/mr1_local_crown_replay.json)
- [m3_crown_exact_line_replay.py](m3_crown_exact_line_replay.py) → [M3/M5 OOS 与 MR1 同 Crown 线价对照](results/m3_crown_exact_line_replay.json)
- [m3_grid_crown_replay.py](m3_grid_crown_replay.py) → [同期全比分网格与 Crown 任意主盘探索](results/m3_grid_crown_replay.json)

## 可复核数据现状

| 数据 | 唯一赛事/样本 | 能支持什么 | 不能支持什么 |
| --- | ---: | --- | --- |
| M3 penaltyblog 严格赛季前推预测（Football-Data.co.uk 赛果输入） | 最新报告 17,151 个测试比赛，14,806 场有全部三模型评分预测；当前季 121 场与本机 Crown 索引精确连接，AH0/OU2.5 各有 24/36 场有效价 | 全历史概率评分；当季子样本的 Crown ROI 与同价 M3/M5 比较 | Crown 子样本很小、不能代表 14,806 场；仅发布的 1X2/AH0 与 O2.5 概率不支持任意线结算 |
| M3 同期 penaltyblog 全比分网格 | 39 个 provider ID 有三模型网格；18 场有可验证赛前 Crown 报价；其中 17 场与严格 M3 OOS CSV 精确交集 | 用完整比分分布评价 Crown 任意主盘 | 缓存训练输入未封存逐条内容 hash/结果可得时间，属于探索性扩展，不作为无泄漏证明或主要 OOS 样本 |
| MR1 Crown forward 历史快照，经公开 M4 配对报告 | 1,563 个不同 fixture；AH 1,563、OU 1,563 | 已验证 Crown 标签、报价时点早于 kickoff、FT 观察时点晚于 kickoff 的回放结果 | 是 MR1 历史模型选择的回放，不是 M5 独立模型；不足 10,000 场 |
| M1 `data/m1_history_cache` | 60 个 JSON 缓存文件（仅检查文件清单/大小） | M1 既有训练赛果缓存 | 缓存不是 Crown 报价档案；文件数不等于赛事数 |
| TotalCorner `/match/bookmaker_odds/{id}` | 代码已有 Crown 专属接口调用 | 技术上存在 Crown endpoint 与独立采集实现 | 当前项目文件缺少覆盖 M5 自动采集、保留和公开研究的书面授权范围；本次未发带凭证请求 |

M3 报告 `research/m3/results/latest_penaltyblog_oos_report.json` 最新由 Actions run [41864900732](https://github.com/ljm198964-alt/quant-runner/actions/runs/41864900732) 生成于 2026-11-04T16:16:39.480507Z；该 run SUCCESS，源输入指纹/测试身份/模型版本与上一报告完全相同，9 项 penaltyblog 模型-市场比较分数差均为 0，故这次没有新增学习信息。报告列明训练与测试严格按比赛日期/赛季隔离、当日测试结果不用于训练，且明确 `crown_roi: null`。预测 SHA 仍为 `9375bdbb...csv`，有 17,151 个唯一测试行身份，其中 14,806 行有评分预测。同目录多个预测文件是不同运行快照，不能相加来扩大赛事数。

MR1 全量历史旧基准来自公开 GitHub Actions run `41425306084` 聚合 artifact。另对本机现存 MR1 V23 snapshot index 做只读精确连接，匹配 M3 当前季 121 场；公开结果只存聚合/哈希，不公开逐场安全原始记录，故没有把 MR1 私有记录复制到仓库。

## 本机 Crown 存档复核

本机 MR1 现存 snapshot 经严格 verified-Crown、received < kickoff、FT observed > kickoff 和 fixture identity 检查，得到 1,621 场唯一有效比赛。AH -67.655U/-4.1737%，OU -57.985U/-3.5771%，均为逐场每市场 1U。数据与结果均为本地研究 snapshot 聚合，输入 SHA 与 source HEAD 已保存；不包含公开逐场价格、ID、球队或原始账本。它不能与公开 M4 1,563 场报告逐场核对，不能声称是新增 58 场，也不是 M5 业绩或 M5 Actions 验收。

对当前公开仓库与历史工作流的只读检查确认 Actions Secret 名称 `TOTALCORNER_TOKEN`、`PRIVATE_REPO_TOKEN` 存在（只读元数据，未读取值）；未发现 OddsPapi credential、connector 或保存数据。M3 的 Crown 专项探针于 2026-10-21 有六次成功的只读诊断运行，最新 run 为 `39584036612`；该探针使用固定历史 match IDs，没有形成前瞻报价档案。M3 既有定时 forward-EV 工作流调用的是 TotalCorner **default bookmaker** endpoint（代码明确标为 `default_unspecified_NOT_CROWN`），没有将其价格算作 Crown。当前 M3 独立预测流程最近一次成功 run 为 `41824869171`（2026-11-04 UTC），输出严格日期/赛季前推预测，不含 Crown 报价。用户已确认继续复用现有 Crown 数据授权，本轮未申请新凭证；原始 quote 仍仅在本地归档做只读配对。更完整的来源、工作流和 ToS 审计见 [M3 Crown audit](../m3/M3_CROWN_STAGE_A_B_AUDIT.md)。

## M3/M5 小样本 Crown OOS 切片

严格精确键连接得 121 场 2026/27 M3 OOS fixture，排除 1 个身份碰撞；verified Crown AH0 双侧报价覆盖 24 场、OU2.5 覆盖 36 场。M5 walk-forward blend：AH +5.91U/+24.625%（24 注，95%按 fixture bootstrap 区间 -5.42% 至 +53.54%）；OU -1.66U/-4.611%（36 注，区间 -36.03% 至 +26.94%）。MR1 保存策略与同 quote line/side price/received timestamp 完全一致且有 MR1 verified FT 的共同样本为 AH 11 场、OU 21 场；同样本 M5 AH +30% 对 MR1 +15.45%，OU M5 -27.38% 对 MR1 -28.43%。均是研究回放，小样本，不能外推。详细 M3 单模型、M5、MR1 结果和分联赛聚合见 JSON。

独立的任意主盘网格探索在严格 M3 OOS CSV 交集 AH/OU 各 17 场，ROI 分别 -1.44% 和 -23.41%。该模型使用历史比分缓存，但未逐 forecast 封存训练输入 hash 与结果可得时间，因此仅作同期预测与 Crown 配对覆盖探索，不视为无泄漏证明。它与 AH0/OU2.5 样本不可直接合并。

## 明确结论

- 公开可核实 M4 聚合为 1,563 场，另有本机 MR1 1,621 场只读回放；公开安全聚合的 M3/M5 同线价 OOS 仅 AH 24 场、OU 36 场，远低于 10,000。
- 17,151 场 M3 OOS 赛果可支持概率研究，但其来源不含 Crown 历史报价；不以其他公司的赔率补值，也不将 M3/MR1/M1 的生产模型输出伪装成 M5 融合策略。
- 此仓库已有 M1 缓存与 MR1 Crown snapshots 通过私有仓库/Actions 使用过。当前公开文件并未包含允许 M5 拷贝、公开逐笔历史报价的授权记录。本审计未请求新授权、未读取或显示 token，也未复制私有原始报价。
- TotalCorner API 对无 token 的只读接口探测返回 `TOKEN_ERROR`。未执行带凭证请求、未发起批量历史采集，也未修改生产工作流。
- M3/M5 严格季前推小样本 Crown ROI：AH0 +24.625% / 24 场，区间跨零；OU2.5 -4.611% / 36 场。任意主盘网格探索另为 n=17/市场，AH -1.44%、OU -23.41%，但训练输入时间证据不足，不能用于主 OOS 结论。以上均未达到 10,000 场验证目标。公开 M4 MR1 旧基准 AH -2.8276%、OU -2.9706%（各 1,563 场）不可与本轮小样本直接比较。

## 下一步数据要求

要继续到 10,000 场 M5 Crown 回测，需要至少 10,000 个唯一比赛的精确 UTC kickoff、唯一 fixture 身份、Crown 原始两侧 AH/OU 线价及可信赛前 capture/received UTC、FT 来源/时间，以及现存数据授权覆盖 M5 研究的记录。当前本机已有历史 snapshot 只能支持公开报告中的聚合结果，无法发布私有逐场价格。若没有具备报价时间证据的历史数据，只能先以已许可的未来采集逐步建立前瞻影子数据，不能倒填历史价格。

满足数据条件后，M5 必须先固化一个新的独立基线；按 UTC 日期扩展训练/滚动预测，模型参数仅用已发生赛果，避免同日及未来泄漏。AH/OU 分别输出概率校准、Log Loss、Brier、样本数、赛季拆分及 Crown 覆盖。收益回测采用相同 fixture 集合比较可比模型，并按亚洲盘半赢/半输/走水结算；不通过事后门槛筛选追 ROI。
