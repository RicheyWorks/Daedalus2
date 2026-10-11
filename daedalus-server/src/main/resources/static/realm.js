// SPDX-License-Identifier: MIT
// Daedalus Realm (ADR-018). Reads GET /world/{id}/chunks + /chunk/blocks, meshes each 16³ chunk
// with hidden-face culling, and writes cubes through PUT/DELETE /world/{id}/block — the same
// endpoints the well and the automation driver use, so the server stays the only authority.
// Live: STOMP /topic/world/{id}/events. A BLOCK_PLACED/REMOVED frame patches one cube and
// remeshes its chunk; a WORLD_REVISION_CHANGED frame typed ISLAND refetches the lane.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const WORLD = "world-zero";
const API = "/api/v1/world/" + WORLD;
const SIZE = 16;
const TOKEN_KEY = "daedalus.token"; // shared with the well, so a sign-in there carries here

// Display colours per BlockType name. The server sends the palette (names in ordinal order);
// unknown names render as stone, so a newer server never breaks an older page.
const COLORS = {
  STONE: 0x7d7b84, DIRT: 0x7a5230, WOOD: 0x9a6b3f, GLASS: 0xa8d8e8, GRASS: 0x6cc046,
  SAND: 0xe2d08c, WATER: 0x2f80d8, LOG: 0x7a5232, LEAVES: 0x4aa44f, BLOSSOM: 0xf29bc0,
  GRAVEL: 0x9b9387, CRYSTAL: 0xa070ff, CLOUD: 0xf4f6fb,
};
const SEE_THROUGH = new Set(["AIR", "GLASS", "WATER", "CLOUD"]);
const TRANSLUCENT = new Set(["GLASS", "WATER"]);
const BUILDABLE = ["GRASS", "DIRT", "STONE", "WOOD", "LOG", "LEAVES", "BLOSSOM", "SAND",
  "GRAVEL", "GLASS", "WATER", "CRYSTAL", "CLOUD"];

const state = {
  palette: ["AIR"],          // ordinal → name, from the server
  chunks: new Map(),         // "cx,cy,cz" → Uint8Array(4096)
  meshes: new Map(),         // "cx,cy,cz" → THREE.Group
  revision: 0,
  islands: [],
  arks: [],                  // from GET /arks (ADR-019)
  arkModels: new Map(),      // ark id → THREE.Group placed at its berth
  species: [],               // the canon, from GET /species (ADR-021)
  clockOffset: 0,            // server epoch − local epoch, from /arks and ark frames (ADR-020)
  richness: new Map(),       // island slot → kinds living there (ADR-024)
  day: 0,                    // the ecology's latest day
  lifeSlot: null,            // the island whose Life panel is open
  mode: "look",
  block: "GRASS",
  token: safeGet(TOKEN_KEY),
  stomp: null,
  live: false,
};

function safeGet(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
function safeSet(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* private mode */ } }

// ---------------------------------------------------------------- scene
const canvas = document.getElementById("view");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = skyTexture();
scene.fog = new THREE.Fog(0x9fb8d8, 140, 420);
const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 2000);
camera.position.set(40, 90, -30);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.target.set(0, 40, -96);
controls.maxDistance = 600;
scene.add(new THREE.HemisphereLight(0xe8f0ff, 0x6b5a44, 1.5));
scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const sun = new THREE.DirectionalLight(0xfff0d8, 1.9);
sun.position.set(90, 160, 120);
scene.add(sun);
const opaqueMat = new THREE.MeshLambertMaterial({ vertexColors: true });
const glassMat = new THREE.MeshLambertMaterial({ vertexColors: true, transparent: true,
  opacity: 0.62, depthWrite: false });
const hover = new THREE.LineSegments(
  new THREE.EdgesGeometry(new THREE.BoxGeometry(1.02, 1.02, 1.02)),
  new THREE.LineBasicMaterial({ color: 0xf5c14a }));
hover.visible = false;
scene.add(hover);

