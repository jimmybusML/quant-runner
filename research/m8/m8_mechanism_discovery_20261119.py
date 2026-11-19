#!/usr/bin/env python3
"""M8 M1-M8 mechanism discovery audit.

Research-only replay. Reads the frozen membership archive, historical Crown AH
path features, verified score ledger, audited receipt rows, and the local
read-only Crown capture store. It never writes to production databases or
changes frozen memberships.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import math
import os
import sqlite3
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/m8/mechanism_discovery_20261119"
COHORTS = ("base", "A", "B", "C", "D", "E", "F", "G")
FOUNDATION_SHA = "6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665"
RECEIPT_CUTOFF = "2026-11-13T13:50:53Z"


def envpath(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser()


MEMBERSHIP = envpath(
    "M8_MEMBERSHIP_PATH",
    "/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl",
)
PATH_FEATURES = envpath(
    "M8_PATH_FEATURES",
    "/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl",
)
SAME_LINE_FEATURES = envpath(
    "M8_SAME_LINE_FEATURES",
    "/Users/mac/QuantAsiaDesk/research-work/m8_same_line_probability_path_20261114.jsonl",
)
SCORE_ROWS = envpath(
    "M8_SCORE_ROWS",
    "/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl",
)
EXTRA_FEATURES = envpath(
    "M8_EXTRA_FEATURES",
    "/Users/mac/QuantAsiaDesk/research-work/m8_extra_inventory_frozen_eight_20261115.jsonl",
)
CAPTURE_DB = envpath(
    "M8_CAPTURE_DB", "/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3"
)
RECEIPT_REPLAY = envpath(
    "M8_RECEIPT_REPLAY",
    "/Users/mac/QuantAsiaDesk/research-work/m8_new_receipt_frozen_eight_FT_20261115.jsonl",
)
RECEIPT_AUDIT = ROOT / "research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl"
DECOMPOSITION = ROOT / "research/m8/selective_decomposition_20261120/M8_SELECTIVE_DECOMPOSITION_RESULTS_20261120.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path):
    with path.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def iso_week(date: str) -> str:
    d = dt.date.fromisoformat(date[:10])
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def mdd(rows, pnl_key="pnl_u", date_key="date"):
    by_day = collections.defaultdict(float)
    for r in rows:
        if r.get(date_key) and r.get(pnl_key) is not None:
            by_day[str(r[date_key])[:10]] += float(r[pnl_key])
    equity = high = drawdown = 0.0
    peak_day = trough_day = None
    for day, value in sorted(by_day.items()):
        equity += value
        if equity > high:
            high, peak_day = equity, day
        if high - equity > drawdown:
            drawdown, trough_day = high - equity, day
    return {"max_drawdown_u": round(drawdown, 6), "peak_day": peak_day, "trough_day": trough_day}


def stats(rows, pnl_key="pnl_u", date_key="date"):
    rows = [r for r in rows if r.get(pnl_key) is not None]
    n = len(rows)
    u = sum(float(r[pnl_key]) for r in rows)
    dates = [str(r[date_key])[:10] for r in rows if r.get(date_key)]
    weeks = sorted({iso_week(d) for d in dates})
    # Weekly mean uses the full ISO-week span between first and last observed bet.
    week_count = 0
    if dates:
        a, b = dt.date.fromisoformat(min(dates)), dt.date.fromisoformat(max(dates))
        wa, wb = a.isocalendar(), b.isocalendar()
        week_count = (dt.date.fromisocalendar(wb.year, wb.week, 1) - dt.date.fromisocalendar(wa.year, wa.week, 1)).days // 7 + 1
    return {
        "n": n,
        "net_u": round(u, 6),
        "roi_pct": round(100 * u / n, 6) if n else None,
        "weeks_with_orders": len(weeks),
        "week_span": week_count,
        "orders_per_week_span": round(n / week_count, 6) if week_count else None,
        "weekly": {
            w: {"n": len(v), "net_u": round(sum(float(x[pnl_key]) for x in v), 6)}
            for w, v in sorted(
                ((w, [r for r in rows if iso_week(str(r[date_key])) == w]) for w in weeks),
                key=lambda z: z[0],
            )
        },
        **mdd(rows, pnl_key, date_key),
    }


def settle(line: float, odds: float, goal_diff: int) -> tuple[float, str]:
    """One-unit Asian handicap return, split quarter lines into two half stakes."""
    q = round(float(line) * 4) / 4
    doubled = q * 2
    if abs(doubled - round(doubled)) < 1e-9:
        legs = [q]
    else:
        legs = [math.floor(doubled) / 2, math.ceil(doubled) / 2]
    returns = []
    for leg in legs:
        margin = goal_diff + leg
        if margin > 1e-9:
            returns.append(float(odds) - 1)
        elif margin < -1e-9:
            returns.append(-1.0)
        else:
            returns.append(0.0)
    value = sum(returns) / len(returns)
    if value <= -0.999999:
        state = "full_loss"
    elif value < -1e-9:
        state = "half_loss"
    elif abs(value) < 1e-9:
        state = "push"
    elif value < float(odds) - 1 - 1e-8:
        state = "half_win"
    else:
        state = "full_win"
    return value, state


def safe_float(x, default=0.0):
    try:
        if x is None:
            return default
        y = float(x)
        return y if math.isfinite(y) else default
    except (TypeError, ValueError):
        return default


def market_bucket(line):
    x = abs(safe_float(line))
    if x < 0.125:
        return "0"
    if x <= 0.75:
        return "0.25-0.75"
    if x <= 1.5:
        return "1-1.5"
    return ">1.5"


def price_bucket(price):
    x = safe_float(price)
    if x < 1.65:
        return "<1.65"
    if x < 1.85:
        return "1.65-1.84"
    if x < 2.05:
        return "1.85-2.04"
    return ">=2.05"


def grouped_stats(rows, key_fn, pnl_key="pnl_u"):
    buckets = collections.defaultdict(list)
    for r in rows:
        buckets[str(key_fn(r))].append(r)
    return {k: stats(v, pnl_key) for k, v in sorted(buckets.items())}


def collect_inputs():
    paths = [MEMBERSHIP, PATH_FEATURES, SAME_LINE_FEATURES, SCORE_ROWS, EXTRA_FEATURES, CAPTURE_DB, RECEIPT_REPLAY, RECEIPT_AUDIT, DECOMPOSITION]
    return {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in paths}


def features_by_fid():
    feats = {}
    for p in (PATH_FEATURES, EXTRA_FEATURES, SAME_LINE_FEATURES):
        for r in read_jsonl(p):
            fid = str(r["fid"])
            if fid not in feats:
                feats[fid] = r
            else:
                # Keep the full path row as canonical, filling fields such as
                # unchanged-line probability path that live in a companion file.
                for key, value in r.items():
                    if key not in feats[fid] or feats[fid][key] is None:
                        feats[fid][key] = value
    return feats


def _sg(x):
    return 1 if safe_float(x) > 1e-9 else -1 if safe_float(x) < -1e-9 else 0


def _ah_expected(line, home_price, away_price, rate_home, rate_away):
    """Exact frozen G helper: independent score-grid expected AH payoff."""
    k = 40
    hp, ap = [math.exp(-rate_home)], [math.exp(-rate_away)]
    for i in range(1, k):
        hp.append(hp[-1] * rate_home / i)
        ap.append(ap[-1] * rate_away / i)
    def legs(q):
        d = q * 2
        if abs(d - round(d)) < 1e-9:
            return [q]
        return [math.floor(d) / 2, math.ceil(d) / 2]
    ev_home = ev_away = 0.0
    for i, ph in enumerate(hp):
        for j, pa in enumerate(ap):
            prob = ph * pa
            for hline in legs(line):
                m = i - j + hline
                ev_home += prob / len(legs(line)) * ((home_price - 1) if m > 0 else -1 if m < 0 else 0)
                ev_away += prob / len(legs(line)) * ((away_price - 1) if m < 0 else -1 if m > 0 else 0)
    return ev_home, ev_away


def frozen_rule_side(cohort, feature, score):
    """Recreate each frozen cohort's direction from its pregame path rule."""
    if not feature:
        return None, "missing_market_path"
    line = safe_float(feature.get("end_line"))
    if cohort in ("base", "A", "B"):
        return ("home" if line > 0 else "away"), "frozen_underdog_rule"
    if cohort == "C":
        if abs(line) < 1e-9:
            return None, "C_requires_nonzero_line"
        return ("away" if line > 0 else "home"), "frozen_favorite_rule"
    if cohort == "D":
        return "away", "frozen_zero_line_water_rule"
    if cohort in ("E", "F"):
        p0, p3, p1 = (feature.get(k) for k in ("p0", "p3", "p1"))
        if p0 is None or p3 is None or p1 is None:
            return None, "missing_same_line_probability_path"
        a, b = _sg(safe_float(p3) - safe_float(p0)), _sg(safe_float(p1) - safe_float(p3))
        net = _sg(safe_float(p1) - safe_float(p0))
        s = net or a or b or _sg(feature.get("last_move"))
        if not s or not safe_float(feature.get("n_price_moves")):
            return None, "frozen_EF_rule_not_triggered"
        ups, downs = safe_float(feature.get("up_moves")), safe_float(feature.get("down_moves"))
        if cohort == "E" and ups and downs and not net:
            return ("away" if s > 0 else "home"), "frozen_bidirectional_retrace_rule"
        if cohort == "F" and (not ups or not downs) and a == 0 and b * s == 1:
            return ("home" if s > 0 else "away"), "frozen_one_way_relative_price_rule"
        return None, "frozen_EF_rule_not_triggered"
    if cohort == "G":
        if feature.get("path_shape") != "reverted":
            return None, "G_requires_reverted_path"
        rh, ra = (score or {}).get("lambda_home_0.025"), (score or {}).get("lambda_away_0.025")
        if rh is None or ra is None:
            rates = feature.get("score_rates") or []
            if len(rates) != 2:
                return None, "G_score_rates_unavailable"
            rh, ra = rates
        market = _sg(
            safe_float(feature.get("away_price")) /
            max(safe_float(feature.get("home_price")) + safe_float(feature.get("away_price")), 1e-9)
            - safe_float(feature.get("start_away_price")) /
            max(safe_float(feature.get("start_home_price")) + safe_float(feature.get("start_away_price")), 1e-9)
        )
        if market == 0:
            return None, "G_market_relative_price_flat"
        eh, ea = _ah_expected(line, safe_float(feature.get("home_price")), safe_float(feature.get("away_price")), float(rh), float(ra))
        model = _sg(eh - ea) or 1
        if market == model:
            return ("away" if model > 0 else "home"), "frozen_score_market_contrarian_rule"
        return None, "G_score_market_did_not_align"
    return None, "unknown_frozen_cohort"


