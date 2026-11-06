#!/usr/bin/env node
// Run the original MR1 V6 cross-market core on a private prepared M5 batch.
// The input JSONL contains fixture identity, score, Crown AH/OU/X1X2 quotes,
// and UTC timestamps. Only aggregate metrics are written to the public repo.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, xs) => {
  if (x.startsWith('--')) a.push([x.slice(2), xs[i + 1]]);
  return a;
}, []));
for (const key of ['input', 'report', 'mr1-core', 'mr1-market-core', 'source-repo-head']) {
  if (!args[key]) throw new Error(`missing --${key}`);
}
const traceRows = [];
const { evaluateCrossMarket } = await import(pathToFileURL(path.resolve(args['mr1-core'])));
const cats = ['win', 'half_win', 'push', 'half_loss', 'loss'];
const probKey = { win: 'full_win', half_win: 'half_win', push: 'push', half_loss: 'half_loss', loss: 'full_loss' };
const rows = fs.readFileSync(args.input, 'utf8').split('\n').filter(Boolean).map(JSON.parse);
const ids = new Set();
for (const r of rows) {
  if (ids.has(String(r.match_id))) throw new Error('duplicate fixture identity in input');
  ids.add(String(r.match_id));
  if (!(r.train_end_utc < r.prediction_asof_utc && r.prediction_asof_utc < r.kickoff_utc)) throw new Error('invalid forecast chronology');
  for (const market of ['AH', 'OU', 'X1X2']) {
    const q = r.quotes?.[market];
    if (!q || !(r.prediction_asof_utc <= q.event_utc && q.event_utc < r.kickoff_utc)) throw new Error(`invalid ${market} event chronology`);
    if (q.receipt_utc && q.receipt_utc < q.event_utc) throw new Error(`invalid ${market} receipt chronology`);
  }
}

function splitLine(line) {
  if (Math.abs(line * 2 - Math.round(line * 2)) < 1e-8) return [line, line];
  const low = Math.floor(line * 2) / 2;
  return [low, low + 0.5];
}
function settle(market, side, homeLine, line, home, away, price) {
  const legs = splitLine(line).map(part => {
    let signed;
    if (market === 'AH') signed = side === 'home' ? 4 * (home - away + part) : 4 * (away - home - part);
    else signed = side === 'over' ? 4 * (home + away - part) : 4 * (part - home - away);
    return signed > 1e-9 ? 1 : signed < -1e-9 ? -1 : 0;
  });
  const wins = legs.filter(x => x === 1).length;
  const losses = legs.filter(x => x === -1).length;
  const category = wins === 2 ? 'win' : wins === 1 ? 'half_win' : losses === 2 ? 'loss' : losses === 1 ? 'half_loss' : 'push';
  return { category, pnl: legs.reduce((s, x) => s + (x === 1 ? price - 1 : x === -1 ? -1 : 0), 0) / 2 };
}
function summarize(xs) {
  const pnl = xs.reduce((s, x) => s + x.pnl, 0);
  const settlement = Object.fromEntries(cats.map(c => [c, xs.filter(x => x.category === c).length]));
  let balance = 0, peak = 0, maxDd = 0;
  const eventPnl = new Map();
  for (const x of xs) eventPnl.set(x.event, (eventPnl.get(x.event) ?? 0) + x.pnl);
  for (const t of [...eventPnl.keys()].sort()) { balance += eventPnl.get(t); peak = Math.max(peak, balance); maxDd = Math.max(maxDd, peak - balance); }
  let ll = 0, brier = 0;
  for (const x of xs) {
    ll -= Math.log(Math.max(x.probs[probKey[x.category]], 1e-15));
    for (const c of cats) brier += (x.probs[probKey[c]] - (c === x.category ? 1 : 0)) ** 2;
  }
  const byYear = {};
  for (const year of [...new Set(xs.map(x => x.year))].sort()) {
    const group = xs.filter(x => x.year === year), net = group.reduce((s, x) => s + x.pnl, 0);
    byYear[year] = { bets: group.length, net_units: +net.toFixed(6), roi_pct: +(100 * net / group.length).toFixed(6) };
  }
  return {
    unique_fixtures: xs.length, simulated_bets: xs.length, settled_bets: xs.length, stake_units: xs.length,
    net_units: +pnl.toFixed(6), roi_pct: +(100 * pnl / xs.length).toFixed(6), settlement_counts: settlement,
    max_drawdown_units_by_quote_event_time: +maxDd.toFixed(6), settlement_log_loss: +(ll / xs.length).toFixed(8),
    settlement_brier: +(brier / xs.length).toFixed(8), quote_sources: { Crown: xs.length },
    response_receipts: { pre_kickoff: xs.filter(x => x.receipt < x.kickoff).length, post_kickoff: xs.filter(x => x.receipt >= x.kickoff).length },
    by_utc_kickoff_year: byYear,
  };
}

