#!/usr/bin/env python3
"""Independent Crown SQLite, fixture identity, FT, AH and FID audit."""
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, sqlite3

ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=ROOT/'research/m8/formation_matchup_20261120'
DB=pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
PATHS=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl')
SCORES=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl')
FROZEN=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
SCHEDULE=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl')
UTC=dt.timezone.utc
def readj(p):
    with p.open(encoding='utf8') as f:
        for s in f:
            if s.strip():yield json.loads(s)
def iso(s):return dt.datetime.fromisoformat(str(s).replace('Z','+00:00'))
def settle(line,side,hg,ag,odds):
    x=float(line) if side=='home' else -float(line)
    gd=int(hg)-int(ag) if side=='home' else int(ag)-int(hg)
    if abs(float(line)*4-round(float(line)*4))>1e-8:raise ValueError('line grid')
    legs=[x] if abs(x*2-round(x*2))<1e-9 else [math.floor(x*2)/2,math.ceil(x*2)/2]
    vals=[]
    for leg in legs:
        d=gd+leg; vals.append(float(odds)-1 if d>1e-9 else -1. if d< -1e-9 else 0.)
    s=''.join('W' if v>0 else 'L' if v<0 else 'P' for v in vals)
    label={'W':'full_win','WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss','L':'full_loss','P':'push'}[s]
    return round(sum(vals)/len(vals),6),label
def main():
    scores={str(x['fid']):x for x in readj(SCORES)}
    paths={str(x['fid']):x for x in readj(PATHS)}
    frozen={str(x['fid']) for x in readj(FROZEN)}
    schedule={str(x['match_id']):x for x in readj(SCHEDULE)}
    rows=[json.loads(s) for s in gzip.open(OUT/'formation_matchup_per_fixture_20261120.jsonl.gz','rt',encoding='utf8') if s.strip()]
    probs=collections.Counter(); price_errors=[]; id_errors=[]; pnl_errors=[]; result_rows=[]; seen=set()
    db=sqlite3.connect(f'file:{DB}?mode=ro',uri=True)
    qsql="""SELECT q.sequence_index,q.handicap_home,q.home_decimal,q.away_decimal,q.quote_source_at_utc,
                     c.capture_mode,c.response_sha256,c.source_file,c.kickoff_at_utc
              FROM asian_quote q JOIN capture c USING(capture_key)
              WHERE q.fixture_id=? AND q.quote_kind='movement' AND q.quote_source_at_utc IS NOT NULL"""
    for r in rows:
        fid=str(r['fid']); probs['ledger_rows']+=1
        if fid in seen:probs['duplicate_test_fid']+=1
        seen.add(fid)
        s=scores.get(fid); sc=schedule.get(fid); p=paths.get(fid)
        if not sc:id_errors.append({'fid':fid,'reason':'missing_schedule'});continue
        if int(sc['home_goals'])!=int(r['hg']) or int(sc['away_goals'])!=int(r['ag']):
            id_errors.append({'fid':fid,'reason':'FT_mismatch'});continue
        if str(sc['home'])!=str(r['home']) or str(sc['away'])!=str(r['away']) or str(sc['league_id'])!=str(r['league_id']):
            id_errors.append({'fid':fid,'reason':'schedule_identity_mismatch'});continue
        if s and (int(s['hg'])!=int(r['hg']) or int(s['ag'])!=int(r['ag']) or str(s['league'])!=str(r['league_id'])):
            id_errors.append({'fid':fid,'reason':'independent_score_identity_FT_mismatch'});continue
        ko=iso(r['kickoff_utc']).astimezone(UTC); cutoff=ko-dt.timedelta(hours=1)
        qs=[]
        for q in db.execute(qsql,(fid,)):
            try:
                ts=iso(q[4]).astimezone(UTC)
                capture_ko=iso(q[8]).astimezone(UTC)
                if ts<=cutoff and ts<=capture_ko-dt.timedelta(hours=1) and q[5]=='historical' and float(q[2])>1 and float(q[3])>1:
                    qs.append((ts,int(q[0]),q))
            except Exception:continue
        if not qs:
            price_errors.append({'fid':fid,'reason':'no_historical_quote_before_T1'});continue
        # T1 price is the latest Crown movement event at or before kickoff - 1h.
        q=max(qs,key=lambda z:(z[0],z[1]))[2]
        if abs(float(q[1])-float(r['line']))>1e-8 or abs(float(q[2])-float(r['home_odds']))>1e-8 or abs(float(q[3])-float(r['away_odds']))>1e-8:
            price_errors.append({'fid':fid,'reason':'Crown_T1_price_mismatch','db':[q[1],q[2],q[3]],'ledger':[r['line'],r['home_odds'],r['away_odds']]});continue
        if r.get('Crown_response_sha256') and str(q[6])!=str(r['Crown_response_sha256']):
            price_errors.append({'fid':fid,'reason':'Crown_raw_response_SHA_mismatch','db':q[6],'ledger':r['Crown_response_sha256']});continue
        if p and (abs(float(p['end_line'])-float(r['line']))>1e-8 or abs(float(p['home_price'])-float(r['home_odds']))>1e-8 or abs(float(p['away_price'])-float(r['away_odds']))>1e-8):
            price_errors.append({'fid':fid,'reason':'original_path_input_mismatch'});continue
        probs['raw_Crown_T1_price_match']+=1
        for m in ('market','market_plus_formation'):
            side=r[f'{m}_chosen_side'];odds=float(r['home_odds'] if side=='home' else r['away_odds'])
            pnl,label=settle(r['line'],side,r['hg'],r['ag'],odds)
            if abs(pnl-float(r[f'{m}_pnl_always_U']))>1e-6 or label!=r[f'{m}_settlement_always']:
                pnl_errors.append({'fid':fid,'method':m,'expected':[pnl,label],'actual':[r[f'{m}_pnl_always_U'],r[f'{m}_settlement_always']]})
            for suffix in ('ev_positive',):
                observed= pnl if r[f'{m}_bet_{suffix}'] else 0.
                if abs(observed-float(r[f'{m}_pnl_{suffix}_U']))>1e-6:pnl_errors.append({'fid':fid,'method':m+suffix,'expected':observed,'actual':r[f'{m}_pnl_{suffix}_U']})
        result_rows.append(r)
    candidate_ids={r['fid'] for r in result_rows if not r['frozen_member']}
    probs['frozen_overlap_fids']=len(candidate_ids&frozen);probs['candidate_unique_FIDs']=len(candidate_ids)
    probs['live_capture_FIDs']=db.execute("SELECT COUNT(DISTINCT fixture_id) FROM capture WHERE capture_mode='live' AND fixture_id IN (%s)" % ','.join('?'*len(seen)),tuple(seen)).fetchone()[0] if seen else 0
    result={'study':'M8_CROWN_AH_HISTORICAL_FORMATION_MATCHUP_INDEPENDENT_AUDIT','checked_prediction_rows':len(rows),
      'counts':dict(probs),'price_issues':len(price_errors),'identity_FT_issues':len(id_errors),'settlement_issues':len(pnl_errors),
      'price_issue_examples':price_errors[:20],'identity_issue_examples':id_errors[:20],'settlement_issue_examples':pnl_errors[:20],
      'settlement':'independently reimplemented; equal half-stakes for quarter lines','pass':not price_errors and not id_errors and not pnl_errors and not probs['duplicate_test_fid'] and not probs['frozen_overlap_fids']}
    (OUT/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
