// SPDX-License-Identifier: MIT
// Visitor rules. Server GalleryOps remains the source of land and ownership truth.
export const CITY = Object.freeze({ minX: -30, minZ: -158, side: 156, block: 24, street: 6 });
const AVENUES = ['Ash Lane', 'Pixel Street', 'Origin Way', 'Gallery Row', 'Voxel Avenue', 'Frame Road'];
const STREETS = ['North Rim', 'Canvas Street', 'Plinth Road', 'Easel Street', 'Lantern Way', 'South Rim'];
export const QUESTS = Object.freeze([
  { id: 'origin', title: 'Find the Origin', goal: 1, text: 'Reach the crystal spire that anchors this surviving fragment.' },
  { id: 'streets', title: 'Read the old city', goal: 3, text: 'Walk three different named streets. The city remembers its routes.' },
  { id: 'parcels', title: 'Meet the fragments', goal: 4, text: 'Inspect four addressed parcels and record their building limits.' },
  { id: 'art', title: 'Witness a memory', goal: 1, text: 'Study a maze artwork. Its paths echo the broken ground.' },
  { id: 'echoes', title: 'Gather the three echoes', goal: 3, text: 'Find the amber, tide and bloom memory markers around the city.' },
  { id: 'return', title: 'Light the memory mosaic', goal: 1, text: 'Bring all three echoes back to the Origin spire.' },
  { id: 'drone', title: 'Prepare the next crossing', goal: 1, text: 'After restoring the mosaic, visit the drone pad beside the spire.' }
]);

