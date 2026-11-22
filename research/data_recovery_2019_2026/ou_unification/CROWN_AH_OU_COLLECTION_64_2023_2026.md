# Crown AH+OU 64 联赛采集进度（2023—2026）

更新时间：2026-11-22 09:59 UTC（初始覆盖表为07:23 UTC基线，后续状态见逐时检查点）
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


## 2026-11-22 08:03 UTC：结算窗口后自动续采及覆盖增量

- 08:00:12 UTC safe-window PID 49373 在上一轮统一结算结束后自动重建固定范围缺口队列并恢复collector PID 71205，队列42,932个FID；单场仍为一次`columns=asianList,goalList`请求、启动间隔5.2秒。
- 08:03 UTC复核覆盖：48,102场目标赛程及可信full FT；AH开收盘32,449（缺15,653）、AH变化36,342（缺11,760）、OU开收盘32,445（缺15,657）、OU变化4,972（缺43,130）。相较07:54一致快照，OU变化序列净增5场，其他字段计数不变。逐年覆盖见`crown_64_coverage_snapshot_20261122T0803Z.json`。字段缺口是逐市场覆盖缺口；队列会跳过已尝试且HTTP/API成功但未返回Crown市场的终态FID，因此与待请求队列数不相等。
- 08:00:21—08:02:16 UTC的16个成功响应覆盖16个不同FID，其中5个为AH+OU双市场报价、11个HTTP/API成功但回包无Crown市场。5个双市场逐场AH/OU summary和movement数量及原始响应SHA已独立核验，见`crown_64_verified_increment_20261122T0803Z.json`。
- 另有FID `130037122`在08:02:20—08:02:42遇3次`IncompleteRead`，08:02:53因统一结算PID 71744触发安全暂停；该FID标记`PAUSED_FOR_SCHEDULED_JOB`并保留重试，不记成无报价。暂停时safe-window PID 49373仍在运行。恢复窗口成功回包速度为16场/约115秒，即约7.81场/分钟；此前独立实测21场/约141秒为8.9场/分钟。两段波动没有证明吞吐提升；硬请求间隔上限约11.54场/分钟，双市场合并仍把原本AH、OU分开请求的每FID网络请求数减半。当前耗时仍主要来自5.2秒请求间隔、连接响应和重试/安全窗口；单场SQLite写入约0.001—0.016秒，非当前瓶颈。未提升频率或并发。
- 截至08:03传输审计累计357次attempt：271 success、80 `IncompleteRead`、6 `TOO_MANY_REQUEST`；36个遇过错误的FID中35个已成功恢复，剩余1个为上述安全暂停可重试FID。报告及全量审计见`crown_64_transport_audit_20261122T0803Z.json`。
- independent settlement窗口每次均触发暂停，未中断任何MR1/结算生产任务；safe-window会等待作业退出和安静期后重建队列继续。统一库存仍是2023—2026年固定64联赛，未触及2019—2022或范围外赛事。


## 2026-11-22 08:12 UTC：第二批自动续采与运输重试

- 08:07:07 UTC driver PID49373在结算窗口后重建队列为42,916并启动collector PID72721。08:11:49 UTC，MR1 PID73748及统一结算PID73753出现，采集子进程按既有安全窗口暂停；driver仍活跃等待这些任务退出。下次恢复会重建队列，当前不把08:07队列冒充为暂停时准确剩余数。
- 本批覆盖31个成功响应FID（2023年队列先行），其中13个返回Crown AH+OU四层数据，18个HTTP/API成功但没有Crown AH/OU报价；另3个FID请求失败或被暂停，保留重试。13条双市场记录的raw文件SHA逐条复核与日志一致。
- 08:12 UTC只读数据库快照：目标赛程48,102场；AH开收盘32,449、AH movement36,342、OU开收盘32,445、OU movement4,985；相较08:03 OU movement +13，其他字段不变。field-level缺口15,653、11,760、15,657、43,117。快照、逐场响应、计划暂停事件、传输审计及SHA均在T0812Z证据文件。
- 本批31个成功FID在首末成功响应间隔约236秒，按间隔计约7.63场/分钟；截至08:12没有证据表明吞吐高于先前21场/约141秒的8.9场/分钟窗口。5.2秒单次请求启动间隔理论上限11.54场/分钟；遇到IncompleteRead的单FID需按6/11/16秒退避，重试叠加到该速率上。SQLite每场写入仍为毫秒级。AH与OU联合请求较两次分开请求将每FID网络请求数减半，但不提高服务商请求频率。
- 截至本快照累计402次请求attempt：302 success、94 `IncompleteRead`、6 `TOO_MANY_REQUEST`；41个经历错误的FID中38个已恢复，3个失败仍待下一窗口重试（FID `130037122`、`130037654`、`130042375`），均不作为无报价计数。最新运输审计与重试明细见`crown_64_transport_audit_20261122T0812Z.json`及`crown_64_verified_increment_20261122T0812Z.json`。
- 本轮未调整5.2秒间隔、并发、服务商限流或生产流程；未改生产模型、TG、账本。固定范围仍为64联赛及2023—2026，其他年份/联赛未请求。


## 2026-11-22 08:53 UTC：2023—2026负责人接续采集检查点

- 任务范围继续固定为原64个Provider League ID、2023—2026赛程共48,102个FID。队列按现有赛程顺序推进，截至本检查点访问到的请求均为2023年；没有请求2019—2022或64联赛以外的赛事。完整年份队列量在本轮前核对为2023:14,293、2024:14,553、2025:13,520、2026:467个未尝试/未终态项；队列会随共享SQLite覆盖及成功HTTP状态重建。
- safe-window driver PID 49373持续运行，按5.2秒请求起始间隔，只在MR1/统一结算任务空闲窗口运行。08:39:53队列42,782；collector PID 79779在08:43:29因MR1 PID 80582安全暂停。该段42个FID均取得HTTP响应（14 `BOTH_MARKETS`、28 `NO_CROWN_MARKET_DATA`），42份raw SHA全部一致、范围违规0。08:47:31队列降至42,740，覆盖OH/OU字段分别为AH开收盘32,449、AH走势36,342、OU开收盘32,445、OU走势5,032；相对08:39:53只有OU走势增加14。
- PID 79779退出后，08:47:31—08:49:31 collector PID 81472又完成24个不同FID（7 `BOTH_MARKETS`、17无Crown报价），24/24 raw SHA匹配，范围违规0。08:51:43下一次队列重建为42,716，数据库覆盖为AH开收盘32,449、AH走势36,342、OU开收盘32,445、OU走势5,039，较08:47 OU走势再增7。
- 08:51:43—08:52:17 collector PID 82359追加7个FID响应（5 `BOTH_MARKETS`、2无Crown报价），7/7 raw SHA匹配，范围违规0。08:52:17遇统一结算PID 82484后自动安全暂停；driver未退出，等待任务完成和12秒空闲期后重建队列续采。此7场窗口后的当前完整覆盖数等待下一次队列重建，不把08:51:43计数冒充为更新后的覆盖。
- 累积传输审计至08:52为591次attempt：478成功、107 `IncompleteRead`、6 `TOO_MANY_REQUEST`。不把传输失败标为无盘口；失败状态可由重建队列重试。最近三段连续无重试的请求间隔接近5.2秒上限，对应理论上限约11.54个FID/分钟；未提高频率、未绕过服务商限流。请求仍用实测可同时返回AH/OU的`columns=asianList,goalList`，并按每场缺失的市场及open/close/movement类别选择请求字段。
- 响应检查点、raw SHA结果、覆盖及传输审计见同目录`crown_64_collection_checkpoint_20261122T0849Z.jsonl`、`crown_64_collection_checkpoint_20261122T0852Z.jsonl`、相应`crown_64_driver_checkpoint_*`、`crown_64_verified_increment_*`、`crown_64_coverage_snapshot_*`和`crown_64_transport_audit_20261122T0852Z.json`。T0841覆盖快照的采集时点已按文件真实mtime修正为08:41:10Z。
- 历史回取统一标记为historical，不称为真实赛前收据。OU独立采集进程当前未运行；AH+OU合并采集器复用旧响应与统一SQLite。没有模型研究、生产配置、TG派单或正式账本变更。


