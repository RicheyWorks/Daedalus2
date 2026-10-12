// SPDX-License-Identifier: MIT
// rd-jukebox: a Reaction / Diffusion / Song jukebox standing in the realm.
// A separate module: realm.js only shares its scene, camera, ground look-up and block colours on
// window.daedalusRealm and fires "realm:islands"; everything jukebox lives here and under /api/v1/jukebox.
//
//  Songs  — guest seed songs (files) + rd-studio engine seeds; no wallet needed.
//  Tokens — a signed-in wallet's RDSong tokens (Robinhood Chain, read-only), each playing its own on-chain HTML
//           in a sandboxed frame (opaque origin: it can't read the sign-in token).
//  Radio  — Radio Browser stations around you, local FM first (ported from ComputerPets; see docs/rd-jukebox.md).
//  Sound  — the player chain (jukebox-audio.js): gain, 10-band EQ + presets, tone filter, output and input devices,
//           with an always-on ear-safety limiter at the end and a live waveform + spectrum.
//  Keys   — a keyboard: per voice an instrument (synth or a real seed-song sample), wave, ADSR, brightness, blend.
//
// Everything the browser plays comes from this origin (seeds, rd-studio renders, the radio relay), so it can run
// through WebAudio without CORS taint. Requests time out (the panel never hangs) and the studio's health is shown.
//
// Look: the panel is a realm .panel (same CSS variables, buttons, spacing); the 3D prop and the panel's accents take
// their colours from the current world's own blocks (by world style), re-themed whenever the world changes.
import * as THREE from "three";
import * as SND from "./jukebox-audio.js";
import * as PRESS from "./rd-press.js";

const API = "/api/v1/jukebox";
const PLACE_KEY = "daedalus.jukebox.place";   // a typed radio place, remembered on this device only
const SOUND_KEY = "daedalus.jukebox.sound";   // EQ / level / filter / voices, remembered on this device only
const TIMEOUT_MS = 4000;                      // no jukebox request may hold the panel longer than this
const POLL_MAX = 20;                          // 202 "rendering" polls per song before giving up quietly

/** Each world style dresses the jukebox in its own blocks (names resolve through the realm's block colours). */
const WORLD_LOOKS = {
  SKY_ISLANDS: { body: "WOOD", trim: "LOG", tubeA: "BLOSSOM", tubeB: "WATER", glow: "LAMP" },
  PARCELS: { body: "ROAD", trim: "PAVING", tubeA: "NEON_PINK", tubeB: "NEON_CYAN", glow: "WINDOW_LIT" },
  BRICKS: { body: "BRICK_RED", trim: "BRICK_WHITE", tubeA: "BRICK_YELLOW", tubeB: "BRICK_BLUE", glow: "SPAWN" },
  GALLERY: { body: "STONE", trim: "PAVING", tubeA: "LAMP", tubeB: "GLASS", glow: "LAMP" },
};
const DEFAULT_LOOK = WORLD_LOOKS.SKY_ISLANDS;
const FALLBACK_HEX = 0x888888;

const J = {
  config: null, seeds: [], tokens: [], me: null, tab: "songs", source: null, playing: false,
  genre: "original", studio: false, studioHealth: { state: "OFF" }, render: SND.sanitizeRender(null), radio: { list: [], note: "", loading: false, dead: new Set() },
  group: null, mats: null, skin: null, coat: null, light: null, look: null, style: null, where: null,
  audio: new Audio(),
  snd: null, mediaSrc: null, lineIn: null, studio: { state: "OFF" }, poll: null,
  voices: { lead: SND.defaultVoice(), bass: { ...SND.defaultVoice(), wave: "triangle", brightness: 0.35 }, pad: { ...SND.defaultVoice(), wave: "sine", attack: 0.4, release: 1.2, blend: 0.6 } },
  voice: "lead", held: new Map(), samples: new Map(), sinks: [], inputs: [],
};
J.audio.crossOrigin = "anonymous";            // same-origin anyway; keeps the element routable through WebAudio
J.audio.preload = "none";
window.daedalusJukebox = J;   // for the browser harness
J.play = it => play(it);

const realm = () => window.daedalusRealm || {};
function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e[k] = v;
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  e.append(...kids.filter(k => k != null));
  return e;
}
async function getJson(path, { auth = false, timeout = TIMEOUT_MS } = {}) {
  const headers = { Accept: "application/json" };
  if (auth && realm().token) headers.Authorization = "Bearer " + realm().token;
  const ac = new AbortController(), timer = setTimeout(() => ac.abort(), timeout);
  let res;
  try { res = await fetch(path, { headers, signal: ac.signal }); }
  catch (e) { throw Object.assign(new Error(e.name === "AbortError" ? "timed out" : "offline"), { status: 0 }); }
  finally { clearTimeout(timer); }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw Object.assign(new Error(body.error || body.detail || "HTTP " + res.status), { status: res.status });
  }
  return res.json();
}
const shortAddr = a => `${a.slice(0, 6)}…${a.slice(-4)}`;

// ---------------------------------------------------------------- world look
function blockHex(name) {
  const c = realm().blockColors || {};
  return c[name] ?? FALLBACK_HEX;
}
function currentLook() {
  return WORLD_LOOKS[realm().style] || DEFAULT_LOOK;
}
const css = hex => "#" + hex.toString(16).padStart(6, "0");
/** Paint the prop and the panel accents in the current world's blocks. Cheap: safe to call on every change. */
function applyLook() {
  J.look = currentLook();
  J.style = realm().style || "SKY_ISLANDS";
  const p = document.getElementById("jukebox");
  if (p) {
    p.style.setProperty("--jb-a", css(blockHex(J.look.tubeA)));
    p.style.setProperty("--jb-b", css(blockHex(J.look.tubeB)));
    p.dataset.world = J.style;
  }
  if (!J.mats) return;
  J.mats.body.color.setHex(blockHex(J.look.body));
  J.mats.trim.color.setHex(blockHex(J.look.trim));
  for (const [m, role] of [[J.mats.tubeA, "tubeA"], [J.mats.tubeB, "tubeB"]]) {
    m.color.setHex(blockHex(J.look[role])); m.emissive.setHex(blockHex(J.look[role]));
  }
  J.light.color.setHex(blockHex(J.look.glow));
}