function skyTexture() {
  const c = document.createElement("canvas");
  c.width = 2; c.height = 256;
  const g = c.getContext("2d");
  const grad = g.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, "#1f3f86");
  grad.addColorStop(0.55, "#8fa9d6");
  grad.addColorStop(1, "#f2b98a");
  g.fillStyle = grad;
  g.fillRect(0, 0, 2, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

// ---------------------------------------------------------------- world model
const key = (cx, cy, cz) => cx + "," + cy + "," + cz;
const idx = (lx, ly, lz) => lx + SIZE * (ly + SIZE * lz);
const div = (a) => Math.floor(a / SIZE);
const mod = (a) => ((a % SIZE) + SIZE) % SIZE;

function nameAt(x, y, z) {
  const data = state.chunks.get(key(div(x), div(y), div(z)));
  if (!data) return "AIR";
  return state.palette[data[idx(mod(x), mod(y), mod(z))]] || "STONE";
}

function setLocal(x, y, z, name) {
  const k = key(div(x), div(y), div(z));
  let data = state.chunks.get(k);
  if (!data) { data = new Uint8Array(SIZE * SIZE * SIZE); state.chunks.set(k, data); }
  const ord = state.palette.indexOf(name);
  data[idx(mod(x), mod(y), mod(z))] = ord < 0 ? 0 : ord;
}

// ---------------------------------------------------------------- meshing
const FACES = [
  { n: [1, 0, 0], shade: 0.86, c: [[1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 1]] },
  { n: [-1, 0, 0], shade: 0.86, c: [[0, 0, 1], [0, 1, 1], [0, 1, 0], [0, 0, 0]] },
  { n: [0, 1, 0], shade: 1.0, c: [[0, 1, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0]] },
  { n: [0, -1, 0], shade: 0.62, c: [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]] },
  { n: [0, 0, 1], shade: 0.94, c: [[1, 0, 1], [1, 1, 1], [0, 1, 1], [0, 0, 1]] },
  { n: [0, 0, -1], shade: 0.78, c: [[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]] },
];

function jitter(x, y, z) {
  let h = (x * 374761393 + y * 668265263 + z * 2147483647) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return 0.94 + (((h ^ (h >>> 16)) >>> 0) % 1000) / 1000 * 0.12;
}

function buildChunk(cx, cy, cz) {
  const k = key(cx, cy, cz);
  const old = state.meshes.get(k);
  if (old) {
    scene.remove(old);
    old.children.forEach(m => m.geometry.dispose());
    state.meshes.delete(k);
  }
  const data = state.chunks.get(k);
  if (!data) return;
  const buf = { solid: { p: [], n: [], c: [], i: [] }, glass: { p: [], n: [], c: [], i: [] } };
  const col = new THREE.Color();
  const ox = cx * SIZE, oy = cy * SIZE, oz = cz * SIZE;
  for (let lz = 0; lz < SIZE; lz++) for (let ly = 0; ly < SIZE; ly++) for (let lx = 0; lx < SIZE; lx++) {
    const name = state.palette[data[idx(lx, ly, lz)]] || "STONE";
    if (name === "AIR") continue;
    const x = ox + lx, y = oy + ly, z = oz + lz;
    const target = TRANSLUCENT.has(name) ? buf.glass : buf.solid;
    for (const f of FACES) {
      const nb = nameAt(x + f.n[0], y + f.n[1], z + f.n[2]);
      // A face is hidden by an opaque neighbour, or by more of the same see-through stuff.
      if (!SEE_THROUGH.has(nb) || nb === name) continue;
      col.setHex(COLORS[name] ?? COLORS.STONE).convertSRGBToLinear();
      const s = f.shade * jitter(x, y, z);
      const base = target.p.length / 3;
      for (const v of f.c) {
        target.p.push(x + v[0], y + v[1], z + v[2]);
        target.n.push(f.n[0], f.n[1], f.n[2]);
        target.c.push(col.r * s, col.g * s, col.b * s);
      }
      target.i.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
  }
  const group = new THREE.Group();
  for (const [part, mat] of [[buf.solid, opaqueMat], [buf.glass, glassMat]]) {
    if (!part.i.length) continue;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(part.p, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(part.n, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(part.c, 3));
    g.setIndex(part.i);
    g.computeBoundingSphere();
    const mesh = new THREE.Mesh(g, mat);
    mesh.renderOrder = mat === glassMat ? 1 : 0;
    group.add(mesh);
  }
  group.userData.chunk = k;
  scene.add(group);
  state.meshes.set(k, group);
}

function remeshAround(x, y, z) {
  const cx = div(x), cy = div(y), cz = div(z);
  const todo = new Set([key(cx, cy, cz)]);
  const lx = mod(x), ly = mod(y), lz = mod(z);
  if (lx === 0) todo.add(key(cx - 1, cy, cz));
  if (lx === SIZE - 1) todo.add(key(cx + 1, cy, cz));
  if (ly === 0) todo.add(key(cx, cy - 1, cz));
  if (ly === SIZE - 1) todo.add(key(cx, cy + 1, cz));
  if (lz === 0) todo.add(key(cx, cy, cz - 1));
  if (lz === SIZE - 1) todo.add(key(cx, cy, cz + 1));
  for (const k of todo) {
    const [a, b, c] = k.split(",").map(Number);
    if (state.chunks.has(k)) buildChunk(a, b, c);
  }
}

// ---------------------------------------------------------------- REST
async function api(path, opts = {}) {
  const headers = Object.assign({ "Accept": "application/json" }, opts.headers || {});
  if (opts.body) headers["Content-Type"] = "application/json";
  if (state.token) headers.Authorization = "Bearer " + state.token;
  const res = await fetch(path, Object.assign({}, opts, { headers }));
  if (res.status === 401 || res.status === 403) {
    const err = new Error("sign in to build");
    err.auth = true;
    throw err;
  }
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) { /* not json */ }
    throw new Error(detail);
  }
  return res.json();
}

