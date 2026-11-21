"""Re-execute original M8 6/3/1 eight-group path rules on full 48,890
historical Crown AH T6 fixtures, using ALL quote events between T6 and T1.
Derived from original m8_frozen_eight_earlier_window_replay_20261116.py,
not the 3-point-only shorthand of cross-league PR67.
Research only. No production/Telegram writes; historic retrieved raw is not live.
"""
import gzip,json,collections,hashlib,math,datetime,bisect,pathlib,sys
import numpy as np
P=pathlib.Path(__file__).resolve().parent
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
S={}
for line in (WORK/'m8_independent_score_strength_20261114.jsonl').open():
 r=json.loads(line)
 S[str(r['fid'])]=(float(r['lambda_home_0.025']),float(r['lambda_away_0.025']))
expanded={}
extra=P/'source69/research/m8/red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'
if not extra.exists(): extra=WORK/'recovered_factors_20261121/source69/research/m8/red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'
with gzip.open(extra,'rt') as f:
 for line in f:
  r=json.loads(line)
  expanded[str(r['fid'])]={'path':r['source_files'][0],'sha':r['source_sha256'][0],
    'score_rates':tuple(r['score_rates']),'source_info':r}
assert len(expanded)==6967
m={}
for line in (WORK/'m8_foundation_20261115/historical_membership.jsonl').open():
 r=json.loads(line);m[str(r['fid'])]=r
assert len(m)==10294
original={}
for line in (WORK/'jack_crown_round1_20261121/unified_quotes.jsonl').open():
 r=json.loads(line)
 if r['T']==6:original[str(r['fid'])]=r
assert len(original)==41923
priced={}
with gzip.open(P/'full_priced_T6_original_and_expanded.jsonl.gz','rt') as f:
 for line in f:
  r=json.loads(line);priced[str(r['fid'])]=r
assert len(priced)==48890
def parse(s):
 x=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 if x.tzinfo:return x.astimezone(datetime.timezone.utc)
 return x.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8))).astimezone(datetime.timezone.utc)
def sg(v):return 1 if v>1e-9 else -1 if v< -1e-9 else 0
def prob(q):return q[3]/(q[2]+q[3])
def pmf(lam):
 l=[math.exp(-lam)]
 for k in range(1,40):l.append(l[-1]*lam/k)
 return np.array(l)
def frozen_G_sign(rates,l,h,a):
 hp,ap=map(pmf,rates)
 gd=np.arange(40)[:,None]-np.arange(40)[None,:]
 masses=hp[:,None]*ap[None,:]
 w=lose=0.
 for z in (math.floor(l*2+1e-8)/2, math.ceil(l*2-1e-8)/2):
  w+=masses[gd+z>0].sum()/2;lose+=masses[gd+z<0].sum()/2
 return sg(w*(h-1)-lose-(lose*(a-1)-w)) or 1
def settle(l,side,hg,ag,ho,ao):
 signed=l*(1 if side=='home' else -1)
 d=(hg-ag)*(1 if side=='home' else -1)
 odds=ho if side=='home' else ao
 def part(z):
  x=d+z
  return odds-1 if x>1e-9 else -1. if x< -1e-9 else 0.
 if int(round(signed*4))%2:return (part(signed-.25)+part(signed+.25))/2
 return part(signed)
