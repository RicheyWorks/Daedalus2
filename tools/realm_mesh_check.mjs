// SPDX-License-Identifier: MIT
// node tools/realm_mesh_check.mjs: realm-mesh.js against the mesher it replaced (copied below as it was in realm.js),
// on random worlds. Every buffer must match exactly; prints the speed-up. Exit 1 on any difference.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const { meshChunk } = await import(join(root, "daedalus-server/src/main/resources/static/realm-mesh.js"));

const SIZE = 16;
const FACES = [
  { n: [1, 0, 0], shade: 0.86, c: [[1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 1]] },
  { n: [-1, 0, 0], shade: 0.86, c: [[0, 0, 1], [0, 1, 1], [0, 1, 0], [0, 0, 0]] },
  { n: [0, 1, 0], shade: 1.0, c: [[0, 1, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0]] },
  { n: [0, -1, 0], shade: 0.62, c: [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]] },
  { n: [0, 0, 1], shade: 0.94, c: [[1, 0, 1], [1, 1, 1], [0, 1, 1], [0, 0, 1]] },
  { n: [0, 0, -1], shade: 0.78, c: [[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]] },
];
const RAINBOW = ["RAINBOW_RED", "RAINBOW_BLUE"];
const SEE_THROUGH = new Set(["AIR", "GLASS", "WATER", "CLOUD", "PORTAL", ...RAINBOW]);
const TRANSLUCENT = new Set(["GLASS", "WATER", "PORTAL", ...RAINBOW]);
const GLOW = new Set(["LAMP", "CRYSTAL", "LAVA"]);
const GLOW_GAIN = { LAMP: 3.2, CRYSTAL: 1.6, LAVA: 2.2 };
const STUDDED = new Set(["BASEPLATE", "BRICK_RED"]);
const AO_SHADE = [0.5, 0.66, 0.83, 1.0];
const PALETTE = ["AIR", "STONE", "GRASS", "DIRT", "GLASS", "WATER", "LAMP", "CRYSTAL", "BASEPLATE", "BRICK_RED",
  "CLOUD", "RAINBOW_RED", "LAVA", "LEAVES"];   // ordinal 14+ is unknown to this palette -> drawn as STONE
const TILES = { STONE: 0, GRASS: 4, DIRT: 6, WATER: 8, LEAVES: 5 };
const tileUV = (name) => { const i = TILES[name] ?? 11, s = 1 / 4, inset = 0.5 / 256;
  return [(i % 4) * s + inset, 1 - (Math.floor(i / 4) + 1) * s + inset, s - 2 * inset]; };
const linear = (name) => { let h = 7; for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return [(h & 255) / 255, ((h >> 8) & 255) / 255, ((h >> 16) & 255) / 255]; };
function jitter(x, y, z) {
  let h = (x * 374761393 + y * 668265263 + z * 2147483647) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return 0.94 + (((h ^ (h >>> 16)) >>> 0) % 1000) / 1000 * 0.12;
}

