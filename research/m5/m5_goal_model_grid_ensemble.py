#!/usr/bin/env python3
"""Fit a leak-safe three-model score-grid blend on 2025 and emit 2026 OOS.

AH weights minimize exact-score log loss. OU weights minimize the proper
log loss of the full-goal-total distribution. Fixture-level predictions stay
in the protected M5 archive; only aggregate metrics and fitted weights publish.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


def read(path: Path) -> tuple[bytes, dict[str, dict]]:
    raw = path.read_bytes()
    rows = {}
    for line in raw.decode().splitlines():
        try:
            row = json.loads(line)
            mid = str(row['match_id'])
            if mid in rows:
                raise ValueError(f'duplicate fixture in {path.name}')
            rows[mid] = row
        except (json.JSONDecodeError, KeyError):
            continue
    return raw, rows


def instant(s: str) -> datetime:
    value = datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('timestamp must include UTC offset')
    return value.astimezone(timezone.utc)


def align(rows: list[dict]) -> bool:
    x = rows[0]
    return all(all(r.get(k) == x.get(k) for k in
                   ('match_id','league','home','away','kickoff','home_goals','away_goals'))
               and instant(r['train_end_utc']) == instant(x['train_end_utc'])
               and instant(r['prediction_asof_utc']) == instant(x['prediction_asof_utc'])
               for r in rows[1:])


def tensor(row: dict) -> np.ndarray:
    a = np.asarray(row['prediction']['grid'], dtype=float)
    if a.shape != (15,15) or not np.isfinite(a).all() or (a < 0).any():
        raise ValueError('invalid score grid')
    total = a.sum()
    if not np.isclose(total, 1.0, atol=1e-7):
        raise ValueError('score grid must sum to 1')
    return a / total


def goal_totals(grid: np.ndarray) -> np.ndarray:
    result=np.zeros(15,dtype=float)
    for h in range(15):
        for a in range(15): result[min(h+a,14)]+=grid[h,a]
    return result


def fit_weights(rows: list[list[dict]], objective: str) -> list[float]:
    grids = np.asarray([[tensor(r) for r in group] for group in rows])
    hg = np.asarray([int(group[0]['home_goals']) for group in rows])
    ag = np.asarray([int(group[0]['away_goals']) for group in rows])
    if objective == 'AH_exact_score_logloss':
        labels = np.minimum(hg,14)*15 + np.minimum(ag,14)
        flat = grids.reshape(len(rows),3,225)
        observed = np.take_along_axis(flat, labels[:,None,None], axis=2)[:,:,0]
        losses = -np.log(np.clip(observed,1e-15,1)).mean(axis=0)
        def loss(w): return -np.log(np.clip(observed @ w,1e-15,1)).mean()
    else:
        totals = hg + ag
        probs = np.asarray([[goal_totals(g) for g in models] for models in grids])
        observed = np.take_along_axis(probs, np.minimum(totals,14)[:,None,None],axis=2)[:,:,0]
        losses = -np.log(np.clip(observed,1e-15,1)).mean(axis=0)
        def loss(w): return -np.log(np.clip(observed @ w,1e-15,1)).mean()
    candidates = []
    for start in np.eye(3):
        result = minimize(loss, start, method='SLSQP', bounds=[(0,1)]*3,
                          constraints=[{'type':'eq','fun':lambda w: float(w.sum()-1)}],
                          options={'ftol':1e-12,'maxiter':1000})
        if result.success:
            candidates.append(result)
    if not candidates:
        raise RuntimeError('simplex optimization failed')
    best = min(candidates,key=lambda r:r.fun)
    return [round(float(x),10) for x in best.x]


def proper_report(rows, weights: list[float], objective: str) -> dict:
    mixes=[]; fixtures=[]
    for item in rows:
        group, has_bivariate = item if isinstance(item, tuple) else (item, True)
        if not has_bivariate: group=group[:2]
        w=np.asarray(weights if has_bivariate else weights[:2],dtype=float)
        w=w/w.sum()
        mixes.append(np.einsum('m,mij->ij',w,np.asarray([tensor(r) for r in group])))
        fixtures.append(group[0])
    mix=np.asarray(mixes)
    hg=np.asarray([int(g['home_goals']) for g in fixtures]); ag=np.asarray([int(g['away_goals']) for g in fixtures])
    if objective == 'AH_exact_score_logloss':
        obs=mix[np.arange(len(rows)),np.minimum(hg,14),np.minimum(ag,14)]
    else:
        totals=np.asarray([goal_totals(g) for g in mix])
        obs=totals[np.arange(len(rows)),np.minimum(hg+ag,14)]
    return {'fixtures':len(rows),'log_loss':round(float(-np.log(np.clip(obs,1e-15,1)).mean()),8),
            'weights_baseline_recency_bivariate':weights}


def component_report(rows, index: int, objective: str) -> dict:
    grids=np.asarray([tensor(group[index]) for group in rows])
    hg=np.asarray([int(group[0]['home_goals']) for group in rows]); ag=np.asarray([int(group[0]['away_goals']) for group in rows])
    if objective=='AH_exact_score_logloss': obs=grids[np.arange(len(rows)),np.minimum(hg,14),np.minimum(ag,14)]
    else:
        totals=np.asarray([goal_totals(g) for g in grids])
        obs=totals[np.arange(len(rows)),np.minimum(hg+ag,14)]
    return {'fixtures':len(rows),'log_loss':round(float(-np.log(np.clip(obs,1e-15,1)).mean()),8)}


def run(a):
    paths=[a.baseline,a.recency,a.bivariate]
    loaded=[read(p) for p in paths]
    allrows=[x[1] for x in loaded]
    shared=set.intersection(set(allrows[0]),set(allrows[1]))
    groups={}
    excluded={'source_missing':0,'identity_or_time_mismatch':0,'chronology':0}
    for mid in sorted(shared):
        rs=[d[mid] for d in allrows[:2]]
        br=allrows[2].get(mid)
        if br is not None: rs.append(br)
        if not align(rs): excluded['identity_or_time_mismatch']+=1; continue
        ko=instant(rs[0]['kickoff']); asof=instant(rs[0]['prediction_asof_utc']); train=instant(rs[0]['train_end_utc'])
        if not train < asof < ko: excluded['chronology']+=1; continue
        groups[mid]=(rs, br is not None)
    train=[v[0] for v in groups.values() if v[1] and instant(v[0][0]['kickoff']).year==2025]
    test=[v for v in groups.values() if instant(v[0][0]['kickoff']).year==2026]
    if not train or not test: raise ValueError('missing prior-year training or target-year holdout')
    ah=fit_weights(train,'AH_exact_score_logloss'); ou=fit_weights(train,'OU_total_goal_logloss')
    complete_test=[g for g,has in test if has]
    baseline_recency_test=[g[:2] for g,_ in test]
    # Both use full grids; separate market-specific weights are fit only on 2025.
    outdir=a.private_dir/'m5-model-oos'/'2025-trained-ensemble'
    outdir.mkdir(parents=True,exist_ok=True)
    target_paths={m:outdir/f'm5_goal_model_2026_ensemble_{m.lower()}.jsonl' for m in ('AH','OU')}
    records={'AH':[],'OU':[]}
    bivar_missing=0
    for packed in sorted(test,key=lambda x:x[0][0]['match_id']):
        group,has_bivariate=packed
        if not has_bivariate:
            bivar_missing+=1
            group=group[:2]
        rows=group
        grids=[tensor(r) for r in rows]
        weights={}
        for market,full in (('AH',ah),('OU',ou)):
            current=np.asarray(full if has_bivariate else full[:2],dtype=float)
            weights[market]=current/current.sum()
        p={'AH':np.einsum('m,mij->ij',weights['AH'],np.asarray(grids)),
           'OU':np.einsum('m,mij->ij',weights['OU'],np.asarray(grids))}
        # Each market gets its separately prior-year-fitted blend.
        for market,grid in p.items():
            r=rows[0]
            payload={k:r[k] for k in ('match_id','league','home','away','kickoff','home_goals','away_goals',
                                         'train_end_utc','prediction_asof_utc')}
            payload['prediction']={'grid':grid.tolist()}
            payload['blend_market']=market
            payload['blend_weights']=weights[market].tolist()
            records[market].append(json.dumps(payload,separators=(',',':')))
    texts={m:'\n'.join(records[m])+'\n' for m in ('AH','OU')}
    for market,path in target_paths.items(): path.write_text(texts[market],encoding='utf-8')
    report={'protocol':'M5_2025_TRAIN_2026_OOS_MARKET_SPECIFIC_GRID_BLEND_V1',
      'generated_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
      'model_order':['baseline','recency','penaltyblog_bivariate'],
      'source_sha256':[hashlib.sha256(x[0]).hexdigest() for x in loaded],
      'shared_baseline_recency_fixture_count_after_identity_time_checks':len(groups),
      'training_year':2025,'training_unique_fixtures':len(train),'target_year':2026,
      'target_unique_fixtures':len(test),'bivariate_unavailable_target_fixtures':bivar_missing,'training_target_ids_disjoint':True,
      'AH_exact_score_training':proper_report(train,ah,'AH_exact_score_logloss'),
      'OU_goal_total_training':proper_report(train,ou,'OU_total_goal_logloss'),
      'holdout_proper_scores':{'AH_exact_score':proper_report(test,ah,'AH_exact_score_logloss'),
                               'OU_goal_total':proper_report(test,ou,'OU_total_goal_logloss')},
      'component_scores_on_2026_common_3_model_fixtures':{
        name:{'AH_exact_score':component_report(complete_test,i,'AH_exact_score_logloss'),
              'OU_goal_total':component_report(complete_test,i,'OU_total_goal_logloss')}
        for i,name in enumerate(('baseline','recency','bivariate'))},
      'baseline_recency_scores_on_full_2026_scope':{
        name:{'AH_exact_score':component_report(baseline_recency_test,i,'AH_exact_score_logloss'),
              'OU_goal_total':component_report(baseline_recency_test,i,'OU_total_goal_logloss')}
        for i,name in enumerate(('baseline','recency'))},
      'holdout_forecast_sha256':{m:hashlib.sha256(texts[m].encode()).hexdigest() for m in texts},
      'private_forecasts_path':{m:str(path) for m,path in target_paths.items()},'excluded_counts':excluded,
      'method_note':'Separate AH/OU blend weights are fit only on 2025 OOS fixtures with all three models by proper score. For target fixtures with unseen bivariate teams, weights on the two always-available M5 models are renormalized without excluding the match. One 2026 row per fixture-market; no ROI, odds, or 2026 result is used for fitting.'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','private_forecasts_path')},sort_keys=True))


def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--recency',type=Path,required=True);p.add_argument('--bivariate',type=Path,required=True);p.add_argument('--private-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);run(p.parse_args())
if __name__=='__main__': main()
