#!/usr/bin/env python3
"""Time-forward M8 AH study of historical formation profiles and matchups.

Only prior completed Transfermarkt games are used to describe a team's style.
The target match's formation, lineup, FT and future eight-group status are never
features. Crown T1 historical event prices are used only for retrospective AH
settlement. This is not proof of live feature availability.
"""
from __future__ import annotations
import bisect, collections, csv, datetime as dt, difflib, gzip, hashlib, json, math, pathlib, re, sqlite3, unicodedata
import numpy as np
from scipy.special import ndtr

ROOT = pathlib.Path(__file__).resolve().parents[3]
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
OUT = ROOT / 'research/m8/formation_matchup_20261120'
OUT.mkdir(parents=True, exist_ok=True)
TM_PATH = WORK / 'm8_pregame_info_source_20261117/games.csv.gz'
PATHS = WORK / 'm8_late_full_path_water_features_20261114.jsonl'
SCORES = WORK / 'm8_independent_score_strength_20261114.jsonl'
FROZEN = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
SCHEDULE = WORK / 'crown-drop-expanded-62/schedule_universe.jsonl'
DB = pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
RECEIPTS = ROOT / 'research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl'
TZ = dt.timezone(dt.timedelta(hours=8)); UTC = dt.timezone.utc
ALPHA = 100.0
GROUPS = ('base','A','B','C','D','E','F','G')
# Explicit TotalCorner provider -> Transfermarkt competition bridge previously
# audited in the M8 venue study. Unsupported competitions are counted, not guessed.
COMP = {'1':'GB1','12':'IT1','14':'ES1','16':'L1','25':'FR1','29':'A1','31':'BE1','35':'TS1','37':'NL1','48':'PL1','51':'PO1','52':'RO1','61':'C1','62':'TR1','66':'SE1','70':'DK1','73':'JAP1','75':'RSK1','88':'NO1','141':'GR1','262':'SC1','290':'SA1','303':'SER1','319':'UKR1','26540':'KR1',
        # Four additional expanded-scope competitions have explicit exact TM IDs.
        '129':'BRA1','19290':'ARG1','779':'MEX1','85':'MLS1'}

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def readj(p):
    with open(p,encoding='utf8') as f:
        for s in f:
            if s.strip(): yield json.loads(s)
def norm(s):
    x=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    x=re.sub(r'\b(fc|cf|sc|afc|ac|club|football|soccer|fk|as)\b',' ',x)
    return re.sub(r'[^a-z0-9]','',x)
def sim(a,b):
    a,b=norm(a),norm(b)
    if not a or not b:return 0.
    if a==b:return 1.
    if min(len(a),len(b))>=6 and (a in b or b in a):return .91
    return difflib.SequenceMatcher(None,a,b).ratio()
def parse_form(s):
    s=str(s or '').strip()
    m=re.match(r'^(\d+)\s*[-–]',s)
    if not m:return None,None
    defenders=int(m.group(1)); band='3' if defenders==3 else '4' if defenders==4 else '5plus' if defenders>=5 else 'other'
    key=re.sub(r'\s+',' ',s.lower())
    return band,key
