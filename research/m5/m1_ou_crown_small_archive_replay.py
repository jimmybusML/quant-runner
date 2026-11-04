#!/usr/bin/env python3
"""Sanitized replay of the existing, frozen M1 Crown OU archive.

Inputs stay in the private M1 checkout. The output contains aggregate metrics
only (no fixture IDs, teams, lines, prices, API data, or raw quote records).
This is a small candidate replay, not a 10k M5 backtest or production rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

VARIANTS = (
    "crown_market_poisson",
    "m1_calibrated",
    "m1_raw_base",
    "market_75pct_calibrated_25pct",
    "market_75pct_raw_25pct",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def instant(value: str) -> datetime:
    x = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if x.tzinfo is None:
        raise ValueError("timezone-naive timestamp")
    return x.astimezone(timezone.utc)


def line_parts(line: float) -> list[float]:
    if not math.isfinite(line) or abs(line * 4 - round(line * 4)) > 1e-8:
        raise ValueError("unsupported Asian total line")
    if abs(line * 2 - round(line * 2)) < 1e-8:
        return [line, line]
    lower = math.floor(line * 2) / 2
    return [lower, lower + 0.5]


def leg_result(side: str, total: int, line: float) -> int:
    margin = total - line
    if side == "under":
        margin = -margin
    return 1 if margin > 1e-9 else -1 if margin < -1e-9 else 0


def settle(side: str, total: int, line: float, price: float) -> tuple[float, str]:
    legs = [leg_result(side, total, x) for x in line_parts(line)]
    pnl = sum(price - 1 if x == 1 else -1 if x == -1 else 0 for x in legs) / 2
    ordered = sorted(legs)
    category = (
        "win" if ordered == [1, 1] else "half_win" if ordered == [0, 1]
        else "loss" if ordered == [-1, -1] else "half_loss" if ordered == [-1, 0]
        else "push" if ordered == [0, 0] else "other"
    )
    if category == "other":
        raise ValueError("invalid Asian OU settlement state")
    return pnl, category


def expected_pnl(mean: float, side: str, line: float, price: float) -> float:
    if not math.isfinite(mean) or mean <= 0 or not math.isfinite(price) or price <= 1:
        raise ValueError("invalid mean or Crown price")
    prob = math.exp(-mean)
    result = 0.0
    for total in range(41):
        if total:
            prob *= mean / total
        result += prob * settle(side, total, line, price)[0]
    return result


def summarize(rows: list[dict], variant: str, positive_ev_only: bool) -> dict:
    selected = []
    for row in rows:
        odds = ((row["over_ev"], "over", row["over_price"]),
                (row["under_ev"], "under", row["under_price"]))
        ev, side, price = max(odds, key=lambda x: x[0])
        if positive_ev_only and ev <= 0:
            continue
        selected.append((row, side, price, ev))
    settled = [(r, s, p, ev) for r, s, p, ev in selected if r["total_goals"] is not None]
    pnl = 0.0
    outcomes = Counter()
    by_league = defaultdict(lambda: {"bets": 0, "pnl": 0.0})
    ordered_settled = sorted(settled, key=lambda x: (x[0]["decision_at"], x[0]["kickoff"]))
    equity = peak = drawdown = 0.0
    for row, side, price, ev in ordered_settled:
        gain, category = settle(side, row["total_goals"], row["line"], price)
        pnl += gain
        outcomes[category] += 1
        equity += gain
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        league = row["league"] or "UNKNOWN"
        by_league[league]["bets"] += 1
        by_league[league]["pnl"] += gain
    n = len(settled)
    settled_universe = [r for r in rows if r["total_goals"] is not None]
    rng = random.Random(260911 if not positive_ev_only else 260912)
    boot = []
    for _ in range(5000):
        boot_pnl = 0.0
        boot_bets = 0
        for _ in settled_universe:
            row = settled_universe[rng.randrange(len(settled_universe))]
            candidates = ((row["over_ev"], "over", row["over_price"]),
                          (row["under_ev"], "under", row["under_price"]))
            ev, side, price = max(candidates, key=lambda x: x[0])
            if positive_ev_only and ev <= 0:
                continue
            gain, _ = settle(side, row["total_goals"], row["line"], price)
            boot_pnl += gain
            boot_bets += 1
        if boot_bets:
            boot.append(boot_pnl / boot_bets)
    boot.sort()
    return {
        "simulated_bets_including_pending": len(selected),
        "settled_bets": n,
        "pending_bets": len(selected) - n,
        "net_units": round(pnl, 6),
        "roi": round(pnl / n, 8) if n else None,
        "fixture_bootstrap_roi_95pct_descriptive": [round(boot[int(.025 * len(boot))], 8),
                                                     round(boot[min(len(boot) - 1, int(.975 * len(boot)))], 8)] if boot else None,
        "max_drawdown_units_by_utc_day": round(drawdown, 6),
        "settlement_counts": {k: outcomes[k] for k in ("win", "half_win", "loss", "half_loss", "push")},
        "by_league": {k: {"settled_bets": v["bets"], "net_units": round(v["pnl"], 6),
                           "roi": round(v["pnl"] / v["bets"], 8) if v["bets"] else None}
                      for k, v in sorted(by_league.items())},
        "selection": "choose the Crown-price side with greatest model expected return; " +
                     ("retain only positive expected return (research candidate gate)" if positive_ev_only else "bet one unit on every eligible settled fixture"),
    }


def run(observations_path: Path, summary_path: Path, verified_ft_path: Path) -> dict:
    observations = [json.loads(x) for x in observations_path.read_text().splitlines() if x.strip()]
    summary = json.loads(summary_path.read_text())
    outcome_rows = summary.get("per_fixture_outcome_rows", [])
    outcomes = {str(x["fixture_id"]): x for x in outcome_rows}
    if len(outcomes) != len(outcome_rows):
        raise ValueError("duplicate outcome fixture")
    verified_ft_doc = json.loads(verified_ft_path.read_text())
    verified_ft = verified_ft_doc.get("results", {})
    eligible = [x for x in observations if x.get("status") == "LOCKED_ELIGIBLE"]
    if len(eligible) != len({str(x.get("fixture_id")) for x in eligible}):
        raise ValueError("duplicate first-observation fixture")
    if len(observations) != len({str(x.get("fixture_id")) for x in observations}):
        raise ValueError("duplicate V23 observation fixture")
    if len(observations) != summary.get("capture_population", {}).get("unique_first_observed_fixtures"):
        raise ValueError("first-observation count differs from source summary")
    if summary.get("bookmaker_source") != "crown":
        raise ValueError("archive is not Crown-only")
    rows, pending = [], 0
    settlement_sources = Counter()
    for x in eligible:
        fixture = str(x.get("fixture_id"))
        kickoff = instant(x["kickoff_at"])
        started, finished = instant(x["scan_started_at"]), instant(x["scan_completed_at"])
        event = instant(x["crown_event_at"])
        age = float(x["price_age_minutes"])
        if not started < finished < kickoff or not event < kickoff or event > finished:
            raise ValueError("forecast or Crown evidence was not strictly pre-kickoff")
        if age < 0 or age > 180 or not x.get("crown_quote_evidence_sha256"):
            raise ValueError("eligible Crown evidence failed frozen protocol checks")
        line, over, under = (float(x[k]) for k in ("asian_ou_line", "over_price", "under_price"))
        means = x.get("predicted_total_variants") or {}
        if not all(isinstance(means.get(k), (int, float)) for k in VARIANTS):
            raise ValueError("missing frozen candidate prediction")
        outcome = outcomes.get(fixture)
        total = None
        league = str(x.get("competition") or "UNKNOWN")
        if outcome:
            source = outcome.get("result_source")
            if source not in ("TOTALCORNER_VERIFIED_FT_BY_MATCH_VIEW", "M1_FORMAL_VERIFIED_FT_RECEIPT"):
                raise ValueError("unverified FT source")
            total = int(outcome["total_goals"])
            if source == "TOTALCORNER_VERIFIED_FT_BY_MATCH_VIEW":
                receipt = verified_ft.get(fixture)
                if not receipt or receipt.get("result_status") != "full" or receipt.get("identity_verified") is not True:
                    raise ValueError("missing verified full-time receipt")
                if instant(receipt["observed_at"]) <= kickoff or sum(int(v) for v in receipt["goals"]) != total:
                    raise ValueError("FT receipt is not post-kickoff or total does not match")
            settlement_sources[source] += 1
        else:
            pending += 1
        base = {"line": line, "over_price": over, "under_price": under,
                "total_goals": total, "kickoff": kickoff.isoformat(),
                "decision_at": finished.isoformat(), "league": league}
        for variant in VARIANTS:
            mean = float(means[variant])
            base[variant + "_over_ev"] = expected_pnl(mean, "over", line, over)
            base[variant + "_under_ev"] = expected_pnl(mean, "under", line, under)
        rows.append(base)
    if len(rows) != 56 or pending != 4:
        raise ValueError("sample no longer matches the frozen V23 aggregate snapshot")
    methods = {}
    for variant in VARIANTS:
        # Avoid publishing a per-match action table; use only aggregate statistics.
        model_rows = [{**r, "over_ev": r[variant + "_over_ev"], "under_ev": r[variant + "_under_ev"]} for r in rows]
        methods[variant] = {
            "bet_best_side_all_eligible": summarize(model_rows, variant, False),
            "positive_ev_only_candidate": summarize(model_rows, variant, True),
        }
    result = {
        "protocol": "M5_M1_FROZEN_CROWN_OU_ARCHIVE_REPLAY_V1",
        "input_sha256": {"observations": digest(observations_path), "verified_ft_summary": digest(summary_path),
                         "verified_ft_receipts": digest(verified_ft_path)},
        "source_protocol": "M1_OU_CROWN_MARKET_CHALLENGER_V23",
        "source_frozen_at_utc": summary.get("frozen_at_utc"),
        "source_snapshot_generated_utc": summary.get("generated_at"),
        "source_bookmaker": "Crown",
        "population": {"first_observed_unique_fixtures": summary.get("capture_population", {}).get("unique_first_observed_fixtures"),
                       "frozen_protocol_eligible_fixtures": len(eligible),
                       "settled_verified_fixtures": len(rows) - pending,
                       "pending_fixtures": pending,
                       "kickoff_start_utc": min(r["kickoff"] for r in rows),
                       "kickoff_end_utc": max(r["kickoff"] for r in rows)},
        "settlement_evidence_source_counts": dict(sorted(settlement_sources.items())),
        "prediction_and_quote_isolation": "Every retained M1 scan and Crown source event was verified before kickoff; the frozen protocol required quote age <=180 minutes at scan completion. The source archive has no direct bookmaker execution receipt; returns are simulated from its saved Crown-labelled quotes.",
        "settlement": "One-unit Asian OU settlement with half/quarter line splitting; only verified FT rows are included in settled ROI. Four eligible fixtures without an FT in this snapshot remain pending.",
        "methods": methods,
        "interpretation": "This frozen M1 subarchive has only 52 settled fixtures. It is a same-Crown OU research replay and does not meet the 10,000-match requirement or establish an M5 strategy.",
        "raw_quote_values_or_fixture_rows_published": False,
    }
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--observations", type=Path, required=True)
    p.add_argument("--summary", type=Path, required=True)
    p.add_argument("--verified-ft", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = run(a.observations, a.summary, a.verified_ft)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    compact = {k: {s: {"settled_bets": d["settled_bets"], "net_units": d["net_units"], "roi": d["roi"]}
                   for s, d in v.items()} for k, v in result["methods"].items()}
    print(json.dumps({"output": str(a.out), "population": result["population"], "methods": compact}, indent=2))


if __name__ == "__main__":
    main()
