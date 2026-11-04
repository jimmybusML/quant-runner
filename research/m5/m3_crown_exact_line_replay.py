#!/usr/bin/env python3
"""Exact-key M3 OOS predictions versus saved, verified pre-kickoff Crown quotes.

The private MR1 V23 archive is read-only. Public output contains only aggregate
counts, scores, returns, timestamps, and hashes; it never contains row identities,
team names, odds, or quote lines. This evaluates the M3-supported AH0 and OU2.5
contracts only, because the saved M3 artifact does not expose full goal matrices.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

LEAGUE_CODES = {
    "England Premier League": "E0",
    "Germany Bundesliga I": "D1",
    "France Ligue 1": "F1",
    "Italy Serie A": "I1",
    "Spain La Liga": "SP1",
    "Belgium First Division A": "B1",
}
MODELS = ("poisson", "dixon_coles", "bivariate_poisson")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", value)


def instant(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def read_predictions(path: Path):
    by_key = defaultdict(list)
    raw = path.read_bytes()
    for row in csv.DictReader(raw.decode("utf-8-sig").splitlines()):
        if row.get("prediction_status") != "predicted":
            continue
        try:
            probabilities = {
                "p_home": float(row["p_home"]), "p_draw": float(row["p_draw"]), "p_away": float(row["p_away"]),
                "ah_win": float(row["ah_home_0_p_win"]), "ah_push": float(row["ah_home_0_p_push"]),
                "ah_lose": float(row["ah_home_0_p_lose"]), "ou_over": float(row["ou_p_over_2_5"]),
            }
        except (ValueError, TypeError, KeyError):
            continue
        if (any(not math.isfinite(x) or x < 0 or x > 1 for x in probabilities.values())
                or abs(sum(probabilities[k] for k in ("p_home", "p_draw", "p_away")) - 1) > 1e-5
                or abs(sum(probabilities[k] for k in ("ah_win", "ah_push", "ah_lose")) - 1) > 1e-5):
            continue
        date = str(row.get("match_date_utc") or "")[:10]
        if not date:
            continue
        key = (str(row.get("league") or ""), date, norm(row.get("home_team")), norm(row.get("away_team")))
        by_key[key].append({**row, **probabilities})
    valid = {}
    collisions = 0
    for key, rows in by_key.items():
        counts = Counter(str(row.get("model")) for row in rows)
        if any(n != 1 for n in counts.values()):
            collisions += 1
            continue
        if set(counts) == set(MODELS):
            valid[key] = {str(row["model"]): row for row in rows}
    return valid, collisions, raw


def score_multiclass(rows, truth):
    losses, briers = [], []
    for row in rows:
        p = [row["p_home"], row["p_draw"], row["p_away"]]
        y = [1.0 if truth == i else 0.0 for i in range(3)]
        losses.append(-math.log(max(p[truth], 1e-15)))
        briers.append(sum((x - z) ** 2 for x, z in zip(p, y)))
    return round(sum(losses) / len(losses), 8), round(sum(briers) / len(briers), 8)


def settle_ah0(side, home_goals, away_goals, price):
    margin = home_goals - away_goals if side == "home" else away_goals - home_goals
    if margin > 0:
        return price - 1.0, "win"
    if margin < 0:
        return -1.0, "loss"
    return 0.0, "push"


def settle_ou25(side, home_goals, away_goals, price):
    over = home_goals + away_goals > 2.5
    won = (side == "over") == over
    return (price - 1.0, "win") if won else (-1.0, "loss")


def bet_market(market, probability_rows, quote, goals):
    market_quotes = quote["market"]
    if market == "AH":
        win = probability_rows["ah_win"]
        lose = probability_rows["ah_lose"]
        sides = {
            "home": (win * (market_quotes["home_price"] - 1.0) - lose, market_quotes["home_price"]),
            "away": (lose * (market_quotes["away_price"] - 1.0) - win, market_quotes["away_price"]),
        }
        side = max(sides, key=lambda s: sides[s][0])
        pnl, result = settle_ah0(side, *goals, sides[side][1])
        return pnl, result, side
    over = probability_rows["ou_over"]
    sides = {
        "over": (over * (market_quotes["over_price"] - 1.0) - (1.0 - over), market_quotes["over_price"]),
        "under": ((1.0 - over) * (market_quotes["under_price"] - 1.0) - over, market_quotes["under_price"]),
    }
    side = max(sides, key=lambda s: sides[s][0])
    pnl, result = settle_ou25(side, *goals, sides[side][1])
    return pnl, result, side


def bootstrap_roi(values, seed, repetitions=10000):
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    estimates = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(repetitions))
    return {
        "method": "fixture bootstrap percentile interval; descriptive, not a model-selection target",
        "repetitions": repetitions,
        "lower_95": round(estimates[int(0.025 * (repetitions - 1))], 8),
        "upper_95": round(estimates[int(0.975 * (repetitions - 1))], 8),
    }


def summarize(market, model_groups, seed_base):
    entries = {}
    for model, rows in model_groups.items():
        pnl = sum(row[0] for row in rows)
        outcomes = Counter(row[1] for row in rows)
        league_groups = defaultdict(list)
        by_quote_time = defaultdict(float)
        for row in rows:
            league_groups[row[6]].append(row[0])
            by_quote_time[row[5]] += row[0]
        equity = peak = mdd = 0.0
        for quote_time in sorted(by_quote_time):
            equity += by_quote_time[quote_time]
            peak = max(peak, equity)
            mdd = max(mdd, peak - equity)
        result = {
            "unique_fixtures_with_prediction_and_price": len(rows),
            "simulated_bets": len(rows), "settled_bets": len(rows), "pending_bets": 0,
            "net_units": round(pnl, 6), "roi": round(pnl / len(rows), 8) if rows else None,
            "roi_bootstrap_95pct": bootstrap_roi([row[0] for row in rows], seed_base),
            "settlement_counts": {k: outcomes[k] for k in ("win", "half_win", "loss", "half_loss", "push")},
            "max_drawdown_units_by_quote_timestamp": round(mdd, 6),
            "by_league_diagnostic_only": {
                league: {"settled_bets": len(values), "net_units": round(sum(values), 6),
                         "roi": round(sum(values) / len(values), 8)}
                for league, values in sorted(league_groups.items())
            },
        }
        if rows and market == "AH" and all("ah_win" in row[3] for row in rows):
            truth = {"home": 0, "draw": 1, "away": 2}
            ll, br = [], []
            for row in rows:
                probs = [row[3]["ah_win"], row[3]["ah_push"], row[3]["ah_lose"]]
                label = truth[row[4]]
                ll.append(-math.log(max(probs[label], 1e-15)))
                br.append(sum((v - (1.0 if i == label else 0.0)) ** 2 for i, v in enumerate(probs)))
            result["probability_log_loss"] = round(sum(ll) / len(ll), 8)
            result["probability_brier"] = round(sum(br) / len(br), 8)
        elif rows and market == "OU" and all("ou_over" in row[3] for row in rows):
            ll, br = [], []
            for row in rows:
                p = row[3]["ou_over"]
                y = 1.0 if row[4] == "over" else 0.0
                ll.append(-(y * math.log(max(p, 1e-15)) + (1-y) * math.log(max(1-p, 1e-15))))
                br.append((p-y) ** 2)
            result["probability_log_loss"] = round(sum(ll) / len(ll), 8)
            result["probability_brier"] = round(sum(br) / len(br), 8)
        else:
            result["probability_log_loss"] = None
            result["probability_brier"] = None
        entries[model] = result
    return entries


def analyze(mr1_root: Path, prediction_csv: Path, stack_report: Path):
    root = mr1_root / "data/prospective-market/shadow-v23"
    index_path, registry_path = root / "snapshot-index.jsonl", root / "fixtures.json"
    index_initial = (index_path.stat().st_size, index_path.stat().st_mtime_ns)
    index_raw = index_path.read_bytes()
    if (index_path.stat().st_size, index_path.stat().st_mtime_ns) != index_initial:
        raise RuntimeError("MR1 index changed while taking read snapshot; retry")
    registry_stat = (registry_path.stat().st_size, registry_path.stat().st_mtime_ns)
    registry_raw = registry_path.read_bytes()
    registry = json.loads(registry_raw)
    predictions, prediction_collisions, prediction_raw = read_predictions(prediction_csv)
    stack_raw = stack_report.read_bytes()
    stack = json.loads(stack_raw)
    weights = {}
    for market, name in (("AH", "1x2"), ("OU", "ou_over_2_5")):
        split = next(x for x in stack["markets"][name]["season_splits"] if x["test_season"] == "2627")
        weights[market] = split["walkforward_weights"]

    registry_by_key = defaultdict(list)
    fixture_seasons = Counter()
    for fixture_id, fixture in registry.items():
        code = LEAGUE_CODES.get(str(fixture.get("league") or ""))
        kickoff = instant(fixture.get("kickoff_at"))
        if not code or not kickoff:
            continue
        key = (code, kickoff.date().isoformat(), norm(fixture.get("home")), norm(fixture.get("away")))
        registry_by_key[key].append((str(fixture_id), fixture, kickoff))
        fixture_seasons[str(fixture.get("split") or "UNKNOWN")] += 1

    common_keys = set(predictions) & set(registry_by_key)
    key_collisions = sum(len(registry_by_key[key]) != 1 for key in common_keys)
    matched_keys = [key for key in common_keys if len(registry_by_key[key]) == 1]
    matched_ids = {registry_by_key[key][0][0] for key in matched_keys}
    result_dir = mr1_root / "data/strategy-shadow-ledger/results"
    relevant_result_files = sorted(p for p in result_dir.glob("*.json") if p.stem in matched_ids)
    result_stats = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in relevant_result_files}
    verified_results = {}
    result_hashes = []
    for path in relevant_result_files:
        try:
            raw = path.read_bytes()
            row = json.loads(raw)
            fixture_id = str(row.get("match_id") or "")
            observed = instant(row.get("observed_at"))
            scores = (int(row["home_goals"]), int(row["away_goals"]))
        except (OSError, ValueError, TypeError, KeyError):
            continue
        if (path.stem == fixture_id and row.get("status") == "FT" and observed
                and scores[0] >= 0 and scores[1] >= 0):
            verified_results[fixture_id] = {"scores": scores, "observed": observed, "sha": sha(raw)}
            result_hashes.append(sha(raw))
    selected = {}
    quote_observations = Counter()
    snapshot_stats = {}

    for line in index_raw.decode("utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            quote_observations["bad_index_json"] += 1
            continue
        fixture_id = str(entry.get("match_id") or "")
        if fixture_id not in matched_ids:
            continue
        snapshot_path = root / str(entry.get("snapshot_path") or "")
        try:
            stat = snapshot_path.stat()
            snapshot_stats[snapshot_path] = (stat.st_size, stat.st_mtime_ns)
            raw = snapshot_path.read_bytes()
            snapshot = json.loads(raw)
        except (OSError, ValueError):
            quote_observations["unreadable_snapshot"] += 1
            continue
        quote_observations["matched_index_rows"] += 1
        if (snapshot.get("source_bookmaker") != "crown"
                or snapshot.get("source_bookmaker_verified") is not True):
            quote_observations["not_verified_crown"] += 1
            continue
        if snapshot.get("classification") != "SNAPSHOT_OK" or snapshot.get("prematch_valid") is not True:
            quote_observations["not_valid_prematch"] += 1
            continue
        kickoff = instant(snapshot.get("kickoff_at"))
        received = instant(snapshot.get("received_at"))
        if not kickoff or not received or received >= kickoff:
            quote_observations["invalid_chronology"] += 1
            continue
        if snapshot.get("match_id") != fixture_id:
            quote_observations["identity_mismatch"] += 1
            continue
        for market, target_line, price_fields in (
            ("AH", 0.0, ("home_price", "away_price")),
            ("OU", 2.5, ("over_price", "under_price")),
        ):
            q = snapshot.get(market) or {}
            try:
                line_value = float(q.get("line"))
                prices = {field: float(q[field]) for field in price_fields}
            except (TypeError, ValueError, KeyError):
                continue
            if abs(line_value - target_line) > 1e-9 or any(not math.isfinite(x) or x <= 1 for x in prices.values()):
                continue
            observed = instant(q.get("observed_at_utc") or q.get("observed_at") or snapshot.get("received_at"))
            if not observed or observed >= kickoff:
                continue
            if observed > received:
                quote_observations["quote_after_received"] += 1
                continue
            key = (fixture_id, market)
            candidate = {"observed": observed, "kickoff": kickoff, "received": received,
                         "market": {"line": line_value, **prices}, "raw_sha": sha(raw)}
            if key not in selected or observed > selected[key]["observed"]:
                selected[key] = candidate

    forward_dir = mr1_root / "data/mr1-v6-cross-market/forward/records"
    relevant_forward_files = sorted(p for p in forward_dir.glob("*.json") if p.name.split("-")[0] in matched_ids)
    forward_stats = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in relevant_forward_files}
    mr1_matches = defaultdict(list)
    mr1_record_hashes = []
    for path in relevant_forward_files:
        try:
            raw = path.read_bytes()
            row = json.loads(raw)
        except (OSError, ValueError):
            quote_observations["unreadable_mr1_forward_record"] += 1
            continue
        fixture_id = str(row.get("match_id") or "")
        if path.name.split("-")[0] != fixture_id:
            quote_observations["mr1_record_identity_mismatch"] += 1
            continue
        if row.get("source_bookmaker") != "crown" or row.get("source_bookmaker_verified") is not True:
            continue
        if row.get("production_write") is not False or row.get("telegram_write") is not False:
            continue
        received = instant(row.get("received_at"))
        kickoff = instant(row.get("kickoff_at"))
        if not received or not kickoff or received >= kickoff:
            continue
        for market, target_line, price_fields, allowed_sides in (
            ("AH", 0.0, ("home_price", "away_price"), ("home", "away")),
            ("OU", 2.5, ("over_price", "under_price"), ("over", "under")),
        ):
            quote = selected.get((fixture_id, market))
            contract = ((row.get("evaluation") or {}).get(market) or {}).get("selected")
            if not quote or not isinstance(contract, dict) or received != quote["received"]:
                continue
            try:
                line_value, price = float(contract["line"]), float(contract["price"])
            except (TypeError, ValueError, KeyError):
                continue
            side = str(contract.get("side") or "")
            if abs(line_value - target_line) > 1e-9 or side not in allowed_sides:
                continue
            side_index = allowed_sides.index(side)
            if abs(price - quote["market"][price_fields[side_index]]) > 1e-8:
                continue
            mr1_matches[(fixture_id, market)].append({"side": side, "price": price,
                                                       "received": received, "raw_sha": sha(raw)})
            mr1_record_hashes.append(sha(raw))
    mr1_selected = {}
    mr1_conflicts = 0
    for key, rows in mr1_matches.items():
        unique = {(row["side"], row["price"], row["received"]) for row in rows}
        if len(unique) != 1:
            mr1_conflicts += 1
            continue
        mr1_selected[key] = rows[0]

    # There must be one captured price per unique fixture/market, with no
    # look-ahead in model training and with quarter/half settlement preserved.
    evaluated = {market: defaultdict(list) for market in ("AH", "OU")}
    evaluated_common = {market: defaultdict(list) for market in ("AH", "OU")}
    for key in matched_keys:
        fixture_id, fixture, kickoff = registry_by_key[key][0]
        model_rows = predictions[key]
        if any(not row.get("train_end_utc") or instant(row["train_end_utc"]) >= kickoff for row in model_rows.values()):
            quote_observations["training_cut_after_kickoff"] += 1
            continue
        outcome_row = next(iter(model_rows.values()))
        try:
            home_goals, away_goals = int(outcome_row["actual_home_goals"]), int(outcome_row["actual_away_goals"])
        except (ValueError, TypeError):
            continue
        if any((int(row["actual_home_goals"]), int(row["actual_away_goals"])) != (home_goals, away_goals)
               or row.get("season") != outcome_row.get("season")
               or row.get("train_end_utc") != outcome_row.get("train_end_utc") for row in model_rows.values()):
            quote_observations["model_result_or_season_disagreement"] += 1
            continue
        verified_ft = verified_results.get(fixture_id)
        verified_ft_after_kickoff = bool(verified_ft and verified_ft["observed"] > kickoff)
        if not verified_ft_after_kickoff:
            quote_observations["missing_verified_ft_after_kickoff"] += 1
        if verified_ft_after_kickoff and verified_ft["scores"] != (home_goals, away_goals):
            quote_observations["m3_mr1_ft_disagreement"] += 1
            continue
        if (home_goals, away_goals) != (int(fixture.get("home_goals", home_goals)), int(fixture.get("away_goals", away_goals))):
            # Registry normally has no scores; when it does, do not accept disagreements.
            quote_observations["result_identity_disagreement"] += 1
            continue
        result = "home" if home_goals > away_goals else "draw" if home_goals == away_goals else "away"
        ou_result = "over" if home_goals + away_goals > 2.5 else "under"
        for market in ("AH", "OU"):
            quote = selected.get((fixture_id, market))
            if not quote:
                continue
            rows = {m: model_rows[m] for m in MODELS}
            blend = {}
            for field in (("ah_win", "ah_push", "ah_lose") if market == "AH" else ("ou_over",)):
                blend[field] = sum(weights[market][m] * rows[m][field] for m in MODELS)
            for model in MODELS:
                row = rows[model]
                p = ({"ah_win": row["ah_win"], "ah_push": row["ah_push"], "ah_lose": row["ah_lose"]}
                     if market == "AH" else {"ou_over": row["ou_over"]})
                pnl, settled, side = bet_market(market, p, quote, (home_goals, away_goals))
                truth = result if market == "AH" else ou_result
                event = (pnl, settled, side, row, truth, quote["observed"], key[0], fixture_id)
                evaluated[market][model].append(event)
                if verified_ft_after_kickoff and (fixture_id, market) in mr1_selected:
                    evaluated_common[market][model].append(event)
            pnl, settled, side = bet_market(market, blend, quote, (home_goals, away_goals))
            truth = result if market == "AH" else ou_result
            event = (pnl, settled, side, blend, truth, quote["observed"], key[0], fixture_id)
            evaluated[market]["m5_walkforward_blend"].append(event)
            if verified_ft_after_kickoff and (fixture_id, market) in mr1_selected:
                evaluated_common[market]["m5_walkforward_blend"].append(event)
            mr1 = mr1_selected.get((fixture_id, market))
            if mr1 and verified_ft_after_kickoff:
                if market == "AH":
                    mpnl, mresult = settle_ah0(mr1["side"], home_goals, away_goals, mr1["price"])
                else:
                    mpnl, mresult = settle_ou25(mr1["side"], home_goals, away_goals, mr1["price"])
                evaluated_common[market]["mr1_saved_selection"].append(
                    (mpnl, mresult, mr1["side"], {}, truth, quote["observed"], key[0], fixture_id))

    market_results = {market: summarize(market, groups, 20261104 + (0 if market == "AH" else 1))
                      for market, groups in evaluated.items()}
    common_results = {market: summarize(market, groups, 20261154 + (0 if market == "AH" else 1))
                      for market, groups in evaluated_common.items()}

    final_index = (index_path.stat().st_size, index_path.stat().st_mtime_ns)
    final_registry = (registry_path.stat().st_size, registry_path.stat().st_mtime_ns)
    if final_index != index_initial or final_registry != registry_stat:
        raise RuntimeError("MR1 archive changed during read; rerun against a stable snapshot")
    for path, stat in snapshot_stats.items():
        if (path.stat().st_size, path.stat().st_mtime_ns) != stat:
            raise RuntimeError("MR1 quote snapshot changed during read; rerun against a stable snapshot")
    final_forward_files = sorted(p for p in forward_dir.glob("*.json") if p.name.split("-")[0] in matched_ids)
    if final_forward_files != relevant_forward_files or any(
        (path.stat().st_size, path.stat().st_mtime_ns) != stat for path, stat in forward_stats.items()
    ):
        raise RuntimeError("MR1 forward records changed during read; rerun against a stable snapshot")
    final_result_files = sorted(p for p in result_dir.glob("*.json") if p.stem in matched_ids)
    if final_result_files != relevant_result_files or any(
        (path.stat().st_size, path.stat().st_mtime_ns) != stat for path, stat in result_stats.items()
    ):
        raise RuntimeError("MR1 settlement records changed during read; rerun against a stable snapshot")
    quote_manifest = "\n".join(sorted({x["raw_sha"] for x in selected.values()})).encode()
    coverage = Counter(market for _, market in selected)
    both = sum((fixture_id, "AH") in selected and (fixture_id, "OU") in selected for fixture_id in matched_ids)
    return {
        "protocol": "M5_M3_OOS_CROWN_EXACT_LINE_REPLAY_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "prediction_source": "Public M3 strict season-forward predictions; one exact league/date/home/away key, all three model rows required.",
        "prediction_csv_sha256": sha(prediction_raw),
        "stack_report_sha256": sha(stack_raw),
        "crown_fixture_registry_sha256": sha(registry_raw),
        "verified_ft_record_hash_set_sha256": sha("\n".join(sorted(set(result_hashes))).encode()),
        "crown_quote_snapshot_hash_set_sha256": sha(quote_manifest),
        "crown_index_sha256": sha(index_raw),
        "m3_all_model_prediction_fixtures": len(predictions),
        "m3_key_collisions_excluded": prediction_collisions,
        "mr1_supported_scope_registry_fixtures": len(registry_by_key),
        "exact_join_candidate_fixtures": len(common_keys),
        "exact_join_identity_collisions_excluded": key_collisions,
        "exact_join_unique_fixtures": len(matched_keys),
        "exact_join_fixtures_with_verified_ft_after_kickoff": len(verified_results),
        "exact_join_kickoff_start_utc": min(registry_by_key[k][0][2] for k in matched_keys).isoformat() if matched_keys else None,
        "exact_join_kickoff_end_utc": max(registry_by_key[k][0][2] for k in matched_keys).isoformat() if matched_keys else None,
        "crown_quote_unique_fixtures_by_market": dict(coverage),
        "crown_quote_fixtures_with_both_markets": both,
        "mr1_same_snapshot_selection_fixtures_by_market": dict(Counter(market for _, market in mr1_selected)),
        "mr1_same_snapshot_selection_conflicts_excluded": mr1_conflicts,
        "mr1_forward_quote_record_hash_set_sha256": sha("\n".join(sorted(set(mr1_record_hashes))).encode()),
        "snapshot_audit_counts": dict(quote_observations),
        "stack_weights_from_seasons_before_2026_27": weights,
        "markets": market_results,
        "same_crown_quote_comparison_mr1_m3_m5": common_results,
        "crown_quote_times_utc_by_market": {
            market: {
                "observed_start": min((q["observed"] for (fixture_id, m), q in selected.items() if m == market), default=None).isoformat() if any(m == market for _, m in selected) else None,
                "observed_end": max((q["observed"] for (fixture_id, m), q in selected.items() if m == market), default=None).isoformat() if any(m == market for _, m in selected) else None,
                "received_start": min((q["received"] for (fixture_id, m), q in selected.items() if m == market), default=None).isoformat() if any(m == market for _, m in selected) else None,
                "received_end": max((q["received"] for (fixture_id, m), q in selected.items() if m == market), default=None).isoformat() if any(m == market for _, m in selected) else None,
            } for market in ("AH", "OU")
        },
        "method": "For each unique exact-joined fixture, use the latest saved verified Crown quote strictly before kickoff on AH0 or OU2.5. Select the higher model-implied expected-return side on every available fixture (no EV gate); settle one unit. AH/OU are independent.",
        "limitations": [
            "Research-only chronological replay; M3 probabilities are generated by strict season-forward simulation, not contemporaneous archived prediction timestamps.",
            "M3 artifact exposes AH0 probabilities and OU2.5 probability only; no claims are made for other lines.",
            "Crown archive overlap is a small subset and does not meet the 10,000-fixture objective.",
            "MR1 comparison is included only where its saved chosen side, line, price, and receipt timestamp exactly match the Crown snapshot used by M3/M5.",
            "No private row identifiers, teams, odds, quote lines, or raw snapshots are included.",
            "No production, ledger, Telegram, network, or credential operation was performed.",
        ],
        "production_modified": False, "telegram_write": False, "network_requests": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mr1-root", type=Path, required=True)
    parser.add_argument("--prediction-csv", type=Path, required=True)
    parser.add_argument("--stack-report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.mr1_root, args.prediction_csv, args.stack_report)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("generated_utc", "exact_join_unique_fixtures", "crown_quote_unique_fixtures_by_market", "markets")}, indent=2))


if __name__ == "__main__":
    main()
