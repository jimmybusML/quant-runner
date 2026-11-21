# Unverified FT readiness audit — 2026-11-21 14:53 UTC

This is a source-status classification of the 5,180 FIDs still lacking a verified final score in the 14:49 UTC inventory. It does not infer scores or decide that a fixture was abandoned.

| Classification at snapshot time | FIDs |
|---|---:|
| Kickoff still in the future; not yet due for FT verification | 310 |
| Past kickoff; all saved schedule sources have missing/unknown status | 4,235 |
| Past kickoff; at least one source explicitly reports a non-full status | 635 |
| Missing kickoff timestamp | 0 |

The source score fields contain `0:0` placeholders for 4,757 candidates. These values remain unverified and are not treated as results. The 635 non-full rows retain their exact source status strings in the per-FID output so postponed, cancelled, interrupted, and provider-specific codes are not guessed from their numeric values.

The reproducible script is `audit_unverified_ft_readiness.py`. Its outputs are `unverified_ft_readiness_2019_2026_summary.json`, `unverified_ft_readiness_2019_2026_by_league_year.csv`, and `unverified_ft_readiness_2019_2026_per_fid.jsonl`. The input is the SHA-pinned `unverified_FT_candidates.jsonl`; no network request or database write was performed.
