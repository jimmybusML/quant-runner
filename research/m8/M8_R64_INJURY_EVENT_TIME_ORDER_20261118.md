# M8 R64 — 伤停首次公开时间 / 多来源确认 / Crown T12 时间顺序研究

日期：2026-11-18

## 研究目的

停止继续调整“伤停人数权重”。本轮改为研究事件级时间顺序：

1. 某个新缺阵状态第一次公开确认的时间；
2. 第二、第三独立来源确认该状态的时间；
3. Crown T12 AH source event 的时间；
4. Crown T12 / T24 报价是否已经反映该信息；
5. 信息确认发生在 Crown T12 source event 之前还是之后。

目标不是把“Guardian 文章发布时间”继续当成信息首次公开时间，而是还原真实信息事件。

## R61 数据基线

R61 使用 2026-10-09 至 2026-11-06 的 47 个 dated-news/Crown T12 匹配，其中 46 个完成 FT AH reconciliation，39 个研究诊断样本。

文章级时间关系：

- 33/46：Guardian article published 时间早于 Crown T12 source event；
- 13/46：Guardian article published 时间晚于 Crown T12 source event；
- 31/46：Guardian article last-modified 时间早于 Crown T12 source event；
- 15/46：Guardian article last-modified 时间晚于/等于 Crown T12 source event。

这证明“文章发布时间晚于 Crown”不能直接等价于“新信息晚于 Crown”。

## 事件级核查样本

### 1. Arsenal–Leeds / Christos Tzolis：文章级假阳性

Crown T12 source event：
2026-10-09 15:12:41 UTC。

Guardian 赛前文章：
2026-10-09 16:22:09 UTC。

但 Tzolis 的伤停并不是在 Guardian 文章出现时才首次公开。Evening Standard 在 10 月 6 日已经报道其国际比赛受伤并列为伤停；10 月 9 日 14:20 UK（13:20 UTC）的 Daily Cannon 又报道 Arteta 赛前发布会确认其缺阵。

因此 Crown 15:12 UTC 时，Tzolis 缺阵信息已经公开；Guardian 16:22 UTC 只是较晚的汇总载体。

结论：这是“文章级 after-market”但“事件级 before-market”的典型假阳性。

### 2. Everton–Chelsea / Emmanuel Emegha：真实的快速公开 → Crown 跟随

Emegha 在 10 月 15 日训练中出现新的小伤情。

2026-10-16：

- BBC 对 Xabi Alonso 赛前发布会的记录时间：13:24 UTC，明确确认 Emegha 因周四训练中的 knock 无法出场；
- 其他媒体在约 13:30–13:33 UTC 继续发布同一确认；
- Crown T12 AH source event：13:39:10 UTC。

因此，至少按目前可检索到的公开事件：

**首次明确确认 → 多来源确认 → Crown source event**

大致顺序为：

13:24 → 13:30–13:33 → 13:39 UTC。

Crown source event 比第一条明确公开确认晚约 15 分钟。

R61 对应 Everton–Chelsea：

- T12 AH：Everton +0.25；
- T12 主客赔率：1.96 / 1.92；
- T24 AH 仍为 +0.25；
- T24 主客赔率：2.02 / 1.86；
- 该场 T24/T12 盘口线未变。

这已经形成一个值得继续研究的事件样本：**新缺阵确认在 Crown T12 source event 之前公开，而 T12→T24 盘口线没有发生变化。**

### 3. Brentford–Nottingham Forest / Fabio Carvalho：目前最有价值的“after-T12”样本

Crown T12 source event：
2026-10-29 11:34:11 UTC。

随后 10 月 30 日赛前出现 Carvalho 缺阵确认：

- Sports Mole：约 12:46 UTC；
- BBC：15:32 GMT（15:32 UTC）；
- Brentford 官方/媒体聚合约 14:24 UTC；
- 多来源共同确认 Carvalho 将因伤缺席至国际比赛日之后。

这里的关键不是“Carvalho 什么时候受伤”——报道说明伤情本身已存在约 10 天至两周——而是**“本轮比赛明确缺阵”的确认时间晚于 Crown T12 source event**。

对应 R61：

- T12 AH：Brentford -0.5；
- T12 主客赔率：2.05 / 1.83；
- T24 AH：-0.5；
- T24 主客赔率：2.05 / 1.83；
- T12→T24 盘口线未变，赔率也未变；
- 最终赛果 Brentford 2–0 Forest。

因此该样本比“Guardian 发布时间晚于 Crown”有价值得多：它实际出现了**Crown T12 source event → 新的多来源缺阵确认 → 后续 Crown 报价仍未表现出明显线/价调整**的时间结构。

## 第一轮结论

目前不能宣布“伤停首次公开时间已经产生稳定盈利策略”，但方向值得继续。

真正需要研究的变量已经从：

> 伤停人数多少

转为：

> **信息事件相对 Crown T12 的时间位置 + 确认速度 + Crown 报价反应速度。**

目前已经确认两个重要事实：

1. Guardian article timestamp 会产生大量假阳性，不能继续直接作为“首次公开时间”；
2. 确实存在“新缺阵状态在 Crown T12 source event 之后才被多来源确认”的真实事件，也存在“信息已经公开但 Crown 后续才记录 source event”的反向情况。

## 下一轮研究方向

下一轮应继续做事件级重建，不改变现有模型身份和已确认规则：

- 从 R61 的 46 个已对账样本逐场识别“本周新出现的缺阵/状态变化”；
- 对每个事件寻找第一公开源；
- 再寻找第二、第三独立确认源；
- 计算：
  - first_public_utc
  - second_confirm_utc
  - multi_source_confirm_utc
  - Crown_T12_source_event_utc
  - Crown_T12_received_utc
  - T12→T24 line change
  - T12→T24 odds change
- 将事件分成：
  - public_before_T12
  - multi_confirm_before_T12
  - first_confirm_after_T12
  - multi_confirm_after_T12
- 最后才测试这些时间桶是否与 AH/OU 结果存在稳定关系。

本轮暂不新增 Gate、过滤条件、赔率阈值或下注规则。