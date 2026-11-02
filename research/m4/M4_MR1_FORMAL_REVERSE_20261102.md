# M4: MR1 AH 正式 Telegram 订单全量正打/反打结算（2026-11-02）

来源：`ljm198964-alt/mr1-shadow` master 正式账本 `data/mr1-v6-cross-market/formal/{sent.jsonl,settled.json}`，账本 `generated_at` = 2026-11-02T13:00:39.927Z。反向赔率来自同仓库 master `data/mr1-v6-cross-market/forward/records/{source_snapshot_key}.json` 中 verified Crown AH `all_sides`，并逐条核对 match_id、source_snapshot_sha256、原方向、盘口线、原单赔率，使用同一快照反方向赔率与正式结算状态反算。

- 正式已发送 574 单；已结算 497 单；当时未结算 77 单。
- 已结算涵盖 344 个不同 match_id，31 联赛；正式单以 signal_id 为单位计数，同一比赛不同正式订单不合并为一单。
- 对 497 条已结算单：历史 forward 快照成功读取 497、校验并配对 497、缺失 0。
- 正打总收益 +1.875 U、ROI +0.3773%；反打反事实收益 -32.380 U、ROI -6.5151%，每单等额一单位。
- 反方向状态：全赢 194、半赢 29、走水 22、半输 50、全输 202。
- **反打未真实发送 Telegram**；本表仅是对已有正式 TG 单按原时点 Crown 赔率的反事实计算，不是新的实盘战绩。
- 样本内逐联赛差异不可直接认定未来盈利；以下仅供 M4 研究，不自动启用反打、Pass、阈值或模型修改。

| 联赛 | 正式已结单 | 正打 PnL U | 正打 ROI | 反打 PnL U | 反打 ROI |
|---|---:|---:|---:|---:|---:|
| Colombia Primera A | 28 | +0.180 | +0.64% | -1.555 | -5.55% |
| Japan J2-League | 28 | -0.440 | -1.57% | -1.265 | -4.52% |
| England Championship | 27 | -8.215 | -30.43% | +6.320 | +23.41% |
| Italy Serie B | 27 | +0.085 | +0.31% | -1.700 | -6.30% |
| Sweden Allsvenskan | 24 | +6.005 | +25.02% | -7.740 | -32.25% |
| Spain Segunda | 24 | -2.100 | -8.75% | +0.530 | +2.21% |
| Sweden Superettan | 23 | -0.520 | -2.26% | -0.460 | -2.00% |
| Republic of Ireland Premier Division | 23 | +4.190 | +18.22% | -5.775 | -25.11% |
| Portugal Primeira Liga | 22 | +5.295 | +24.07% | -6.715 | -30.52% |
| Netherlands Eerste Divisie | 20 | +1.865 | +9.32% | -3.215 | -16.07% |
| Scotland Premiership | 20 | -2.265 | -11.33% | +1.030 | +5.15% |
| Austria 2. Liga | 18 | -0.775 | -4.31% | +0.135 | +0.75% |
| Türkiye Super Lig | 18 | -7.840 | -43.56% | +6.910 | +38.39% |
| Belgium First Division A | 17 | -1.070 | -6.29% | +0.030 | +0.18% |
| Poland Ekstraklasa | 16 | -4.335 | -27.09% | +3.455 | +21.59% |
| Austria Bundesliga | 16 | +1.935 | +12.09% | -2.770 | -17.31% |
| Ukraine Vyscha Liga | 14 | +2.420 | +17.29% | -3.210 | -22.93% |
| Denmark Division 1 | 13 | +5.820 | +44.77% | -6.690 | -51.46% |
| Switzerland Super League | 13 | -1.935 | -14.88% | +1.100 | +8.46% |
| Netherlands Eredivisie | 12 | +2.785 | +23.21% | -3.045 | -25.38% |
| Japan J-League | 11 | -9.000 | -81.82% | +7.660 | +69.64% |
| Norway Division 1 | 11 | +3.840 | +34.91% | -5.050 | -45.91% |
| South Korea K League 1 | 11 | +4.340 | +39.45% | -5.210 | -47.36% |
| Switzerland Challenge League | 10 | +1.095 | +10.95% | -1.900 | -19.00% |
| Denmark Superligaen | 9 | +1.120 | +12.44% | -1.770 | -19.67% |
| France Ligue 1 | 9 | -3.100 | -34.44% | +2.640 | +29.33% |
| Spain La Liga | 8 | +0.930 | +11.62% | -1.190 | -14.88% |
| Germany Bundesliga I | 7 | +0.275 | +3.93% | -0.520 | -7.43% |
| Italy Serie A | 7 | +0.795 | +11.36% | -1.030 | -14.71% |
| Norway Eliteserien | 6 | +0.185 | +3.08% | -0.650 | -10.83% |
| Germany Bundesliga II | 5 | +0.310 | +6.20% | -0.730 | -14.60% |

核查：正式账本生成时间可能早于当前时间；M4 全量计算截至该已读快照。没有改 MR1 生产策略、TG 通知、账本或结算。
