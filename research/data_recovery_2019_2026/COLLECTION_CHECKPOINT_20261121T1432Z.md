# 2019–2026 all-league historical recovery checkpoint

Snapshot time: 2026-11-21 14:32 UTC. This is an interim data inventory, not a completion claim.

## Live supplemental schedule recovery

The resumable TotalCorner schedule collector (PID 10634) remains active. Its append-only log records 457 successful request attempts and 13,402 newly observed FIDs. Provider pages read without failures:

| Provider league | Pages read | Reported total | Target-period FIDs | Status |
|---|---:|---:|---:|---|
| Spain Segunda (15) | 126 | 196 | 3,731 | Reached pre-2019 boundary |
| Portugal Segunda Liga (57) | 80 | 149 | 2,366 | Reached pre-2019 boundary |
| Ukraine Persha Liga (63) | 38 | 65 | 1,101 | Reached pre-2019 boundary |
| Netherlands Eerste Divisie (121) | 102 | 157 | 3,017 | Reached pre-2019 boundary |
| Japan J2 (128) | 111 | 184 | 3,307 | Still paging; no failures |

The collector defers while an identified scheduled settlement job is active. Raw response bodies and request logs remain in the authorized local workspace; no licensed response bodies are committed.

## Latest schedule and Crown inventory audit

- 127,633 unique schedule FIDs across 70 provider league IDs and 560 league/year cells.
- 122,504 FIDs have verified full-time scores; 5,129 remain unresolved.
- Crown movement quotes: 52,999 FIDs / 4,429,709 quote rows; 49,697 captures explicitly returned no AH movement quotes; 951 failed attempts remain distinct from no-quote responses.
- Crown summary quotes: 49,144 FIDs / 99,520 rows.
- 74,634 current schedule FIDs lack movement quote inventory; the expanding supplemental source means this count will change.
- 9 schedule identity/date conflicts remain isolated; 0 bad cached pages were found.

The supplemental normalized schedule snapshot has 13,522 record versions and SHA256 `af4b89feee1a0a5fa148c49b0eb321e6ff63493cb69119c811311b09158b6a46`.

## Unresolved FT candidates checked against Crown raw responses

A strict offline audit examined 5,129 unresolved FT candidates. Of these, 456 have Crown captures and 1,493 distinct raw responses were checked. No response met the exact-FID, league, kickoff, exact team-name, full-status and nonnegative integer score criteria. Strictly verified Crown raw FT additions: 0. The audit had 0 issues, 0 API requests and 0 SQLite writes. Missing or non-full statuses remain unknown, not inferred scores.

## Work completed in this checkpoint

The coverage matrix, inventory summary, per-FID Crown raw FT audit, offline historical Crown summary import record and this handoff were refreshed. The offline importer added 62 historical summary captures / 124 quote rows using the existing parser; no API requests or live capture rows were changed. A follow-up verifier matched the exact 62 imported `(FID, layer, response SHA)` references and independently confirmed all 62 captures / 124 quote rows. An initial time-cutoff audit had also included 70 unrelated historical movement captures collected during the same period; those were outside this import list and were excluded from the import-specific verifier, with their stored receive times left untouched. Event time and actual receive-time provenance remain separate.

The full 2019–2026 data recovery is still active. Next: finish the current 15-league schedule pagination through the 2019 boundary, then rebuild and collect the remaining movement candidates from the refreshed schedule union, and continue per-league/year FT and price-history gap reconciliation.
