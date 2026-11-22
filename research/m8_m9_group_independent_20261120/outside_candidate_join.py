import gzip,json,collections,pathlib
root=pathlib.Path(__file__).parents[1];out=pathlib.Path(__file__).parent
m9={}
with gzip.open(root/'m8_m9_joint_20261120/m8_m9_unique_fid_union.jsonl.gz','rt') as f:
 for l in f:
  x=json.loads(l)
  if not x['m8_member'] and x['m9']:m9[x['fid']]=x['m9']
agg=collections.defaultdict(lambda:[0,0.,0.]); seen=collections.defaultdict(set);matches=[]
with gzip.open(root/'m8/frozen_eight_boundary_expansion_20261119/boundary_candidate_prediction_ledger_20261119.jsonl.gz','rt') as f:
 for l in f:
  x=json.loads(l);m=m9.get(x['fid'])
  if not m:continue
  key=(x['model'],x['similarity_quantile'],x['source_group'],'same' if x['direction']==m['m9_side'] else 'opposite')
  if x['fid'] in seen[key]:continue
  seen[key].add(x['fid']);v=agg[key];v[0]+=1;v[1]+=x['pnl'];v[2]+=m['m9_pnl']
  matches.append({'fid':x['fid'],'year':x['year'],'group':x['source_group'],'model':x['model'],'quantile':x['similarity_quantile'],'relation':key[-1],'candidate_pnl':x['pnl'],'m9_pnl':m['m9_pnl'],'candidate_direction':x['direction'],'m9_direction':m['m9_side'],'candidate_line':x['AH_line_home'],'m9_line':m['crown_line_home']})
rows=[{'model':k[0],'quantile':k[1],'group':k[2],'relation':k[3],'n':v[0],'candidate_net_u':round(v[1],3),'m9_net_u':round(v[2],3),'candidate_roi_pct':round(100*v[1]/v[0],3)} for k,v in sorted(agg.items())]
(out/'outside_candidate_join_summary.json').write_text(json.dumps(rows,indent=2)+'\n')
with gzip.open(out/'outside_candidate_join_matches.jsonl.gz','wt') as f:
 for x in matches:f.write(json.dumps(x)+'\n')
print('M9 outside',len(m9),'candidate matches',len(matches),'unique candidate FIDs',len({x['fid'] for x in matches}))
print('market_path_plus_team_history quantile .9 same:')
for x in rows:
 if x['model']=='market_path_plus_team_history' and x['quantile']==.9 and x['relation']=='same':print(x)
print('IMPORTANT candidate vs M9 contract exact line',sum(x['candidate_line']==x['m9_line'] for x in matches),'/',len(matches))
