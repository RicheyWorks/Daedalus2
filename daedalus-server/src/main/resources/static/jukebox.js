// SPDX-License-Identifier: MIT
// rd-jukebox: a Reaction / Diffusion / Song jukebox standing on the first island of the realm.
// A separate module on purpose: realm.js only exposes its scene (window.daedalusRealm) and says when the
// islands are in ("realm:islands"); everything jukebox lives here and in /api/v1/jukebox.
//  - Guest (no wallet): plays the seed songs.
//  - Wallet signed in: plays the RDSong tokens that wallet holds on Robinhood Chain (read-only RPC on the
//    server), each in its own on-chain HTML, sandboxed (opaque origin: it cannot read the sign-in token).
//  - The skin is a Gray-Scott reaction-diffusion coat grown from the song's seed (token id or seed name).
//  - Genre + studio go through /api/v1/jukebox/arrangement (rd-studio seam; stubbed until it exists).
import * as THREE from "three";

const J = {
  config: null, seeds: [], tokens: [], me: null, source: null, playing: false,
  group: null, skin: null, glow: [], rd: null, audio: new Audio(), genre: "original", studio: false,
};
window.daedalusJukebox = J;     // for the browser harness

const realm = () => window.daedalusRealm;
const $ = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) k === "class" ? (e.className = v) : k.startsWith("on") ? (e[k] = v) : e.setAttribute(k, v);
  for (const k of kids) e.append(k);
  return e;
};
async function get(path, auth) {
  const headers = { Accept: "application/json" };
  const tok = realm() && realm().token;
  if (auth && tok) headers.Authorization = "Bearer " + tok;
  const r = await fetch(path, { headers });
  if (!r.ok) throw Object.assign(new Error((await r.json().catch(() => ({}))).error || "HTTP " + r.status), { status: r.status });
  return r.json();
}

// ---------------------------------------------------------------- the coat (Gray-Scott reaction-diffusion)
function hash32(s) { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
function rng(seed) { let a = seed || 1; return () => { a ^= a << 13; a ^= a >>> 17; a ^= a << 5; return (a >>> 0) / 4294967296; }; }
class Coat {
  constructor(seed, n = 96) {
    this.n = n; const r = rng(hash32(seed));
    // Known-alive Gray-Scott regimes (spots, worms, mazes, coral), nudged per seed: every coat is a living pattern.
    const regimes = [[0.035, 0.065], [0.029, 0.057], [0.042, 0.063], [0.022, 0.051], [0.026, 0.055], [0.039, 0.058]];
    const [F0, k0] = regimes[(r() * regimes.length) | 0];
    this.F = F0 + (r() - 0.5) * 0.002; this.k = k0 + (r() - 0.5) * 0.001;
    this.hue = r(); this.a = new Float32Array(n * n).fill(1); this.b = new Float32Array(n * n);
    for (let s = 0; s < 40; s++) {
      const cx = (r() * n) | 0, cy = (r() * n) | 0, rad = 2 + ((r() * 3) | 0);
      for (let y = -rad; y <= rad; y++) for (let x = -rad; x <= rad; x++) { const j = ((cy + y + n) % n) * n + ((cx + x + n) % n); this.a[j] = 0.5; this.b[j] = 0.25; }
    }
    this.canvas = $("canvas"); this.canvas.width = this.canvas.height = n;
    this.ctx = this.canvas.getContext("2d"); this.img = this.ctx.createImageData(n, n);
    this.step(2500); this.paint();
  }
  step(iters) {
    const { n, F, k } = this; let a = this.a, b = this.b; const a2 = new Float32Array(n * n), b2 = new Float32Array(n * n);
    for (let it = 0; it < iters; it++) {
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const i = y * n + x, l = y * n + (x + n - 1) % n, rr = y * n + (x + 1) % n, u = ((y + n - 1) % n) * n + x, d = ((y + 1) % n) * n + x;
        const la = a[l] + a[rr] + a[u] + a[d] - 4 * a[i], lb = b[l] + b[rr] + b[u] + b[d] - 4 * b[i], abb = a[i] * b[i] * b[i];
        a2[i] = a[i] + 0.2 * la - abb + F * (1 - a[i]); b2[i] = b[i] + 0.1 * lb + abb - (k + F) * b[i];   // Da·dt ≤ ¼: stable
      }
      a.set(a2); b.set(b2);
    }
  }
  paint(shift = 0) {
    const c = new THREE.Color(), d = this.img.data;
    let max = 1e-6; for (let i = 0; i < this.b.length; i++) max = Math.max(max, this.b[i]);
    for (let i = 0; i < this.n * this.n; i++) {
      const v = Math.min(1, Math.max(0, this.b[i] / max));
      c.setHSL((this.hue + shift + v * 0.25) % 1, 0.8, 0.18 + v * 0.55);
      d[i * 4] = c.r * 255; d[i * 4 + 1] = c.g * 255; d[i * 4 + 2] = c.b * 255; d[i * 4 + 3] = 255;
    }
    this.ctx.putImageData(this.img, 0, 0);
  }
}