// ---------------------------------------------------------------- the coat
// Tokens wear their real Turing coat (rd-studio /coat.png for RDSong.tokenHash, a seamless tile). Seeds, and tokens
// when rd-studio is down, wear a Gray-Scott coat grown here from the song's name: deterministic, not the engine's.
function hash32(s) { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
function rng(seed) { let a = seed || 1; return () => { a ^= a << 13; a ^= a >>> 17; a ^= a << 5; return (a >>> 0) / 4294967296; }; }
const REGIMES = [[0.035, 0.065], [0.029, 0.057], [0.042, 0.063], [0.022, 0.051], [0.026, 0.055], [0.039, 0.058]];
class GrownCoat {
  constructor(seed, n = 96) {
    const r = rng(hash32(seed)), [F0, k0] = REGIMES[(r() * REGIMES.length) | 0];
    Object.assign(this, { n, F: F0 + (r() - 0.5) * 0.002, k: k0 + (r() - 0.5) * 0.001, hue: r() });
    this.a = new Float32Array(n * n).fill(1); this.b = new Float32Array(n * n);
    for (let s = 0; s < 40; s++) {
      const cx = (r() * n) | 0, cy = (r() * n) | 0, rad = 2 + ((r() * 3) | 0);
      for (let y = -rad; y <= rad; y++) for (let x = -rad; x <= rad; x++) {
        const j = ((cy + y + n) % n) * n + ((cx + x + n) % n); this.a[j] = 0.5; this.b[j] = 0.25;
      }
    }
    this.canvas = el("canvas", { width: n, height: n });
    this.ctx = this.canvas.getContext("2d"); this.img = this.ctx.createImageData(n, n);
    this.step(2500); this.paint();
  }
  step(iters) {   // Gray-Scott on a torus; Da = .2, Db = .1, dt = 1 keeps the explicit scheme stable
    const { n, F, k, a, b } = this, a2 = new Float32Array(n * n), b2 = new Float32Array(n * n);
    for (let it = 0; it < iters; it++) {
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const i = y * n + x, l = y * n + (x + n - 1) % n, r = y * n + (x + 1) % n, u = ((y + n - 1) % n) * n + x, d = ((y + 1) % n) * n + x;
        const abb = a[i] * b[i] * b[i];
        a2[i] = a[i] + 0.2 * (a[l] + a[r] + a[u] + a[d] - 4 * a[i]) - abb + F * (1 - a[i]);
        b2[i] = b[i] + 0.1 * (b[l] + b[r] + b[u] + b[d] - 4 * b[i]) + abb - (k + F) * b[i];
      }
      a.set(a2); b.set(b2);
    }
  }
  paint(shift = 0) {
    const c = new THREE.Color(), d = this.img.data;
    let max = 1e-6; for (const v of this.b) max = Math.max(max, v);
    for (let i = 0; i < this.n * this.n; i++) {
      const v = Math.min(1, Math.max(0, this.b[i] / max));
      c.setHSL((this.hue + shift + v * 0.25) % 1, 0.8, 0.18 + v * 0.55);
      d[i * 4] = c.r * 255; d[i * 4 + 1] = c.g * 255; d[i * 4 + 2] = c.b * 255; d[i * 4 + 3] = 255;
    }
    this.ctx.putImageData(this.img, 0, 0);
  }
}
function setSkin(texture) {
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  if (J.skin && J.skin !== texture) J.skin.dispose();
  J.skin = texture;
  if (J.mats) { J.mats.coat.map = texture; J.mats.coat.emissiveMap = texture; J.mats.coat.needsUpdate = true; }
}
function growSkin(seed) {
  J.coat = new GrownCoat(seed);
  const t = new THREE.CanvasTexture(J.coat.canvas); t.magFilter = THREE.NearestFilter;
  setSkin(t);
}
/** The token's real coat; falls back to a grown one if the chain or rd-studio can't answer. */
async function tokenSkin(id) {
  const want = J.source;
  try {
    const { hash } = await getJson(`${API}/tokens/${id}/hash`);
    if (!J.config.studio) throw new Error("no studio");
    const tex = await new THREE.TextureLoader().loadAsync(`${API}/coat.png?hash=${hash}&size=512`);
    if (J.source !== want) { tex.dispose(); return; }
    tex.repeat.set(1, 1); tex.anisotropy = 8;
    J.coat = null; setSkin(tex);
    getJson(`${API}/coat?hash=${hash}`).then(meta => {
      if (J.source !== want) return;
      J.mats.coat.roughness = meta.kind === "spots" ? 0.55 : 0.7;
      J.source.coat = meta.traits ? Object.values(meta.traits).slice(0, 3).join(" · ") : meta.kind;
      renderNow();
    }).catch(() => {});
  } catch (e) {
    if (J.source === want) growSkin("token:" + id);
  }
}

// ---------------------------------------------------------------- the prop
// Where it stands: islands — walk in from the dock to the first open ground (never a treetop or a pond);
// parcels, galleries and bricks — beside the world's pad or spawn.
const GROUND = new Set(["GRASS", "DIRT", "SAND", "STONE", "GRAVEL", "PAVING", "ROAD", "BASEPLATE", "HELIPAD"]);
function spot(R) {
  const open = (x, y, z) => ["AIR", "CLOUD"].includes(R.nameAt(x, y, z));
  const groundIn = (x, z, top, bottom) => {
    let y = top; while (y > bottom && open(x, y, z)) y--;
    return y > bottom && GROUND.has(R.nameAt(x, y, z)) && open(x, y + 1, z) && open(x, y + 3, z)
      && open(x, y + 1, z + 1) && open(x + 1, y + 1, z) ? y + 1 : null;
  };
  const isle = R.islands && R.islands[0];
  if (isle && !R.district && !R.gallery && !R.bricks) {
    const dx = isle.dockX ?? isle.x, dz = isle.dockZ ?? (isle.z + isle.radius);
    const top = isle.y + (isle.top || 8) + 2, bottom = isle.y + (isle.bottom ?? -8);
    const steps = Math.max(1, Math.hypot(isle.x - dx, isle.z - dz) | 0);
    for (let s = 3; s <= steps; s++) {
      const x = Math.round(dx + (isle.x - dx) * s / steps), z = Math.round(dz + (isle.z - dz) * s / steps);
      for (const ox of [0, 2, -2, 4, -4]) { const y = groundIn(x + ox, z, top, bottom); if (y != null) return { x: x + ox, y, z }; }
    }
    return { x: Math.round(isle.x), y: isle.y + (isle.top || 8) + 1, z: Math.round(isle.z) };
  }
  const pad = R.district ? { x: R.district.padX, y: R.district.padY, z: R.district.padZ }
    : R.gallery ? { x: R.gallery.padX, y: R.gallery.padY, z: R.gallery.padZ }
    : R.bricks ? { x: R.bricks.spawnX, y: R.bricks.spawnY, z: R.bricks.spawnZ } : null;
  if (!pad) return null;
  for (let r = 6; r <= 16; r += 2) for (const [ox, oz] of [[r, 0], [-r, 0], [0, r], [0, -r]]) {
    const x = Math.round(pad.x + ox), z = Math.round(pad.z + oz), y = groundIn(x, z, pad.y + 8, pad.y - 8);
    if (y != null) return { x, y, z };
  }
  return { x: Math.round(pad.x) + 6, y: pad.y + 1, z: Math.round(pad.z) };
}
function buildProp() {
  const R = realm(); if (!R.scene || !R.nameAt || J.group) return;
  const at = spot(R); if (!at) return;
  const g = new THREE.Group(); g.name = "rd-jukebox"; g.position.set(at.x + 0.5, at.y, at.z + 0.5);
  J.mats = {
    body: new THREE.MeshStandardMaterial({ roughness: 0.6 }),
    trim: new THREE.MeshStandardMaterial({ roughness: 0.3, metalness: 0.4 }),
    coat: new THREE.MeshStandardMaterial({ roughness: 0.4, emissive: 0xffffff, emissiveIntensity: 0.55 }),
    grill: new THREE.MeshStandardMaterial({ color: 0x15110d, roughness: 0.9 }),
    tubeA: new THREE.MeshStandardMaterial({ emissiveIntensity: 1.2, transparent: true, opacity: 0.85 }),
    tubeB: new THREE.MeshStandardMaterial({ emissiveIntensity: 1.2, transparent: true, opacity: 0.85 }),
  };
  const { body: bm, trim, coat, grill: gm } = J.mats;
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.7, 0.9), [bm, bm, bm, bm, coat, bm]);
  body.position.y = 0.85; g.add(body);
  // A full cylinder sunk halfway into the body: the visible half is the arch; its front cap wears the coat.
  const arch = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 0.9, 40), [bm, coat, bm]);
  arch.rotation.x = Math.PI / 2; arch.position.y = 1.7; g.add(arch);
  for (const [dx, m] of [[-0.62, J.mats.tubeA], [0.62, J.mats.tubeB]]) {
    const t = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 1.6, 12), m); t.position.set(dx, 0.95, 0.47); g.add(t);
  }
  const grill = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.45), gm); grill.position.set(0, 0.35, 0.452); g.add(grill);
  const bar = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.06, 0.06), trim); bar.position.set(0, 0.62, 0.47); g.add(bar);
  J.light = new THREE.PointLight(0xffffff, 1.5, 9); J.light.position.set(0, 1.6, 1.2); g.add(J.light);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  R.scene.add(g); J.group = g; J.where = { x: at.x + 0.5, y: at.y, z: at.z + 0.5 };
  growSkin("jukebox:" + (R.style || "SKY_ISLANDS"));
  applyLook();
}

let frameNo = 0;
function animate(t) {
  safetyCheck();
  drawViz();
  if (J.group) {
    const beat = J.playing ? 0.5 + 0.5 * Math.sin(t / 180) : 0.2;
    [J.mats.tubeA, J.mats.tubeB].forEach((m, i) => { m.emissiveIntensity = 0.6 + (J.playing ? 1.2 * Math.abs(Math.sin(t / 240 + i)) : 0.2); });
    J.light.intensity = 0.8 + beat * 2;
    if (J.playing && J.coat && (frameNo++ % 6) === 0) { J.coat.step(6); J.coat.paint((t / 20000) % 1); J.skin.needsUpdate = true; }
    if (J.playing && !J.coat && J.skin) J.skin.offset.y = (t / 60000) % 1;   // a real coat drifts slowly (it tiles)
  }
  requestAnimationFrame(animate);
}

