#!/usr/bin/env python3
"""Same-fixture proper-score comparison of M5 goal model and strict M3 OOS rows."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, re, unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

LEAGUE_CODES = {
    "England Premier League": "E0", "Italy Serie A": "I1", "Spain La Liga": "SP1",
    "France Ligue 1": "F1", "Germany Bundesliga": "D1",
    "Belgium First Division A": "B1", "Belgium Jupiler Pro League": "B1",
}
MODELS = ("poisson", "dixon_coles", "bivariate_poisson")

def sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", text)

def score(probabilities, actual):
    p = [min(1-1e-12, max(1e-12, float(x))) for x in probabilities]
    return -math.log(p[actual]), sum((p[i] - (1.0 if i == actual else 0.0))**2 for i in range(len(p)))

def run(m3_csv: Path, m5_forecast_jsonl: Path, output: Path, kickoff_year: int | None = None):
    m3_raw=m3_csv.read_bytes(); m5_raw=m5_forecast_jsonl.read_bytes()
    m5={}
    for line in m5_raw.decode().splitlines():
        try:
            row=json.loads(line); league=LEAGUE_CODES.get(row["league"])
            if not league: continue
            if kickoff_year is not None and int(str(row["kickoff"])[:4]) != kickoff_year: continue
            key=(league,row["kickoff"][:10],norm(row["home"]),norm(row["away"]))
            if key in m5: m5.pop(key)
            else: m5[key]=row
        except Exception: continue
    m3=defaultdict(list)
    for row in csv.DictReader(m3_raw.decode().splitlines()):
        key=(row["league"],row["match_date_utc"][:10],norm(row["home_team"]),norm(row["away_team"]))
        m3[key].append(row)
    common=[]; collisions=0; missing=0
    for key, forecast in m5.items():
        records=m3.get(key,[])
        by_model={r.get("model"):r for r in records}
        if len(by_model)!=3 or any(model not in by_model for model in MODELS):
            continue
        if any(not by_model[m].get(f) for m in MODELS for f in ("p_home","p_draw","p_away","ou_p_over_2_5")):
            missing+=1; continue
        try: actual=(int(forecast["home_goals"]),int(forecast["away_goals"]))
        except Exception: continue
        if any((int(by_model[m]["actual_home_goals"]),int(by_model[m]["actual_away_goals"]))!=actual for m in MODELS):
            collisions+=1; continue
        common.append((forecast,by_model,actual))
    results={"AH_1X2_probability_proxy":{},"OU_O2_5":{}}
    models=list(MODELS)+["m5_independent_goal_rates"]
    for market in results:
        for model in models:
            ll=br=0.0
            for forecast, by_model, (home,away) in common:
                actual=0 if home>away else 1 if home==away else 2
                if model=="m5_independent_goal_rates":
                    grid=forecast["prediction"]["grid"]
                    p=[sum(grid[h][a] for h in range(15) for a in range(15) if h>a),
                       sum(grid[i][i] for i in range(15)),
                       sum(grid[h][a] for h in range(15) for a in range(15) if h<a)]
                    over=sum(grid[h][a] for h in range(15) for a in range(15) if h+a>2)
                else:
                    row=by_model[model]; p=[float(row["p_home"]),float(row["p_draw"]),float(row["p_away"])]
                    over=float(row["ou_p_over_2_5"])
                if market=="AH_1X2_probability_proxy": x,y=score(p,actual)
                else:
                    observed=int(home+away>2); over=min(1-1e-12,max(1e-12,over))
                    x=-(observed*math.log(over)+(1-observed)*math.log(1-over)); y=(over-observed)**2
                ll+=x; br+=y
            n=len(common)
            results[market][model]={"fixtures":n,"log_loss":round(ll/n,8) if n else None,"brier":round(br/n,8) if n else None}
    report={"protocol":"M5_PARTIAL_SCOPE_M3_STRICT_OOS_COMMON_FIXTURE_SCORE_V1",
            "generated_utc":datetime.now(timezone.utc).isoformat(),"m3_prediction_sha256":sha(m3_raw),
            "m5_private_forecast_sha256":sha(m5_raw),"m5_model_oos_fixtures_scored":len(m5),
            "m5_kickoff_year_filter":kickoff_year,
            "exact_common_fixture_count":len(common),"result_identity_conflicts_excluded":collisions,
            "incomplete_m3_score_rows_excluded":missing,"m3_models":list(MODELS),"scores":results,
            "roi":None,"crown_prices_used":False,
            "scope_note":"Only six M3-supported leagues and exact fixture/date/team joins; the M5 source schedule universe is partial. AH values are 1X2 three-way probability proxies, not Asian-contract settlement ROI. Proper-score comparison only; no Crown price."}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"common_fixtures":len(common),"scores":results,"output":str(output)}))

def main():
    p=argparse.ArgumentParser(); p.add_argument("--m3-csv",type=Path,required=True); p.add_argument("--m5-forecasts",type=Path,required=True); p.add_argument("--kickoff-year",type=int); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); run(a.m3_csv,a.m5_forecasts,a.output,a.kickoff_year)
if __name__=="__main__": main()
