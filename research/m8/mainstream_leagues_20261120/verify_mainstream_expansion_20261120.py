#!/usr/bin/env python3
"""Independent Crown-path/FT, AH settlement and FID audit for M8 league study."""
import collections, datetime as dt, gzip, hashlib, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
D=ROOT/'research/m8/mainstream_leagues_20261120'
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
PATH=WORK/'m8_late_full_path_water_features_20261114.jsonl'
SCORES=WORK/'m8_independent_score_strength_20261114.jsonl'
MEM=WORK/'m8_foundation_20261115/historical_membership.jsonl'
M8=ROOT/'research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl'
TZ=dt.timezone(dt.timedelta(hours=8))

def readj(p):
    with p.open(encoding='utf8') as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def settle(line, side, odds, hg, ag):
    signed=float(line)*(1 if side=='home' else -1)
    gd=(int(hg)-int(ag))*(1 if side=='home' else -1)
    q=signed*2
    legs=[signed] if abs(q-round(q))<1e-9 else [math.floor(q)/2,math.ceil(q)/2]
    outcomes=[];pnl=0.0
    for leg in legs:
        x=gd+leg
        if x>1e-9: outcomes.append('W');pnl+=(float(odds)-1)/len(legs)
        elif x < -1e-9: outcomes.append('L');pnl-=1/len(legs)
        else: outcomes.append('P')
    state={'W':'full_win','L':'full_loss','P':'push','WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss'}[''.join(outcomes)]
    return round(pnl,10),state

def metrics(rows):
    rows=list(rows); daily=collections.defaultdict(float)
    for r in rows: daily[r['date']]+=float(r['net_u'])
    eq=peak=mdd=0.0
    for day in sorted(daily):
        eq+=daily[day];peak=max(peak,eq);mdd=max(mdd,peak-eq)
    return {'n':len(rows),'net_u':round(sum(float(r['net_u']) for r in rows),6),
            'roi_pct':round(100*sum(float(r['net_u']) for r in rows)/len(rows),6) if rows else None,
            'mdd_u':round(mdd,6)}

def close(a,b,tol=1e-5): return a is not None and b is not None and abs(float(a)-float(b))<=tol

