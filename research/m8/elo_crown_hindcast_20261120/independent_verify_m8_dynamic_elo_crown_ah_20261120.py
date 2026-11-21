#!/usr/bin/env python3
"""Independent AH settlement and provenance verifier for the Elo research ledgers."""
import gzip, hashlib, json, math
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
SCORES=Path('/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl')
MARKETS=Path('/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl')
FROZEN=Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
RECEIPTS=Path('/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')
FT=Path('/Users/mac/QuantAsiaDesk/research-work/m7/m7_actual_received_Crown_verified_FT_index_20261110_v3.jsonl')
PRED=HERE/'m8_dynamic_elo_crown_ah_predictions_20261120.jsonl.gz'
RPRED=HERE/'m8_dynamic_elo_crown_ah_true_receipt_replay_20261120.jsonl.gz'

def jl(p): return [json.loads(x) for x in p.open(encoding='utf-8') if x.strip()]
def gz(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]
def settlement(line,side,hg,ag,odds):
    line=float(line);odds=float(odds)
    legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
    values=[]
    for leg in legs:
        margin=hg-ag+leg if side=='home' else ag-hg-leg
        values.append(odds-1 if margin>1e-9 else -1 if margin<-1e-9 else 0)
    state='full_win' if all(v>0 for v in values) else 'half_win' if any(v>0 for v in values) else 'push' if all(v==0 for v in values) else 'half_loss' if any(v==0 for v in values) else 'full_loss'
    return sum(values)/len(values),state

scores={str(x['fid']):x for x in jl(SCORES)}
markets={str(x['fid']):x for x in jl(MARKETS)}
frozen={str(x['fid']):x for x in jl(FROZEN)}
pred=gz(PRED)
seen=Counter();sums=defaultdict(float);unique_by_method={m:set() for m in ('CROWN_ONLY','ELO_CONTRACT','CROWN_PLUS_ELO')}
for r in pred:
    m=r['method'];fid=str(r['fid']);seen[m]+=1;unique_by_method[m].add(fid)
    assert fid in scores and fid in markets, fid
    src=markets[fid];sc=scores[fid]
    assert str(r['end_line'])==str(src['end_line']) or abs(float(r['end_line'])-float(src['end_line']))<1e-12
    assert abs(float(r['home_price'])-float(src['home_price']))<1e-12
    assert abs(float(r['away_price'])-float(src['away_price']))<1e-12
    assert int(r['hg'])==int(sc['hg']) and int(r['ag'])==int(sc['ag'])
    assert bool(r['original_eight_overlap'])==(fid in frozen)
    assert bool(r['unique_incremental'])==(fid not in frozen)
    assert r['selected_side'] in ('home','away')
    u,s=settlement(src['end_line'],r['selected_side'],int(sc['hg']),int(sc['ag']),r['selected_price'])
    assert abs(u-float(r['net_u']))<1e-9 and s==r['settlement'], (fid,u,r['net_u'],s,r['settlement'])
    sums[m]+=u
    probs=r['predicted_probs'];assert abs(sum(float(x) for x in probs.values())-1)<1e-8
    evside=r['ev_positive_side']
    if evside:
        eu,es=settlement(src['end_line'],evside,int(sc['hg']),int(sc['ag']),src[f'{evside}_price'])
    else: eu,es=0.0,'no_bet'
    assert abs(eu-float(r['ev_positive_net_u']))<1e-9 and es==r['ev_positive_settlement']
assert len(pred)==sum(seen.values()) and len(set.intersection(*unique_by_method.values()))==len(unique_by_method['CROWN_ONLY'])
assert all(x==unique_by_method['CROWN_ONLY'] for x in unique_by_method.values())
assert all(len(x-set(frozen))==21455 for x in unique_by_method.values())

ft={str(x.get('match_id')):x for x in jl(FT) if x.get('status')=='verified_ft'}
receipt_archive=jl(RECEIPTS);by_fid=defaultdict(list)
for x in receipt_archive: by_fid[str(x.get('fixture_id'))].append(x)
receipt_rows=gz(RPRED)
assert len(receipt_rows)==84, len(receipt_rows)
receipt_sum=0.0
for r in receipt_rows:
    assert r['method']=='CROWN_ONLY' and r['true_crown_http_receipt'] is True
    fid=str(r['fid']);assert fid in ft and fid in by_fid
    ftrow=ft[fid];assert int(ftrow['home_goals'])==int(r['hg']) and int(ftrow['away_goals'])==int(r['ag'])
    assert int(ftrow['home_goals'])>=0 and int(ftrow['away_goals'])>=0
    matches=[x for x in by_fid[fid] if datetime.fromisoformat(x['received_utc'].replace('Z','+00:00'))==datetime.fromisoformat(r['received_utc'].replace('Z','+00:00')) and x.get('raw_sha256')==r['raw_sha256']]
    assert matches, fid
    origin=matches[0];rawdoc=json.load(open(origin['source_file'],encoding='utf-8'))
    rawstr=rawdoc['raw_response'];assert hashlib.sha256(rawstr.encode()).hexdigest()==r['raw_sha256']
    raw=json.loads(rawstr);event=next(e for e in raw.get('data',[]) if str(e.get('id'))==fid)
    crown=next(b for b in event.get('bookmakers',[]) if b.get('slug')=='crown')
    assert any(len(q)>=5 and abs(float(q[1])-float(r['line']))<1e-9 and abs(float(q[2])-float(r['home_price']))<1e-9 and abs(float(q[3])-float(r['away_price']))<1e-9 for q in crown.get('asian_list',[]))
    u,s=settlement(r['line'],r['selected_side'],int(ftrow['home_goals']),int(ftrow['away_goals']),r['selected_price'])
    assert abs(u-float(r['net_u']))<1e-9 and s==r['settlement'],fid
    receipt_sum+=u

out={'historical_rows_per_method':dict(seen),'unique_test_fids_per_method':{m:len(v) for m,v in unique_by_method.items()},'new_fids_per_method':{m:len(v-set(frozen)) for m,v in unique_by_method.items()},'historical_net_u_recomputed':dict(sums),'receipt_crown_only_rows':len(receipt_rows),'receipt_net_u_recomputed':round(receipt_sum,6),'quarter_lines_recalculated':True,'frozen_fid_overlap_checked':True,'receipt_raw_sha_and_exact_crown_quote_checked':True,'verified_ft_rechecked':True}
print(json.dumps(out,indent=2))
