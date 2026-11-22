# 2019–2026历史库存补齐｜阶段检查点 2026-11-22 01:11 UTC

本文件记录进行中的数据补齐任务。它不是全量完成声明。

## 已核验赛事库存

- 已发现并按精确provider ID/名称映射对齐：118个TotalCorner联赛ID；不同赛事来源按FID保留来源行，不以名称相似做自动合并。
- 合并库存：203,962个唯一FID。其输入包括原141,623 FID库存和53批TotalCorner赛程（89,842个唯一FID；与原库存重叠27,503，净增加62,339）。
- 193,014个FID已有至少一个可信完整FT来源；10,948个仍缺可信完整FT。最近一次按源状态分类将其拆为：300场尚未开赛、2场开赛时间缺失、294场没有可见赛程/比分来源、9,229场状态缺失或未知、1,123场状态非full但含义未核实。另9,737场出现占位0:0，该值未当作已核实比分。分类可能互相交叠，尤其占位0:0不与状态类别相加。
- 该118联赛范围是从当前正式配置、赛程来源、历史缓存和既有映射中识别出的并集，仍继续检查遗漏来源；不代表全球联赛全集已穷尽。

## Crown历史movement补采状态

- 原movement缺层队列：101,266个FID，manifest SHA256 `5e24fc27dba4047f52d4a40bef74b50a0dc13694194ecf150f437bc26147d79a`。summary缺层的独立队列另有153,762个FID；本检查点未启动summary批次，避免与正在使用的TotalCorner采集资源并行。
- 安全窗口驱动PID 59381仍运行。最近一次记录的collector PID 74018在01:08:59 UTC因正式赛果任务启动而暂停，driver继续守候互斥窗口；没有手工终止或并发启动第二个Crown collector。
- 截至SQLite查询时点01:08:57 UTC，movement队列中280个FID已有终态Capture：257个`QUOTES_SAVED`共57,380条AH movement报价，23个`NO_CROWN_AH_QUOTES`。按原队列计算尚有100,986个FID未形成终态。`NO_CROWN_AH_QUOTES`仅代表该次响应无AH报价，不推断历史上绝无报价。
- 当前append log计有257条SAVED、23条NO_CROWN_AH_QUOTES和18条FETCH_FAILED尝试记录；失败会保留并进入恢复逻辑。安全暂停期间的KeyboardInterrupt traceback也写入合并stdout日志，JSONL汇总器会跳过非JSON行；源响应、Capture和failed_attempt分别保存，后续继续核实失败重试状态。
- 全库SQLite只读观察：movement历史层53,257个有报价FID、4,487,330条报价行；summary历史层49,054个有报价FID、99,242条报价行；此外95个FID/278行Crown真实现场收据独立保留，未与历史回取混算。另有49,721个movement层FID的历史Capture为无报价状态。数据库quote行中movement源事件时间均有值，1,488条实际接收时间为空；缺失保持为空，不用文件时间补造。
- 当前请求沿用原采集器默认5.2秒间隔、历史缓存复用、source event与HTTP实际接收时间分开记录，所有新增批次标为`historical`；实际Crown报价和FT仍逐源保存，未用其他博彩公司填补。

## 复算输入

- `fixture_inventory_2019_2026.jsonl.gz` SHA256 `b25d73d97f0dd3ba4be4fa609f2fadcb626bee10d373c873495e3d348f23f83c`
- `fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz` SHA256 `25dfbeba66b8161a3ea80af49afdcf1eda81b792cffbf2023a1b6986212e881e`
- `supplemental_totalcorner_schedules_53leagues_2019_2026.jsonl.gz` SHA256 `861e5884f4a97307c0e5fa82366194cfc6a3ccad335c7e11f1a7817a4be7b119`
- `unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz` SHA256 `3e5bceeced007bdaf3ec2dc31be0b612f4fe34a928434c46700aa84af5c91968`
- `unverified_ft_readiness_203962_inventory_20261122.jsonl` SHA256 `23214da746462daebe6e70b99d56db8475b86798d6b7152f134b43635dc8b755`
- `unverified_ft_readiness_203962_inventory_by_league_year_20261122.csv` SHA256 `fe9ea28b7d19e8cca7adc2c2e4feb44aea4e04dffa64ea68f93c961d31266a6d`

详细逐FID及联赛×年份覆盖留在私有Mac研究目录；公开交接仅发布汇总、脚本和哈希引用，不上传Crown原始HTTP响应或数据库。

## 后续实际工作

1. 让当前movement队列在安全窗口内续跑；结批后从SQLite重新生成未终态队列并复核每个失败FID。
2. 完成movement并校核原始响应SHA、source time、receive time、线水和联赛×年份覆盖后，再对独立summary层续跑。
3. 复查2019–2022年ID 51、61、10480等旧报价稀疏项，并持续枚举尚未纳入118项来源并集的现有联赛映射。
4. 分批补核10,948个FT缺口：已归档来源优先逐FID严核，未知/非full状态不猜测含义；无可靠来源的保留缺口。
5. 更新完整逐联赛、逐赛季、逐FID覆盖表和输入/输出SHA，报告新增比赛、FT、Crown报价行数及各来源限制。

本轮仅检查和保存数据恢复进度；没有模型训练、策略研究、回测、Telegram派单或正式账本修改。
