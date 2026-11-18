"""M8 E-H batch experiments. Research only; all features use existing Crown caches.

Shared loader/settlement ancestry: /Users/mac/QuantAsiaDesk/research-work/
m8_early_joint_path_incremental_20261116.py. Historical source-event replays are
not live receipts. No new production rules or data collection are introduced.
"""
from __future__ import annotations
import collections, datetime, json, math
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import sys, types

def settle_score(market,line,side,hg,ag,odds):
    """Independent exact two-leg Asian settlement, stake 1U total."""
    line=float(line);odds=float(odds);hg=int(hg);ag=int(ag)
    if market=='AH':
        margin=(hg-ag+line) if side=='home' else (ag-hg-line)
    elif market=='OU':
        total=hg+ag;margin=(total-line) if side=='over' else (line-total)
    else: raise ValueError(market)
    lo=math.floor(line*2+1e-9)/2;hi=math.ceil(line*2-1e-9)/2
    # For whole/half lines the two legs are identical; quarter lines split.
    if abs(lo-hi)<1e-9: components=[margin]
    else:
        # margin above used the original line; adjust each split component.
        if market=='AH': base=(hg-ag+line) if side=='home' else (ag-hg-line)
        else: base=((hg+ag)-line) if side=='over' else (line-(hg+ag))
        delta=(hi-lo)/2
        # L is already side-adjusted in the margin, so quarter split adjustment
        # is simply +/- one quarter goal relative to the midpoint contract.
        components=[base-delta,base+delta]
    pnl=0.0
    for v in components:
        stake=1.0/len(components)
        pnl+=stake*(odds-1) if v>1e-9 else -stake if v<-1e-9 else 0.0
    return ('win' if pnl>0 else 'loss' if pnl<0 else 'push',pnl)

def manual_ah_settle(line,side,hg,ag,odds):
    """Independent leg-by-leg audit using the stored home-handicap convention."""
    line=float(line)
    if round(line*4)%2:
        legs=[math.floor(line*2)/2,math.ceil(line*2)/2]
    else:
        legs=[line]
    result=0.0
    for leg in legs:
        margin=(int(hg)-int(ag)+leg) if side=='home' else (int(ag)-int(hg)-leg)
        result += (1/len(legs))*(float(odds)-1 if margin>1e-9 else -1 if margin<-1e-9 else 0)
    return result

# The private data scripts import this repository module, which is intentionally
# absent from the public runner checkout. Inject the small settlement interface
# they need using the independent implementation above.
for name in ('research','research.m3','research.m3.probabilities'):
    if name not in sys.modules: sys.modules[name]=types.ModuleType(name)
sys.modules['research.m3.probabilities'].settle_score=settle_score

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research' / 'm8'
P = Path('/Users/mac/QuantAsiaDesk/research-work')

# Reuse the audited T24/T12 Crown AH/OU loader, exact Crown quote/FT checks,
# frozen eight membership, receipt exclusion and score function. Stop before its
# old R22 loop so this file does not overwrite any prior output.
src = (P/'m8_early_joint_path_incremental_20261116.py').read_text()
src=src.replace('from research.m3.probabilities import settle_score','')
exec(compile(src[:src.rindex("out={'method'")], 'm8_existing_audited_loader', 'exec'))

def ridge_predict(X, Z, y, train, years, penalty=100.0):
    pred=np.zeros(len(Z));hp=np.zeros(len(X));models={}
    for year in (2024,2025,2026):
        tr=train & (years<year); te=(years==year)
        mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
        xx=(X[tr]-mu)/sd;reg=np.eye(X.shape[1])*penalty;reg[0,0]=0
        beta=np.linalg.solve(xx.T@xx+reg,xx.T@y[tr])
        ix=np.where(te)[0]
        if len(ix): hp[ix]=((X[ix]-mu)/sd)@beta
        models[str(year)]={'train_n':int(tr.sum()),'features':int(X.shape[1]),'ridge':penalty}
    return hp,models

def payouts(q, line_key='al', home_key='ah', away_key='aa', home_u='home_U', away_u='away_U'):
    return np.asarray([float(x[home_u]) for x in q]),np.asarray([float(x[away_u]) for x in q])

