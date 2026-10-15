// SPDX-License-Identifier: MIT
// Daedalus Realm (ADR-018). Reads GET /world/{id}/chunks + /chunk/blocks, meshes each 16³ chunk
// with hidden-face culling, and writes cubes through PUT/DELETE /world/{id}/block — the same
// endpoints the well and the automation driver use, so the server stays the only authority.
// Live: STOMP /topic/world/{id}/events. A BLOCK_PLACED/REMOVED frame patches one cube and
// remeshes its chunk; a WORLD_REVISION_CHANGED frame typed ISLAND refetches the lane.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { meshChunk } from "/realm-mesh.js";
import "/controllers/daedalus-pad.js";          // shared controller layer (window.DaedalusPad), see docs/controllers.md

// Which world this page shows (ADR-030): ?world=<id>, World Zero by default.
const WORLD = (() => {
  try {
    const w = new URLSearchParams(location.search).get("world");
    return w && /^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$/.test(w) ? w : "world-zero";
  } catch (e) { return "world-zero"; }
})();
const API = "/api/v1/world/" + WORLD;
const SIZE = 16;
const TOKEN_KEY = "daedalus.token"; // shared with the well, so a sign-in there carries here
const NAME_KEY = "daedalus.realm.name"; // the name an open dev server knows you by (ADR-026)

// Display colours per BlockType name. The server sends the palette (names in ordinal order);
// unknown names render as stone, so a newer server never breaks an older page.
const COLORS = {
  STONE: 0x7d7b84, DIRT: 0x7a5230, WOOD: 0x9a6b3f, GLASS: 0xa8d8e8, GRASS: 0x6cc046,
  SAND: 0xe2d08c, WATER: 0x2f80d8, LOG: 0x7a5232, LEAVES: 0x4aa44f, BLOSSOM: 0xf29bc0,
  GRAVEL: 0x9b9387, CRYSTAL: 0xa070ff, CLOUD: 0xf4f6fb,
  // Sky gates (ADR-031): a rainbow's bands and the doorway in the clouds.
  RAINBOW_RED: 0xff4d4d, RAINBOW_ORANGE: 0xff9a3c, RAINBOW_YELLOW: 0xffe25a, RAINBOW_GREEN: 0x5ee07a,
  RAINBOW_BLUE: 0x4aa8ff, RAINBOW_VIOLET: 0xa66bff, PORTAL: 0xd7b8ff,
  // Parcels worlds (ADR-033): asphalt, sidewalks and plazas, the helipad.
  ROAD: 0x4a4d57, PAVING: 0xe4ddcf, HELIPAD: 0xf28c28,
  // Bricks worlds (ADR-034): the baseplate, bright bricks, the spawn pad and the obby's lava.
  BASEPLATE: 0xa3a2a5, BRICK_RED: 0xc4281c, BRICK_BLUE: 0x0d69ac, BRICK_YELLOW: 0xf5cd30,
  BRICK_GREEN: 0x4b974b, BRICK_WHITE: 0xf2f3f3, SPAWN: 0x1fb5b0, LAVA: 0xff3b1f,
  // Light (ADR-038): a street lamp's head, neon trim, a lit window.
  LAMP: 0xffd9a0, NEON_PINK: 0xff4fc8, NEON_CYAN: 0x4ff4ff, WINDOW_LIT: 0xffe7b0,
  // Lands (ADR-050): deep rock, the glowing heartstone core, ores by depth, the meteor's starmetal.
  DEEPSTONE: 0x4a4f5c, HEARTSTONE: 0xff8a3d, COAL_ORE: 0x34343a, COPPER_ORE: 0xc8703a, IRON_ORE: 0xc9b49c,
  GOLD_ORE: 0xf2c230, STARMETAL: 0x7fe3ff,
};
// Blocks that give off light: drawn unlit and brighter than white, so the bloom pass makes them glow.
const GLOW = new Set(["LAMP", "NEON_PINK", "NEON_CYAN", "WINDOW_LIT", "CRYSTAL", "LAVA", "HEARTSTONE", "STARMETAL"]);
const GLOW_GAIN = { LAMP: 3.2, NEON_PINK: 2.6, NEON_CYAN: 2.6, WINDOW_LIT: 2.4, CRYSTAL: 1.6, LAVA: 2.2, HEARTSTONE: 2.0, STARMETAL: 2.2 };
// Which texture-atlas tile each block wears (renderer only: the cubes and the export are unchanged).
const TILE = {
  STONE: 0, GRAVEL: 10, DIRT: 6, SAND: 6, GRASS: 4, LEAVES: 5, BLOSSOM: 5, WOOD: 2, LOG: 9,
  PAVING: 3, ROAD: 10, HELIPAD: 3, BASEPLATE: 11, CLOUD: 11, GLASS: 11, WATER: 8, CRYSTAL: 11,
  BRICK_RED: 1, BRICK_BLUE: 1, BRICK_YELLOW: 1, BRICK_GREEN: 1, BRICK_WHITE: 1, SPAWN: 11, LAVA: 8,
  LAMP: 11, NEON_PINK: 11, NEON_CYAN: 11, WINDOW_LIT: 7, PORTAL: 11,
  DEEPSTONE: 0, HEARTSTONE: 11, COAL_ORE: 10, COPPER_ORE: 10, IRON_ORE: 10, GOLD_ORE: 10, STARMETAL: 11,
};
// Studded tops: these cubes wear the bricks' studs on their upper face (ADR-034). Renderer only: the
// cubes, the export and the C++ mesher are unchanged, so a World Package's triangles still match.
const STUDDED = new Set(["BASEPLATE", "BRICK_RED", "BRICK_BLUE", "BRICK_YELLOW", "BRICK_GREEN", "BRICK_WHITE", "SPAWN"]);
const RAINBOW = ["RAINBOW_RED", "RAINBOW_ORANGE", "RAINBOW_YELLOW", "RAINBOW_GREEN", "RAINBOW_BLUE", "RAINBOW_VIOLET"];
const SEE_THROUGH = new Set(["AIR", "GLASS", "WATER", "CLOUD", "PORTAL", ...RAINBOW]);
const TRANSLUCENT = new Set(["GLASS", "WATER", "PORTAL", ...RAINBOW]);
const BUILDABLE = ["GRASS", "DIRT", "STONE", "WOOD", "LOG", "LEAVES", "BLOSSOM", "SAND",
  "GRAVEL", "GLASS", "WATER", "CRYSTAL", "CLOUD", "PAVING"];

const state = {
  palette: ["AIR"],          // ordinal → name, from the server
  chunks: new Map(),         // "cx,cy,cz" → Uint8Array(4096)
  meshes: new Map(),         // "cx,cy,cz" → THREE.Group
  revision: 0,
  islands: [],
  arks: [],                  // from GET /arks (ADR-019)
  gates: [],                 // this world's sky gates (ADR-031)
  hail: null,                // the ark coming up to the gate to meet you after a crossing
  arkModels: new Map(),      // ark id → THREE.Group placed at its berth
  species: [],               // the canon, from GET /species (ADR-021)
  clockOffset: 0,            // server epoch − local epoch, from /arks and ark frames (ADR-020)
  richness: new Map(),       // island slot → kinds living there (ADR-024)
  day: 0,                    // the ecology's latest day
  lifeSlot: null,            // the island whose Life panel is open
  creatures: new Map(),      // island slot → { sig, group, list } of creature models (ADR-025)
  loading: 0,                // world loads in flight; creatures are not placed during one
  mode: "look",
  block: "GRASS",
  token: safeGet(TOKEN_KEY),
  me: safeGet(TOKEN_KEY) ? (safeGet("daedalus.user") || "") : (safeGet(NAME_KEY) || ""),  // who builds (ADR-026)
  stomp: null,
  live: false,
};

function safeGet(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
function safeSet(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* private mode */ } }

// ---------------------------------------------------------------- scene
const canvas = document.getElementById("view");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;   // filmic: bright glow rolls off instead of clipping
renderer.toneMappingExposure = 1.0;
const scene = new THREE.Scene();
scene.background = skyTexture();
scene.fog = new THREE.Fog(0x9fb8d8, 140, 420);
const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 2000);
camera.position.set(40, 90, -30);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.target.set(0, 40, -96);
controls.maxDistance = 600;
const hemi = new THREE.HemisphereLight(0xe8f0ff, 0x6b5a44, 1.5);
scene.add(hemi);
const ambient = new THREE.AmbientLight(0xffffff, 0.55);
scene.add(ambient);
const sun = new THREE.DirectionalLight(0xfff0d8, 1.9);
sun.position.set(90, 160, 120);
scene.add(sun);

// ---------------------------------------------------------------- atmosphere (ADR-038)
// Bloom picks out what glows (lamps, neon, lit windows: colours above 1.0); ACES tone mapping keeps the rest.
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.55, 0.45, 0.92);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// The sky by hour: [hour, top colour, horizon colour, sun colour, sun strength, ambient, fog colour, exposure, bloom]
const SKY = [
  [0, "#05060f", "#1b1530", 0x8aa0ff, 0.15, 0.22, 0x141428, 0.95, 1.05],
  [5, "#1a1638", "#e7816a", 0xffb38a, 0.55, 0.42, 0x6a5878, 1.0, 0.8],
  [7, "#2f5aa8", "#f6c39a", 0xffe1bf, 1.4, 0.6, 0xb8bfd8, 1.0, 0.5],
  [12, "#1f3f86", "#9fbbe6", 0xfff0d8, 1.9, 0.75, 0x9fb8d8, 1.0, 0.45],
  [17, "#2d3f8a", "#f3a77a", 0xffc89a, 1.3, 0.6, 0xc9a7a0, 1.0, 0.55],
  [19, "#28205a", "#ff7a6a", 0xff9a7a, 0.6, 0.45, 0x5e4a6e, 1.0, 0.8],
  [21, "#0b0b22", "#3a2a5a", 0x9aa8ff, 0.2, 0.26, 0x1c1a34, 0.95, 1.0],
  [24, "#05060f", "#1b1530", 0x8aa0ff, 0.15, 0.22, 0x141428, 0.95, 1.05],
];
const ATMO = { hour: null, rain: false, glow: true, lastSky: null };
state.atmo = ATMO;

function currentHour() {
  if (ATMO.hour != null) return ATMO.hour;
  const d = new Date();
  return state.clockHour ?? (d.getHours() + d.getMinutes() / 60);
}

function mixHex(a, b, t) { return new THREE.Color(a).lerp(new THREE.Color(b), t); }

function applySky() {
  const h = ((currentHour() % 24) + 24) % 24;
  let i = 0;
  while (i < SKY.length - 2 && SKY[i + 1][0] <= h) i++;
  const A = SKY[i], B = SKY[i + 1], t = (h - A[0]) / (B[0] - A[0]);
  const lerp = (x, y) => x + (y - x) * t;
  const top = mixHex(A[1], B[1], t), horizon = mixHex(A[2], B[2], t);
  const sig = top.getHexString() + horizon.getHexString();
  if (sig !== ATMO.lastSky) {          // redraw the gradient only when it changed
    ATMO.lastSky = sig;
    const c = document.createElement("canvas");
    c.width = 2; c.height = 256;
    const g = c.getContext("2d");
    const grad = g.createLinearGradient(0, 0, 0, 256);
    grad.addColorStop(0, "#" + top.getHexString());
    grad.addColorStop(1, "#" + horizon.getHexString());
    g.fillStyle = grad;
    g.fillRect(0, 0, 2, 256);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    if (scene.background && scene.background.dispose) scene.background.dispose();
    scene.background = tex;
  }
  const angle = (h - 6) / 24 * Math.PI * 2;           // sunrise at 6, noon overhead
  sun.position.set(Math.cos(angle) * 200, Math.max(30, Math.sin(angle) * 220), 120);
  sun.color.copy(mixHex(A[3], B[3], t));
  sun.intensity = lerp(A[4], B[4]) * (ATMO.rain ? 0.6 : 1);
  ambient.intensity = lerp(A[5], B[5]);
  hemi.intensity = lerp(A[5], B[5]) * 2.2;
  const fog = mixHex(A[6], B[6], t);
  scene.fog.color.copy(fog);
  scene.fog.near = ATMO.rain ? 40 : 140;
  scene.fog.far = ATMO.rain ? 260 : 420;
  renderer.toneMappingExposure = lerp(A[7], B[7]);
  bloom.strength = ATMO.glow ? lerp(A[8], B[8]) : 0;
  ATMO.night = h < 6 || h >= 19.5;
}

// Street lamps light their surroundings: a small pool of point lights moved to the lamps nearest the camera.
const LAMP_LIGHTS = [];
for (let k = 0; k < 10; k++) {
  const l = new THREE.PointLight(0xffc98a, 0, 18, 1.6);
  scene.add(l);
  LAMP_LIGHTS.push(l);
}
const lamps = new Map();   // chunk key -> [[x, y, z], ...] lamp blocks, kept by buildChunk
function placeLampLights() {
  const cam = camera.position, all = [];
  for (const list of lamps.values()) for (const p of list) all.push(p);
  all.sort((a, b) => (a[0] - cam.x) ** 2 + (a[1] - cam.y) ** 2 + (a[2] - cam.z) ** 2
                   - ((b[0] - cam.x) ** 2 + (b[1] - cam.y) ** 2 + (b[2] - cam.z) ** 2));
  const on = ATMO.night ? 6 : 0.6;
  LAMP_LIGHTS.forEach((l, k) => {
    const p = all[k];
    l.intensity = p ? on : 0;
    if (p) l.position.set(p[0] + 0.5, p[1] - 0.2, p[2] + 0.5);
  });
  state.lampLights = LAMP_LIGHTS.filter(l => l.intensity > 0).length;
}

// Rain: streaks that fall around the camera and wrap, one instanced draw.
const RAIN_N = 2600;
const rain = new THREE.InstancedMesh(new THREE.BoxGeometry(0.03, 0.9, 0.03),
  new THREE.MeshBasicMaterial({ color: 0xaab8d8, transparent: true, opacity: 0.45, toneMapped: false }), RAIN_N);
rain.frustumCulled = false;
rain.visible = false;
const rainDrops = Array.from({ length: RAIN_N }, () => [Math.random() * 80 - 40, Math.random() * 60, Math.random() * 80 - 40]);
scene.add(rain);
const rainM = new THREE.Matrix4();
function moveRain(dt) {
  rain.visible = ATMO.rain;
  if (!ATMO.rain) return;
  const c = camera.position;
  for (let k = 0; k < RAIN_N; k++) {
    const d = rainDrops[k];
    d[1] -= dt * 0.045;
    if (d[1] < -20) d[1] += 60;
    rainM.makeTranslation(c.x + d[0], c.y + d[1], c.z + d[2]);
    rain.setMatrixAt(k, rainM);
  }
  rain.instanceMatrix.needsUpdate = true;
}
const ATLAS = atlasTexture();
const opaqueMat = new THREE.MeshLambertMaterial({ vertexColors: true, map: ATLAS });
const glassMat = new THREE.MeshLambertMaterial({ vertexColors: true, transparent: true,
  opacity: 0.62, depthWrite: false, map: ATLAS });
// Glowing blocks: unlit, colours above 1.0, so the bloom pass picks them out at night and in daylight alike.
const glowMat = new THREE.MeshBasicMaterial({ vertexColors: true, map: ATLAS, toneMapped: false });

/** The block texture atlas: 4 x 4 tiles of 64 px, grey patterns that multiply each cube's colour. Drawn
 *  once in a canvas, so the page loads no images: speckled stone, brick courses, planks, paving slabs,
 *  grass, leaves, fine grain, a lit window grid, water ripples, bark, gravel and a smooth tile. */
