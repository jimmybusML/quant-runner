#!/usr/bin/env python3
"""Count exact M1 Crown OU to M3 OOS fixture joins without exposing private IDs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

LEAGUE_CODE = {
    "England Premier League": "E0",
    "Germany Bundesliga I": "D1",
    "France Ligue 1": "F1",
    "Italy Serie A": "I1",
    "Spain La Liga": "SP1",
    "Belgium First Division A": "B1",
}
MODELS = {"poisson", "dixon_coles", "bivariate_poisson"}


def normalize_team(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", value)


def run(observations: Path, summary: Path, m3_csv: Path) -> dict:
    obs = [json.loads(x) for x in observations.read_text().splitlines() if x.strip()]
    settled_ids = {str(x["fixture_id"]) for x in json.loads(summary.read_text()).get("per_fixture_outcome_rows", [])}
    m1 = [x for x in obs if x.get("status") == "LOCKED_ELIGIBLE" and str(x.get("fixture_id")) in settled_ids]
    m1_keys = defaultdict(set)
    for x in m1:
        league = LEAGUE_CODE.get(str(x.get("competition")))
        if league:
            key = (league, str(x.get("kickoff_calendar_day_utc")), normalize_team(x.get("home")), normalize_team(x.get("away")))
            m1_keys[key].add(str(x.get("fixture_id")))
    m3_rows = defaultdict(Counter)
    with m3_csv.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (str(r.get("league")), str(r.get("match_date_utc", ""))[:10],
                   normalize_team(r.get("home_team")), normalize_team(r.get("away_team")))
            if r.get("p_home"):
                m3_rows[key][str(r.get("model"))] += 1
    m3 = {key: {model for model, count in values.items() if count == 1}
          for key, values in m3_rows.items() if all(count == 1 for count in values.values())}
    collisions_m1 = sum(len(v) != 1 for v in m1_keys.values())
    collisions_m3 = sum(any(count > 1 for count in values.values()) for values in m3_rows.values())
    common = [k for k in m1_keys.keys() & m3.keys() if len(m1_keys[k]) == 1 and m3[k] == MODELS]
    return {
        "protocol": "M5_M1_M3_EXACT_COMPOSITE_JOIN_AUDIT_V1",
        "inputs_sha256": {
            "m1_observations": hashlib.sha256(observations.read_bytes()).hexdigest(),
            "m1_settled_summary": hashlib.sha256(summary.read_bytes()).hexdigest(),
            "m3_oos_csv": hashlib.sha256(m3_csv.read_bytes()).hexdigest(),
        },
        "m1_eligible_settled_unique_fixtures": len({str(x.get("fixture_id")) for x in m1}),
        "m3_common_scored_unique_fixtures": sum(v == MODELS for v in m3.values()),
        "exact_join_key": ["league_code", "UTC_calendar_date", "normalized_home_team", "normalized_away_team"],
        "m1_key_collisions": collisions_m1,
        "m3_key_collisions": collisions_m3,
        "m1_m3_exact_common_fixtures_with_all_three_m3_predictions": len(common),
        "price_source": "M1 archived Crown quotes only; this join audit itself computes no PnL.",
        "raw_fixture_ids_or_names_published": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--observations", type=Path, required=True)
    p.add_argument("--summary", type=Path, required=True)
    p.add_argument("--m3-csv", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    report = run(a.observations, a.summary, a.m3_csv)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