def build_member_rows(members, feats, scores):
    out = []
    for m in members:
        f = feats.get(str(m["fid"]))
        s = scores.get(str(m["fid"])) or (f.get("score_row") if f else None)
        side, side_reason = frozen_rule_side(str(m.get("cohort")), f, s)
        row = dict(m)
        row.update({"fid": str(m["fid"]), "direction": side, "direction_status": side_reason})
        if f:
            row.update({
                "league": str(m.get("league") or f.get("league")),
                "line_home": safe_float(f.get("end_line")),
                "odds_home": safe_float(f.get("home_price")),
                "odds_away": safe_float(f.get("away_price")),
                "start_line_home": safe_float(f.get("start_line")),
                "start_odds_home": safe_float(f.get("start_home_price")),
                "start_odds_away": safe_float(f.get("start_away_price")),
                "quote_count": int(safe_float(f.get("n_events"))),
                "line_changes": int(safe_float(f.get("n_line_changes"))),
                "line_range": safe_float(f.get("line_range")),
                "line_shape": f.get("path_shape"),
                "path_6_3_1": f.get("path_6_3_1"),
                "event_age_min": f.get("late_event_age_min"),
                "kickoff_utc": f.get("kickoff_utc"),
            })
            if side:
                row["selected_odds"] = row["odds_home"] if side == "home" else row["odds_away"]
                row["selected_line"] = row["line_home"] if side == "home" else -row["line_home"]
                row["selected_pnl"] = safe_float(m.get("pnl"))
                expected = safe_float(f["end_home_U"] if side == "home" else f["end_away_U"])
                row["frozen_rule_pnl_reproduction"] = abs(expected - row["selected_pnl"]) <= 1e-5
                row["recomputed_strategy_return"] = expected
                row["reverse_pnl"] = safe_float(f["end_away_U"] if side == "home" else f["end_home_U"])
                row["favorite_side"] = "home" if row["line_home"] < -1e-9 else "away" if row["line_home"] > 1e-9 else "level"
                row["selected_is_favorite"] = (side == row["favorite_side"]) if row["favorite_side"] != "level" else None
                if s and s.get("hg") is not None and s.get("ag") is not None:
                    gd = int(s["hg"]) - int(s["ag"])
                    line = row["selected_line"]
                    row["settlement_state_recomputed"] = settle(line, row["selected_odds"], gd if side == "home" else -gd)[1]
        out.append(row)
    return out