function decode(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function loadWorld() {
  const list = await api(API + "/chunks");
  state.revision = list.revision;
  const rows = list.chunks;
  let next = 0;
  async function worker() {
    while (next < rows.length) {
      const r = rows[next++];
      const c = await api(`${API}/chunk/blocks?x=${r.x}&y=${r.y}&z=${r.z}`);
      state.palette = c.palette;
      if (c.present) state.chunks.set(key(c.x, c.y, c.z), decode(c.data));
    }
  }
  await Promise.all([worker(), worker(), worker(), worker(), worker(), worker()]);
  for (const k of state.chunks.keys()) {
    const [a, b, c] = k.split(",").map(Number);
    buildChunk(a, b, c);
  }
  status();
  return rows.length;
}

async function loadIslands(focusSlot) {
  const res = await api(API + "/islands");
  state.islands = res.islands;
  const host = document.getElementById("islands");
  host.textContent = "";
  if (!state.islands.length) {
    const p = document.createElement("div");
    p.className = "isle";
    p.innerHTML = "<div>No islands yet. Pick a seed and press <b>Raise</b>.</div>";
    host.appendChild(p);
  }
  for (const isle of state.islands) {
    const row = document.createElement("div");
    row.className = "isle";
    const info = document.createElement("div");
    info.innerHTML = `<b>Isle ${isle.slot}</b> · seed ${isle.seed}<br>` +
      `${isle.trees} trees (${isle.blossomTrees} blossom) · ${isle.columns} cols` +
      (isle.waterfall ? " · waterfall" : "") + ` · ${isle.crystals} crystals`;
    const kinds = document.createElement("span");
    kinds.className = "kinds-count";
    kinds.dataset.slot = isle.slot;
    info.append(document.createElement("br"), kinds);
    const go = document.createElement("button");
    go.className = "go";
    go.textContent = "Go";
    go.onclick = () => { if (RIDE.id) toggleRide(RIDE.id); flyTo(isle); };
    const life = document.createElement("button");
    life.className = "life-btn" + (state.lifeSlot === isle.slot ? " on" : "");
    life.dataset.slot = isle.slot;
    life.textContent = "Life";
    life.onclick = () => toggleLife(isle.slot);
    row.append(info, life, go);
    host.appendChild(row);
  }
  renderRichness();
  Promise.all(state.islands.map(i => api(`${API}/islands/${i.slot}/ecology`)
    .then(r => { state.richness.set(i.slot, r.richness); state.day = Math.max(state.day, r.day); })
    .catch(() => {}))).then(renderRichness);
  status();
  if (focusSlot !== undefined) {
    const isle = state.islands.find(i => i.slot === focusSlot);
    if (isle) flyTo(isle);
  }
}

// ---------------------------------------------------------------- island life (ADR-023/024)
const GUILD_COLORS = { MEADOW: "#7ccf52", CANOPY: "#2f9e5a", POND: "#3a8ee6", DECOMPOSER: "#a3784c",
  STARBORN: "#a070ff", MARINE: "#2bc6c6", UNKNOWN: "#888" };
function renderRichness() {
  document.querySelectorAll(".kinds-count").forEach(el => {
    const n = state.richness.get(Number(el.dataset.slot));
    el.textContent = n === undefined ? "" : (n ? `${n} kind${n === 1 ? "" : "s"} living` : "barren — waiting for an ark");
  });
}
function toggleLife(slot) {
  state.lifeSlot = state.lifeSlot === slot ? null : slot;
  document.querySelectorAll(".life-btn").forEach(b => b.classList.toggle("on", Number(b.dataset.slot) === state.lifeSlot));
  loadLife();
}
let lifeSeq = 0;
async function loadLife() {
  const host = document.getElementById("life");
  const seq = ++lifeSeq;                         // frames can overlap fetches; only the newest renders
  if (state.lifeSlot === null) { host.textContent = ""; host.style.display = "none"; return; }
  const slot = state.lifeSlot;
  let res;
  try { res = await api(`${API}/islands/${slot}/ecology`); } catch (e) { handleError(e); return; }
  if (seq !== lifeSeq || state.lifeSlot !== slot) return;
  state.richness.set(slot, res.richness);
  state.day = Math.max(state.day, res.day);
  renderRichness();
  host.style.display = "block";
  host.textContent = "";
  const head = document.createElement("div");
  head.className = "life-head";
  head.dataset.day = res.day;
  head.innerHTML = `<b>Isle ${slot}</b> · day <span class="day">${res.day}</span><br>` +
    `<span>${res.richness} kinds · ${Math.round(res.total)} individuals · H′ ${res.shannon.toFixed(2)} · ` +
    `evenness ${res.evenness.toFixed(2)}</span>`;
  host.appendChild(head);
  if (!res.species.length) {
    const p = document.createElement("div");
    p.className = "note";
    p.textContent = "Nothing lives here yet. Sail an ark in — or wait for wings and spores on the wind.";
    host.appendChild(p);
    return;
  }
  const top = Math.log10(1 + res.species[0].count);
  for (const sp of res.species) {
    const row = document.createElement("div");
    row.className = "kind life-row";
    row.dataset.key = sp.key;
    const pct = Math.max(4, Math.round(100 * Math.log10(1 + sp.count) / top));
    row.innerHTML = `<b>${sp.name}</b> <span>${sp.guild.toLowerCase()} · ${Math.round(sp.count)}</span>` +
      `<i style="width:${pct}%;background:${GUILD_COLORS[sp.guild] || GUILD_COLORS.UNKNOWN}"></i>`;
    host.appendChild(row);
  }
}
function speciesName(key) {
  const sp = state.species.find(s => s.key === key);
  return sp ? sp.name : key;
}
function namesOf(keys) {
  const names = keys.map(speciesName);
  return names.length > 3 ? `${names.slice(0, 3).join(", ")} and ${names.length - 3} more` : names.join(", ");
}
function onLifeFrame(f) {
  state.clockOffset = f.now - Date.now();
  state.day = Math.max(state.day, f.day);
  for (const [slot, n] of Object.entries(f.richness || {})) state.richness.set(Number(slot), n);
  renderRichness();
  const ark = state.arks.find(a => a.id === f.arkId);
  if (f.kind === "LANDED") {
    toast(`${ark ? ark.name : f.arkId} put ${namesOf(f.keys)} ashore on Isle ${f.slot}`);
    loadArks();
  } else if (f.kind === "BOARDED") {
    toast(`Stowaways aboard ${ark ? ark.name : f.arkId}: ${namesOf(f.keys)}`);
    loadArks();
  }
  if (state.lifeSlot !== null && (f.kind === "DAY" || f.slot === state.lifeSlot)) loadLife();
}

// ---------------------------------------------------------------- bestiary (ADR-021)
const GUILD_NOTES = {
  MEADOW: "grass and scrub", CANOPY: "trees", POND: "pond and stream", DECOMPOSER: "soil and deadwood",
  STARBORN: "fell with the meteor; lives on the crystals", MARINE: "the sea fell away — no island holds them yet",
};
async function loadSpecies() {
  const res = await api("/api/v1/species");
  state.species = res.species;
  const host = document.getElementById("bestiary");
  host.textContent = "";
  const chips = document.createElement("div");
  chips.className = "chips";
  const list = document.createElement("div");
  list.className = "kinds";
  for (const [guild, n] of Object.entries(res.guilds)) {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.dataset.guild = guild;
    chip.textContent = `${guild.toLowerCase()} ${n}`;
    chip.onclick = () => {
      const open = chip.classList.toggle("on");
      chips.querySelectorAll(".chip").forEach(c => { if (c !== chip) c.classList.remove("on"); });
      list.textContent = "";
      if (!open) return;
      const note = document.createElement("div");
      note.className = "note";
      note.textContent = GUILD_NOTES[guild] || "";
      list.appendChild(note);
      for (const sp of state.species.filter(x => x.guild === guild)) {
        const row = document.createElement("div");
        row.className = "kind";
        row.innerHTML = `<b>${sp.name}</b> <span>${sp.size.toLowerCase()} · ${sp.strategy}-selected` +
          `${sp.disperses ? " · flies or drifts" : " · needs an ark"}${sp.rarity === "LEGENDARY" ? " · legendary" : ""}</span>`;
        list.appendChild(row);
      }
    };
    chips.appendChild(chip);
  }
  host.append(chips, list);
}

// ---------------------------------------------------------------- arks (ADR-019)
// One model, cloned per ark. Its origin is deck level with the bow on +X. At a berth it lies
// side-on across the pier tip — beam toward the island, bow along +X, parallel to the rim — so a
// 23-cube hull never reaches back into the terrain the way a pier-parallel mooring did.
const ARK_SCALE = 0.6;
const ARK_STANDOFF = 9;      // pier tip → hull centreline: half beam plus wing, scaled
let arkTemplate = null;
let arkTemplateLoad = null;
function loadArkModel() {
  if (!arkTemplateLoad) {
    arkTemplateLoad = new GLTFLoader().loadAsync("/models/ark.glb").then(g => {
      g.scene.traverse(o => {
        if (o.isMesh) {
          o.material = new THREE.MeshLambertMaterial({ vertexColors: true });
          if (o.name.includes("Lamps")) o.material.emissive = new THREE.Color(0x6b4a12);
        }
      });
      arkTemplate = g.scene;
      return arkTemplate;
    });
  }
  return arkTemplateLoad;
}

function labelSprite(text) {
  const c = document.createElement("canvas");
  c.width = 512; c.height = 96;
  const g = c.getContext("2d");
  g.font = "600 44px system-ui, sans-serif";
  const w = Math.min(500, g.measureText(text).width + 40);
  g.fillStyle = "rgba(22,18,14,0.78)";
  g.beginPath(); g.roundRect((512 - w) / 2, 14, w, 68, 18); g.fill();
  g.fillStyle = "#f5c14a"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(text, 256, 49);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false }));
  sprite.scale.set(16, 3, 1);
  sprite.renderOrder = 5;
  return sprite;
}

