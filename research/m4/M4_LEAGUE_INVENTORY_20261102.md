# M4 / MR1 全联赛历史研究池统计（2026-11-02）

来源 GitHub Actions run 41382404863（success），原始 artifact m4-paired-ft-research；代码提交 eb1280b4。研究池为 MR1 V6 forward 多时点研究，非 TG 实战策略，也非 M3。

全量研究文件 18418 条，104 联赛；可验证配对 1563 独立场，11980 有效快照。每联赛“独立场数”按比赛 ID；各联赛之间未合并。表中 ROI 是每场在 T0.5 的模型 selected 盘口历史反事实收益，非正式 MR1 选单回测。

配置来源：MR1 master/config/validation-spec.json 的 competition_scope country token / exclusion tokens。这里仅按联赛名称字符串检查这两个字段，**不是**正式完整准入结论；未知/排除词结果也不应据此修改策略。配置 token 名称匹配可能有误判，需后续核验正式 MR1 selector 同时运行的全部条件。

简要名称规则分组：国家词命中 104 联赛/累计 2533 独立赛事；排除词命中 0 联赛/0 场；其他 0 联赛/0 场。该分组不是最终目标范围核验。

| 联赛 | 研究独立场 | 有效 FT 独立场 | T0.5 AH 样本 | T0.5 AH ROI | T0.5 OU ROI | 配置名称初筛 |
|---|---:|---:|---:|---:|---:|---|
| England Championship | 70 | 55 | 53 | -12.5% | -6.8% | 国家词命中（待完整策略核验） |
| Japan J2-League | 70 | 45 | 37 | 3.7% | 16.7% | 国家词命中（待完整策略核验） |
| Colombia Primera A | 63 | 40 | 39 | 20.0% | 27.3% | 国家词命中（待完整策略核验） |
| Spain Segunda | 55 | 37 | 37 | -21.3% | -5.6% | 国家词命中（待完整策略核验） |
| Italy Serie A | 50 | 28 | 27 | -18.9% | -31.2% | 国家词命中（待完整策略核验） |
| Italy Serie B | 50 | 39 | 38 | -2.9% | 2.6% | 国家词命中（待完整策略核验） |
| Japan J-League | 50 | 41 | 38 | -8.3% | -20.1% | 国家词命中（待完整策略核验） |
| Norway Division 1 | 49 | 33 | 31 | 1.1% | -17.0% | 国家词命中（待完整策略核验） |
| Netherlands Eerste Divisie | 48 | 35 | 29 | -3.7% | 14.1% | 国家词命中（待完整策略核验） |
| Türkiye 1 Lig | 46 | 29 | 27 | -5.3% | -20.4% | 国家词命中（待完整策略核验） |
| Saudi Arabia Pro League | 45 | 27 | 25 | 1.5% | -13.7% | 国家词命中（待完整策略核验） |
| Spain La Liga | 41 | 29 | 28 | 1.7% | 7.6% | 国家词命中（待完整策略核验） |
| England Premier League | 40 | 21 | 21 | 14.1% | -11.1% | 国家词命中（待完整策略核验） |
| Sweden Allsvenskan | 40 | 32 | 31 | 14.4% | 12.7% | 国家词命中（待完整策略核验） |
| Romania Liga II | 39 | 27 | 27 | -26.2% | -8.7% | 国家词命中（待完整策略核验） |
| Poland Ekstraklasa | 37 | 32 | 31 | -30.0% | -9.7% | 国家词命中（待完整策略核验） |
| Poland I Liga | 37 | 20 | 18 | -19.6% | 1.1% | 国家词命中（待完整策略核验） |
| China Division 1 | 36 | 16 | 15 | -2.5% | 0.8% | 国家词命中（待完整策略核验） |
| France Ligue 1 | 36 | 25 | 22 | -35.4% | -10.7% | 国家词命中（待完整策略核验） |
| France Ligue 2 | 36 | 23 | 23 | -30.4% | -13.4% | 国家词命中（待完整策略核验） |
| Germany Bundesliga I | 36 | 23 | 23 | 1.9% | 3.4% | 国家词命中（待完整策略核验） |
| Germany Bundesliga II | 36 | 26 | 25 | -11.9% | 57.0% | 国家词命中（待完整策略核验） |
| Netherlands Eredivisie | 36 | 26 | 26 | 25.3% | -19.3% | 国家词命中（待完整策略核验） |
| Czechia First League | 33 | 16 | 16 | -20.9% | 45.8% | 国家词命中（待完整策略核验） |
| Egypt Division 2 | 33 | 23 | 21 | 24.3% | -13.0% | 国家词命中（待完整策略核验） |
| Romania Liga I | 33 | 19 | 17 | -28.7% | -12.5% | 国家词命中（待完整策略核验） |
| Türkiye Super Lig | 33 | 27 | 27 | -34.7% | 5.5% | 国家词命中（待完整策略核验） |
| Austria 2. Liga | 32 | 28 | 27 | 2.8% | 15.5% | 国家词命中（待完整策略核验） |
| Czechia 2. Liga | 32 | 20 | 19 | 15.7% | -13.8% | 国家词命中（待完整策略核验） |
| Norway Eliteserien | 32 | 20 | 20 | 19.7% | -6.5% | 国家词命中（待完整策略核验） |
| South Korea K League 2 | 32 | 18 | 18 | -30.4% | -21.7% | 国家词命中（待完整策略核验） |
| Sweden Superettan | 32 | 27 | 26 | -2.5% | -10.2% | 国家词命中（待完整策略核验） |
| Northern Ireland Premier | 31 | 14 | 9 | 65.7% | -35.7% | 国家词命中（待完整策略核验） |
| Ukraine Vyscha Liga | 31 | 23 | 21 | 23.3% | -41.3% | 国家词命中（待完整策略核验） |
| Wales Premier League | 31 | 11 | 10 | -13.1% | -32.7% | 国家词命中（待完整策略核验） |
| Serbia Super Liga | 30 | 18 | 17 | -49.1% | 16.7% | 国家词命中（待完整策略核验） |
| Kazakhstan Premier League | 29 | 17 | 12 | -39.5% | -32.4% | 国家词命中（待完整策略核验） |
| Cyprus Division 1 | 28 | 14 | 14 | -26.7% | -1.9% | 国家词命中（待完整策略核验） |
| Israel Premier League | 28 | 13 | 13 | -17.8% | 31.6% | 国家词命中（待完整策略核验） |
| Portugal Primeira Liga | 28 | 21 | 18 | 3.8% | -0.3% | 国家词命中（待完整策略核验） |
| Portugal Segunda Liga | 28 | 12 | 12 | 29.9% | -26.5% | 国家词命中（待完整策略核验） |
| Scotland Championship | 28 | 12 | 7 | 13.7% | 40.3% | 国家词命中（待完整策略核验） |
| Malta Premier League | 27 | 17 | 13 | 11.9% | 28.2% | 国家词命中（待完整策略核验） |
| Scotland Premiership | 27 | 25 | 23 | -1.5% | -9.8% | 国家词命中（待完整策略核验） |
| Egypt Division 1 | 26 | 17 | 17 | -30.4% | -49.0% | 国家词命中（待完整策略核验） |
| Greece Super League 1 | 26 | 12 | 12 | -28.6% | -5.3% | 国家词命中（待完整策略核验） |
| Slovakia Super Liga | 26 | 12 | 11 | 38.8% | 35.5% | 国家词命中（待完整策略核验） |
| Belgium First Division A | 25 | 19 | 19 | -6.6% | -29.1% | 国家词命中（待完整策略核验） |
| Austria Bundesliga | 24 | 23 | 23 | -20.4% | -35.7% | 国家词命中（待完整策略核验） |
| China Super League | 24 | 24 | 23 | -11.1% | -7.8% | 国家词命中（待完整策略核验） |
| Denmark Division 1 | 24 | 22 | 22 | -0.7% | 9.8% | 国家词命中（待完整策略核验） |
| Denmark Superligaen | 24 | 19 | 18 | 7.3% | 4.3% | 国家词命中（待完整策略核验） |
| Finland Veikkausliiga | 24 | 15 | 15 | -36.5% | 43.8% | 国家词命中（待完整策略核验） |
| Israel Leumit Liga | 24 | 19 | 14 | -10.3% | 1.2% | 国家词命中（待完整策略核验） |
| South Korea K League 1 | 24 | 21 | 21 | 4.7% | -23.5% | 国家词命中（待完整策略核验） |
| Estonia Meistriliiga | 23 | 11 | 11 | -1.2% | -4.9% | 国家词命中（待完整策略核验） |
| Saudi Arabia Division 1 | 23 | 12 | 10 | -0.4% | 24.1% | 国家词命中（待完整策略核验） |
| Slovakia 2. Liga | 23 | 7 | 7 | 40.3% | 6.0% | 国家词命中（待完整策略核验） |
| Belgium First Division B | 21 | 7 | 7 | -40.1% | -24.5% | 国家词命中（待完整策略核验） |
| Bulgaria First League | 21 | 9 | 9 | -24.1% | -9.4% | 国家词命中（待完整策略核验） |
| Latvia Virsliga | 21 | 12 | 10 | 24.4% | -15.6% | 国家词命中（待完整策略核验） |
| Republic of Ireland Premier Division | 21 | 20 | 20 | 6.9% | 5.8% | 国家词命中（待完整策略核验） |
| Croatia HNL | 20 | 10 | 10 | 34.8% | -7.2% | 国家词命中（待完整策略核验） |
| Slovenia Prva Liga | 20 | 10 | 9 | 14.8% | -5.0% | 国家词命中（待完整策略核验） |
| Republic of Ireland First Division | 19 | 10 | 8 | 64.4% | 33.1% | 国家词命中（待完整策略核验） |
| Croatia 1.NL | 18 | 11 | 10 | -26.9% | -12.0% | 国家词命中（待完整策略核验） |
| Iceland Premier League | 18 | 11 | 10 | 49.3% | -8.4% | 国家词命中（待完整策略核验） |
| Switzerland Super League | 18 | 13 | 13 | -1.5% | 16.6% | 国家词命中（待完整策略核验） |
| Bulgaria Second League | 17 | 8 | 8 | 46.1% | -29.5% | 国家词命中（待完整策略核验） |
| Greece Super League 2 | 17 | 3 | 3 | -83.3% | 32.7% | 国家词命中（待完整策略核验） |
| Hungary NB I | 17 | 8 | 8 | 55.9% | 20.5% | 国家词命中（待完整策略核验） |
| Slovenia 2. SNL | 17 | 4 | 4 | 4.0% | 19.8% | 国家词命中（待完整策略核验） |
| Wales Championship South | 17 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Azerbaijan Premier League | 16 | 9 | 6 | -1.5% | -70.0% | 国家词命中（待完整策略核验） |
| Wales Championship North | 16 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Lithuania 1 Lyga | 15 | 6 | 6 | -13.4% | -8.5% | 国家词命中（待完整策略核验） |
| Switzerland Challenge League | 15 | 12 | 12 | 17.8% | 13.9% | 国家词命中（待完整策略核验） |
| Serbia Prva Liga | 14 | 6 | 6 | 47.7% | 22.6% | 国家词命中（待完整策略核验） |
| Lithuania A Lyga | 13 | 5 | 5 | -62.6% | -61.2% | 国家词命中（待完整策略核验） |
| Montenegro Prva Liga | 11 | 6 | 6 | -10.5% | -83.3% | 国家词命中（待完整策略核验） |
| Bosnia & Herzegovina 1st League | 10 | 4 | 4 | 0.0% | -4.0% | 国家词命中（待完整策略核验） |
| Finland Ykkosliiga | 10 | 10 | 10 | 66.6% | -22.6% | 国家词命中（待完整策略核验） |
| Georgia Erovnuli Liga | 10 | 5 | 4 | 27.9% | 82.0% | 国家词命中（待完整策略核验） |
| Hungary NB II | 9 | 3 | 3 | 90.3% | 26.7% | 国家词命中（待完整策略核验） |
| Albania Championship | 8 | 2 | 2 | 92.5% | -31.0% | 国家词命中（待完整策略核验） |
| Armenia Premier League | 8 | 3 | 3 | 80.3% | 28.7% | 国家词命中（待完整策略核验） |
| Bosnia & Herzegovina Premier Liga | 8 | 2 | 2 | 89.0% | 87.0% | 国家词命中（待完整策略核验） |
| Northern Ireland Championship | 8 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Ukraine Persha Liga | 8 | 2 | 2 | -75.0% | -5.5% | 国家词命中（待完整策略核验） |
| Estonia Esiliiga | 7 | 6 | 6 | -12.3% | 22.8% | 国家词命中（待完整策略核验） |
| Albania First Division | 6 | 3 | 3 | 62.2% | 22.3% | 国家词命中（待完整策略核验） |
| Cyprus Division 2 | 5 | 2 | 2 | -100.0% | -100.0% | 国家词命中（待完整策略核验） |
| Azerbaijan Division 1 | 4 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Montenegro Druga Liga | 4 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| North Macedonia First League | 4 | 3 | 3 | -37.3% | 13.3% | 国家词命中（待完整策略核验） |
| Malta Challenge League | 3 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Northern Ireland Conference Premier | 3 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| South Korea (W) K League | 3 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| South Korea K League 3 | 3 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Kosovo Division 2 | 2 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Faroe Islands Premier League | 1 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Kosovo Division 1 | 1 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Kosovo Superliga | 1 | 0 | — | — | — | 国家词命中（待完整策略核验） |
| Latvia 1. Liga | 1 | 1 | 1 | -100.0% | -50.0% | 国家词命中（待完整策略核验） |

**注意**：小样本 ROI 极不稳定；不同联赛时间/盘口组成不同，不能据此直接删联赛或上线新过滤。需要基于真实 MR1 selector 严格重放，联赛/小时同场对照，以及前推验证。M3 是否同场有历史预测与同一 Crown 报价另行核验；不能拿 M3 旧五大联赛 OOS 与这些赛事假配对。
