# R24 | 2024 first forward-year evaluation (2019-2023 candidate and method freeze)

**Important: 2024 is a first held-out calendar year for the 494 frozen R7-R15 candidates. No 2024-informed reselection.**

Pre-2024 freeze: PRE2024_METHOD_FREEZE_R24.json with source/result SHA256. Historical odds are retrospectively obtained, not proven executable. No production changes.

## 2024 fixture-level, 1U stake, equal votes

| Timing | Conflict handling | Orders | Net U | ROI | MDD U | Profitable months | Losing months |
|---|---|---:|---:|---:|---:|---:|---:|
| earliest | skip | 7982 | -217.73 | -2.7278% | 232.35 | 2 | 10 |
| earliest | net | 9225 | -306.735 | -3.325% | 322.51 | 3 | 9 |
| earliest | margin2 | 3800 | -87.375 | -2.2993% | 100.16 | 4 | 8 |
| earliest | margin3 | 1793 | -54.015 | -3.0125% | 63.305 | 5 | 7 |
| latest | skip | 8015 | -161.565 | -2.0158% | 244.82 | 4 | 8 |
| latest | net | 9421 | -181.1 | -1.9223% | 267.78 | 5 | 7 |
| latest | margin2 | 4884 | -163.155 | -3.3406% | 187.79 | 2 | 10 |
| latest | margin3 | 2611 | -82.92 | -3.1758% | 107.635 | 4 | 8 |
| T24 | skip | 2180 | -88.82 | -4.0743% | 100.195 | 2 | 10 |
| T24 | net | 2392 | -94.405 | -3.9467% | 107.455 | 2 | 10 |
| T24 | margin2 | 950 | -2.18 | -0.2295% | 22.76 | 5 | 7 |
| T24 | margin3 | 476 | -7.565 | -1.5893% | 29.82 | 6 | 6 |
| T12 | skip | 4940 | -75.475 | -1.5278% | 130.22 | 6 | 6 |
| T12 | net | 5786 | -98.37 | -1.7001% | 147.875 | 6 | 6 |
| T12 | margin2 | 2182 | -42.635 | -1.9539% | 72.26 | 4 | 8 |
| T12 | margin3 | 878 | -37.98 | -4.3257% | 54.02 | 6 | 6 |
| T6 | skip | 4904 | -135.905 | -2.7713% | 164.46 | 3 | 9 |
| T6 | net | 6241 | -172.555 | -2.7649% | 206.775 | 5 | 7 |
| T6 | margin2 | 2967 | -103.065 | -3.4737% | 117.72 | 3 | 9 |
| T6 | margin3 | 1432 | -62.665 | -4.376% | 75.345 | 2 | 10 |
| T2 | skip | 5846 | -141.82 | -2.4259% | 209.73 | 4 | 8 |
| T2 | net | 6815 | -159.98 | -2.3475% | 225.605 | 4 | 8 |
| T2 | margin2 | 3794 | -132.975 | -3.5049% | 154.385 | 4 | 8 |
| T2 | margin3 | 2122 | -68.325 | -3.2198% | 90.7 | 4 | 8 |

## 2024 alternative weights on earliest signal-bearing horizon, net votes

| Vote weighting | Stake approach | Orders | Net U | ROI |
|---|---|---:|---:|---:|
| equal | flat | 9225 | -306.735 | -3.325% |
| equal | vote_margin | 9225 | -270.565 | -2.9329% |
| batch | flat | 8960 | -288.63 | -3.2213% |
| batch | vote_margin | 8960 | -258.826 | -2.8887% |
| sqrt_n | flat | 10141 | -367.7 | -3.6259% |
| sqrt_n | vote_margin | 10141 | -317.187 | -3.1278% |
| train_roi | flat | 10157 | -253.765 | -2.4984% |
| train_roi | vote_margin | 10157 | -236.325 | -2.3267% |

## Interpretation and caveats

- The historical 494 R7-R15 candidates were selected using 2019-2023 only, so 2024 is a new-year evaluation of those fixed definitions.
- The 2024 performance is negative for all listed equal-vote timing and conflict alternatives. Do not choose the least-negative 2024 variant as if it were pre-registered.
- All tested 2024 alternatives (including experimental vote-margin stake sizes) are in FORWARD_2024_R24_RESULTS.json. The variable-size approach is not a user-approved bankroll rule.
- R17/R18 candidate additions were not part of the 494 frozen candidates; their evaluation remains separate.
- Crown event-time historical quotes were retrieved retrospectively in 2026; ability to execute at those prices in 2024 is unverified.
- The 2024 dataset has a different match mix and coverage from 2019-2023; do not attribute the return change to a single cause without further investigation.
- No 2025-2026 results used. No M8, Telegram, settlement or production modifications.
