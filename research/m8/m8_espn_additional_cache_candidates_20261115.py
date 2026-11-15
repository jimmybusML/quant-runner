import collections,datetime,hashlib,json,re,unicodedata
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
s=(R/'m8_early_exact_cross_market_consistency_20261115.py').read_text()
exec(s[:s.index('C=collections.Counter();rows=[]')])
target={r['fid']:r for r in map(json.loads,(R/'m8_early_joint_market_inventory_20261115.jsonl').open()) if r['T']==12 and r['year']==2026 and r['date']>='2026-08-01'}
previous={r['fid']:r for r in map(json.loads,(R/'m8_espn_cached_performance_verified_20261115.jsonl').open())}
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower())
idx=collections.defaultdict(list);scope={}
for fid,r in target.items():
 try:
  f,sha,lid=jobs[fid];b=f.read_bytes();assert not sha or hashlib.sha256(b).hexdigest()==sha
  x=next(v for v in json.loads(b)['data'] if str(v['id'])==fid)
  k=dt(x['start'])
  assert str(x['l_id'])==r['league']==str(lid) and str(x['h_id'])==r['home_id'] and str(x['a_id'])==r['away_id'] and (int(x['hg']),int(x['ag']))==(r['hg'],r['ag']) and x['status']=='full'
  q={'fid':fid,'league':r['league'],'date':r['date'],'year':r['year'],'ko':k.isoformat(),'home':r['home_id'],'away':r['away_id'],'hg':r['hg'],'ag':r['ag'],'hn':str(x['h']),'an':str(x['a'])}
  scope[fid]=q;idx[(q['ko'],q['hg'],q['ag'])].append(q)
 except Exception:continue
D=P/'data/epl_laliga_crown_5seasons';maps=json.load((D/'espn_identity_review.json').open())
# The two league-specific historical feeds can use previously confirmed seasonal team names;
# general all-soccer feeds require exact normalized names, no fuzzy or date/score-only fallback.
alias={}
for key,v in maps.items():
 l=key.split('|')[0]
 lid='1' if l=='England Premier League' else '14'
 for a,b in v.get('team_map',{}).items():alias.setdefault((lid,norm(a)),set()).add(norm(b))
files=[(D/'espn_source/eng_1_2026.json','1'),(D/'espn_source/esp_1_2026.json','14')]
for root in (R/'m7/m7_remaining_FT_exact_id_20261110/espn/raw-dates',R/'m7/m7_actual_receipt_1596_pending_FT_recheck_20261112/espn_raw_dates'):
 files.extend((p,None) for p in sorted(root.glob('*.json')))
C=collections.Counter();new={};bad=set();fields=('totalShots','shotsOnTarget','possessionPct','totalGoals')
def okname(a,b,l,known):return norm(a)==norm(b) or known and alias.get((l,norm(a)),set())=={norm(b)}
for f,lid in files:
 b=f.read_bytes();sha=hashlib.sha256(b).hexdigest()
 for e in json.loads(b).get('events',[]):
  C['event_rows']+=1
  try:
   c=e['competitions'][0]
   if c['status']['type']['name']!='STATUS_FULL_TIME':continue
   k=datetime.datetime.fromisoformat(e['date'].replace('Z','+00:00')).astimezone(datetime.timezone.utc).isoformat()
   t={x['homeAway']:x for x in c['competitors']};h,a=t['home'],t['away'];hg,ag=int(h['score']),int(a['score'])
   cand=[q for q in idx.get((k,hg,ag),[]) if (lid is None or q['league']==lid) and okname(h['team']['displayName'],q['hn'],q['league'],lid is not None) and okname(a['team']['displayName'],q['an'],q['league'],lid is not None)]
   if len(cand)!=1:continue
   q=cand[0];fid=q['fid']
   def parse(x,score):
    s={v['name']:float(v['displayValue']) for v in x['statistics'] if v['name'] in fields}
    assert s['totalGoals']==score and 0<=s['shotsOnTarget']<=s['totalShots'] and 0<=s['possessionPct']<=100
    return s
   x,y=parse(h,hg),parse(a,ag);assert abs(x['possessionPct']+y['possessionPct']-100)<.2
   r={a:q[a] for a in ('fid','league','date','year','ko','home','away','hg','ag')};r.update(hshots=x['totalShots'],ashots=y['totalShots'],hsot=x['shotsOnTarget'],asot=y['shotsOnTarget'],hposs=x['possessionPct'],aposs=y['possessionPct'],espn_id=str(e['id']))
   if fid in previous:continue
   if fid in new and new[fid]['record']!=r:bad.add(fid);continue
   new[fid]={'record':r,'source':str(f),'sha256':sha,'league_explicit':lid is not None}
  except (KeyError,ValueError,AssertionError,TypeError,IndexError):C['invalid_candidate']+=1
for fid in bad:new.pop(fid,None)
out={'target_recent':len(target),'raw_verified':len(scope),'new_n':len(new),'new_leagues':dict(collections.Counter(v['record']['league'] for v in new.values())),'source_explicit_league':sum(x['league_explicit'] for x in new.values()),'conflicting_ids':len(bad),'counts':dict(C),'notes':'general multi-league scoreboard lacks per-event league field; candidate requires unique exact UTC time, score and both normalized names, but league not independently verified. Retain separately as candidate; not merged into confirmed model.'}
(R/'m8_espn_additional_cache_candidates_20261115.json').write_text(json.dumps(out,indent=2))
(R/'m8_espn_additional_cache_candidates_20261115.jsonl').write_text(''.join(json.dumps(v)+'\n' for v in new.values()))
print('CACHE',json.dumps(out),flush=True)
