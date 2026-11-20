#!/usr/bin/env python3
"""Independent raw Crown T12 / FT / settlement checks for squad-value study."""
from __future__ import annotations
import collections, datetime as dt, gzip, json, math, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).resolve().parent
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
MARKET=WORK/'m8_early_joint_market_inventory_20261115.jsonl'
FROZEN=WORK/'m8_foundation_20261115/historical_membership.jsonl'
LEDGER=OUT/'squad_value_per_fixture_20261120.jsonl.gz'
SUMMARY=OUT/'m8_squad_value_results_20261120.json'

def settle(line,side,hg,ag,odds):
    line=float(line)
    if abs(line*4-round(line*4))>1e-7:raise ValueError('line outside quarter grid')
    legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
    out=[]
    for leg in legs:
        margin=hg-ag+leg if side=='home' else ag-hg-leg
        out.append(float(odds)-1 if margin>1e-9 else -1.0 if margin< -1e-9 else 0.0)
    val=sum(out)/len(out)
    state='full_win' if all(x>0 for x in out) else 'half_win' if any(x>0 for x in out) else 'push' if all(x==0 for x in out) else 'half_loss' if any(x==0 for x in out) else 'full_loss'
    return val,state

def main():
    raw={}
    with MARKET.open(encoding='utf-8') as f:
        for line in f:
            x=json.loads(line)
            if int(x['T'])==12:raw[str(x['fid'])]=x
    frozen={}
    with FROZEN.open(encoding='utf-8') as f:
        for line in f:
            x=json.loads(line);frozen[str(x['fid'])]=x
    if len(frozen)!=10294:raise AssertionError('frozen M8 membership changed')
    rows=[]
    with gzip.open(LEDGER,'rt',encoding='utf-8') as f:
        rows=[json.loads(line) for line in f]
    s=json.loads(SUMMARY.read_text())
    model_rows=collections.defaultdict(list); source_checks=settle_checks=selection_checks=feature_time_checks=0
    for x in rows:
        model_rows[x['model']].append(x)
        z=raw.get(str(x['fid']))
        if z is None:raise AssertionError(f'missing Crown T12 FID {x["fid"]}')
        checks=(str(z['date'])==str(x['date']) and str(z['league'])==str(x['league']) and
          str(z['home_id'])==str(x.get('home_id',z['home_id'])) and str(z['away_id'])==str(x.get('away_id',z['away_id'])) and
          abs(float(z['al'])-float(x['line']))<1e-9 and abs(float(z['ah'])-float(x['home_odds']))<1e-9 and
          abs(float(z['aa'])-float(x['away_odds']))<1e-9 and int(z['hg'])==int(x['FT_home']) and int(z['ag'])==int(x['FT_away']))
        if not checks:raise AssertionError(f'Crown quote or FT mismatch {x["fid"]}/{x["model"]}')
        source_checks+=1
        price=float(x['home_odds'] if x['side']=='home' else x['away_odds'])
        if abs(price-float(x['price']))>1e-9:raise AssertionError(f'price mismatch {x["fid"]}/{x["model"]}')
        pnl,state=settle(x['line'],x['side'],int(x['FT_home']),int(x['FT_away']),price)
        if abs(pnl-float(x['net_u']))>1e-7 or state!=x['settlement']:raise AssertionError(f'AH settlement mismatch {x["fid"]}/{x["model"]}')
        settle_checks+=1
        if x['model']=='LOWER_PRICE':
            expected='home' if float(z['ah'])<=float(z['aa']) else 'away'
        else:
            expected='home' if float(x['predicted_home_minus_away_u'])>=0 else 'away'
        if x['side']!=expected:raise AssertionError(f'side choice mismatch {x["fid"]}/{x["model"]}')
        selection_checks+=1
        target=dt.date.fromisoformat(str(x['date']))
        fc=dt.date.fromisoformat(str(x['feature_cutoff_date']))
        vc=dt.date.fromisoformat(str(x['valuation_cutoff_date']))
        if fc>=target or vc>=fc or (target-fc).days!=3 or (fc-vc).days!=30:raise AssertionError(f'feature cutoff invalid {x["fid"]}')
        if bool(x['frozen_eight_overlap_posthoc'])!=(str(x['fid']) in frozen):raise AssertionError('frozen overlap flag')
        feature_time_checks+=1
    expected_models=set(s['models'])
    if set(model_rows)!=expected_models:raise AssertionError('model set differs')
    incremental_by_model={}; weekly={}
    for m,rr in model_rows.items():
        fids=[str(x['fid']) for x in rr]
        if len(fids)!=len(set(fids)):raise AssertionError(f'duplicate FID within {m}')
        inc=[x for x in rr if str(x['fid']) not in frozen]
        if len(inc)!=s['models'][m]['incremental_unique_fids']:raise AssertionError(f'increment count mismatch {m}')
        total=round(sum(float(x['net_u']) for x in inc),6)
        if abs(total-s['models'][m]['incremental']['net_u'])>1e-6:raise AssertionError(f'total pnl mismatch {m}')
        byyear={}
        for y,z in s['models'][m]['incremental_by_year'].items():
            yr=[x for x in inc if str(x['year'])==y]
            if len(yr)!=z['orders'] or abs(sum(float(x['net_u']) for x in yr)-z['net_u'])>1e-6:raise AssertionError(f'year mismatch {m}/{y}')
            byyear[y]={'orders':len(yr),'net_u':round(sum(float(x['net_u']) for x in yr),6)}
        incremental_by_model[m]={'orders':len(inc),'net_u':total,'years':byyear}
        w=collections.defaultdict(lambda:[0,0.0])
        for x in inc:w[x['iso_week']][0]+=1;w[x['iso_week']][1]+=float(x['net_u'])
        weekly[m]={k:{'orders':v[0],'net_u':round(v[1],6)} for k,v in sorted(w.items())}
    # All model sets have common test IDs; 2026 targets are capped to source
    # appearance coverage rather than freezing an obsolete roster after cutoff.
    sets={m:{str(x['fid']) for x in rr} for m,rr in model_rows.items()}
    if any(v!=next(iter(sets.values())) for v in sets.values()):raise AssertionError('model test FIDs not identical')
    out={'status':'PASS','raw_crown_t12_inventory_rows':len(raw),'frozen_eight_fids':len(frozen),'ledger_rows':len(rows),
      'models':sorted(model_rows),'quote_ft_identity_checks':source_checks,'independent_ah_settlement_checks':settle_checks,
      'side_rule_checks':selection_checks,'cutoff_and_frozen_overlap_checks':feature_time_checks,
      'unique_common_test_fids':len(next(iter(sets.values()))),'incremental_fids_by_model':incremental_by_model,
      'weekly_incremental_by_model':weekly,'same_test_fid_set_across_models':True,
      'historical_event_time_only':True,'actual_receipt_performance':'not available; zero FID overlap after appearance-source cutoff and zero value snapshot timestamp proof'}
    (OUT/'squad_value_independent_verification_20261120.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='weekly_incremental_by_model'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
