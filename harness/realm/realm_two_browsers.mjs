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
await context.route("https://cdn.jsdelivr.net/npm/ethers@6.17.0/**", r => {
  r.fulfill({ body: fs.readFileSync(`${NM}/ethers/dist/ethers.min.js`), contentType: "application/javascript", headers: { "access-control-allow-origin": "*" } });
});
await context.route("https://cdn.jsdelivr.net/npm/three@0.160.0/**", r => {
  const rel = new URL(r.request().url()).pathname.replace("/npm/three@0.160.0/", "");
  r.fulfill({ body: fs.readFileSync(`${NM}/three/${rel}`), contentType: "application/javascript", headers: { "access-control-allow-origin": "*" } });
});

/**
 * The errors a check should see. SockJS falls back to XHR polling when a starved page drops its websocket, and
 * if the page then misses its own poll the server forgets the session: the next send is a 404 on
 * /ws/<n>/<session>/xhr_send, the browser logs a matching "Failed to load resource … 404", and the realm reconnects
 * by itself (connectLive). Those pairs are transport weather, not the page's fault; every other error counts.
 */
function cleanErrors(errors) {
  const ws = errors.filter(e => /^404 .*\/ws\/\d+\/[^/]+\/xhr/.test(e));
  let generic = ws.length;
  return errors.filter(e => {
    if (ws.includes(e)) return false;
    if (generic > 0 && /Failed to load resource: the server responded with a status of 404/.test(e)) { generic--; return false; }
    return true;
  });
}

// Every 4xx/5xx any page meets, with its URL, printed at the end: a console "Failed to load resource" names no URL.
const httpErrors = [];
context.on("response", r => { if (r.status() >= 400) httpErrors.push(`${r.status()} ${r.request().method()} ${r.url()}`); });