function atlasTexture() {
  const T = 64, c = document.createElement("canvas");
  c.width = c.height = T * 4;
  const g = c.getContext("2d");
  let seed = 7;
  const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
  const tile = (i, draw) => { g.save(); g.translate((i % 4) * T, Math.floor(i / 4) * T); draw(); g.restore(); };
  const base = (v) => { g.fillStyle = `rgb(${v},${v},${v})`; g.fillRect(0, 0, T, T); };
  const speck = (n, lo, hi, size) => {
    for (let k = 0; k < n; k++) {
      const v = lo + rnd() * (hi - lo);
      g.fillStyle = `rgb(${v},${v},${v})`;
      g.fillRect(Math.floor(rnd() * T), Math.floor(rnd() * T), size, size);
    }
  };
  tile(0, () => { base(222); speck(900, 180, 255, 2); speck(60, 150, 190, 4); });                     // stone
  tile(1, () => { base(236); g.fillStyle = "rgb(150,150,150)";                                        // brick
    for (let r = 0; r < 4; r++) { g.fillRect(0, r * 16, T, 2); const off = r % 2 ? 0 : 16;
      for (let x = off; x < T; x += 32) g.fillRect(x, r * 16, 2, 16); } speck(200, 205, 250, 2); });
  tile(2, () => { base(230); g.fillStyle = "rgb(170,170,170)";                                        // planks
    for (let r = 0; r < 4; r++) g.fillRect(0, r * 16 + 15, T, 1); speck(300, 200, 245, 1);
    for (let k = 0; k < 18; k++) { g.fillStyle = "rgba(120,120,120,0.35)"; g.fillRect(rnd() * T, rnd() * T, 10, 1); } });
  tile(3, () => { base(240); g.fillStyle = "rgb(175,175,175)";                                        // paving
    g.fillRect(0, 0, T, 2); g.fillRect(0, 32, T, 2); g.fillRect(0, 0, 2, T); g.fillRect(32, 0, 2, T); speck(250, 215, 255, 2); });
  tile(4, () => { base(226); speck(700, 175, 255, 2); speck(120, 240, 255, 1); });                     // grass
  tile(5, () => { base(205); speck(500, 150, 255, 3); speck(90, 110, 150, 2); });                      // leaves
  tile(6, () => { base(232); speck(1400, 200, 255, 1); });                                             // fine grain
  tile(7, () => { base(70); g.fillStyle = "rgb(255,255,255)";                                          // lit windows
    for (let r = 0; r < 2; r++) for (let q = 0; q < 2; q++) if (rnd() > 0.15) g.fillRect(6 + q * 32, 6 + r * 32, 20, 20); });
  tile(8, () => { base(225); g.strokeStyle = "rgba(255,255,255,0.6)";                                  // ripples
    for (let k = 0; k < 6; k++) { g.beginPath(); g.ellipse(rnd() * T, rnd() * T, 8 + rnd() * 10, 3, 0, 0, 7); g.stroke(); } });
  tile(9, () => { base(215); g.fillStyle = "rgba(110,110,110,0.5)";                                    // bark
    for (let x = 2; x < T; x += 7) g.fillRect(x + rnd() * 2, 0, 2, T); speck(200, 190, 240, 2); });
  tile(10, () => { base(210); speck(260, 140, 255, 4); });                                             // gravel
  tile(11, () => { base(246); speck(80, 228, 255, 2); });                                              // smooth
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = THREE.NearestFilter;            // crisp texels up close, like the voxels themselves
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.anisotropy = 4;
  return t;
}

/** The atlas rectangle of a tile, inset half a texel so neighbouring tiles never bleed in. */
function tileUV(i) {
  const s = 1 / 4, inset = 0.5 / 256;
  const u0 = (i % 4) * s + inset, v0 = 1 - (Math.floor(i / 4) + 1) * s + inset;
  return [u0, v0, s - 2 * inset];
}
const studMat = new THREE.MeshLambertMaterial({ vertexColors: true, map: studTexture() });
/** One stud on a cube's top, drawn once: a raised ring, lit from the top left, multiplied by the cube's colour. */
function studTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  g.fillStyle = "#e6e6e6";
  g.fillRect(0, 0, 64, 64);
  g.strokeStyle = "rgba(0,0,0,0.18)";
  g.strokeRect(0.5, 0.5, 63, 63);
  const ring = g.createRadialGradient(26, 26, 4, 32, 32, 20);
  ring.addColorStop(0, "#ffffff");
  ring.addColorStop(0.75, "#f2f2f2");
  ring.addColorStop(1, "#9a9a9a");
  g.fillStyle = ring;
  g.beginPath();
  g.arc(32, 32, 18, 0, Math.PI * 2);
  g.fill();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}
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
  if (typeof composer !== "undefined") composer.setSize(w, h);
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

// Ambient occlusion per face corner: 3 = open, 0 = tucked into a corner.
const AO_SHADE = [0.5, 0.66, 0.83, 1.0];

// One linear-space colour per block name, converted once (the old mesher converted per face).
const linearRGB = new Map();
function linearOf(name) {
  let rgb = linearRGB.get(name);
  if (!rgb) {
    const c = new THREE.Color().setHex(COLORS[name] ?? COLORS.STONE).convertSRGBToLinear();
    rgb = [c.r, c.g, c.b];
    linearRGB.set(name, rgb);
  }
  return rgb;
}
const MESH_CFG = { faces: FACES, seeThrough: SEE_THROUGH, translucent: TRANSLUCENT, glow: GLOW, studded: STUDDED,
  glowGain: GLOW_GAIN, tileUV: (name) => tileUV(TILE[name] ?? 0), linear: linearOf, jitter, aoShade: AO_SHADE };
const chunkAt = (cx, cy, cz) => state.chunks.get(key(cx, cy, cz));

function buildChunk(cx, cy, cz) {
  const k = key(cx, cy, cz);
  const old = state.meshes.get(k);
  if (old) {
    scene.remove(old);
    old.children.forEach(m => m.geometry.dispose());
    state.meshes.delete(k);
  }
  // realm-mesh.js: the chunk and a 2-cube border in one flat array, then array reads only (ADR-064)
  const buf = meshChunk(cx, cy, cz, chunkAt, state.palette, MESH_CFG);
  if (!buf) return;
  const lampsHere = buf.lamps;
  const group = new THREE.Group();
  for (const [part, mat] of [[buf.solid, opaqueMat], [buf.studs, studMat], [buf.glow, glowMat], [buf.glass, glassMat]]) {
    if (!part.i.length) continue;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(part.p, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(part.n, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(part.c, 3));
    if (part.uv) g.setAttribute("uv", new THREE.Float32BufferAttribute(part.uv, 2));
    g.setIndex(part.i);
    g.computeBoundingSphere();
    const mesh = new THREE.Mesh(g, mat);
    mesh.renderOrder = mat === glassMat ? 1 : 0;
    group.add(mesh);
  }
  group.userData.chunk = k;
  scene.add(group);
  state.meshes.set(k, group);
  if (lampsHere.length) lamps.set(k, lampsHere); else lamps.delete(k);
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
  state.loading++;                   // creatures wait: a surface scanned mid-load would be cached half-built
  try {
    await fetchWorld();
  } finally {
    state.loading--;
  }
  surfaces.clear();
  if (state.species.length) refreshCreatures();
}

/** Dense ordinals from the batch's run-length payload: (ordinal, len lo, len hi) triples, 4096 cubes in all. */
function decodeRuns(b64) {
  const runs = decode(b64), out = new Uint8Array(SIZE * SIZE * SIZE);
  let at = 0;
  for (let k = 0; k + 2 < runs.length; k += 3) {
    const n = runs[k + 1] | (runs[k + 2] << 8);
    out.fill(runs[k], at, at + n);
    at += n;
  }
  return out;
}

async function fetchWorld() {
  // One request for the whole world, run-length encoded (ADR-064); older servers answer 404 and we go per chunk.
  let batch = null;
  try { batch = await api(API + "/chunks/blocks"); } catch (e) { batch = null; }
  if (batch && Array.isArray(batch.chunks)) {
    state.revision = batch.revision;
    state.palette = batch.palette;
    for (const r of batch.chunks) state.chunks.set(key(r.x, r.y, r.z), decodeRuns(r.runs));
    for (const k of state.chunks.keys()) {
      const [a, b, c] = k.split(",").map(Number);
      buildChunk(a, b, c);
    }
    status();
    return batch.chunks.length;
  }
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
  if (state.district) return loadPlots(focusSlot);
  if (state.bricks) return showObby();
  if (state.gallery) {
    state.gallery = await api(API + "/gallery");     // owners change: read the parcels again
    return showGallery(focusSlot);
  }
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
    host.appendChild(ownerRow(isle));
  }
  renderRichness();
  Promise.all(state.islands.map(i => api(`${API}/islands/${i.slot}/ecology`)
    .then(r => {
      state.richness.set(i.slot, r.richness);
      state.day = Math.max(state.day, r.day);
      if (state.species.length) populate(i, r);
    })
    .catch(() => {}))).then(renderRichness);
  status();
  if (focusSlot !== undefined) {
    const isle = state.islands.find(i => i.slot === focusSlot);
    if (isle) flyTo(isle);
  }
}

// ---------------------------------------------------------------- ownership (ADR-026)
/** A wallet address is shown short (0x7099…79c8); a name as it is. */
function shortName(name) { return /^0x[0-9a-f]{40}$/.test(name) ? `${name.slice(0, 6)}…${name.slice(-4)}` : name; }
function mine(isle) { return !!state.me && isle.owner === state.me; }

// ---------------------------------------------------------------- plots (ADR-033)
// A Parcels world has no islands: an 8 × 8 map of plots around the plaza. Tap a plot to see who holds
// it, claim it, let others build, or fly over. Nobody builds on an unclaimed plot, a street or the plaza.
const PAD_SLOT = 2000;
function plotNoun(slot) { return state.district ? `Plot ${slot}` : `Isle ${slot}`; }
async function detectDistrict() {
  // Ask the registry for this world's style first: a sky-islands world has no /plots to ask for.
  state.district = null;
  state.bricks = null;
  try {
    const here = (await api("/api/v1/worlds")).worlds.find(w => w.id === WORLD);
    state.style = here ? here.style : "SKY_ISLANDS";
    if (state.style === "PARCELS") state.district = await api(API + "/plots");
    if (state.style === "BRICKS") state.bricks = await api(API + "/obby");
    if (state.style === "GALLERY") state.gallery = await api(API + "/gallery");
  } catch (e) {
    state.district = null;
  }
  const parcels = !!state.district, bricks = !!state.bricks, gallery = !!state.gallery;
  document.getElementById("laneTitle").textContent = parcels ? "PLOTS" : bricks ? "OBBY" : gallery ? "PARCELS" : "ISLAND LANE";
  document.getElementById("raiseRow").style.display = parcels || bricks || gallery ? "none" : "";
  document.getElementById("arksTitle").textContent = parcels ? "HELICOPTER" : bricks ? "PLANE" : gallery ? "DRONE" : "ARKS";
  if (gallery) {
    streetLabels();
    BUILDABLE.splice(0, BUILDABLE.length, "BRICK_WHITE", "GLASS", "PAVING", "WOOD", "STONE", "CRYSTAL", "BRICK_RED",
      "BRICK_BLUE", "BRICK_YELLOW", "LEAVES", "WATER");
    document.getElementById("palette").textContent = "";
    buildPalette();
    selectBlock("BRICK_WHITE");
    setMode("look");
  }
  if (bricks) {
    BUILDABLE.splice(0, BUILDABLE.length, "BRICK_RED", "BRICK_BLUE", "BRICK_YELLOW", "BRICK_GREEN", "BRICK_WHITE",
      "BASEPLATE", "GLASS", "WOOD", "CRYSTAL");
    document.getElementById("palette").textContent = "";
    buildPalette();
    selectBlock("BRICK_RED");
    setMode("look");
  }
}
async function loadPlots(focusSlot) {
  const res = await api(API + "/plots");
  state.district = res;
  state.plots = res.plots;
  const host = document.getElementById("islands");
  host.textContent = "";
  const grid = document.createElement("div");
  grid.className = "plot-grid";
  for (let n = 0; n < 64; n++) {
    const p = res.plots.find(x => x.n === n);
    const cell = document.createElement("button");
    cell.dataset.plot = n;
    if (!p) {
      cell.className = "plot plaza";
      cell.disabled = true;
      cell.setAttribute("aria-label", "Plaza");
    } else {
      cell.className = "plot" + (p.owner ? (mine(p) ? " yours" : " owned") : "") + (state.plotSlot === n ? " on" : "");
      cell.textContent = n;
      cell.title = `Plot ${n} · ${p.show.toLowerCase()}` + (p.owner ? ` · ${shortName(p.owner)}` : " · open");
      cell.onclick = () => { state.plotSlot = n; loadPlots(); flyTo(plotCenter(p)); };
    }
    grid.appendChild(cell);
  }
  host.appendChild(grid);
  const claimed = res.plots.filter(p => p.owner).length;
  const line = document.createElement("div");
  line.className = "note-line";
  line.textContent = `${claimed} of ${res.plots.length} plots claimed · build up to ${res.height} high`;
  host.appendChild(line);
  const picked = res.plots.find(p => p.n === state.plotSlot);
  if (picked) {
    const head = document.createElement("div");
    head.className = "isle";
    head.innerHTML = `<div><b>Plot ${picked.n}</b> · ${picked.show.toLowerCase()}</div>`;
    host.appendChild(head);
    host.appendChild(ownerRow(Object.assign({ slot: picked.n }, picked)));
  }
  status();
  if (focusSlot !== undefined) {
    const p = res.plots.find(x => x.n === focusSlot);
    if (p) flyTo(plotCenter(p));
  }
}
function plotCenter(p) { return { x: (p.minX + p.maxX + 1) / 2, y: 0, z: (p.minZ + p.maxZ + 1) / 2 }; }
function plotAt(x, z) {
  return (state.plots || []).find(p => x >= p.minX && x <= p.maxX && z >= p.minZ && z <= p.maxZ);
}

function ownerRow(isle) {
  const row = document.createElement("div");
  row.className = "owner";
  row.dataset.slot = isle.slot;
  const line = document.createElement("div");
  line.className = "owner-line";
  if (!isle.owner) line.textContent = state.district ? "open — claim it to build here" : "open — anyone may build";
  else line.textContent = mine(isle) ? "yours" + (isle.builders.length ? ` · builders: ${isle.builders.map(shortName).join(", ")}` : "")
    : `owned by ${shortName(isle.owner)}` + (isle.builders.includes(state.me) ? " · you may build" : "");
  row.appendChild(line);
  const act = document.createElement("div");
  act.className = "owner-act";
  if (!isle.owner) {
    act.appendChild(button("Claim", "claim", () => claimAct("claim", isle.slot)));
  } else if (mine(isle)) {
    const who = document.createElement("input");
    who.className = "builder-name";
    who.placeholder = "builder";
    who.setAttribute("aria-label", `Let someone build on Isle ${isle.slot}`);
    act.append(who, button("Let build", "let", () => who.value.trim() && claimAct("builders", isle.slot, { builder: who.value.trim(), allow: true })));
    for (const b of isle.builders) {
      act.appendChild(button(`${b} ×`, "unlet", () => claimAct("builders", isle.slot, { builder: b, allow: false })));
    }
    if (!state.district && wallet.config && wallet.config.deeds && /^0x[0-9a-f]{40}$/.test(state.me)) {
      act.appendChild(button(wallet.minted.has(isle.slot) ? "Deed minted" : "Mint deed", "mint", () => mintDeed(isle)));
    }
    act.appendChild(button("Give up", "abandon", () => claimAct("abandon", isle.slot)));
  }
  row.appendChild(act);
  return row;
}
function button(text, cls, onclick) {
  const b = document.createElement("button");
  b.textContent = text;
  b.className = cls;
  b.onclick = onclick;
  return b;
}
const CLAIM_WORDS = {
  CLAIMED: s => `${plotNoun(s)} is yours`, ABANDONED: s => `You gave up ${plotNoun(s)}`,
  GRANTED: () => "They may build there now", REVOKED: () => "They can no longer build there",
  ALREADY_CLAIMED: s => `${plotNoun(s)} already has an owner`, BLOCKED: () => "Another parcel is in the way",
  BAD_OWNER: () => "Pick a name first (letters, digits, . _ @ -)", NOT_OWNER: s => `${plotNoun(s)} is not yours`,
  NOT_CLAIMED: s => `${plotNoun(s)} has no owner`, BAD_BUILDER: () => "That name cannot be a builder",
  NO_SUCH_ISLAND: s => `No island in slot ${s}`, NO_SUCH_PLOT: s => `There is no plot ${s}`,
};
async function claimAct(verb, slot, extra = {}) {
  if (!state.me && !state.token) { toast("Pick a name first"); document.getElementById("me").focus(); return; }
  try {
    const res = await api(`${API}/islands/${slot}/${verb}`, { method: "POST",
      body: JSON.stringify(Object.assign({ actorId: state.me }, extra)) });
    toast((CLAIM_WORDS[res.result] || (() => res.result))(slot));
    await loadIslands();
  } catch (e) {
    handleError(e);
  }
}
function islandAt(x, z) {
  return state.islands.find(i => Math.abs(x - i.x) <= 47 && Math.abs(z - i.z) <= 47);
}
function setupMe() {
  const field = document.getElementById("me");
  field.value = state.me;
  field.disabled = !!state.token;          // signed in: the server knows who you are
  // Signed in with a wallet, the Connect button already shows who you are.
  field.style.display = state.token && /^0x[0-9a-f]{40}$/.test(state.me) ? "none" : "";
  field.title = state.token ? "Signed in" : "The name this open server knows you by";
  field.addEventListener("change", () => {
    state.me = field.value.trim();
    safeSet(NAME_KEY, state.me);
    loadIslands();
  });
}

