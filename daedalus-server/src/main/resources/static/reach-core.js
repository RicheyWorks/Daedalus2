// SPDX-License-Identifier: MIT
// The voxel isle's shape for the browser (ADR-058): a line-for-line port of the Unreal plugin's
// DaedalusVoxelIsleCore.h and the Java VoxelIsle. tools/reach_parity.mjs checks this file against
// engines/unreal/core-test/voxel_isle_parity.txt (the same counts and cube hash as C++ and Java).
export const OFF = -2147483648;
export const LAYERS = ["GRASS", "SAND", "DIRT", "STONE", "HEART", "MEADOW"];
export const [GRASS, SAND, DIRT, STONE, HEART, MEADOW] = [0, 1, 2, 3, 4, 5];

// Unsigned 32-bit constants as int32 for Math.imul (2246822519 and 3266489917 wrap).
const K1 = 374761393, K2 = 668265263, K3 = 2246822519 | 0, K4 = 3266489917 | 0, K5 = 1274126177;

function hash(p, ix, iy, salt) {
  let h = (Math.imul(ix, K1) + Math.imul(iy, K2) + Math.imul(p.seed, K3) + Math.imul(salt, K4)) | 0;
  h = Math.imul(h ^ (h >>> 13), K5);
  return ((h ^ (h >>> 16)) & 0xffff) / 65535.0;
}

export function noise(p, x, y, salt) {
  const fx0 = Math.floor(x), fy0 = Math.floor(y);
  const x0 = fx0 | 0, y0 = fy0 | 0;
  const fx = x - fx0, fy = y - fy0;
  const sx = fx * fx * (3.0 - 2.0 * fx), sy = fy * fy * (3.0 - 2.0 * fy);
  const a = hash(p, x0, y0, salt) + (hash(p, x0 + 1, y0, salt) - hash(p, x0, y0, salt)) * sx;
  const b = hash(p, x0, y0 + 1, salt) + (hash(p, x0 + 1, y0 + 1, salt) - hash(p, x0, y0 + 1, salt)) * sx;
  return a + (b - a) * sy;
}

const dist = (x, y) => Math.sqrt(x * x + y * y);

export function inPond(p, x, y) {
  if (p.pondRadius <= 0) return false;
  const r = p.pondRadius * (0.85 + 0.3 * noise(p, x * 0.15, y * 0.15, 9));
  return dist(x - p.pondX, y - p.pondY) < r;
}

export function columnTop(p, x, y) {
  const r = dist(x, y);
  const cx = r > 0 ? x / r : 1.0, cy = r > 0 ? y / r : 0.0;
  const edge = p.radius * (0.84 + 0.16 * noise(p, cx * 3.0 + 10.0, cy * 3.0 + 10.0, 1));
  if (r >= edge) return OFF;
  const t = 1.0 - r / edge;
  let h = p.summitHeight * Math.pow(t, 1.6) + 2.5 * noise(p, x * 0.07, y * 0.07, 2) + 1.2 * noise(p, x * 0.2, y * 0.2, 3);
  h = Math.floor(h / 2.0) * 2.0;
  if (inPond(p, x, y)) return -2;
  return h > 0 ? Math.trunc(h) : 0;
}

export function columnBottom(p, x, y) {
  let t = 1.0 - dist(x, y) / p.radius;
  t = t < 0 ? 0 : (t > 1 ? 1 : t);
  return -3 - Math.trunc(p.depth * Math.pow(t, 1.1) * (0.8 + 0.4 * noise(p, x * 0.1, y * 0.1, 4)));
}

/** Every visible cube in Y-major, X, then Z order: emit(x, y, z, layer). Returns the column count. */
export function build(p, emit) {
  const n = p.radius + 2, w = 2 * n + 1;
  const tops = new Int32Array(w * w), bots = new Int32Array(w * w);
  for (let y = -n; y <= n; ++y) {
    for (let x = -n; x <= n; ++x) {
      const i = (y + n) * w + (x + n);
      tops[i] = columnTop(p, x, y);
      bots[i] = tops[i] === OFF ? 0 : columnBottom(p, x, y);
    }
  }
  const top = (x, y) => (x < -n || x > n || y < -n || y > n) ? OFF : tops[(y + n) * w + (x + n)];
  const bot = (x, y) => (x < -n || x > n || y < -n || y > n) ? 0 : bots[(y + n) * w + (x + n)];
  const NX = [1, -1, 0, 0], NY = [0, 0, 1, -1];
  let columns = 0;
  for (let y = -n; y <= n; ++y) {
    for (let x = -n; x <= n; ++x) {
      const t = top(x, y);
      if (t === OFF) continue;
      ++columns;
      const b = bot(x, y);
      const shore = inPond(p, x, y) || (p.pondRadius > 0 && dist(x - p.pondX, y - p.pondY) < p.pondRadius + 2.5)
        || top(x + 2, y) === OFF || top(x - 2, y) === OFF || top(x, y + 2) === OFF || top(x, y - 2) === OFF;
      for (let z = b; z <= t; ++z) {
        let open = z === t || z === b;
        for (let k = 0; k < 4 && !open; ++k) {
          const nt = top(x + NX[k], y + NY[k]);
          open = nt === OFF || nt < z || bot(x + NX[k], y + NY[k]) > z;
        }
        if (!open) continue;
        let l = STONE;
        if (z === t) l = shore ? SAND : (noise(p, x * 0.09, y * 0.09, 7) > 0.55 ? MEADOW : GRASS);
        else if (z >= t - 2) l = DIRT;
        if (z <= b + 1 && dist(x, y) < 4.0) l = HEART;
        emit(x, y, z, l);
      }
    }
  }
  return columns;
}