// ---- the old mesher, as realm.js had it (THREE.Color swapped for linear(), the scene parts left out)
function oldMesh(chunks, cx, cy, cz) {
  const key = (a, b, c) => a + "," + b + "," + c;
  const idx = (lx, ly, lz) => lx + SIZE * (ly + SIZE * lz);
  const div = (a) => Math.floor(a / SIZE);
  const mod = (a) => ((a % SIZE) + SIZE) % SIZE;
  const nameAt = (x, y, z) => { const d = chunks.get(key(div(x), div(y), div(z))); if (!d) return "AIR";
    return PALETTE[d[idx(mod(x), mod(y), mod(z))]] || "STONE"; };
  const solidAt = (x, y, z) => !SEE_THROUGH.has(nameAt(x, y, z));
  function cornerAO(x, y, z, n, v) {
    const axes = n[0] !== 0 ? [1, 2] : n[1] !== 0 ? [0, 2] : [0, 1];
    const o = [x + n[0], y + n[1], z + n[2]];
    const d1 = [0, 0, 0], d2 = [0, 0, 0];
    d1[axes[0]] = v[axes[0]] ? 1 : -1;
    d2[axes[1]] = v[axes[1]] ? 1 : -1;
    const s1 = solidAt(o[0] + d1[0], o[1] + d1[1], o[2] + d1[2]);
    const s2 = solidAt(o[0] + d2[0], o[1] + d2[1], o[2] + d2[2]);
    if (s1 && s2) return 0;
    const c = solidAt(o[0] + d1[0] + d2[0], o[1] + d1[1] + d2[1], o[2] + d1[2] + d2[2]);
    return 3 - (s1 + s2 + c);
  }
  const data = chunks.get(key(cx, cy, cz));
  if (!data) return null;
  const part = () => ({ p: [], n: [], c: [], i: [], uv: [] });
  const buf = { solid: part(), glass: part(), studs: part(), glow: part(), lamps: [] };
  const ox = cx * SIZE, oy = cy * SIZE, oz = cz * SIZE;
  for (let lz = 0; lz < SIZE; lz++) for (let ly = 0; ly < SIZE; ly++) for (let lx = 0; lx < SIZE; lx++) {
    const name = PALETTE[data[idx(lx, ly, lz)]] || "STONE";
    if (name === "AIR") continue;
    const x = ox + lx, y = oy + ly, z = oz + lz;
    const glowing = GLOW.has(name);
    if (name === "LAMP") buf.lamps.push([x, y, z]);
    const own = glowing ? buf.glow : TRANSLUCENT.has(name) ? buf.glass : buf.solid;
    const studded = STUDDED.has(name);
    for (const f of FACES) {
      const target = studded && f.n[1] === 1 ? buf.studs : own;
      const nb = nameAt(x + f.n[0], y + f.n[1], z + f.n[2]);
      if (!SEE_THROUGH.has(nb) || nb === name) continue;
      const rgb = linear(name);
      const s = glowing ? GLOW_GAIN[name] : f.shade * jitter(x, y, z);
      const base = target.p.length / 3;
      const [u0, v0, us] = tileUV(name);
      const ao = [];
      for (const v of f.c) {
        const a = glowing ? 3 : cornerAO(x, y, z, f.n, v);
        ao.push(a);
        const k = s * AO_SHADE[a];
        target.p.push(x + v[0], y + v[1], z + v[2]);
        target.n.push(f.n[0], f.n[1], f.n[2]);
        target.c.push(rgb[0] * k, rgb[1] * k, rgb[2] * k);
        if (target === buf.studs) target.uv.push(v[0], v[2]);
        else { const [p, q] = f.n[0] !== 0 ? [v[2], v[1]] : f.n[1] !== 0 ? [v[0], v[2]] : [v[0], v[1]];
          target.uv.push(u0 + p * us, v0 + q * us); }
      }
      if (ao[0] + ao[2] > ao[1] + ao[3]) target.i.push(base, base + 1, base + 2, base, base + 2, base + 3);
      else target.i.push(base + 1, base + 2, base + 3, base + 1, base + 3, base);
    }
  }
  return buf;
}

// ---- random worlds: terrain with caves, glass, water, lamps, bricks, and an unknown ordinal
let seed = 64;
const rnd = () => ((seed = (Math.imul(seed, 1103515245) + 12345) >>> 0) / 4294967296);
function world(variant) {
  const chunks = new Map();
  for (let cz = -1; cz <= 1; cz++) for (let cy = -1; cy <= 1; cy++) for (let cx = -1; cx <= 1; cx++) {
    if (variant % 3 === 1 && rnd() < 0.3 && !(cx === 0 && cy === 0 && cz === 0)) continue;   // holes: missing chunks
    const d = new Uint8Array(4096);
    for (let i = 0; i < 4096; i++) {
      const y = cy * 16 + ((i >> 4) & 15), x = cx * 16 + (i & 15), z = cz * 16 + (i >> 8);
      const h = 4 + Math.floor(6 * Math.sin(x / 5 + variant) * Math.cos(z / 7));
      let o = y < h - 3 ? 1 : y < h - 1 ? 3 : y < h ? 2 : 0;
      if (o && rnd() < 0.08) o = 0;
      if (!o && rnd() < 0.03) o = 1 + Math.floor(rnd() * 14);
      d[i] = o;
    }
    chunks.set(cx + "," + cy + "," + cz, d);
  }
  return chunks;
}

const cfg = { faces: FACES, seeThrough: SEE_THROUGH, translucent: TRANSLUCENT, glow: GLOW, studded: STUDDED,
  glowGain: GLOW_GAIN, tileUV, linear, jitter, aoShade: AO_SHADE };
let ok = 0, total = 0, tOld = 0, tNew = 0, quads = 0;
for (let v = 0; v < 12; v++) {
  const chunks = world(v);
  const at = (a, b, c) => chunks.get(a + "," + b + "," + c);
  for (const [cx, cy, cz] of [[0, 0, 0], [1, 0, 0], [-1, 1, -1], [0, -1, 1], [5, 5, 5]]) {
    total++;
    let t0 = performance.now();
    const a = oldMesh(chunks, cx, cy, cz);
    tOld += performance.now() - t0;
    t0 = performance.now();
    const b = meshChunk(cx, cy, cz, at, PALETTE, cfg);
    tNew += performance.now() - t0;
    const same = JSON.stringify(a) === JSON.stringify(b);
    if (a) quads += (a.solid.i.length + a.glass.i.length + a.studs.i.length + a.glow.i.length) / 6;
    if (same) ok++;
    else console.log(`FAIL world ${v} chunk ${cx},${cy},${cz}`);
  }
}
console.log(`  ${quads} quads; old ${tOld.toFixed(1)} ms, new ${tNew.toFixed(1)} ms (${(tOld / tNew).toFixed(1)}x)`);
console.log(`${ok}/${total}`);
process.exit(ok === total ? 0 : 1);