function hash(value) {
  let h = 2166136261;
  for (const c of String(value)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

export function visitorCity(seed = '7') {
  const streets = [];
  for (let i = 0; i < 6; i++) {
    const x = CITY.minX + i * 30 + 3, z = CITY.minZ + i * 30 + 3;
    streets.push({ name: AVENUES[i], x1: x, z1: CITY.minZ, x2: x, z2: CITY.minZ + 155 });
    streets.push({ name: STREETS[i], x1: CITY.minX, z1: z, x2: CITY.minX + 155, z2: z });
  }
  const parcels = [];
  for (let bz = 0; bz < 5; bz++) for (let bx = 0; bx < 5; bx++) {
    if (bx === 2 && bz === 2) continue;
    const x = CITY.minX + 6 + bx * 30, z = CITY.minZ + 6 + bz * 30;
    const cuts = [[0, 0, 12, 12], [12, 0, 12, 12], [0, 12, 12, 12], [12, 12, 12, 12]];
    const pattern = (bx * 3 + bz * 5) % 3;
    const layout = pattern === 0 ? cuts : pattern === 1 ? [[0, 0, 24, 12], [0, 12, 24, 12]] : [[0, 0, 12, 24], [12, 0, 12, 24]];
    for (const [dx, dz, w, d] of layout) {
      const n = parcels.length;
      const parcel = { n, minX: x + dx, minZ: z + dz, maxX: x + dx + w - 1, maxZ: z + dz + d - 1,
        height: Math.max(Math.abs(bx - 2), Math.abs(bz - 2)) <= 1 ? 32 : 20,
        gallery: hash(`${seed}:${n}`) % 4 === 0, owner: '', builders: [], address: '' };
      const nearest = streets.map(s => ({ s, d: s.x1 === s.x2
        ? Math.min(Math.abs(s.x1 - parcel.minX), Math.abs(s.x1 - parcel.maxX))
        : Math.min(Math.abs(s.z1 - parcel.minZ), Math.abs(s.z1 - parcel.maxZ)) })).sort((a, b) => a.d - b.d)[0];
      parcel.address = `${n + 1} ${nearest.s.name}`;
      parcels.push(parcel);
    }
  }
  return { worldId: 'visitor-draft', seed: String(seed), plazaMinX: 36, plazaMinZ: -92, plazaMaxX: 59,
    plazaMaxZ: -69, padX: 48, padY: 1, padZ: -80, parcels, streets, source: 'draft' };
}

export function normalizeCity(body, seed) {
  if (!body || !Array.isArray(body.parcels) || !Array.isArray(body.streets) || body.parcels.length > 512) {
    throw new Error('The server returned an invalid Gallery City.');
  }
  const ints = ['plazaMinX', 'plazaMinZ', 'plazaMaxX', 'plazaMaxZ', 'padX', 'padZ'];
  if (ints.some(k => !Number.isSafeInteger(body[k]) || Math.abs(body[k]) > 100000)) throw new Error('Invalid city bounds.');
  if (body.plazaMinX > body.plazaMaxX || body.plazaMinZ > body.plazaMaxZ) throw new Error('Inverted plaza.');
  const ids = new Set();
  const parcels = body.parcels.map(p => {
    if (['n', 'minX', 'minZ', 'maxX', 'maxZ', 'height'].some(k => !Number.isSafeInteger(p[k])) ||
      ids.has(p.n) || p.n < 0 || p.minX > p.maxX || p.minZ > p.maxZ || p.height < 1 || p.height > 512 ||
      p.minX < CITY.minX || p.maxX >= CITY.minX + CITY.side || p.minZ < CITY.minZ || p.maxZ >= CITY.minZ + CITY.side) {
      throw new Error('Invalid parcel geometry.');
    }
    ids.add(p.n);
    return { ...p, address: String(p.address || `Parcel ${p.n}`).slice(0, 120), owner: String(p.owner || '').slice(0, 160),
      builders: Array.isArray(p.builders) ? p.builders.map(String).slice(0, 128) : [], gallery: p.gallery === true };
  });
  const streets = body.streets.map(s => {
    if (['x1', 'z1', 'x2', 'z2'].some(k => !Number.isSafeInteger(s[k]) || Math.abs(s[k]) > 100000)) throw new Error('Invalid street.');
    return { ...s, name: String(s.name).slice(0, 80) };
  });
  return { ...body, seed: String(seed), parcels, streets, source: 'server' };
}

export function parcelAt(city, x, z) {
  return city.parcels.find(p => x >= p.minX && x <= p.maxX && z >= p.minZ && z <= p.maxZ) || null;
}

export function walkable(city, x, z) {
  if (x < CITY.minX + 1 || x >= CITY.minX + CITY.side - 1 || z < CITY.minZ + 1 || z >= CITY.minZ + CITY.side - 1) return false;
  const p = parcelAt(city, x, z);
  // Buildings are a visitor-view silhouette, never a collision claim about server voxels.
  return !p || !(x >= p.minX + 2 && x <= p.maxX - 2 && z >= p.minZ + 2 && z <= p.maxZ - 2);
}

export function route(city, from, target) {
  const start = { x: Math.round(from.x), z: Math.round(from.z) };
  if (!walkable(city, start.x, start.z)) return [];
  let end = { x: Math.round(target.x), z: Math.round(target.z) };
  if (!walkable(city, end.x, end.z)) {
    let nearest = null, distance = Infinity;
    for (let dz = -16; dz <= 16; dz++) for (let dx = -16; dx <= 16; dx++) {
      const x = end.x + dx, z = end.z + dz, d = dx * dx + dz * dz;
      if (d < distance && walkable(city, x, z)) { nearest = { x, z }; distance = d; }
    }
    if (!nearest) return [];
    end = nearest;
  }
  const key = p => `${p.x},${p.z}`, todo = [start], previous = new Map([[key(start), null]]);
  let found = false;
  for (let head = 0; head < todo.length && head < CITY.side * CITY.side; head++) {
    const at = todo[head];
    if (at.x === end.x && at.z === end.z) { found = true; break; }
    for (const [dx, dz] of [[0, -1], [1, 0], [0, 1], [-1, 0]]) {
      const next = { x: at.x + dx, z: at.z + dz }, id = key(next);
      if (previous.has(id) || !walkable(city, next.x, next.z)) continue;
      previous.set(id, at); todo.push(next);
    }
  }
  if (!found) return [];
  const path = [];
  for (let p = end; previous.get(key(p)); p = previous.get(key(p))) path.push(p);
  return path.reverse();
}

export function echoMarkers(city) {
  return [{ id: 'amber', name: 'Amber echo', x: CITY.minX + 33, z: CITY.minZ + 33, color: '#ffcd7b' },
    { id: 'tide', name: 'Tide echo', x: CITY.minX + 123, z: CITY.minZ + 63, color: '#92d4fb' },
    { id: 'bloom', name: 'Bloom echo', x: CITY.minX + 63, z: CITY.minZ + 123, color: '#b5e5bc' }];
}

export function newJournal(city) {
  return { schemaVersion: 1, city: `${city.source}:${city.worldId}:${city.seed}`, x: city.padX, z: city.padZ,
    parcels: [], streets: [], echoes: [], art: [], origin: false, returned: false, drone: false, steps: 0 };
}

export function restoreJournal(city, saved) {
  const fresh = newJournal(city);
  if (!saved || saved.schemaVersion !== 1 || saved.city !== fresh.city ||
      !Number.isSafeInteger(saved.x) || !Number.isSafeInteger(saved.z) || !walkable(city, saved.x, saved.z)) return fresh;
  const parcelIds = new Set(city.parcels.map(p => p.n)), streetNames = new Set(city.streets.map(s => s.name));
  const clean = (list, valid, limit) => Array.isArray(list) ? [...new Set(list.filter(v => valid.has(v)))].slice(0, limit) : [];
  const result = { ...fresh, x: saved.x, z: saved.z, parcels: clean(saved.parcels, parcelIds, 512),
    streets: clean(saved.streets, streetNames, 32), echoes: clean(saved.echoes, new Set(['amber', 'tide', 'bloom']), 3),
    art: Array.isArray(saved.art) ? [...new Set(saved.art.filter(v => typeof v === 'string' && v.length < 120))].slice(0, 512) : [],
    origin: saved.origin === true, steps: Number.isSafeInteger(saved.steps) && saved.steps >= 0 ? saved.steps : 0 };
  result.returned = saved.returned === true && result.echoes.length === 3 && result.origin;
  result.drone = saved.drone === true && result.returned;
  return result;
}

export function observe(city, journal) {
  const events = [];
  const add = (field, value, message) => { if (!journal[field].includes(value)) { journal[field].push(value); events.push(message); } };
  for (const s of city.streets) {
    const d = s.x1 === s.x2 ? Math.abs(journal.x - s.x1) : Math.abs(journal.z - s.z1);
    if (d < 2.2) add('streets', s.name, `Recorded ${s.name}.`);
  }
  const centre = { x: (city.plazaMinX + city.plazaMaxX) / 2, z: (city.plazaMinZ + city.plazaMaxZ) / 2 };
  const distance = p => Math.hypot(journal.x - p.x, journal.z - p.z);
  if (distance(centre) < 7 && !journal.origin) { journal.origin = true; events.push('The Origin spire remembers the old planet.'); }
  for (const echo of echoMarkers(city)) if (distance(echo) < 3) add('echoes', echo.id, `Recovered the ${echo.name.toLowerCase()}.`);
  if (journal.echoes.length === 3 && distance(centre) < 7 && !journal.returned) {
    journal.returned = true; events.push('The memory mosaic glows. Three fragments tell one story.');
  }
  if (journal.returned && distance({ x: city.padX, z: city.padZ }) < 3 && !journal.drone) {
    journal.drone = true; events.push('The drone pad is ready. Your next realm awaits.');
  }
  return events;
}

export function questProgress(journal) {
  const counts = { origin: Number(journal.origin), streets: journal.streets.length, parcels: journal.parcels.length,
    art: journal.art.length, echoes: journal.echoes.length, return: Number(journal.returned), drone: Number(journal.drone) };
  return QUESTS.map(q => ({ ...q, count: Math.min(q.goal, counts[q.id]), done: counts[q.id] >= q.goal }));
}