// ---------------------------------------------------------------- the panel (a realm .panel)
const STYLE = `
  #jukebox { left: 12px; top: var(--jb-top, 76px); width: min(340px, calc(100vw - 24px)); max-height: calc(100vh - var(--jb-top, 76px) - 94px);
    display: flex; flex-direction: column; padding: 12px; z-index: 6; opacity: 0; transform: translateY(8px);
    pointer-events: none; transition: opacity .18s ease, transform .18s ease; border-top: 3px solid var(--jb-a, var(--gold)); }
  #jukebox.open { opacity: 1; transform: none; pointer-events: auto; }
  #jukebox h2 { margin: 0; font-size: 13px; color: var(--gold); letter-spacing: .06em; flex: 1; }
  #jukebox .jb-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  #jukebox .jb-tabs { display: flex; gap: 6px; margin-bottom: 8px; }
  #jukebox .jb-tabs button { flex: 1; padding: 0 8px; }
  #jukebox .jb-tabs button.on { border-color: var(--jb-a, var(--gold)); box-shadow: inset 0 -3px 0 var(--jb-b, var(--accent)); }
  #jukebox .jb-now { border: 1px solid var(--line); border-radius: 10px; padding: 8px 10px; margin-bottom: 8px;
    background: rgba(0,0,0,.25); display: flex; gap: 10px; align-items: center; }
  #jukebox .jb-now .eq { width: 18px; height: 18px; display: flex; gap: 2px; align-items: flex-end; }
  #jukebox .jb-now .eq i { flex: 1; background: var(--jb-b, var(--accent)); height: 30%; border-radius: 1px; }
  #jukebox.playing .jb-now .eq i { animation: jb-eq .9s ease-in-out infinite alternate; }
  #jukebox.playing .jb-now .eq i:nth-child(2) { animation-delay: -.3s; } #jukebox.playing .jb-now .eq i:nth-child(3) { animation-delay: -.6s; }
  @keyframes jb-eq { from { height: 20%; } to { height: 100%; } }
  #jukebox .jb-now b { display: block; color: var(--text); font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  #jukebox .jb-now span { color: var(--dim); font-size: 11px; }
  #jukebox .jb-now > div { flex: 1; min-width: 0; }
  #jukebox .jb-list { overflow-y: auto; touch-action: pan-y; flex: 1 1 auto; min-height: 60px; }
  #jukebox .jb-group { color: var(--gold); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; margin: 8px 0 2px; }
  #jukebox .jb-row { border-top: 1px solid var(--line); padding: 6px 0; display: flex; gap: 8px; align-items: center; cursor: pointer; }
  #jukebox .jb-row:first-child { border-top: 0; }
  #jukebox .jb-row div { flex: 1; min-width: 0; font-size: 12px; color: var(--dim); }
  #jukebox .jb-row b { display: block; color: var(--text); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  #jukebox .jb-row.on b { color: var(--gold); }
  #jukebox .jb-row.dead { opacity: .45; }
  #jukebox .jb-row img, #jukebox .jb-row .dot { width: 32px; height: 32px; border-radius: 8px; flex: 0 0 auto; object-fit: cover;
    border: 1px solid var(--line); background: linear-gradient(135deg, var(--jb-a, var(--gold)), var(--jb-b, var(--accent))); }
  #jukebox .jb-tag { font-size: 10px; color: var(--accent); border: 1px solid var(--line); border-radius: 6px; padding: 1px 5px; margin-left: 4px; }
  #jukebox .jb-controls { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 8px; }
  #jukebox select, #jukebox input[type=text] { min-height: 44px; font: inherit; color: var(--text); background: rgba(0,0,0,.35);
    border: 1px solid var(--line); border-radius: 10px; padding: 0 8px; min-width: 0; }
  #jukebox input[type=text] { flex: 1; }
  #jukebox label.jb-check { display: flex; align-items: center; gap: 6px; color: var(--dim); font-size: 12px; }
  #jukebox input[type=checkbox] { width: 20px; height: 20px; accent-color: var(--gold); }
  #jukebox .note-line { margin: 6px 0 0; min-height: 14px; }
  #jukebox iframe { width: 100%; height: 160px; border: 1px solid var(--line); border-radius: 10px; background: #000; margin-top: 8px; flex: 0 0 auto; }
  #jukebox .jb-status { font-size: 10px; letter-spacing: .06em; text-transform: uppercase; border: 1px solid var(--line);
    border-radius: 999px; padding: 2px 8px; color: var(--dim); white-space: nowrap; }
  #jukebox .jb-status::before { content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 5px;
    background: var(--dim); vertical-align: 1px; }
  #jukebox .jb-status.UP::before { background: #5ad17a; } #jukebox .jb-status.DEGRADED::before { background: var(--warn, #e0a33a); }
  #jukebox .jb-status.DOWN::before { background: #e05050; }
  #jukebox .jb-tabs { flex-wrap: wrap; } #jukebox .jb-tabs button { min-width: 56px; }
  #jbViz { display: block; width: 100%; height: 44px; margin-bottom: 8px; border-radius: 8px; background: rgba(0,0,0,.3);
    border: 1px solid var(--line); }
  #jbTool { overflow-y: auto; flex: 1 1 auto; min-height: 60px; display: none; font-size: 12px; color: var(--dim); }
  #jukebox.tool #jbTool { display: block; } #jukebox.tool #jbList, #jukebox.tool #jbControls { display: none !important; }
  #jbTool .jb-field { display: flex; align-items: center; gap: 8px; margin: 6px 0; }
  #jbTool .jb-field > span { flex: 0 0 74px; }
  #jbTool .jb-field select, #jbTool .jb-field input[type=range] { flex: 1; min-width: 0; }
  #jbTool input[type=range] { accent-color: var(--jb-a, var(--gold)); min-height: 28px; }
  #jbTool .jb-seg { display: flex; gap: 4px; flex: 1; } #jbTool .jb-seg button { flex: 1; min-height: 36px; padding: 0 4px; }
  #jbTool .jb-seg button.on { border-color: var(--jb-a, var(--gold)); box-shadow: inset 0 -3px 0 var(--jb-b, var(--accent)); color: var(--text); }
  #jbTool .jb-eq { display: flex; justify-content: space-between; gap: 2px; height: 120px; margin: 6px 0 2px; }
  #jbTool .jb-eq label { display: flex; flex-direction: column; align-items: center; flex: 1; font-size: 9px; gap: 2px; }
  #jbTool .jb-eq input { writing-mode: vertical-lr; direction: rtl; width: 22px; height: 96px; min-height: 0; }
  #jukebox .jb-press { display: grid; grid-template-columns: minmax(140px, 200px) 1fr; gap: 12px; align-items: center; margin-top: 8px; }
  #jukebox .jb-press canvas { width: 100%; aspect-ratio: 1; border-radius: 50%; box-shadow: 0 6px 24px rgba(0,0,0,.45); }
  #jukebox .jb-press-txt { display: flex; flex-direction: column; gap: 4px; }
  #jukebox .jb-press-txt progress { width: 100%; height: 6px; accent-color: var(--jb-a, #e0b04a); }
  #jukebox .jb-press-alt { grid-column: 1 / -1; display: flex; gap: 8px; flex-wrap: wrap; }
  #jukebox .jb-btn { border: 1px solid var(--line); background: var(--jb-a, #e0b04a); color: #111; border-radius: 8px; padding: 6px 10px; cursor: pointer; font: inherit; }
  #jukebox .jb-btn.ghost { background: transparent; color: var(--text); }
  @media (prefers-reduced-motion: reduce) { #jukebox .jb-press canvas { box-shadow: none; } }
  #jbTool .jb-sub { margin: 10px 0 2px; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted, #999); }
  #jbTool .jb-row { display: flex; align-items: center; gap: 8px; }
  #jbTool .jb-val { min-width: 52px; font-variant-numeric: tabular-nums; }
  #jbTool .jb-safe { color: var(--text); border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px; margin: 8px 0;
    background: rgba(0,0,0,.25); }
  #jbTool .jb-keys { position: relative; height: 92px; margin: 10px 0 4px; user-select: none; touch-action: none; }
  #jbTool .jb-keys button { position: absolute; top: 0; bottom: 0; padding: 0; min-height: 0; border-radius: 0 0 6px 6px;
    background: #f2f2ee; border: 1px solid var(--line); color: #555; font-size: 9px; display: flex; align-items: flex-end; justify-content: center; }
  #jbTool .jb-keys button.black { background: #1b1b1f; color: #aaa; bottom: 38%; z-index: 1; }
  #jbTool .jb-keys button.down { background: var(--jb-a, var(--gold)); color: #111; }
  #jukeboxBtn { position: fixed; left: 12px; bottom: max(12px, env(safe-area-inset-bottom)); z-index: 6; }
  body.playing #jukeboxBtn, body.playing #jukebox { display: none; }
  @media (max-width: 720px) {
    #jukebox { left: 8px; right: 8px; top: auto; width: auto; bottom: calc(max(8px, env(safe-area-inset-bottom)) + 70px);
      max-height: 58vh; border-radius: 14px; }
    #jukeboxBtn { bottom: calc(max(12px, env(safe-area-inset-bottom)) + 70px); }
    #jukebox.open ~ #jukeboxBtn { display: none; }
  }`;