## 2026-11-22 09:03 UTC：安全窗口续采增量

| 数据层 | 已有 / 48,102 | 缺失 | 本轮新增（截至最后可确认队列） |
|---|---:|---:|---:|
| 固定64联赛赛程 | 48,102 | 0 | 0 |
| 可信 full FT | 48,102 | 0 | 0 |
| Crown AH open/close | 32,449 | 15,653 | 0 |
| Crown AH movement | 36,342 | 11,760 | 0 |
| Crown OU open/close | 32,445 | 15,657 | 0 |
| Crown OU movement | 5,048（08:57:44Z队列审计） | 43,054 | +6（后续逐场响应推算，待下一队列审计确认） |

- 08:55:13Z safe-window重建队列42,709时，覆盖为AH open/close 32,449、AH movement 36,342、OU open/close 32,445、OU movement 5,044。collector PID83124在08:56:28Z因MR1 PID83376暂停；该窗15个唯一FID全部有HTTP响应，4 `BOTH_MARKETS`、11 `NO_CROWN_MARKET_DATA`，15份raw SHA均匹配且越界0。08:57:44Z下次队列审计为42,694，OU movement增至5,048（+4）。
- collector PID83699于08:57:44Z恢复；08:59:59Z因统一结算PID84224再次安全暂停。该段27个唯一FID收到响应，6 `BOTH_MARKETS`、21 `NO_CROWN_MARKET_DATA`，raw SHA 27/27匹配、越界0。根据请求前缺失quote-kind与已保存kind逐FID重建，该段预计再新增6个OU movement；预计计数5,054，**等待安全队列重建确认**。
- 该段首个响应08:57:48Z、末个09:00:04Z；26个间隔/136秒约11.47个FID/分钟，接近5.2秒间隔的理论上限11.54。服务响应中位约1.2秒，SQLite逐行写入毫秒级；并发/加速请求不改变5.2秒限制。本次没有改变频率。
- 截至09:00审计累计633次attempt：520 success、107 `IncompleteRead`、6 `TOO_MANY_REQUEST`。空Crown响应仍保留原始响应并与真实无报价分开标识；传输失败不标记为无报价。
- 08:59:59Z后统一结算PID84224退出前又出现MR1 PID84765，safe-window父进程PID49373仍在运行并继续等待；未中断任何计划任务。后续队列会在计划任务清空且满足安静期后自动重建。
- T0902、T0901逐场响应/driver检查点、逐响应raw SHA与覆盖重建、T0900传输审计见同目录；本阶段仍只做历史采集，不做模型/策略研究，不改生产模型、TG、正式账本或生产调度。
- 08:57队列42,694项按5.2秒间隔计算理论最低请求时长约61.7小时；这是连续运行、不含安全窗口暂停与失败重试的请求时间估算，不是日历完成承诺。终态HTTP200但回包无Crown报价的FID不进入重试队列，仍作为无报价覆盖缺口单独留存。


## 2026-11-22 09:13 UTC：安全窗口续采增量

| 数据类型 | 已有 / 48,102 | 缺失 | 本段新增 |
|---|---:|---:|---:|
| 固定64联赛赛程 | 48,102 | 0 | 0 |
| 可信 full FT | 48,102 | 0 | 0 |
| Crown AH开收盘 | 32,449 | 15,653 | 0 |
| Crown AH变化序列 | 36,342 | 11,760 | 0 |
| Crown OU开收盘 | 32,445 | 15,657 | 0 |
| Crown OU变化序列 | 5,074（09:10:52 UTC队列重建） | 43,028（该基线） | +7（逐场核验，等待下一队列重建确认） |

- 固定范围和数据源未变：64个Provider League ID、2023—2026、48,102个已有FID；只读复用赛程与可信比分，不抓其他年份或联赛。安全driver PID 49373仍在运行，09:10:52 UTC重建缺口队列42,621后启动collector PID 86648，当前按顺序处理2023赛事；请求间隔5.2秒。
- 从09:08:38至09:13:50 UTC增量窗口核验33个唯一FID：7个FID在统一库中均已有AH与OU记录且本次只新增OU走势、26个HTTP/API成功但无Crown市场报价；33份原始响应SHA均通过，范围外FID 0，重复FID 0。7个成功报价都只补入OU movement；AH和开收盘未增加。相关逐场证据和SHA在`crown_64_collection_checkpoint_20261122T0913Z.jsonl`及`crown_64_verified_increment_20261122T0913Z.json`；执行文件、固定赛事清单及33份原始响应SHA列入`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T0913Z.txt`。
- 最近累计传输审计717次attempt：602 success、109 `IncompleteRead`、6 `TOO_MANY_REQUEST`；45个曾遇错误的FID均已恢复，当前可重试失败0。T0913统计见`crown_64_transport_audit_20261122T0913Z.json`。
- 该33场从首个响应09:10:56.661Z至末个09:13:46.540Z，32个间隔约169.9秒，约11.30 FID/分钟，接近5.2秒节奏理论上限11.54。下一队列审计前由缺失quote-kind回推OU movement覆盖5,081；权威SQLite计数待driver自动队列重建确认。纯5.2秒间隔下42,621项约61.56小时，不含安全暂停和重试，不是日历完成承诺。
- 合并`asianList,goalList`仍是一FID一次请求、按已缺市场/quote-kind选择请求项。历史回取保存源报价时间、实际HTTP接收UTC、原始响应SHA；不把历史回取标为真实赛前实收。未修改生产模型、Telegram、正式账本或生产调度。


## 2026-11-22 09:20 UTC：暂停恢复后续采增量

| 数据类型 | 权威已有 / 48,102 | 缺失（基线） | 基线后新增 |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | 0 |
| 可信 full FT | 48,102 | 0 | 0 |
| Crown AH开收盘 | 32,449 | 15,653 | 0 |
| Crown AH变化序列 | 36,342 | 11,760 | 0 |
| Crown OU开收盘 | 32,445 | 15,657 | 0 |
| Crown OU变化序列 | 5,082（09:18:14 UTC队列重建） | 43,020 | +6（09:20增量内，等待下一次队列重建） |

- 固定64联赛2023—2026范围不变。MR1及统一结算运行期间safe-window于09:14:26 UTC暂停collector；作业结束后09:18:14 UTC自动重建队列并恢复。权威队列42,580，覆盖AH开收盘32,449、AH走势36,342、OU开收盘32,445、OU走势5,082。当前父driver PID49373、collector PID88327运行，间隔5.2秒。
- 从09:18:14队列重建到09:20快照，21个唯一FID收到响应：6个FID在库里已有AH及OU记录（本次均只保存OU movement）、15个HTTP/API成功但无Crown市场报价；raw SHA 21/21通过，FID范围外0，重复0。新增报价种类只有OU movement 6条，AH及开收盘为0；推算OU movement 5,088，等待下一权威队列重建。证据：T0920逐场检查点、增量JSON、覆盖快照。
- T0920累计审计743次attempt：628成功、109 `IncompleteRead`、6 `TOO_MANY_REQUEST`；45个错误FID均已恢复，当前retryable失败0。该窗口首末响应09:18:18.347—09:20:02.471 UTC，20个间隔约104.1秒，折合约11.52请求/分钟，接近5.2秒间隔对应的理论上限11.54/分钟。纯请求间隔下42,580项约61.5小时，未计安全暂停/重试，不是日历完成承诺。
- 文件SHA和本段21个原始响应SHA见`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T0920Z.txt`。回取数据保持historical身份；未触碰正式模型、Telegram、账本或调度。


