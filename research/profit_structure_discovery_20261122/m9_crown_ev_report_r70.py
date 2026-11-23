#!/usr/bin/env python3
"""Render reproducible R70 AH EV research and selected-side decomposition."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
a=json.loads((P/"M9_CROWN_EV_CALIBRATION_R70.json").read_text())
b=json.loads((P/"M9_CROWN_EV_DIRECTION_R70B.json").read_text())
names={"annual_bp":"Annual bivariate Poisson",
       "annual_dc":"Annual Dixon-Coles",
       "dynamic_ekf":"Sequential dynamic Poisson EKF"}
MODEL_KEYS=("annual_bp","annual_dc","dynamic_ekf")
LEADS=("lead6h","lead12h")
def t(cols,rows):
    return ["| "+" | ".join(map(str,cols))+" |","|"+"|".join(["---"]*len(cols))+"|"]+[
        "| "+" | ".join(map(str,row))+" |" for row in rows]
s=["# R70 | Why model EV overstates four-year historical Crown AH returns",
   "",
   "## Executive finding",
   "**The main observed mismatch is conditional on which side the model selects, rather than an equally large average bias when the same model is evaluated on fixed home or fixed away positions.** The models are on average close to the actual fixed-side payout at archived odds, but choosing the side with the model's highest estimated EV creates a large optimistic gap. This suggests a lack of exploitable information relative to the Crown market and potential winner's-curse selection effects, not a proven single causal mechanism.",
   "",
   "## Data scope / counting",
   "- Uses Codex recovered **2023–2026** completed fixtures and audited historical Crown movement/open source quotations at or before kickoff T−6h and T−12h.",
   "- The R70 computation rechecked **165,390** model-price calculations: 27,826 matches × 3 models at T−6h and 27,304 × 3 at T−12h. In each scenario a fixture occurs once. The same fixture can occur once in each scenario; do not sum 6h and 12h counts as distinct games.",
   "- **None** of the 275 M9 formal Telegram sends appears here. Every 1U result is simulated retrospectively, not an actual filled bet. Original Crown raw response SHA256 and identity were audited by R68.",
   "- No EV or sample-size selection requirement was imposed: the model chooses the higher of the two estimated side EVs even if both are negative. Grouping labels are analytical descriptions only, not betting rules.",
   "",
   "## 1. Three-model EV prediction vs historical settled returns",
   ""]
for lead in LEADS:
    group=a["groups"][lead]
    s += [f"### {lead}", ""]
    s += t(["Model","Matches","Predicted EV","Simulated ROI","Overstatement (pp)","Five-state Brier","Five-state log loss"],
      [[names[model],f"{x['n']:,}",f"{x['pred_ev_pct']:+.2f}%",
        f"{x['real_roi_pct']:+.2f}%",f"{x['gap_pp']:+.2f}",
        f"{x['brier5']:.5f}",f"{x['logloss5']:.5f}"]
       for model in MODEL_KEYS for x in [group[model]["overall"]]])
    s+=[""]
s+=["The winning-side forecast is not a market edge simply because its estimated EV is positive. All three models overstate the chosen-side EV relative to historically settled unit returns.",
   "",
   "## 2. Fixing the side reveals an important distinction",
   "A five-state wager has exactly reversed outcomes if backed on the opposite side. R70B independently reconstructs the opposite-side five-state distribution from the stored model-selected side, using genuine archived home/away odds. Thus we can compare model-selected EV with **always-home**, **always-away**, and **the unselected side**, on exactly the same matches and prices.",
   ""]
for lead in LEADS:
    s += [f"### {lead}: dynamic EKF — selection versus fixed direction", ""]
    g=b["models"][lead]["dynamic_ekf"]["all"]
    s+=t(["Selection","N","Predicted EV","Historical ROI","Gap pp","Predicted full win","Actual full win"],
       [[{"selected":"Model picks larger EV","unselected":"Opposite of model pick",
          "home":"Always home","away":"Always away"}[side],
         f"{r['n']:,}",f"{r['model_ev_pct']:+.2f}%",f"{r['simulated_roi_pct']:+.2f}%",
         f"{r['gap_pp']:+.2f}",f"{r['predicted_fullwin_pct']:.2f}%",
         f"{r['observed_fullwin_pct']:.2f}%"]
        for side,r in g.items()])
    s+=[""]
s+=["Always-home/away are **diagnostic comparators**, not recommended strategies. The opposite side also loses on average; the data do not prove that automatically reversing model picks would be profitable.",
      "",
      "## 3. Five-state probability errors are conditional on selection",
      "For each matched quote the selected direction's distribution sums to 1 and its EV and full/half/push settlement were independently recalculated. Below are dynamic EKF class-average probabilities and historical observed outcomes on the model-selected direction:",
      ""]
for lead in LEADS:
    cal=a["groups"][lead]["dynamic_ekf"]["overall"]["state_calibration"]
    s+=[f"### {lead}", ""]
    s+=t(["State","Mean predicted","Observed frequency","Forecast−observed pp"],
       [[name,f"{z['predicted_pct']:.2f}%",f"{z['observed_pct']:.2f}%",
         f"{z['gap_pp']:+.2f}"] for name,z in cal.items()])
    s+=[""]
s+=["## 4. Four calendar years: is the gap repeated?",
   "The following four-year figures refer to **identical-model, identical-Crown-time scenario**, not contemporaneously dispatched bets.",
   ""]
for lead in LEADS:
    by=a["groups"][lead]["dynamic_ekf"]["by_year"]
    s+=[f"### {lead} dynamic EKF", ""]
    s+=t(["Year","N","Predicted EV","Historical ROI","Overstatement pp"],
         [[year,f"{z['n']:,}",f"{z['pred_ev_pct']:+.2f}%",
           f"{z['real_roi_pct']:+.2f}%",f"{z['gap_pp']:+.2f}"]
           for year,z in by.items()])
    s+=[""]
s+=["Both timing scenarios show positive EV overstatement in every year. The positive bias of a very broad selected-direction group is not evidence that a *profitable subgroup* persists.",
   "",
   "## 5. Full EV distribution: does highest model EV actually pay?",
   "The JSON contains all 2.5-percentage-point EV histogram cells and each year's matching histogram for all three models, plus 20 equal-frequency forecast-EV cells per model/lead. No combinations were hidden behind an n-based threshold. Here are the dynamic EKF quantiles from the most unfavorable to the model's highest forecast EV.",
   ""]
for lead in LEADS:
    z=a["groups"][lead]["dynamic_ekf"]["ev_twenty_quantile_cells"]
    s+=[f"### {lead}: 20 equal-frequency EV groups", ""]
    s+=t(["Quantile","N","EV range","Mean forecast EV","Historical ROI","EV gap pp"],
         [[r["quantile_1_to_20"],r["n"],
           f"{r['min_ev_pct']:+.1f}% to {r['max_ev_pct']:+.1f}%",
           f"{r['pred_ev_pct']:+.2f}%",
           f"{r['real_roi_pct']:+.2f}%",
           f"{r['gap_pp']:+.2f}"] for r in z])
    s+=[""]
s+=["This is a descriptive ranking **over all four years**, not a time-forward selected betting rule. A positive-looking isolated cell is not independent proof of profitable trade selection.",
   "",
   "## 6. Handicap quarter structure and odds distribution",
   "The entire exact home-handicap line set, all quarter-point types, home-gives/home-gets, model-selected side and decimal-odds 0.1 buckets are in the JSON (not restricted to a preset handicap range).",
   ""]
for lead in LEADS:
    frac=a["groups"][lead]["dynamic_ekf"]["by_handicap_fraction"]
    s+=[f"### {lead}: handicap fractional portion", ""]
    s+=t(["Fraction","N","Forecast EV","ROI","Gap pp"],
       [[k,f"{v['n']:,}",f"{v['pred_ev_pct']:+.2f}%",f"{v['real_roi_pct']:+.2f}%",
         f"{v['gap_pp']:+.2f}"] for k,v in frac.items()])
    s+=[""]
s+=["No single handicap fraction is identified as a stable profitable category. Different year×handicap records appear in the R70 JSON and can disagree even when aggregate differences appear large.",
   "",
   "## 7. First forward-only test of EV calibration bias",
   "For an exploratory diagnostic only, fit a two-parameter linear payoff-versus-model-EV mapping, or simply subtract the historical average EV bias, **using only prior calendar years**. Test in 2024, 2025, 2026 without fitting either correction to the test year's outcomes. This is not a new order rule or improvement in profitability; it tests whether the optimism in a model's *reported* EV carries forward.",
   ""]
for lead in LEADS:
    z=a["groups"][lead]["dynamic_ekf"]["forward_only_ev_correction"]
    s+=[f"### {lead} dynamic EKF", ""]
    s+=t(["Test year","N","Prior-year bias pp","Fitted slope","Actual ROI","Raw EV","Prior-shift EV","Prior-linear EV","Raw MSE","Shift MSE","Linear MSE"],
       [[r["test_year"],r["test_n"],f"{r['train_gap_pp']:+.2f}",f"{r['linear_slope']:+.3f}",
         f"{r['realized_roi_pct']:+.2f}%",f"{r['raw_ev_pct']:+.2f}%",
         f"{r['prior_bias_corrected_ev_pct']:+.2f}%",
         f"{r['prior_linear_corrected_ev_pct']:+.2f}%",
         f"{r['raw_mse']:.4f}",f"{r['prior_bias_mse']:.4f}",
         f"{r['prior_linear_mse']:.4f}"] for r in z["years"]])
    s+=[""]
    s.append(f"Pooled out-of-year one-unit payout prediction MSE (2024–26): raw {z['pooled_raw_mse']:.6f}, prior-bias adjustment {z['pooled_prior_bias_mse']:.6f}, prior-linear mapping {z['pooled_prior_linear_mse']:.6f}. These changes only improve the *numerical forecast of payoff* in this retrospective experiment; they do not make the return positive or change the sign of any settled historical bet.")
    s+=[""]
s+=["## 8. What is supported and what is not",
   "- **Supported:** The selected-side optimistic EV bias is far larger than the same model's fixed-side average EV bias. Four years have similar overall positive selected-side overstatements; 2024–26 forward-only payoff-mapping tests reduce mean-squared errors.",
   "- **Not proven:** The difference is entirely attributable to a single algorithm defect, or that R70 recalibration of profit predictions alone improves trade ROI. All tested directions remain overall negative. The fitted mapping can have a negative slope because extreme model-market disagreements are particularly unreliable.",
   "- **Crucial historical limitation:** Most 2023–25 Crown responses were retrieved in 2026. The provider's quote event time before kickoff does NOT establish that our system received it then. Prior results entered after a 3-hour model availability proxy, not verified first-receipt timestamps.",
   "- **Model comparability:** Annual frozen bivariate/DC versus online EKF use different update frequencies. This analysis isolates return-forecast diagnostics on matched fixtures, not a pure experimental comparison of online update algorithms.",
   "- **Dependence:** Fixed 6h and 12h snapshots of one match are correlated, and league/team temporal dependencies remain. Bootstrap ranges by whole leagues are exploratory, not definitive financial significance tests.",
   "",
   "## Reproducible evidence / no production changes",
   "- Input: local user Codex archive and R66/R68 original fixture/quote evidence; R68 SHA256 Crown raw identity/source checks; R70 recomputes 165,390 state/EV/1U payout observations; R70B additionally checks exact reversal for all 165,390.",
   "- Calculations: m9_crown_ev_calibration_r70.py, m9_crown_ev_direction_r70b.py; report: m9_crown_ev_report_r70.py.",
   "- Aggregate outputs: M9_CROWN_EV_CALIBRATION_R70.json, M9_CROWN_EV_DIRECTION_R70B.json, M9_CROWN_EV_CALIBRATION_R70.md. Individual fixture IDs and source paths remain in private local data, not in git.",
   "- Formal M9, Telegram dispatch, production Crown source requirements, official/settled ledger and accepted project rules were **not changed**.",
   "",
   "## Optional next research, not confirmed rules",
   "Investigate conditional calibration against the market using prior-year-only estimate/realization pairs, independent of whether the model's preferred side is home or away; test whether the ranking of model-market disagreement contains any robust forward edge. No EV cutoffs, restrictive categories, auto-trading conditions or model replacements are authorized by this report.",
   ""]
while s and not s[-1]:s.pop()
(P/"M9_CROWN_EV_CALIBRATION_R70.md").write_text("\n".join(s)+"\n")
print("R70 REPORT",len(s),"lines, file size",
      (P/"M9_CROWN_EV_CALIBRATION_R70.md").stat().st_size)