function panel() {
  let p = document.getElementById("jukebox");
  if (p) return p;
  document.head.append(el("style", {}, STYLE));
  const tab = (id, label) => el("button", { "data-tab": id, onclick: () => showTab(id) }, label);
  p = el("div", { id: "jukebox", class: "panel", role: "dialog", "aria-label": "Jukebox" },
    el("div", { class: "jb-head" }, el("h2", {}, "JUKEBOX"),
      el("span", { class: "jb-status", id: "jbStatus", title: "rd-studio" }, "studio off"), el("button", { id: "jbClose", title: "Close", "aria-label": "Close", onclick: () => openPanel(false) }, "×")),
    el("div", { class: "jb-tabs", role: "tablist" }, tab("songs", "Songs"), tab("tokens", "Tokens"), tab("radio", "Radio"),
      tab("sound", "Sound"), tab("keys", "Keys")),
    el("div", { class: "jb-now", id: "jbNow" }, el("div", { class: "eq" }, el("i"), el("i"), el("i")),
      el("div", {}, el("b", { id: "jbNowTitle" }, "Nothing playing"), el("span", { id: "jbNowSub" }, "Pick a song")),
      el("button", { id: "jbPlay", "aria-label": "Play or stop", onclick: () => (J.playing ? stop() : play(J.source || firstItem())) }, "▶")),
    el("canvas", { id: "jbViz", width: 640, height: 88, "aria-label": "Waveform and spectrum" }),
    el("div", { id: "jbTop" }),
    el("div", { class: "jb-list", id: "jbList" }),
    el("div", { id: "jbTool" }),
    el("div", { class: "jb-controls", id: "jbControls" },
      el("select", { id: "jbGenre", "aria-label": "Genre", onchange: e => { J.genre = e.target.value; if (J.playing) play(J.source); } }),
      el("label", { class: "jb-check" }, el("input", { type: "checkbox", id: "jbStudio", onchange: e => { J.studio = e.target.checked; if (J.playing) play(J.source); } }), "Studio quality")),
    el("div", { class: "note-line", id: "jbNote" }),
    el("div", { id: "jbStage" }));
  document.body.append(p, el("button", { id: "jukeboxBtn", onclick: () => openPanel(true) }, "♪ Jukebox"));
  applyLook();
  return p;
}
function openPanel(on) {
  panel().classList.toggle("open", on);
  document.getElementById("jukeboxBtn").style.visibility = on ? "hidden" : "";
  if (on && J.where && realm().lookAt) realm().lookAt(J.where.x, J.where.y + 1.2, J.where.z, [0, 0, 1]);
  if (on && J.tab === "radio" && !J.radio.list.length) loadRadio();
}
function showTab(id) {
  J.tab = id;
  if (id === "radio" && !J.radio.list.length && !J.radio.loading) loadRadio();
  render();
}
const note = text => { document.getElementById("jbNote").textContent = text || ""; };

function items() {
  if (J.tab === "tokens") return J.tokens.map(id => ({ kind: "token", id, title: `Token #${id}`, sub: `RDSong · chain ${J.config.chainId}` }));
  if (J.tab === "radio") return J.radio.list.map(s => ({ kind: "radio", ...s, title: s.name,
    sub: [s.band !== "OTHER" ? s.band : null, s.place, s.km != null ? `${s.km} km` : null].filter(Boolean).join(" · ") }));
  return J.seeds.map(s => ({ kind: "seed", ...s, sub: s.studio ? "rd-studio engine seed" : "seed song" }));
}
const firstItem = () => items().find(i => !(i.kind === "radio" && J.radio.dead.has(i.id))) || null;
const same = (a, b) => a && b && a.kind === b.kind && (a.id ?? a.name) === (b.id ?? b.name);

const TOOLS = new Set(["sound", "keys"]);
function render() {
  panel().classList.toggle("tool", TOOLS.has(J.tab));
  renderStatus();
  if (TOOLS.has(J.tab)) {
    for (const b of document.querySelectorAll("#jukebox .jb-tabs button")) {
      b.classList.toggle("on", b.dataset.tab === J.tab); b.setAttribute("aria-selected", b.dataset.tab === J.tab);
    }
    document.getElementById("jbTop").textContent = "";
    renderNow();
    return J.tab === "sound" ? renderSound() : renderKeys();
  }
  for (const b of document.querySelectorAll("#jukebox .jb-tabs button")) {
    b.classList.toggle("on", b.dataset.tab === J.tab);
    b.setAttribute("aria-selected", b.dataset.tab === J.tab);
  }
  const g = document.getElementById("jbGenre");
  if (!g.options.length) for (const x of J.config.genres) g.append(el("option", { value: x }, x[0].toUpperCase() + x.slice(1)));
  document.getElementById("jbControls").style.display = J.tab === "radio" ? "none" : "";
  renderTop(); renderNow();
  const host = document.getElementById("jbList"); host.textContent = "";
  const list = items();
  if (!list.length) host.append(el("div", { class: "note-line" }, emptyText()));
  let lastTier = null;
  for (const it of list) {
    if (it.kind === "radio" && it.tier !== lastTier) {
      lastTier = it.tier;
      host.append(el("div", { class: "jb-group" }, { LOCAL_FM: "Local FM", LOCAL: "Other local", ELSEWHERE: "More stations" }[it.tier]));
    }
    const dead = it.kind === "radio" && J.radio.dead.has(it.id);
    host.append(el("div", { class: "jb-row" + (same(J.source, it) ? " on" : "") + (dead ? " dead" : ""), role: "button", tabindex: "0",
      onclick: () => play(it), onkeydown: e => { if (e.key === "Enter") play(it); } },
      it.cover ? el("img", { src: it.cover, alt: "" }) : el("span", { class: "dot" }),
      el("div", {}, el("b", {}, it.title), it.sub, dead ? " · off the air" : null)));
  }
}
function emptyText() {
  if (J.tab === "tokens") return !J.me ? "Connect a wallet to play the RDSong tokens you hold."
    : !J.config.onChain ? "This server isn't reading the chain." : "This wallet holds no RDSong tokens yet.";
  if (J.tab === "radio") return J.radio.loading ? "Finding stations near you…" : J.radio.note || "No stations.";
  return "No songs on this server.";
}
function renderTop() {
  const top = document.getElementById("jbTop"); top.textContent = "";
  if (J.tab === "tokens" && J.me) top.append(el("div", { class: "note-line" }, `Holder ${shortAddr(J.me)} · ${J.tokens.length} token${J.tokens.length === 1 ? "" : "s"}`));
  if (J.tab !== "radio") return;
  const field = el("input", { type: "text", id: "jbPlace", placeholder: "City, state or country", value: localStorage.getItem(PLACE_KEY) || "" });
  const go = () => { localStorage.setItem(PLACE_KEY, field.value.trim()); loadRadio({ typed: true }); };
  field.onkeydown = e => { if (e.key === "Enter") go(); };
  top.append(el("div", { class: "jb-controls" }, field, el("button", { onclick: go }, "Find"),
    el("button", { title: "Use my location", "aria-label": "Use my location", onclick: () => loadRadio({ locate: true }) }, "Near me")));
  if (J.radio.note && J.radio.list.length) top.append(el("div", { class: "note-line" }, J.radio.note));
}
function renderNow() {
  const s = J.source, t = document.getElementById("jbNowTitle"), sub = document.getElementById("jbNowSub");
  if (!t) return;
  t.textContent = s ? s.title : "Nothing playing";
  sub.textContent = !s ? "Pick a song" : [J.playing ? "Playing" : "Stopped", s.kind === "radio" ? "radio" : J.genre !== "original" ? J.genre : null,
    J.studio && s.kind !== "radio" ? "studio" : null, s.coat || null].filter(Boolean).join(" · ");
  document.getElementById("jbPlay").textContent = J.playing ? "■" : "▶";
  panel().classList.toggle("playing", J.playing);
}

