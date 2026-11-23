# R56 | Retrospective M9 original vs true residual score-grid on actual Crown quotes

## Results

Read-only same-fixture comparison using real M9 Crown quote receipt and formal settlement records (verified in R55). Original and corrected model-class score grids were reconstructed from latest historical cache with pre-quote kickoff filtering. These are NOT archived production score grids, and input availability as of the historical quote receipt is not proven.

| Metric | Result |
|---|---:|
| Settled Crown fixtures compared | 14 |
| Reconstructed original agrees with production side | 14 |
| Original vs enhanced same direction | 14 |
| Excluded due to missing fixture/team in reconstructed training | 10 |
| original_rebuilt_pnl | -3.100U |
| corrected_pnl | -3.100U |
| actual_production_pnl | -3.100U |

League sample counts: 1: 7, 12: 4, 61: 3.

## Interpretation

On this small retrospective matched-Crown sample, prior forecast-residual correction did not flip any AH selection. Both reconstructed versions therefore have identical settled PnL. This does not establish improvement or deterioration in real tradable ROI. The original reconstructed side matches formal production for all included fixtures, but does not prove its entire grid matches the historical production model.

## Exclusions

Ten additional settled orders in the three pilot leagues were excluded because their fixture or team was absent from the reconstructed training universe. They were not silently counted as losses or wins.

## Limitations
- Historical training cache is latest snapshot, filtered by kickoff only; NOT a point-in-time as-of model input archive.
- Original baseline refit once per league at earliest quote receipt; not exact production per-run M9 grid, so baseline side may differ from actual production.
- Actual Crown quote and settlement are verified by R55; challenger decision is retrospective, not a live pre-registered shadow.
- Small sample from three leagues; no inference of long-term ROI.
- No Telegram send or formal ledger change.

## Research continuation (not a production rule)

For stronger evidence, calculate both versions at future actual Crown receipt times, preserve exact pre-match training snapshots and full score grids, and compare same-fixture outcomes without changing official orders. Broader league coverage is also needed.