def exact_rule(path,ko,rates):
 cuts=[ko-datetime.timedelta(hours=i) for i in (6,3,1)]
 times=[q[0] for q in path]
 ix=[bisect.bisect_right(times,t)-1 for t in cuts]
 if min(ix)<0:return (None,None,'no_T6',None)
 i,j,k=ix;start,mid,end=[path[z] for z in ix];seq=path[i:k+1]
 steps=[(u,v) for u,v in zip(seq,seq[1:]) if u[1]!=v[1]]
 l=end[1];sl=start[1];ml=mid[1]
 def state(x,y):return 'deepen' if (y-x)*l>0 else 'weaken' if (y-x)*l<0 else 'same'
 shape='never_changed' if not steps else ('reverted' if sl==l else
    'one_way' if all((v[1]-u[1])*(l-sl)>0 for u,v in steps) else 'oscillating')
 dog='home' if l>0 else 'away';fav='away' if l>0 else 'home'
 g=side=None
 if (l-sl)*l>0:g='base';side=dog
 elif l and state(sl,ml)+'_'+state(ml,l)=='deepen_weaken':g='A';side=dog
 elif l and state(sl,ml)+'_'+state(ml,l)=='weaken_same':g='B';side=dog
 elif l and shape=='oscillating':g='C';side=fav
 elif not l and shape=='reverted':
  dur=sh=sa=0.
  for n,q in enumerate(seq):
   if q[1]!=l:continue
   lo=max(cuts[0],q[0]);hi=seq[n+1][0] if n+1<len(seq) else cuts[2]
   dd=max(0.,(hi-lo).total_seconds());dur+=dd;sh+=dd*q[2];sa+=dd*q[3]
  if dur and (end[2]-sh/dur)-(end[3]-sa/dur)<-1e-9:g='D';side='away'
 elif not l and shape=='never_changed':
  p0,p3,p1=map(prob,(start,mid,end));x,y=sg(p3-p0),sg(p1-p3);net=sg(p1-p0)
  moves=[prob(v)-prob(u) for u,v in zip(seq,seq[1:]) if abs(prob(v)-prob(u))>1e-10]
  ss=net or x or y or sg(moves[-1] if moves else 0)
  if ss and moves:
   up=any(z>0 for z in moves);down=any(z<0 for z in moves)
   if up and down and not net:g='E';side='away' if ss>0 else 'home'
   elif (not up or not down) and x==0 and y*ss==1:g='F';side='home' if ss>0 else 'away'
 if g is None and shape=='reverted' and rates:
  market=sg(prob(end)-prob(start));mod=frozen_G_sign(rates,l,end[2],end[3])
  if market and market==mod:g='G';side='away' if mod>0 else 'home'
 return (g,side,shape,(start,mid,end,len(seq),ix))
stats=collections.Counter()
ledger=[]
for fid,record in priced.items():
 if record['source']=='original49':
  r=original[fid];sourcefile=pathlib.Path(r['source_file']);sha=r['raw_sha256']
  rates=S.get(fid)
 else:
  r=expanded[fid];sourcefile=pathlib.Path(r['path']);sha=r['sha'];rates=r['score_rates']
 try:
  body=sourcefile.read_bytes()
  if hashlib.sha256(body).hexdigest()!=sha:stats['raw_sha_mismatch']+=1;continue
  f=next(x for x in json.loads(body).get('data',[]) if str(x.get('id'))==fid)
  if str(f.get('l_id'))!=str(record['league']):stats['league_mismatch']+=1;continue
  ko=parse(f['start'])
  if ko!=parse(record['ko']):stats['ko_mismatch']+=1;continue
  if (int(f['hg']),int(f['ag']))!=(record['hg'],record['ag']):stats['ft_mismatch']+=1;continue
  crown=next(b for b in f.get('bookmakers',[]) if b['slug']=='crown')
  path=[]
  for item in crown.get('asian_list') or []:
   try:
    t=parse(item[4]);l,ho,ao=map(float,item[1:4])
    if t<ko and ho>1 and ao>1 and all(math.isfinite(z) for z in (l,ho,ao)) and abs(l*4-round(l*4))<1e-8:
     path.append((t,l,ho,ao))
   except Exception:pass
  path.sort(key=lambda x:x[0])
  stats['source_'+record['source']]+=1
  g,side,shape,details=exact_rule(path,ko,rates)
  if shape=='no_T6':stats['no_full_631']+=1;continue
  stats['full_quote_path']+=1
  stat_member=m.get(fid)
  if record['source']=='original49' and stat_member and not rates:
   stats['frozen_missing_score_rate']+=1
  if g is None:
   stats['no_trigger']+=1
   continue
  stats['group_'+g]+=1
  a,b,c,nseq,ix=details
  l,ho,ao=c[1],c[2],c[3]
  pnl=settle(l,side,record['hg'],record['ag'],ho,ao)
  row={'fid':fid,'year':record['year'],'league':record['league'],
    'source':record['source'],'group':g,'side':side,'net_u_T1':pnl,
    'is_frozen_member':bool(stat_member),
    'frozen_group':stat_member['cohort'] if stat_member else None,
    'T1_home_line':l,'T1_home_odds':ho,'T1_away_odds':ao,
    'T6_utc':a[0].isoformat(),'T3_utc':b[0].isoformat(),'T1_utc':c[0].isoformat(),
    'T6_to_T1_full_quote_events':nseq,'shape_full_quote_path':shape,
    'raw_sha256':sha,'prospective_observation':False}
  if stat_member:
   stats['frozen_member_replay_hit']+=1
   stats['frozen_group_match']+=g==stat_member['cohort']
   stats['frozen_pnl_match']+=abs(pnl-float(stat_member['pnl']))<1e-7
   stats['frozen_group_mismatch']+=g!=stat_member['cohort']
   stats['frozen_pnl_mismatch']+=abs(pnl-float(stat_member['pnl']))>=1e-7
  ledger.append(row)
 except Exception as e:
  stattype='error_'+type(e).__name__
  stats[stattype]+=1
  if stats[stattype]<3:print('ERROR',fid,str(e)[:200],flush=True)
 if stats['source_original49']+stats['source_expanded15'] in (5000,20000,40000):
  print('PROGRESS',stats['source_original49']+stats['source_expanded15'],dict(stats),flush=True)
