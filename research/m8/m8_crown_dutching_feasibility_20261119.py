#!/usr/bin/env python3
"""Audit simultaneous two-sided Crown AH Dutching/underround opportunities.
Research only. No inference from result, no speculative cross-time pairing.
Historical source-event odds and genuinely received quote rows kept separate.
"""
import collections,datetime as dt,hashlib,json,math,sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
OUT=ROOT/'research/m8/m8_crown_dutching_feasibility_20261119'
SOURCES={
 'historical_T1':WORK/'m8_late_full_path_water_features_20261114.jsonl',
 'historical_T12_T24':WORK/'m8_early_joint_market_inventory_20261115.jsonl',
}
DB=Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
def viable(a,b):
    if a is None or b is None:return None
    try:
        a=float(a);b=float(b)
        if not all(map(math.isfinite,(a,b))) or a<=1 or b<=1:return None
        reciprocal=1/a+1/b
        return reciprocal
    except (TypeError,ValueError):return None
def grp():
    return {'quotes':0,'underround':0,'at_even':0,'overround':0,'min_reciprocal':2.0,'max_dutch_margin':-1.0,
      'gross_overround_sum':0.,'positive_dutch_gain_sum':0.}
def add(by,kind,year,fid,home,away,examples,tag):
    v=viable(home,away)
    if v is None:return
    g=by[(kind,str(year))]
    g['quotes']+=1;g['min_reciprocal']=min(v,g['min_reciprocal'])
    g['max_dutch_margin']=max(1-v,g['max_dutch_margin'])
    g['gross_overround_sum']+=v-1
    if v<1-1e-9:
        g['underround']+=1
        gain=1/v-1
        g['positive_dutch_gain_sum']+=gain
        if len(examples)<30:examples.append({'kind':kind,'fid':fid,'year':year,'reciprocal':v,'dutch_gain_on_total_stake':gain,'tag':tag})
    elif v>1+1e-9:g['overround']+=1
    else:g['at_even']+=1

def main():
    by=collections.defaultdict(grp);ex=[];files={}
    for kind,p in SOURCES.items():
        files[kind]=hashlib.sha256(p.read_bytes()).hexdigest()
        for line in p.open():
            r=json.loads(line)
            if kind=='historical_T1':
                add(by,kind,r['year'],str(r['fid']),r.get('home_price'),r.get('away_price'),ex,r.get('date'))
            else:
                add(by,kind+'_T'+str(r['T']),r['year'],str(r['fid']),r.get('ah'),r.get('aa'),ex,r.get('date'))
    c=sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True)
    z=c.execute("""select q.fixture_id,c.kickoff_at_utc,c.data_layer,c.capture_mode,q.quote_kind,q.handicap_home,
      q.home_decimal,q.away_decimal,q.response_received_at_utc,q.quote_source_at_utc
      from asian_quote q join capture c on c.capture_key=q.capture_key
      where c.data_layer='summary' and c.capture_mode='live'
        and c.prospective_observation=1 and c.status='QUOTES_SAVED'
        and q.quote_before_kickoff=1""")
    count=collections.Counter();unique=collections.defaultdict(set)
    for fid,kick,layer,mode,qkind,line,h,a,received,observed in z:
        if not received or not kick or received>=kick:
            count['bad_received_time']+=1;continue
        if observed and observed>received:
            count['bad_observed_time']+=1;continue
        try:y=dt.datetime.fromisoformat(kick.replace('Z','+00:00')).year
        except:count['bad_kickoff']+=1;continue
        name='actual_HTTP_receipt_'+qkind
        add(by,name,y,str(fid),h,a,ex,received)
        unique[name].add(str(fid))
    # Additional independently stored MR1 prospective Crown receipts. Each
    # snapshot may represent another horizon for the same FID; count quote
    # observations, not independent games. No raw HTTP body is published.
    mr1=Path('/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23')
    index=mr1/'snapshot-index.jsonl'
    files['actual_MR1_snapshot_index']=hashlib.sha256(index.read_bytes()).hexdigest()
    raw_quality=collections.Counter()
    with index.open() as f:
        for line in f:
            row=json.loads(line)
            if row.get('classification')!='SNAPSHOT_OK':continue
            p=mr1/row['snapshot_path']
            try:
                content=p.read_bytes()
                if hashlib.sha256(content).hexdigest()!=row['snapshot_sha256']:
                    raw_quality['snapshot_sha_fail']+=1;continue
                s=json.loads(content)
                quote=s.get('AH') or {}
                if not (s.get('source_bookmaker')=='crown' and s.get('source_bookmaker_verified')):
                    raw_quality['not_verified_crown']+=1;continue
                recv=s['received_at'];kick=s['kickoff_at'];src=quote.get('observed_at_utc')
                if not recv or not kick or recv>=kick or (src and src>recv):
                    raw_quality['not_prospective_or_source_after_receipt']+=1;continue
                if quote.get('line') is None:raw_quality['missing_ah_line']+=1;continue
                year=int(kick[:4]);fid=str(row['match_id'])
                v=viable(quote.get('home_price'),quote.get('away_price'))
                if v is None:raw_quality['no_valid_prices']+=1;continue
                add(by,'actual_MR1_snapshot',year,fid,quote['home_price'],quote['away_price'],ex,recv)
                unique['actual_MR1_snapshot'].add(fid)
                raw_quality['valid_receipt_snapshot']+=1
            except Exception:
                raw_quality['parse_error']+=1
    count.update(raw_quality)
    summary={
      'hypothesis':'Same-time two-sided opposite AH bets on exact complementary handicap contract. Arbitrage possible only if (1/home_decimal)+(1/away_decimal)<1 and both prices executable simultaneously.',
      'research_only':True,'historical_source':'post-event retrieval; source event timestamps do not prove real historical receipt',
      'actual_receipt_source':'Crown direct live summary SQLite real HTTP received before kickoff',
      'source_sha256':files,'conditions_are_mathematical_definition_not_production_gate':True,
      'counts_by_source_year':{},
      'actual_http_unique_fids':{k:len(v) for k,v in unique.items()},'quality':dict(count),'illustrative_underround_rows':ex}
    for (kind,year),v in sorted(by.items()):
        n=v['quotes']
        summary['counts_by_source_year'].setdefault(kind,{})[year]={
         **{k:v[k] for k in ('quotes','underround','at_even','overround')},
         'min_reciprocal':round(v['min_reciprocal'],8),
         'best_dutch_margin':round(v['max_dutch_margin'],8),
         'average_book_overround_pct':round(100*v['gross_overround_sum']/n,6) if n else None,
         'positive_dutch_gain_sum_per_full_stake':round(v['positive_dutch_gain_sum'],6)
        }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False)[:14000])
if __name__=='__main__':main()
