#!/usr/bin/env python3
"""Compare frozen M1 OU means and M5 score grids on exact same Crown quotes.

Private M1 observations and FT receipts remain outside the repo. This is a
small paired research replay, not M1 or M5 production performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout
from research.m5.m1_ou_crown_small_archive_replay import VARIANTS, instant, line_parts, settle


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def poisson_ou_ev(mean: float, side: str, line: float, price: float) -> float:
    probability = math.exp(-mean)
    total_ev = 0.0
    for goals in range(41):
        if goals:
            probability *= mean / goals
        total_ev += probability * settle(side, goals, line, price)[0]
    return total_ev


def run(args) -> dict:
    forecast_raw = args.forecasts.read_bytes()
    forecasts = {}
    for line in forecast_raw.decode().splitlines():
        try:
            row = json.loads(line)
            forecasts[str(row["match_id"])] = row
        except Exception:
            continue
    obs_raw = args.observations.read_bytes()
    observations = [json.loads(line) for line in obs_raw.decode().splitlines() if line.strip()]
    summary_raw = args.summary.read_bytes()
    summary = json.loads(summary_raw)
    ft_raw = args.verified_ft.read_bytes()
    ft_doc = json.loads(ft_raw)
    outcomes = {str(x["fixture_id"]): x for x in summary.get("per_fixture_outcome_rows", [])}
    ft_receipts = ft_doc.get("results", {})
    if summary.get("bookmaker_source") != "crown":
        raise ValueError("M1 V23 source archive is not Crown-only")
    eligible = [x for x in observations if x.get("status") == "LOCKED_ELIGIBLE"]
    if len(eligible) != len({str(x.get("fixture_id")) for x in eligible}):
        raise ValueError("duplicate eligible M1 fixture identity")
    paired = []
    exclusions = Counter()
    for x in eligible:
        mid = str(x.get("fixture_id") or "")
        if str(x.get("bookmaker", "")).strip().casefold() != "crown":
            exclusions["row_not_explicitly_crown"] += 1
            continue
        f = forecasts.get(mid)
        if not f:
            exclusions["no_exact_m5_fixture_id"] += 1
            continue
        try:
            ko = instant(x["kickoff_at"])
            event = instant(x["crown_event_at"])
            started, finished = instant(x["scan_started_at"]), instant(x["scan_completed_at"])
            asof = instant(f["prediction_asof_utc"])
            if (not started < finished < ko or not event < ko or event > finished
                    or event < asof or instant(f["kickoff"]) != ko):
                exclusions["bad_forecast_quote_order"] += 1
                continue
            if (f["home"], f["away"]) != (x["home"], x["away"]):
                exclusions["team_identity_mismatch"] += 1
                continue
            age = float(x.get("price_age_minutes", -1))
            if not x.get("crown_quote_evidence_sha256") or age < 0 or age > 180:
                exclusions["missing_crown_evidence"] += 1
                continue
            ft = ft_receipts.get(mid)
            outcome = outcomes.get(mid)
            if not outcome or not ft or outcome.get("result_source") not in (
                    "TOTALCORNER_VERIFIED_FT_BY_MATCH_VIEW", "M1_FORMAL_VERIFIED_FT_RECEIPT"):
                exclusions["no_verified_ft"] += 1
                continue
            if (ft.get("result_status") != "full" or ft.get("identity_verified") is not True
                    or instant(ft["observed_at"]) <= ko
                    or sum(int(v) for v in ft["goals"]) != int(outcome["total_goals"])):
                exclusions["bad_verified_ft"] += 1
                continue
            if (int(f["home_goals"]) + int(f["away_goals"])) != int(outcome["total_goals"]):
                exclusions["m5_ft_mismatch"] += 1
                continue
            line = float(x["asian_ou_line"])
            over_price, under_price = float(x["over_price"]), float(x["under_price"])
            if any(not math.isfinite(v) for v in (line, over_price, under_price)) or min(over_price, under_price) <= 1:
                exclusions["invalid_quote"] += 1
                continue
            means = x.get("predicted_total_variants") or {}
            if any(not isinstance(means.get(m), (int, float)) for m in VARIANTS):
                exclusions["missing_m1_variant"] += 1
                continue
            paired.append({"forecast": f, "line": line, "over": over_price, "under": under_price,
                           "total": int(outcome["total_goals"]), "means": means,
                           "event": event, "quote_hash": x["crown_quote_evidence_sha256"]})
        except (KeyError, ValueError, TypeError, OverflowError):
            exclusions["invalid_record"] += 1
    model_names = list(VARIANTS) + ["m5_independent_goal_rates"]
    results = {}
    for model in model_names:
        outcomes_count = Counter()
        pnl = 0.0
        for row in paired:
            if model == "m5_independent_goal_rates":
                grid = row["forecast"]["prediction"]["grid"]
                evs = [expected_return(grid, "OU", "over", row["line"], row["over"]),
                       expected_return(grid, "OU", "under", row["line"], row["under"])]
            else:
                mean = float(row["means"][model])
                evs = [poisson_ou_ev(mean, "over", row["line"], row["over"]),
                       poisson_ou_ev(mean, "under", row["line"], row["under"])]
            side = "over" if evs[0] >= evs[1] else "under"
            price = row["over"] if side == "over" else row["under"]
            if model == "m5_independent_goal_rates":
                legs, category = legs_result("OU", side, row["line"], row["forecast"]["home_goals"], row["forecast"]["away_goals"])
                units = payout(legs, price)
            else:
                units, category = settle(side, row["total"], row["line"], price)
            outcomes_count[category] += 1
            pnl += units
        n = len(paired)
        results[model] = {
            "unique_crown_quote_fixtures": n, "simulated_bets": n, "settled_bets": n,
            "full_win": outcomes_count["win"], "half_win": outcomes_count["half_win"],
            "full_loss": outcomes_count["loss"], "half_loss": outcomes_count["half_loss"],
            "push": outcomes_count["push"], "net_units": round(pnl, 6),
            "roi_pct": round(100 * pnl / n, 6) if n else None,
        }
    result = {
        "protocol": "M5_M1_FROZEN_CROWN_OU_EXACT_QUOTE_OOS_COMPARISON_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_rows": len(forecasts), "forecast_sha256": sha(forecast_raw),
        "M1_observations_sha256": sha(obs_raw), "M1_summary_sha256": sha(summary_raw),
        "M1_verified_FT_receipt_sha256": sha(ft_raw),
        "unique_exact_fixture_quote_ft_pairs": len(paired),
        "eligible_M1_Crown_fixtures": len(eligible), "exclusions": dict(exclusions),
        "models": results,
        "scope_note": "M1 frozen expected-total variants converted to Poisson goal-count distributions using the same settlement approach as the existing sanitized M1 archive replay; compared with M5 score-grid probabilities on exact fixture ID, teams, kickoff, Crown line, prices, and verified FT. One unit per fixture for each model. This small retrospective paired sample is not the official M1 production ledger or a broad independent test.",
        "crown_prices_used_only": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"n": len(paired), "models": {k: {x: v[x] for x in ("net_units", "roi_pct")} for k, v in results.items()}, "output": str(args.output)}))
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--forecasts", type=Path, required=True)
    p.add_argument("--observations", type=Path, required=True)
    p.add_argument("--summary", type=Path, required=True)
    p.add_argument("--verified-ft", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    run(p.parse_args())


if __name__ == "__main__":
    main()
