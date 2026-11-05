#!/usr/bin/env python3
"""Aggregate-only, Crown-first M5 Crown/TotalCorner event-time replay.

All fixture-level inputs and raw provider responses remain in a private archive.
TotalCorner default odds are source-distinct and only fill a missing Crown
fixture-market. Historical source event time is not represented as receipt time.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m3.reference.m1_runtime_policy import scope_status
from research.m5.crown_historical_capture import ensure_private_destination, local_to_utc, utc_now
from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout, split_line, bootstrap, score


def instant(v):
    try:
        d=datetime.fromisoformat(str(v).replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError,ValueError): return None

def read_jsonl(p):
    out=[]
    if p.exists():
        with p.open(encoding='utf-8') as f:
            for line in f:
                try: out.append(json.loads(line))
                except ValueError: continue
    return out

def raw_event(rows, market, asof, kickoff, zone):
    key='asian_list' if market=='AH' else 'goal_list'
    valid=[]
    for r in rows or []:
        if not isinstance(r,list) or len(r)<8: continue
        minute,line_raw,p1,p2,raw_time,_hs,_as,closed=r[:8]
        if minute not in (None,'',0,'0') or closed not in (0,'0',False): continue
        observed=local_to_utc(raw_time,zone)
        if not observed or observed<asof or observed>=kickoff: continue
        try:
            parts=[float(x.strip()) for x in str(line_raw).replace('/',',').split(',')]
            prices=(float(p1),float(p2)); line=sum(parts)/len(parts)
            if len(parts) not in (1,2) or any(not math.isfinite(x) for x in parts+list(prices)) or any(x<=1 for x in prices): continue
            split_line(line)
        except (ValueError,TypeError,ZeroDivisionError): continue
        valid.append((observed,line,prices))
    return max(valid,key=lambda x:x[0]) if valid else None

def fixture_row(payload, mid):
    data=payload.get('data') if isinstance(payload,dict) else None
    rows=data if isinstance(data,list) else ([data] if isinstance(data,dict) else [])
    found=[x for x in rows if isinstance(x,dict) and str(x.get('id') or '')==mid]
    return found[0] if len(found)==1 else None

def event_rows(provider_row, market, source):
    if source=='crown':
        books=[b for b in provider_row.get('bookmakers',[]) if isinstance(b,dict) and b.get('slug')=='crown']
        if len(books)!=1: return []
        return books[0].get('asian_list' if market=='AH' else 'goal_list') or []
    return provider_row.get('asian_list' if market=='AH' else 'goal_list') or []

def summarize(rows, market, seed):
    outcomes=Counter(r['category'] for r in rows); pnl=sum(r['pnl'] for r in rows); n=len(rows)
    bytime=defaultdict(float)
    for r in rows: bytime[r['event_utc']]+=r['pnl']
    equity=peak=dd=0.0
    for t in sorted(bytime):
        equity+=bytime[t]; peak=max(peak,equity); dd=max(dd,peak-equity)
    ll,br=score([(r['category'],r['distribution']) for r in rows])
    sources=Counter(r['source'] for r in rows)
    receipt=Counter('pre_kickoff' if r['receipt_before_kickoff'] else 'post_kickoff' for r in rows)
    byyear=defaultdict(list)
    for r in rows: byyear[r['kickoff_utc'][:4]].append(r['pnl'])
    return {'unique_fixtures':n,'simulated_bets':n,'settled_bets':n,'pending_bets':0,
      'settlement_counts':{k:outcomes[k] for k in ('win','half_win','push','half_loss','loss')},
      'net_units':round(pnl,6),'roi_pct':round(100*pnl/n,6) if n else None,
      'max_drawdown_units_by_source_event_time':round(dd,6) if n else None,
      'roi_bootstrap_95pct':bootstrap([r['pnl'] for r in rows],seed),
      'settlement_log_loss':ll,'settlement_brier':br,
      'source_fixture_markets':dict(sources),'quote_receipt_timing':dict(receipt),
      'by_utc_kickoff_year':{y:{'fixtures':len(v),'net_units':round(sum(v),6),'roi_pct':round(100*sum(v)/len(v),6)} for y,v in sorted(byyear.items())}}

def run(a):
    root=ensure_private_destination(a.private_dir); zone=ZoneInfo(a.source_timezone)
    manifest_raw=(root/'candidate-manifest.json').read_bytes(); manifest=json.loads(manifest_raw)
    forecast_path=root/'m5-model-oos'/'m5_goal_model_forecasts.jsonl'; forecast_raw=forecast_path.read_bytes()
    forecasts={}
    for line in forecast_raw.decode().splitlines():
        try:
            r=json.loads(line); forecasts[str(r['match_id'])]=r
        except Exception: continue
    crown_receipts={str(x.get('match_id')):x for x in read_jsonl(root/'crown-response-index.jsonl')}
    total_receipts={}
    for x in read_jsonl(root/'totalcorner-default-index.jsonl'):
        if x.get('status')=='verified_fixture_response': total_receipts[str(x.get('match_id'))]=x
    counts=Counter(); market_rows={m:[] for m in ('AH','OU')}; hashes=set()
    for fixture in manifest.get('rows',[]):
        mid=str(fixture.get('match_id') or ''); f=forecasts.get(mid)
        if not f: continue
        asof=instant(f.get('prediction_asof_utc')); train=instant(f.get('train_end_utc')); kickoff=instant(f.get('kickoff'))
        if not asof or not train or not kickoff or train>=asof or asof>=kickoff:
            counts['bad_forecast_chronology']+=1; continue
        if (f.get('league'),f.get('home'),f.get('away'),f.get('kickoff'),f.get('home_goals'),f.get('away_goals')) != (fixture.get('league'),fixture.get('home'),fixture.get('away'),fixture.get('kickoff_utc'),fixture.get('home_goals'),fixture.get('away_goals')):
            counts['forecast_fixture_identity_mismatch']+=1; continue
        score_actual=(int(fixture['home_goals']),int(fixture['away_goals']))
        for market in ('AH','OU'):
            chosen=None; source=None; receipt_at=None
            cp=root/'crown-responses'/f'{mid}.json'; crown_quote=None
            if cp.exists():
                try:
                    raw=cp.read_bytes(); payload=json.loads(raw); row=fixture_row(payload,mid)
                    if payload.get('success')==1 and row and row.get('h')==fixture['home'] and row.get('a')==fixture['away'] and row.get('l')==fixture['league']:
                        start=local_to_utc(row.get('start'),zone)
                        if start==kickoff and (int(row.get('hg')),int(row.get('ag')))==score_actual:
                            crown_quote=raw_event(event_rows(row,market,'crown'),market,asof,kickoff,zone)
                            if crown_quote:
                                chosen=crown_quote; source='Crown'
                                receipt_at=instant(crown_receipts.get(mid,{}).get('captured_at_utc'))
                                hashes.add(hashlib.sha256(raw).hexdigest())
                except Exception: counts['invalid_crown_response']+=1
            if chosen is None:
                tp=root/'totalcorner-default-responses'/f'{mid}.json'; entry=total_receipts.get(mid)
                if tp.exists() and entry:
                    try:
                        raw=tp.read_bytes(); payload=json.loads(raw); row=fixture_row(payload,mid)
                        if payload.get('success')==1 and row and row.get('h')==fixture['home'] and row.get('a')==fixture['away'] and row.get('l')==fixture['league']:
                            start=local_to_utc(row.get('start'),zone)
                            if start==kickoff and ((row.get('hg') is None and row.get('ag') is None) or (int(row.get('hg')),int(row.get('ag')))==score_actual):
                                tq=raw_event(event_rows(row,market,'totalcorner'),market,asof,kickoff,zone)
                                if tq:
                                    chosen=tq;source='TotalCorner_default';receipt_at=instant(entry.get('captured_at_utc'));hashes.add(hashlib.sha256(raw).hexdigest())
                    except Exception: counts['invalid_totalcorner_response']+=1
            if not chosen: continue
            observed,line,prices=chosen
            grid=f.get('prediction',{}).get('grid')
            if not isinstance(grid,list): counts['missing_score_grid']+=1; continue
            try:
                mass=math.fsum(float(v) for row in grid for v in row)
                if abs(mass-1)>1e-7 or any(not math.isfinite(float(v)) or float(v)<0 for row in grid for v in row): raise ValueError
                sides=('home','away') if market=='AH' else ('over','under')
                ev=[expected_return(grid,market,s,line,p) for s,p in zip(sides,prices)]
                side_idx=0 if ev[0]>=ev[1] else 1; side=sides[side_idx]; price=prices[side_idx]
                legs,category=legs_result(market,side,line,*score_actual); pnl=payout(legs,price)
                distribution=defaultdict(float)
                for h,row in enumerate(grid):
                    for away,prob in enumerate(row):
                        _,cat=legs_result(market,side,line,h,away);distribution[cat]+=float(prob)
                market_rows[market].append({'pnl':pnl,'category':category,'distribution':distribution,
                   'event_utc':observed.isoformat(),'kickoff_utc':kickoff.isoformat(),
                   'source':source,'receipt_before_kickoff':bool(receipt_at and receipt_at<kickoff)})
                counts[f'{market}_{source}']+=1
            except Exception: counts['invalid_forecast_or_settlement']+=1
    result={'protocol':'M5_CROWN_FIRST_TOTALCORNER_FALLBACK_EVENT_TIME_REPLAY_V1','generated_utc':utc_now(),
      'input_hashes':{'candidate_manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),'forecast_sha256':hashlib.sha256(forecast_raw).hexdigest(),'quote_response_hash_set_sha256':hashlib.sha256('\n'.join(sorted(hashes)).encode()).hexdigest()},
      'candidate_fixtures':len(manifest.get('rows',[])),'forecast_rows':len(forecasts),
      'source_selection':'Per fixture-market, latest valid Crown source event at/after prediction as-of and before kickoff; TotalCorner default only if that Crown fixture-market is absent. No duplicate fixture-market bets. One unit per selected side; no EV threshold.',
      'timing_note':'Historical API responses were fetched after fixtures. Pre-kickoff source event timestamps support event-time retrospective replay only; they do not prove contemporaneous pre-kickoff receipt or executable price.',
      'markets':{m:summarize(rows,m,seed=20261105+(0 if m=='AH' else 1)) for m,rows in market_rows.items()},
      'audit_counts':dict(counts)}
    out=a.output.expanduser().resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_name(out.name+f'.tmp-{os.getpid()}');tmp.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8');os.replace(tmp,out)
    print(json.dumps({'generated_utc':result['generated_utc'],'markets':result['markets'],'candidate_fixtures':result['candidate_fixtures']},ensure_ascii=False,sort_keys=True))

def main():
    p=argparse.ArgumentParser();p.add_argument('--private-dir',type=Path,required=True);p.add_argument('--source-timezone',default='Asia/Shanghai');p.add_argument('--output',type=Path,required=True);run(p.parse_args())
if __name__=='__main__': main()