def stat_rows(rows, pnl):
    ix=np.asarray([r is not None for r in pnl],bool)
    vals=np.asarray([0 if x is None else x for x in pnl],float)
    dates=collections.defaultdict(float);weeks=collections.Counter()
    for r,v,ok in zip(rows,vals,ix):
        if ok:
            dates[r['date']]+=v;weeks[datetime.date.fromisoformat(r['date']).strftime('%G-W%V')]+=1
    curve=peak=dd=0.
    for d,v in sorted(dates.items()):
        curve+=v;peak=max(peak,curve);dd=max(dd,peak-curve)
    n=int(ix.sum());u=float(vals[ix].sum())
    return {'n':n,'net_U':round(u,3),'ROI_pct':round(100*u/n,3) if n else None,
            'daily_MDD_U':round(dd,3),'active_weeks':len(weeks),
            'average_per_active_week':round(n/len(weeks),3) if weeks else None,
            'weekly_counts':dict(sorted(weeks.items()))}

def order_rows(method, rows, sides, home_u, away_u, line, hp, ap, source_type, kickoff_map=None):
    result=[]
    for i,(r,side) in enumerate(zip(rows,sides)):
        pnl=float(home_u[i] if side=='home' else away_u[i])
        kickoff=(kickoff_map or {}).get(r['fid'])
        if kickoff is not None:
            ko=kickoff.isoformat().replace('+00:00','Z')
            sig=(kickoff-datetime.timedelta(hours=12)).isoformat().replace('+00:00','Z') if source_type=='actual_http_receipt' else None
        else:
            ko=None;sig=None
        result.append({'fid':str(r['fid']),'kickoff_utc':ko,'date':r['date'],'signal_time_utc':sig,
                       'method':method,'line_home':float(line[i]),'odds_home':float(hp[i]),
                       'odds_away':float(ap[i]),'side':side,'pnl_u':round(pnl,6),
                       'source_type':source_type,'foundation_overlap':str(r['fid']) in ids})
    return result

def write_orders(name, orders):
    path=OUT/f'm8_batch_{name}_orders_20261118.jsonl'
    path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in orders))
    return str(path.relative_to(ROOT))

# T24/T12 core exact-Crown sample; one AH contract per fixture and all candidates
# retained. First run E (discrete AH contract settlement) and F (asynchronous
# AH-vs-OU quote updates), both as prior-calendar-year payout-difference models.
Xbase=np.asarray([feature(a,b,'path') for a,b in hist]); Zbase=np.asarray([feature(a,b,'path') for a,b in pairs])
yh=np.asarray([float(x['home_U'])-float(x['away_U']) for x in H]);yr=np.asarray([float(x['home_U'])-float(x['away_U']) for x in R])
basepred,basefit=ridge_predict(Xbase,Zbase,yh,history_ind,HY)
homeH,awayH=payouts(H);homeR,awayR=payouts(R)
base_side_H=np.where(basepred>=0,'home','away')

# E: Five-state AH settlement distribution: full loss / half loss / push /
# half win / full win for the home contract. The AH line is the home-team line.
# A previous-year multinomial calibration forecasts these states conditional on
# the exact signed quarter-line, price share, vig and quote age; expected returns
# use the exact two-component quarter-line payout algebra.
def settlement_class(line, hg, ag):
    lo=math.floor(line*2+1e-9)/2; hi=math.ceil(line*2-1e-9)/2
    vals=[hg-ag+lo,hg-ag+hi]
    wins=sum(v>1e-9 for v in vals);losses=sum(v<-1e-9 for v in vals)
    if wins==2:return 4
    if wins==1 and losses==0:return 3
    if wins==0 and losses==0:return 2
    if losses==1 and wins==0:return 1
    return 0
def contract_features(q):
    out=[]
    for r in q:
        ln=float(r['al']);h=float(r['ah']);a=float(r['aa'])
        share=(1/h)/(1/h+1/a);vig=1/h+1/a-1
        frac=round((abs(ln)%1)*4)/4
        out.append([1.,ln,abs(ln),math.log1p(abs(ln)),share-.5,vig,
                    math.log1p(max(0,float(r.get('age_ah',0)))),
                    float(abs(ln)<1e-9),float(frac==0),float(frac==.25),float(frac==.5),float(frac==.75),
                    float(ln<0),float(ln>0),ln*(share-.5),abs(ln)*(share-.5)])
    return np.asarray(out)