/**
 * The isle's visible surface as merged quads, a port of DaedalusVoxelIsleCore.h's Mesh() (ADR-064: one mesh, not a
 * cube per block). Each quad is [layer, normal, plane, u0, u1, v0, v1]. Normal is 0 +X, 1 -X, 2 +Y, 3 -Y, 4 +Z,
 * 5 -Z. The quad lies in its normal axis's plane, at `plane`. The u/v axes are (Y, Z) for X normals, (X, Z) for Y
 * normals and (X, Y) for Z normals.
 * tools/reach_parity.mjs checks it against engines/unreal/core-test/voxel_mesh_parity.txt.
 */
export function mesh(p) {
  const n = p.radius + 2, w = 2 * n + 1;
  const tops = new Int32Array(w * w), bots = new Int32Array(w * w), sh = new Uint8Array(w * w);
  for (let y = -n; y <= n; ++y) {
    for (let x = -n; x <= n; ++x) {
      const i = (y + n) * w + (x + n);
      tops[i] = columnTop(p, x, y);
      bots[i] = tops[i] === OFF ? 0 : columnBottom(p, x, y);
      if (tops[i] !== OFF) sh[i] = shore(p, x, y) ? 1 : 0;
    }
  }
  const layerAt = (x, y, z) => { const i = (y + n) * w + (x + n); return layerOf(p, x, y, z, tops[i], bots[i], sh[i] !== 0); };
  return meshGrid(n, tops, bots, layerAt, 1);
}

function shore(p, x, y) {
  return inPond(p, x, y) || (p.pondRadius > 0 && dist(x - p.pondX, y - p.pondY) < p.pondRadius + 2.5)
    || columnTop(p, x + 2, y) === OFF || columnTop(p, x - 2, y) === OFF || columnTop(p, x, y + 2) === OFF
    || columnTop(p, x, y - 2) === OFF;
}

function layerOf(p, x, y, z, t, b, isShore) {
  let l = STONE;
  if (z === t) l = isShore ? SAND : (noise(p, x * 0.09, y * 0.09, 7) > 0.55 ? MEADOW : GRASS);
  else if (z >= t - 2) l = DIRT;
  if (z <= b + 1 && dist(x, y) < 4.0) l = HEART;
  return l;
}

const floorDiv = (a, b) => Math.floor(a / b);

/** A far-away version (rule 5): step x step columns per coarse cell; a port of MeshLod() (parity-tested). */
export function meshLod(p, step) {
  if (step <= 1) return mesh(p);
  const fine = p.radius + 2;
  const n = floorDiv(fine, step) + 1, w = 2 * n + 1;
  const tops = new Int32Array(w * w).fill(OFF), bots = new Int32Array(w * w);
  const repX = new Int32Array(w * w), repY = new Int32Array(w * w), repShore = new Uint8Array(w * w);
  for (let cy = -n; cy <= n; ++cy) {
    for (let cx = -n; cx <= n; ++cx) {
      let land = 0, hi = OFF, lo = 0, bx = 0, by = 0;
      for (let y = cy * step; y < (cy + 1) * step; ++y) {
        for (let x = cx * step; x < (cx + 1) * step; ++x) {
          if (x < -fine || x > fine || y < -fine || y > fine) continue;
          const t = columnTop(p, x, y);
          if (t === OFF) continue;
          const b = columnBottom(p, x, y);
          if (land === 0 || t > hi) { hi = t; bx = x; by = y; }
          lo = land === 0 ? b : Math.min(b, lo);
          ++land;
        }
      }
      if (land * 4 < step * step) continue;
      const i = (cy + n) * w + (cx + n);
      tops[i] = hi; bots[i] = lo; repX[i] = bx; repY[i] = by; repShore[i] = shore(p, bx, by) ? 1 : 0;
    }
  }
  const layerAt = (cx, cy, z) => { const i = (cy + n) * w + (cx + n); return layerOf(p, repX[i], repY[i], z, tops[i], bots[i], repShore[i] !== 0); };
  return meshGrid(n, tops, bots, layerAt, step);
}

