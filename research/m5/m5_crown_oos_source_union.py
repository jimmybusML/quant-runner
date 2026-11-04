#!/usr/bin/env python3
"""Deduplicated 2026 M5 Crown replay across two evidence tiers.

Use MR1 V23 quotes when a fixture-market has a verified Crown receipt before
kickoff and independent FT receipt. Add TotalCorner historical Crown
event-time quotes only for fixture-markets absent from V23. This prevents
double counting while retaining the weaker post-event-retrieved cohort as a
separate reported stratum. Public output contains aggregates and hashes only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def dt(value):
    try:
        value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return value.astimezone(timezone.utc) if value.tzinfo else None
    except (TypeError, ValueError):
        return None

def norm(value):
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower())

def identity_key(forecast):
    kickoff = dt(forecast.get("kickoff"))
    if not kickoff: raise ValueError("forecast identity lacks explicit kickoff UTC")
    return (norm(forecast.get("league")), kickoff.date().isoformat(),
            norm(forecast.get("home")), norm(forecast.get("away")))

def load_forecasts(path: Path, year: int | None = None):
    raw = path.read_bytes()
    rows = {}
    for line in raw.decode().splitlines():
        try:
            row = json.loads(line)
            mid = str(row["match_id"])
            kickoff = dt(row.get("kickoff"))
            if not kickoff or (year is not None and kickoff.year != year):
                continue
            if mid in rows:
                raise ValueError("duplicate forecast fixture ID")
            rows[mid] = row
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
    return raw, rows

def load_mr1(root: Path, forecasts: dict):
    base = root / "data/prospective-market/shadow-v23"
    index_path, registry_path = base / "snapshot-index.jsonl", base / "fixtures.json"
    index_raw, registry_raw = index_path.read_bytes(), registry_path.read_bytes()
    registry = json.loads(registry_raw)
    ft_dir = root / "data/strategy-shadow-ledger/results"
    ft_rows, ft_hashes, ft_stats = {}, set(), {}
    for path in ft_dir.glob("*.json"):
        try:
            raw = path.read_bytes(); row = json.loads(raw)
            if (row.get("status") == "FT" and str(row.get("match_id")) == path.stem
                    and isinstance(row.get("home_goals"), int) and isinstance(row.get("away_goals"), int)):
                ft_rows[path.stem] = row; ft_hashes.add(sha(raw))
                ft_stats[path] = (len(raw), path.stat().st_mtime_ns)
        except Exception:
            continue
    from collections import defaultdict
    candidates = defaultdict(list); snap_hashes = set(); snap_stats = {}; audit = Counter()
    for line in index_raw.decode().splitlines():
        try: entry = json.loads(line)
        except Exception: continue
        mid = str(entry.get("match_id") or ""); forecast = forecasts.get(mid)
        if not forecast or entry.get("classification") != "SNAPSHOT_OK": continue
        path = base / str(entry.get("snapshot_path") or "")
        try:
            st = path.stat(); raw = path.read_bytes(); snapshot = json.loads(raw)
        except Exception: continue
        reg = registry.get(mid, {}); kickoff = dt(forecast.get("kickoff")); ft = ft_rows.get(mid)
        if (snapshot.get("match_id") != mid or reg.get("match_id") != mid
                or any(reg.get(k) != forecast.get(k) for k in ("league", "home", "away"))
                or not kickoff or dt(snapshot.get("kickoff_at")) != kickoff or dt(reg.get("kickoff_at")) != kickoff):
            continue
        if (snapshot.get("source_bookmaker") != "crown" or snapshot.get("source_bookmaker_verified") is not True
                or snapshot.get("prematch_valid") is not True): continue
        if (not ft or (ft.get("home_goals"), ft.get("away_goals")) != (forecast.get("home_goals"), forecast.get("away_goals"))
                or not dt(ft.get("observed_at")) or dt(ft.get("observed_at")) <= kickoff): continue
        received = dt(snapshot.get("received_at")); asof = dt(forecast.get("prediction_asof_utc"))
        if not received or received >= kickoff or not asof or received < asof: continue
        markets = ("AH", "OU")
        for market in markets:
            quote = snapshot.get(market) or {}
            observed = dt(quote.get("observed_at_utc") or quote.get("observed_at"))
            if not observed or not asof <= observed <= received < kickoff or quote.get("closed") is True: continue
            try:
                line = float(quote["line"])
                prices = (float(quote["home_price"]), float(quote["away_price"])) if market == "AH" else (float(quote["over_price"]), float(quote["under_price"]))
            except (KeyError, TypeError, ValueError): continue
            if abs(line * 4 - round(line * 4)) > 1e-8 or any(not math.isfinite(p) or p <= 1 for p in prices): continue
            candidates[(mid, market)].append({"source": "MR1_V23_RECEIVED_BEFORE_KICKOFF", "observed": observed,
                                               "received": received, "line": line, "prices": prices,
                                               "quote_sha": sha(raw), "ft_sha": sha(json.dumps(ft, sort_keys=True).encode())})
            snap_hashes.add(sha(raw)); snap_stats[path] = (st.st_size, st.st_mtime_ns)
            audit[f"{market}_verified_rows"] += 1
    selected = {key: max(values, key=lambda r: (r["observed"], r["received"])) for key, values in candidates.items()}
    return selected, {"index_path": index_path, "registry_path": registry_path,
                     "index_raw": index_raw, "registry_raw": registry_raw,
                     "snap_stats": snap_stats, "ft_stats": ft_stats,
                     "snapshot_hashes": snap_hashes, "ft_hashes": ft_hashes,
                     "audit": audit}

def load_totalcorner(private_dir: Path, forecasts: dict, source_timezone: str):
    from research.m5.crown_historical_capture import local_to_utc
    zone = ZoneInfo(source_timezone); selected = {}; hashes = set(); stats = {}; audit = Counter()
    folder = private_dir / "crown-responses"
    for mid, forecast in forecasts.items():
        path = folder / f"{mid}.json"
        if not path.exists(): continue
        try:
            st = path.stat(); raw = path.read_bytes(); payload = json.loads(raw)
            matches = [m for m in payload.get("data", []) if isinstance(m, dict) and str(m.get("id")) == mid]
            books = [b for m in matches for b in (m.get("bookmakers") or []) if isinstance(b, dict) and b.get("slug") == "crown"]
            kickoff = dt(forecast.get("kickoff"))
            if (payload.get("success") != 1 or len(matches) != 1 or len(books) != 1 or not kickoff
                    or (matches[0].get("h"), matches[0].get("a"), matches[0].get("l")) != (forecast.get("home"), forecast.get("away"), forecast.get("league"))
                    or local_to_utc(matches[0].get("start"), zone) != kickoff
                    or (int(matches[0].get("hg")), int(matches[0].get("ag"))) != (int(forecast["home_goals"]), int(forecast["away_goals"]))):
                continue
            asof = dt(forecast.get("prediction_asof_utc"))
            if not asof: continue
            for market, field in (("AH", "asian_list"), ("OU", "goal_list")):
                eligible = []
                for row in books[0].get(field) or []:
                    if not isinstance(row, list) or len(row) != 8 or row[0] is not None or row[7] not in (0, "0", False): continue
                    observed = local_to_utc(row[4], zone)
                    try:
                        parts = [float(x.strip()) for x in str(row[1]).split(",")]
                        line = sum(parts) / len(parts); prices = (float(row[2]), float(row[3]))
                    except (TypeError, ValueError, ZeroDivisionError): continue
                    if (not observed or not asof <= observed < kickoff or len(parts) not in (1, 2)
                            or abs(line * 4 - round(line * 4)) > 1e-8
                            or any(not math.isfinite(p) or p <= 1 for p in prices)): continue
                    eligible.append({"source": "TOTALCORNER_CROWN_EVENTTIME_ONLY", "observed": observed,
                                     "received": None, "line": line, "prices": prices, "quote_sha": sha(raw), "ft_sha": None})
                if eligible:
                    selected[(mid, market)] = max(eligible, key=lambda r: r["observed"])
                    audit[f"{market}_eventtime_rows"] += 1
            if any((mid, m) in selected for m in ("AH", "OU")):
                hashes.add(sha(raw)); stats[path] = (st.st_size, st.st_mtime_ns)
        except Exception:
            continue
    return selected, {"hashes": hashes, "stats": stats, "audit": audit}

def score_row(forecast, quote, market):
    from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout
    grid = forecast["prediction"]["grid"]; line = quote["line"]; prices = quote["prices"]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    evs = [expected_return(grid, market, side, line, price) for side, price in zip(sides, prices)]
    i = 0 if evs[0] >= evs[1] else 1; side, price = sides[i], prices[i]
    hg, ag = int(forecast["home_goals"]), int(forecast["away_goals"])
    legs, category = legs_result(market, side, line, hg, ag); units = payout(legs, price)
    dist = Counter()
    for h, row in enumerate(grid):
        for a, probability in enumerate(row):
            _, cat = legs_result(market, side, line, h, a); dist[cat] += float(probability)
    cats = ("win", "half_win", "push", "half_loss", "loss")
    return {"source": quote["source"], "observed": quote["observed"], "category": category,
            "units": units, "log_loss": -math.log(max(dist[category], 1e-15)),
            "brier": sum((dist[c] - (1.0 if c == category else 0.0)) ** 2 for c in cats)}

def summarize(rows):
    n = len(rows); outcomes = Counter(r["category"] for r in rows); net = sum(r["units"] for r in rows)
    by_quote_time = Counter()
    for r in rows: by_quote_time[r["observed"]] += r["units"]
    equity = peak = dd = 0.0
    for quote_time in sorted(by_quote_time):
        equity += by_quote_time[quote_time]; peak = max(peak, equity); dd = max(dd, peak - equity)
    by_league = {}
    for league in sorted({r["league"] for r in rows if r.get("league")}):
        group = [r for r in rows if r.get("league") == league]
        league_outcomes = Counter(r["category"] for r in group); league_net = sum(r["units"] for r in group)
        by_league[league] = {"unique_fixtures": len(group), "simulated_bets": len(group),
                             "settled_bets": len(group), "net_units": round(league_net, 6),
                             "roi_pct": round(league_net * 100 / len(group), 6) if group else None,
                             "full_win": league_outcomes["win"], "half_win": league_outcomes["half_win"],
                             "push": league_outcomes["push"], "half_loss": league_outcomes["half_loss"],
                             "full_loss": league_outcomes["loss"]}
    return {"unique_fixtures": n, "simulated_bets": n, "settled_bets": n,
            "full_win": outcomes["win"], "half_win": outcomes["half_win"], "push": outcomes["push"],
            "half_loss": outcomes["half_loss"], "full_loss": outcomes["loss"],
            "net_units": round(net, 6), "roi_pct": round(net * 100 / n, 6) if n else None,
            "max_drawdown_units_by_quote_event": round(dd, 6) if n else None,
            "settlement_log_loss": round(sum(r["log_loss"] for r in rows) / n, 8) if n else None,
            "settlement_brier": round(sum(r["brier"] for r in rows) / n, 8) if n else None,
            "by_league": by_league}

def run(mr1_root: Path, private_dir: Path, baseline_path: Path, candidate_path: Path,
        output: Path, source_timezone: str):
    baseline_raw, baseline = load_forecasts(baseline_path, 2026)
    candidate_raw, candidate = load_forecasts(candidate_path, 2026)
    if not candidate: raise ValueError("candidate has no 2026 forecast rows")
    for mid, row in candidate.items():
        b = baseline.get(mid)
        if not b or any(b.get(k) != row.get(k) for k in ("league", "home", "away", "kickoff", "home_goals", "away_goals")):
            raise ValueError("baseline/candidate fixture identity or result mismatch")
    mr1, mr1_src = load_mr1(mr1_root, candidate)
    tc, tc_src = load_totalcorner(private_dir, candidate, source_timezone)
    # Re-key on normalized league / UTC date / ordered teams, not only source
    # IDs. This catches cross-provider ID changes and enforces fixture-market
    # uniqueness in the public sample.
    def by_identity(records):
        result = {}
        for (mid, market), quote in records.items():
            key = (identity_key(candidate[mid]), market)
            if key in result:
                raise ValueError("duplicate normalized fixture identity within a quote source")
            result[key] = (mid, quote)
        return result
    mr1_identity = by_identity(mr1)
    tc_identity = by_identity(tc)
    # Prefer a genuinely received pre-kickoff quote on overlapping fixtures.
    # Keep every TotalCorner-only event-time quote as a separate weaker stratum.
    union = dict(mr1_identity)
    for key, value in tc_identity.items():
        if key not in union: union[key] = value
    if (mr1_src["index_path"].read_bytes() != mr1_src["index_raw"]
            or mr1_src["registry_path"].read_bytes() != mr1_src["registry_raw"]):
        raise RuntimeError("MR1 quote archive index changed during replay")
    for path, (size, mtime) in {**mr1_src["snap_stats"], **mr1_src["ft_stats"], **tc_src["stats"]}.items():
        if path.stat().st_size != size or path.stat().st_mtime_ns != mtime:
            raise RuntimeError("source quote or FT input changed during replay")
    # Recheck the TotalCorner source identity set and stable fingerprints by
    # reading the exact quote response files selected above.
    markets = {}
    for market in ("AH", "OU"):
        selected = {key: value for key, value in union.items() if key[1] == market}
        mr1_selected = {key: value for key, value in mr1_identity.items() if key[1] == market}
        tc_selected = {key: value for key, value in tc_identity.items() if key[1] == market}
        tc_only = {key: value for key, value in tc_selected.items() if key not in mr1_selected}
        model_results = {}
        for label, source_rows in (("MR1_received", mr1_selected), ("TotalCorner_eventtime_only", tc_only), ("deduplicated_union", selected)):
            baseline_scored = []
            candidate_scored = []
            for mid, quote in source_rows.values():
                baseline_row = score_row(baseline[mid], quote, market); baseline_row["league"] = baseline[mid]["league"]
                candidate_row = score_row(candidate[mid], quote, market); candidate_row["league"] = candidate[mid]["league"]
                baseline_scored.append(baseline_row); candidate_scored.append(candidate_row)
            model_results[label] = {"baseline": summarize(baseline_scored), "recency_candidate": summarize(candidate_scored)}
        markets[market] = {"MR1_fixture_count": len(mr1_selected), "TotalCorner_raw_fixture_count": len(tc_selected),
                           "same_fixture_identity_source_overlap": len(set(mr1_selected) & set(tc_selected)),
                           "TotalCorner_unique_additions": len(tc_only), "deduplicated_fixture_count": len(selected),
                           "by_evidence_cohort": model_results}
    result = {"protocol": "M5_CROWN_SOURCE_PRIORITY_UNION_OOS_V1",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "baseline_forecast_sha256": sha(baseline_raw), "candidate_forecast_sha256": sha(candidate_raw),
              "forecast_fixture_count": len(candidate), "MR1_snapshot_index_sha256": sha(mr1_src["index_raw"]),
              "MR1_fixture_registry_sha256": sha(mr1_src["registry_raw"]),
              "MR1_quote_snapshot_hash_set_sha256": sha("\n".join(sorted(mr1_src["snapshot_hashes"])).encode()),
              "MR1_verified_FT_hash_set_sha256": sha("\n".join(sorted(mr1_src["ft_hashes"])).encode()),
              "TotalCorner_response_hash_set_sha256": sha("\n".join(sorted(tc_src["hashes"])).encode()),
              "source_priority": "Deduplicate on normalized league, UTC kickoff date, ordered home and away teams, and market. For cross-source overlap retain the MR1 V23 Crown snapshot with received<kickoff and independent FT. Add only TotalCorner event-time Crown movements whose normalized fixture-market is absent from MR1. This produces one row per fixture and market; source cohorts and the unique union are reported separately.",
              "TotalCorner_limitation": "Source event timestamp precedes kickoff, but the historical endpoint response was retrieved after the match and its score is in that response; this is not contemporaneous receipt proof. It is never counted twice when joined with the MR1 receipt-verified cohort.",
              "scope_note": "Partial frozen 51-league M1 scope; strict annual UTC M5 OOS forecasts. AH and OU are separate. Crown prices only; no EV threshold; one 1U simulated bet per unique fixture-market. No rows, identities, teams, odds or credentials are published.",
              "markets": markets}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "markets": {m: {"deduplicated_fixture_count": x["deduplicated_fixture_count"],
              "same_fixture_identity_source_overlap": x["same_fixture_identity_source_overlap"],
              "union_baseline": x["by_evidence_cohort"]["deduplicated_union"]["baseline"],
              "union_recency_candidate": x["by_evidence_cohort"]["deduplicated_union"]["recency_candidate"]}
              for m, x in markets.items()}}, indent=2, sort_keys=True))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mr1-root", type=Path, required=True)
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--baseline-forecasts", type=Path, required=True)
    p.add_argument("--candidate-forecasts", type=Path, required=True)
    p.add_argument("--source-timezone", default="Asia/Shanghai")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.mr1_root, a.private_dir, a.baseline_forecasts, a.candidate_forecasts, a.output, a.source_timezone)

if __name__ == "__main__":
    main()
