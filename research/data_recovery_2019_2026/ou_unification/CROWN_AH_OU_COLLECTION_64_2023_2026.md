# Crown AH+OU 64 联赛采集进度（2023—2026）

更新时间：2026-11-22 07:23 UTC
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
| Crown AH 开盘+收盘 | 32,449 | 15,653 | 0 场 FID |
| Crown AH 变化序列 | 36,342 | 11,760 | 0 场 FID |
| Crown OU 开盘+收盘 | 32,445 | 15,657 | 0 场 FID |
| Crown OU 变化序列 | 4,944 | 43,158 | 55 场 FID |

截至07:21:59 UTC，OU变化序列覆盖4,944场；自动请求队列43,031场。按覆盖项计算的缺口另含近期HTTP响应未返回Crown bookmaker的FID；不把这些单次无报价状态推断为永久无盘。

## 一次请求合并 AH/OU 的实测

实际调用 TotalCorner Crown：`columns=asianList,goalList`。2023 年 FID `128294217` 的 HTTP 200 / API success 响应同时含：

- AH `asian_list` 97 行，`asian.open/close` 各 1 行。
- OU `goal_list` 89 行，`goal.open/close` 各 1 行。
- 响应 SHA256：`0c84b0976ad28b6a69c0dc475a8f92e868da0a4b902823e0d5973c5d33c56ac4`。
- 实际接收时间：`2026-11-22T06:21:46.333966Z`。
- 原始响应保存在统一 Crown raw store：`/Users/mac/QuantAsiaDesk/data/crown_quote_store/raw/historical/128294217/0c84b0976ad28b6a69c0dc475a8f92e868da0a4b902823e0d5973c5d33c56ac4.json`。

另外两场 2023 FID `128644918`、`128644920` 也各由同一响应取得 AH/OU 开收盘与变化序列。该请求把 AH 和 OU 两次独立请求合成每个 FID 一次，响应中的空字段不会当作完整报价。

截至07:23 UTC，采集日志218条、191个唯一FID，最新状态134个HTTP 200响应未含Crown bookmaker、57个AH/OU双市场完整、0个未解决传输失败。217次请求attempt中165成功、51 `IncompleteRead`、1 `TOO_MANY_REQUEST`。19个FID曾出现传输/API错误，已全部在后续请求中恢复；1次限流后退避重试成功。报价齐全成功响应中位大小10,609字节；无Crown响应中位392.5字节。诊断代码已加入截断响应的`partial_bytes`和`expected_remaining_bytes`日志字段，当前运行进程早于此改动，尚未产生新字段；下一安全窗口新进程将启用。请求启动间隔仍为5.2秒，不增加并发。

## OU 独立任务接续

已读取并检查 `full_history_backfill_20261121/collect_crown_ou_history.py`、追加式网络日志和 `crown_ou_raw/`。该独立 OU 任务记录 430 行：424 `OU_SUMMARY_SAVED`、4 `NO_CROWN_OU`、2 `FETCH_FAILED`。全部现存原始数据已导入共享 SQLite `crown_ou_source` / `crown_ou_quote`；导入前后校验响应 SHA 和 FID 身份均无差异。独立 OU 采集进程已停止，今后由合并采集器按单个 Crown 响应同时写 AH、OU。旧数据保留，不删除。

## 采集进程与安全窗口

新的 `safe_window_combined_driver.py` 于2026-11-22 06:21 UTC启动。检测到MR1/统一结算计划任务时等待或中断当前批次；生产任务结束并空闲12秒后再续采。07:21:59 UTC队列43,031，覆盖为AH开收盘32,449、AH变化36,342、OU开收盘32,445、OU变化4,944。安全驱动PID 49373运行；采集子进程PID 61886于07:22:43 UTC因MR1计划任务暂停，等待安全窗口续采。失败FID在后续队列重建中重试。

当前请求节奏为5.2秒，单市场分开请求理论上对同一比赛需要两次网络请求；合并后每场一次。按43,031个当前待请求FID粗估，若每场均需一请求且严格每5.2秒，约62.0小时；日历时间还会受安全窗口及失败重试影响。估算仅用于容量说明，不代表已完成。

