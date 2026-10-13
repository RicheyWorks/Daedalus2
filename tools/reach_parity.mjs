// SPDX-License-Identifier: MIT
// node tools/reach_parity.mjs: the browser's voxel isle (reach-core.js) against the C++ core's parity file.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const core = await import(join(root, "daedalus-server/src/main/resources/static/reach-core.js"));
const lines = readFileSync(join(root, "engines/unreal/core-test/voxel_isle_parity.txt"), "utf8")
  .split("\n").filter((l) => l && !l.startsWith("#"));
let ok = 0;
const MASK = (1n << 64n) - 1n;
for (const line of lines) {
  const [a, want, cols] = line.split("|").map((s) => s.trim());
  const [seed, radius, summitHeight, depth, pondX, pondY, pondRadius] = a.split(" ").map(Number);
  const p = { seed, radius, summitHeight, depth, pondX, pondY, pondRadius };
  let good = true;
  for (const c of cols.split(" ")) {
    const [x, y, t, b] = c.split(",").map(Number);
    const top = core.columnTop(p, x, y);
    if (top !== t || (top !== core.OFF && core.columnBottom(p, x, y) !== b)) good = false;
  }
  const layers = [0, 0, 0, 0, 0, 0];
  let cubes = 0, h = 14695981039346656037n;
  const columns = core.build(p, (x, y, z, l) => {
    cubes++; layers[l]++;
    for (const v of [x, y, z, l]) { h ^= BigInt(v >>> 0); h = (h * 1099511628211n) & MASK; }
  });
  const got = [columns, cubes, ...layers, h.toString()].join(" ");
  good = good && got === want;
  console.log(`${good ? "ok  " : "FAIL"} seed ${seed} radius ${radius}${good ? "" : `\n  want ${want}\n  got  ${got}`}`);
  ok += good;
}
console.log(`${ok}/${lines.length}`);
process.exit(ok === lines.length ? 0 : 1);
