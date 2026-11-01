"""Independent research-only M3 AH reverse-side audit. No production decisions or TG."""
import argparse, collections, json
from pathlib import Path
from research.m3.probabilities import settle_score

def audit(events):
    all_orders = [e for e in events if e.get("protocol") == "M3_SHADOW_ORDER_V1" and e.get("market") == "AH"]
    # One shadow order per fixture × model × market, regardless of scan/run.
    earliest = {}
    for order in all_orders:
        key = (order.get("fixture_identity_id"), order.get("model"), order.get("market"))
        rank = (order.get("forecasted_at_utc") or "", order.get("event_id") or "")
        if key not in earliest or rank < (
            earliest[key].get("forecasted_at_utc") or "",
            earliest[key].get("event_id") or "",
        ):
            earliest[key] = order
    orders = list(earliest.values())
    settlements = {e.get("shadow_order_event_id"): e for e in events if e.get("protocol") == "M3_TOTALCORNER_FORWARD_SETTLEMENT_V1"}
    quotes = collections.defaultdict(list)
    for e in events:
        if e.get("protocol") == "M3_TOTALCORNER_FORWARD_EV_V1" and e.get("market") == "AH":
            key = (e.get("forecast_id"), e.get("quote_snapshot_recorded_utc"), e.get("line"), e.get("side"))
            quotes[key].append(e)
    totals = collections.defaultdict(lambda: collections.Counter())
    exclusions = collections.Counter()
    unique = set()
    for o in orders:
        group = totals[o.get("model", "UNKNOWN")]
        group["orders"] += 1
        result = settlements.get(o["event_id"])
        if result is None:
            continue
        group["settled"] += 1
        reverse_side = "away" if o.get("side") == "home" else "home"
        key = (o.get("forecast_id"), o.get("quote_snapshot_recorded_utc"), o.get("line"), reverse_side)
        found = [q for q in quotes[key] if q.get("bookmaker") == "totalcorner_default_NOT_CROWN"]
        if len(found) != 1:
            exclusions["reverse_quote_missing_or_ambiguous"] += 1
            continue
        price = found[0].get("decimal_odd")
        if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 1:
            exclusions["invalid_reverse_price"] += 1
            continue
        try:
            state, pnl = settle_score("AH", o["line"], reverse_side, result["home_goals"], result["away_goals"], price)
        except (ValueError, KeyError, TypeError):
            exclusions["invalid_settlement"] += 1
            continue
        group["paired"] += 1
        group["reverse_units"] += pnl
        group["original_units"] += result["hypothetical_unit_return"]
        group["reverse_" + state.lower()] += 1
        unique.add((o.get("totalcorner_match_id"), o.get("quote_snapshot_recorded_utc"), o.get("line"), o.get("side")))
    result = {"protocol": "M3_AH_REVERSE_RESEARCH_AUDIT_V1", "research_only": True,
              "formal_order": False, "telegram_sent": False, "quote_source": "TotalCorner default, NOT Crown",
              "models": {}, "distinct_quote_decisions": len(unique), "exclusions": dict(exclusions),
              "raw_ah_order_events": len(all_orders), "unique_ah_orders": len(orders),
              "duplicates_excluded": len(all_orders) - len(orders),
              "dedup_key": "fixture_identity_id × model × market; earliest forecasted_at_utc"}
    for model, counter in sorted(totals.items()):
        v = dict(counter)
        v["reverse_roi_percent"] = round(100 * v["reverse_units"] / v["paired"], 4) if v.get("paired") else None
        v["original_roi_percent_paired"] = round(100 * v["original_units"] / v["paired"], 4) if v.get("paired") else None
        result["models"][model] = v
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    events = [json.loads(line) for line in args.ledger.open() if line.strip()]
    result = audit(events)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
