from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
exec((P/'m8_score_market_divergence_full_AH_20261114.py').read_text().split('out={}\n')[0])
Z=G[('shape_relation','reverted','agree')]
ids={(r['year'],r['fid']) for r in Z}
assert len(ids)==len(Z) and not ids&set(prior)
z=[{**r,'pnl':r['contra_U']} for r in Z]
oldrows=[{**r,'pnl':prior[(r['year'],r['fid'])][1]} for r in A if (r['year'],r['fid']) in prior]
def result(rs):
 d={p:st([r for r in rs if era(r)==p],'pnl') for p in ('2019-23','2024-25','2026')}
 d['annual']={str(y):st([r for r in rs if r['year']==y],'pnl') for y in range(2019,2027)}
 d['2026_H1']=st([r for r in rs if r['year']==2026 and r['month']<='2026-06'],'pnl');d['2026_H2']=st([r for r in rs if r['year']==2026 and r['month']>='2026-07'],'pnl')
 q=[r for r in rs if r['year']==2026];weeks=collections.Counter()
 for r in q:
  w=datetime.date.fromisoformat(r['date']).isocalendar();weeks[(w.year,w.week)]+=1
 d['weeks']={'mean44':round(len(q)/44,2),'max':max(weeks.values())}
 d['monthly']={m:st([r for r in q if r['month']==m],'pnl') for m in sorted({r['month'] for r in q})}
 day=collections.defaultdict(lambda:[0.,0.])
 for r in q:day[r['date']][0]+=r['pnl'];day[r['date']][1]+=1
 a=np.array(list(day.values()));rng=np.random.default_rng(261114);v=[]
 for i in range(4000):
  sample=a[rng.integers(len(a),size=len(a))].sum(0);v.append(sample[0]*100/sample[1])
 d['2026_day_bootstrap95_descriptive']=[round(float(v),3) for v in np.percentile(v,[2.5,97.5])]
 return d
out={'G':result(z),'G_nonzero':result([r for r in z if not r['end_zero']]),'G_zero':result([r for r in z if r['end_zero']]),'old7':result(oldrows),'old7+G':result(oldrows+z),'old_without_B+G':result([r for r in oldrows if r['prior_group']!='B']+z)}
out['G_2026_by_league']={l:st([r for r in z if r['year']==2026 and r['league']==l],'pnl') for l in sorted({r['league'] for r in z if r['year']==2026})}
for tag,v in out.items():
 if tag!='G_2026_by_league':print('CANDIDATE',tag,{p:v[p] for p in ('2019-23','2024-25','2026','2026_H1','2026_H2','weeks','2026_day_bootstrap95_descriptive')},'annual',v['annual'],flush=True)
(P/'m8_score_market_reversion_G_combo_20261114.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
