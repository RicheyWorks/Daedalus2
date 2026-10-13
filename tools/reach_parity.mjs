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
// The Orrery herbs and brews (orrery-core.js) against the C++ table and all 576 brews.
const orr = await import(join(root, "daedalus-server/src/main/resources/static/orrery-core.js"));
const rows = readFileSync(join(root, "engines/unreal/core-test/orrery_parity.txt"), "utf8").split("\n").filter((l) => l && !l.startsWith("#"));
let herbsOk = 0, brewsOk = 0, herbs = 0, brews = 0;
for (const r of rows) {
  const [kind, a, b, ...rest] = r.split(" ");
  if (kind === "herb") {
    herbs++;
    const h = orr.findHerb(a);
    herbsOk += !!h && h.hour === Number(b) && h.constellation === rest[0] && (orr.isDay(h.hour) ? 1 : 0) === Number(rest[1]);
  } else {
    brews++;
    const want = rest.join(" ") === "-" ? "" : rest.join(" ");
    brewsOk += orr.brewOf(a, b) === want;
  }
}
const orrGood = herbs === 24 && brews === 576 && herbsOk === herbs && brewsOk === brews && orr.HERBS.length === 24;
console.log(`${orrGood ? "ok  " : "FAIL"} orrery herbs ${herbsOk}/${herbs}, brews ${brewsOk}/${brews}`);
// The merged surface mesh (mesh()) against the C++ Mesh(): quad count and hash, per isle.
const meshRows = readFileSync(join(root, "engines/unreal/core-test/voxel_mesh_parity.txt"), "utf8").split("\n").filter((l) => l && !l.startsWith("#"));
let meshOk = 0;
for (const r of meshRows) {
  const [a, want] = r.split("|").map((x) => x.trim());
  const [seed, radius, summitHeight, depth, pondX, pondY, pondRadius] = a.split(" ").map(Number);
  const q = core.mesh({ seed, radius, summitHeight, depth, pondX, pondY, pondRadius });
  let h = 14695981039346656037n;
  for (const quad of q) for (const v of quad) { h ^= BigInt(v >>> 0); h = (h * 1099511628211n) & MASK; }
  const got = `${q.length} ${h}`;
  const good = got === want;
  console.log(`${good ? "ok  " : "FAIL"} mesh seed ${seed} radius ${radius}: ${q.length} quads${good ? "" : ` (want ${want})`}`);
  meshOk += good;
}
const total = lines.length + 1 + meshRows.length, passed = ok + (orrGood ? 1 : 0) + meshOk;
console.log(`${passed}/${total}`);
process.exit(passed === total ? 0 : 1);
