// SPDX-License-Identifier: MIT
// The realm's chunk mesher, without three.js or the DOM, so node can test it (tools/realm_mesh_check.mjs).
//
// ADR-064 (RAM and time like Minecraft): the old mesher asked "what is at x,y,z?" through a string-keyed Map for
// every face and every ambient-occlusion corner, about 70 Map lookups and string builds per visible cube. This one
// copies the chunk and a two-cube border into one flat 20x20x20 array first (the border covers AO's corner reach),
// so every question after that is an array read. The faces, colours, AO, UVs and triangle order are the same bytes
// as before: realm_mesh_check.mjs compares both on random worlds.

export const PAD = 2;
const SIZE = 16;
const W = SIZE + 2 * PAD;   // 20

/**
 * Mesh one chunk.
 * @param chunkAt (cx, cy, cz) -> Uint8Array(4096) | undefined
 * @param palette ordinal -> block name ("AIR" first)
 * @param cfg { faces, seeThrough, translucent, glow, studded, glowGain, tileUV(name) -> [u0, v0, us],
 *              linear(name) -> [r, g, b] (linear-space colour), jitter(x, y, z), aoShade }
 * @returns { solid, glass, studs, glow: { p, n, c, i, uv }, lamps: [[x, y, z], ...] } or null without data
 */
export function meshChunk(cx, cy, cz, chunkAt, palette, cfg) {
  const data = chunkAt(cx, cy, cz);
  if (!data) return null;
  // names of the chunk plus a 2-cube border; neighbour chunks fetched once each
  const names = new Array(W * W * W);
  const near = new Map();
  const chunkFor = (dx, dy, dz) => {
    const k = (dx + 1) + 3 * ((dy + 1) + 3 * (dz + 1));
    if (!near.has(k)) near.set(k, dx === 0 && dy === 0 && dz === 0 ? data : chunkAt(cx + dx, cy + dy, cz + dz));
    return near.get(k);
  };
  for (let pz = 0; pz < W; pz++) {
    const lz = pz - PAD, dz = lz < 0 ? -1 : lz >= SIZE ? 1 : 0, mz = lz - dz * SIZE;
    for (let py = 0; py < W; py++) {
      const ly = py - PAD, dy = ly < 0 ? -1 : ly >= SIZE ? 1 : 0, my = ly - dy * SIZE;
      for (let px = 0; px < W; px++) {
        const lx = px - PAD, dx = lx < 0 ? -1 : lx >= SIZE ? 1 : 0, mx = lx - dx * SIZE;
        const d = chunkFor(dx, dy, dz);
        names[px + W * (py + W * pz)] = d ? (palette[d[mx + SIZE * (my + SIZE * mz)]] || "STONE") : "AIR";
      }
    }
  }
  const see = cfg.seeThrough;
  const solid = new Uint8Array(W * W * W);
  for (let i = 0; i < names.length; i++) solid[i] = see.has(names[i]) ? 0 : 1;
  const at = (lx, ly, lz) => (lx + PAD) + W * ((ly + PAD) + W * (lz + PAD));

  const cornerAO = (lx, ly, lz, n, v) => {
    const axes = n[0] !== 0 ? [1, 2] : n[1] !== 0 ? [0, 2] : [0, 1];
    const o = [lx + n[0], ly + n[1], lz + n[2]];
    const d1 = [0, 0, 0], d2 = [0, 0, 0];
    d1[axes[0]] = v[axes[0]] ? 1 : -1;
    d2[axes[1]] = v[axes[1]] ? 1 : -1;
    const s1 = solid[at(o[0] + d1[0], o[1] + d1[1], o[2] + d1[2])];
    const s2 = solid[at(o[0] + d2[0], o[1] + d2[1], o[2] + d2[2])];
    if (s1 && s2) return 0;
    const c = solid[at(o[0] + d1[0] + d2[0], o[1] + d1[1] + d2[1], o[2] + d1[2] + d2[2])];
    return 3 - (s1 + s2 + c);
  };

  const part = () => ({ p: [], n: [], c: [], i: [], uv: [] });
  const buf = { solid: part(), glass: part(), studs: part(), glow: part(), lamps: [] };
  const ox = cx * SIZE, oy = cy * SIZE, oz = cz * SIZE;
  for (let lz = 0; lz < SIZE; lz++) for (let ly = 0; ly < SIZE; ly++) for (let lx = 0; lx < SIZE; lx++) {
    const name = names[at(lx, ly, lz)];
    if (name === "AIR") continue;
    const x = ox + lx, y = oy + ly, z = oz + lz;
    const glowing = cfg.glow.has(name);
    if (name === "LAMP") buf.lamps.push([x, y, z]);
    const own = glowing ? buf.glow : cfg.translucent.has(name) ? buf.glass : buf.solid;
    const studded = cfg.studded.has(name);
    let rgb = null, uv = null;
    for (const f of cfg.faces) {
      const target = studded && f.n[1] === 1 ? buf.studs : own;
      const nb = names[at(lx + f.n[0], ly + f.n[1], lz + f.n[2])];
      if (!see.has(nb) || nb === name) continue;
      if (!rgb) { rgb = cfg.linear(name); uv = cfg.tileUV(name); }
      const s = glowing ? cfg.glowGain[name] : f.shade * cfg.jitter(x, y, z);
      const base = target.p.length / 3;
      const [u0, v0, us] = uv;
      const ao = [];
      for (const v of f.c) {
        const a = glowing ? 3 : cornerAO(lx, ly, lz, f.n, v);
        ao.push(a);
        const k = s * cfg.aoShade[a];
        target.p.push(x + v[0], y + v[1], z + v[2]);
        target.n.push(f.n[0], f.n[1], f.n[2]);
        target.c.push(rgb[0] * k, rgb[1] * k, rgb[2] * k);
        if (target === buf.studs) {
          target.uv.push(v[0], v[2]);
        } else {
          const [p, q] = f.n[0] !== 0 ? [v[2], v[1]] : f.n[1] !== 0 ? [v[0], v[2]] : [v[0], v[1]];
          target.uv.push(u0 + p * us, v0 + q * us);
        }
      }
      if (ao[0] + ao[2] > ao[1] + ao[3]) target.i.push(base, base + 1, base + 2, base, base + 2, base + 3);
      else target.i.push(base + 1, base + 2, base + 3, base + 1, base + 3, base);
    }
  }
  return buf;
}
