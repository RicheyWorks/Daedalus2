// SPDX-License-Identifier: MIT
// The Orrery Reach in the browser (ADR-058). The isles come from /api/v1/reach/orrery: names, seeds, sizes,
// offsets and the column heights that the Java port computes. The cubes are grown here by reach-core.js, the same
// core, and a sample of columns is checked against the server's, so what you see is what Unreal builds.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import * as core from "/reach-core.js";
import * as orrery from "/orrery-core.js";

// Presentation only: each isle's grass and stone, as orr_reach.py paints them in Unreal (the shape is the core's).
const LOOK = {
  "Claude Island": { grass: [0.34, 0.72, 0.26], stone: [0.48, 0.46, 0.54] },
  "Bloomfields": { grass: [0.44, 0.78, 0.30], stone: [0.56, 0.48, 0.40] },
  "Tidewells": { grass: [0.30, 0.66, 0.42], stone: [0.42, 0.46, 0.54] },
  "Lens Forge": { grass: [0.52, 0.56, 0.38], stone: [0.56, 0.54, 0.60] },
  "Vault": { grass: [0.30, 0.40, 0.58], stone: [0.30, 0.30, 0.40] },
};
const SAND = [0.92, 0.82, 0.56], DIRT = [0.50, 0.34, 0.20], HEART = [1.0, 0.42, 0.25], WATER = 0x1a61bf;

const statusEl = document.getElementById("status");
const canvas = document.getElementById("view");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x8fb4e8, 400, 1400);
const camera = new THREE.PerspectiveCamera(55, 1, 0.5, 4000);
camera.position.set(220, 180, 260);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.maxDistance = 1600;
controls.target.set(0, 0, 0);

const hemi = new THREE.HemisphereLight(0xdfe8ff, 0x5a4a3a, 1.2);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff0d8, 2.2);
scene.add(sun);
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.6, 0.5, 0.85);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// Stars, shown at night.
const stars = (() => {
  const n = 2500, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const u = Math.random() * 2 - 1, a = Math.random() * Math.PI * 2, r = 2500;
    const s = Math.sqrt(1 - u * u);
    pos.set([Math.cos(a) * s * r, Math.abs(u) * r * 0.9 + 100, Math.sin(a) * s * r], i * 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const m = new THREE.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, transparent: true, fog: false });
  const p = new THREE.Points(g, m);
  scene.add(p);
  return p;
})();

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  composer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

// Unreal is X/Y across and Z up, in cm; here one cube is one unit with Y up: (x, y, z)ue -> (x, z, y).
const toScene = (x, y, z) => new THREE.Vector3(x, z, y);

const centres = {};

const LOD_NEAR = 700, LOD_FAR = 1600;   // scene units (1 = one cube = 1 m) from the camera to the isle's centre

/** Merged quads ([layer, normal, plane, u0, u1, v0, v1]) as one mesh per layer, offset to the isle's place. */
function quadMeshes(quads, [ox, oy, oz], mats) {
  const per = mats.map(() => ({ pos: [], nrm: [], idx: [] }));
  const NRM = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
  const corner = (q, u, v) => q[1] <= 1 ? [q[2], u, v] : q[1] <= 3 ? [u, q[2], v] : [u, v, q[2]];
  for (const q of quads) {
    const b = per[q[0]];
    const pts = [corner(q, q[3], q[5]), corner(q, q[4], q[5]), corner(q, q[4], q[6]), corner(q, q[3], q[6])]
      .map(([x, y, z]) => toScene(ox + x, oy + y, oz + z));
    const n = NRM[q[1]];
    const ns = toScene(n[0], n[1], n[2]);
    const base = b.pos.length / 3;
    for (const v of pts) { b.pos.push(v.x, v.y, v.z); b.nrm.push(ns.x, ns.y, ns.z); }
    // three.js front faces wind counter-clockwise seen from the normal; the axis swap flips handedness, so check.
    const e1 = pts[1].clone().sub(pts[0]), e2 = pts[2].clone().sub(pts[0]);
    if (e1.cross(e2).dot(ns) > 0) b.idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
    else b.idx.push(base, base + 2, base + 1, base, base + 3, base + 2);
  }
  const g = new THREE.Group();
  per.forEach((b, l) => {
    if (!b.idx.length) return;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(b.pos, 3));
    geo.setAttribute("normal", new THREE.Float32BufferAttribute(b.nrm, 3));
    geo.setIndex(b.pos.length / 3 > 65535 ? new THREE.Uint32BufferAttribute(b.idx, 1) : new THREE.Uint16BufferAttribute(b.idx, 1));
    geo.computeBoundingSphere();
    g.add(new THREE.Mesh(geo, mats[l]));
  });
  return g;
}

