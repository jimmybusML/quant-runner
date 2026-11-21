#!/usr/bin/env python3
"""Append only exact-match expanded-15 prior-ground geocode needs to cacheable list."""
import collections, gzip, json, pathlib

OUT = pathlib.Path(__file__).resolve().parent
BASE_QUERIES = OUT / 'venue_geocode_queries_base_20261121.jsonl'
QUERIES = OUT / 'venue_geocode_queries_20261121.jsonl'
LINKS = OUT / 'expanded15_venue_linkage_by_fid_20261121.jsonl.gz'

def main():
    queries = [json.loads(x) for x in BASE_QUERIES.open(encoding='utf-8') if x.strip()]
    by_query = {r['query']: r for r in queries}
    years_by_key = collections.defaultdict(collections.Counter)
    roles_by_key = collections.defaultdict(collections.Counter)
    fids_by_key = collections.defaultdict(set)
    for r in map(json.loads, gzip.open(LINKS, 'rt', encoding='utf-8')):
        if not r.get('both_prior_grounds_unique'):
            continue
        country = r.get('transfermarkt_country')
        for role, venue in (('host_expected_ground', r.get('home_prior_ground')),
                            ('away_usual_home_ground', r.get('away_prior_home_ground'))):
            if not venue or not country:
                continue
            query = f'{venue}, {country}'
            years_by_key[query][str(r['year'])] += 1
            roles_by_key[query][role] += 1
            fids_by_key[query].add(r['fid'])
    additions = []
    for query in sorted(years_by_key):
        if query in by_query:
            row = by_query[query]
            base_n = int(row.get('candidate_fids') or 0)
            row['candidate_fids'] = base_n + len(fids_by_key[query])
            row['expanded15_candidate_fids'] = len(fids_by_key[query])
            row['expanded15_years'] = dict(sorted(years_by_key[query].items()))
            row['expanded15_roles'] = dict(roles_by_key[query])
        else:
            venue, country = query.rsplit(', ', 1)
            row = {'venue': venue, 'country': country, 'query': query,
                   'candidate_fids': len(fids_by_key[query]),
                   'years': dict(sorted(years_by_key[query].items())),
                   'roles': dict(roles_by_key[query]),
                   'expanded15_candidate_fids': len(fids_by_key[query]),
                   'expanded15_years': dict(sorted(years_by_key[query].items())),
                   'expanded15_roles': dict(roles_by_key[query]), 'source': 'expanded15 strict linkage audit'}
            queries.append(row)
            by_query[query] = row
            additions.append(row)
    queries.sort(key=lambda x: x['query'])
    with QUERIES.open('w', encoding='utf-8') as f:
        for r in queries:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    with (OUT / 'expanded15_geocode_query_additions_20261121.jsonl').open('w', encoding='utf-8') as f:
        for r in additions:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    print(json.dumps({'merged_queries': len(queries), 'new_unique_queries': len(additions),
                      'new_queries': [x['query'] for x in additions]}, ensure_ascii=False))

if __name__ == '__main__':
    main()
