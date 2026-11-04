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
