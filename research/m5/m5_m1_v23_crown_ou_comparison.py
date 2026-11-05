#!/usr/bin/env python3
"""Compare M5 and frozen M1 V23 OU forecasts on identical verified Crown quotes.

Private inputs stay outside the repository. The output is aggregate-only and
requires an exact source fixture ID, UTC kickoff, team identity, strict M5
walk-forward timestamps, pre-kickoff Crown observation/receipt, and verified
post-kickoff FT. No positive-EV filter or other bet-count rule is applied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def instant(value: str | None) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def identity(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower())


def outcome_distribution(grid: list[list[float]], side: str, line: float) -> tuple[float, ...]:
    categories = ("win", "half_win", "push", "half_loss", "loss")
    distribution = Counter()
    for home, row in enumerate(grid):
        for away, probability in enumerate(row):
            _, category = legs_result("OU", side, line, home, away)
            distribution[category] += float(probability)
    return tuple(distribution[key] for key in categories)


def score_rows(rows: list[dict], model_key: str) -> dict:
    scored = []
    for row in rows:
        if model_key == "M5_full_score_grid":
            grid = row["forecast"]["prediction"]["grid"]
            sides = ("over", "under")
            evs = [expected_return(grid, "OU", side, row["line"], price)
                   for side, price in zip(sides, row["prices"])]
            side_i = 0 if evs[0] >= evs[1] else 1
            side, ev, price = sides[side_i], evs[side_i], row["prices"][side_i]
            distribution = outcome_distribution(grid, side, row["line"])
        else:
            mean = float(row["observation"]["predicted_total_variants"]["m1_calibrated"])
            sides = ("over", "under")
            evs = [0.0, 0.0]
            # Evaluate the frozen M1 Poisson total model on the exact Crown contract.
            # Its expected-return helper is represented by a truncated Poisson grid.
            grid = []
            probability = math.exp(-mean)
            probs = [probability]
            for goals in range(1, 41):
                probability *= mean / goals
                probs.append(probability)
            total_mass = sum(probs)
            probs = [p / total_mass for p in probs]
            for i, side_name in enumerate(sides):
                evs[i] = sum(probs[g] * payout(legs_result("OU", side_name, row["line"], 0, g)[0], row["prices"][i])
                             for g in range(41))
            side_i = 0 if evs[0] >= evs[1] else 1
            side, ev, price = sides[side_i], evs[side_i], row["prices"][side_i]
            distribution_counter = Counter()
            for goals, probability in enumerate(probs):
                _, category = legs_result("OU", side, row["line"], 0, goals)
                distribution_counter[category] += probability
            distribution = tuple(distribution_counter[k] for k in ("win", "half_win", "push", "half_loss", "loss"))

        total = row["total_goals"]
        _, actual = legs_result("OU", side, row["line"], 0, total)
        units = payout(legs_result("OU", side, row["line"], 0, total)[0], price)
        categories = ("win", "half_win", "push", "half_loss", "loss")
        actual_index = categories.index(actual)
        brier = sum((p - (1.0 if i == actual_index else 0.0)) ** 2 for i, p in enumerate(distribution))
        scored.append({"row": row, "units": units, "category": actual, "log_loss": -math.log(max(distribution[actual_index], 1e-15)),
                       "brier": brier, "ev": ev})

    n = len(scored)
    outcomes = Counter(x["category"] for x in scored)
    pnl_by_event: dict[datetime, float] = defaultdict(float)
    for item in scored:
        pnl_by_event[item["row"]["observed"]] += item["units"]
    equity = peak = max_dd = 0.0
    for event in sorted(pnl_by_event):
        equity += pnl_by_event[event]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    rng = random.Random(20261105)
    values = [x["units"] for x in scored]
    boot = sorted(100 * sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000)) if n else []
    return {
        "unique_fixtures": n,
        "simulated_bets": n,
        "settled_bets": n,
        "settlement_counts": {key: outcomes[key] for key in ("win", "half_win", "push", "half_loss", "loss")},
        "net_units": round(sum(values), 6),
        "roi_pct": round(100 * sum(values) / n, 6) if n else None,
        "max_drawdown_units_by_quote_event": round(max_dd, 6),
        "settlement_log_loss": round(sum(x["log_loss"] for x in scored) / n, 8) if n else None,
        "settlement_brier": round(sum(x["brier"] for x in scored) / n, 8) if n else None,
        "mean_selected_ev_pct": round(100 * sum(x["ev"] for x in scored) / n, 6) if n else None,
        "fixture_bootstrap_roi_95pct": [round(boot[249], 6), round(boot[9749], 6)] if n else None,
    }


def run(forecasts_path: Path, observations_path: Path, summary_path: Path, verified_ft_path: Path) -> dict:
    forecast_raw = forecasts_path.read_bytes()
    forecast_rows = {}
    for line in forecast_raw.decode().splitlines():
        try:
            row = json.loads(line)
            forecast_rows[str(row["match_id"])] = row
        except Exception:
            continue
    observations_raw = observations_path.read_bytes()
    observations = [json.loads(line) for line in observations_raw.decode().splitlines() if line.strip()]
    summary_raw = summary_path.read_bytes()
    summary = json.loads(summary_raw)
    ft_raw = verified_ft_path.read_bytes()
    ft_doc = json.loads(ft_raw)
    ft_records = ft_doc.get("results", {})
    outcomes = {str(row["fixture_id"]): row for row in summary.get("per_fixture_outcome_rows", [])}
    eligible = [row for row in observations if row.get("status") == "LOCKED_ELIGIBLE"]
    counts = Counter()
    rows = []

    if summary.get("bookmaker_source") != "crown" or summary.get("protocol") != "M1_OU_CROWN_MARKET_CHALLENGER_V23":
        raise ValueError("input archive is not the frozen Crown V23 source")
    if len(observations) != len({str(row.get("fixture_id")) for row in observations}):
        raise ValueError("duplicate source fixture observations")
    if len(eligible) != len({str(row.get("fixture_id")) for row in eligible}):
        raise ValueError("duplicate eligible source fixture observations")

    for observation in eligible:
        mid = str(observation.get("fixture_id") or "")
        forecast = forecast_rows.get(mid)
        if not forecast:
            counts["no_exact_m5_fixture_id"] += 1
            continue
        kickoff = instant(observation.get("kickoff_at"))
        scan_start = instant(observation.get("scan_started_at"))
        scan_received = instant(observation.get("scan_completed_at"))
        quote_event = instant(observation.get("crown_event_at"))
        pred_asof = instant(forecast.get("prediction_asof_utc"))
        train_end = instant(forecast.get("train_end_utc"))
        forecast_kickoff = instant(forecast.get("kickoff"))
        if not all((kickoff, scan_start, scan_received, quote_event, pred_asof, train_end, forecast_kickoff)):
            counts["invalid_timestamp"] += 1
            continue
        if (kickoff != forecast_kickoff or quote_event >= kickoff or scan_start >= scan_received or scan_received >= kickoff
                or quote_event > scan_received or pred_asof > quote_event or train_end >= pred_asof):
            counts["time_order_or_kickoff_mismatch"] += 1
            continue
        if any(identity(observation.get(field)) != identity(forecast.get(field)) for field in ("home", "away", "competition")):
            # M1 stores the competition under `competition`; M5 uses `league`.
            if identity(observation.get("home")) != identity(forecast.get("home")) or identity(observation.get("away")) != identity(forecast.get("away")):
                counts["team_identity_mismatch"] += 1
                continue
            if identity(observation.get("competition")) != identity(forecast.get("league")):
                counts["league_identity_mismatch"] += 1
                continue
        if not forecast.get("prediction", {}).get("grid"):
            counts["m5_grid_missing"] += 1
            continue

        outcome = outcomes.get(mid)
        if not outcome or outcome.get("result_source") not in ("TOTALCORNER_VERIFIED_FT_BY_MATCH_VIEW", "M1_FORMAL_VERIFIED_FT_RECEIPT"):
            counts["no_independent_verified_ft"] += 1
            continue
        if outcome.get("result_source") == "TOTALCORNER_VERIFIED_FT_BY_MATCH_VIEW":
            receipt = ft_records.get(mid)
            receipt_at = instant((receipt or {}).get("observed_at"))
            if (not receipt or receipt.get("result_status") != "full" or receipt.get("identity_verified") is not True
                    or str(receipt.get("fixture_id")) != mid or not receipt_at or receipt_at <= kickoff):
                counts["ft_receipt_validation_fail"] += 1
                continue
            goals = receipt.get("goals") or []
            if len(goals) != 2:
                counts["ft_receipt_validation_fail"] += 1
                continue
            total_goals = sum(int(goal) for goal in goals)
            if total_goals != int(outcome["total_goals"]):
                counts["ft_total_mismatch"] += 1
                continue
        else:
            # Formal FT receipts in this frozen report are independently verified;
            # retain only when a matching post-kickoff receipt is present.
            receipt = ft_records.get(mid)
            receipt_at = instant((receipt or {}).get("observed_at"))
            if (not receipt or receipt.get("result_status") != "full" or receipt.get("identity_verified") is not True
                    or str(receipt.get("fixture_id")) != mid or not receipt_at or receipt_at <= kickoff):
                counts["ft_receipt_validation_fail"] += 1
                continue
            goals = receipt.get("goals") or []
            if len(goals) != 2:
                counts["ft_receipt_validation_fail"] += 1
                continue
            total_goals = sum(int(goal) for goal in goals)
            if total_goals != int(outcome["total_goals"]):
                counts["ft_total_mismatch"] += 1
                continue

        try:
            line = float(observation["asian_ou_line"])
            prices = (float(observation["over_price"]), float(observation["under_price"]))
        except (KeyError, TypeError, ValueError):
            counts["invalid_ou_quote"] += 1
            continue
        if (not math.isfinite(line) or abs(line * 4 - round(line * 4)) > 1e-8
                or any(not math.isfinite(price) or price <= 1 for price in prices)
                or str(observation.get("bookmaker", "")).casefold() != "crown"):
            counts["invalid_ou_quote"] += 1
            continue
        rows.append({"forecast": forecast, "observation": observation, "line": line, "prices": prices,
                     "total_goals": total_goals, "observed": quote_event, "kickoff": kickoff})
        counts["eligible_settled_common_fixtures"] += 1

    if len(rows) != len({str(row["observation"]["fixture_id"]) for row in rows}):
        raise ValueError("duplicate joined fixture")
    if not rows:
        raise ValueError(f"no valid M5/M1 Crown OU comparison rows; sanitized_validation_counts={dict(counts)}")

    # Re-check that the source's frozen eligibility rule itself is present in this join.
    for row in rows:
        observation = row["observation"]
        event = row["observed"]
        received = instant(observation["scan_completed_at"])
        if not (event < received < row["kickoff"]):
            raise ValueError("Crown event/receipt/kickoff sequence failed")

    return {
        "protocol": "M5_M1_V23_CROWN_OU_SAME_QUOTE_REPLAY_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_bookmaker": "Crown",
        "source_protocol": summary["protocol"],
        "forecast_sha256": digest(forecast_raw),
        "private_source_hashes": {
            "M1_Crown_observations": digest(observations_raw),
            "M1_frozen_summary": digest(summary_raw),
            "independent_verified_FT_receipts": digest(ft_raw),
        },
        "forecast_rows": len(forecast_rows),
        "source_observations": len(observations),
        "source_eligible_fixtures": len(eligible),
        "exact_common_settled_fixtures": len(rows),
        "unique_leagues": len({row["forecast"]["league"] for row in rows}),
        "kickoff_utc_range": [min(row["kickoff"] for row in rows).isoformat().replace("+00:00", "Z"),
                              max(row["kickoff"] for row in rows).isoformat().replace("+00:00", "Z")],
        "crown_quote_event_utc_range": [min(row["observed"] for row in rows).isoformat().replace("+00:00", "Z"),
                                        max(row["observed"] for row in rows).isoformat().replace("+00:00", "Z")],
        "crown_quote_receipt_utc_range": [
            min(instant(row["observation"]["scan_completed_at"]) for row in rows).isoformat().replace("+00:00", "Z"),
            max(instant(row["observation"]["scan_completed_at"]) for row in rows).isoformat().replace("+00:00", "Z"),
        ],
        "quote_received_before_kickoff_verified": True,
        "m5_train_end_and_asof_precede_crown_event_verified": True,
        "outcome_source_independent_post_kickoff_receipt_verified": True,
        "unique_fixture_identity": "Exact TotalCorner match ID plus identical UTC kickoff and normalized home/away/league names; one Crown OU contract per fixture.",
        "selection_method": "On each identical Crown OU line and over/under price pair, each model selects its higher expected-return side and stakes 1U; no EV threshold or other bet-count filter.",
        "markets": {"OU": {
            "M5_annual_walk_forward_full_score_grid": score_rows(rows, "M5_full_score_grid"),
            "M1_V23_frozen_calibrated_total_model": score_rows(rows, "M1_calibrated"),
        }},
        "validation_counts": dict(counts),
        "limitations": [
            "This is a small retrospective same-Crown comparison, not 10,000 fixtures and not an M5 prospective live-signal ledger.",
            "The M1 V23 quote-selection archive was frozen before this M5 comparison; this does not imply the M5 model was contemporaneously issued.",
            "Only OU is available in this source archive; no AH result is inferred.",
        ],
        "raw_quotes_fixture_rows_and_ids_published": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--verified-ft", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.forecasts, args.observations, args.summary, args.verified_ft)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"generated_utc": result["generated_utc"], "source_eligible_fixtures": result["source_eligible_fixtures"],
                      "exact_common_settled_fixtures": result["exact_common_settled_fixtures"],
                      "markets": result["markets"], "validation_counts": result["validation_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
