# R9: Expanded five-year positive candidate search (2019-2023 only)

New candidate vocabulary: signed handicap line, actual bet-side odds, same-line no-vig probability movement and interactions. Feature bins are exploratory and not production rules.

Examined 6350 candidate definitions; 61 show positive net U in every year 2019-2023. With 27 prior R7 candidates, 88 candidate definitions total, not necessarily independent.

## All 61 candidates, year by year

| Candidate ID | 2019 ROI | 2020 ROI | 2021 ROI | 2022 ROI | 2023 ROI | N | Net U | ROI | Max DD U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| T2|side_price,prob_delta|side_price=1;prob_delta=3|underdog | +5.36% | +2.31% | +12.00% | +0.14% | +4.21% | 1022 | +55.055 | +5.39% | 12.950 |
| T2|side_price,momentum,prob_delta|side_price=2;momentum=2;prob_delta=1|favorite | +20.38% | +2.60% | +2.70% | +7.41% | +1.69% | 1016 | +51.320 | +5.05% | 18.285 |
| T2|side_price,momentum,prob_delta|side_price=1;momentum=2;prob_delta=3|underdog | +8.78% | +0.27% | +8.74% | +0.40% | +13.16% | 592 | +50.870 | +8.59% | 10.700 |
| T2|side_price,prob_delta|side_price=2;prob_delta=1|favorite | +13.31% | +0.22% | +0.61% | +5.86% | +1.14% | 1251 | +37.360 | +2.99% | 15.805 |
| T12|age,prob_delta|age=2;prob_delta=3|home | +2.04% | +3.80% | +8.67% | +3.70% | +2.18% | 795 | +32.430 | +4.08% | 26.010 |
| T2|line,side_price,prob_delta|line=0;side_price=2;prob_delta=1|favorite | +32.79% | +37.15% | +15.85% | +15.38% | +17.42% | 137 | +30.840 | +22.51% | 3.100 |
| T6|side_price|side_price=0|underdog | +20.00% | +26.63% | +1.74% | +5.39% | +6.35% | 365 | +28.330 | +7.76% | 7.220 |
| T6|side_price,prob_delta|side_price=0;prob_delta=1|away | +27.86% | +31.54% | +22.45% | +8.31% | +18.64% | 145 | +28.250 | +19.48% | 4.000 |
| T12|age,prob_delta|age=0;prob_delta=1|favorite | +1.76% | +1.49% | +1.15% | +7.74% | +0.54% | 1095 | +26.780 | +2.45% | 14.230 |
| T6|side_price,signed_line|side_price=0;signed_line=3|away | +17.69% | +47.18% | +4.51% | +0.43% | +6.66% | 250 | +25.140 | +10.06% | 9.690 |
| T6|side_price,signed_line|side_price=0;signed_line=3|underdog | +23.88% | +41.54% | +18.21% | +5.47% | +7.11% | 156 | +20.750 | +13.30% | 8.185 |
| T6|line,side_price,prob_delta|line=2;side_price=3;prob_delta=4|favorite | +9.00% | +26.26% | +5.12% | +30.36% | +29.49% | 88 | +20.140 | +22.89% | 4.000 |
| T6|line,side_price,prob_delta|line=3;side_price=3;prob_delta=2|underdog | +21.94% | +20.06% | +12.21% | +24.62% | +5.16% | 155 | +19.505 | +12.58% | 5.285 |
| T6|line,side_price,prob_delta|line=1;side_price=0;prob_delta=1|away | +19.33% | +34.75% | +39.71% | +23.06% | +18.18% | 74 | +18.865 | +25.49% | 4.465 |
| T6|side_price,prob_delta|side_price=0;prob_delta=1|underdog | +19.17% | +50.88% | +32.34% | +29.28% | +6.96% | 98 | +17.900 | +18.27% | 3.465 |
| T2|line,prob_delta|line=4;prob_delta=1|home | +62.50% | +70.00% | +9.94% | +11.80% | +12.90% | 78 | +17.350 | +22.24% | 4.000 |
| T6|side_price,momentum,prob_delta|side_price=0;momentum=2;prob_delta=1|away | +27.86% | +23.09% | +11.61% | +5.80% | +14.73% | 118 | +17.285 | +14.65% | 4.000 |
| T24|line,prob_delta|line=3;prob_delta=1|away | +5.85% | +10.54% | +3.29% | +8.23% | +9.92% | 223 | +16.395 | +7.35% | 7.345 |
| T24|signed_line,prob_delta|signed_line=1;prob_delta=1|away | +7.92% | +8.04% | +11.60% | +10.61% | +12.62% | 156 | +16.310 | +10.46% | 7.490 |
| T24|signed_line,prob_delta|signed_line=1;prob_delta=1|underdog | +7.92% | +8.04% | +11.60% | +10.61% | +12.62% | 156 | +16.310 | +10.46% | 7.490 |
| T6|line,side_price,prob_delta|line=1;side_price=0;prob_delta=1|underdog | +34.00% | +46.86% | +37.25% | +29.28% | +5.05% | 73 | +15.105 | +20.69% | 4.070 |
| T12|signed_line|signed_line=6|home | +36.00% | +4.46% | +16.38% | +1.78% | +12.50% | 94 | +14.120 | +15.02% | 3.280 |
| T12|signed_line|signed_line=6|underdog | +36.00% | +4.46% | +16.38% | +1.78% | +12.50% | 94 | +14.120 | +15.02% | 3.280 |
| T12|side_price,momentum,prob_delta|side_price=1;momentum=3;prob_delta=1|favorite | +40.81% | +5.95% | +3.71% | +7.24% | +8.78% | 142 | +13.650 | +9.61% | 7.875 |
| T2|signed_line|signed_line=6|home | +27.57% | +7.68% | +13.28% | +10.69% | +5.90% | 117 | +13.165 | +11.25% | 3.550 |
| T2|signed_line|signed_line=6|underdog | +27.57% | +7.68% | +13.28% | +10.69% | +5.90% | 117 | +13.165 | +11.25% | 3.550 |
| T6|side_price,momentum,prob_delta|side_price=3;momentum=3;prob_delta=3|favorite | +28.50% | +18.44% | +38.20% | +44.20% | +29.23% | 39 | +12.060 | +30.92% | 2.500 |
| T12|line,side_price,prob_delta|line=1;side_price=2;prob_delta=4|away | +40.83% | +31.10% | +3.38% | +7.92% | +4.90% | 109 | +11.660 | +10.70% | 6.170 |
| T2|line,side_price,prob_delta|line=4;side_price=2;prob_delta=1|home | +93.33% | +44.75% | +14.11% | +45.20% | +10.04% | 38 | +11.585 | +30.49% | 2.520 |
| T6|line,side_price,prob_delta|line=1;side_price=0;prob_delta=0|underdog | +19.00% | +59.25% | +36.00% | +61.70% | +9.04% | 44 | +10.070 | +22.89% | 3.000 |
| T2|line,prob_delta|line=4;prob_delta=4|favorite | +49.06% | +10.19% | +26.50% | +2.14% | +2.42% | 71 | +10.045 | +14.15% | 4.000 |
| T2|signed_line,prob_delta|signed_line=0;prob_delta=1|home | +48.75% | +63.33% | +12.71% | +7.58% | +5.38% | 63 | +10.045 | +15.94% | 4.000 |
| T2|signed_line,prob_delta|signed_line=0;prob_delta=1|favorite | +48.75% | +63.33% | +12.71% | +7.58% | +5.38% | 63 | +10.045 | +15.94% | 4.000 |
| T24|line,side_price,prob_delta|line=3;side_price=1;prob_delta=1|underdog | +32.27% | +10.41% | +2.04% | +25.62% | +3.11% | 83 | +9.845 | +11.86% | 3.860 |
| T12|line,prob_delta|line=4;prob_delta=0|underdog | +32.50% | +18.67% | +42.00% | +29.00% | +53.55% | 26 | +9.680 | +37.23% | 2.000 |
| T12|side_price,signed_line|side_price=3;signed_line=6|home | +26.00% | +31.00% | +33.67% | +100.00% | +32.30% | 28 | +9.460 | +33.79% | 3.000 |
| T12|side_price,signed_line|side_price=3;signed_line=6|underdog | +26.00% | +31.00% | +33.67% | +100.00% | +32.30% | 28 | +9.460 | +33.79% | 3.000 |
| T6|side_price,momentum|side_price=0;momentum=1|away | +14.25% | +41.50% | +7.55% | +1.58% | +16.46% | 69 | +9.395 | +13.62% | 5.085 |
| T24|line,side_price,prob_delta|line=2;side_price=1;prob_delta=3|away | +4.11% | +28.88% | +10.09% | +19.91% | +5.81% | 65 | +9.335 | +14.36% | 3.505 |
| T6|side_price,momentum,prob_delta|side_price=0;momentum=2;prob_delta=1|underdog | +19.17% | +41.83% | +25.95% | +21.57% | +2.70% | 76 | +9.265 | +12.19% | 3.605 |
| T6|signed_line,prob_delta|signed_line=0;prob_delta=2|away | +39.60% | +45.67% | +29.95% | +8.77% | +1.84% | 60 | +9.195 | +15.32% | 6.380 |
| T6|signed_line,prob_delta|signed_line=0;prob_delta=2|underdog | +39.60% | +45.67% | +29.95% | +8.77% | +1.84% | 60 | +9.195 | +15.32% | 6.380 |
| T24|signed_line,prob_delta|signed_line=3;prob_delta=4|away | +91.00% | +49.33% | +1.50% | +41.67% | +19.32% | 31 | +9.135 | +29.47% | 3.000 |
| T6|line,side_price,prob_delta|line=1;side_price=0;prob_delta=0|away | +19.00% | +59.25% | +36.00% | +61.70% | +3.34% | 56 | +8.990 | +16.05% | 6.000 |
| T12|momentum,prob_delta|momentum=1;prob_delta=4|away | +10.22% | +14.72% | +3.21% | +19.09% | +0.18% | 121 | +8.970 | +7.41% | 5.090 |
| T2|line,side_price,prob_delta|line=4;side_price=2;prob_delta=4|home | +15.33% | +12.78% | +50.67% | +21.00% | +17.00% | 32 | +8.200 | +25.62% | 2.100 |
| T2|line,side_price,prob_delta|line=0;side_price=1;prob_delta=3|home | +4.29% | +2.86% | +7.35% | +6.38% | +6.31% | 137 | +7.830 | +5.72% | 5.390 |
| T2|side_price,momentum,prob_delta|side_price=1;momentum=1;prob_delta=1|away | +1.23% | +9.14% | +2.68% | +6.10% | +2.94% | 173 | +7.045 | +4.07% | 6.930 |
| T24|line,prob_delta|line=0;prob_delta=4|away | +91.00% | +64.00% | +103.00% | +26.50% | +10.70% | 20 | +7.020 | +35.10% | 2.000 |
| T6|line,side_price,prob_delta|line=0;side_price=0;prob_delta=1|away | +79.00% | +13.25% | +5.00% | +7.50% | +22.79% | 39 | +6.550 | +16.79% | 2.240 |
| T6|side_price,momentum|side_price=2;momentum=4|home | +96.00% | +3.50% | +22.25% | +90.00% | +38.75% | 21 | +6.255 | +29.79% | 2.000 |
| T2|line,side_price,prob_delta|line=1;side_price=4;prob_delta=4|underdog | +55.50% | +112.00% | +112.00% | +55.50% | +17.30% | 14 | +5.080 | +36.29% | 2.000 |
| T2|signed_line,prob_delta|signed_line=6;prob_delta=1|home | +28.50% | +60.00% | +0.11% | +41.50% | +0.56% | 30 | +4.945 | +16.48% | 2.190 |
| T2|signed_line,prob_delta|signed_line=6;prob_delta=1|underdog | +28.50% | +60.00% | +0.11% | +41.50% | +0.56% | 30 | +4.945 | +16.48% | 2.190 |
| T24|side_price,momentum,prob_delta|side_price=1;momentum=2;prob_delta=4|underdog | +40.00% | +84.00% | +0.17% | +65.00% | +11.00% | 17 | +4.780 | +28.12% | 2.000 |
| T2|line,side_price,prob_delta|line=1;side_price=0;prob_delta=3|underdog | +39.00% | +29.25% | +2.50% | +14.44% | +3.10% | 46 | +4.165 | +9.05% | 4.430 |
| T6|side_price,momentum,prob_delta|side_price=0;momentum=1;prob_delta=2|away | +5.83% | +23.75% | +22.58% | +5.50% | +8.15% | 32 | +3.870 | +12.09% | 2.460 |
| T2|line,side_price,prob_delta|line=4;side_price=1;prob_delta=3|away | +10.50% | +42.50% | +11.00% | +19.00% | +15.67% | 21 | +3.665 | +17.45% | 1.500 |
| T2|line,side_price,prob_delta|line=1;side_price=0;prob_delta=3|home | +59.00% | +19.30% | +4.96% | +1.72% | +3.34% | 45 | +3.480 | +7.73% | 5.815 |
| T6|line,side_price,prob_delta|line=1;side_price=4;prob_delta=3|underdog | +5.50% | +22.17% | +5.50% | +5.50% | +46.60% | 14 | +3.325 | +23.75% | 2.000 |
| T2|side_price,momentum,prob_delta|side_price=1;momentum=3;prob_delta=1|away | +44.00% | +17.75% | +18.50% | +89.00% | +5.93% | 17 | +3.180 | +18.71% | 2.000 |