// ---------------------------------------------------------------- sound engine (jukebox-audio.js)
// Built on the first gesture (browsers only start audio after one). Every source joins the chain's input, so the
// limiter is between it and the speakers; if checkChain() ever fails, the context is suspended (silence, not loud).
function ensureSound() {
  if (J.snd) { if (J.snd.ctx.state === "suspended" && !J.unsafe) J.snd.ctx.resume(); return J.snd; }
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  const ctx = SND.trackGraph(new AC({ latencyHint: "playback" }));
  J.snd = SND.createChain(ctx);
  J.mediaSrc = ctx.createMediaElementSource(J.audio);   // from here the element is only heard through the chain
  J.snd.connectSource(J.mediaSrc);
  loadSound();
  return J.snd;
}
function safetyCheck() {
  if (!J.snd) return;
  J.snd.guard();
  if (!J.snd.checkChain()) {
    J.unsafe = true; J.snd.ctx.suspend();
    note("Sound stopped: the safety limiter is missing from the chain. Reload the page.");
  }
}
function saveSound() {
  if (!J.snd) return;
  const st = J.snd.state;
  localStorage.setItem(SOUND_KEY, JSON.stringify({ level: st.level, preset: st.preset, bands: st.bands, filter: st.filter, voices: J.voices, render: J.render }));
}
function loadSound() {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(SOUND_KEY) || "{}") || {}; } catch (e) { saved = {}; }
  const c = J.snd;
  c.setLevel(saved.level);
  if (saved.preset === "custom" && Array.isArray(saved.bands)) saved.bands.slice(0, 10).forEach((db, i) => c.setBand(i, db));
  else c.setPreset(saved.preset);
  c.setFilter(saved.filter);
  J.render = SND.sanitizeRender(saved.render);
  if (saved.voices && typeof saved.voices === "object") for (const k of Object.keys(J.voices)) J.voices[k] = SND.sanitizeVoice(saved.voices[k]);
}

async function listDevices() {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  const all = await navigator.mediaDevices.enumerateDevices().catch(() => []);
  J.sinks = all.filter(d => d.kind === "audiooutput");
  J.inputs = all.filter(d => d.kind === "audioinput");
}
async function setOutput(id) {
  const ctx = J.snd?.ctx;
  if (!ctx || typeof ctx.setSinkId !== "function") return note("This browser can't switch outputs: using the system default.");
  try { await ctx.setSinkId(id === "default" ? "" : id); note("Output switched."); }
  catch (e) { note("That output isn't available."); }
}
async function setInput(id) {
  if (J.lineIn) { J.lineIn.off(); J.lineIn.stream.getTracks().forEach(t => t.stop()); J.lineIn = null; }
  if (id === "player") return note("");
  const c = ensureSound();
  if (!c || !navigator.mediaDevices?.getUserMedia) return note("No line-in on this browser.");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { deviceId: id === "any" ? undefined : { exact: id },
      echoCancellation: true, noiseSuppression: false, autoGainControl: false } });
    const src = c.ctx.createMediaStreamSource(stream);
    J.lineIn = { stream, off: c.connectSource(src) };
    note("Line in is live through the EQ and limiter. Use headphones to avoid feedback.");
    listDevices().then(() => J.tab === "sound" && renderSound());
  } catch (e) { note("Microphone permission was not given."); }
}

/** The waveform (line) over the spectrum (bars), in the world's accent colours. */
let vizBuf = null, vizFreq = null;
function drawViz() {
  const cv = document.getElementById("jbViz");
  if (!cv || !panel().classList.contains("open")) return;
  const g = cv.getContext("2d"), w = cv.width, h = cv.height;
  g.clearRect(0, 0, w, h);
  const cs = getComputedStyle(document.documentElement);
  const a = cs.getPropertyValue("--jb-a").trim() || "#e0b04a", b = cs.getPropertyValue("--jb-b").trim() || "#5ac8e0";
  const an = J.snd?.analyser;
  if (!an) { g.fillStyle = b; g.globalAlpha = .35; g.fillRect(0, h / 2, w, 1); g.globalAlpha = 1; return; }
  vizFreq ||= new Uint8Array(an.frequencyBinCount); vizBuf ||= new Uint8Array(an.fftSize);
  an.getByteFrequencyData(vizFreq); an.getByteTimeDomainData(vizBuf);
  const bars = 48, bw = w / bars;
  g.fillStyle = b; g.globalAlpha = .55;
  for (let i = 0; i < bars; i++) {                       // log-spaced bins: bass is not one bar wide
    const bin = Math.min(vizFreq.length - 1, Math.floor(Math.pow(vizFreq.length, i / bars)));
    const v = vizFreq[bin] / 255;
    g.fillRect(i * bw + 1, h - v * h, bw - 2, v * h);
  }
  g.globalAlpha = 1; g.strokeStyle = a; g.lineWidth = 2; g.beginPath();
  for (let i = 0; i < vizBuf.length; i += 4) {
    const x = i / vizBuf.length * w, y = vizBuf[i] / 255 * h;
    i ? g.lineTo(x, y) : g.moveTo(x, y);
  }
  g.stroke();
}

function field(label, control) { return el("label", { class: "jb-field" }, el("span", {}, label), control); }
function select(id, options, value, onchange) {
  const s = el("select", { id, onchange: e => onchange(e.target.value) });
  for (const [v, t] of options) s.append(el("option", { value: v }, t));
  s.value = value; return s;
}
function slider(id, min, max, step, value, oninput) {
  return el("input", { type: "range", id, min, max, step, value, oninput: e => oninput(+e.target.value) });
}
const cap = s => s[0].toUpperCase() + s.slice(1);

function renderSound() {
  const host = document.getElementById("jbTool"); host.textContent = "";
  const c = ensureSound();
  if (!c) { host.append(el("div", { class: "note-line" }, "This browser has no WebAudio.")); return; }
  const st = c.state;
  const seg = el("div", { class: "jb-seg", role: "radiogroup", "aria-label": "Gain" },
    ...Object.keys(SND.GAIN_LEVELS).map(l => el("button", { class: st.level === l ? "on" : "", "aria-pressed": st.level === l,
      onclick: () => { c.setLevel(l); saveSound(); renderSound(); } }, cap(l))));
  host.append(field("Gain", seg));
  host.append(field("EQ", select("jbPreset", [...Object.keys(SND.PRESETS).map(p => [p, cap(p)]), ...(st.preset === "custom" ? [["custom", "Custom"]] : [])],
    st.preset, v => { c.setPreset(v); saveSound(); renderSound(); })));
  const eq = el("div", { class: "jb-eq" });
  SND.EQ_BANDS.forEach((f, i) => eq.append(el("label", { title: `${f} Hz` },
    slider(`jbBand${i}`, -SND.EQ_RANGE_DB, SND.EQ_RANGE_DB, 0.5, st.bands[i], v => { c.setBand(i, v); saveSound(); document.getElementById("jbPreset").value = "custom"; }),
    f >= 1000 ? `${f / 1000}k` : String(f))));
  host.append(eq);
  host.append(field("Tone", select("jbFilter", Object.keys(SND.FILTERS).map(f => [f, cap(f)]), st.filter, v => { c.setFilter(v); saveSound(); })));
  const canSink = typeof c.ctx.setSinkId === "function";
  host.append(field("Output", select("jbOut", [["default", canSink ? "System default" : "System default (fixed in this browser)"],
    ...J.sinks.filter(d => d.deviceId && d.deviceId !== "default").map((d, i) => [d.deviceId, d.label || `Output ${i + 1}`])], "default", setOutput)));
  host.lastChild.querySelector("select").disabled = !canSink;
  host.append(field("Input", select("jbIn", [["player", "Jukebox player"], ["any", "Line in / mic"],
    ...J.inputs.filter(d => d.deviceId && d.deviceId !== "default").map((d, i) => [d.deviceId, d.label || `Input ${i + 1}`])],
    J.lineIn ? "any" : "player", setInput)));
  // rd-studio r4 render options: applied by the studio to the rendered file (and cached per option set)
  const r = J.render, setR = (k, v) => { J.render = SND.sanitizeRender({ ...J.render, [k]: v }); saveSound(); if (J.source && J.source.kind !== "radio") play(J.source); };
  host.append(el("div", { class: "jb-sub" }, "Studio render"));
  host.append(field("Headphones", select("jbPhones", SND.HEADPHONE_PRESETS.map(p => [p, cap(p)]), r.preset, v => setR("preset", v))));
  const vin = slider("jbVinyl", 0, 100, 10, r.vinyl, v => { vinOut.textContent = v ? `${v}` : "off"; });
  const vinOut = el("span", { class: "jb-val" }, r.vinyl ? `${r.vinyl}` : "off");
  vin.onchange = e => { setR("vinyl", +e.target.value); renderSound(); };
  host.append(field("Vinyl", el("div", { class: "jb-row" }, vin, vinOut)));
  const noiseOn = el("input", { type: "checkbox", id: "jbNoise", checked: r.noise !== "off", disabled: !r.vinyl,
    onchange: e => { setR("noise", e.target.checked ? "-48" : "off"); renderSound(); } });
  const noiseLvl = slider("jbNoiseDb", -60, -30, 1, r.noise === "off" ? -48 : +r.noise, () => {});
  noiseLvl.disabled = r.noise === "off" || !r.vinyl;
  noiseLvl.onchange = e => setR("noise", String(e.target.value));
  host.append(field("Surface noise", el("div", { class: "jb-row" }, noiseOn, noiseLvl, el("span", { class: "jb-val" }, r.noise === "off" ? "off" : `${r.noise} dB`))));
  host.append(field("Hi-Res", el("label", { class: "jb-row" }, el("input", { type: "checkbox", id: "jbFlac", checked: r.format === "flac",
    onchange: e => setR("format", e.target.checked ? "flac" : "mp3") }), el("span", {}, "24-bit FLAC"))));
  host.append(el("div", { class: "jb-safe", id: "jbSafe" },
    "Ear-safety limiter: always on. Everything you hear passes a -10 dB, 20:1 limiter with a fixed ceiling."));
  if (J.source?.kind === "token" && !J.audio.src.includes("/studio/audio/")) host.append(el("div", { class: "note-line" },
    "This token's player runs its own audio in a sandbox, so this EQ can't reach it until rd-studio renders it."));
}