const marketRows = { AH: [], OU: [] };
let invalid = 0;
for (const r of rows) {
  const q = r.quotes;
  const ah = { home_line: Number(q.AH.line), away_line: -Number(q.AH.line), home_price: Number(q.AH.prices[0]), away_price: Number(q.AH.prices[1]) };
  const ou = { over_line: Number(q.OU.line), under_line: Number(q.OU.line), over_price: Number(q.OU.prices[0]), under_price: Number(q.OU.prices[1]) };
  const x1x2 = { home_price: Number(q.X1X2.prices[0]), draw_price: Number(q.X1X2.prices[1]), away_price: Number(q.X1X2.prices[2]) };
  const result = evaluateCrossMarket({ ah, ou, x1x2, maxGoals: 18 });
  if (result.status !== 'ok') { invalid++; continue; }
  for (const market of ['AH', 'OU']) {
    const selected = result[market]?.selected;
    if (!selected) { invalid++; continue; }
    const commonLine = Number(q[market].line);
    const settled = settle(market, selected.side, Number(q.AH.line), commonLine,
      Number(r.actual_home_goals), Number(r.actual_away_goals), Number(selected.price));
    traceRows.push({ match_id: String(r.match_id), league: r.league, year: r.year, market,
      line: commonLine, side: selected.side, price: Number(selected.price), ...settled,
      probabilities: selected.five_state_probabilities, event_utc: q[market].event_utc,
      receipt_utc: q.X1X2.receipt_utc, kickoff_utc: r.kickoff_utc });
    marketRows[market].push({ ...settled, probs: selected.five_state_probabilities,
      year: String(r.kickoff_utc).slice(0, 4), event: q[market].event_utc,
      receipt: q.X1X2.receipt_utc, kickoff: r.kickoff_utc });
  }
}
const digest = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const markets = { AH: summarize(marketRows.AH), OU: summarize(marketRows.OU) };
let traceDigest = null;
if (args['trace-private']) {
  const tracePath = path.resolve(args['trace-private']);
  const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
  if (tracePath === repoRoot || tracePath.startsWith(repoRoot + path.sep)) throw new Error('fixture-level trace must remain outside the public repository');
  fs.mkdirSync(path.dirname(tracePath), { recursive: true, mode: 0o700 });
  fs.chmodSync(path.dirname(tracePath), 0o700);
  const bytes = traceRows.map(x => JSON.stringify(x)).join('\n') + '\n';
  fs.writeFileSync(tracePath, bytes, { mode: 0o600 });
  fs.chmodSync(tracePath, 0o600);
  traceDigest = digest(tracePath);
}
const report = {
  protocol: 'M5_MR1_V6_CROSS_MARKET_CORE_EXPANDED_CROWN_OOS_V1', generated_utc: new Date().toISOString(),
  source_repo_head: args['source-repo-head'],
  source_file_sha256: { 'src/v6-cross-market-core.js': digest(args['mr1-core']), 'src/market-implied-v2.js': digest(args['mr1-market-core']) },
  runner_sha256: digest(new URL(import.meta.url).pathname), input_private_batch_sha256: digest(args.input),
  private_trace_sha256: traceDigest,
  unique_input_fixtures: rows.length, invalid_model_rows: invalid, markets,
  method: 'Actual MR1 V6 cross-market core: fit a Poisson score distribution to Crown de-vigged 1X2 odds; independently select the higher expected-return side at the exact same Crown AH or OU line/prices; settle the AH handicap in the home-line frame, one 1U stake per fixture-market with Asian split-line settlement. Quote events are after the M3 prediction as-of and before kickoff; no results enter MR1 fit or selection.',
  limitations: [
    'Crown response receipts for these historical event quotes were obtained after kickoff; this is retrospective event-time OOS, not contemporaneously executable ROI.',
    'Cohort is the intersection with M3 strict OOS forecasts and valid pregame Crown AH, OU, and 1X2 quote events, not all source-union rows.',
    'Only aggregate outcomes are written to the public repository; fixture identifiers and odds remain in the authorized private archive.',
    'No production model, Telegram route, ledger, or trade gate was changed.',
  ],
};
fs.mkdirSync(path.dirname(path.resolve(args.report)), { recursive: true });
fs.writeFileSync(args.report, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ generated_utc: report.generated_utc, unique_input_fixtures: rows.length, invalid_model_rows: invalid, markets }));
