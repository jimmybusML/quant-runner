# PROJECT HANDOFF

## Current project state — 2026-11-18

### M8 research

Latest completed research:
**M8 R65 — Crown T12 之后真正新缺阵事件审计**

Report:
research/m8/M8_R65_TRUE_NEW_ABSENCE_AFTER_T12_20261118.md

Machine-readable event data:
research/m8/m8_r65_true_new_absence_after_t12_20261118.json

Report commit:
2381549febd6afed2b44fecba8a8932499680ffc

Event-data commit:
f2fe32a793419b52ea30722dcabab24e58f4222d

### R65 confirmed research facts

R61 baseline:
- 47 dated-news/Crown T12 matches
- 46 FT AH reconciled
- 39 research diagnostic samples

R65 moved from article timestamps to player-level event timelines.

Four high-confidence genuine new absences were identified after the Crown T12 source event:
1. Liverpool–Man City — Dominik Szoboszlai
2. Arsenal–Everton — Jack Grealish
3. Chelsea–Man Utd — Jordan Henderson
4. Bournemouth–Leeds — Noah Okafor

One additional event is medium confidence:
5. Sunderland–Leeds — Nico Elvedi, matchday illness; exact first-public UTC timestamp still unresolved.

These events are materially different from “Guardian article published after T12” cases because the underlying player status changed or became newly unavailable after T12.

### Important methodological correction to R64

The earlier R64 Emegha timestamp should not be treated as a confirmed true post-T12 new-absence event. Later source checks showed that some pre-match secondary reports may have already carried Emegha as unavailable before the Crown T12 event, so R64's 13:24 UTC manager-confirmation claim is not sufficiently reliable for the new-event bucket.

R64's broader conclusion remains valid: article publication time is not equivalent to first public information time.

### R65 event observations

- Szoboszlai: T12 2026-10-10 20:43:14 UTC; new public absence signal appeared on matchday morning; later official/independent confirmation.
- Grealish: T12 2026-10-23 22:16:38 UTC; matchday sickness confirmation at least 14 hours later; prior-day projections still had him available.
- Henderson: T12 2026-10-30 21:31:03 UTC; matchday confirmation around 11:50–11:52 UK; he was originally in line to play.
- Okafor: T12 2026-10-28 22:11:35 UTC; new adductor issue during Friday final training; matchday absence confirmed.
- Elvedi: T12 2026-10-25 00:34:38 UTC; matchday illness exclusion, but exact first-public timestamp unresolved.

### Key unresolved production/research variable

The next high-value task is not more injury-count weighting.

It is to recover:
1. first_public_utc
2. second_confirm_utc
3. multi_source_confirm_utc
4. Crown_T12_source_event_utc
5. Crown_T12_received_utc
6. Crown_T24_source_event_utc
7. Crown_T24_received_utc
8. whether T24 formed before or after the new information
9. exact T12→T24 price/line change

Without the real T24 formation/receipt timestamp, a later T24 price cannot be causally attributed to the new absence.

### Current status

No new hard Gate, filter, threshold, quantity limit, betting rule, production logic, Telegram rule, or settlement rule was added.

No production code was changed.
No production workflow was triggered.
No formal Telegram order was created.
No research result is included in formal M1/MR1/M8 production performance.

Next task: reconstruct Crown T24 source/receipt timing for the R65 true-event cases, then expand the same audit to additional R61 fixtures where a genuinely new matchday absence may have appeared after T12.
