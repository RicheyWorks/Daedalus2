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
