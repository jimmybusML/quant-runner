# 2026-11-03 M1 + MR1 正式 TG 补结后联赛亏损来源

- 来源：原 M1 正式 TG 账本（旧版/补结版）以及原 MR1 V6 AH 正式 TG settled.json（497笔/557笔）；补结的 TG 身份不变，研究数据生成 2026-11-03T06:51Z；只读分析，未修改生产策略。
- 总计新补结 67 单，净 -23.270 U：M1 AH 7 单 -2.770 U；MR1 AH 60 单 -20.500 U；MR1 新结 60 单 47 场独立比赛。
- 正式 MR1 60 新结状态：全赢 13、半赢 5、走水 4、半输 6、全输 32。

## 新补结 MR1 按联赛

| League | New settled TG bets | Distinct matches | Net U |
|---|---:|---:|---:|
| Portugal Primeira Liga | 9 | 5 | -5.070 |
| Norway Division 1 | 7 | 6 | -5.060 |
| Colombia Primera A | 4 | 3 | -2.500 |
| France Ligue 1 | 2 | 2 | -2.000 |
| Poland Ekstraklasa | 2 | 2 | -2.000 |
| Italy Serie B | 5 | 3 | -1.685 |
| Sweden Allsvenskan | 6 | 4 | -1.650 |
| Sweden Superettan | 2 | 1 | -1.500 |
| Denmark Superligaen | 3 | 3 | -1.150 |
| Denmark Division 1 | 1 | 1 | -1.000 |
| Austria Bundesliga | 1 | 1 | -1.000 |
| Germany Bundesliga I | 1 | 1 | -1.000 |
| Ukraine Vyscha Liga | 1 | 1 | -1.000 |
| Netherlands Eerste Divisie | 2 | 2 | -0.590 |
| Türkiye Super Lig | 1 | 1 | +0.830 |
| Netherlands Eredivisie | 1 | 1 | +0.960 |
| Switzerland Super League | 2 | 2 | +1.090 |
| Spain Segunda | 6 | 5 | +1.795 |
| Belgium First Division A | 4 | 3 | +2.030 |

## 新补结 M1 AH 按联赛

| League | TG bets | Net U |
|---|---:|---:|
| France Ligue 1 | 1 | -1.000 |
| England Premier League | 1 | -1.000 |
| Romania Liga I | 1 | -1.000 |
| Poland Ekstraklasa | 1 | -1.000 |
| Argentina Liga Profesional | 2 | +0.330 |
| Colombia Primera A | 1 | +0.900 |

## 上周 2026-10-26 至 2026-11-01 MR1 AH 全部已结算按联赛

| League | Settled TG bets | Distinct matches | Net U |
|---|---:|---:|---:|
| England Championship | 17 | 11 | -9.165 |
| Portugal Primeira Liga | 14 | 9 | -6.350 |
| Colombia Primera A | 15 | 11 | -6.205 |
| Norway Division 1 | 8 | 7 | -6.060 |
| France Ligue 1 | 5 | 4 | -5.000 |
| Türkiye Super Lig | 11 | 7 | -4.390 |
| Italy Serie B | 23 | 16 | -3.955 |
| Denmark Superligaen | 6 | 6 | -3.150 |
| Japan J-League | 3 | 3 | -3.000 |
| Belgium First Division A | 12 | 8 | -2.300 |
| Poland Ekstraklasa | 7 | 5 | -2.095 |
| Japan J2-League | 7 | 7 | -1.800 |
| Germany Bundesliga II | 3 | 3 | -1.520 |
| Sweden Superettan | 10 | 8 | -0.715 |
| South Korea K League 1 | 4 | 3 | -0.110 |
| Spain La Liga | 5 | 5 | +0.060 |
| Denmark Division 1 | 7 | 5 | +0.280 |
| Italy Serie A | 4 | 4 | +0.410 |
| Norway Eliteserien | 2 | 1 | +0.465 |
| Netherlands Eerste Divisie | 9 | 8 | +0.690 |
| Germany Bundesliga I | 3 | 2 | +0.900 |
| Sweden Allsvenskan | 18 | 13 | +1.020 |
| Netherlands Eredivisie | 7 | 5 | +1.310 |
| Switzerland Super League | 6 | 4 | +1.460 |
| Austria Bundesliga | 9 | 6 | +1.720 |
| Ukraine Vyscha Liga | 4 | 2 | +2.195 |
| Austria 2. Liga | 8 | 5 | +2.390 |
| Switzerland Challenge League | 4 | 2 | +3.265 |
| Scotland Premiership | 11 | 8 | +5.235 |
| Republic of Ireland Premier Division | 8 | 5 | +5.430 |
| Spain Segunda | 16 | 11 | +6.345 |

## 同场多笔 TG 订单的相关性

- MR1 新补结的 60 笔正式 TG 订单对应 47 个 match_id；12 场比赛有不止一笔真实 TG 订单，共 25 笔，净 -7.500U。其余 35 场各一笔，净 -13.000U。
- 这是 **同场多笔真实订单**，不是计算程序重复记账；不要把 60 单等同 60 个独立比赛，亦不应未经用户确认改变正式派单幂等或数量规则。

| League | Match | Formal TG bets | Total U |
|---|---|---:|---:|
| Portugal Primeira Liga | Braga vs Famalicao | 2 | -2.000 |
| Norway Division 1 | Lyn 1896 vs Raufoss | 2 | -2.000 |
| Italy Serie B | Palermo vs Vicenza | 2 | -2.000 |
| Portugal Primeira Liga | FC Arouca vs Nacional | 3 | -1.500 |
| Portugal Primeira Liga | Academico Viseu vs Rio Ave | 2 | -1.500 |
| Colombia Primera A | Deportivo Cali vs Boyaca Chico | 2 | -1.500 |
| Sweden Allsvenskan | GAIS vs AIK | 2 | -1.500 |
| Sweden Superettan | Landskrona vs Orebro SK | 2 | -1.500 |
| Italy Serie B | Arezzo vs Ascoli | 2 | +1.315 |
| Sweden Allsvenskan | Elfsborg vs Orgryte IS | 2 | +1.350 |
| Spain Segunda | Burgos vs CD Castellon | 2 | +1.365 |
| Belgium First Division A | Lommel vs Gent | 2 | +1.970 |

## 解释边界

这次收益突然变化的直接原因是赛果结算账本延迟，本轮重新查询已完场比赛并结算。不能据此断定模型在补结当天突然产生所有亏损。英冠是上周原方向总体最大亏损（-9.165U），但这次新增 MR1 亏损最集中在葡超（-5.070U）与挪威甲级（-5.060U）。研究分析不代表任何新的联赛剔除、反打或同场派单限制已经生效。