// ---------------------------------------------------------------- worlds (ADR-030)
// Every world this server mounts, the one you are in marked; "Visit" opens another in this page, and a
// seed, a name and a style mount a new world: sky islands, or a Parcels district (ADR-033).
async function loadWorlds() {
  const host = document.getElementById("worlds");
  if (!host) return;
  let res;
  try { res = await api("/api/v1/worlds"); } catch (e) { return; }
  state.worlds = res.worlds;
  const here = res.worlds.find(w => w.id === WORLD);
  if (here) {
    document.getElementById("worldTitle").textContent = here.title;
    document.title = `${here.title} · Daedalus Realm`;
  }
  host.textContent = "";
  for (const w of res.worlds) {
    const row = document.createElement("div");
    row.className = "isle world-row";
    row.dataset.world = w.id;
    const info = document.createElement("div");
    info.innerHTML = `<b></b><br><span></span>`;
    info.querySelector("b").textContent = w.title;
    info.querySelector("span").textContent = w.style === "PARCELS" ? `${w.styleTitle} · 60 plots`
      : w.style === "BRICKS" ? `${w.styleTitle} · obby and sandbox`
      : w.style === "GALLERY" ? `${w.styleTitle} · parcels and galleries`
      : `${w.styleTitle} · ${w.islands} island${w.islands === 1 ? "" : "s"}`;
    row.appendChild(info);
    if (w.id === WORLD) {
      const here = document.createElement("span");
      here.className = "here";
      here.textContent = "you are here";
      row.appendChild(here);
    } else {
      const linked = (state.gates || []).some(g => g.toWorld === w.id);
      if (linked) {
        const tag = document.createElement("span");
        tag.className = "here gate-open";
        tag.textContent = "gate open";
        row.appendChild(tag);
      } else {
        row.appendChild(button("Open gate", "open-gate", () => openGateTo(w.id)));
      }
      row.appendChild(button("Visit", "visit", () => { location.href = `/realm.html?world=${encodeURIComponent(w.id)}`; }));
    }
    host.appendChild(row);
  }
  const pickStyle = document.getElementById("newWorldStyle");
  if (pickStyle && !pickStyle.options.length) {
    for (const s of res.styles.filter(x => x.ready)) {
      const o = document.createElement("option");
      o.value = s.style; o.textContent = s.title;
      pickStyle.appendChild(o);
    }
  }
  const soon = res.styles.filter(s => !s.ready).map(s => s.title);
  const note = document.getElementById("worldsSoon");
  if (note) note.textContent = soon.length ? `Coming: ${soon.join(", ")}` : "";
}
async function createWorld() {
  const name = document.getElementById("newWorldName").value.trim();
  const seedRaw = document.getElementById("newWorldSeed").value.trim();
  const id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 32);
  const seed = seedRaw === "" ? Math.floor(Math.random() * 1e9) : Number(seedRaw);
  if (!name || id.length < 3) { toast("Name the world (3+ letters)"); return; }
  if (!Number.isInteger(seed)) { toast("Seed must be a whole number"); return; }
  try {
    const res = await api("/api/v1/worlds", { method: "POST", body: JSON.stringify({ id, style: (document.getElementById("newWorldStyle") || {}).value || "SKY_ISLANDS", seed, title: name }) });
    const words = { CREATED: `${name} is born`, EXISTS: "A world with that name exists", BAD_ID: "Use letters and digits",
      BAD_TITLE: "That name won't do", FULL: "This server holds all the worlds it can", STYLE_NOT_READY: "That style is coming" };
    toast(words[res.result] || res.result);
    if (res.result === "CREATED") location.href = `/realm.html?world=${encodeURIComponent(res.world.id)}`;
    else loadWorlds();
  } catch (e) {
    handleError(e);
  }
}

// ---------------------------------------------------------------- sky gates (ADR-031)
// Gates float in the clouds on the far side of the rainbow, far from every island: no one walks there.
// Ride an ark to a gate and you cross into the world it opens on. There, that world's ark comes up to
// its own gate to meet you and carries you down to an island.
const GATE_BASE = 1000;
function placeName(slot) {
  if (slot === PAD_SLOT) return state.bricks ? "the runway" : state.gallery ? "the Origin pad" : "the helipad";
  if (slot >= GATE_BASE) {
    const g = state.gates.find(x => x.slot === slot);
    return g ? `the gate to ${g.toTitle}` : "a sky gate";
  }
  return `Isle ${slot}`;
}
async function loadGates() {
  try {
    const res = await api(`/api/v1/world/${encodeURIComponent(WORLD)}/gates`);
    state.gates = res.gates;
    state.mount = res.mount;
  } catch (e) {
    state.gates = [];
  }
  renderArkList();
  if (state.worlds) loadWorlds();
}
function crossGate(gate) {
  toast(`Through the clouds to ${gate.toTitle}…`);
  state.crossing = gate;
  setTimeout(() => {
    location.href = `/realm.html?world=${encodeURIComponent(gate.toWorld)}&arrive=${gate.toGate}`;
  }, 1200);
}
/** Arrived through a gate (?arrive=N): look at this world's gate and hail an ark to meet you there. */
async function arriveThroughGate() {
  // Only a page that came through a gate hails anything. Number(null) is 0, so before this check every
  // plain page load in a world with a gate sent an ark up to gate 0 (found by the ADR-033 harness).
  const raw = new URLSearchParams(location.search).get("arrive");
  if (raw === null || !/^\d+$/.test(raw)) return;
  const g = Number(raw);
  const gate = state.gates.find(x => x.gate === g);
  if (!gate) return;
  flyTo({ x: gate.x, y: gate.y - 6, z: gate.z + 20 });
  const ark = state.arks.find(a => a.state === "MOORED" && a.slot < GATE_BASE) || state.arks.find(a => a.state === "MOORED");
  if (!ark) { toast("No ark is free to meet you — wait at the gate"); return; }
  state.hail = { arkId: ark.id, gate: gate.gate };
  state.lastHail = { arkId: ark.id, gate: gate.gate, at: Date.now() };   // stays after the meeting (harness, debugging)
  toast(`Welcome to ${document.getElementById("worldTitle").textContent}. ${ark.name} is coming up to the gate for you`);
  await sailArk(ark.id, gate.slot);
}
async function openGateTo(worldId) {
  try {
    const res = await api(`/api/v1/world/${encodeURIComponent(WORLD)}/gates`, { method: "POST", body: JSON.stringify({ toWorld: worldId }) });
    const words = { OPENED: "A gate opens in the clouds past the rainbow", ALREADY_LINKED: "A gate there is already open",
      FULL: "No sky left for another gate", NO_SUCH_WORLD: "No such world", SAME_WORLD: "That is this world" };
    toast(words[res.result] || res.result);
    if (res.result === "OPENED") {
      const gate = { x: 48 + 96 * res.gate, y: 72, z: -210 };
      flyTo({ x: gate.x, y: gate.y - 6, z: gate.z + 30 });
    }
  } catch (e) {
    handleError(e);
  }
}

