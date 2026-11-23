#!/usr/bin/env python3
"""R69 full four-year Crown movement T-minus-6h / T-minus-12h scenarios."""
import collections,json,math,datetime as dt
from pathlib import Path
import numpy as np
R=Path.home()/"QuantAsiaDesk"
P=Path(__file__).resolve().parent
source=json.loads((P/"M9_HISTORICAL_CROWN_LEAD_R68.json").read_text())
original=json.loads((P/"M9_HISTORICAL_CROWN_AUDIT_R65.json").read_text())
audit={"verified_distinct_source_files":source["distinct_checked_response_and_fixture"],
       "source_file_hash_problems":source["hash_or_identity_failures"],
       "matched_completed_fixtures":source["counts"]["selected_lead6h"],
       "selected_quotes":source["counts"]["raw_ok"],
       "source":{year:{"valid_completed_unique_ids":original["source"][year]["valid_completed_unique_ids"],
                         "quote":{"matched_selected_quote_open":source["by_year_kind"][year]["lead6h"],
                                  "matched_selected_quote_close":source["by_year_kind"][year]["lead12h"]}}
                 for year in ("2023","2024","2025","2026")}}
r66=[json.loads((P/f"M9_HISTORICAL_CROWN_R66_SHARD{i}_lead.json").read_text()) for i in range(4)]
assert not any(x["errors"] for x in r66),[x["errors"] for x in r66 if x["errors"]]
rows=[]
for i in range(4):
    private=json.loads((R/f"state/m9_r66_replay_shard{i}_lead_private.json").read_text())["rows"]
    assert len(private)==sum(x["valid"] for x in r66[i]["leagues"]),(i,len(private))
    rows+=private
assert len(rows)>10000
MODELS=("annual_bp","annual_dc","dynamic_ekf")
YEARS=("2023","2024","2025","2026")
KINDS=("lead6h","lead12h")
STRATEGIES=("ev_side","neutral_side")
def summarize(items):
    data={"n":len(items),"unique_fixtures":len({x["fid"] for x in items}),
          "lead_minutes_p10_p50_p90":[float(x) for x in np.percentile([r["lead_minutes"] for r in items],[10,50,90])]} if items else {"n":0}
    if not items:return data
    data["models"]={}
    for name in MODELS:
        m={"one_ll":sum(r["results"][name]["one_ll"] for r in items)/len(items)}
        for strategy in STRATEGIES:
            rec=[r["results"][name][("ev_choice" if strategy=="ev_side" else "neutral_choice")] for r in items]
            pnl=sum(float(v["pnl_u"]) for v in rec);n=len(rec)
            m[strategy]={"n":n,
              "net_u":pnl,"roi_percent":100*pnl/n,
              "predicted_ev_per_order":sum(v["ev"] for v in rec)/n,
              "predicted_ev_total_u":sum(v["ev"] for v in rec),
              "outcomes":dict(collections.Counter(v["state"] for v in rec)),
              "home_choices":sum(r["results"][name][strategy]=="home" for r in items)}
        data["models"][name]=m
    data["direction_diff_ev_dynamic_vs_annual_bp"]=sum(r["results"]["dynamic_ekf"]["ev_side"]!=r["results"]["annual_bp"]["ev_side"] for r in items)
    data["direction_diff_ev_dynamic_vs_annual_dc"]=sum(r["results"]["dynamic_ekf"]["ev_side"]!=r["results"]["annual_dc"]["ev_side"] for r in items)
    return data
by_kind={kind:summarize([r for r in rows if r["kind"]==kind]) for kind in KINDS}
by_year_kind={year:{kind:summarize([r for r in rows if r["year"]==year and r["kind"]==kind]) for kind in KINDS} for year in YEARS}
by_league_kind={lid:{kind:[r for r in rows if r["league"]==lid and r["kind"]==kind] for kind in KINDS}
                for lid in set(r["league"] for r in rows)}
def bootstrap(kind,base,challenger,strategy):
    teams=sorted(by_league_kind,key=int)
    delta=[];counts=[]
    for lid in teams:
        records=by_league_kind[lid][kind];delta.append(sum(
            r["results"][challenger][("ev_choice" if strategy=="ev_side" else "neutral_choice")]["pnl_u"]-r["results"][base][("ev_choice" if strategy=="ev_side" else "neutral_choice")]["pnl_u"]
            for r in records))
        counts.append(len(records))
    a=np.array(delta);n=np.array(counts)
    rng=np.random.default_rng(20261123)
    idx=rng.integers(0,len(teams),size=(4000,len(teams)))
    simulated=a[idx].sum(axis=1)/n[idx].sum(axis=1)
    return {"mean_unit_roi_gain":float(a.sum()/n.sum()),
            "improved_leagues":int((a>0).sum()),"total_leagues":len(teams),
            "league_cluster_bootstrap_95":[float(x) for x in np.percentile(simulated,[2.5,97.5])]}