function isleMeshes(isle) {
  const p = { seed: isle.seed, radius: isle.radius, summitHeight: isle.summitHeight, depth: isle.depth,
    pondX: isle.pond[0], pondY: isle.pond[1], pondRadius: isle.pond[2] };
  const [ox, oy, oz] = isle.offsetCm.map((v) => v / 100);
  const look = LOOK[isle.name] || LOOK["Claude Island"];
  const g = look.grass;
  const colours = [g, SAND, DIRT, look.stone, HEART, [g[0] * 1.25 + 0.04, g[1] * 1.18, g[2] * 0.8]];
  // One merged surface mesh per layer (ADR-062, Minecraft's rule 3): only the visible faces, merged greedily by the
  // same core as Unreal (mesh() = DaedalusVoxelIsleCore Mesh(), parity-tested), instead of an instanced cube per block.
  // Far away (rule 5, like Distant Horizons) the coarse meshLod() versions stand in: 4x4 then 8x8 columns per cell.
  const mats = colours.map((col, l) => {
    const c = new THREE.Color().setRGB(...col, THREE.SRGBColorSpace);
    return l === core.HEART
      ? new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: 2.5, roughness: 0.4, flatShading: true })
      : new THREE.MeshStandardMaterial({ color: c, roughness: 0.9, flatShading: true });
  });
  const quads = core.mesh(p);
  const lod = new THREE.LOD();
  lod.addLevel(quadMeshes(quads, [0, 0, 0], mats), 0);
  lod.addLevel(quadMeshes(core.meshLod(p, 4), [0, 0, 0], mats), LOD_NEAR);
  lod.addLevel(quadMeshes(core.meshLod(p, 8), [0, 0, 0], mats), LOD_FAR);
  lod.position.copy(toScene(ox, oy, oz));   // LOD picks its level by the camera's distance to this point
  const group = new THREE.Group();
  group.add(lod);
  const cubes = { n: quads.length };
  if (p.pondRadius > 0) {
    const water = new THREE.Mesh(new THREE.CircleGeometry(p.pondRadius * 1.05, 48),
      new THREE.MeshStandardMaterial({ color: WATER, roughness: 0.15, metalness: 0.1, transparent: true, opacity: 0.85 }));
    water.rotation.x = -Math.PI / 2;
    water.position.copy(toScene(ox + p.pondX, oy + p.pondY, oz - 0.6));
    group.add(water);
    // the waterfall where the pond's stream leaves the rim
    const len = Math.hypot(p.pondX, p.pondY) || 1;
    const edge = p.radius * 0.95;
    const falls = new THREE.Mesh(new THREE.BoxGeometry(4, p.depth * 0.7, 4),
      new THREE.MeshStandardMaterial({ color: WATER, transparent: true, opacity: 0.7, roughness: 0.2 }));
    falls.position.copy(toScene(ox + (p.pondX / len) * edge, oy + (p.pondY / len) * edge, oz - p.depth * 0.35));
    group.add(falls);
  }
  // a label above the summit
  const label = textSprite(isle.name);
  label.position.copy(toScene(ox, oy, oz + p.summitHeight + 22));
  group.add(label);
  centres[isle.name] = { at: toScene(ox, oy, oz + 4), r: p.radius, p, o: [ox, oy, oz] };
  return { group, cubes: cubes.n, p };
}