## 2026-11-22 09:26 UTC：继续恢复与队列检查

| 数据类型 | 已有 / 48,102 | 缺失 | 本段新增 |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | 0 |
| 可信 full FT | 48,102 | 0 | 0 |
| Crown AH开收盘 | 32,449 | 15,653 | 0 |
| Crown AH变化序列 | 36,342 | 11,760 | 0 |
| Crown OU开收盘 | 32,445 | 15,657 | 0 |
| Crown OU变化序列 | 5,092（09:25:52 UTC权威重建） | 43,010 | +3（截至T0926快照；该窗口另有4条发生在重建前） |

- 09:21:36 UTC MR1安全暂停后，driver PID49373等待既有任务完成；09:25:52 UTC重建队列后自动恢复collector PID90068。队列从42,580减至42,540，Crown OU走势从5,082增至5,092；AH和开收盘覆盖不变。当前队列仍只包括固定64联赛2023—2026缺口。
- 自T0920快照创建09:20:05.501 UTC后共核验28个唯一FID（7个统一库中AH/OU均有记录、21个成功响应没有Crown报价）。逐场raw SHA 28/28匹配，范围外0、重复0；该段新写入7条OU movement，其余AH/OU开收盘与AH走势新增0；按响应时间拆分，19个FID在09:25:52队列重建前完成（其中4条OU走势），9个在重建后完成（其中3条OU走势）。因此T0926快照时重建后走势推算为5,095，待下次队列重建。明细、原始SHA和时间见T0926检查点及增量JSON。
- 累计传输审计771次attempt：656成功、109 `IncompleteRead`、6 `TOO_MANY_REQUEST`；45个遇错FID全部恢复，当前可重试失败0。T0920无计划暂停的短窗口21请求/20间隔/104.1秒，约11.52请求/分钟，接近5.2秒间隔理论上限11.54；生产安全窗口暂停会降低日历吞吐。
- 42,540个当前权威队列项按5.2秒间隔的纯请求时间约61.45小时，不含既有任务暂停及重试，非完成日期承诺。所有新数据均为historical回取，不作实时赛前收据。SHA清单和运行事件见T0926对应文件。


## 2026-11-22 09:30 UTC：MR1暂停窗口的在途批次核验

| 数据类型 | 权威已有 / 48,102 | 缺失 | 权威检查后新增（待重建） |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | 0 |
| 可信 full FT | 48,102 | 0 | 0 |
| Crown AH开收盘 | 32,449 | 15,653 | 0 |
| Crown AH变化序列 | 36,342 | 11,760 | 0 |
| Crown OU开收盘 | 32,445 | 15,657 | 0 |
| Crown OU变化序列 | 5,092（09:25:52 UTC重建） | 43,010 | +9（逐场核验，待下次重建） |

- 09:25:52 UTC队列42,540，collector PID90068以5.2秒间隔恢复；09:28:39 UTC收到MR1 PID90627触发的暂停信号，父driver PID49373仍运行等待；collector完成在途请求后于09:28:43退出。该权威重建包含此前队列批次增加的OU走势10条（5,082→5,092）。
- 从09:25:52队列重建至最后一个在途响应09:28:43，共33个唯一FID：9个在统一数据库中已有AH与OU报价且本次只新增OU movement，24个HTTP/API成功但未返回Crown市场报价。原始响应SHA 33/33匹配；越界FID 0，重复FID 0。AH/OU开收盘和AH movement均未增加。9条新走势的库覆盖推算5,101，待下次权威重建。逐场与身份/时间/SHA见`crown_64_collection_checkpoint_20261122T0930Z.jsonl`和增量JSON。
- 该活动窗口首末响应09:25:56.846—09:28:43.138 UTC，32个间隔约166.3秒，约11.5请求/分钟，接近5.2秒间隔理论上限；MR1安全暂停减少日历吞吐。累计795 attempts：680成功、109 `IncompleteRead`、6 `TOO_MANY_REQUEST`；45个遇错FID全部恢复，当前重试失败0。
- 最新权威待处理队列为42,540项；若扣除本批已终态33个，下一次重建队列预计最多42,507项（队列数待实际确认）。纯5.2秒间隔约61.4小时，不含安全暂停和重试。响应均为historical回取。执行、driver、覆盖、原始响应SHA与传输证据的清单见T0930 manifest。


## 2026-11-22 09:34 UTC：权威队列确认并续采

| 数据类型 | 已有 / 48,102 | 缺失 | 本段新增 |
|---|---:|---:|---:|
| 固定64联赛赛程 | 48,102 | 0 | 0 |
| 可信 full FT | 48,102 | 0 | 0 |
| Crown AH开收盘 | 32,449 | 15,653 | 0 |
| Crown AH变化序列 | 36,342 | 11,760 | 0 |
| Crown OU开收盘 | 32,445 | 15,657 | 0 |
| Crown OU变化序列 | 5,101（09:33:34 UTC权威重建） | 43,001 | +3（重建后暂计） |

- 09:33:34 UTC safe-window自动恢复并重建缺口队列，待请求FID为42,507，覆盖AH开收盘32,449、AH走势36,342、OU开收盘32,445、OU走势5,101。该快照确认T0930批次推算的OU走势+9以及队列减少33均已落库。父driver PID49373仍运行，采集子进程PID91750启动，频率5.2秒。
- T0930检查点创建后至09:34:23，共8个新增唯一FID：3个FID在库中已有AH与OU记录、本次只新增OU movement；5个HTTP/API成功但没有Crown市场报价。8份raw响应SHA全部匹配、FID越界0、重复0。AH、AH走势及OU开收盘新增0；OU movement推算5,104，等待下一次队列重建。逐场字段见T0934 JSONL及increment。
- 最新累积审计804次attempt：688 success、110 `IncompleteRead`、6 `TOO_MANY_REQUEST`；46个错误FID均后来恢复，最新可重试失败0。此前33场活动批次稳定窗口约11.5请求/分钟，接近5.2秒间隔理论上限；安全暂停和失败重试降低日历吞吐，SQLite写入仍为毫秒级。
- 42,507项按5.2秒固定间隔的理论纯请求时间约61.4小时，不含安全暂停和重试，不是完成日期承诺。T0934对应逐场、队列事件、覆盖、传输审计及SHA清单留档。历史回取与真实赛前实收分开。


## 2026-11-22 09:36 UTC：MR1暂停前后批次核验

| 数据类型 | 最新权威已有 / 48,102 | 缺失 | 队列重建后新增（待下次重建） |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | 0 |
| 可信 full FT | 48,102 | 0 | 0 |
| Crown AH开收盘 | 32,449 | 15,653 | 0 |
| Crown AH变化序列 | 36,342 | 11,760 | 0 |
| Crown OU开收盘 | 32,445 | 15,657 | 0 |
| Crown OU变化序列 | 5,101（09:33:34 UTC重建） | 43,001 | +10 |