bootstrap_results={kind:{
    "dynamic_vs_annual_bp_Ev_choice":bootstrap(kind,"annual_bp","dynamic_ekf","ev_side"),
    "dynamic_vs_annual_dc_Ev_choice":bootstrap(kind,"annual_dc","dynamic_ekf","ev_side"),
    "annual_dc_vs_annual_bp_Ev_choice":bootstrap(kind,"annual_bp","annual_dc","ev_side")}
    for kind in KINDS}
coverage=collections.Counter()
for z in r66:
    for x in z["leagues"]:
        coverage["league_files"]+=1;coverage["quotes_selected"]+=x["selected"];coverage["model_compatible_quotes"]+=x["valid"]
        coverage["dc_rho_projections"]+=x["rho_projected"]
        for k,v in x["skipped"].items():coverage["skip_"+k]+=v
out={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
    "scope":"Codex historical 2023-26 full-time matches and historical Crown source files, NOT 275 M9 formal orders.",
    "method":"Crown real archive open/close prices with genuine historical SOURCE timestamps; model predictions at those time points use only prior match results whose kickoff+3h elapsed, but historical score first-receipt and Crown live reception in 2023-25 not established. One unconditional simulated home/away decision per matching historical event, both EV-maximizing at actual quoted prices and neutral-2.0 direction, no EV gate. Historical backtest only, no investment/execution claim.",
    "audit":{"verified_files":audit["verified_distinct_source_files"],"raw_integrity_problems":audit["source_file_hash_problems"],
             "matched_completed_fixtures":audit["matched_completed_fixtures"],"selected_quotes":audit["selected_quotes"]},
    "model_coverage":dict(coverage),"by_kind":by_kind,"by_year_kind":by_year_kind,
    "bootstrap":bootstrap_results}