def matching_controls(member_rows, feats):
    """Nearest nonmember controls under three predeclared caliper sets."""
    member_fids = {r["fid"] for r in member_rows}
    universe = [r for fid, r in feats.items() if fid not in member_fids]
    by_stratum = collections.defaultdict(list)
    for c in universe:
        year, league = int(c.get("year") or 0), str(c.get("league") or "")
        by_stratum[(year, league)].append(c)
    specs = {
        "tight": {"line": 0.125, "odds": 0.05, "fav_price": 0.08, "date_days": 30},
        "primary": {"line": 0.25, "odds": 0.10, "fav_price": 0.12, "date_days": 60},
        "broad": {"line": 0.50, "odds": 0.15, "fav_price": 0.18, "date_days": 120},
    }
    results, pair_rows = {}, []
    for spec, cal in specs.items():
        by_group = collections.defaultdict(list)
        for m in member_rows:
            if not m.get("direction") or not m.get("selected_odds"):
                continue
            cand = by_stratum.get((int(m.get("year") or 0), str(m.get("league") or "")), [])
            md = dt.date.fromisoformat(str(m["date"])[:10])
            best = None
            for c in cand:
                c_line = safe_float(c.get("end_line"))
                c_favorite = "home" if c_line < -1e-9 else "away" if c_line > 1e-9 else "level"
                if c_favorite != m["favorite_side"]:
                    continue
                cd = dt.date.fromisoformat(str(c["date"])[:10])
                dd = abs((cd - md).days)
                l = safe_float(c.get("end_line")) if m["direction"] == "home" else -safe_float(c.get("end_line"))
                o = safe_float(c.get("home_price")) if m["direction"] == "home" else safe_float(c.get("away_price"))
                favp = min(safe_float(c.get("home_price")), safe_float(c.get("away_price")))
                ld, od, fd = abs(l - m["selected_line"]), abs(o - m["selected_odds"]), abs(favp - min(m["odds_home"], m["odds_away"]))
                if dd > cal["date_days"] or ld > cal["line"] + 1e-9 or od > cal["odds"] + 1e-9 or fd > cal["fav_price"] + 1e-9:
                    continue
                # Same original side role and favorite/dog role, same year/league, local date.
                distance = ld / max(cal["line"], .001) + od / cal["odds"] + fd / cal["fav_price"] + dd / cal["date_days"]
                side_pnl = safe_float(c.get("end_home_U")) if m["direction"] == "home" else safe_float(c.get("end_away_U"))
                candrow = {"fid": str(c["fid"]), "pnl_u": side_pnl, "date": c["date"], "distance": distance}
                if best is None or distance < best["distance"]:
                    best = candrow
            if best:
                by_group[str(m["cohort"])].append((m, best))
                pair_rows.append({"spec": spec, "cohort": m["cohort"], "member_fid": m["fid"], "control_fid": best["fid"], "member_pnl_u": m["selected_pnl"], "control_same_side_pnl_u": best["pnl_u"], "distance": round(best["distance"], 6), "calipers": cal})
        results[spec] = {}
        for group, pairs in by_group.items():
            by_year = collections.defaultdict(list)
            for m, c in pairs:
                by_year[str(m.get("year"))].append((m, c))
            results[spec][group] = {
                "n_matched": len(pairs),
                "members": stats([dict(date=m["date"], pnl_u=m["selected_pnl"]) for m, _ in pairs]),
                "same_side_controls": stats([dict(date=m["date"], pnl_u=c["pnl_u"]) for m, c in pairs]),
                "member_minus_control_u": round(sum(m["selected_pnl"] - c["pnl_u"] for m, c in pairs), 6),
                "unique_control_fids": len({c["fid"] for _, c in pairs}),
                "by_year": {
                    year: {
                        "n": len(rows),
                        "member_u": round(sum(m["selected_pnl"] for m, _ in rows), 6),
                        "control_u": round(sum(c["pnl_u"] for _, c in rows), 6),
                        "member_minus_control_u": round(sum(m["selected_pnl"] - c["pnl_u"] for m, c in rows), 6),
                    }
                    for year, rows in sorted(by_year.items())
                },
            }
    # The pair file keeps only each method/spec row; it is intentionally not a trade list.
    return results, pair_rows