def parse_date(s): return dt.date.fromisoformat(str(s)[:10])
def settle(line,side,hg,ag,odds):
    # Split quarter AH contracts into equal half-stakes, then apply each leg.
    if abs(float(line)*4-round(float(line)*4))>1e-8: raise ValueError(f'bad AH line {line}')
    x=float(line) if side=='home' else -float(line)
    gd=int(hg)-int(ag) if side=='home' else int(ag)-int(hg)
    legs=[x] if abs(x*2-round(x*2))<1e-8 else [math.floor(x*2)/2,math.ceil(x*2)/2]
    returns=[]
    for leg in legs:
        margin=gd+leg
        returns.append(float(odds)-1 if margin>1e-9 else -1. if margin< -1e-9 else 0.)
    labels=['W' if z>0 else 'L' if z<0 else 'P' for z in returns]
    label={'WW':'full_win','W':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss','L':'full_loss','P':'push'}[''.join(labels)]
    return sum(returns)/len(returns),label
def dist(mean,sigma):
    vals=list(range(-20,21)); ps=[]
    for g in vals: ps.append(float(ndtr((g+.5-mean)/sigma)-ndtr((g-.5-mean)/sigma)))
    ps[0]=float(ndtr((-19.5-mean)/sigma)); ps[-1]=float(1-ndtr((19.5-mean)/sigma))
    z=sum(ps); return vals,[max(0,p/z) for p in ps]
def ev(line,odds,side,vals,ps):
    total=0.
    for g,p in zip(vals,ps): total+=p*settle(line,side,g,0,odds)[0] if False else p*settle(line,side,g,0,odds)[0]
    return total
def ev_margin(line,odds,side,vals,ps):
    # settle() accepts home/away score; represent a signed margin as (g,0).
    return sum(p*settle(line,side,g,0,odds)[0] for g,p in zip(vals,ps))
def fit_ridge(X,y):
    mu=X.mean(0); sd=X.std(0); sd[sd<1e-10]=1.
    Z=(X-mu)/sd; ym=float(y.mean())
    beta=np.linalg.solve(Z.T@Z+ALPHA*np.eye(Z.shape[1]),Z.T@(y-ym))
    pred=Z@beta+ym; sigma=max(.65,float(np.sqrt(np.mean((y-pred)**2))))
    return (mu,sd,ym,beta,sigma)
def predict(model,x):
    mu,sd,ym,beta,sigma=model
    return float(((x-mu)/sd)@beta+ym),sigma
def vector(r,formation=False):
    line=float(r['line']); ho=float(r['home_odds']); ao=float(r['away_odds'])
    ih=1/ho; ia=1/ao; share=ih/max(ih+ia,1e-12)
    v=[-line,abs(line),math.log(max(ao,1e-6)/max(ho,1e-6)),share]
    if formation: v += [r[k] for k in FORM_FEATURES]
    return np.asarray(v,float)
FORM_FEATURES=['h3','h5','a3','a5','h_entropy','a_entropy','h_n_log','a_n_log',
               'h3_a4','h3_a5','h4_a3','h5_a3','h4_a4','style_gap3']
def feature_for_team(team,comp,cutoff,hist):
    arr=hist.get((team,comp),[]); dates=[x[0] for x in arr]
    hi=bisect.bisect_left(dates,cutoff); lo=bisect.bisect_left(dates,cutoff-dt.timedelta(days=365))
    obs=arr[max(lo,hi-10):hi]
    counts=collections.Counter(x[1] for x in obs); n=len(obs)
    shares={k:(counts[k]+1)/(n+4) for k in ('3','4','5plus','other')}
    exact=collections.Counter(x[2] for x in obs)
    entropy=0.
    if len(obs)>1:
        ps=[v/n for v in exact.values()]; entropy=-sum(p*math.log(p) for p in ps)/math.log(max(len(ps),2))
    return {'share3':shares['3'],'share4':shares['4'],'share5':shares['5plus'],'entropy':entropy,'n':n}
def mdd(rows):
    by=collections.defaultdict(float)
    for r in rows:by[r['date']]+=r['net_u']
    c=p=dd=0.
    for _,u in sorted(by.items()):c+=u;p=max(p,c);dd=max(dd,p-c)
    return round(dd,6)
def stat(rows,calendar_weeks=None):
    rows=list(rows); candidate_fids=len({r['fid'] for r in rows})
    rows=[r for r in rows if r.get('settlement')!='no_bet']
    n=len(rows); u=sum(r['net_u'] for r in rows)
    if calendar_weeks is None:
        if rows: calendar_weeks=(parse_date(max(r['date'] for r in rows))-parse_date(min(r['date'] for r in rows))).days//7+1
        else: calendar_weeks=0
    return {'n':n,'candidate_unique_fids':candidate_fids,'no_bet_fids':candidate_fids-n,
            'net_U':round(u,6),'ROI_pct':round(100*u/n,6) if n else None,'max_drawdown_U':mdd(rows),
            'calendar_weeks':calendar_weeks,'avg_orders_per_calendar_week':round(n/calendar_weeks,6) if calendar_weeks else 0.,
            'active_weeks':len({r['iso_week'] for r in rows}),
            'weekly':{k:{'n':len(v),'net_U':round(sum(z['net_u'] for z in v),6)} for k,v in sorted(groupby_week(rows).items())}}
def groupby_week(rows):
    d=collections.defaultdict(list)
    for r in rows:d[r['iso_week']].append(r)
    return d

def main():
    for p in (TM_PATH,PATHS,SCORES,FROZEN,SCHEDULE,DB): assert p.exists(),p
    # Target inventory and frozen membership. Membership is applied only after prediction.
    path={str(x['fid']):x for x in readj(PATHS)}; original_path_n=len(path)
    scores={str(x['fid']):x for x in readj(SCORES)}
    sched={str(x['match_id']):x for x in readj(SCHEDULE)}
    frozen={str(x['fid']) for x in readj(FROZEN)}
    assert len(frozen)==10294
    # Extend the 49-league prebuilt path inventory with exact-mapped expanded
    # Brazil/Argentina/Mexico/MLS fixtures using only saved historical Crown
    # movement rows. No API access and no quote later than kickoff - 1 hour.
    extra_leagues={'129','19290','779','85'}
    extra_fids=[fid for fid,x in sched.items() if x['league_id'] in extra_leagues and fid not in path]
    extra_status=collections.Counter(); rawq=sqlite3.connect(f'file:{DB}?mode=ro',uri=True)
    q_by_fid=collections.defaultdict(list)
    sql="""SELECT q.fixture_id,q.handicap_home,q.home_decimal,q.away_decimal,q.quote_source_at_utc,
                     c.kickoff_at_utc,c.response_sha256,c.capture_mode,c.data_layer
              FROM asian_quote q JOIN capture c USING(capture_key)
              WHERE q.fixture_id IN ({}) AND q.quote_kind='movement'"""
    for start in range(0,len(extra_fids),400):
        batch=extra_fids[start:start+400]
        for z in rawq.execute(sql.format(','.join('?' for _ in batch)),batch):q_by_fid[str(z[0])].append(z)
    for fid in extra_fids:
        sc=sched[fid]; options=[]
        try:
            ko=dt.datetime.fromisoformat(str(sc['kickoff_source_local']).replace(' ','T')).replace(tzinfo=TZ).astimezone(UTC)
            cutoff=ko-dt.timedelta(hours=1)
        except Exception:extra_status['bad_kickoff']+=1;continue
        for z in q_by_fid.get(fid,[]):
            try:
                qt=dt.datetime.fromisoformat(str(z[4]).replace('Z','+00:00')).astimezone(UTC)
                capture_ko=dt.datetime.fromisoformat(str(z[5]).replace('Z','+00:00')).astimezone(UTC)
                if z[7]!='historical' or z[8]!='movement' or qt>cutoff or float(z[2])<=1 or float(z[3])<=1:continue
                # Use the raw capture's kickoff for price cutoff; schedule time is
                # retained for an explicit mismatch audit rather than substituted.
                cap_cut=capture_ko-dt.timedelta(hours=1)
                if qt>cap_cut:continue
                options.append((qt,z))
            except Exception:continue
        if not options:extra_status['no_valid_T1_Crown_quote']+=1;continue
        latest=max(qt for qt,z in options); latest_rows=[z for qt,z in options if qt==latest]
        distinct={(round(float(z[1]),8),round(float(z[2]),8),round(float(z[3]),8)) for z in latest_rows}
        if len(distinct)!=1:extra_status['conflicting_same_event_quote']+=1;continue
        z=latest_rows[0]
        path[fid]={'fid':fid,'end_line':float(z[1]),'home_price':float(z[2]),'away_price':float(z[3]),
                   'source':'Crown SQLite historical movement event','T1_source_event_utc':str(z[4]),
                   'response_sha256':str(z[6]),'capture_kickoff_utc':str(z[5]),
                   'schedule_kickoff_source_local':str(sc['kickoff_source_local'])}
        scores[fid]={'fid':fid,'league':str(sc['league_id']),'ko':dt.datetime.fromisoformat(str(z[5]).replace('Z','+00:00')).astimezone(UTC).isoformat(),
                     'home':str(sc['home']),'away':str(sc['away']),'hg':int(sc['home_goals']),'ag':int(sc['away_goals'])}
        extra_status['valid_T1_Crown_quote']+=1
    rawq.close()
    tm=[]; bycompday=collections.defaultdict(list); history=collections.defaultdict(list); form_counts=collections.Counter()
    with gzip.open(TM_PATH,'rt',encoding='utf8') as f:
        for r in csv.DictReader(f):
            try:
                d=parse_date(r['date']); comp=str(r.get('competition_id') or '')
                hb,hk=parse_form(r.get('home_club_formation')); ab,ak=parse_form(r.get('away_club_formation'))
                z={'id':str(r.get('game_id') or ''),'comp':comp,'date':d,'home':r['home_club_name'],'away':r['away_club_name'],
                   'hid':str(r.get('home_club_id') or ''),'aid':str(r.get('away_club_id') or ''),
                   'hg':int(r['home_club_goals']),'ag':int(r['away_club_goals']),
                   'hband':hb,'hform':hk,'aband':ab,'aform':ak}
                tm.append(z); bycompday[(comp,d)].append(z)
                if hb: history[(z['hid'],comp)].append((d,hb,hk))
                if ab: history[(z['aid'],comp)].append((d,ab,ak))
                form_counts['both' if hb and ab else 'one' if hb or ab else 'neither']+=1
            except (ValueError,TypeError,KeyError): continue
    for k in history:history[k].sort(key=lambda x:x[0])
    # Match target fixtures on prior approved comp/date/team identity only; use FT
    # strictly as a post-match validation after candidate selection.
    mapped=[]; status=collections.Counter(); issues=[]
    for fid,p in path.items():
        s=scores.get(fid); sc=sched.get(fid)
        if not s or not sc: status['missing_score_or_schedule']=status.get('missing_score_or_schedule',0)+1; continue
        lid=str(s.get('league') or sc.get('league_id') or '')
        comp=COMP.get(lid)
        if not comp: status['unsupported_competition']=status.get('unsupported_competition',0)+1; continue
        try:
            ko=dt.datetime.fromisoformat(str(s['ko']).replace('Z','+00:00'))
            if ko.tzinfo is None:ko=ko.replace(tzinfo=UTC)
            ko=ko.astimezone(UTC); day=ko.astimezone(TZ).date()
            hg,ag=int(s['hg']),int(s['ag'])
        except Exception:status['bad_score_time']=status.get('bad_score_time',0)+1;continue
        opts=[]
        for delta in (-1,0,1):
            for t in bycompday.get((comp,day+dt.timedelta(days=delta)),[]):
                sh=sim(sc['home'],t['home']); sa=sim(sc['away'],t['away'])
                if min(sh,sa)>=.85:opts.append((min(sh,sa),sh,sa,t))
        opts.sort(key=lambda x:(-x[0],x[3]['id']))
        if not opts:status['no_team_date_match']+=1;continue
        if len(opts)>1 and opts[0][0]-opts[1][0]<=.05:status['ambiguous_team_date']+=1;continue
        t=opts[0][3]
        if (t['hg'],t['ag'])!=(hg,ag):status['postmatch_ft_mismatch']+=1;continue
        if int(sc['home_goals'])!=hg or int(sc['away_goals'])!=ag:status['schedule_ft_mismatch']+=1;continue
        # The target's own TM formation is deliberately ignored.
        status['mapped_identity_ft_verified']+=1
        mapped.append({'fid':fid,'league_id':lid,'league':str(sc['source_league']),'comp':comp,'date':day.isoformat(),
           'year':day.year,'iso_week':f"{day.isocalendar().year}-W{day.isocalendar().week:02d}",
           'home':sc['home'],'away':sc['away'],'home_tm_id':t['hid'],'away_tm_id':t['aid'],
           'hg':hg,'ag':ag,'gd':hg-ag,'line':float(p['end_line']),'home_odds':float(p['home_price']),'away_odds':float(p['away_price']),
           'frozen_member':fid in frozen,'target_tm_game_id':t['id'],'target_tm_formation_ignored':True,
           'kickoff_utc':ko.isoformat(),'cutoff_beijing_date':(day-dt.timedelta(days=3)).isoformat(),
           'identity_similarity_home':round(opts[0][1],4),'identity_similarity_away':round(opts[0][2],4),
           'Crown_price_source':str(p.get('source','existing M8 T1 full-path event')),
           'T1_source_event_utc':p.get('T1_source_event_utc'),'Crown_response_sha256':p.get('response_sha256'),
           'schedule_kickoff_source_local':sc.get('kickoff_source_local')})
    mapped.sort(key=lambda r:(r['date'],r['fid']))
    # Snapshot features strictly before Beijing date - 3 days, using prior
    # 365d and at most ten most recent completed appearances per team.
    for r in mapped:
        cut=parse_date(r['cutoff_beijing_date'])
        h=feature_for_team(r['home_tm_id'],r['comp'],cut,history)
        a=feature_for_team(r['away_tm_id'],r['comp'],cut,history)
        h4=max(0.,1-h['share3']-h['share5']);a4=max(0.,1-a['share3']-a['share5'])
        r.update({'h3':h['share3'],'h5':h['share5'],'a3':a['share3'],'a5':a['share5'],
          'h_entropy':h['entropy'],'a_entropy':a['entropy'],'h_n_log':math.log1p(h['n']),'a_n_log':math.log1p(a['n']),
          'h3_a4':h['share3']*a4,'h3_a5':h['share3']*a['share5'],'h4_a3':h4*a['share3'],
          'h5_a3':h['share5']*a['share3'],'h4_a4':h4*a4,'style_gap3':h['share3']-a['share3'],
          'home_prior_games_365d':h['n'],'away_prior_games_365d':a['n']})
    # Chronological yearly holdout; same rows for market and formation models.
    scored=[]; candidates=[]; folds={}
    target_years=(2024,2025,2026)
    for year in target_years:
        train=[r for r in mapped if r['year']<year and r['year']>=2019]
        test=[r for r in mapped if r['year']==year]
        if not train or not test:folds[str(year)]={'train_n':len(train),'test_n':len(test),'status':'not_estimable'};continue
        y=np.asarray([r['gd'] for r in train],float)
        models={}
        for name,form in [('market',False),('market_plus_formation',True)]:
            X=np.vstack([vector(r,form) for r in train]); models[name]=fit_ridge(X,y)
        folds[str(year)]={'train_n':len(train),'test_n':len(test),'train_years':[min(r['year'] for r in train),max(r['year'] for r in train)],'alpha':ALPHA}
        for r in test:
            out={k:r[k] for k in r}
            for name,form in [('market',False),('market_plus_formation',True)]:
                mean,sigma=predict(models[name],vector(r,form)); vals,ps=dist(mean,sigma)
                hev=ev_margin(r['line'],r['home_odds'],'home',vals,ps)
                aev=ev_margin(r['line'],r['away_odds'],'away',vals,ps)
                side='home' if hev>=aev else 'away'; chosen_ev=max(hev,aev)
                odds=r['home_odds'] if side=='home' else r['away_odds']
                pnl,label=settle(r['line'],side,r['hg'],r['ag'],odds)
                out[f'{name}_predicted_home_margin']=round(mean,6)
                out[f'{name}_sigma']=round(sigma,6)
                out[f'{name}_home_EV_U']=round(hev,6);out[f'{name}_away_EV_U']=round(aev,6)
                out[f'{name}_chosen_side']=side;out[f'{name}_chosen_EV_U']=round(chosen_ev,6)
                out[f'{name}_pnl_always_U']=round(pnl,6);out[f'{name}_settlement_always']=label
                out[f'{name}_pnl_ev_positive_U']=round(pnl if chosen_ev>0 else 0.,6)
                out[f'{name}_bet_ev_positive']=bool(chosen_ev>0)
            scored.append(out)
            if not r['frozen_member']:
                for name in ('market','market_plus_formation'):
                    base={**out,'method':name,'action':'bet_best_side'}
                    base.update({'side':out[f'{name}_chosen_side'],'net_u':out[f'{name}_pnl_always_U'],'settlement':out[f'{name}_settlement_always']})
                    candidates.append(base)
                    abst={**out,'method':name+'_ev_positive','action':'bet_if_predicted_EV_positive'}
                    abst.update({'side':out[f'{name}_chosen_side'],'net_u':out[f'{name}_pnl_ev_positive_U'],'settlement':out[f'{name}_settlement_always'] if out[f'{name}_bet_ev_positive'] else 'no_bet'})
                    candidates.append(abst)
    # Portfolio summaries share one test inventory calendar denominator.
    target_dates=[parse_date(r['date']) for r in mapped if r['year'] in target_years]
    test_weeks=(max(target_dates)-min(target_dates)).days//7+1 if target_dates else 0
    methods={}
    for m in ('market','market_plus_formation','market_ev_positive','market_plus_formation_ev_positive'):
        rr=[x for x in candidates if x['method']==m]
        methods[m]={'overall':stat(rr,test_weeks),'per_year':{},'per_league':{}}
        for y in target_years:
            subset=[x for x in rr if x['year']==y]
            ds=[parse_date(z['date']) for z in mapped if z['year']==y]
            yw=(max(ds)-min(ds)).days//7+1 if ds else 0
            methods[m]['per_year'][str(y)]=stat(subset,yw)
        for league in sorted({x['league'] for x in rr}):
            methods[m]['per_league'][league]=stat([x for x in rr if x['league']==league])
    # Frozen portfolio and all augmented portfolios: zero FID overlap by design.
    frows=[]
    for x in readj(FROZEN):
        d=x.get('date') or x.get('kickoff_beijing') or ''
        if not d: continue
        d=str(d)[:10]; year=int(d[:4])
        if year not in target_years:continue
        frows.append({'fid':str(x['fid']),'date':d,'year':year,'iso_week':f"{parse_date(d).isocalendar().year}-W{parse_date(d).isocalendar().week:02d}",'net_u':float(x['pnl'])})
    frozen_ids={x['fid'] for x in frows}; candidate_fids={x['fid'] for x in candidates if x['action']=='bet_best_side'}
    assert not frozen_ids.intersection(candidate_fids)
    frozen_stat=stat(frows)
    merged={}
    for m in methods:
        orders=[x for x in candidates if x['method']==m]
        union={x['fid']:x for x in frows}
        for x in orders:
            if x['action']=='bet_best_side' or x['settlement']!='no_bet':union[x['fid']]=x
        merged[m]=stat(union.values())
    # Saved receipts only permit market/FID overlap audit; historical bulk formation
    # records lack original availability timestamps, so no prospective claim.
    receipt_ids=set()
    if RECEIPTS.exists():
        for x in readj(RECEIPTS):
            fid=x.get('fid') or x.get('fixture_id')
            if fid is not None:receipt_ids.add(str(fid))
    receipt_target={r['fid'] for r in mapped if r['year'] in target_years and r['fid'] in receipt_ids}
    receipt_model_rows=[r for r in scored if r['fid'] in receipt_target]
    result={'study':'M8_CROWN_AH_HISTORICAL_FORMATION_MATCHUP','created_utc':dt.datetime.now(UTC).isoformat(),
      'scope':{'Crown_path_rows_original_inventory':original_path_n,
        'Crown_T1_quotes_extended15_exact_mapped':dict(extra_status),'Crown_path_and_T1_rows_combined':len(path),'score_rows_plus_schedule_FT':len(scores),'schedule_unique_fids':len(sched),'TM_game_rows':len(tm),'mapped_targets':len(mapped),
        'mapped_by_year':dict(collections.Counter(str(r['year']) for r in mapped)),'mapped_by_league':dict(collections.Counter(r['league'] for r in mapped)),
        'target_formation_completeness':dict(form_counts),'test_rows_2024_2026':len(scored),'test_rows_outside_frozen':sum(not r['frozen_member'] for r in scored),
        'frozen_overlap_test_rows':sum(r['frozen_member'] for r in scored),'receipt_FID_overlap':len(receipt_target),'receipt_rows_with_retrospective_model_score':len(receipt_model_rows),
        'receipt_features_proven_available_at_receipt':0,'history_cutoff':'target Beijing date minus 3 days, strict prior 365 days, last 10 dated completed matches with a parsed formation'},
      'coverage_status':dict(status),'folds':folds,'features':{'market':['-Crown home handicap line','absolute handicap line','log away/home decimal odds','normalized home implied share'],
        'formation':FORM_FEATURES,'formation_history':'prior same Transfermarkt competition, target team ID, strict cutoff, prior 365d, at most 10 most recent games; Laplace smoothing (one pseudo-count in 4 categories); exact formation entropy is descriptive model input'},
      'methodology':{'target':'home goals minus away goals','training':'expanding-year: 2024 trains 2019-2023; 2025 trains 2019-2024; 2026 trains 2019-2025','model':'standardized Ridge, fixed alpha=100, same target rows and Crown AH prices for market-only and market-plus-formation','AH':'Crown historical T1 source-event line and both decimal prices; quarter-lines split into equal legs; 1U unit; no external bookmaker prices','policies':'always choose the higher model EV side; separate research-only abstention variant bets only when the model EV is positive','information_boundary':'target formation and lineup are ignored; model features use only prior dated matches strictly before target Beijing date minus 3 days; target FT is label only','live_limit':'Transfermarkt is a retrospective bulk file without formation first-publication/receipt timestamps; receipt FID overlap is not prospective validation'},
      'results':methods,'frozen_baseline_2024_2026':frozen_stat,'merged_with_frozen':merged,
      'deduplication':{'frozen_unique_fids':len(frozen_ids),'candidate_unique_fids':len(candidate_fids),'overlap':len(frozen_ids&candidate_fids)},
      'formal_orders':0,'formal_ledger_writes':0,'production_changes':0,'crown_api_requests':0}
    (OUT/'formation_matchup_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with gzip.open(OUT/'formation_matchup_per_fixture_20261120.jsonl.gz','wt',encoding='utf8') as f:
        for r in scored:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    with gzip.open(OUT/'formation_matchup_orders_20261120.jsonl.gz','wt',encoding='utf8') as f:
        for r in candidates:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'mapped':len(mapped),'coverage':dict(status),'folds':folds,'methods':{k:v['overall'] for k,v in methods.items()},'frozen':frozen_stat,'merged':merged,'receipt_overlap':len(receipt_target)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