## 开源工具核查

- [OddsHarvester](https://github.com/jordantete/OddsHarvester)：支持从 OddsPortal 获取历史赔率、指定 bookmaker、亚洲盘/大小球及赔率历史；来源不是 TotalCorner/Crown，未证明 Crown 报价覆盖与原始 HTTP/事件时间可对齐，因此不作为 Crown 数据源或本轮部署工具。
- [oddsportal_scraper](https://github.com/djibril-marega/oddsportal_scraper)：当前 README 描述赛事结果及 1X2 开收盘，不能补齐 Crown AH/OU 路径。
- [soccerdata MatchHistory](https://soccerdata.readthedocs.io/en/stable/reference/matchhistory.html)：数据源是 Football-Data.co.uk CSV；可含其他来源比赛信息，但不是 Crown 赔率，本地 2023—2026目标比分已由 TotalCorner `full` 状态覆盖，本轮不部署。

## 工程边界和下一检查点

只新增研究目录内的恢复/统一采集代码及本检查点。所有网络请求均取自固定 64 联赛、2023—2026 FID 队列；2019—2022 仅保留已有数据，不进入此轮请求。保留外部数据库已有其他联赛数据，不新请求、不删除。未改 M8/其他正式模型、Telegram、正式账本或生产调度。

代码：`collect_crown_ah_ou_64.py`、`integrate_crown_ou_history.py`、`safe_window_combined_driver.py`。下一次检查需从共享 SQLite 重新生成逐年/逐联赛市场覆盖，核对日志—raw SHA—收件时间—两市场行数，并报告重试后有效吞吐及剩余 FID。任务尚未完成。

本公开提交的执行快照：`crown_64_collection_checkpoint_20261122T0723Z.jsonl`（218条逐场/状态记录）；安全窗口快照：`crown_64_driver_checkpoint_20261122T0723Z.jsonl`；传输诊断：`crown_64_transport_audit_20261122T0723Z.json`；逐年/逐联赛覆盖：`crown_64_coverage_latest.json`；输入输出SHA：`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T0723Z.txt`。正在增长的主日志与请求队列留作本地续采文件，队列可从固定赛事清单和共享SQLite重新生成。


## 2026-11-22 07:35 UTC：2023—2026续采检查点

- 本轮核验继续限定固定64个Provider League ID与2023—2026年，共48,102个既有FID；赛程SHA仍为`a9d48b40cba84e5bf49f490b4b25bada9bc12a6266e6da0eed51c063166b8258`。日志里截至本检查点231个唯一FID全部属于2023年、覆盖20个批准联赛；越界FID为0。历史赛程/FT库存没有重新下载或改变。
- 使用SQLite只读查询事务读取一致快照（`PRAGMA query_only=ON`、BEGIN；未写共享库）。07:35:13Z覆盖为：AH开收盘32,449（缺15,653）、AH变化36,342（缺11,760）、OU开收盘32,445（缺15,657）、OU变化4,951（缺43,151）。相比07:23已提交检查点，唯有OU变化净覆盖增加7场；各报价层不同FID可相交，缺失数不相加。分年覆盖在`crown_64_coverage_snapshot_20261122T0735Z.json`。
- 07:31:59Z安全驱动重建缺口队列并启动采集子进程PID 64219，队列43,010个FID；07:35时父驱动PID 49373和子进程仍活跃，单次Crown联合请求间隔5.2秒。07:31:59—07:34:36的21个唯一FID响应约8.9场/分钟，包含传输重试和限流退避；按5.2秒间隔的无重试上限约11.5场/分钟。按当前队列计算约62.1小时纯请求时间，不含重试、调度安全窗口和日历停顿。
- 累计传输审计（日志在07:35Z采样）：259条日志记录、229个唯一FID，267次HTTP/API尝试中203成功、59次`IncompleteRead`、5次`TOO_MANY_REQUEST`；25个FID曾有传输/API错误且随后全部成功，当前日志无未恢复的传输失败。8条新式截断诊断字段已出现，56条旧错误记录因采集进程版本较旧而无该字段。带Crown盘口的响应和无Crown bookmaker响应大小差异仍然明显；该观察不证明无报价的永久性。
- safe-window因MR1或统一结算作业运行暂停采集，并在作业退出后自动续跑；当前已于07:31:59Z续跑。本轮没有停止生产任务或绕过空闲窗口。继续使用经实测有效的`columns=asianList,goalList`合并响应，原始响应、SHA256、HTTP接收时间以及source事件时间仍分别保存；该模式为历史回取，非真实赛前收据。
- 本次逐场快照、driver事件快照、覆盖JSON、传输审计及SHA清单一并提交。统一采集/存储仍未完成，不把空响应记成已取得盘口，不改请求间隔、正式生产模型、Telegram、正式账本或调度。

### 运行态更新（2026-11-22 07:35:31 UTC）

07:35:31 UTC，安全窗口检测到统一结算任务PID 65004，已暂停采集子进程PID 64219；安全驱动PID 49373仍运行，等待结算/MR1作业退出后重新排队续采。该暂停发生在07:35:13 UTC一致覆盖快照之后；不要把当时的“子进程运行中”误读为当前仍在请求。队列将在恢复时重建。

## 2026-11-22 07:41 UTC：安全窗口恢复后的OU movement新增

- 统一结算/MR1任务结束后，driver于07:39:57 UTC重建队列并以PID 66356恢复。此次队列待请求FID为42,981个；覆盖字段与07:39:54一致只读数据库快照相符（该快照OU movement 4,953）。
- 07:41:17 UTC一致只读快照显示AH开收盘32,449、AH movement36,342、OU开收盘32,445、OU movement4,960；OU movement新增7场，分年覆盖为2023 71、2024 0、2025 1,111、2026 3,778。field-level原始缺口为15,653、11,760、15,657、43,142。当前采集日志唯一FID 239场，全部在2023年且provider league均在固定64个ID内，越界0。
- 从07:39:57 UTC本轮恢复点到快照，日志出现7个唯一FID，7个响应均含OU变化序列；合并请求也保存同响应内AH summary/movement和OU summary/movement。所有记录带Crown原始响应SHA、实际接收时间和历史模式。此前暂停边界FID `130037617` / `130037627` 的响应SHA均复核匹配raw文件；两场分别保留50、58条`goal_list`，均为历史回取。数据证据见`crown_64_pause_boundary_fids_20261122T0739Z.json`。
- 截至07:41传输审计：270条日志、239唯一FID、280次请求尝试（213成功、61 `IncompleteRead`、6 `TOO_MANY_REQUEST`）；28个遇过传输/API错误的FID全部恢复成功，目前无未恢复失败。最近恢复后新一批请求仍以5.2秒启动间隔运行；不擅自提高频率。
- 安全driver PID 49373与采集PID 66356在快照时活跃。队列规模已从07:31的43,010降至07:39重建的42,981；尚有大规模缺口，纯请求时间仍约62小时级，实际日历时间取决于生产安全窗口和重试。无模型/策略/Telegram/账本/生产调度改动。

## 2026-11-22 07:44 UTC：MR1窗口前续采及暂停记录

- 07:43:43 UTC一致只读SQLite快照：AH开收盘32,449、AH movement36,342、OU开收盘32,445、OU movement4,962；字段缺口分别15,653、11,760、15,657、43,140。固定赛事/可信FT清单仍48,102场。与07:41快照相比OU movement再净增2场。
- 自07:39:57重启队列后，已有32个新的唯一FID取得HTTP/API成功响应（9个双市场完整、23个成功HTTP200但响应无Crown盘口）；这些都在固定64联赛和2023—2026年内。逐场合计日志265唯一FID，全部均为2023年、越界0。
- 07:43:45 UTC，safe-window检测到MR1任务PID67291，暂停collector PID66356；safe-window父进程PID49373仍活跃。一个在暂停边界的FID `130037365` 留下`PAUSED_FOR_SCHEDULED_JOB`/`IncompleteRead`日志，不记作无盘口；collector重启后会因该失败未列入终态集合而重新进入队列。
- 07:44传输日志审计累计311次尝试：238 success、67 `IncompleteRead`、6 `TOO_MANY_REQUEST`。31个曾遇错误的FID里30个已恢复；唯一剩余记录为安全暂停造成的可重试中断。原始响应SHA、收件时间和市场行数仍逐场保留。队列最新完整重建仍为07:39的42,981，因07:43暂停发生在整批循环内，当前剩余数待安全窗口恢复后重建，不用估数替代。
- 快照见`crown_64_coverage_snapshot_20261122T0743Z.json`、逐场/driver快照与`crown_64_transport_audit_20261122T0744Z.json`。只有当前采集相关工作，未修改正式模型、Telegram、账本、生产采集频率或调度规则。

## 2026-11-22 07:51 UTC：恢复一轮后再次因MR1安全暂停

- 07:51:42 UTC一致只读快照：48,102个固定赛程FID及可信full FT；AH开收盘32,449、AH movement36,342、OU开收盘32,445、OU movement4,965。字段缺口分别15,653、11,760、15,657、43,137。OU movement比07:43快照再增加3场。
- 07:49:02队列重建后，11个唯一FID收到成功HTTP/API响应（3场双市场完整、8场无Crown bookmaker数据）。3场新增OU movement FID为`130037365`、`130036441`、`130037117`；逐条raw文件SHA256均与SQLite/采集日志一致，见`crown_64_collection_checkpoint_20261122T0751Z.jsonl`及原始响应路径。暂停边界FID `130037365` 的07:44失败已在本轮恢复为双市场完整，AH movement 130行、OU `goal_list` 120行。
- 07:50:59 UTC driver检测到MR1计划任务PID 69022，暂停collector PID 68638；safe-window PID 49373仍运行。FID `130036444` 的一次请求因该暂停记录`PAUSED_FOR_SCHEDULED_JOB`，保留可重试状态，不当作无报价。最新重建队列仍是42,949，待MR1退出后自动重建实际余量。
- 累计传输审计截至07:51：328次请求attempt，249成功、73次`IncompleteRead`、6次`TOO_MANY_REQUEST`；33个有错误FID中32个恢复，剩余1个是上述安全暂停中断。所有范围审计仍为固定64 ID/2023—2026；当前日志276唯一FID均为2023年、越界0。

## 2026-11-22 07:55 UTC：MR1/结算窗口前新增两场可核市场报价

- 07:54:56 UTC一致只读覆盖快照：48,102个固定赛程/可信full FT FID；AH开收盘32,449、AH movement36,342、OU开收盘32,445、OU movement4,967。field-level缺口15,653、11,760、15,657、43,135；较07:51快照OU movement新增2场。
- 07:49—07:53本批在结算再次暂停前完成11个唯一FID的成功响应，3个双市场完整、8个无Crown报价。两条新覆盖报价是FID `130036444`（league 1，AH summary2/AH movement61/OU summary2/OU movement74）和FID `130037120`（league14，AH summary2/AH movement73/OU summary2/OU movement33）；两条raw文件SHA均经独立哈希核实。被暂停边界的FID `130036444` 前次失败已实际恢复。
- safe-window父进程PID49373仍活跃；统一结算PID69648及其M3 settlement子进程PID69884运行，采集子进程已安全暂停。最近一次队列重建为07:53:15 UTC、42,938个待请求；下一队列待窗口退出后重建，暂停中断不认作无盘口。
- 截至07:55传输审计累计334次尝试（255成功、73 `IncompleteRead`、6 `TOO_MANY_REQUEST`），33个遇错FID全部恢复，未恢复失败为0。原始日志281唯一FID全在批准范围、年份2023，越界0。完整证据在同目录07:54/07:55检查点及SHA manifest。
