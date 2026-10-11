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
B.canon = Object.fromEntries((await (await fetch(BASE + "/api/v1/species")).json()).species.map(s => [s.key, s]));
check("both pages load and go live over STOMP", true);
const gl = await A.page.evaluate(() => !!document.getElementById("view").getContext("webgl2") || !!document.getElementById("view").getContext("webgl"));
check("WebGL context available", gl);

// --- The bestiary (ADR-021): the whole canon arrives, and a guild chip lists its kinds.
await A.page.waitForFunction(() => window.daedalusRealm.species.length === 221, null, { timeout: 15000 });
await A.page.click('.chip[data-guild="STARBORN"]');
const starborn = await A.page.locator(".kinds .kind").count();
check("bestiary lists the starborn guild", starborn === 22, `${starborn} kinds`);
await A.page.click('.chip[data-guild="STARBORN"]');

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
await A.page.evaluate(() => document.querySelector("#islands button.go").click());
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
// Aim at the centre of the cube's camera-facing faces, as a player would — not the screen centre,
// where the crystal can sit edge-on to the ray.
const aim = await A.page.evaluate(({ x, y, z }) => window.daedalusRealm.project(x + 0.5, y + 0.5, z + 0.5), put);
await A.page.mouse.click(aim.x, aim.y);
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

// --- Voyages (ADR-020): a second island, then A sails ark-0 there; B watches it cross and tie up.
await A.page.click("#modeLook");
await A.page.fill("#seed", "42");
await A.page.click("#raise");
for (const p of [A, B]) {
  await p.page.waitForFunction(() => window.daedalusRealm.islands.length === 2 && window.daedalusRealm.arkModels.size === 2,
    null, { timeout: 30000 });
}
check("a second island launches a second ark on both pages", true);
await A.page.selectOption('.ark[data-ark="ark-0"] select.dest', "1");
const ordered = A.page.waitForResponse(r => r.url().endsWith("/arks/ark-0/voyage"));
await A.page.click('.ark[data-ark="ark-0"] button.sail');
const order = await (await ordered).json();
check("Sail orders a voyage", order.result === "SAILING" && order.ark.toSlot === 1, `${order.result} ${order.ark.arriveAt - order.ark.departAt} ms`);
const sailing = await B.page.waitForFunction(() => {
  const a = window.daedalusRealm.arks.find(x => x.id === "ark-0");
  return a && a.state === "SAILING";
}, null, { timeout: 10000 }).then(() => true, () => false);
check("B hears DEPARTED over STOMP", sailing);
const xAt = () => B.page.evaluate(() => window.daedalusRealm.arkModels.get("ark-0").position.toArray());
const p0 = await xAt();
await B.page.waitForTimeout(2500);
const p1 = await xAt();
check("B's ark model moves toward the destination", p1[0] > p0[0] + 3, `x ${p0[0].toFixed(1)} → ${p1[0].toFixed(1)}`);
// A background tab gets no animation frames; bring A forward so its camera can follow.
await A.page.bringToFront();
await A.page.waitForTimeout(800);
check("A rides along (Ride shows Stop)", await A.page.evaluate(() => document.querySelector('.ark[data-ark="ark-0"] button.ride').textContent === "Stop"));
const gap = await A.page.evaluate(() => {
  const s = window.daedalusRealm, m = s.arkModels.get("ark-0");
  return s.debugTarget().distanceTo(m.position);
});
check("the ride camera stays on the ark", gap < 3, `target ${gap.toFixed(2)} cubes from the ark`);
await A.page.waitForTimeout(1500);
await A.page.screenshot({ path: path.join(OUT, "realm_voyage.png") });
const wait = order.ark.arriveAt - order.ark.departAt + 6000;
const moored = await B.page.waitForFunction(() => {
  const a = window.daedalusRealm.arks.find(x => x.id === "ark-0");
  return a && a.state === "MOORED" && a.slot === 1;
}, null, { timeout: wait }).then(() => true, () => false);
check("B hears ARRIVED and moors the ark at Isle 1", moored);
const end = await B.page.evaluate(() => {
  const s = window.daedalusRealm, m = s.arkModels.get("ark-0"), isle = s.islands.find(i => i.slot === 1);
  return { x: m.position.x, dockX: isle.dockX, z: m.position.z, dockZ: isle.dockZ };
});
check("the moored model sits off Isle 1's pier", Math.abs(end.x - (end.dockX + 0.5)) < 1 && Math.abs(end.z - (end.dockZ + 9)) < 1, JSON.stringify(end));
const serverArk = (await (await fetch(BASE + "/api/v1/world/world-zero/arks")).json()).arks[0];
check("the server agrees: ark-0 moored at slot 1", serverArk.state === "MOORED" && serverArk.slot === 1);

