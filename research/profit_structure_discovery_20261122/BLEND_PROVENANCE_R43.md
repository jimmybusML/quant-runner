# R43 | Root-cause investigation: M5/Crown market-adjusted blend provenance and pricing identity

## Source provenance

- Source code: /Users/mac/QuantAsiaDesk/research-work/m7/m7_frozen_market_probability_blend.py
- Source SHA256: a82db4c126f111e16f1a8053e5c539f9897fc3936b593ff2bae948062df0fc5d
- Frozen summary: /Users/mac/QuantAsiaDesk/research-work/m7/m7_frozen_market_probability_blend_summary.json
- Source summary SHA256: c0727294bd25c15df682670c093bde96f6f2a1e1cc79eac8b0e739dfa2a994bc
- Input ledger: /Users/mac/QuantAsiaDesk/research-work/m7/m7_frozen_market_probability_blend_all_orders.jsonl
- Input SHA256: 6f0bcfc146b6730c23c231589a066d0550aa2dd766c10d89ac2971919768b069

## Exact algorithm from existing source

1. Build M5 five-outcome settlement distribution from exact score grid for a Crown AH quote.
2. Compute normalized two-sided Crown price share q = (1/odds_selected) / ((1/odds_selected)+(1/odds_opposite)).
3. Keep M5 push mass and full-vs-half outcome ratios; reweight positive and negative mass so effective win stake fraction matches q.
4. Fit a convex weight in increments of 0.01 by 2025 realized settlement-class negative log likelihood, not by ROI.
5. Freeze the 2025-selected AH weight at 1.0 and evaluate on later 2026 historical observations.

## 2025 training selection

| Metric | Value |
|---|---:|
| training_fixtures | 1075 |
| raw_m5_nll | 1.04594483 |
| market_adjusted_nll | 0.99796369 |
| selected_blend_weight | 1.0 |
| selected_blend_nll | 0.99796369 |
| selection | minimum 2025 settlement-class NLL over 0.01 grid; frozen for 2026 |

## Full audit

| Year | n | Mean quoted overround | Raw M5 effective win share | Crown no-vig share | Difference pp | Raw EV | Adjusted EV | Realized U | Positive adjusted EV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025 | 1075 | 4.92% | 60.91% | 49.93% | +10.98 | +14.43% | -4.09% | -7.44% | 0 |
| 2026 | 8325 | 4.85% | 60.56% | 49.92% | +10.63 | +13.86% | -4.02% | -3.67% | 0 |

## Mathematical mechanism

For adjusted vector, effective win share q=(1/selected_odds)/(1/selected_odds+1/opposite_odds). With W=p_fullwin+0.5*p_halfwin and L=p_fullloss+0.5*p_halfloss, W/(W+L)=q, hence EV_adjusted=W*(odds-1)-L=(W+L)*(q*odds-1), strictly negative for positive bookmaker overround and W+L>0. Therefore 100% market-adjusted weight cannot have positive EV for either side at quoted odds.

This identity was verified for all 9,400 rows: no market-share mismatches, no push-mass changes, and blended vectors exactly equal the 100% adjusted vectors. Positive adjusted EV = 0 in both years. The zero-bet result is therefore a construction consequence, not demonstrated profitable discrimination.

## 2026 original portfolio provenance

{
  "all_fixed_window_candidates": {
    "orders": 8325,
    "unique_fixtures": 8325,
    "net_units": -305.625,
    "roi_pct": -3.671171,
    "wins": 3895,
    "losses": 3882,
    "pushes": 548
  },
  "blend_positive_expected_return": {
    "orders": 0,
    "unique_fixtures": 0,
    "net_units": 0,
    "roi_pct": null,
    "wins": 0,
    "losses": 0,
    "pushes": 0
  },
  "raw_m5_positive_ev_baseline": {
    "orders": 7160,
    "unique_fixtures": 7160,
    "net_units": -205.055,
    "roi_pct": -2.863897,
    "wins": 3373,
    "losses": 3309,
    "pushes": 478
  }
}

## Critical distinctions

- The 2025 blend-vs-raw log loss is in-sample for the selected blend weight. The frozen 2026 weight is temporally later, but all historical Crown responses were retrieved after kickoff.
- This explains why market adjustment improves probability calibration while removing positive theoretical EV. It does not prove the raw M5 score-grid forecast lacks all independent information; that requires proper independently timestamped evaluation.
- R43 is not an R7 27 or all494 analysis; the original historical structure studies are separate.
- No production or Telegram changes.

## Caveats
- This is an algebraic result of the market_adjust function, not evidence of discovered predictive mispricing.
- 2025 blend weight chosen using 2025 actual settlement outcomes; 2025 model-vs-blend logloss comparison is in-sample.
- 2026 frozen weight is later historical test, but Crown responses were retrieved after kickoff, not live executable.
- The 2026 positive-EV portfolio has 0 orders by construction when AH weight=1 and both sides use same odds-derived q; this is not evidence of a successful profitable selection strategy.
- No pure independent Crown five-class distribution is observed. The adjusted distribution retains M5 push and full/half mix.
- This is M5/M7 historical research, NOT R7 27, all494 or official Telegram orders.
- No production changes, new filters, thresholds, or gates.