// ---------------------------------------------------------------- wallet (ADR-028)
// Sign in with Ethereum: the server writes the message, the wallet signs it unchanged, and the token
// that comes back names the wallet address. Minting a deed: the owner asks the realm for a voucher and
// redeems it on the RealmIslands contract from their own wallet (they pay the gas). ethers is loaded
// only when a wallet is used, so the realm costs nothing extra for anyone else.
const wallet = { config: null, minted: new Set() };
let ethersLib = null;
async function ethersOf() {
  if (!ethersLib) ethersLib = await import("ethers");
  return ethersLib;
}
const ISLANDS_ABI = [
  "function mint((address to,uint256 slot,uint64 seed,uint8 radius,uint256 deadline) deed, bytes signature)",
  "function ownerOf(uint256 slot) view returns (address)",
];
async function setupWallet() {
  try {
    const res = await fetch("/api/v1/auth/wallet/config");
    if (!res.ok) return;                       // wallet sign-in is off on this server
    wallet.config = await res.json();
  } catch (e) { return; }
  const b = document.getElementById("wallet");
  b.style.display = "";
  b.onclick = connectWallet;
  showWallet();
}
function showWallet() {
  const b = document.getElementById("wallet");
  const signedIn = /^0x[0-9a-f]{40}$/.test(state.me) && state.token;
  b.textContent = signedIn ? `${state.me.slice(0, 6)}…${state.me.slice(-4)}` : "Connect wallet";
  b.classList.toggle("on", !!signedIn);
}
async function connectWallet() {
  if (!window.ethereum) { toast("No wallet found: install one (MetaMask, Rabby…) to sign in"); return; }
  try {
    const [account] = await window.ethereum.request({ method: "eth_requestAccounts" });
    const nonce = await api(`/api/v1/auth/wallet/nonce?address=${encodeURIComponent(account)}`);
    const signature = await window.ethereum.request({ method: "personal_sign", params: [nonce.message, account] });
    const res = await fetch("/api/v1/auth/wallet", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: nonce.message, signature }) });
    if (!res.ok) { toast("Sign-in refused: " + (res.headers.get("X-Wallet-Refused") || res.status)); return; }
    const body = await res.json();
    state.token = body.token;
    safeSet(TOKEN_KEY, body.token);
    safeSet("daedalus.user", account.toLowerCase());
    state.me = account.toLowerCase();
    setupMe();
    showWallet();
    toast(`Signed in as ${state.me.slice(0, 6)}…${state.me.slice(-4)}`);
    if (state.stomp) { try { state.stomp.disconnect(); } catch (e) { /* closing */ } }
    connectLive();
    await loadIslands();
  } catch (e) {
    toast(e && e.code === 4001 ? "Signature request was declined" : "Wallet sign-in failed: " + (e.message || e));
  }
}
async function mintDeed(isle) {
  if (wallet.minted.has(isle.slot)) { window.open(`${API}/tokens/${isle.slot}`, "_blank", "noopener"); return; }
  try {
    const v = await api(`${API}/islands/${isle.slot}/deed-voucher`, { method: "POST" });
    const { BrowserProvider, Contract } = await ethersOf();
    const provider = new BrowserProvider(window.ethereum);
    const chain = Number((await provider.getNetwork()).chainId);
    if (chain !== v.chainId) {
      await window.ethereum.request({ method: "wallet_switchEthereumChain", params: [{ chainId: "0x" + v.chainId.toString(16) }] });
    }
    const signer = await provider.getSigner();
    const islands = new Contract(v.contract, ISLANDS_ABI, signer);
    toast(`Minting Isle ${isle.slot}'s deed — confirm in your wallet`);
    const tx = await islands.mint({ to: v.to, slot: v.slot, seed: BigInt(v.seed), radius: v.radius, deadline: v.deadline }, v.signature);
    await tx.wait();
    wallet.minted.add(isle.slot);
    state.lastMint = { slot: isle.slot, tx: tx.hash };
    toast(`Isle ${isle.slot}'s deed is yours on chain`);
    await loadIslands();
  } catch (e) {
    const why = e && e.code === "ACTION_REJECTED" ? "you declined the transaction"
      : e && /ERC721InvalidSender/.test(String(e.message)) ? "this island's deed is already minted"
      : (e && (e.shortMessage || e.message)) || String(e);
    toast(`No deed: ${why}`);
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
  const deed = document.createElement("a");
  deed.className = "deed";
  deed.href = `${API}/tokens/${slot}`;
  deed.target = "_blank";
  deed.rel = "noopener";
  deed.title = `Isle ${slot}'s deed (token metadata)`;
  const pic = document.createElement("img");
  pic.src = `${API}/islands/${slot}/portrait.png`;
  pic.alt = `Portrait of Isle ${slot}`;
  pic.width = 64; pic.height = 64;
  deed.appendChild(pic);
  host.appendChild(deed);
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
  if (f.kind === "DAY") {
    if (f.day % 5 === 0) refreshCreatures();            // counts drift slowly; a redraw every few days
  } else {
    refreshCreatures([f.slot]);                          // a landing or a departure changes who is there now
  }
}

// ---------------------------------------------------------------- creatures (ADR-025)
// Every kind living on an island is drawn there: a few voxel bodies per kind (more for a bigger
// population, never more than SHOW_MAX), placed where its guild lives — meadow kinds on open
// ground, pond kinds on water, canopy kinds in the crowns, decomposers as caps on the soil,
// starborn under the hanging crystals. Placement is seeded by island and kind, so every page
// draws the same island the same way. Bodies are client art only; the server owns the counts.
const SHOW_MAX = 5;
const ISLAND_SHOW_CAP = 90;
const SIZE_SCALE = { TINY: 0.42, SMALL: 0.62, MEDIUM: 0.9, LARGE: 1.4, SESSILE: 0.7 };
function hash32(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function rng(seed) {                   // mulberry32: small, seeded, the same on every page
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function shownFor(count) { return Math.max(1, Math.min(SHOW_MAX, Math.ceil(Math.log2(count + 1)))); }

const GROUND = new Set(["GRASS", "DIRT", "SAND", "GRAVEL", "STONE"]);
const CROWN = new Set(["LEAVES", "BLOSSOM"]);
const surfaces = new Map();            // slot → { revision, meadow, pond, canopy, soil, crystal }
function surfaceOf(isle) {
  const cached = surfaces.get(isle.slot);
  if (cached && cached.revision === state.revision) return cached;
  const out = { revision: state.revision, meadow: [], pond: [], canopy: [], soil: [], crystal: [] };
  const r = isle.radius + 6, top = isle.y + isle.top + 1, bottom = isle.y + isle.bottom - 1;
  for (let x = isle.x - r; x <= isle.x + r; x++) {
    for (let z = isle.z - r; z <= isle.z + r; z++) {
      let crown = null;
      for (let y = top; y >= bottom; y--) {
        const n = nameAt(x, y, z);
        if (n === "AIR" || n === "CLOUD") continue;
        if (CROWN.has(n)) { if (!crown) crown = [x, y + 1, z]; continue; }
        if (n === "LOG") continue;
        if (n === "WATER") out.pond.push([x, y + 1, z]);
        else if (GROUND.has(n)) {
          out.meadow.push([x, y + 1, z]);
          if (n === "DIRT" || n === "GRASS") out.soil.push([x, y + 1, z]);
        }
        break;
      }
      if (crown) out.canopy.push(crown);
      for (let y = bottom; y <= isle.y; y++) {
        const n = nameAt(x, y, z);
        if (n === "AIR") continue;
        if (n === "CRYSTAL") out.crystal.push([x, y - 1, z]);
        break;
      }
    }
  }
  surfaces.set(isle.slot, out);
  return out;
}

const creatureGeo = new THREE.BoxGeometry(1, 1, 1);
const creatureMats = new Map();
function creatureMat(hex, glow) {
  const k = hex + (glow ? "g" : "");
  if (!creatureMats.has(k)) {
    creatureMats.set(k, new THREE.MeshLambertMaterial({ color: hex, emissive: glow ? hex : 0x000000,
      emissiveIntensity: glow ? 0.8 : 0 }));
  }
  return creatureMats.get(k);
}
function box(parent, mat, w, h, d, x, y, z) {
  const m = new THREE.Mesh(creatureGeo, mat);
  m.scale.set(w, h, d);
  m.position.set(x, y, z);
  parent.add(m);
  return m;
}
/** A small voxel body for one kind: colours and proportions from its key, shape from its guild. */
function creatureModel(sp) {
  const h = hash32(sp.key), g = new THREE.Group();
  const body = new THREE.Color().setHSL((h % 360) / 360, 0.45 + ((h >>> 9) % 30) / 100, 0.42 + ((h >>> 17) % 20) / 100);
  const accent = new THREE.Color().setHSL(((h >>> 5) % 360) / 360, 0.6, 0.6);
  const glow = sp.guild === "STARBORN";
  const mb = creatureMat(body.getHex(), glow), ma = creatureMat(accent.getHex(), glow);
  if (sp.size === "SESSILE" || sp.guild === "DECOMPOSER") {
    box(g, creatureMat(0xe9dcc3, false), 0.22, 0.45, 0.22, 0, 0.22, 0);   // stem
    box(g, mb, 0.7, 0.28, 0.7, 0, 0.55, 0);                              // cap
    box(g, ma, 0.14, 0.08, 0.14, 0.18, 0.72, 0.1);                        // spot
  } else if (sp.disperses || sp.guild === "STARBORN") {
    box(g, mb, 0.7, 0.45, 0.45, 0, 0.5, 0);                               // body
    box(g, ma, 0.3, 0.3, 0.3, 0.45, 0.62, 0);                             // head
    const wl = box(g, ma, 0.4, 0.08, 0.7, -0.05, 0.62, 0.55);             // wings
    const wr = box(g, ma, 0.4, 0.08, 0.7, -0.05, 0.62, -0.55);
    g.userData.wings = [wl, wr];
  } else if (sp.guild === "POND") {
    box(g, mb, 0.9, 0.3, 0.5, 0, 0.15, 0);                                // flat swimmer
    box(g, ma, 0.25, 0.25, 0.5, -0.55, 0.15, 0);                          // tail
  } else {
    box(g, mb, 0.9, 0.5, 0.5, 0, 0.55, 0);                                // body
    box(g, ma, 0.4, 0.4, 0.4, 0.6, 0.8, 0);                               // head
    for (const [lx, lz] of [[0.3, 0.17], [0.3, -0.17], [-0.3, 0.17], [-0.3, -0.17]]) {
      box(g, mb, 0.14, 0.3, 0.14, lx, 0.15, lz);                          // legs
    }
  }
  g.scale.setScalar(SIZE_SCALE[sp.size] || 0.6);
  return g;
}
function spotsFor(sp, surf) {
  if (sp.guild === "STARBORN") return surf.crystal.length ? surf.crystal : surf.meadow;
  if (sp.guild === "POND") return surf.pond.length ? surf.pond : surf.meadow;
  if (sp.guild === "CANOPY") return surf.canopy.length ? surf.canopy : surf.meadow;
  if (sp.guild === "DECOMPOSER") return surf.soil.length ? surf.soil : surf.meadow;
  return surf.meadow;
}
/** Redraw an island's creatures from its ecology answer, unless what is shown would not change. */
function populate(isle, life) {
  if (state.loading) return;           // loadWorld redraws every island when it finishes
  const plan = [];
  let budget = ISLAND_SHOW_CAP;
  for (const row of life.species) {
    const sp = state.species.find(s => s.key === row.key);
    if (!sp || budget <= 0) continue;
    const n = Math.min(budget, shownFor(row.count));
    budget -= n;
    plan.push([sp, n]);
  }
  const sig = state.revision + "|" + plan.map(([sp, n]) => sp.key + ":" + n).join(",");
  const had = state.creatures.get(isle.slot);
  if (had && had.sig === sig) return;
  if (had) scene.remove(had.group);
  const surf = surfaceOf(isle);
  const group = new THREE.Group();
  group.name = "creatures-" + isle.slot;
  const list = [];
  for (const [sp, n] of plan) {
    const spots = spotsFor(sp, surf);
    if (!spots.length) continue;
    const rand = rng(hash32(isle.seed + ":" + sp.key));
    for (let i = 0; i < n; i++) {
      const [x, y, z] = spots[Math.floor(rand() * spots.length)];
      const m = creatureModel(sp);
      const flies = sp.guild === "STARBORN" || (sp.disperses && sp.guild !== "DECOMPOSER" && sp.size !== "SESSILE");
      const home = new THREE.Vector3(x + 0.5, y + (flies ? 1.5 + rand() * 2.5 : 0), z + 0.5);
      if (sp.guild === "STARBORN") home.y -= 3;           // hanging under the crystal
      m.position.copy(home);
      m.rotation.y = rand() * Math.PI * 2;
      m.userData = Object.assign(m.userData, { key: sp.key, home, flies, sessile: sp.size === "SESSILE" || sp.guild === "DECOMPOSER",
        phase: rand() * Math.PI * 2, speed: 0.4 + rand() * 0.6, roam: flies ? 2.5 : 1.2, ground: [x, y, z] });
      group.add(m);
      list.push(m);
    }
  }
  scene.add(group);
  state.creatures.set(isle.slot, { sig, group, list });
}
function moveCreatures(t) {
  const s = t / 1000;
  for (const { list } of state.creatures.values()) {
    for (const m of list) {
      const u = m.userData;
      if (u.sessile) continue;
      const a = u.phase + s * u.speed * 0.5;
      m.position.x = u.home.x + Math.cos(a) * u.roam * 0.5;
      m.position.z = u.home.z + Math.sin(a * 0.8) * u.roam * 0.5;
      m.rotation.y = -a + Math.PI / 2;
      if (u.flies) {
        m.position.y = u.home.y + Math.sin(s * 2 + u.phase) * 0.4;
        if (u.wings) { const f = Math.sin(s * 14 + u.phase) * 0.5; u.wings[0].rotation.x = f; u.wings[1].rotation.x = -f; }
      } else {
        m.position.y = u.home.y + Math.abs(Math.sin(s * 3 + u.phase)) * 0.12;
      }
    }
  }
}
async function refreshCreatures(slots) {
  for (const isle of state.islands) {
    if (slots && !slots.includes(isle.slot)) continue;
    try { populate(isle, await api(`${API}/islands/${isle.slot}/ecology`)); } catch (e) { /* next frame retries */ }
  }
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
/**
 * The Parcels world's helicopter (ADR-033), built from boxes like the creatures: an orange cabin with a
 * glass nose, a tail boom, skids, and two rotors the frame loop spins. About 12 cubes nose to tail.
 */
function helicopterModel() {
  const g = new THREE.Group();
  const body = creatureMat(0xf28c28), white = creatureMat(0xf4f1ea), dark = creatureMat(0x2b2d33);
  const glass = new THREE.MeshLambertMaterial({ color: 0x9fd4ec, transparent: true, opacity: 0.7 });
  box(g, body, 5, 3.2, 3.4, 0, 2.4, 0);              // cabin
  box(g, glass, 1.8, 2.4, 3.0, 3.1, 2.6, 0);         // nose
  box(g, white, 5.2, 0.6, 3.5, 0, 1.0, 0);           // belly stripe
  box(g, body, 6, 0.9, 0.9, -5.4, 3.2, 0);           // tail boom
  box(g, body, 1.0, 2.2, 0.4, -8.2, 4.0, 0);         // fin
  for (const side of [-1, 1]) {
    box(g, dark, 6.5, 0.3, 0.3, 0.2, 0.15, side * 1.6);   // skids
    box(g, dark, 0.3, 0.9, 0.3, -1.4, 0.6, side * 1.6);
    box(g, dark, 0.3, 0.9, 0.3, 1.6, 0.6, side * 1.6);
  }
  box(g, dark, 0.5, 0.8, 0.5, 0, 4.3, 0);            // mast
  const rotor = new THREE.Group();
  rotor.name = "rotor";
  rotor.position.set(0, 4.8, 0);
  box(rotor, dark, 13, 0.15, 0.6, 0, 0, 0);
  box(rotor, dark, 0.6, 0.15, 13, 0, 0, 0);
  g.add(rotor);
  const tail = new THREE.Group();
  tail.name = "tailRotor";
  tail.position.set(-8.3, 4.0, 0.4);
  box(tail, dark, 2.6, 0.3, 0.12, 0, 0, 0);
  box(tail, dark, 0.3, 2.6, 0.12, 0, 0, 0);
  g.add(tail);
  return g;
}

/** The Bricks world's plane (ADR-034): a stud-bright monoplane of boxes with a propeller that spins. */
function planeModel() {
  const g = new THREE.Group();
  const blue = creatureMat(0x0d69ac), white = creatureMat(0xf2f3f3), red = creatureMat(0xc4281c),
    yellow = creatureMat(0xf5cd30), dark = creatureMat(0x2b2d33);
  const glass = new THREE.MeshLambertMaterial({ color: 0x9fd4ec, transparent: true, opacity: 0.7 });
  box(g, blue, 9, 2, 2, 0, 2.2, 0);                  // fuselage, nose along +X
  box(g, glass, 2, 1.2, 1.6, 1.6, 3.6, 0);           // canopy
  box(g, white, 3, 0.4, 14, 0.6, 2.4, 0);            // wings
  box(g, red, 0.4, 0.42, 14.1, 2.0, 2.4, 0);         // wing stripe
  box(g, white, 2, 0.3, 5, -4, 2.6, 0);              // tailplane
  box(g, red, 2, 2.4, 0.3, -4, 4, 0);                // fin
  box(g, yellow, 0.6, 1, 1, 4.8, 2.2, 0);            // spinner
  for (const side of [-1, 1]) {
    box(g, dark, 0.3, 1.4, 0.3, 1.2, 0.9, side * 1.4);  // legs
    box(g, dark, 1, 0.8, 0.5, 1.2, 0.4, side * 1.4);    // wheels
  }
  const prop = new THREE.Group();
  prop.name = "prop";
  prop.position.set(5.2, 2.2, 0);
  box(prop, dark, 0.15, 5, 0.5, 0, 0, 0);
  g.add(prop);
  return g;
}

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

// Arks tied up at the same pier lie side by side along the rim, not inside each other: the
// lowest id takes the berth, the next one a hull's length east, the next west, and so on.
const BERTH_SPACING = 26;
const BERTH_STEPS = [0, 1, -1, 2, -2, 3, -3];
function isHeli(arkId) { return /^(heli|plane|drone)-/.test(arkId || ""); }    // the world's own aircraft
function mooring(slot, arkId) {
  if (slot === PAD_SLOT && state.district) {
    return new THREE.Vector3(state.district.padX, state.district.padY, state.district.padZ);
  }
  if (slot === PAD_SLOT && state.gallery) {
    return new THREE.Vector3(state.gallery.padX, state.gallery.padY, state.gallery.padZ);
  }
  if (slot === PAD_SLOT && state.bricks) {
    return new THREE.Vector3(state.bricks.hangarX + 0.5, state.bricks.hangarY, state.bricks.hangarZ + 0.5);
  }
  const gate = state.gates.find(g => g.slot === slot);
  if (gate) return new THREE.Vector3(gate.berthX + 0.5, gate.berthY, gate.berthZ + (isHeli(arkId) ? 0.5 : ARK_STANDOFF));
  const isle = state.islands.find(i => i.slot === slot);
  if (!isle) return null;
  const here = new Set(state.arks.filter(a => a.slot === slot).map(a => a.id));
  if (arkId) here.add(arkId);
  const rank = Math.max(0, [...here].sort().indexOf(arkId));
  const step = BERTH_STEPS[rank % BERTH_STEPS.length];
  return new THREE.Vector3(isle.dockX + 0.5 + step * BERTH_SPACING, isle.dockY + 1, isle.dockZ + ARK_STANDOFF);
}

function serverNow() { return Date.now() + state.clockOffset; }

/** Where an ark is and which way it faces, on server time (ADR-020). */
function arkPose(ark, now) {
  if (ark.state !== "SAILING") {
    return { pos: mooring(ark.slot, ark.id) || new THREE.Vector3(ark.x + 0.5, ark.y, ark.z + ARK_STANDOFF), yaw: 0, t: 1 };
  }
  const a = mooring(ark.fromSlot, ark.id), b = mooring(ark.toSlot, ark.id);
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
      const hull = /^plane-/.test(ark.id) ? planeModel() : /^drone-/.test(ark.id) ? droneModel()
        : isHeli(ark.id) ? helicopterModel() : template.clone(true);
      if (!isHeli(ark.id)) hull.scale.setScalar(ARK_SCALE);
      hull.name = "hull";
      model.add(hull);
      const label = labelSprite(ark.name);
      label.position.set(0, isHeli(ark.id) ? 12 : 22, 0);
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
    const where = ark.state === "SAILING" ? `sailing ${placeName(ark.fromSlot)} → ${placeName(ark.toSlot)}` : `moored at ${placeName(ark.slot)}`;
    const held = (ark.hold || []).length;
    const flies = isHeli(ark.id);
    info.innerHTML = `<b>${ark.name}</b><br><span class="where">${flies ? where.replace("sailing", "flying").replace("moored at", "on") : where}</span>` +
      (flies ? "" : `<br><span class="hold">${held ? `carrying ${held} kind${held === 1 ? "" : "s"}` : "hold empty"}</span>`);
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
    if (ark.homeSlot === PAD_SLOT && ark.slot !== PAD_SLOT) {
      const o = document.createElement("option");
      o.value = PAD_SLOT; o.textContent = state.bricks ? "Runway" : state.gallery ? "Origin" : "Helipad";
      pick.appendChild(o);
    }
    for (const g of state.gates) {
      if (g.slot === ark.slot) continue;
      const o = document.createElement("option");
      o.value = g.slot; o.textContent = `Gate → ${g.toTitle}`;
      pick.appendChild(o);
    }
    const sail = document.createElement("button");
    sail.className = "sail"; sail.textContent = flies ? "Fly" : "Sail";
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
    const gate = toSlot >= GATE_BASE && toSlot < GATE_BASE + 8;
    const body = toSlot === PAD_SLOT ? { toHome: true } : gate ? { toGate: toSlot - GATE_BASE } : { toSlot };
    const res = await api(`${API}/arks/${arkId}/voyage`, { method: "POST", body: JSON.stringify(body) });
    if (res.result === "SAILING") {
      applyArk(res.ark, res.now);
      toast(isHeli(arkId) ? `${res.ark.name} lifts off for ${placeName(toSlot)}` : `${res.ark.name} cast off for ${placeName(toSlot)}`);
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
  const gate = state.gates.find(g => g.slot === f.toSlot);
  const row = Object.assign({}, ark, f.kind === "DEPARTED"
    ? { state: "SAILING", slot: f.toSlot, fromSlot: f.fromSlot, toSlot: f.toSlot, departAt: f.departAt, arriveAt: f.arriveAt }
    : { state: "MOORED", slot: f.toSlot, fromSlot: -1, toSlot: -1, departAt: 0, arriveAt: 0 });
  if (isle) { row.x = isle.dockX; row.y = isle.dockY + 1; row.z = isle.dockZ; }
  if (gate) { row.x = gate.berthX; row.y = gate.berthY; row.z = gate.berthZ; }
  if (f.toSlot === PAD_SLOT && state.district) { row.x = state.district.padX; row.y = state.district.padY; row.z = state.district.padZ; }
  if (f.toSlot === PAD_SLOT && state.bricks) { row.x = state.bricks.hangarX; row.y = state.bricks.hangarY; row.z = state.bricks.hangarZ; }
  if (f.toSlot === PAD_SLOT && state.gallery) { row.x = state.gallery.padX; row.y = state.gallery.padY; row.z = state.gallery.padZ; }
  applyArk(row);
  if (f.kind !== "ARRIVED") return;
  toast(isHeli(ark.id) ? `${ark.name} set down at ${placeName(f.toSlot)}` : `${ark.name} tied up at ${placeName(f.toSlot)}`);
  if (state.hail && state.hail.arkId === f.arkId && gate) {
    // The ark that came to meet you at this world's gate now carries you to an island.
    const ark2 = state.arks.find(a => a.id === f.arkId);
    state.hail = null;
    toast(`${ark2.name} met you at the gate — sailing for ${placeName(ark2.homeSlot)}`);
    sailArk(ark2.id, ark2.homeSlot);
  } else if (gate && RIDE.id === f.arkId) {
    crossGate(gate);                                          // you rode it to the gate: through you go
  }
}

function moveArks(t) {
  const now = serverNow();
  for (const model of state.arkModels.values()) {
    const ark = model.userData.ark;
    if (!ark) continue;
    const pose = arkPose(ark, now);
    const phase = ark.homeSlot * 1.7;
    const flies = isHeli(ark.id);
    const bob = flies ? (ark.state === "SAILING" ? 0.2 : 0) : ark.state === "SAILING" ? 0.15 : 0.35;
    model.position.copy(pose.pos);
    model.position.y += Math.sin(t / 1400 + phase) * bob;
    const hull = model.getObjectByName("hull");
    if (hull) hull.rotation.set(0, pose.yaw, flies ? 0 : Math.sin(t / 1900 + phase) * 0.015);
    const rotor = model.getObjectByName("rotor");
    if (rotor) rotor.rotation.y = t / (ark.state === "SAILING" ? 40 : 160);
    const tail = model.getObjectByName("tailRotor");
    if (tail) tail.rotation.z = t / 30;
    const prop = model.getObjectByName("prop");
    if (prop) prop.rotation.x = t / (ark.state === "SAILING" ? 25 : 90);
    for (let r = 0; r < 4; r++) {
      const rotor4 = model.getObjectByName("rotor" + r);
      if (rotor4) rotor4.rotation.y = (r % 2 ? -1 : 1) * t / (ark.state === "SAILING" ? 30 : 120);
    }
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
    const who = state.me ? `&actorId=${encodeURIComponent(state.me)}` : "";
    const res = name === "AIR"
      ? await api(`${API}/block?x=${x}&y=${y}&z=${z}${who}`, { method: "DELETE" })
      : await api(API + "/block", { method: "PUT", body: JSON.stringify({ x, y, z, type: name, actorId: state.me || undefined }) });
    if (res.result === "DENIED") {
      setLocal(x, y, z, before);
      remeshAround(x, y, z);
      if (state.bricks) {
        state.lastRefusal = y > state.bricks.height ? `Bricks are built up to ${state.bricks.height} high`
          : y <= 0 ? "The baseplate stays put" : "The obby, the spawn and the runway stay as they are";
      } else if (state.district) {
        const p = plotAt(x, z);
        state.lastRefusal = !p ? "Streets and the plaza are for everyone; nobody builds there"
          : y > state.district.height ? `Plots are built up to ${state.district.height} high`
          : p.owner ? `Plot ${p.n} belongs to ${shortName(p.owner)}` : `Claim Plot ${p.n} to build on it`;
      } else {
        const isle = islandAt(x, z);
        state.lastRefusal = isle && isle.owner ? `Isle ${isle.slot} belongs to ${shortName(isle.owner)}` : "That plot is not yours to change";
      }
      toast(state.lastRefusal);
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
  } else if (ev.kind === "WORLD_REVISION_CHANGED" && ev.type === "CLAIM") {
    loadIslands();
  } else if (ev.kind === "WORLD_REVISION_CHANGED" && ev.type === "ART") {
    loadArt();
  } else if (ev.kind === "WORLD_REVISION_CHANGED" && ev.type === "GATE") {
    loadWorld().then(loadGates);
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
  if (moved > 8 || !quick || state.mode === "play") return; // a drag is a camera move
  if (state.mode === "look") {
    if (state.gallery) lookTap(e.clientX, e.clientY);
    return;
  }
  if (state.mode === "hang") { hangTap(e.clientX, e.clientY); return; }
  const p = pick(e.clientX, e.clientY);
  if (!p) return;
  if (state.mode === "build") writeBlock(p.next.x, p.next.y, p.next.z, state.block);
  else if (state.mode === "break") writeBlock(p.at.x, p.at.y, p.at.z, "AIR");
});
canvas.addEventListener("contextmenu", e => e.preventDefault());

function setMode(m) {
  const was = state.mode;
  state.mode = m;
  for (const [id, mode] of [["modeLook", "look"], ["modeBuild", "build"], ["modeBreak", "break"], ["modePlay", "play"]]) {
    document.getElementById(id).classList.toggle("on", mode === m);
  }
  hover.visible = false;
  hover.material.color.setHex(m === "break" ? 0xff5a5f : 0xf5c14a);
  if (m === "play" && was !== "play") startPlay();
  if (m !== "play" && was === "play") stopPlay();
}
document.getElementById("modePlay").onclick = () => setMode(state.mode === "play" ? "look" : "play");
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
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
  if (state.mode === "play") { playKey(e, true); return; }
  if (e.key === "p" || e.key === "P") setMode("play");
  if (e.key === "l" || e.key === "L") setMode("look");
  if (e.key === "b" || e.key === "B") setMode("build");
  if (e.key === "x" || e.key === "X") setMode("break");
  const n = Number(e.key);
  if (n >= 1 && n <= 9 && BUILDABLE[n - 1]) selectBlock(BUILDABLE[n - 1]);
});

window.addEventListener("keyup", e => { if (state.mode === "play") playKey(e, false); });

// ---------------------------------------------------------------- Sky and weather panel (ADR-038)
// Time of day (or the live clock), rain and glow. Per-viewer, so the choice lives in this browser only.
const atmoUI = {
  panel: document.getElementById("atmo"), btn: document.getElementById("atmoBtn"),
  live: document.getElementById("atmoLive"), time: document.getElementById("atmoTime"),
  hour: document.getElementById("atmoHour"), rain: document.getElementById("atmoRain"),
  glow: document.getElementById("atmoGlow"),
};
function hhmm(h) { const m = Math.round(h * 60) % 1440; return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0"); }
function syncAtmoUI() {
  atmoUI.live.checked = ATMO.hour == null;
  atmoUI.time.disabled = ATMO.hour == null;
  atmoUI.time.value = currentHour();
  atmoUI.hour.textContent = hhmm(currentHour());
  atmoUI.rain.checked = ATMO.rain;
  atmoUI.glow.checked = ATMO.glow;
}
function saveAtmo() {
  try { localStorage.setItem("daedalus.atmo", JSON.stringify({ hour: ATMO.hour, rain: ATMO.rain, glow: ATMO.glow })); } catch (_) {}
}
try {
  const saved = JSON.parse(localStorage.getItem("daedalus.atmo") || "null");
  if (saved) { ATMO.hour = saved.hour ?? null; ATMO.rain = !!saved.rain; ATMO.glow = saved.glow !== false; }
} catch (_) {}
function toggleAtmo(open) {
  const on = open ?? !atmoUI.panel.classList.contains("open");
  atmoUI.panel.classList.toggle("open", on);
  atmoUI.btn.classList.toggle("on", on);
  atmoUI.btn.setAttribute("aria-expanded", String(on));
  if (on) syncAtmoUI();
}
atmoUI.btn.addEventListener("click", () => toggleAtmo());
atmoUI.live.addEventListener("change", () => { ATMO.hour = atmoUI.live.checked ? null : Number(atmoUI.time.value); syncAtmoUI(); saveAtmo(); });
atmoUI.time.addEventListener("input", () => { ATMO.hour = Number(atmoUI.time.value); syncAtmoUI(); saveAtmo(); });
atmoUI.rain.addEventListener("change", () => { ATMO.rain = atmoUI.rain.checked; saveAtmo(); });
atmoUI.glow.addEventListener("change", () => { ATMO.glow = atmoUI.glow.checked; saveAtmo(); });
window.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || state.mode === "play") return;
  if (e.key === "o" || e.key === "O") toggleAtmo();
});
setInterval(() => { if (atmoUI.panel.classList.contains("open") && ATMO.hour == null) syncAtmoUI(); }, 30000);
state.atmoUI = { toggle: toggleAtmo, sync: syncAtmoUI };


// ---------------------------------------------------------------- Gallery City (ADR-035)
// Parcels on named streets around the Origin; galleries of maze art. Tap a frame to see it close up, tap
// the ground to pick a parcel; on your own parcel, choose a seed and a size, press Hang art, tap a wall.
function showGallery(focusSlot) {
  const host = document.getElementById("islands");
  host.textContent = "";
  const g = state.gallery;
  const claimed = g.parcels.filter(p => p.owner).length;
  const head = document.createElement("div");
  head.className = "note-line";
  head.textContent = `${g.parcels.length} parcels on ${g.streets.length} streets · ${claimed} claimed · ` +
    `${plural((state.art || []).length, "frame")} on the walls. Tap the ground to pick a parcel; tap a frame to look closer.`;
  host.appendChild(head);
  const mineList = g.parcels.filter(p => mine(p));
  for (const p of mineList) host.appendChild(parcelRow(p, false));
  const picked = g.parcels.find(p => p.n === state.parcelSlot);
  if (picked && !mine(picked)) host.appendChild(parcelRow(picked, true));
  const canHang = picked && (mine(picked) || picked.builders.includes(state.me));
  if (canHang) host.appendChild(hangForm(picked));
  status();
  if (focusSlot !== undefined) {
    const p = g.parcels.find(x => x.n === focusSlot);
    if (p) flyTo(plotCenter(p));
  }
}
function parcelRow(p, withOwner) {
  const wrap = document.createElement("div");
  const row = document.createElement("div");
  row.className = "isle parcel-row" + (state.parcelSlot === p.n ? " on" : "");
  row.dataset.parcel = p.n;
  const info = document.createElement("div");
  info.innerHTML = `<b></b><br><span></span>`;
  info.querySelector("b").textContent = p.address;
  info.querySelector("span").textContent = `${p.maxX - p.minX + 1}×${p.maxZ - p.minZ + 1} · up to ${p.height} high` +
    (p.gallery ? " · gallery" : "");
  row.append(info, button("Go", "go", () => { state.parcelSlot = p.n; flyTo(plotCenter(p)); showGallery(); }));
  wrap.appendChild(row);
  wrap.appendChild(ownerRow(Object.assign({ slot: p.n }, p)));
  return wrap;
}
function hangForm(p) {
  const box = document.createElement("div");
  box.className = "hang-form";
  box.innerHTML = `<div class="owner-line">Hang maze art on a wall of ${p.address}</div>`;
  const row = document.createElement("div");
  row.className = "owner-act";
  const seed = document.createElement("input");
  seed.id = "artSeed"; seed.inputMode = "numeric"; seed.placeholder = "seed"; seed.setAttribute("aria-label", "Art seed");
  seed.value = state.artSeed || String(Math.floor(Math.random() * 1e6));
  const size = document.createElement("select");
  size.id = "artSize"; size.setAttribute("aria-label", "Frame size");
  for (const s of ["2x2", "3x2", "3x3", "4x3", "5x4"]) {
    const o = document.createElement("option"); o.value = s; o.textContent = s.replace("x", " × "); size.appendChild(o);
  }
  size.value = state.artSize || "3x2";
  const title = document.createElement("input");
  title.id = "artTitle"; title.placeholder = "title"; title.maxLength = 60; title.setAttribute("aria-label", "Art title");
  title.value = state.artTitle || "";
  const preview = document.createElement("img");
  preview.className = "art-preview";
  preview.alt = "Maze art preview";
  const showPreview = () => { if (/^-?\d+$/.test(seed.value.trim())) preview.src = `/api/v1/art/maze/${seed.value.trim()}.png`; };
  seed.addEventListener("input", showPreview);
  // Keep what was typed: the panel is redrawn whenever art changes anywhere in the city.
  seed.addEventListener("input", () => { state.artSeed = seed.value.trim(); });
  size.addEventListener("change", () => { state.artSize = size.value; });
  title.addEventListener("input", () => { state.artTitle = title.value; });
  showPreview();
  row.append(seed, size, title, preview, button(state.mode === "hang" ? "Tap a wall…" : "Hang art", "hang", () => {
    if (!/^-?\d+$/.test(seed.value.trim())) { toast("The seed is a whole number"); return; }
    state.artSeed = seed.value.trim(); state.artSize = size.value; state.artTitle = title.value.trim();
    setMode("hang");
    toast("Tap a wall of your parcel to hang it");
    showGallery();
  }));
  box.appendChild(row);
  return box;
}
async function hangTap(clientX, clientY) {
  const p = pick(clientX, clientY);
  if (!p) return;
  const n = p.normal.map(Math.round);
  const facing = n[2] === 1 ? "SOUTH" : n[2] === -1 ? "NORTH" : n[0] === 1 ? "EAST" : n[0] === -1 ? "WEST" : null;
  if (!facing) { toast("Hang art on a wall, not a floor or a roof"); return; }
  const [w, h] = (state.artSize || "3x2").split("x").map(Number);
  const alongX = facing === "SOUTH" || facing === "NORTH";
  const start = (alongX ? p.at.x : p.at.z) - Math.floor((w - 1) / 2);
  const body = { x: alongX ? start : p.at.x, y: p.at.y, z: alongX ? p.at.z : start, facing, w, h,
    seed: Number(state.artSeed), title: state.artTitle || undefined, actorId: state.me || undefined };
  try {
    const res = await api(API + "/art", { method: "POST", body: JSON.stringify(body) });
    const words = { HUNG: "Hung", NOT_YOURS: "That wall is not yours to hang on", NO_WALL: "It needs a solid wall behind it and open air in front",
      OVERLAP: "Another frame hangs there", FULL: "This parcel's walls are full", BAD_ACTOR: "Pick a name first" };
    state.lastHang = res;
    toast(res.result === "HUNG" ? `“${res.art.title}” hangs on ${res.art.address}` : (words[res.result] || res.result));
    if (res.result === "HUNG") { setMode("look"); await loadArt(); showGallery(); }
  } catch (e) {
    handleError(e);
  }
}
const artGroup = new THREE.Group();
artGroup.name = "art";
scene.add(artGroup);
const artTextures = new Map();
const frameMat = new THREE.MeshLambertMaterial({ color: 0x2b2118 });
function artTexture(url) {
  if (!artTextures.has(url)) {
    const t = new THREE.TextureLoader().load(url);
    t.colorSpace = THREE.SRGBColorSpace;
    t.magFilter = THREE.NearestFilter;
    artTextures.set(url, t);
  }
  return artTextures.get(url);
}
/** A frame on its wall: the picture just off the face, a dark moulding round it. */
function artModel(a) {
  const g = new THREE.Group();
  const pic = new THREE.Mesh(new THREE.PlaneGeometry(a.w - 0.24, a.h - 0.24),
    new THREE.MeshBasicMaterial({ map: artTexture(a.image) }));
  pic.userData.art = a;
  g.add(pic);
  for (const [w, h, x, y] of [[a.w, 0.14, 0, a.h / 2 - 0.07], [a.w, 0.14, 0, -a.h / 2 + 0.07],
    [0.14, a.h, a.w / 2 - 0.07, 0], [0.14, a.h, -a.w / 2 + 0.07, 0]]) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.08), frameMat);
    m.position.set(x, y, 0);
    m.userData.art = a;
    g.add(m);
  }
  // The picture sits 3 cm off the wall's face, centred on the cubes it covers.
  const cy = a.y + a.h / 2;
  const at = {
    SOUTH: [a.x + a.w / 2, cy, a.z + 1.03], NORTH: [a.x + a.w / 2, cy, a.z - 0.03],
    EAST: [a.x + 1.03, cy, a.z + a.w / 2], WEST: [a.x - 0.03, cy, a.z + a.w / 2],
  }[a.facing];
  g.position.set(at[0], at[1], at[2]);
  g.rotation.y = { SOUTH: 0, NORTH: Math.PI, EAST: Math.PI / 2, WEST: -Math.PI / 2 }[a.facing];
  g.userData.art = a;
  return g;
}
async function loadArt() {
  if (!state.gallery) return;
  const res = await api(API + "/art");
  state.art = res.art;
  const seen = new Set();
  for (const a of res.art) {
    seen.add(a.id);
    const key2 = `${a.id}:${a.x},${a.y},${a.z},${a.facing},${a.w},${a.h},${a.seed}`;
    const had = state.artModels.get(a.id);
    if (had && had.userData.key === key2) continue;
    if (had) artGroup.remove(had);
    const m = artModel(a);
    m.userData.key = key2;
    artGroup.add(m);
    state.artModels.set(a.id, m);
  }
  for (const [id, m] of state.artModels) {
    if (!seen.has(id)) { artGroup.remove(m); state.artModels.delete(id); }
  }
  showGallery();
}
state.artModels = new Map();
/** Look mode in a Gallery City: a frame opens the viewer; the ground picks the parcel under it. */
function lookTap(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  pointer.set(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
  ray.setFromCamera(pointer, camera);
  const hitArt = ray.intersectObjects(artGroup.children, true)[0];
  const p = pick(clientX, clientY);
  if (hitArt && (!p || hitArt.distance <= camera.position.distanceTo(new THREE.Vector3(...p.point)) + 0.2)) {
    openViewer(hitArt.object.userData.art);
    return;
  }
  if (!p) return;
  const parcel = state.gallery.parcels.find(q => p.at.x >= q.minX && p.at.x <= q.maxX && p.at.z >= q.minZ && p.at.z <= q.maxZ);
  if (parcel) { state.parcelSlot = parcel.n; showGallery(); toast(parcel.address + (parcel.owner ? ` · ${shortName(parcel.owner)}` : " · open")); }
}
function openViewer(a) {
  const v = document.getElementById("viewer");
  v.querySelector("img").src = a.image;
  v.querySelector(".v-title").textContent = a.title;
  v.querySelector(".v-meta").textContent = `${a.generator} · seed ${a.seed} · ${a.w} × ${a.h} · ${a.address}` +
    (a.owner ? ` · hung by ${shortName(a.owner)}` : " · the gallery's own");
  const down = v.querySelector(".v-down");
  down.style.display = a.owner && state.me && a.owner === state.me ? "" : "none";
  down.onclick = async () => {
    try {
      const res = await api(`${API}/art/${encodeURIComponent(a.id)}?actorId=${encodeURIComponent(state.me)}`, { method: "DELETE" });
      toast(res.result === "TAKEN_DOWN" ? "Taken down" : res.result);
      closeViewer();
      await loadArt();
    } catch (e) { handleError(e); }
  };
  v.style.display = "block";
  state.viewing = a;
}
function closeViewer() { document.getElementById("viewer").style.display = "none"; state.viewing = null; }
document.getElementById("viewerClose").onclick = closeViewer;
function streetLabels() {
  for (const s of state.gallery.streets) {
    for (const f of [0.18, 0.5, 0.82]) {
      const label = labelSprite(s.name);
      label.material.depthTest = true;
      label.scale.set(10, 1.9, 1);
      label.position.set(s.x1 + (s.x2 - s.x1) * f + 0.5, 2.2, s.z1 + (s.z2 - s.z1) * f + 0.5);
      label.name = "street";
      scene.add(label);
    }
  }
}
/** Gallery City's drone (ADR-035): a camera quadcopter of boxes, four rotors that spin. */
function droneModel() {
  const g = new THREE.Group();
  const body = creatureMat(0xf2f3f3), dark = creatureMat(0x2b2d33), lens = creatureMat(0x1fb5b0, true);
  box(g, body, 2.4, 0.8, 2.4, 0, 1.6, 0);
  box(g, dark, 0.8, 0.8, 0.8, 0.9, 1.0, 0);          // camera
  box(g, lens, 0.12, 0.4, 0.4, 1.33, 1.0, 0);
  for (let r = 0; r < 4; r++) {
    const a = Math.PI / 4 + r * Math.PI / 2;
    const x = Math.cos(a) * 2.2, z = Math.sin(a) * 2.2;
    const arm = box(g, dark, 2.6, 0.25, 0.25, x / 2, 1.8, z / 2);
    arm.rotation.y = -a;
    box(g, dark, 0.3, 0.6, 0.3, x, 2.0, z);
    const rotor = new THREE.Group();
    rotor.name = "rotor" + r;
    rotor.position.set(x, 2.35, z);
    box(rotor, dark, 2.2, 0.06, 0.25, 0, 0, 0);
    g.add(rotor);
    box(g, dark, 0.2, 1.2, 0.2, x * 0.6, 0.6, z * 0.6);   // legs
  }
  return g;
}

// ---------------------------------------------------------------- the fight (ADR-037)
// Zelda II, in three dimensions. Standing, you thrust high and your shield covers high; crouching (C, or
// hold Crouch) you thrust low, your shield covers low, and you cannot walk. Foes guard a height and strike
// at one: a shardback's shell guards high, a dust wisp floats too high for a low thrust, a stone knight's
// shield moves and it strikes wherever it is not guarding. A hit knocks you back and leaves you blinking
// for a second. Every foe beaten is EXP on the server; when EXP covers a level, you choose which: Attack,
// Magic or Life. A fall costs your unspent EXP. The rules come from the server (/hero/rules), so every
// client plays the same game.
const HERO = {
  data: null, rules: null, hp: 6, mp: 8, stance: "HIGH", thrust: 0, recover: 0, hitThisThrust: false,
  blink: 0, knock: new THREE.Vector3(), clank: 0, sword: null, shield: null,
};
const FOES = [];
let foeId = 0, spawnTimer = 2, fightOn = false;
state.hero = HERO;
state.foes = FOES;
state.spawning = true;
const THRUST_TIME = 0.24, THRUST_ACTIVE = 0.14, THRUST_RECOVER = 0.36, REACH = 1.75;
function heroName() {
  if (!state.me) {
    state.me = "guest-" + Math.random().toString(36).slice(2, 7);
    safeSet(NAME_KEY, state.me);
    const field = document.getElementById("me");
    if (field) field.value = state.me;
  }
  return state.me;
}
async function loadHero() {
  try {
    if (!HERO.rules) HERO.rules = await api("/api/v1/hero/rules");
    HERO.data = await api(`/api/v1/hero?actorId=${encodeURIComponent(heroName())}`);
  } catch (e) { handleError(e); }
  renderHud();
}
function rule(kind) { return HERO.rules && HERO.rules.foes.find(f => f.kind === kind); }
async function startFight() {
  fightOn = true;
  await loadHero();
  HERO.hp = HERO.data ? HERO.data.maxLife : 6;
  HERO.mp = HERO.data ? HERO.data.maxMagic : 8;
  HERO.stance = "HIGH";
  if (!HERO.sword) armAvatar();
  document.getElementById("heroHud").style.display = "block";
  renderHud();
}
function stopFight() {
  fightOn = false;
  while (FOES.length) removeFoe(FOES[0]);
  document.getElementById("heroHud").style.display = "none";
  document.getElementById("levelUp").style.display = "none";
}
/** A sword in the right hand and a shield on the left arm of the blocky avatar. */
function armAvatar() {
  const m = AVATAR.model;
  const steel = creatureMat(0xd9dde3), hilt = creatureMat(0x7a5232), wood = creatureMat(0x9a6b3f), rim = creatureMat(0xf5cd30);
  const sword = new THREE.Group();
  box(sword, hilt, 0.12, 0.12, 0.3, 0, 0, 0);
  box(sword, steel, 0.08, 0.08, 1.0, 0, 0, -0.62);
  sword.position.set(0.63, 1.05, -0.2);
  sword.name = "sword";
  m.add(sword);
  const shield = new THREE.Group();
  box(shield, wood, 0.12, 0.62, 0.5, 0, 0, 0);
  box(shield, rim, 0.14, 0.16, 0.16, 0.0, 0.0, 0.0);
  shield.position.set(-0.72, 1.3, -0.15);
  shield.name = "shield";
  m.add(shield);
  HERO.sword = sword;
  HERO.shield = shield;
}
function heroThrust() {
  if (!fightOn || HERO.recover > 0) return;
  HERO.thrust = THRUST_TIME;
  HERO.recover = THRUST_RECOVER;
  HERO.hitThisThrust = false;
}
function heroCrouch(down) { if (fightOn) HERO.stance = down ? "LOW" : "HIGH"; }
function heroHeal() {
  if (!fightOn || !HERO.data || !HERO.rules) return;
  if (HERO.mp < HERO.rules.healCost) { toast("Not enough magic"); return; }
  HERO.mp -= HERO.rules.healCost;
  HERO.hp = Math.min(HERO.data.maxLife, HERO.hp + HERO.rules.healAmount);
  toast("Heal!");
  renderHud();
}
function groundAt(x, z, fromY) {
  for (let y = Math.floor(fromY) + 3; y > fromY - 12; y--) {
    if (solidCube(x, y - 1, z) && !solidCube(x, y, z) && !solidCube(x, y + 1, z)) return y;
  }
  return null;
}
/** Night by your own clock (Animal Crossing): eight in the evening to six in the morning. */
function isNight() {
  const h = state.clockHour ?? new Date().getHours();   // state.clockHour lets a test choose the hour
  return h >= 20 || h < 6;
}
/** True on land you hold: your island, plot or parcel is home, and home is safe by day. */
function onHome(x, z) {
  if (!state.me) return false;
  const holds = q => q && q.owner === state.me;
  if (state.district) return holds(plotAt(x, z));
  if (state.gallery) return holds(state.gallery.parcels.find(q => x >= q.minX && x <= q.maxX && z >= q.minZ && z <= q.maxZ));
  return holds(islandAt(x, z));
}
/** Whether foes may come to (x, z): never at the safe places, and at home only after dark. */
function encounterAllowed(x, z) {
  if (safeAt(x, z)) return false;
  if (onHome(x, z) && !isNight()) return false;
  return true;
}
state.encounterAllowed = encounterAllowed;
/** Where foes do not come: spawn pads, the plazas, the obby. */
function safeAt(x, z) {
  const inside = (b, pad = 0) => b && x >= b.minX - pad && x <= b.maxX + pad && z >= b.minZ - pad && z <= b.maxZ + pad;
  if (state.bricks && x >= 2 && x <= 38) return true;
  if (state.bricks && Math.abs(x - state.bricks.spawnX) < 8 && Math.abs(z - state.bricks.spawnZ) < 8) return true;
  if (state.district && Math.abs(x - state.district.padX) < 20 && Math.abs(z - state.district.padZ) < 20) return true;
  if (state.gallery && inside({ minX: state.gallery.plazaMinX, maxX: state.gallery.plazaMaxX, minZ: state.gallery.plazaMinZ, maxZ: state.gallery.plazaMaxZ })) return true;
  return false;
}
function foeModel(kind) {
  const g = new THREE.Group();
  const eye = creatureMat(0xffffff), pupil = creatureMat(0x111111);
  if (kind === "BLIGHT_SLIME") {
    box(g, creatureMat(0x6b3fa0), 0.9, 0.7, 0.9, 0, 0.35, 0);
    box(g, eye, 0.18, 0.18, 0.05, -0.2, 0.5, -0.46); box(g, eye, 0.18, 0.18, 0.05, 0.2, 0.5, -0.46);
    box(g, pupil, 0.08, 0.08, 0.06, -0.2, 0.5, -0.48); box(g, pupil, 0.08, 0.08, 0.06, 0.2, 0.5, -0.48);
  } else if (kind === "SHARDBACK") {
    box(g, creatureMat(0x3a2f2a), 1.1, 0.6, 1.4, 0, 0.45, 0);
    const shell = box(g, creatureMat(0xa070ff, true), 1.2, 0.6, 1.0, 0, 1.0, -0.1);   // the shell guards high
    shell.name = "shell";
    box(g, eye, 0.15, 0.15, 0.05, -0.25, 0.55, -0.72); box(g, eye, 0.15, 0.15, 0.05, 0.25, 0.55, -0.72);
    for (const sx of [-0.6, 0.6]) for (const sz of [-0.4, 0.3]) box(g, creatureMat(0x2a2522), 0.15, 0.4, 0.15, sx, 0.15, sz);
  } else if (kind === "DUST_WISP") {
    box(g, new THREE.MeshLambertMaterial({ color: 0xc9c2b8, transparent: true, opacity: 0.75 }), 0.8, 0.8, 0.8, 0, 0, 0);
    box(g, creatureMat(0xffd27a, true), 0.35, 0.35, 0.35, 0, 0, 0);
    box(g, pupil, 0.1, 0.1, 0.05, -0.15, 0.1, -0.42); box(g, pupil, 0.1, 0.1, 0.05, 0.15, 0.1, -0.42);
  } else {
    const stone = creatureMat(0x7d7b84), dark = creatureMat(0x3d3b42);
    box(g, stone, 0.5, 0.9, 0.5, -0.22, 0.45, 0); box(g, stone, 0.5, 0.9, 0.5, 0.22, 0.45, 0);
    box(g, stone, 1.0, 0.9, 0.6, 0, 1.35, 0);
    box(g, dark, 0.6, 0.55, 0.6, 0, 2.05, 0);
    box(g, creatureMat(0xff3b1f, true), 0.4, 0.08, 0.05, 0, 2.1, -0.31);              // the visor's glow
    const shield = new THREE.Group();
    box(shield, dark, 0.15, 0.75, 0.8, 0, 0, 0);
    shield.position.set(-0.62, 1.4, -0.3);
    shield.name = "knightShield";
    g.add(shield);
    const blade = new THREE.Group();
    box(blade, creatureMat(0xd9dde3), 0.1, 0.1, 1.3, 0, 0, -0.65);
    blade.position.set(0.62, 1.4, -0.2);
    blade.name = "knightSword";
    g.add(blade);
  }
  return g;
}
function spawnFoe(kind, x, z) {
  const r = rule(kind);
  if (!r) return null;
  const y = groundAt(x, z, AVATAR.pos.y);
  if (y === null) return null;
  const f = { id: ++foeId, kind, r, pos: new THREE.Vector3(x + 0.5, y, z + 0.5), hp: r.life, shield: "HIGH",
    shieldTimer: 1.2, windup: 0, striking: null, cooldown: 1.0, blink: 0, knock: new THREE.Vector3(), model: foeModel(kind) };
  if (kind === "DUST_WISP") f.pos.y += 1.4;
  scene.add(f.model);
  FOES.push(f);
  return f;
}
state.spawnFoe = (kind, dx, dz) => {   // a foe dx, dz from the avatar (the harness, and future scripted fights)
  const f = spawnFoe(kind, Math.floor(AVATAR.pos.x + dx), Math.floor(AVATAR.pos.z + dz));
  return f ? f.id : null;
};
function removeFoe(f) {
  scene.remove(f.model);
  const i = FOES.indexOf(f);
  if (i >= 0) FOES.splice(i, 1);
}
function pickKind() {
  const beaten = HERO.data ? HERO.data.beaten : 0;
  const r = Math.random() * 100;
  if (beaten >= 4 && r < 12) return "STONE_KNIGHT";
  if (r < 35) return "SHARDBACK";
  if (r < 55) return "DUST_WISP";
  return "BLIGHT_SLIME";
}
function facingVec() { return new THREE.Vector3(-Math.sin(AVATAR.yaw), 0, -Math.cos(AVATAR.yaw)); }
function fightStep(dt) {
  if (!fightOn) return;
  HERO.thrust = Math.max(0, HERO.thrust - dt);
  HERO.recover = Math.max(0, HERO.recover - dt);
  HERO.blink = Math.max(0, HERO.blink - dt);
  HERO.clank = Math.max(0, HERO.clank - dt);
  // Wild foes come to you, a few at a time, away from the safe places.
  if (state.spawning) {
    spawnTimer -= dt;
    if (spawnTimer <= 0) {
      spawnTimer = 3 + Math.random() * 3;
      if (FOES.length < 3) {
        const a = Math.random() * Math.PI * 2, d = 9 + Math.random() * 5;
        const x = Math.floor(AVATAR.pos.x + Math.cos(a) * d), z = Math.floor(AVATAR.pos.z + Math.sin(a) * d);
        if (encounterAllowed(x, z) && encounterAllowed(Math.floor(AVATAR.pos.x), Math.floor(AVATAR.pos.z))) spawnFoe(pickKind(), x, z);
      }
    }
  }
  const fwd = facingVec();
  const heroCenter = AVATAR.pos.clone().add(new THREE.Vector3(0, 0.9, 0));
  for (const f of [...FOES]) {
    const to = new THREE.Vector3().subVectors(AVATAR.pos, f.pos).setY(0);
    const dist = to.length();
    if (dist > 45) { removeFoe(f); continue; }
    f.blink = Math.max(0, f.blink - dt);
    f.cooldown = Math.max(0, f.cooldown - dt);
    if (f.r.shifting) {
      f.shieldTimer -= dt;
      if (f.shieldTimer <= 0 && f.windup <= 0) { f.shield = f.shield === "HIGH" ? "LOW" : "HIGH"; f.shieldTimer = 0.9 + Math.random() * 0.8; }
    }
    // Close in, unless winding up a strike; knockback carries a foe back.
    const step = new THREE.Vector3();
    if (dist > 1.2 && f.windup <= 0) step.copy(to).normalize().multiplyScalar(f.r.speed * dt);
    step.add(f.knock.clone().multiplyScalar(dt));
    f.knock.multiplyScalar(Math.pow(0.01, dt));
    const nx = f.pos.x + step.x, nz = f.pos.z + step.z;
    if (f.kind === "DUST_WISP") {
      f.pos.x = nx; f.pos.z = nz;
      f.pos.y += ((AVATAR.pos.y + 1.45) - f.pos.y) * Math.min(1, dt * 2);
    } else {
      const gy = groundAt(Math.floor(nx), Math.floor(nz), f.pos.y);
      if (gy !== null && Math.abs(gy - f.pos.y) <= 1.01) { f.pos.x = nx; f.pos.z = nz; f.pos.y = gy; }
    }
    // Strike: a wind-up you can see, then a blow at a height.
    if (f.windup > 0) {
      f.windup -= dt;
      if (f.windup <= 0) {
        const height = f.r.shifting ? (f.shield === "HIGH" ? "LOW" : "HIGH") : f.r.strike;
        if (dist <= 1.95) heroStruck(f, height, to);
        f.cooldown = f.r.shifting ? 1.0 : 1.3;
      }
    } else if (dist <= 1.5 && f.cooldown <= 0 && HERO.blink <= 0) {
      f.windup = 0.45;
    }
  }
  // The thrust: in its first frames, the blade finds the foe in front.
  if (HERO.thrust > THRUST_TIME - THRUST_ACTIVE && !HERO.hitThisThrust) {
    let best = null, bestD = 99;
    for (const f of FOES) {
      const to = new THREE.Vector3().subVectors(f.pos, AVATAR.pos).setY(0);
      const d = to.length();
      if (d > REACH + 0.5 || d < 0.01) continue;
      if (to.normalize().dot(fwd) < 0.6) continue;
      if (d < bestD) { best = f; bestD = d; }
    }
    if (best) {
      HERO.hitThisThrust = true;
      thrustAt(best);
    }
  }
}
function thrustAt(f) {
  const at = HERO.stance;
  let outcome;
  if (f.r.reach && f.r.reach !== at) outcome = "OUT_OF_REACH";
  else outcome = (f.r.shifting ? f.shield : f.r.guard) === at ? "GUARDED" : "HIT";
  if (outcome === "HIT" && f.blink > 0) outcome = "BLINKING";      // still reeling from the last hit
  state.thrusts = (state.thrusts || 0) + 1;
  state.lastThrust = { foe: f.kind, at, outcome, shield: f.shield, n: state.thrusts };
  if (outcome === "GUARDED") {
    HERO.clank = 0.25;
    HERO.knock.add(facingVec().multiplyScalar(-4));
    return;
  }
  if (outcome !== "HIT") return;
  f.hp -= HERO.data ? HERO.data.damage : 1;
  f.blink = 0.25;
  f.knock.copy(facingVec().multiplyScalar(8));
  if (f.hp <= 0) beatFoe(f);
}
async function beatFoe(f) {
  removeFoe(f);
  state.lastBeat = { kind: f.kind, exp: f.r.exp };
  if (Math.random() < 0.25) HERO.hp = Math.min(HERO.data ? HERO.data.maxLife : 6, HERO.hp + 2);
  else if (Math.random() < 0.25) HERO.mp = Math.min(HERO.data ? HERO.data.maxMagic : 8, HERO.mp + 4);
  try {
    const res = await api("/api/v1/hero/defeat", { method: "POST", body: JSON.stringify({ foe: f.kind, actorId: heroName() }) });
    HERO.data = res;
    toast(res.result === "BEAT" ? `${f.r.title} beaten · +${f.r.exp} EXP` : "Too fast!");
  } catch (e) { handleError(e); }
  renderHud();
}
function heroStruck(f, height, awayFromFoe) {
  const shieldUp = HERO.thrust <= 0;          // mid-thrust, the shield is out of place
  if (shieldUp && HERO.stance === height) {
    HERO.clank = 0.25;
    state.lastBlock = { foe: f.kind, height };
    HERO.knock.add(awayFromFoe.clone().normalize().multiplyScalar(3));
    return;
  }
  if (HERO.blink > 0) return;
  const life = HERO.data ? HERO.data.life : 1;
  const hurt = Math.max(1, f.r.power - Math.floor((life - 1) / 2));
  HERO.hp -= hurt;
  HERO.blink = 1.0;
  HERO.knock.add(awayFromFoe.clone().normalize().multiplyScalar(9));
  AVATAR.vel.y = Math.max(AVATAR.vel.y, 5);
  AVATAR.onGround = false;
  state.lastHurt = { foe: f.kind, height, hurt, hp: HERO.hp };
  renderHud();
  if (HERO.hp <= 0) heroFalls();
}
async function heroFalls() {
  while (FOES.length) removeFoe(FOES[0]);
  try { HERO.data = await api("/api/v1/hero/fall", { method: "POST", body: JSON.stringify({ actorId: heroName() }) }); } catch (e) { handleError(e); }
  HERO.hp = HERO.data ? HERO.data.maxLife : 6;
  HERO.mp = HERO.data ? HERO.data.maxMagic : 8;
  placeAvatar(AVATAR.respawn);
  state.lastFall = { at: Date.now() };
  toast("You fell. Your unspent EXP is lost; your levels stay.");
  renderHud();
}
function drawFight(t) {
  if (!fightOn || !AVATAR.model) return;
  const m = AVATAR.model;
  m.visible = HERO.blink <= 0 || Math.floor(t / 70) % 2 === 0;
  m.scale.y = HERO.stance === "LOW" ? 0.72 : 1;
  if (HERO.sword) {
    const out = HERO.thrust > 0 ? Math.sin((1 - HERO.thrust / THRUST_TIME) * Math.PI) * 0.6 : 0;
    HERO.sword.position.set(0.63, HERO.stance === "LOW" ? 0.75 : 1.15, -0.2 - out);
    HERO.shield.position.y = HERO.stance === "LOW" ? 0.75 : 1.35;
  }
  for (const f of FOES) {
    f.model.position.copy(f.pos);
    if (f.kind === "BLIGHT_SLIME") f.model.position.y += Math.abs(Math.sin(t / 160 + f.id)) * 0.35;
    if (f.kind === "DUST_WISP") f.model.position.y += Math.sin(t / 300 + f.id) * 0.15;
    f.model.rotation.y = Math.atan2(-(AVATAR.pos.x - f.pos.x), -(AVATAR.pos.z - f.pos.z));
    f.model.visible = f.blink <= 0 || Math.floor(t / 50) % 2 === 0;
    const ks = f.model.getObjectByName("knightShield");
    if (ks) ks.position.y = f.shield === "HIGH" ? 1.45 : 0.6;
    const kb = f.model.getObjectByName("knightSword");
    if (kb) kb.position.y = (f.shield === "HIGH" ? 0.65 : 1.45) + (f.windup > 0 ? 0.25 : 0);
    f.model.scale.setScalar(f.windup > 0 ? 1.08 : 1);       // the wind-up you learn to read
  }
}
function hearts(hp, max) {
  let s = "";
  for (let i = 0; i < max; i += 2) s += hp >= i + 2 ? "♥" : hp === i + 1 ? "❥" : "♡";
  return s;
}
function renderHud() {
  const hud = document.getElementById("heroHud");
  if (!hud) return;
  const d = HERO.data;
  const max = d ? d.maxLife : 6, mmax = d ? d.maxMagic : 8;
  hud.querySelector(".hearts").textContent = hearts(Math.max(0, HERO.hp), max);
  hud.querySelector(".magic i").style.width = `${Math.round(100 * HERO.mp / mmax)}%`;
  hud.querySelector(".levels").textContent = d ? `ATTACK ${d.attack} · MAGIC ${d.magic} · LIFE ${d.life}` : "";
  const nexts = d ? [d.nextLife, d.nextMagic, d.nextAttack].filter(n => n > 0) : [];
  hud.querySelector(".exp").textContent = d ? `EXP ${d.exp}` + (nexts.length ? ` / ${Math.min(...nexts)}` : "") : "";
  const up = document.getElementById("levelUp");
  if (d && d.canRaise.length) {
    up.style.display = "block";
    for (const b of up.querySelectorAll("button[data-stat]")) {
      const stat = b.dataset.stat;
      const cost = { ATTACK: d.nextAttack, MAGIC: d.nextMagic, LIFE: d.nextLife }[stat];
      b.disabled = !d.canRaise.includes(stat);
      b.textContent = `${stat[0]}${stat.slice(1).toLowerCase()} ${cost > 0 ? cost : "max"}`;
    }
  } else {
    up.style.display = "none";
  }
}
async function raiseStat(stat) {
  try {
    const res = await api("/api/v1/hero/raise", { method: "POST", body: JSON.stringify({ stat, actorId: heroName() }) });
    HERO.data = res;
    if (res.result === "RAISED") {
      HERO.hp = res.maxLife;
      HERO.mp = res.maxMagic;
      toast(`LEVEL UP — ${stat[0]}${stat.slice(1).toLowerCase()} ${res[stat.toLowerCase()]}`);
    }
  } catch (e) { handleError(e); }
  renderHud();
}
for (const b of document.querySelectorAll("#levelUp button[data-stat]")) b.onclick = () => raiseStat(b.dataset.stat);
document.getElementById("levelLater").onclick = () => { document.getElementById("levelUp").style.display = "none"; };
document.getElementById("swordBtn").addEventListener("pointerdown", e => { e.preventDefault(); heroThrust(); });
const crouchBtn = document.getElementById("crouchBtn");
crouchBtn.addEventListener("pointerdown", e => { e.preventDefault(); heroCrouch(true); });
for (const ev of ["pointerup", "pointercancel", "pointerleave"]) crouchBtn.addEventListener(ev, () => heroCrouch(false));
document.getElementById("healBtn").addEventListener("pointerdown", e => { e.preventDefault(); heroHeal(); });
state.heroAct = { thrust: heroThrust, crouch: heroCrouch, heal: heroHeal, raise: raiseStat };
state.clearFoes = () => { while (FOES.length) removeFoe(FOES[0]); };

// ---------------------------------------------------------------- obby (ADR-034)
function showObby() {
  const host = document.getElementById("islands");
  host.textContent = "";
  const o = state.bricks;
  const checkpoints = o.platforms.filter(p => p.checkpoint).length;
  const row = document.createElement("div");
  row.className = "isle obby-row";
  const info = document.createElement("div");
  info.innerHTML = `<b>The obby</b><br>${o.platforms.length} jumps over lava · ${checkpoints} checkpoints · gold finish` +
    `<br><span class="obby-best"></span>`;
  row.appendChild(info);
  row.appendChild(button("Play", "play-obby", () => setMode("play")));
  host.appendChild(row);
  const note = document.createElement("div");
  note.className = "note-line";
  note.textContent = `Build anywhere on the plate up to ${o.height} high; the obby, spawn and runway stay as they are.`;
  host.appendChild(note);
  renderBest();
  status();
}
function renderBest() {
  const el = document.querySelector(".obby-best");
  if (el) el.textContent = AVATAR.best ? `your best: ${(AVATAR.best / 1000).toFixed(1)} s` : "";
}

// ---------------------------------------------------------------- play: a blocky avatar (ADR-034)
// Walk and jump in any world: WASD or arrows and Space, or the stick and the jump button on a tablet.
// Cubes are the ground; water, portals, rainbows and clouds are not. In a Bricks world the obby is live:
// lava sends you back to your last checkpoint, and the gold finish stops the clock.
const AVATAR = {
  on: false, pos: new THREE.Vector3(), vel: new THREE.Vector3(), onGround: false, yaw: 0, model: null,
  keys: new Set(), joy: { x: 0, y: 0 }, pad: { x: 0, y: 0 }, jump: false, respawn: null, reached: -1, finished: false,
  deaths: 0, startedAt: 0, best: 0, last: null, acc: 0,
};
const AV_HALF = 0.32, AV_HEIGHT = 1.8, GRAVITY = 30, JUMP_SPEED = 9.6, RUN_SPEED = 6, STEP = 1 / 120;
const WALK_THROUGH = new Set(["AIR", "WATER", "PORTAL", "CLOUD", ...RAINBOW]);
function solidCube(x, y, z) { return !WALK_THROUGH.has(nameAt(Math.floor(x), Math.floor(y), Math.floor(z))); }
function avatarModel() {
  const g = new THREE.Group();
  const skin = creatureMat(0xf5cd30), shirt = creatureMat(0x0d69ac), pants = creatureMat(0x4b974b);
  const legs = [box(g, pants, 0.42, 0.85, 0.42, -0.22, 0.425, 0), box(g, pants, 0.42, 0.85, 0.42, 0.22, 0.425, 0)];
  box(g, shirt, 0.86, 0.8, 0.44, 0, 1.25, 0);
  const arms = [box(g, skin, 0.38, 0.8, 0.38, -0.63, 1.25, 0), box(g, skin, 0.38, 0.8, 0.38, 0.63, 1.25, 0)];
  box(g, skin, 0.5, 0.5, 0.5, 0, 1.92, 0);
  box(g, creatureMat(0x1b1b1b), 0.08, 0.08, 0.02, -0.1, 1.98, -0.26);
  box(g, creatureMat(0x1b1b1b), 0.08, 0.08, 0.02, 0.1, 1.98, -0.26);
  g.userData.legs = legs;
  g.userData.arms = arms;
  return g;
}
/** Where play starts: a Bricks world's spawn, a Parcels world's helipad, or the top of the first island. */
function spawnPoint() {
  if (state.bricks) return new THREE.Vector3(state.bricks.spawnX + 0.5, state.bricks.spawnY, state.bricks.spawnZ + 0.5);
  if (state.district) return new THREE.Vector3(state.district.padX + 0.5, state.district.padY + 0.5, state.district.padZ + 4.5);
  if (state.gallery) return new THREE.Vector3(state.gallery.padX + 0.5, state.gallery.padY, state.gallery.padZ + 6.5);
  const isle = state.islands[0];
  const x = isle ? isle.x : Math.round(controls.target.x), z = isle ? isle.z : Math.round(controls.target.z);
  for (let y = 120; y > -64; y--) if (solidCube(x, y - 1, z)) return new THREE.Vector3(x + 0.5, y, z + 0.5);
  return new THREE.Vector3(x + 0.5, 60, z + 0.5);
}
function startPlay() {
  if (RIDE.id) toggleRide(RIDE.id);
  flight++;
  AVATAR.on = true;
  AVATAR.respawn = spawnPoint();
  AVATAR.reached = -1;
  AVATAR.finished = false;
  AVATAR.deaths = 0;
  AVATAR.startedAt = performance.now();
  if (!AVATAR.model) { AVATAR.model = avatarModel(); AVATAR.model.name = "avatar"; }
  scene.add(AVATAR.model);
  placeAvatar(AVATAR.respawn);
  // A camera behind the avatar, looking the way the obby runs (−Z).
  controls.target.copy(AVATAR.pos).add(new THREE.Vector3(0, 1.4, 0));
  camera.position.copy(AVATAR.pos).add(new THREE.Vector3(0, 6, 11));
  AVATAR.last = AVATAR.pos.clone();
  document.body.classList.add("playing");
  toast(state.bricks ? "Run the obby! WASD / arrows and Space, or the stick and Jump"
    : "WASD / arrows, Space jumps, J thrusts, hold C to crouch, H heals. Controller: stick moves, A jumps, X thrusts, hold B crouches, Y heals");
  startFight();
}
function stopPlay() {
  AVATAR.on = false;
  AVATAR.keys.clear();
  AVATAR.joy.x = AVATAR.joy.y = 0;
  AVATAR.pad.x = AVATAR.pad.y = 0;
  AVATAR.jump = false;
  if (AVATAR.model) scene.remove(AVATAR.model);
  document.body.classList.remove("playing");
  stopFight();
}
function placeAvatar(p) {
  AVATAR.pos.copy(p);
  AVATAR.vel.set(0, 0, 0);
  AVATAR.onGround = false;
}
function playKey(e, down) {
  const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  if (["w", "a", "s", "d", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(k)) e.preventDefault();
  if (k === " ") { AVATAR.jump = down; return; }
  if (k === "j" || k === "k") { if (down && !e.repeat) heroThrust(); return; }
  if (k === "c" || k === "Control") { heroCrouch(down); return; }
  if (k === "h") { if (down && !e.repeat) heroHeal(); return; }
  if (down && (k === "Escape" || k === "l")) { setMode("look"); return; }
  if (down) AVATAR.keys.add(k); else AVATAR.keys.delete(k);
}
function overlaps(p) {
  for (let x = Math.floor(p.x - AV_HALF); x <= Math.floor(p.x + AV_HALF - 1e-6); x++) {
    for (let y = Math.floor(p.y); y <= Math.floor(p.y + AV_HEIGHT - 1e-6); y++) {
      for (let z = Math.floor(p.z - AV_HALF); z <= Math.floor(p.z + AV_HALF - 1e-6); z++) {
        if (solidCube(x, y, z)) return true;
      }
    }
  }
  return false;
}
function moveAxis(axis, d) {
  if (!d) return false;
  const p = AVATAR.pos;
  p[axis] += d;
  if (!overlaps(p)) return false;
  // Back out to the face we hit. No auto-step: a cube up is a jump, as in the obbies this comes from.
  if (axis === "y") p.y = d > 0 ? Math.floor(p.y + AV_HEIGHT) - AV_HEIGHT - 1e-4 : Math.floor(p.y) + 1;
  else p[axis] = d > 0 ? Math.floor(p[axis] + AV_HALF) - AV_HALF - 1e-4 : Math.floor(p[axis] - AV_HALF) + 1 + AV_HALF + 1e-4;
  return true;
}
function playStep(dt) {
  const fwd = new THREE.Vector3().subVectors(controls.target, camera.position).setY(0);
  if (fwd.lengthSq() < 1e-6) fwd.set(0, 0, -1);
  fwd.normalize();
  const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
  const k = AVATAR.keys;
  let ix = (k.has("d") || k.has("ArrowRight") ? 1 : 0) - (k.has("a") || k.has("ArrowLeft") ? 1 : 0) + AVATAR.joy.x + AVATAR.pad.x;
  let iz = (k.has("w") || k.has("ArrowUp") ? 1 : 0) - (k.has("s") || k.has("ArrowDown") ? 1 : 0) + AVATAR.joy.y + AVATAR.pad.y;
  const len = Math.hypot(ix, iz);
  if (len > 1) { ix /= len; iz /= len; }
  const want = right.multiplyScalar(ix).add(fwd.multiplyScalar(iz));
  const speed = HERO.stance === "LOW" ? 0 : RUN_SPEED;          // crouched, you hold your ground (Zelda II)
  AVATAR.vel.x = want.x * speed + HERO.knock.x;
  AVATAR.vel.z = want.z * speed + HERO.knock.z;
  HERO.knock.multiplyScalar(Math.pow(0.004, dt));
  if (want.lengthSq() > 0.01 && HERO.thrust <= 0) AVATAR.yaw = Math.atan2(-want.x, -want.z);
  if (AVATAR.jump && AVATAR.onGround) { AVATAR.vel.y = JUMP_SPEED; AVATAR.onGround = false; }
  AVATAR.vel.y = Math.max(-40, AVATAR.vel.y - GRAVITY * dt);
  moveAxis("x", AVATAR.vel.x * dt);
  moveAxis("z", AVATAR.vel.z * dt);
  const hitY = moveAxis("y", AVATAR.vel.y * dt);
  if (hitY) { if (AVATAR.vel.y < 0) AVATAR.onGround = true; AVATAR.vel.y = 0; }
  else if (AVATAR.vel.y < 0 || !overlapsBelow()) AVATAR.onGround = false;
  underFoot();
}
function overlapsBelow() {
  const p = AVATAR.pos.clone();
  p.y -= 0.05;
  return overlaps(p);
}
function underFoot() {
  const p = AVATAR.pos;
  const name = nameAt(Math.floor(p.x), Math.floor(p.y - 0.05), Math.floor(p.z));
  if (name === "LAVA" || p.y < -40) { die(); return; }
  if (!state.bricks || !AVATAR.onGround) return;
  const fx = Math.floor(p.x), fz = Math.floor(p.z), fy = Math.floor(p.y - 0.05);
  const on = q => fx >= q.minX && fx <= q.maxX && fz >= q.minZ && fz <= q.maxZ && fy === q.y;
  const i = state.bricks.platforms.findIndex(on);
  if (i > AVATAR.reached) {
    AVATAR.reached = i;
    const q = state.bricks.platforms[i];
    if (q.checkpoint) {
      AVATAR.respawn = new THREE.Vector3((q.minX + q.maxX + 1) / 2, q.y + 1, (q.minZ + q.maxZ + 1) / 2);
      toast(`Checkpoint! ${i + 1} of ${state.bricks.platforms.length}`);
    }
  }
  if (!AVATAR.finished && on(state.bricks.finish)) {
    AVATAR.finished = true;
    const ms = performance.now() - AVATAR.startedAt;
    AVATAR.best = AVATAR.best ? Math.min(AVATAR.best, ms) : ms;
    state.lastFinish = { ms, deaths: AVATAR.deaths };
    toast(`Obby complete! ${(ms / 1000).toFixed(1)} s, ${plural(AVATAR.deaths, "fall")} in the lava`);
    renderBest();
  }
}
function die() {
  AVATAR.deaths++;
  state.lastDeath = { at: AVATAR.pos.toArray(), deaths: AVATAR.deaths };
  placeAvatar(AVATAR.respawn);
  toast(AVATAR.reached >= 0 && state.bricks ? "Ouch! Back to your checkpoint" : "Ouch! Back to the start");
}
// ---------------------------------------------------------------- Controllers (shared DaedalusPad module)
// Left stick / d-pad moves, right stick orbits the camera, A jumps, X or RT thrusts, hold B crouches, Y heals,
// View goes back to look mode, Menu/Start enters or leaves play. Any pad the module knows (standard, community
// mapped retro / arcade / adapter, or taught with BIND on the Prismheart page) works here with the same file.
const PAD = window.DaedalusPad ? window.DaedalusPad.create({
  bundle: "/controllers/controller-bundle.json", digitalStick: false,
  onChange: e => {
    if (e.type === "connect") toast(`${e.pad.name} connected`);
    if (e.type !== "down" && e.type !== "up") return;
    const down = e.type === "down";
    if (e.action === "menu" && down) { setMode(state.mode === "play" ? "look" : "play"); return; }
    if (state.mode !== "play") return;
    if (e.action === "a") AVATAR.jump = down;
    else if ((e.action === "x" || e.action === "zr") && down) heroThrust();
    else if (e.action === "b") heroCrouch(down);
    else if (e.action === "y" && down) heroHeal();
    else if (e.action === "back" && down) setMode("look");
  },
}) : null;
state.pad = PAD;
function padPlay(dtMs) {
  if (!PAD) return;
  PAD.poll();
  const a = PAD.axes();
  const dx = (PAD.held("right") ? 1 : 0) - (PAD.held("left") ? 1 : 0), dy = (PAD.held("up") ? 1 : 0) - (PAD.held("down") ? 1 : 0);
  AVATAR.pad.x = a.lx + dx; AVATAR.pad.y = -a.ly + dy;
  if (a.rx || a.ry) {                                       // right stick orbits around the avatar, rate-based like the hero
    const off = camera.position.clone().sub(controls.target);
    const sph = new THREE.Spherical().setFromVector3(off);
    sph.theta -= a.rx * 2.6 * dtMs / 1000;
    sph.phi = Math.min(Math.PI * 0.47, Math.max(0.15, sph.phi + a.ry * 1.8 * dtMs / 1000));
    camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(sph));
  }
}
function movePlay(t, dtMs) {
  if (!AVATAR.on) return;
  padPlay(dtMs);
  AVATAR.acc = Math.min(0.5, AVATAR.acc + dtMs / 1000);   // a long stall is not a teleport
  while (AVATAR.acc >= STEP) { playStep(STEP); fightStep(STEP); AVATAR.acc -= STEP; }
  drawFight(t);
  const m = AVATAR.model;
  m.position.copy(AVATAR.pos);
  m.rotation.y = AVATAR.yaw;
  const moving = Math.hypot(AVATAR.vel.x, AVATAR.vel.z) > 0.5;
  const swing = moving && AVATAR.onGround ? Math.sin(t / 90) * 0.7 : 0;
  m.userData.legs[0].rotation.x = swing; m.userData.legs[1].rotation.x = -swing;
  m.userData.arms[0].rotation.x = -swing; m.userData.arms[1].rotation.x = swing;
  // The camera follows: whatever moved the avatar moves the view, and the player can still orbit.
  const d = AVATAR.pos.clone().sub(AVATAR.last);
  camera.position.add(d);
  controls.target.add(d);
  AVATAR.last.copy(AVATAR.pos);
}
state.avatar = AVATAR;
function setupStick() {
  const stick = document.getElementById("stick"), knob = document.getElementById("knob");
  let id = null;
  const moveTo = e => {
    const r = stick.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width * 2 - 1, y = (e.clientY - r.top) / r.height * 2 - 1;
    const l = Math.max(1, Math.hypot(x, y));
    AVATAR.joy.x = x / l; AVATAR.joy.y = -y / l;
    knob.style.transform = `translate(${AVATAR.joy.x * 34}px, ${-AVATAR.joy.y * 34}px)`;
  };
  stick.addEventListener("pointerdown", e => { id = e.pointerId; stick.setPointerCapture(id); moveTo(e); });
  stick.addEventListener("pointermove", e => { if (e.pointerId === id) moveTo(e); });
  const end = e => { if (e.pointerId !== id) return; id = null; AVATAR.joy.x = AVATAR.joy.y = 0; knob.style.transform = ""; };
  stick.addEventListener("pointerup", end);
  stick.addEventListener("pointercancel", end);
  const jump = document.getElementById("jumpBtn");
  jump.addEventListener("pointerdown", e => { e.preventDefault(); AVATAR.jump = true; });
  for (const ev of ["pointerup", "pointercancel", "pointerleave"]) jump.addEventListener(ev, () => { AVATAR.jump = false; });
}
setupStick();

// ---------------------------------------------------------------- HUD
let toastTimer = 0;
function toast(text) {
  const t = document.getElementById("toast");
  t.textContent = text;
  t.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.style.display = "none"; }, 2600);
}

