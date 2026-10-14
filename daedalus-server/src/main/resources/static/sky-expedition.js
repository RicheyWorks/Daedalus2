/* Original Shattered Planet visitor chapter. Existing server reads only. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const canvas = $('atlas'), ctx = canvas.getContext('2d');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const CAPS = { water: 12, food: 10, lift: 12 };
  const names = ['Copper Wake', 'Lantern Shoal', 'Mossbound Crown', 'The Listening Root', 'Rainward Hollow', 'Brass Orchard', 'Starfall Hearth', 'The Quiet Pier', 'Bloomwake Ridge'];
  let atlas = null, expedition = null, selected = null, plan = null, flight = null;
  let generation = 0, toastTimer = 0, points = [], gatePoints = [], width = 0, height = 0;
  let persistenceAvailable = true, frame = 0;

  function hash(value) { let h = 2166136261; for (const ch of String(value)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
  function random(seed) { let s = hash(seed); return () => { s += 0x6D2B79F5; let t = s; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const integer = (v, min, max) => Number.isSafeInteger(v) && v >= min && v <= max;
  const text = (v, fallback = '') => typeof v === 'string' ? v.slice(0, 200) : fallback;
  const escapedWorld = id => encodeURIComponent(id);
  const islandName = island => atlas.mode === 'draft' ? names[island.slot % names.length] : `Fragment ${island.slot}`;
  const storageKey = () => `daedalus.sky-expedition.v1:${atlas.mode}:${atlas.id}:${encodeURIComponent(atlas.seed)}`;

  function notify(message) { $('toast').textContent = message; $('toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('visible'), 4200); }
  function appendJournal(message) { expedition.journal.unshift({ at: new Date().toISOString(), text: message.slice(0, 260) }); expedition.journal = expedition.journal.slice(0, 36); }
  function persist() {
    try { localStorage.setItem(storageKey(), JSON.stringify(expedition)); persistenceAvailable = true; }
    catch (_) { persistenceAvailable = false; }
    $('save-status').textContent = persistenceAvailable ? 'Device-local journal saved separately for this source, world and seed. No server save or inventory write.' : 'Device storage is unavailable. This visitor expedition stays in memory for this page only.';
  }
  function newExpedition() {
    const slot = atlas.islands[0]?.slot ?? null;
    return { version: 1, mode: atlas.mode, world: atlas.id, seed: atlas.seed, slot, supplies: { water: 8, food: 6, lift: 8 }, morale: 100, visited: slot === null ? [] : [slot], surveyed: [], stocked: [], crystalRecorded: false, questRecorded: false, journal: [{ at: new Date().toISOString(), text: 'The visitor ark opens its atlas. Nothing here changes live land or inventory.' }] };
  }
  function restore() {
    const fresh = newExpedition();
    try {
      const raw = localStorage.getItem(storageKey());
      if (!raw || raw.length > 22000) return fresh;
      const s = JSON.parse(raw), slots = new Set(atlas.islands.map(i => i.slot));
      const validList = list => Array.isArray(list) && list.length <= 512 && list.every(n => integer(n, 0, 100000) && slots.has(n)) && new Set(list).size === list.length;
      if (!s || s.version !== 1 || s.mode !== atlas.mode || s.world !== atlas.id || s.seed !== atlas.seed || !slots.has(s.slot) || !s.supplies || !Object.entries(CAPS).every(([key, cap]) => integer(s.supplies[key], 0, cap)) || !integer(s.morale, 0, 100) || !validList(s.visited) || !validList(s.surveyed) || !validList(s.stocked) || !s.visited.includes(s.slot) || !s.surveyed.every(n => s.visited.includes(n)) || !s.stocked.every(n => s.visited.includes(n)) || typeof s.crystalRecorded !== 'boolean' || typeof s.questRecorded !== 'boolean' || (s.crystalRecorded && !s.surveyed.some(n => atlas.islands.find(i => i.slot === n).crystals > 0)) || (s.questRecorded && !(s.visited.length >= 3 && s.surveyed.length >= 2 && s.crystalRecorded)) || !Array.isArray(s.journal) || s.journal.length > 36 || !s.journal.every(j => j && typeof j.text === 'string' && j.text.length <= 260 && typeof j.at === 'string' && j.at.length <= 32 && Number.isFinite(Date.parse(j.at)))) {
        notify('This local journal does not match the atlas. A fresh visitor expedition is open.'); return fresh;
      }
      return { ...fresh, slot: s.slot, supplies: { ...s.supplies }, morale: s.morale, visited: [...s.visited], surveyed: [...s.surveyed], stocked: [...s.stocked], crystalRecorded: s.crystalRecorded, questRecorded: s.questRecorded, journal: s.journal.map(j => ({ at: j.at, text: j.text })) };
    } catch (_) { persistenceAvailable = false; return fresh; }
  }
  function draft(seed) {
    const r = random(seed), islands = names.map((_, slot) => ({
      slot, x: Math.round(Math.cos(slot * 2.399) * (slot ? 170 + slot * 42 : 0)), y: Math.round(r() * 80), z: Math.round(Math.sin(slot * 2.399) * (slot ? 170 + slot * 42 : 0)),
      seed: `${seed}:${slot}`, radius: 18 + Math.floor(r() * 12), columns: 700 + Math.floor(r() * 1000), blocks: 4000 + Math.floor(r() * 3000), trees: 9 + Math.floor(r() * 26), blossomTrees: Math.floor(r() * 7), pondColumns: slot % 3 ? 25 + Math.floor(r() * 50) : 0,
      streamLength: slot % 3 ? 12 : 0, waterfall: slot % 3 === 1, crystals: slot === 3 || slot === 6 ? 7 : 0, boulders: 3 + Math.floor(r() * 9), top: 8, bottom: -17, dockX: 0, dockY: 0, dockZ: 0, owner: '', builders: []
    }));
    return { mode: 'draft', id: 'visitor-draft', seed, title: 'The Copper Wake Archipelago', islands, gates: [], arks: [], mount: 'AIRSHIP', mountReady: false, now: 0, warnings: [] };
  }
  async function getJSON(path, signal) {
    const response = await fetch(path, { method: 'GET', credentials: 'same-origin', signal, headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? 'This server requires an authenticated session for that read.' : `Atlas read unavailable (${response.status}).`);
    const raw = await response.text();
    if (raw.length > 2000000) throw new Error('Atlas response exceeds this visitor page’s limit.');
    // Preserve numerical Java long seeds/revisions as text before JSON loses their precision.
    return JSON.parse(raw.replace(/("(?:seed|revision)"\s*:\s*)(-?\d+)(?=\s*[,}])/g, (match, prefix, value) => Number.isSafeInteger(Number(value)) ? match : `${prefix}"${value}"`));
  }
  function normalIsland(row) {
    if (!row || !integer(row.slot, 0, 100000) || !['x', 'y', 'z'].every(k => integer(row[k], -2147483648, 2147483647)) || !integer(row.radius, 1, 255)) return null;
    const out = { ...row, owner: text(row.owner), builders: Array.isArray(row.builders) ? row.builders.filter(v => typeof v === 'string').slice(0, 100).map(v => v.slice(0, 100)) : [] };
    for (const k of ['columns', 'blocks', 'trees', 'blossomTrees', 'pondColumns', 'streamLength', 'crystals', 'boulders']) out[k] = integer(row[k], 0, 2147483647) ? row[k] : 0;
    out.waterfall = row.waterfall === true; out.seed = typeof row.seed === 'string' || Number.isSafeInteger(row.seed) ? String(row.seed) : 'unknown';
    return out;
  }
  let readController = null;
  async function readServer(desired = '') {
    if (flight) return notify('Finish this local passage before changing the atlas.');
    const ticket = ++generation;
    readController?.abort(); readController = new AbortController();
    const controller = readController, timeout = setTimeout(() => controller.abort(), 8000);
    $('refresh').disabled = true; $('source-note').textContent = 'Reading existing mounted worlds, fragments, gates and fleet…';
    try {
      const directory = await getJSON('/api/v1/worlds', controller.signal);
      if (!Array.isArray(directory.worlds)) throw new Error('World directory schema is unavailable.');
      const worlds = directory.worlds.filter(w => w && w.style === 'SKY_ISLANDS' && /^[A-Za-z0-9_-]{1,64}$/.test(w.id));
      if (!worlds.length) throw new Error('No mounted Sky Islands world is available.');
      const world = worlds.find(w => w.id === desired) || worlds.find(w => w.id === 'world-zero') || worlds[0];
      const prefix = `/api/v1/world/${escapedWorld(world.id)}`;
      const values = await Promise.allSettled(['islands', 'gates', 'arks'].map(route => getJSON(`${prefix}/${route}`, controller.signal)));
      if (ticket !== generation) return;
      if (values[0].status !== 'fulfilled') throw values[0].reason;
      const data = values[0].value;
      if (data.worldId !== world.id || !Array.isArray(data.islands)) throw new Error('Island response belongs to an unknown world.');
      const seen = new Set(), islands = data.islands.slice(0, 512).map(normalIsland).filter(i => i && !seen.has(i.slot) && seen.add(i.slot));
      if (!islands.length) throw new Error('This mounted world has no readable fragments yet.');
      const gateData = values[1].status === 'fulfilled' ? values[1].value : null;
      const arkData = values[2].status === 'fulfilled' ? values[2].value : null;
      const gates = gateData?.worldId === world.id && Array.isArray(gateData.gates) ? gateData.gates.slice(0, 32).filter(g => g && integer(g.gate, 0, 1000) && ['x', 'y', 'z'].every(k => integer(g[k], -2147483648, 2147483647))).map(g => ({ ...g, toWorld: text(g.toWorld), toTitle: text(g.toTitle) })) : [];
      const arks = arkData?.worldId === world.id && Array.isArray(arkData.arks) ? arkData.arks.slice(0, 128).filter(a => a && typeof a.id === 'string').map(a => ({ ...a, id: text(a.id), name: text(a.name, 'Unnamed ark'), state: text(a.state), hold: Array.isArray(a.hold) ? a.hold.slice(0, 100) : [] })) : [];
      const warnings = [];
      if (values[1].status !== 'fulfilled') warnings.push('Gate read unavailable');
      else if (gateData?.worldId !== world.id || !Array.isArray(gateData.gates)) warnings.push('Gate response schema unavailable');
      if (values[2].status !== 'fulfilled') warnings.push('Fleet read unavailable');
      else if (arkData?.worldId !== world.id || !Array.isArray(arkData.arks)) warnings.push('Fleet response schema unavailable');
      if (data.islands.length > islands.length) warnings.push('Map shows up to 512 readable fragments');
      $('world-select').replaceChildren(...worlds.map(w => { const option = document.createElement('option'); option.value = w.id; option.textContent = text(w.title, w.id); return option; }));
      $('world-select').value = world.id;
      openAtlas({ mode: 'server', id: world.id, seed: String(world.seed ?? 'unknown'), title: text(world.title, world.id), islands, gates, arks, mount: text(gateData?.mount, 'AIRSHIP'), mountReady: gateData?.mountReady === true, now: arkData?.now, warnings });
      $('source-note').textContent = `Server snapshot: ${world.id} · ${islands.length} fragments. Visitor travel/supplies remain local.${warnings.length ? ' ' + warnings.join(' · ') + '.' : ''}`;
    } catch (error) {
      if (ticket !== generation) return;
      const reason = error.name === 'AbortError' ? 'Server read timed out or was replaced.' : error.message;
      if (atlas.mode !== 'draft') openAtlas(draft($('draft-seed').value.trim().slice(0, 64) || 'arkkeeper-7'));
      $('source-note').textContent = `${reason} Showing a seeded local visitor draft; these fragments and claims are not server land.`;
      $('world-select').replaceChildren(new Option('Server world unavailable', ''));
    } finally { clearTimeout(timeout); if (ticket === generation) $('refresh').disabled = false; }
  }
  function openAtlas(next) {
    atlas = next; expedition = restore(); selected = expedition.slot; plan = null; flight = null;
    $('mode-badge').textContent = atlas.mode === 'server' ? 'SERVER SNAPSHOT · LOCAL VISITOR' : 'LOCAL VISITOR DRAFT';
    $('mode-badge').classList.toggle('server', atlas.mode === 'server');
    $('atlas-title').textContent = atlas.title; resize(); render(); persist();
  }
  function currentIsland() { return atlas.islands.find(i => i.slot === expedition.slot); }
  function selectedIsland() { return atlas.islands.find(i => i.slot === selected); }
  function choose(slot) { if (flight) return; selected = slot; plan = null; render(); }
  function cost(from, to) { const distance = Math.hypot(to.x - from.x, to.y - from.y, to.z - from.z); return { water: Math.min(3, 1 + Math.floor(distance / 600)), food: 1, lift: Math.min(5, 1 + Math.floor(distance / 350)), distance: Math.round(distance) }; }
  function canPay(c) { return expedition.morale >= 20 && Object.keys(CAPS).every(k => expedition.supplies[k] >= c[k]); }
  function planPassage() {
    if (flight || selected === expedition.slot) return;
    plan = { from: expedition.slot, to: selected, ...cost(currentIsland(), selectedIsland()) }; render();
  }
  function sail() {
    if (!plan || flight || plan.from !== expedition.slot || !canPay(plan)) return notify('This visitor passage needs more camp supplies or a rest.');
    const destination = selectedIsland(), fromPoint = points.find(p => p.slot === plan.from), toPoint = points.find(p => p.slot === plan.to);
    if (!destination || !fromPoint || !toPoint) return;
    for (const key of Object.keys(CAPS)) expedition.supplies[key] -= plan[key];
    expedition.morale = Math.max(0, expedition.morale - 14);
    // Commit the local destination before animation, so reload cannot spend twice for one passage.
    const previousSlot = expedition.slot; expedition.slot = destination.slot;
    if (!expedition.visited.includes(destination.slot)) expedition.visited.push(destination.slot);
    appendJournal(`Local passage: Fragment ${previousSlot} → ${islandName(destination)}. No real ark was dispatched.`);
    flight = { from: previousSlot, to: destination.slot, start: performance.now(), duration: reducedMotion ? 1 : 1800 };
    plan = null; finishQuest(); persist(); render();
  }
  function restock() {
    const island = currentIsland();
    if (!island || flight || expedition.stocked.includes(island.slot)) return notify('This fragment’s one local camp cache has already been prepared.');
    const gains = { water: island.pondColumns > 0 || island.waterfall ? 4 : 1, food: island.trees > 0 ? 3 : 1, lift: island.crystals > 0 ? 4 : 2 };
    for (const key of Object.keys(CAPS)) expedition.supplies[key] = Math.min(CAPS[key], expedition.supplies[key] + gains[key]);
    expedition.stocked.push(island.slot); appendJournal(`Prepared one finite visitor camp cache at ${islandName(island)}. Habitat traits guided the draft; no live harvest.`);
    persist(); render(); notify('Visitor camp supplied. This cache can be prepared once per local expedition.');
  }
  function survey() {
    const island = currentIsland();
    if (!island || flight || expedition.surveyed.includes(island.slot)) return notify('This fragment is already in your local survey.');
    if (expedition.supplies.water < 1) return notify('A local survey needs one water ration.');
    expedition.supplies.water--; expedition.surveyed.push(island.slot);
    if (island.crystals > 0) expedition.crystalRecorded = true;
    appendJournal(`${islandName(island)}: ${island.pondColumns > 0 ? 'pond habitat' : 'dry ground'}, ${island.trees} trees${island.crystals ? ', crystal resonance recorded' : ''}. Distance shapes colonization; arrival never guarantees survival.`);
    finishQuest(); persist(); render();
  }
  function rest() {
    if (flight || expedition.morale === 100) return notify('Your visitor crew is already rested.');
    if (expedition.supplies.food < 1) return notify('Resting at a local camp needs one food ration.');
    expedition.supplies.food--; expedition.morale = Math.min(100, expedition.morale + 45);
    appendJournal('Shared a visitor camp meal and rested the crew. No server food was consumed.'); persist(); render();
  }
  function questFacts() { return [expedition.visited.length >= 3, expedition.surveyed.length >= 2, expedition.crystalRecorded]; }
  function finishQuest() {
    if (!expedition.questRecorded && questFacts().every(Boolean)) { expedition.questRecorded = true; appendJournal('The Thread of Living Lands is recorded: three berths, two habitat surveys and a crystal’s quiet resonance. Knowledge is the reward; no item or NFT is issued.'); notify('Chapter recorded. Your route carries a little more knowledge home.'); }
  }
  function addTrait(parent, label, value) { const div = document.createElement('div'), dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = label; dd.textContent = value; div.append(dt, dd); parent.append(div); }
  function render() {
    const island = selectedIsland(); if (!island) return;
    $('island-title').textContent = islandName(island);
    $('island-description').textContent = `${island.waterfall ? 'Water spills from a surviving piece of the old crust.' : island.crystals ? 'A seam of impact crystal catches the pale sunlight.' : island.trees ? 'Roots and canopy hold a little of the old world together.' : 'Bare stone waits for a lineage to take hold.'} ${atlas.mode === 'draft' ? 'Seeded visitor fiction.' : 'Traits from the existing island record.'}`;
    const traits = $('traits'); traits.replaceChildren();
    for (const [label, value] of [['Radius', `${island.radius} m`], ['Tree cover', island.trees], ['Pond columns', island.pondColumns], ['Crystals', island.crystals], ['Seed', island.seed.length > 20 ? island.seed.slice(0, 18) + '…' : island.seed], ['Berth', `slot ${island.slot}`]]) addTrait(traits, label, String(value));
    $('claim-note').textContent = atlas.mode === 'draft' ? 'Draft fragment: no server claim or deed.' : island.owner ? `Server claim: ${island.owner}. ${island.builders.length} named builders. This is a server claim record, not checked chain ownership.` : 'Server claim owner field is empty. This does not establish NFT availability or your building rights.';
    $('plan').disabled = !!flight || selected === expedition.slot;
    $('sail').disabled = !!flight || !plan || !canPay(plan);
    $('route-note').textContent = flight ? 'Your local visitor ark is following its plotted passage…' : plan ? `${plan.distance.toLocaleString()} m in this atlas · ${plan.water} water, ${plan.food} food, ${plan.lift} lift charges. ${canPay(plan) ? 'Local supplies are sufficient.' : 'Prepare camp supplies or rest before this passage.'}` : selected === expedition.slot ? 'You are at this visitor berth. Survey it or prepare its single local cache.' : 'Plan a local passage. Server arks, terrain and inventory stay authoritative and unchanged.';
    const link = $('live-island-link'); link.hidden = atlas.mode !== 'server'; link.href = `/realm.html?world=${escapedWorld(atlas.id)}#isle=${island.slot}`;
    $('position-label').textContent = `Visitor berth · ${islandName(currentIsland())} · crew ${expedition.morale}% rested`;
    $('supplies').replaceChildren(...Object.keys(CAPS).map(key => { const div = document.createElement('div'); div.className = 'supply'; const b = document.createElement('b'), small = document.createElement('small'); b.textContent = `${expedition.supplies[key]}/${CAPS[key]}`; small.textContent = key === 'lift' ? 'LIFT CHARGES' : key.toUpperCase(); div.append(b, small); return div; }));
    $('restock').disabled = !!flight || expedition.stocked.includes(expedition.slot);
    $('survey').disabled = !!flight || expedition.surveyed.includes(expedition.slot) || expedition.supplies.water < 1;
    $('rest').disabled = !!flight || expedition.morale === 100 || expedition.supplies.food < 1;
    $('new-journal').disabled = !!flight; $('draft-seed').disabled = !!flight; $('draft-form').querySelector('button').disabled = !!flight; $('world-select').disabled = !!flight;
    const list = $('island-list'); list.replaceChildren(...atlas.islands.map(i => { const button = document.createElement('button'); button.type = 'button'; button.textContent = `${expedition.visited.includes(i.slot) ? '✦ ' : ''}${islandName(i)}`; button.className = i.slot === selected ? 'selected' : ''; button.setAttribute('aria-pressed', String(i.slot === selected)); button.disabled = !!flight; button.addEventListener('click', () => choose(i.slot)); return button; }));
    const facts = questFacts(), descriptions = [`Keep a route between three fragments (${Math.min(3, expedition.visited.length)}/3)`, `Read two habitats without disturbing their life (${Math.min(2, expedition.surveyed.length)}/2)`, 'Record a crystal-bearing fragment’s resonance'];
    $('objectives').replaceChildren(...descriptions.map((description, i) => { const li = document.createElement('li'); li.textContent = description; li.className = facts[i] ? 'complete' : ''; return li; }));
    $('quest-count').textContent = `${facts.filter(Boolean).length} / 3`;
    $('quest-note').textContent = expedition.questRecorded ? 'Chapter recorded locally. This carries knowledge, with no live quest reward, item, currency or NFT.' : atlas.islands.length < 3 || !atlas.islands.some(i => i.crystals > 0) ? 'This snapshot does not contain every chapter destination. Explore what exists, or grow a separate visitor draft; no missing server land is invented.' : 'Visitor objectives only. Find crystal-bearing ground, then survey it. No server progression changes.';
    $('journal').replaceChildren(...expedition.journal.map(j => { const li = document.createElement('li'), time = document.createElement('time'); time.dateTime = j.at; time.textContent = new Date(j.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); const span = document.createElement('span'); span.textContent = j.text; li.append(time, span); return li; }));
    renderGates(); renderFleet();
  }
  function renderGates() {
    const host = $('gates'); host.replaceChildren();
    if (!atlas.gates.length) { const p = document.createElement('p'); p.className = 'fineprint'; p.textContent = atlas.mode === 'draft' ? 'A pale rainbow hints at the next realm. This draft does not invent a live gate or destination.' : atlas.warnings.some(w => w.startsWith('Gate')) ? 'Gate data was unavailable; no destination is inferred.' : 'No paired gate is present in this server snapshot.'; host.append(p); return; }
    for (const gate of atlas.gates) {
      const card = document.createElement('div'); card.className = 'gate-card'; const title = document.createElement('strong'), note = document.createElement('p'); title.textContent = `Gate ${gate.gate} · ${gate.toTitle || gate.toWorld || 'Unspecified destination'}`; note.textContent = `Past the rainbow · ${atlas.mount}${atlas.mountReady ? ' mount enabled in the snapshot' : ' mount readiness not established'}. Opens the existing realm page; this visitor preview issues no travel command.`;
      card.append(title, note);
      if (/^[A-Za-z0-9_-]{1,64}$/.test(gate.toWorld)) { const a = document.createElement('a'); a.href = `/realm.html?world=${escapedWorld(gate.toWorld)}`; a.textContent = 'Open destination page →'; card.append(a); }
      host.append(card);
    }
  }
  function renderFleet() {
    const host = $('fleet'); host.replaceChildren();
    if (!atlas.arks.length) { const p = document.createElement('p'); p.className = 'fineprint'; p.textContent = atlas.mode === 'draft' ? 'Copper Wake is your fictional visitor ark. No server vessel, animal hold or voyage is created.' : atlas.warnings.some(w => w.startsWith('Fleet')) ? 'Fleet read unavailable; local traveler is independent.' : 'No arks in this server snapshot.'; host.append(p); return; }
    for (const ark of atlas.arks) {
      const card = document.createElement('div'); card.className = 'ark-card'; const title = document.createElement('strong'), position = document.createElement('p'), hold = document.createElement('p'); title.textContent = ark.name;
      position.textContent = ark.state === 'SAILING' ? `Observed sailing · ${ark.fromSlot} → ${ark.toSlot}` : `Observed ${ark.state || 'unknown state'} · berth ${integer(ark.slot, -1, 100000) ? ark.slot : '?'}`;
      const populated = ark.hold.filter(row => row && typeof row.name === 'string' && Number.isFinite(row.count) && row.count > 0);
      hold.textContent = populated.length ? `Hold: ${populated.slice(0, 3).map(row => `${text(row.name)} ×${Math.round(row.count * 10) / 10}`).join(', ')}${populated.length > 3 ? ` +${populated.length - 3} kinds` : ''}` : 'Hold: no positive cargo count in this snapshot.';
      card.append(title, position, hold); host.append(card);
    }
  }
  function resize() {
    width = canvas.clientWidth; height = canvas.clientHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2); canvas.width = Math.max(1, Math.round(width * dpr)); canvas.height = Math.max(1, Math.round(height * dpr)); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); project();
  }
  function project() {
    if (!atlas) return;
    const rows = [...atlas.islands, ...atlas.gates], xs = rows.map(i => i.x), zs = rows.map(i => i.z);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minZ = Math.min(...zs), maxZ = Math.max(...zs);
    const scale = Math.min(Math.max(1, width - 150) / Math.max(240, maxX - minX), Math.max(1, height - 165) / Math.max(240, (maxZ - minZ) * .68));
    const midX = (minX + maxX) / 2, midZ = (minZ + maxZ) / 2;
    const point = row => ({ ...row, sx: width / 2 + (row.x - midX) * scale, sy: height / 2 + (row.z - midZ) * scale * .68 - 12, size: Math.max(13, Math.min(35, row.radius ? row.radius * scale * .8 : 20)) });
    points = atlas.islands.map(point); gatePoints = atlas.gates.map(point);
  }
  function poly(vertices, fill, stroke = null) { ctx.beginPath(); vertices.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); if (stroke) { ctx.strokeStyle = stroke; ctx.stroke(); } }
  function drawIsland(p, seconds) {
    const x = p.sx, y = p.sy + (reducedMotion ? 0 : Math.sin(seconds * .45 + p.slot) * 3), s = p.size;
    const top = [[x-s,y],[x-s*.5,y-s*.4],[x+s*.6,y-s*.35],[x+s,y],[x+s*.45,y+s*.38],[x-s*.55,y+s*.35]];
    poly([[x-s,y],[x-s*.55,y+s*.35],[x+s*.45,y+s*.38],[x+s,y],[x+s*.4,y+s*1.05],[x-s*.2,y+s*1.35],[x-s*.75,y+s*.75]], '#263940');
    poly([[x-s*.55,y+s*.35],[x+s*.45,y+s*.38],[x+s*.4,y+s*1.05],[x-s*.2,y+s*1.35]], '#17313d');
    poly(top, p.pondColumns > 0 ? '#4d8775' : p.crystals > 0 ? '#547679' : '#697f58', p.slot === selected ? '#e6b66a' : '#7daa8a');
    if (p.pondColumns > 0) { ctx.fillStyle = '#79cfc4'; ctx.beginPath(); ctx.ellipse(x+s*.16,y+s*.05,s*.27,s*.12,-.2,0,Math.PI*2); ctx.fill(); }
    const r = random(p.seed);
    for (let n = 0; n < Math.min(7,p.trees); n++) { const tx = x + (r()-.5)*s*1.35, ty = y+(r()-.5)*s*.4; ctx.fillStyle='#674f3d'; ctx.fillRect(tx-1,ty-10,2,12); poly([[tx-5,ty-7],[tx,ty-18],[tx+5,ty-7]],n%3===0?'#a1bc86':'#355e4d'); }
    if (p.crystals > 0) poly([[x+s*.52,y-1],[x+s*.44,y-17],[x+s*.64,y-22],[x+s*.74,y-8]],'#96d6e5','#ccf4f1');
    if (p.waterfall) { ctx.strokeStyle='#80d5d277'; ctx.lineWidth=3; ctx.beginPath(); ctx.moveTo(x+s*.5,y+s*.24); ctx.bezierCurveTo(x+s*.6,y+s*.8,x+s*.45,y+s*1.35,x+s*.48,y+s*1.8); ctx.stroke(); ctx.lineWidth=1; }
    if (expedition.visited.includes(p.slot)) { ctx.strokeStyle=p.slot===expedition.slot?'#e6b66a':'#7ad4bf70'; ctx.setLineDash([3,5]); ctx.beginPath(); ctx.ellipse(x,y+s*.07,s+8,s*.58,0,0,Math.PI*2); ctx.stroke(); ctx.setLineDash([]); }
    if (points.length < 30 || p.slot === selected || p.slot === expedition.slot) { ctx.font='10px system-ui'; ctx.textAlign='center'; ctx.fillStyle=p.slot===selected?'#e6b66a':'#b7c5c7'; ctx.fillText(islandName(p),x,y+s*1.8+15); }
  }
  function drawArk(x,y) { poly([[x-13,y],[x+14,y],[x+8,y+7],[x-8,y+7]],'#c29a62','#e6b66a'); ctx.strokeStyle='#d1ad75'; ctx.beginPath(); ctx.moveTo(x,y);ctx.lineTo(x,y-20);ctx.stroke();poly([[x+1,y-19],[x+11,y-8],[x+1,y-5]],'#e4d5ad');ctx.fillStyle='#7ad4bf';ctx.beginPath();ctx.arc(x,y+12,3,0,Math.PI*2);ctx.fill(); }
  function draw(timestamp) {
    frame = requestAnimationFrame(draw); if (!atlas || document.hidden || !width || !height) return;
    const seconds = timestamp/1000; ctx.clearRect(0,0,width,height);
    const background=ctx.createLinearGradient(0,0,0,height);background.addColorStop(0,'#082335');background.addColorStop(1,'#0b2937');ctx.fillStyle=background;ctx.fillRect(0,0,width,height);
    ctx.strokeStyle='#85b8b809'; ctx.beginPath(); for(let x=20;x<width;x+=40){ctx.moveTo(x,0);ctx.lineTo(x,height);}for(let y=20;y<height;y+=40){ctx.moveTo(0,y);ctx.lineTo(width,y);}ctx.stroke();
    const r=random(atlas.seed);for(let n=0;n<65;n++){const x=r()*width,y=r()*height;ctx.fillStyle=n%9?'#9dcdd72e':'#e6b66a66';ctx.fillRect(x,y,n%9?1:2,n%9?1:2);}
    ctx.strokeStyle='#69958e18';ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(width*.52,height*.58,width*.47,height*.45,-.12,0,Math.PI*2);ctx.stroke();
    for(let n=0;n<4;n++){const x=((n*237+(reducedMotion?0:seconds*6))%(width+180))-90,y=55+n*83;ctx.fillStyle='#b1d4d80b';ctx.beginPath();ctx.ellipse(x,y,65,15,0,0,Math.PI*2);ctx.fill();}
    const route=flight||plan;if(route){const a=points.find(p=>p.slot===route.from),b=points.find(p=>p.slot===route.to);if(a&&b){ctx.strokeStyle='#7ad4bf';ctx.setLineDash([5,6]);ctx.beginPath();ctx.moveTo(a.sx,a.sy);ctx.lineTo(b.sx,b.sy);ctx.stroke();ctx.setLineDash([]);}}
    [...points].sort((a,b)=>a.sy-b.sy).forEach(p=>drawIsland(p,seconds));
    for(const p of gatePoints){ctx.lineWidth=3;['#db8797','#e6b66a','#a1c993','#73bbcc'].forEach((color,i)=>{ctx.strokeStyle=color;ctx.beginPath();ctx.arc(p.sx,p.sy,18+i*4,Math.PI,0);ctx.stroke();});ctx.lineWidth=1;ctx.fillStyle='#d0dddd';ctx.textAlign='center';ctx.font='10px system-ui';ctx.fillText(`Gate ${p.gate}`,p.sx,p.sy+17);}
    if(!gatePoints.length&&atlas.mode==='draft'){ctx.strokeStyle='#e6b66a26';ctx.beginPath();ctx.arc(width-70,70,40,Math.PI,0);ctx.stroke();}
    let berth=points.find(p=>p.slot===expedition.slot);
    if(flight){const a=points.find(p=>p.slot===flight.from),b=points.find(p=>p.slot===flight.to),t=Math.min(1,(timestamp-flight.start)/flight.duration),ease=t*t*(3-2*t);if(a&&b)berth={sx:a.sx+(b.sx-a.sx)*ease,sy:a.sy+(b.sy-a.sy)*ease-Math.sin(t*Math.PI)*25};if(t===1){flight=null;render();}}
    if(berth)drawArk(berth.sx,berth.sy-32);
    ctx.fillStyle='#e6b66a88';ctx.textAlign='left';ctx.font='9px system-ui';ctx.fillText(atlas.mode==='draft'?'LOCAL VISITOR DRAFT · NOT SERVER GEOMETRY':'READ-ONLY SERVER CHART · LOCAL VISITOR ARK',18,height-18);
  }
  canvas.addEventListener('click',event=>{if(flight)return;const box=canvas.getBoundingClientRect(),x=event.clientX-box.left,y=event.clientY-box.top;const nearest=[...points].sort((a,b)=>Math.hypot(a.sx-x,a.sy-y)-Math.hypot(b.sx-x,b.sy-y))[0];if(nearest&&Math.hypot(nearest.sx-x,nearest.sy-y)<Math.max(30,nearest.size*1.4))choose(nearest.slot);});
  $('plan').addEventListener('click',planPassage);$('sail').addEventListener('click',sail);$('restock').addEventListener('click',restock);$('survey').addEventListener('click',survey);$('rest').addEventListener('click',rest);
  $('refresh').addEventListener('click',()=>readServer($('world-select').value));
  $('world-select').addEventListener('change',()=>readServer($('world-select').value));
  $('draft-form').addEventListener('submit',event=>{event.preventDefault();if(flight)return;generation++;readController?.abort();$('refresh').disabled=false;const seed=$('draft-seed').value.trim().slice(0,64)||'arkkeeper-7';$('draft-seed').value=seed;openAtlas(draft(seed));$('source-note').textContent='Seeded local visitor draft. Fragments, camp supplies and discoveries are device-local fiction; no server land is created.';});
  $('new-journal').addEventListener('click',()=>{if(flight)return;if(!window.confirm('Restart only this device’s visitor journal and supplies for the current atlas? Live game data is unaffected.'))return;expedition=newExpedition();selected=expedition.slot;plan=null;persist();render();notify('A fresh local expedition is open for this atlas.');});
  window.addEventListener('resize',resize);if(window.ResizeObserver)new ResizeObserver(resize).observe(canvas);
  window.addEventListener('pagehide',()=>{cancelAnimationFrame(frame);readController?.abort();});
  window.addEventListener('pageshow',event=>{if(event.persisted){resize();frame=requestAnimationFrame(draw);}});
  openAtlas(draft('arkkeeper-7'));frame=requestAnimationFrame(draw);
  const requested=new URLSearchParams(location.search).get('world');readServer(requested&&/^[A-Za-z0-9_-]{1,64}$/.test(requested)?requested:'');
})();