const KEY_ROW = "awsedftgyhujkolp;'";        // a computer keyboard row, C4 upwards (white + black keys)
function renderKeys() {
  const host = document.getElementById("jbTool"); host.textContent = "";
  const c = ensureSound();
  if (!c) { host.append(el("div", { class: "note-line" }, "This browser has no WebAudio.")); return; }
  const v = J.voices[J.voice];
  const set = (k, val) => { J.voices[J.voice] = SND.sanitizeVoice({ ...J.voices[J.voice], [k]: val }); saveSound(); };
  host.append(field("Voice", el("div", { class: "jb-seg" }, ...Object.keys(J.voices).map(k =>
    el("button", { class: J.voice === k ? "on" : "", "aria-pressed": J.voice === k, onclick: () => { J.voice = k; renderKeys(); } }, cap(k))))));
  const samples = J.seeds.filter(s => s.audio).slice(0, 40).map(s => [`sample:${s.name}`, `Sample: ${s.title}`]);
  const studioV = (J.studioVoices || []).map(x => [`studio:${x.name}`, `Studio: ${x.name}`]);
  if (J.config?.studio && !J.studioVoices) loadStudioVoices();
  host.append(field("Instrument", select("jbInst", [["synth", "Synth"], ...studioV, ...samples], v.instrument, val => { set("instrument", val); loadSample(val); })));
  host.append(field("Wave", select("jbWave", SND.WAVES.map(w => [w, cap(w)]), v.wave, val => set("wave", val))));
  for (const [k, label, min, max, step] of [["attack", "Attack", 0.001, 2, 0.001], ["decay", "Decay", 0.001, 3, 0.001],
    ["sustain", "Sustain", 0, 1, 0.01], ["release", "Release", 0.005, 4, 0.005], ["brightness", "Brightness", 0, 1, 0.01], ["blend", "Blend", 0, 1, 0.01]])
    host.append(field(label, slider(`jb_${k}`, min, max, step, v[k], val => set(k, val))));
  // two octaves from C4 (C3 for the bass voice)
  const keys = el("div", { class: "jb-keys", id: "jbKeys" });
  const whites = [0, 2, 4, 5, 7, 9, 11], base = J.voice === "bass" ? 48 : 60;
  let wi = 0;
  for (let n = 0; n < 24; n++) {
    const black = !whites.includes(n % 12), ww = 100 / 14;
    const left = black ? (wi * ww - ww * 0.3) : wi * ww;
    const label = KEY_ROW[n] && n < KEY_ROW.length ? KEY_ROW[n].toUpperCase() : "";
    const k = el("button", { class: black ? "black" : "", "data-note": base + n, "aria-label": `note ${base + n}`,
      style: `left:${left}%;width:${black ? ww * 0.6 : ww}%` }, label);
    k.onpointerdown = e => { e.preventDefault(); k.setPointerCapture(e.pointerId); press(base + n); };
    k.onpointerup = k.onpointercancel = () => release(base + n);
    keys.append(k);
    if (!black) wi++;
  }
  host.append(keys);
  host.append(el("div", { class: "note-line", id: "jbKeysNote" }, v.instrument.startsWith("studio:")
    ? "Studio voice: rd-studio renders each note (rd-voice/1) with this envelope; the synth covers it until the note arrives."
    : J.config?.studio ? "Pick a Studio voice to play rd-studio's own instruments." : ""));
  loadSample(v.instrument);
}
async function loadSample(inst) {
  if (!inst.startsWith("sample:") || J.samples.has(inst) || !J.snd) return;
  const seed = J.seeds.find(s => `sample:${s.name}` === inst);
  if (!seed?.audio) return;
  J.samples.set(inst, null);                            // in flight
  try {
    const ac = new AbortController(), timer = setTimeout(() => ac.abort(), 8000);
    const buf = await (await fetch(seed.audio, { signal: ac.signal })).arrayBuffer();
    clearTimeout(timer);
    const full = await J.snd.ctx.decodeAudioData(buf);
    const len = Math.min(full.length, Math.floor(full.sampleRate * 2));   // a 2 s slice is the instrument
    const slice = J.snd.ctx.createBuffer(full.numberOfChannels, len, full.sampleRate);
    for (let ch = 0; ch < full.numberOfChannels; ch++) slice.copyToChannel(full.getChannelData(ch).subarray(0, len), ch);
    J.samples.set(inst, slice);
  } catch (e) { J.samples.delete(inst); note("That sample didn't load: using the synth."); }
}
async function loadStudioVoices() {
  J.studioVoices = [];
  try {
    const d = await getJson(`${API}/studio/voices`);
    J.studioVoices = (d.voices || []).filter(x => typeof x.name === "string").slice(0, 200);
    J.studioRegister = Object.fromEntries(J.studioVoices.map(x => [x.name, x.register || {}]));
  } catch (e) { J.studioVoices = []; }
  if (J.tab === "keys") renderKeys();
}
/** One studio note (cached per voice + pitch + envelope): fetch rd-studio's render once, decode, keep the buffer. */
const studioNotes = new Map();
function studioNote(c, v, n) {
  const name = v.instrument.slice(7);
  let q; try { q = SND.noteQuery(name, v, n); } catch (e) { return null; }
  const k = q.toString();
  if (!studioNotes.has(k)) {
    studioNotes.set(k, (async () => {
      const r = await getJson(`${API}/studio/note?${k}`);
      const ac = new AbortController(), timer = setTimeout(() => ac.abort(), 8000);
      const buf = await (await fetch(r.url, { signal: ac.signal })).arrayBuffer(); clearTimeout(timer);
      return c.ctx.decodeAudioData(buf);
    })().catch(() => { studioNotes.delete(k); return null; }));
    if (studioNotes.size > 400) studioNotes.delete(studioNotes.keys().next().value);
  }
  return studioNotes.get(k);
}
function playBuffer(c, buf) {
  const src = c.ctx.createBufferSource(); src.buffer = buf;
  const off = c.connectSource(src); src.onended = () => off?.();
  src.start();
  return { stop() { /* the studio render carries its own release tail */ } };
}
function press(n) {
  const c = ensureSound(); if (!c || J.held.has(n) || J.unsafe) return;
  const v = J.voices[J.voice];
  if (v.instrument.startsWith("studio:")) {
    const pending = studioNote(c, v, n);
    if (pending) {
      const hold = { stopped: false, live: null, stop() { this.stopped = true; this.live?.stop(); } };
      J.held.set(n, hold);
      let fallback = null;
      const t = setTimeout(() => { if (!hold.live && !hold.stopped) fallback = SND.noteOn(c, { ...v, instrument: "synth" }, n, null); }, 120);
      pending.then(buf => {
        clearTimeout(t);
        if (!buf) { if (!fallback && !hold.stopped) hold.live = SND.noteOn(c, { ...v, instrument: "synth" }, n, null); return; }
        if (fallback) { fallback.stop(); return; }                      // the synth already covered this press
        if (!hold.stopped) hold.live = playBuffer(c, buf); else playBuffer(c, buf);
      });
      document.querySelector(`#jbKeys [data-note="${n}"]`)?.classList.add("down");
      return;
    }
  }
  J.held.set(n, SND.noteOn(c, v, n, J.samples.get(v.instrument) || null));
  document.querySelector(`#jbKeys [data-note="${n}"]`)?.classList.add("down");
}
function release(n) {
  J.held.get(n)?.stop(); J.held.delete(n);
  document.querySelector(`#jbKeys [data-note="${n}"]`)?.classList.remove("down");
}
addEventListener("keydown", e => {
  if (J.tab !== "keys" || e.repeat || e.metaKey || e.ctrlKey || /INPUT|SELECT|TEXTAREA/.test(document.activeElement?.tagName || "")) return;
  const i = KEY_ROW.indexOf(e.key.toLowerCase()); if (i < 0 || !panel().classList.contains("open")) return;
  e.preventDefault(); press((J.voice === "bass" ? 48 : 60) + i);
});
addEventListener("keyup", e => { const i = KEY_ROW.indexOf(e.key.toLowerCase()); if (i >= 0) release((J.voice === "bass" ? 48 : 60) + i); });

