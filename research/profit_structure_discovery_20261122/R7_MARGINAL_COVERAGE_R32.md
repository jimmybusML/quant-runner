# R32 | R7 original 27 candidate marginal coverage and historical-only ordering

Original candidate definitions unchanged. The greedy order is a **research descriptive ranking** based solely on 2019-2023 incremental fixture order count (tie-break training net U); it is not an approved filter, quantity gate or production logic. All 2024 results are already-inspected retrospective Crown data.

## 2019-2023-only coverage ordering

| Step | Original candidate added | Historical orders | Historical net U | Historical ROI | 2024 orders | 2024 net U | 2024 ROI |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | T12|line,age|line=0;age=0|favorite | 476 | 23.49 | 4.9349% | 236 | 0.19 | 0.0805% |
| 2 | T6|price|price=4|underdog | 869 | 52.15 | 6.0012% | 555 | 3.705 | 0.6676% |
| 3 | T24|line,price|line=3;price=1|underdog | 1232 | 85.585 | 6.9468% | 742 | 11.21 | 1.5108% |
| 4 | T2|momentum,age|momentum=1;age=1|underdog | 1536 | 100.415 | 6.5374% | 1152 | 27.565 | 2.3928% |
| 5 | T12|line,momentum|line=2;momentum=3|favorite | 1786 | 126.055 | 7.058% | 1260 | 25.53 | 2.0262% |
| 6 | T12|momentum,age|momentum=3;age=2|underdog | 1929 | 159.175 | 8.2517% | 1320 | 20.235 | 1.533% |
| 7 | T2|line,price,momentum|line=2;price=2;momentum=1|favorite | 2051 | 183.35 | 8.9395% | 1401 | 23.36 | 1.6674% |
| 8 | T12|price,momentum|price=2;momentum=3|away | 2145 | 205.45 | 9.5781% | 1462 | 37.93 | 2.5944% |
| 9 | T2|line,price|line=4;price=3|underdog | 2228 | 217.4 | 9.7576% | 1523 | 42.98 | 2.8221% |
| 10 | T12|line,age|line=2;age=4|underdog | 2285 | 219.42 | 9.6026% | 1581 | 33.785 | 2.1369% |
| 11 | T24|line,momentum|line=0;momentum=1|away | 2321 | 223.11 | 9.6127% | 1593 | 32.145 | 2.0179% |
| 12 | T12|line,price,momentum|line=2;price=1;momentum=3|favorite | 2357 | 217.85 | 9.2427% | 1618 | 33.095 | 2.0454% |
| 13 | T2|line,price,momentum|line=3;price=3;momentum=3|away | 2385 | 220.53 | 9.2465% | 1645 | 25.65 | 1.5593% |
| 14 | T6|momentum,age|momentum=4;age=0|home | 2410 | 230.42 | 9.561% | 1665 | 23.9 | 1.4354% |
| 15 | T2|line,price,momentum|line=2;price=4;momentum=2|favorite | 2435 | 238.205 | 9.7825% | 1686 | 21.63 | 1.2829% |
| 16 | T12|momentum|momentum=4|favorite | 2446 | 239.53 | 9.7927% | 1688 | 21.47 | 1.2719% |
| 17 | T6|price,momentum|price=1;momentum=4|favorite | 2450 | 242.16 | 9.8841% | 1691 | 18.74 | 1.1082% |
| 18 | T12|line,price,momentum|line=0;price=0;momentum=3|underdog | 2451 | 243.51 | 9.9351% | 1691 | 20.465 | 1.2102% |
| 19 | T12|line,price,momentum|line=0;price=0;momentum=3|away | 2459 | 244.98 | 9.9626% | 1698 | 22.835 | 1.3448% |
| 20 | T6|price,momentum|price=4;momentum=2|underdog | 2459 | 244.98 | 9.9626% | 1698 | 22.835 | 1.3448% |
| 21 | T6|price,momentum|price=2;momentum=4|home | 2459 | 244.98 | 9.9626% | 1698 | 22.835 | 1.3448% |
| 22 | T6|line,price|line=1;price=4|underdog | 2459 | 244.98 | 9.9626% | 1698 | 22.835 | 1.3448% |
| 23 | T6|line,price|line=1;price=4|away | 2459 | 244.98 | 9.9626% | 1698 | 22.835 | 1.3448% |
| 24 | T24|line,price,momentum|line=3;price=1;momentum=2|underdog | 2459 | 244.98 | 9.9626% | 1698 | 22.835 | 1.3448% |
| 25 | T12|price,momentum|price=1;momentum=4|favorite | 2459 | 244.98 | 9.9626% | 1698 | 22.835 | 1.3448% |
| 26 | T24|line,momentum|line=0;momentum=1|favorite | 2451 | 244.89 | 9.9914% | 1696 | 21.885 | 1.2904% |
| 27 | T6|price,momentum|price=4;momentum=1|away | 2425 | 248.44 | 10.2449% | 1680 | 20.975 | 1.2485% |

