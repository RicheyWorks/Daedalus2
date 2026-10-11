// Two real Chromium pages on /realm.html against a live Daedalus server.
// A raises an island and taps cubes in and out; B must see every change arrive over STOMP.
// Console errors on either page fail the run.
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const BASE = process.argv[2] || "http://localhost:8088";
const OUT = process.argv[3] || ".";
const NM = path.resolve("node_modules");
const failures = [];
const check = (label, ok, extra = "") => {
  console.log((ok ? "PASS " : "FAIL ") + label + (extra ? "  " + extra : ""));
  if (!ok) failures.push(label);
};

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
await context.route("https://cdnjs.cloudflare.com/**", r => {
  const u = r.request().url();
  const file = u.includes("sockjs") ? `${NM}/sockjs-client/dist/sockjs.min.js` : `${NM}/stompjs/lib/stomp.min.js`;
  r.fulfill({ body: fs.readFileSync(file), contentType: "application/javascript", headers: { "access-control-allow-origin": "*" } });
});
await context.route("https://cdn.jsdelivr.net/npm/three@0.160.0/**", r => {
  const rel = new URL(r.request().url()).pathname.replace("/npm/three@0.160.0/", "");
  r.fulfill({ body: fs.readFileSync(`${NM}/three/${rel}`), contentType: "application/javascript", headers: { "access-control-allow-origin": "*" } });
});

async function open(name) {
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  await page.goto(BASE + "/realm.html");
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live, null, { timeout: 30000 });
  return { name, page, errors };
}
const A = await open("A");
const B = await open("B");
check("both pages load and go live over STOMP", true);
const gl = await A.page.evaluate(() => !!document.getElementById("view").getContext("webgl2") || !!document.getElementById("view").getContext("webgl"));
check("WebGL context available", gl);

// --- A raises an island from the UI; B learns about it from the STOMP frame alone.
await A.page.fill("#seed", "11");
await A.page.click("#raise");
await A.page.waitForFunction(() => window.daedalusRealm.islands.length === 1, null, { timeout: 30000 });
await B.page.waitForFunction(() => window.daedalusRealm.islands.length === 1, null, { timeout: 30000 });
const cubes = p => p.evaluate(() => [...window.daedalusRealm.chunks.values()]
  .reduce((a, d) => a + d.reduce((s, v) => s + (v ? 1 : 0), 0), 0));
const serverCubes = async () => {
  const r = await (await fetch(BASE + "/api/v1/world/world-zero/chunks")).json();
  return r.chunks.reduce((a, c) => a + c.occupied, 0);
};
await B.page.waitForFunction(n => [...window.daedalusRealm.chunks.values()]
  .reduce((a, d) => a + d.reduce((s, v) => s + (v ? 1 : 0), 0), 0) === n, await serverCubes(), { timeout: 30000 });
const [ca, cb, cs] = [await cubes(A.page), await cubes(B.page), await serverCubes()];
check("island raised; A, B and server agree on every cube", ca === cs && cb === cs, `A=${ca} B=${cb} server=${cs}`);
// --- Arks (ADR-019): the island launched one, both pages moor its model at the pier.
await B.page.waitForFunction(() => window.daedalusRealm.arkModels.size === 1, null, { timeout: 30000 });
const arkA = await A.page.evaluate(() => {
  const s = window.daedalusRealm, ark = s.arks[0], m = s.arkModels.get(ark.id);
  let meshes = 0; m.traverse(o => { if (o.isMesh) meshes++; });
  return { n: s.arks.length, id: ark.id, name: ark.name, meshes };
});
check("one ark per island, model loaded on A", arkA.n === 1 && arkA.id === "ark-0" && arkA.meshes >= 3, JSON.stringify(arkA));
check("B moored the same ark", await B.page.evaluate(n => window.daedalusRealm.arks[0].name === n, arkA.name));
const berthPlank = await A.page.evaluate(() => {
  const s = window.daedalusRealm, a = s.arks[0], S = 16, d = v => Math.floor(v / S), m = v => ((v % S) + S) % S;
  const at = (x, y, z) => { const c = s.chunks.get(d(x) + "," + d(y) + "," + d(z)); return c ? s.palette[c[m(x) + S * (m(y) + S * m(z))]] : "AIR"; };
  return [at(a.x, a.y, a.z), at(a.x, a.y - 1, a.z)];
});
check("the ark's berth is open air over a pier plank", berthPlank[0] === "AIR" && berthPlank[1] === "WOOD", berthPlank.join(" over "));
await A.page.evaluate(() => { const a = window.daedalusRealm.arks[0]; document.querySelector("#arks button").click(); });
await A.page.waitForTimeout(1300);
await A.page.screenshot({ path: path.join(OUT, "realm_ark.png") });
await A.page.evaluate(() => document.querySelector("#islands button").click());
await A.page.waitForTimeout(1300);
const meshes = await A.page.evaluate(() => window.daedalusRealm.meshes.size);
check("island meshed into chunk groups", meshes > 10, `${meshes} chunk meshes`);
await A.page.waitForTimeout(1300); // fly-to animation
await A.page.screenshot({ path: path.join(OUT, "realm_island.png") });

