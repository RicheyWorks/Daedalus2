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
  const lod = a.startsWith("lod") ? Number(a.split(" ")[0].slice(3)) : 1;
  const [seed, radius, summitHeight, depth, pondX, pondY, pondRadius] = (lod > 1 ? a.split(" ").slice(1) : a.split(" ")).map(Number);
  const prm = { seed, radius, summitHeight, depth, pondX, pondY, pondRadius };
  const q = lod > 1 ? core.meshLod(prm, lod) : core.mesh(prm);
  let h = 14695981039346656037n;
  for (const quad of q) for (const v of quad) { h ^= BigInt(v >>> 0); h = (h * 1099511628211n) & MASK; }
  const got = `${q.length} ${h}`;
  const good = got === want;
  console.log(`${good ? "ok  " : "FAIL"} mesh${lod > 1 ? " lod" + lod : ""} seed ${seed} radius ${radius}: ${q.length} quads${good ? "" : ` (want ${want})`}`);
  meshOk += good;
}
// The squad director (tactics-core.js) against the C++ Decide()+Write(): 40 seeded squads, byte for byte.
const tac = await import(join(root, "daedalus-server/src/main/resources/static/tactics-core.js"));
const tl = readFileSync(join(root, "engines/unreal/core-test/tactics_parity.txt"), "utf8").split("\n");
let tacCases = 0, tacOk = 0;
for (let i = 0; i < tl.length; i++) {
  if (!tl[i].startsWith("case ")) continue;
  const c = tl[i].split(" ");
  const id = Number(c[1]);
  const player = { x: Number(c[3]), y: Number(c[4]), z: Number(c[5]) };
  const units = [];
  let j = i + 1;
  for (; tl[j].startsWith("unit "); j++) {
    const u = tl[j].split(" ");
    units.push({ name: u[1], at: { x: Number(u[2]), y: Number(u[3]), z: Number(u[4]) }, health: Number(u[5]), maxHealth: Number(u[6]), seesPlayer: u[7] === "1" });
  }
  let want = "";
  for (j = j + 1; tl[j] !== "end"; j++) want += tl[j] + "\n";
  const got = tac.write(tac.decide("sq-" + id, id, units, player));
  tacCases++;
  if (got === want) tacOk++; else console.log(`FAIL tactics case ${id}\n  want ${JSON.stringify(want)}\n  got  ${JSON.stringify(got)}`);
}
const numOk = tac.num(0.25) === "0.2" && tac.num(0.35) === "0.3" && tac.num(-0.04) === "-0.0" && tac.num(-0.0) === "-0.0" && tac.num(-0.25) === "-0.2" && tac.num(0.75) === "0.8";
const tacGood = tacCases === 40 && tacOk === 40 && numOk;
console.log(`${tacGood ? "ok  " : "FAIL"} tactics director ${tacOk}/${tacCases} squads byte for byte; printf rounding ${numOk ? "ok" : "WRONG"}`);
const total = lines.length + 1 + meshRows.length + 1, passed = ok + (orrGood ? 1 : 0) + meshOk + (tacGood ? 1 : 0);
console.log(`${passed}/${total}`);
process.exit(passed === total ? 0 : 1);
