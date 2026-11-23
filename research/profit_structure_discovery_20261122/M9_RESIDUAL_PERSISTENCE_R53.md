# R53 | Do true model forecast errors persist across seasons?

## Source and method

Independent M3 penaltyblog bivariate season-forward out-of-sample 1X2 predictions. Per-team residual = actual match points (win=1, draw=.5, loss=0) minus expected points (Pwin+.5Pdraw), averaged over team fixtures. For each next season, compare earlier one-season or pooled two-season residual to the held-out season observed residual for teams appearing in both. No later season outcomes enter the prior estimate.

## English Premier League E0

| Test season | Prior window | Teams | Pearson r | Same-sign proportion |
|---|---|---:|---:|---:|
| 2324 | prior1 | 16 | +0.3720 | 56.2% |
| 2324 | prior2 | 17 | +0.3468 | 76.5% |
| 2425 | prior1 | 17 | +0.4655 | 76.5% |
| 2425 | prior2 | 19 | +0.6461 | 78.9% |
| 2526 | prior1 | 17 | +0.4712 | 76.5% |
| 2526 | prior2 | 18 | +0.5828 | 72.2% |
| 2627 | prior1 | 16 | +0.5027 | 75.0% |
| 2627 | prior2 | 16 | +0.5925 | 68.8% |

## Other leagues, two-season residual

| League | 2023/24 r | 2024/25 r | 2025/26 r | 2026/27 partial r |
|---|---:|---:|---:|---:|
| B1 | +0.621 | -0.144 | +0.180 | -0.097 |
| D1 | -0.173 | +0.545 | +0.346 | +0.466 |
| E0 | +0.347 | +0.646 | +0.583 | +0.593 |
| F1 | +0.040 | +0.253 | -0.070 | +0.256 |
| I1 | -0.174 | +0.419 | +0.111 | +0.278 |
| SP1 | +0.430 | +0.191 | +0.135 | +0.055 |
- prior1: 16/24 league-season groups with positive cross-team correlation.
- prior2: 19/24 league-season groups with positive cross-team correlation.

## Interpretation

E0 shows positive residual correlation across all four test periods. This supports studying persistent model misspecification, but correlation and same-sign proportions across small team samples are not a trading edge. The same E0 seasons were used in R50-R52, so this is a deeper diagnostic, not independent replication.

## Limitations
- Previous/current season model predictions are OOS per source, but league-season OOS archive may use date-only timestamps.
- Per-team Pearson correlation is across teams, not independent match evidence; sample sizes limited.
- Current-season residual is evaluated retrospectively, never used to generate the earlier forecast.
- A stable correction to 1X2 can arise from shrinkage or calibration even without persistent team residual sign.
- No M9 score-grid, Crown price or formal trading ROI.

## Next research (optional)

- Estimate residual correction on full M9 bivariate score grids using only previous information.
- Quantify whether actual Asian handicap probabilities and Crown price matched results improve, avoiding post-match odds snapshots as if executable.
- Do not change M9 formal model or league rules without user authorization.
