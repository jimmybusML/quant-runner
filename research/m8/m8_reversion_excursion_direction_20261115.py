import json,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
exec((P/'m8_score_market_divergence_full_AH_20261114.py').read_text().split('out={}\n')[0])
gids={(r['year'],r['fid']) for r in G[('shape_relation','reverted','agree')]}
remain=[r for r in G[('remaining_all',)] if r['path_shape']=='reverted' and (r['year'],r['fid']) not in gids]
groups=collections.defaultdict(list)
for r in remain:
 if r['end_zero']:continue
 # Relative to final favorite (same start/end line), the intermediate excursion can face either way.
 ma=r['fav_end_vs_max'];mi=r['fav_end_vs_min']
 typ='fav_strengthened_only' if ma<0 and mi==0 else 'fav_weakened_only' if mi>0 and ma==0 else 'both_directions'
 market=direction(r['away_price']/(r['home_price']+r['away_price'])-r['start_away_price']/(r['start_home_price']+r['start_away_price']))
 fav='home' if r['end_line']<0 else 'away'
 rel='flat' if market=='flat' else 'fav' if market==fav else 'dog'
 groups[('excursion',typ)].append(r)
 groups[('excursion_market',typ,rel)].append(r)
 groups[('excursion_model',typ,r['relation'])].append(r)
out={}
for k,z in sorted(groups.items()):
 v={f:summary(z,f) for f in ('end_fav_U','end_dog_U','ind_U','contra_U')}
 out['|'.join(k)]=v
 if k[0]=='excursion' or any(all(x[p]['ROI'] is not None and x[p]['ROI']>0 for p in ('2019-23','2024-25','2026')) for x in v.values()):
  print('EXCURSION',k,{f:{p:x[p] for p in ('2019-23','2024-25','2026','2026_H1','2026_H2')} for f,x in v.items()},flush=True)
# Broad null-price change group, without subdividing by minutes.
flat=[r for r in remain if r['relation']=='flat']
out['all_flat']={f:summary(flat,f) for f in ('ind_U','contra_U')}
print('FLAT',out['all_flat'],flush=True)
(P/'m8_reversion_excursion_direction_20261115.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
