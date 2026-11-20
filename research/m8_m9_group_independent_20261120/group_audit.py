import gzip,json,collections,pathlib
src=pathlib.Path(__file__).parents[1]/'m8_m9_joint_20261120/m8_m9_unique_fid_union.jsonl.gz'
out=pathlib.Path(__file__).parent
stats=collections.defaultdict(lambda:{'n':0,'m8_u':0.,'m9_u':0.,'same':0,'opposite':0})
league_cohorts=collections.defaultdict(lambda:collections.Counter())
outside=collections.defaultdict(lambda:{'n':0,'m9_u':0.})
with gzip.open(src,'rt') as f:
 for line in f:
  x=json.loads(line);m=x.get('m9');co=x.get('m8_cohort');league=x.get('league_id');year=x['kickoff_utc'][:4]
  if x.get('m8_member'):
   league_cohorts[league][co]+=1
  if not m:continue
  if x.get('m8_member'):
   side='same' if x['m8_side']==m['m9_side'] else 'opposite'
   s=stats[(co,year,side)];s['n']+=1;s['m8_u']+=m['m8_pnl_repriced_same_Crown_contract'];s['m9_u']+=m['m9_pnl'];s[side]+=1
  else:
   s=outside[(league,year)];s['n']+=1;s['m9_u']+=m['m9_pnl']
rows=[{'group':c,'year':y,'relation':d,**{k:round(v,3) if isinstance(v,float) else v for k,v in s.items()}} for (c,y,d),s in sorted(stats.items())]
(out/'group_year_direction.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
agg=collections.defaultdict(lambda:[0,0.,0.]);
for x in rows:
 a=agg[(x['group'],x['relation'])];a[0]+=x['n'];a[1]+=x['m8_u'];a[2]+=x['m9_u']
print('group relation n M8_U M9_U')
for k,v in sorted(agg.items()):print(*k,v[0],round(v[1],3),round(v[2],3))
print('outside distinct league/year',len(outside),'M8 groups',len({x[0] for x in agg}))
print('outside total',sum(v['n'] for v in outside.values()),round(sum(v['m9_u'] for v in outside.values()),3))
print('CDE annual:')
for c in ['C','D','E','G']:
 for y in sorted({x['year'] for x in rows}):
  z=[x for x in rows if x['group']==c and x['year']==y];
  if z:print(c,y,sum(x['n'] for x in z),round(sum(x['m9_u'] for x in z),3),round(sum(x['m8_u'] for x in z),3))
(out/'league_group_overlap.json').write_text(json.dumps({k:dict(v) for k,v in league_cohorts.items()},indent=2)+'\n')
(out/'outside_m9_league_year.json').write_text(json.dumps([{'league_id':k[0],'year':k[1],**{a:round(b,3) if isinstance(b,float) else b for a,b in v.items()}} for k,v in sorted(outside.items())],indent=2)+'\n')
