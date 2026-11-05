"""Read actual Crown movement endpoint for selected source schedule IDs without emitting prices."""
import argparse,json,os,time,urllib.parse,urllib.request

def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='+',required=True);a=p.parse_args()
    token=os.environ.get('TOTALCORNER_TOKEN')
    if not token: raise RuntimeError('TOTALCORNER_TOKEN is missing')
    for match_id in a.ids:
        url='https://api.totalcorner.com/v1/match/bookmaker_odds/'+urllib.parse.quote(match_id,safe='')+'?'+urllib.parse.urlencode({'token':token,'bookmaker':'crown','columns':'asianList,goalList'})
        for retry in range(7):
            with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept':'application/json'}),timeout=30) as response:
                result=json.load(response)
            code=(result.get('error') or {}).get('code') if isinstance(result.get('error'),dict) else None
            if code=='TOO_MANY_REQUEST' and retry<6:
                time.sleep(11);continue
            break
        if result.get('success')!=1:
            print(json.dumps({'status':'API_UNSUCCESSFUL','error_code':code}));continue
        matches=[m for m in result.get('data',[]) if str(m.get('id'))==match_id]
        crown=[b for m in matches for b in m.get('bookmakers',[]) if b.get('slug')=='crown']
        print(json.dumps({'status':'CROWN_IDENTIFIED' if len(crown)==1 else 'CROWN_MISSING_OR_AMBIGUOUS','source_match_count':len(matches),'crown_bookmaker_count':len(crown),'ah_movement_rows':len(crown[0].get('asian_list',[])) if len(crown)==1 else 0,'ou_movement_rows':len(crown[0].get('goal_list',[])) if len(crown)==1 else 0,'camel_ah_rows':len(crown[0].get('asianList',[])) if len(crown)==1 else 0,'camel_ou_rows':len(crown[0].get('goalList',[])) if len(crown)==1 else 0,'bet_placed':False,'telegram_sent':False}))
        time.sleep(2.2)
if __name__=='__main__': main()
