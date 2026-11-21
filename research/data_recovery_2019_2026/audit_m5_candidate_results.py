#!/usr/bin/env python3
"""Compare the existing partial M5 full-time manifest to the unified FID inventory."""
from __future__ import annotations
import collections, gzip, hashlib, json
from pathlib import Path

M5=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/candidate-manifest.partial.json')
INVENTORY=Path(__file__).resolve().parent/'fixture_inventory_2019_2026.jsonl.gz'
UNVERIFIED=Path(__file__).resolve().parent/'unverified_FT_candidates.jsonl'
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    m5=json.loads(M5.read_text(encoding='utf-8'));rows={};year_counts=collections.Counter();league_counts=collections.Counter()
    for r in m5.get('rows',[]):
        y=int(str(r.get('kickoff_utc',''))[:4])
        if not 2019<=y<=2026:continue
        fid=str(r.get('match_id') or '')
        if not fid:continue
        pair=(int(r['home_goals']),int(r['away_goals']))
        rows[fid]=(pair,r)
        year_counts[y]+=1;league_counts[(str(r.get('league') or 'UNKNOWN'),y)]+=1
    unverified={json.loads(x)['match_id'] for x in UNVERIFIED.open(encoding='utf-8') if x.strip()}
    inventory={}
    with gzip.open(INVENTORY,'rt',encoding='utf-8') as f:
        for line in f:
            r=json.loads(line);inventory[str(r['fid'])]=r
    matched=set(rows)&set(inventory);score_conflicts=[];m5_without_full=[];full_count=0
    for fid in sorted(matched):
        rr=inventory[fid]
        page=rr.get('totalcorner_page_records',[])+rr.get('M1_history_cache_records',[])
        full=[x for x in page if x.get('status')=='full']
        if full:full_count+=1
        for x in full:
            try:v=(int(x.get('home_goals')),int(x.get('away_goals')))
            except (TypeError,ValueError):continue
            if v!=rows[fid][0]:score_conflicts.append({'match_id':fid,'M5_score':rows[fid][0],'schedule_score':v,'status':x.get('status')})
        if not full:m5_without_full.append(fid)
    official={
      '160205699':{'score':[4,0],'source_name':'Atalanta official match report','source_url':'https://en.atalanta.it/news/the-three-points-go-to-inter'},
      '172688907':{'score':[0,1],'source_name':'SSC Napoli official match report','source_url':'https://sscnapoli.it/en/news/match-report-lecce-napoli-0-1'} }
    conflict_fids=sorted({x['match_id'] for x in score_conflicts});details=[]
    for fid in conflict_fids:
        rr=inventory[fid];m5_score=rows[fid][0];records=[]
        for source_key in ('totalcorner_page_records','M1_history_cache_records'):
            for z in rr.get(source_key,[]):
                records.append({'source_type':source_key,'source_file':z.get('page_file') or z.get('source_file'),
                  'source_sha256':z.get('page_sha256'),'status':z.get('status'),
                  'kickoff_utc':z.get('kickoff_utc'),'home':z.get('home_name'),'away':z.get('away_name'),
                  'home_goals':z.get('home_goals'),'away_goals':z.get('away_goals')})
        official_result=official.get(fid)
        details.append({'match_id':fid,'provider_league_id':rr['provider_league_id'],'year':rr['year'],
          'home':rows[fid][1].get('home'),'away':rows[fid][1].get('away'),'kickoff_utc':rows[fid][1].get('kickoff_utc'),
          'M5_candidate_manifest_score':m5_score,'schedule_and_M1_source_rows':records,
          'official_external_result_evidence':official_result,
          'official_result_matches_M5':bool(official_result and tuple(official_result['score'])==m5_score)})
    with (OUT/'score_source_disagreements.jsonl').open('w',encoding='utf-8') as f:
        for x in details:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    summary={'source_file':str(M5),'source_sha256':sha(M5),'source_protocol':m5.get('protocol'),
      'source_complete_historical_universe':m5.get('complete_historical_universe'),
      'source_rows_target_years':len(rows),'source_target_year_counts':dict(year_counts),
      'source_target_league_year_counts':[{'league':k[0],'year':k[1],'matches':v} for k,v in sorted(league_counts.items())],
      'unique_fids':len(rows),'exact_fid_overlap_unified_inventory':len(matched),'M5_candidate_FIDs_also_present_with_full_status_in_unified_sources':full_count,
      'M5_candidate_FIDs_without_verified_full_status_in_unified_sources':len(m5_without_full),
      'M5_candidate_FIDs_overlapping_unverified_FT_manifest':len(set(rows)&unverified),
      'score_conflicts_against_full_status_schedule_rows':len(score_conflicts),
      'score_conflict_examples':score_conflicts[:100],'unique_conflict_FIDs':len(details),
      'score_source_disagreement_file':'score_source_disagreements.jsonl','score_source_disagreement_sha256':sha(OUT/'score_source_disagreements.jsonl'),
      'output_inventory_sha256':sha(INVENTORY),'unverified_manifest_sha256':sha(UNVERIFIED)}
    out=OUT/'m5_candidate_results_audit.json';out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('source_target_league_year_counts','score_conflict_examples')},ensure_ascii=False))

if __name__=='__main__':main()