def ridge_forward(feats, frozen_fids, member_rows):
    """Direct expected AH payoff model; annual expanding forward, both sides then no-bet."""
    numeric = [
        "signed_line", "abs_line", "price", "opposite_price", "implied_prob", "vig_sum",
        "fav_side", "selected_is_fav", "selected_price_gap", "line_change_signed",
        "line_range", "line_changes", "quote_count", "final_line_minutes", "late_event_age_min",
        "last_line_change_age_min", "selected_price_move", "selected_water_vs_mean", "pstd",
        "p_range", "n_price_moves", "up_moves", "down_moves", "variation", "last_move",
        "fav_end_vs_start_signed", "fav_end_vs_max", "fav_end_vs_min", "fav_last_move_signed",
    ]
    examples = []
    for r in feats.values():
        if safe_float(r.get("home_price")) <= 1 or safe_float(r.get("away_price")) <= 1:
            continue
        year = int(r.get("year") or 0)
        for side in ("home", "away"):
            is_home = side == "home"
            price = safe_float(r.get("home_price" if is_home else "away_price"))
            opp = safe_float(r.get("away_price" if is_home else "home_price"))
            line = safe_float(r.get("end_line")) * (1 if is_home else -1)
            home_line = safe_float(r.get("end_line"))
            fav_is_home = home_line < -1e-9
            fav_side = "home" if home_line < -1e-9 else "away" if home_line > 1e-9 else "level"
            selected_is_fav = is_home == fav_is_home if fav_side != "level" else False
            x = {
                "signed_line": line, "abs_line": abs(line), "price": price, "opposite_price": opp,
                "implied_prob": 1 / price, "vig_sum": 1 / price + 1 / opp,
                "fav_side": 1.0 if fav_is_home else 0.0, "selected_is_fav": float(selected_is_fav),
                "selected_price_gap": price - opp,
                "line_change_signed": (safe_float(r.get("end_line")) - safe_float(r.get("start_line"))) * (1 if is_home else -1),
                "line_range": safe_float(r.get("line_range")), "line_changes": safe_float(r.get("n_line_changes")),
                "quote_count": safe_float(r.get("n_events")), "final_line_minutes": safe_float(r.get("final_line_minutes")),
                "late_event_age_min": safe_float(r.get("late_event_age_min")),
                "last_line_change_age_min": safe_float(r.get("last_line_change_age_min")),
                "selected_price_move": price - safe_float(r.get("start_home_price" if is_home else "start_away_price")),
                "selected_water_vs_mean": safe_float(r.get("home_price_vs_timeavg" if is_home else "away_price_vs_timeavg")),
                "pstd": safe_float(r.get("pstd")), "p_range": safe_float(r.get("pmax")) - safe_float(r.get("pmin")),
                "n_price_moves": safe_float(r.get("n_price_moves")), "up_moves": safe_float(r.get("up_moves")),
                "down_moves": safe_float(r.get("down_moves")), "variation": safe_float(r.get("variation")),
                "last_move": safe_float(r.get("last_move")),
                "fav_end_vs_start_signed": safe_float(r.get("fav_end_vs_start")) * (1 if (is_home == fav_is_home and fav_side != "level") else -1),
                "fav_end_vs_max": safe_float(r.get("fav_end_vs_max")), "fav_end_vs_min": safe_float(r.get("fav_end_vs_min")),
                "fav_last_move_signed": safe_float(r.get("fav_last_move")) * (1 if (is_home == fav_is_home and fav_side != "level") else -1),
            }
            y = safe_float(r.get("end_home_U" if is_home else "end_away_U"))
            examples.append({"fid": str(r["fid"]), "year": year, "date": r.get("date"), "league": str(r.get("league")), "side": side, "x": [x[k] for k in numeric], "y": y})
    predictions = []
    years = sorted({r["year"] for r in examples if r["year"] >= 2023})
    for target_year in years:
        train = [r for r in examples if r["year"] < target_year and r["year"] > 0]
        test_by_fid = collections.defaultdict(list)
        for r in examples:
            if r["year"] == target_year:
                test_by_fid[r["fid"]].append(r)
        if len(train) < 100:
            continue
        X = np.asarray([r["x"] for r in train], dtype=float)
        y = np.asarray([r["y"] for r in train], dtype=float)
        mu, sd = X.mean(axis=0), X.std(axis=0)
        sd[sd < 1e-8] = 1.0
        Xs = (X - mu) / sd
        ym = y.mean()
        xc = Xs - Xs.mean(axis=0)
        yc = y - ym
        alpha = 100.0  # fixed research regularization; not tuned on target-year outcomes
        beta = np.linalg.solve(xc.T @ xc + alpha * np.eye(xc.shape[1]), xc.T @ yc)
        intercept = ym - Xs.mean(axis=0) @ beta
        for fid, sides in test_by_fid.items():
            scored = []
            for r in sides:
                pred = float(((np.asarray(r["x"]) - mu) / sd) @ beta + intercept)
                scored.append((pred, r))
            pred, selected = max(scored, key=lambda z: z[0])
            action = selected["side"] if pred > 0 else None
            actual = selected["y"] if action else 0.0
            predictions.append({
                "fid": fid, "year": target_year, "date": selected["date"], "league": selected["league"],
                "pred_home_ev": round(next((p for p, r in scored if r["side"] == "home"), float("nan")), 8),
                "pred_away_ev": round(next((p for p, r in scored if r["side"] == "away"), float("nan")), 8),
                "selected_side": action, "predicted_ev": round(pred, 8), "pnl_u": round(actual, 6),
                "foundation_overlap": fid in frozen_fids,
                "incremental_pnl_u": 0.0 if fid in frozen_fids else round(actual, 6),
                "model": "expanding_year_ridge_direct_side_return_alpha100",
            })
    summary = {}
    for y in years:
        allrows = [r for r in predictions if r["year"] == y]
        selected = [r for r in allrows if r["selected_side"]]
        added = [r for r in selected if not r["foundation_overlap"]]
        foundation_y = [
            {"date": r["date"], "pnl_u": safe_float(r["pnl"])}
            for r in member_rows if int(r.get("year") or 0) == y
        ]
        merged_y = foundation_y + [{"date": r["date"], "pnl_u": safe_float(r["pnl_u"])} for r in added]
        summary[str(y)] = {
            "train_years": sorted({r["year"] for r in examples if r["year"] < y}),
            "test_fids": len(allrows), "selected_all": stats(selected), "selected_outside_foundation": stats(added),
            "merged_with_foundation": {
                **stats(merged_y),
                "foundation_fids": sum(1 for r in allrows if r["foundation_overlap"]),
                "new_fids": len(added),
                "new_net_u": round(sum(r["pnl_u"] for r in added), 6),
            },
        }
    return {"feature_names": numeric, "alpha": 100.0, "threshold": "predicted best-side return > 0; otherwise no bet (research only)", "annual": summary}, predictions


