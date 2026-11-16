import json,datetime,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Restore frozen OU candidate membership and verified receipt universe.
s=(P/'m8_tc_complementary_league_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
ouids={a['fid'] for a,b in zip(t,band|static(t)) if b}|{a['fid'] for a,b in zip(rt,rb|static(rt)) if b}
assert len(ids)>0 and len(ouids)>=2238
from research.m3.probabilities import settle_score
# Use all previously stored joint-market historical quotes, not TC-performance coverage.
inventory=collections.defaultdict(dict)
for a in load('m8_early_joint_market_inventory_20261115.jsonl'):
 if a['T'] in (24,12): 
  assert a['T'] not in inventory[a['fid']]
  inventory[a['fid']][a['T']]=a
hist=[]
for f,q in inventory.items():
 if 24 not in q or 12 not in q:continue
 a,b=q[24],q[12]
 assert all(a[k]==b[k] for k in ('fid','date','year','league','home_id','away_id','hg','ag'))
 hist.append((a,b))
print('historical pairs',len(hist),'leagues',len({b['league'] for a,b in hist}),flush=True)
# Actual receipts: final score identity already established in rows; verify each raw snapshot.
pairs=[];errors=collections.Counter();rd={a['fid']:a for a in rows}
verified_kickoff={a['fid']:audit['dt'](a['kickoff_utc']) for a in records if a['verified_receipt'] and a['FT'] is not None}
for f,b in rd.items():
 qs=sorted(audit['by'][f],key=lambda a:audit['dt'](a['received_utc']),reverse=True)
 e=[a for a in qs if (audit['dt'](a['kickoff_utc'])-audit['dt'](a['received_utc'])).total_seconds()>=86400]
 l=[a for a in qs if 43200<=(audit['dt'](a['kickoff_utc'])-audit['dt'](a['received_utc'])).total_seconds()<86400]
 if not e or not l:errors['no_two_time_windows']+=1;continue
 def checked(seq,T):
  for a in seq:
   try:
    q=audit['verify'](a)
    assert all(str(q[x])==str(b[y]) for x,y in [('id','fid'),('l_id','league'),('h_id','home_id'),('a_id','away_id')])
    assert audit['local'](q['start']).date().isoformat()==b['date']
    ko=audit['dt'](a['kickoff_utc']);assert ko==verified_kickoff[f];cut=ko-datetime.timedelta(hours=T)
    obj={k:b[k] for k in ('fid','league','date','year','hg','ag','home_id','away_id')}
    for market,names in [('AH',('al','ah','aa','home','away')),('OU',('ol','oo','ou','over','under'))]:
     ln,x,y,sa,sb=names;d=a['markets'][market]
     obj[ln]=d['line'];obj[x]=d['odds'][sa];obj[y]=d['odds'][sb]
     obj['age_'+market.lower()]=(cut-audit['dt'](d['source_event_utc'])).total_seconds()/3600
     assert obj['age_'+market.lower()]>=0
     for side,price in [(sa,obj[x]),(sb,obj[y])]:obj[side+'_U']=settle_score(market,obj[ln],side,int(obj['hg']),int(obj['ag']),price)[1]
    return obj
   except Exception as exc:errors['verify:'+type(exc).__name__]+=1
  return None
 aa=checked(e,24);bb=checked(l,12)
 if aa and bb:pairs.append((aa,bb))
print('verified actual pairs',len(pairs),'errors',dict(errors),flush=True)
# Current price and line as baseline; add cross-market movements observed before T12.
def snapshot(q):
 ah=q['aa']/(q['ah']+q['aa']);ou=q['ou']/(q['oo']+q['ou'])
 return np.array([q['al'],q['ol'],ah,ou,1/q['ah']+1/q['aa']-1,1/q['oo']+1/q['ou']-1])
def feature(a,b,kind):
 x=snapshot(a);y=snapshot(b)
 f=[1.,*y,abs(y[0]),np.log1p(b['age_ah']),np.log1p(b['age_ou'])]
 if kind=='path':
  delta=y-x;f += list(delta)+[np.log1p(a['age_ah']),np.log1p(a['age_ou']),delta[0]*delta[1],delta[2]*delta[3],y[0]*delta[3],y[1]*delta[2]]
 return f
H=[b for a,b in hist];R=[b for a,b in pairs]
HY=np.array([b['year'] for b in H]);RY=np.array([b['year'] for b in R])
# Fit solely on earlier calendar years; exclude all verified receipt target IDs in fit.
history_ind=np.array([b['fid'] not in receiptids for b in H]);foundation=np.array([b['fid'] not in ids for b in H]);other=np.array([b['fid'] not in ouids for b in H])
rf=np.array([b['fid'] not in ids for b in R]);ro=np.array([b['fid'] not in ouids for b in R])
def score(q,p,mask):
 if not mask.any():return {'n':0}
 d=collections.defaultdict(float);weeks=collections.Counter()
 for a,u,b in zip(q,p,mask):
  if b:
   d[a['date']]+=float(u);weeks[datetime.date.fromisoformat(a['date']).strftime('%G-W%V')]+=1
 c=peak=dd=0.
 for _,u in sorted(d.items()):c+=u;peak=max(peak,c);dd=max(dd,peak-c)
 return {**g['stat'](p[mask]),'daily_mdd':round(dd,3),'active_weeks':len(weeks),'weekly_counts':dict(sorted(weeks.items()))}
out={'method':'R22 paired historical T24/T12 Crown AH+OU, prior calendar year ridge payout-difference model (penalty100 inherited as experimental), current-only versus pre-T12 cross-market path. Both sides scored and one side per market per fixture, no EV or outcome filter. Whole time periods retained. Actual pregame receipt pairs separately raw/snapshot/FT verified, no separate prospective model claims; historical quote times are not real receipt times. Original-eight and saved OU candidate fixture IDs excluded only to measure incremental contribution. All results retained.','coverage':{'historical_pairs':len(H),'historical_leagues':len({a['league'] for a in H}),'receipt_pairs':len(R),'receipt_errors':dict(errors),'receipt_outside_eight':int(rf.sum()),'receipt_outside_all_candidates':int((rf&ro).sum()),'historical_dates':[min(a['date'] for a in H),max(a['date'] for a in H)],'receipt_dates':[min(a['date'] for a in R),max(a['date'] for a in R)] if R else None},'models':{}}
for market,sa,sb in [('AH','home_U','away_U'),('OU','over_U','under_U')]:
 hu=vec(H,sa);au=vec(H,sb);ru=vec(R,sa);ra=vec(R,sb)
 y=hu-au
 for kind in ('current','path'):
  X=np.array([feature(a,b,kind) for a,b in hist]);Z=np.array([feature(a,b,kind) for a,b in pairs])
  hp=np.zeros(len(H));rp0=np.zeros(len(R));used=np.zeros(len(H),bool);rused=np.zeros(len(R),bool);meta={}
  for yr in (2024,2025,2026):
   tr=(HY<yr)&history_ind;te=HY==yr;re=RY==yr
   mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
   xx=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
   beta=np.linalg.solve(xx.T@xx+pen,xx.T@y[tr])
   hp[te]=((X[te]-mu)/sd)@beta
   if re.any():rp0[re]=((Z[re]-mu)/sd)@beta
   used|=te;rused|=re;meta[str(yr)]=int(tr.sum())
  pnl=np.where(hp>=0,hu,au);rrp=np.where(rp0>=0,ru,ra)
  hmask=used&foundation;hm=hmask&other;rm=rused&rf;rm0=rm&ro
  a={'historical_outside_eight':score(H,pnl,hmask),'historical_incremental':score(H,pnl,hm),'historical_incremental_disjoint_receipt':score(H,pnl,hm&history_ind),'receipt_outside_eight':score(R,rrp,rm),'receipt_incremental':score(R,rrp,rm0),'year':{str(yr):score(H,pnl,hm&(HY==yr)) for yr in (2024,2025,2026)},'train_n':meta}
  # Full partition by observable quote differences, descriptive only.
  def changed(pairs):
   return np.array([any(abs(float(x[k])-float(y[k]))>1e-10 for k in ('al','ol','ah','aa','oo','ou')) for x,y in pairs])
  hc=changed(hist);rc=changed(pairs)
  a['change_partition']={'history_changed':score(H,pnl,hm&hc),'history_unchanged':score(H,pnl,hm&~hc),'receipt_changed':score(R,rrp,rm0&rc),'receipt_unchanged':score(R,rrp,rm0&~rc)}
  assert a['change_partition']['history_changed']['n']+a['change_partition']['history_unchanged']['n']==a['historical_incremental']['n']
  assert a['change_partition']['receipt_changed']['n']+a['change_partition']['receipt_unchanged']['n']==a['receipt_incremental']['n']
  print('CHANGE_PARTITION',market,kind,{k:{j:b for j,b in x.items() if j!='weekly_counts'} for k,x in a['change_partition'].items()},flush=True)
  out['models'][market+'_'+kind]=a
  small=lambda x:{k:v0 for k,v0 in x.items() if k!='weekly_counts'}
  print(market,kind,{k:small(a[k]) for k in ('historical_outside_eight','historical_incremental','historical_incremental_disjoint_receipt','receipt_outside_eight','receipt_incremental')},'year',{k:small(v0) for k,v0 in a['year'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v0 for k,v0 in manifest['input_sha256'].items()),'scripts':all(dig(k)==v0 for k,v0 in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_early_joint_path_incremental_20261116.json').write_text(json.dumps(out,indent=2))