(P/"M9_HISTORICAL_CROWN_R68_R69.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
def tbl(head,lines):
    return ["| "+" | ".join(head)+" |","|"+("|".join(["---"]*len(head)))+"|"]+[
        "| "+" | ".join(str(v) for v in line)+" |" for line in lines]
names={"annual_bp":"Annual bivariate Poisson","annual_dc":"Annual Dixon-Coles","dynamic_ekf":"Online Poisson EKF"}
s=["# R68–R69 | Codex 2023–2026 historical Crown movement T-6h and T-12h replay","",
   "## Four-year Codex historical recovery and lead-time sensitivity",
   "This study uses the four-year historical Codex recovered match and bookmaker database. The former R64 M9 formal 275 orders were an irrelevant sample and **are not used here**. No production files were changed.",
   "",
   "## Original historical data audit",
   f"- 2023–2026 completed cache fixtures: {sum(audit['source'][y]['valid_completed_unique_ids'] for y in YEARS):,}, from 61 league files.",
   f"- Joined SHA-verified historical Crown T−6h/T−12h movement/open snapshots: {audit['selected_quotes']:,} price events, {audit['matched_completed_fixtures']:,} unique complete fixtures, {audit['verified_distinct_source_files']:,} distinct checked original source files; SHA/Crown identity errors: {audit['source_file_hash_problems']}.",
   "- The database also preserves over four million historical Crown AH movement rows; we selected the latest eligible Crown historical movement/open source quote at or before the start minus 6h and minus 12h. These are two lead-time sensitivity scenarios, **not** user-approved production constraints. Other timestamps remain in the original database.",
   ""]
s+=tbl(["Year","Completed unique games","Matched Crown T−6h","Matched Crown T−12h"],
  [[y,f"{audit['source'][y]['valid_completed_unique_ids']:,}",
      f"{audit['source'][y]['quote'].get('matched_selected_quote_open',0):,}",
      f"{audit['source'][y]['quote'].get('matched_selected_quote_close',0):,}"] for y in YEARS])
s+=["","## Model-compatible historical Crown paired samples","",
    f"All three fitted models produced same-fixture prediction + retrospective AH payout on {coverage['model_compatible_quotes']:,} price events (not distinct fixtures); 6h and 12h snapshots from one fixture are dependent. {coverage['quotes_selected']-coverage['model_compatible_quotes']:,} price events could not be paired across all model classes, chiefly unavailable pre-year training or unseen teams. No fabricated probabilities for those rows. There were {coverage['dc_rho_projections']} per-fixture valid-rho adjustments in DC implementation.",
    "",
    "## Historical model decisions using actual Crown odds",
    "At each historical T−6h or T−12h source quote, each model selects home or away by maximum **model expected return using that Crown price**, even if both estimated returns are negative. This is deliberately not EV-threshold-filtered; the payout is a retrospective counterfactual for one unit on the chosen side. These two lead-time scenarios correspond to different hypothetical execution times and should **not** be combined as separate fixtures. No Telegram was sent.",
    ""]
for kind in KINDS:
    v=by_kind[kind]
    s+=[f"### Crown {kind} event — {v['n']:,} matched price observations, {v['unique_fixtures']:,} matches",
        f"Provider quote lead-time p10 / median / p90 (minutes): {v['lead_minutes_p10_p50_p90'][0]:.1f} / {v['lead_minutes_p10_p50_p90'][1]:.1f} / {v['lead_minutes_p10_p50_p90'][2]:.1f}.",
        ""]
    s+=tbl(["Model","Prob 1X2 LL","Simulated net U","Simulated ROI","Model predicted EV / bet","Home picks"],
    [[names[m],f"{v['models'][m]['one_ll']:.6f}",
      f"{v['models'][m]['ev_side']['net_u']:+.3f}",
      f"{v['models'][m]['ev_side']['roi_percent']:+.3f}%",
      f"{v['models'][m]['ev_side']['predicted_ev_per_order']:+.4f}",
      str(v['models'][m]['ev_side']['home_choices'])] for m in MODELS])
    s+=["","### By year: historical quote-level simulation",
        ""]
    s+=tbl(["Year","Matched","BP ROI","DC ROI","EKF ROI"],
      [[y,str(by_year_kind[y][kind]['n'])]+[
        f"{by_year_kind[y][kind]['models'][m]['ev_side']['roi_percent']:+.2f}%"
        if by_year_kind[y][kind]["n"] else "N/A" for m in MODELS] for y in YEARS])
    s+=["","### Descriptive league-cluster ROI differences",""]
    s+=tbl(["Comparison","ROI gain (percentage points)","Leagues improving","Bootstrap 95% range (percentage points)"],
    [[k,f"{v['mean_unit_roi_gain']*100:+.3f}",f"{v['improved_leagues']}/{v['total_leagues']}",
      f"[{v['league_cluster_bootstrap_95'][0]*100:+.3f}, {v['league_cluster_bootstrap_95'][1]*100:+.3f}]"]
      for k,v in bootstrap_results[kind].items()])
    s+=[""]
s+=["## Evidential limits and next decisions",
    "- These are archived Crown historical **provider source timestamps**, not actual 2023–25 system-received bid/ask confirmations. Captures taken in November 2026 cannot prove quotes were accessible at past event times. Do not label this live trade ROI or formal achieved ROI.",
    "- Actual first receipt of every historical final score is not archived in this cache; training used kickoff+3h as an exploratory availability proxy. This is not a user-approved production gate or proof of exact historical causality.",
    "- Full 2023–26 Crown quote and fixture universes differ; results cover the intersection only and are not an unfiltered production trading universe.",
    "- Annual frozen Bivariate/DC model versus dynamic EKF differ in update cadence. R63 monthly refit comparison remains relevant. All EKF prior/process parameters are exploratory, not final product logic.",
    "- All outcomes include full win, half win, push, half loss, full loss using independent Asian payout settlement code; no EV score threshold, order cap, new model switching rule, or live runner deployment introduced.",
    "- Price-before-kickoff event timing is not necessarily practical: late closing prices can be seconds before start. Opening prices give another historical timepoint; neither assures execution.",
    "- Bootstrap resamples whole league histories, not proof of independent years or conclusive true ROI. Several repeated research comparisons mean apparent wins may be chance.",
    "- All raw fixture-level strategy comparisons remain in local nonproduction state files, not published order identifiers.",
    "",
    "## Research files",
    "- m9_historical_crown_lead_r68.py: SHA-audited historic Crown open/movement selection at or before T−6h / T−12h.",
    "- m9_historical_crown_models_r66.py: three model grids, real Crown source-quote price EV, independent settlement simulation.",
    "- m9_historical_crown_lead_summary_r69.py: public aggregate 4-year practical lead-time analysis.",
    "- M9_HISTORICAL_CROWN_LEAD_R68.json, M9_HISTORICAL_CROWN_R68_R69.json: summary evidence.",
    "",
    "## Optional further investigation",
    "Use the full movement-price timeline, genuine archived pre-match receipts where available, and a same-update-frequency model challenger. Distinguish historical market-EV exploration from actual auditable forward orders. No deployment or user rule changes.",
    ""]
(P/"M9_HISTORICAL_CROWN_R68_R69.md").write_text("\n".join(s))
print(json.dumps({"audit":out["audit"],"coverage":out["model_coverage"],
    "by_kind":out["by_kind"],"by_year_kind":{y:{k:{"n":v["n"],"roi":{m:v["models"][m]["ev_side"]["roi_percent"] if v["n"] else None for m in MODELS}} for k,v in yr.items()} for y,yr in by_year_kind.items()},
    "bootstrap":bootstrap_results},ensure_ascii=False,indent=2))