function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }
function status() {
  document.getElementById("dot").classList.toggle("on", state.live);
  const cubes = [...state.chunks.values()].reduce((a, d) => a + d.reduce((s, v) => s + (v ? 1 : 0), 0), 0);
  document.getElementById("statusText").textContent =
    `${state.live ? "live" : "offline"} · revision ${state.revision} · ${state.chunks.size} chunks · ` +
    `${cubes.toLocaleString()} cubes · ` + (state.gallery
      ? `${plural(state.gallery.parcels.filter(p => p.owner).length, "parcel")} claimed · ${plural((state.art || []).length, "frame")} · ${plural(state.arks.length, "drone")}`
      : state.bricks
      ? `${plural(state.bricks.platforms.length, "jump")} · ${plural(state.arks.length, "plane")}`
      : state.district
      ? `${plural((state.plots || []).filter(p => p.owner).length, "plot")} claimed · ${plural(state.arks.length, "helicopter")}`
      : `${plural(state.islands.length, "island")} · ${plural(state.arks.length, "ark")}`);
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
    state.me = username;
    setupMe();
    document.getElementById("login").style.display = "none";
    toast("Signed in as " + username);
    if (state.stomp) { try { state.stomp.disconnect(); } catch (e) { /* closing */ } }
    connectLive();
  } catch (e) {
    toast(e.message);
  }
};

