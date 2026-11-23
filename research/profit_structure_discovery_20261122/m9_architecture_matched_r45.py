#!/usr/bin/env python3
"""R45 read-only matched-fixture predictive scoring: M5 annual vs pre-existing bivariate and recency variants.
The bivariate archive is NOT the production M9 runner, and no Crown ROI is claimed."""
import collections,json,math,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=Path("/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/m5-model-oos")
SOURCES={"m5_annual":ROOT/"m5_goal_model_forecasts.jsonl",
"bivariate_archive":ROOT/"m5_goal_model_baseline_matched_penaltyblog_bivariate_2025_2026.jsonl",
"recency_archive":ROOT/"m5_goal_model_baseline_matched_recency_2025_2026.jsonl"}
raw=collections.defaultdict(dict);seen=collections.Counter();errors=collections.Counter()
for model,path in SOURCES.items():
 for line in path.open():
  a=json.loads(line);year=str(a.get("year"))
  if year not in ("2025","2026"):continue
  seen[model]+=1
  key=(str(a["match_id"]),year)
  if key in raw[model]:errors[model+"_duplicate"]+=1;continue
  g=a.get("prediction",{}).get("grid")
  if not g or len(g)<3:errors[model+"_no_grid"]+=1;continue
  h=int(a["home_goals"]);aw=int(a["away_goals"])
  try:
   home=sum(v for i,row in enumerate(g) for j,v in enumerate(row) if i>j)
   draw=sum(g[i][i] for i in range(min(len(g),len(g[0]))))
   away=1-home-draw
   p=(home,draw,away)
   if min(p)<-1e-7 or abs(sum(p)-1)>1e-6:errors[model+"_bad_probs"]+=1;continue
   truth=0 if h>aw else 1 if h==aw else 2
   raw[model][key]=dict(p=p,truth=truth,league=a.get("league"),kickoff=a["kickoff"],
    ll=-math.log(max(p[truth],1e-12)),brier=sum((v-(i==truth))**2 for i,v in enumerate(p)),
    exact_ll=-math.log(max(g[h][aw] if h<len(g) and aw<len(g[h]) else 0,1e-12)))
  except Exception:errors[model+"_invalid"]+=1
common=set.intersection(*(set(v) for v in raw.values()))
def score(keys,model):
 vals=[raw[model][k] for k in keys];n=len(vals)
 return dict(n=n,mean_1x2_logloss=round(sum(v["ll"] for v in vals)/n,7),
 mean_1x2_brier=round(sum(v["brier"] for v in vals)/n,7),
 mean_exact_score_logloss=round(sum(v["exact_ll"] for v in vals)/n,7)) if n else dict(n=0)
years={}
for year in ("2025","2026"):
 keys=sorted(k for k in common if k[1]==year)
 years[year]={"matched_fixtures":len(keys),"models":{m:score(keys,m) for m in SOURCES},
 "paired_delta_vs_M5":{m:dict(logloss=round(score(keys,m)["mean_1x2_logloss"]-score(keys,"m5_annual")["mean_1x2_logloss"],7),
 brier=round(score(keys,m)["mean_1x2_brier"]-score(keys,"m5_annual")["mean_1x2_brier"],7),
 exact_ll=round(score(keys,m)["mean_exact_score_logloss"]-score(keys,"m5_annual")["mean_exact_score_logloss"],7)) for m in SOURCES if m!="m5_annual"}}
out=dict(scope="R45 read-only same-fixture predictive comparison; archival bivariate baseline is not M9 production runner",
source_files={m:str(p) for m,p in SOURCES.items()},source_rows=dict(seen),
source_valid_rows={m:len(v) for m,v in raw.items()},source_errors=dict(errors),
matched_total=len(common),years=years,
caveats=["Bivariate archived forecasts and recency archived forecasts are pre-existing M5 comparison artifacts, NOT the M9 production runner trained with M3 history. Therefore no M9 production improvement can be inferred.",
 "This scores predictive accuracy on common fixture IDs only; not Crown line/price or Asian settlement ROI.",
 "2025/26 historical results can have been examined during earlier research, so this is retrospective matched scoring, not pristine untouched prospective confirmation.",
 "Archived forecast training as-of provenance must be checked separately before claiming executable point-in-time forecast equivalence.",
 "No selection thresholds, gates, strategy, M9 production code, Telegram or formal ledgers changed."])
(P/"M9_ARCHITECTURE_MATCHED_R45.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("R45",json.dumps(dict(source_rows=out["source_rows"],source_valid=out["source_valid_rows"],matched=out["matched_total"],errors=out["source_errors"],years=years),ensure_ascii=False),flush=True)