/** The greedy mesher over a column grid [-n, n]^2; across-coordinates are multiplied by scale. */
function meshGrid(n, tops, bots, layerAt, scale) {
  const w = 2 * n + 1;
  const idx = (x, y) => (y + n) * w + (x + n);
  const top = (x, y) => (x < -n || x > n || y < -n || y > n) ? OFF : tops[idx(x, y)];
  const bot = (x, y) => (x < -n || x > n || y < -n || y > n) ? 0 : bots[idx(x, y)];
  const out = [];
  // tops (4) and bottoms (5): greedy rectangles over (height, layer)
  for (let face = 4; face <= 5; ++face) {
    const done = new Uint8Array(w * w);
    const key = (x, y) => {
      const t = top(x, y);
      if (t === OFF) return null;
      const h = face === 4 ? t : bot(x, y);
      return [h, layerAt(x, y, h)];
    };
    for (let y = -n; y <= n; ++y) {
      for (let x = -n; x <= n; ++x) {
        if (done[idx(x, y)]) continue;
        const k = key(x, y);
        if (!k) continue;
        const [h, l] = k;
        const same = (ax, ay) => {
          if (ax > n || ay > n || done[idx(ax, ay)]) return false;
          const k2 = key(ax, ay);
          return k2 !== null && k2[0] === h && k2[1] === l;
        };
        let x1 = x;
        while (same(x1 + 1, y)) ++x1;
        let y1 = y;
        for (let grow = true; grow;) {
          for (let ax = x; ax <= x1 && grow; ++ax) grow = same(ax, y1 + 1);
          if (grow) ++y1;
        }
        for (let ay = y; ay <= y1; ++ay) for (let ax = x; ax <= x1; ++ax) done[idx(ax, ay)] = 1;
        out.push([l, face, face === 4 ? h + 1 : h, x * scale, (x1 + 1) * scale, y * scale, (y1 + 1) * scale]);
      }
    }
  }
  // sides: per wall line, greedy rectangles on (along, z)
  const DX = [1, -1, 0, 0], DY = [0, 0, 1, -1];
  for (let d = 0; d < 4; ++d) {
    const alongY = d < 2;
    for (let line = -n; line <= n; ++line) {
      const spanB = new Int32Array(w), spanT = new Int32Array(w);
      let zMin = 0, zMax = -1;
      for (let k = -n; k <= n; ++k) {
        const x = alongY ? line : k, y = alongY ? k : line;
        spanB[k + n] = 1; spanT[k + n] = 0;
        if (top(x, y) === OFF) continue;
        spanB[k + n] = bot(x, y); spanT[k + n] = top(x, y);
        if (zMax < zMin) { zMin = bot(x, y); zMax = top(x, y); }
        zMin = Math.min(zMin, bot(x, y));
        zMax = Math.max(zMax, top(x, y));
      }
      if (zMax < zMin) continue;
      const h = zMax - zMin + 1;
      const f = new Int8Array(w * h).fill(-1);
      for (let k = -n; k <= n; ++k) {
        const x = alongY ? line : k, y = alongY ? k : line;
        const b = spanB[k + n], t = spanT[k + n];
        if (b > t) continue;
        const nt = top(x + DX[d], y + DY[d]), nb = bot(x + DX[d], y + DY[d]);
        for (let z = b; z <= t; ++z) if (nt === OFF || z > nt || z < nb) f[(z - zMin) * w + (k + n)] = layerAt(x, y, z);
      }
      for (let z = 0; z < h; ++z) {
        for (let k = 0; k < w; ++k) {
          const l = f[z * w + k];
          if (l < 0) continue;
          let k1 = k;
          while (k1 + 1 < w && f[z * w + k1 + 1] === l) ++k1;
          let z1 = z;
          for (let grow = true; grow;) {
            for (let a = k; a <= k1 && grow; ++a) grow = z1 + 1 < h && f[(z1 + 1) * w + a] === l;
            if (grow) ++z1;
          }
          for (let az = z; az <= z1; ++az) for (let a = k; a <= k1; ++a) f[az * w + a] = -1;
          const plane = (d === 0 || d === 2) ? line + 1 : line;
          out.push([l, d, plane * scale, (k - n) * scale, (k1 + 1 - n) * scale, z + zMin, z1 + 1 + zMin]);
        }
      }
    }
  }
  return out;
}
