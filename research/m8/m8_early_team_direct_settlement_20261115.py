from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_independent_team_market_residual_20261115.py').read_text()
s=s[:s.index("out={'score_history_n'")]+s[s.index("out={'score_history_n'"):s.index(" for y in (2024,2025,2026):\n  tr=")]
# Above ends in the existing horizon loop, preserving score and residual calculations.
s+=r'''
 for y in (2024,2025,2026):
  tr=[r for r in z if r['year']<y];te=[r for r in z if r['year']==y];oo={'n':len(te)}
  for kind in ('market','market_score','market_score_residual'):
   X=np.array([feat(r,kind) for r in tr]);Xt=np.array([feat(r,kind) for r in te])
   mu=X.mean(0);sd=X.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1;X=(X-mu)/sd;Xt=(Xt-mu)/sd
   reg=np.eye(X.shape[1])*100;reg[0,0]=0
   rr={}
   for m,sa,sb in [('AH','home_U','away_U'),('OU','over_U','under_U')]:
    Y=np.stack([vec(tr,sa),vec(tr,sb)],axis=1)
    beta=np.linalg.solve(X.T@X+reg,X.T@Y);pred=Xt@beta
    v=np.where(pred[:,0]>=pred[:,1],vec(te,sa),vec(te,sb));rr[m]={'all':stat(v),'positive_estimate_diagnostic':stat(v[pred.max(1)>0])}
   oo[kind]=rr
  rec['years'][str(y)]=oo;print('DIRECT',T,y,json.dumps(oo),flush=True)
 out['horizons'][str(T)]=rec
(P/'m8_early_team_direct_settlement_20261115.json').write_text(json.dumps(out,indent=2))
'''
exec(compile(s,'direct_settlement','exec'))