async function open(name) {
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.request().method()} ${r.url()}`); });
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
// Step off: a page still riding ark-0 would go through the gate with it when the Sky gates section sails it
// there (as a rider should), and the two arrivals would race to hail Isle Two's one ark.
await A.page.click('.ark[data-ark="ark-0"] button.ride');
check("Stop ends the ride", await A.page.evaluate(() => document.querySelector('.ark[data-ark="ark-0"] button.ride').textContent === "Ride"));
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
const pair = await B.page.evaluate(() => {
  const m = window.daedalusRealm.arkModels;
  return [m.get("ark-0").position.x, m.get("ark-1").position.x];
});
check("two arks at one pier lie side by side, not inside each other", Math.abs(pair[0] - pair[1]) >= 20,
  `x ${pair.map(v => v.toFixed(1)).join(" / ")}`);
check("the moored model sits off Isle 1's pier", Math.abs(end.x - (end.dockX + 0.5)) < 1 && Math.abs(end.z - (end.dockZ + 9)) < 1, JSON.stringify(end));
const serverArk = (await (await fetch(BASE + "/api/v1/world/world-zero/arks")).json()).arks[0];
check("the server agrees: ark-0 moored at slot 1", serverArk.state === "MOORED" && serverArk.slot === 1);

// --- Life (ADR-023/024): the ark put its founders ashore; B hears it and can open Isle 1's Life panel.
const landedLabel = await B.page.waitForFunction(() => {
  const el = document.querySelector('.kinds-count[data-slot="1"]');
  return el && /^\d+ kinds? living$/.test(el.textContent) ? el.textContent : false;
}, null, { timeout: 15000 }).then(h => h.jsonValue(), () => null);
// Days tick every 2 s, so the label and the server can be a frame apart: poll until they agree.
let life1 = null, labelNow = landedLabel;
for (let i = 0; i < 20; i++) {
  life1 = await (await fetch(BASE + "/api/v1/world/world-zero/islands/1/ecology")).json();
  labelNow = await B.page.evaluate(() => document.querySelector('.kinds-count[data-slot="1"]')?.textContent || "");
  if (labelNow === `${life1.richness} kind${life1.richness === 1 ? "" : "s"} living`) break;
  await B.page.waitForTimeout(300);
}
check("B's lane shows the kinds now living on Isle 1", !!landedLabel && labelNow === `${life1.richness} kind${life1.richness === 1 ? "" : "s"} living`,
  `${labelNow} / server ${life1.richness}`);
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

// --- Creatures (ADR-025): every kind on Isle 1 is drawn there, where its guild lives, the same on every page.
await Promise.all([A.page.evaluate(() => window.daedalusRealm.refreshCreatures([1])),
  B.page.evaluate(() => window.daedalusRealm.refreshCreatures([1]))]);
const drawn = p => p.evaluate(() => {
  const s = window.daedalusRealm, c = s.creatures.get(1);
  if (!c) return null;
  return c.list.map(m => ({ key: m.userData.key, home: [m.userData.home.x, m.userData.home.y, m.userData.home.z],
    ground: m.userData.ground, flies: m.userData.flies,
    under: s.nameAt(m.userData.ground[0], m.userData.ground[1] - 1, m.userData.ground[2]),
    at: s.nameAt(...m.userData.ground) }));
});
const dA = await drawn(A.page), dB = await drawn(B.page);
const life1c = await (await fetch(BASE + "/api/v1/world/world-zero/islands/1/ecology")).json();
const living = new Set(life1c.species.map(s => s.key));
const kindsDrawn = new Set((dB || []).map(c => c.key));
check("creatures are drawn on Isle 1", dB && dB.length > 0, `${dB ? dB.length : 0} bodies, ${kindsDrawn.size} kinds`);
check("every drawn kind lives on Isle 1 on the server", [...kindsDrawn].filter(k => !living.has(k)).length <= 1,
  [...kindsDrawn].filter(k => !living.has(k)).join(","));
const grounded = (dB || []).filter(c => !c.flies && c.ground[1] > 30);
check("walkers, swimmers and caps stand on a real surface", grounded.length > 0 &&
  grounded.every(c => (c.at === "AIR" || c.at === "CLOUD") && c.under !== "AIR"),
  grounded.filter(c => !((c.at === "AIR" || c.at === "CLOUD") && c.under !== "AIR")).slice(0, 3)
    .map(c => `${c.key}@${c.ground.join(",")} in ${c.at} over ${c.under}`).join("; "));
const pondKinds = (dB || []).filter(c => B.canon[c.key]?.guild === "POND");
check("pond kinds are on the water", pondKinds.every(c => c.under === "WATER"), `${pondKinds.length} pond bodies`);
const nth = list => { const seen = {}; return (list || []).map(c => [c.key + "#" + (seen[c.key] = (seen[c.key] || 0) + 1), c.home.join(",")]); };
const homesA = new Map(nth(dA));
const shared = nth(dB).filter(([k]) => homesA.has(k));
const moved = shared.filter(([k, h]) => homesA.get(k) !== h);
check("A and B draw each body in the same place", shared.length > 0 && moved.length === 0,
  `${shared.length} compared${moved.length ? ", differ: " + moved.slice(0, 2).map(m => m[0]).join(",") : ""}`);
// --- Ownership (ADR-026): A claims Isle 1 as alice; B (bob) is refused until alice lets him build.
const ownerLine = (p, slot) => p.evaluate(s => document.querySelector(`.owner[data-slot="${s}"] .owner-line`)?.textContent || "", slot);
await A.page.fill("#me", "alice");
await A.page.dispatchEvent("#me", "change");
await B.page.fill("#me", "bob");
await B.page.dispatchEvent("#me", "change");
await A.page.waitForSelector('.owner[data-slot="1"] button.claim');
await A.page.click('.owner[data-slot="1"] button.claim');
const bSeesOwner = await B.page.waitForFunction(() =>
  (document.querySelector('.owner[data-slot="1"] .owner-line')?.textContent || "") === "owned by alice", null, { timeout: 10000 })
  .then(() => true, () => false);
check("A claims Isle 1; B's lane says it is alice's", bSeesOwner && (await ownerLine(A.page, 1)) === "yours", await ownerLine(B.page, 1));
const spot = await B.page.evaluate(() => { const i = window.daedalusRealm.islands[1]; return { x: i.x + 3, y: i.y + i.top + 2, z: i.z + 3 }; });
const refused = B.page.waitForResponse(r => r.url().endsWith("/block") && r.request().method() === "PUT");
await B.page.evaluate(p => window.daedalusRealm.writeBlock(p.x, p.y, p.z, "CRYSTAL"), spot);
const refusal = await (await refused).json();
check("bob's cube on alice's island is DENIED", refusal.result === "DENIED", refusal.result);
check("B rolls the cube back and says whose island it is",
  await B.page.evaluate(p => window.daedalusRealm.nameAt(p.x, p.y, p.z) === "AIR" &&
    window.daedalusRealm.lastRefusal === "Isle 1 belongs to alice", spot));
await A.page.fill('.owner[data-slot="1"] input.builder-name', "bob");
await A.page.click('.owner[data-slot="1"] button.let');
await B.page.waitForFunction(() => (document.querySelector('.owner[data-slot="1"] .owner-line')?.textContent || "").endsWith("you may build"), null, { timeout: 10000 }).catch(() => {});
const allowed = B.page.waitForResponse(r => r.url().endsWith("/block") && r.request().method() === "PUT");
await B.page.evaluate(p => window.daedalusRealm.writeBlock(p.x, p.y, p.z, "CRYSTAL"), spot);
const ok = await (await allowed).json();
check("once alice lets bob build, his cube lands", ok.result === "PLACED", ok.result);
const aSees = await A.page.waitForFunction(p => window.daedalusRealm.nameAt(p.x, p.y, p.z) === "CRYSTAL", spot, { timeout: 10000 }).then(() => true, () => false);
check("A sees bob's cube on her island", aSees);
await A.page.click('.owner[data-slot="1"] button.abandon');
const reopened = await B.page.waitForFunction(() => (document.querySelector('.owner[data-slot="1"] .owner-line')?.textContent || "").startsWith("open"), null, { timeout: 10000 }).then(() => true, () => false);
const serverIsle = (await (await fetch(BASE + "/api/v1/world/world-zero/islands")).json()).islands[1];
check("alice gives Isle 1 up; it is open again everywhere", reopened && serverIsle.owner === "" && serverIsle.builders.length === 0);
await A.page.click('.owner[data-slot="1"] button.claim');
await A.page.waitForFunction(() => (document.querySelector('.owner[data-slot="1"] .owner-line')?.textContent || "") === "yours", null, { timeout: 10000 }).catch(() => {});

await B.page.evaluate(() => document.querySelectorAll("#islands button.go")[1].click());
await B.page.waitForTimeout(1500);
await B.page.screenshot({ path: path.join(OUT, "realm_creatures.png") });

// --- Deeds (ADR-027): the Life panel shows the token portrait; a deed's link opens on its island.
const deedImg = await B.page.waitForFunction(() => {
  const img = document.querySelector("#life .deed img");
  return img && img.complete && img.naturalWidth === 512 ? img.getAttribute("src") : false;
}, null, { timeout: 10000 }).then(h => h.jsonValue(), () => null);
check("the Life panel shows Isle 1's portrait", deedImg && deedImg.endsWith("/islands/1/portrait.png"), String(deedImg));
const meta = await (await fetch(BASE + "/api/v1/world/world-zero/tokens/1")).json();
const metaImg = await fetch(meta.image);
check("token 1's metadata points at a real PNG", metaImg.ok && metaImg.headers.get("content-type") === "image/png",
  `${meta.name} → ${meta.image}`);
const D = await (async () => {
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(meta.external_url);
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live, null, { timeout: 30000 });
  return { name: "D", page, errors };
})();
const opened = await D.page.waitForFunction(() => window.daedalusRealm.lifeSlot === 1 &&
  document.querySelectorAll("#life .life-row").length > 0, null, { timeout: 15000 }).then(() => true, () => false);
check("the deed's link opens the realm on Isle 1 with its Life panel", opened, meta.external_url);
await D.page.waitForTimeout(1200);
await D.page.screenshot({ path: path.join(OUT, "realm_deed.png") });

// --- Wallet (ADR-028): a page with a wallet signs in, claims Isle 0 and mints its deed on a local chain.
// Runs when REALM_RPC points at a Hardhat node with RealmIslands deployed (chain/: npm run node, deploy:local)
// and the server has DAEDALUS_WALLET_ENABLED=true with that contract and the matching deed key.
const RPC = process.env.REALM_RPC;
let W = null;
if (RPC) {
  const { Wallet, JsonRpcProvider, Contract, getBytes, isHexString } = await import("ethers");
  const chain = new JsonRpcProvider(RPC);
  // Hardhat test account 1: published, local chains only.
  const player = new Wallet("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d", chain);
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  // window.ethereum, as a browser wallet exposes it: accounts and signing here, everything else to the node.
  await page.exposeFunction("__walletRpc", async (method, paramsJson) => {
    const params = JSON.parse(paramsJson || "[]");
    try {
      switch (method) {
        case "eth_requestAccounts": case "eth_accounts": return JSON.stringify({ result: [player.address] });
        case "personal_sign": {
          const m = params[0];
          return JSON.stringify({ result: await player.signMessage(isHexString(m) ? getBytes(m) : m) });
        }
        case "wallet_switchEthereumChain": return JSON.stringify({ result: null });
        case "eth_sendTransaction": {
          const t = params[0];
          const sent = await player.sendTransaction({ to: t.to, data: t.data, value: t.value ?? 0n, gasLimit: t.gas });
          return JSON.stringify({ result: sent.hash });
        }
        default: return JSON.stringify({ result: await chain.send(method, params) });
      }
    } catch (e) {
      return JSON.stringify({ error: { code: e.code ?? -32603, message: e.shortMessage || e.message } });
    }
  });
  await page.addInitScript(() => {
    window.ethereum = {
      isTestWallet: true,
      async request({ method, params }) {
        const o = JSON.parse(await window.__walletRpc(method, JSON.stringify(params || [])));
        if (o.error) throw Object.assign(new Error(o.error.message), { code: o.error.code });
        return o.result;
      },
      on() {}, removeListener() {},
    };
  });
  await page.goto(BASE + "/realm.html");
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live, null, { timeout: 30000 });
  W = { name: "W", page, errors };
  const cfg = await (await fetch(BASE + "/api/v1/auth/wallet/config")).json();
  await page.waitForSelector("#wallet", { state: "visible", timeout: 10000 });
  await page.click("#wallet");
  const signedIn = await page.waitForFunction(a => window.daedalusRealm.me === a && !!window.daedalusRealm.token,
    player.address.toLowerCase(), { timeout: 15000 }).then(() => true, () => false);
  check("a wallet signs the server's message and the realm knows it by its address", signedIn,
    await page.evaluate(() => document.getElementById("wallet").textContent));
  await page.waitForSelector('.owner[data-slot="0"] button.claim', { timeout: 10000 });
  await page.click('.owner[data-slot="0"] button.claim');
  await page.waitForFunction(() => document.querySelector('.owner[data-slot="0"] .owner-line')?.textContent === "yours", null, { timeout: 10000 });
  const claimed = (await (await fetch(BASE + "/api/v1/world/world-zero/islands")).json()).islands[0].owner;
  check("the wallet claims Isle 0 under its address", claimed === player.address.toLowerCase(), claimed);
  await page.waitForSelector('.owner[data-slot="0"] button.mint', { timeout: 10000 });
  await page.click('.owner[data-slot="0"] button.mint');
  const minted = await page.waitForFunction(() => window.daedalusRealm.lastMint && window.daedalusRealm.lastMint.slot === 0, null, { timeout: 60000 })
    .then(() => true, () => false);
  const islands = new Contract(cfg.deedContract, ["function ownerOf(uint256) view returns (address)", "function seedOf(uint256) view returns (uint64)", "function tokenURI(uint256) view returns (string)"], chain);
  const onChain = minted ? { owner: await islands.ownerOf(0), seed: await islands.seedOf(0), uri: await islands.tokenURI(0) } : null;
  check("Mint deed puts Isle 0 on chain: ownerOf(0) is the wallet and seedOf(0) is the island's seed",
    !!onChain && onChain.owner === player.address && onChain.seed === 11n,
    onChain ? `${onChain.owner} seed ${onChain.seed} ${onChain.uri}` : await page.evaluate(() => document.getElementById("toast").textContent));
  const layout = await page.evaluate(() => {
    const input = document.querySelector('.owner[data-slot="0"] input.builder-name').getBoundingClientRect();
    const row = document.querySelector('.owner[data-slot="0"] .owner-act').getBoundingClientRect();
    return { input: Math.round(input.width), row: Math.round(row.width), name: getComputedStyle(document.getElementById("me")).display };
  });
  check("the builder field gets a full row and the name box gives way to the wallet button",
    layout.input >= layout.row - 2 && layout.name === "none", JSON.stringify(layout));
  const noToken = await fetch(BASE + "/api/v1/world/world-zero/islands/0/deed-voucher", { method: "POST" });
  check("no voucher without a signed-in wallet", noToken.status === 401, String(noToken.status));
  await page.screenshot({ path: path.join(OUT, "realm_wallet.png") });
}

// --- Worlds (ADR-030): name a new world on page C's form, land in it, and visit back.
{
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(BASE + "/realm.html");
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live, null, { timeout: 30000 });
  await page.waitForSelector('.world-row[data-world="world-zero"] .here', { timeout: 10000 });
  const zeroBefore = (await (await fetch(BASE + "/api/v1/world/world-zero/islands")).json()).islands.length;
  await page.fill("#newWorldName", "Isle Two");
  await page.fill("#newWorldSeed", "42");
  await Promise.all([page.waitForURL(/realm\.html\?world=isle-two/, { timeout: 30000 }), page.click("#newWorldGo")]);
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live && window.daedalusRealm.islands.length === 1, null, { timeout: 30000 });
  const there = await page.evaluate(() => ({
    title: document.getElementById("worldTitle").textContent,
    seed: window.daedalusRealm.islands[0].seed,
    here: document.querySelector('.world-row[data-world="isle-two"] .here') !== null,
    arks: window.daedalusRealm.arks.length,
  }));
  check("a new world is named on the page, born with its own island, and the page moves into it",
    there.title === "Isle Two" && there.seed === 42 && there.here && there.arks === 1, JSON.stringify(there));
  const zeroAfter = (await (await fetch(BASE + "/api/v1/world/world-zero/islands")).json()).islands.length;
  check("World Zero's lane is untouched by the new world", zeroAfter === zeroBefore, `${zeroBefore} → ${zeroAfter} islands`);
  await page.waitForTimeout(1300);
  await page.screenshot({ path: path.join(OUT, "realm_world_two.png") });
  await Promise.all([page.waitForURL(/realm\.html\?world=world-zero$/, { timeout: 30000 }), page.click('.world-row[data-world="world-zero"] button.visit')]);
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.islands.length === 2, null, { timeout: 30000 });
  check("Visit carries the page back to World Zero", (await page.evaluate(() => document.getElementById("worldTitle").textContent)) === "World Zero");
  check("no console errors while crossing worlds", cleanErrors(errors).length === 0, cleanErrors(errors).slice(0, 3).join(" | "));
  await page.close();
}

// --- Sky gates (ADR-031): open a gate to Isle Two, ride an ark through the rainbow to it, cross over, and
// let Isle Two's ark come up to its own gate to carry you down to its island.
{
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(BASE + "/realm.html?world=world-zero");
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live && window.daedalusRealm.arks.length >= 2, null, { timeout: 30000 });
  await page.waitForSelector('.world-row[data-world="isle-two"] button.open-gate', { timeout: 10000 });
  await page.click('.world-row[data-world="isle-two"] button.open-gate');
  const gateUp = await page.waitForFunction(() => {
    const s = window.daedalusRealm;
    if (s.gates.length !== 1) return false;
    const g = s.gates[0];
    return s.nameAt(g.x, g.y, g.z) === "PORTAL" && s.nameAt(g.x, g.y - 14 + 17, -170) === "RAINBOW_VIOLET";
  }, null, { timeout: 20000 }).then(() => true, () => false);
  check("Open gate builds a doorway in the clouds past a rainbow, and the page draws it", gateUp,
    JSON.stringify(await page.evaluate(() => window.daedalusRealm.gates)));
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUT, "realm_rainbow_gate.png") });
  const reach = await page.evaluate(() => {
    const s = window.daedalusRealm, g = s.gates[0];
    return { gateZ: g.z, islandsZ: s.islands.map(i => i.z) };
  });
  check("the gate is far from every island: no one walks there", reach.islandsZ.every(z => z - reach.gateZ > 100), JSON.stringify(reach));
  await page.selectOption('.ark[data-ark="ark-0"] select.dest', "1000");
  await page.click('.ark[data-ark="ark-0"] button.sail');
  const crossed = await page.waitForURL(/realm\.html\?world=isle-two&arrive=0$/, { timeout: 90000 }).then(() => true, () => false);
  check("riding ark-0 to the gate carries you through to Isle Two", crossed, page.url());
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live && window.daedalusRealm.gates.length === 1, null, { timeout: 30000 });
  const hailed = await page.waitForFunction(() => window.daedalusRealm.lastHail && window.daedalusRealm.lastHail.arkId === "ark-0", null, { timeout: 30000 })
    .then(() => true, () => false);
  check("on the far side, Isle Two's ark is hailed up to its gate", hailed, JSON.stringify(await page.evaluate(() => ({
    url: location.href, lastHail: window.daedalusRealm.lastHail, gates: window.daedalusRealm.gates.length,
    arks: window.daedalusRealm.arks.map(a => `${a.id}:${a.state}@${a.slot}`), toast: document.getElementById("toast").textContent }))));
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(OUT, "realm_gate_arrival.png") });
  const home = await page.waitForFunction(() => {
    const a = window.daedalusRealm.arks.find(x => x.id === "ark-0");
    return a && a.state === "SAILING" && a.fromSlot === 1000 && a.toSlot === 0;
  }, null, { timeout: 90000 }).then(() => true, () => false);
  check("it meets you at the gate and sails you down to its island", home,
    JSON.stringify(await page.evaluate(() => window.daedalusRealm.arks.find(x => x.id === "ark-0"))));
  check("no console errors on the gate run", cleanErrors(errors).length === 0, cleanErrors(errors).slice(0, 3).join(" | "));
  await page.close();
}

// --- World Package (ADR-032): the world, exported once, loads in another engine exactly as the realm draws it.
{
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(BASE + "/realm.html?world=world-zero");
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live && window.daedalusRealm.gates.length === 1, null, { timeout: 30000 });
  const pkg = await page.evaluate(async () => {
    const { GLTFLoader } = await import("three/addons/loaders/GLTFLoader.js");
    const manifest = await (await fetch("/api/v1/world/world-zero/package/manifest")).json();
    const gltf = await new GLTFLoader().loadAsync("/api/v1/world/world-zero/package/world.glb");
    let tris = 0, nodes = 0, translucent = 0, outOfRange = 0;
    gltf.scene.traverse(o => {
      if (o.isMesh) {
        tris += o.geometry.index.count / 3;
        if (o.material.transparent) translucent++;
        const c = o.geometry.attributes.color.array;
        for (let i = 0; i < c.length; i++) if (c[i] < 0 || c[i] > 1) outOfRange++;
      }
    });
    // A one-primitive node loads as a Mesh, a two-primitive node as a Group of two: count the scene's nodes.
    nodes = gltf.scene.children.filter(o => o.name.startsWith("chunk_")).length;
    // What the realm itself drew: its chunk meshes' triangles.
    let realmTris = 0;
    for (const group of window.daedalusRealm.meshes.values()) {
      for (const m of group.children) if (m.isMesh && m.geometry.index) realmTris += m.geometry.index.count / 3;
    }
    const zip = await fetch("/api/v1/world/world-zero/package");
    return { manifest, tris, nodes, translucent, outOfRange, realmTris, zipType: zip.headers.get("content-type"),
             zipName: zip.headers.get("content-disposition"), zipBytes: (await zip.arrayBuffer()).byteLength };
  });
  check("the World Package manifest names the world, its gate and its arks", pkg.manifest.format === "daedalus-world-package"
      && pkg.manifest.world.id === "world-zero" && pkg.manifest.gates.length === 1 && pkg.manifest.gates[0].toWorld === "isle-two"
      && pkg.manifest.arks.length === 2, JSON.stringify({ world: pkg.manifest.world, gates: pkg.manifest.gates.length, arks: pkg.manifest.arks.length }));
  check("three.js loads world.glb: one node per chunk, the manifest's triangles, blended glass and rainbow",
      pkg.nodes === pkg.manifest.geometry.chunks && pkg.tris === pkg.manifest.geometry.triangles && pkg.translucent > 0 && pkg.outOfRange === 0,
      `${pkg.nodes} nodes / ${pkg.manifest.geometry.chunks} chunks, ${pkg.tris} / ${pkg.manifest.geometry.triangles} triangles, ${pkg.translucent} blended, ${pkg.outOfRange} colours out of 0..1`);
  check("the exported world has exactly the triangles the realm draws", pkg.realmTris === pkg.tris,
      `realm ${pkg.realmTris}, package ${pkg.tris}`);
  check("the whole package downloads as a named zip", pkg.zipType === "application/zip" && /world-zero-r\d+\.daedalus\.zip/.test(pkg.zipName) && pkg.zipBytes > 100000,
      `${pkg.zipType} ${pkg.zipName} ${pkg.zipBytes} bytes`);
  check("no page errors loading the package", cleanErrors(errors).length === 0, cleanErrors(errors).slice(0, 3).join(" | "));
  await page.close();
}

// --- Parcels (ADR-033): a Decentraland-style world. Claim a plot from the map, build on it (and only on it),
// and fly the helicopter from the plaza's pad up through the rainbow to a gate.
{
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(BASE + "/realm.html");
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live, null, { timeout: 30000 });
  await page.fill("#newWorldName", "Plaza Town");
  await page.fill("#newWorldSeed", "5");
  await page.selectOption("#newWorldStyle", "PARCELS");
  await Promise.all([page.waitForURL(/realm\.html\?world=plaza-town/, { timeout: 30000 }), page.click("#newWorldGo")]);
  await page.waitForFunction(() => { const s = window.daedalusRealm;
    return s && s.live && s.district && s.plots && s.plots.length === 60 && s.arks.length === 1 && s.arkModels.size === 1; },
  null, { timeout: 30000 });
  const look = await page.evaluate(() => {
    const s = window.daedalusRealm, d = s.district;
    return { cells: document.querySelectorAll(".plot-grid .plot").length, plaza: document.querySelectorAll(".plot-grid .plot.plaza").length,
      lane: document.getElementById("laneTitle").textContent, raise: getComputedStyle(document.getElementById("raiseRow")).display,
      heli: s.arks[0].id, name: s.arks[0].name, rotor: !!s.arkModels.get("heli-0").getObjectByName("rotor"),
      pad: s.nameAt(d.padX - 5, 0, d.padZ - 5), road: s.nameAt(-25, 0, -60), islands: s.islands.length };
  });
  check("a Parcels world is born with its district: a plot map around the plaza, a helipad, a helicopter",
    look.cells === 64 && look.plaza === 4 && look.lane === "PLOTS" && look.raise === "none" && look.heli === "heli-0"
      && look.rotor && look.pad === "HELIPAD" && look.road === "ROAD" && look.islands === 0, JSON.stringify(look));
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(OUT, "realm_parcels.png") });

  await page.fill("#me", "carol");
  await page.dispatchEvent("#me", "change");
  await page.click('.plot-grid .plot[data-plot="9"]');
  await page.waitForSelector("#islands .owner button.claim", { timeout: 10000 });
  await page.click("#islands .owner button.claim");
  const claimed = await page.waitForFunction(() => {
    const p = (window.daedalusRealm.plots || []).find(x => x.n === 9);
    return p && p.owner === "carol" && document.querySelector('.plot-grid .plot[data-plot="9"]').classList.contains("yours");
  }, null, { timeout: 10000 }).then(() => true, () => false);
  check("tapping plot 9 on the map and Claim makes it carol's", claimed);

  const tries = await page.evaluate(async () => {
    const s = window.daedalusRealm, p = s.plots.find(x => x.n === 9), q = s.plots.find(x => x.n === 10);
    const out = {};
    s.lastRefusal = null; await s.writeBlock(p.minX + 3, 1, p.minZ + 3, "CRYSTAL"); out.inside = s.lastRefusal;
    s.lastRefusal = null; await s.writeBlock(p.maxX + 2, 1, p.minZ + 3, "CRYSTAL"); out.street = s.lastRefusal;
    s.lastRefusal = null; await s.writeBlock(p.minX + 3, s.district.height + 1, p.minZ + 3, "CRYSTAL"); out.high = s.lastRefusal;
    s.lastRefusal = null; await s.writeBlock(q.minX + 3, 1, q.minZ + 3, "CRYSTAL"); out.open = s.lastRefusal;
    out.at = [p.minX + 3, p.minZ + 3, p.maxX + 2];
    return out;
  });
  const cube = async (x, y, z) => (await (await fetch(`${BASE}/api/v1/world/plaza-town/block?x=${x}&y=${y}&z=${z}`)).json()).type;
  const built = await cube(tries.at[0], 1, tries.at[1]);
  const street = await cube(tries.at[2], 1, tries.at[1]);
  check("carol builds on her plot; a street, the sky over the limit and an unclaimed plot each refuse with a reason",
    built === "CRYSTAL" && street === "AIR" && !tries.inside && /Streets/.test(tries.street || "") && /high/.test(tries.high || "")
      && /Claim Plot 10/.test(tries.open || ""), JSON.stringify(Object.assign({ built, street }, tries)));

  const opened = await (await fetch(BASE + "/api/v1/world/plaza-town/gates", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ toWorld: "world-zero" }) })).json();
  await page.waitForFunction(() => window.daedalusRealm.gates.length === 1
    && document.querySelector('.ark[data-ark="heli-0"] select.dest option[value="1000"]'), null, { timeout: 20000 });
  await page.selectOption('.ark[data-ark="heli-0"] select.dest', "1000");
  const lifted = await page.evaluate(() => document.querySelector('.ark[data-ark="heli-0"] button.sail').textContent);
  await page.click('.ark[data-ark="heli-0"] button.sail');
  const up = await page.waitForFunction(() => { const a = window.daedalusRealm.arks[0], m = window.daedalusRealm.arkModels.get("heli-0");
    return a.state === "SAILING" && m.position.y > 20; }, null, { timeout: 30000 }).then(() => true, () => false);
  check("Fly lifts the helicopter off the pad toward the gate", opened.result === "OPENED" && lifted === "Fly" && up,
    JSON.stringify({ opened, lifted }));
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(OUT, "realm_helicopter.png") });
  const crossed = await page.waitForURL(new RegExp(`realm\\.html\\?world=world-zero&arrive=${opened.toGate}$`), { timeout: 120000 })
    .then(() => true, () => false);
  check("riding the helicopter through the rainbow carries you to World Zero", crossed, page.url());
  const met = await page.waitForFunction(g => window.daedalusRealm && window.daedalusRealm.lastHail && window.daedalusRealm.lastHail.gate === g,
    opened.toGate, { timeout: 30000 }).then(() => true, () => false);
  check("World Zero hails one of its arks up to the gate the helicopter came through", met,
    JSON.stringify(await page.evaluate(() => window.daedalusRealm && window.daedalusRealm.lastHail)));
  check("no console errors in the Parcels world", cleanErrors(errors).length === 0, cleanErrors(errors).slice(0, 3).join(" | "));
  await page.close();
}

// --- Bricks (ADR-034): the Roblox look. A studded baseplate, an obby over lava, a plane on the runway, and a
// blocky avatar you play as: walk, fall in the lava, reach a checkpoint, jump onto the gold finish.
{
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(BASE + "/realm.html");
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live, null, { timeout: 30000 });
  await page.fill("#newWorldName", "Studs");
  await page.fill("#newWorldSeed", "11");
  await page.selectOption("#newWorldStyle", "BRICKS");
  await Promise.all([page.waitForURL(/realm\.html\?world=studs/, { timeout: 30000 }), page.click("#newWorldGo")]);
  await page.waitForFunction(() => { const s = window.daedalusRealm;
    return s && s.live && s.bricks && s.arks.length === 1 && s.arkModels.size === 1; }, null, { timeout: 30000 });
  const look = await page.evaluate(() => {
    const s = window.daedalusRealm, b = s.bricks;
    return { lane: document.getElementById("laneTitle").textContent, jumps: b.platforms.length,
      studs: [...s.meshes.values()].some(g => g.children.some(m => m.material.map)),
      spawn: s.nameAt(b.spawnX, b.spawnY - 1, b.spawnZ), plate: s.nameAt(80, 0, -100),
      lava: s.nameAt(b.platforms[3].minX, b.lavaY, b.platforms[3].minZ),
      plane: s.arks[0].id, prop: !!s.arkModels.get("plane-0").getObjectByName("prop"),
      palette: [...document.querySelectorAll(".swatch")].map(x => x.title.split(" ")[0]).slice(0, 3) };
  });
  check("a Bricks world is born with a studded baseplate, a spawn, an obby over lava and a plane",
    look.lane === "OBBY" && look.jumps === 18 && look.studs && look.spawn === "SPAWN" && look.plate === "BASEPLATE"
      && look.lava === "LAVA" && look.plane === "plane-0" && look.prop && look.palette[0] === "BRICK_RED", JSON.stringify(look));
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(OUT, "realm_bricks.png") });

  const built = await page.evaluate(async () => {
    const s = window.daedalusRealm, out = {};
    s.lastRefusal = null; await s.writeBlock(80, 1, -100, "BRICK_BLUE"); out.plate = s.lastRefusal;
    s.lastRefusal = null; await s.writeBlock(20, 6, -60, "BRICK_BLUE"); out.obby = s.lastRefusal;
    s.lastRefusal = null; await s.writeBlock(80, s.bricks.height + 1, -100, "BRICK_BLUE"); out.high = s.lastRefusal;
    return out;
  });
  const placed = (await (await fetch(`${BASE}/api/v1/world/studs/block?x=80&y=1&z=-100`)).json()).type;
  check("anyone builds on the open plate; the obby and the sky over the limit refuse with reasons",
    placed === "BRICK_BLUE" && !built.plate && /obby/.test(built.obby || "") && /48 high/.test(built.high || ""),
    JSON.stringify(Object.assign({ placed }, built)));

  await page.bringToFront();   // a background tab gets no animation frames, so no physics
  await page.click("#modePlay");
  await page.waitForFunction(() => window.daedalusRealm.avatar.on && document.body.classList.contains("playing"), null, { timeout: 5000 });
  await page.waitForTimeout(600);
  const a0 = await page.evaluate(() => window.daedalusRealm.avatar.pos.toArray());
  await page.keyboard.down("w");
  await page.waitForFunction(z => window.daedalusRealm.avatar.pos.z < z - 1.5, a0[2], { timeout: 8000 }).catch(() => {});
  await page.keyboard.up("w");
  await page.waitForTimeout(300);
  const a1 = await page.evaluate(() => ({ p: window.daedalusRealm.avatar.pos.toArray(), ground: window.daedalusRealm.avatar.onGround,
    stick: getComputedStyle(document.getElementById("stick")).display }));
  check("Play puts a blocky avatar on the spawn, and W walks it toward the obby", Math.abs(a0[0] - 20.5) < 0.6 && a0[1] === 2
    && a1.p[2] < a0[2] - 1 && a1.ground && a1.stick === "block", JSON.stringify({ a0, a1 }));
  await page.screenshot({ path: path.join(OUT, "realm_play.png") });

  const fell = await page.evaluate(async () => {
    const s = window.daedalusRealm, q = s.bricks.platforms[2];
    s.avatar.pos.set(q.minX - 3 + 0.5, s.bricks.lavaY + 2, q.minZ + 0.5);
    s.avatar.vel.set(0, 0, 0);
    await new Promise(r => setTimeout(r, 1500));
    return { death: s.lastDeath, at: s.avatar.pos.toArray() };
  });
  check("lava sends the avatar back to the spawn before any checkpoint", fell.death && fell.death.deaths === 1
    && Math.abs(fell.at[2] - (-23.5)) < 0.6, JSON.stringify(fell));

  const cp = await page.evaluate(async () => {
    const s = window.daedalusRealm, q = s.bricks.platforms[17];
    s.avatar.pos.set((q.minX + q.maxX + 1) / 2, q.y + 1.2, (q.minZ + q.maxZ + 1) / 2);
    s.avatar.vel.set(0, 0, 0);
    await new Promise(r => setTimeout(r, 800));
    const out = { reached: s.avatar.reached, respawn: s.avatar.respawn.toArray(), y: q.y };
    s.avatar.pos.z = q.minZ + 0.4;     // to the platform's far edge, facing the finish
    return out;
  });
  check("standing on the last checkpoint makes it the place to come back to", cp.reached === 17 && cp.respawn[1] === cp.y + 1,
    JSON.stringify(cp));
  // Hold Forward and Jump until the run ends one way or the other: on a starved page a frame can come late,
  // so the keys are held by outcome, not by the clock, as a player holds them until they land.
  const deathsBefore = await page.evaluate(() => window.daedalusRealm.avatar.deaths);
  await page.keyboard.down("w");
  await page.keyboard.down(" ");
  await page.waitForFunction(d => window.daedalusRealm.lastFinish || window.daedalusRealm.avatar.deaths > d, deathsBefore,
    { timeout: 15000 }).catch(() => {});
  await page.keyboard.up(" ");
  await page.keyboard.up("w");
  const done = await page.waitForFunction(() => window.daedalusRealm.lastFinish, null, { timeout: 3000 }).then(() => true, () => false);
  check("a running jump from the checkpoint lands on the gold finish and stops the clock", done,
    JSON.stringify(await page.evaluate(() => ({ f: window.daedalusRealm.lastFinish, p: window.daedalusRealm.avatar.pos.toArray(),
      toast: document.getElementById("toast").textContent }))));
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(OUT, "realm_obby_finish.png") });
  await page.click("#modePlay");
  check("Play again leaves play: the avatar goes and the stick hides", await page.evaluate(() =>
    !window.daedalusRealm.avatar.on && getComputedStyle(document.getElementById("stick")).display === "none"));
  check("no console errors in the Bricks world", cleanErrors(errors).length === 0, cleanErrors(errors).slice(0, 3).join(" | "));
  await page.close();
}

// --- The fight (ADR-037): Zelda II in the realm. High and low decide every exchange; EXP is the server's;
// a level is a choice that resets EXP; a hit knocks you back; a shield stops a blow at its height; a fall
// costs unspent EXP.
{
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(BASE + "/realm.html");
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live && window.daedalusRealm.islands.length >= 1, null, { timeout: 30000 });
  await page.bringToFront();
  const heroName = `link-${Date.now() % 1000000}`;     // a new hero every run
  await page.fill("#me", heroName);
  await page.dispatchEvent("#me", "change");
  await page.click("#modePlay");
  await page.waitForFunction(() => window.daedalusRealm.hero.data && window.daedalusRealm.avatar.onGround, null, { timeout: 15000 });
  const sleep = ms => page.waitForTimeout(ms);
  const ev = (f, a) => page.evaluate(f, a);
  await ev(() => { window.daedalusRealm.spawning = false; });
  const hud = await ev(() => ({ hearts: document.querySelector("#heroHud .hearts").textContent, sword: getComputedStyle(document.getElementById("swordBtn")).display,
    side: getComputedStyle(document.getElementById("side")).display }));
  check("Play arms the hero: three hearts, a sword and crouch on screen, the panel out of the way",
    hud.hearts === "♥♥♥" && hud.sword === "block" && hud.side === "none", JSON.stringify(hud));

  // Swing until the foes are gone (or 25 s pass): thrust whenever the sword has recovered, facing the nearest
  // foe, at the height `stance(foe)` names. Held by outcome, not by a count of swings, so a page that gets few
  // frames still finishes the fight.
  const fight = async stance => {
    const outcomes = [];
    const t0 = Date.now();
    while (Date.now() - t0 < 25000 && await ev(() => window.daedalusRealm.foes.length)) {
      const before = await ev(st => { const r = window.daedalusRealm, f = r.foes[0];
        r.avatar.yaw = Math.atan2(-(f.pos.x - r.avatar.pos.x), -(f.pos.z - r.avatar.pos.z));
        r.heroAct.crouch(st === "LOW" || (st === "READ" && f.shield === "HIGH"));
        if (r.hero.hp < 3) r.hero.hp = r.hero.data.maxLife;     // a potion between rounds
        if (r.hero.recover > 0) return -1;
        const n = r.thrusts || 0; r.heroAct.thrust(); return n; }, stance);
      await sleep(120);
      if (before < 0) continue;
      await page.waitForFunction(() => window.daedalusRealm.hero.recover <= 0, null, { timeout: 5000 }).catch(() => {});
      const t = await ev(() => window.daedalusRealm.lastThrust || {});
      outcomes.push(t.n > before ? t.outcome : "MISS");
    }
    await ev(() => window.daedalusRealm.heroAct.crouch(false));
    return outcomes;
  };
  const fresh = s => { const r = window.daedalusRealm; r.avatar.yaw = 0; r.avatar.vel.set(0, 0, 0); r.hero.knock.set(0, 0, 0);
    r.hero.hp = r.hero.data.maxLife; r.hero.blink = 0; return r.spawnFoe(s, 0, -1.6); };
  // One thrust, waited for until it has met something (or recovered), however few frames the page gets.
  const thrustOnce = async () => {
    const n = await ev(() => { const r = window.daedalusRealm; const k = r.thrusts || 0; r.heroAct.thrust(); return k; });
    await page.waitForFunction(k => (window.daedalusRealm.lastThrust || {}).n > k, n, { timeout: 8000 }).catch(() => {});
    return ev(k => { const t = window.daedalusRealm.lastThrust || {}; return t.n > k ? t : { outcome: "MISS" }; }, n);
  };
  await ev(fresh, "SHARDBACK");
  await page.waitForFunction(() => window.daedalusRealm.foes.length === 1, null, { timeout: 5000 }).catch(() => {});
  const high = await thrustOnce();
  await fight("LOW");
  await page.waitForFunction(() => window.daedalusRealm.hero.data.beaten >= 1, null, { timeout: 5000 }).catch(() => {});
  const afterShard = await ev(() => ({ low: window.daedalusRealm.lastThrust, foes: window.daedalusRealm.foes.length, exp: window.daedalusRealm.hero.data.exp }));
  check("a shardback's shell turns a standing thrust; crouch and thrust low to beat it (+5 EXP on the server)",
    high.outcome === "GUARDED" && afterShard.low?.outcome === "HIT" && afterShard.low?.at === "LOW" && afterShard.foes === 0 && afterShard.exp === 5,
    JSON.stringify({ high, afterShard }));

  await ev(fresh, "STONE_KNIGHT");
  // Read the knight's shield and thrust at the other height: your shield then sits where its sword is going.
  const duel = await fight("READ");
  const won = await page.waitForFunction(() => window.daedalusRealm.hero.data.exp >= 55, null, { timeout: 5000 }).then(() => true, () => false);
  const levelUp = await ev(() => ({ shown: getComputedStyle(document.getElementById("levelUp")).display,
    life: !document.querySelector('#levelUp button[data-stat="LIFE"]').disabled, magic: !document.querySelector('#levelUp button[data-stat="MAGIC"]').disabled,
    exp: window.daedalusRealm.hero.data.exp }));
  check("reading the stone knight's moving shield wins the duel; 55 EXP opens LEVEL UP with only Life affordable",
    won && duel.includes("HIT") && levelUp.shown === "block" && levelUp.life && !levelUp.magic,
    JSON.stringify({ duel, levelUp }));
  await page.screenshot({ path: path.join(OUT, "realm_level_up.png") });
  await page.click('#levelUp button[data-stat="LIFE"]');
  const raised = await page.waitForFunction(() => window.daedalusRealm.hero.data.life === 2, null, { timeout: 5000 }).then(() => true, () => false);
  const after = await ev(() => ({ exp: window.daedalusRealm.hero.data.exp, hearts: document.querySelector("#heroHud .hearts").textContent,
    shown: getComputedStyle(document.getElementById("levelUp")).display }));
  check("choosing Life: Life 2, a fourth heart, EXP back to zero (Zelda II)", raised && after.exp === 0 && after.hearts === "♥♥♥♥"
    && after.shown === "none", JSON.stringify(after));

  await ev(fresh, "SHARDBACK");
  const blocked = await page.waitForFunction(() => window.daedalusRealm.lastBlock && window.daedalusRealm.lastBlock.foe === "SHARDBACK",
    null, { timeout: 8000 }).then(() => true, () => false);
  await ev(() => window.daedalusRealm.clearFoes());
  const p0 = await ev(() => window.daedalusRealm.avatar.pos.toArray());
  await ev(fresh, "BLIGHT_SLIME");
  const hurt = await page.waitForFunction(() => window.daedalusRealm.lastHurt && window.daedalusRealm.lastHurt.foe === "BLIGHT_SLIME",
    null, { timeout: 8000 }).then(() => true, () => false);
  await page.waitForFunction(() => window.daedalusRealm.hero.knock.length() < 0.2, null, { timeout: 8000 }).catch(() => {});
  const struck = await ev(() => ({ hurt: window.daedalusRealm.lastHurt, p: window.daedalusRealm.avatar.pos.toArray(),
    hearts: document.querySelector("#heroHud .hearts").textContent }));
  const pushed = Math.hypot(struck.p[0] - p0[0], struck.p[2] - p0[2]);
  check("standing, the shield stops a shardback's high bite; a slime's low blow gets under it and knocks you back",
    blocked && hurt && struck.hurt.height === "LOW" && pushed > 1 && struck.hurt.hp < 8 && struck.hearts !== "♥♥♥♥",
    JSON.stringify(Object.assign({ blocked, pushed }, struck)));

  await ev(() => window.daedalusRealm.clearFoes());
  await ev(fresh, "DUST_WISP");
  await sleep(300);
  // One crouching thrust at the wisp, counted only if it met the wisp; then stand and beat it.
  let lowWisp = { outcome: "NONE" };
  for (let tries = 0; tries < 20 && lowWisp.foe !== "DUST_WISP"; tries++) {
    const before = await ev(() => { const r = window.daedalusRealm, f = r.foes[0];
      r.avatar.yaw = Math.atan2(-(f.pos.x - r.avatar.pos.x), -(f.pos.z - r.avatar.pos.z));
      r.heroAct.crouch(true); const n = r.thrusts || 0; r.heroAct.thrust(); return n; });
    await page.waitForFunction(() => window.daedalusRealm.hero.recover <= 0, null, { timeout: 5000 }).catch(() => {});
    const t = await ev(() => window.daedalusRealm.lastThrust || {});
    if (t.n > before) lowWisp = t;
  }
  await fight("HIGH");
  await page.waitForFunction(() => window.daedalusRealm.hero.data.exp === 3, null, { timeout: 5000 }).catch(() => {});
  const wispExp = await ev(() => window.daedalusRealm.hero.data.exp);
  await ev(() => { window.daedalusRealm.hero.hp = 1; });
  await ev(fresh, "BLIGHT_SLIME");
  await ev(() => { window.daedalusRealm.hero.hp = 1; });
  const fell = await page.waitForFunction(() => window.daedalusRealm.lastFall, null, { timeout: 10000 }).then(() => true, () => false);
  await page.waitForFunction(() => window.daedalusRealm.hero.data.exp === 0, null, { timeout: 5000 }).catch(() => {});
  const server = await (await fetch(BASE + "/api/v1/hero?actorId=" + heroName)).json();
  check("a wisp floats past a low thrust and falls to a high one (+3); a fall then costs that EXP, not the Life level",
    lowWisp.outcome === "OUT_OF_REACH" && wispExp === 3 && fell && server.exp === 0 && server.life === 2 && server.beaten === 3,
    JSON.stringify({ lowWisp, wispExp, server }));
  // Home is safe by day: on an island you hold, nothing comes for you until eight in the evening.
  await ev(() => window.daedalusRealm.clearFoes());
  // A home of the hero's own: a new island, claimed.
  const raisedHome = await (await fetch(`${BASE}/api/v1/world/world-zero/islands`, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ seed: 77 }) })).json();
  const slot = raisedHome.island.slot;
  await fetch(`${BASE}/api/v1/world/world-zero/islands/${slot}/claim`, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actorId: heroName }) });
  await page.waitForFunction(([s, n]) => (window.daedalusRealm.islands.find(i => i.slot === s) || {}).owner === n, [slot, heroName],
    { timeout: 15000 }).catch(() => {});
  const isle = await ev(s => window.daedalusRealm.islands.find(i => i.slot === s), slot);
  const home = await ev(i => { const r = window.daedalusRealm; const at = [i.x + 3, i.z + 3];
    r.clockHour = 14; const noon = r.encounterAllowed(...at);
    r.clockHour = 23; const night = r.encounterAllowed(...at);
    r.clockHour = 14; const away = r.encounterAllowed(i.x + 200, i.z);
    r.clockHour = undefined; return { noon, night, away }; }, isle);
  check("no random attacks on your own island by day; they come at night, and anywhere that is not home",
    !home.noon && home.night && home.away, JSON.stringify(home));
  await page.screenshot({ path: path.join(OUT, "realm_fight.png") });
  check("no console errors in the fight", cleanErrors(errors).length === 0, cleanErrors(errors).slice(0, 3).join(" | "));
  await page.close();
}

// --- Gallery City (ADR-035): the Cryptovoxels look. Streets with names, galleries of maze art; tap a frame
// to see it close up; claim a parcel by tapping it, build a wall, and hang your own art on it.
{
  const page = await context.newPage();
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("response", r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(BASE + "/realm.html");
  await page.waitForFunction(() => window.daedalusRealm && window.daedalusRealm.live, null, { timeout: 30000 });
  await page.fill("#newWorldName", "Origin City");
  await page.fill("#newWorldSeed", "3");
  await page.selectOption("#newWorldStyle", "GALLERY");
  await Promise.all([page.waitForURL(/realm\.html\?world=origin-city/, { timeout: 30000 }), page.click("#newWorldGo")]);
  await page.bringToFront();
  await page.waitForFunction(() => { const s = window.daedalusRealm;
    return s && s.live && s.gallery && s.art && s.art.length > 0 && s.artModels.size === s.art.length && s.arkModels.size === 1; },
  null, { timeout: 40000 });
  await page.waitForFunction(() => [...window.daedalusRealm.artModels.values()].every(m => m.children[0].material.map.image
    && m.children[0].material.map.image.width === 256), null, { timeout: 30000 }).catch(() => {});
  const look = await page.evaluate(() => {
    const s = window.daedalusRealm;
    return { lane: document.getElementById("laneTitle").textContent, frames: s.art.length,
      loaded: [...s.artModels.values()].filter(m => m.children[0].material.map.image && m.children[0].material.map.image.width === 256).length,
      parcels: s.gallery.parcels.length, streets: s.gallery.streets.length, drone: s.arks[0].id,
      rotors: !!s.arkModels.get("drone-0").getObjectByName("rotor3"), pad: s.nameAt(s.gallery.padX - 3, 0, s.gallery.padZ),
      palette: document.querySelector(".swatch").title.split(" ")[0] };
  });
  const served = (await (await fetch(BASE + "/api/v1/world/origin-city/art")).json()).art.length;
  check("a Gallery City is born with named streets, parcels, galleries of maze art on the walls, and a drone",
    look.lane === "PARCELS" && look.frames > 20 && look.frames === served && look.loaded === look.frames && look.parcels === 68
      && look.streets === 12 && look.drone === "drone-0" && look.rotors && look.pad === "HELIPAD" && look.palette === "BRICK_WHITE",
    JSON.stringify(Object.assign({ served }, look)));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(OUT, "realm_gallery.png") });

  const first = await page.evaluate(() => {
    const s = window.daedalusRealm, a = s.art[0], c = s.artModels.get(a.id).position;
    const off = { SOUTH: [0, 0, 1], NORTH: [0, 0, -1], EAST: [1, 0, 0], WEST: [-1, 0, 0] }[a.facing];
    s.lookAt(c.x, c.y, c.z, off);
    return { a, c: [c.x, c.y, c.z] };
  });
  await page.bringToFront();
  let viewed = false;
  for (let tries = 0; tries < 3 && !viewed; tries++) {
    await page.waitForTimeout(900);
    const sp = await page.evaluate(c => window.daedalusRealm.project(c[0], c[1], c[2]), first.c);
    await page.mouse.click(sp.x, sp.y);
    viewed = await page.waitForFunction(() => window.daedalusRealm.viewing, null, { timeout: 3000 }).then(() => true, () => false);
  }
  const v = await page.evaluate(() => ({ title: document.querySelector("#viewer .v-title").textContent,
    img: document.querySelector("#viewer img").getAttribute("src"), down: getComputedStyle(document.querySelector("#viewer .v-down")).display }));
  check("tapping a frame opens it close up: title, generator, seed, and no Take down on the gallery's own",
    viewed && v.title === first.a.title && v.img === first.a.image && v.down === "none", JSON.stringify(v));
  await page.screenshot({ path: path.join(OUT, "realm_art_viewer.png") });
  await page.click("#viewerClose");

  await page.fill("#me", "dora");
  await page.dispatchEvent("#me", "change");
  const target = await page.evaluate(() => {
    const s = window.daedalusRealm, p = s.gallery.parcels.find(q => !q.gallery && !q.owner);
    const cx = (p.minX + p.maxX + 1) / 2, cz = (p.minZ + p.maxZ + 1) / 2;
    return { n: p.n, cx, cz, minX: p.minX, minZ: p.minZ };
  });
  // A tap is a quick press that does not move; on a busy run a slow frame can make it read as a drag, so
  // the harness taps again (as a person would) until the panel shows the parcel, up to three times.
  await page.bringToFront();
  for (let tries = 0; tries < 3; tries++) {
    await page.evaluate(t => { const s = window.daedalusRealm; s.lookFrom(t.cx, 0.5, t.cz, t.cx, 22, t.cz + 14); }, target);
    await page.waitForTimeout(800);
    const gp = await page.evaluate(t => window.daedalusRealm.project(t.cx + 0.5, 1.0, t.cz + 0.5), target);
    await page.mouse.click(gp.x, gp.y);
    const ok = await page.waitForFunction(n => window.daedalusRealm.parcelSlot === n, target.n, { timeout: 3000 }).then(() => true, () => false);
    if (ok) break;
  }
  await page.waitForSelector(`#islands .owner[data-slot="${target.n}"] button.claim`, { timeout: 5000 }).catch(() => {});
  await page.click(`#islands .owner[data-slot="${target.n}"] button.claim`).catch(() => {});
  const mine = await page.waitForFunction(n => { const p = window.daedalusRealm.gallery.parcels.find(q => q.n === n); return p && p.owner === "dora"; },
    target.n, { timeout: 10000 }).then(() => true, () => false);
  check("tapping the ground picks a parcel, and Claim makes it dora's", mine,
    JSON.stringify({ picked: await page.evaluate(() => window.daedalusRealm.parcelSlot), want: target.n }));

  await page.evaluate(async t => {
    const s = window.daedalusRealm;
    for (let x = t.minX + 2; x < t.minX + 6; x++) for (let y = 1; y <= 3; y++) await s.writeBlock(x, y, t.minZ + 2, "BRICK_WHITE");
  }, target);
  await page.waitForSelector("#artSeed", { timeout: 5000 });
  await page.fill("#artSeed", "77");
  await page.selectOption("#artSize", "3x2");
  await page.fill("#artTitle", "Dora's Maze");
  await page.click(".hang-form button.hang");
  const wall = { x: target.minX + 3, y: 2, z: target.minZ + 2 };
  await page.evaluate(w => window.daedalusRealm.lookAt(w.x + 0.5, w.y + 0.5, w.z + 1, [0, 0, 1]), wall);
  await page.waitForTimeout(700);
  const wp = await page.evaluate(w => window.daedalusRealm.project(w.x + 0.5, w.y + 0.5, w.z + 1.001), wall);
  await page.mouse.click(wp.x, wp.y);
  const hung = await page.waitForFunction(() => (window.daedalusRealm.art || []).some(a => a.owner === "dora"), null, { timeout: 10000 })
    .then(() => true, () => false);
  const mineArt = await page.evaluate(() => window.daedalusRealm.art.find(a => a.owner === "dora"));
  const servedMine = (await (await fetch(BASE + "/api/v1/world/origin-city/art")).json()).art.find(a => a.owner === "dora");
  check("Hang art, then a tap on dora's wall, hangs seed 77 there for everyone",
    hung && mineArt && mineArt.seed === 77 && mineArt.title === "Dora's Maze" && mineArt.facing === "SOUTH" && servedMine
      && servedMine.id === mineArt.id && mineArt.w === 3 && mineArt.h === 2,
    JSON.stringify({ mineArt, lastHang: await page.evaluate(() => window.daedalusRealm.lastHang) }));
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(OUT, "realm_hung_art.png") });
  check("no console errors in Gallery City", cleanErrors(errors).length === 0, cleanErrors(errors).slice(0, 3).join(" | "));
  await page.close();
}