def fit_multinom(X,y,train,years):
    probs=np.zeros((len(X),5));fits={}
    for year in (2024,2025,2026):
        tr=train&(years<year);te=years==year
        mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
        a=(X[tr]-mu)/sd;b=(X[te]-mu)/sd
        # Class 2 as reference to identify the five-way softmax.
        D=np.eye(5)[:,:4]-np.eye(5)[2,:4]
        Y=np.eye(5)[y[tr]][:,:4]-np.eye(5)[y[tr],2,None]
        def objective(flat):
            W=flat.reshape(a.shape[1],4);logits=a@W
            full=np.column_stack((logits,np.zeros(len(logits))))
            full-=full.max(1,keepdims=True);p=np.exp(full);p/=p.sum(1,keepdims=True)
            loss=-np.log(np.maximum(p[np.arange(len(p)),y[tr]],1e-15)).sum()+50*np.sum(W[1:]**2)
            grad=a.T@(p[:,:4]-np.eye(5)[y[tr]][:,:4])+100*np.vstack((np.zeros((1,4)),W[1:]))
            return loss,grad.ravel()
        opt=minimize(objective,np.zeros(a.shape[1]*4),jac=True,method='L-BFGS-B',options={'maxiter':250,'ftol':1e-10})
        if not opt.success: raise RuntimeError(f'E fit {year}: {opt.message}')
        W=opt.x.reshape(a.shape[1],4);logits=np.column_stack((b@W,np.zeros(len(b))));logits-=logits.max(1,keepdims=True)
        pp=np.exp(logits);pp/=pp.sum(1,keepdims=True);probs[te]=pp
        fits[str(year)]={'train_n':int(tr.sum()),'features':int(X.shape[1]),'regularization':50.0}
    return probs,fits

