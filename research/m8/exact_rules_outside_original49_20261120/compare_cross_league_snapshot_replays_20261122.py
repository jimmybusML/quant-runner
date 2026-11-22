#!/usr/bin/env python3
"""Compare the current replay with the last published snapshot without refitting."""
import gzip, json, pathlib, subprocess

HERE = pathlib.Path(__file__).resolve().parent
PREVIOUS_COMMIT = "37328888"
DB_SHA256 = "28e0f1aa4ed69205c8933950f270c1805e831d9314d22622191fb5029d44592a"
PATHS = "exact_rule_cross_league_all_complete_paths.jsonl.gz"
ORDERS = "exact_rule_cross_league_orders.jsonl.gz"


def previous_rows(name):
    blob = subprocess.check_output([
        "git", "show", f"{PREVIOUS_COMMIT}:research/m8/exact_rules_outside_original49_20261120/{name}"
    ])
    return [json.loads(row) for row in gzip.decompress(blob).splitlines() if row]


def current_rows(name):
    with gzip.open(HERE / name, "rt", encoding="utf-8") as stream:
        return [json.loads(row) for row in stream if row.strip()]


def main():
    old_paths = {r["fid"]: r for r in previous_rows(PATHS)}
    old_orders = {r["fid"]: r for r in previous_rows(ORDERS)}
    new_paths = {r["fid"]: r for r in current_rows(PATHS)}
    new_orders = {r["fid"]: r for r in current_rows(ORDERS)}

    common_path_ids = set(old_paths) & set(new_paths)
    path_fields = ("start_line", "mid_line", "end_line", "p0", "p3", "p1", "path_6_3_1", "path_shape")
    changed_path_ids = [fid for fid in common_path_ids if any(old_paths[fid].get(k) != new_paths[fid].get(k) for k in path_fields)]
    common_order_ids = set(old_orders) & set(new_orders)
    order_fields = ("group", "side", "end_line", "price", "net_u", "settlement")
    changed_order_ids = [fid for fid in common_order_ids if any(old_orders[fid].get(k) != new_orders[fid].get(k) for k in order_fields)]
    old_u = sum(float(r["net_u"]) for r in old_orders.values())
    new_u = sum(float(r["net_u"]) for r in new_orders.values())
    new_ids = set(new_orders) - set(old_orders)
    out = {
        "comparison": "prior committed history replay vs fixed SQLite online-backup snapshot replay",
        "previous_commit": PREVIOUS_COMMIT,
        "current_sqlite_snapshot_sha256": DB_SHA256,
        "complete_paths": {
            "previous": len(old_paths), "current": len(new_paths),
            "new_fids": len(set(new_paths) - set(old_paths)),
            "missing_fids": len(set(old_paths) - set(new_paths)),
            "common_fids": len(common_path_ids),
            "common_paths_with_changed_T6_T3_T1_or_rule_features": len(changed_path_ids),
        },
        "orders": {
            "previous": len(old_orders), "current": len(new_orders),
            "new_order_fids": len(new_ids), "removed_order_fids": len(set(old_orders) - set(new_orders)),
            "common_order_fids": len(common_order_ids), "common_orders_with_changed_group_side_contract_or_pnl": len(changed_order_ids),
            "previous_net_u": round(old_u, 6), "current_net_u": round(new_u, 6),
            "net_u_delta": round(new_u - old_u, 6),
            "new_order_net_u": round(sum(float(new_orders[fid]["net_u"]) for fid in new_ids), 6),
            "changed_common_order_net_u_delta": round(sum(float(new_orders[fid]["net_u"]) - float(old_orders[fid]["net_u"]) for fid in common_order_ids), 6),
        },
        "method_note": "Prior outputs were read from the prior Git tree. Current outputs were computed from the fixed SQLite online-backup snapshot. The new coverage is a data-availability change, not a rule or parameter change.",
    }
    (HERE / "snapshot_delta_audit_20261122.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