// --- Life (ADR-023/024): the ark put its founders ashore; B hears it and can open Isle 1's Life panel.
const landedLabel = await B.page.waitForFunction(() => {
  const el = document.querySelector('.kinds-count[data-slot="1"]');
  return el && /^\d+ kinds? living$/.test(el.textContent) ? el.textContent : false;
}, null, { timeout: 15000 }).then(h => h.jsonValue(), () => null);
const life1 = await (await fetch(BASE + "/api/v1/world/world-zero/islands/1/ecology")).json();
check("B's lane shows the kinds now living on Isle 1", landedLabel === `${life1.richness} kind${life1.richness === 1 ? "" : "s"} living`, `${landedLabel} / server ${life1.richness}`);
const life0 = await (await fetch(BASE + "/api/v1/world/world-zero/islands/0/ecology")).json();
const walkers0 = life0.species.filter(sp => !(B.canon[sp.key] || {}).disperses).length;
check("Isle 0 holds no ark-bound kind: only wings and spores reach it", walkers0 === 0,
  `${life0.richness} kinds, ${walkers0} ark-bound`);
check("the server's ark-0 hold shrank by what landed", serverArk.hold.length < 6 && life1.richness >= 6 - serverArk.hold.length,
  `${serverArk.hold.length} kinds still aboard`);
await B.page.click('.life-btn[data-slot="1"]');
const rows = await B.page.waitForFunction(() => document.querySelectorAll("#life .life-row").length, null, { timeout: 10000 })
  .then(h => h.jsonValue(), () => 0);
const life1b = await (await fetch(BASE + "/api/v1/world/world-zero/islands/1/ecology")).json();
check("tapping Life lists every kind on Isle 1", rows === life1b.richness || rows === life1.richness, `${rows} rows, server ${life1b.richness}`);
const day0 = await B.page.evaluate(() => window.daedalusRealm.day);
const dayMoved = await B.page.waitForFunction(d => window.daedalusRealm.day > d, day0, { timeout: 12000 }).then(() => true, () => false);
check("B hears a DAY frame and the day advances", dayMoved, `from day ${day0}`);
const panelDay = await B.page.waitForFunction(() => {
  const head = document.querySelector("#life .life-head");
  return head && Number(head.dataset.day) === window.daedalusRealm.day;
}, null, { timeout: 8000 }).then(() => true, () => false);
check("the open Life panel follows the day", panelDay, await B.page.evaluate(() =>
  `panel day ${document.querySelector("#life .life-head")?.dataset.day}, state day ${window.daedalusRealm.day}`));
await B.page.screenshot({ path: path.join(OUT, "realm_life.png") });

// --- Reload: a fresh page rebuilds the same world from REST alone.
const C = await open("C");
await C.page.waitForFunction(() => window.daedalusRealm.islands.length === 2, null, { timeout: 30000 });
check("a fresh page rebuilds the same world", (await cubes(C.page)) === (await serverCubes()));
await C.page.waitForFunction(() => window.daedalusRealm.arks.length === 2, null, { timeout: 15000 });
check("a fresh page knows where every ark is", await C.page.evaluate(() => window.daedalusRealm.arks.find(a => a.id === "ark-0").slot === 1));

for (const p of [A, B, C]) check(`no console errors on page ${p.name}`, p.errors.length === 0, p.errors.slice(0, 3).join(" | "));
await browser.close();
console.log(failures.length ? `\n${failures.length} FAILED` : "\nALL PASS");
process.exit(failures.length ? 1 : 0);
