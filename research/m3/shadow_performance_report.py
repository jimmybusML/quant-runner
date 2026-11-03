"""Read-only reconciliation of M3 shadow orders and settlement events."""
import argparse
import collections
import datetime
import json
from pathlib import Path

def summarize(path):
    orders = {}
    settled = {}
    counts = collections.Counter()
    with Path(path).open() as stream:
        for line in stream:
            if not line.strip():
                continue
            e = json.loads(line)
            protocol = e.get("protocol")
            counts[protocol] += 1
            if protocol == "M3_SHADOW_ORDER_V1":
                orders[e["event_id"]] = e
            elif protocol == "M3_TOTALCORNER_FORWARD_SETTLEMENT_V1":
                settled.setdefault(e.get("shadow_order_event_id"), []).append(e)
    # User-approved M3 order identity: one earliest actual shadow order per
    # fixture_id x model x AH/OU. Legacy duplicate events remain immutable.
    by_identity = {}
    for oid, order in orders.items():
        key = (str(order["fixture_identity_id"]), order["model"], order["market"])
        prior = by_identity.get(key)
        if prior is None or (str(order["forecasted_at_utc"]), oid) < (str(prior[1]["forecasted_at_utc"]), prior[0]):
            by_identity[key] = (oid, order)
    selected_orders = dict(by_identity.values())
    results = {}
    anomalies = []
    for model in ("poisson", "dixon_coles", "bivariate_poisson"):
        results[model] = {}
        for market in ("AH", "OU"):
            selection = [(oid, o) for oid, o in selected_orders.items() if o.get("model") == model and o.get("market") == market]
            states = collections.Counter()
            net = 0.0
            valid = 0
            for oid, order in selection:
                records = settled.get(oid, [])
                if not records:
                    continue
                if len(records) != 1:
                    anomalies.append({"order": oid, "reason": "duplicate settlement"})
                    continue
                record = records[0]
                if any(record.get(k) != order.get(k) for k in ("market", "side", "line")):
                    anomalies.append({"order": oid, "reason": "order/settlement mismatch"})
                    continue
                state = record.get("settlement_state")
                unit = record.get("hypothetical_unit_return")
                if state not in ("FULL_WIN", "HALF_WIN", "PUSH", "HALF_LOSS", "FULL_LOSS") or not isinstance(unit, (int, float)):
                    anomalies.append({"order": oid, "reason": "invalid result"})
                    continue
                valid += 1
                states[state] += 1
                net += unit
            results[model][market] = {
                "orders": len(selection), "settled": valid,
                "unsettled_or_invalid": len(selection) - valid,
                "full_win": states["FULL_WIN"], "half_win": states["HALF_WIN"],
                "push": states["PUSH"], "half_loss": states["HALF_LOSS"],
                "full_loss": states["FULL_LOSS"], "net_units": round(net, 6),
                "roi_percent": round(net * 100 / valid, 4) if valid else None
            }
    return {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "M3 SHADOW ONLY; NOT FORMAL TELEGRAM",
        "source": str(path), "event_counts": dict(counts),
        "order_identity": "fixture_identity_id × model × market; earliest forecasted_at_utc",
        "raw_shadow_order_events": len(orders),
        "unique_shadow_orders": len(selected_orders),
        "legacy_duplicate_order_events_excluded": len(orders) - len(selected_orders),
        "models": results, "anomalies": anomalies,
        "orphan_settlements": sum(len(v) for k, v in settled.items() if k not in orders)
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = summarize(args.ledger)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "REPORTED", "output": str(output),
                      "orders": result["event_counts"].get("M3_SHADOW_ORDER_V1", 0),
                      "settlements": result["event_counts"].get("M3_TOTALCORNER_FORWARD_SETTLEMENT_V1", 0),
                      "anomalies": len(result["anomalies"])}))

if __name__ == "__main__":
    main()
