#!/usr/bin/env python3
"""Non-mutating per-model reconciliation audit, including overdue identities."""
import datetime as dt
import json
from pathlib import Path

BASE=Path.home()/'QuantAsiaDesk'
NOW=dt.datetime.now(dt.timezone.utc)

def utc(x):
    if not x:return None
    try:
        v=dt.datetime.fromisoformat(str(x).replace('Z','+00:00'))
        return v.astimezone(dt.timezone.utc) if v.tzinfo else None
    except (ValueError,TypeError):return None

m1=json.loads((BASE/'repos/m1/results/m1_formal_ledger.json').read_text())
mr=BASE/'repos/mr1/data/mr1-v6-cross-market/formal'
sent=[json.loads(x) for x in (mr/'sent.jsonl').read_text().splitlines() if x]
settled=json.loads((mr/'settled.json').read_text())['entries']
models={}
for model,records in [
    ('m1',[{'id':k,'fixture_id':v.get('fixture_id'),'kickoff':v.get('kickoff'),'market':v.get('market')} for k,v in m1['picks'].items() if k not in m1['settlements']]),
    ('mr1',[{'id':v['signal_id'],'fixture_id':v.get('match_id'),'kickoff':v.get('kickoff_at'),'market':'AH'} for v in sent if v['signal_id'] not in settled])]:
    for row in records:
        start=utc(row['kickoff'])
        row['status']='KICKOFF_NOT_REACHED' if start and start>NOW else 'PAST_KICKOFF_RESULT_UNVERIFIED' if start else 'KICKOFF_IDENTITY_UNVERIFIED'
    models[model]={'unsettled':len(records),'past_kickoff_unverified':sum(x['status']=='PAST_KICKOFF_RESULT_UNVERIFIED' for x in records),'records':records}
report=BASE/'state/m3_latest.json'
if report.exists():
    x=json.loads(report.read_text());models['m3']={'report_generated_at':x.get('generated_at_utc'),'unique_shadow_orders':x.get('unique_shadow_orders'),'shadow_only':True,'lines':x.get('models')}
output={'generated_at':NOW.isoformat(),'models':models,'note':'Past kickoff is not proof of full time. No results or payouts are inferred.'}
p=BASE/'state/unified_settlement_pending.json';temp=p.with_suffix('.tmp');temp.write_text(json.dumps(output,ensure_ascii=False,indent=2));temp.replace(p)
print(json.dumps({'generated_at':output['generated_at'],'m1':{k:v for k,v in models['m1'].items() if k!='records'},'mr1':{k:v for k,v in models['mr1'].items() if k!='records'},'m3_report_time':models.get('m3',{}).get('report_generated_at')},ensure_ascii=False))