// ---------------------------------------------------------------- the prop
// Where it stands: walk in from the island's dock toward its centre and take the first open ground
// (grass, dirt, sand or stone, with headroom), so it never perches on a treetop or in a pond.
const GROUND = new Set(["GRASS", "DIRT", "SAND", "STONE", "GRAVEL"]);
function spot(R, isle) {
  const dx = isle.dockX ?? isle.x, dz = isle.dockZ ?? (isle.z + isle.radius);
  const top = isle.y + (isle.top || 8) + 2, bottom = isle.y + (isle.bottom ?? -8);
  const open = (x, y, z) => ["AIR", "CLOUD"].includes(R.nameAt(x, y, z));
  const steps = Math.max(1, Math.hypot(isle.x - dx, isle.z - dz) | 0);
  if (R.nameAt) for (let s = 3; s <= steps; s++) {
    const x = Math.round(dx + (isle.x - dx) * s / steps), z = Math.round(dz + (isle.z - dz) * s / steps);
    for (const ox of [0, 2, -2, 4, -4]) {
      let y = top; while (y > bottom && open(x + ox, y, z)) y--;           // first solid cube from above
      if (y > bottom && GROUND.has(R.nameAt(x + ox, y, z)) && open(x + ox, y + 1, z) && open(x + ox, y + 3, z)
          && open(x + ox, y + 1, z + 1) && open(x + ox + 1, y + 1, z)) return { x: x + ox, y: y + 1, z };
    }
  }
  return { x: Math.round(isle.x), y: isle.y + (isle.top || 8) + 1, z: Math.round(isle.z) };
}
function buildProp(isle) {
  const R = realm(); if (!R || !R.scene || J.group) return;
  const { x, y, z } = spot(R, isle);
  const g = new THREE.Group(); g.name = "rd-jukebox"; g.position.set(x + 0.5, y, z + 0.5);
  J.rd = new Coat("guest:" + (J.seeds[0] ? J.seeds[0].name : "jukebox"));
  J.skin = new THREE.CanvasTexture(J.rd.canvas); J.skin.colorSpace = THREE.SRGBColorSpace;
  J.skin.magFilter = THREE.NearestFilter; J.skin.wrapS = J.skin.wrapT = THREE.RepeatWrapping;
  const wood = new THREE.MeshStandardMaterial({ color: 0x5a2f17, roughness: 0.6 });
  const coat = new THREE.MeshStandardMaterial({ map: J.skin, roughness: 0.35, emissive: 0xffffff, emissiveMap: J.skin, emissiveIntensity: 0.6 });
  const chrome = new THREE.MeshStandardMaterial({ color: 0xd9d9e0, metalness: 1, roughness: 0.2 });
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.7, 0.9), [wood, wood, wood, wood, coat, wood]);
  body.position.y = 0.85; g.add(body);
  // Full cylinder sunk halfway into the body: the visible top half is the classic arch; its front cap wears the coat.
  const arch = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 0.9, 40), [wood, coat, wood]);
  arch.rotation.x = Math.PI / 2;
  arch.position.y = 1.7; g.add(arch);
  for (const [dx, hue] of [[-0.62, 0.95], [0.62, 0.55]]) {      // bubbler tubes up each side
    const m = new THREE.MeshStandardMaterial({ color: new THREE.Color().setHSL(hue, 1, 0.5), emissive: new THREE.Color().setHSL(hue, 1, 0.5), emissiveIntensity: 1.2, transparent: true, opacity: 0.85 });
    const t = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 1.6, 12), m); t.position.set(dx, 0.95, 0.47); g.add(t); J.glow.push(m);
  }
  const grill = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.45), new THREE.MeshStandardMaterial({ color: 0x1b1410, roughness: 0.9 }));
  grill.position.set(0, 0.35, 0.452); g.add(grill);
  const bar = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.06, 0.06), chrome); bar.position.set(0, 0.62, 0.47); g.add(bar);
  const light = new THREE.PointLight(0xffc070, 1.5, 9); light.position.set(0, 1.6, 1.2); g.add(light); J.light = light;
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.userData.jukebox = true; } });
  R.scene.add(g); J.group = g; J.where = { x: x + 0.5, y, z: z + 0.5 };
  R.jukebox = J;
}
function reskin(seed) {
  if (!J.skin) return;
  J.rd = new Coat(seed); J.skin.image = J.rd.canvas; J.skin.needsUpdate = true;
}
let tick = 0;
function animate(t) {
  if (J.group) {
    const beat = J.playing ? 0.5 + 0.5 * Math.sin(t / 180) : 0.2;
    J.glow.forEach((m, i) => { m.emissiveIntensity = 0.6 + (J.playing ? 1.2 * Math.abs(Math.sin(t / 240 + i)) : 0.2); });
    if (J.light) J.light.intensity = 0.8 + beat * 2;
    if (J.playing && (tick++ % 6) === 0) { J.rd.step(6); J.rd.paint((t / 20000) % 1); J.skin.needsUpdate = true; }
  }
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);

