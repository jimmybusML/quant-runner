#!/usr/bin/env python3
"""Classify unresolved schedule FTs by kickoff time and preserved source status."""
from __future__ import annotations
import argparse,collections,csv,datetime as dt,hashlib,json,pathlib
OUT=pathlib.Path(__file__).resolve().parent
INPUT=OUT/'unverified_FT_candidates.jsonl'

def parse_utc(value):
    if not value:return None
    try:
        x=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return x.replace(tzinfo=dt.timezone.utc) if x.tzinfo is None else x.astimezone(dt.timezone.utc)
    except Exception:return None

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--as-of-utc',default=None);a=p.parse_args()
    asof=parse_utc(a.as_of_utc) if a.as_of_utc else dt.datetime.now(dt.timezone.utc)
    if asof is None:raise SystemExit('invalid --as-of-utc')
    groups=collections.defaultdict(lambda:{'fids':set(),'reason':collections.Counter(),'statuses':collections.Counter(),'placeholder_0_0':set(),'status_full_score_invalid':set(),'kickoff_min':None,'kickoff_max':None})
    totals=collections.Counter();rows=[];seen=set()
    with INPUT.open(encoding='utf-8') as f:
        for line in f:
            r=json.loads(line);fid=str(r['match_id'])
            if fid in seen:raise SystemExit(f'duplicate candidate FID: {fid}')
            seen.add(fid);kickoff=parse_utc(r.get('kickoff_utc'));statuses=sorted({str(x) for x in r.get('observed_statuses',[])})
            scores=sorted({str(x) for x in r.get('observed_scores',[])})
            if kickoff is None:reason='kickoff_missing'
            elif kickoff>asof:reason='future_fixture_not_due'
            elif 'full' in {x.lower() for x in statuses}:
                reason='full_status_score_invalid'
            elif any(x.lower() in ('none','unknown','') for x in statuses):reason='past_kickoff_status_missing_or_unknown'
            elif statuses:reason='provider_reports_non_full_status'
            else:reason='past_kickoff_no_status_record'
            year=int(r['calendar_year_utc']);key=(str(r['provider_league_id']),year);g=groups[key]
            g['fids'].add(fid);g['reason'][reason]+=1;g['statuses'].update(statuses)
            if '0:0' in scores:g['placeholder_0_0'].add(fid)
            if reason=='full_status_score_invalid':g['status_full_score_invalid'].add(fid)
            if kickoff:
                g['kickoff_min']=min(kickoff,g['kickoff_min']) if g['kickoff_min'] else kickoff
                g['kickoff_max']=max(kickoff,g['kickoff_max']) if g['kickoff_max'] else kickoff
            totals[reason]+=1
            rows.append({'fid':fid,'provider_league_id':str(r['provider_league_id']),'calendar_year_utc':year,
                'kickoff_utc':kickoff.isoformat().replace('+00:00','Z') if kickoff else None,'ft_readiness':reason,
                'observed_statuses':statuses,'observed_scores':scores,'placeholder_0_0_present':'0:0' in scores})
    matrix=[]
    for (lid,year),g in sorted(groups.items()):
        row={'provider_league_id':lid,'calendar_year_utc':year,'unresolved_fids':len(g['fids']),
             'kickoff_min_utc':g['kickoff_min'].isoformat().replace('+00:00','Z') if g['kickoff_min'] else None,
             'kickoff_max_utc':g['kickoff_max'].isoformat().replace('+00:00','Z') if g['kickoff_max'] else None,
             'placeholder_0_0_fids':len(g['placeholder_0_0']),'status_full_score_invalid_fids':len(g['status_full_score_invalid'])}
        row.update({name:g['reason'].get(name,0) for name in sorted({x['ft_readiness'] for x in rows})})
        row['observed_status_counts_json']=json.dumps(dict(sorted(g['statuses'].items())),ensure_ascii=False,separators=(',',':'))
        matrix.append(row)
    prefix='unverified_ft_readiness_2019_2026'
    csvpath=OUT/f'{prefix}_by_league_year.csv'
    fields=list(matrix[0]) if matrix else ['provider_league_id','calendar_year_utc','unresolved_fids']
    with csvpath.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(matrix)
    jsonlpath=OUT/f'{prefix}_per_fid.jsonl'
    with jsonlpath.open('w',encoding='utf-8') as f:
        for r in sorted(rows,key=lambda x:(x['provider_league_id'],x['calendar_year_utc'],x['fid'])):f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    result={'as_of_utc':asof.isoformat().replace('+00:00','Z'),'candidate_count':len(rows),'input_sha256':sha(INPUT),'counts_by_ft_readiness':dict(sorted(totals.items())),
      'placeholder_0_0_fids':sum(len(g['placeholder_0_0']) for g in groups.values()),'league_year_rows':len(matrix),
      'outputs':{csvpath.name:sha(csvpath),jsonlpath.name:sha(jsonlpath)},
      'interpretation':'Future fixtures are not yet due for FT verification. Past-kickoff statuses and 0:0 values are preserved as source observations and never treated as verified final scores.'}
    out=OUT/f'{prefix}_summary.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