def receipt_audit():
    # Existing audited rows are used as result references; the database pass verifies
    # only post-archive live observations and does not substitute quote horizons.
    audited = list(read_jsonl(RECEIPT_AUDIT))
    audited_summary = {}
    by_method = collections.defaultdict(list)
    for r in audited:
        by_method[r.get("method")].append(r)
    for method, rows in by_method.items():
        audited_summary[method] = stats([{"date": r["date"], "pnl_u": r["pnl_u"]} for r in rows])

    cutoff = RECEIPT_CUTOFF
    con = sqlite3.connect(f"file:{CAPTURE_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    captures = con.execute(
        """SELECT c.fixture_id,c.capture_key,c.response_received_at_utc,c.source_file,c.response_sha256,
                  c.kickoff_at_utc,c.prospective_observation,c.status
           FROM capture c
           WHERE c.capture_mode='live' AND c.prospective_observation=1 AND c.response_received_at_utc>?
           ORDER BY c.response_received_at_utc""", (cutoff,)
    ).fetchall()
    quote_rows = con.execute(
        """SELECT c.fixture_id,c.capture_key,c.response_received_at_utc,c.source_file,c.response_sha256,
                  c.kickoff_at_utc,c.prospective_observation,c.status,q.sequence_index,q.quote_kind,
                  q.handicap_home,q.home_decimal,q.away_decimal,q.quote_source_at_utc
           FROM capture c LEFT JOIN asian_quote q ON q.capture_key=c.capture_key
           WHERE c.capture_mode='live' AND c.prospective_observation=1 AND c.response_received_at_utc>?
           ORDER BY c.response_received_at_utc,q.sequence_index""", (cutoff,)
    ).fetchall()
    found, hash_ok, prekick, raw_files = set(), 0, 0, 0
    for r in captures:
        found.add(str(r["fixture_id"]))
        p = Path(r["source_file"])
        if not p.is_absolute():
            p = CAPTURE_DB.parent / p
        if p.exists():
            raw_files += 1
            if sha256(p) == r["response_sha256"]:
                hash_ok += 1
        try:
            if r["kickoff_at_utc"] and r["response_received_at_utc"]:
                received = dt.datetime.fromisoformat(r["response_received_at_utc"].replace("Z", "+00:00"))
                kickoff = dt.datetime.fromisoformat(r["kickoff_at_utc"].replace("Z", "+00:00"))
                prekick += int(received < kickoff)
        except ValueError:
            pass
    con.close()
    rescored = json.load(DECOMPOSITION.open())
    receipt_matches = list(read_jsonl(RECEIPT_REPLAY))
    receipt_signals = [r for r in receipt_matches if r.get("cohort") and r.get("side") and r.get("pnl") is not None]
    receipt_by_group = {}
    for group in COHORTS:
        selected = [r for r in receipt_signals if r.get("cohort") == group]
        receipt_by_group[group] = stats([{"date": str(r["kickoff_utc"])[:10], "pnl_u": r["pnl"]} for r in selected])
    return {
        "archive_cutoff_utc": cutoff,
        "audited_actual_receipt_order_rows": len(audited),
        "audited_actual_receipt_by_method": audited_summary,
        "frozen_eight_true_receipt_replay": {
            "validated_unique_fids": len({str(r["fid"]) for r in receipt_matches}),
            "frozen_signals": len(receipt_signals),
            "signals_by_group": receipt_by_group,
            "all_signal_results": stats([{"date": str(r["kickoff_utc"])[:10], "pnl_u": r["pnl"]} for r in receipt_signals]),
            "interpretation": "Retrospective replay on real pregame Crown HTTP receipts; not a strategy locked at receipt time and not formal Telegram orders.",
        },
        "post_cutoff_live_capture_responses": len(captures),
        "post_cutoff_live_capture_quote_rows": len(quote_rows),
        "post_cutoff_live_capture_unique_fids": len(found),
        "post_cutoff_raw_files_found": raw_files,
        "post_cutoff_raw_sha_matches": hash_ok,
        "post_cutoff_received_before_current_kickoff_rows": prekick,
        "post_cutoff_unique_fids": sorted(found),
        "new_receipt_result_from_prior_audit": rescored.get("new_receipt_coverage", {}),
        "limitation": "Post-cutoff quote snapshots are separate from historical event replay. Existing A-L outcome design overlap and one rescheduled/unscorable FID are preserved; no substitute quote is used.",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    members = list(read_jsonl(MEMBERSHIP))
    feats = features_by_fid()
    scores = {str(r["fid"]): r for r in read_jsonl(SCORE_ROWS)}
    member_rows = build_member_rows(members, feats, scores)
    frozen_fids = {str(r["fid"]) for r in members}

    # Audit settlement implementation across the complete historical path table.
    settlement_audit = collections.Counter()
    for fid, f in feats.items():
        s = scores.get(fid)
        if (not s or s.get("hg") is None or s.get("ag") is None) and f.get("score_row"):
            s = f["score_row"]
        if not s or s.get("hg") is None or s.get("ag") is None:
            settlement_audit["missing_ft_or_identity_row"] += 1
            continue
        gd = int(s["hg"]) - int(s["ag"])
        for side in ("home", "away"):
            line = safe_float(f.get("end_line")) * (1 if side == "home" else -1)
            odds = safe_float(f.get("home_price" if side == "home" else "away_price"))
            ret, _ = settle(line, odds, gd if side == "home" else -gd)
            stored = safe_float(f.get("end_home_U" if side == "home" else "end_away_U"))
            settlement_audit["matched" if abs(ret - stored) < 1e-5 else "mismatch"] += 1

    annual_groups, group_overview, group_intersections = {}, {}, {}
    for cohort in COHORTS:
        rows = [r for r in member_rows if r.get("cohort") == cohort]
        group_overview[cohort] = {
            "all": stats(rows, "pnl"),
            "by_year": grouped_stats(rows, lambda r: r.get("year"), "pnl"),
            "frozen_rule_direction_status": collections.Counter(r["direction_status"] for r in rows),
            "frozen_rule_pnl_reproduction": collections.Counter(str(r.get("frozen_rule_pnl_reproduction")) for r in rows if r.get("direction")),
            "direction_performance_reconstructed_from_frozen_rule": stats([{"date":r["date"],"pnl_u":r["selected_pnl"]} for r in rows if r.get("direction")]),
            "by_abs_handicap": grouped_stats(rows, lambda r: market_bucket(r.get("line_home")), "pnl"),
            "by_selected_odds": grouped_stats([r for r in rows if r.get("selected_odds")], lambda r: price_bucket(r["selected_odds"]), "pnl"),
            "by_direction": grouped_stats([r for r in rows if r.get("direction")], lambda r: r["direction"], "pnl"),
            "by_vintage": grouped_stats(rows, lambda r: r.get("vintage", "unknown"), "pnl"),
            "settlement_states": collections.Counter(r.get("settlement_state_recomputed", "not_recomputed") for r in rows),
            "path_shape": grouped_stats(rows, lambda r: r.get("line_shape", "unknown"), "pnl"),
            "2026_weekly": {
                w: x for w, x in stats([r for r in rows if int(r.get("year") or 0) == 2026], "pnl")["weekly"].items()
            },
        }
    for a in COHORTS:
        for b in COHORTS:
            if a < b:
                fa = {r["fid"] for r in members if r.get("cohort") == a}
                fb = {r["fid"] for r in members if r.get("cohort") == b}
                group_intersections[f"{a}__{b}"] = len(fa & fb)

    # M1 feature/payoff controls and M3 virtual sides / entry-vintage counterfactuals.
    matched, matched_rows = matching_controls(member_rows, feats)
    reversals = {}
    for cohort in COHORTS:
        rows = [r for r in member_rows if r.get("cohort") == cohort and r.get("direction") and r.get("fid") in scores and r.get("fid") in feats]
        rev = [{"date": r["date"], "pnl_u": r["reverse_pnl"]} for r in rows]
        fav = [{"date": r["date"], "pnl_u": safe_float(feats[r["fid"]].get("end_fav_U", 0.0))} for r in rows if r["favorite_side"] != "level"]
        dog = [{"date": r["date"], "pnl_u": safe_float(feats[r["fid"]].get("end_dog_U", 0.0))} for r in rows if r["favorite_side"] != "level"]
        opening = []
        for r in rows:
            f, s = feats[r["fid"]], scores[r["fid"]]
            gd = int(s["hg"]) - int(s["ag"])
            home = r["direction"] == "home"
            line = safe_float(f.get("start_line")) * (1 if home else -1)
            odds = safe_float(f.get("start_home_price" if home else "start_away_price"))
            opening.append({"date": r["date"], "pnl_u": settle(line, odds, gd if home else -gd)[0]})
        reversals[cohort] = {
            "chosen_side": stats([{"date":r["date"],"pnl_u":r["selected_pnl"]} for r in rows]),
            "opposite_side_same_final_contract": stats(rev),
            "market_favorite_same_final_contract": stats(fav),
            "market_underdog_same_final_contract": stats(dog),
            "same_selected_side_at_open_line_and_price": stats(opening),
            "direction_identifiable_n": len(rows),
        }

    # M4/M7: time-forward direct-payoff model and its unique-FID incremental value.
    model, predictions = ridge_forward(feats, frozen_fids, member_rows)
    # M5/M6: source coverage week audit and real receipt lineage.
    coverage = collections.Counter()
    for r in feats.values():
        if r.get("date") and int(r.get("year") or 0) >= 2024:
            coverage[iso_week(r["date"])] += 1
    frozen_weekly = {w: x for w, x in group_overview["base"]["by_year"].get("2026", {}).items()} if False else {}
    week_source = {
        w: {"historical_path_fixture_rows": n, "frozen_foundation_signals": sum(1 for r in members if iso_week(r["date"]) == w)}
        for w, n in sorted(coverage.items()) if w.startswith("2026-")
    }
    for week in ("2026-W41", "2026-W42", "2026-W43", "2026-W44", "2026-W45", "2026-W46"):
        week_source.setdefault(week, {"historical_path_fixture_rows": 0, "frozen_foundation_signals": 0})
        week_source[week]["archive_cutoff_caveat"] = "historical membership snapshot ends 2026-11-03; a partial W45 and all W46 cannot be interpreted as full-week zero signal"

    receipts = receipt_audit()
    # Full file comparisons, including prior checks of 48 misbound quotes and 21 post-cutoff HTTP responses.
    decomp = json.load(DECOMPOSITION.open())
    mismatch = decomp.get("mismatch_audit_note", {})
    fresh = decomp.get("new_receipt_coverage", {})

    # Full per-game retained rows: frozen foundation mechanisms, direct payoff model, and matched controls.
    (OUT / "frozen_eight_fixture_mechanism_rows.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in member_rows)
    )
    (OUT / "direct_payoff_forward_predictions.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in predictions)
    )
    (OUT / "matched_control_pairs.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in matched_rows)
    )

    results = {
        "study": "M8 frozen eight mechanism attribution and independent Crown AH expansion, M1-M8",
        "research_only": True,
        "frozen_foundation": {"rows": len(members), "unique_fids": len(frozen_fids), "sha256": FOUNDATION_SHA,
                              "actual_local_sha256": sha256(MEMBERSHIP), "feature_join_rows": sum(r["fid"] in feats for r in member_rows),
                              "feature_join_missing": [r["fid"] for r in member_rows if r["fid"] not in feats],
                              "groups": group_overview, "group_overlap_fids": group_intersections},
        "quarter_line_settlement_audit": dict(settlement_audit),
        "M1_mechanism_decomposition": {
            "group_results": group_overview,
            "market_favorite_vs_underdog_and_path_placebos": reversals,
            "interpretation": "Eight-group direction is reconstructed from the archived frozen cohort definitions and pregame path fields, not inferred from realized PnL. The stored frozen PnL is independently checked against the reproduced side return. Any rule-return mismatch is retained and reported.",
        },
        "M2_matched_counterfactual": {"matching_specs": matched, "pair_file": "matched_control_pairs.jsonl", "method": "same year and league, same favorite role, same selected home/away role, local kickoff date, similar AH line and chosen decimal price; outcome is the same side's Crown return; nearest control with replacement", "caveat": "Historical matching is diagnostic and not a deployable prediction rule; repeated controls are disclosed."},
        "M3_natural_experiment_placebos": reversals,
        "M4_transferable_market_mechanism": model,
        "M5_data_coverage_and_quote_mismatch": {
            "historical_path_coverage_by_2026_iso_week": week_source,
            "receipt_archive_quote_mismatches": mismatch,
            "data_cutoff": "frozen historical membership through 2026-11-03; historic Crown path data cannot imply later full-week absence",
            "no_substitute_quote_used": True,
        },
        "M6_true_receipt_and_capacity_audit": receipts,
        "M7_independent_mechanism_exploration": {
            "candidate": "expanding-year ridge regression predicts each side's realized AH unit payoff from contemporaneous Crown AH price, line, quote-path and temporal-stability descriptors; select the higher predicted side only if its predicted payoff is positive, otherwise abstain",
            "forward_predictions_file": "direct_payoff_forward_predictions.jsonl",
            "hypothesis_novelty": "Different target from A-L directional scores/q80: direct side-specific settlement payoff, no future T1 group membership, results, or later quote fields. Some inputs are historical Crown path primitives already studied; no claim that every primitive is new.",
            "all_years_and_nonpositive_results_preserved": True,
        },
        "M8_unseen_receipt_replay": {
            "post_archive_unique_new_receipt_fids": fresh.get("captured_unique_fids"),
            "new_fids_absent_from_prior_A_L_scores": fresh.get("new_fids_absent_from_all_prior_A_L_scores"),
            "new_fids_with_model_and_verified_settlement": 0,
            "detail": "Previously scored FIDs are replays, not unseen outcome validation. The one absent FID in the prior audit was rescheduled and could not be aligned to a valid frozen model input and verified FT; it is not assigned a synthetic score or result.",
        },
        "execution": {
            "command": "python3 research/m8/m8_mechanism_discovery_20261119.py",
            "inputs": collect_inputs(),
            "private_raw_crown_quotes_published": False,
            "production_models_telegram_official_ledger_changed": False,
        },
    }
    (OUT / "M8_MECHANISM_DISCOVERY_RESULTS_20261119.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=lambda x: dict(x) if isinstance(x, collections.Counter) else str(x)))
    print(json.dumps({
        "output": str(OUT), "foundation_rows": len(members), "feature_rows": len(feats),
        "settlement_audit": dict(settlement_audit),
        "model_years": {y: {"n": r["selected_outside_foundation"]["n"], "u": r["selected_outside_foundation"]["net_u"], "roi_pct": r["selected_outside_foundation"]["roi_pct"]} for y, r in model["annual"].items()},
        "receipt_fids": fresh.get("captured_unique_fids"),
    }, indent=2, ensure_ascii=False, default=lambda x: dict(x) if isinstance(x, collections.Counter) else str(x)))


if __name__ == "__main__":
    main()
