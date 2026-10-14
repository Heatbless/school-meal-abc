// Host events are the only source of search decisions. This module renders them.
import {api, loadConfiguration, configurationNotice} from './configuration.js';
import {renderResults} from './results.js';
const $ = id => document.getElementById(id);
const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const categories = ['staple', 'protein', 'vegetable', 'fruit'];
const colors = {employed: '#b67914', onlooker: '#49766d', scout: '#896aad'};
const money = value => new Intl.NumberFormat('id-ID', {style: 'currency', currency: 'IDR', maximumFractionDigits: 0}).format(value);
const score = value => Number(value).toFixed(4);
const pct = value => `${(value * 100).toFixed(1)}%`;
const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
};
const svg = (tag, attributes, text) => {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
};
let configuration, runId, state, playing = false, busy = false, selected = 0;
let lastEvent, timer, operation = Promise.resolve(), eventLog = [], animatedSequence = null;
const component = id => configuration?.catalog.find(item => item.id === id);
const componentName = id => component(id)?.name ?? id ?? 'No substitution available';

function notice(id, text) { $(id).textContent = text; $(id).hidden = !text; }
function fail(error) { pause(); notice('error-message', error.message); }

function rememberRun(id) {
  try { id ? sessionStorage.setItem('bca.tab.run', id) : sessionStorage.removeItem('bca.tab.run'); }
  catch { /* Reset still cleans the current run if browser storage is unavailable. */ }
}
async function retirePreviousRun() {
  let previous;
  try { previous = sessionStorage.getItem('bca.tab.run'); } catch { return; }
  if (previous) {
    try { await api(`/api/runs/${previous}`, {method: 'DELETE'}); }
    catch (error) { if (error.status !== 404) throw error; }
    rememberRun(null);
  }
}
async function reloadConfiguration() {
  configuration = await loadConfiguration();
  notice('info-message', configurationNotice());
}
function summarizeConfiguration() {
  const p = configuration.planning, a = configuration.algorithm;
  $('scenario-summary').textContent = `${p.servings.join(' / ')} servings per day · ${money(p.budget_per_serving)} per serving · ${a.sources} sources · seed ${a.seed}.`;
}
function controls() {
  const terminal = ['completed', 'stopped'].includes(state?.status);
  $('play-button').disabled = !configuration || busy || playing || terminal;
  $('step-button').disabled = !configuration || busy || playing || terminal;
  $('pause-button').disabled = !playing;
  $('stop-button').disabled = !runId || terminal || busy;
  $('reset-button').disabled = busy;
  $('run-status').textContent = terminal ? `${state.status === 'completed' ? 'Completed' : 'Stopped'} · ${state.stop_reason?.replaceAll('_', ' ')}` : playing ? 'Playing · host advances each event' : runId ? 'Paused · no automatic advancement' : 'Ready to initialize';
}
async function ensureRun() {
  if (runId) return;
  const {catalog, planning, algorithm} = configuration;
  const result = await api('/api/runs', {method: 'POST', body: JSON.stringify({catalog, planning, algorithm})});
  runId = result.id; state = result.state;
  rememberRun(runId);
}
async function advance() {
  if (busy) return;
  busy = true; notice('error-message', ''); controls();
  try {
    await ensureRun();
    const result = await api(`/api/runs/${runId}/step`, {method: 'POST', body: JSON.stringify({steps: 1})});
    state = result.state;
    for (const event of result.events) {
      lastEvent = event;
      eventLog.unshift(event); eventLog = eventLog.slice(0, 80);
    }
    render();
    if (['completed', 'stopped'].includes(state.status)) pause();
  } finally { busy = false; controls(); }
}
function pause() { playing = false; clearTimeout(timer); controls(); }
function play() {
  if (playing || busy) return;
  playing = true; controls();
  const tick = async () => {
    if (!playing) return;
    operation = advance();
    try { await operation; } catch (error) { fail(error); }
    if (playing) timer = setTimeout(tick, [1200, 750, 400, 180, 55][Number($('speed-control').value) - 1]);
  };
  tick();
}
function selectSource(index) { selected = index; renderPopulation(); renderHive(false); }
function sourcePosition(index) {
  const count = state?.sources.length ?? configuration?.algorithm.sources ?? 16;
  const half = Math.ceil(count / 2), side = index < half ? 0 : 1;
  const local = side ? index - half : index;
  const columns = half > 16 ? 4 : 2;
  const rows = Math.ceil(half / columns);
  return {x: (side ? 530 : 70) + (local % columns) * (200 / Math.max(1, columns - 1)),
          y: 45 + Math.floor(local / columns) * (300 / Math.max(1, rows - 1))};
}
function renderHive(animate = true) {
  const nodes = $('source-nodes'); nodes.replaceChildren();
  for (const source of state?.sources ?? []) {
    const {x, y} = sourcePosition(source.index);
    const compact = state.sources.length > 32;
    const r = compact ? 20 : 28;
    const group = svg('g', {class: `source-node ${source.index === selected ? 'selected' : ''} ${source.index === lastEvent?.source ? 'active' : ''}`, transform: `translate(${x} ${y})`, tabindex: '0', role: 'button', 'aria-label': `Inspect source ${source.index + 1}, score ${score(source.score)}`});
    group.append(svg('polygon', {points: Array.from({length: 6}, (_, i) => `${Math.cos(Math.PI / 3 * i) * r},${Math.sin(Math.PI / 3 * i) * r}`).join(' ')}), svg('text', {'text-anchor': 'middle', y: compact ? 4 : 0}, `S${source.index + 1}`));
    if (source.index === lastEvent?.source) group.firstChild.style.stroke = colors[lastEvent.role] ?? colors.scout;
    if (!compact) group.append(svg('text', {'text-anchor': 'middle', y: 14, class: 'source-score'}, source.score.toFixed(2)));
    group.addEventListener('click', () => selectSource(source.index));
    group.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectSource(source.index); }});
    nodes.append(group);
  }
  if (!animate || (lastEvent && animatedSequence === lastEvent.seq)) return;
  animatedSequence = lastEvent?.seq ?? null;
  const bee = $('moving-bee'), path = $('flight-path');
  if (lastEvent?.source === undefined) { bee.setAttribute('hidden', ''); path.setAttribute('d', ''); return; }
  bee.removeAttribute('hidden');
  const target = sourcePosition(lastEvent.source);
  const start = lastEvent.role === 'employed' ? target : {x: 400, y: 188};
  const end = lastEvent.role === 'employed' ? {x: target.x + 35, y: target.y - 24} : target;
  path.setAttribute('stroke', colors[lastEvent.role] ?? colors.scout);
  path.setAttribute('d', `M${start.x} ${start.y} Q${(start.x + end.x) / 2} ${Math.min(start.y, end.y) - 35} ${end.x} ${end.y}`);
  bee.style.transition = 'none'; bee.style.transform = `translate(${start.x}px, ${start.y}px)`;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    bee.style.transition = ''; bee.style.transform = `translate(${end.x}px, ${end.y}px)`;
  }));
}
function menuWeek(schedule, evaluation) {
  const week = el('div', undefined, 'menu-week');
  for (let i = 0; i < 5; i++) {
    const day = el('article', undefined, 'day-card'); day.append(el('h4', days[i]));
    for (let j = 0; j < 4; j++) {
      const row = el('div', undefined, 'component-row'); row.append(el('span', categories[j]), document.createTextNode(componentName(schedule[i * 4 + j]))); day.append(row);
    }
    if (evaluation) {
      const d = evaluation.days[i];
      day.append(el('p', `${d.servings.toLocaleString()} servings · ${money(d.cost)}\n${d.nutrition.energy.toFixed(0)} kcal · ${d.nutrition.protein.toFixed(1)} g protein · ${d.nutrition.fiber.toFixed(1)} g fiber\n${d.workload.toFixed(0)} person-minutes`));
    }
    week.append(day);
  }
  return week;
}
function renderPopulation() {
  const roster = $('source-roster'); roster.replaceChildren();
  if (!state?.sources.length) { roster.append(el('p', 'The colony will appear after initialization.', 'muted')); $('selected-source').replaceChildren(); return; }
  for (const source of state.sources) {
    const card = el('button', undefined, `source-card ${source.index === selected ? 'selected' : ''}`);
    card.id = `source-${source.index}`;
    card.setAttribute('aria-pressed', source.index === selected ? 'true' : 'false');
    card.append(el('span', `SOURCE ${source.index + 1}`), el('strong', source.score.toFixed(3)), el('span', `${pct(source.probability)} current chance`), el('span', `${source.trials} / ${configuration.algorithm.limit} failures`));
    card.addEventListener('click', () => selectSource(source.index)); roster.append(card);
  }
  const source = state.sources[selected] ?? state.sources[0]; selected = source.index;
  $('selected-source').replaceChildren(el('h3', `Source ${selected + 1} · current five-day schedule`), menuWeek(source.schedule, source.evaluation));
}
function comparisonTable(before, candidate) {
  const table = el('table', undefined, 'comparison-table');
  const header = el('tr'); for (const text of ['Weighted term', 'Previous', 'Candidate']) header.append(el('th', text)); table.append(header);
  for (const key of Object.keys(candidate.contributions)) {
    const row = el('tr'); row.append(el('td', key), el('td', score(before.contributions[key])), el('td', score(candidate.contributions[key]))); table.append(row);
  }
  return table;
}
function renderDecision() {
  const target = $('decision-details'), event = lastEvent;
  $('probability-panel').hidden = event?.role !== 'onlooker';
  if (!event) { target.replaceChildren(el('p', 'Accepted improvements replace a schedule. Failed attempts increase its abandonment counter.', 'muted')); return; }
  const callout = $('event-callout'); callout.replaceChildren(el('strong', event.message));
  target.replaceChildren();
  if (event.type === 'attempt') {
    target.append(el('p', `${event.role} bee · source ${event.source + 1} · partner ${event.partner + 1}`, 'decision-kicker'));
    const mutation = el('div', undefined, 'mutation');
    mutation.append(el('span', event.position === null ? 'NO ELIGIBLE SUBSTITUTION' : `${days[Math.floor(event.position / 4)]} · ${categories[event.position % 4]}`), el('strong', componentName(event.previous_component)), el('b', '↓'), el('strong', componentName(event.candidate_component)));
    target.append(mutation);
    const metrics = el('div', undefined, 'decision-metrics');
    for (const [label, value] of [['Previous score', event.old_score], ['Candidate score', event.candidate_score]]) {
      const metric = el('div', label); metric.append(el('strong', score(value))); metrics.append(metric);
    }
    target.append(metrics, el('p', `${event.accepted ? 'Accepted · strictly better' : 'Rejected · source unchanged'} · failure count ${event.trials}`, `outcome ${event.accepted ? 'accepted' : 'rejected'}`));
    target.append(comparisonTable(event.previous_evaluation, event.candidate_evaluation));
    callout.append(el('p', event.accepted ? 'The candidate replaced its source and the failure counter reset to zero.' : 'The candidate did not improve the score. The original schedule remains; the failure counter increases.'));
  } else if (event.type === 'scout') {
    target.append(el('p', `Source ${event.source + 1} abandoned`, 'decision-kicker'), el('h3', 'A fresh random school week'), el('p', `${event.abandoned.trials} failed attempts reached the limit of ${configuration.algorithm.limit}. The source has been replaced; its failure counter is now zero.`, 'muted'), el('p', `Previous ${score(event.abandoned.score)} → replacement ${score(event.replacement.score)}`, 'outcome'));
    callout.append(el('p', 'Scout replacement explores a fresh schedule even if its score is worse. Independent best memory is preserved.'));
  } else {
    target.append(el('h3', event.type === 'initialized' ? 'A population of possibilities' : event.type === 'cycle' ? 'The best week stays in memory' : event.type === 'completed' ? 'Search complete' : 'Check for abandoned sources'), el('p', event.message, 'muted'));
    if (event.type === 'initialized') target.append(el('p', `${configuration.algorithm.sources} employed bees, ${configuration.algorithm.onlookers} onlooker attempts per cycle. Seed ${configuration.algorithm.seed}.`, 'muted'));
  }
  if (event.role === 'onlooker') {
    $('draw-value').textContent = `Random draw ${event.draw.toFixed(6)} → source ${event.source + 1}`;
    const bars = $('probability-bars'); bars.replaceChildren();
    const max = Math.max(...event.probabilities);
    event.probabilities.forEach((probability, index) => {
      const row = el('div', undefined, `probability-row ${index === event.source ? 'chosen' : ''}`), track = el('div', undefined, 'probability-track'), fill = el('span');
      fill.style.width = `${probability / max * 100}%`; track.append(fill);
      row.append(el('span', `S${index + 1}`), track, el('span', pct(probability))); bars.append(row);
    });
  }
}
function renderChart() {
  const chart = $('convergence-chart'); chart.replaceChildren();
  const history = state?.history ?? [];
  if (!history.length) { chart.append(svg('text', {x: 320, y: 100, 'text-anchor': 'middle'}, 'Initialize a run to track best-score progress.')); return; }
  const max = Math.max(...history.map(item => item.score)), min = Math.min(...history.map(item => item.score));
  const range = Math.max(max - min, 0.05), low = Math.max(0, min - range * .15), high = max + range * .15;
  const x = cycle => 55 + cycle / Math.max(1, history.at(-1).cycle) * 550;
  const y = value => 170 - (value - low) / (high - low) * 140;
  for (let i = 0; i < 4; i++) {
    const value = low + (high - low) * i / 3, pos = y(value);
    chart.append(svg('line', {x1: 55, x2: 605, y1: pos, y2: pos, stroke: '#e3e1d6'}), svg('text', {x: 46, y: pos + 3, 'text-anchor': 'end'}, value.toFixed(2)));
  }
  chart.append(svg('polyline', {points: history.map(item => `${x(item.cycle)},${y(item.score)}`).join(' '), fill: 'none', stroke: '#b67914', 'stroke-width': 2.5}));
  chart.append(svg('circle', {cx: x(history.at(-1).cycle), cy: y(history.at(-1).score), r: 4, fill: '#b67914'}));
  chart.append(svg('text', {x: 55, y: 190}, '0'), svg('text', {x: 605, y: 190, 'text-anchor': 'end'}, `Cycle ${history.at(-1).cycle}`));
}
function renderBest() {
  const target = $('best-result'), best = state?.best;
  if (!best) { target.replaceChildren(el('p', 'Your best weekly menu, target status, and school totals will appear here as the search runs.', 'muted')); $('target-status').textContent = 'Awaiting search'; return; }
  const evaluation = best.evaluation;
  $('target-status').textContent = evaluation.targets_met ? 'All configured targets met' : `${evaluation.violations.length} target violations`;
  renderResults(target, best, configuration);
}
function render() {
  $('best-score').textContent = state?.best ? score(state.best.evaluation.score) : '—';
  $('cycle-count').replaceChildren(document.createTextNode(`${state?.cycle ?? 0} `), el('small', `/ ${configuration.algorithm.max_cycles}`));
  $('evaluation-count').textContent = state?.evaluations ?? 0;
  $('phase-label').textContent = state?.phase ?? 'initialization';
  $('phase-badge').textContent = state?.phase ?? 'Ready';
  $('phase-badge').style.color = colors[state?.phase] ?? '';
  renderHive(); renderPopulation(); renderDecision(); renderChart(); renderBest();
  $('event-count').textContent = `${state?.sequence ?? 0} events`;
  $('event-log').replaceChildren();
  if (!eventLog.length) $('event-log').append(el('li', 'Waiting for the first host event.'));
  for (const event of eventLog) { const row = el('li'); row.append(el('span', `#${event.seq}`, 'event-seq'), el('span', event.message)); $('event-log').append(row); }
  controls();
}
$('play-button').addEventListener('click', play);
$('pause-button').addEventListener('click', pause);
$('step-button').addEventListener('click', () => { operation = advance(); operation.catch(fail); });
$('speed-control').addEventListener('input', () => { $('speed-value').textContent = `${$('speed-control').value}×`; });
$('stop-button').addEventListener('click', async () => {
  pause(); await operation.catch(() => {}); busy = true; controls();
  try { if (runId) state = await api(`/api/runs/${runId}/stop`, {method: 'POST'}); render(); }
  catch (error) { fail(error); } finally { busy = false; controls(); }
});
$('reset-button').addEventListener('click', async () => {
  pause(); await operation.catch(() => {}); busy = true; controls();
  try {
    if (runId) {
      try { await api(`/api/runs/${runId}`, {method: 'DELETE'}); }
      catch (error) { if (error.status !== 404) throw error; }
    }
    runId = null; state = null; lastEvent = null; eventLog = []; selected = 0; animatedSequence = null;
    rememberRun(null);
    await reloadConfiguration(); summarizeConfiguration();
    $('event-callout').replaceChildren(el('strong', 'A food source is a whole school week.'), el('p', 'Press Step to initialize the population with your current settings.'));
    notice('error-message', ''); render();
  } catch (error) { fail(error); } finally { busy = false; controls(); }
});
try { await retirePreviousRun(); await reloadConfiguration(); summarizeConfiguration(); render(); }
catch (error) { fail(error); }
// Keep controls accurately disabled during startup and when the host is unavailable.
controls();