## Monthly performance and drawdowns

All 60 months for all 61 candidates (including zero-activity months): expanded_five_year_r9_monthly.csv. Full year/month and drawdown peak/trough data: expanded_five_year_r9_results.json.

| Candidate ID | Active months | Profitable months | Losing months | Worst month | DD peak | DD trough |
|---|---:|---:|---:|---|---|---|
| T2|side_price,prob_delta|side_price=1;prob_delta=3|underdog | 56 | 30 | 25 | 2021-04 (-6.865U) | 2022-09-10T14:30:00+00:00 | 2023-08-12T14:00:00+00:00 |
| T2|side_price,momentum,prob_delta|side_price=2;momentum=2;prob_delta=1|favorite | 57 | 32 | 25 | 2020-12 (-5.970U) | 2022-05-14T10:00:00+00:00 | 2023-07-15T10:00:00+00:00 |
| T2|side_price,momentum,prob_delta|side_price=1;momentum=2;prob_delta=3|underdog | 55 | 34 | 21 | 2021-04 (-6.285U) | 2021-01-10T13:30:00+00:00 | 2021-05-08T11:00:00+00:00 |
| T2|side_price,prob_delta|side_price=2;prob_delta=1|favorite | 57 | 31 | 26 | 2020-12 (-8.010U) | 2020-11-29T14:00:00+00:00 | 2021-03-06T05:00:00+00:00 |
| T12|age,prob_delta|age=2;prob_delta=3|home | 57 | 34 | 22 | 2023-08 (-13.440U) | 2021-09-18T05:20:00+00:00 | 2023-09-02T10:00:00+00:00 |
| T2|line,side_price,prob_delta|line=0;side_price=2;prob_delta=1|favorite | 50 | 29 | 15 | 2023-12 (-1.100U) | 2023-11-04T17:00:00+00:00 | 2023-12-30T15:00:00+00:00 |
| T6|side_price|side_price=0|underdog | 51 | 33 | 18 | 2022-08 (-3.210U) | 2023-04-16T13:00:00+00:00 | 2023-05-20T12:00:00+00:00 |
| T6|side_price,prob_delta|side_price=0;prob_delta=1|away | 45 | 29 | 14 | 2021-03 (-2.460U) | 2021-03-03T20:00:00+00:00 | 2021-03-20T16:00:00+00:00 |
| T12|age,prob_delta|age=0;prob_delta=1|favorite | 56 | 32 | 24 | 2020-11 (-10.180U) | 2019-12-21T19:45:00+00:00 | 2020-03-01T16:00:00+00:00 |
| T6|side_price,signed_line|side_price=0;signed_line=3|away | 50 | 32 | 17 | 2022-08 (-4.210U) | 2022-04-21T17:00:00+00:00 | 2023-06-11T09:00:00+00:00 |
| T6|side_price,signed_line|side_price=0;signed_line=3|underdog | 43 | 30 | 13 | 2022-08 (-3.210U) | 2022-04-21T17:00:00+00:00 | 2023-09-01T15:00:00+00:00 |
| T6|line,side_price,prob_delta|line=2;side_price=3;prob_delta=4|favorite | 34 | 23 | 10 | 2023-04 (-2.000U) | 2023-02-17T19:45:00+00:00 | 2023-04-22T13:30:00+00:00 |
| T6|line,side_price,prob_delta|line=3;side_price=3;prob_delta=2|underdog | 40 | 28 | 12 | 2023-11 (-3.425U) | 2023-09-09T13:30:00+00:00 | 2023-11-25T14:00:00+00:00 |
| T6|line,side_price,prob_delta|line=1;side_price=0;prob_delta=1|away | 35 | 23 | 12 | 2019-05 (-1.000U) | 2023-01-29T14:00:00+00:00 | 2023-09-01T15:00:00+00:00 |
| T6|side_price,prob_delta|side_price=0;prob_delta=1|underdog | 38 | 25 | 13 | 2023-10 (-1.665U) | 2023-10-06T14:30:00+00:00 | 2023-10-28T14:00:00+00:00 |
| T2|line,prob_delta|line=4;prob_delta=1|home | 35 | 24 | 11 | 2022-04 (-2.500U) | 2022-03-20T15:45:00+00:00 | 2022-05-06T16:45:00+00:00 |
| T6|side_price,momentum,prob_delta|side_price=0;momentum=2;prob_delta=1|away | 39 | 21 | 15 | 2021-03 (-2.460U) | 2021-03-03T20:00:00+00:00 | 2021-03-20T16:00:00+00:00 |
| T24|line,prob_delta|line=3;prob_delta=1|away | 46 | 26 | 20 | 2020-01 (-3.990U) | 2021-05-01T15:00:00+00:00 | 2022-08-15T19:30:00+00:00 |
| T24|signed_line,prob_delta|signed_line=1;prob_delta=1|away | 45 | 26 | 19 | 2020-01 (-3.990U) | 2019-12-07T17:30:00+00:00 | 2020-01-24T19:30:00+00:00 |
| T24|signed_line,prob_delta|signed_line=1;prob_delta=1|underdog | 45 | 26 | 19 | 2020-01 (-3.990U) | 2019-12-07T17:30:00+00:00 | 2020-01-24T19:30:00+00:00 |
| T6|line,side_price,prob_delta|line=1;side_price=0;prob_delta=1|underdog | 35 | 23 | 12 | 2023-12 (-1.690U) | 2023-01-29T14:00:00+00:00 | 2023-09-01T15:00:00+00:00 |
| T12|signed_line|signed_line=6|home | 37 | 20 | 14 | 2023-09 (-2.280U) | 2023-08-27T13:00:00+00:00 | 2023-10-07T15:00:00+00:00 |
| T12|signed_line|signed_line=6|underdog | 37 | 20 | 14 | 2023-09 (-2.280U) | 2023-08-27T13:00:00+00:00 | 2023-10-07T15:00:00+00:00 |
| T12|side_price,momentum,prob_delta|side_price=1;momentum=3;prob_delta=1|favorite | 47 | 24 | 22 | 2020-12 (-2.865U) | 2020-10-04T05:00:00+00:00 | 2021-04-18T05:00:00+00:00 |
| T2|signed_line|signed_line=6|home | 41 | 21 | 15 | 2021-12 (-2.180U) | 2021-11-19T19:30:00+00:00 | 2022-08-31T19:00:00+00:00 |
| T2|signed_line|signed_line=6|underdog | 41 | 21 | 15 | 2021-12 (-2.180U) | 2021-11-19T19:30:00+00:00 | 2022-08-31T19:00:00+00:00 |
| T6|side_price,momentum,prob_delta|side_price=3;momentum=3;prob_delta=3|favorite | 27 | 18 | 7 | 2020-06 (-1.000U) | 2020-09-05T09:00:00+00:00 | 2020-12-06T16:00:00+00:00 |
| T12|line,side_price,prob_delta|line=1;side_price=2;prob_delta=4|away | 41 | 23 | 18 | 2023-12 (-5.700U) | 2023-12-02T10:30:00+00:00 | 2023-12-31T17:45:00+00:00 |
| T2|line,side_price,prob_delta|line=4;side_price=2;prob_delta=1|home | 24 | 16 | 8 | 2022-04 (-1.500U) | 2020-05-30T16:30:00+00:00 | 2021-11-27T17:30:00+00:00 |
| T6|line,side_price,prob_delta|line=1;side_price=0;prob_delta=0|underdog | 23 | 19 | 4 | 2023-05 (-2.000U) | 2023-02-18T17:45:00+00:00 | 2023-05-06T13:30:00+00:00 |
| T2|line,prob_delta|line=4;prob_delta=4|favorite | 33 | 18 | 14 | 2020-02 (-2.060U) | 2020-02-01T16:30:00+00:00 | 2020-06-06T13:30:00+00:00 |
| T2|signed_line,prob_delta|signed_line=0;prob_delta=1|home | 32 | 20 | 12 | 2022-04 (-2.500U) | 2022-03-20T15:45:00+00:00 | 2022-05-06T16:45:00+00:00 |
| T2|signed_line,prob_delta|signed_line=0;prob_delta=1|favorite | 32 | 20 | 12 | 2022-04 (-2.500U) | 2022-03-20T15:45:00+00:00 | 2022-05-06T16:45:00+00:00 |
| T24|line,side_price,prob_delta|line=3;side_price=1;prob_delta=1|underdog | 37 | 21 | 15 | 2022-08 (-2.000U) | 2021-01-09T14:30:00+00:00 | 2021-03-17T18:00:00+00:00 |
| T12|line,prob_delta|line=4;prob_delta=0|underdog | 16 | 12 | 4 | 2019-08 (-1.000U) | 2020-02-21T19:30:00+00:00 | 2020-12-12T19:00:00+00:00 |
| T12|side_price,signed_line|side_price=3;signed_line=6|home | 19 | 12 | 3 | 2023-09 (-2.000U) | 2023-08-25T11:35:00+00:00 | 2023-10-07T15:00:00+00:00 |
| T12|side_price,signed_line|side_price=3;signed_line=6|underdog | 19 | 12 | 3 | 2023-09 (-2.000U) | 2023-08-25T11:35:00+00:00 | 2023-10-07T15:00:00+00:00 |
| T6|side_price,momentum|side_price=0;momentum=1|away | 31 | 19 | 10 | 2023-08 (-2.230U) | 2022-04-01T10:00:00+00:00 | 2023-08-14T16:00:00+00:00 |
| T24|line,side_price,prob_delta|line=2;side_price=1;prob_delta=3|away | 36 | 17 | 18 | 2019-10 (-1.180U) | 2022-05-21T18:45:00+00:00 | 2023-09-03T17:00:00+00:00 |
| T6|side_price,momentum,prob_delta|side_price=0;momentum=2;prob_delta=1|underdog | 32 | 19 | 13 | 2023-10 (-2.235U) | 2023-02-04T17:30:00+00:00 | 2023-05-13T15:00:00+00:00 |
| T6|signed_line,prob_delta|signed_line=0;prob_delta=2|away | 27 | 17 | 9 | 2023-10 (-2.910U) | 2023-09-02T18:00:00+00:00 | 2023-10-28T14:00:00+00:00 |
| T6|signed_line,prob_delta|signed_line=0;prob_delta=2|underdog | 27 | 17 | 9 | 2023-10 (-2.910U) | 2023-09-02T18:00:00+00:00 | 2023-10-28T14:00:00+00:00 |
| T24|signed_line,prob_delta|signed_line=3;prob_delta=4|away | 19 | 12 | 7 | 2020-09 (-1.000U) | 2022-10-29T16:30:00+00:00 | 2023-09-03T15:30:00+00:00 |
| T6|line,side_price,prob_delta|line=1;side_price=0;prob_delta=0|away | 23 | 19 | 4 | 2023-11 (-2.900U) | 2023-11-04T16:00:00+00:00 | 2023-12-08T16:30:00+00:00 |
| T12|momentum,prob_delta|momentum=1;prob_delta=4|away | 42 | 22 | 19 | 2023-11 (-3.090U) | 2023-10-31T19:45:00+00:00 | 2023-12-06T20:15:00+00:00 |
| T2|line,side_price,prob_delta|line=4;side_price=2;prob_delta=4|home | 22 | 14 | 6 | 2020-02 (-1.060U) | 2022-02-19T17:45:00+00:00 | 2023-10-06T15:00:00+00:00 |
| T2|line,side_price,prob_delta|line=0;side_price=1;prob_delta=3|home | 45 | 22 | 17 | 2023-10 (-3.300U) | 2023-10-01T13:00:00+00:00 | 2023-11-12T15:30:00+00:00 |
| T2|side_price,momentum,prob_delta|side_price=1;momentum=1;prob_delta=1|away | 47 | 24 | 21 | 2022-05 (-2.000U) | 2023-06-04T19:00:00+00:00 | 2023-12-09T17:00:00+00:00 |
| T24|line,prob_delta|line=0;prob_delta=4|away | 14 | 9 | 3 | 2022-02 (-1.000U) | 2022-04-29T06:00:00+00:00 | 2023-08-05T11:35:00+00:00 |
| T6|line,side_price,prob_delta|line=0;side_price=0;prob_delta=1|away | 25 | 13 | 7 | 2021-03 (-2.000U) | 2020-03-01T14:00:00+00:00 | 2021-03-20T16:00:00+00:00 |
| T6|side_price,momentum|side_price=2;momentum=4|home | 14 | 8 | 5 | 2020-07 (-1.000U) | 2019-09-14T16:30:00+00:00 | 2020-09-13T13:00:00+00:00 |
| T2|line,side_price,prob_delta|line=1;side_price=4;prob_delta=4|underdog | 10 | 8 | 2 | 2023-02 (-1.000U) | 2023-01-23T17:30:00+00:00 | 2023-08-06T18:30:00+00:00 |
| T2|signed_line,prob_delta|signed_line=6;prob_delta=1|home | 22 | 12 | 6 | 2023-09 (-2.000U) | 2023-06-03T19:00:00+00:00 | 2023-12-17T13:30:00+00:00 |
| T2|signed_line,prob_delta|signed_line=6;prob_delta=1|underdog | 22 | 12 | 6 | 2023-09 (-2.000U) | 2023-06-03T19:00:00+00:00 | 2023-12-17T13:30:00+00:00 |
| T24|side_price,momentum,prob_delta|side_price=1;momentum=2;prob_delta=4|underdog | 12 | 9 | 3 | 2023-12 (-1.200U) | 2023-10-28T15:30:00+00:00 | 2023-12-03T11:00:00+00:00 |
| T2|line,side_price,prob_delta|line=1;side_price=0;prob_delta=3|underdog | 24 | 15 | 9 | 2021-10 (-2.615U) | 2021-08-24T10:00:00+00:00 | 2022-08-27T15:30:00+00:00 |
| T6|side_price,momentum,prob_delta|side_price=0;momentum=1;prob_delta=2|away | 21 | 13 | 6 | 2023-08 (-1.620U) | 2022-02-23T19:30:00+00:00 | 2023-08-11T16:00:00+00:00 |
| T2|line,side_price,prob_delta|line=4;side_price=1;prob_delta=3|away | 16 | 11 | 5 | 2019-10 (-1.000U) | 2023-05-14T18:45:00+00:00 | 2023-10-22T15:31:00+00:00 |
| T2|line,side_price,prob_delta|line=1;side_price=0;prob_delta=3|home | 25 | 16 | 9 | 2021-10 (-3.000U) | 2021-08-24T10:00:00+00:00 | 2022-08-27T15:30:00+00:00 |
| T6|line,side_price,prob_delta|line=1;side_price=4;prob_delta=3|underdog | 13 | 9 | 4 | 2020-09 (-1.000U) | 2020-07-11T10:00:00+00:00 | 2021-02-21T17:00:00+00:00 |
| T2|side_price,momentum,prob_delta|side_price=1;momentum=3;prob_delta=1|away | 12 | 9 | 3 | 2020-12 (-2.000U) | 2020-10-04T08:00:00+00:00 | 2020-12-12T20:00:00+00:00 |

## Audit boundaries

- All candidates were selected within the same 2019-2023 period: five profitable years are NOT independent forward validation; multiple testing and in-sample selection bias apply.
- Candidate overlap, opposite-direction conflicts and de-duplicated combination returns are NOT YET computed for these 61 new structures; do not sum profits.
- Drawdown uses equal 1U stakes ordered by kickoff, not bankroll percentage.
- Same-line no-vig probability change uses source-side1 convention; it must not be assumed to mean odds movement in the selected bet direction.
- Crown event timestamps were retrieved retrospectively in 2026, not proof of actual historical executable prices.
- 2024-2026 excluded. All 61 are pending user review. Frozen M8 and production unchanged.