def main():
    result=json.loads((D/'M8_MAINSTREAM_LEAGUE_RESULTS_20261120.json').read_text())
    paths={str(x['fid']):x for x in readj(PATH)}
    scores={str(x['fid']):x for x in readj(SCORES)}
    frozen={str(x['fid']):x for x in readj(MEM)}
    choices=result['annual_training_side_choices']
    all_rows=[]; seen=set(); errors=collections.Counter(); by_method=collections.defaultdict(list)
    folds=collections.defaultdict(list)
    with gzip.open(D/'per_fixture_league_predictions_20261120.jsonl.gz','rt',encoding='utf8') as f:
        for line in f:
            r=json.loads(line);fid=str(r['fid']);method=r['strategy'];key=(method,fid)
            if key in seen: errors['duplicate_method_fid']+=1;continue
            seen.add(key)
            p=paths.get(fid);s=scores.get(fid)
            if p is None or s is None: errors['source_fid_missing']+=1;continue
            try:
                ko=dt.datetime.fromisoformat(str(s['ko']).replace('Z','+00:00'))
                date=ko.astimezone(TZ).date().isoformat()
                hg,ag=int(s['hg']),int(s['ag']);line0=float(p['end_line']);ho=float(p['home_price']);ao=float(p['away_price'])
                if (str(p['league'])!=str(s['league']) or str(r['league'])!=str(p['league']) or
                    str(r['home_id'])!=str(s['home']) or str(r['away_id'])!=str(s['away']) or
                    date!=r['date'] or (hg,ag)!=(int(r['FT_home']),int(r['FT_away'])) or
                    not close(line0,r['home_line'],1e-8) or not close(ho,r['home_odds'],1e-8) or not close(ao,r['away_odds'],1e-8)):
                    errors['crown_path_ft_identity_mismatch']+=1;continue
                hp,hs=settle(line0,'home',ho,hg,ag);ap,ass=settle(line0,'away',ao,hg,ag)
                if not close(hp,p.get('end_home_U'),1e-8) or not close(ap,p.get('end_away_U'),1e-8):errors['source_path_settlement_mismatch']+=1;continue
                if r['frozen_eight']!=(fid in frozen):errors['frozen_membership_mismatch']+=1
                if not close(r['home_net_u'],hp,1e-8) or not close(r['away_net_u'],ap,1e-8) or r['home_settlement']!=hs or r['away_settlement']!=ass:
                    errors['ledger_both_sides_settlement_mismatch']+=1;continue
                fav='home' if ho<=ao else 'away';dog='away' if fav=='home' else 'home'
                side=r['direction']
                if method=='universal_crown_favorite_baseline' and side!=fav:errors['favorite_direction_mismatch']+=1
                if method=='universal_crown_underdog_baseline' and side!=dog:errors['underdog_direction_mismatch']+=1
                if method=='league_prior_favorite_vs_underdog':
                    ch=choices.get(f"{r['league']}:{r['year']}",{}).get('selected_side')
                    if ch!=r['selected_prior_side'] or side!=(fav if ch=='favorite' else dog):errors['walkforward_choice_mismatch']+=1
                rp=hp if side=='home' else ap;rs=hs if side=='home' else ass
                if not close(rp,r['net_u'],1e-8) or rs!=r['settlement']:errors['prediction_settlement_mismatch']+=1;continue
                all_rows.append(r);by_method[method].append(r)
                if not r['frozen_eight']:folds[(method,int(r['year']))].append(r)
            except Exception: errors['malformed_row']+=1
    # Recompute each method's complete out-of-eight, annual, weekly, league and union totals.
    summary_checks={};stat=result['strategy_results_outside_original_eight']
    for method,rs in by_method.items():
        outside=[r for r in rs if not r['frozen_eight']]
        got=metrics(outside);want=stat[method]
        for k in ('n','net_u','roi_pct','mdd_u'):
            if not close(got[k],want.get(k),1e-5):errors[f'{method}_overall_{k}_mismatch']+=1
        annual={}
        for y in sorted({int(r['year']) for r in outside}):
            annual[str(y)]=metrics(r for r in outside if int(r['year'])==y)
            w=want.get('year',{}).get(str(y),{})
            for k in ('n','net_u','roi_pct'):
                if not close(annual[str(y)].get(k),w.get(k),1e-5):errors[f'{method}_{y}_{k}_mismatch']+=1
        summary_checks[method]={'outside_eight':got,'annual':annual}
    selected='league_prior_favorite_vs_underdog'
    chosen=[r for r in by_method[selected] if not r['frozen_eight']]
    if len({r['fid'] for r in chosen})!=len(chosen):errors['selected_duplicate_fid']+=1
    # Assert prior choices use only earlier-year fixtures in that same league.
    # Rebuild the historical train inventory directly from source-event Crown
    # paths and FT, including pre-2022 records which have no prediction rows.
    fixtures=[]
    for fid,p in paths.items():
        s=scores.get(fid)
        if s is None: continue
        try:
            ko=dt.datetime.fromisoformat(str(s['ko']).replace('Z','+00:00'))
            year=ko.astimezone(TZ).year
            if year<2019 or year>2026: continue
            hg,ag=int(s['hg']),int(s['ag']);line0=float(p['end_line']);ho=float(p['home_price']);ao=float(p['away_price'])
            hp,hs=settle(line0,'home',ho,hg,ag);ap,ass=settle(line0,'away',ao,hg,ag)
            if not close(hp,p.get('end_home_U'),1e-8) or not close(ap,p.get('end_away_U'),1e-8):continue
            fav='home' if ho<=ao else 'away';dog='away' if fav=='home' else 'home'
            fixtures.append({'fid':fid,'league':str(p['league']),'year':year,'date':ko.astimezone(TZ).date().isoformat(),
                'home_net_u':hp,'away_net_u':ap,'favorite_side':fav,'underdog_side':dog})
        except Exception: continue
    choice_checks=0
    for key,c in choices.items():
        lid,ys=key.split(':');year=int(ys)
        hist=[r for r in fixtures if r['league']==lid and int(r['year'])<year]
        if len(hist)!=int(c['train_n']):errors['walkforward_training_n_mismatch']+=1;continue
        fav=sum(float(r['home_net_u'] if r['favorite_side']=='home' else r['away_net_u']) for r in hist)
        dog=sum(float(r['home_net_u'] if r['underdog_side']=='home' else r['away_net_u']) for r in hist)
        expected='underdog' if hist and dog>fav else 'favorite'
        if expected!=c['selected_side'] or not close(fav,c['favorite_train_net_u']) or not close(dog,c['underdog_train_net_u']):errors['walkforward_training_reconstruction_mismatch']+=1
        choice_checks+=1
    # Rebuild original-eight union from frozen manifest PnL plus candidate ledger; FID-disjoint by construction.
    union=[]
    for fid,x in frozen.items():
        if 2022<=int(x.get('year') or 0)<=2026:
            union.append({'fid':fid,'date':str(x['date']),'net_u':float(x['pnl']),'frozen_eight':True})
    union_fids={r['fid'] for r in union}
    for r in chosen:
        if r['fid'] in union_fids:errors['candidate_frozen_overlap_after_filter']+=1
        else:union_fids.add(r['fid']);union.append({'fid':r['fid'],'date':r['date'],'net_u':r['net_u'],'frozen_eight':False})
    union_got=metrics(union);union_want=result['frozen_eight_union_by_strategy'][selected]
    for k in ('n','net_u','roi_pct','mdd_u'):
        if not close(union_got[k],union_want.get(k),1e-5):errors[f'union_{k}_mismatch']+=1
    # Actual-receipt replay: reconstruct one exact Crown receipt/FT tuple per FID from the independently audited rows.
    aud=collections.defaultdict(list)
    for x in readj(M8):aud[str(x['fid'])].append(x)
    rec_rows=[];rec_seen=set()
    with gzip.open(D/'actual_receipt_replay_per_fixture_20261120.jsonl.gz','rt',encoding='utf8') as f:
        for line in f:
            r=json.loads(line);fid=str(r['fid'])
            if fid in rec_seen:errors['duplicate_actual_receipt_fid']+=1
            rec_seen.add(fid)
            source=aud.get(fid,[])
            tuples={(float(x['line_home']),float(x['odds_home']),float(x['odds_away']),str(x['ft'])) for x in source}
            if len(tuples)!=1:errors['receipt_source_quote_ft_conflict']+=1;continue
            q=next(iter(tuples));parts=str(q[3]).replace(':','-').split('-')
            hg,ag=map(int,parts[:2]);ko=dt.datetime.fromisoformat(str(source[0]['kickoff_utc']).replace('Z','+00:00'))
            recv=dt.datetime.fromisoformat(str(source[0]['received_utc']).replace('Z','+00:00'))
            raw_set={str(x.get('raw_sha256') or '') for x in source};snap_set={str(x.get('snapshot_sha256') or '') for x in source};recv_set={str(x.get('received_utc') or '') for x in source}
            if recv>=ko:errors['receipt_not_pregame']+=1
            if (len(raw_set)!=1 or len(snap_set)!=1 or len(recv_set)!=1 or
                str(r.get('raw_sha256') or '') not in raw_set or str(r.get('snapshot_sha256') or '') not in snap_set or str(r.get('received_utc') or '') not in recv_set or
                len(r.get('raw_sha256') or '')!=64 or any(c not in '0123456789abcdef' for c in str(r.get('raw_sha256') or '').lower()) or
                len(r.get('snapshot_sha256') or '')!=64 or any(c not in '0123456789abcdef' for c in str(r.get('snapshot_sha256') or '').lower()) or
                not close(bool(r['frozen_eight']),fid in frozen,0) or
                not close(q[0],r['home_line'],1e-8) or not close(q[1],r['home_odds'],1e-8) or not close(q[2],r['away_odds'],1e-8) or (hg,ag)!=(int(r['FT_home']),int(r['FT_away']))):
                errors['receipt_quote_ft_or_hash_mismatch']+=1;continue
            side=r['direction'];pnl,state=settle(q[0],side,q[1] if side=='home' else q[2],hg,ag)
            if not close(pnl,r['net_u'],1e-8) or state!=r['settlement']:errors['receipt_pnl_mismatch']+=1;continue
            rec_rows.append(r)
    rec_outside=[r for r in rec_rows if not r['frozen_eight']]
    rec_got=metrics(rec_outside);rec_want=result['actual_http_receipt_replay_outside_original_eight'][selected]
    for k in ('n','net_u','roi_pct','mdd_u'):
        if not close(rec_got[k],rec_want.get(k),1e-5):errors[f'receipt_{k}_mismatch']+=1
    out={'study':'M8 mainstream league expansion independent audit','source_path_unique_fids':len(paths),'score_unique_fids':len(scores),
         'frozen_unique_fids':len(frozen),'prediction_rows_read':sum(map(len,by_method.values())),'methods':summary_checks,
         'selected_unique_outside_eight_fids':len({r['fid'] for r in chosen}),'walkforward_training_choices_reconstructed':choice_checks,
         'merged_original_eight_and_candidate':{'metrics':union_got,'candidate_incremental_net_u':round(sum(r['net_u'] for r in chosen),6)},
         'actual_receipt_rows_replayed':len(rec_rows),'actual_receipt_unique_fids':len(rec_seen),
         'actual_receipt_frozen_overlap_fids':sum(bool(r['frozen_eight']) for r in rec_rows),
         'actual_receipt_outside_eight_fids':len(rec_outside),'actual_receipt_selected_method_outside_eight':rec_got,
         'all_2024_2026_intensive_ids_found':result['input_counts']['intensive_2024_26_target_fids_not_found']==0,
         'errors':dict(errors),'pass':not errors}
    (D/'independent_audit_20261120.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False,indent=2))
    if errors: raise SystemExit(1)

if __name__=='__main__': main()
