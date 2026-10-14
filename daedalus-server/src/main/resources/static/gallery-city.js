// SPDX-License-Identifier: MIT
import { CITY, visitorCity, normalizeCity, parcelAt, walkable, route, echoMarkers, newJournal, restoreJournal, observe, questProgress } from './gallery-city-core.js';

const $ = id => document.getElementById(id);
const canvas = $('city'), ctx = canvas.getContext('2d');
const params = new URLSearchParams(location.search);
const seedPattern = /^-?\d{1,19}$/;
let city = visitorCity('7'), journal = newJournal(city), frames = [], selected = null, activeFrame = null;
let mounted = [], path = [], follow = false, zoom = 1, camera = { x: 48, z: -80 };
let transform = { scale: 1, left: 0, top: 0 }, width = 800, height = 650, last = 0, saveElapsed = 0;
let generation = 0, dragging = null, toastTimer, saveDirty = false, worldInitialized = false;
const keys = new Set();
const palette = ['#afd5bf', '#b8ccec', '#ebc9ba', '#ddd2ed', '#e4d5b0', '#badbdb'];
$('seed').value = seedPattern.test(params.get('seed') || '') ? params.get('seed') : '7';

async function readJson(url, signal) {
  const response = await fetch(url, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Server read returned ${response.status}.`);
  return response.json();
}

function saveKey() { return `daedalus:gallery-expedition:v1:${journal.city}`; }
function readSave() {
  try { const raw = localStorage.getItem(saveKey()); if (raw && raw.length < 100000) journal = restoreJournal(city, JSON.parse(raw)); }
  catch { $('save-status').textContent = 'Device storage unavailable; this visit stays in memory.'; }
}
function save() {
  if (!saveDirty) return;
  try { localStorage.setItem(saveKey(), JSON.stringify(journal)); $('save-status').textContent = 'Visitor journal saved on this device.'; saveDirty = false; }
  catch { $('save-status').textContent = 'Could not save on this device. Current visit remains in memory.'; }
}
function toast(text) {
  $('toast').textContent = text; $('toast').classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('show'), 4200);
}
function touchJournal() { saveDirty = true; renderJournal(); }

function renderJournal() {
  const quests = questProgress(journal), done = quests.filter(q => q.done).length;
  $('quests').replaceChildren(...quests.map(q => {
    const row = document.createElement('div'); row.className = `quest${q.done ? ' done' : ''}`;
    const mark = document.createElement('span'); mark.className = 'quest-mark'; mark.textContent = q.done ? '✓' : '·';
    const content = document.createElement('div'), title = document.createElement('h3'), detail = document.createElement('p'), count = document.createElement('small');
    title.textContent = q.title; detail.textContent = q.text; count.textContent = `${q.count} / ${q.goal}`;
    content.append(title, detail, count); row.append(mark, content); return row;
  }));
  $('progress-fill').style.width = `${done / quests.length * 100}%`;
  $('progress-label').textContent = `${done} of ${quests.length} expedition objectives · ${journal.steps} steps`;
  $('location').textContent = nearestStreet() || 'Origin plaza';
}
function nearestStreet() {
  const street = city.streets.map(s => ({ s, distance: s.x1 === s.x2 ? Math.abs(journal.x - s.x1) : Math.abs(journal.z - s.z1) }))
    .sort((a, b) => a.distance - b.distance)[0];
  return street && street.distance < 4 ? street.s.name : null;
}

function fact(name, value) {
  const row = document.createElement('div'); row.className = 'fact';
  const label = document.createElement('span'), content = document.createElement('span');
  label.textContent = name; content.textContent = value; row.append(label, content); return row;
}
function inspect(p = null) {
  if (!p) {
    p = city.parcels.map(p => ({ p, d: Math.hypot(journal.x - Math.max(p.minX, Math.min(p.maxX, journal.x)),
      journal.z - Math.max(p.minZ, Math.min(p.maxZ, journal.z))) })).sort((a, b) => a.d - b.d).find(v => v.d < 8)?.p;
  }
  if (!p) { toast('Walk closer to a parcel edge to inspect it.'); return; }
  selected = p;
  $('parcel-title').textContent = p.address;
  $('parcel-detail').textContent = p.gallery ? 'A gallery preserves the old planet in maze art.' : 'An addressed parcel awaits its next chapter.';
  $('parcel-facts').replaceChildren(fact('Parcel', String(p.n)), fact('Footprint', `${p.maxX - p.minX + 1} × ${p.maxZ - p.minZ + 1} cubes`),
    fact('Height limit', `${p.height} cubes`), fact('Owner', city.source === 'server' ? p.owner || 'Unclaimed on server' : 'Not read from server'),
    fact('Builders', city.source === 'server' ? String(p.builders.length) : 'Unknown'), fact('Land source', city.source === 'server' ? city.worldId : 'Visitor draft'));
  const d = Math.hypot(journal.x - Math.max(p.minX, Math.min(p.maxX, journal.x)), journal.z - Math.max(p.minZ, Math.min(p.maxZ, journal.z)));
  if (d < 8 && !journal.parcels.includes(p.n)) { journal.parcels.push(p.n); touchJournal(); toast(`Recorded ${p.address}.`); }
  const candidates = frames.filter(f => f.x >= p.minX && f.x <= p.maxX && f.z >= p.minZ && f.z <= p.maxZ);
  activeFrame = candidates[0] || (city.source === 'draft' && p.gallery ? {
    id: `draft:${p.n}`, seed: (p.n * 7919 + 4242) % 1000000000, title: `Visitor study ${p.n + 1}`, generator: 'Maze study',
    image: `/api/v1/art/maze/${(p.n * 7919 + 4242) % 1000000000}.png`, draft: true } : null);
  $('artwork').replaceChildren(); $('view-art').hidden = !activeFrame;
  if (activeFrame) {
    const caption = document.createElement('p');
    caption.textContent = activeFrame.draft ? 'Visitor sample: this frame is not placed in a server parcel.' : `${activeFrame.title} · ${activeFrame.generator}`;
    $('artwork').append(caption);
    const image = document.createElement('img'); image.alt = `Maze artwork: ${activeFrame.title}`; image.loading = 'lazy';
    const imageUrl = `/api/v1/art/maze/${activeFrame.seed}.png`;
    image.src = imageUrl;
    image.addEventListener('error', () => { image.remove(); caption.textContent += ' · Artwork image unavailable from server.'; });
    $('artwork').append(image);
  }
}
function studyArt() {
  if (!activeFrame || !selected) return;
  const distance = Math.hypot(journal.x - Math.max(selected.minX, Math.min(selected.maxX, journal.x)),
    journal.z - Math.max(selected.minZ, Math.min(selected.maxZ, journal.z)));
  if (distance > 8) { toast('Walk closer to this gallery before recording its artwork.'); return; }
  const image = $('artwork').querySelector('img');
  if (!image || !image.complete || !image.naturalWidth) { toast('Wait for the server artwork image to load before studying it.'); return; }
  const id = String(activeFrame.id);
  if (!journal.art.includes(id)) { journal.art.push(id); touchJournal(); toast('A maze memory is recorded in your journal.'); }
  else toast('This artwork is already in your journal.');
}

let loadController;
async function loadCity() {
  const seed = $('seed').value.trim();
  if (!seedPattern.test(seed)) { toast('Use an integer seed of up to 19 digits.'); return; }
  let asLong;
  try { asLong = BigInt(seed); } catch { toast('Invalid seed.'); return; }
  if (asLong < -9223372036854775808n || asLong > 9223372036854775807n) { toast('Seed exceeds the realm’s signed 64-bit range.'); return; }
  const request = ++generation;
  loadController?.abort(); loadController = new AbortController();
  const controller = loadController, timeout = setTimeout(() => controller.abort(), 7000);
  $('load').disabled = true; $('connection').textContent = 'Reading the realm server…';
  save(); keys.clear(); path = []; frames = []; selected = null; activeFrame = null;
  $('artwork').replaceChildren(); $('parcel-facts').replaceChildren(); $('view-art').hidden = true;
  $('parcel-title').textContent = 'Explore the city'; $('parcel-detail').textContent = 'Walk to a parcel edge to inspect its address.';
  let next = visitorCity(seed), failure = '';
  try {
    const body = await readJson('/api/v1/worlds', controller.signal);
    mounted = Array.isArray(body.worlds) ? body.worlds.filter(w => w.style === 'GALLERY' && typeof w.id === 'string') : [];
    const previous = worldInitialized ? $('world').value : params.get('world');
    worldInitialized = true;
    $('world').replaceChildren(new Option('Visitor draft', ''), ...mounted.map(w => new Option(w.title || w.id, w.id)));
    const match = mounted.find(w => w.id === previous) || (previous === null ? mounted[0] : null);
    if (match) {
      $('world').value = match.id;
      const url = `/api/v1/world/${encodeURIComponent(match.id)}`;
      // JSON seeds outside safe integer precision are kept as an instance label, never used to mint or regenerate land.
      const instanceSeed = Number.isSafeInteger(match.seed) ? String(match.seed) : `instance:${match.id}`;
      next = normalizeCity(await readJson(`${url}/gallery`, controller.signal), instanceSeed);
      try {
        const art = await readJson(`${url}/art`, controller.signal);
        if (Array.isArray(art.art)) frames = art.art.filter(f => Number.isSafeInteger(f.seed) && f.seed >= 0 && f.seed < 1000000000 &&
          Number.isFinite(f.x) && Number.isFinite(f.z) && typeof f.id === 'string').slice(0, 4096);
      } catch { failure = ' · artwork list unavailable'; }
    } else failure = previous ? 'Requested Gallery world is not mounted.' : 'No Gallery world is mounted.';
  } catch (error) { failure = error.name === 'AbortError' ? 'Realm read timed out.' : 'Realm server unavailable.'; }
  finally { clearTimeout(timeout); }
  if (request !== generation) return;
  city = next; journal = newJournal(city); readSave(); camera = { x: city.padX, z: city.padZ }; zoom = 1; follow = false;
  $('connection').textContent = city.source === 'server' ? `Server city: ${city.worldId}${failure}` : `Visitor draft · ${failure}`;
  $('land-summary').textContent = city.source === 'server'
    ? 'Owner and builder labels are read from this realm instance. Gallery plot NFT minting still needs the plot deed integration.'
    : 'This local city is an exploration draft. Server ownership and plot NFT availability have not been read.';
  const url = new URL(location.href); url.searchParams.set('seed', seed);
  if (city.source === 'server') url.searchParams.set('world', city.worldId); else url.searchParams.delete('world');
  history.replaceState(null, '', url);
  $('load').disabled = false; renderJournal();
  if (city.source === 'draft') toast('Visitor draft loaded. Seeded gallery choices are illustrative; land ownership is unknown.');
}

function resize() {
  const box = canvas.getBoundingClientRect(), ratio = Math.min(window.devicePixelRatio || 1, 2);
  width = box.width; height = box.height; canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}
function screen(x, z) { return { x: transform.left + (x - CITY.minX) * transform.scale, y: transform.top + (z - CITY.minZ) * transform.scale }; }
function world(x, y) { return { x: (x - transform.left) / transform.scale + CITY.minX, z: (y - transform.top) / transform.scale + CITY.minZ }; }
function rectangle(x, z, w, d, color) {
  const p = screen(x, z); ctx.fillStyle = color; ctx.fillRect(p.x, p.y, w * transform.scale, d * transform.scale);
}
function circle(x, z, radius, color) {
  const p = screen(x, z); ctx.beginPath(); ctx.arc(p.x, p.y, radius * transform.scale, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
}
function label(x, z, text, color, size = 9) {
  const p = screen(x, z); ctx.font = `600 ${size}px system-ui`; ctx.fillStyle = color; ctx.textAlign = 'center'; ctx.fillText(text, p.x, p.y);
}
function draw(time) {
  ctx.clearRect(0, 0, width, height);
  const sky = ctx.createLinearGradient(0, 0, 0, height); sky.addColorStop(0, '#233848'); sky.addColorStop(1, '#101e2e');
  ctx.fillStyle = sky; ctx.fillRect(0, 0, width, height);
  const baseScale = Math.min((width - 64) / CITY.side, (height - 170) / CITY.side);
  transform.scale = Math.max(.8, baseScale) * zoom;
  const centre = follow ? journal : camera;
  transform.left = width / 2 - (centre.x - CITY.minX) * transform.scale;
  transform.top = height / 2 + 48 - (centre.z - CITY.minZ) * transform.scale;
  // A floating remnant below the city, drawn as original code-native silhouettes.
  rectangle(CITY.minX + 3, CITY.minZ + 6, CITY.side, CITY.side, '#0a1421');
  rectangle(CITY.minX, CITY.minZ, CITY.side, CITY.side, '#57757b');
  rectangle(CITY.minX, CITY.minZ, CITY.side, 2, '#7c989a');
  for (const s of city.streets) {
    if (s.x1 === s.x2) rectangle(s.x1 - 2, CITY.minZ, 4, CITY.side, '#344d58');
    else rectangle(CITY.minX, s.z1 - 2, CITY.side, 4, '#344d58');
  }
  for (const p of city.parcels) {
    const w = p.maxX - p.minX + 1, d = p.maxZ - p.minZ + 1, color = palette[p.n % palette.length];
    rectangle(p.minX, p.minZ, w, d, journal.parcels.includes(p.n) ? '#6c8e86' : '#5f7c7e');
    rectangle(p.minX + 3, p.minZ + 3, w - 3, d - 3, '#25374690');
    rectangle(p.minX + 2, p.minZ + 2, w - 4, d - 4, p.gallery ? '#e5e7df' : color);
    rectangle(p.minX + 2, p.maxZ - 2, w - 4, 1, p.gallery ? '#a5c4c6' : '#6f8998');
    rectangle(p.minX + 3, p.minZ + 3, w - 6, 1, '#ffffff45');
    if (p.gallery) {
      rectangle(p.minX + 4, p.minZ + 5, Math.max(2, w - 8), Math.max(2, d - 10), '#9dc4c8');
      rectangle(p.minX + 5, p.minZ + 5, Math.max(1, w - 10), 1, '#d8eced');
      const pos = screen((p.minX + p.maxX) / 2, p.maxZ - 1); ctx.fillStyle = '#c5864c'; ctx.fillRect(pos.x - 2, pos.y - 3, 4, 6);
    }
    if (selected?.n === p.n) {
      const point = screen(p.minX, p.minZ); ctx.strokeStyle = '#f8d69a'; ctx.lineWidth = 2;
      ctx.strokeRect(point.x, point.y, w * transform.scale, d * transform.scale);
    }
    if (transform.scale > 3) label((p.minX + p.maxX) / 2, p.minZ + 2, String(p.n + 1), '#142a36', 9);
  }
  rectangle(city.plazaMinX, city.plazaMinZ, city.plazaMaxX - city.plazaMinX + 1, city.plazaMaxZ - city.plazaMinZ + 1, '#bad6c6');
  rectangle(city.plazaMinX + 2, city.plazaMinZ + 2, city.plazaMaxX - city.plazaMinX - 3, city.plazaMaxZ - city.plazaMinZ - 3, '#8eb5a3');
  const spireX = (city.plazaMinX + city.plazaMaxX) / 2, spireZ = (city.plazaMinZ + city.plazaMaxZ) / 2 - 2;
  const spire = screen(spireX, spireZ), pulse = journal.returned ? 1.2 : .75;
  circle(spireX, spireZ, 4.5, journal.returned ? '#ead695' : '#9ce8dc');
  ctx.save(); ctx.translate(spire.x, spire.y); ctx.fillStyle = journal.returned ? '#fff1b1' : '#d2fff2';
  ctx.beginPath(); ctx.moveTo(0, -14 * pulse); ctx.lineTo(7, 0); ctx.lineTo(0, 8); ctx.lineTo(-7, 0); ctx.closePath(); ctx.fill(); ctx.restore();
  circle(city.padX, city.padZ + 5, 2.5, '#486c72'); label(city.padX, city.padZ + 5, '+', '#d9ecde', 13);
  if (transform.scale > 2) label(spireX, city.plazaMaxZ + 4, 'THE ORIGIN', '#d8ede0', 10);
  for (const marker of echoMarkers(city)) {
    const got = journal.echoes.includes(marker.id), p = screen(marker.x, marker.z);
    circle(marker.x, marker.z, 2, got ? '#284b48' : marker.color);
    ctx.strokeStyle = marker.color; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(p.x, p.y, (3 + Math.sin(time / 800) * .4) * transform.scale, 0, Math.PI * 2); ctx.stroke();
    if (transform.scale > 2) label(marker.x, marker.z - 4, got ? '✓' : marker.name.toUpperCase(), marker.color, 8);
  }
  if (path.length) {
    ctx.strokeStyle = '#ffe2a388'; ctx.lineWidth = Math.max(1, transform.scale / 2); ctx.beginPath();
    const at = screen(journal.x, journal.z); ctx.moveTo(at.x, at.y);
    for (const p of path) { const point = screen(p.x, p.z); ctx.lineTo(point.x, point.y); } ctx.stroke();
  }
  const player = screen(journal.x, journal.z); ctx.fillStyle = '#08222c88'; ctx.beginPath(); ctx.ellipse(player.x + 3, player.y + 5, 7, 3, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#f7d8a4'; ctx.fillRect(player.x - 3, player.y - 10, 6, 6); ctx.fillStyle = '#effaf4'; ctx.fillRect(player.x - 4, player.y - 4, 8, 8);
  ctx.fillStyle = '#467985'; ctx.fillRect(player.x - 4, player.y + 4, 3, 4); ctx.fillRect(player.x + 1, player.y + 4, 3, 4);
  if (journal.returned) { ctx.strokeStyle = '#ffdd97'; ctx.beginPath(); ctx.arc(player.x, player.y, 12, 0, Math.PI * 2); ctx.stroke(); }
}

let movementElapsed = 0;
function tick(time) {
  const delta = last ? Math.min((time - last) / 1000, .1) : 0; last = time;
  movementElapsed += delta; saveElapsed += delta;
  if (movementElapsed > .065) {
    movementElapsed = 0;
    let dx = 0, dz = 0;
    if (keys.has('north')) dz--;
    if (keys.has('south')) dz++;
    if (keys.has('west')) dx--;
    if (keys.has('east')) dx++;
    let next = null;
    if (dx || dz) { path = []; next = { x: journal.x + dx, z: journal.z + dz }; }
    else if (path.length) next = path.shift();
    if (next && walkable(city, next.x, next.z)) {
      journal.x = next.x; journal.z = next.z; journal.steps++; saveDirty = true;
      const events = observe(city, journal); if (events.length) { toast(events.join(' ')); renderJournal(); }
      if (journal.steps % 8 === 0) $('location').textContent = nearestStreet() || 'Parcel courtyard';
    }
  }
  if (saveElapsed > 2) { saveElapsed = 0; save(); }
  draw(time); requestAnimationFrame(tick);
}

const directions = { w: 'north', ArrowUp: 'north', s: 'south', ArrowDown: 'south', a: 'west', ArrowLeft: 'west', d: 'east', ArrowRight: 'east' };
document.addEventListener('keydown', event => {
  if (/^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(event.target.tagName) || event.ctrlKey || event.metaKey || event.altKey) return;
  const direction = directions[event.key] || directions[event.key.toLowerCase()];
  if (direction) { event.preventDefault(); keys.add(direction); }
  if (event.key.toLowerCase() === 'e' && !event.repeat) inspect();
});
document.addEventListener('keyup', event => { const dir = directions[event.key] || directions[event.key.toLowerCase()]; if (dir) keys.delete(dir); });
window.addEventListener('blur', () => { keys.clear(); save(); });
document.addEventListener('visibilitychange', () => { if (document.hidden) { keys.clear(); save(); } });
window.addEventListener('pagehide', save);
document.querySelectorAll('[data-move]').forEach(button => {
  button.addEventListener('pointerdown', event => { event.preventDefault(); button.setPointerCapture(event.pointerId); keys.add(button.dataset.move); });
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) button.addEventListener(type, () => keys.delete(button.dataset.move));
});
canvas.addEventListener('pointerdown', event => {
  canvas.focus(); canvas.setPointerCapture(event.pointerId);
  dragging = { x: event.offsetX, y: event.offsetY, originalX: camera.x, originalZ: camera.z, moved: false };
});
canvas.addEventListener('pointermove', event => {
  if (!dragging) return;
  const dx = event.offsetX - dragging.x, dy = event.offsetY - dragging.y;
  if (Math.hypot(dx, dy) > 7) dragging.moved = true;
  if (dragging.moved) { follow = false; camera.x = dragging.originalX - dx / transform.scale; camera.z = dragging.originalZ - dy / transform.scale; }
});
canvas.addEventListener('pointerup', event => {
  if (!dragging) return;
  if (!dragging.moved) {
    const destination = world(event.offsetX, event.offsetY);
    path = route(city, journal, destination);
    const p = parcelAt(city, destination.x, destination.z); if (p) inspect(p);
    if (!path.length && Math.hypot(destination.x - journal.x, destination.z - journal.z) > 3) toast('Choose a destination inside the city.');
  }
  dragging = null;
});
canvas.addEventListener('pointercancel', () => { dragging = null; });
canvas.addEventListener('wheel', event => { event.preventDefault(); zoom = Math.max(.75, Math.min(4, zoom * (event.deltaY > 0 ? .9 : 1.1))); }, { passive: false });
$('zoom-in').addEventListener('click', () => { zoom = Math.min(4, zoom * 1.25); });
$('zoom-out').addEventListener('click', () => { zoom = Math.max(.75, zoom / 1.25); });
$('follow').addEventListener('click', () => { follow = true; zoom = Math.max(zoom, 2); });
$('overview').addEventListener('click', () => { follow = false; zoom = 1; camera = { x: 48, z: -80 }; });
$('inspect').addEventListener('click', () => inspect()); $('view-art').addEventListener('click', studyArt);
$('load').addEventListener('click', loadCity);
$('seed').addEventListener('keydown', event => { if (event.key === 'Enter') loadCity(); });
$('reset').addEventListener('click', () => { journal = newJournal(city); path = []; touchJournal(); save(); toast('Started a fresh visitor journal for this city.'); });
new ResizeObserver(resize).observe(canvas); resize(); renderJournal(); requestAnimationFrame(tick); loadCity();
