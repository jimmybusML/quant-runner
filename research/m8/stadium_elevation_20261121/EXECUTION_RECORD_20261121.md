# 执行记录：M8 球场海拔差 × Crown AH

执行日期：2026-11-21（北京时间）  
研究工作树：`/private/tmp/quant-runner-m8-crossleague`  
研究分支：`research/m8-exact-cross-league-expansion`  
执行类型：只读 Crown 历史审计 + 研究文件生成；没有调用生产接口、派单或回写账本。

## 实际执行

| 阶段 | 实际命令/动作 | 结果 |
|---|---|---|
| 赛前主场代理 | `prepare_altitude_targets.py` | 11,686 个已对齐比赛行；9,149 个全期八组外 FID；目标赛前回看 365 天并排除目标日前 3 天 |
| 追加15联赛场地覆盖 | `audit_new15_venue_linkage.py` | 2024–2026 有 4,403 个完整 Crown 路径 FID；83 个严格 Transfermarkt 唯一匹配，78 个双方唯一先前主场，补充坐标/高程后 17 个双方均有海拔且都属于 provider league 85 |
| 场地地理连接 | OSM Nominatim 串行缓存查询 + `build_venue_coordinate_catalog.py` | 416 个原始 venue-country 查询；新增17个扩展联赛场地查询；全库得到229个接受坐标项、223个唯一坐标；名称不符/歧义保留未解析 |
| 海拔 | `fetch_srtm90_elevation.py` | SRTM90m 原始响应缓存；先前214坐标已缓存，本轮新增9坐标一个批次成功，新增批次空值0；总计223坐标中2个海拔为空 |
| 时间前推 | `run_stadium_elevation_ah.py` | 2024/2025/2026 分年度训练，仅用目标年之前历史；训练行 1,762/2,647/3,794；候选测试行 680/915/386，合计1,981 |
| Crown/FT 独立校验 | `verify_stadium_elevation_crown_ft_20261121.py` | 1,981/1,981 FID 的 Crown 原始响应 SHA、联赛/球队ID、开球、T−60 行情、FT 和 AH 结算通过；3模型共5,943行，错误0 |

SQLite movement 表直接提供1,953场 T−60 行。另28场（均为2026）没有对应的 movement 行，但它们的 summary capture 指向的 SHA 绑定原始 Crown 响应保留完整 `asian_list`；独立校验器从 raw 响应恢复每场最新 T−60 行并逐场比对，28/28均一致。全部1,981个历史响应的 HTTP 收件时间均晚于开球，历史响应均不能当作真实赛前收据。

## 样本与收益概览

- 1,981 个八组外唯一候选 FID，与冻结原八组重叠0。
- 同一测试集上 Market only +7.970U；Market+team −97.970U；Market+team+elevation −98.190U。
- 加入高程相对 Market+team 的净利润变化 −0.220U，最大回撤更高，目标净胜球 RMSE/MAE 略差。
- 1981个全量候选跨132个观察周，历史均值15.008单/周；2026部分年度覆盖至已有Transfermarkt比赛数据2026-07-06。
- 严格 T−60 原始响应事件回放没有实收前瞻验证：HTTP response received before kickoff FID = 0。
- 同期冻结八组基线5,955单、+164.085U；合并经核验的高程模型后7,936单、+65.895U，新增净贡献−98.190U。

详细年度、周度、月份、联赛、赔率与结算计数位于 `altitude_crown_ah_summary_20261121.json`；逐场模型预测位于 `altitude_per_fixture_predictions_20261121.jsonl.gz`，独立结算复核位于 `independent_crown_ft_per_fixture_20261121.jsonl.gz`。

## 工程与生产状态

没有改动 `M8`、M1、MR1、M9 的正式策略，没有新增正式 Gate/过滤/限额，没有改动 Telegram、正式账本、Crown 生产采集链或自动调度；没有提交或宣称 Telegram 派单和正式实战。

