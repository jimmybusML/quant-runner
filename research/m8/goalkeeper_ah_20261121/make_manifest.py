#!/usr/bin/env python3
"""Write SHA256 input/output manifest for this historical research run."""
import hashlib,json,pathlib

P=pathlib.Path(__file__).resolve().parent
inputs={
 '/Users/mac/QuantAsiaDesk/research-work/m8_pregame_info_source_20261117/appearances.csv.gz':'e096c2b158fc3d52c4550526c4d4850dd62f31007652f4bcae112eadb1646802',
 '/Users/mac/QuantAsiaDesk/research-work/m8_pregame_info_source_20261117/games.csv.gz':'142561989017d379bcf9e72bad0b87e0996bae0e7b710ebb3def9255f464c741',
 '/Users/mac/QuantAsiaDesk/research-work/m8_pregame_info_source_20261117/game_lineups.csv.gz':'5e83d6fad28364aadfea608013700cf09990062eede1ad9ef189189b0af47ba2',
 '/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3':'7401078708d56a122987fde6231ae4b8cf296020d7fae54048437e73462c8a3f',
 '/private/tmp/quant-runner-m8-goalkeeper/research/m8/player_load_rotation_20261119/m8_player_load_rotation_feature_rows_20261119.jsonl.gz':'d7735b5f56237b793fffc335f292ea7b6db1a0a5459ef9368f76f2b0b99abba5',
 '/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl':'6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665',
 '/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl':'e8cf152c821725139b5492746faa32fe46889886c3971878ee9cb6473e3662f8',
}
files=sorted(x for x in P.iterdir() if x.is_file() and x.name!='SHA256SUMS_20261121.txt')
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
schedule_root=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules')
schedule_files=sorted(schedule_root.glob('*/page-*.raw.json'))
schedule_manifest={'root':str(schedule_root),'file_count':len(schedule_files),
                   'files':[{'path':str(x.relative_to(schedule_root)),'sha256':sha(x)} for x in schedule_files]}
(P/'schedule_source_sha256_20261121.json').write_text(json.dumps(schedule_manifest,ensure_ascii=False,separators=(',',':'))+'\n')
files=sorted(x for x in P.iterdir() if x.is_file() and x.name!='SHA256SUMS_20261121.txt')
lines=[]
for path,digest in inputs.items():lines.append(f'{digest}  {path}')
lines.append(f"{sha(P/'schedule_source_sha256_20261121.json')}  {P/'schedule_source_sha256_20261121.json'}")
for entry in schedule_manifest['files']:
 lines.append(f"{entry['sha256']}  {schedule_root/entry['path']}")
repo=P.parents[2]
for path in files:lines.append(f'{sha(path)}  {path.relative_to(repo)}')
lines.append(f"{sha(repo/'PROJECT_HANDOFF.md')}  PROJECT_HANDOFF.md")
(P/'SHA256SUMS_20261121.txt').write_text('\n'.join(lines)+'\n')
print(P/'SHA256SUMS_20261121.txt')
