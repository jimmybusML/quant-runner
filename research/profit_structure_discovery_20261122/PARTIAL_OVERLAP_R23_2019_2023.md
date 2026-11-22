# R23 | Partial signal overlap and historical monthly stability

2019-2023 Crown AH only; 494 R7-R15 definitions already selected using outcomes from all five years. Research-only.

## Pairwise Jaccard overlap

Total candidate pairs: 121771; pairs sharing any signal: 5034.

| Jaccard at least | Pair count |
|---|---:|
| 0.5 | 158 |
| 0.7 | 88 |
| 0.8 | 71 |
| 0.9 | 49 |
| 0.95 | 43 |
| 1.0 | 42 |

Connected components based on Jaccard links (transitive chaining is not equivalent to all members mutually similar):

- Threshold 0.5: 378 components; largest 16; 191 candidates in multi-member components.
- Threshold 0.7: 419 components; largest 4; 136 candidates in multi-member components.
- Threshold 0.8: 433 components; largest 4; 114 candidates in multi-member components.
- Threshold 0.9: 446 components; largest 3; 95 candidates in multi-member components.
- Threshold 0.95: 452 components; largest 3; 83 candidates in multi-member components.
- Threshold 1.0: 453 components; largest 3; 81 candidates in multi-member components.

## Monthly stability, earliest/latest signal-bearing quote

| Timing | Conflict | Orders | Net U | Positive months | Negative months | Active months | Worst month |
|---|---|---:|---:|---:|---:|---:|---|
| earliest | skip | 11678 | 1049.77 | 50 | 8 | 58 | ['2023-02', {'n': 219, 'net_U': -18.055, 'roi_pct': -8.2443}] |
| earliest | net | 13137 | 1154.46 | 53 | 5 | 58 | ['2023-02', {'n': 240, 'net_U': -22.61, 'roi_pct': -9.4208}] |
| earliest | margin2 | 5250 | 804.215 | 55 | 3 | 58 | ['2022-03', {'n': 64, 'net_U': -4.895, 'roi_pct': -7.6484}] |
| earliest | margin3 | 2643 | 467.65 | 50 | 8 | 58 | ['2023-09', {'n': 154, 'net_U': -4.165, 'roi_pct': -2.7045}] |
| latest | skip | 11962 | 835.565 | 50 | 8 | 58 | ['2023-02', {'n': 229, 'net_U': -10.545, 'roi_pct': -4.6048}] |
| latest | net | 13410 | 888.38 | 53 | 5 | 58 | ['2023-07', {'n': 50, 'net_U': -9.175, 'roi_pct': -18.35}] |
| latest | margin2 | 6984 | 653.79 | 51 | 7 | 58 | ['2022-03', {'n': 93, 'net_U': -5.66, 'roi_pct': -6.086}] |
| latest | margin3 | 3842 | 463.62 | 51 | 7 | 58 | ['2023-05', {'n': 81, 'net_U': -3.555, 'roi_pct': -4.3889}] |

## Interpretive limits

- Jaccard compares exact matching fixture, quote horizon and physical side; disjoint events may still represent related market mechanisms.
- Monthly positivity is descriptive, not out-of-sample: all 494 structures were preselected on 2019-2023 full-period outcomes.
- A stronger raw vote margin is not necessarily independent consensus due to candidate feature correlations.
- Timing choice and margin cutoffs are experimental comparisons, not user-approved gates or production rules.
- No 2024-2026 data or production changes.