// ---------------------------------------------------------------- studio status
function renderStatus() {
  const chip = document.getElementById("jbStatus"); if (!chip) return;
  const st = J.config?.studio ? (J.studioHealth.state || "UP") : "OFF";
  chip.className = "jb-status " + st;
  chip.textContent = { UP: "studio up", DEGRADED: "studio slow", DOWN: "studio down", OFF: "studio off" }[st] || "studio";
  const h = J.studioHealth;
  chip.title = h.lastError ? `rd-studio: ${h.lastError}` : `rd-studio${h.engine ? " " + h.engine : ""}${h.p95Ms != null ? `, p95 ${h.p95Ms} ms` : ""}`;
}
async function refreshStatus() {
  try {
    const c = await getJson(`${API}/config`);
    J.config = { ...J.config, ...c }; J.studioHealth = c.studioHealth || { state: "OFF" };
  } catch (e) { J.studioHealth = { state: "DOWN", lastError: "the realm didn't answer" }; }
  renderStatus();
}

// ---------------------------------------------------------------- playing
async function play(it) {
  if (!it) return;
  stop(true);
  ensureSound();                                   // a tap started this: the audio context may start now
  J.source = it; J.playing = true;
  note("");
  if (it.kind === "radio") {
    growSkin("radio:" + it.id);
    playUrl(it.play, () => { J.radio.dead.add(it.id); note(`${it.name} is off the air: trying the next station.`); next(it); });
    return render();
  }
  if (it.kind === "token") tokenSkin(it.id); else growSkin("seed:" + it.name);
  const key = it.kind === "token" ? "token:" + it.id : "seed:" + it.name;
  render();
  pressRecord(it, key);
}
/** One arrangement ask, bounded by TIMEOUT_MS: null when the realm or studio is slow. */
async function arrangement(key) {
  try { return await getJson(arrangementUrl(key)); }
  catch (e) { return null; }
}
function arrangementUrl(key) {
  const r = J.render, q = new URLSearchParams({ source: key, genre: J.genre, studio: String(!!J.studio) });
  if (r.format !== "mp3") q.set("format", r.format);           // rd-studio r4 render options; defaults stay off the query
  if (r.preset !== "neutral") q.set("preset", r.preset);
  if (r.vinyl) q.set("vinyl", String(r.vinyl));
  if (r.vinyl && r.noise !== "off") q.set("noise", r.noise);
  return `${API}/arrangement?${q}`;
}

// ---------------------------------------------------------------- pressing your record
// The engine is frozen, so the studio render is always preferred: a miss answers 202 and rd-studio presses it at priority
// (15-20 s). Meanwhile the token's coat is stamped into the label and the groove is cut from its waveform. The raw on-chain
// HTML never plays by itself: it's an opt-in button, quieter, behind its own limiter (rd-audio-shim, server-side).
async function labelFor(it) {
  let seed = it.kind === "token" ? `token:${it.id}` : `seed:${it.name}`, src = it.cover || null;
  if (it.kind === "token") {
    try {
      const { hash } = await getJson(`${API}/tokens/${it.id}/hash`); seed = hash;
      if (J.config.studio) src = `${API}/coat.png?hash=${hash}&size=512`;
    } catch (e) { /* palette from the id */ }
  }
  let img = null;
  if (src) { img = new Image(); img.decoding = "async"; img.src = src; img.onerror = () => J.press?.set({ label: null }); }
  return { seed, img };
}
async function pressRecord(it, key, plain) {
  const stage = document.getElementById("jbStage"); stage.textContent = "";
  const cv = el("canvas", { id: "jbPress", width: 360, height: 360, role: "img", "aria-label": `${it.title}: the record` });
  const head = el("b", { id: "jbPressHead" }, "Pressing your record…"), eta = el("span", { id: "jbPressEta" }, "");
  const bar = el("progress", { id: "jbPressBar", max: 100, value: 0 });
  const alt = el("div", { class: "jb-press-alt" });
  stage.append(el("div", { class: "jb-press", role: "status", "aria-live": "polite" }, cv, el("div", { class: "jb-press-txt" }, head, eta, bar), alt));
  const { seed, img } = await labelFor(it);
  if (J.source !== it) return;
  J.press?.destroy();
  J.press = PRESS.createPress(cv, { seed, label: img });
  rawButton(it, alt);
  const ac = new AbortController(); J.pressAbort = ac;
  let started = null, etaMs = 40_000;           // Prometheus: ~40 s idle, longer while the batch runs
  const tick = setInterval(() => {
    if (J.source !== it || started == null) return;
    const p = PRESS.pressProgress(performance.now() - started, etaMs);
    J.press.set({ phase: "pressing", progress: p }); bar.value = Math.round(p * 100);
    const left = Math.max(0, Math.round((etaMs - (performance.now() - started)) / 1000));
    eta.textContent = left > 0 ? `about ${left} s` : "almost there…";
  }, 250);
  const url = plain ? `${API}/arrangement?${new URLSearchParams({ source: key, genre: "original", studio: "false" })}` : arrangementUrl(key);
  const r = await PRESS.pollArrange(url, {
    signal: ac.signal,
    onPressing: (e) => { if (started != null && e.etaMs > 0) etaMs = Math.max(etaMs, performance.now() - started + e.etaMs);
      if (started == null) { started = performance.now(); etaMs = e.etaMs > 0 ? Math.max(e.etaMs, 15_000) : etaMs; J.press.set({ phase: "pressing", progress: 0.02 }); } },
    onBusy: () => { eta.textContent = "the studio is busy: waiting for a slot…"; },
  });
  clearInterval(tick);
  if (J.source !== it || ac.signal.aborted || it.onchain) return;
  if (r.kind === "ready") {
    head.textContent = started == null ? "Your record" : "Pressed."; eta.textContent = r.data?.note || ""; bar.value = 100;
    J.press.set({ phase: "playing", analyser: J.snd?.analyser || null });
    document.getElementById("jbGuest")?.remove();                     // nothing to wait for any more
    J.playing = true;
    playUrl(r.url, () => retryRender(it, key));
    return render();
  }
  // a genre / studio / option variant failed (QA) or has no render: the default press (original, plain) is still preferred
  const variant = J.genre !== "original" || J.studio || J.render.format !== "mp3" || J.render.preset !== "neutral" || J.render.vinyl;
  if (!plain && variant && (r.kind === "none" || r.kind === "failed")) return pressRecord(it, key, true);
  // the studio couldn't press it: seeds have their own file (through the limiter); tokens stay visual + opt-in raw
  J.press.set({ phase: "idle", progress: 0 }); bar.remove();
  const why = { unknown: "rd-studio doesn't know this song.", failed: "the studio's quality check stopped it.", timeout: "the studio is taking too long.",
    unreachable: "rd-studio isn't reachable right now.", none: "rd-studio has no render for this.", bad: "that render option isn't valid." }[r.kind] || "rd-studio didn't answer.";
  if (it.kind === "seed" && it.audio) {
    head.textContent = "Playing the seed file"; eta.textContent = why;
    J.press.set({ phase: "playing", analyser: J.snd?.analyser || null });
    playUrl(it.audio, () => note("That song didn't load."));
  } else {
    head.textContent = r.kind === "failed" ? "This record can't be pressed yet" : "Not pressed"; eta.textContent = why;
    J.playing = false;
    if (it.kind === "token" && rawOptedIn()) playOnChain(it);        // the listener chose on-chain this session
    else if (!(await playGuestSeed(why))) J.playing = false;
  }
  render();
}
/**
 * On-chain playback is an explicit opt-in only ("unprotected"): it loads rd-studio's jukebox live copy of the frozen v6
 * engine (-12 dB after a limiter), never tokenHTML. The choice is remembered for this session only.
 */
