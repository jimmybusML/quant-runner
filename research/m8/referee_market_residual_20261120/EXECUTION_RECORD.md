# Execution record — M8 referee-specific Crown AH residual

- Research date: 2026-11-20; refresh verification run at `2026-11-20T12:46Z`.
- Research branch base: latest fetched `origin/main` at `36cedce` (`Persist M3 immutable event segment(s)`).
- Crown AH only; no OU model, production workflow, Telegram dispatch, formal ledger write, collection change, or change to frozen M8 groups.
- The target referee is joined from the retrospective Transfermarkt game archive. Its announcement/receipt time is not present. Thus results are historical mechanism diagnostics, not proof of a pregame-available signal.

## Reproduction and verification commands

```text
python3 -m py_compile research/m8/referee_market_residual_20261120/run_referee_residual_research.py research/m8/referee_market_residual_20261120/verify_referee_research.py
python3 research/m8/referee_market_residual_20261120/run_referee_residual_research.py
python3 research/m8/referee_market_residual_20261120/verify_referee_research.py
python3 research/m8/referee_market_residual_20261120/write_sha256_manifest.py
```

The main research run completed. The verifier returned `pass=true`, with 7,081 unique FIDs, 5,501 incremental FIDs outside frozen membership, zero FID overlap, 35,405 method settlement rows and zero settlement/summary errors. For all 7,081 fixtures it independently matched the Crown T1 historical source quote (line and both decimal prices) to the raw response and verified identity and FT. These response bodies are local private data and were not committed.

## Result snapshot

- 2024–2026 outside the frozen eight: 5,501 orders, −14.275U for the referee-only model; the market-plus-referee model lost −213.565U. Same-fixture market-only lost −231.760U, so the referee feature reduced that loss by 18.195U but did not generate profit.
- All three yearly folds for market-plus-referee were negative: 2024 −119.605U, 2025 −40.870U, 2026 through July 6 −53.090U.
- Referee-only was +29.115U in 2024, −48.195U in 2025 and +4.805U in 2026; the cumulative result remained negative.
- The experimental nonpositive-predicted-EV abstention diagnostic made 1,496 bets and lost −68.935U; it is not a production rule.
- The actual MR1 HTTP receipt archive had zero FID overlap with this prediction ledger. Historical Crown quote timestamps are source-event times and are not reported as actual received or executable prices.

## Input and coverage notes

The public SHA manifest hashes all research inputs and generated artifacts. The independent verifier re-reads the raw Crown event archive and the cached raw response index on the Mac; the raw files themselves and any credentials are not included in the public repository. The target assignment source has no verified pregame timestamp. Data stop at 2026-07-06 for target fixtures; no October–November 2026 receipt result is inferred.

## Publication state

This experiment is on standalone research branch `research/m8-referee-residual-20261120`, based on `origin/main` `36cedce`; it is separate from the older cross-league PR branch. Commit `b777327e7de9ecc3d9ab7bffaba39cbc4dabe360` was pushed and PR [#69](https://github.com/jimmybusML/quant-runner/pull/69) is OPEN against `main`, not merged. This is not an M8 production or official Telegram result.