// ---------------------------------------------------------------- the panel
function panel() {
  if (document.getElementById("jukebox")) return document.getElementById("jukebox");
  const css = $("style", {}, `
    #jukebox{position:fixed;right:14px;bottom:14px;width:330px;max-height:70vh;overflow:auto;z-index:40;background:rgba(22,18,14,.92);
      border:1px solid rgba(245,193,74,.45);border-radius:14px;color:#f2ead8;font:13px system-ui,sans-serif;padding:12px;display:none;box-shadow:0 8px 30px #000a}
    #jukebox.open{display:block} #jukebox h3{margin:0 0 4px;font:700 15px Georgia,serif;color:#f5c14a;letter-spacing:.04em}
    #jukebox .mode{color:#b09a72;font-size:12px;margin-bottom:8px} #jukebox .songs{display:grid;gap:4px;margin:8px 0}
    #jukebox .song{display:flex;gap:8px;align-items:center;background:#ffffff0d;border:1px solid transparent;border-radius:8px;padding:4px 6px;cursor:pointer;color:inherit;text-align:left;font:inherit}
    #jukebox .song.on{border-color:#f5c14a;background:#f5c14a22} #jukebox .song img{width:34px;height:34px;border-radius:50%;object-fit:cover}
    #jukebox .row{display:flex;gap:8px;align-items:center;margin:6px 0} #jukebox select,#jukebox button.act{background:#2a221a;color:#f2ead8;border:1px solid #6b5536;border-radius:7px;padding:4px 8px;font:inherit}
    #jukebox .note{color:#b09a72;font-size:11px;min-height:14px} #jukebox iframe{width:100%;height:190px;border:0;border-radius:8px;background:#000;margin-top:6px}
    #jukeboxBtn{position:fixed;right:14px;bottom:14px;z-index:39;background:#2a1d10;color:#f5c14a;border:1px solid #f5c14a88;border-radius:22px;padding:8px 14px;font:600 13px system-ui;cursor:pointer}
    #jukebox .x{float:right;background:none;border:0;color:#b09a72;font-size:16px;cursor:pointer}`);
  document.head.append(css);
  const genre = $("select", { id: "jbGenre", "aria-label": "genre" });
  const studio = $("input", { type: "checkbox", id: "jbStudio" });
  const p = $("div", { id: "jukebox", role: "dialog", "aria-label": "Jukebox" },
    $("button", { class: "x", title: "close", onclick: () => openPanel(false) }, "×"),
    $("h3", {}, "Reaction / Diffusion / Song"),
    $("div", { class: "mode", id: "jbMode" }, ""),
    $("div", { class: "songs", id: "jbSongs" }),
    $("div", { class: "row" }, $("label", { for: "jbGenre" }, "Genre"), genre,
      $("label", {}, studio, " Studio quality")),
    $("div", { class: "row" }, $("button", { class: "act", id: "jbPlay", onclick: () => (J.playing ? stop() : play(J.source || first())) }, "▶ Play")),
    $("div", { class: "note", id: "jbNote" }),
    $("div", { id: "jbStage" }));
  genre.onchange = () => { J.genre = genre.value; if (J.playing) play(J.source); };
  studio.onchange = () => { J.studio = studio.checked; if (J.playing) play(J.source); };
  document.body.append(p, $("button", { id: "jukeboxBtn", onclick: () => openPanel(true) }, "♪ Jukebox"));
  return p;
}
function openPanel(on) {
  panel().classList.toggle("open", on);
  document.getElementById("jukeboxBtn").style.display = on ? "none" : "";
  if (on && J.where && realm().lookAt) realm().lookAt(J.where.x, J.where.y + 1.2, J.where.z, [0, 0, 1]);
}
const first = () => (J.tokens.length ? { kind: "token", id: J.tokens[0] } : J.seeds[0] ? { kind: "seed", ...J.seeds[0] } : null);
function renderSongs() {
  panel();
  const g = document.getElementById("jbGenre");
  if (!g.options.length) for (const x of (J.config && J.config.genres) || ["original"]) g.append($("option", { value: x }, x[0].toUpperCase() + x.slice(1)));
  const holder = J.tokens.length > 0;
  document.getElementById("jbMode").textContent = holder
    ? `Holder ${J.me.slice(0, 6)}…${J.me.slice(-4)} · ${J.tokens.length} token${J.tokens.length === 1 ? "" : "s"} · chain ${J.config.chainId}`
    : J.me ? `Wallet ${J.me.slice(0, 6)}…${J.me.slice(-4)} holds no RDSong tokens yet — guest seed songs` : "Guest mode — seed songs (connect a wallet to play your tokens)";
  const host = document.getElementById("jbSongs"); host.textContent = "";
  const items = holder ? J.tokens.map(id => ({ kind: "token", id, title: `Token #${id}` })) : J.seeds.map(s => ({ kind: "seed", ...s }));
  if (!items.length) host.append($("div", { class: "note" }, "No songs configured on this server."));
  for (const it of items) {
    const on = J.source && J.source.kind === it.kind && (it.kind === "token" ? J.source.id === it.id : J.source.name === it.name);
    host.append($("button", { class: "song" + (on ? " on" : ""), onclick: () => play(it) },
      it.cover ? $("img", { src: it.cover, alt: "" }) : $("span", {}, "◉"), $("span", {}, it.title)));
  }
}
async function play(src) {
  if (!src) return;
  stop(true); J.source = src; J.playing = true;
  const key = src.kind === "token" ? "token:" + src.id : "seed:" + src.name;
  reskin(key);
  const note = document.getElementById("jbNote"), stage = document.getElementById("jbStage");
  let arr = null;
  try { arr = await get(`/api/v1/jukebox/arrangement?source=${encodeURIComponent(key)}&genre=${J.genre}&studio=${J.studio}`); } catch (e) { /* seam down: original */ }
  note.textContent = arr ? arr.note : "";
  if (arr && arr.url) { J.audio.src = arr.url; J.audio.play().catch(() => {}); }
  else if (src.kind === "seed") { J.audio.src = src.audio; J.audio.play().catch(e => { note.textContent = "Tap ▶ again to start audio (" + e.name + ")"; }); }
  else {
    // The token plays itself: its own on-chain HTML, sandboxed with no same-origin access.
    stage.append($("iframe", { src: `/api/v1/jukebox/tokens/${src.id}/html`, sandbox: "allow-scripts", allow: "autoplay", title: `Token #${src.id}` }));
  }
  document.getElementById("jbPlay").textContent = "■ Stop";
  renderSongs();
}
function stop(quiet) {
  J.audio.pause(); J.playing = false;
  const stage = document.getElementById("jbStage"); if (stage) stage.textContent = "";
  if (!quiet) { const b = document.getElementById("jbPlay"); if (b) b.textContent = "▶ Play"; }
}
J.audio.onended = () => { J.playing = false; const b = document.getElementById("jbPlay"); if (b) b.textContent = "▶ Play"; };

