#!/usr/bin/env python3
"""Independent FID, AH-leg settlement, and summary reconciliation."""
import collections, datetime as dt, gzip, json, math, pathlib, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).resolve().parent
LEDGER=OUT/'referee_discipline_interaction_per_fixture_20261121.jsonl.gz'
SUMMARY=OUT/'referee_discipline_interaction_summary_20261121.json'
FOUNDATION=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
PR69=ROOT/'research/m8/referee_market_residual_20261120/referee_market_residual_per_fixture.jsonl.gz'

def load_gz(p):
    with gzip.open(p,'rt',encoding='utf8') as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def load_jsonl(p):
    with open(p,encoding='utf8') as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def settle(line,side,gd,odds):
    # Independent implementation: signed contract, then split quarter AH into
    # adjacent half-goal legs. Return class and mean net return per 1U.
    h=float(line) if side=='home' else -float(line)
    m=int(gd) if side=='home' else -int(gd)
    q=h*4
    if abs(q-round(q))>1e-8: raise ValueError('line is not on quarter-goal grid')
    if round(q)%2==0: legs=[h]
    else:
        lo=math.floor(h*2)/2
        legs=[lo,lo+.5]
    pnl=[]; states=[]
    for x in legs:
        z=m+x
        states.append('W' if z>1e-9 else 'L' if z< -1e-9 else 'P')
        pnl.append(float(odds)-1 if z>1e-9 else -1. if z< -1e-9 else 0.)
    net=sum(pnl)/len(pnl)
    label=('full_win' if all(x=='W' for x in states) else
           'full_loss' if all(x=='L' for x in states) else
           'push' if all(x=='P' for x in states) else
           'half_win' if net>0 else 'half_loss' if net<0 else 'push')
    return label,net
def calc(rows):
    bets=[r for r in rows if r['chosen_side'] is not None]
    n=len(bets);u=sum(float(r['net_u']) for r in bets);daily=collections.defaultdict(float)
    for r in bets: daily[r['date']]+=float(r['net_u'])
    c=peak=mdd=0.
    for day in sorted(daily):
        c+=daily[day];peak=max(peak,c);mdd=max(mdd,peak-c)
    ds=[dt.date.fromisoformat(r['date']) for r in bets]
    weeks=((max(ds)-min(ds)).days//7+1) if ds else 1
    return {'n':n,'net_U':round(u,6),'ROI_pct':round(100*u/n,6) if n else None,
            'MDD_U':round(mdd,6),'orders_per_week':round(n/weeks,6) if n else 0.}
def main():
    records=list(load_gz(LEDGER)); summary=json.loads(SUMMARY.read_text())
    frozen_rows=[{'fid':str(r['fid']),'date':str(r['date'])[:10],'net_u':float(r['pnl']),'chosen_side':'frozen'} for r in load_jsonl(FOUNDATION)]
    frozen={r['fid'] for r in frozen_rows}
    source=list(load_gz(PR69)); pr={str(r['fid']):r for r in source}
    errors=collections.Counter(); by_method=collections.defaultdict(list)
    for r in records:
        if r['frozen_overlap'] != (r['fid'] in frozen): errors['frozen_membership_flag_mismatch']+=1
        cutoff=dt.date.fromisoformat(r['date'])-dt.timedelta(days=3)
        v=r.get('ref_prior_max_date_365')
        if v and dt.date.fromisoformat(v)>=cutoff: errors['referee_history_cutoff']+=1
        for name,row in r.items():
            if name.endswith('_cutoff') and name=='discipline_cutoff':
                # The generating history uses completed matches with the
                # declared three-day UTC-calendar lag, audited in R48 source.
                if '3 UTC calendar days' not in row: errors['discipline_cutoff_label']+=1
        old=pr.get(r['fid'])
        if old is None: errors['missing_pr69_crown_audit_fid']+=1
        elif (str(r['league']),str(r['home_id']),str(r['away_id']),int(r['hg']),int(r['ag']),float(r['line']),float(r['home_odds']),float(r['away_odds'])) != (str(old['league']),str(old['home']),str(old['away']),int(old['hg']),int(old['ag']),float(old['line']),float(old['home_odds']),float(old['away_odds'])):
            errors['pr69_identity_quote_ft_mismatch']+=1
        side=r['chosen_side']
        if side is not None:
            price=float(r['home_odds'] if side=='home' else r['away_odds'])
            state,net=settle(r['line'],side,r['gd'],price)
            if state!=r['settlement'] or abs(net-float(r['net_u']))>1e-8: errors['independent_settlement_mismatch']+=1
        by_method[r['method']].append(r)
    checks={}
    for method,rows in by_method.items():
        ids=[r['fid'] for r in rows]
        if len(ids)!=len(set(ids)): errors['duplicate_fid_'+method]+=1
        outside=[r for r in rows if not r['frozen_overlap']]
        metrics=calc(outside);checks[method]=metrics
        exp=summary['models'][method]['incremental_outside_frozen']
        for k,a,b in [('n','n','n'),('net_U','net_U','net_U'),('ROI_pct','ROI_pct','ROI_pct'),('MDD_U','MDD_U','MDD_U'),('orders_per_week','orders_per_week','orders_per_week')]:
            if metrics[a]!=exp[b]:errors['summary_'+method+'_'+k]+=1
        cand=[r for r in rows if not r['frozen_overlap']]
        union=frozen_rows+cand
        union_metric=calc(union)
        union_exp=summary['frozen_plus_candidate_full_frozen_union'][method]
        for k in ('n','net_U','ROI_pct','MDD_U'):
            if union_metric[k]!=union_exp[k]:errors['full_union_'+method+'_'+k]+=1
    candidate_sets=[{r['fid'] for r in rr if not r['frozen_overlap']} for rr in by_method.values()]
    if candidate_sets and any(s!=candidate_sets[0] for s in candidate_sets[1:]): errors['methods_not_same_candidate_cohort']+=1
    result={'per_fixture_rows':len(records),'methods':len(by_method),'unique_candidate_fids':len(set(r['fid'] for r in records)),
            'candidate_outside_frozen_unique_fids':len(set(r['fid'] for r in records if not r['frozen_overlap'])),
            'shared_fids_reconciled_to_PR69_raw_crown_FT_audit':len(set(r['fid'] for r in records)&set(pr)),
            'independent_metrics':checks,'errors':dict(errors),'pass':not errors,
            'sha256':{str(p):sha(p) for p in (LEDGER,SUMMARY,FOUNDATION,PR69)}}
    (OUT/'independent_verification_20261121.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sha256'},ensure_ascii=False,indent=2))
    if errors: raise SystemExit('Independent verification failed')
if __name__=='__main__': main()
