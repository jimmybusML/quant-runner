import json,collections,datetime,hashlib
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_joint_path_incremental_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Exact AH and OU payout are computed from matching T12 Crown quotes in the
# original R22 data. Each pair stakes half a unit on each market.
assert len(H)==38846 and len(R)==1230
def pay_matrix(q):
 return np.column_stack([
  .5*(vec(q,'home_U')+vec(q,'over_U')),
  .5*(vec(q,'home_U')+vec(q,'under_U')),
  .5*(vec(q,'away_U')+vec(q,'over_U')),
  .5*(vec(q,'away_U')+vec(q,'under_U')),
 ])
HP=pay_matrix(H);RP=pay_matrix(R)
def phase(v):return int(round(float(v)*4))%4
def group(q,mode):
 if mode=='pooled':return ['all']*len(q)
 if mode=='quarter_faces':return [(phase(x['al']),phase(x['ol'])) for x in q]
 if mode=='sign_quarter_faces':
  return [(int(np.sign(float(x['al']))),phase(x['al']),phase(x['ol'])) for x in q]
 if mode=='current_exact_lines':return [(float(x['al']),float(x['ol'])) for x in q]
 raise ValueError(mode)
def choose_prior(history,mask,groups,payment,targetgroups):
 # Past-only average realized 1U pair payout; if entirely unseen exact
 # group, use overall pooled past choice. No minimum-count threshold.
 sums=collections.defaultdict(lambda:np.zeros(4));n=collections.Counter()
 for i in np.flatnonzero(mask):
  k=groups[i];sums[k]+=payment[i];n[k]+=1
 pooled=np.argmax(payment[mask].mean(axis=0))
 return np.array([int(np.argmax(sums[k]/n[k])) if n[k] else int(pooled) for k in targetgroups],int),n
hm=(HY>=2024)&(HY<=2026)&foundation&other
rm=rf&ro
out={'method':'R47 price-only, model-free historical settlement check of paired AH and OU bets. Four exact T12 Crown two-market contracts per match, half-unit allocated to AH and half to OU for total stake 1U. Past-calendar-year realized pair payoffs determine one of four side combinations for each present-time contract family, no selective skip, no EV gate, no sample-size minimum, unseen group uses pooled historical side. Compare pooled, two quarter-line face types, sign+two quarter-line faces, and exact two signed lines; group definitions research only, not production rules. Same fixtures/market odds and time-based earlier-year training as R22, exclude receipt target FIDs from fit. All periods and negative subgroups retained. Historical quotes retrieved after events with prior source-event timestamps are not real-time receipt. Original8 and old unpromoted candidate exclusions only retrospective incremental accounting; not real-time known signals. Receipt replay separate with overlapping fixtures.','coverage':{'history_pairs':len(H),'receipt_pairs':len(R),'historical_incremental':int(hm.sum()),'receipt_incremental':int(rm.sum()),'historical_disjoint_receipt':int((hm&history_ind).sum()),'year_counts':{str(y):int((hm&(HY==y)).sum()) for y in (2024,2025,2026)}},'models':{}}
for mode in ('pooled','quarter_faces','sign_quarter_faces','current_exact_lines'):
 hgroups=group(H,mode);rgroups=group(R,mode);pred=np.zeros(len(H),int);rpred=np.zeros(len(R),int);meta={}
 for y in (2024,2025,2026):
  tr=(HY<y)&history_ind;te=np.flatnonzero(HY==y);re=np.flatnonzero(RY==y)
  assert np.max(HY[tr])<y
  pred[te],n=choose_prior(H,tr,hgroups,HP,[hgroups[i] for i in te])
  rpred[re],_=choose_prior(H,tr,hgroups,HP,[rgroups[i] for i in re])
  meta[str(y)]={'train_n':int(tr.sum()),'observed_training_groups':len(n),'test_groups':len({hgroups[i] for i in te}),'receipt_groups':len({rgroups[i] for i in re}),'unseen_test_n':sum(n[hgroups[i]]==0 for i in te),'unseen_receipt_n':sum(n[rgroups[i]]==0 for i in re)}
 hp=HP[np.arange(len(H)),pred];rp=RP[np.arange(len(R)),rpred]
 z={'history':score(H,hp,hm),'history_disjoint_receipt':score(H,hp,hm&history_ind),'receipt':score(R,rp,rm),'year':{str(y):score(H,hp,hm&(HY==y)) for y in (2024,2025,2026)},'fit':meta}
 # Each market legs separately, same compound choice; not additional stakes.
 for market,cols in [('AH',(0,2)),('OU',(0,1))]:
  hside=pred//2 if market=='AH' else pred%2
  rside=rpred//2 if market=='AH' else rpred%2
  w=vec(H,'home_U' if market=='AH' else 'over_U');l=vec(H,'away_U' if market=='AH' else 'under_U')
  rw=vec(R,'home_U' if market=='AH' else 'over_U');rl=vec(R,'away_U' if market=='AH' else 'under_U')
  z[market+'_leg']={'history':score(H,np.where(hside==0,w,l),hm),'receipt':score(R,np.where(rside==0,rw,rl),rm)}
 out['models'][mode]=z
 strip=lambda x:{k:v for k,v in x.items() if k!='weekly_counts'}
 print('RESULT',mode,'H',strip(z['history']),'R',strip(z['receipt']),'annual',{y:strip(v) for y,v in z['year'].items()},'disjoint',strip(z['history_disjoint_receipt']),flush=True)
 print('LEGS',mode,{m:(strip(z[m+'_leg']['history']),strip(z[m+'_leg']['receipt'])) for m in ('AH','OU')},'train',meta,flush=True)
# Also test unconditional fixed direction benchmarks for transparency.
bench={
 'home_over':HP[:,0], 'home_under':HP[:,1],'away_over':HP[:,2],'away_under':HP[:,3],
 'equal_four_sides':HP.mean(axis=1),
}
out['reference']={k:{'history':score(H,p,hm),'receipt':score(R,(RP[:,0] if k=='home_over' else RP[:,1] if k=='home_under' else RP[:,2] if k=='away_over' else RP[:,3] if k=='away_under' else RP.mean(axis=1)),rm)} for k,p in bench.items()}
for k,z in out['reference'].items():
 print('REFERENCE',k,z['history']['n'],z['history']['ROI'],z['receipt']['n'],z['receipt']['ROI'],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_cross_market_pair_settlement_20261117.json').write_text(json.dumps(out,indent=2))