// --- A taps a cube in through the real pointer path; B sees it land.
await A.page.click("#modeBuild");
await A.page.click('.swatch[title^="CRYSTAL"]');
const center = { x: 640, y: 400 };
const placed = A.page.waitForResponse(r => r.url().endsWith("/block") && r.request().method() === "PUT");
await A.page.mouse.click(center.x, center.y);
const put = await (await placed).json();
check("tap in Build mode PUTs a cube", put.result === "PLACED" && put.type === "CRYSTAL", JSON.stringify({ x: put.x, y: put.y, z: put.z, result: put.result }));
const seen = await B.page.waitForFunction(({ x, y, z }) => {
  const s = window.daedalusRealm, S = 16, d = a => Math.floor(a / S), m = a => ((a % S) + S) % S;
  const data = s.chunks.get(d(x) + "," + d(y) + "," + d(z));
  return data && s.palette[data[m(x) + S * (m(y) + S * m(z))]] === "CRYSTAL";
}, put, { timeout: 10000 }).then(() => true, () => false);
check("B sees A's cube arrive live (STOMP BLOCK_PLACED)", seen);
await A.page.screenshot({ path: path.join(OUT, "realm_built.png") });

// --- A breaks it again; B sees it go.
await A.page.click("#modeBreak");
const removed = A.page.waitForResponse(r => r.url().includes("/block?") && r.request().method() === "DELETE");
await A.page.mouse.click(center.x, center.y);
const del = await (await removed).json();
check("tap in Break mode DELETEs the cube it hit", del.result === "REMOVED" && del.previous === "CRYSTAL",
  JSON.stringify({ x: del.x, y: del.y, z: del.z, previous: del.previous }));
const gone = await B.page.waitForFunction(({ x, y, z }) => {
  const s = window.daedalusRealm, S = 16, d = a => Math.floor(a / S), m = a => ((a % S) + S) % S;
  const data = s.chunks.get(d(x) + "," + d(y) + "," + d(z));
  return !data || data[m(x) + S * (m(y) + S * m(z))] === 0;
}, del, { timeout: 10000 }).then(() => true, () => false);
check("B sees the cube removed live (STOMP BLOCK_REMOVED)", gone);

// --- A drag is a camera move, never an edit.
const revBefore = await A.page.evaluate(() => window.daedalusRealm.revision);
await A.page.mouse.move(500, 400); await A.page.mouse.down();
await A.page.mouse.move(700, 450, { steps: 8 }); await A.page.mouse.up();
await A.page.waitForTimeout(400);
check("dragging in Break mode orbits and edits nothing", (await A.page.evaluate(() => window.daedalusRealm.revision)) === revBefore);

// --- Reload: a fresh page rebuilds the same world from REST alone.
const C = await open("C");
await C.page.waitForFunction(() => window.daedalusRealm.islands.length === 1, null, { timeout: 30000 });
check("a fresh page rebuilds the same world", (await cubes(C.page)) === (await serverCubes()));

for (const p of [A, B, C]) check(`no console errors on page ${p.name}`, p.errors.length === 0, p.errors.slice(0, 3).join(" | "));
await browser.close();
console.log(failures.length ? `\n${failures.length} FAILED` : "\nALL PASS");
process.exit(failures.length ? 1 : 0);