const CRUISE = 16;           // cubes an ark climbs above the straight line between berths
const RIDE = { id: null, last: null };

function mooring(slot) {
  const isle = state.islands.find(i => i.slot === slot);
  if (!isle) return null;
  return new THREE.Vector3(isle.dockX + 0.5, isle.dockY + 1, isle.dockZ + ARK_STANDOFF);
}

function serverNow() { return Date.now() + state.clockOffset; }

/** Where an ark is and which way it faces, on server time (ADR-020). */
function arkPose(ark, now) {
  if (ark.state !== "SAILING") {
    return { pos: mooring(ark.slot) || new THREE.Vector3(ark.x + 0.5, ark.y, ark.z + ARK_STANDOFF), yaw: 0, t: 1 };
  }
  const a = mooring(ark.fromSlot), b = mooring(ark.toSlot);
  if (!a || !b) return { pos: new THREE.Vector3(ark.x, ark.y, ark.z), yaw: 0, t: 1 };
  const t = Math.min(1, Math.max(0, (now - ark.departAt) / (ark.arriveAt - ark.departAt)));
  const e = t * t * (3 - 2 * t);
  const pos = a.clone().lerp(b, e);
  pos.y += Math.sin(Math.PI * t) * CRUISE;
  const heading = Math.atan2(-(b.z - a.z), b.x - a.x);
  // Turn toward the destination while casting off, back to the berth heading while tying up.
  const turn = Math.min(1, t * 6, (1 - t) * 6);
  return { pos, yaw: heading * turn, t };
}

