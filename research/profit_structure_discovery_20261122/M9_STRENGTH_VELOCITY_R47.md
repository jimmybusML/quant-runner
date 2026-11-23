# R47 | M9 research: does team-strength change speed improve forecasts?

## Experiment

All variants are exploratory probability post-processing, not M9 parameter refitting. Each test season uses the two strictly prior seasons, per-league previous-season team point residuals (actual minus model expected). Velocity = most-recent prior-season residual minus earlier prior-season residual. No current-season results are used.

Data source: research/m3/results/predictions/a382ebde7d0a89d8574ee3168c1923529084296de890a8abf5a18ff64d83c977.csv (generated 2026-11-22T21:29:25.966007+00:00). Independent M3 penaltyblog bivariate season-forward model, not production M9.

## Same-fixture out-of-sample 1X2 log loss (lower is better)

| Season | Matches | Original | Prior season residual | Residual change speed only | Recent + speed | Two-season residual mean |
|---|---:|---:|---:|---:|---:|---:|
| 2324 | 1890 | 1.00002126 | 1.00340327 | 1.0112968 | 1.0226633 | 0.99900223 |
| 2425 | 1882 | 1.00716041 | 1.0040103 | 1.02016869 | 1.02715335 | 1.00006359 |
| 2526 | 1880 | 1.00140026 | 1.00008937 | 1.01078759 | 1.01547888 | 0.99855781 |
| 2627 | 528 | 0.95616231 | 0.95369787 | 0.96837229 | 0.97106329 | 0.95002128 |

## Interpretation

- Raw change-speed extrapolation worsened log loss in each listed season, as did recent-plus-speed.
- The simple two-season residual mean improved log loss versus original bivariate in each listed season, including the season where recent-only residual worsened.
- The test is exploratory, not a fitted parameter search; no statistical uncertainty estimate, AH price pairing or tradable edge proof.
- Two-season smoothing could be capturing persistent team-strength mismatch rather than actual velocity.
- Do not treat this as evidence that dynamic bivariate Poisson parameters have been optimized.

## Caveats
- Source is independent M3 penaltyblog season-forward model, not production M9 training and fixture universe.
- Season-aggregated residual change is a proxy for speed, not rolling-match temporal update or dynamic goal-intensity fitting.
- No Asian handicap quote pairing or ROI; not evidence of betting edge.
- No model gates, quantity restrictions, production or Telegram changes.

## Next proposed research

Refit true bivariate score-grid parameters with prior-match temporal weights on the same M9 fixture universe and evaluate full Asian settlement versus original M9. Preserve baseline and official production.
