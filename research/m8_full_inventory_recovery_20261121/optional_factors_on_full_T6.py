"""Same Crown T6 contract for all three directional signals; pure retrospective diagnostic, no filter deployment."""
import gzip,json,collections
from pathlib import Path
P=Path(__file__).resolve().parent
BASE=P/'full_T6_model_comparison_ledger.jsonl.gz'
ROOT=Path('/Users/mac/.codex/worktrees/m8-discipline-referee/quant-runner-m8-goalkeeper/research/m8')
PAIR=ROOT/'player_pair_cohesion_20261121/pair_cohesion_per_fixture_20261121.jsonl.gz'
FORM=ROOT/'prior_formation_market_20261121/formation_market_per_fixture_20261121.jsonl.gz'
def load(p,method):
 with gzip.open(p,'rt') as f:return {r['fid']:r for s in f if (r:=json.loads(s))['method']==method and not r['frozen_overlap']}
pair=load(PAIR,'market_plus_pair');form=load(FORM,'market_plus_formation')
with gzip.open(BASE,'rt') as f:
 base={r['fid']:r for s in f if (r:=json.loads(s))['model']=='jack10_binary' and r['window']=='fixed_2019_23' and not r['is_m8_member']}
assert len(base)==22120
groups=collections.defaultdict(lambda:collections.defaultdict(lambda:{'n':0,'u':0.}))
detail=[]
for fid,r in base.items():
 sources={'jack10':r['side']}
 if fid in pair:sources['pair']=pair[fid]['chosen_side']
 if fid in form:sources['formation']=form[fid]['chosen_side']
 if len(sources)<2:continue
 year=r['year']
 for name,side in sources.items():
  pnl=float(r['home_U'] if side=='home' else r['away_U'])
  for key in ('all',str(year)):
   z=groups[('source',name,key)]['all'];z['n']+=1;z['u']+=pnl
 if 'pair' in sources and 'formation' in sources:
  agree=sources['pair']==sources['formation']
  samejack=sources['jack10']==sources['pair'] if agree else False
  case='pair_form_agree' if agree else 'pair_form_disagree'
  for name in sources:
   val=float(r['home_U'] if sources[name]=='home' else r['away_U'])
   for key in ('all',str(year)):
    z=groups[(case,name,key)]['all'];z['n']+=1;z['u']+=val
  detail.append({'fid':fid,'year':year,'jack_side':sources['jack10'],'pair_side':sources['pair'],'formation_side':sources['formation'],
    'pair_formation_agree':agree,'all_three_agree':agree and samejack,
    'T6_home_u':r['home_U'],'T6_away_u':r['away_U']})
result={'base_outside_T6':len(base),'available_pair':len(set(base)&set(pair)),
   'available_formation':len(set(base)&set(form)),
   'available_both':len(detail),
   'not_both':len(base)-len(detail),
   'T6_source_event_only':True,
   'groups':{'|'.join(k):{'n':v['all']['n'],'net_U':round(v['all']['u'],3),
         'ROI_pct':round(v['all']['u']/v['all']['n']*100,3)} for k,v in groups.items()}}
(P/'optional_factors_on_full_T6_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
with gzip.open(P/'optional_factors_on_full_T6_overlap.jsonl.gz','wt') as f:
 for r in detail:f.write(json.dumps(r,ensure_ascii=False)+'\n')
print(json.dumps({'coverage':{k:v for k,v in result.items() if k!='groups'},'selected_groups':{k:v for k,v in result['groups'].items() if k[0:19]=='pair_form_agree' or k[0:22]=='pair_form_disagree'}},ensure_ascii=False,indent=2))