function textSprite(text) {
  const c = document.createElement("canvas");
  c.width = 512; c.height = 96;
  const g = c.getContext("2d");
  g.font = "600 52px system-ui, sans-serif";
  g.textAlign = "center"; g.textBaseline = "middle";
  g.lineWidth = 8; g.strokeStyle = "rgba(10,12,30,.85)"; g.strokeText(text, 256, 48);
  g.fillStyle = "#f5c96a"; g.fillText(text, 256, 48);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthWrite: false, fog: false }));
  s.scale.set(64, 12, 1);
  return s;
}

// Sky bridges from Claude Island's rim to each target's rim, sagging like rope bridges (orr_reach.py).
function bridge(fromName, toName) {
  const a = centres[fromName], b = centres[toName];
  if (!a || !b) return null;
  const dx = b.o[0] - a.o[0], dy = b.o[1] - a.o[1];
  const L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L;
  const sx = a.o[0] + ux * a.r * 0.8, sy = a.o[1] + uy * a.r * 0.8;
  const ex = b.o[0] - ux * b.r * 0.8, ey = b.o[1] - uy * b.r * 0.8;
  const topAt = (c, wx, wy) => {
    const t = core.columnTop(c.p, Math.floor(wx - c.o[0]), Math.floor(wy - c.o[1]));
    return c.o[2] + (t === core.OFF ? 0 : t + 1);
  };
  const sz = topAt(a, sx, sy) + 0.2, ez = topAt(b, ex, ey) + 0.2;
  const span = Math.hypot(ex - sx, ey - sy), n = Math.max(2, Math.round(span / 1.2)), sag = span * 0.06;
  const planks = new THREE.InstancedMesh(new THREE.BoxGeometry(1.0, 0.25, 3.2),
    new THREE.MeshStandardMaterial({ color: 0x8a5a32, roughness: 0.9 }), n);
  const yaw = Math.atan2(ey - sy, ex - sx);
  const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -yaw);
  const rope = [[], []];
  const m4 = new THREE.Matrix4();
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const x = sx + (ex - sx) * t, y = sy + (ey - sy) * t, z = sz + (ez - sz) * t - sag * 4 * t * (1 - t);
    m4.compose(toScene(x, y, z), q, new THREE.Vector3(1, 1, 1));
    planks.setMatrixAt(i, m4);
    for (const side of [0, 1]) {
      const off = side ? 1.6 : -1.6;
      rope[side].push(toScene(x - uy * off, y + ux * off, z + 1.1));
    }
  }
  const g = new THREE.Group();
  g.add(planks);
  for (const pts of rope) {
    g.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0xd8c39a })));
  }
  return g;
}

// The sky: a day colour, dusk, night; the sun goes round once a day.
const SKY = [[0, 0x0b1030], [5, 0x1c2350], [6.5, 0xf2a46b], [8, 0x8fb4e8], [17, 0x8fb4e8], [18.5, 0xe0846a],
  [20, 0x1c2350], [24, 0x0b1030]];