// --- Reload: a fresh page rebuilds the same world from REST alone, and sends no ship anywhere.
const voyagesBefore = (await (await fetch(BASE + "/api/v1/world/world-zero/arks")).json()).arks.map(a => `${a.id}:${a.departAt}`).join(",");
const isleCount = (await (await fetch(BASE + "/api/v1/world/world-zero/islands")).json()).islands.length;
const C = await open("C");
await C.page.waitForFunction(n => window.daedalusRealm.islands.length === n, isleCount, { timeout: 30000 });
check("a fresh page rebuilds the same world", (await cubes(C.page)) === (await serverCubes()));
await C.page.waitForFunction(n => window.daedalusRealm.arks.length === n, isleCount, { timeout: 15000 });
const serverArks = (await (await fetch(BASE + "/api/v1/world/world-zero/arks")).json()).arks.map(a => `${a.id}@${a.slot}`).join(",");
const pageArks = await C.page.evaluate(() => window.daedalusRealm.arks.map(a => `${a.id}@${a.slot}`).join(","));
check("a fresh page knows where every ark is", pageArks === serverArks, `${pageArks} / server ${serverArks}`);
await C.page.waitForTimeout(2000);
const voyagesAfter = (await (await fetch(BASE + "/api/v1/world/world-zero/arks")).json()).arks.map(a => `${a.id}:${a.departAt}`).join(",");
// An ark already under way may tie up meanwhile (departAt back to 0); none may set out (a new departAt).
const before = Object.fromEntries(voyagesBefore.split(",").map(v => v.split(":")));
const setOut = voyagesAfter.split(",").map(v => v.split(":")).filter(([id, t]) => t !== "0" && t !== before[id]);
check("opening a page hails no ark (only a page that came through a gate does)", setOut.length === 0,
  `${voyagesBefore} → ${voyagesAfter}`);

for (const p of [A, B, C, D, ...(W ? [W] : [])]) check(`no console errors on page ${p.name}`, cleanErrors(p.errors).length === 0, cleanErrors(p.errors).slice(0, 3).join(" | "));
console.log(httpErrors.length ? `HTTP errors seen: ${[...new Set(httpErrors)].join(" | ")}` : "HTTP errors seen: none");
await browser.close();
console.log(failures.length ? `\n${failures.length} FAILED` : "\nALL PASS");
process.exit(failures.length ? 1 : 0);
