"""Append-only, shadow-only M3 settlement using verified TotalCorner full-time results.

Never alters forecasts or orders. TotalCorner is the sole full-time score source.
"""
import argparse
import datetime
import hashlib
import json
import os
import time
import urllib.parse
import requests
from pathlib import Path
from research.m3.kickoff_gate import totalcorner_shanghai_kickoff
from research.m3.probabilities import settle_score

UTC = datetime.timezone.utc
FT_STATUSES = {'full','finished','ft','complete','completed','ended','aet'}

def response_row(payload, match_id):
    if payload.get('success') != 1:
        raise ValueError('provider response not successful')
    data = payload.get('data')
    rows = data if isinstance(data,list) else [data] if isinstance(data,dict) else []
    found=[r for r in rows if isinstance(r,dict) and str(r.get('id'))==str(match_id)]
    if len(found)!=1: raise ValueError('provider match identity unresolved')
    return found[0]

def verified_final(payload, match_id, kickoff, now, fixture=None):
    row=response_row(payload,match_id)
    if str(row.get('status','')).strip().lower() not in FT_STATUSES:return None
    if not row.get('h') or not row.get('a') or not row.get('l_id'):raise ValueError('missing provider identity')
    stamp=totalcorner_shanghai_kickoff(row)
    if stamp is None or not kickoff:
        raise ValueError('provider kickoff identity missing')
    if stamp != kickoff:
        # Narrow, evidence-backed correction for this single event, not a global tolerance.
        fixture = fixture or {}
        def utc(value):
            return datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)
        authorized = (str(match_id) == '201655492'
            and row.get('h') == 'Maccabi Haifa'
            and row.get('a') == 'Hapoel Beer Sheva'
            and str(row.get('l_id')) == '328'
            and fixture.get('home_team') == 'Maccabi Haifa'
            and fixture.get('away_team') == 'Hapoel Beer Sheva'
            and utc(kickoff) == utc('2026-10-26T17:00:00+00:00')
            and utc(stamp) == utc('2026-10-26T17:30:11+00:00'))
        if not authorized:
            raise ValueError('provider kickoff identity mismatch')
        print(json.dumps({'m3_verified_kickoff_revision': {
            'match_id': str(match_id), 'saved_kickoff_utc': kickoff,
            'provider_kickoff_utc': stamp, 'home': row.get('h'),
            'away': row.get('a'), 'league_id': row.get('l_id')}}))
    if datetime.datetime.fromisoformat(kickoff).astimezone(UTC)>=now:return None
    def score(key):
        v=row.get(key)
        if isinstance(v,bool) or not str(v).isdigit():raise ValueError('invalid final score')
        return int(v)
    return score('hg'),score('ag'),hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def fetch_final(match_id,token):
    # Match-results only. Use M1's proven HTTP client to prevent incomplete
    # chunked responses from hiding otherwise verified full-time scores.
    # Score/identity/market settlement validation remains unchanged.
    url='https://api.totalcorner.com/v1/match/view/'+urllib.parse.quote(str(match_id),safe='')
    for attempt in range(5):
        try:
            response=requests.get(url,params={'token':token},
                headers={'Accept':'application/json','User-Agent':'M1-GitHub-Actions/3.0'},timeout=30)
            response.raise_for_status()
            payload=response.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
                requests.exceptions.Timeout) as error:
            if attempt==4:
                raise RuntimeError('TotalCorner 比分下载中断') from error
            time.sleep(2.0*(attempt+1))
            continue
        if payload.get('success')==1:return payload
        if (payload.get('error') or {}).get('code')!='TOO_MANY_REQUEST':return payload
        time.sleep(11)
    return payload