function applySky(hour) {
  let i = 0;
  while (i < SKY.length - 2 && hour > SKY[i + 1][0]) i++;
  const [h0, c0] = SKY[i], [h1, c1] = SKY[i + 1];
  const col = new THREE.Color(c0).lerp(new THREE.Color(c1), (hour - h0) / Math.max(h1 - h0, 1e-6));
  scene.background = col;
  scene.fog.color.copy(col);
  const a = ((hour - 6) / 24) * Math.PI * 2;
  const up = Math.sin(a);
  sun.position.set(Math.cos(a) * 600, up * 600, 250);
  sun.intensity = Math.max(0, up) * 2.4;
  hemi.intensity = 0.5 + Math.max(0, up) * 0.8;   // never pitch black: dusk and night stay readable
  stars.material.opacity = Math.max(0, Math.min(1, -up * 3));
  bloom.strength = 0.5 + Math.max(0, -up) * 0.8;
  const hh = Math.floor(hour) % 24, mm = Math.floor((hour % 1) * 60);
  document.getElementById("clock").textContent = `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
  // The starbloom of this hour (one per hour), its constellation partner, and the brew they make together.
  const h = orrery.inBloom(hour);
  const partner = orrery.HERBS.find((x) => x.constellation === h.constellation && x.name !== h.name);
  document.getElementById("bloom").textContent =
    `In bloom: ${h.name} (${h.constellation}, ${orrery.isDay(h.hour) ? "day" : "night"}). ` +
    `With ${partner.name} at ${String(partner.hour).padStart(2, "0")}:00 it steeps a ${orrery.brewOf(h.name, partner.name)}.`;
}

function flyTo(name) {
  const c = centres[name];
  if (!c) return;
  const from = controls.target.clone(), to = c.at.clone();
  const camFrom = camera.position.clone();
  const camTo = to.clone().add(new THREE.Vector3(c.r * 1.3, c.r * 0.9, c.r * 1.5));
  const t0 = performance.now();
  (function step(now) {
    const t = Math.max(0, Math.min(1, (now - t0) / 1200)), e = t * t * (3 - 2 * t);
    controls.target.lerpVectors(from, to, e);
    camera.position.lerpVectors(camFrom, camTo, e);
    if (t < 1) requestAnimationFrame(step);
  })(t0);
}

// Spot-check: the browser's columns against the server's (decoded int16, -32768 = none).
function checkAgainstServer(isle) {
  const decode = (b64) => new Int16Array(Uint8Array.from(atob(b64), (ch) => ch.charCodeAt(0)).buffer);
  const tops = decode(isle.tops);
  const p = centres[isle.name].p, n = p.radius + 2, w = isle.grid;
  let bad = 0, n0 = 0;
  for (let i = 0; i < tops.length; i += 97) {
    const x = (i % w) - n, y = Math.floor(i / w) - n;
    const want = tops[i] === -32768 ? core.OFF : tops[i];
    if (core.columnTop(p, x, y) !== want) bad++;
    n0++;
  }
  return { bad, n: n0 };
}

async function main() {
  let reach;
  try {
    const res = await fetch("/api/v1/reach/orrery", { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(res.status + " " + res.statusText);
    reach = await res.json();
  } catch (e) {
    statusEl.textContent = "Couldn't reach the server for the isles: " + e.message;
    return;
  }
  let total = 0, checked = 0, bad = 0;
  const buttons = document.getElementById("isles");
  for (const isle of reach.isles) {
    const { group, cubes } = isleMeshes(isle);
    scene.add(group);
    total += cubes;
    const c = checkAgainstServer(isle);
    checked += c.n; bad += c.bad;
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = isle.name;
    b.addEventListener("click", () => flyTo(isle.name));
    buttons.appendChild(b);
  }
  for (const to of reach.bridges) {
    const g = bridge(reach.isles[0].name, to);
    if (g) scene.add(g);
  }
  const verdict = bad === 0
    ? `<b class="ok">matches the server's ${checked} sampled columns</b>`
    : `<b class="warn">${bad} of ${checked} sampled columns differ from the server</b>`;
  statusEl.innerHTML = `${reach.isles.length} isles, ${total.toLocaleString()} merged faces, ${reach.bridges.length} sky bridges. ${verdict}.`;
  flyTo(reach.isles[0].name);
}

const hourInput = document.getElementById("hour");
const playBtn = document.getElementById("play");
let playing = false;
hourInput.addEventListener("input", () => applySky(Number(hourInput.value)));
playBtn.addEventListener("click", () => {
  playing = !playing;
  playBtn.textContent = playing ? "Pause" : "Play";
  playBtn.setAttribute("aria-pressed", String(playing));
});
applySky(Number(hourInput.value));

let last = performance.now();
window.__reachInfo = () => renderer.info;   // for the headless check: triangles and geometries drawn
// Headless checks: put the camera somewhere, and switch the far LODs off to measure what they save.
window.__reachView = (x, y, z) => { camera.position.set(x, y, z); controls.target.set(0, 0, 0); controls.update(); };
window.__reachLods = (on) => scene.traverse((o) => { if (o.isLOD) o.autoUpdate = on; if (o.isLOD && !on) o.levels.forEach((l, i) => { l.object.visible = i === 0; }); });
renderer.setAnimationLoop((now) => {
  const dt = (now - last) / 1000;
  last = now;
  if (playing) {
    const h = (Number(hourInput.value) + dt * 0.5) % 24;   // one sky hour every two seconds
    hourInput.value = String(h);
    applySky(h);
  }
  controls.update();
  composer.render();
});

main();