XE=contract_features(H);ZE=contract_features(R)
classes=np.asarray([settlement_class(float(r['al']),int(r['hg']),int(r['ag'])) for r in H])
pe,efit=fit_multinom(XE,classes,history_ind,HY)
# Same year-coherent calibration for live receipt rows; no receipt outcomes enter fit.
pr=np.zeros((len(R),5))
for year in (2024,2025,2026):
    tr=history_ind&(HY<year);re=RY==year
    if not re.any():continue
    mu=XE[tr].mean(0);sd=XE[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
    a=(XE[tr]-mu)/sd;b=(ZE[re]-mu)/sd
    def obj(flat):
        W=flat.reshape(a.shape[1],4);l=np.column_stack((a@W,np.zeros(len(a))));l-=l.max(1,keepdims=True);p=np.exp(l);p/=p.sum(1,keepdims=True)
        loss=-np.log(np.maximum(p[np.arange(len(p)),classes[tr]],1e-15)).sum()+50*np.sum(W[1:]**2)
        grad=a.T@(p[:,:4]-np.eye(5)[classes[tr]][:,:4])+100*np.vstack((np.zeros((1,4)),W[1:]))
        return loss,grad.ravel()
    opt=minimize(obj,np.zeros(a.shape[1]*4),jac=True,method='L-BFGS-B',options={'maxiter':250,'ftol':1e-10})
    if not opt.success:raise RuntimeError(opt.message)
    l=np.column_stack((b@opt.x.reshape(a.shape[1],4),np.zeros(len(b))));l-=l.max(1,keepdims=True);p=np.exp(l);pr[re]=p/p.sum(1,keepdims=True)

def exp_returns(probs,rows):
    p0,p1,p2,p3,p4=probs.T;home=[];away=[]
    for r,a,b,c,d,e in zip(rows,p0,p1,p2,p3,p4):
        home.append(e*(float(r['ah'])-1)+.5*d*(float(r['ah'])-1)-a-.5*b)
        away.append(a*(float(r['aa'])-1)+.5*b*(float(r['aa'])-1)-e-.5*d)
    return np.asarray(home),np.asarray(away)
eh,ea=exp_returns(pe,H);erh,era=exp_returns(pr,R)
e_side_H=np.where(eh>=ea,'home','away');e_side_R=np.where(erh>=era,'home','away')
e_pnl_H=np.where(e_side_H=='home',homeH,awayH);e_pnl_R=np.where(e_side_R=='home',homeR,awayR)
base_pnl_H=np.where(base_side_H=='home',homeH,awayH)

# F: Asynchronous Crown market updates. Add AH/OU source-age imbalance and
# market-update disagreement to the same prior-year AH payout target. The feature
# is explicitly different from R35's static cross-market fit: it uses T24->T12
# updates and relative source freshness, while retaining complete matched rows.
def async_features(pairs_):
    vals=[]
    for a,b in pairs_:
        xa=snapshot(a);xb=snapshot(b);d=xb-xa
        ahage=float(b.get('age_ah',0));ouage=float(b.get('age_ou',0));oldiff=ahage-ouage
        ahold=abs(float(a.get('age_ah',0))-float(b.get('age_ah',0)))
        ouold=abs(float(a.get('age_ou',0))-float(b.get('age_ou',0)))
        vals.append([oldiff,abs(oldiff),ahage,ouage,ahage*ouage,
                     ahage-float(a.get('age_ah',0)),ouage-float(a.get('age_ou',0)),
                     d[2],d[3],abs(d[2]),abs(d[3]),
                     d[3]-d[2],d[2]*d[3],
                     float(abs(d[3])>.001 and abs(d[2])<=.001),
                     float(abs(d[2])>.001 and abs(d[3])<=.001),
                     float(oldiff>0),float(oldiff<0),oldiff*(d[3]-d[2])])
    return np.asarray(vals)
XF=np.column_stack((Xbase,async_features(hist)));ZF=np.column_stack((Zbase,async_features(pairs)))
fpred,ffit=ridge_predict(XF,ZF,yh,history_ind,HY)
f_side_H=np.where(fpred>=0,'home','away');f_side_R=np.where(ridge_predict(XF,ZF,yh,history_ind,HY)[0][:len(R)]>=0,'home','away') if False else None
# Receipt forecasts must use the same fold coefficients; predict them directly.
def predict_receipts(X,Z,y,train,years):
    out=np.zeros(len(Z));fits={}
    for year in (2024,2025,2026):
        tr=train&(years<year);re=RY==year
        if not re.any():continue
        mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
        a=(X[tr]-mu)/sd;reg=np.eye(X.shape[1])*100;reg[0,0]=0
        beta=np.linalg.solve(a.T@a+reg,a.T@y[tr]);out[re]=((Z[re]-mu)/sd)@beta
        fits[str(year)]={'train_n':int(tr.sum())}
    return out,fits
frpred,frfit=predict_receipts(XF,ZF,yh,history_ind,HY)
f_side_R=np.where(frpred>=0,'home','away');f_pnl_H=np.where(f_side_H=='home',homeH,awayH);f_pnl_R=np.where(f_side_R=='home',homeR,awayR)

# H: Team x exact AH contract-position residual. For each club, role and signed
# contract-position band, estimate past Crown settlement residual (actual PnL
# minus no-vig market expectation), strictly before the target UTC date. This
# differs from R26-R30's goal/attack/defence residuals: the memory is realized
# contract payout error conditioned on AH position. The prior is shrunk by 8.
def pos_key(side_line):
    sg='fav' if side_line < -1e-9 else 'dog' if side_line > 1e-9 else 'pk'
    a=abs(side_line)
    band='0_025' if a<=.25+1e-9 else '05_075' if a<=.75+1e-9 else '1_15' if a<=1.5+1e-9 else '15plus'
    return sg+'_'+band
def team_features(target_rows):
    # Build outcome residual observations from non-receipt historical rows only.
    events=[]
    for r in H:
        if str(r['fid']) in receiptids:continue
        ln=float(r['al']);h=float(r['ah']);a=float(r['aa'])
        for team,role,side,handicap,odds,own_u,other_odds in (
            (r['home_id'],'home','home',ln,h,float(r['home_U']),a),
            (r['away_id'],'away','away',-ln,a,float(r['away_U']),h)):
            if not team:continue
            q=(1/odds)/(1/odds+1/other_odds)
            expected=q*(odds-1)-(1-q)
            residual=own_u-expected
            events.append((r['date'],str(team),role,pos_key(handicap),residual,str(r['fid'])))
    events.sort(key=lambda z:z[0])
    # target rows sorted as well, then query cumulative sums whose date is strictly earlier.
    indexed=collections.defaultdict(list)
    for e in events:indexed[(e[1],e[2],e[3])].append(e)
    from bisect import bisect_left
    idxdates={k:[x[0] for x in v] for k,v in indexed.items()}
    out=np.zeros((len(target_rows),4));counts=np.zeros((len(target_rows),4),dtype=int)
    for i,r in enumerate(target_rows):
        ln=float(r['al']);d=r['date']
        for j,(team,role,handicap) in enumerate(((r['home_id'],'home',ln),(r['away_id'],'away',-ln))):
            if not team:continue
            v=indexed.get((str(team),role,pos_key(handicap)),[]);ds=idxdates.get((str(team),role,pos_key(handicap)),[])
            stop=bisect_left(ds,d);n=stop;s=sum(x[4] for x in v[:stop])
            out[i,j]=s/(8+n);counts[i,j]=n
        out[i,2]=math.log1p(counts[i,0]);out[i,3]=math.log1p(counts[i,1])
    return out,counts
XH0,nh=team_features(H);ZH0,nr=team_features(R)
XH=np.column_stack((Xbase,XH0));ZH=np.column_stack((Zbase,ZH0))
hpred,hfit=ridge_predict(XH,ZH,yh,history_ind,HY)
hrpred,hrfit=predict_receipts(XH,ZH,yh,history_ind,HY)
h_side_H=np.where(hpred>=0,'home','away');h_side_R=np.where(hrpred>=0,'home','away')
h_pnl_H=np.where(h_side_H=='home',homeH,awayH);h_pnl_R=np.where(h_side_R=='home',homeR,awayR)

# G: Existing T-6 to T-1 Crown asian_list replay. Feature producer's source code
# explicitly limits event sequence to [T-6,T-1]; it is a retrospective source-event
# replay, not actual receipt or real liquidity/volume. It has no verified receipt
# counterpart, so no actual-receipt return is asserted here.
gpath=P/'m8_late_full_path_water_features_20261114.jsonl'
Gall=[json.loads(x) for x in gpath.open()]
Gall=[x for x in Gall if x.get('end_line') is not None and x.get('end_home_U') is not None and x.get('home_price') is not None and x.get('away_price') is not None]
G=[x for x in Gall if int(x['year']) in (2024,2025,2026)]
g_features=[];gy=[]
for r in Gall:
    cat={'never_changed':0,'one_way':1,'reverted':2,'oscillating':3}.get(r.get('path_shape'),-1)
    pshape=[float(cat==j) for j in range(4)]
    g_features.append([1.,float(r['end_line']),abs(float(r['end_line'])),
        math.log1p(float(r['n_events'])),math.log1p(float(r['n_line_changes'])),float(r['line_range']),
        float(r['final_line_minutes'])/360.,float(r['late_event_age_min'])/60.,
        float(r.get('last_line_change_age_min') or 0)/360.,float(r.get('fav_end_vs_start') or 0),
        float(r.get('fav_end_vs_max') or 0),float(r.get('fav_end_vs_min') or 0),
        float(r.get('fav_last_move') or 0),float(r.get('dog_price_change') or 0),
        float(r.get('fav_price_change') or 0),*pshape,
        math.log1p(float(r['home_price'])),math.log1p(float(r['away_price']))])
    gy.append(float(r['end_home_U'])-float(r['end_away_U']))
GX=np.asarray(g_features);gY=np.asarray(gy);gYears=np.asarray([int(x['year']) for x in Gall])
gpred=np.zeros(len(Gall));gfit={}
for year in (2024,2025,2026):
    tr=gYears<year;te=gYears==year;mu=GX[tr].mean(0);sd=GX[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
    a=(GX[tr]-mu)/sd;reg=np.eye(GX.shape[1])*100;reg[0,0]=0;beta=np.linalg.solve(a.T@a+reg,a.T@gY[tr]);gpred[te]=((GX[te]-mu)/sd)@beta
    gfit[str(year)]={'train_n':int(tr.sum()),'features':int(GX.shape[1]),'ridge':100}
gids={str(x['fid']):i for i,x in enumerate(Gall)}
Gidx=np.asarray([gids[str(x['fid'])] for x in G],int)
gSide=np.where(gpred[Gidx]>=0,'home','away');gPnL=np.asarray([float(x['end_home_U']) if s=='home' else float(x['end_away_U']) for x,s in zip(G,gSide)])

manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
foundation_check={'membership_sha256':__import__('hashlib').sha256((P/manifest['historical_membership']['local_file']).read_bytes()).hexdigest()==manifest['historical_membership']['sha256'],
                   'input_sha256_all_match':all(__import__('hashlib').sha256((P/k).read_bytes()).hexdigest()==v for k,v in manifest['input_sha256'].items()),
                   'script_sha256_all_match':all(__import__('hashlib').sha256((P/k).read_bytes()).hexdigest()==v for k,v in manifest['script_sha256'].items())}
if not all(foundation_check.values()):raise AssertionError(foundation_check)

# Independent PnL re-settlement of the full historical and verified-receipt
# T12 samples. Compare both side returns in the input rows to an explicit split-leg
# implementation, catching side-sign and quarter-line errors before export.
settlement_audit={'historical_fixture_sides_checked':0,'historical_side_mismatches':0,
                  'actual_receipt_fixture_sides_checked':0,'actual_receipt_side_mismatches':0}
for rows0,kind in ((H,'historical'),(R,'actual_receipt')):
    mismatches=0;checked=0
    for r in rows0:
        for side,key,price_key in (('home','home_U','ah'),('away','away_U','aa')):
            expected=manual_ah_settle(r['al'],side,r['hg'],r['ag'],r[price_key])
            checked+=1
            if abs(expected-float(r[key]))>1e-7:mismatches+=1
    settlement_audit[kind+'_fixture_sides_checked']=checked
    settlement_audit[kind+'_side_mismatches']=mismatches
    if mismatches:raise AssertionError(f'{kind} settlement mismatches {mismatches}/{checked}')

# Score each method across years, incremental-over-foundation and actual receipt
# rows. Output one unique order per method/FID, preserving overlaps for parent union.
def summarize(method, rows, pnl, years, actual=False):
    out={'all':stat_rows(rows,pnl),'outside_frozen_eight':stat_rows([r for r in rows if str(r['fid']) not in ids],[p for r,p in zip(rows,pnl) if str(r['fid']) not in ids]),'year':{}}
    for y in (2024,2025,2026):
        ix=[i for i,r in enumerate(rows) if int(r['year'])==y]
        out['year'][str(y)]=stat_rows([rows[i] for i in ix],[pnl[i] for i in ix])
        ix=[i for i,r in enumerate(rows) if int(r['year'])==y and str(r['fid']) not in ids]
        out['year'][str(y)]['outside_frozen_eight']=stat_rows([rows[i] for i in ix],[pnl[i] for i in ix])
    return out

# To maintain one unique actual receipt record per (method,fid), fit predictions on the
# actual receipt fixture list with the identical earlier-year historical coefficient.
# (R rows are year 2026 only in the current receipt cache.)
def baseline_receipt(X,Z,y,train,years):return predict_receipts(X,Z,y,train,years)[0]
base_receipt_pred=baseline_receipt(Xbase,Zbase,yh,history_ind,HY)

# Exact raw/snapshot receipts and independent FT source for every selected T12 row.
archive_rows=[json.loads(x) for x in (P/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl').open()]
receipt_archive=collections.defaultdict(list)
for a in archive_rows:
    if 720<=float(a.get('received_minutes_to_kickoff',-1))<1440 and 'AH' in a.get('markets',{}):
        receipt_archive[str(a['fixture_id'])].append(a)
coverage_rows=[json.loads(x) for x in (P/'m8_independent_receipt_coverage_20261115.jsonl').open()]
ft_source_map={str(x['fid']):x.get('FT_source') for x in coverage_rows if x.get('verified_receipt') and x.get('FT') is not None}
receipt_meta={}
for r in R:
    candidates=[a for a in receipt_archive.get(str(r['fid']),[]) if
      float(a['markets']['AH']['line'])==float(r['al']) and
      float(a['markets']['AH']['odds']['home'])==float(r['ah']) and
      float(a['markets']['AH']['odds']['away'])==float(r['aa'])]
    if not candidates:raise AssertionError(f"no receipt archive match for {r['fid']}")
    receipt_meta[str(r['fid'])]=max(candidates,key=lambda z:z['received_utc'])
if len(receipt_meta)!=len(R):raise AssertionError('actual receipt archive FID mismatch')

orders={}
method_results={}
for name,hsides,hpnls,rsides,rpnls in (
    ('E_discrete_AH_contract_calibration',e_side_H,e_pnl_H,e_side_R,np.where(e_side_R=='home',homeR,awayR)),
    ('F_async_Crown_market_updates',f_side_H,f_pnl_H,f_side_R,f_pnl_R),
    ('H_team_contract_position_residual',h_side_H,h_pnl_H,h_side_R,h_pnl_R)):
    # historical rows from H are T12 Crown event-time historical replay
    hs=order_rows(name,H,hsides,homeH,awayH,vec(H,'al'),vec(H,'ah'),vec(H,'aa'),'historical_event_replay')
    rs=order_rows(name,R,rsides,homeR,awayR,vec(R,'al'),vec(R,'ah'),vec(R,'aa'),'actual_http_receipt',verified_kickoff)
    for row in rs:
        meta=receipt_meta.get(row['fid'])
        if meta is None:raise AssertionError(f"missing actual receipt evidence for {row['fid']}")
        row.update({'received_utc':meta['received_utc'],'raw_sha256':meta['raw_sha256'],
                    'snapshot_sha256':meta['snapshot_sha256'],'FT_source':ft_source_map.get(row['fid']),
                    'AH_source_event_utc':meta['markets']['AH']['source_event_utc'],
                    'snapshot_horizon':meta['snapshot_horizon'],
                    'received_minutes_to_kickoff':meta['received_minutes_to_kickoff']})
        if not row['FT_source']:raise AssertionError(f"missing FT source for {row['fid']}")
    orders[name]=hs+rs
    method_results[name]={'historical':summarize(name,H,hpnls,HY),'actual_http_receipt':summarize(name,R,rpnls,RY,True),
      'history_receipt_overlap_ids':len({str(x['fid']) for x in H}&{str(x['fid']) for x in R}),
      'historical_orders_path':write_orders(name,hs),'actual_receipt_orders_path':write_orders(name+'_actual_receipt',rs)}

# E settlement diagnostics: class frequencies and exact expected-return uplift vs
# the same Crown market baseline, always over the whole retrospective cohort.
e_diagnostics={'class_counts':dict(collections.Counter(map(int,classes))),
 'expected_home_ev_mean':round(float(eh.mean()),6),'expected_away_ev_mean':round(float(ea.mean()),6),
 'selected_side_agrees_with_R22_path':int(np.sum(e_side_H==base_side_H)),
 'selected_side_changes_vs_R22_path':int(np.sum(e_side_H!=base_side_H)),
 'selected_side_changes_outside_eight':int(sum(e_side_H[i]!=base_side_H[i] for i,r in enumerate(H) if str(r['fid']) not in ids))}

# F freshness/update diagnostics, measured without calling quote age a liquidity measure.
af=async_features(hist)
f_diagnostics={'T12_pairs':len(H),'AH_older_than_OU_n':int((af[:,0]>0).sum()),
 'OU_older_than_AH_n':int((af[:,0]<0).sum()),'same_freshness_n':int((af[:,0]==0).sum()),
 'OU_moved_AH_not_moved_n':int(((np.abs(af[:,13])>0)).sum()),
 'AH_moved_OU_not_moved_n':int(((np.abs(af[:,14])>0)).sum()),
 'note':'Source quote age and two historical timepoint snapshots measure update timing only; not executable queue/volume.'}

# H coverage: team-contract features depend on a strictly earlier UTC calendar date.
h_coverage={'history_fixtures':len(H),'receipt_fixtures':len(R),'historical_rows_with_any_team_contract_history':int((nh[:,:2].sum(1)>0).sum()),
 'actual_receipt_rows_with_any_team_contract_history':int((nr[:,:2].sum(1)>0).sum()),
 'median_prior_bucket_obs_home':float(np.median(nh[:,0])),'median_prior_bucket_obs_away':float(np.median(nh[:,1])),
 'receipt_kickoff_timestamps_verified':int(len(verified_kickoff))}

# G orders and score on exact Crown T−1 AH close stored by existing T−6→T−1 cache.
gorders=[]
for i,(r,side,pnl) in enumerate(zip(G,gSide,gPnL)):
    # This JSONL retains AH close prices and independently computed correct PnL.
    ko=None;sig=None
    kickoff=verified_kickoff.get(str(r['fid']))
    if kickoff is not None:
        ko=kickoff.isoformat().replace('+00:00','Z')
        sig=(kickoff-datetime.timedelta(hours=1)).isoformat().replace('+00:00','Z')
    gorders.append({'fid':str(r['fid']),'kickoff_utc':ko,'date':r['date'],'signal_time_utc':sig,
      'method':'G_T6_T1_Crown_microstructure_replay','line_home':float(r['end_line']),
      'odds_home':float(r['home_price']),'odds_away':float(r['away_price']),
      'side':side,'pnl_u':round(float(pnl),6),'source_type':'historical_event_replay',
      'foundation_overlap':str(r['fid']) in ids})
g_orders_path=write_orders('G_T6_T1_Crown_microstructure_replay',gorders)
g_results={'historical':stat_rows(G,gPnL),'outside_frozen_eight':stat_rows([r for r in G if str(r['fid']) not in ids],[p for r,p in zip(G,gPnL) if str(r['fid']) not in ids]),
 'year':{str(y):stat_rows([r for r in G if int(r['year'])==y],[p for r,p in zip(G,gPnL) if int(r['year'])==y]) for y in (2024,2025,2026)},
 'orders_path':g_orders_path,'actual_http_receipt':'not available: T−6→T−1 event feature archive is retrospective source-event history, not raw actual HTTP receipt.'}

# Parent-level union input uses one row per method/FID, with receipt observations
# kept separate from historical event-time rows.
aggregate_orders=[]
for rows0 in orders.values(): aggregate_orders.extend(rows0)
aggregate_orders.extend(gorders)
(OUT/'m8_batch_eh_orders_20261118.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in aggregate_orders))
result_orders_path='research/m8/m8_batch_eh_orders_20261118.jsonl'

# Expand yearly/weekly performance for all methods with correct quarter-line PnL.
for name,ss,pp,rr,prr in (
    ('E_discrete_AH_contract_calibration',e_side_H,e_pnl_H,e_side_R,np.where(e_side_R=='home',homeR,awayR)),
    ('F_async_Crown_market_updates',f_side_H,f_pnl_H,f_side_R,f_pnl_R),
    ('H_team_contract_position_residual',h_side_H,h_pnl_H,h_side_R,h_pnl_R)):
    method_results[name]['yearly_unique_incremental']={str(y):stat_rows([r for r in H if int(r['year'])==y and str(r['fid']) not in ids],[p for r,p in zip(H,pp) if int(r['year'])==y and str(r['fid']) not in ids]) for y in (2024,2025,2026)}
    method_results[name]['yearly_actual_receipts_incremental']={str(y):stat_rows([r for r in R if int(r['year'])==y and str(r['fid']) not in ids],[p for r,p in zip(R,prr) if int(r['year'])==y and str(r['fid']) not in ids]) for y in (2024,2025,2026)}

result={'task':'M8 batch E-H research; no production changes','input_scope':{'historical_T24_T12_pairs':len(H),'actual_HTTP_T24_T12_pairs':len(R),'historical_years_2024_2025_2026':{str(y):int((HY==y).sum()) for y in (2024,2025,2026)},'actual_receipt_years':{str(y):int((RY==y).sum()) for y in (2024,2025,2026)},'foundation_frozen_sha_checks':foundation_check},
 'closest_prior_work':{
  'E':'R38 M8_SCORE_CATEGORY_CALIBRATION_20261117.md calibrated goal-margin/total-goal categories, and R54 m8_ah_contract_settlement_bias_20261117.py modeled linear AH contract shapes. This test instead forecasts exact 5-state AH settlement outcomes conditional on the offered AH quarter-line and returns.',
  'F':'R35 M8_CROSS_MARKET_RESEARCH_20261116.md used static cross-market AH/OU/1X2 prices; this test uses AH-vs-OU update age imbalance and divergent T24-to-T12 movements.',
  'G':'R37 M8_SAME_LINE_QUOTE_PRESSURE_20261117.md analyzed common price levels and R53 recency diagnostics. This test uses the already cached sequence of T−6→T−1 quote arrival/line/price path features and T−1 Crown close.',
  'H':'R26-R30 tested team score/attack/defense residuals and home/away or league structure. This test uses a team-role-by-signed-AH-position history of exact Crown contract payout residuals.'},
 'method_results':method_results,'E_diagnostics':e_diagnostics,'F_async_update_diagnostics':f_diagnostics,'H_feature_coverage':h_coverage,'G_T6_T1':g_results,'union_orders_path':result_orders_path,
 'independent_AH_settlement_audit':settlement_audit,
 'actual_receipt_evidence':{'exact_received_utc_raw_and_snapshot_sha_matches':len(receipt_meta),
                            'FT_source_counts':dict(collections.Counter(ft_source_map.get(f) for f in receipt_meta)),
                            'snapshot_horizon_counts':dict(collections.Counter(a['snapshot_horizon'] for a in receipt_meta.values())),
                            'all_actual_receipt_rows_have_FT_source':all(bool(ft_source_map.get(f)) for f in receipt_meta)},
 'caveats':[
  'AH outcome settlement uses Crown prices and exact quarter-line split; historical labels and quoted lines are retrospective event-time replays, not receipt-time prices.',
  'Actual HTTP receipt rows are the separately verified T24/T12 sample; these are not an independently precommitted live strategy or formal TG trades.',
  'G source file restricts events to T−6 through T−1, but its rows are recovered retrospectively; actual-receipt overlap and true receipt-time feasibility are not established.',
  'E-H are model experiments, not production rules; all unique fixture overlap with frozen eight remains explicit in order JSONL.' ]}
(OUT/'m8_batch_eh_summary_20261118.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'coverage':result['input_scope'],'models':{k:{'H':v['historical']['outside_frozen_eight'],'R':v['actual_http_receipt']['outside_frozen_eight']} for k,v in method_results.items()},'G':g_results['outside_frozen_eight'],'foundation':foundation_check},ensure_ascii=False,indent=2))