async function refreshHolder() {
  const R = realm(); const me = R && /^0x[0-9a-f]{40}$/.test(R.me || "") && R.token ? R.me : null;
  if (me === J.me) return;
  J.me = me; J.tokens = [];
  if (me && J.config && J.config.onChain) {
    try { J.tokens = (await get("/api/v1/jukebox/owned", true)).tokens; }
    catch (e) { document.getElementById("jbNote").textContent = e.message; }
  }
  renderSongs();
}

async function boot() {
  try { J.config = await get("/api/v1/jukebox/config"); } catch (e) { return; }
  if (!J.config.enabled) return;                 // the jukebox is off on this server
  try { J.seeds = (await get("/api/v1/jukebox/seeds")).seeds; } catch (e) { J.seeds = []; }
  renderSongs();
  const place = () => { const R = realm(); if (R && R.islands && R.islands.length) buildProp(R.islands[0]); };
  place(); window.addEventListener("realm:islands", place);
  setInterval(refreshHolder, 1500); refreshHolder();
  // Tap the jukebox in the world to open it.
  addEventListener("pointerup", ev => {
    const R = realm(); if (!J.group || !R.camera || ev.target.tagName !== "CANVAS") return;
    const r = ev.target.getBoundingClientRect(), ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((ev.clientX - r.left) / r.width * 2 - 1, -(ev.clientY - r.top) / r.height * 2 + 1), R.camera);
    if (ray.intersectObject(J.group, true).length) openPanel(true);
  });
}
boot();
