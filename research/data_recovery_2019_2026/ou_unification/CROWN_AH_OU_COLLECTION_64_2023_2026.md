# Crown AH+OU 64 联赛采集进度（2023—2026）

更新时间：2026-11-22 06:35 UTC
性质：历史采集与采集效率工程；不是模型研究、回测或正式实战。

## 范围

范围来自 `research-work/crown-drop-expanded-62/schedule_universe.jsonl` 中原 49 联赛加扩展 15 联赛的固定 Provider League ID 集合。代码对全部来源行校验 64 个 ID，再只选择 2023—2026 年赛事。ID：

`1,10,12,14,16,25,29,31,33,35,37,40,43,45,46,47,48,51,52,55,60,61,62,66,68,70,73,75,85,88,109,116,129,141,145,152,177,262,290,297,298,299,303,314,319,328,330,332,345,378,670,779,979,1439,8172,8293,10480,10714,11498,19290,26540,27388,27389,27390`.

当前赛程库存：48,102 个唯一 FID，2023 年 14,673、2024 年 14,553、2025 年 14,631、2026 年 4,245（现有赛程截止 2026-06-30）。这 48,102 场都在本次采集目标内。TotalCorner 本地赛程页中 48,102 场均有 `status=full` 和双方比分；不把比分字段缺失或状态不明的赛事默认为完场。

## 已有覆盖和缺口

以下按唯一 FID 统计；“变化序列”要求至少一条市场变化行。开盘/收盘与变化序列分开计数。覆盖数据来自共享 SQLite `crown_quotes.sqlite3`，仅计 64 联赛 2023—2026。

| 数据项 | 已有 | 缺失 | 本轮新增（截至本检查点） |
|---|---:|---:|---:|
| 64 联赛赛程 | 48,102 | 0 | 0 |
| TotalCorner `full` 完场比分 | 48,102 | 0 | 0 |
| Crown AH 开盘+收盘 | 32,449 | 15,653 | 3 场 FID |
| Crown AH 变化序列 | 36,342 | 11,760 | 3 场 FID |
| Crown OU 开盘+收盘 | 32,445 | 15,657 | 3 场 FID |
| Crown OU 变化序列 | 4,901 | 43,201 | 12 场 FID |

截至06:35 UTC，四项市场数据齐全的唯一 FID 为4,901；尚未完整的FID为43,201，其中24场在本轮一次采集后收到HTTP 200但响应没有Crown报价，1场最新状态仍是传输失败、可重试。缺失不是“无盘口”的推断；仅将响应实际不含Crown bookmaker的记录标为`NO_CROWN_MARKET_DATA`。

## 一次请求合并 AH/OU 的实测

实际调用 TotalCorner Crown：`columns=asianList,goalList`。2023 年 FID `128294217` 的 HTTP 200 / API success 响应同时含：

- AH `asian_list` 97 行，`asian.open/close` 各 1 行。
- OU `goal_list` 89 行，`goal.open/close` 各 1 行。
- 响应 SHA256：`0c84b0976ad28b6a69c0dc475a8f92e868da0a4b902823e0d5973c5d33c56ac4`。
- 实际接收时间：`2026-11-22T06:21:46.333966Z`。
- 原始响应保存在统一 Crown raw store：`/Users/mac/QuantAsiaDesk/data/crown_quote_store/raw/historical/128294217/0c84b0976ad28b6a69c0dc475a8f92e868da0a4b902823e0d5973c5d33c56ac4.json`。

另外两场 2023 FID `128644918`、`128644920` 也各由同一响应取得 AH/OU 开收盘与变化序列。该请求把 AH 和 OU 两次独立请求合成每个 FID 一次，响应中的空字段不会当作完整报价。