## Leave-one-out from complete original R7 portfolio

Positive delta means keeping candidate yields more 2024 net U than removing it; this is not isolated causal PnL.

| Removed candidate | 2019-23 net U delta | 2019-23 order delta | 2024 net U delta | 2024 order delta |
|---|---:|---:|---:|---:|
| T2|momentum,age|momentum=1;age=1|underdog | 10.275 | 255 | 18.875 | 333 |
| T12|price,momentum|price=2;momentum=3|away | 25.79 | 78 | 12.62 | 55 |
| T12|line,age|line=0;age=0|favorite | 18.685 | 403 | 4.28 | 205 |
| T2|line,price|line=4;price=3|underdog | 11.92 | 81 | 4.19 | 60 |
| T2|line,price,momentum|line=2;price=2;momentum=1|favorite | 25.175 | 121 | 4.005 | 82 |
| T12|line,price,momentum|line=0;price=0;momentum=3|away | 1.47 | 8 | 2.37 | 7 |
| T12|line,price,momentum|line=0;price=0;momentum=3|underdog | 1.47 | 8 | 2.37 | 7 |
| T24|line,momentum|line=0;momentum=1|away | 0.2 | -8 | 1.0 | -2 |
| T12|line,price,momentum|line=2;price=1;momentum=3|favorite | -5.26 | 36 | 0.95 | 25 |
| T12|line,momentum|line=2;momentum=3|favorite | -6.865 | 24 | 0.735 | 21 |
| T6|price|price=4|underdog | -2.92 | -25 | 0.585 | -8 |
| T12|momentum|momentum=4|favorite | -1.395 | 5 | 0.0 | 0 |
| T12|price,momentum|price=1;momentum=4|favorite | 0.0 | 0 | 0.0 | 0 |
| T24|line,price,momentum|line=3;price=1;momentum=2|underdog | 0.0 | 0 | 0.0 | 0 |
| T6|line,price|line=1;price=4|away | 3.0 | -3 | 0.0 | 0 |
| T6|line,price|line=1;price=4|underdog | -2.4 | -3 | 0.0 | 0 |
| T6|price,momentum|price=2;momentum=4|home | 0.0 | 0 | 0.0 | 0 |
| T6|price,momentum|price=4;momentum=2|underdog | 0.0 | 0 | 0.0 | 0 |
| T6|momentum,age|momentum=4;age=0|home | -1.27 | 1 | -0.02 | -1 |
| T6|price,momentum|price=4;momentum=1|away | 3.55 | -26 | -0.91 | -16 |
| T24|line,momentum|line=0;momentum=1|favorite | -0.09 | -8 | -0.95 | -2 |
| T2|line,price,momentum|line=2;price=4;momentum=2|favorite | 7.785 | 25 | -2.27 | 21 |
| T6|price,momentum|price=1;momentum=4|favorite | 2.63 | 4 | -2.73 | 3 |
| T12|momentum,age|momentum=3;age=2|underdog | 22.545 | 131 | -6.05 | 65 |
| T24|line,price|line=3;price=1|underdog | 2.45 | 34 | -6.77 | 18 |
| T2|line,price,momentum|line=3;price=3;momentum=3|away | 4.68 | 26 | -7.445 | 27 |
| T12|line,age|line=2;age=4|underdog | 2.02 | 57 | -10.305 | 57 |

## Interpretation and cautions

- The historical-coverage-ranked 9 candidate research prefix has 2024 n1523 +42.980U ROI+2.8221%, while all original R7 has n1680 +20.975U ROI+1.2485%. **The 9-step point was identified after looking at 2024 outcomes, not an independently selected strategy.**
- Order counts can decrease as candidates are added because equal-net vote ties or changes in chosen earliest eligible horizon can suppress or replace orders. Indeed the full 27 has fewer orders than the 19-step prefix.
- Leave-one-out differences reflect changes in side, horizon and coverage; do not interpret as candidate-specific standalone PnL.
- R7 candidate selection used 2019-2023 in-sample and 2024 is already repeatedly inspected.
- 2025-2026 untouched; no changes to Telegram, M8, original candidate definitions, or production rules.

- Greedy ordering is a research diagnostic of historical incremental fixture coverage, not a new strategy rule or selection gate.
- Training ranking uses only 2019-2023, but the original R7 candidates were selected on those years and 2024 has been repeatedly inspected.
- Removing or adding a candidate can change earliest eligible horizon and majority direction; net-U differences are portfolio-level and not causal contribution.
- The 27 step counts are descriptive; do not interpret any step as an approved portfolio size.
- 2025-2026 not used; no production or Telegram changes; retrospective Crown prices are not proven executable.