- 09:33:34 UTC重建队列42,507并启动collector PID91750；09:35:45 UTC MR1 PID92187触发安全暂停，collector完成在途请求后于09:35:47退出，父driver PID49373仍运行等待。批次共处理25个FID（10个在库已有AH及OU、且只新增OU走势；15个成功响应没有Crown报价），raw SHA 25/25通过，范围外0、重复0。AH线、水位变化、AH/OU开收盘新增0；OU movement由5,101推算到5,111，待下次队列重建。
- T0934快照后增量17个唯一FID：7个保存OU movement，10个无Crown市场价；SHA 17/17通过，无范围或重复错误。批次范围和每场收件时间/响应SHA见T0936证据文件。
- 累计821 attempts：705成功、110 `IncompleteRead`、6 `TOO_MANY_REQUEST`；46个错误FID全部已恢复，当前retryable失败0。暂停前25次活动窗口按请求开始间隔约11.18次/分钟，接近固定5.2秒节奏。
- 09:33:34队列42,507项；按本批已完成25项，下一队列预估42,482（待自动重建确认）。纯间隔理论约61.4小时，不计安全暂停和重试。09:35:45之后由安全驱动等待MR1，不并发请求。所有数据均为历史回取。


## 2026-11-22 09:39 UTC：安全恢复后续采检查点

| 数据类型 | 权威已有 / 48,102 | 缺失 | 权威检查后新增（待下一次重建） |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | 0 |
| 可信 full FT | 48,102 | 0 | 0 |
| Crown AH开收盘 | 32,449 | 15,653 | 0 |
| Crown AH变化序列 | 36,342 | 11,760 | 0 |
| Crown OU开收盘 | 32,445 | 15,657 | 0 |
| Crown OU变化序列 | 5,111（09:36:51 UTC权威重建） | 42,991 | +4 |

- 09:36:51 UTC安全driver完成队列重建并启动collector PID92433。权威待请求42,482；AH开收盘32,449、AH走势36,342、OU开收盘32,445、OU走势5,111。固定64联赛/2023—2026范围未变。
- 至09:39:03 UTC，18个唯一FID收到响应：4个FID在库中已有AH/OU记录且本次只补OU movement，14个HTTP/API成功但没有Crown市场价。18份原始SHA均匹配，越界0、重复0；OU走势推算5,115、队列估算42,464，均待下一次权威重建。AH开收盘、AH走势、OU开收盘新增0。
- 累计839 attempts：723 success、110 `IncompleteRead`、6 `TOO_MANY_REQUEST`；46个错FID全部恢复，当前retryable失败0。T0938增量/逐场SHA/队列快照与传输审计已保存。采集配置仍为5.2秒间隔，数据均为historical回取。
- 09:38:19 UTC统一结算PID92747触发安全暂停，collector PID92433完成最后在途响应后停止；父driver PID49373仍运行等待。此时最新已确认队列仍为42,482，刚完成的18个FID预计使下一队列最多降至42,464，实际数待自动重建。


## 2026-11-22 09:43 UTC：继续负责2023—2026年64联赛采集

| 数据类型 | 权威已有 / 48,102 | 缺失 | 队列重建后本段新增（待下次权威重建） |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | 0 |
| 可信 full FT | 48,102 | 0 | 0 |
| Crown AH开收盘 | 32,449 | 15,653 | 0 |
| Crown AH变化序列 | 36,342 | 11,760 | 0 |
| Crown OU开收盘 | 32,445 | 15,657 | 0 |
| Crown OU变化序列 | 5,116 | 42,986 | +3（12个响应中） |

- 工作范围仍为固定64个Provider League ID、2023—2026；不请求其他年份或联赛。原有48,102场赛程和可信full FT均复用。09:42:36.881 UTC队列权威重建为42,459；AH开收盘32,449、AH走势36,342、OU开收盘32,445、OU走势5,116。safe-window父driver PID49373持续运行，collector PID93691启动，节奏5.2秒。
- 从本次队列重建后至09:43:38.206 UTC，有12个唯一FID完成响应：3个已有AH/OU报价的FID只新增OU movement，9个HTTP/API成功但返回无Crown AH/OU报价。raw SHA 12/12匹配；联赛ID与64联赛赛程一致，越界0、重复0。AH及开收盘无新增；OU走势推算5,119，属队列重建后的增量，等待下一次权威重建。
- 本次累计transport audit为856 attempts：740 success、110 `IncompleteRead`、6 `TOO_MANY_REQUEST`；46个遇错FID均已恢复，当前可重试失败0。成功短窗口12个响应/约61秒，约11.8场/分钟；仅代表当前短观察段，未改变5.2秒间隔或服务商限流行为。SQLite写入仍非瓶颈。
- T0943的响应明细、raw SHA核对、driver事件、覆盖和transport审计见同目录`crown_64_collection_checkpoint_20261122T0943Z.jsonl`、`crown_64_verified_increment_20261122T0943Z.json`、`crown_64_driver_checkpoint_20261122T0943Z.jsonl`、`crown_64_coverage_snapshot_20261122T0943Z.json`及manifest。所有新增响应均为历史回取，不代表赛前实收。
- 余下权威队列42,459场；按5.2秒间隔的纯请求时间约61.2小时，未计生产作业安全暂停及重试。collector持续自动续采；本轮没有改正式模型、Telegram、账本、采集频率、生产调度或既有规则。


## 2026-11-22 09:46 UTC：结算安全暂停与当前开源工具复核