async function loadArks() {
  const res = await api(API + "/arks");
  state.clockOffset = res.now - Date.now();
  state.arks = res.arks;
  const template = await loadArkModel();
  const seen = new Set();
  for (const ark of state.arks) {
    seen.add(ark.id);
    let model = state.arkModels.get(ark.id);
    if (!model) {
      model = new THREE.Group();
      const hull = template.clone(true);
      hull.scale.setScalar(ARK_SCALE);
      hull.name = "hull";
      model.add(hull);
      const label = labelSprite(ark.name);
      label.position.set(0, 22, 0);
      model.add(label);
      model.name = ark.id;
      scene.add(model);
      state.arkModels.set(ark.id, model);
    }
    model.userData.ark = ark;
  }
  for (const [id, model] of state.arkModels) {
    if (!seen.has(id)) { scene.remove(model); state.arkModels.delete(id); }
  }
  renderArkList();
  status();
}

function renderArkList() {
  const host = document.getElementById("arks");
  if (!host) return;
  host.textContent = "";
  for (const ark of state.arks) {
    const row = document.createElement("div");
    row.className = "isle ark";
    row.dataset.ark = ark.id;
    const info = document.createElement("div");
    const where = ark.state === "SAILING" ? `sailing Isle ${ark.fromSlot} → Isle ${ark.toSlot}` : `moored at Isle ${ark.slot}`;
    const held = (ark.hold || []).length;
    info.innerHTML = `<b>${ark.name}</b><br><span class="where">${where}</span><br>` +
      `<span class="hold">${held ? `carrying ${held} kind${held === 1 ? "" : "s"}` : "hold empty"}</span>`;
    if (held) info.title = ark.hold.map(h => `${h.name} ×${Math.round(h.count)}`).join("\n");
    const controls = document.createElement("div");
    controls.style.cssText = "flex:0 0 auto;display:flex;gap:6px;align-items:center";
    const pick = document.createElement("select");
    pick.className = "dest";
    pick.setAttribute("aria-label", "Destination for " + ark.name);
    for (const isle of state.islands) {
      if (isle.slot === ark.slot) continue;
      const o = document.createElement("option");
      o.value = isle.slot; o.textContent = "Isle " + isle.slot;
      pick.appendChild(o);
    }
    const sail = document.createElement("button");
    sail.className = "sail"; sail.textContent = "Sail";
    sail.disabled = ark.state === "SAILING" || !pick.options.length;
    sail.onclick = () => sailArk(ark.id, Number(pick.value));
    const ride = document.createElement("button");
    ride.className = "ride" + (RIDE.id === ark.id ? " on" : "");
    ride.textContent = RIDE.id === ark.id ? "Stop" : "Ride";
    ride.onclick = () => toggleRide(ark.id);
    if (pick.options.length && ark.state !== "SAILING") controls.append(pick, sail);
    controls.append(ride);
    row.append(info, controls);
    host.appendChild(row);
  }
}

