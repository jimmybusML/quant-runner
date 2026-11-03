import fs from 'node:fs/promises';
import {notifyV6AhFormal} from '../repos/mr1/src/v6-ah-formal-notify.js';

// Mirrors the existing GitHub workflow's 2026-10-19 formal AH resumption.
const path='data/mr1-v6-cross-market/formal/state.json';
const original=await fs.readFile(path,'utf8');
const state=JSON.parse(original);
state.activated_at='2026-10-19T09:17:21.033Z';
try{
  await fs.writeFile(path,JSON.stringify(state,null,2)+'\n');
  const result=await notifyV6AhFormal({shadowOnly:false});
  console.log('MR1_AH_LOCAL_FORMAL_RESULT '+JSON.stringify(result));
}finally{
  await fs.writeFile(path,original);
}
