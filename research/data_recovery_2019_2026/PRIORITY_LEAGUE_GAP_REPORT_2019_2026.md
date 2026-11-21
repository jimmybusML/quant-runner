# 2019–2026 点名联赛历史库存缺口离线核查

> 本报告仅核查现有规范化库存和本机只读 Crown SQLite；没有发网络请求、没有把缺失比分或盘口补造为有效数据，也不缩小全量补采范围。

- 生成时间 UTC：`2026-11-21T19:35:29.212708+00:00`
- 库存文件 SHA256：`c0bccf93b87aafd072db9f3237977e65d14002d52393e637082bef5d9c59455a`
- Crown SQLite SHA256：`292ccbde5afe72490e2978599640e8a06a075d8d73c5210f75b002046414d298`
- 逐响应原始证据账本：`priority_league_gap_noquote_receipts_2019_2022.jsonl.gz`；含私有原始文件路径和每条响应SHA，原始HTTP body未复制到仓库。

## 全期按 UTC 年覆盖

| 联赛 ID / 名称 | UTC年 | 库存 FID | status=full 且数字 FT | Movement capture FID | 明确无 Crown AH FID | Crown AH 报价 FID | Movement 报价行 | T6 FID |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 51 Portugal Primeira Liga | 2019 | 309 | 306 | 134 | 134 | 0 | 0 | 0 |
| 51 Portugal Primeira Liga | 2020 | 293 | 273 | 273 | 273 | 0 | 0 | 0 |
| 51 Portugal Primeira Liga | 2021 | 352 | 346 | 346 | 346 | 0 | 0 | 0 |
| 51 Portugal Primeira Liga | 2022 | 291 | 282 | 282 | 282 | 0 | 0 | 0 |
| 51 Portugal Primeira Liga | 2023 | 316 | 315 | 315 | 198 | 117 | 7227 | 44 |
| 51 Portugal Primeira Liga | 2024 | 320 | 314 | 314 | 4 | 310 | 20650 | 227 |
| 51 Portugal Primeira Liga | 2025 | 305 | 302 | 302 | 20 | 282 | 24791 | 282 |
| 51 Portugal Primeira Liga | 2026 | 276 | 257 | 254 | 0 | 254 | 52320 | 254 |
| 61 Switzerland Super League | 2019 | 185 | 180 | 90 | 90 | 0 | 0 | 0 |
| 61 Switzerland Super League | 2020 | 169 | 152 | 152 | 152 | 0 | 0 | 0 |
| 61 Switzerland Super League | 2021 | 206 | 203 | 203 | 203 | 0 | 0 | 0 |
| 61 Switzerland Super League | 2022 | 170 | 167 | 167 | 167 | 0 | 0 | 0 |
| 61 Switzerland Super League | 2023 | 211 | 208 | 208 | 142 | 66 | 3300 | 26 |
| 61 Switzerland Super League | 2024 | 228 | 228 | 228 | 40 | 188 | 10541 | 149 |
| 61 Switzerland Super League | 2025 | 234 | 232 | 232 | 30 | 202 | 13634 | 199 |
| 61 Switzerland Super League | 2026 | 207 | 195 | 188 | 3 | 185 | 31959 | 185 |
| 10480 Georgia Erovnuli Liga | 2019 | 174 | 169 | 169 | 169 | 0 | 0 | 0 |
| 10480 Georgia Erovnuli Liga | 2020 | 87 | 86 | 86 | 86 | 0 | 0 | 0 |
| 10480 Georgia Erovnuli Liga | 2021 | 176 | 174 | 174 | 174 | 0 | 0 | 0 |
| 10480 Georgia Erovnuli Liga | 2022 | 182 | 175 | 175 | 175 | 0 | 0 | 0 |
| 10480 Georgia Erovnuli Liga | 2023 | 176 | 175 | 175 | 149 | 26 | 423 | 11 |
| 10480 Georgia Erovnuli Liga | 2024 | 174 | 168 | 168 | 82 | 86 | 1395 | 70 |
| 10480 Georgia Erovnuli Liga | 2025 | 172 | 169 | 169 | 68 | 101 | 2354 | 99 |
| 10480 Georgia Erovnuli Liga | 2026 | 161 | 157 | 113 | 0 | 113 | 14867 | 109 |

## 2019–2022 无 Crown AH 报价响应逐条核验

- 2,594 个赛程 FID中，2251 条历史 movement capture 明确标为 `NO_CROWN_AH_QUOTES`；其中 2251 个唯一 FID 的原始响应SHA、FID/联赛/球队身份和 Crown `asian_list=[]` 均逐条通过核对。capture 状态为历史回取，`response_received_at_utc` 是回取实际接收时间，不是赛前实收。
- 另有 343 个 FID 没有 movement capture；它们不是已确认无盘口，也没有可供校验的 Crown 原始响应。
- 按联赛 / UTC年拆开，下面依次为“库存FID / verified full FT / 明确无 AH 响应 / 无 movement capture / 有 Crown AH FID”：

| 联赛 ID | 年 | 库存 / full FT / no-quote / no-capture / 有报价 FID |
|---:|---:|---|
| 51 | 2019 | 309 / 306 / 134 / 175 / 0 |
| 51 | 2020 | 293 / 273 / 273 / 20 / 0 |
| 51 | 2021 | 352 / 346 / 346 / 6 / 0 |
| 51 | 2022 | 291 / 282 / 282 / 9 / 0 |
| 61 | 2019 | 185 / 180 / 90 / 95 / 0 |
| 61 | 2020 | 169 / 152 / 152 / 17 / 0 |
| 61 | 2021 | 206 / 203 / 203 / 3 / 0 |
| 61 | 2022 | 170 / 167 / 167 / 3 / 0 |
| 10480 | 2019 | 174 / 169 / 169 / 5 / 0 |
| 10480 | 2020 | 87 / 86 / 86 / 1 / 0 |
| 10480 | 2021 | 176 / 174 / 174 / 2 / 0 |
| 10480 | 2022 | 182 / 175 / 175 / 7 / 0 |

## 结论与边界

- ID 51、61、10480 在 2019–2022 的赛程和 status=full 赛果已大部分存在于当前跨源库存；本核查没有证据支持将“缺少历史赛事/赛果”概括为这几年的整体状态。完整 FT 计数只认可提供 `status=full` 且比分为数字的源行；其余数字比分可能来自非 full/占位记录，不计为已验证 FT。
- 这三个联赛在 2019–2022 没有任何 Crown movement AH 报价行。2,251 场已有经SHA核验的成功响应，其中 Crown 书商存在但亚洲盘数组为空；343 场连 movement capture 都没有。该证据说明当前回放库存状态，不证明上游接口永远无法返回历史盘口；尚未再次请求这343场。
- 2023–2026 已能看到部分或大量 Crown AH movement报价，说明其覆盖按年份变化。所有 `prospective_quote_rows` 均为0；这些历史报价不属于当时HTTP赛前实收。
- 发现的源映射/FT冲突和失败尝试仍单独保留在JSON；本次没有按名称强行合并ID，也没有删除现有记录。此三联赛专项核查不代替全115联赛及全部来源的整体覆盖复核。

机器可读逐联赛逐年结果：`priority_league_gap_inventory_2019_2026.json`。
