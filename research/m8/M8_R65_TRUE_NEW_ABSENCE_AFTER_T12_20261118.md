# M8 R65 — Crown T12 之后真正新缺阵事件审计

日期：2026-11-18

## 研究目标

本轮不再研究“伤停人数多少”，而是识别：

真正的新缺阵/新可用性变化，是否在 Crown T12 source event 之后才首次公开，并在 Crown 后续报价形成之前被多来源确认。

R61 已证明 Guardian 文章 published/modified 时间不能直接代表首次公开时间。本轮因此逐场追踪具体球员、此前状态、事件发生/首次公开、独立确认和 Crown T12 顺序。

## 第一轮结果

目前在 R61 的 46 场已完成 FT AH 对账样本中，已经找到：

- 4 个高置信度“真正新缺阵在 T12 之后公开”的事件
- 1 个中置信度候选事件
- 另有多个“文章晚于 T12、但实际信息早已公开”的假事件

这说明研究方向已经从“文章时间戳”进入了真正有价值的事件时间线。

## A. 高置信度事件

### 1. Liverpool – Man City：Dominik Szoboszlai

Crown T12 source event：2026-10-10 20:43:14 UTC。

Friday 的赛前发布会没有把 Szoboszlai 列为伤疑。到比赛日 Sunday morning，记者拍到 Liverpool 抵达酒店的画面时没有发现 Szoboszlai，首次产生公开疑问；随后独立媒体确认他缺席，Liverpool 官方最终确认其因腿后腱问题无法出场。citeturn993646search2turn993646search6turn249171search2

因此顺序是：T12 → 球员缺席公开信号 → 独立媒体确认 → 官方确认。

R61 Crown：T12 AH +0.25，1.90 / 1.98；T24 AH +0.25，1.85 / 2.03；FT Liverpool 0–3 Man City。

真正值得研究的是：新缺阵出现后，盘口线没有变化，价格发生变化。但目前不能把价格变化归因给 Szoboszlai，因为还缺 Crown T24 的精确形成时间。

### 2. Arsenal – Everton：Jack Grealish

Crown T12 source event：2026-10-23 22:16:38 UTC。

周五 Everton 的赛前信息仍然保持较大程度不公开；赛前预测阵容仍把 Grealish 放入首发。比赛日 Everton 官方确认 Grealish 因 sickness 缺席。Sports Mole 在 10 月 24 日 13:48 UK（12:48 UTC）已经记录该官方确认，随后其他媒体继续确认。citeturn967210search0turn967210search1turn967210search2

R61 原 Guardian 快照中 Everton 的 reported unavailable 是 0，所以这不是简单的“文章后来才更新”。

Crown：T12 -1.25，2.07 / 1.81；T24 -1.25，2.02 / 1.86；FT Arsenal 2–0 Everton。

### 3. Chelsea – Man Utd：Jordan Henderson

Crown T12 source event：2026-10-30 21:31:03 UTC。

Henderson 原本在预计阵容中。比赛日 Xabi Alonso 确认他生病并出现发烧；MyFootballFacts 的比赛日球队信息在 11:50 UK 已把 Henderson 列为不在阵容，London Evening Standard 在 11:52 UK 进一步报道原因，BBC 来源也记录 Alonso 对其 illness/fever 的解释。citeturn599330search1turn599330search0turn599330search2

因此顺序是：T12 → Henderson 新病情 → 多来源确认，时间差超过 14 小时。

Crown：T12 -0.5，1.99 / 1.89；T24 -0.75，2.05 / 1.83；FT Chelsea 2–0 Man Utd。

这里特别值得继续研究，因为 T24 盘口线发生了 0.25 的变化，但仅凭价格方向还不能断言这是 Henderson 造成的。

### 4. Bournemouth – Leeds：Noah Okafor

Crown T12 source event：2026-10-28 22:11:35 UTC。

