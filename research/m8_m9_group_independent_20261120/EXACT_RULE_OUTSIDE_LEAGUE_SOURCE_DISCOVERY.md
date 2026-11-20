# M8原八组精确规则跨原49联赛：新数据源审计（2026-11-20）

## 已核对事实

原M8精确路径特征输入 `m8_late_full_path_water_features_20261114.jsonl` 39,101行、`m8_extra_inventory_frozen_eight_20261115.jsonl` 5,842行，联赛ID均只属于原49联赛。故先前M8画像扩展、联赛favorite/underdog研究并非原八组精确规则的跨范围测试。

发现本机另一独立 Crown 历史数据库：`/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3`，只读检查时包含 `capture` 110,133行、`asian_quote` 3,398,388行。其62类扩展赛程归档 `/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl` 有64个provider league ID、96,504赛事。按冻结原49联赛ID集合排除后，剩余15个provider ID、18,374个赛事；逐FID连接 `asian_quote.quote_before_kickoff=1` 得到7,106个存在开赛前**源事件**报价的唯一赛事。

主要外部联赛覆盖（开赛前源事件报价FID）：MLS 2,975、巴西甲932、阿根廷甲807、墨西哥Liga MX759、埃及超585、国际友谊赛492、阿尔巴尼亚超201、波黑超198、欧国联A/B/C合计137、海湾杯14、科索沃6；安道尔超与白俄罗斯超0。原始quote记录量不等于有效T6/T3/T1窗口。

## 后续具体工作

从该只读DB提取原49联赛外逐FID历史报价事件序列，核验精确开球UTC、Crown源、主客盘口线符号、T6/T3/T1可用性、完整FT，再复用 `research/m8/m8_frozen_eight_boundary_expansion_20261119.py` 中的 `assign_exact_group`/`group_side` 与原冻结精确规则；G必须保留原独立比分评分参数和可用性，不得以M9替换。按组别、联赛、年份输出新增FID、净U、ROI和跨组重叠；与冻结10294个FID去重。报价源事件时间不等于实际HTTP收件时间，不能作为正式实战。

本次只是发现可用原始报价来源，**尚未证明7,106个赛事均可精确复算，更没有发现新的盈利订单**。未修改任何生产策略或账本。
