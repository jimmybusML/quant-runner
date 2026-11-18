#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M8 E/I/market_response selective-result decomposition and new-receipt replay.
Research-only. Does not edit production code or foundation membership.
"""
import collections, contextlib, datetime as dt, gzip, hashlib, io, json, math, sqlite3, statistics, tempfile, shutil
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[2]
M8=ROOT/'research/m8'
DATA=M8/'selective_research_20261119'
OUT=M8/'selective_decomposition_20261120'
OUT.mkdir(exist_ok=True)
RUN_TMP=Path(tempfile.mkdtemp(prefix='m8_selective_decomp_'))
RESULT=json.load(open(DATA/'M8_SELECTIVE_PROFITABILITY_RESULTS_20261119.json'))
FOUNDATION_PATH=Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
foundation={str(json.loads(x)['fid']):json.loads(x) for x in FOUNDATION_PATH.open()}
METHODS=['E_discrete_AH_contract_calibration','I_line_style','market_response']
SCORE_PATH=DATA/'m8_selective_scores_20261119.jsonl.gz'
score=[]; all_actual_score_rows=[]
with gzip.open(SCORE_PATH,'rt') as f:
 for line in f:
  r=json.loads(line)
  if r.get('source_type')=='actual_http_receipt': all_actual_score_rows.append(r)
  if r['method'] in METHODS and r.get('actual_home_u') is not None: score.append(r)

# Exact source loaders and models are rerun in isolated namespaces. Their output paths
# are redirected so no prior artifact is overwritten.
def exec_script(path, replacements):
 s=path.read_text()
 for a,b in replacements:
  if a not in s: raise RuntimeError(f'missing patch fragment in {path}: {a}')
  s=s.replace(a,b)
 ns={'__file__':str(path),'__name__':'__m8_selective_decomp__'}
 with contextlib.redirect_stdout(io.StringIO()): exec(compile(s,str(path),'exec'),ns,ns)
 return ns
P=Path('/Users/mac/QuantAsiaDesk/research-work')
loader_path=P/'m8_team_shot_residual_research_20261116.py'
# The batch I/L runner reconstructs the audited quote pairs/features and frozen folds.
il=exec_script(M8/'m8_batch_il_20261118.py',[("OUT = Path(__file__).resolve().parent",f"OUT = Path('{RUN_TMP}/isolated_il')\nOUT.mkdir(parents=True, exist_ok=True)")])
# E runner has its own exact feature transform and softmax fit.
eh=exec_script(M8/'m8_batch_eh_20261118.py',[("OUT = ROOT / 'research' / 'm8'",f"OUT = Path('{RUN_TMP}/isolated_eh')\nOUT.mkdir(parents=True, exist_ok=True)")])

# Map league IDs from the audited Crown AH loader.
league_by_fid={str(r['fid']):str(r['league']) for r in il['H']}
league_by_fid.update({str(r['fid']):str(r['league']) for r in il['R']})
# Use authenticated Crown archive league labels; names are labels only.
league_name_by_id={}
archive_path=Path('/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')
archive=[json.loads(x) for x in archive_path.open()]
for rec0 in archive: league_name_by_id[str(rec0.get('league_id'))]=rec0.get('league')
archive_by_time={(str(rec0['fixture_id']),str(rec0['received_utc'])):rec0 for rec0 in archive}
# SQLite actual live receipts strictly after the committed receipt archive cutoff.
db=sqlite3.connect('file:/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3?mode=ro',uri=True)
captures=db.execute("""select fixture_id,response_received_at_utc,source_file,response_sha256,kickoff_at_utc
 from capture where capture_mode='live' and data_layer='summary'
 and response_received_at_utc>'2026-11-13T13:50:53.484Z' order by response_received_at_utc""").fetchall()

# Basic ledger metrics, keeping all rows in a 6-week comparable window.
def dateweek(s):
 d=dt.date.fromisoformat(str(s)[:10]); iso=d.isocalendar(); return f'{iso.year}-W{iso.week:02d}'
def summary(rows):
 rows=[r for r in rows if r.get('pnl_u') is not None]
 if not rows:return {'n':0,'U':0,'ROI_pct':None,'MDD_U':0,'weeks':0,'weekly':{}}
 byday=collections.defaultdict(float);byweek=collections.defaultdict(lambda:[0,0.])
 for r in rows:
  d=str(r['date'])[:10];p=float(r['pnl_u']);byday[d]+=p
  w=dateweek(d);byweek[w][0]+=1;byweek[w][1]+=p
 b=peak=mdd=0.
 for d in sorted(byday): b+=byday[d];peak=max(peak,b);mdd=max(mdd,peak-b)
 u=sum(float(r['pnl_u']) for r in rows)
 return {'n':len(rows),'U':round(u,6),'ROI_pct':round(u/len(rows)*100,6),'MDD_U':round(mdd,6),'weeks':len(byweek),
         'weekly':{k:{'n':v[0],'U':round(v[1],6),'ROI_pct':round(100*v[1]/v[0],6)} for k,v in sorted(byweek.items())}}
def qstats(vals):
 a=np.asarray(vals,float)
 return {'n':len(a),'mean':float(a.mean()),'sd':float(a.std(ddof=1)) if len(a)>1 else 0.,'quantiles':{str(q):float(np.quantile(a,q)) for q in [0,.1,.25,.5,.75,.9,1]}}
def bin_table(rows,field):
 d=collections.defaultdict(list)
 for r in rows:d[str(r.get(field,'NA'))].append(r)
 return {k:summary(v) for k,v in sorted(d.items())}

year_detail={}
for method in METHODS:
 z=[r for r in score if r['method']==method and r['source_type']=='historical_event_replay' and not r.get('foundation_overlap')]
 year_detail[method]={}
 threshold=float(RESULT['actual_receipt_transfer_calibrations'][method]['top20_prior_confidence']['threshold'])
 for year in (2024,2025,2026):
  yr=[r for r in z if int(r['date'][:4])==year]
  conf=[r for r in yr if r.get('confidence_abs') is not None]
  sel=[r for r in conf if abs(float(r['confidence_abs']))>=threshold]
  year_detail[method][str(year)]={'all':summary(yr),'score_distribution':qstats([r['score_home_minus_away'] for r in conf]),
    'confidence_distribution':qstats([abs(float(r['confidence_abs'])) for r in conf]),'score_bins_quintile_descriptive':{},
    'fixed_2024_25_q80_selected':summary(sel),
    'market_favorite_odds':bin_table(sel,'favorite_odds_bucket'),'handicap_line':bin_table(sel,'line_bucket'),
    'side':bin_table(sel,'side'),'league_by_id':bin_table(sel,'league_id')}
  if conf:
   edges=np.quantile([float(r['confidence_abs']) for r in conf],[0,.2,.4,.6,.8,1]); bins=collections.defaultdict(list)
   for r in conf: bins[min(4,int(np.searchsorted(edges[1:-1],float(r['confidence_abs']),side='right')))].append(r)
   year_detail[method][str(year)]['score_bins_quintile_descriptive']={str(k):summary(v) for k,v in sorted(bins.items())}

# Actual receipt rows are only the three methods, exact audit-pass rows with receipt_horizon.
actual_by_method={}
for m in METHODS:
 actual_by_method[m]=[r for r in score if r['method']==m and r['source_type']=='actual_http_receipt' and r.get('receipt_horizon') and not r.get('foundation_overlap')]

# Per-week concentration and market/time/league contributions.
actual_detail={}
for m in METHODS:
 rows=actual_by_method[m]
 # Join receipt time/minutes and FT source from independent audit rows.
 audit={}
 for line in open(M8/'m8_batch_actual_receipt_independently_audited_20261118.jsonl'):
  x=json.loads(line)
  if x['method']==m:audit[str(x['fid'])]=x
 th=float(RESULT['actual_receipt_transfer_calibrations'][m]['top20_prior_confidence']['threshold'])
 selected=[r for r in rows if r.get('confidence_abs') is not None and abs(float(r['confidence_abs']))>=th]
 for r in selected:
  a=audit.get(r['fid']) or archive_by_time.get((r['fid'],str(r.get('received_utc'))),{});r['league_id']=league_by_fid.get(r['fid'],'NA')
  r['league_name']=league_name_by_id.get(r['league_id'],r['league_id'])
  r['received_minutes_to_kickoff']=a.get('received_minutes_to_kickoff')
  r['snapshot_horizon']=a.get('snapshot_horizon')
 # exact date range weeks 41-46; include foundation base on same fixture-date window separately
 actual_detail[m]={'threshold':th,'full_valid_pool':summary(rows),'selected_incremental':summary(selected),
   'selected_score_distribution':qstats([r['score_home_minus_away'] for r in selected]),
   'selected_weekly':{w:{'n':v['n'],'U':v['U'],'ROI_pct':v['ROI_pct']} for w,v in summary(selected)['weekly'].items()},
   'league':bin_table(selected,'league_name'),'league_id':bin_table(selected,'league_id'),'handicap_line':bin_table(selected,'line_bucket'),
   'market_fav_odds':bin_table(selected,'favorite_odds_bucket'),'predicted_side':bin_table(selected,'side'),
   'receipt_horizon':bin_table(selected,'snapshot_horizon')}
 # kickoff timing bands from actual receipt metadata
 tb=collections.defaultdict(list)
 for r in selected:
  x=r.get('received_minutes_to_kickoff')
  b='NA' if x is None else '<1h' if x<60 else '1-3h' if x<180 else '3-12h' if x<720 else '>=12h'
  tb[b].append(r)
 actual_detail[m]['receipt_lead_time']= {k:summary(v) for k,v in sorted(tb.items())}

# Original frozen eight exact same actual-receipt ISO-week window.
base=[]
for fid,r in foundation.items():
 if dateweek(r['date']) in {f'2026-W{i:02d}' for i in range(41,47)}:
  base.append({'fid':fid,'date':r['date'],'pnl_u':float(r['pnl'])})
base_stats=summary(base)
# Within identical window, non-overlap candidate subsets and merged result per individual method.
window_comparison={}
for m in METHODS:
 cand=[r for r in actual_by_method[m] if dateweek(r['date']) in {f'2026-W{i:02d}' for i in range(41,47)} and abs(float(r.get('confidence_abs') or 0))>=actual_detail[m]['threshold']]
 ids={r['fid'] for r in cand}; merged=base+[r for r in cand if r['fid'] not in foundation]
 def sixweek(rows):
  x=summary(rows); weeks=[f'2026-W{i:02d}' for i in range(41,47)]; weekly=x.get('weekly',{});x['weekly']={w:weekly.get(w,{'n':0,'U':0.0,'ROI_pct':None}) for w in weeks};x['weeks_elapsed']=6;x['orders_per_week']=x['n']/6;return x
 window_comparison[m]={'base':sixweek(base),'new_candidates':sixweek(cand),'new_outside_base':sixweek([r for r in cand if r['fid'] not in foundation]),
  'merged_foundation':sixweek(merged),'overlap_with_base':sum(r['fid'] in foundation for r in cand),
  'unique_new_fids':len({r['fid'] for r in cand if r['fid'] not in foundation})}

# Same-FID historical quote comparison: separate event-source prices from actual receipts.
hist_by_key={(r['method'],r['fid']):r for r in score if r['source_type']=='historical_event_replay'}
paired_receipt_comparison={}
for m in METHODS:
 selected= [r for r in actual_by_method[m] if abs(float(r.get('confidence_abs') or 0))>=actual_detail[m]['threshold']]
 pairs0=[(r,hist_by_key.get((m,r['fid']))) for r in selected if hist_by_key.get((m,r['fid'])) is not None]
 paired_receipt_comparison[m]={'n_same_fid':len(pairs0),'quote_exact_n':sum((r['line_home'],r['odds_home'],r['odds_away'])==(h['line_home'],h['odds_home'],h['odds_away']) for r,h in pairs0),
  'line_changed_n':sum(r['line_home']!=h['line_home'] for r,h in pairs0),'price_changed_n':sum((r['odds_home'],r['odds_away'])!=(h['odds_home'],h['odds_away']) for r,h in pairs0),
  'side_changed_n':sum(r['side']!=h['side'] for r,h in pairs0),'historical_same_fid_pnl':summary([dict(r,date=r['date'],pnl_u=h['pnl_u']) for r,h in pairs0]),
  'actual_receipt_pnl':summary([r for r,h in pairs0])}

# New response snapshots: choose the latest as-of-receipt response per FID; verify raw file SHA,
# Crown source quote local-time(+08:00) <= receive and kickoff, then settle at existing verified FT.
snapshot_rows=[]
for fid,received,path,sha,kickoff in captures:
 raw=Path(path).read_bytes(); assert hashlib.sha256(raw).hexdigest()==sha, (fid,received,'sha mismatch')
 obj=json.loads(raw); event=obj['data'][0]; crown=next((b for b in event['bookmakers'] if b.get('slug')=='crown'),None)
 if not crown or not crown.get('asian') or not crown.get('goal'):continue
 recv=dt.datetime.fromisoformat(received.replace('Z','+00:00')); ko=dt.datetime.fromisoformat(kickoff.replace('Z','+00:00'))
 market={}
 valid=True
 for k,field in [('AH','asian'),('OU','goal')]:
  q=crown[field]['close']; local=dt.datetime.strptime(q['time'],'%Y-%m-%d %H:%M:%S').replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
  utc=local.astimezone(dt.timezone.utc)
  if utc>recv or utc>=ko:valid=False
  market[k]={'source_local':q['time'],'source_utc':utc.isoformat(),'source_age_minutes':(recv-utc).total_seconds()/60,**q}
 if not valid: continue
 snapshot_rows.append({'fid':str(fid),'received_utc':received,'kickoff_utc':kickoff,'league_name':event.get('l'),'league_id':str(event.get('l_id')),
  'response_sha256':sha,'raw_file_sha256_verified':True,'AH':market['AH'],'OU':market['OU']})
# Keep latest valid Crown quote per FID; captures may repeat same response/price.
latest={}
for r in snapshot_rows:
 if r['fid'] not in latest or r['received_utc']>latest[r['fid']]['received_utc']:latest[r['fid']]=r

# Recompute E/I/MR from these new quote inputs using unchanged 2024-25 training and q80 thresholds.
# Outcomes are used only for settlement, never for features or fit.
R_by_fid={str(q['fid']):q for q in il['R']}; EH_R={str(q['fid']):q for q in eh['R']}
Rindex={str(q['fid']):i for i,q in enumerate(il['R'])}; pair_by_fid={str(p[0]['fid']):p for p in il['pairs']}
new_score_rows=[]
# E fixed softmax fit, trained only on historical rows in year < 2026.
tr_e=eh['history_ind'] & (eh['HY']<2026)
mu_e=eh['XE'][tr_e].mean(0);sd_e=eh['XE'][tr_e].std(0);mu_e[0]=0;sd_e[0]=1;sd_e[sd_e<1e-10]=1
Ae=(eh['XE'][tr_e]-mu_e)/sd_e; ye=eh['classes'][tr_e]
def e_obj(flat):
 W=flat.reshape(Ae.shape[1],4); logits=np.column_stack((Ae@W,np.zeros(len(Ae))));logits-=logits.max(1,keepdims=True);p=np.exp(logits);p/=p.sum(1,keepdims=True)
 loss=-np.log(np.maximum(p[np.arange(len(p)),ye],1e-15)).sum()+50*np.sum(W[1:]**2)
 grad=Ae.T@(p[:,:4]-np.eye(5)[ye][:,:4])+100*np.vstack((np.zeros((1,4)),W[1:]))
 return loss,grad.ravel()
opt=minimize(e_obj,np.zeros(Ae.shape[1]*4),jac=True,method='L-BFGS-B',options={'maxiter':250,'ftol':1e-10})
assert opt.success
We=opt.x.reshape(Ae.shape[1],4)
for fid,snap in latest.items():
 if fid not in R_by_fid or fid not in EH_R or fid not in pair_by_fid:continue
 baseq=R_by_fid[fid]; olde=EH_R[fid]
 q=dict(baseq);q.update({'al':float(snap['AH']['line']),'ah':float(snap['AH']['home']),'aa':float(snap['AH']['away']),
  'ol':float(snap['OU']['line']),'oo':float(snap['OU']['over']),'ou':float(snap['OU']['under']),
  'age_ah':snap['AH']['source_age_minutes'],'age_ou':snap['OU']['source_age_minutes']})
 # E softmax at current actual Crown contract.
 ex=eh['contract_features']([q]);be=(ex-mu_e)/sd_e;logits=np.column_stack((be@We,np.zeros(1)));logits-=logits.max(1,keepdims=True);pp=np.exp(logits);pp/=pp.sum(1,keepdims=True)
 p0,p1,p2,p3,p4=pp[0];ehome=p4*(q['ah']-1)+.5*p3*(q['ah']-1)-p0-.5*p1; eaway=p0*(q['aa']-1)+.5*p1*(q['aa']-1)-p4-.5*p3
 eside='home' if ehome>=eaway else 'away'; epnl=eh['manual_ah_settle'](q['al'],eside,int(q['hg']),int(q['ag']),q['ah'] if eside=='home' else q['aa'])
 # Latent market-response path features with exact T24 anchor and newly received Crown AH/OU quote.
 tq={k:q[k] for k in ('al','ah','aa','ol','oo','ou')};tq.update({k:q[k] for k in ('fid','date','year','home_id','away_id','hg','ag','league') if k in q})
 first=pair_by_fid[fid][0];il['cache_quote'](first);il['cache_quote'](tq);valid,xnew=il['latent']([(first,tq)])
 if not valid[0]:raise RuntimeError(f'latent inversion invalid {fid}')
 i=Rindex[fid];shot=il['rs'][i:i+1]
 basefeat=il['make_x'](xnew,'response');z=shot[:,[0,1,4,5]];line=np.array([q['al']])[:,None]
 xi=np.column_stack((basefeat,z,line,z*line))
 # Two exact saved Ridge/GLM formulations, fitted on historical only (<2026).
 tr=il['history_ind']&(il['HY']<2026); ytot=il['hyn'][tr]; home=il['hyh'][tr]; ntot=il['hyn'][tr]
 aa,bb,cc,dd=il['state'](il['hx']); na,nb,nc,nd=il['state'](xnew)
 total_i,_=il['fit_total'](il['X_I'][tr],ytot,bb[tr],xi,nb)
 frac_i,_=il['fit_share'](il['X_I'][tr],home,ntot,dd[tr],xi,nd)
 side_i,_,hev_i,aev_i=il['choose_ev']([q],total_i,frac_i); iside=str(side_i[0]); ipnl=il['settle_ah'](int(q['hg'])-int(q['ag']) if iside=='home' else int(q['ag'])-int(q['hg']),float(q['al']) if iside=='home' else -float(q['al']),float(q['ah']) if iside=='home' else float(q['aa']))
 # market_response uses the same fit but the un-interacted Crown response features.
 xbase=il['make_x'](xnew,'response')
 total_m,_=il['fit_total'](il['X_BASE'][tr],ytot,bb[tr],xbase,nb)
 frac_m,_=il['fit_share'](il['X_BASE'][tr],home,ntot,dd[tr],xbase,nd)
 side_m,_,hev_m,aev_m=il['choose_ev']([q],total_m,frac_m); mside=str(side_m[0]); mpnl=il['settle_ah'](int(q['hg'])-int(q['ag']) if mside=='home' else int(q['ag'])-int(q['hg']),float(q['al']) if mside=='home' else -float(q['al']),float(q['ah']) if mside=='home' else float(q['aa']))
 vals={'E_discrete_AH_contract_calibration':(eside,epnl,max(ehome,eaway),ehome,eaway),
       'I_line_style':(iside,ipnl,abs(float(hev_i[0])-float(aev_i[0])),float(hev_i[0]),float(aev_i[0])),
       'market_response':(mside,mpnl,abs(float(hev_m[0])-float(aev_m[0])),float(hev_m[0]),float(aev_m[0]))}
 for m,(side,pnl,conf,he,ae) in vals.items():
  threshold=float(RESULT['actual_receipt_transfer_calibrations'][m]['top20_prior_confidence']['threshold'])
  new_score_rows.append({'fid':fid,'date':str(q['date']),'league_id':snap['league_id'],'league_name':snap['league_name'],
   'received_utc':snap['received_utc'],'kickoff_utc':snap['kickoff_utc'],'quote_source_utc_AH':snap['AH']['source_utc'],
   'line_home':q['al'],'odds_home':q['ah'],'odds_away':q['aa'],'side':side,'predicted_home_EV':he,'predicted_away_EV':ae,
   'confidence':conf,'confidence_abs_for_gate':abs(conf),'saved_threshold':threshold,'selected_by_saved_threshold':abs(conf)>=threshold,'settlement_u':round(float(pnl),6),'pnl_u':round(float(pnl),6),
   'already_in_20261119_design':True,'foundation_overlap':fid in foundation,'method':m})

# Same-match prediction correlations and conflict ledger on previously selected sets.
selected={m:{r['fid']:r for r in actual_by_method[m] if abs(float(r.get('confidence_abs') or 0))>=actual_detail[m]['threshold']} for m in METHODS}
common=set.intersection(*(set(selected[m]) for m in METHODS))
conflicts=[]
for fid in sorted(set.union(*(set(selected[m]) for m in METHODS))):
 rows={m:selected[m].get(fid) for m in METHODS}
 dirs={m:(r.get('side') if r else None) for m,r in rows.items()}
 if len({v for v in dirs.values() if v})>1:
  conflicts.append({'fid':fid,'date':next(r['date'] for r in rows.values() if r),'league_id':league_by_fid.get(fid),
   'scores':{m:(rows[m].get('score_home_minus_away') if rows[m] else None) for m in METHODS},'directions':dirs,
   'actual_pnl':{m:(rows[m].get('pnl_u') if rows[m] else None) for m in METHODS},
   'line_home':{m:(rows[m].get('line_home') if rows[m] else None) for m in METHODS},
   'odds':{m:([rows[m].get('odds_home'),rows[m].get('odds_away')] if rows[m] else None) for m in METHODS}})
# Compute score-pair correlations on rows with complete, same-FID selected scores.
correlations={}
for a,b in [('E_discrete_AH_contract_calibration','I_line_style'),('E_discrete_AH_contract_calibration','market_response'),('I_line_style','market_response')]:
 ids=set(selected[a])&set(selected[b]);x=[];y=[]
 for fid in ids:
  x.append(float(selected[a][fid]['score_home_minus_away']));y.append(float(selected[b][fid]['score_home_minus_away']))
 correlations[f'{a}__{b}']={'shared_fids':len(ids),'score_pearson':float(np.corrcoef(x,y)[0,1]) if len(ids)>2 and np.std(x)>0 and np.std(y)>0 else None,
  'same_direction':sum(selected[a][fid]['side']==selected[b][fid]['side'] for fid in ids)}

# 48 quote mismatch reasons re-evaluated against exact original receive-time archive row.
archive_path=Path('/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')
archive=[json.loads(x) for x in archive_path.open()]
archkey={(str(x['fixture_id']),str(x['received_utc'])):x for x in archive}
receipts={}
for r in score:
 if r['source_type']=='actual_http_receipt' and r['method'] in METHODS and not r.get('receipt_horizon'):
  if r.get('received_utc') and r.get('line_home') is not None:receipts[(r['method'],r['fid'])]=r
# Audit candidates without pass horizon identify 48 at the global set; report exact source labels if available.
mismatch_types=collections.Counter(); mismatch_fids=collections.defaultdict(set); mismatch_horizon_exact=collections.Counter(); mismatch_examples=[]
for r in all_actual_score_rows:
 t=r.get('received_utc') or r.get('signal_time_utc'); rec=archkey.get((str(r['fid']),str(t))) if t else None
 if not rec:continue
 ah=rec.get('markets',{}).get('AH') or {};od=ah.get('odds') or {};diff=[]
 if abs(float(ah.get('line',999))-float(r['line_home']))>1e-8:diff.append('line')
 if abs(float(od.get('home',999))-float(r['odds_home']))>1e-8:diff.append('home_odds')
 if abs(float(od.get('away',999))-float(r['odds_away']))>1e-8:diff.append('away_odds')
 if diff:
  k='+'.join(diff);mismatch_types[k]+=1;mismatch_fids[k].add(r['fid'])
  any_exact=any(str(a0['fixture_id'])==str(r['fid']) and abs(float(a0['markets']['AH']['line'])-float(r['line_home']))<1e-8 and abs(float(a0['markets']['AH']['odds']['home'])-float(r['odds_home']))<1e-8 and abs(float(a0['markets']['AH']['odds']['away'])-float(r['odds_away']))<1e-8 for a0 in archive)
  if any_exact:mismatch_horizon_exact[k]+=1
  if len(mismatch_examples)<24:mismatch_examples.append({'fid':r['fid'],'method':r['method'],'receipt_utc':t,'receipt_horizon':rec.get('snapshot_horizon'),'candidate_quote':[r['line_home'],r['odds_home'],r['odds_away']],'archived_quote':[ah.get('line'),od.get('home'),od.get('away')],'candidate_quote_seen_at_other_horizon':any_exact})
mismatch_summary={'rows':sum(mismatch_types.values()),'unique_fids':len(set().union(*mismatch_fids.values()) if mismatch_fids else set()),'mismatch_field_patterns':dict(mismatch_types),'unique_fids_by_pattern':{k:len(v) for k,v in mismatch_fids.items()},'candidate_quote_seen_at_other_horizon_by_pattern':dict(mismatch_horizon_exact),'interpretation':'Mismatches are primarily stale/different Crown price snapshots assigned to a later receipt cutoff; do not treat them as received prices. No substitute market prices were used.','examples':mismatch_examples}


out={
 'study':'M8 E/I/market_response decomposition and fresh receipt replay 2026-11-20',
 'thresholds_frozen':{m:float(RESULT['actual_receipt_transfer_calibrations'][m]['top20_prior_confidence']['threshold']) for m in METHODS},
 'historical_outside_frozen_eight':year_detail,
 'actual_receipt_outside_frozen_eight':actual_detail,
 'same_2026_W41_W46_window':window_comparison,
 'same_fixture_overlap_correlations':correlations,'direction_conflicts':conflicts,'same_fid_historical_vs_receipt':paired_receipt_comparison,
 'new_receipt_snapshot_rows':snapshot_rows,'new_receipt_latest_by_fid':list(latest.values()),'new_receipt_rescored':new_score_rows,
 'new_receipt_rescore_summary':{m:{'all_receipt_rows':summary([dict(r,pnl_u=r['settlement_u']) for r in new_score_rows if r['method']==m]),'selected_rows':summary([dict(r,pnl_u=r['settlement_u']) for r in new_score_rows if r['method']==m and r['selected_by_saved_threshold']]),'selected_fids':[r['fid'] for r in new_score_rows if r['method']==m and r['selected_by_saved_threshold']]} for m in METHODS},
 'new_receipt_coverage':{'captured_unique_fids':len(latest),'rescored_fids_by_method':{m:len({r['fid'] for r in new_score_rows if r['method']==m}) for m in METHODS},'unscored_fids':[{'fid':fid,'reason':'FID is absent from the saved M8 score/features; old receipt archive uses a stale 2026-11-12 kickoff while the live Crown response confirms rescheduled kickoff 2026-11-14, so prior horizon/time features and verified FT cannot be aligned.'} for fid in sorted(set(latest)-{r['fid'] for r in new_score_rows})],'new_fids_absent_from_all_prior_A_L_scores':sorted(set(latest)-{r['fid'] for r in score})},
 'mismatch_audit_note':mismatch_summary,
 'scope_notes':['Historical event-time rows are Crown source-event replay; actual receipts are true Crown HTTP received-before-kickoff data and kept separate.','2024 and 2025 are historical pre-forward baselines, not actual receipt years.','Selected subset thresholds are frozen at the 2024-25 historical confidence 80th percentile from the 2026-11-19 study; no threshold was tuned to 2026 realized PnL.','All late receipt FIDs already appeared in the 2026-11-19 design; they are new quote snapshots but not untouched fixture/outcome holdouts.','All selected candidate PnL is quarter-line Crown AH leg settlement at the quote in question; no alternative bookmaker odds were used.','E/I/market_response totals are separate model ledgers with overlap; conflicts are retained and no arbitration rule is applied.']}
(OUT/'M8_SELECTIVE_DECOMPOSITION_RESULTS_20261120.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=lambda o:o.item() if isinstance(o,np.generic) else str(o)))
# Concise CSV-like per new receipt prediction records and conflict list.
(OUT/'new_receipt_rescore_20261120.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'),default=lambda o:o.item() if isinstance(o,np.generic) else str(o))+'\n' for r in new_score_rows))
(OUT/'direction_conflicts_20261120.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'),default=lambda o:o.item() if isinstance(o,np.generic) else str(o))+'\n' for r in conflicts))
shutil.rmtree(RUN_TMP, ignore_errors=True)
print('RESULT',OUT/'M8_SELECTIVE_DECOMPOSITION_RESULTS_20261120.json')
print('HIST',json.dumps({m:{y:{'all':{k:v['all'][k] for k in ('n','U','ROI_pct','MDD_U')},'q80':{k:v['fixed_2024_25_q80_selected'][k] for k in ('n','U','ROI_pct','MDD_U')}} for y,v in yr.items()} for m,yr in year_detail.items()},ensure_ascii=False))
print('ACTUAL',json.dumps({m:{'selected':{k:actual_detail[m]['selected_incremental'][k] for k in ('n','U','ROI_pct','MDD_U','weeks')},'weekly':actual_detail[m]['selected_weekly'],'top_leagues':sorted([{'league':k,'n':v['n'],'U':v['U'],'ROI_pct':v['ROI_pct']} for k,v in actual_detail[m]['league'].items()],key=lambda z:(-abs(z['U']),-z['n']))[:8],'lines':actual_detail[m]['handicap_line'],'lead_time':actual_detail[m]['receipt_lead_time']} for m in METHODS},ensure_ascii=False))
print('BASEWINDOW',json.dumps({m:{k:{q:v[k].get(q) for q in ('n','U','ROI_pct','MDD_U','orders_per_week')} for k in ('base','new_outside_base','merged_foundation')} for m,v in window_comparison.items()},ensure_ascii=False))
print('OVERLAP',correlations,'conflicts',len(conflicts))
print('NEW',json.dumps(out['new_receipt_rescore_summary'],ensure_ascii=False,default=lambda o:o.item() if isinstance(o,np.generic) else str(o)))
