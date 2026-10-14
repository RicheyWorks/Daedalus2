/* SPDX-License-Identifier: MIT
 * Browser survey/adventure over the authoritative DRR 1 realm spec. This is not
 * the native C++ party engine, a wallet client or a deed/ownership service.
 */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const screen = $('screen'), ctx = screen.getContext('2d');
  const atlas = $('atlas'), atlasCtx = atlas.getContext('2d');
  const TILE = 16, COLS = 31, ROWS = 23, BAG_SLOTS = 12;
  const WALKABLE = new Set('.Th:=%,bD><VKAO|_');
  const TILES = new Set('.T~h^:=%,#bDLC><VKAOQ|-_W');
  const DIRECTIONS = [[0, -1], [1, 0], [0, 1], [-1, 0]];
  const ZONE_COLORS = ['#80c797', '#d0c970', '#d89278', '#b6a0de', '#90b594', '#8bbbb7', '#797dad', '#a485b9', '#c886a7'];
  const TIER_KEYS = ['', 'BRONZE_KEY', 'SILVER_KEY', 'STAR_KEY'];
  const TIER_NAMES = ['', 'bronze', 'silver', 'star'];
  const TILE_NAMES = {'.': 'meadow', T: 'forest', '~': 'sea', h: 'hills', '^': 'mountain', ':': 'shore', '=': 'bridge', '%': 'swamp', ',': 'cobbles', '#': 'stone', b: 'brick floor', D: 'door', L: 'locked door', C: 'chest', '>': 'stairs down', '<': 'stairs up', V: 'town gate', K: 'castle gate', A: 'cave mouth', O: 'portal', Q: 'throne', '|': 'carpet', '-': 'counter', _: 'cave floor', W: 'cave wall'};
  let realm = null, state = null, fingerprint = '', provenance = '', loading = false;
  let facing = [0, -1], trail = [], route = [], routeGoal = null, routeTimer = null;
  let camera = {x: 0, y: 0}, battle = null, saveTimer = null, request = null;
  let held = null, heldTimer = null, lastLog = '', lastZone = '', frame = 0;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  function number(token, min = 0, max = 1000000) {
    if (!/^-?\d+$/.test(token || '')) throw new Error('Invalid numeric field.');
    const n = Number(token);
    if (!Number.isSafeInteger(n) || n < min || n > max) throw new Error('Numeric field outside supported range.');
    return n;
  }
  function seedValue(value) {
    if (!/^-?\d{1,19}$/.test(String(value).trim())) throw new Error('Use a whole-number portal seed.');
    const n = BigInt(String(value).trim());
    if (n < -9223372036854775808n || n > 9223372036854775807n) throw new Error('Seed must fit a signed 64-bit integer.');
    return n.toString();
  }
  function identifier(value) {
    if (!/^[A-Z0-9_]{1,40}$/.test(value || '')) throw new Error('Invalid realm identifier.');
    return value;
  }
  const key = p => `${p.map},${p.x},${p.y}`;
  const cellKey = (x, y) => `${x},${y}`;
  const samePlace = (a, b) => a.map === b.map && a.x === b.x && a.y === b.y;
  function place(fields, at = 1) {
    return {map: identifier(fields[at]), x: number(fields[at + 1], 0, 127), y: number(fields[at + 2], 0, 127)};
  }
  function rest(fields, start) { return fields.slice(start).join(' ').slice(0, 2000); }
  function unique(map, id, value) {
    if (map.has(id)) throw new Error(`Duplicate realm record: ${id}.`);
    map.set(id, value);
  }
  function color(value) {
    if (!/^[0-9a-fA-F]{1,6}$/.test(value || '')) throw new Error('Invalid palette color.');
    return `#${value.padStart(6, '0')}`;
  }

  /** DRR 1 is line-oriented, with free text only after the fixed fields. */
  function parseSpec(text) {
    if (text.length > 512000) throw new Error('Realm spec exceeds the browser survey budget.');
    const lines = text.replace(/^\uFEFF/, '').replace(/\r/g, '').split('\n');
    if (lines[0].trim() !== 'DRR 1') throw new Error('Expected a DRR 1 realm spec.');
    const r = {seed: null, name: '', maps: new Map(), items: new Map(), monsters: new Map(), zones: new Map(), shops: new Map(), links: new Map(), chests: new Map(), doors: new Map(), npcs: new Map(), bosses: new Map(), news: [], spawn: null, portal: null};
    for (let i = 1; i < lines.length; i++) {
      if (!lines[i].trim()) continue;
      const f = lines[i].trim().split(/\s+/), type = f[0];
      try {
        switch (type) {
          case 'seed': if (r.seed !== null) throw new Error('Duplicate seed.'); r.seed = seedValue(f[1]); break;
          case 'name': r.name = rest(f, 1); break;
          case 'item': {
            if (!['USE', 'KEY', 'WEAPON', 'ARMOR', 'TREASURE'].includes(f[2])) throw new Error('Unknown item kind.');
            const id = identifier(f[1]); unique(r.items, id, {id, kind: f[2], price: number(f[3]), power: number(f[4]), title: rest(f, 5)}); break;
          }
          case 'monster': {
            const id = identifier(f[1]); unique(r.monsters, id, {id, shape: number(f[2], 0, 7), body: color(f[3]), accent: color(f[4]), hp: number(f[5], 1), atk: number(f[6]), def: number(f[7]), agi: number(f[8]), exp: number(f[9]), gold: number(f[10]), rarity: identifier(f[11]), traits: f[12] === '-' ? [] : f[12].split(','), drop: f[13] === '-' ? null : identifier(f[13]), dropOneIn: number(f[14]), title: rest(f, 15)}); break;
          }
          case 'map': {
            const m = {id: identifier(f[1]), w: number(f[2], 1, 128), h: number(f[3], 1, 128), music: identifier(f[4]), dark: number(f[5], 0, 1) === 1, exit: f[6] === '-' ? null : place(f, 6), title: rest(f, 9), rows: [], zones: []};
            let ended = false;
            for (++i; i < lines.length; i++) {
              const l = lines[i];
              if (l.trim() === 'end') { ended = true; break; }
              if (l.startsWith('row ')) {
                const row = l.slice(4);
                if (row.length !== m.w || [...row].some(c => !TILES.has(c))) throw new Error(`Bad tiles in map ${m.id}.`);
                m.rows.push(row);
              } else if (l.startsWith('zrow ')) {
                const row = l.slice(5);
                if (row.length !== m.w || !/^[.0-9A-Za-z]+$/.test(row)) throw new Error(`Bad zone row in map ${m.id}.`);
                m.zones.push(row);
              } else throw new Error(`Unexpected map line in ${m.id}.`);
            }
            if (!ended || m.rows.length !== m.h || (m.zones.length && m.zones.length !== m.h)) throw new Error(`Incomplete map ${m.id}.`);
            if (!m.zones.length) m.zones = Array(m.h).fill('.'.repeat(m.w));
            if (r.maps.size >= 16) throw new Error('Too many maps.');
            unique(r.maps, m.id, m); break;
          }
          case 'zone': {
            if (!/^[0-9A-Za-z]$/.test(f[1])) throw new Error('Invalid zone identifier.');
            const entries = f.slice(3).map(e => { const a = e.split(':'); if (a.length !== 4) throw new Error('Bad encounter table.'); const entry = {monster: identifier(a[0]), weight: number(a[1], 1), min: number(a[2], 1, 3), max: number(a[3], 1, 3)}; if (entry.min > entry.max) throw new Error('Bad group range.'); return entry; });
            if (!entries.length) throw new Error('Empty encounter zone.');
            unique(r.zones, f[1], {id: f[1], rate: number(f[2], 2), entries}); break;
          }
          case 'link': { const from = place(f), to = place(f, 4); unique(r.links, key(from), {from, to}); break; }
          case 'chest': { const at = place(f); if (!['GOLD', 'ITEM', 'MIMIC'].includes(f[4])) throw new Error('Unknown chest kind.'); unique(r.chests, key(at), {at, kind: f[4], value: f[4] === 'GOLD' ? number(f[5]) : identifier(f[5])}); break; }
          case 'door': { const at = place(f); unique(r.doors, key(at), {at, tier: number(f[4], 1, 3)}); break; }
          case 'npc': {
            const at = place(f); if (!['TALK', 'NEWS', 'INN', 'SHOP', 'QUEEN'].includes(f[10])) throw new Error('Unknown NPC role.');
            unique(r.npcs, key(at), {at, wanders: number(f[4], 0, 1) === 1, look: f.slice(5, 10).map(color), role: f[10], price: number(f[11]), shop: f[12] === '-' ? null : identifier(f[12]), lines: rest(f, 13).split('/')}); break;
          }
          case 'shop': unique(r.shops, identifier(f[1]), f.slice(2).map(identifier)); break;
          case 'boss': { const at = place(f); unique(r.bosses, key(at), {at, monster: identifier(f[4])}); break; }
          case 'spawn': if (r.spawn) throw new Error('Duplicate spawn.'); r.spawn = place(f); break;
          case 'portal': if (r.portal) throw new Error('Duplicate portal.'); r.portal = place(f); break;
          case 'news': if (r.news.length < 100) r.news.push(rest(f, 1)); break;
          default: throw new Error(`Unknown DRR fact '${type}'.`);
        }
      } catch (error) { throw new Error(`DRR line ${i + 1}: ${error.message}`); }
    }
    if (!r.spawn || !r.portal || !r.maps.size || !r.name || r.seed === null) throw new Error('Realm is missing its seed, name, maps or portal.');
    const assertPlace = p => { const m = r.maps.get(p.map); if (!m || p.x >= m.w || p.y >= m.h) throw new Error(`Invalid place ${key(p)}.`); };
    assertPlace(r.spawn); assertPlace(r.portal);
    if (r.maps.get(r.portal.map).rows[r.portal.y][r.portal.x] !== 'O') throw new Error('Portal record does not match its map tile.');
    if (!WALKABLE.has(r.maps.get(r.spawn.map).rows[r.spawn.y][r.spawn.x])) throw new Error('Spawn is not walkable.');
    for (const m of r.maps.values()) { if (m.exit) assertPlace(m.exit); for (const row of m.zones) for (const z of row) if (z !== '.' && !r.zones.has(z)) throw new Error(`Unknown zone ${z}.`); }
    for (const l of r.links.values()) { assertPlace(l.from); assertPlace(l.to); if (!WALKABLE.has(r.maps.get(l.to.map).rows[l.to.y][l.to.x])) throw new Error('Link destination is blocked.'); }
    for (const set of [r.chests, r.doors, r.npcs, r.bosses]) for (const e of set.values()) assertPlace(e.at);
    for (const c of r.chests.values()) if (r.maps.get(c.at.map).rows[c.at.y][c.at.x] !== 'C') throw new Error('Chest record does not match its map tile.');
    for (const d of r.doors.values()) if (r.maps.get(d.at.map).rows[d.at.y][d.at.x] !== 'L') throw new Error('Door record does not match its map tile.');
    for (const z of r.zones.values()) for (const e of z.entries) if (!r.monsters.has(e.monster)) throw new Error('Unknown encounter monster.');
    for (const stock of r.shops.values()) for (const item of stock) if (!r.items.has(item)) throw new Error('Unknown shop item.');
    for (const n of r.npcs.values()) if (n.shop && !r.shops.has(n.shop)) throw new Error('Unknown NPC shop.');
    for (const c of r.chests.values()) if ((c.kind === 'ITEM' && !r.items.has(c.value)) || (c.kind === 'MIMIC' && !r.monsters.has(c.value))) throw new Error('Unknown chest contents.');
    for (const b of r.bosses.values()) if (!r.monsters.has(b.monster)) throw new Error('Unknown guardian.');
    for (const m of r.monsters.values()) if (m.drop && !r.items.has(m.drop)) throw new Error('Unknown monster drop.');
    return r;
  }

  function specFingerprint(text) {
    let hash = 2166136261;
    for (const c of text.replace(/\r/g, '')) hash = Math.imul(hash ^ c.charCodeAt(0), 16777619);
    return (hash >>> 0).toString(16).padStart(8, '0');
  }
  const storageKey = () => `daedalus.portal-expedition.v1:${realm.seed}:${fingerprint}`;
  function freshState() {
    const bag = Object.create(null);
    for (const [id, amount] of [['HERB', 3], ['TONIC', 1], ['TORCH', 2], ['WINGS', 1], ['CLUB', 1], ['CLOTHES', 1]]) if (realm.items.has(id)) bag[id] = amount;
    return {version: 1, seed: realm.seed, fingerprint, createdAt: new Date().toISOString(), at: {...realm.spawn}, steps: 0, hp: 160, maxHp: 160, focus: 36, maxFocus: 36, gold: 180, xp: 0, might: 0, bag, weapon: bag.CLUB ? 'CLUB' : null, armor: bag.CLOTHES ? 'CLOTHES' : null, torch: false, blessed: false, returned: false, visited: [realm.spawn.map], talked: [], opened: [], unlocked: [], defeated: [], collected: [], observed: [], seen: {}, logs: [], rng: parseInt(fingerprint, 16) || 7};
  }
  function restoreState() {
    const initial = freshState();
    try {
      const raw = localStorage.getItem(storageKey());
      if (!raw) return initial;
      const s = JSON.parse(raw);
      if (!s || s.version !== 1 || s.seed !== realm.seed || s.fingerprint !== fingerprint) return initial;
      const bag = Object.create(null);
      for (const [id, amount] of Object.entries(s.bag || {})) if (realm.items.has(id) && Number.isInteger(amount) && amount > 0 && amount <= 999) bag[id] = amount;
      if (Object.keys(bag).length > BAG_SLOTS) return initial;
      const finite = (n, lo, hi, fallback) => Number.isInteger(n) && n >= lo && n <= hi ? n : fallback;
      initial.bag = bag;
      for (const id of ['weapon', 'armor']) initial[id] = realm.items.get(s[id])?.kind === (id === 'weapon' ? 'WEAPON' : 'ARMOR') && bag[s[id]] ? s[id] : null;
      for (const [field, set] of [['opened', realm.chests], ['unlocked', realm.doors], ['defeated', realm.bosses], ['talked', realm.npcs], ['visited', realm.maps], ['observed', realm.zones], ['collected', realm.items]]) initial[field] = [...new Set(Array.isArray(s[field]) ? s[field].filter(v => set.has(v)) : [])];
      initial.maxHp = finite(s.maxHp, 160, 9999, 160); initial.hp = finite(s.hp, 1, initial.maxHp, initial.maxHp);
      initial.focus = finite(s.focus, 0, 36, 36); initial.gold = finite(s.gold, 0, 999999, 180);
      initial.steps = finite(s.steps, 0, 9999999, 0); initial.xp = finite(s.xp, 0, 999999, 0); initial.might = finite(s.might, 0, 999, 0);
      initial.rng = finite(s.rng, 0, 4294967295, initial.rng);
      initial.blessed = s.blessed === true; initial.returned = s.returned === true; initial.torch = s.torch === true;
      const m = realm.maps.get(s.at?.map);
      if (m && Number.isInteger(s.at.x) && Number.isInteger(s.at.y) && s.at.x >= 0 && s.at.y >= 0 && s.at.x < m.w && s.at.y < m.h) {
        const t = m.rows[s.at.y][s.at.x], k = key(s.at);
        if (WALKABLE.has(t) || (t === 'L' && initial.unlocked.includes(k)) || (t === 'C' && initial.opened.includes(k))) initial.at = {...s.at};
      }
      for (const [mapId, cells] of Object.entries(s.seen || {})) {
        const map = realm.maps.get(mapId);
        if (!map || !Array.isArray(cells)) continue;
        initial.seen[mapId] = [...new Set(cells.slice(0, map.w * map.h).filter(c => { const [x, y] = String(c).split(',').map(Number); return /^\d+,\d+$/.test(c) && x < map.w && y < map.h; }))];
      }
      initial.logs = Array.isArray(s.logs) ? s.logs.filter(l => typeof l === 'string').slice(0, 40).map(l => l.slice(0, 500)) : [];
      if (typeof s.createdAt === 'string' && s.createdAt.length < 40) initial.createdAt = s.createdAt;
      $('save-status').textContent = 'Restored this seed’s local expedition.';
      return initial;
    } catch { $('save-status').textContent = 'Local save unavailable. Export your journal to keep a copy.'; return initial; }
  }
  function saveNow() {
    if (!realm || !state) return;
    clearTimeout(saveTimer);
    try { localStorage.setItem(storageKey(), JSON.stringify(state)); $('save-status').textContent = `Saved locally · ${state.steps} steps · seed ${realm.seed}`; }
    catch { $('save-status').textContent = 'Browser storage unavailable. Export a journal copy.'; }
  }
  function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(saveNow, 350); }
  function log(message) {
    if (!state) return;
    state.logs.unshift(message); state.logs = state.logs.slice(0, 40); renderLog();
  }
  function renderLog() {
    const stamp = state.logs.join('\n'); if (stamp === lastLog) return; lastLog = stamp;
    $('log').replaceChildren(...state.logs.slice(0, 16).map((line, i) => { const li = document.createElement('li'), counter = document.createElement('small'), text = document.createElement('span'); counter.textContent = String(state.logs.length - i).padStart(2, '0'); text.textContent = line; li.append(counter, text); return li; }));
  }
  function random() { state.rng = (Math.imul(state.rng, 1664525) + 1013904223) >>> 0; return state.rng / 4294967296; }
  const currentMap = () => realm.maps.get(state.at.map);
  const rank = () => 1 + Math.min(12, Math.floor(state.xp / 80));
  const attack = () => 22 + rank() * 3 + state.might + (realm.items.get(state.weapon)?.power || 0);
  const defense = () => 10 + rank() + (realm.items.get(state.armor)?.power || 0);
  const seen = (x, y, map = state.at.map) => (state.seen[map] || []).includes(cellKey(x, y));
  function reveal() {
    const m = currentMap(), cells = new Set(state.seen[m.id] || []), radius = m.dark ? (state.torch ? 7 : 2) : 7;
    for (let y = Math.max(0, state.at.y - radius); y <= Math.min(m.h - 1, state.at.y + radius); y++) for (let x = Math.max(0, state.at.x - radius); x <= Math.min(m.w - 1, state.at.x + radius); x++) if (Math.hypot(x - state.at.x, y - state.at.y) <= radius + .4) cells.add(cellKey(x, y));
    state.seen[m.id] = [...cells];
  }
  function tileAt(x, y, m = currentMap()) { return m.rows[y]?.[x] || (m.dark ? 'W' : m.exit ? '.' : '~'); }
  function canWalk(x, y, m = currentMap()) {
    if (x < 0 || y < 0 || x >= m.w || y >= m.h) return false;
    const k = key({map: m.id, x, y}), t = tileAt(x, y, m);
    if (realm.npcs.has(k) || (realm.bosses.has(k) && !state.defeated.includes(k))) return false;
    return WALKABLE.has(t) || (t === 'L' && state.unlocked.includes(k)) || (t === 'C' && state.opened.includes(k));
  }
  function nearby(at, range = 1) { return at.map === state.at.map && Math.abs(at.x - state.at.x) + Math.abs(at.y - state.at.y) <= range; }
  function canTalk(n) {
    if (nearby(n.at)) return true;
    if (!nearby(n.at, 2)) return false;
    if (n.at.x === state.at.x) return tileAt(n.at.x, (n.at.y + state.at.y) / 2) === '-';
    if (n.at.y === state.at.y) return tileAt((n.at.x + state.at.x) / 2, n.at.y) === '-';
    return false;
  }
  function setSource(message, mode) { $('source-status').textContent = message; $('source-dot').className = `dot ${mode || ''}`; }
  async function loadSeed(value) {
    let seed;
    try { seed = seedValue(value); } catch (error) { setSource(error.message, 'failed'); return; }
    saveNow(); stopRoute(); stopHeld();
    if (request) request.abort();
    const controller = new AbortController(); request = controller; loading = true; $('enter').disabled = true; $('demo').hidden = true;
    setSource(`Reading DRR 1 · seed ${seed}…`, '');
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(`/api/v1/retro/${encodeURIComponent(seed)}`, {signal: controller.signal, headers: {Accept: 'text/plain'}});
      if (!response.ok) throw new Error(response.status === 429 ? 'Realm generation budget reached. Try again shortly.' : `Realm server responded ${response.status}.`);
      const text = await response.text(), parsed = parseSpec(text);
      if (parsed.seed !== seed) throw new Error('The returned realm has a different seed.');
      if (request !== controller) return;
      openRealm(parsed, text, 'server');
    } catch (error) {
      if (request !== controller) return;
      const reason = error.name === 'AbortError' ? 'The realm server did not respond in time.' : error.message;
      setSource(`${reason}${realm ? ` Still viewing ${provenance === 'server' ? 'server' : 'shipped'} seed ${realm.seed}.` : ''}`, 'failed');
      $('demo').hidden = false;
      if (!realm) setDetails('The portal signal is quiet', ['The server is unavailable or returned an unsupported spec. Retry the seed, or open the existing shipped seed 7 as an offline visitor expedition.']);
    } finally { clearTimeout(timeout); if (request === controller) { loading = false; $('enter').disabled = false; request = null; refresh(); inspectNearby(); } }
  }
  function openRealm(parsed, text, source) {
    realm = parsed; fingerprint = specFingerprint(text); provenance = source;
    battle = null; stopRoute(); trail = []; lastZone = ''; lastLog = '';
    state = restoreState(); state.visited = [...new Set([...state.visited, state.at.map])];
    $('seed').value = realm.seed; $('screen-empty').hidden = true;
    const params = new URLSearchParams(location.search); params.set('seed', realm.seed);
    history.replaceState(null, '', `${location.pathname}?${params.toString()}`);
    setSource(source === 'server' ? `Server DRR 1 · seed ${realm.seed} · ${realm.maps.size} maps` : `OFFLINE VISITOR · shipped seed 7 · ${realm.maps.size} maps`, source === 'server' ? 'online' : '');
    if (!state.logs.length) log('A hero, a sage and a scout step through a portal. The broken world becomes pixels.');
    if (source !== 'server') log('Offline visitor expedition: the shipped seed 7. This is not newly generated server land.');
    reveal(); refresh(); inspectNearby(); scheduleSave();
  }

  function stopRoute() { route = []; routeGoal = null; clearInterval(routeTimer); routeTimer = null; }
  function move(dx, dy, fromRoute = false) {
    if (!realm || loading || battle) return false;
    if (!fromRoute) stopRoute();
    facing = [dx, dy]; const m = currentMap(), x = state.at.x + dx, y = state.at.y + dy;
    if (x < 0 || y < 0 || x >= m.w || y >= m.h) {
      if (m.exit) { travel(m.exit); return true; }
      $('hint').textContent = 'The sea marks the edge of this fragment.'; return false;
    }
    const p = {map: m.id, x, y}, k = key(p);
    if (!canWalk(x, y)) {
      if (realm.doors.has(k) && !state.unlocked.includes(k)) inspectDoor(realm.doors.get(k));
      else if (realm.chests.has(k) && !state.opened.includes(k)) inspectChest(realm.chests.get(k));
      else if (realm.npcs.has(k)) inspectNpc(realm.npcs.get(k), false);
      else if (realm.bosses.has(k) && !state.defeated.includes(k)) inspectBoss(realm.bosses.get(k));
      else $('hint').textContent = `The ${TILE_NAMES[tileAt(x, y)] || 'terrain'} blocks your path.`;
      return false;
    }
    trail.unshift({...state.at}); trail = trail.slice(0, 2); state.at = p; state.steps++;
    reveal();
    const link = realm.links.get(k);
    if (link) { travel(link.to); return true; }
    if (samePlace(state.at, realm.portal)) onPortal(false);
    refresh(); inspectNearby(); scheduleSave(); return true;
  }
  function travel(to) {
    stopRoute(); const wasDark = currentMap().dark;
    state.at = {...to}; trail = []; const m = currentMap();
    if (wasDark && !m.dark) state.torch = false;
    const first = !state.visited.includes(m.id);
    state.visited = [...new Set([...state.visited, m.id])];
    log(`${first ? 'Discovered' : 'Entered'} ${m.title}. ${m.dark ? 'The cave keeps its own darkness.' : m.id === 'FIELD' ? 'The arks sail beyond the sky.' : 'Its people remember the old planet.'}`);
    reveal(); refresh(); inspectNearby(); scheduleSave();
  }
  function pathTo(target) {
    const m = currentMap(), queue = [{x: state.at.x, y: state.at.y}], previous = new Map([[cellKey(state.at.x, state.at.y), null]]);
    for (let i = 0; i < queue.length; i++) {
      const p = queue[i]; if (p.x === target.x && p.y === target.y) break;
      for (const [dx, dy] of DIRECTIONS) {
        const x = p.x + dx, y = p.y + dy, k = cellKey(x, y);
        if (previous.has(k) || !canWalk(x, y) || ($('fog').checked && !seen(x, y))) continue;
        previous.set(k, p); queue.push({x, y});
      }
    }
    if (!previous.has(cellKey(target.x, target.y))) return null;
    const result = []; let cursor = {x: target.x, y: target.y};
    while (cursor) { result.unshift(cursor); cursor = previous.get(cellKey(cursor.x, cursor.y)); }
    return result.slice(1);
  }
  function plotRoute(x, y) {
    if (!realm || battle || loading) return;
    const m = currentMap(); if (x < 0 || y < 0 || x >= m.w || y >= m.h) return;
    stopRoute(); stopHeld();
    if ($('fog').checked && !seen(x, y)) { $('hint').textContent = 'Explore toward the unknown first, or turn off Discovery fog to survey the seed atlas.'; return; }
    const p = {map: m.id, x, y}, entity = entityAt(p);
    let candidates = canWalk(x, y) ? [{x, y}] : DIRECTIONS.map(([dx, dy]) => ({x: x + dx, y: y + dy})).filter(v => canWalk(v.x, v.y));
    if (entity?.type === 'npc') for (const [dx, dy] of DIRECTIONS) if (tileAt(x + dx, y + dy) === '-' && canWalk(x + dx * 2, y + dy * 2)) candidates.push({x: x + dx * 2, y: y + dy * 2});
    const paths = candidates.map(pathTo).filter(Boolean).sort((a, b) => a.length - b.length);
    if (!paths.length) { $('hint').textContent = 'No known walking route. A lock, guardian, wall or undiscovered ground may be in the way.'; return; }
    route = paths[0]; routeGoal = p;
    $('hint').textContent = `${route.length} steps plotted. Press Esc or move to stop.`;
    if (!route.length) { finishRoute(p); return; }
    routeTimer = setInterval(() => {
      if (!route.length || battle || loading) { stopRoute(); return; }
      const next = route.shift(), goal = routeGoal;
      const dx = next.x - state.at.x, dy = next.y - state.at.y;
      if (Math.abs(dx) + Math.abs(dy) !== 1 || !move(dx, dy, true)) { stopRoute(); return; }
      if (!route.length && routeGoal) finishRoute(goal);
    }, 130);
  }
  function finishRoute(target) {
    stopRoute(); const e = entityAt(target);
    if (e) inspectEntity(e, false);
    else { $('hint').textContent = `Arrived at ${TILE_NAMES[tileAt(target.x, target.y)] || 'the waypoint'}.`; inspectNearby(); }
    screen.focus({preventScroll: true});
  }
  function entityAt(p) {
    const k = key(p);
    if (realm.npcs.has(k)) return {type: 'npc', data: realm.npcs.get(k)};
    if (realm.chests.has(k) && !state.opened.includes(k)) return {type: 'chest', data: realm.chests.get(k)};
    if (realm.doors.has(k) && !state.unlocked.includes(k)) return {type: 'door', data: realm.doors.get(k)};
    if (realm.bosses.has(k) && !state.defeated.includes(k)) return {type: 'boss', data: realm.bosses.get(k)};
    if (samePlace(p, realm.portal)) return {type: 'portal', data: {at: p}};
    if (realm.links.has(k)) return {type: 'link', data: realm.links.get(k)};
    return null;
  }
  function nearestEntity() {
    const at = state.at, current = entityAt(at); if (current) return current;
    const positions = [{map: at.map, x: at.x + facing[0], y: at.y + facing[1]}, ...DIRECTIONS.map(([dx, dy]) => ({map: at.map, x: at.x + dx, y: at.y + dy}))];
    for (const p of positions) { const e = entityAt(p); if (e) return e; }
    const across = {map: at.map, x: at.x + facing[0] * 2, y: at.y + facing[1] * 2};
    const n = realm.npcs.get(key(across)); if (n && canTalk(n)) return {type: 'npc', data: n};
    for (const n of realm.npcs.values()) if (canTalk(n)) return {type: 'npc', data: n};
    return null;
  }
  function interact() {
    if (!realm || loading) return;
    stopRoute(); if (battle) { $('hint').textContent = 'Choose a command in Nearby / Action.'; return; }
    const e = nearestEntity(); if (e) inspectEntity(e, true);
    else { showZone(); setDetails('A moment on the road', ['The party pauses. Inspect the seed atlas, observe a zone, or walk toward the next road. Town keepers can be reached across their counters.']); }
  }
  function inspectEntity(e, act) {
    if (e.type === 'npc') inspectNpc(e.data, act);
    else if (e.type === 'chest') { if (act) openChest(e.data); else inspectChest(e.data); }
    else if (e.type === 'door') { if (act) unlockDoor(e.data); else inspectDoor(e.data); }
    else if (e.type === 'boss') inspectBoss(e.data);
    else if (e.type === 'portal') onPortal(act);
    else if (e.type === 'link') { const l = e.data; setDetails('A road between maps', [`This passage leads to ${realm.maps.get(l.to.map).title}.`], [{label: 'Take passage', run: () => { if (nearby(l.from, 0)) travel(l.to); else plotRoute(l.from.x, l.from.y); }}]); }
  }
  function inspectNearby() {
    if (battle || !realm) return;
    const e = nearestEntity();
    if (e) { inspectEntity(e, false); $('hint').textContent = e.type === 'npc' ? 'Speak to the keeper. Shops work across the counter.' : e.type === 'boss' ? 'A guardian stands in the only passage.' : 'Press E or Interact to investigate.'; }
    else { setDetails(`${currentMap().dark ? 'Into the deep' : 'The road ahead'}`, [currentMap().dark ? 'The cave is a maze from the Daedalus engines. Keep your torch lit and trace the corridors. Keys are placed by the real seed, never invented by this page.' : 'An ark crew’s children keep these towns alive. Read their notices, visit the queen and follow the surviving roads toward the cave.'], [{label: 'Observe this zone', run: observeZone}]); }
  }
  function setDetails(title, paragraphs = [], actions = []) {
    $('detail-heading').textContent = title;
    $('detail').replaceChildren(...paragraphs.map(text => { const p = document.createElement('p'); p.textContent = text; return p; }));
    $('actions').replaceChildren(...actions.map(action => { const b = document.createElement('button'); b.type = 'button'; b.textContent = action.label; if (action.primary) b.className = 'primary'; if (action.disabled) b.disabled = true; b.addEventListener('click', action.run); return b; }));
  }
  function inspectNpc(n, speak) {
    if (battle || loading) return;
    if (!canTalk(n)) { $('hint').textContent = 'Walk beside the person, or up to their counter.'; return; }
    if (speak) {
      if (!state.talked.includes(key(n.at))) state.talked.push(key(n.at));
      log(n.lines.join(' '));
      if (n.role === 'QUEEN') { state.blessed = true; state.hp = state.maxHp; state.focus = state.maxFocus; log('The queen blesses the crew. The castle becomes their refuge.'); }
    }
    const name = n.lines[0].split(':')[0] || n.role;
    const paragraphs = speak ? [...n.lines, ...(n.role === 'NEWS' ? realm.news : [])] : [`${name} waits nearby. ${n.wanders ? 'Their native realm counterpart wanders these streets.' : 'They keep this place.'}`];
    const actions = !speak ? [{label: `Speak to ${name.toLowerCase()}`, primary: true, run: () => inspectNpc(n, true)}] : [];
    if (speak && n.role === 'INN') actions.push({label: `Rest · ${n.price} local gold`, run: () => { if (!canTalk(n)) return; if (state.gold < n.price) { log('The innkeeper asks for more local gold.'); return; } state.gold -= n.price; state.hp = state.maxHp; state.focus = state.maxFocus; log('At the inn, all three dream of a planet with no broken edges. Health and focus restored.'); refresh(); scheduleSave(); }});
    if (speak && n.role === 'SHOP') {
      paragraphs.push('Trade uses expedition gold saved in this browser. Found-only items are never sold by the shop.');
      for (const id of realm.shops.get(n.shop) || []) { const item = realm.items.get(id); if (item.price > 0) actions.push({label: `${item.title} · ${item.price}g`, run: () => buy(n, id)}); }
    }
    setDetails(name, paragraphs, actions); refresh(); scheduleSave();
  }
  function give(id, count = 1) {
    if (!realm.items.has(id)) return false;
    if (!state.bag[id] && Object.keys(state.bag).length >= BAG_SLOTS) { log('The 12-kind bag is full. Use or sell a supply before collecting this item.'); return false; }
    state.bag[id] = Math.min(999, (state.bag[id] || 0) + count);
    if (!state.collected.includes(id)) state.collected.push(id);
    return true;
  }
  function consume(id) { if (!state.bag[id]) return false; if (--state.bag[id] <= 0) delete state.bag[id]; return true; }
  function buy(n, id) {
    if (loading || battle || !canTalk(n) || !(realm.shops.get(n.shop) || []).includes(id)) return;
    const item = realm.items.get(id); if (state.gold < item.price) { log(`You need ${item.price} local gold for ${item.title}.`); return; }
    if (!give(id)) return;
    state.gold -= item.price; log(`Bought ${item.title} with expedition gold.`); refresh(); inspectNpc(n, true); scheduleSave();
  }
  function inspectDoor(d) {
    setDetails(`A ${TIER_NAMES[d.tier]} lock`, [`This door consumes one ${TIER_NAMES[d.tier]} key. Higher-tier keys do not substitute for it.`, state.bag[TIER_KEYS[d.tier]] ? 'The party carries the right key.' : d.tier === 1 ? 'Ask the keymaker at the castle.' : d.tier === 2 ? 'The silver key was lost on the second cave floor.' : 'The star key lies past the Shard Tyrant.'], [{label: 'Unlock door', primary: true, run: () => unlockDoor(d)}]);
  }
  function unlockDoor(d) {
    if (battle || loading || !nearby(d.at) || state.unlocked.includes(key(d.at))) return;
    if (!consume(TIER_KEYS[d.tier])) { log(`The ${TIER_NAMES[d.tier]} lock needs its matching key.`); inspectDoor(d); return; }
    state.unlocked.push(key(d.at)); log(`Opened the ${TIER_NAMES[d.tier]} lock. Its key is spent.`); refresh(); inspectNearby(); scheduleSave();
  }
  function inspectChest(c) {
    setDetails('A seeded chest', ['The realm generator placed this chest here. Its contents stay concealed until your party opens it.', currentMap().dark ? 'Some chests in the deep are mimics. Prepare before you reach inside.' : 'A little of the old world is still in its keeping.'], [{label: 'Open chest', primary: true, run: () => openChest(c)}]);
  }
  function openChest(c) {
    if (battle || loading || !nearby(c.at) || state.opened.includes(key(c.at))) return;
    if (c.kind === 'MIMIC') { startBattle(c.value, {type: 'chest', id: key(c.at)}); return; }
    if (c.kind === 'ITEM' && !give(c.value)) return;
    if (c.kind === 'GOLD') state.gold = Math.min(999999, state.gold + c.value);
    state.opened.push(key(c.at)); log(c.kind === 'GOLD' ? `The chest holds ${c.value} local gold.` : `Recovered ${realm.items.get(c.value).title}.`);
    refresh(); inspectNearby(); scheduleSave();
  }
  function inspectBoss(b) {
    const monster = realm.monsters.get(b.monster);
    setDetails(monster.title, ['The guardian holds the only passage to the star key. It will not let the crew pass untouched.', `${monster.hp} HP · ${monster.atk} attack · ${monster.def} defense. Prepare gear, herbs and focus before this local expedition duel.`, 'Browser battles use a shared health pool and simplified commands. Native party combat has its own complete engine.'], [{label: 'Face guardian', primary: true, run: () => { if (nearby(b.at)) startBattle(b.monster, {type: 'boss', id: key(b.at)}); }}]);
  }
  function startBattle(id, origin) {
    if (battle || loading) return;
    stopRoute(); stopHeld(); const monster = realm.monsters.get(id);
    battle = {monster, hp: monster.hp, origin, round: 0};
    log(`${origin.type === 'boss' ? 'The guardian rises' : 'The chest bites'}: ${monster.title}.`);
    renderBattle(); refresh(); scheduleSave();
  }
  function renderBattle() {
    if (!battle) return;
    const m = battle.monster;
    setDetails(m.title, [`Local expedition duel · round ${battle.round + 1}`, `${battle.hp} / ${m.hp} enemy health · party strike ${attack()} · party defense ${defense()}`, 'Strike deals physical damage. Blaze costs 6 focus. Mend costs 5 focus. Guard halves the next response and restores 3 focus.'], [
      {label: 'Strike', primary: true, run: () => combat('strike')},
      {label: 'Blaze · 6 focus', disabled: state.focus < 6, run: () => combat('blaze')},
      {label: 'Mend · 5 focus', disabled: state.focus < 5, run: () => combat('mend')},
      {label: 'Guard', run: () => combat('guard')},
      {label: 'Herb', disabled: !state.bag.HERB, run: () => combat('herb')},
      {label: 'Tonic', disabled: !state.bag.TONIC, run: () => combat('tonic')},
      {label: 'Retreat', disabled: m.traits.includes('BOSS'), run: () => combat('retreat')}
    ]);
    const meter = document.createElement('progress'); meter.className = 'battle-health'; meter.max = m.hp; meter.value = Math.max(0, battle.hp); meter.setAttribute('aria-label', `${m.title} health`); $('detail').append(meter);
  }
  function combat(command) {
    if (!battle || loading) return;
    const b = battle, m = b.monster; let guarded = false;
    if (command === 'retreat' && !m.traits.includes('BOSS')) { battle = null; log('The crew withdraws. The unopened chest waits for another attempt.'); refresh(); inspectNearby(); scheduleSave(); return; }
    if (command === 'strike') { const damage = Math.max(1, attack() - Math.floor(m.def / 2) + Math.floor(random() * 6)); b.hp -= damage; log(`The crew strikes for ${damage}.`); }
    else if (command === 'blaze' && state.focus >= 6) { state.focus -= 6; const damage = 30 + rank() * 4 + Math.floor(random() * 7); b.hp -= damage; log(`The sage sends a blaze for ${damage}.`); }
    else if (command === 'mend' && state.focus >= 5) { state.focus -= 5; state.hp = Math.min(state.maxHp, state.hp + 38 + rank() * 3); log('The sage mends the party.'); }
    else if (command === 'guard') { guarded = true; state.focus = Math.min(state.maxFocus, state.focus + 3); log('The scout calls the rhythm. The crew guards and regains focus.'); }
    else if (command === 'herb' && consume('HERB')) { state.hp = Math.min(state.maxHp, state.hp + realm.items.get('HERB').power); log('The crew shares a healing herb.'); }
    else if (command === 'tonic' && consume('TONIC')) { state.focus = Math.min(state.maxFocus, state.focus + realm.items.get('TONIC').power); log('A tonic restores focus.'); }
    else return;
    if (b.hp <= 0) { winBattle(); return; }
    const hits = m.traits.includes('DOUBLE') ? 2 : 1;
    let damage = Math.max(2, m.atk - Math.floor(defense() / 2) + Math.floor(random() * 4)) * hits;
    if (guarded) damage = Math.ceil(damage / 2);
    state.hp = Math.max(0, state.hp - damage); b.round++;
    log(`${m.title} answers for ${damage}${hits === 2 ? ' in two blows' : ''}.`);
    if (state.hp <= 0) { loseBattle(); return; }
    renderBattle(); refresh(); scheduleSave();
  }
  function winBattle() {
    const b = battle, m = b.monster, oldRank = rank();
    state.gold = Math.min(999999, state.gold + m.gold); state.xp = Math.min(999999, state.xp + m.exp);
    if (b.origin.type === 'boss') state.defeated.push(b.origin.id); else state.opened.push(b.origin.id);
    log(`${m.title} falls. ${m.gold} local gold and ${m.exp} expedition experience earned.`);
    if (m.drop && m.dropOneIn > 0 && random() < 1 / m.dropOneIn) { if (give(m.drop)) log(`Recovered ${realm.items.get(m.drop).title} from the encounter.`); }
    if (rank() > oldRank) { state.hp = Math.min(state.maxHp, state.hp + 30); state.focus = Math.min(state.maxFocus, state.focus + 8); log(`Expedition rank ${rank()}. The crew finds its second wind.`); }
    battle = null; refresh(); inspectNearby(); scheduleSave();
  }
  function loseBattle() {
    battle = null; state.gold = Math.floor(state.gold / 2); state.hp = state.maxHp; state.focus = state.maxFocus; state.torch = false;
    const queen = [...realm.npcs.values()].find(n => n.role === 'QUEEN');
    const refuge = state.blessed && queen ? {map: queen.at.map, x: queen.at.x, y: queen.at.y + 1} : realm.spawn;
    log('The crew retreats to its refuge. Half its local gold stays in the deep; health and focus return.'); travel(refuge);
  }
  function useItem(id) {
    if (!realm || battle || loading || !state.bag[id]) return;
    const item = realm.items.get(id);
    if (item.kind === 'WEAPON' || item.kind === 'ARMOR') { state[item.kind === 'WEAPON' ? 'weapon' : 'armor'] = id; log(`Equipped ${item.title}.`); }
    else if (id === 'HERB') { if (state.hp === state.maxHp) { log('Health is already full. Keep the herb for the deep.'); return; } consume(id); state.hp = Math.min(state.maxHp, state.hp + item.power); log('An herb restores party health.'); }
    else if (id === 'TONIC') { if (state.focus === state.maxFocus) { log('Focus is already full.'); return; } consume(id); state.focus = Math.min(state.maxFocus, state.focus + item.power); log('A tonic restores party focus.'); }
    else if (id === 'TORCH') { lightTorch(); return; }
    else if (id === 'WINGS') { returnHome(); return; }
    else if (id === 'MIGHT_SEED') { consume(id); state.might += item.power; log('The might seed strengthens every future strike.'); }
    else if (id === 'LIFE_SEED') { consume(id); state.maxHp += item.power; state.hp += item.power; log('The life seed widens the party’s shared health pool.'); }
    else { log('This item has no field use in the browser expedition.'); return; }
    reveal(); refresh(); scheduleSave();
  }
  function lightTorch() {
    if (!realm || loading || battle) return;
    if (!currentMap().dark) { log('Save the torch for the cave.'); return; }
    if (state.torch) { log('The current torch lasts until the crew leaves the cave.'); return; }
    if (!consume('TORCH')) { log('The party needs a torch from a town or the castle keymaker.'); return; }
    state.torch = true; log('Torch lit. The darkness gives up seven tiles of its secrets.'); reveal(); refresh(); scheduleSave();
  }
  function returnHome() {
    if (!realm || loading || battle) return;
    if (samePlace(state.at, realm.portal)) { onPortal(true); return; }
    if (!consume('WINGS')) { log('Returning instantly consumes WINGS. You can also walk back through the real roads and stairs.'); return; }
    state.torch = false; travel(realm.portal); onPortal(true);
  }
  function onPortal(act) {
    if (state.collected.includes('STAR_BLADE') && !state.returned) { state.returned = true; log('The crew brings the star blade through the surviving roads to the portal. The light is home.'); }
    setDetails('The portal home', ['The cube hums with a thousand fragments beyond this one. Your crew is still three people, still one promise.', state.returned ? 'Your local journal records a finished expedition. This progress is not a deed or a mint entitlement.' : 'Recover the star blade from the queen’s vault, then return to close the expedition.'], [{label: 'Record homecoming', run: () => { log(state.returned ? 'Homecoming recorded in the local keeper’s journal.' : 'The portal records the journey so far. The star blade is still out there.'); refresh(); scheduleSave(); }}]);
    if (act) { log('The portal remembers the party’s local expedition.'); refresh(); scheduleSave(); }
  }
  function sell(id) {
    if (!realm || battle || loading || !state.bag[id]) return;
    const shop = [...realm.npcs.values()].find(n => n.role === 'SHOP' && canTalk(n));
    if (!shop) { log('Walk to a shopkeeper before selling.'); return; }
    if (state.weapon === id || state.armor === id) { log('Keep your equipped gear. Equip a replacement before selling it.'); return; }
    const item = realm.items.get(id), value = item.kind === 'TREASURE' ? item.power : Math.floor(item.price / 2);
    if (value <= 0) { log('The keeper will not buy this found-only item.'); return; }
    consume(id); state.gold = Math.min(999999, state.gold + value); log(`Sold ${item.title} for ${value} local gold.`); refresh(); scheduleSave();
  }
  function observeZone() {
    if (!realm || loading || battle) return;
    const m = currentMap(), id = m.zones[state.at.y][state.at.x], z = realm.zones.get(id);
    if (!z) { log('Safe ground. No monster table is attached to this tile.'); showZone(); return; }
    const total = z.entries.reduce((sum, e) => sum + e.weight, 0); let roll = random() * total, choice = z.entries[z.entries.length - 1];
    for (const e of z.entries) { roll -= e.weight; if (roll < 0) { choice = e; break; } }
    const monster = realm.monsters.get(choice.monster), count = choice.min + Math.floor(random() * (choice.max - choice.min + 1));
    const first = !state.observed.includes(id); if (first) { state.observed.push(id); state.xp = Math.min(999999, state.xp + 12); }
    log(`Zone ${id} field sighting: ${count} ${monster.title}${count > 1 ? ' creatures' : ''}. ${first ? 'New zone catalogued; +12 local experience.' : 'Observation added to the journal.'}`);
    setDetails('A field sighting', [`${monster.title} · ${monster.rarity.toLowerCase()} · ${count} in this observed group.`, `The encounter table gives this species weight ${choice.weight} out of ${total}. Observing a zone is a survey activity; it does not trigger native combat.`, monster.traits.length ? `Native traits: ${monster.traits.join(', ')}.` : 'No special native traits listed.']);
    showZone(); refresh(); scheduleSave();
  }
  function showZone() {
    if (!realm) return;
    const id = currentMap().zones[state.at.y][state.at.x], z = realm.zones.get(id);
    if (lastZone === id) return; lastZone = id;
    const target = $('zone-detail'); target.replaceChildren();
    const note = document.createElement('p'); note.className = 'zone-label';
    if (!z) { note.textContent = 'Safe ground · no encounter zone'; target.append(note); return; }
    note.textContent = `Zone ${id} · native encounter interval ${z.rate} · ${state.observed.includes(id) ? 'catalogued' : 'unobserved'}`; target.append(note);
    const total = z.entries.reduce((sum, e) => sum + e.weight, 0), table = document.createElement('table'), head = document.createElement('thead'), row = document.createElement('tr');
    for (const title of ['Species / group', 'Weight']) { const th = document.createElement('th'); th.scope = 'col'; th.textContent = title; row.append(th); } head.append(row); table.append(head);
    const body = document.createElement('tbody');
    for (const e of z.entries) {
      const monster = realm.monsters.get(e.monster), tr = document.createElement('tr'), name = document.createElement('td'), weight = document.createElement('td'), traits = document.createElement('span');
      name.textContent = `${monster.title} · ${e.min}–${e.max}`; traits.className = 'traits'; traits.textContent = monster.rarity; name.append(traits); weight.textContent = `${(e.weight / total * 100).toFixed(1)}%`; tr.append(name, weight); body.append(tr);
    }
    table.append(body); target.append(table);
  }

  function questList() {
    const talkedIn = id => state.talked.some(k => k.startsWith(`${id},`));
    const tyrant = [...realm.bosses.values()].find(b => b.monster === 'SHARD_TYRANT');
    return [
      ['Through the cube', 'Register the party on the surviving fragment.', state.visited.includes(realm.spawn.map)],
      ['The first voices', `Speak to a keeper in ${realm.maps.get('TOWN1')?.title || 'the first town'}.`, talkedIn('TOWN1')],
      ['A queen’s promise', 'Receive the blessing: “Our world broke, but we endure.”', state.blessed],
      ['The far town', `Speak to a keeper in ${realm.maps.get('TOWN2')?.title || 'the far town'}.`, talkedIn('TOWN2')],
      ['The long dark', 'Cross the cave mouth and enter the first floor.', state.visited.includes('CAVE1')],
      ['Silver in the maze', 'Recover the placed silver key on the second floor.', state.collected.includes('SILVER_KEY')],
      ['The only passage', 'Defeat the Shard Tyrant in a local expedition duel.', !!tyrant && state.defeated.includes(key(tyrant.at))],
      ['The light in the vault', 'Use the star key and recover the STAR BLADE.', state.collected.includes('STAR_BLADE')],
      ['Bring it home', 'Return with the star blade to the seed’s portal.', state.returned]
    ];
  }
  function renderBag() {
    const bag = $('bag'); bag.replaceChildren();
    for (const [id, count] of Object.entries(state.bag)) {
      const item = realm.items.get(id), row = document.createElement('div'), label = document.createElement('span'), quantity = document.createElement('span'), buttons = document.createElement('div'); row.className = 'bag-row';
      label.textContent = item.title; quantity.className = 'count'; quantity.textContent = ` ×${count}`; label.append(quantity);
      const equipped = state.weapon === id || state.armor === id;
      if (equipped) { const e = document.createElement('span'); e.className = 'equipped'; e.textContent = ' EQUIPPED'; label.append(e); }
      if (['WEAPON', 'ARMOR', 'USE'].includes(item.kind) && id !== 'ANTIDOTE') { const use = document.createElement('button'); use.type = 'button'; use.textContent = item.kind === 'USE' ? 'Use' : 'Equip'; use.disabled = !!battle || loading || equipped; use.addEventListener('click', () => useItem(id)); buttons.append(use); }
      if (item.price > 0 || item.kind === 'TREASURE') { const sale = document.createElement('button'); sale.type = 'button'; sale.textContent = 'Sell'; sale.disabled = !!battle || loading || equipped; sale.addEventListener('click', () => sell(id)); buttons.append(sale); }
      row.append(label, buttons); bag.append(row);
    }
    if (!Object.keys(state.bag).length) { const empty = document.createElement('p'); empty.className = 'muted'; empty.textContent = 'An empty bag. Ask the shopkeeper for supplies.'; bag.append(empty); }
  }
  function renderWaypoints() {
    const m = currentMap(), container = $('waypoints'); container.replaceChildren();
    for (const l of realm.links.values()) if (l.from.map === m.id) {
      const button = document.createElement('button'), coord = document.createElement('span'), known = seen(l.from.x, l.from.y) || !$('fog').checked;
      button.type = 'button'; button.textContent = known ? realm.maps.get(l.to.map).title : 'Unsurveyed passage'; coord.textContent = known ? `${l.from.x},${l.from.y} ↗` : '?'; button.append(coord); button.disabled = !known || !!battle || loading;
      button.addEventListener('click', () => plotRoute(l.from.x, l.from.y)); container.append(button);
    }
    if (m.exit) { const b = document.createElement('button'); b.type = 'button'; b.textContent = 'Return through the town gate ↓'; b.disabled = !!battle || loading; b.addEventListener('click', () => { const exits = []; for (let x = 0; x < m.w; x++) if (WALKABLE.has(tileAt(x, m.h - 1))) exits.push({x, y: m.h - 1}); const paths = exits.map(p => ({p, path: pathTo(p)})).filter(e => e.path).sort((a, b) => a.path.length - b.path.length); if (paths.length) plotRoute(paths[0].p.x, paths[0].p.y); else $('hint').textContent = 'Explore toward the south gate first.'; }); container.append(b); }
    if (m.id === realm.portal.map) { const b = document.createElement('button'); b.type = 'button'; b.textContent = 'Portal home ↗'; b.disabled = !!battle || loading; b.addEventListener('click', () => plotRoute(realm.portal.x, realm.portal.y)); container.append(b); }
  }
  function refresh() {
    if (!realm || !state) return;
    const m = currentMap(); $('map-name').textContent = m.title; $('map-type').textContent = m.dark ? 'CAVE EXPEDITION' : `${m.music} SURVEY`;
    $('coord').textContent = `SEED ${realm.seed} / ${state.at.x},${state.at.y}`; $('cue').textContent = `CUE · ${battle ? battle.origin.type === 'boss' ? 'BOSS' : 'BATTLE' : m.music} · VISUAL ONLY`;
    $('hp').textContent = `${state.hp} / ${state.maxHp}`; $('health').max = state.maxHp; $('health').value = state.hp;
    $('mp').textContent = `${state.focus} / ${state.maxFocus}`; $('gold').textContent = state.gold.toLocaleString(); $('rank').textContent = `${rank()} / ${state.steps.toLocaleString()}`;
    $('torch').textContent = state.torch ? 'Torch lit' : 'Light torch'; $('torch').disabled = !!battle || loading;
    $('interact').disabled = loading; $('observe').disabled = !!battle || loading; $('return').disabled = !!battle || loading;
    $('discovery').textContent = `${state.seen[m.id]?.length || 0} / ${m.w * m.h} tiles recorded · ${state.visited.length} / ${realm.maps.size} maps visited`;
    const quests = questList(), complete = quests.filter(q => q[2]).length; $('quest-progress').value = complete; $('quest-count').textContent = `${complete} / ${quests.length} chapters recorded locally`;
    $('quests').replaceChildren(...quests.map(([title, note, done]) => { const li = document.createElement('li'), div = document.createElement('div'), strong = document.createElement('strong'), small = document.createElement('small'); li.className = done ? 'done' : ''; strong.textContent = title; small.textContent = note; div.append(strong, small); li.append(div); return li; }));
    renderBag(); renderWaypoints(); renderLog(); lastZone = ''; showZone(); drawAtlas(); drawFrame();
  }

  function rect(c, x, y, w, h, fill) { c.fillStyle = fill; c.fillRect(x, y, w, h); }
  function tile(c, t, x, y, wx, wy, time, size = 16) {
    const s = size / 16;
    c.save(); c.translate(x, y); c.scale(s, s);
    const p = (a, b, w, h, fill) => rect(c, a, b, w, h, fill);
    const grain = ((wx * 17 + wy * 29) & 7), wave = reducedMotion ? 0 : Math.floor(time / 500) % 3;
    const floors = {'.': '#526c49', T: '#425c40', '~': '#253b5c', h: '#76866a', '^': '#4c506a', ':': '#bcaa78', '=': '#2e4659', '%': '#4b6461', ',': '#8b8b8b', '#': '#5b6372', b: '#a77b62', D: '#a77b62', L: '#a77b62', C: '#64596d', '>': '#555167', '<': '#555167', V: '#526c49', K: '#526c49', A: '#76866a', O: '#526c49', Q: '#a77b62', '|': '#79526c', '-': '#a77b62', _: '#555167', W: '#303042'};
    p(0, 0, 16, 16, floors[t] || '#526c49');
    if (t === '.' || t === 'T') { p(grain + 2, 4, 2, 1, '#6d865b'); p((grain + 7) % 14, 11, 2, 1, '#314e3b'); }
    if (t === '~') { p(1 + wave, 5, 7, 1, '#425e77'); p(8 - wave, 12, 5, 1, '#3c536f'); }
    if (t === 'T') { p(7, 10, 3, 5, '#65534b'); p(5, 1, 6, 3, '#77935b'); p(3, 4, 10, 5, '#35563e'); p(1, 8, 14, 4, '#29453a'); p(4, 6, 4, 2, '#729063'); }
    if (t === ':' || t === '%') { p(grain + 2, 4, 2, 1, t === ':' ? '#daca99' : '#688076'); p(9, 11, 4, 1, t === ':' ? '#a28b63' : '#364d52'); }
    if (t === 'h' || t === '^') { p(3, 8, 10, 6, t === 'h' ? '#535e57' : '#747684'); p(5, 5, 6, 5, t === 'h' ? '#9ea384' : '#8c8b9c'); p(7, 2, 2, 4, t === 'h' ? '#bcc1a2' : '#cfbec3'); p(3, 14, 11, 2, '#323f4a'); }
    if (t === '=' || t === '-') { p(0, 3, 16, 10, '#92735c'); for (let i = 0; i < 16; i += 4) p(i, 3, 1, 10, '#534b50'); p(0, 3, 16, 2, '#c6a37b'); }
    if ([',', 'b', '#', 'W', '_'].includes(t)) { p(0, 7, 16, 1, t === 'W' ? '#232435' : '#00000020'); p(8, 0, 1, 7, '#00000020'); p(3, 8, 1, 8, '#00000020'); if (t === '#') p(0, 0, 16, 2, '#9ba0a5'); }
    if (t === 'D' || t === 'L') { p(3, 1, 10, 15, t === 'L' ? '#5e4b62' : '#51494e'); p(5, 3, 6, 13, '#98705e'); p(5, 3, 1, 13, '#c29b70'); p(9, 10, 2, 2, t === 'L' ? '#ffd08a' : '#372d37'); }
    if (t === 'C') { p(3, 5, 10, 8, '#8f604b'); p(2, 3, 12, 5, '#cfa268'); p(3, 7, 10, 2, '#5f4150'); p(7, 6, 2, 4, '#ffdc9c'); p(3, 13, 11, 2, '#352c44'); }
    if (t === '>' || t === '<') { p(2, 2, 12, 12, '#302c40'); for (let i = 0; i < 4; i++) p(4, 3 + i * 3, 8, 1, '#b2a3ae'); p(t === '>' ? 10 : 3, 5, 2, 6, '#e5c69a'); }
    if (t === 'V') { p(3, 7, 10, 8, '#d7b384'); p(1, 5, 14, 3, '#b15e65'); p(4, 2, 8, 3, '#db8b7a'); p(7, 10, 3, 5, '#53455e'); p(4, 9, 2, 2, '#83d5c2'); }
    if (t === 'K') { p(2, 5, 12, 10, '#adb0c3'); p(1, 2, 4, 5, '#c9c9d7'); p(11, 2, 4, 5, '#c9c9d7'); p(6, 2, 4, 4, '#adb0c3'); p(6, 9, 4, 6, '#5a4d72'); p(7, 1, 5, 2, '#ffd08a'); }
    if (t === 'A') { p(2, 6, 12, 9, '#7b7280'); p(4, 3, 8, 8, '#96928d'); p(5, 8, 6, 7, '#252234'); p(6, 7, 4, 2, '#252234'); }
    if (t === 'O') { p(4, 1, 8, 2, '#cab5ff'); p(2, 3, 2, 10, '#a896f6'); p(12, 3, 2, 10, '#a896f6'); p(4, 13, 8, 2, '#cab5ff'); p(5, 4, 6, 8, '#4b3e7c'); p(7 + wave, 6, 2, 5, '#b9abef'); }
    if (t === '|') { p(2, 0, 1, 16, '#d2a576'); p(13, 0, 1, 16, '#d2a576'); p(7, 5, 2, 2, '#a77a8e'); }
    if (t === 'Q') { p(2, 1, 12, 5, '#d8ac75'); p(3, 5, 10, 7, '#98617a'); p(1, 8, 3, 6, '#d8ac75'); p(12, 8, 3, 6, '#d8ac75'); }
    c.restore();
  }
  function person(c, x, y, colors, leader, time) {
    const bob = reducedMotion ? 0 : Math.floor(time / 400) % 2;
    rect(c, x + 3, y + 13, 10, 2, '#11162360'); rect(c, x + 5, y + 10, 3, 4, colors[2]); rect(c, x + 9, y + 10, 3, 4 - bob, colors[2]);
    if (colors[4] && colors[4] !== '#000000') rect(c, x + 3, y + 6, 11, 6, colors[4]);
    rect(c, x + 4, y + 6, 8, 5, colors[1]); rect(c, x + 5, y + 2, 6, 5, '#e5c296'); rect(c, x + 4, y + 1, 8, 3, colors[0]);
    if (colors[3] && colors[3] !== '#000000') rect(c, x + 3, y, 10, 2, colors[3]);
    rect(c, x + 6, y + 4, 1, 1, '#302b42'); rect(c, x + 10, y + 4, 1, 1, '#302b42');
    if (leader) { rect(c, x + 1, y + 7, 2, 7, '#f5dcc4'); rect(c, x, y + 9, 4, 1, '#ffd08a'); }
  }
  function monsterSprite(c, m, x, y, scale = 1) {
    c.save(); c.translate(x, y); c.scale(scale, scale); const p = (a, b, w, h, col) => rect(c, a, b, w, h, col);
    p(1, 14, 14, 2, '#14132380');
    if (m.shape === 0) { p(3, 7, 10, 7, m.body); p(5, 4, 6, 4, m.body); p(2, 11, 12, 3, m.accent); }
    else if (m.shape === 1) { p(6, 1, 5, 11, m.body); p(3, 4, 5, 5, m.body); p(10, 7, 4, 5, m.accent); p(5, 11, 5, 3, m.accent); }
    else if (m.shape === 2) { p(2, 6, 12, 7, m.body); p(4, 3, 8, 5, m.body); for (let i = 3; i < 13; i += 4) p(i, 1, 2, 5, m.accent); p(3, 13, 3, 2, m.accent); p(10, 13, 3, 2, m.accent); }
    else if (m.shape === 3) { p(6, 8, 5, 7, '#bfb795'); p(2, 4, 12, 5, m.body); p(4, 2, 8, 4, m.body); p(4, 5, 2, 2, m.accent); p(10, 3, 2, 2, m.accent); }
    else if (m.shape === 4) { p(5, 2, 6, 5, m.body); p(3, 7, 10, 5, m.body); p(4, 12, 3, 3, m.accent); p(10, 12, 3, 3, m.accent); p(1, 4, 2, 10, m.accent); p(12, 7, 3, 6, m.accent); }
    else if (m.shape === 5) { p(6, 6, 4, 8, m.body); p(1, 2, 4, 7, m.body); p(3, 5, 10, 4, m.body); p(11, 2, 4, 7, m.body); p(6, 6, 1, 2, m.accent); p(9, 6, 1, 2, m.accent); }
    else if (m.shape === 6) { p(2, 5, 12, 9, m.body); p(1, 2, 14, 4, m.accent); p(3, 7, 10, 4, '#292335'); for (let i = 3; i < 13; i += 3) p(i, 7, 2, 2, '#eee1c3'); }
    else { p(4, 3, 8, 11, m.body); p(2, 5, 12, 7, m.body); p(6, 6, 5, 5, m.accent); p(8, 7, 2, 3, '#20283b'); }
    if (![3, 5, 6, 7].includes(m.shape)) { p(6, 6, 1, 2, '#181c31'); p(10, 6, 1, 2, '#181c31'); }
    c.restore();
  }
  function visible(x, y) {
    const m = currentMap();
    return m.dark ? Math.hypot(x - state.at.x, y - state.at.y) <= (state.torch ? 7 : 2) + .4 : !$('fog').checked || seen(x, y);
  }
  function drawFrame(time = 0) {
    if (!realm || !state) { rect(ctx, 0, 0, screen.width, screen.height, '#151931'); return; }
    const m = currentMap(); camera = {x: state.at.x - Math.floor(COLS / 2), y: state.at.y - Math.floor(ROWS / 2)};
    for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) {
      const wx = camera.x + x, wy = camera.y + y, inside = wx >= 0 && wy >= 0 && wx < m.w && wy < m.h;
      let t = tileAt(wx, wy, m), k = key({map: m.id, x: wx, y: wy});
      if ((t === 'L' && state.unlocked.includes(k)) || (t === 'C' && state.opened.includes(k))) t = m.dark ? '_' : 'b';
      tile(ctx, t, x * TILE, y * TILE, wx, wy, time);
      if (inside && !visible(wx, wy)) rect(ctx, x * TILE, y * TILE, TILE, TILE, seen(wx, wy) ? '#101327c9' : '#101327f3');
      if ($('zones').checked && inside && visible(wx, wy)) { const z = m.zones[wy][wx]; if (z !== '.') rect(ctx, x * TILE, y * TILE, 16, 16, `${ZONE_COLORS[parseInt(z, 36) % ZONE_COLORS.length]}44`); }
    }
    for (const p of route) if (visible(p.x, p.y)) rect(ctx, (p.x - camera.x) * TILE + 6, (p.y - camera.y) * TILE + 6, 4, 4, '#ffd08ac0');
    for (const n of realm.npcs.values()) if (n.at.map === m.id && visible(n.at.x, n.at.y)) person(ctx, (n.at.x - camera.x) * TILE, (n.at.y - camera.y) * TILE, n.look, false, time);
    for (const b of realm.bosses.values()) if (b.at.map === m.id && !state.defeated.includes(key(b.at)) && visible(b.at.x, b.at.y)) monsterSprite(ctx, realm.monsters.get(b.monster), (b.at.x - camera.x) * TILE, (b.at.y - camera.y) * TILE);
    const looks = [['#63485d', '#ffd08a', '#575285', '#000000', '#bc647b'], ['#dad3c8', '#a896f6', '#5b567b', '#000000', '#000000'], ['#8e6948', '#7fe0c1', '#52616c', '#000000', '#000000']];
    for (let i = trail.length - 1; i >= 0; i--) { const p = trail[i]; if (p.map === m.id && visible(p.x, p.y)) person(ctx, (p.x - camera.x) * TILE, (p.y - camera.y) * TILE, looks[i + 1], false, time); }
    person(ctx, (state.at.x - camera.x) * TILE, (state.at.y - camera.y) * TILE, looks[0], true, time);
    if (state.torch && m.dark) { const x = (state.at.x - camera.x) * TILE, y = (state.at.y - camera.y) * TILE; rect(ctx, x + 13, y + 6, 2, 6, '#927059'); rect(ctx, x + 12, y + 3, 4, 4, '#ffcc82'); rect(ctx, x + 13, y + 2, 2, 3, '#fff1c4'); }
    if (battle) {
      rect(ctx, 0, 0, screen.width, screen.height, '#111023d9');
      for (let i = 0; i < 35; i++) rect(ctx, (i * 97 + 15) % 496, (i * 59 + 18) % 220, 1, 1, '#746984');
      monsterSprite(ctx, battle.monster, 208, 92, 5);
      ctx.textAlign = 'center'; ctx.font = 'bold 15px monospace'; ctx.fillStyle = '#ffd08a'; ctx.fillText(battle.monster.title, 248, 215);
      ctx.font = '10px monospace'; ctx.fillStyle = '#cbc1df'; ctx.fillText('LOCAL EXPEDITION DUEL', 248, 238);
      rect(ctx, 150, 253, 196, 6, '#474055'); rect(ctx, 150, 253, Math.floor(196 * battle.hp / battle.monster.hp), 6, '#ff9b95');
      ctx.fillText('Choose your command below the map.', 248, 287); ctx.textAlign = 'left';
    }
  }
  function drawAtlas() {
    if (!realm || !state) return;
    const m = currentMap(), s = Math.min(256 / m.w, 256 / m.h), ox = Math.floor((256 - m.w * s) / 2), oy = Math.floor((256 - m.h * s) / 2);
    rect(atlasCtx, 0, 0, 256, 256, '#0c1022');
    const palette = {'.': '#647d57', T: '#365843', '~': '#283e60', h: '#889277', '^': '#6c6b81', ':': '#c6b783', '=': '#b39575', '%': '#536e67', ',': '#8f9195', '#': '#4b5264', b: '#a38474', D: '#d7b58d', L: '#e7bd7c', C: '#ffd08a', '>': '#b1a1d7', '<': '#b1a1d7', V: '#7fe0c1', K: '#ffd08a', A: '#ff9b95', O: '#b0a0ff', Q: '#ffd08a', '|': '#975c77', '-': '#b39575', _: '#8f8196', W: '#2b2e43'};
    for (let y = 0; y < m.h; y++) for (let x = 0; x < m.w; x++) {
      const known = !$('fog').checked || seen(x, y), z = m.zones[y][x];
      const fill = !known ? '#181d33' : $('zones').checked && z !== '.' ? ZONE_COLORS[parseInt(z, 36) % ZONE_COLORS.length] : palette[m.rows[y][x]];
      rect(atlasCtx, Math.floor(ox + x * s), Math.floor(oy + y * s), Math.ceil(s), Math.ceil(s), fill);
    }
    for (const p of route) rect(atlasCtx, ox + p.x * s, oy + p.y * s, Math.max(1, s), Math.max(1, s), '#fff0b9');
    const px = Math.floor(ox + state.at.x * s), py = Math.floor(oy + state.at.y * s);
    rect(atlasCtx, px - 1, py - 1, Math.ceil(s) + 2, Math.ceil(s) + 2, '#15182b'); rect(atlasCtx, px, py, Math.ceil(s), Math.ceil(s), '#ffffff');
  }
  function clickScreen(event) {
    if (!realm) return;
    const r = screen.getBoundingClientRect(), x = Math.floor((event.clientX - r.left) / r.width * screen.width / TILE) + camera.x, y = Math.floor((event.clientY - r.top) / r.height * screen.height / TILE) + camera.y;
    plotRoute(x, y);
  }
  function clickAtlas(event) {
    if (!realm) return;
    const r = atlas.getBoundingClientRect(), m = currentMap(), s = Math.min(256 / m.w, 256 / m.h), ox = Math.floor((256 - m.w * s) / 2), oy = Math.floor((256 - m.h * s) / 2);
    plotRoute(Math.floor(((event.clientX - r.left) / r.width * 256 - ox) / s), Math.floor(((event.clientY - r.top) / r.height * 256 - oy) / s));
  }
  function stopHeld() { clearInterval(heldTimer); heldTimer = null; held = null; }
  function startHeld(dx, dy, token) { stopHeld(); held = token; move(dx, dy); heldTimer = setInterval(() => move(dx, dy), 150); }
  const keys = {ArrowUp: [0, -1], w: [0, -1], ArrowRight: [1, 0], d: [1, 0], ArrowDown: [0, 1], s: [0, 1], ArrowLeft: [-1, 0], a: [-1, 0]};
  document.addEventListener('keydown', event => {
    if (event.target.closest('input,textarea,select,button,a') || event.ctrlKey || event.metaKey || event.altKey) return;
    const token = event.key.length === 1 ? event.key.toLowerCase() : event.key;
    if (keys[token]) { event.preventDefault(); if (event.repeat || held === token) return; startHeld(...keys[token], token); }
    else if (token === 'e' || token === ' ') { event.preventDefault(); if (!event.repeat) interact(); }
    else if (token === 'Escape') { stopRoute(); stopHeld(); $('hint').textContent = 'Route stopped. The crew waits for your lead.'; }
  });
  document.addEventListener('keyup', e => { const token = e.key.length === 1 ? e.key.toLowerCase() : e.key; if (held === token) stopHeld(); });
  window.addEventListener('blur', () => { stopHeld(); stopRoute(); saveNow(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) { stopHeld(); stopRoute(); saveNow(); } });
  window.addEventListener('pagehide', saveNow);
  for (const b of document.querySelectorAll('[data-move]')) {
    b.addEventListener('pointerdown', e => { e.preventDefault(); b.setPointerCapture(e.pointerId); const [dx, dy] = b.dataset.move.split(',').map(Number); startHeld(dx, dy, b); });
    b.addEventListener('pointerup', stopHeld); b.addEventListener('pointercancel', stopHeld); b.addEventListener('lostpointercapture', stopHeld);
  }
  $('touch-act').addEventListener('click', interact); $('interact').addEventListener('click', interact); $('observe').addEventListener('click', observeZone); $('torch').addEventListener('click', lightTorch); $('return').addEventListener('click', returnHome);
  screen.addEventListener('click', clickScreen); atlas.addEventListener('click', clickAtlas);
  $('zones').addEventListener('change', refresh); $('fog').addEventListener('change', () => { stopRoute(); refresh(); });
  $('seed-form').addEventListener('submit', e => { e.preventDefault(); loadSeed($('seed').value); });
  $('demo').addEventListener('click', () => { try { if (request) request.abort(); request = null; loading = false; $('enter').disabled = false; $('demo').hidden = true; openRealm(parseSpec(SHIPPED_SPEC), SHIPPED_SPEC, 'shipped'); } catch (e) { setSource(e.message, 'failed'); } });
  $('reset').addEventListener('click', () => {
    if (!realm || loading) return;
    if (!window.confirm(`Start a new local expedition for seed ${realm.seed}? This replaces only this browser journal.`)) return;
    stopRoute(); stopHeld(); battle = null; state = freshState(); trail = []; lastLog = ''; reveal(); log('A new crew crosses the cube. The roads remain; the expedition begins again.'); refresh(); inspectNearby(); saveNow();
  });
  $('export').addEventListener('click', () => {
    if (!realm || !state) return;
    saveNow();
    const record = {kind: 'Daedalus local portal expedition', authority: 'visitor journal only; no NFT, deed, ownership or native-save authority', source: provenance, specFingerprint: fingerprint, realmSeed: realm.seed, exportedAt: new Date().toISOString(), chapters: questList().map(([title, note, completed]) => ({title, note, completed})), progress: state};
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], {type: 'application/json'})), a = document.createElement('a'); a.href = url; a.download = `portal-expedition-${realm.seed}.json`; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  function animate(time) {
    frame++;
    if (!document.hidden && realm && (frame % (reducedMotion ? 30 : 4) === 0)) { drawFrame(time); if (route.length) drawAtlas(); }
    requestAnimationFrame(animate);
  }
  // Existing shipped native realm-7.drr content embedded as a string. Only
  // the explicit offline button opens it; a failed requested seed is never replaced.
  const SHIPPED_SPEC = "DRR 1\nseed 7\nname SHARDLANDS\nitem HERB USE 10 25 HERB\nitem TONIC USE 30 10 TONIC\nitem ANTIDOTE USE 8 0 ANTIDOTE\nitem TORCH USE 8 3 TORCH\nitem WINGS USE 25 0 WINGS\nitem MIGHT_SEED USE 0 2 MIGHT SEED\nitem LIFE_SEED USE 0 6 LIFE SEED\nitem BRONZE_KEY KEY 45 1 BRONZE KEY\nitem SILVER_KEY KEY 0 2 SILVER KEY\nitem STAR_KEY KEY 0 3 STAR KEY\nitem CLUB WEAPON 25 4 CLUB\nitem COPPER_SWORD WEAPON 110 9 COPPER SWORD\nitem IRON_AXE WEAPON 280 15 IRON AXE\nitem EMBER_BLADE WEAPON 0 22 EMBER BLADE\nitem STAR_BLADE WEAPON 0 30 STAR BLADE\nitem CLOTHES ARMOR 15 2 CLOTHES\nitem LEATHER_VEST ARMOR 70 6 LEATHER VEST\nitem CHAIN_MAIL ARMOR 240 12 CHAIN MAIL\nitem SHARD_MAIL ARMOR 0 18 SHARD MAIL\nitem METEOR_MAIL ARMOR 0 26 METEOR MAIL\nitem STAR_SHARD TREASURE 0 300 STAR SHARD\nmonster BLIGHT_SLIME 0 58d840 188c10 6 5 2 3 2 2 COMMON POISON HERB 8 BLIGHT SLIME\nmonster BOG_SLIME 0 8c34c8 4c1478 14 9 5 4 6 6 UNCOMMON POISON,CALL ANTIDOTE 6 BOG SLIME\nmonster LUCKY_DRIP 0 f8b800 c87800 4 6 99 30 120 10 RARE FLEE,HARD MIGHT_SEED 4 LUCKY DRIP\nmonster DUST_WISP 1 bcbcbc 8c34c8 8 7 3 9 3 4 COMMON - TONIC 10 DUST WISP\nmonster EMBER_WISP 1 f87818 d82800 16 11 6 12 9 9 UNCOMMON ZAP TONIC 6 EMBER WISP\nmonster SHARDBACK 2 9c9c9c 3ce0e0 16 10 9 4 6 7 COMMON - HERB 6 SHARDBACK\nmonster GLASSBACK 2 f0f0fc f878c8 28 15 18 6 16 14 UNCOMMON CALL STAR_SHARD 16 GLASSBACK\nmonster PUFFCAP 3 d82800 f0d090 10 6 4 5 4 5 COMMON SLEEP HERB 8 PUFFCAP\nmonster SHADECAP 3 8c34c8 9c9c9c 22 12 8 8 12 12 UNCOMMON SLEEP,HEAL LIFE_SEED 12 SHADECAP\nmonster GLOOMWING 5 3c3c3c d82800 12 9 4 14 6 6 COMMON FLEE TORCH 6 GLOOMWING\nmonster STARE_ORB 7 f8f8f8 58f8 20 12 7 10 14 12 UNCOMMON SLEEP,ZAP TONIC 5 STARE ORB\nmonster GNASHBOX 6 a0581c f8b800 34 18 12 9 30 60 RARE ZAP STAR_SHARD 3 GNASHBOX\nmonster MOSS_KNIGHT 4 2c8c18 80d010 36 17 14 7 32 25 UNCOMMON - CHAIN_MAIL 12 MOSS KNIGHT\nmonster STONE_KNIGHT 4 7c7c7c d82800 50 21 18 7 55 40 RARE DOUBLE IRON_AXE 10 STONE KNIGHT\nmonster SHARD_TYRANT 4 f8b800 8c34c8 160 28 20 12 400 300 LEGENDARY ZAP,HEAL,DOUBLE,BOSS STAR_SHARD 1 SHARD TYRANT\nmap FIELD 64 64 FIELD 0 - 0 0 FIELD\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~:::::~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~:TT.:::::~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~::TT.......:~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~:..TT........:~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~:..:~~~~~~~~:...TT........:~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~:...~~~~~~~~:...TT........:~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~....:~~~~~~~:...T.........:~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~....:~~~~~~:............TT:::~::::~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~....:~~~~~~:............TTTTT.:...:~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~....:~~~~~~:............TTTTT......:~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~:.....:~~~~::............TTTTT.......~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~.......~~~~:.........................:~~~~~~~~~~\nrow :::~~~~~~~~~~~~:.......:~~~.TTTT.........hhhhhh......:~~~~~~~~~~\nrow :::~~~~~~~~~~~~........:~~~.T%TTT........hhhhhhh.....:~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~.........:::T%%%TT........hhhhhhhh.....:~~~~~~~~~\nrow ~~~~~~~~~~~~~~:..........:T%%%%TT.........hhhhhhhhh.A..:~~~~~~~~\nrow ~~~~~~~~~~~~~~.........TT:::%%%T...........hhhhhhhhh...:~~~~~~~~\nrow ~~~~~~~~~~~:::........T:::::%%%T..............hhhhhh...:~~~~~~~~\nrow ~~~~~~~~~~~:..........::~:::%%TT..............hhhhhh....~~~~~~~~\nrow ~~~~~~~~~~~:.........:~~~~~::.................hhh^hh....:~~~~~~~\nrow ~~~~~~~~~~~..........:~~~~~~:............hh..hhhh^^h....:~~~~~~~\nrow ~~~~~~~~~~:.........::~~~~~~:............hhhhhhhhhhhh....~~~~~~~\nrow ~~~~~~~~:::.........:~~~~~~~:........hhhhhhhhhhhhhhhhV...~~~~~~~\nrow ~~~~~~~:::..........:~~~~~~~%T.....hhhhhhh^^^^hhhhhh....:~~~~~~~\nrow ~~~~~~~:::T.........:~~~~~~~%T....hhhhhhhh^^^^^hhh......:~~~~~~~\nrow ~~~~~~~:%TT.........:~~~~~~~%%...hhhhhhhhh^^^^^^h.......:~~~~~~~\nrow ~~~~~~~:TTT.........:~~~~~~~%%..Vhhhhhhhhh^^^^^hhh......:~~~~~~~\nrow ~~~~~~~~:T...........::~~~~:%%T....hhhhhhhhhhhhhhhh.....~~~~~~~~\nrow ~~~~~~~~:.............::~~~::%TT.................hhh....~~~~~~~~\nrow ~~~~~~~~~..............:~~~::%%%TTTTTTTT.........hh....:~~~~~~~~\nrow ~~~~~~~~~..............::::::TT%%%%%%%%T...............:~~~~~~~~\nrow ~~~~~~~~~.......TT......:::::.O%%%%%%%%T..............:~~~~~~~~~\nrow ~~~~~~~~:.....KTTTT............T%%%%:::::::~~:.......~~~~~~~~~~~\nrow ::::~~~~:......TTTTT...........::::~~:~~~~~~~~~:...:~~~~~~~~~~~~\nrow .....:::.......TTThhhh.........:~~~~~::~~~~~~~~~~::~~~~~~~~~~~~~\nrow .................Thhhhhh.......~~~~~~::~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ........TTT.......hhhhhhhhh....~~~~~~::~~~~~~~~~~~~~~~~~~~~~~~~~\nrow .......TTTT.......hh^^^hhhh...:~~~~~:::~~~~~~~~~~~~~~~~~~~~~~~~~\nrow .......T%%TT......hhhhhhhhh...:~~~~:::~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow .....:::::::::....hhhhhhhhh...T~~~:::::~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ....:~~~~~~~~::....hhhh........:~:%%%T::~~~~~~~~~~~~~~~~~~~~~~~~\nrow :::::~~~~~~~~~:....hh..........T%%%%%T..:~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~:...hh..........T%%%%%T..:~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~...hh..........TTTT%%T..~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~...hh...........TTTTT...:~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~:...............TTTT.....~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~:...............TTTT......:~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~:...............TTTTT......::~~~~~~~~~~~~~~~~~~~\nrow :::~~~~~~~~~~~~~:TT.............TTTTTT......::~::~~~~:~~~~~~~~~~\nrow ..:~~~~~~~~~~~~~~:%T.....h......T%%%%%.......:::::~~~~::::::~~~~\nrow ..:~~~~~~~~~~~~~~~:T............T%%%%%T..:....:.::~~~~~:::::~~~~\nrow .:~~~~~~~~~~~~~~~~:T............%%%%%%T.:::::::::~~~~~~~~::~~~~~\nrow ~~~~~~~~~~~~~~~~~~~:...........T%%::%T.:::::~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~:.........::~~~~:::~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~.......:~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~:....:~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~:..:~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nrow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nzrow ..................................22222.........................\nzrow .................................255222222......................\nzrow ...............................225522222222.....................\nzrow ..............................22255222222222....................\nzrow .................2222........222255222222222....................\nzrow .................2222........222255222222222....................\nzrow .................22222.......222252222222222....................\nzrow .................22222......222222222222255222.2222.............\nzrow .................22222......222222222222255555222222............\nzrow .................22222......2222222222222555552222222...........\nzrow ................2222222....22222222222222555552222222...........\nzrow ................2222222....222222222222222222222222222..........\nzrow ...............222222222...255552222222223333332222222..........\nzrow ...............222222222...254555222222223333333222222..........\nzrow ...............2222222222225444552222222233333333222222.........\nzrow ..............22222222222254444552222222223333333332.222........\nzrow ..............222222222552214445112222222223333333332222........\nzrow ...........222222222225222114445111222222222223333332222........\nzrow ...........2222222222222.1114455111122222222223333332222........\nzrow ...........22222222222.....1111111111222222222333.3322222.......\nzrow ...........22222222222......111111111122233223333..322222.......\nzrow ..........222222222222......11111111111223333333333332222.......\nzrow ........2222222222222.......1111111113333333333333333.222.......\nzrow .......22222222222221.......45011113333333....33333322222.......\nzrow .......22252222222211.......40001133333333.....3332222222.......\nzrow .......24552222222111.......44000333333333......322222222.......\nzrow .......25552222221111.......4400.033333333.....3332222222.......\nzrow ........252222221111111....04400000333333333333333322222........\nzrow ........2222222111111111...00400000011111111112223332222........\nzrow .........222221111111111...00444000005551111111223322222........\nzrow .........222211111111110000000.4444444451111111122222222........\nzrow .........22211115511110000000...44444445111111111222222.........\nzrow ........222111.5555110000000.....4440000111..11122222...........\nzrow 2222....222211155555110000000...000..0.........22222............\nzrow 222222222222211555333310000000.0.....01..........22.............\nzrow 2222222222222211153333330000000......11.........................\nzrow 2222222255522221113333333000000......11.........................\nzrow 22222225555222221133...33300000.....111.........................\nzrow 2222222544552222213333333330000....111..........................\nzrow 2222222222222222223333333331000...11111.........................\nzrow 22222........2222223333111111000.1444511........................\nzrow 22222.........222223311111111105444445111.......................\nzrow ...............22223311111111115444445112.......................\nzrow ................222332111111111555544512........................\nzrow ................2223322111111111555551222.......................\nzrow ................2222222211111111555512222.......................\nzrow ................222222222111111155552222222.....................\nzrow ................22222222221111115555522222222...................\nzrow ................255222222221111155555522222222.22...............\nzrow .................245222223221111544444222222222222..............\nzrow ..................25222222222111544444522222222222..............\nzrow ..................2522222222221244444452222222222...............\nzrow ...................2222222222225442245222222....................\nzrow .....................222222222222....222........................\nzrow .......................22222222.................................\nzrow .......................222222...................................\nzrow ........................2222....................................\nzrow .........................22.....................................\nzrow ................................................................\nzrow ................................................................\nzrow ................................................................\nzrow ................................................................\nzrow ................................................................\nzrow ................................................................\nend\nmap TOWN1 24 20 TOWN 0 FIELD 32 26 ASHDALE\nrow ########################\nrow #,,,,,,,,,,,,,,,,,,,,,,#\nrow #,#######,,,,,,#######,#\nrow #,#bbbbb#,,,,,,#bbbbb#,#\nrow #,#-----#,,,,,,#-----#,#\nrow #,#bbbbb#,,,,,,#bbbbb#,#\nrow #,#bbbbb#,,,,,,#bbbbb#,#\nrow #,###D###,,,,,,###D###,#\nrow #,,,,,,,,,,,,,,,,,,,,,,#\nrow #,,T,...T,,,,,,,,,,,,,,#\nrow #,#######,,,,,,#######,#\nrow #,#Cbbbb#,,,,,,#bbbbb#,#\nrow #,#bbbbbL,,,,,,#-----#,#\nrow #,#bbbbb#,,,,,,#bbbbb#,#\nrow #,#bbbbC#,,,,,,#bbbbb#,#\nrow #,#######,,,,,,###D###,#\nrow #T,,.,..,,,,,,,,,,,,,,,#\nrow #T,.,,,.,,,,,,,T.,TT,,.#\nrow #,,,,,,,,,,,,,,,,,,,,,,#\nrow ############D###########\nend\nmap TOWN2 24 20 TOWN 0 FIELD 53 22 STONEHOLM\nrow ########################\nrow #,,,,,,,,,,,,,,,,,,,,,,#\nrow #,#######,,,,,,#######,#\nrow #,#bbbbb#,,,,,,#bbbbb#,#\nrow #,#-----#,,,,,,#-----#,#\nrow #,#bbbbb#,,,,,,#bbbbb#,#\nrow #,#bbbbb#,,,,,,#bbbbb#,#\nrow #,###D###,,,,,,###D###,#\nrow #,,,,,,,,,,,,,,,,,,,,,,#\nrow #,,T.,.,T,,,,,,,,,,,,,,#\nrow #,#######,,,,,,#######,#\nrow #,#Cbbbb#,,,,,,#bbbbb#,#\nrow #.#bbbbbL,,,,,,#-----#,#\nrow #T#bbbbb#,,,,,,#bbbbb#,#\nrow #.#CbbbC#,,,,,,#bbbbb#,#\nrow #,#######,,,,,,###D###,#\nrow #T,TT,,..,,,,,,,,,,,,,,#\nrow #,,,TT.T,,,,,,,.,,T,,.T#\nrow #,,,,,,,,,,,,,,,,,,,,,,#\nrow ############D###########\nend\nmap CASTLE 20 18 CASTLE 0 FIELD 14 32 CASTLE\nrow ####################\nrow #bbbbb#bbbQbb#bbbbb#\nrow #bCbCb#bbb|bb#bbCbb#\nrow #bbbbbLbbb|bbLbbbbb#\nrow #bCbbb#bbb|bb#bbCbb#\nrow #bbbbb#bbb|bb#bbbbb#\nrow #######bbb|bb#######\nrow #bbbbbbbbb|bbbbbbbb#\nrow #bbbbbbbbb|bbbbbbbb#\nrow #bb#bbb#bb|bb#bbb#b#\nrow #bbbbbbbbb|bbbbbbbb#\nrow #bbbbbbbbb|bbbbbbbb#\nrow #bbbbbbbbb|bbbbbbbb#\nrow #bb#bbb#bb|bb#bbb#b#\nrow #bbbbbbbbb|bbbbbbbb#\nrow #bbbbbbbbb|bbbbbbbb#\nrow #bbbbbbbbb|bbbbbbbb#\nrow ##########D#########\nend\nmap CAVE1 31 23 CAVE 1 - 0 0 CAVE B1\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\nrow WWW_____WWWWWWWWWWWWW_____WWWWW\nrow WWW_____WWWWWWWWWWWWW_____WWWWW\nrow WWW__<____________________WWWWW\nrow WWW_____WWWWWWWWWWWWW_____WWWWW\nrow WWW_____WWWWWWWWWWWWW_____WWWWW\nrow WWWWW_WWWWWWWWWWWWWWWWW_WWWWWWW\nrow WWWWW_WWWWWWWWWWWWWWWWW_WWWWWWW\nrow WWWWW_WWWWWWWWWWWWWWWWW_WWWWWWW\nrow WWWWW_WWWWWWWWWWWWWWWWW_WWWWWWW\nrow WWWWW_WWWWWWWWWWWWWWWWW_WWWWWWW\nrow WWWWW_WWWWWWW____CWWWWW_WWWWWWW\nrow WWWWW_WWWWWWW_____WWWWW_WWWWWWW\nrow WWWWW_____________WWWWW_WWWWWWW\nrow WWWWW___WWWWW_____WWWWW_WWWWWWW\nrow WWWWWC__WWWWW_____WWWC_____>WWW\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\nzrow ...............................\nzrow ...............................\nzrow ...............................\nzrow ...66666.............66666.....\nzrow ...6...6.............66666.....\nzrow ...6...6666666666666666666.....\nzrow ...6...6.............66666.....\nzrow ...66666.............66666.....\nzrow .....6.................6.......\nzrow .....6.................6.......\nzrow .....6.................6.......\nzrow .....6.................6.......\nzrow .....6.................6.......\nzrow .....6.......6666......6.......\nzrow .....6.......66666.....6.......\nzrow .....6666666666666.....6.......\nzrow .....666.....66666.....6.......\nzrow ......66.....66666....6666.....\nzrow ...............................\nzrow ...............................\nzrow ...............................\nzrow ...............................\nzrow ...............................\nend\nmap CAVE2 27 19 CAVE 1 - 0 0 CAVE B2\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWW\nrow W<______________W___W_____W\nrow W_W_WWWWWWWWWWW_W_W_W_WWW_W\nrow W_W___________W_W_W_____W_W\nrow W_WWWWWWWWWWW_WWW_WWWWW_W_W\nrow W___________W_____W___W_W_W\nrow WWWWW_WWWWWWWWW_WWW_W_W_W_W\nrow WC____W_______W_W___W___W_W\nrow WWWWWWW_WWWWW_W_W_WWW_WWW_W\nrow W_______W___W_W___W_____W_W\nrow W_W_WWWWW_W_W_W_WWW_WWW_W_W\nrow W_W_W___W_W___W_____W_____W\nrow W_W_W_W_W_W_WWWWWWW_W_WWW_W\nrow W_W_W_W_W___W_____W_____W_W\nrow W_W_W_W_WWW_W_W_W_WWWWW_W_W\nrow W_WCW_W___W_WCW_W_______W_W\nrow W_WWW_WWW_W_WWW_WWWWWWWWW_W\nrow W_______W>W_____WC________W\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWW\nzrow ...........................\nzrow ...7777777777777.777.77777.\nzrow ...7...........7.7.7.7...7.\nzrow .7.77777777777.7.7.77777.7.\nzrow .7...........7...7.....7.7.\nzrow .77777777777.77777.777.7.7.\nzrow .....7.........7...7.7.7.7.\nzrow ..7777.7777777.7.777.777.7.\nzrow .......7.....7.7.7...7...7.\nzrow .7777777.777.7.777.77777.7.\nzrow .7.7.....7.7.7.7...7...7.7.\nzrow .7.7.777.7.777.77777.77777.\nzrow .7.7.7.7.7.7.......7.7...7.\nzrow .7.7.7.7.777.77777.77777.7.\nzrow .7.7.7.7...7.7.7.7.....7.7.\nzrow .7...7.777.7...7.7777777.7.\nzrow .7...7.....7...7.........7.\nzrow .7777777...77777..77777777.\nzrow ...........................\nend\nmap CAVE3 27 19 CAVE 1 - 0 0 CAVE B3\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWW\nrow W<W_____W_______________W_W\nrow W_W_W_WWW_WWWWW_WWWWWWW_W_W\nrow W_W_W________CW_W_____W___W\nrow W_W_WWWWWWWWWWW_WWWWW_WWW_W\nrow W___W_____W___W_W_______W_W\nrow W_WWW_WWW_W_W_W_W_WWWWWWW_W\nrow WCW___W_W_W_W___W_W_____W_W\nrow WWW_WWW_W_W_WWWWW_W_WWW_W_W\nrow W___W_____W___W_____W___W_W\nrow W_WWWWWWW_WWW_W_WWWWW_WWW_W\nrow W_______W_____W_____W_W___W\nrow W_WWWWW_WWWWWWWWWWW_W_W_WWW\nrow W_WC__W_____W_____W_W___W_W\nrow W_WWW_WWWWW_W_WWW_WWW_WWW_W\nrow W___W___W___W_W___WCW_W___W\nrow WWW_WWW_W_WWW_W_WWW_W_WWW_W\nrow W_______W_____W_____W_____W\nrow WWWWWWWWWWWWWWWWWWWWWWWWWWW\nzrow ...........................\nzrow ...88888.888888888888888.8.\nzrow ...8.8...8.....8.......8.8.\nzrow .8.8.88888888..8.88888.888.\nzrow .8.8...........8.....8...8.\nzrow .888.88888.888.8.8888888.8.\nzrow .8...8...8.8.8.8.8.......8.\nzrow ...888.8.8.8.888.8.88888.8.\nzrow ...8...8.8.8.....8.8...8.8.\nzrow .888.88888.888.88888.888.8.\nzrow .8.......8...8.8.....8...8.\nzrow .8888888.88888.88888.8.888.\nzrow .8.....8...........8.8.8...\nzrow .8..88.88888.88888.8.888.8.\nzrow .8...8.....8.8...8...8...8.\nzrow .888.888.888.8.888.8.8.888.\nzrow ...8...8.8...8.8.....8...8.\nzrow .8888888.88888.88888.88888.\nzrow ...........................\nend\nzone 0 22 BLIGHT_SLIME:50:1:3 DUST_WISP:30:1:2 PUFFCAP:20:1:2\nzone 1 20 BLIGHT_SLIME:20:2:3 DUST_WISP:20:1:3 PUFFCAP:15:1:2 SHARDBACK:20:1:2 EMBER_WISP:12:1:2 BOG_SLIME:10:1:2 LUCKY_DRIP:2:1:1\nzone 2 18 SHARDBACK:18:1:3 EMBER_WISP:18:1:3 GLASSBACK:14:1:2 SHADECAP:14:1:2 STARE_ORB:12:1:2 MOSS_KNIGHT:10:1:1 LUCKY_DRIP:3:1:2 STONE_KNIGHT:3:1:1\nzone 3 16 SHARDBACK:40:1:3 GLASSBACK:15:1:2 MOSS_KNIGHT:8:1:1 LUCKY_DRIP:2:1:1\nzone 4 14 BLIGHT_SLIME:25:2:3 BOG_SLIME:35:1:3 PUFFCAP:15:1:3 SHADECAP:15:1:2\nzone 5 20 PUFFCAP:35:1:3 DUST_WISP:25:1:2 GLOOMWING:25:1:3 SHADECAP:10:1:1\nzone 6 14 GLOOMWING:35:1:3 SHARDBACK:25:1:2 BOG_SLIME:20:1:2 STARE_ORB:15:1:1 LUCKY_DRIP:3:1:1\nzone 7 13 GLOOMWING:20:2:3 STARE_ORB:22:1:2 GLASSBACK:20:1:2 MOSS_KNIGHT:18:1:2 LUCKY_DRIP:4:1:2\nzone 8 12 STONE_KNIGHT:25:1:2 MOSS_KNIGHT:25:1:2 STARE_ORB:20:1:3 GLASSBACK:20:1:3 LUCKY_DRIP:5:1:2\nlink FIELD 32 26 TOWN1 12 18\nlink FIELD 53 22 TOWN2 12 18\nlink FIELD 14 32 CASTLE 10 16\nlink FIELD 52 15 CAVE1 5 5\nlink CAVE1 5 5 FIELD 52 15\nlink CAVE1 27 17 CAVE2 1 1\nlink CAVE2 1 1 CAVE1 27 17\nlink CAVE2 9 17 CAVE3 1 1\nlink CAVE3 1 1 CAVE2 9 17\nchest TOWN1 3 11 ITEM ANTIDOTE\nchest TOWN1 7 14 ITEM BRONZE_KEY\nchest TOWN2 3 11 GOLD 39\nchest TOWN2 7 14 ITEM TORCH\nchest TOWN2 3 14 GOLD 145\nchest CASTLE 2 2 ITEM SHARD_MAIL\nchest CASTLE 4 2 ITEM TONIC\nchest CASTLE 2 4 ITEM HERB\nchest CASTLE 16 2 ITEM STAR_BLADE\nchest CASTLE 16 4 ITEM METEOR_MAIL\nchest CAVE3 19 15 ITEM STAR_KEY\nchest CAVE1 21 17 ITEM MIGHT_SEED\nchest CAVE1 5 17 ITEM HERB\nchest CAVE1 17 13 ITEM STAR_SHARD\nchest CAVE2 3 15 ITEM SILVER_KEY\nchest CAVE2 17 17 ITEM BRONZE_KEY\nchest CAVE2 1 7 ITEM EMBER_BLADE\nchest CAVE2 13 15 ITEM MIGHT_SEED\nchest CAVE3 1 7 MIMIC GNASHBOX\nchest CAVE3 13 3 GOLD 355\nchest CAVE3 3 13 MIMIC GNASHBOX\ndoor TOWN1 8 12 1\ndoor TOWN2 8 12 1\ndoor CASTLE 6 3 2\ndoor CASTLE 13 3 3\nnpc TOWN1 5 3 0 7c4c14 8c34c8 3c3c3c 0 0 INN 6 - INNKEEPER: WELCOME, TRAVELERS.\nnpc TOWN1 18 3 0 bcbcbc d82800 28a0 0 0 SHOP 0 T1ITEMS MERCHANT: HERBS AND TORCHES!\nnpc TOWN1 18 11 0 f87818 2c8c18 28a0 0 0 SHOP 0 T1GEAR SMITH: STEEL FOR THE ROAD.\nnpc TOWN1 11 9 1 d82800 8c34c8 3c3c3c 0 0 NEWS 0 - ELDER: NEWS OF THE DAY!\nnpc TOWN1 13 17 0 3c3c3c 8c34c8 7c7c7c 0 0 TALK 0 - GUARD: THE CAVE MOUTH LIES/FAR TO THE NORTHEAST.\nnpc TOWN1 10 14 1 bcbcbc 8888 603008 0 0 TALK 0 - KID: A GOLD SLIME RAN FROM ME!/LUCKY DRIPS FLEE. HIT THEM FAST.\nnpc TOWN1 13 5 1 bcbcbc d82800 7c7c7c 0 0 TALK 0 - WOMAN: THE STOREROOM WANTS/A BRONZE KEY. THE CASTLE SELLS THEM./THE CASTLE IS TO THE WEST.\nnpc TOWN2 5 3 0 d82800 8888 7c7c7c 0 0 INN 14 - INNKEEPER: WELCOME, TRAVELERS.\nnpc TOWN2 18 3 0 f87818 a0581c 3c3c3c 0 0 SHOP 0 T2ITEMS MERCHANT: HERBS AND TORCHES!\nnpc TOWN2 18 11 0 f8b800 8888 3c3c3c 0 0 SHOP 0 T2GEAR SMITH: STEEL FOR THE ROAD.\nnpc TOWN2 11 9 1 bcbcbc a0581c 28a0 0 0 NEWS 0 - ELDER: NEWS OF THE DAY!\nnpc TOWN2 13 17 0 bcbcbc 8c34c8 28a0 0 0 TALK 0 - GUARD: THE QUEEN'S VAULT/OPENS ONLY TO A STAR KEY.\nnpc TOWN2 10 14 1 7c4c14 8888 3c3c3c 0 0 TALK 0 - MINER: THE STAR KEY LIES AT THE/BOTTOM OF THE CAVE, PAST A/TYRANT MADE OF SHARDS.\nnpc TOWN2 13 5 1 3c3c3c 58f8 3c3c3c 0 0 TALK 0 - SAGE: CHESTS IN THE DEEP CAN BITE./BRING TORCHES. THE DARK IS LONG.\nnpc CASTLE 10 2 0 bcbcbc 58f8 7c7c7c f8b800 d82800 QUEEN 0 - QUEEN: WELCOME, TRAVELERS./OUR WORLD BROKE, BUT WE ENDURE./HELP EACH OTHER. THAT IS HOW WE LIVE.\nnpc CASTLE 7 11 1 bcbcbc 58f8 28a0 0 0 TALK 0 - KNIGHT: A SILVER KEY OPENS/THE TREASURY. IT WAS LOST/IN THE CAVE'S SECOND FLOOR.\nnpc CASTLE 15 11 1 7c4c14 a0581c 603008 0 0 NEWS 0 - SCHOLAR: THE BUBBLE HOLDS/EVERY PIECE OF OUR WORLD.\nnpc CASTLE 4 15 0 7c4c14 d82800 603008 0 0 SHOP 0 KEYS KEYMAKER: KEYS, TORCHES, WINGS.\nshop T1ITEMS HERB ANTIDOTE TORCH WINGS\nshop T1GEAR CLUB COPPER_SWORD CLOTHES LEATHER_VEST\nshop T2ITEMS HERB TONIC ANTIDOTE TORCH WINGS\nshop T2GEAR COPPER_SWORD IRON_AXE LEATHER_VEST CHAIN_MAIL\nshop KEYS BRONZE_KEY TORCH WINGS HERB\nboss CAVE3 19 16 SHARD_TYRANT\nspawn FIELD 30 32\nportal FIELD 30 31\nnews A STAR FELL BEYOND STONEHOLM.\nnews THE ARKS SAIL AT DUSK.\nnews LUCKY DRIPS WERE SEEN IN THE MEADOW.\n";
  drawFrame(); requestAnimationFrame(animate);
  const initialSeed = new URLSearchParams(location.search).get('seed') || '7';
  $('seed').value = initialSeed; loadSeed(initialSeed);
})();
