#!/usr/bin/env python3
"""Read-only, sanitized refresh of the existing MR1 Crown one-fixture replay.

The private MR1 checkout is an input only. Public output contains aggregates,
hashes, and league summaries; it never contains fixture IDs, teams, prices,
quote rows, or ledgers. No API calls or writes to the source checkout occur.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import unicodedata


def instant(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def selected(row, market):
    evaluation = row.get("evaluation", {})
    if not isinstance(evaluation, dict) or evaluation.get("status") != "ok":
        return None
    entry = evaluation.get(market, {}) if isinstance(evaluation, dict) else {}
    return entry.get("selected") if isinstance(entry, dict) else None


def settle(side, line, price, home_goals, away_goals, market):
    if side not in (("home", "away") if market == "AH" else ("over", "under")):
        return None
    try:
        line, price = float(line), float(price)
    except (TypeError, ValueError):
        return None
    if price <= 1 or abs(line * 4 - round(line * 4)) > 1e-8:
        return None
    parts = [line, line] if abs(line * 2 - round(line * 2)) < 1e-8 else [math.floor(line * 2) / 2, math.floor(line * 2) / 2 + .5]
    legs = []
    for part in parts:
        margin = ((home_goals - away_goals) if side == "home" else (away_goals - home_goals)) + part if market == "AH" else (home_goals + away_goals - part) * (1 if side == "over" else -1)
        legs.append(1 if margin > 1e-9 else -1 if margin < -1e-9 else 0)
    pnl = sum(price - 1 if x == 1 else -1 if x == -1 else 0 for x in legs) / 2
    state = sorted(legs)
    outcome = "win" if state == [1, 1] else "half_win" if state == [0, 1] else "loss" if state == [-1, -1] else "half_loss" if state == [-1, 0] else "push" if state == [0, 0] else None
    return (pnl, outcome) if outcome else None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_competition(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def in_mr1_scope(name, scope):
    league = normalize_competition(name)
    included = any(normalize_competition(x) in league for x in scope.get("include_country_tokens", []))
    excluded = any(normalize_competition(x) in league for x in scope.get("exclude_competition_tokens", []))
    return included and not excluded


def snapshot(files):
    return {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in files}


def source_head(root: Path):
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except Exception:
        return None


def analyze(root: Path):
    forward_dir = root / "data/mr1-v6-cross-market/forward/records"
    result_dir = root / "data/strategy-shadow-ledger/results"
    scope_path = root / "config/validation-spec.json"
    config_raw = scope_path.read_bytes()
    scope = json.loads(config_raw).get("competition_scope", {})
    if not scope:
        raise ValueError("missing frozen MR1 competition scope")
    forward_files = sorted(forward_dir.glob("*.json"))
    result_files = sorted(result_dir.glob("*.json"))
    initial_inventory = snapshot(forward_files + result_files + [scope_path])
    ft = {}
    input_hashes = []
    counts = Counter()
    for path in result_files:
        try:
            raw = path.read_bytes()
            row = json.loads(raw)
        except (OSError, ValueError):
            counts["bad_result_json"] += 1
            continue
        if (row.get("status") == "FT" and str(row.get("match_id")) == path.stem
                and all(isinstance(row.get(k), int) and row[k] >= 0 for k in ("home_goals", "away_goals"))):
            ft[path.stem] = row
            input_hashes.append((str(path.relative_to(root)), digest(raw)))
    group = defaultdict(list)
    league_ids = defaultdict(set)
    kickoffs = []
    quote_times = []
    for path in forward_files:
        counts["forward_files"] += 1
        match_id = path.name.split("-")[0]
        try:
            raw = path.read_bytes()
            row = json.loads(raw)
        except (OSError, ValueError):
            counts["bad_forward_json"] += 1
            continue
        league = str(row.get("league") or "UNKNOWN")
        league_ids[league].add(match_id)
        outcome = ft.get(match_id)
        if not outcome:
            counts["no_verified_ft"] += 1
            continue
        kickoff, received, observed = instant(row.get("kickoff_at")), instant(row.get("received_at")), instant(outcome.get("observed_at"))
        if not kickoff or not received or received >= kickoff or not observed or observed <= kickoff:
            counts["invalid_time"] += 1
            continue
        if row.get("source_bookmaker") != "crown" or row.get("source_bookmaker_verified") is not True:
            counts["unverified_crown"] += 1
            continue
        if str(row.get("match_id")) != match_id:
            counts["wrong_identity"] += 1
            continue
        counts["valid_crown_forward_snapshots"] += 1
        if not in_mr1_scope(league, scope):
            counts["valid_crown_out_of_scope"] += 1
            continue
        counts["valid_crown_in_scope_snapshots"] += 1
        kickoffs.append(kickoff)
        quote_times.append(received)
        input_hashes.append((str(path.relative_to(root)), digest(raw)))
        group[match_id].append((row, outcome))

    aggregates = {m: {"n": 0, "pnl": 0.0, "outcomes": Counter(),
                      "by_league": defaultdict(lambda: {"n": 0, "pnl": 0.0}),
                      "by_quote_time": defaultdict(float), "by_side": defaultdict(lambda: {"n": 0, "pnl": 0.0}),
                      "by_horizon": defaultdict(lambda: {"n": 0, "pnl": 0.0}),
                      "by_quote_age_band": defaultdict(lambda: {"n": 0, "pnl": 0.0}),
                      "quote_age_sum": 0.0, "quote_age_n": 0, "horizons": Counter(),
                      "ev_sum": 0.0, "ev_n": 0, "positive_ev": 0} for m in ("AH", "OU")}
    for match_id, records in group.items():
        for market in ("AH", "OU"):
            chosen = None
            for row, result in sorted(records, key=lambda pair: pair[0].get("received_at", ""), reverse=True):
                contract = selected(row, market)
                if not contract:
                    continue
                settled = settle(contract.get("side"), contract.get("line"), contract.get("price"), result["home_goals"], result["away_goals"], market)
                if settled is not None:
                    chosen = row, result, contract, settled
                    break
            if not chosen:
                continue
            row, result, contract, (pnl, category) = chosen
            a = aggregates[market]
            a["n"] += 1
            a["pnl"] += pnl
            a["outcomes"][category] += 1
            a["by_league"][str(row.get("league") or "UNKNOWN")]["n"] += 1
            a["by_league"][str(row.get("league") or "UNKNOWN")]["pnl"] += pnl
            side = str(contract.get("side") or "UNKNOWN")
            a["by_side"][side]["n"] += 1
            a["by_side"][side]["pnl"] += pnl
            horizon = str(row.get("horizon") or "UNKNOWN")
            a["by_horizon"][horizon]["n"] += 1
            a["by_horizon"][horizon]["pnl"] += pnl
            a["by_quote_time"][str(row.get("received_at"))] += pnl
            age = (row.get("quote_ages_minutes") or {}).get(market)
            if isinstance(age, (int, float)) and math.isfinite(age) and age >= 0:
                a["quote_age_sum"] += age
                a["quote_age_n"] += 1
                band = "<30m" if age < 30 else "30-60m" if age < 60 else "60-120m" if age < 120 else ">=120m"
                a["by_quote_age_band"][band]["n"] += 1
                a["by_quote_age_band"][band]["pnl"] += pnl
            ev = contract.get("EV")
            if isinstance(ev, (int, float)) and math.isfinite(ev):
                a["ev_sum"] += ev
                a["ev_n"] += 1
                a["positive_ev"] += int(ev > 0)
            a["horizons"][str(row.get("horizon") or "UNKNOWN")] += 1

    formatted = {}
    for market, a in aggregates.items():
        equity = peak = drawdown = 0.0
        # Bets sharing a quote receive timestamp are treated as simultaneous.
        for quote_time in sorted(a["by_quote_time"]):
            equity += a["by_quote_time"][quote_time]
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        n = a["n"]
        formatted[market] = {
            "unique_fixtures": n,
            "simulated_bets": n,
            "settled_bets": n,
            "pending_bets": 0,
            "net_units": round(a["pnl"], 6),
            "roi": round(a["pnl"] / n, 8) if n else None,
            "max_drawdown_units_by_quote_timestamp": round(drawdown, 6),
            "settlement_counts": {k: a["outcomes"][k] for k in ("win", "half_win", "loss", "half_loss", "push")},
            "mean_model_ev": round(a["ev_sum"] / a["ev_n"], 8) if a["ev_n"] else None,
            "realized_roi_minus_mean_model_ev": round(a["pnl"] / n - a["ev_sum"] / a["ev_n"], 8) if n and a["ev_n"] == n else None,
            "positive_model_ev_count_diagnostic_only": a["positive_ev"],
            "mean_quote_age_minutes": round(a["quote_age_sum"] / a["quote_age_n"], 3) if a["quote_age_n"] else None,
            "by_league": {k: {"settled_bets": v["n"], "net_units": round(v["pnl"], 6), "roi": round(v["pnl"] / v["n"], 8) if v["n"] else None} for k, v in sorted(a["by_league"].items())},
            "by_side": {k: {"settled_bets": v["n"], "net_units": round(v["pnl"], 6), "roi": round(v["pnl"] / v["n"], 8) if v["n"] else None} for k, v in sorted(a["by_side"].items())},
            "by_horizon": {k: {"settled_bets": v["n"], "net_units": round(v["pnl"], 6), "roi": round(v["pnl"] / v["n"], 8) if v["n"] else None} for k, v in sorted(a["by_horizon"].items())},
            "by_horizon_bet_counts": dict(sorted(a["horizons"].items())),
            "by_quote_age_band_diagnostic_only": {k: {"settled_bets": v["n"], "net_units": round(v["pnl"], 6), "roi": round(v["pnl"] / v["n"], 8) if v["n"] else None} for k, v in sorted(a["by_quote_age_band"].items())},
        }
    final_forward_files = sorted(forward_dir.glob("*.json"))
    final_result_files = sorted(result_dir.glob("*.json"))
    final_files = final_forward_files + final_result_files
    final_inventory = snapshot(final_files + [scope_path])
    if (forward_files != final_forward_files or result_files != final_result_files
            or initial_inventory != final_inventory):
        raise RuntimeError("MR1 source changed during this read; rerun against a stable snapshot")
    manifest = "\n".join(f"{p}\t{h}" for p, h in sorted(input_hashes)).encode()
    return {
        "protocol": "M5_MR1_LOCAL_CROWN_ONE_FIXTURE_REPLAY_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_repo_head": source_head(root),
        "source_paths": ["data/mr1-v6-cross-market/forward/records", "data/strategy-shadow-ledger/results"],
        "competition_scope_sha256": digest(config_raw),
        "competition_scope_protocol": json.loads(config_raw).get("competition_scope_version") or "config/validation-spec.json competition_scope",
        "source_data_snapshot_sha256": digest(manifest),
        "inventory": {
            "forward_snapshot_files": len(forward_files),
            "settlement_result_files": len(result_files),
            "verified_ft_files": len(ft),
            "valid_crown_snapshot_observations_with_ft": counts["valid_crown_forward_snapshots"],
            "valid_crown_snapshot_observations_inside_mr1_scope": counts["valid_crown_in_scope_snapshots"],
            "valid_crown_snapshot_observations_outside_mr1_scope": counts["valid_crown_out_of_scope"],
            "unique_fixture_ids_with_verified_prematch_crown": len(group),
            "league_count_in_forward_inventory": len(league_ids),
            "kickoff_start_utc": min(kickoffs).isoformat() if kickoffs else None,
            "kickoff_end_utc": max(kickoffs).isoformat() if kickoffs else None,
            "quote_received_start_utc": min(quote_times).isoformat() if quote_times else None,
            "quote_received_end_utc": max(quote_times).isoformat() if quote_times else None,
            "invalid_time_snapshots": counts["invalid_time"],
            "unverified_crown_snapshots": counts["unverified_crown"],
            "wrong_match_identity": counts["wrong_identity"],
            "bad_forward_json": counts["bad_forward_json"],
        },
        "markets": formatted,
        "method": "For each verified fixture and market, use the latest valid saved MR1 model-selected Crown quote strictly before kickoff; one unit; Asian full/half/push settlement.",
        "limitations": [
            "Historical MR1 research replay, not M5 predictions or formal TG results.",
            "Only aggregate metrics are published; source prices, teams, fixture IDs, records, and ledgers remain private.",
            "Source was read locally and checked unchanged during analysis. This report does not pin or archive private raw data in the public repository.",
            "This is a historical snapshot and does not establish future profitability.",
        ],
        "production_modified": False,
        "telegram_write": False,
        "network_requests": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mr1-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.mr1_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.out), "generated_utc": report["generated_utc"], "inventory": report["inventory"],
                      "markets": {m: {k: v[k] for k in ("unique_fixtures", "net_units", "roi", "max_drawdown_units_by_quote_timestamp")} for m, v in report["markets"].items()}}, indent=2))


if __name__ == "__main__":
    main()
