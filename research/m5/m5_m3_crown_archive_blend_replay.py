#!/usr/bin/env python3
"""Chronological M3/M5 probability comparison on fixed Crown AH0 and OU2.5.

Reads the private M5 forecast/quote archive and public strict M3 OOS rows.
Only aggregate metrics and hashes are written to the requested output path.
The default holdout begins 2026-09-01 UTC; market-specific M3/M5 blend weights
are fitted on earlier settled fixtures by log loss, never on holdout ROI.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.crown_historical_capture import local_to_utc
from research.m5.m3_grid_crown_replay import bootstrap
from research.m5.m5_goal_model_m3_comparison import LEAGUE_CODES, MODELS, norm
from research.m5.m5_source_union_replay import event_rows, fixture_row, instant, read_jsonl

MARKETS = ("AH", "OU")
CATS = ("win", "push", "loss")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_line(raw: object) -> float | None:
    try:
        parts = [float(x.strip()) for x in str(raw).replace("/", ",").split(",")]
    except (TypeError, ValueError):
        return None
    if len(parts) not in (1, 2) or any(not math.isfinite(x) for x in parts):
        return None
    line = sum(parts) / len(parts)
    if abs(line * 4 - round(line * 4)) > 1e-8:
        return None
    return line


def crown_quote(rows: object, market: str, asof, kickoff, zone):
    key = "asian_list" if market == "AH" else "goal_list"
    target_line = 0.0 if market == "AH" else 2.5
    valid = []
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, list) or len(row) < 8:
            continue
        minute, raw_line, price_1, price_2, raw_time, _, _, closed = row[:8]
        if minute not in (None, "", 0, "0") or closed not in (0, "0", False):
            continue
        observed = local_to_utc(raw_time, zone)
        line = parse_line(raw_line)
        try:
            prices = (float(price_1), float(price_2))
        except (TypeError, ValueError):
            continue
        if (not observed or observed < asof or observed >= kickoff or line != target_line
                or any(not math.isfinite(x) or x <= 1 for x in prices)):
            continue
        valid.append((observed, prices))
    return max(valid, key=lambda x: x[0]) if valid else None


def probs_from_grid(grid, market: str) -> tuple[float, ...]:
    if not isinstance(grid, list) or not grid or any(not isinstance(row, list) for row in grid):
        raise ValueError("invalid score grid")
    mass = math.fsum(float(p) for row in grid for p in row)
    if abs(mass - 1.0) > 1e-7:
        raise ValueError("score grid does not sum to one")
    if market == "AH":
        win = push = loss = 0.0
        for h, row in enumerate(grid):
            for a, raw in enumerate(row):
                p = float(raw)
                if not math.isfinite(p) or p < 0:
                    raise ValueError("invalid score probability")
                if h > a:
                    win += p
                elif h == a:
                    push += p
                else:
                    loss += p
        return win, push, loss
    over = math.fsum(float(p) for h, row in enumerate(grid) for a, p in enumerate(row) if h + a > 2)
    return over, 1.0 - over


def m3_probs(row, market: str) -> tuple[float, ...]:
    if market == "AH":
        vals = tuple(float(row[k]) for k in ("ah_home_0_p_win", "ah_home_0_p_push", "ah_home_0_p_lose"))
        if any(not math.isfinite(p) or p < 0 for p in vals) or abs(sum(vals) - 1) > 1e-5:
            raise ValueError("invalid M3 AH0 probabilities")
        return vals
    over = float(row["ou_p_over_2_5"])
    if not math.isfinite(over) or not 0 <= over <= 1:
        raise ValueError("invalid M3 OU probability")
    return over, 1.0 - over


def outcome(market: str, home: int, away: int) -> int:
    if market == "AH":
        return 0 if home > away else 1 if home == away else 2
    return 0 if home + away > 2 else 1


def logloss(probabilities, actual: int) -> float:
    return -math.log(max(float(probabilities[actual]), 1e-15))


def choose_side(market: str, probs, prices):
    if market == "AH":
        p_home, p_push, p_away = probs
        home_ev = p_home * (prices[0] - 1) - p_away
        away_ev = p_away * (prices[1] - 1) - p_home
        idx = 0 if home_ev >= away_ev else 1
        return idx, prices[idx]
    p_over, p_under = probs
    over_ev = p_over * (prices[0] - 1) - p_under
    under_ev = p_under * (prices[1] - 1) - p_over
    idx = 0 if over_ev >= under_ev else 1
    return idx, prices[idx]


def model_side_probs(market: str, base, side_idx: int):
    if market == "AH":
        return tuple(base) if side_idx == 0 else (base[2], base[1], base[0])
    return tuple(base) if side_idx == 0 else (base[1], base[0])


def settle_pnl(market: str, side_idx: int, price: float, home: int, away: int) -> tuple[float, str]:
    actual = outcome(market, home, away)
    if market == "AH":
        if actual == 1:
            return 0.0, "push"
        win = actual == (0 if side_idx == 0 else 2)
    else:
        win = actual == side_idx
    return (price - 1.0, "win") if win else (-1.0, "loss")


def summarize(rows, market: str, seed: int):
    if not rows:
        return {"unique_fixtures": 0, "simulated_bets": 0, "settled_bets": 0, "net_units": 0,
                "roi_pct": None, "settlement_counts": {x: 0 for x in ("win", "half_win", "push", "half_loss", "loss")}}
    counts = Counter(x["category"] for x in rows)
    pnl = [x["pnl"] for x in rows]
    bytime = defaultdict(float)
    for row in rows:
        bytime[row["quote_event_utc"]] += row["pnl"]
    equity = peak = dd = 0.0
    for t in sorted(bytime):
        equity += bytime[t]
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    ll = sum(logloss(x["chosen_side_probs"], x["chosen_side_actual"]) for x in rows) / len(rows)
    brier = sum(sum((p - (1.0 if i == x["chosen_side_actual"] else 0.0)) ** 2
                    for i, p in enumerate(x["chosen_side_probs"])) for x in rows) / len(rows)
    ci = bootstrap(pnl, seed)
    if ci:
        ci = {**ci, "lower_95": round(ci["lower_95"] * 100, 6),
              "upper_95": round(ci["upper_95"] * 100, 6), "units": "percent"}
    return {"unique_fixtures": len(rows), "simulated_bets": len(rows), "settled_bets": len(rows), "pending_bets": 0,
            # These fixed contracts cannot half-win or half-lose; retain the
            # common AH/OU report schema and explicitly report both as zero.
            "settlement_counts": {"win": counts["win"], "half_win": 0, "push": counts["push"],
                                  "half_loss": 0, "loss": counts["loss"]},
            "net_units": round(sum(pnl), 6), "roi_pct": round(100 * sum(pnl) / len(rows), 6),
            "max_drawdown_units_by_quote_event_time": round(dd, 6),
            "roi_bootstrap_95pct": ci, "settlement_log_loss": round(ll, 8),
            "settlement_brier": round(brier, 8),
            "source_fixture_markets": {"Crown": len(rows)},
            "quote_receipt_timing": dict(Counter("pre_kickoff" if x["receipt_before_kickoff"] else "post_kickoff" for x in rows))}


def run(private_dir: Path, m3_csv: Path, output: Path, holdout_start: str, source_timezone: str):
    private_dir = private_dir.expanduser().resolve()
    manifest_raw = (private_dir / "candidate-manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    forecast_path = private_dir / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    forecast_raw = forecast_path.read_bytes()
    forecasts = {}
    for line in forecast_raw.decode().splitlines():
        try:
            row = json.loads(line)
            forecasts[str(row["match_id"])] = row
        except Exception:
            continue
    m3_raw = m3_csv.read_bytes()
    m3_by_key = defaultdict(list)
    counts = Counter()
    for row in csv.DictReader(m3_raw.decode("utf-8-sig").splitlines()):
        if row.get("prediction_status") != "predicted" or row.get("model") not in MODELS:
            continue
        try:
            train_end = instant(row.get("train_end_utc"))
            asof = instant(row.get("match_date_utc"))
            if not train_end or not asof or train_end >= asof:
                counts["m3_non_oos_prediction_rows_excluded"] += 1
                continue
            key = (row["league"], row["match_date_utc"][:10], norm(row["home_team"]), norm(row["away_team"]))
            m3_by_key[key].append(row)
            counts["m3_strict_oos_prediction_rows"] += 1
        except Exception:
            counts["invalid_m3_prediction_rows"] += 1
            continue
    m3 = {}
    collisions = 0
    for key, rows in m3_by_key.items():
        by_model = defaultdict(list)
        for row in rows:
            by_model[row["model"]].append(row)
        if set(by_model) == set(MODELS) and all(len(by_model[m]) == 1 for m in MODELS):
            m3[key] = {model: by_model[model][0] for model in MODELS}
        else:
            collisions += 1
    receipts = {str(x.get("match_id")): x for x in read_jsonl(private_dir / "crown-response-index.jsonl")}
    zone = ZoneInfo(source_timezone)
    cutoff = instant(holdout_start + "T00:00:00Z")
    if cutoff is None:
        raise ValueError("holdout start must be an ISO UTC date")
    examples = {market: [] for market in MARKETS}
    quote_hashes = set()
    for fixture in manifest.get("rows", []):
        mid = str(fixture.get("match_id") or "")
        f = forecasts.get(mid)
        if not f:
            continue
        try:
            kickoff = instant(f["kickoff"])
            m5_asof = instant(f["prediction_asof_utc"])
            m5_train = instant(f["train_end_utc"])
            home, away = int(fixture["home_goals"]), int(fixture["away_goals"])
            grid = f["prediction"]["grid"]
            if not kickoff or not m5_asof or not m5_train or m5_train >= m5_asof:
                counts["bad_m5_chronology"] += 1
                continue
            key = (LEAGUE_CODES.get(str(fixture.get("league") or "")), kickoff.date().isoformat(),
                   norm(fixture.get("home")), norm(fixture.get("away")))
            if not key[0]:
                continue
            model_rows = m3.get(key)
            if not model_rows:
                continue
            actuals = {(int(r["actual_home_goals"]), int(r["actual_away_goals"])) for r in model_rows.values()}
            if len(actuals) != 1 or next(iter(actuals)) != (home, away):
                counts["m3_actual_mismatch"] += 1
                continue
            m3_asof = instant(next(iter(model_rows.values()))["match_date_utc"])
            asof = max(m5_asof, m3_asof)
            if asof >= kickoff:
                counts["bad_joint_asof"] += 1
                continue
            crown_path = private_dir / "crown-responses" / f"{mid}.json"
            if not crown_path.exists():
                continue
            raw = crown_path.read_bytes()
            payload = json.loads(raw)
            provider = fixture_row(payload, mid)
            if (payload.get("success") != 1 or not provider or provider.get("h") != fixture["home"]
                    or provider.get("a") != fixture["away"] or provider.get("l") != fixture["league"]):
                counts["crown_identity_failure"] += 1
                continue
            if local_to_utc(provider.get("start"), zone) != kickoff:
                counts["kickoff_mismatch"] += 1
                continue
            try:
                if (int(provider.get("hg")), int(provider.get("ag"))) != (home, away):
                    counts["score_mismatch"] += 1
                    continue
            except (TypeError, ValueError):
                counts["score_missing"] += 1
                continue
            receipt = instant(receipts.get(mid, {}).get("captured_at_utc"))
            if not receipt:
                counts["receipt_missing"] += 1
                continue
            quote_hashes.add(sha(raw))
            for market in MARKETS:
                quote = crown_quote(event_rows(provider, market, "crown"), market, asof, kickoff, zone)
                if not quote:
                    continue
                observed, prices = quote
                if receipt < observed:
                    counts["receipt_precedes_quote_event"] += 1
                    continue
                key_rows = {}
                m5_probs = probs_from_grid(grid, market)
                for model in MODELS:
                    key_rows[model] = m3_probs(model_rows[model], market)
                # Each row has one common strict OOS M3 fixture and M5 forecast.
                actual = outcome(market, home, away)
                for model, probabilities in {"M5": m5_probs, **key_rows}.items():
                    examples[market].append({"model": model, "kickoff": kickoff, "asof": asof,
                        "quote_event": observed, "receipt": receipt, "prices": prices,
                        "probabilities": probabilities, "actual": actual, "home": home, "away": away,
                        "fixture_key_hash": hashlib.sha256("|".join(key).encode()).hexdigest()})
        except Exception:
            counts["invalid_join_or_probability"] += 1

    weights = {}
    all_metrics = {}
    coverage = {}
    model_selection = {}
    for market in MARKETS:
        market_rows = examples[market]
        fixture_key_counts = Counter(r["fixture_key_hash"] for r in market_rows if r["model"] == "M5")
        colliding_keys = {key for key, count in fixture_key_counts.items() if count > 1}
        counts[f"{market}_M3_M5_identity_key_collisions"] = len(colliding_keys)
        market_rows = [r for r in market_rows if r["fixture_key_hash"] not in colliding_keys]
        # Deduplicate each model observation by its M3 fixture key hash and model.
        dedup = {}
        for row in market_rows:
            dedup[(row["fixture_key_hash"], row["model"])] = row
        market_rows = list(dedup.values())
        train_rows = [r for r in market_rows if r["kickoff"] < cutoff]
        test_rows = [r for r in market_rows if r["kickoff"] >= cutoff]
        train_index = defaultdict(dict)
        test_index = defaultdict(dict)
        for row in train_rows:
            train_index[row["fixture_key_hash"]][row["model"]] = row
        for row in test_rows:
            test_index[row["fixture_key_hash"]][row["model"]] = row
        weights[market] = {}
        for model in MODELS:
            best = None
            best_pairs = 0
            for step in range(21):
                w = step / 20.0
                losses = []
                for pair in train_index.values():
                    row, partner = pair.get(model), pair.get("M5")
                    if not row or not partner:
                        continue
                    blended = tuple(w * a + (1 - w) * b for a, b in zip(partner["probabilities"], row["probabilities"]))
                    losses.append(logloss(blended, row["actual"]))
                if losses:
                    candidate = (sum(losses) / len(losses), w)
                    if best is None or candidate < best:
                        best = candidate
                        best_pairs = len(losses)
            weights[market][model] = {"m5_weight": best[1] if best else None,
                                      "m3_weight": 1 - best[1] if best else None,
                                      "training_pairs": best_pairs,
                                      "train_log_loss": round(best[0], 8) if best else None}
        chosen_models = ["M5", *MODELS, *[f"blend_M5_{m}" for m in MODELS]]
        for model in chosen_models:
            out_rows = []
            for pair in test_index.values():
                base_model = model.removeprefix("blend_M5_") if model.startswith("blend_M5_") else model
                row = pair.get(base_model)
                if not row:
                    continue
                probs = row["probabilities"]
                if model.startswith("blend_M5_"):
                    weight = weights[market][base_model].get("m5_weight")
                    partner = pair.get("M5")
                    if weight is not None and partner:
                        probs = tuple(weight * a + (1 - weight) * b for a, b in zip(partner["probabilities"], probs))
                side_idx, price = choose_side(market, probs, row["prices"])
                pnl, category = settle_pnl(market, side_idx, price, row["home"], row["away"])
                side_probs = model_side_probs(market, probs, side_idx)
                side_actual = row["actual"] if side_idx == 0 else (2 - row["actual"] if market == "AH" else 1 - row["actual"])
                out_rows.append({"pnl": pnl, "category": category,
                    "quote_event_utc": row["quote_event"].isoformat(), "receipt_before_kickoff": row["receipt"] < row["kickoff"],
                    "chosen_side_probs": side_probs, "chosen_side_actual": side_actual})
            all_metrics.setdefault(market, {})[model] = summarize(out_rows, market, 20261106 + len(all_metrics.get(market, {})))
            all_metrics[market][model]["holdout_fixtures"] = len(out_rows)
            all_metrics[market][model]["holdout_start_utc"] = holdout_start
        # Record contract counts independently of model rows.
        counts[f"{market}_train_contract_fixtures"] = len({r["fixture_key_hash"] for r in train_rows if r["model"] == "M5"})
        counts[f"{market}_holdout_contract_fixtures"] = len({r["fixture_key_hash"] for r in test_rows if r["model"] == "M5"})
        eligible_weights = [(model, item["train_log_loss"]) for model, item in weights[market].items()
                            if item["train_log_loss"] is not None]
        selected = min(eligible_weights, key=lambda item: (item[1], item[0]))[0] if eligible_weights else None
        model_selection[market] = {"criterion": "lowest training-period log loss only",
                                   "selected_m3_model": selected,
                                   "selected_holdout_series": f"blend_M5_{selected}" if selected else None,
                                   "holdout_roi_not_used": True}
        market_coverage = {}
        for label, group in (("train", train_index), ("holdout", test_index)):
            unique = [pair["M5"] for pair in group.values() if pair.get("M5")]
            market_coverage[label] = {"unique_fixtures": len(unique),
                "first_kickoff_utc": min((r["kickoff"].isoformat() for r in unique), default=None),
                "last_kickoff_utc": max((r["kickoff"].isoformat() for r in unique), default=None),
                "first_quote_event_utc": min((r["quote_event"].isoformat() for r in unique), default=None),
                "last_quote_event_utc": max((r["quote_event"].isoformat() for r in unique), default=None)}
        coverage[market] = market_coverage

    report = {"protocol": "M5_M3_CROWN_AH0_OU25_CHRONOLOGICAL_BLEND_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {"m3_strict_oos_csv_sha256": sha(m3_raw), "m5_forecast_sha256": sha(forecast_raw),
                   "candidate_manifest_sha256": sha(manifest_raw),
                   "crown_raw_response_hash_set_sha256": sha("\n".join(sorted(quote_hashes)).encode())},
        "holdout_start_utc": holdout_start, "blend_weights_fitted_by": "training-period multiclass/binary log loss; 0.05 grid; never holdout ROI",
        "blend_weights": weights, "model_selection_by_training_log_loss": model_selection,
        "markets": all_metrics, "utc_coverage": coverage,
        "audit_counts": dict(counts),
        "source": "Crown only; exact UTC date/league/normalized-team join; AH0 and OU2.5 fixed contracts; latest eligible Crown event after both M5 and M3 prediction as-of and before kickoff.",
        "selection": "Each model selects the higher expected-return side on every available contract, with no EV threshold or market/league/time/volume filter.",
        "timing_limit": "M3 and M5 forecast records are retrospective walk-forward outputs with verified train_end < prediction_asof <= quote_event < kickoff, not forecasts archived contemporaneously before each event. Historical Crown responses were also retrieved after kickoff. Results are retrospective source-event-time replay, not actual contemporaneous pre-kickoff receipt or executable ROI.",
        "scope_limit": "Only exact M3-supported league/fixture joins and exact AH0/OU2.5 lines; no source mixing or duplicate fixture-market bets. Research only; no production strategy changes."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"], "holdout_start_utc": holdout_start,
                      "blend_weights": weights, "markets": all_metrics, "audit_counts": dict(counts)}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--m3-csv", type=Path, default=Path(__file__).resolve().parents[1] / "m3/results/predictions/9375bdbbb60e7b3c9e71d13bdc7f9e0d6ec57649579a4c2e4a14b9cbf4de8cc0.csv")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--holdout-start", default="2026-09-01")
    p.add_argument("--source-timezone", default="Asia/Shanghai")
    a = p.parse_args()
    run(a.private_dir, a.m3_csv, a.output, a.holdout_start, a.source_timezone)


if __name__ == "__main__":
    main()