with gzip.open(P/'faithful_frozen_full_path_48890_ledger.jsonl.gz','wt') as w:
 for r in ledger:w.write(json.dumps(r,ensure_ascii=False)+'\n')
by=collections.defaultdict(list)
for r in ledger:
 by[(r['source'],r['group'],'member' if r['is_frozen_member'] else 'outside')].append(r)
def pack(rs):
 n=len(rs);u=sum(float(r['net_u_T1']) for r in rs)
 return {'n':n,'net_U':round(u,4),'ROI_pct':round(100*u/n,4) if n else None}
summary={'input_FIDs':len(priced),'original49':len(original),'expanded15':len(expanded),
 'processed':dict(stats),'group_source_membership':{'|'.join(key):pack(v) for key,v in by.items()},
 'annual_outside':{'|'.join(map(str,(source,year))):pack([r for r in ledger if r['source']==source and not r['is_frozen_member'] and r['year']==year])
   for source in ('original49','expanded15') for year in range(2019,2027)},
 'group_annual_outside':{'|'.join(map(str,(source,g,year))):pack([r for r in ledger if r['source']==source and not r['is_frozen_member'] and r['group']==g and r['year']==year])
    for source in ('original49','expanded15') for g in ('base','A','B','C','D','E','F','G') for year in range(2019,2027)},
 'old_PR67_1160_is_NOT_authoritatively_validated':True,
 'notes':['Full raw quote path per original 2016 M8 replay (as of 2026-11-16 naming), not only 3 sampled endpoints',
   'Existing membership kept frozen; exact group and pnl should match for source history if same historic vintage',
   'Original49 G uses prior saved score_rate data when present; expanded15 G uses previously derived pre-target rates',
   'Historical raw quote source-event, NOT verified actual pregame received odds',
   'All current T6-priced 48,890 distinct FIDs processed; missing original frozen 679 retained in baseline but absent here',
   'No production orders or rule changes']}
(P/'faithful_frozen_full_path_48890_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print('FAITHFUL_COMPLETED',json.dumps(dict(stats)),flush=True)
print('GROUPS',json.dumps(summary['group_source_membership']),flush=True)