async function sailArk(arkId, toSlot) {
  try {
    const res = await api(`${API}/arks/${arkId}/voyage`, { method: "POST", body: JSON.stringify({ toSlot }) });
    if (res.result === "SAILING") {
      applyArk(res.ark, res.now);
      toast(`${res.ark.name} cast off for Isle ${toSlot}`);
      if (!RIDE.id) toggleRide(arkId);
    } else {
      toast({ ALREADY_THERE: "Already moored there", UNDERWAY: "Already under way", NO_SUCH_ISLAND: "No island in that slot" }[res.result] || res.result);
    }
  } catch (e) {
    handleError(e);
  }
}

function applyArk(row, now) {
  if (now) state.clockOffset = now - Date.now();
  const i = state.arks.findIndex(a => a.id === row.id);
  if (i >= 0) state.arks[i] = row; else state.arks.push(row);
  const model = state.arkModels.get(row.id);
  if (model) model.userData.ark = row;
  renderArkList();
}

function toggleRide(arkId) {
  flight++;                 // a fly-to still running would drag the camera off the ark
  RIDE.id = RIDE.id === arkId ? null : arkId;
  RIDE.last = null;
  renderArkList();
}

function onArkFrame(f) {
  state.clockOffset = f.now - Date.now();
  const ark = state.arks.find(a => a.id === f.arkId);
  if (!ark) { loadArks(); return; }
  const isle = state.islands.find(i => i.slot === f.toSlot);
  const row = Object.assign({}, ark, f.kind === "DEPARTED"
    ? { state: "SAILING", slot: f.toSlot, fromSlot: f.fromSlot, toSlot: f.toSlot, departAt: f.departAt, arriveAt: f.arriveAt }
    : { state: "MOORED", slot: f.toSlot, fromSlot: -1, toSlot: -1, departAt: 0, arriveAt: 0 });
  if (isle) { row.x = isle.dockX; row.y = isle.dockY + 1; row.z = isle.dockZ; }
  applyArk(row);
  if (f.kind === "ARRIVED") toast(`${ark.name} tied up at Isle ${f.toSlot}`);
}

function moveArks(t) {
  const now = serverNow();
  for (const model of state.arkModels.values()) {
    const ark = model.userData.ark;
    if (!ark) continue;
    const pose = arkPose(ark, now);
    const phase = ark.homeSlot * 1.7;
    const bob = ark.state === "SAILING" ? 0.15 : 0.35;
    model.position.copy(pose.pos);
    model.position.y += Math.sin(t / 1400 + phase) * bob;
    const hull = model.getObjectByName("hull");
    if (hull) hull.rotation.set(0, pose.yaw, Math.sin(t / 1900 + phase) * 0.015);
    if (RIDE.id === ark.id) {
      if (RIDE.last) {
        const d = model.position.clone().sub(RIDE.last);
        camera.position.add(d);
        controls.target.add(d);
      } else {
        // Snap to a chase view once; afterwards only the ark's own motion moves the camera, so
        // the rider can still orbit around it. (A fly-to here fought the follow and lost the ark.)
        controls.target.copy(model.position);
        camera.position.copy(model.position).add(new THREE.Vector3(-34, 18, 34));
      }
      RIDE.last = model.position.clone();
    }
  }
}