这是目前最干净的“新伤发生在 T12 之后”的案例之一。10 月 30 日 Leeds 赛前，Farke 仍表示 Okafor 正常训练、可用；随后 Okafor 在周五最后一次训练中再次出现 adductor pain。Beren Cross/Leeds Live 随后确认这一情况，比赛日他没有进入 Leeds 阵容。citeturn392953search1turn830409search0turn830409search2

这里不是“旧伤 → 晚报道”，而是：T12 → 最后训练发生新伤情 → 缺阵确认。

Crown：T12 -0.25，1.83 / 2.05；T24 -0.25，1.83 / 2.05；FT Bournemouth 2–0 Leeds。

T12 与 T24 完全没有价格变化。如果 Crown T24 的形成时间是在 Okafor 新伤公开之后，这将是一个非常值得研究的“新信息进入市场但 Crown 快照未重新定价”案例。但目前还缺 T24 的真实形成时间，所以不能下这个结论。

## B. 中置信度候选

### Sunderland – Leeds：Nico Elvedi

Crown T12 source event：2026-10-25 00:34:38 UTC。

10 月 23–24 日 Leeds 的赛前预测仍把 Elvedi 放在首发后防中，且此前信息没有新的 Leeds 防线问题。citeturn635293search0turn635293search1

比赛日他因 illness 被排除。citeturn830409search10

因此它很可能也是：T12 → overnight illness → matchday absence。

但目前无法从公开资料可靠恢复“首次公开”的精确 UTC 分钟，因此暂时不把它和上面的四场放在同一置信度。

## C. 反例：为什么必须继续找“首次公开”

Arsenal – Leeds / Tzolis：Guardian 文章是在 Crown T12 之后发布，但 Tzolis 的伤情早已通过更早的报道和 Arsenal 方面公开，因此不能把 Guardian 发布时间当作首次公开。

Aston Villa – Man City / Manzambi：比赛前后出现新的 late fitness-test 报道，但更早的报道已经存在，因此“晚发布”并不等于信息刚刚进入市场。

Brentford – Nottingham Forest / Carvalho：Crown T12 更早，随后出现大量 Carvalho 缺阵报道，但 Carvalho 并非刚刚变成缺阵；他此前已经处于缺阵状态。

这三个例子说明：文章晚于 Crown ≠ 新信息晚于 Crown。

## 当前最重要的发现

真正值得研究的对象已经从 Guardian article timestamp 变成：

first_public_event → second_source_confirm → Crown T12 → Crown T24。

目前已经找到 4 个高置信度事件：

| 比赛 | 新缺阵 | T12 后？ | T24 line | T24 price 是否变化 |
|---|---|---:|---:|---:|
| Liverpool–Man City | Szoboszlai | 是 | 不变 | 是 |
| Arsenal–Everton | Grealish | 是 | 不变 | 是 |
| Chelsea–Man Utd | Henderson | 是 | 变 | 是 |
| Bournemouth–Leeds | Okafor | 是 | 不变 | 不变 |

这已经出现一个有价值的分化：有些新信息出现后 Crown 后续价格发生变化；有些则完全没有变化。

所以真正应该研究的不是“新缺阵后买谁”，而是：新缺阵公开以后，Crown 是否已经完成定价，以及定价速度有多快。

## 下一轮核心任务

现在最关键的缺口已经明确，不是继续找更多伤停人数，而是恢复每场：

1. first_public_utc
2. second_confirm_utc
3. multi_source_confirm_utc
4. Crown_T12_source_event_utc
5. Crown_T12_received_utc
6. Crown_T24_source_event_utc
7. Crown_T24_received_utc
8. 新信息发生时 T24 是否已经形成
9. T12 → T24 的真实价格变化

只有拿到第 6、7 项，才能判断：新信息发生后，Crown 是先看到信息再报价，还是报价已经形成以后才出现信息。

本轮没有新增 Gate、过滤器、下注规则、数量限制或生产逻辑。

研究数据：research/m8/m8_r65_true_new_absence_after_t12_20261118.json
GitHub commit：f2fe32a793419b52ea30722dcabab24e58f4222d