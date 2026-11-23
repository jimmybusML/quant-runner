# R46 | Independent season-forward bivariate forecast enhancement research

## Method

Read-only independent M3 penaltyblog bivariate predictions; compare original 1X2 probabilities with two explicitly exploratory transformations trained on prior season only, per league. Team residual is previous-season actual minus predicted match points per team divided by matches, applied as opposing home/away probability exponential offsets. Draw calibration is previous-season actual/predicted draw count ratio. These are NOT the production M9 scorer and NOT a refitted dynamic bivariate Poisson or full Dixon-Coles low-score adjustment.

## Result

| Season | N | Original bivariate LL | Draw adjustment LL | Team residual LL | Combined LL |
|---|---:|---:|---:|---:|---:|
| 2425 | 1882 | 1.00716041 | 1.0068108 | 1.0040103 | 1.00354717 |
| 2526 | 1880 | 1.00140026 | 1.00207716 | 1.00008937 | 1.0007101 |
| 2627 | 528 | 0.95616231 | 0.95675126 | 0.95369787 | 0.95434213 |

Lower LL is better. Team residual transformation improves LL in all three evaluated seasons. The standalone draw adjustment worsens 2025/26 and 2026/27; combined adjustment does not consistently beat team-only. The differences are small and have not been established as statistically significant.

## Independent reference models

| Season | Poisson base LL | Dixon-Coles base LL | Bivariate base LL |
|---|---:|---:|---:|
| 2425 | 1.00785346 | 1.00684369 | 1.00716041 |
| 2526 | 1.00150739 | 1.00106395 | 1.00140026 |
| 2627 | 0.95620202 | 0.95790459 | 0.95616231 |

## Limitations

- The source uses six Football-Data leagues and date-only records. Production M9 uses different M3-history fixture scope and actual Crown AH line; this is a mechanism test, not direct M9 backtest.
- A prior-season OOS forecast is used to fit corrections; no current test-season results are used for correction fitting.
- Team residual transformation is a simple exploratory post-processing of 1X2 probability, not actual dynamic team-strength bivariate parameter refitting.
- Draw calibration is not a full low-score correction, because this prediction artifact has no exact-score matrix.
- Crown line, market-price errors, full five-state AH settlement and Telegram ROI are not available from this source; no claim of market edge.
- No rules, thresholds, gates, M9 production logic, or formal Telegram orders were changed.

## Next empirical step

Reproduce the same challengers on the actual M9 training and fixture universe with full bivariate score matrices, then evaluate exact-score NLL, five-state AH settlement probabilities and same-timestamp Crown market prices. This is a research proposal, not an automatic production change.