let flight = 0;            // bumped by every fly-to and ride, so a stale fly-to stops itself
function flyTo(isle) {
  // While riding, the ark owns the camera. A late fly-to (an island raise finishing after its
  // STOMP reload already showed the island) used to land mid-ride and strand the camera.
  if (RIDE.id) return;
  const mine = ++flight;
  const t = new THREE.Vector3(isle.x, isle.y + 4, isle.z);
  const from = camera.position.clone();
  const to = new THREE.Vector3(isle.x + 46, isle.y + 38, isle.z + 46);
  const startT = controls.target.clone();
  const t0 = performance.now();
  function step(now) {
    if (mine !== flight) return;
    const k = Math.min(1, (now - t0) / 900);
    const e = k * k * (3 - 2 * k);
    camera.position.lerpVectors(from, to, e);
    controls.target.lerpVectors(startT, t, e);
    if (k < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

async function raiseIsland() {
  const field = document.getElementById("seed");
  const raw = field.value.trim();
  const seed = raw === "" ? Math.floor(Math.random() * 1e9) : Number(raw);
  if (!Number.isFinite(seed) || !Number.isInteger(seed)) { toast("Seed must be a whole number"); return; }
  try {
    toast("Raising island " + seed + "…");
    const res = await api(API + "/islands", { method: "POST", body: JSON.stringify({ seed }) });
    if (res.result !== "RAISED") { toast("Island lane is full"); return; }
    field.value = "";
    toast(`Isle ${res.island.slot} raised from seed ${seed}`);
    // The STOMP frame also triggers a reload; doing it here keeps a page without STOMP honest.
    await loadWorld();
    await loadIslands(res.island.slot);
    await loadArks();
  } catch (e) {
    handleError(e);
  }
}

async function writeBlock(x, y, z, name) {
  const before = nameAt(x, y, z);
  setLocal(x, y, z, name);           // optimistic; the server answer or its frame corrects it
  remeshAround(x, y, z);
  try {
    const res = name === "AIR"
      ? await api(`${API}/block?x=${x}&y=${y}&z=${z}`, { method: "DELETE" })
      : await api(API + "/block", { method: "PUT", body: JSON.stringify({ x, y, z, type: name }) });
    if (res.result === "DENIED") {
      setLocal(x, y, z, before);
      remeshAround(x, y, z);
      toast("That plot is not yours to change");
      return;
    }
    state.revision = Math.max(state.revision, res.revision);
    status();
  } catch (e) {
    setLocal(x, y, z, before);
    remeshAround(x, y, z);
    handleError(e);
  }
}

function handleError(e) {
  if (e.auth) { showLogin(); toast("Sign in to build"); return; }
  toast(e.message || String(e));
}

// ---------------------------------------------------------------- STOMP
function connectLive() {
  if (typeof Stomp === "undefined" || typeof SockJS === "undefined") { status(); return; }
  const client = Stomp.over(new SockJS("/ws"));
  client.debug = null;
  const headers = {};
  if (state.token) headers.Authorization = "Bearer " + state.token;
  client.connect(headers, () => {
    state.live = true;
    state.stomp = client;
    status();
    client.subscribe(`/topic/world/${WORLD}/events`, f => onFrame(JSON.parse(f.body)));
    client.subscribe(`/topic/world/${WORLD}/arks`, f => onArkFrame(JSON.parse(f.body)));
    client.subscribe(`/topic/world/${WORLD}/ecology`, f => onLifeFrame(JSON.parse(f.body)));
  }, () => {
    state.live = false;
    status();
    setTimeout(connectLive, 3000);
  });
}

let reloadQueued = false;
function onFrame(ev) {
  state.revision = Math.max(state.revision, ev.revision || 0);
  if (ev.kind === "BLOCK_PLACED" || ev.kind === "BLOCK_REMOVED") {
    const now = ev.kind === "BLOCK_REMOVED" ? "AIR" : ev.type;
    if (nameAt(ev.x, ev.y, ev.z) !== now) {
      setLocal(ev.x, ev.y, ev.z, now);
      remeshAround(ev.x, ev.y, ev.z);
    }
  } else if (ev.kind === "WORLD_REVISION_CHANGED" && ev.type === "ISLAND" && !reloadQueued) {
    reloadQueued = true;
    setTimeout(async () => {
      reloadQueued = false;
      await loadWorld();
      await loadIslands();
      await loadArks();
    }, 150);
  }
  status();
}

// ---------------------------------------------------------------- input
const ray = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let down = null;

function pick(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  pointer.set(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
  ray.setFromCamera(pointer, camera);
  const targets = [];
  state.meshes.forEach(g => g.children.forEach(m => targets.push(m)));
  const hit = ray.intersectObjects(targets, false)[0];
  if (!hit) return null;
  const n = hit.face.normal;
  // Locate the cube from the hit triangle's centroid, not the hit point: a ray that lands exactly
  // on a cube edge (the camera's integer diagonal does this at screen centre) puts the hit point on
  // an integer boundary where floor() picks the neighbour. A triangle's centroid is strictly inside
  // its face, so stepping half a cube back along the normal always lands in the cube that owns it.
  const pos = hit.object.geometry.attributes.position;
  const centroid = new THREE.Vector3()
    .add(new THREE.Vector3().fromBufferAttribute(pos, hit.face.a))
    .add(new THREE.Vector3().fromBufferAttribute(pos, hit.face.b))
    .add(new THREE.Vector3().fromBufferAttribute(pos, hit.face.c))
    .multiplyScalar(1 / 3);
  const inside = centroid.addScaledVector(n, -0.5);
  const at = { x: Math.floor(inside.x), y: Math.floor(inside.y), z: Math.floor(inside.z) };
  return { at, next: { x: at.x + Math.round(n.x), y: at.y + Math.round(n.y), z: at.z + Math.round(n.z) },
    point: hit.point.toArray(), normal: n.toArray(), name: nameAt(at.x, at.y, at.z) };
}

canvas.addEventListener("pointerdown", e => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
canvas.addEventListener("pointermove", e => {
  if (state.mode === "look" || e.pointerType === "touch") { hover.visible = false; return; }
  const p = pick(e.clientX, e.clientY);
  hover.visible = !!p;
  if (p) {
    const c = state.mode === "build" ? p.next : p.at;
    hover.position.set(c.x + 0.5, c.y + 0.5, c.z + 0.5);
  }
});
canvas.addEventListener("pointerup", e => {
  if (!down) return;
  const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
  const quick = performance.now() - down.t < 450;
  down = null;
  if (moved > 8 || !quick || state.mode === "look") return; // a drag is a camera move
  const p = pick(e.clientX, e.clientY);
  if (!p) return;
  if (state.mode === "build") writeBlock(p.next.x, p.next.y, p.next.z, state.block);
  else if (state.mode === "break") writeBlock(p.at.x, p.at.y, p.at.z, "AIR");
});
canvas.addEventListener("contextmenu", e => e.preventDefault());

function setMode(m) {
  state.mode = m;
  for (const [id, mode] of [["modeLook", "look"], ["modeBuild", "build"], ["modeBreak", "break"]]) {
    document.getElementById(id).classList.toggle("on", mode === m);
  }
  hover.visible = false;
  hover.material.color.setHex(m === "break" ? 0xff5a5f : 0xf5c14a);
}
document.getElementById("modeLook").onclick = () => setMode("look");
document.getElementById("modeBuild").onclick = () => setMode("build");
document.getElementById("modeBreak").onclick = () => setMode("break");
document.getElementById("raise").onclick = raiseIsland;
document.getElementById("seed").addEventListener("keydown", e => { if (e.key === "Enter") raiseIsland(); });

function buildPalette() {
  const host = document.getElementById("palette");
  BUILDABLE.forEach((name, i) => {
    const b = document.createElement("button");
    b.className = "swatch" + (name === state.block ? " on" : "");
    b.title = name + (i < 9 ? ` (${i + 1})` : "");
    const sw = document.createElement("i");
    sw.style.background = "#" + (COLORS[name] ?? 0x888888).toString(16).padStart(6, "0");
    const label = document.createElement("span");
    label.textContent = name.toLowerCase();
    b.append(sw, label);
    b.onclick = () => selectBlock(name);
    host.appendChild(b);
  });
}
function selectBlock(name) {
  state.block = name;
  document.querySelectorAll(".swatch").forEach(s => s.classList.toggle("on", s.title.startsWith(name)));
  if (state.mode === "look") setMode("build");
}
window.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT") return;
  if (e.key === "l" || e.key === "L") setMode("look");
  if (e.key === "b" || e.key === "B") setMode("build");
  if (e.key === "x" || e.key === "X") setMode("break");
  const n = Number(e.key);
  if (n >= 1 && n <= 9 && BUILDABLE[n - 1]) selectBlock(BUILDABLE[n - 1]);
});

// ---------------------------------------------------------------- HUD
let toastTimer = 0;
function toast(text) {
  const t = document.getElementById("toast");
  t.textContent = text;
  t.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.style.display = "none"; }, 2600);
}

function status() {
  document.getElementById("dot").classList.toggle("on", state.live);
  const cubes = [...state.chunks.values()].reduce((a, d) => a + d.reduce((s, v) => s + (v ? 1 : 0), 0), 0);
  document.getElementById("statusText").textContent =
    `${state.live ? "live" : "offline"} · revision ${state.revision} · ${state.chunks.size} chunks · ` +
    `${cubes.toLocaleString()} cubes · ${state.islands.length} islands · ${state.arks.length} arks`;
}

function showLogin() { document.getElementById("login").style.display = "block"; }
document.getElementById("loginCancel").onclick = () => { document.getElementById("login").style.display = "none"; };
document.getElementById("loginGo").onclick = async () => {
  const username = document.getElementById("user").value.trim();
  const password = document.getElementById("pass").value;
  try {
    const res = await fetch("/api/v1/auth/login", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
    if (!res.ok) throw new Error("Sign-in refused");
    const body = await res.json();
    state.token = body.token;
    safeSet(TOKEN_KEY, body.token);
    safeSet("daedalus.user", username);
    document.getElementById("login").style.display = "none";
    toast("Signed in as " + username);
    if (state.stomp) { try { state.stomp.disconnect(); } catch (e) { /* closing */ } }
    connectLive();
  } catch (e) {
    toast(e.message);
  }
};

// ---------------------------------------------------------------- go
function frame(t) {
  controls.update();
  moveArks(t || 0);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
buildPalette();
frame();
window.daedalusRealm = state; // for the browser harness and curious operators
state.pick = pick;           // the exact pick the pointer uses, so a harness can ask what a tap hits
state.debugTarget = () => controls.target.clone();
state.project = (x, y, z) => {  // screen pixel of a world point, for a harness to tap a cube
  const v = new THREE.Vector3(x, y, z).project(camera), r = canvas.getBoundingClientRect();
  return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (1 - v.y) / 2 * r.height };
};
(async () => {
  try {
    await loadWorld();
    await loadIslands();
    await loadArks();
    await loadSpecies();
    if (state.islands.length) flyTo(state.islands[0]);
    status();
  } catch (e) {
    handleError(e);
  }
  connectLive();
})();