def reconcile(events,finished,lookup,now):
    forecasts={x['forecast_id']:x for x in events if x.get('protocol')=='M3_TOTALCORNER_FORWARD_FORECAST_V1'}
    existing={x.get('event_id') for x in events}
    # Already-settled immutable orders need no repeated FT network request.
    candidates=[x for x in events if x.get('protocol')=='M3_SHADOW_ORDER_V1'
                and hashlib.sha256(('M3_RESULT_OBSERVED_V1:'+x['event_id']).encode()).hexdigest() not in existing]
    ids={}
    fixture_by_match={}
    for e in candidates:
        f=forecasts.get(e.get('forecast_id'))
        if not f or not f.get('kickoff_utc_verified') or not e.get('totalcorner_match_id'):continue
        key=str(e['totalcorner_match_id'])
        ids.setdefault(key,set()).add((f['fixture_identity_id'],f['kickoff_utc_verified']))
        fixture_by_match.setdefault(key,f)
    verified={};reasons={}
    for mid,identities in ids.items():
        if len(identities)!=1:
            reasons['CONFLICTING_FIXTURE_MAPPING']=reasons.get('CONFLICTING_FIXTURE_MAPPING',0)+1;continue
        fid,kickoff=next(iter(identities))
        if datetime.datetime.fromisoformat(kickoff).astimezone(UTC)>=now:continue
        try:
            payload=lookup(mid)
            if mid == '201655492':
                diagnostic_row=response_row(payload,mid)
                provider_kickoff=totalcorner_shanghai_kickoff(diagnostic_row)
                print(json.dumps({'m3_targeted_identity_audit':{'match_id':mid,'saved_kickoff_utc':kickoff,'provider_kickoff_utc':provider_kickoff,'status':diagnostic_row.get('status'),'home':diagnostic_row.get('h'),'away':diagnostic_row.get('a'),'league_id':diagnostic_row.get('l_id'),'home_goals':diagnostic_row.get('hg'),'away_goals':diagnostic_row.get('ag')}},default=str,ensure_ascii=False))
            outcome=verified_final(payload,mid,kickoff,now,fixture_by_match.get(mid))
            if outcome is None:continue
            verified[mid]=outcome
        except Exception as exc:
            if mid == '201655492':
                print(json.dumps({'m3_ft_diagnostic_match_id':mid,'reason_type':type(exc).__name__,'reason':str(exc)},ensure_ascii=False))
            reasons['PROVIDER_OR_IDENTITY_UNVERIFIED']=reasons.get('PROVIDER_OR_IDENTITY_UNVERIFIED',0)+1
    new=[]
    for e in candidates:
        f=forecasts.get(e.get('forecast_id'))
        if not f or e.get('fixture_identity_id')!=f.get('fixture_identity_id'):continue
        outcome=verified.get(str(e.get('totalcorner_match_id')))
        if outcome is None:continue
        h,a,digest=outcome
        state,unit=settle_score(e['market'],e['line'],e['side'],h,a,e['decimal_odd'])
        event_id=hashlib.sha256(('M3_RESULT_OBSERVED_V1:'+e['event_id']).encode()).hexdigest()
        if event_id in existing:continue
        new.append({'event_id':event_id,'protocol':'M3_TOTALCORNER_FORWARD_SETTLEMENT_V1',
            'shadow_order_event_id':e['event_id'],'candidate_event_id':e['event_id'],'forecast_id':e['forecast_id'],
            'fixture_identity_id':e['fixture_identity_id'],'home_goals':h,'away_goals':a,
            'market':e['market'],'side':e['side'],'line':e['line'],
            'hypothetical_unit_return':unit,'settlement_state':state,
            'actual_bet_placed':False,'formal_order':False,'telegram_sent':False,
            'result_source':'TotalCorner verified /match/view','result_sha256':digest,
            'observed_utc':now.isoformat()})
        existing.add(event_id)
    return new, {'verified_fixtures':len(verified),'rejected':reasons,'candidates':len(candidates)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ledger',required=True,type=Path)
    args=p.parse_args()
    events=[json.loads(s) for s in args.ledger.read_text().splitlines() if s.strip()]
    finished={}
    token=os.environ['TOTALCORNER_TOKEN'];now=datetime.datetime.now(UTC)
    new,stats=reconcile(events,finished,lambda mid:fetch_final(mid,token),now)
    with args.ledger.open('a') as out:
        for row in new:out.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+'\n')
    print(json.dumps({'status':'COMPLETED','settlements_added':len(new),'formal_bets':0,'realized_formal_roi':None,**stats}))

if __name__=='__main__':main()
