import json,math,collections
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Load prior definitions without executing its historical fitting/report loop.
s=(P/'m8_cross_market_latent_pricing_20261114.py').read_text()
exec(s.split('# Comparative regressions:')[0])
S={r['fid']:r for r in map(json.loads,(P/'m8_independent_score_strength_20261114.jsonl').open())}
M=[r for r in R if not r['prior'] and r['fid'] in S]
assert len(M)==7632,len(M)
from math import lgamma
def end_share(total,fraction,line):
 return ah_share(total,fraction,line)
def expected(th,ta,line,priceh,pricea):
 h=pmf(th);a=pmf(ta).cumsum(axis=1)
 W=np.zeros(len(th));L=W.copy()
 for l in halves(line):
  W+=(h*cdf_at(a,np.ceil(goals+l[:,None])-1)).sum(axis=1)/2
  L+=(h*(1-cdf_at(a,np.floor(goals+l[:,None])))).sum(axis=1)/2
 return W*(priceh-1)-L,L*(pricea-1)-W
def stat(v):
 n=len(v);u=float(np.sum(v));return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
def part(r):return '2025' if r['year']==2025 else 'H1' if r['month']<='2026-06' else 'H2'
labels=np.array([part(r) for r in M]);L=np.array([r['end_line'] for r in M]);ph=np.array([r['home_price'] for r in M]);pa=np.array([r['away_price'] for r in M])
yh=np.array([r['end_home_U'] for r in M]);ya=np.array([r['end_away_U'] for r in M])
hg=np.array([S[r['fid']]['hg'] for r in M]);ag=np.array([S[r['fid']]['ag'] for r in M])
def vec(k):return np.array([r[k] for r in M])
def sv(k):return np.array([S[r['fid']][k] for r in M])
total=vec('latent_total_1');margin=vec('latent_margin_1');mh=(total+margin)/2;ma=(total-margin)/2
def scoring(h,a,mask):
 ll=h+a-hg*np.log(h)-ag*np.log(a)
 return {'mean_goal_MAE':round(float(np.mean((abs(h-hg)+abs(a-ag))[mask])/2),4),'poisson_NLL_without_factorial':round(float(np.mean(ll[mask])),4)}
out={'source':'Score-only online goal ratings using earlier UTC dates versus Crown T1 implied rates, on exact prior-cohort remainder. Blends and positive-estimate subsets are exploratory experiments, no production selection rules.','coverage':{'n':len(M),'history_both_teams_seen':sum(S[r['fid']]['history_home_n']>0 and S[r['fid']]['history_away_n']>0 for r in M)},'score_calibration':{},'blends':{},'model':{}}
for speed in ('0.025','0.06'):
 sh,sa=sv('lambda_home_'+speed),sv('lambda_away_'+speed)
 for weight in (0.,.25,.5,.75,1.):
  h=(1-weight)*mh+weight*sh;a=(1-weight)*ma+weight*sa
  eh,ea=expected(h,a,L,ph,pa);p=np.maximum(eh,ea);v=np.where(eh>=ea,yh,ya)
  name=speed+'|'+str(weight);out['blends'][name]={}
  for era in ('2025','H1','H2'):
   mask=labels==era
   out['blends'][name][era]={'all':stat(v[mask]),'positive_estimate':stat(v[mask&(p>1e-9)]),'scoring':scoring(h,a,mask)}
  print('BLEND',name,out['blends'][name],flush=True)
# Chronological supervised comparison with independent-rate improvement; same target sample as last turn.
def f(r,use_score):
 z=S[r['fid']]
 a0,a3,a1=[r['AH_p'+k] for k in ('0','3','1')];l0,l1=r['start_line'],r['end_line']
 u0,u3,u1=[r['OU_l'+k] for k in ('0','3','1')];o0,o3,o1=[r['OU_p'+k] for k in ('0','3','1')]
 v=[1,l0,l1,abs(l1),l1-l0,a0,a3,a1,a1-a0,a3-a0,a1-a3,(a1-a0)*l1,r['home_price'],r['away_price'],r['line_range'],math.log1p(r['n_line_changes']),math.log1p(r['n_events']),r['end_zero'],u0,u3,u1,u1-u0,u3-u0,u1-u3,o0,o3,o1,o1-o0,o3-o0,o1-o3,r['OU_over_odds'],r['OU_under_odds'],l1*u1,(l1-l0)*(u1-u0),(a1-a0)*(o1-o0),l1*(u1-u0),l1*(o1-o0)]
 if use_score:
  h,a=z['lambda_home_0.025'],z['lambda_away_0.025'];t=h+a;m=h-a
  mt,mm=r['latent_total_1'],r['latent_margin_1']
  v.extend([h,a,t,m,t-mt,m-mm,(m-mm)*l1,(m-mm)*(a1-a0),(t-mt)*(u1-u0),math.log1p(z['history_home_n']),math.log1p(z['history_away_n'])])
 return v
for label in ('H1','H2'):
 for add in (False,True):
  tr=[r for r in M if part(r)=='2025' or (label=='H2' and part(r)=='H1')];te=[r for r in M if part(r)==label]
  X=np.array([f(r,add) for r in tr]);Y=np.array([[r['end_home_U'],r['end_away_U']] for r in tr]);mu=X.mean(0);sd=X.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1;X=(X-mu)/sd;reg=np.eye(X.shape[1])*100;reg[0,0]=0
  coeff=np.linalg.solve(X.T@X+reg,X.T@Y);p=((np.array([f(r,add) for r in te])-mu)/sd)@coeff
  v=np.where(p[:,0]>=p[:,1],[r['end_home_U'] for r in te],[r['end_away_U'] for r in te])
  k=label+'|'+('market+team' if add else 'market')
  out['model'][k]={'all':stat(v),'positive_estimate':stat(v[p.max(1)>0])}
  print('MODEL',k,out['model'][k],flush=True)
(P/'m8_independent_score_market_comparison_20261114.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
