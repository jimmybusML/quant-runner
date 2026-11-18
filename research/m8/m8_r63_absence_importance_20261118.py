import json, re, unicodedata, math, hashlib, collections
from pathlib import Path
import pandas as pd
import numpy as np

P=Path('/Users/mac/QuantAsiaDesk/research-work')
CACHE=P/'m8_r62_full_season_guardian_source_20261118'
R62=json.loads((P/'m8_r62_full_season_absence_ah_replay_20261118.json').read_text())

def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    s=re.sub(r'\([^)]*\)',' ',s)
    s=re.sub(r'[^a-z0-9 ]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def base_name(s):
    return re.sub(r'\s*\([^)]*\)','',str(s)).strip()

# Reuse exact Guardian parser contract from R61.
s=(P/'m8_r61_dated_team_news_audit_20261118.py').read_text()
ns={}
exec(s[:s.index('sources=[]')],ns)
ns['SOURCE']=CACHE

def parse_source(day,url):
    return ns['extract'](url,day)

# Match fixtures from R62 with raw player names preserved.
raw=[]
for src in R62['sources']:
    r=parse_source(src['date'],src['url'])
    for m in r['matches']:
        if len(m['teams'])!=2: continue
        raw.append((src,m))
# R62 fixture set is canonical; source parser may expose extra sections

# Transfermarkt-derived appearance data. GB1 is Premier League.
games=pd.read_csv(P/'m8_pregame_info_source_20261117/games.csv.gz',compression='gzip',
                  usecols=['game_id','competition_id','date','home_club_id','away_club_id','home_club_name','away_club_name'])
games=games[games.competition_id.eq('GB1')].copy()
games['date']=pd.to_datetime(games.date,utc=True)
games['h_norm']=games.home_club_name.map(norm); games['a_norm']=games.away_club_name.map(norm)
apps=pd.read_csv(P/'m8_pregame_info_source_20261117/appearances.csv.gz',compression='gzip',
                 usecols=['date','player_id','player_club_id','player_name','competition_id','minutes_played'])
apps['date']=pd.to_datetime(apps.date,utc=True)
apps['name_norm']=apps.player_name.map(norm)
# All competitions for importance; GB1 subset separately.
apps_all=apps.copy()
apps_pl=apps[apps.competition_id.eq('GB1')].copy()

# Name lookup by club and time is built from appearances. We use the most recent
# prior 730d candidate pool; exact full-name first, then unique surname within club.
def candidates_for(club_id, cutoff):
    lo=cutoff-pd.Timedelta(days=730)
    x=apps_all[(apps_all.player_club_id.eq(club_id)) & (apps_all.date.between(lo,cutoff))]
    return x

cache_cand={}
def map_player(raw_name, club_id, cutoff):
    key=(int(club_id),cutoff.date(),base_name(raw_name))
    if key in cache_cand:return cache_cand[key]
    x=candidates_for(club_id,cutoff)
    q=norm(base_name(raw_name))
    if not q:
        cache_cand[key]=(None,'empty'); return cache_cand[key]
    exact=x[x.name_norm.eq(q)]
    if len(exact):
        # Choose the player_id with most recent appearance if duplicated aliases.
        pid=int(exact.sort_values('date').iloc[-1].player_id)
        pname=str(exact.sort_values('date').iloc[-1].player_name)
        cache_cand[key]=((pid,pname),'exact'); return cache_cand[key]
    # Unique surname match within club/time.
    toks=q.split()
    surname=toks[-1]
    sx=x[x.name_norm.str.split().str[-1].eq(surname)]
    pids=sx.player_id.drop_duplicates().tolist()
    if len(pids)==1:
        row=sx.sort_values('date').iloc[-1]
        cache_cand[key]=((int(row.player_id),str(row.player_name)),'surname_unique')
        return cache_cand[key]
    # If a multi-token name shares all normalized tokens with a candidate.
    if len(toks)>1:
        def overlap(v):
            a=set(v.split()); b=set(toks)
            return len(a&b)/max(1,len(a|b))
        scores=x[['player_id','player_name','name_norm']].drop_duplicates().copy()
        scores['sc']=scores.name_norm.map(overlap)
        mx=scores.sc.max() if len(scores) else 0
        top=scores[scores.sc==mx]
        if mx>=0.75 and len(top)==1:
            row=top.iloc[0]
            cache_cand[key]=((int(row.player_id),str(row.player_name)),'token_overlap')
            return cache_cand[key]
    cache_cand[key]=(None,'unmatched'); return cache_cand[key]

# Club id resolution by exact normalized club name, with year/day proximity.
club_map=collections.defaultdict(set)
for r in games.itertuples():
    club_map[r.h_norm].add(int(r.home_club_id)); club_map[r.a_norm].add(int(r.away_club_id))

ALIASES={
 "man city":"manchester city","manchester city":"manchester city",
 "man utd":"manchester united","manchester united":"manchester united",
 "nottm forest":"nottingham forest","nottingham forest":"nottingham forest",
 "wolves":"wolverhampton wanderers","wolverhampton":"wolverhampton wanderers","wolverhampton wanderers":"wolverhampton wanderers",
 "spurs":"tottenham","tottenham":"tottenham",
 "west ham":"west ham united","west ham united":"west ham united",
 "brighton":"brighton and hove albion","brighton and hove albion":"brighton and hove albion",
 "palace":"crystal palace","crystal palace":"crystal palace",
 "villa":"aston villa","aston villa":"aston villa"
}
def canon_team(s): return ALIASES.get(norm(s),norm(s))
def resolve_club(team_name, match_date):
    q=canon_team(team_name)
    day=games[games.date.dt.date==match_date.date()]
    cand=[]
    for r in day.itertuples():
        for nm,cid in [(r.h_norm,r.home_club_id),(r.a_norm,r.away_club_id)]:
            cand.append((sim(q,canon_team(nm)),int(cid),nm))
    cand.sort(reverse=True)
    return cand[0][1] if cand and cand[0][0]>=0.55 else None

out={'study':'M8_R63_ABSENCE_IMPORTANCE_WEIGHTED_BY_PRIOR_PLAYER_MINUTES_20261118',
     'hypothesis':'Raw injury/suspension counts can be misleading when absent players have different prior usage. Compare the side with greater reported absent-player prior minutes, using only appearances dated before kickoff. This is retrospective research, not a live rule.',
     'source_basis':'R62 Guardian historical pregame injury/suspension articles + Transfermarkt-derived appearance history already present in the research source bundle + exact R62 Crown T12 AH/FT fixtures. No future result/T1 membership used for weighting.',
     'fixtures':[],'mapping':{},'by_year':{},'foundation':{}}

# Match each canonical R62 fixture to the corresponding parsed Guardian section on the same source date.
# Use string similarity only for retrospective team-name aliases (Man City/Manchester City, etc.).
from difflib import SequenceMatcher
def sim(a,b): return SequenceMatcher(None,norm(a),norm(b)).ratio()
r62_by={z['fid']:z for z in R62['fixtures']}
for src in R62['sources']:
    parsed=parse_source(src['date'],src['url'])
    for z in [x for x in r62_by.values() if x['source_news_day']==src['date']]:
        scored=[]
        for m in parsed['matches']:
            scored.append((sim(z['home'],m['home_label'])+sim(z['away'],m['away_label']),m))
        if not scored: continue
        scored.sort(key=lambda x:x[0],reverse=True)
        if scored[0][0] < 1.0: continue
        m=scored[0][1]
        kick=pd.Timestamp(z['UTC_kickoff']).tz_convert('UTC')
        clubs=[resolve_club(m['teams'][0]['name'],kick),resolve_club(m['teams'][1]['name'],kick)]
        if None in clubs: continue
        team_rows=[]; total_map=0; total_names=0; method_counts=collections.Counter()
        for team,club_id in zip(m['teams'],clubs):
            details=[]
            for status in ('injured','suspended'):
                for rawname in team[status]:
                    total_names+=1
                    mp,method=map_player(rawname,club_id,kick); method_counts[method]+=1
                    if mp is None: continue
                    pid,pname=mp; lo=kick-pd.Timedelta(days=365)
                    pa=apps_all[(apps_all.player_id.eq(pid)) & (apps_all.player_club_id.eq(club_id)) & (apps_all.date.between(lo,kick))]
                    pp=apps_pl[(apps_pl.player_id.eq(pid)) & (apps_pl.player_club_id.eq(club_id)) & (apps_pl.date.between(lo,kick))]
                    details.append({'reported_name':rawname,'matched_player':pname,'player_id':pid,'match_method':method,
                                    'prior365_all_minutes':float(pa.minutes_played.sum()),'prior365_pl_minutes':float(pp.minutes_played.sum())})
                    total_map+=1
            team_rows.append({'team':team['name'],'club_id':club_id,'players':details,
                              'raw_absence_count':len(team['injured'])+len(team['suspended']),'mapped_absence_count':len(details),
                              'weighted_all_minutes':sum(d['prior365_all_minutes'] for d in details),
                              'weighted_pl_minutes':sum(d['prior365_pl_minutes'] for d in details),
                              'max_absent_all_minutes':max([d['prior365_all_minutes'] for d in details] or [0]),
                              'max_absent_pl_minutes':max([d['prior365_pl_minutes'] for d in details] or [0])})
        if total_names==0: continue
        weighted_all='home' if team_rows[0]['weighted_all_minutes']>team_rows[1]['weighted_all_minutes'] else 'away' if team_rows[1]['weighted_all_minutes']>team_rows[0]['weighted_all_minutes'] else None
        weighted_pl='home' if team_rows[0]['weighted_pl_minutes']>team_rows[1]['weighted_pl_minutes'] else 'away' if team_rows[1]['weighted_pl_minutes']>team_rows[0]['weighted_pl_minutes'] else None
        max_all='home' if team_rows[0]['max_absent_all_minutes']>team_rows[1]['max_absent_all_minutes'] else 'away' if team_rows[1]['max_absent_all_minutes']>team_rows[0]['max_absent_all_minutes'] else None
        max_pl='home' if team_rows[0]['max_absent_pl_minutes']>team_rows[1]['max_absent_pl_minutes'] else 'away' if team_rows[1]['max_absent_pl_minutes']>team_rows[0]['max_absent_pl_minutes'] else None
        rr=dict(z); rr['importance']=team_rows
        rr['weighted_all_minutes_side']=weighted_all; rr['weighted_pl_minutes_side']=weighted_pl
        rr['max_absent_all_minutes_side']=max_all; rr['max_absent_pl_minutes_side']=max_pl
        rr['mapping_total_names']=total_names; rr['mapping_matched_names']=total_map; rr['mapping_method_counts']=dict(method_counts)
        for key,side in [('weighted_all',weighted_all),('weighted_pl',weighted_pl),('max_all',max_all),('max_pl',max_pl)]:
            if side: rr[key+'_PnL']=rr['Crown_home_PnL'] if side=='home' else rr['Crown_away_PnL']
        out['fixtures'].append(rr)

def calc(a):
    a=np.asarray(a,dtype=float)
    return {'n':int(len(a)),'U':round(float(a.sum()),3),'ROI':round(float(a.mean()*100),3) if len(a) else None,
            'wins':int((a>1e-8).sum()),'losses':int((a<-1e-8).sum()),'push':int((abs(a)<=1e-8).sum())}
def g(rows,key):
    r=[x for x in rows if x.get(key+'_PnL') is not None and x.get('underdog_PnL') is not None]
    return {'n':len(r),key+'_AH':calc([x[key+'_PnL'] for x in r]),
            'same_games_underdog':calc([x['underdog_PnL'] for x in r]),
            'same_games_home':calc([x['Crown_home_PnL'] for x in r]),
            'same_games_away':calc([x['Crown_away_PnL'] for x in r]),
            key+'_minus_underdog':calc([x[key+'_PnL']-x['underdog_PnL'] for x in r])}
for yr in (2024,2025,2026):
 rows=[x for x in out['fixtures'] if x['year']==yr]
 out['by_year'][str(yr)]={k:g(rows,k) for k in ['weighted_all','weighted_pl','max_all','max_pl']}
# Raw R62 result on exact same fixtures.
for yr in (2024,2025,2026):
 rows=[x for x in out['fixtures'] if x['year']==yr and x['research_more_absent_side']]
 out['by_year'][str(yr)]['raw_count']=calc([x['more_PnL'] for x in rows])

allrows=out['fixtures']
out['mapping']={
 'fixtures_with_team_mapping':len(allrows),
 'reported_absence_names':sum(x['mapping_total_names'] for x in allrows),
 'matched_absence_names':sum(x['mapping_matched_names'] for x in allrows),
 'name_match_rate':round(sum(x['mapping_matched_names'] for x in allrows)/max(1,sum(x['mapping_total_names'] for x in allrows)),4),
 'methods':dict(collections.Counter(m for x in allrows for m in x['mapping_method_counts'] for _ in range(x['mapping_method_counts'][m]))),
 '2026_appearance_coverage_warning':'Appearance source ends 2026-06-28, so prior-365-day minutes for late-2026 fixtures are incomplete. 2026 weighted results are diagnostic only; 2024/25 are the complete-window evaluation.'
}
# Correct methods aggregation
mc=collections.Counter()
for x in allrows:
    mc.update(x['mapping_method_counts'])
out['mapping']['methods']=dict(mc)
for key in ['weighted_all','weighted_pl','max_all','max_pl']:
    out['by_year']['ALL_'+key]=g(allrows,key)

# Foundation hashes from R62 manifest, same integrity contract.
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
digest=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={
 'membership':digest(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(digest(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(digest(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())

(P/'m8_r63_absence_importance_20261118.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('R63_FIXTURES',len(out['fixtures']))
print('MAPPING',out['mapping'])
for yr,v in out['by_year'].items(): print('YEAR',yr,json.dumps(v,ensure_ascii=False))
