# R55 | M9 actual Crown AH receipt and settlement audit

## Verified current production evidence

Source: local M9 formal Telegram event ledger, Crown raw quote evidence, historical M1 fixture ID cache. Audit time UTC: 2026-11-23T01:59:19.125042+00:00.

| Metric | Verified count |
|---|---:|
| telegram_sent | 272 |
| crown_hash_verified | 272 |
| crown_time_verified | 272 |
| historical_fixture_matched | 272 |
| settled | 247 |
| settlement_pnl_verified | 247 |

Unsettled: **25**.

## Official M9 AH settled performance (not R54 challenger)

| Outcome | Orders |
|---|---:|
| FULL_WIN | 95 |
| HALF_WIN | 19 |
| PUSH | 15 |
| HALF_LOSS | 15 |
| FULL_LOSS | 103 |

Net: **-15.365U**. Settled ROI (1U per settled order): **-6.221%**.

Ledger/evidence validation failures: **0**.

## Research relevance

The local recent production sample has verifiable actual pre-kickoff Crown quote receipt and Telegram send timestamps, and all 247 settled PnL values independently match AH settlement recalculation. However, it does NOT provide historically saved enhanced full-score-grid predictions for the same matches; R54 old historical fixtures have not been paired to Crown quotes. A production-vs-challenger ROI claim is not yet valid.

## Limitations
- Formal recent M9 Telegram sample, not same as R54 historical 3386 fixtures.
- Verified quote receipt timestamps support production orders, not historical replay prices for unrelated matches.
- No original-versus-residual-enhanced M9 score-grid forecasts saved at the actual historical send time; no valid challenger ROI comparison yet.
- Historical cache is a latest snapshot; fixture ID match does not prove past as-of model input availability.
- Read-only: no formal Telegram, production code or ledger modification.

## Suggested next research (not production rules)

Create a read-only challenger shadow calculation at future actual quote receipt times, retain original and corrected score matrices with input provenance, and compare same-fixture Crown AH five-state settlement. Do not send challenger Telegram orders or change M9 production.
