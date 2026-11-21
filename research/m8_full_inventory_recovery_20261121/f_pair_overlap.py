import gzip,json,collections
from pathlib import Path
P=Path(__file__).resolve().parent
F=P/'source67/research/m8_m9_group_independent_20261120/exact_rule_cross_league/group_f_market_mechanism_20261121/f_group_market_mechanism_rows.jsonl.gz'
PAIR=Path('/Users/mac/.codex/worktrees/m8-discipline-referee/quant-runner-m8-goalkeeper/research/m8/player_pair_expanded15_20261121/pooled_pair_cohesion_market_plus_pair_ledger.jsonl.gz')
def load(p):
 with gzip.open(p,'rt') as f:return {str(r['fid']):r for s in f if (r:=json.loads(s))}
f=load(F);p=load(PAIR);ids=sorted(set(f)&set(p))
a=[]
for fid in ids:
 x=f[fid];y=p[fid]
 if x['ft']!=[y['hg'],y['ag']]:raise AssertionError(fid)
 side=y['chosen_side'];ff=x['selected_side']
 a.append({'fid':fid,'year':x['year'],'league':x['league'],
           'F_side':ff,'pair_side':side,'F_T1_net_U':x['selected_net_U'],
           'pair_T12_net_U':y['net_u'],
           'pair_side_on_F_T1_net_U':x['home_net_U' if side=='home' else 'away_net_U'],
           'line_F_T1':x['T1']['line_home'],'line_pair_T12':y['line']})
result={'F_total':len(f),'pair_expanded15_total':len(p),'overlap':len(ids),
        'overlap_rows':a,
        'F_all_net_U':round(sum(x['selected_net_U'] for x in f.values()),3),
        'pair_all_net_U':round(sum(x['net_u'] for x in p.values()),3),
        'F_overlapping_T1_net_U':round(sum(x['F_T1_net_U'] for x in a),3),
        'pair_overlapping_T12_net_U':round(sum(x['pair_T12_net_U'] for x in a),3),
        'pair_on_F_T1_net_U':round(sum(x['pair_side_on_F_T1_net_U'] for x in a),3),
        'same_side':sum(x['F_side']==x['pair_side'] for x in a),
        'different_line':sum(x['line_F_T1']!=x['line_pair_T12'] for x in a)}
(P/'f_pair_overlap.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='overlap_rows'},ensure_ascii=False,indent=2))
