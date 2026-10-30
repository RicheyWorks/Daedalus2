// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/angler_guide_test.js
// Actual fishing/menu/item/request/dialog/clock/status functions and canonical fish/Windmere data.
// Fake paint/audio/storage peers. Synthetic HUD-threshold geometry and Portal fallback are labeled below.
// No browser/devices/assets/native storage/build/full-IIFE execution or runtime acceptance.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const fish = data("prism-fish").fish, village = data("prism-village"), parties = data("party").party, interiors = data("interiors").interiors, menus = data("menus").layouts;
const townTiles = Object.fromEntries(data("town-tiles").tiles.filter(t => t.realm === "prism").map(t => [t.tile, t]));
const spells = data("spells").spells, dirs = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [between("const LOGICAL =", "const KEYMAP ="), between("const hit =", "/* ---------- controllers:"), line("const CHARS ="), line("const tw ="), line("const T ="),
  between("function gauge(", "/* ---------- party ---------- */"), between("const START_LEVEL =", "/* ---------- maps"),
  between("const STEP_MIN =", "function dark("), line("const DIRS ="), line("const at ="), line("const npcAt ="), line("const VOICE ="),
  between("function villageMap()", "function interiorMap("), between("function interact()", "function innPrompt("),
  between("let dlg = null;", "function drawDialog("), between("let fishing = null;", "/* ---------- field menu ---------- */"),
  between("let menu = null;", "function drawEquip("), between("const STATUS =", "/* ---------- bestiary:"),
  between("function spellHint(", "function drawBattle("), between("function titlePrompt(", "function drawTitle("),
  "function cleanup(now){\n" + cleanup + "\n}",
  "this.api={start:()=>{party=buildParty();},villageMap,interact,castLine,pickFish,fishTick,endFish,drawFish,drawFishLog,drawFishingHUD," +
  "anglerGuideTick,fishFeedingHint,openMenu,closeMenu,menuTick,villageRequest,dialogTick,useItem,fieldItems,cleanup," +
  "fishing:()=>fishing,menu:()=>menu,dialog:()=>dlg,party:()=>party,bag:()=>bag,gold:()=>gold,chars:CHARS," +
  "inputs:()=>({pressed,pressedAt,held,SRC}),resources:()=>({party,reserve,bag,gold,state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},opened:Array.from(opened),map,P,D})," +
  "view:()=>({mode,fishing,menu,dlg,pressed,pressedAt,held,SRC,fade,now})};"
].join("\n");
function shore() {
  const tile = (x, y) => village.grid[y] && village.grid[y][x], npc = (x, y) => village.npcs.some(n => n.x === x && n.y === y);
  for (let y = 0; y < village.grid.length; y++) for (let x = 0; x < village.grid[y].length; x++) {
    if (!(townTiles[tile(x, y)] || {}).walkable || npc(x, y)) continue;
    for (const [dir, [dx, dy]] of Object.entries(dirs)) if (tile(x + dx, y + dy) === "Water" && !npc(x + dx, y + dy)) return { x, y, dir, tx: x + dx, ty: y + dy };
  }
  throw new Error("canonical Windmere must have a usable fresh-water shore");
}
const shoreline = shore();
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], sounds = [], notices = [], rolls = [], counters = { rng: 0, storage: 0 }, gear = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors[r])) for (const it of shop.stock || []) if (it.effect || it.attack != null || it.defence != null) gear[it.name] = clone(it);
  for (const f of fish) gear[f.name] = { name: f.name, effect: f.effect, price: f.price, fish: true };
  const math = Object.create(Math); math.random = () => { assert.ok(rolls.length, "reading/painting must not draw random values"); counters.rng++; return rolls.shift(); };
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, fish: clone(fish), village: clone(village), town_tiles: clone(townTiles), menus: clone(menus[realm]), rects: { sprites: {} }, spells: clone(spells.filter(s => s.realm === realm)), ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, Math: math, now: 0, mode: "field", map: null, B: null, PAD: null, fade: 0, fadeCb: null, opened: new Set(),
    P: { x: shoreline.x, y: shoreline.y, fx: shoreline.x * 16, fy: shoreline.y * 16, dir: shoreline.dir, moving: 0, step: 0 },
    state: { beaten: new Set(), ways: new Set(), fish: {}, quests: {}, seen: {}, air: null, returnTo: null, day: 1, minute: 600, steps: 0, sinceBattle: 0 },
    performance: { now: () => c.now }, clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), sfx: x => sounds.push(x), toast: (...args) => notices.push(args),
    flying: () => false, drawField: () => paints.push({ kind: "field" }), spr() {}, shardCount: () => 0,
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    cursor: (x, y) => paints.push({ kind: "cursor", x, y }), win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }),
    g: { fillStyle: "", strokeStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); }, beginPath() {}, moveTo(x, y) { paints.push({ kind: "move", x, y }); }, lineTo(x, y) { paints.push({ kind: "line", x, y }); }, stroke() {}, ellipse(...args) { paints.push({ kind: "ellipse", args }); } },
    localStorage: { getItem() { counters.storage++; throw new Error("angler UI must not read native saves"); }, setItem() { counters.storage++; throw new Error("angler UI must not write native saves"); }, removeItem() { counters.storage++; throw new Error("angler UI must not erase saves"); } },
    saveGame() { counters.storage++; throw new Error("angler UI must not autosave"); }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start(); c.map = c.api.villageMap();
  const resources = () => JSON.stringify(c.api.resources());
  return { c, api: c.api, paints, sounds, notices, counters, rolls, resources,
    roll(...values) { values.forEach(n => assert.ok(n >= 0 && n < 1)); rolls.push(...values); },
    tick(keys = [], dt = 0) { c.now += dt * 1000; for (const key of keys) { c.api.inputs().pressed[key] = true; c.api.inputs().pressedAt[key] = c.now; }
      if (c.api.dialog()) c.api.dialogTick(dt); else if (c.mode === "fish") c.api.fishTick(dt); else if (c.mode === "menu") c.api.menuTick(); c.api.cleanup(c.now); },
    draw(method = "drawFishLog") { paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), effects = JSON.stringify({ counters, rolls, sounds, notices }); c.api[method]();
      assert.equal(resources(), before); assert.equal(JSON.stringify(c.api.view()), view, "painting cannot advance time, consume an edge or change selection/fishing");
      assert.equal(JSON.stringify({ counters, rolls, sounds, notices }), effects, "painting cannot reward, spend, save, roll RNG or emit effects"); return paints; },
    labels(confirm = "ABCDEFGH", cancel = "IJKLMNOP") { c.PAD = { devices: () => [{ index: 0 }], label: action => action === "confirm" ? confirm : cancel }; }
  };
}
const at = (s, y, x) => s.paints.filter(p => p.kind === "text" && p.y === y && (x === undefined || p.x === x));
function bounds(s) { for (const p of s.paints.filter(p => ["text", "rect", "window"].includes(p.kind))) {
  assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p));
  if (p.kind === "text") assert.ok([...p.label].every(k => s.api.chars.includes(k)), p.label);
} }
function guide(s) { s.api.openMenu(); for (let i = 0; i < 6; i++) s.tick(["down"]); s.tick(["a"]); assert.equal(s.api.menu().sub, "fish"); return s; }
function species(s, index) { for (let n = 0; s.api.menu().ii !== index && n < fish.length; n++) s.tick(["down"]); assert.equal(s.api.menu().ii, index); }
function midRoll(s, index) { const night = s.c.state.minute >= 1080 || s.c.state.minute < 300, weights = fish.map(f => night ? f.night_weight || f.weight : f.weight); return (weights.slice(0, index).reduce((a, n) => a + n, 0) + weights[index] / 2) / weights.reduce((a, n) => a + n, 0); }
function cast(s) { s.roll(0.5); s.api.interact(); assert.equal(s.c.mode, "fish"); assert.equal(s.api.fishing().phase, "wait"); assert.equal(s.api.fishing().wait, 2.4); assert.equal(s.c.map.grid[shoreline.ty][shoreline.tx], "Water"); return s; }
function bite(s, index = 0) { s.roll(midRoll(s, index)); s.tick([], s.api.fishing().wait); assert.equal(s.api.fishing().phase, "bite"); assert.equal(s.api.fishing().fish.name, fish[index].name); }
function caught(s, index = 0) { cast(s); bite(s, index); s.tick(["a"]); assert.equal(s.api.fishing().phase, "done"); return s; }
function leave(s) { s.tick([], 0.31); s.tick(["b"]); assert.equal(s.c.mode, "field"); assert.equal(s.api.fishing(), null); }
function finishDialog(s) { for (let n = 0; s.api.dialog() && n < 6; n++) { s.tick([], 5); s.tick(["a"]); } assert.equal(s.api.dialog(), null); }
function hudTop(s) { const panel = s.paints.find(p => p.kind === "rect" && p.x === 4 && p.w === s.c.W - 8 && p.h === 54); assert.ok(panel); return panel.y; }
check("uncaught species keep names/notes secret even when a disposable pack holds that fish", () => {
  const s = guide(session()); s.api.bag()[fish[3].name] = 2;
  for (let i = 0; i < fish.length; i++) { species(s, i); s.draw(); const labels = s.paints.filter(p => p.kind === "text").map(p => p.label);
    for (const f of fish) { assert.ok(!labels.includes(f.name.toUpperCase())); assert.ok(!labels.some(l => l.includes(f.note.slice(0, 12).toUpperCase()))); }
    assert.equal(labels.filter(l => l === "???").length, 6); assert.ok(labels.includes("NOT CAUGHT YET.")); assert.ok(labels.includes("KNOWN 0/6"));
  }
});
check("real catches, eating and the actual carp-request choice retain lifetime count while pack count falls", () => {
  const s = session(), index = fish.findIndex(f => f.name === "Sunscale Carp"), name = fish[index].name; caught(s, index); leave(s); caught(s, index); leave(s);
  assert.equal(s.c.state.fish[name], 2); assert.equal(s.api.bag()[name], 2); s.api.party()[0].hp = 1; s.api.openMenu(); s.tick(["a"]);
  const ii = s.api.fieldItems().indexOf(name); assert.ok(ii >= 0); for (let n = 0; s.api.menu().ii !== ii && n < s.api.fieldItems().length; n++) s.tick(["down"]); s.tick(["a"]);
  assert.equal(s.api.bag()[name], 1); assert.equal(s.c.state.fish[name], 2); s.api.closeMenu();
  // Call the real request handler and real dialog choice; no pathfinding/NPC traversal claim.
  const elder = clone(village.npcs.find(n => n.request)); assert.equal(elder.request.item, name); const gold = s.api.gold(); s.api.villageRequest(elder); assert.ok(s.api.dialog().choice); s.tick([], 5); s.tick(["a"]); finishDialog(s);
  assert.equal(s.api.gold(), gold + elder.request.gold); assert.equal(s.api.bag()[name], 0); assert.equal(s.c.state.fish[name], 2); s.api.villageRequest(elder); finishDialog(s); assert.equal(s.api.gold(), gold + elder.request.gold);
  guide(s); species(s, index); s.draw(); const row = at(s, 58 + index * 14); assert.ok(row.some(p => p.label === name.toUpperCase())); assert.ok(row.some(p => p.label === "2" && p.x < 300)); assert.ok(row.some(p => p.label === "0" && p.x >= 300));
});
check("canonical feeding advice matches normalized day/dusk/night sampler choices, including unchanged-weight common fish", () => {
  const s = session(), expected = ["DAYLIGHT", "DAYLIGHT", "DAYLIGHT", "DUSK/NIGHT", "DUSK/NIGHT", "DUSK/NIGHT"];
  for (let i = 0; i < fish.length; i++) assert.equal(s.api.fishFeedingHint(s.c.D.fish[i]), (i < 3 ? "MORE LIKELY IN " : "MORE LIKELY AT ") + expected[i] + ".");
  // One midpoint in each real authored interval proves both clock phases select the advertised table.
  for (const minute of [600, 1140, 1320]) { s.c.state.minute = minute; for (let i = 0; i < fish.length; i++) { s.roll(midRoll(s, i)); assert.equal(s.api.pickFish().name, fish[i].name); } }
  assert.equal(s.counters.rng, 18); assert.equal(s.rolls.length, 0);
});
check("help toggles once, ignores species arrows while open, and closes/drains concurrent edges before a fresh open", () => {
  const s = guide(session()); species(s, 4); s.tick(["left", "right", "up", "down"]); assert.equal(s.api.menu().fishHelp, true); assert.equal(s.api.menu().ii, 4);
  s.tick(["up", "down"]); assert.equal(s.api.menu().ii, 4); s.tick(["right"]); assert.equal(s.api.menu().fishHelp, false); assert.equal(s.api.menu().ii, 4);
  s.tick(["a", "b", "left", "right", "up", "down"]); assert.equal(s.api.menu().sub, null); for (const key of ["a", "b", "left", "right", "up", "down"]) assert.equal(!!s.api.inputs().pressed[key], false);
  s.tick(); assert.equal(s.api.menu().sub, null); s.tick(["a"]); assert.equal(s.api.menu().sub, "fish"); assert.equal(s.api.menu().fishHelp, false); assert.equal(s.api.menu().ii, 0);
});
for (const width of [320, 256]) check("guide species/notes/large counters/help/font/mapped controls remain bounded and pure at " + width, () => {
  const s = guide(session(width)); s.labels(); for (const f of fish) { s.c.state.fish[f.name] = Number.MAX_SAFE_INTEGER; s.api.bag()[f.name] = Number.MAX_SAFE_INTEGER; }
  for (let i = 0; i < fish.length; i++) { species(s, i); s.draw(); bounds(s); assert.ok(at(s, 10).some(p => p.label === "KNOWN 6/6")); const cap = width < 320 ? "99+" : "9999+";
    assert.equal(at(s, 58 + i * 14).filter(p => p.label === cap).length, 2); assert.ok(at(s, 190, 12)[0].label.includes(i < 3 ? "DAYLIGHT" : "DUSK/NIGHT")); assert.ok(!s.paints.some(p => p.kind === "text" && p.label.includes(";")));
  }
  s.tick(["right"]); s.draw(); bounds(s); assert.ok(at(s, 140, 12)[0].label.includes("ABCDEFGH")); assert.equal(at(s, 212, 12)[0].label, "LEFT/RIGHT: LOG IJKLMNOP: BACK");
  const before = JSON.stringify(s.paints); s.draw(); assert.equal(JSON.stringify(s.paints), before);
});
check("actual new/repeat catches award once and the done delay/transition retain the existing resources and clock", () => {
  const s = session(), name = fish[0].name, clock = [s.c.state.day, s.c.state.minute]; caught(s); assert.ok(s.api.fishing().msg.startsWith("NEW!")); assert.equal(s.api.bag()[name], 1); assert.equal(s.c.state.fish[name], 1);
  s.tick(["b"], 0.05); assert.equal(s.c.mode, "fish"); s.tick([], 0.2); s.tick([], 0.1); assert.equal(s.c.mode, "fish", "expired early Back cannot dismiss later");
  const before = s.resources(); s.tick(["a", "b", "start"]); assert.equal(s.c.mode, "field"); assert.equal(s.resources(), before); for (const k of ["a", "b", "start"]) assert.equal(!!s.api.inputs().pressed[k], false);
  caught(s); assert.ok(!s.api.fishing().msg.startsWith("NEW!")); assert.equal(s.api.bag()[name], 2); assert.equal(s.c.state.fish[name], 2); s.draw("drawFish"); assert.equal(at(s, hudTop(s) + 8, 12)[0].label, "CAUGHT REEDLING!");
  leave(s); assert.deepEqual([s.c.state.day, s.c.state.minute], clock); assert.equal(s.counters.rng, 4); assert.equal(s.counters.storage, 0);
});
check("early, exact-window, missed and simultaneous strike/cancel priorities stay in the actual fishTick", () => {
  const early = cast(session()), before = early.resources(); early.tick(["a"]); assert.match(early.api.fishing().msg, /TOO SOON/); assert.equal(early.resources(), before); assert.equal(early.counters.rng, 1);
  const missed = cast(session()); bite(missed, 5); const window = missed.api.fishing().fish.window_s; missed.tick([], window); assert.equal(missed.api.fishing().phase, "bite"); missed.tick([], 0.01); assert.match(missed.api.fishing().msg, /GOT AWAY/); assert.equal(missed.c.state.fish[fish[5].name], undefined);
  const cancelled = cast(session()); bite(cancelled); const saved = cancelled.resources(); cancelled.tick(["a", "b", "start"]); assert.equal(cancelled.c.mode, "field"); assert.equal(cancelled.resources(), saved);
  // Preserve the existing strike-before-expiry branch; this is a parity check, not a timing-rule change.
  const strike = cast(session()); bite(strike, 5); strike.tick(["a"], strike.api.fishing().fish.window_s + 0.01); assert.equal(strike.api.fishing().phase, "done"); assert.equal(strike.c.state.fish[fish[5].name], 1);
});
for (const width of [320, 256]) check("real wait/bite/success/miss HUD controls and remaining-window gauge fit at " + width, () => {
  const s = cast(session(width)); s.labels(); s.draw("drawFish"); bounds(s); const top = hudTop(s); assert.ok(at(s, top + 40, 12).some(p => p.label === "IJKLMNOP: REEL IN"));
  bite(s, 5); s.tick([], s.api.fishing().fish.window_s / 2); s.draw("drawFish"); bounds(s); assert.equal(hudTop(s), top); assert.equal(at(s, top + 8, 12)[0].label, "BITE! ABCDEFGH: STRIKE");
  const fill = s.paints.find(p => p.kind === "rect" && p.x === 13 && p.y === top + 41 && p.color === "#58b898"); assert.ok(fill); assert.equal(fill.w, Math.round((width - 26) / 2));
  s.tick(["a"]); s.api.bag()[fish[5].name] = Number.MAX_SAFE_INTEGER; s.draw("drawFish"); bounds(s); assert.ok(at(s, top + 8, 12)[0].label.startsWith("NEW! CAUGHT PRISMSCALE KOI!")); assert.equal(at(s, top + 20, 12)[0].label, "LEGENDARY / PACK 9999+"); assert.equal(at(s, top + 40, 12)[0].label, "ABCDEFGH/IJKLMNOP: CONTINUE");
  const miss = cast(session(width)); miss.labels(); miss.tick(["a"]); miss.draw("drawFish"); bounds(miss); assert.ok(miss.paints.some(p => p.kind === "text" && p.label.includes("TOO SOON")));
  const late = cast(session(width)); late.labels(); bite(late, 5); late.tick([], late.api.fishing().fish.window_s + 0.01); late.draw("drawFish"); bounds(late); assert.ok(late.paints.some(p => p.kind === "text" && p.label === "IT GOT AWAY."));
});
check("actual canonical shoreline projection is used by drawFish at both widths without drawing-time changes", () => {
  for (const width of [320, 256]) { const s = cast(session(width)), p = s.c.P, grid = s.c.map.grid;
    assert.equal(grid[shoreline.ty][shoreline.tx], "Water"); s.draw("drawFish"); const lineTo = s.paints.find(p => p.kind === "line"), gh = grid.length * 16, oy = gh < 224 ? (224 - gh) / 2 : -Math.max(0, Math.min(p.fy + 8 - 112, gh - 224));
    const base = Math.round(oy + shoreline.ty * 16 + 8); assert.equal(lineTo.y, base - 2); assert.equal(hudTop(s), base >= 152 ? 4 : 166); bounds(s);
  }
});
function stableDip(production = source) {
  for (const base of [151, 152]) { const s = session(256, "prism", production);
    // Explicit synthetic threshold fixture: this camera/room is not an authored Windmere cast location.
    s.c.map = { kind: "village", grid: Array.from({ length: 24 }, () => Array(24).fill("Grass")), npcs: [] }; s.c.P.fx = 128; s.c.P.fy = base === 151 ? 201 : 200; s.roll(0.5); s.api.castLine(8, 15);
    s.draw("drawFish"); const top = hudTop(s); assert.equal(top, base >= 152 ? 4 : 166); s.roll(0.1); s.tick([], s.api.fishing().wait); s.draw("drawFish"); assert.equal(hudTop(s), top, "three-pixel bite dip never selects another panel");
  }
}
check("synthetic threshold geometry proves undipped bobber placement, with a controlled dipped-position failure", () => {
  stableDip(); const dipped = source.replace('return drawFishingHUD(f, Math.round(oy + f.y * T + 8));', 'return drawFishingHUD(f, by);'); assert.notEqual(dipped, source); assert.throws(() => stableDip(dipped), assert.AssertionError);
});
check("Portal guard retains the old log and HUD with a supplied table, without claiming an authored Portal pond", () => {
  const s = guide(session(256, "portal")); s.draw(); assert.ok(at(s, 9, 12).some(p => p.label === "FISH LOG")); assert.ok(!s.paints.some(p => p.kind === "text" && p.label === "FISH GUIDE")); s.tick(["right"]); assert.equal(s.api.menu().fishHelp, undefined);
  s.api.closeMenu(); cast(s); s.draw("drawFish"); assert.ok(s.paints.some(p => p.kind === "window" && p.x === 4 && p.y === 194 && p.h === 26)); assert.ok(!s.paints.some(p => p.kind === "rect" && p.h === 54 && p.x === 4)); assert.ok(at(s, 204, 14)[0].label.includes("A: STRIKE"));
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("angler guide: " + checks + " focused groups passed; fake painters/storage, synthetic threshold and Portal fallback labeled; no runtime acceptance");
