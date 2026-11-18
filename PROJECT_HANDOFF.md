# PROJECT HANDOFF

## Current project state — 2026-11-18

### M8 research

The latest completed research is **M8 R64 — injury event timing / multi-source confirmation / Crown T12 temporal ordering**.

GitHub report:
research/m8/M8_R64_INJURY_EVENT_TIME_ORDER_20261118.md

Commit:
bc66ef0d36475a4cc63aa49a660d2905e328e152

### Confirmed research facts

R61 baseline:
- 47 dated-news/Crown T12 matches
- 46 FT AH reconciled
- 39 research diagnostic samples

R64 found that Guardian article timestamps are not sufficient to identify first public injury information. A Guardian article can be published after the Crown T12 source event even when the underlying absence was already public earlier.

Event-level spot checks identified both directions:
- Arsenal–Leeds / Tzolis: information was already public before Crown T12 source event; Guardian article was a later aggregation.
- Everton–Chelsea / Emegha: manager confirmation at 13:24 UTC preceded Crown T12 source event at 13:39:10 UTC; multiple outlets confirmed shortly afterward.
- Brentford–Nottingham Forest / Fabio Carvalho: Crown T12 source event at 11:34:11 UTC preceded subsequent multi-source confirmation that Carvalho would miss the match; T12 and T24 AH line/price in the R61 snapshot were unchanged.

### Current research direction

Do not continue adjusting injury-count weights.

Continue event-level reconstruction:
1. first public confirmation time;
2. second/third independent confirmation time;
3. Crown T12 source-event time;
4. Crown T12 received time;
5. T12→T24 line and odds response;
6. match result.

Classify events by temporal order before testing profitability.

No new hard gates, filters, thresholds, quantity limits, or betting rules were added by R64.

### Next concrete task

Continue from R64 by reconstructing the event timeline across the R61 46 reconciled fixtures, prioritizing newly confirmed absences that occur after the Crown T12 source event and checking whether Crown T24 subsequently reprices them.
