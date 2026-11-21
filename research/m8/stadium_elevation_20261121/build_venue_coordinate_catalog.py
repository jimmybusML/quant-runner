#!/usr/bin/env python3
"""Resolve only explicit, name-matching stadium-like OSM results; keep misses."""
import hashlib,json,pathlib,re,unicodedata,collections
OUT=pathlib.Path(__file__).resolve().parent
CACHE=OUT/'nominatim_geocode_cache_20261121.jsonl'
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]','',s)
def main():
 rows=[json.loads(x) for x in CACHE.open(encoding='utf8') if x.strip()]
 selected=[];review=[];types=collections.Counter()
 for r in rows:
  exact=[]
  for x in r.get('response') or []:
   typ=x.get('type');types[typ]+=1
   if typ not in {'stadium','sports_centre','pitch'}:continue
   q=norm(r['venue']);name=norm(x.get('name'));display=norm(x.get('display_name'))
   if not q or not (q==name or q in display or name in q):continue
   address=x.get('address') or {};country=address.get('country')
   if not country:continue
   exact.append(x)
  if len(exact)!=1:
   review.append({'venue':r.get('venue'),'country':r.get('country'),'candidate_fids':r.get('candidate_fids'),'nominatim_results':len(r.get('response') or []),'name_and_type_matches':len(exact),'reason':'no exact stadium-like match' if not exact else 'ambiguous exact stadium-like matches','response_sha256':r.get('response_sha256')})
   continue
  x=exact[0]
  selected.append({'venue':r['venue'],'country_query':r['country'],'candidate_fids':r['candidate_fids'],'years':r['years'],
    'latitude':float(x['lat']),'longitude':float(x['lon']),'osm_type':x.get('type'),'osm_category':x.get('category'),
    'osm_id':x.get('osm_id'),'display_name':x.get('display_name'),'address_country':(x.get('address') or {}).get('country'),
    'importance':x.get('importance'),'geocode_query_sha256':hashlib.sha256(r['query_key'].encode()).hexdigest(),
    'geocode_response_sha256':r.get('response_sha256'),'attribution':'© OpenStreetMap contributors, ODbL'})
 for name,items in [('venue_coordinates_20261121.jsonl',selected),('venue_coordinate_unresolved_20261121.jsonl',review)]:
  with (OUT/name).open('w',encoding='utf8') as f:
   for x in sorted(items,key=lambda z:(z.get('venue') or '')):f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
 print(json.dumps({'geocode_cache_rows':len(rows),'accepted_unique_locations':len(selected),'unresolved_locations':len(review),'accepted_candidate_fids':sum(int(x.get('candidate_fids') or 0) for x in selected),'unresolved_candidate_fids':sum(int(x.get('candidate_fids') or 0) for x in review),'accepted_osm_types':dict(collections.Counter(x['osm_type'] for x in selected)),'nominatim_type_observations':dict(types)},ensure_ascii=False))
if __name__=='__main__':main()