// ---------------------------------------------------------------- go
let lastFrame = 0;
let frameCount = 0;
function frame(t) {
  const now = t || 0;
  const dtMs = lastFrame ? Math.min(250, now - lastFrame) : 16;
  lastFrame = now;
  movePlay(now, dtMs);
  controls.update();
  moveArks(t || 0);
  moveCreatures(t || 0);
  applySky();
  moveRain(dtMs);
  if ((frameCount++ % 30) === 0) placeLampLights();
  composer.render();
  requestAnimationFrame(frame);
}
buildPalette();
setupMe();
loadWorlds();
document.getElementById("newWorldGo").onclick = createWorld;
setupWallet();
frame();
window.daedalusRealm = state; // for the browser harness and curious operators
state.pick = pick;           // the exact pick the pointer uses, so a harness can ask what a tap hits
state.debugTarget = () => controls.target.clone();
state.refreshCreatures = refreshCreatures;
state.writeBlock = writeBlock;
state.nameAt = nameAt;
state.lookFrom = (tx, ty, tz, cx, cy, cz) => {   // put the camera at (cx, cy, cz) looking at (tx, ty, tz)
  if (RIDE.id) toggleRide(RIDE.id);
  flight++;
  controls.target.set(tx, ty, tz);
  camera.position.set(cx, cy, cz);  controls.update();
  camera.updateMatrixWorld();   // a tap right after must see the new view, even before the next frame draws
};
state.lookAt = (x, y, z, from) => {   // stand in front of a point and face it (a harness, or a link to a frame)
  if (RIDE.id) toggleRide(RIDE.id);
  flight++;
  controls.target.set(x, y, z);
  camera.position.set(x + from[0] * 6, y + 0.4, z + from[2] * 6);  controls.update();
  camera.updateMatrixWorld();   // a tap right after must see the new view, even before the next frame draws
};
state.project = (x, y, z) => {  // screen pixel of a world point, for a harness to tap a cube
  camera.updateMatrixWorld();
  const v = new THREE.Vector3(x, y, z).project(camera), r = canvas.getBoundingClientRect();
  return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (1 - v.y) / 2 * r.height };
};
(async () => {
  try {
    await detectDistrict();
    await loadWorld();
    await loadIslands();
    await loadGates();
    await loadArks();
    if (state.gallery) await loadArt();
    // A traveller through a gate is met first: the creatures can finish loading while the ark comes up.
    const arriving = arriveThroughGate();
    await loadSpecies();
    await refreshCreatures();
    // A deed's external_url is realm.html#isle=N (ADR-027): open on that island with its Life panel.
    const linked = /^#isle=(\d+)$/.exec(location.hash);
    const target = linked && state.islands.find(i => i.slot === Number(linked[1]));
    const viaGate = /[?&]arrive=\d+(&|$)/.test(location.search);   // the gate view wins
    if (target) { flyTo(target); toggleLife(target.slot); }
    else if (viaGate) { /* arriveThroughGate already looks at the gate */ }
    else if (state.islands.length) flyTo(state.islands[0]);
    else if (state.district) flyTo({ x: state.district.padX, y: 0, z: state.district.padZ + 10 });
    else if (state.bricks) flyTo({ x: state.bricks.spawnX, y: state.bricks.spawnY, z: state.bricks.spawnZ - 20 });
    else if (state.gallery) flyTo({ x: state.gallery.padX, y: 2, z: state.gallery.padZ + 6 });
    await arriving;
    status();
  } catch (e) {
    handleError(e);
  }
  connectLive();
})();