至06:35 UTC，37个唯一FID已有采集尝试结果：12个四项齐全、24个成功响应但无Crown bookmaker、1个请求仍失败待重试。合并接口已在2023样本实证。首轮旧写入路径单场端到端耗时7.61秒；改用共享writer/单事务后，28份HTTP 200响应平均网络耗时1.223秒，平均数据库写入0.00313秒，最高0.0089秒。配置请求启动间隔5.2秒；本样本含重试与无市场响应，不据此推断长期有效速率。已增加逐次请求时间与错误记录，便于持续核对速率/失败类型。不以并发绕过服务商限制。

## OU 独立任务接续

已读取并检查 `full_history_backfill_20261121/collect_crown_ou_history.py`、追加式网络日志和 `crown_ou_raw/`。该独立 OU 任务记录 430 行：424 `OU_SUMMARY_SAVED`、4 `NO_CROWN_OU`、2 `FETCH_FAILED`。全部现存原始数据已导入共享 SQLite `crown_ou_source` / `crown_ou_quote`；导入前后校验响应 SHA 和 FID 身份均无差异。独立 OU 采集进程已停止，今后由合并采集器按单个 Crown 响应同时写 AH、OU。旧数据保留，不删除。

## 采集进程与安全窗口

新的 `safe_window_combined_driver.py` 于2026-11-22 06:21 UTC启动。检测到MR1/统一结算计划任务时等待或中断当前批次；生产任务结束并空闲12秒后再续采。当前运行结果及单场原始SHA追加到`crown_64_combined_collection.jsonl`，安全窗口状态记入`crown_64_combined_driver_events.jsonl`。首次待处理队列43,213场，当前市场数据缺口43,201场；续采会重建队列，排除已完整报价和已有无Crown响应记录的FID，失败仍可重试。当前安全驱动与采集子进程正在运行。

当前请求节奏为5.2秒，单市场分开请求理论上对同一场比赛需要两次网络请求；合并后每场一次。按约43,177个未终态请求FID估算，纯5.2秒节奏约62.4小时，日历时间还会受计划任务安全窗口和失败重试影响。估算仅用于容量说明，不代表已完成。

## 开源工具核查

- [OddsHarvester](https://github.com/jordantete/OddsHarvester)：支持从 OddsPortal 获取历史赔率、指定 bookmaker、亚洲盘/大小球及赔率历史；来源不是 TotalCorner/Crown，未证明 Crown 报价覆盖与原始 HTTP/事件时间可对齐，因此不作为 Crown 数据源或本轮部署工具。
- [oddsportal_scraper](https://github.com/djibril-marega/oddsportal_scraper)：当前 README 描述赛事结果及 1X2 开收盘，不能补齐 Crown AH/OU 路径。
- [soccerdata MatchHistory](https://soccerdata.readthedocs.io/en/stable/reference/matchhistory.html)：数据源是 Football-Data.co.uk CSV；可含其他来源比赛信息，但不是 Crown 赔率，本地 2023—2026目标比分已由 TotalCorner `full` 状态覆盖，本轮不部署。

## 工程边界和下一检查点

只新增研究目录内的恢复/统一采集代码及本检查点。所有网络请求均取自固定 64 联赛、2023—2026 FID 队列；2019—2022 仅保留已有数据，不进入此轮请求。保留外部数据库已有其他联赛数据，不新请求、不删除。未改 M8/其他正式模型、Telegram、正式账本或生产调度。

代码：`collect_crown_ah_ou_64.py`、`integrate_crown_ou_history.py`、`safe_window_combined_driver.py`。下一次检查需从共享 SQLite 重新生成逐年/逐联赛市场覆盖，核对日志—raw SHA—收件时间—两市场行数，并报告重试后有效吞吐及剩余 FID。任务尚未完成。

本公开提交的执行快照：`crown_64_collection_checkpoint_20261122T0635Z.jsonl`（43条逐场/状态记录）；安全窗口快照：`crown_64_driver_checkpoint_20261122T0635Z.jsonl`；逐年/逐联赛覆盖：`crown_64_coverage_latest.json`；输入输出SHA：`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T0635Z.txt`。正在增长的主日志与请求队列留作本地续采文件，队列可从固定赛事清单和共享SQLite重新生成。