- safe-window driver PID49373于09:42:36.881 UTC恢复，权威队列42,459，collector PID93691按5.2秒间隔运行；09:46:00.688 UTC因统一结算PID94502再次自动暂停，子进程完成请求后退出，父driver继续等待并会在既有安全窗口后重建队列。
- 本队列批次截至09:46:04.201 UTC实际处理40个唯一FID（均属2023年）：5个请求响应补入OU movement，35个HTTP/API成功响应没有Crown盘口。原始响应SHA 40/40通过，联赛ID/范围错误0，FID重复0；AH、AH走势、AH/OU开收盘均无新增。OU movement从本次权威基线5,116推算增加5至5,121，等待下一次队列重建确认。权威基线队列仍42,459，暂停后精确剩余数尚待自动重建。
- 截至该批传输审计累计884 attempts：768 success、110 `IncompleteRead`、6 `TOO_MANY_REQUEST`；46个发生错误的FID全部已恢复，当前可重试失败0。该批40个响应在约207秒窗口内完成，约11.6 FID/分钟；请求节奏未高于5.2秒间隔上限，SQLite写入毫秒级不是瓶颈。安全暂停降低日历吞吐；没有提高频率或绕过限流。
- 开源项目检查（2026-11-22，阅读上游README/功能说明，没有安装或运行它们）：[OddsHarvester](https://github.com/jordantete/OddsHarvester)声明支持OddsPortal历史、足球AH/OU、指定bookmaker及赔率历史；但不能证明每个目标FID均有Crown市场/双边价格，且报价来源是OddsPortal页面，不是本地Crown HTTP原响应，不能并入本库Crown记录或减少对Crown接口的请求。
- 同名`oddsportal_scraper`复核了两个公开仓库：[djibril-marega版本](https://github.com/djibril-marega/oddsportal_scraper)README输出比赛结果及1X2开/收盘赔率；[Bedbin17版本](https://github.com/Bedbin17/oddsportal_scraper)列出O/U与若干1X2衍生市场，未列足球AH。两者均不能满足本任务AH+OU且可追溯Crown原始响应/收件时间的要求。
- [soccerdata](https://github.com/probberechts/soccerdata)对外列出的来源包括Club Elo、ESPN、FBref、Football-Data.co.uk、Sofascore等，未提供Crown报价接口；现有64联赛赛程和可信full FT已完整覆盖，所以不会减少当前Crown盘口队列。以上工具均未部署，避免引入其他博彩公司数据冒充Crown。
- T0946逐场记录、queue/driver事件、覆盖、transport审计和SHA manifest见`crown_64_collection_checkpoint_20261122T0946Z.jsonl`等配套文件。仍是纯历史回取，不构成真实赛前HTTP收据。


## 2026-11-22 09:59 UTC：固定范围核对、OU旧任务整合复核与续采

- 可重复范围审计`audit_crown_64_scope.py`直接复用collector的64个ID，与赛程文件全时期64个Provider ID集合精确相等；96,504条全时期schedule行、48,102个2023—2026唯一FID，年份分布2023 14,673、2024 14,553、2025 14,631、2026 4,245。目标期赛程涉及63个ID：ID 314（赛程身份Belarus Premier League/白俄罗斯超级联赛）在该文件只有2019—2021共675场，2023—2026为0。ID314仍保留在固定64集合中；没有替换或添加联赛。JSON审计及脚本：`crown_64_scope_reconciliation_20261122.json`、`audit_crown_64_scope.py`。
- 只读复核之前OU独立网络回填与统一库：网络日志430行、SQLite `crown_ou_source` 430行；状态为424 `OU_SUMMARY_SAVED`、4 `NO_CROWN_OU`、2 `FETCH_FAILED`。428份原始响应SHA全部匹配；数据库中保留428个open及428个close报价行。全部来源开球年为2019（377）和2020（51），与当前2023—2026目标FID交集0；现有数据已留在统一库，独立OU采集进程不运行。明细审计：`crown_64_ou_network_import_audit_20261122.json`。
- 09:49:48.537 UTC权威队列42,419、AH open-close 32,449、AH movement 36,342、OU open-close 32,445、OU movement 5,121。该批到09:54安全暂停前有45个成功响应FID（33无Crown盘口、12只新增OU movement，raw SHA 45/45通过）以及1个重试中FID `131467401`，该FID遇两次`IncompleteRead`后由安全暂停保留重试。统一结算PID96306期间safe-window父driver PID49373等待，未并发采集。
- 09:56:54.784 UTC安全窗口恢复后确认队列42,374，OU movement 5,133，核实暂停前+12走势落库且45个FID已出请求队列；随后FID `131467401`也自动重试成功（Crown原始SHA保留）。至09:59:23.972 UTC恢复批次另处理25个唯一FID：5个只补OU movement、20个无Crown盘口；SHA 25/25匹配、超范围/重复0。后一批走势估算5,138，仍待下次权威重建。当前collector PID96932、safe-window PID49373运行，5.2秒间隔。
- 截至09:59 transport audit共957 attempts：838 success、113 `IncompleteRead`、6 `TOO_MANY_REQUEST`；曾遇错误的47个FID现已全部恢复，当前retryable失败0。重试错误率按attempt计12.43%，该分母含全部重试尝试；不能解读为12.43%的赛事永久失败。恢复批次25场/约149秒约10.1场/分钟；此前45场/约252秒约10.7场/分钟，均低于5.2秒间隔的理论11.54场/分钟上限。效率提升已通过AH/OU合并将两次请求减少为每FID一次实现；此阶段没有证据显示单次响应、API额度或SQLite写入可继续提高网络请求上限。安全暂停和重试会减少日历速度。
- 最新权威field-level覆盖基线（09:56:54 UTC）与缺口：AH开收盘32,449/15,653、AH走势36,342/11,760、OU开收盘32,445/15,657、OU走势5,133/42,969。待请求队列42,374是排除已终态响应后的重试工作量，不等于仍缺quote字段FID数；HTTP/API成功但无Crown市场数据的FID保留原始证据并继续显示为市场覆盖缺口。纯5.2秒间隔下42,374请求约61.2小时；这不含定时安全暂停、重试及无报价状态。
- 检查点文件分别为T0955（暂停前段）及T0958（恢复后段），不把同一FID的失败尝试与后续成功响应重复当成两场。SHA清单列出每条完整原始响应；部分响应未保存完整raw时仅保留传输失败日志。所有新报价是历史回取，非赛前实收。


## 2026-11-22 10:08 UTC：安全窗口续采与T1008检查点

| 数据类型 | 当前覆盖 / 48,102 | 字段缺失FID | 最近确认待请求队列 |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | — |
| 可信 full FT | 48,102 | 0 | — |
| Crown AH开收盘 | 32,449 | 15,653 | — |
| Crown AH变化序列 | 36,342 | 11,760 | — |
| Crown OU开收盘 | 32,445 | 15,657 | — |
| Crown OU变化序列 | 5,155 | 42,947 | — |
| 待处理历史请求（排除已有终态无报价响应） | — | — | 42,324（10:05:12 UTC重建） |

- T1008只读SQLite审计确认范围仍是固定64 Provider League IDs、2023—2026共48,102个FID；赛程和可信full FT均完整复用。字段缺失FID与待处理请求数口径不同；已成功取得响应但无Crown报价的FID保留原始响应并从重复请求队列剔除。
- 09:59:23.972至10:07:57.978 UTC增量含57个唯一FID：17个保存了OU movement，40个Crown响应没有AH/OU市场数据；AH与AH/OU开收盘无增量。原始响应SHA 57/57匹配，超范围/league mismatch 0、FID重复0、该增量请求错误0。
- T1008全日志传输审计为1,014 attempts：895 success、113 `IncompleteRead`、6 `TOO_MANY_REQUEST`；47个曾失败FID后来全部恢复，最新可重试失败0。T1008覆盖、增量、逐场、driver、transport及SHA manifest均已生成。
- 10:05:12 UTC父driver PID49373重建队列42,324并启动collector PID98655，节奏5.2秒。10:08:30 UTC因MR1计划任务PID99433自动暂停；暂停前该collector批次记录38个响应（11个`BOTH_MARKETS`、27个无Crown市场数据），无传输失败。10:12 UTC发现后续统一结算PID99738运行，父driver保持等待；该生产作业结束后自动重建队列并续采。暂停后的精确待请求数以自动重建为准。
- 57个响应分布在含一次约219秒safe-window的514秒墙钟区间；扣除该暂停后约11.6 FID/min，吻合5.2秒请求间隔上限。未改变频率、并发或限流行为；SQLite写入不是吞吐瓶颈。
- SHA证据：`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T1008Z.txt`及同目录`crown_64_collection_checkpoint_20261122T1008Z.jsonl`、`crown_64_verified_increment_20261122T1008Z.json`、`crown_64_driver_checkpoint_20261122T1008Z.jsonl`、`crown_64_coverage_snapshot_20261122T1008Z.json`、`crown_64_transport_audit_20261122T1008Z.json`。全部为historical回取，不是赛前实收。


## 2026-11-22 10:14 UTC：安全任务后续采与T1014检查点

| 数据类型 | 当前覆盖 / 48,102 | 字段缺失FID | 最近队列重建 |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | — |
| 可信 full FT | 48,102 | 0 | — |
| Crown AH开收盘 | 32,449 | 15,653 | — |
| Crown AH变化序列 | 36,342 | 11,760 | — |
| Crown OU开收盘 | 32,445 | 15,657 | — |
| Crown OU变化序列 | 5,165 | 42,937 | — |
| 待处理请求（排除终态无报价） | — | — | 42,286（10:12:59 UTC） |

- 10:08:30 UTC MR1任务结束后，统一结算PID99738完成，safe-window父driver PID49373于10:12:59重建队列42,286，覆盖AH open/close 32,449、AH movement 36,342、OU open/close 32,445、OU movement 5,159，并自动启动collector PID767，间隔5.2秒。10:14:38 UTC复核collector仍运行。
- 从T1008上次增量终点10:07:57.978至10:14:21.281 UTC，新增22个唯一FID响应：10个补入OU movement，12个无Crown市场；AH及开收盘无新增。共23次HTTP尝试，其中22成功、一次`IncompleteRead`，该FID已恢复成功。22份最终原始响应SHA全匹配；越界/联赛不匹配0、重复0。
- 全日志transport累计1,037 attempts（917 success、114 `IncompleteRead`、6 `TOO_MANY_REQUEST`）；48个出现过传输错误的FID均已恢复，latest retryable failures为0。T1014数据库字段覆盖审计与队列重建均在该固定目标范围。
- T1014响应、增量、driver、coverage、transport和SHA manifest：`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T1014Z.txt`及同目录`crown_64_collection_checkpoint_20261122T1014Z.jsonl`、`crown_64_verified_increment_20261122T1014Z.json`、`crown_64_driver_checkpoint_20261122T1014Z.jsonl`、`crown_64_coverage_snapshot_20261122T1014Z.json`、`crown_64_transport_audit_20261122T1014Z.json`。一切仍标为historical回取。


## 2026-11-22 10:17 UTC：T1017安全暂停响应核验

- 10:12:59 UTC最近重建队列为42,286并启动collector PID767。10:15:41 UTC遇MR1计划任务PID1365后安全暂停；该批次共处理32个唯一FID，9个返回可保存的Crown市场记录、23个HTTP成功但没有Crown AH/OU报价。driver PID49373等待计划任务完成。
- T1014增量结束后至10:15:44.410 UTC的最后16个FID均成功，SHA 16/16匹配，超范围/重复0，新增OU movement 3个FID；AH及开收盘没有新增。最后一批其他已处理记录在10:14:21前的T1014增量中，整体覆盖须等安全任务结束后只读重审确认。
- 当前累计1,053次传输尝试（933 success、114 `IncompleteRead`、6 `TOO_MANY_REQUEST`）；仍没有尚未恢复的错误FID。T1017逐场/增量/driver/transport及manifest已保存。由于同一时段SQLite被排定任务占用，未并行重建覆盖表；最新权威覆盖仍引用T1014（OU movement 5,165），下一次队列重建时更新。
- 证据文件：`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T1017Z.txt`及`crown_64_collection_checkpoint_20261122T1017Z.jsonl`、`crown_64_verified_increment_20261122T1017Z.json`、`crown_64_driver_checkpoint_20261122T1017Z.jsonl`、`crown_64_transport_audit_20261122T1017Z.json`。所有报价仍为历史回取。


## 2026-11-22 10:21 UTC：T1021续采检查点

| 数据类型 | 当前覆盖 / 48,102 | 字段缺失FID | 最近队列重建 |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | — |
| 可信 full FT | 48,102 | 0 | — |
| Crown AH开收盘 | 32,449 | 15,653 | — |
| Crown AH变化序列 | 36,342 | 11,760 | — |
| Crown OU开收盘 | 32,445 | 15,657 | — |
| Crown OU变化序列 | 5,171 | 42,931 | — |
| 待请求历史FID | — | — | 42,254（10:20:24 UTC） |

- 10:12:59队列42,286批次完成32个成功响应后，MR1及统一结算安全窗口结束。10:20:24 UTC权威重建队列42,254；AH开收盘32,449、AH movement 36,342、OU开收盘32,445、OU movement 5,168；collector PID2585已自动续跑，父driver PID49373持续管理安全窗口，间隔5.2秒。
- 10:15:44.410—10:21:20.898 UTC新增11个唯一响应：3个保存OU movement、8个无Crown市场；AH及开收盘无新增。SHA 11/11通过，越界/联赛不匹配0、重复0、请求错误0。覆盖审计截至10:21:20更新至OU movement 5,171，队列仍以上次完整重建数42,254为权威。
- 全日志transport为1,064 attempts：944 success、114 `IncompleteRead`、6 `TOO_MANY_REQUEST`；未恢复错误FID仍为0。T1021逐场、增量、driver、coverage、transport与SHA manifest见对应文件。
- T1021纯请求剩余时间约61.0小时（42,254×5.2秒），不含生产安全暂停和重试；短期吞吐仍由5.2秒服务商请求间隔限定，未提高频率或并发。


## 2026-11-22 10:23 UTC：T1023响应与暂停审计

- 10:20:24队列42,254启动的collector PID2585在10:23:05因MR1 PID3263安全暂停。该批次从启动至最后一个在途响应完成共有32个唯一FID：11个取得待补Crown市场数据，21个返回无AH/OU市场报价；所有请求均成功。
- T1021增量终点10:21:20.898至10:23:10.124再收到21个FID：8个新增OU movement，13个无Crown市场；AH和开收盘未新增。SHA 21/21通过，超范围/重复0，错误0。当前SQLite覆盖权威上限仍是T1021的OU movement 5,171；本批新增8个FID待下次数据库队列重建核准。
- transport累计1,085 attempts：965 success、114 `IncompleteRead`、6 `TOO_MANY_REQUEST`；最新未恢复失败0。证据及manifest：`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T1023Z.txt`及同目录逐场、增量、driver、transport文件。安全作业结束后safe-window会自动重建队列续跑。


## 2026-11-22 10:24 UTC：续采T1024检查点

| 数据类型 | 当前覆盖 / 48,102 | 字段缺失FID | 最近队列重建 |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | — |
| 可信 full FT | 48,102 | 0 | — |
| Crown AH开收盘 | 32,449 | 15,653 | — |
| Crown AH变化序列 | 36,342 | 11,760 | — |
| Crown OU开收盘 | 32,445 | 15,657 | — |
| Crown OU变化序列 | 5,183 | 42,919 | — |
| 待请求历史FID | — | — | 42,222（10:24:10 UTC重建） |

- MR1 PID3263结束后，父driver PID49373于10:24:10 UTC自动重建队列42,222，覆盖AH 32,449/36,342、OU 32,445/5,179，并启动collector PID3500，5.2秒节奏。
- T1023末条响应10:23:10.124之后至10:24:56.063新增9个唯一FID：4个补入OU movement，5个无Crown市场；SHA 9/9通过、越界/重复0、错误0。T1024审计随后确认OU movement覆盖5,183，另3场在该次队列建立后完成。AH及开收盘未新增。
- 全部日志累计1,094次尝试：974 success、114 `IncompleteRead`、6 `TOO_MANY_REQUEST`，当前无可重试失败。T1024逐场/增量/driver/coverage/transport和SHA manifest在同目录。
- 42,222个待请求FID按5.2秒间隔约需61.0小时纯请求时间，生产安全暂停及重试另计；采集尚未完成。


## 2026-11-22 10:28 UTC：安全窗口后续采T1028

| 数据类型 | 当前覆盖 / 48,102 | 字段缺失FID | 最近队列重建 |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | — |
| 可信 full FT | 48,102 | 0 | — |
| Crown AH开收盘 | 32,449 | 15,653 | — |
| Crown AH变化序列 | 36,342 | 11,760 | — |
| Crown OU开收盘 | 32,445 | 15,657 | — |
| Crown OU变化序列 | 5,185 | 42,917 | — |
| 待请求历史FID | — | — | 42,210（10:27:55 UTC重建） |

- 10:25:10 UTC因统一结算PID3719安全暂停；作业结束后safe-window driver PID49373于10:27:55重建队列42,210，字段基线AH 32,449/36,342、OU 32,445/5,184。collector PID4403自动继续，仍为5.2秒间隔。
- T1024最后记录10:24:56.063至10:28:31.305，10个新FID响应：2个新增OU movement、8个无Crown市场；raw SHA 10/10通过，越界/重复/请求错误均0。只读覆盖随即核验OU movement 5,185（比队列基线再多1场）。AH及开收盘不变。
- 累计1,104 attempts：984 success、114 `IncompleteRead`、6 `TOO_MANY_REQUEST`；当前未恢复失败FID为0。T1028的原始逐场记录、增量、driver、coverage、transport与SHA manifest已保存。
- 最近队列42,210按5.2秒间隔约需61.0小时纯请求时间，暂停与重试另计。


## 2026-11-22 10:36 UTC：T1036检查点与安全暂停

| 数据类型 | 最近队列覆盖 / 48,102 | 字段缺失FID | 待请求队列 |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | — |
| 可信full FT | 48,102 | 0 | — |
| Crown AH开收盘 | 32,449 | 15,653 | — |
| Crown AH变化序列 | 36,342 | 11,760 | — |
| Crown OU开收盘 | 32,445 | 15,657 | — |
| Crown OU变化序列 | 5,188 | 42,914 | — |
| 去终态响应后的历史请求 | — | — | 42,179 |

- 10:31:07批次完成19个唯一FID响应后，父driver PID49373在10:35:37重建队列42,179；覆盖AH 32,449/36,342、OU 32,445/5,188。随后启动的短批次被MR1作业PID6198于10:35:53安全暂停。10:36确认父driver仍运行等待该任务。
- T1033增量终点10:32:45.025至10:35:56.782又有4个成功FID：1个保存OU movement、3个无Crown市场。raw SHA 4/4匹配，范围外0、重复0、传输错误0；AH、开收盘无新增。该1个走势更新晚于10:35:37覆盖重建，记为待下次重建确认，不提前增加权威coverage数字。
- 全日志累计1,132 attempts（1,012 success、114 `IncompleteRead`、6 `TOO_MANY_REQUEST`），未恢复失败0。T1036逐场/增量/driver/coverage/transport与SHA manifest已保存；报价均标记historical回取。


## 2026-11-22 10:48 UTC：T1048采集增量与安全暂停

| 数据类型 | 最近权威覆盖 / 48,102 | 字段缺失FID | 最近权威待请求队列 |
|---|---:|---:|---:|
| 64联赛赛程 | 48,102 | 0 | — |
| 可信full FT | 48,102 | 0 | — |
| Crown AH开收盘 | 32,449 | 15,653 | — |
| Crown AH变化序列 | 36,342 | 11,760 | — |
| Crown OU开收盘 | 32,445 | 15,657 | — |
| Crown OU变化序列 | 5,193 | 42,909 | — |
| 去终态响应后的历史请求 | — | — | 42,137（10:43:28 UTC重建） |

- 固定范围仍为原49+扩展15个Provider League ID、2023—2026年；赛程与可信full FT各48,102个FID。没有访问2019—2022或范围外赛事。
- 从10:43:28 UTC权威队列重建至10:47:58 UTC，完成52个唯一FID响应，全部HTTP/API成功；46个返回无Crown市场数据，6个同时满足覆盖状态并只补入OU movement。AH及AH/OU开收盘无新增。原始响应SHA 52/52匹配，重复和范围外FID均为0。
- 10:48:07 UTC，采集子进程因正式统一结算任务PID8873安全停止，父safe-window PID49373保持运行。中断中的FID `131899045`遇到`IncompleteRead`后被安全暂停，仍在可重试队列；不是终态失败。下次空闲窗口由父驱动重新建队列并续采。
- 全采集日志截至T1048累计1,223 attempts：1,102 success、115 `IncompleteRead`、6 `TOO_MANY_REQUEST`。49个曾遇传输/API错误的FID中48个已恢复，另1个是上述安全暂停边界待重试。所有历史回取仍与赛前HTTP实收严格区分。
- 最近实际短窗口52场/约269.5秒，约11.6场/分钟，与5.2秒单请求间隔上限一致；没有提高并发或绕限流。按最近权威队列42,137项计算，约60.9小时纯请求时间，安全暂停与重试另计。
- T1048增量、驱动事件、覆盖快照、transport审计和SHA清单：`crown_64_collection_checkpoint_20261122T1048Z.jsonl`、`crown_64_verified_increment_20261122T1048Z.json`、`crown_64_driver_checkpoint_20261122T1048Z.jsonl`、`crown_64_coverage_snapshot_20261122T1048Z.json`、`crown_64_transport_audit_20261122T1048Z.json`、`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T1048Z.txt`。


## 2026-11-22 10:54 UTC：T1051队列重建与自动续采

- 10:51:35 UTC正式任务结束后，父driver PID49373重新计算队列并自动启动collector PID9666，节奏保持5.2秒。权威队列从42,137减至42,085；AH开收盘32,449、AH变化36,342、OU开收盘32,445，OU变化从5,193增至5,199。
- 从10:51:35至10:54:02的28个唯一响应均在64联赛/2023—2026范围，28份raw SHA通过、重复/越界0；17场无Crown市场数据，11场保存OU movement。其中一次`IncompleteRead`重试后成功；先前被安全暂停的FID `131899045`也已在本批成功补入OU movement。
- T1054全日志审计为1,253 attempts：1,131 success、116 `IncompleteRead`、6 `TOO_MANY_REQUEST`；50个遇错FID全部恢复，最新可重试失败0。当前子进程PID9666继续运行，T1054之后的新响应尚未进入下一个权威队列重建。
- 最近权威队列42,085项折合约60.8小时纯请求时间，安全暂停及后续重试另计。增量、coverage、driver和transport证据分别位于`crown_64_collection_checkpoint_20261122T1054Z.jsonl`、`crown_64_verified_increment_20261122T1054Z.json`、`crown_64_driver_checkpoint_20261122T1054Z.jsonl`、`crown_64_coverage_snapshot_20261122T1054Z.json`、`crown_64_transport_audit_20261122T1054Z.json`，SHA清单位于`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T1054Z.txt`。


## 2026-11-22 10:59 UTC：T1059队列确认与再续采

- 10:55:15 UTC，MR1计划作业PID10456触发collector PID9666安全停止；随后正式统一结算作业运行。父driver PID49373等待安全窗口结束，于10:59:20 UTC重建队列并自动启动collector PID11466。
- 最新权威队列从42,085降至42,043；AH开收盘32,449、AH movement 36,342、OU开收盘32,445、OU movement 5,213。此前10:51:35—10:55:15的42个唯一响应已全部反映在队列重建中：28个无Crown市场数据，14个补入OU movement，raw SHA 42/42通过，范围外/重复0。
- 该窗口有一次`IncompleteRead`重试后成功；先前暂停边界FID `131899045`成功重试。T1059全日志审计累计1,266 attempts：1,144 success、116 `IncompleteRead`、6 `TOO_MANY_REQUEST`，50个错误FID全部恢复，最新可重试失败0。
- 最近权威队列42,043项约需60.7小时纯请求时间，安全暂停和重试另计。collector PID11466已继续按5.2秒节奏运行；T1059之后的响应等待下一次权威队列重建。
- T1059增量、队列覆盖和driver证据：`crown_64_collection_checkpoint_20261122T1059Z.jsonl`、`crown_64_verified_increment_20261122T1059Z.json`、`crown_64_coverage_snapshot_20261122T1059Z.json`、`crown_64_driver_checkpoint_20261122T1059Z.jsonl`及transport审计`crown_64_transport_audit_20261122T1055Z.json`；SHA清单为`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T1059Z.txt`。


## 2026-11-22 11:07 UTC：T1107新队列与续采确认

- 10:59:20—11:02:16 UTC期间处理34个唯一FID，25个成功响应无Crown市场数据，9个保存OU movement；raw SHA 34/34匹配，越界/重复0。11:06:55安全窗口队列重建确认该批全部处理完，待请求从42,043降至42,009，OU movement覆盖从5,213升到5,222。AH和开收盘覆盖未变。
- MR1使collector PID11466于11:02:11安全暂停，父driver PID49373等待作业结束后于11:06:55重建队列，并启动collector PID13127。
- 新批次在11:07:46前另完成10个FID（7个无Crown市场数据、3个保存OU movement）；raw SHA 10/10通过、无越界/重复。该10场在11:06:55队列重建之后，尚未计入下一次权威coverage。
- T1107全日志传输审计为1,310 attempts：1,188 success、116 `IncompleteRead`、6 `TOO_MANY_REQUEST`；曾遇错误的50个FID均已恢复，最新可重试失败0。剩余42,009项按5.2秒节奏约60.7小时纯请求时间，安全暂停和重试另计。
- T1102与T1107的逐场、增量、driver、coverage、transport和SHA证据均在本目录，清单为`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T1107Z.txt`；本批历史回取不代表赛前实收。


## 2026-11-22 11:10 UTC：T1110队列确认

- 11:06:55—11:09:24 UTC完成29个唯一FID响应：21场无Crown行情、8场保存OU movement。29份raw SHA全部匹配，范围外/重复0。11:10:45权威队列确认待请求由42,009减到41,980，OU movement覆盖由5,222增至5,230；AH和开收盘覆盖不变。
- 11:09:23 UTC MR1计划作业使collector PID13127安全暂停；父driver PID49373于任务结束后重建队列，并启动collector PID13996，继续5.2秒节奏。
- T1111全日志1,338 attempts：1,215 success、117 `IncompleteRead`、6 `TOO_MANY_REQUEST`；51个遇错FID全部恢复，最新可重试失败0。
- 最近权威队列41,980项折合约60.6小时纯请求时间，安全暂停及重试另计。T1110逐场、增量、driver和coverage证据及T1111 transport审计均已归档；SHA清单为`CROWN_AH_OU_64_CHECKPOINT_SHA256_20261122T1111Z.txt`。


## 2026-11-22 11:15 UTC：T1115队列重建与再次安全暂停

- 11:10:45—11:11:45 UTC间完成8个唯一FID：4个HTTP/API成功但无Crown行情，4个保存OU movement；raw SHA 8/8匹配，重复/越界0。11:14:31队列重建确认该批已完成，待请求从41,980降至41,972；OU movement覆盖从5,230升到5,234。AH和开收盘不变。
- T1115全日志1,350 attempts：1,227 success、117 `IncompleteRead`、6 `TOO_MANY_REQUEST`；51个曾遇错FID已全部恢复，最新可重试失败0。
- 父driver PID49373于11:14:31重建队列并启动collector PID14895；该collector于11:15:31因MR1计划作业PID15111再次安全暂停。父driver继续运行，暂停后响应留待下一次重建确认。
- 剩余权威队列41,972项，按5.2秒间隔折合约60.6小时纯请求时间。T1115增量、driver、coverage、transport及SHA清单位于本目录；该批仍为historical回取。


## 2026-11-22 11:20 UTC：T1120队列续进

- 11:14:31—11:17:25 UTC完成12个唯一FID响应，10个无Crown市场数据，2个保存OU movement；raw SHA 12/12匹配，越界/重复0，传输尝试均成功。
- 11:17:25 UTC权威重建确认队列从41,972减至41,960；AH开收盘32,449、AH movement 36,342、OU开收盘32,445、OU movement 5,236。OU变化序列较前一快照+2，AH与开收盘无变化。
- T1120全日志1,360 attempts：1,237 success、117 `IncompleteRead`、6 `TOO_MANY_REQUEST`；51个遇错FID全部恢复，最新可重试失败0。父driver PID49373启动collector PID15537，仍按5.2秒间隔运行。
- 剩余41,960项约60.6小时纯请求时间，不含安全暂停和重试。T1120逐场、增量、driver、coverage、transport与SHA manifest已保存，所有记录属于历史回取。


## 2026-11-22 11:22 UTC：T1122续采队列确认

- 11:17:25—11:19:18 UTC间完成22个唯一FID响应：15场无Crown市场，7场保存OU movement。raw SHA 22/22通过、重复/越界0、传输尝试全部成功。
- 11:22:11 UTC安全窗口重建确认队列从41,960减至41,938，OU movement覆盖从5,236增至5,243；AH、AH movement及两市场开收盘均不变。
- T1122全日志1,372 attempts：1,249 success、117 `IncompleteRead`、6 `TOO_MANY_REQUEST`；51个曾遇错FID均恢复，最新可重试失败0。新collector启动后，MR1作业PID16557触发安全暂停，父driver PID49373继续等待并会自动续采。
- 剩余41,938请求约60.6小时纯网络时间，安全暂停和重试另计。T1122增量、覆盖、driver、transport与SHA证据已归档，报价均为historical回取。


## 2026-11-22 11:38 UTC：续采检查点 T1138

- 本轮继续仅覆盖固定64个 Provider League ID、2023—2026 年48,102个既有FID；比赛清单和可信 full FT 均为48,102。历史请求仍使用`columns=asianList,goalList`，每FID最多一次合并请求，间隔5.2秒。
- 11:22:11至11:38:20 UTC间，安全窗口驱动处理72个唯一FID，60次成功响应没有Crown市场报价，12场保存了OU movement；AH及开收盘没有覆盖增量。72份HTTP响应SHA全部匹配，FID重复0、范围外/身份不匹配0。请求共73次attempt，其中72成功、1次transport error后恢复；回取全部为`historical`。
- 11:38:20 UTC权威队列重建：待请求41,866项。覆盖为AH open/close 32,449（缺15,653）、AH movement 36,342（缺11,760）、OU open/close 32,445（缺15,657）、OU movement 5,255（缺42,847）。市场覆盖缺口会重叠，不能相加为待请求数；成功HTTP200但返回空Crown bookmaker的FID单独记作无报价，不冒充已获得市场行。
- T1138全日志累计1,445 attempts：1,321成功、118 `IncompleteRead`、6 `TOO_MANY_REQUEST`；52个曾遇传输/API错误的FID均已恢复，当前可重试失败0。
- 采集子进程PID 18699于11:35 UTC遇统一结算计划作业安全暂停；结算结束后父driver PID49373于11:38:20重建队列并启动新子进程PID20253。接续后42场区间实测约11.5 FID/分钟，接近5.2秒固定间隔上限；未提高频率、并发或绕过限流。
- T1138逐场增量、权威队列、覆盖快照、transport审计和输入输出SHA见`crown_64_collection_checkpoint_20261122T1138Z.jsonl`、`crown_64_verified_increment_20261122T1138Z.json`、`crown_64_driver_checkpoint_20261122T1138Z.jsonl`、`crown_64_coverage_snapshot_20261122T1138Z.json`、`crown_64_transport_audit_20261122T1138Z.json`及对应SHA清单。
- T1138后采集仍在运行；本节只陈述11:38:20 UTC队列检查点，后续在途数据不并入该时点覆盖数。


## 2026-11-22 11:46 UTC：续采检查点 T1146

- 固定范围仍是64个Provider League ID、2023—2026年48,102个FID及48,102个可信full FT。T1138后处理49个唯一FID，35次成功响应没有Crown市场报价，14场保存OU movement；AH和开收盘无新增。49份原始响应SHA全匹配，重复/越界0，49次请求全部成功。
- 11:46:12 UTC权威队列为41,817，较T1138减少49。覆盖AH open/close 32,449、AH movement 36,342、OU open/close 32,445、OU movement 5,269（较T1138增加14）。分市场缺口分别15,653、11,760、15,657、42,833。
- T1146全日志1,494 attempts（1,370 success、118 `IncompleteRead`、6 `TOO_MANY_REQUEST`）；52个遇错FID均恢复，未恢复失败0。活动请求继续采用合并AH+OU接口及5.2秒间隔。
- safe-window父driver PID49373在MR1任务窗口后于11:46:12 UTC重建队列并启动collector PID22018。T1146之后采集仍在继续；下一个检查点需再次核验实际响应SHA和队列。全部为historical回取。
- T1146逐场、增量、driver、coverage、transport和SHA清单见同目录对应文件。
