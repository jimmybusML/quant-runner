"""M8 I/K/L batch research: nonlinear Crown AH contract interactions and discovery.

Research-only. Reuses the validated local T24/T12 Crown and performance cache;
never edits production rules or the frozen M8 foundation.
"""
import collections, datetime, hashlib, json, math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

P = Path('/Users/mac/QuantAsiaDesk/research-work')
OUT = Path(__file__).resolve().parent
# Reuse the already-run R27 feature builder prefix. It loads exact Crown AH
# prices/lines, fixed cohorts, frozen-year split helpers and past-only shot/SOT
# residual features; stop before its prior experiment loop/output write.
s = (P/'m8_team_shot_residual_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])

manifest = json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
membership_path = P/manifest['historical_membership']['local_file']
foundation_ids = {str(json.loads(line)['fid']) for line in membership_path.open()}
# Candidate cohort is the established R24/R25 incremental cohort; report both
# its full size and post-hoc overlap with the frozen eight.
ids_h = np.array([str(x['fid']) for x in H]); ids_r = np.array([str(x['fid']) for x in R])
foundation_h = np.isin(ids_h, list(foundation_ids)); foundation_r = np.isin(ids_r, list(foundation_ids))
eligible_h = hm.copy(); eligible_r = rm.copy()

receipt_archive_path=P/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
receipt_archive=[json.loads(line) for line in receipt_archive_path.open()]
receipt_by_horizon={}
for z in receipt_archive:
    if z.get('markets',{}).get('AH') and z.get('markets',{}).get('OU') and float(z.get('received_minutes_to_kickoff',-1))>0:
        receipt_by_horizon[(str(z['fixture_id']),str(z['snapshot_horizon']))]=z

def ah_design_features(x, shots, q, interaction_kind):
    base = make_x(x, 'response')
    # Explicit AH line in current T12 contract units; current-side prices are
    # already represented in the market response features.
    line = np.array([float(v['al']) for v in q])[:, None]
    # Features 0/1 are long-horizon team shot total/margin; 4/5 are short-minus-
    # long changes. Past-only history, three UTC-date lag, inherited R27 source.
    if interaction_kind == 'I_line_style':
        z = shots[:, [0,1,4,5]]
        return np.column_stack((base, z, line, line*z))
    if interaction_kind == 'K_path_style':
        z = shots[:, [0,1,4,5]]
        # T24->T12 common-contract total and margin repricing interactions.
        mv = x[:, [4,5]]
        inter = np.column_stack((z[:,0]*mv[:,0], z[:,2]*mv[:,0], z[:,1]*mv[:,1], z[:,3]*mv[:,1]))
        return np.column_stack((base, shots, inter))
    raise ValueError(interaction_kind)

X_I = ah_design_features(hx, hs, H, 'I_line_style')
Z_I = ah_design_features(rx, rs, R, 'I_line_style')
X_K = ah_design_features(hx, hs, H, 'K_path_style')
Z_K = ah_design_features(rx, rs, R, 'K_path_style')
X_BASE = make_x(hx, 'response'); Z_BASE = make_x(rx, 'response')
X_SHOT = np.column_stack((X_BASE, hs)); Z_SHOT = np.column_stack((Z_BASE, rs))

def fit_year_forward(X, Z, mode, market_probs=True):
    total = np.zeros(len(H)); share = np.zeros(len(H)); rtotal = np.zeros(len(R)); rshare = np.zeros(len(R))
    fits = {}
    a,b,c,d = state(hx); ra,rb,rc,rd = state(rx)
    for yr in (2024, 2025, 2026):
        tr = (HY < yr) & history_ind
        te = HY == yr; re = RY == yr
        assert tr.any() and int(HY[tr].max()) < yr
        total[te], bt = fit_total(X[tr], hyn[tr], b[tr], X[te], b[te])
        share[te], bf = fit_share(X[tr], hyh[tr], hyn[tr], d[tr], X[te], d[te])
        if re.any():
            rtotal[re], _ = fit_total(X[tr], hyn[tr], b[tr], Z[re], rb[re])
            rshare[re], _ = fit_share(X[tr], hyh[tr], hyn[tr], d[tr], Z[re], rd[re])
        fits[str(yr)] = {'train_n': int(tr.sum()), 'test_n': int(te.sum()), 'receipt_n': int(re.sum()),
                         'total_coefficients': bt.tolist(), 'share_coefficients': bf.tolist()}
    return total, share, rtotal, rshare, fits

def choose_ev(q, total, fraction):
    # Same correct split-quarter AH probability and Crown decimal price logic as
    # the validated R24-R27 runner. Output actual settled pnl from cached FT.
    w,l = g['ah_wl'](total, fraction, vec(q,'al'))
    ah,aa = vec(q,'ah'),vec(q,'aa')
    home_ev = w*(ah-1)-l
    away_ev = l*(aa-1)-w
    home = home_ev >= away_ev
    actual = np.where(home, vec(q,'home_U'), vec(q,'away_U'))
    return np.where(home, 'home', 'away'), actual, home_ev, away_ev

def monthday(q): return str(q['date'])
def summarize(rows):
    if not rows: return {'n':0,'U':0.0,'ROI_pct':None,'MDD_U':0.0,'wins':0,'losses':0,'pushes':0,'weeks':0,'mean_per_active_week':None}
    rows=sorted(rows,key=lambda x:(x['date'],x['fid']))
    pnl=np.array([float(x['pnl_u']) for x in rows]); dates=sorted(set(x['date'] for x in rows))
    dayp=collections.defaultdict(float)
    for x in rows: dayp[x['date']]+=float(x['pnl_u'])
    peak=cur=0.0; mdd=0.0
    for d0 in sorted(dayp): cur+=dayp[d0]; peak=max(peak,cur); mdd=max(mdd,peak-cur)
    weeks=collections.Counter()
    for x in rows:
        dt=datetime.date.fromisoformat(x['date']); weeks[f'{dt.isocalendar().year}-W{dt.isocalendar().week:02d}']+=1
    return {'n':len(rows),'U':round(float(pnl.sum()),6),'ROI_pct':round(float(pnl.mean()*100),6),
            'MDD_U':round(float(mdd),6),'wins':int((pnl>1e-9).sum()),'losses':int((pnl<-1e-9).sum()),
            'pushes':int((abs(pnl)<=1e-9).sum()),'weeks':len(weeks),
            'mean_per_active_week':round(len(rows)/len(weeks),6),'weekly_counts':dict(sorted(weeks.items()))}

def rows_for(method, q, side, pnl, mask, source, overlap):
    out=[]
    for i in np.where(mask)[0]:
        a=q[i]
        dt=datetime.date.fromisoformat(str(a['date']))
        hz=next((h for h in ('T24','T12','T6','T3','T1') if str(method).endswith('_'+h)), None)
        if hz is None and source=='actual_http_receipt':
            hz=next((h for h in ('T12','T18') if (str(a['fid']),h) in receipt_by_horizon), 'T12')
        hz=hz or 'T12'
        rec=receipt_by_horizon.get((str(a['fid']),hz)) if source=='actual_http_receipt' else None
        out.append({'fid':str(a['fid']),'date':str(a['date']),'kickoff_utc':rec.get('kickoff_utc') if rec else None,'signal_time_utc':rec.get('received_utc') if rec else None,
                    'signal_time_label':f"Verified Crown {hz} HTTP receipt" if rec else 'Historical Crown event replay; exact UTC snapshot time unavailable',
                    'method':method,'decision_horizon':hz,'line_home':float(a['al']),'odds_home_decimal':float(a['ah']),
                    'odds_away_decimal':float(a['aa']),'side':str(side[i]),'pnl_u':round(float(pnl[i]),6),
                    'source_type':source,'foundation_overlap':bool(overlap[i]),
                    'receipt_split':rec.get('snapshot_split') if rec else None,
                    'iso_week':f'{dt.isocalendar().year}-W{dt.isocalendar().week:02d}'})
    return out

methods = {}
all_rows=[]
for name,X,Z in [('market_response',X_BASE,Z_BASE),('I_line_style',X_I,Z_I),('K_path_style',X_K,Z_K),('shot_main_effects',X_SHOT,Z_SHOT)]:
    ht,hf,rt,rf,fits=fit_year_forward(X,Z,name)
    side,pnl,hev,aev=choose_ev(H,ht,hf); rside,rpnl,rhev,raev=choose_ev(R,rt,rf)
    hrows=rows_for(name,H,side,pnl,eligible_h,'historical_event_replay',foundation_h)
    rrows=rows_for(name,R,rside,rpnl,eligible_r,'actual_http_receipt',foundation_r)
    all_rows.extend(hrows+rrows)
    markets={'historical_incremental':summarize(hrows),'receipt':summarize(rrows),'years':{},
             'model_fits':fits,'history_all_cohort':summarize(rows_for(name,H,side,pnl,hm,'historical_event_replay',foundation_h))}
    for yr in (2024,2025,2026):
        markets['years'][str(yr)]=summarize(rows_for(name,H,side,pnl,eligible_h&(HY==yr),'historical_event_replay',foundation_h))
    methods[name]=markets
    brief=lambda z:{k:z.get(k) for k in ('n','U','ROI_pct','MDD_U','weeks','mean_per_active_week')}
    print(name,'hist',brief(markets['historical_incremental']),'receipts',brief(markets['receipt']),flush=True)

# L: interpretable shallow CART on direct AH contract return difference.
# The target is home net-U minus away net-U, so quarter-line half outcomes and
# price are retained. Each year's tree uses only prior years, never target FT.
def feature_L(x, shot, q):
    return np.column_stack((make_x(x,'response'), x[:,[4,5,8,11]], shot[:,[0,1,4,5]],
                            np.array([float(z['al']) for z in q]),
                            np.array([float(z['ah'])-float(z['aa']) for z in q])))
XL=feature_L(hx,hs,H); ZL=feature_L(rx,rs,R)
yret=np.array([float(z['home_U'])-float(z['away_U']) for z in H])
def cart_fit_predict(train_x, train_y, test_x, depth, min_leaf):
    nodes=[]; importances=np.zeros(train_x.shape[1])
    def grow(ix, d):
        yy=train_y[ix]; mean=float(yy.mean()); node={'value':mean,'feature':None,'threshold':None,'left':None,'right':None}
        if d>=depth or len(ix)<2*min_leaf or np.var(yy)<1e-12:
            nodes.append(node); return len(nodes)-1
        best=(float(np.sum((yy-mean)**2)),None,None,None,None)
        for j in range(train_x.shape[1]):
            xx=train_x[ix,j]; order=np.argsort(xx,kind='mergesort'); xs=xx[order]; ys=yy[order]
            if xs[0]==xs[-1]: continue
            cs=np.cumsum(ys); css=np.cumsum(ys*ys); n=len(ys); k0=min_leaf; k1=n-min_leaf
            ks=np.arange(k0,k1+1)
            # Candidate split must lie between distinct neighboring values.
            ks=ks[(xs[ks-1] < xs[ks])]
            if not len(ks): continue
            sl=cs[ks-1]; ssl=css[ks-1]; sr=cs[-1]-sl; ssr=css[-1]-ssl
            sse=(ssl-sl*sl/ks)+(ssr-sr*sr/(n-ks))
            q=int(np.argmin(sse)); gain=best[0]-float(sse[q])
            if gain>0:
                k=int(ks[q]); threshold=float((xs[k-1]+xs[k])/2)
                best=(float(sse[q]),j,threshold,ix[xx<=threshold],ix[xx>threshold])
        if best[1] is None:
            nodes.append(node); return len(nodes)-1
        idx=len(nodes); nodes.append(node); j,t,left,right=best[1:]
        nodes[idx].update({'feature':int(j),'threshold':float(t)})
        importances[j]+=best[0] * -1 # overwritten below using child SSE reduction below
        li=grow(left,d+1); ri=grow(right,d+1)
        nodes[idx].update({'left':li,'right':ri})
        return idx
    root=grow(np.arange(len(train_y)),0)
    pred=[]
    for row in test_x:
        i=root
        while nodes[i]['feature'] is not None:
            n=nodes[i]; i=n['left'] if row[n['feature']]<=n['threshold'] else n['right']
        pred.append(nodes[i]['value'])
    return np.asarray(pred),nodes

tree_results={}
for depth in (2,3):
  for leaf in (300,):
    pred=np.zeros(len(H)); rpred=np.zeros(len(R)); treefits={}
    for yr in (2024,2025,2026):
        tr=(HY<yr)&history_ind; te=HY==yr; re=RY==yr
        assert tr.any() and int(HY[tr].max())<yr
        pred[te],nodes=cart_fit_predict(XL[tr],yret[tr],XL[te],depth,leaf)
        if re.any(): rpred[re],_=cart_fit_predict(XL[tr],yret[tr],ZL[re],depth,leaf)
        treefits[str(yr)]={'train_n':int(tr.sum()),'depth':depth,'min_samples_leaf':leaf,
                           'n_leaves':sum(z['feature'] is None for z in nodes)}
    method=f'L_CART_depth{depth}_leaf{leaf}'
    sideH=np.where(pred>=0,'home','away'); pnlH=np.where(pred>=0,vec(H,'home_U'),vec(H,'away_U'))
    sideR=np.where(rpred>=0,'home','away'); pnlR=np.where(rpred>=0,vec(R,'home_U'),vec(R,'away_U'))
    lh=rows_for(method,H,sideH,pnlH,eligible_h,'historical_event_replay',foundation_h)
    lr=rows_for(method,R,sideR,pnlR,eligible_r,'actual_http_receipt',foundation_r)
    all_rows.extend(lh+lr)
    entry={'historical_incremental':summarize(lh),'receipt':summarize(lr),'years':{},'tree_fits':treefits,
           'history_all_cohort':summarize(rows_for(method,H,sideH,pnlH,hm,'historical_event_replay',foundation_h))}
    for yr in (2024,2025,2026): entry['years'][str(yr)]=summarize(rows_for(method,H,sideH,pnlH,eligible_h&(HY==yr),'historical_event_replay',foundation_h))
    methods[method]=entry
    tree_results[method]=entry
    print(method,{'history':brief(entry['historical_incremental']),'receipt':brief(entry['receipt'])},flush=True)

# J: apply an independently trained shallow direct-contract model at each
# truly available Crown receipt cutoff. Historical event-time replay exists at
# T24/T12; T6/T3/T1 are evaluated only on verified actual HTTP receipts.
def quote_key(q): return tuple(float(q[k]) for k in ('al','ol','ah','aa','oo','ou'))
def cache_quote(q):
    k=quote_key(q)
    if k in cache: return
    al,ol,ah,aa,oo,ou=k
    op=np.array([ou/(oo+ou)]); ap=np.array([aa/(ah+aa)])
    total,ok1,e1=g['solve'](op,.0001,20.,lambda x:g['ou_share'](x,np.array([ol])))
    frac,ok2,e2=g['solve'](ap,.00001,.99999,lambda x:g['ah_share'](total,x,np.array([al])))
    if not (bool(ok1[0]) and bool(ok2[0]) and float(e1[0])<1e-5 and float(e2[0])<1e-5):
        raise ValueError(f'cannot invert Crown quote: {k}')
    cache[k]=(float(total[0]),float(frac[0]))

def actual_q_from_archive(rec, base, hz):
    ah=rec['markets']['AH']; ou=rec['markets']['OU']
    q={'fid':str(base['fid']),'league':str(base['league']),'date':str(base['date']),'year':int(base['year']),
       'home_id':str(base['home_id']),'away_id':str(base['away_id']),'hg':int(base['hg']),'ag':int(base['ag']),
       'al':float(ah['line']),'ah':float(ah['odds']['home']),'aa':float(ah['odds']['away']),
       'ol':float(ou['line']),'oo':float(ou['odds']['over']),'ou':float(ou['odds']['under']),
       'age_ah':float(ah.get('source_age_minutes_at_actual_receipt',0)),
       'age_ou':float(ou.get('source_age_minutes_at_actual_receipt',0))}
    q['home_U']=settle_ah(q['hg']-q['ag'],q['al'],q['ah'])
    q['away_U']=settle_ah(q['ag']-q['hg'],-q['al'],q['aa'])
    q['_kickoff_utc']=rec.get('kickoff_utc'); q['_received_utc']=rec.get('received_utc'); q['_horizon']=hz
    return q

def settle_ah(goal_diff, handicap, odds):
    lo=math.floor(float(handicap)*2+1e-10)/2
    hi=math.ceil(float(handicap)*2-1e-10)/2
    ans=0.0
    for h in (lo,hi):
        z=float(goal_diff)+h
        if z>1e-9: ans+=0.5*(float(odds)-1)
        elif z<-1e-9: ans-=0.5
    return round(ans,10)

settlement_audit={'historical_quote_sides_checked':0,'historical_mismatches':0}
for p0 in hist:
    for q0 in p0:
        hu=settle_ah(int(q0['hg'])-int(q0['ag']),float(q0['al']),float(q0['ah']))
        au=settle_ah(int(q0['ag'])-int(q0['hg']),-float(q0['al']),float(q0['aa']))
        settlement_audit['historical_quote_sides_checked']+=2
        if not (math.isclose(hu,float(q0['home_U']),abs_tol=1e-8) and math.isclose(au,float(q0['away_U']),abs_tol=1e-8)):
            settlement_audit['historical_mismatches']+=1
assert settlement_audit['historical_mismatches']==0,settlement_audit

hist_by_horizon={}
for hz,ix in [('T24',0),('T12',1)]:
    qh=[p[ix] for p in hist]
    ph=[(p[0],p[ix]) for p in hist]
    for _,q in ph: cache_quote(q)
    _,xarr=latent(ph)
    hist_by_horizon[hz]=(qh,xarr)

actual_by_horizon={}
pair_r_by_fid={str(p[0]['fid']):p for p in pairs}
rindex={str(q['fid']):i for i,q in enumerate(R)}
for hz in ('T24','T12','T6','T3','T1'):
    qrows=[]; xrows=[]; srows=[]; overlaps=[]; recs=[]
    for q0 in R:
        fid=str(q0['fid']); rec=receipt_by_horizon.get((fid,hz))
        if rec is None: continue
        base_pair=pair_r_by_fid.get(fid)
        if base_pair is None: continue
        if not eligible_r[rindex[fid]]: continue
        tq=actual_q_from_archive(rec,q0,hz)
        first=base_pair[0]
        cache_quote(first); cache_quote(tq)
        valid,xx=latent([(first,tq)])
        if not valid[0]: continue
        qrows.append(tq);xrows.append(xx[0]);srows.append(rs[rindex[fid]])
        overlaps.append(fid in foundation_ids);recs.append(rec)
    if qrows:
        actual_by_horizon[hz]=(qrows,np.asarray(xrows),np.asarray(srows),np.asarray(overlaps),recs)

def cart_model(X,y,depth=3,leaf=300):
    # Use existing deterministic greedy tree routine and return a compact model
    # closure represented by split nodes plus leaves.
    nodes=[]
    def grow(ix,d):
        yy=y[ix]; mean=float(yy.mean()); node={'value':mean,'feature':None,'threshold':None,'left':None,'right':None}
        if d>=depth or len(ix)<2*leaf or np.var(yy)<1e-12:
            nodes.append(node);return len(nodes)-1
        best=(float(np.sum((yy-mean)**2)),None,None,None,None)
        for j in range(X.shape[1]):
            xx=X[ix,j]; order=np.argsort(xx,kind='mergesort'); xs=xx[order]; ys=yy[order]
            if xs[0]==xs[-1]:continue
            cs=np.cumsum(ys);css=np.cumsum(ys*ys);n=len(ys);ks=np.arange(leaf,n-leaf+1);ks=ks[xs[ks-1]<xs[ks]]
            if not len(ks):continue
            sl=cs[ks-1];ssl=css[ks-1];sr=cs[-1]-sl;ssr=css[-1]-ssl
            sse=(ssl-sl*sl/ks)+(ssr-sr*sr/(n-ks));u=int(np.argmin(sse));gain=best[0]-float(sse[u])
            if gain>0:
                k=int(ks[u]);t=float((xs[k-1]+xs[k])/2);best=(float(sse[u]),j,t,ix[xx<=t],ix[xx>t])
        if best[1] is None:nodes.append(node);return len(nodes)-1
        idx=len(nodes);nodes.append(node);j,t,left,right=best[1:]
        nodes[idx].update({'feature':int(j),'threshold':t});li=grow(left,d+1);ri=grow(right,d+1)
        nodes[idx].update({'left':li,'right':ri});return idx
    root=grow(np.arange(len(y)),0)
    def predict(Z):
        out=[]
        for row in Z:
            i=root
            while nodes[i]['feature'] is not None:
                n=nodes[i];i=n['left'] if row[n['feature']]<=n['threshold'] else n['right']
            out.append(nodes[i]['value'])
        return np.asarray(out)
    return predict,nodes

def feature_L_with_quote(x, shot, q):
    return np.column_stack((make_x(x,'response'),x[:,[4,5,8,11]],shot[:,[0,1,4,5]],
                            np.array([float(z['al']) for z in q]),
                            np.array([float(z['ah'])-float(z['aa']) for z in q])))

for hz in ('T24','T12','T6','T3','T1'):
    if hz in ('T24','T12'):
        hq,hxj=hist_by_horizon[hz]; hshot=hs; hmask=eligible_h; years_h=HY
    else:
        # Historical full-sample snapshots for T6/T3/T1 are absent; use the
        # previously frozen T12 model as the explicit training vintage.
        hq,hxj=H,hx; hshot=hs; hmask=np.zeros(len(H),dtype=bool); years_h=HY
    if hz in ('T24','T12'):
        Xj=feature_L_with_quote(hxj,hshot,hq)
        years_to_run=(2024,2025,2026)
    else:
        Xj=feature_L_with_quote(XL[:,:0] if False else hx,hshot,H)
        years_to_run=()
    if hz in actual_by_horizon:
        aq,axj,ashot,aover,arecs=actual_by_horizon[hz]
        Zj=feature_L_with_quote(axj,ashot,aq)
    else: continue
    # For T24/T12, retain matched-year historical replay and train-forward receipts.
    if hz in ('T24','T12'):
        # train/test per year at the same historical cutoff
        hp=np.zeros(len(H)); fitted={}
        for yr in years_to_run:
            tr=(HY<yr)&history_ind
            pred_fn,nodes=cart_model(Xj[tr],np.array([float(z['home_U'])-float(z['away_U']) for z in hq])[tr],depth=3,leaf=300)
            if yr==2026: fitted['2026']={'train_n':int(tr.sum()),'leaf_count':sum(z['feature'] is None for z in nodes)}
            te=HY==yr; hp[te]=pred_fn(Xj[te])
        tr=(HY<2026)&history_ind
        pred_fn,nodes=cart_model(Xj[tr],np.array([float(z['home_U'])-float(z['away_U']) for z in hq])[tr],depth=3,leaf=300)
        rp=pred_fn(Zj)
        h_side=np.where(hp>=0,'home','away');h_pnl=np.array([float(q['home_U']) if h_side[i]=='home' else float(q['away_U']) for i,q in enumerate(hq)])
        hrows=rows_for('J_L_T'+hz[1:]+'_historical',hq,h_side,h_pnl,hmask,'historical_event_replay',foundation_h)
    else:
        # Apply the prior-year T12 model to later true receipts. This is a
        # disclosed transfer across cutoffs, not a historically calibrated T6/T3/T1 model.
        Xtrain=feature_L_with_quote(hx,hs,H); tr=(HY<2026)&history_ind
        target=np.array([float(q['home_U'])-float(q['away_U']) for q in H])
        pred_fn,nodes=cart_model(Xtrain[tr],target[tr],depth=3,leaf=300);rp=pred_fn(Zj)
        hrows=[]; fitted={'training_vintage':'T12 history through 2025','train_n':int(tr.sum()),'leaf_count':sum(z['feature'] is None for z in nodes)}
    rside=np.where(rp>=0,'home','away');rpnl=np.array([float(q['home_U']) if rside[i]=='home' else float(q['away_U']) for i,q in enumerate(aq)])
    rrows=[]
    for i,(q,rec) in enumerate(zip(aq,arecs)):
        rrows.append({'fid':str(q['fid']),'date':str(q['date']),'kickoff_utc':q.get('_kickoff_utc'),'signal_time_utc':q.get('_received_utc'),
                      'signal_time_label':f"Verified actual Crown HTTP {hz} snapshot",'method':f'J_L_CART_{hz}',
                      'decision_horizon':hz,'line_home':q['al'],'odds_home_decimal':q['ah'],'odds_away_decimal':q['aa'],
                      'side':str(rside[i]),'pnl_u':round(float(rpnl[i]),6),'source_type':'actual_http_receipt',
                      'foundation_overlap':bool(aover[i]),'receipt_split':rec.get('snapshot_split'),
                      'iso_week':f"{datetime.date.fromisoformat(q['date']).isocalendar().year}-W{datetime.date.fromisoformat(q['date']).isocalendar().week:02d}"})
    all_rows.extend(hrows+rrows)
    methods[f'J_L_CART_{hz}']={'historical_incremental':summarize(hrows),'receipt':summarize(rrows),'training':fitted,
        'years':{str(yr):summarize([x for x in hrows if x['date'][:4]==str(yr)]) for yr in (2024,2025,2026)},
        'cutoff_comparability_note':'T24/T12 have matching historical event-time archive; T6/T3/T1 are actual HTTP receipts only and transfer the T12-trained direct-return model.'}
    print('J',hz,'history',brief(methods[f'J_L_CART_{hz}']['historical_incremental']),'receipt',brief(methods[f'J_L_CART_{hz}']['receipt']),flush=True)

# Full retained per-fixture ledger and overlap counts across the tested methods.
by_method={}
for row in all_rows: by_method.setdefault(row['method'],{})[row['fid']]=row
names=list(by_method); overlaps={}
for i,a in enumerate(names):
    for b in names[i+1:]:
        common=set(by_method[a])&set(by_method[b])
        overlaps[f'{a}__{b}']={'shared_fids':len(common),'same_side':sum(by_method[a][f]['side']==by_method[b][f]['side'] for f in common),
                               'same_pnl':sum(by_method[a][f]['pnl_u']==by_method[b][f]['pnl_u'] for f in common)}

foundation_sha=hashlib.sha256(membership_path.read_bytes()).hexdigest()
foundation_checks={'membership':foundation_sha==manifest['historical_membership']['sha256'],
                   'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in manifest['input_sha256'].items()),
                   'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in manifest['script_sha256'].items())}
assert all(foundation_checks.values()),foundation_checks
result={'study':'M8 batch I-L 2026-11-18','source_history':str(P/'m8_team_shot_residual_research_20261116.py'),
        'foundation_manifest':manifest,'foundation_membership_sha256_actual':foundation_sha,'foundation_checks':foundation_checks,
        'settlement_audit':settlement_audit,
        'scope':{'historical_full_pairs':len(H),'historical_evaluation':int(eligible_h.sum()),'actual_http_pairs':len(R),'actual_http_evaluation':int(eligible_r.sum()),
                 'frozen_eight_unique_ids':len(foundation_ids),'historical_frozen_overlap':int(foundation_h[eligible_h].sum()),'receipt_frozen_overlap':int(foundation_r[eligible_r].sum()),
                 'historical_years':{str(y):int((eligible_h&(HY==y)).sum()) for y in (2024,2025,2026)},
                 'signal_time_note':'Historical normalized event archive lacks exact UTC snapshot/kickoff timestamps (left null); actual HTTP receipt rows carry archived exact kickoff_utc and received_utc.'},
        'methods':methods,'overlap':overlaps,
        'limits':['R1-R63 nearest comparisons: R27/R28/R45 already test team shot, attack/defence and opponent temporal goal styles; I differs by interaction with exact Crown AH contract line and evaluates correct settlement.','K differs from R23/R37/R59 by past-only performance x multi-window common-contract repricing interactions.','L is a shallow interpretable tree on direct Crown AH net-return difference; depth and leaf supports are all retained, without choosing a profitable slice.','Repeated retrospective research means historical outcomes are not independent confirmation. Real receipt set is historical replay on true HTTP receipts, not a frozen prospective strategy.','Actual HTTP archive is from 2026 and includes exact kickoff and response received UTC timestamps; T6/T3/T1 only support receipt replay, not full historical-year event-time validation.','Per-row settlement net-U is taken from upstream Crown AH quarter-line ledger fields for historical pairs; later real receipt horizons are independently settled from score, home-line sign and received Crown decimal odds.']}
(OUT/'m8_batch_il_20261118.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
with (OUT/'m8_batch_il_orders_20261118.jsonl').open('w') as f:
    for row in all_rows: f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
report=['# M8 I–L 批量研究（2026-11-18）','',
        '仅研究回放；原八组冻结。训练按目标年之前数据前推。I/K 的实现复用R27团队射门前史构造，L/J 使用浅层 CART 直接预测同一 Crown AH 合约两边实际净U之差。',
         '历史 event-time 与真实 HTTP 收据分开；真实收据回放不是预先冻结的前瞻实战。逐笔结算来自正确 quarter-line Crown AH 分腿账本。历史标准化事件表不含精确时间故留空；2026 实收记录保留原 UTC 开球及实际 HTTP 收件时刻。','',
        '| 方法 | 历史新增 n / U / ROI | 2024 | 2025 | 2026 | 实收 HTTP n / U / ROI |','|---|---:|---:|---:|---:|---:|']
for name,m in methods.items():
    h=m.get('historical_incremental',{});r=m.get('receipt',{})
    yrs=[]
    for y in ('2024','2025','2026'):
        z=m.get('years',{}).get(y,{})
        yrs.append(f"{z.get('n',0)} / {z.get('U',0)} / {z.get('ROI_pct')}")
    report.append(f"| {name} | {h.get('n',0)} / {h.get('U',0)} / {h.get('ROI_pct')}% | "+' | '.join(yrs)+f" | {r.get('n',0)} / {r.get('U',0)} / {r.get('ROI_pct')}% |")
report+=['','## 覆盖与解释','',
         f"历史可评估 {int(eligible_h.sum())} 场，真实实收交集 {int(eligible_r.sum())} 场；原八组冻结ID {len(foundation_ids)}。本研究不把多时间点重复视为新独立比赛。按行 ledger 在 `{OUT.name}/m8_batch_il_orders_20261118.jsonl`。",
         'I 与 R27/R28/R45 的核心区别是显式“球队射门风格 × 当前 Crown AH 让球合约线”；K 检验同一风格特征与 T24→T12 Crown 共同比价移动交互。L 将两边按 AH quarter-line 实际净U直接作为训练标签，用浅树发现可解释结构；深度/叶节点参数全部保留，未按历史盈利挑选。',
         'J 将浅树信号逐一应用到 T24/T12/T6/T3/T1。T24/T12 可做历史逐年前推；T6/T3/T1 缺历史原始盘口，仅对真实收到 HTTP 收据运行上一年度 T12 训练版，故属于截止点迁移诊断。每个时间点是同一批比赛的多种报价机会，不能直接相加成订单。',
         '数据限制：只有缓存中已存在的 2024–2026 T24/T12 大样本和 2026 实际收到报价链。R1–R63 已反复探索同源样本，跨年结果不能当独立前瞻。T6/T3/T1缺少历史全量时间序列，只按真实HTTP回执复放。新候选/原八组重叠在逐笔 JSON 的 `foundation_overlap` 标记，后续全局 union 必须按 fid 去重。']
(OUT/'M8_BATCH_IL_RESEARCH_20261118.md').write_text('\n'.join(report)+'\n')
print('WROTE',OUT/'m8_batch_il_20261118.json','rows',len(all_rows),flush=True)