const RAW_KEY = "daedalus.jukebox.onchainOptIn";
function rawOptedIn() { try { return sessionStorage.getItem(RAW_KEY) === "1"; } catch (e) { return false; } }
async function playOnChain(it) {
  it.onchain = true;
  J.pressAbort?.abort(); stopPress("On-chain original (unprotected)");
  J.audio.onerror = null; J.audio.pause(); J.audio.removeAttribute("src"); J.audio.load();
  try { sessionStorage.setItem(RAW_KEY, "1"); } catch (e) { /* private mode */ }
  let hash = "";
  try { hash = (await getJson(`${API}/tokens/${it.id}/hash`)).hash; } catch (e) { return note("Couldn't read this token's hash from the chain."); }
  if (J.source !== it) return;
  const stage = document.getElementById("jbStage");
  stage.querySelector("iframe")?.remove();
  stage.append(el("iframe", { src: `${API}/live?hash=${encodeURIComponent(hash)}&id=${it.id}`, sandbox: "allow-scripts", allow: "autoplay",
    title: `Token #${it.id}, on-chain original` }));
  note("On-chain original: the frozen engine at -12 dB with its own limiter, outside this EQ. Tap the art to start it.");
  J.playing = true; render();
}
/** While a record is pressed, or when it can't be: a guest seed plays at jukebox level, through the limiter. */
async function playGuestSeed(head) {
  const seed = J.seeds.find(s => s.audio) || J.seeds.find(s => s.studio);
  if (!seed) return false;
  let url = seed.audio;
  if (!url) { const a = await arrangement("seed:" + seed.name); url = a && a.url; }
  if (!url) return false;
  if (head) { const h = document.getElementById("jbPressEta"); if (h) h.textContent = `${head} Guest seed: ${seed.title}.`; }
  J.playing = true; J.press?.set({ analyser: J.snd?.analyser || null });
  playUrl(url, () => note("The guest seed didn't load."));
  return true;
}
function rawButton(it, host) {
  host.textContent = "";
  if (it.kind === "seed" && it.audio) {
    host.append(el("button", { class: "jb-btn", id: "jbSeedNow", onclick: () => { J.pressAbort?.abort(); stopPress("Playing the seed file"); J.playing = true; playUrl(it.audio, () => note("That song didn't load.")); render(); } }, "Play the seed file now"));
  }
  if (it.kind !== "token") return;
  host.append(el("button", { class: "jb-btn", id: "jbGuest", onclick: () => playGuestSeed("") }, "Play a guest seed while you wait"));
  host.append(el("button", { class: "jb-btn ghost", id: "jbRaw", title: "The frozen engine itself, at -12 dB with a limiter, outside the jukebox's EQ",
    onclick: () => playOnChain(it) }, "Play original on-chain (unprotected)"));
}
function stopPress(head) {
  const h = document.getElementById("jbPressHead"); if (h) h.textContent = head;
  document.getElementById("jbPressBar")?.remove(); const e = document.getElementById("jbPressEta"); if (e) e.textContent = "";
  J.press?.set({ phase: "idle" });
}
/** A render's file vanished (evicted or a new engine): ask for the arrangement once more, then give up on it. */
async function retryRender(it, key) {
  if (J.source !== it || it.retried) return note("That render didn't load: try again.");
  it.retried = true;
  pressRecord(it, key);
}
function playUrl(url, onDead) {
  J.audio.onerror = () => { if (J.playing) { J.playing = false; renderNow(); onDead(); } };
  J.audio.src = url;
  J.audio.play().catch(e => { if (e.name === "NotAllowedError") note("Tap ▶ to start the sound."); });
}
function next(after) {
  const list = items(), i = list.findIndex(x => same(x, after));
  const nxt = list.slice(i + 1).find(x => !J.radio.dead.has(x.id));
  if (nxt) play(nxt); else render();
}
function stop(quiet) {
  clearTimeout(J.poll);
  J.pressAbort?.abort(); J.press?.destroy(); J.press = null;
  J.audio.onerror = null; J.audio.pause(); J.audio.removeAttribute("src"); J.audio.load();
  J.playing = false;
  const stage = document.getElementById("jbStage"); if (stage) stage.textContent = "";
  if (!quiet) renderNow();
}
J.audio.onended = () => { J.playing = false; renderNow(); };

// ---------------------------------------------------------------- radio: where you are
// ComputerPets only uses a place you typed. Here: a typed place first; else the browser's location if you allow it;
// else your browser language's country. With nothing, the directory's popular stations (and a note saying why).
function browserCountry() {
  const m = /-([A-Z]{2})\b/.exec(navigator.language || ""); return m ? m[1] : "";
}
function locate() {
  return new Promise(res => {
    if (!navigator.geolocation) return res(null);
    navigator.geolocation.getCurrentPosition(p => res({ lat: p.coords.latitude, lon: p.coords.longitude }), () => res(null),
      { maximumAge: 30 * 60_000, timeout: 8000 });
  });
}
async function loadRadio({ locate: wantLocation = false } = {}) {
  J.radio.loading = true; J.radio.list = []; render();
  const q = new URLSearchParams();
  const place = localStorage.getItem(PLACE_KEY) || "";
  if (place) q.set("place", place);
  const here = wantLocation || !place ? await locate() : null;
  if (here) { q.set("lat", here.lat.toFixed(4)); q.set("lon", here.lon.toFixed(4)); }
  if (browserCountry()) q.set("country", browserCountry());
  try {
    const r = await getJson(`${API}/radio/stations?${q}`);
    J.radio.list = r.stations; J.radio.note = r.note || (here ? "" : place ? `Near ${place}` : "");
  } catch (e) {
    J.radio.note = "Can't reach the radio directory right now. Try again in a moment.";
  }
  J.radio.loading = false; render();
}

// ---------------------------------------------------------------- holders + world changes
async function refreshHolder() {
  const R = realm(), me = /^0x[0-9a-f]{40}$/.test(R.me || "") && R.token ? R.me : null;
  if (me === J.me) return;
  J.me = me; J.tokens = [];
  if (me && J.config.onChain) {
    try { J.tokens = (await getJson(`${API}/owned`, { auth: true })).tokens; if (J.tokens.length) J.tab = "tokens"; }
    catch (e) { note(e.message); }
  }
  render();
}
function watchWorld() {
  const R = realm();
  if (!J.group) buildProp();
  if ((R.style || "SKY_ISLANDS") !== J.style) applyLook();
  fitUnderHeader();
}
// Sit just below the realm's #top card, whose height changes with its status line.
function fitUnderHeader() {
  const top = document.getElementById("top");
  if (top) document.documentElement.style.setProperty("--jb-top", `${Math.round(top.getBoundingClientRect().bottom + 8)}px`);
}

async function boot() {
  try { J.config = await getJson(`${API}/config`); } catch (e) { return; }
  if (!J.config.enabled) return;                 // the jukebox is off on this server
  J.studioHealth = J.config.studioHealth || { state: "OFF" };
  try { J.seeds = (await getJson(`${API}/seeds`)).seeds; } catch (e) { J.seeds = []; }
  render();
  setInterval(refreshStatus, 30_000);
  setInterval(safetyCheck, 200);              // the limiter guard must not depend on frames (rAF stalls in background tabs)
  listDevices();
  navigator.mediaDevices?.addEventListener?.("devicechange", () => listDevices().then(() => J.tab === "sound" && renderSound()));
  requestAnimationFrame(animate);
  window.addEventListener("realm:islands", watchWorld);
  window.addEventListener("resize", fitUnderHeader);
  setInterval(() => { watchWorld(); refreshHolder(); }, 1500);
  watchWorld(); refreshHolder();
  addEventListener("pointerup", ev => {   // tap the jukebox in the world to open it
    const R = realm(); if (!J.group || !R.camera || ev.target.tagName !== "CANVAS") return;
    const r = ev.target.getBoundingClientRect(), ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((ev.clientX - r.left) / r.width * 2 - 1, -(ev.clientY - r.top) / r.height * 2 + 1), R.camera);
    if (ray.intersectObject(J.group, true).length) openPanel(true);
  });
}
boot();
