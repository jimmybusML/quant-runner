"""Read-only full match-level evidence, preserving each model and each TG order.

Formal M1/MR1 rows come exclusively from actual Telegram SENT receipts.
Crown home/away prices are anchored to each saved source quote, NOT inferred
as live prices at Telegram send time. No score, line or opponent water is guessed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math
import re

BASE = Path(__file__).resolve().parent
R = BASE / "repos"
BJ = timezone(timedelta(hours=8))


def localtime(text):
    if not text:
        return None
    return datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(BJ)


def number(x):
    try:
        return float(x) if x is not None and math.isfinite(float(x)) else None
    except (ValueError, TypeError):
        return None


def status_result(state):
    return {
        "FULL_WIN": "全赢", "HALF_WIN": "半赢", "PUSH": "走水",
        "HALF_LOSS": "半输", "FULL_LOSS": "全输"
    }.get(state, "未结算")


def file_key(path):
    if not path.exists():
        return ("missing",)
    s = path.stat()
    return (s.st_mtime_ns, s.st_size)


def source_files(model):
    if model == "m1":
        return [R / "m1/results/m1_formal_ledger.json"]
    if model in ("mr1", "m4"):
        return [R / "mr1/data/mr1-v6-cross-market/formal/sent.jsonl",
                R / "mr1/data/mr1-v6-cross-market/formal/settled.json"]
    if model == "m3":
        return [R / "runner/research/m3/results/totalcorner/forward_ev_ledger.jsonl"]
    raise ValueError("未知模型")


def rows_for(model):
    return cache_rows(model, tuple(file_key(p) for p in source_files(model)))


@lru_cache(maxsize=12)
def cache_rows(model, file_signature):
    if model == "m1":
        return build_m1()
    if model == "mr1":
        return build_mr1()
    if model == "m3":
        return build_m3()
    if model == "m4":
        return build_m4()
    return []


def selected_row(m1, market):
    # Fallback team string from pick; normal M1 has home/away in 402 of 402.
    side = str(market.get("side", "")).upper()
    return ("主队" if side == "HOME" else "客队" if side == "AWAY" else "未知")


@lru_cache(maxsize=1)
def chinese_names():
    file = R / "m1/data/football_display_names/display_names.json"
    doc = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    maps = {}
    for typ in ("teams", "competitions"):
        translated = {}
        ambiguous = set()
        for item in (doc.get(typ) or {}).values():
            name = str(item.get("provider_name") or "").strip().casefold()
            target = item.get("canonical_zh") if item.get("status") == "CANONICAL" else None
            if not name or not target:
                continue
            if name in translated and translated[name] != target:
                ambiguous.add(name)
            translated[name] = target
        for name in ambiguous:
            translated.pop(name, None)
        overrides = (doc.get("name_overrides") or {}).get(typ) or {}
        for original, translated_name in overrides.items():
            if original.casefold() not in ambiguous and translated_name:
                translated.setdefault(original.casefold(), translated_name)
        maps[typ] = translated
    return maps


def translated(name, typ):
    if not name:
        return name
    return chinese_names()[typ].get(str(name).strip().casefold()) or name


def display_m1(pick):
    return (translated(pick.get("competition"), "competitions"),
            translated(pick.get("home"), "teams"), translated(pick.get("away"), "teams"))


def display_mr1(order):
    # Exact text actually sent to TG contains the user's existing Chinese names.
    # Use it as-is, never machine-translate or guess uncertain team identities.
    raw = order.get("text") or ""
    matched = re.match(r"^【MR1】\S+\s+\S+\s+(\S+)\s+(.+?)\s+vs\s+(.+?)\s+全场让球\b", raw)
    if matched:
        return matched.group(1), matched.group(2), matched.group(3)
    return (translated(order.get("league"), "competitions"), translated(order.get("home"), "teams"), translated(order.get("away"), "teams"))


def build_m1():
    ledger = json.loads(source_files("m1")[0].read_text(encoding="utf-8"))
    rows = []
    for key, pick in ledger.get("picks", {}).items():
        if pick.get("market") != "AH":
            continue
        tg = ledger.get("notifications", {}).get(key, {}).get("telegram", {})
        if tg.get("status") != "SENT" or not tg.get("provider_message_id"):
            continue
        evidence = pick.get("market_evidence") or {}
        path = evidence.get("market_path") or []
        quote = path[-1] if path else {}
        side = str(evidence.get("side", "")).upper()
        if side not in ("HOME", "AWAY"):
            side = "HOME" if pick.get("selection") == pick.get("home") else "AWAY"
        home_line = number(quote.get("line"))
        chosen = number(pick.get("price"))
        chosen_from_quote = number(quote.get("p1" if side == "HOME" else "p2"))
        match_price = chosen is not None and chosen_from_quote is not None and abs(chosen - chosen_from_quote) < 1e-6
        settlement = ledger.get("settlements", {}).get(key) or []
        finish = settlement[-1] if settlement else None
        verified = pick.get("bookmaker") == "crown" and pick.get("bookmaker_source_verified") is True
        fullpath = []
        for p in path:
            fullpath.append({
                "at": p.get("observed_at"), "home_line": number(p.get("line")),
                "away_line": -number(p["line"]) if number(p.get("line")) is not None else None,
                "home_price": number(p.get("p1")), "away_price": number(p.get("p2")),
                "home_hk": number(p.get("hk1")), "away_hk": number(p.get("hk2"))
            })
        league_zh, home_zh, away_zh = display_m1(pick)
        rows.append({
            "league_zh": league_zh, "home_zh": home_zh, "away_zh": away_zh,
            "id": str(pick["pick_id"]), "fixture": str(pick["fixture_id"]), "model": "m1",
            "league": pick.get("competition") or "联赛未记录", "home": pick.get("home") or "主队未记录",
            "away": pick.get("away") or "客队未记录",
            "posted_at": tg.get("sent_at"), "kickoff": pick.get("kickoff"),
            "quote_at": quote.get("observed_at") or pick.get("source_observation"),
            "market": "AH", "bookmaker": "Crown（有来源验证）" if verified else "旧账本未验证盘口来源",
            "bookmaker_verified": verified,
            "home_line": home_line,
            "away_line": -home_line if home_line is not None else None,
            "home_price": number(quote.get("p1")), "away_price": number(quote.get("p2")),
            "home_hk": number(quote.get("hk1")), "away_hk": number(quote.get("hk2")),
            "selection": pick.get("selection"), "direction": "主队" if side == "HOME" else "客队",
            "selection_line": number(pick.get("line")), "selection_price": chosen,
            "selection_hk": number(pick.get("price_hk")) if pick.get("price_hk") is not None else (chosen-1 if chosen else None),
            "quote_matches_selection": match_price, "ev": number(evidence.get("ev")),
            "result": {"home": finish.get("home_goals"), "away": finish.get("away_goals")} if finish else None,
            "settlement": status_result(finish.get("state") if finish else None),
            "pnl": number(finish.get("pnl_u")) if finish else None,
            "tg_sent": True, "tg_message_id": str(tg["provider_message_id"]),
            "source": "M1 原始发单证据 + 双边赔率路径",
            "quote_path": fullpath,
            "notes": ["报价时间是记录的盘口快照时间，不等于 TG 实际发送时间。"]
                     + ([] if verified else ["这笔历史订单未保存皇冠来源验证，不能冒称其为 Crown 盘口。"]),
            "raw_text": tg.get("raw_line")
        })
    return rows


def read_snapshot(order):
    root = R / "mr1/data/prospective-market/shadow-v23/snapshots"
    path = root / (str(order.get("source_snapshot_key", "")) + "/snapshot.json")
    if not path.exists():
        return None, "这笔订单的原始盘口快照不在本机。"
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != order.get("source_snapshot_sha256"):
        return None, "原始盘口快照校验不一致，本次不展示未经核实的盘口。"
    obj = json.loads(raw)
    if str(obj.get("match_id")) != str(order.get("match_id")):
        return None, "原始盘口快照的比赛身份不一致。"
    if obj.get("source_bookmaker") != "crown" or obj.get("source_bookmaker_verified") is not True:
        return None, "盘口快照没有皇冠来源验证。"
    return obj, None


def build_mr1():
    sent_path, settled_path = source_files("mr1")
    settled = json.loads(settled_path.read_text(encoding="utf-8")).get("entries", {})
    rows = []
    with sent_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            order = json.loads(line)
            if not order.get("telegram_message_id") or not order.get("sent_at"):
                continue
            snapshot, warning = read_snapshot(order)
            ah = (snapshot or {}).get("AH") or {}
            home_line = number(ah.get("line"))
            side = str(order.get("direction", "")).lower()
            chosen = number(order.get("price"))
            quoted = number(ah.get("home_price" if side == "home" else "away_price"))
            settlement = settled.get(order["signal_id"])
            league_zh, home_zh, away_zh = display_mr1(order)
            rows.append({
                "league_zh": league_zh, "home_zh": home_zh, "away_zh": away_zh,
                "id": str(order["signal_id"]), "fixture": str(order["match_id"]), "model": "mr1",
                "league": order.get("league") or "联赛未记录", "home": order.get("home") or "主队未记录",
                "away": order.get("away") or "客队未记录",
                "posted_at": order.get("sent_at"), "kickoff": order.get("kickoff_at"),
                "quote_at": ah.get("observed_at_utc"), "quote_received_at": (snapshot or {}).get("received_at"),
                "market": "AH", "bookmaker": "Crown（已核实）" if snapshot else "盘口快照未核实",
                "bookmaker_verified": bool(snapshot), "home_line": home_line,
                "away_line": -home_line if home_line is not None else None,
                "home_price": number(ah.get("home_price")), "away_price": number(ah.get("away_price")),
                "home_hk": number(ah["home_price"])-1 if ah.get("home_price") is not None else None,
                "away_hk": number(ah["away_price"])-1 if ah.get("away_price") is not None else None,
                "selection": order.get("home") if side == "home" else order.get("away"),
                "direction": "主队" if side == "home" else "客队",
                "selection_line": number(order.get("line")), "selection_price": chosen,
                "selection_hk": (chosen-1 if chosen is not None else None),
                "quote_matches_selection": bool(snapshot) and chosen is not None and quoted is not None and abs(chosen-quoted)<1e-6,
                "ev": number(order.get("EV")),
                "result": {"home": settlement.get("home_goals"), "away": settlement.get("away_goals")} if settlement else None,
                "settlement": status_result(settlement.get("settlement") if settlement else None),
                "pnl": number(settlement.get("realized_pnl")) if settlement else None,
                "tg_sent": True, "tg_message_id": str(order["telegram_message_id"]),
                "source": "MR1 正式 TG 订单 + 原始 Crown 快照",
                "notes": ["这里展示原始盘口报价时间，与 TG 发单时间分别记录。"] + ([warning] if warning else []),
                "source_snapshot_key": order.get("source_snapshot_key"),
                "raw_text": order.get("text")
            })
    return rows


def build_m3():
    # The shadow forecast file is large. Only parse when M3 is selected in UI.
    source = source_files("m3")[0]
    earliest = {}
    settlement = {}
    leagues = {}
    with source.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            proto = e.get("protocol")
            if proto == "M3_SHADOW_ORDER_V1":
                key = (str(e.get("fixture_identity_id")), e.get("model"), e.get("market"))
                other = earliest.get(key)
                if other is None or (str(e.get("forecasted_at_utc")), e["event_id"]) < (str(other.get("forecasted_at_utc")), other["event_id"]):
                    earliest[key] = e
            elif proto == "M3_TOTALCORNER_FORWARD_SETTLEMENT_V1" and e.get("shadow_order_event_id"):
                settlement.setdefault(str(e["shadow_order_event_id"]), []).append(e)
            elif proto == "M3_TOTALCORNER_FUTURE_INVENTORY_V1" and e.get("league_source"):
                fixture = str(e.get("totalcorner_match_id"))
                leagues[(fixture, e.get("home_source"), e.get("away_source"))] = e["league_source"]
    model_names = {"poisson": "泊松", "dixon_coles": "迪克森-科尔斯", "bivariate_poisson": "双变量泊松"}
    rows = []
    for order in earliest.values():
        matches = settlement.get(order["event_id"], [])
        matches = [x for x in matches if x.get("market") == order.get("market") and
                   x.get("side") == order.get("side") and number(x.get("line")) == number(order.get("line"))]
        # Original M3 report uses one unique matching settlement; don't count ambiguity as success.
        match = matches[0] if len(matches) == 1 else None
        side = str(order.get("side", "")).lower()
        market = order.get("market")
        selected_price = number(order.get("decimal_odd"))
        selection = {
            "home": order.get("home_team"), "away": order.get("away_team"),
            "over": "大球", "under": "小球"
        }.get(side, side)
        m3_league = leagues.get((str(order.get("totalcorner_match_id")), order.get("home_team"), order.get("away_team")), "联赛未记录")
        rows.append({
            "league_zh": translated(m3_league, "competitions"),
            "home_zh": translated(order.get("home_team"), "teams"),
            "away_zh": translated(order.get("away_team"), "teams"),
            "id": str(order["event_id"]), "fixture": str(order.get("totalcorner_match_id") or order.get("fixture_identity_id")),
            "model": "m3", "submodel": model_names.get(order.get("model"), order.get("model")),
            "league": leagues.get((str(order.get("totalcorner_match_id")), order.get("home_team"), order.get("away_team")), "联赛未记录"), "home": order.get("home_team") or "主队未记录",
            "away": order.get("away_team") or "客队未记录",
            "posted_at": order.get("forecasted_at_utc"), "kickoff": order.get("kickoff_utc_verified"),
            "quote_at": order.get("quote_snapshot_recorded_utc"), "market": market,
            "bookmaker": "TotalCorner 默认盘口（非 Crown）", "bookmaker_verified": False,
            "home_line": None, "away_line": None, "home_price": None, "away_price": None,
            "home_hk": None, "away_hk": None,
            "selection": selection,
            "direction": {"home": "主队", "away": "客队", "over": "大球", "under": "小球"}.get(side, side),
            "selection_line": number(order.get("line")), "selection_price": selected_price,
            "selection_hk": selected_price-1 if selected_price is not None else None,
            "quote_matches_selection": None, "ev": number(order.get("expected_unit_return")),
            "result": {"home": match.get("home_goals"), "away": match.get("away_goals")} if match else None,
            "settlement": status_result(match.get("settlement_state") if match else None),
            "pnl": number(match.get("hypothetical_unit_return")) if match else None,
            "tg_sent": False, "tg_message_id": None,
            "source": "M3 原始影子预测与赛果证据",
            "notes": ["该研究订单仅保存选中方向的水位，未保存完整双边报价，不能推算对面水位。",
                      "M3 当前使用 TotalCorner 默认盘口，不是皇冠盘口，属于影子研究。"]
        })
    return rows


def build_m4():
    # M4 has NO independent prospective order ledger. The display is an
    # explicit counterfactual over existing MR1 TG history, not M4 orders.
    study = BASE / "state/m4_latest.json"
    doc = json.loads(study.read_text(encoding="utf-8")) if study.exists() else {}
    skip = set(doc.get("study_leagues", []))
    out = []
    for mr in rows_for("mr1"):
        r = dict(mr)
        r["id"] = "m4-study:" + mr["id"]
        r["model"] = "m4"
        r["m4_action"] = "研究假设：跳过" if r["league"] in skip else "研究假设：保留"
        r["m4_reference"] = "MR1 原始正式订单，M4 没有独立下单"
        r["source"] = "M4 研究引用 MR1 已有皇冠报价"
        r["notes"] = list(r.get("notes") or []) + ["本条仅重放 MR1 历史订单并展示 M4 假设，不是 M4 发出的订单。"]
        # Show original MR1 outcome separately, with hypothetical P&L for M4.
        r["mr1_original_pnl"] = mr["pnl"]
        r["mr1_original_settlement"] = mr["settlement"]
        r["pnl"] = 0 if r["league"] in skip and mr["pnl"] is not None else mr["pnl"]
        out.append(r)
    return out


def detail_path(row):
    if row["model"] != "mr1" and row["model"] != "m4":
        return row
    # Find other saved market horizons for exactly this match, only validated Crown.
    origin = R / "mr1/data/prospective-market/shadow-v23/snapshots" / row["fixture"]
    history = []
    if origin.is_dir():
        for path in origin.glob("*/snapshot.json"):
            try:
                snap = json.loads(path.read_text(encoding="utf-8"))
                if str(snap.get("match_id")) != row["fixture"] or snap.get("source_bookmaker") != "crown" or snap.get("source_bookmaker_verified") is not True:
                    continue
                ah = snap.get("AH") or {}
                h = number(ah.get("home_price"))
                a = number(ah.get("away_price"))
                line = number(ah.get("line"))
                if not ah.get("observed_at_utc") or h is None or a is None:
                    continue
                history.append({"at": ah["observed_at_utc"], "home_line": line,
                                "away_line": -line if line is not None else None,
                                "home_price": h, "away_price": a, "home_hk": h-1, "away_hk": a-1})
            except (OSError, ValueError):
                pass
    row = dict(row)
    row["quote_path"] = sorted(history, key=lambda x: x.get("at") or "")
    return row


def filter_and_page(model, scope="all", query="", result="all", page=1, size=40):
    if model not in ("m1", "mr1", "m3", "m4"):
        raise ValueError("未知模型")
    current = rows_for(model)
    now = datetime.now(BJ)
    monday = (now - timedelta(days=now.weekday())).date()
    q = query.strip().casefold()
    filtered = []
    for x in current:
        t = localtime(x["posted_at"])
        if scope in ("this", "last"):
            if t is None:
                continue
            week = t.date()
            if scope == "this" and not monday <= week < monday+timedelta(days=7):
                continue
            if scope == "last" and not monday-timedelta(days=7) <= week < monday:
                continue
        if result == "settled" and x["pnl"] is None:
            continue
        if result == "pending" and x["pnl"] is not None:
            continue
        if result == "loss" and not (x["pnl"] is not None and x["pnl"] < 0):
            continue
        if result == "win" and not (x["pnl"] is not None and x["pnl"] > 0):
            continue
        if q and not any(q in str(x.get(k) or "").casefold() for k in
                         ("league", "home", "away", "league_zh", "home_zh", "away_zh", "fixture", "selection", "direction", "submodel", "id")):
            continue
        filtered.append(x)
    filtered.sort(key=lambda x: (x.get("posted_at") or "", x["id"]), reverse=True)
    n = len(filtered)
    page = max(1, int(page))
    size = max(1, int(size))
    offset = (page-1)*size
    match_counts = {}
    for x in filtered:
        match_counts[x["fixture"]] = match_counts.get(x["fixture"], 0)+1
    data = []
    for x in filtered[offset:offset+size]:
        item = {k:v for k,v in x.items() if k not in ("quote_path", "notes", "raw_text")}
        item["same_game_orders"] = match_counts.get(x["fixture"], 1)
        data.append(item)
    settled = [x for x in filtered if x["pnl"] is not None]
    return {
        "model": model, "total": n, "page": page, "size": size,
        "pages": max(1, math.ceil(n/size)),
        "rows": data, "settled": len(settled), "pending": n-len(settled),
        "net": round(sum(x["pnl"] for x in settled), 4),
        "with_both_prices": sum(1 for x in filtered if x.get("home_hk") is not None and x.get("away_hk") is not None),
        "verified_crown": sum(1 for x in filtered if x.get("bookmaker_verified")),
        "note": "M4 是 MR1 历史订单的研究假设，不代表 M4 已真实下注。" if model == "m4" else None
    }


def get_one(model, ident):
    all_rows = rows_for(model)
    for item in all_rows:
        if item["id"] == ident:
            result = detail_path(item)
            shared = [x for x in all_rows if x["fixture"] == item["fixture"]]
            result["same_match_orders"] = sorted([{
                "id": x["id"], "posted_at": x["posted_at"],
                "direction": x["direction"], "selection_line": x["selection_line"],
                "selection_hk": x["selection_hk"], "settlement": x["settlement"],
                "pnl": x["pnl"], "submodel": x.get("submodel"),
                "market": x["market"], "m4_action": x.get("m4_action")
            } for x in shared], key=lambda x: (x.get("posted_at") or "", x["id"]))
            return result
    return None
