# M5 Crown Archive Coverage Audit — 2026-11-05

This is an aggregate-only audit of an additional local MR1 research archive discovered during M5 coverage review. The source checkout remains read-only. No raw quote, fixture ID, team, token, or private ledger row is copied into the public repository.

## Findings

The archive `mr1-ai-browser-forward/crown-market-benchmark-v26/forward/observations.jsonl` contains 382 browser research records. Only 47 records have the explicit `source_bookmaker=crown` label and both a source quote event timestamp and a local receipt timestamp. All 47 have an AH line and both AH prices, with event time <= receipt time < kickoff. They span four UTC kickoff dates from 2026-10-09 through 2026-10-13. The remaining 335 records have no verified Crown bookmaker label and are excluded.

The schema is AH-only: none of the verified Crown records contains an OU line or paired over/under prices. The archive has 47 unique match IDs. Its saved scope is a browser-capture benchmark and is not a complete historical Crown market archive.

An exact M3 strict-OOS join was attempted using the registered UTC kickoff day and normalized exact home/away names, requiring all three M3 penaltyblog model rows and quote-event <= received < kickoff. It produced zero pairs. The M3 OOS prediction artifact has no matching supported-league predictions on those four dates. This archive therefore adds no valid M3 Crown ROI observations and no OU coverage.

## Existing M5 evidence remains unchanged

The largest usable local Crown historical source remains the verified MR1 V23 snapshot archive. Re-running `m3_crown_exact_line_replay.py` at 2026-11-04T16:36:31Z yielded 121 exact M3 OOS fixtures, Crown AH0 coverage n=24 and OU2.5 coverage n=36. The unchanged small-sample outcomes are AH +5.910U / +24.625% (95% descriptive fixture-bootstrap interval -6.46% to +54.46% in this rerun) and OU -1.660U / -4.611% (-36.06% to +26.83%). These are not evidence for the 10,000-fixture goal or stable positive ROI.

The latest M3 input report describes 13,234 unique season-forward test fixtures across historical periods, but its archived prediction outputs have no Crown price mapping except the small 2026/27 archive overlap above. The 24,347 historical TotalCorner schedule/result IDs previously found in local MR1 batches contain no verified Crown bookmaker identity or timestamped quote snapshots. Ambiguous schedule fields such as `p_asian` and `p_goal` are not treated as Crown prices.

## Collection and authorization boundary

The user confirmed that existing Crown authorization should be reused and instructed us not to seek new authorization. Existing public Actions configuration shows a TotalCorner credential name, but its value was not read. No API request was made in this audit. We also found no public authorization-scope record that independently documents bulk historical extraction permissions. This audit therefore does not establish permission for high-volume historical backfill. Existing saved data has been exhausted for the M3 OOS join attempted here.

For ongoing M3 pairing, the current research capture archive should be treated as a limited prospective AH browser-capture study. To produce independent M3 prospective evidence, a future collector must capture both Crown AH and OU quotes with quote event time, received time, UTC kickoff, exact fixture identity, and an M3 forecast timestamp, and preserve append-only sanitized receipts. No collector is enabled by this report; M1/M2/MR1 production, Telegram, credentials, and trading rules are untouched.

## Status

- Additional verified Crown archive audited: 47 AH fixtures; zero exact M3 strict-OOS joins; zero OU quotes.
- Largest usable existing M3/Crown replay remains AH0 n=24 and OU2.5 n=36.
- Crown historical coverage target of 10,000 fixtures: not met.
- M5 independent AH and OU ROI target: not met.
- API requests, production writes, Telegram writes, and credential reads: zero.

## Follow-up: V26 archive versus M5 historical forecasts (2026-11-05)

A second, local-only audit inspected the existing `market-resolution/latest` rows for the 47 locked Crown observations and the private M5 forecast file. The public V26 `observations.jsonl` is schema-minimal (status, match ID, signal key and first-seen/freeze timestamps); raw resolved quote/fixture payloads remain outside the public repository. The V26 aggregate `summary.json` has 39 settled scoring rows and aggregate Crown observation P&L, but the scored rows contain no quote prices or market lines.

The private quote payloads verified the Crown bookmaker marker and exact fixture identity. All 47 locked observations pass the event / request / receipt sequence with `quote event <= received < kickoff`. Thirty-nine fixtures join by exact match ID and fixture identity to the M5 annual UTC walk-forward forecast and independent post-kickoff FT receipt. On review, the lack of a contemporaneous M5 forecast-generation receipt does not disqualify a historical hindcast: the M5 training cutoff and `prediction_asof_utc` are before the Crown quote and kickoff, and the probabilities can be deterministically reconstructed without the target result. The 39 are valid retrospective M5/Crown AH hindcast observations, but are not archived live M5 signals.

The exact-line replay produced these aggregate results (one 1U bet per unique fixture, no EV gate): M5 on the V26 first-locked Crown quotes, n=39, 8 full wins / 5 half wins / 6 pushes / 3 half losses / 17 losses, -8.985U, ROI -23.038462%, maximum quote-event drawdown 12.695U, settlement log loss 1.16726241 and Brier 0.73294132. The browser AI direction replayed on those same 39 M5-join fixtures and Crown contracts was +9.815U / +25.166667%; this is a small descriptive direction baseline, not an M5 result or formal MR1 model comparison. The V23 later Crown quote for the same 39 fixtures produced M5 -9.475U / -24.294872%. All 39 overlapping V23 quote events are later than their V26 quote events. Consequently V26 adds no new distinct fixture-market to the deduplicated V23 cohort; the union remains AH n=317 (ROI -4.088328%). OU remains V23-only at n=317 and V26 has no OU prices. Do not add the two AH source samples together or treat their different quote times as distinct matches.

The parallel MR1 V6 forward archive has records for 39 of those fixture IDs, but contains only market-fit statuses and selected-side summaries rather than an auditable full score distribution; it is not a substitute M5 forecast. The V26 scored summary omits contract prices/lines, so it cannot independently reproduce the M5 P&L; the private source-verified quote payloads were required for the replay.

Replay code and aggregate receipt: `research/m5/m5_v26_crown_oos_replay.py` and `research/m5/results/m5_v26_crown_oos_replay.json`. Audit source SHA-256 values (local archive only): observations `5d2b236e500c90447274ea0c78123832f6debc6dbb6b3ace136c695da5468db6`, V26 summary `24ad11aad9668aef6c1e425ceb3f0dde71ef7c2d3b40b67e0775dff5db7c5e32`, protocol `a31d541d9ad024530a913ba5de3d985d4fe5fda04386f6109b6f8162ac4dec0b`. No raw quote values, match IDs, teams or credentials were copied into this report. This follow-up made no provider requests or production writes.
