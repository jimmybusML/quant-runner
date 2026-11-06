#!/usr/bin/env python3
"""Fit market-specific settlement-category temperatures on 2025, no ROI use."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from scipy.optimize import minimize_scalar

from research.m5.crown_historical_capture import local_to_utc
from research.m5.m3_grid_crown_replay import expected_return, legs_result
from research.m5.m5_source_union_replay import event_rows, fixture_row, instant, raw_event, read_jsonl, settlement_distribution, temperature_adjust


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def rows_jsonl(path: Path):
    raw=path.read_bytes(); rows={}
    for line in raw.decode().splitlines():
        try:
            row=json.loads(line); mid=str(row['match_id'])
            if mid in rows: raise ValueError('duplicate forecast fixture identity')
            rows[mid]=row
        except (json.JSONDecodeError,KeyError): continue
    return raw,rows


def fit_temperature(probabilities, labels):
    def loss(log_t):
        t=math.exp(float(log_t)); total=0.0
        for d,label in zip(probabilities,labels):
            adjusted=temperature_adjust(d,t)
            total-=math.log(max(adjusted.get(label,0.0),1e-15))
        return total/len(labels)
    result=minimize_scalar(loss,bounds=(math.log(.25),math.log(4.0)),method='bounded',
                           options={'xatol':1e-10,'maxiter':1000})
    if not result.success or not math.isfinite(result.fun): raise RuntimeError('temperature optimizer failed')
    return math.exp(float(result.x)),loss(0.0),float(result.fun)


def run(a):
    root=a.private_dir.expanduser().resolve(); zone=ZoneInfo(a.source_timezone)
    manifest_raw=(root/'candidate-manifest.json').read_bytes(); manifest=json.loads(manifest_raw)
    forecast_path=a.forecast_path or root/'m5-model-oos'/'m5_goal_model_forecasts.jsonl'
    forecast_raw,forecasts=rows_jsonl(forecast_path)
    crown_index={str(r.get('match_id')):r for r in read_jsonl(root/'crown-response-index.jsonl')}
    total_index={}
    for r in read_jsonl(root/'totalcorner-default-index.jsonl'):
        if r.get('status')=='verified_fixture_response': total_index[str(r.get('match_id'))]=r
    samples={m:[] for m in ('AH','OU')}; counts=Counter(); hashset=set()
    for fixture in manifest.get('rows',[]):
        mid=str(fixture.get('match_id') or ''); f=forecasts.get(mid)
        if not f: continue
        ko=instant(f.get('kickoff')); asof=instant(f.get('prediction_asof_utc')); train=instant(f.get('train_end_utc'))
        if not ko or ko.year!=2025: continue
        if not asof or not train or not train<asof<ko: counts['bad_forecast_time']+=1; continue
        if any(f.get(k)!=fixture.get(fk) for k,fk in (('league','league'),('home','home'),('away','away'),('kickoff','kickoff_utc'),('home_goals','home_goals'),('away_goals','away_goals'))):
            counts['forecast_fixture_identity_mismatch']+=1; continue
        actual=(int(fixture['home_goals']),int(fixture['away_goals']))
        for market in ('AH','OU'):
            selected=None; src=None; receipt=None; digest=None
            cp=root/'crown-responses'/f'{mid}.json'
            if cp.exists():
                try:
                    raw=cp.read_bytes(); payload=json.loads(raw); row=fixture_row(payload,mid)
                    if payload.get('success')==1 and row and (row.get('h'),row.get('a'),row.get('l'))==(fixture['home'],fixture['away'],fixture['league']) and local_to_utc(row.get('start'),zone)==ko and (int(row.get('hg')),int(row.get('ag')))==actual:
                        selected=raw_event(event_rows(row,market,'crown'),market,asof,ko,zone)
                        if selected: src='Crown';receipt=instant(crown_index.get(mid,{}).get('captured_at_utc'));digest=sha(raw)
                except Exception: counts['invalid_crown_response']+=1
            if selected is None:
                tp=root/'totalcorner-default-responses'/f'{mid}.json'; entry=total_index.get(mid)
                if tp.exists() and entry:
                    try:
                        raw=tp.read_bytes();payload=json.loads(raw);row=fixture_row(payload,mid)
                        score_missing=row and row.get('hg') is None and row.get('ag') is None
                        score_matches=row and row.get('hg') is not None and row.get('ag') is not None and (int(row.get('hg')),int(row.get('ag')))==actual
                        if payload.get('success')==1 and row and (row.get('h'),row.get('a'),row.get('l'))==(fixture['home'],fixture['away'],fixture['league']) and local_to_utc(row.get('start'),zone)==ko and (score_missing or score_matches):
                            selected=raw_event(event_rows(row,market,'totalcorner'),market,asof,ko,zone)
                            if selected:src='TotalCorner_default';receipt=instant(entry.get('captured_at_utc'));digest=sha(raw)
                    except Exception:counts['invalid_totalcorner_response']+=1
            if not selected: continue
            event,line,prices=selected
            if receipt is None or receipt<event:counts['bad_quote_receipt_order']+=1;continue
            if event<asof or event>=ko:counts['bad_quote_event_order']+=1;continue
            grid=f.get('prediction',{}).get('grid')
            if not isinstance(grid,list):counts['missing_grid']+=1;continue
            sides=('home','away') if market=='AH' else ('over','under')
            ev=[expected_return(grid,market,s,line,p) for s,p in zip(sides,prices)]
            index=0 if ev[0]>=ev[1] else 1
            dist=settlement_distribution(grid,market,sides[index],line)
            _,label=legs_result(market,sides[index],line,*actual)
            samples[market].append({'distribution':dist,'label':label,'source':src,'event':event,'receipt':receipt,'kickoff':ko})
            counts[f'{market}_{src}']+=1;hashset.add(digest)
    temperatures={};details={}
    for market,values in samples.items():
        if len(values)<20:raise ValueError(f'insufficient {market} training rows')
        temp,raw_nll,cal_nll=fit_temperature([r['distribution'] for r in values],[r['label'] for r in values])
        temperatures[market]=round(temp,10)
        categories=Counter(r['label'] for r in values);sources=Counter(r['source'] for r in values)
        details[market]={'training_unique_fixtures':len(values),'category_counts':dict(categories),
          'source_fixtures':dict(sources),'temperature':round(temp,10),
          'training_settlement_log_loss_raw':round(raw_nll,8),'training_settlement_log_loss_calibrated':round(cal_nll,8),
          'all_quote_receipts_post_kickoff':all(r['receipt']>=r['kickoff'] for r in values),
          'selected_quotes_have_receipt_after_event':all(r['receipt']>=r['event'] for r in values),
          'selected_quote_receipt_before_kickoff_count':sum(r['receipt']<r['kickoff'] for r in values)}
    report={'protocol':'M5_MARKET_SETTLEMENT_TEMPERATURE_2025_TRAIN_V1',
      'generated_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
      'training_year':2025,'training_method':'Select higher raw M5 expected-return side using only 2025 forecast distribution and source-priority 2025 line/prices; fit one market-specific power temperature on five-category Asian settlement log loss. No ROI objective or later-year outcome is used.',
      'forecast_sha256':sha(forecast_raw),'candidate_manifest_sha256':sha(manifest_raw),
      'quote_response_hash_set_sha256':sha('\n'.join(sorted(hashset)).encode()),'temperatures':temperatures,
      'training_by_market':details,'audit_counts':dict(counts),
      'source_rule':'Latest valid Crown event at/after forecast as-of and before kickoff; TotalCorner default fills a missing Crown fixture-market. Deduplicate by fixture-market.',
      'receipt_note':'Training historical API responses were fetched after fixtures; source event time was pre-kickoff. Temperature fit is retrospective historical research, not live calibration.',
      'private_rows_and_prices_not_published':True}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
    print(json.dumps({'generated_utc':report['generated_utc'],'temperatures':temperatures,'training_by_market':details,'audit_counts':dict(counts)},ensure_ascii=False,sort_keys=True))


def main():
    p=argparse.ArgumentParser();p.add_argument('--private-dir',type=Path,required=True);p.add_argument('--forecast-path',type=Path);p.add_argument('--source-timezone',default='Asia/Shanghai');p.add_argument('--output',type=Path,required=True);run(p.parse_args())
if __name__=='__main__':main()
