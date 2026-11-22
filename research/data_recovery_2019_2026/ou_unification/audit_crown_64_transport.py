#!/usr/bin/env python3
"""Summarize combined Crown AH+OU transport attempts without touching SQLite."""
import argparse
import collections
import json
import statistics
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--log", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    rows = [json.loads(x) for x in Path(a.log).read_text().splitlines() if x.strip()]
    fixture_rows = [r for r in rows if r.get("match_id")]
    latest = {str(r["match_id"]): r for r in fixture_rows}
    attempts = [x for r in fixture_rows for x in r.get("request_attempts", [])]
    errors = [x for x in attempts if x.get("outcome") != "success"]
    retry_fids = collections.defaultdict(collections.Counter)
    for r in fixture_rows:
        for x in r.get("request_attempts", []):
            if x.get("outcome") != "success":
                retry_fids[str(r["match_id"])][str(x.get("error") or x.get("outcome"))] += 1
    payloads = collections.defaultdict(list)
    for fid, r in latest.items():
        for x in r.get("request_attempts", []):
            if x.get("outcome") == "success" and x.get("response_bytes") is not None:
                payloads[str(r.get("status"))].append(int(x["response_bytes"]))
    payload_summary = {}
    for status, values in payloads.items():
        payload_summary[status] = {
            "n_success_attempts": len(values),
            "median_bytes": statistics.median(values),
            "mean_bytes": round(statistics.mean(values), 3),
            "max_bytes": max(values),
        }
    result = {
        "log_records": len(rows),
        "unique_fids": len(latest),
        "latest_fixture_statuses": dict(collections.Counter(r.get("status") for r in latest.values())),
        "attempts": len(attempts),
        "attempt_outcomes": dict(collections.Counter(r.get("outcome") for r in attempts)),
        "attempt_errors": dict(collections.Counter(str(r.get("error") or r.get("outcome")) for r in errors)),
        "retry_error_fids": len(retry_fids),
        "recovered_after_error_fids": sum(any(x.get("outcome") == "success" for x in r.get("request_attempts", [])) for r in latest.values() if r.get("match_id") in retry_fids),
        "latest_retryable_failures": [
            {"fid": fid, "error": r.get("error"), "attempt_count": r.get("attempt_count")}
            for fid, r in sorted(latest.items()) if r.get("status") == "FETCH_FAILED"
        ],
        "successful_payload_sizes_by_latest_status": payload_summary,
        "partial_byte_diagnostics_present": sum("partial_bytes" in x for x in errors),
        "partial_byte_diagnostics_missing": sum("partial_bytes" not in x for x in errors),
    }
    Path(a.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
