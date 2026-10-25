// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/defeat_recovery_test.js
// Actual defeat/Continue/v1 writer+reader/recruit/Inn/skiff/paint excerpts with canonical catalogs.
// Tiny finished-loss fixture, memory storage, queued timers, cursor/text peers; no battle/route traversal.
// No full IIFE, browser, devices, audible audio, native storage, asset build or runtime acceptance.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Save = require("./journey-save.js"), Ways = require("./waystones.js");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n"), builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, interiors = data("interiors"), town = data("town-tiles"), world = data("worldmap-tiles"), bosses = data("prism-bosses").bosses;
const rawDungeons = data("dungeons").dungeons.prism, ways = data("prism-waystones").waystones;
function tuples(name) { const s = builder.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m")); assert.ok(s, name); return [...s[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g)].map(m => [m[1], m[2]]); }
const quest = tuples("QUEST"), optional = tuples("OPTIONAL_QUEST");
const dungeons = quest.concat(optional).map(([landmark, name], i) => ({ name, landmark, optional: i >= quest.length, final: i === 3, boss_data: clone(bosses.find(b => b.dungeon === name)), floors: clone(rawDungeons.find(d => d.name === name).floors) }));
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const source = [line("const CHARS ="), line("const T ="), line("const hit ="), line("function clearActionButtons()"), line("let journeySerial ="), line("const find ="), line("function airUnlocked()"), line("const flying ="), line("const WAYS ="), line("const follyDungeon ="), line("const follyCleared ="),
  between("const START_LEVEL =", "/* ---------- maps"), between("let footCache =", "/* Sky caches"),
  between("function interiorMap(", "function worldMap()"), between("function goto(", "const find ="),
  between("function finishBattle(", "function bossGate("), between('let SAVE_KEY = "prism.save.v1";', "function beginJourney()"),
  between("function titleTick(", "function drawTitle("), between("function gameOverTick(", "/* ---------- loop ---------- */"),
  "this.api={start:()=>{party=buildParty();},makeMember,recruit,saveGame,readSavedJourney,prepareContinue,titleChoose,titleTick,finishBattle,gameOverTick,drawGameOver,drawDefeatRecovery,chars:CHARS," +
  "party:()=>party,reserve:()=>reserve,bag:()=>bag,gold:()=>gold,setGold:n=>{gold=n;},key:()=>SAVE_KEY,setKey:k=>{SAVE_KEY=k;}," +
  "ui:()=>({goIdx,goT,titleIdx,titleT}),setUI:(index,time=0)=>{goIdx=index;goT=time;},serial:()=>journeySerial," +
  "applyFade:()=>{if(fadeCb){const cb=fadeCb;fadeCb=null;cb();}fade=0;}," +
  "progress:()=>({party,reserve,bag,gold,state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},opened:Array.from(opened),map,P,grids,mode,fade,dlg,shop,menu,B,ending,nameEntry,journeySerial})};"
].join("\n");
let groups = 0;
function check(label, fn) { try { fn(); groups++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], notices = [], sounds = [], pending = [], store = new Map(), pressed = {}, counts = { reads: 0, writes: 0, erases: 0, validates: 0, unlock: 0, rng: 0, settings: 0 }, gear = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors.interiors[r])) for (const it of shop.stock || []) if (it.effect || it.attack != null || it.defence != null) gear[it.name] = clone(it);
  const math = Object.create(Math); math.random = () => { counts.rng++; throw new Error("defeat recovery cannot consume RNG"); };
  const c = { W: width, H: 224, D: { realm_key: realm, party: clone(parties[realm]), gear, dungeons: clone(dungeons), interiors: clone(interiors.interiors[realm]),
      interior_tiles: Object.fromEntries(interiors.tiles.filter(t => t.realm === realm).map(t => [t.tile, clone(t)])), town_tiles: Object.fromEntries(town.tiles.filter(t => t.realm === realm).map(t => [t.tile, clone(t)])),
      world: clone(world.demo_maps[realm]), world_tiles: Object.fromEntries(world.tiles.filter(t => t.realm === realm).map(t => [t.tile, clone(t)])), waystones: clone(ways), frames: {}, ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    state: { beaten: new Set(), seen: {}, fish: {}, quests: {}, ways: new Set(), air: null, steps: 21, sinceBattle: 8, returnTo: { retained: true }, day: 1, minute: 480 }, opened: new Set(), grids: { retained: [1] },
    mode: "field", map: { kind: "world", retained: true }, P: { x: 7, y: 9, fx: 112, fy: 144, moving: 0.4, dir: "left" }, fade: 0, fadeCb: null, B: null, dlg: null, shop: null, menu: null, ending: null, nameEntry: null,
    Math: math, PAD: null, pressed, failReads: false,
    PrismJourneySave: { ...Save, read(...args) { counts.validates++; return Save.read(...args); } }, PrismWaystones: Ways,
    setTimeout(fn, ms) { pending.push({ fn, ms }); return pending.length; }, sfx: s => sounds.push(s), cue() {}, toast: (...args) => notices.push(args), say() {},
    unlockAudio() { counts.unlock++; }, openSettings() { counts.settings++; },
    passTime() { throw new Error("Continue cannot advance game time"); }, wakeAt() { throw new Error("Continue cannot rest/heal the party"); },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: value => String(value).length * 6,
    cursor(x, y) { paints.push({ kind: "cursor", x, y, w: 8, h: 8 }); },
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    g: { fillStyle: "", globalAlpha: 1, fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); } },
    localStorage: { getItem(key) { counts.reads++; if (c.failReads) throw new Error("memory storage unavailable peer"); return store.get(key) ?? null; }, setItem(key, raw) { counts.writes++; store.set(key, raw); }, removeItem() { counts.erases++; throw new Error("recovery must not erase saves"); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start(); c.api.setKey(realm + ".save.v1");
  const progress = () => JSON.stringify(c.api.progress());
  const s = { c, api: c.api, counts, paints, notices, sounds, pending, store, pressed, progress,
    tick(dt = 0, ...keys) { keys.forEach(k => { pressed[k] = true; }); c.api.gameOverTick(dt); },
    draw() { paints.length = 0; const before = progress(), catalogBefore = JSON.stringify(c.D), ui = JSON.stringify(c.api.ui()), bytes = JSON.stringify([...store]), writes = counts.writes, erases = counts.erases, effects = JSON.stringify({ sounds, notices, pending: pending.map(p => p.ms), unlock: counts.unlock, rng: counts.rng, settings: counts.settings }); c.api.drawGameOver(); assert.equal(progress(), before); assert.equal(JSON.stringify(c.D), catalogBefore); assert.equal(JSON.stringify(c.api.ui()), ui, "rendering must not select the recovery option"); assert.equal(JSON.stringify([...store]), bytes); assert.equal(counts.writes, writes); assert.equal(counts.erases, erases); assert.equal(JSON.stringify({ sounds, notices, pending: pending.map(p => p.ms), unlock: counts.unlock, rng: counts.rng, settings: counts.settings }), effects); return paints; },
    labels(confirm = "ABCDEFGH", cancel = "IJKLMNOP", menu = "QRSTUVWX") { c.PAD = { devices: () => [{ index: 0 }], label: a => ({ confirm, cancel, menu })[a] }; }
  };
  return s;
}
function seed(s) {
  const c = s.c, earned = c.D.realm_key === "prism" ? c.D.dungeons.filter(d => !d.final) : [];
  for (const d of earned) { c.state.beaten.add(d.boss_data.name); s.api.recruit(d.name); }
  s.api.party().forEach((m, i) => { m.hp = Math.max(1, m.max - 11 - i); m.mp = Math.max(0, m.mmax - 3 - i); });
  s.api.reserve().forEach(m => { m.hp = Math.max(1, m.max - 7); m.mp = Math.max(0, m.mmax - 1); });
  s.api.bag()["Herb Tonic"] = 3; s.api.setGold(731); c.state.day = 17; c.state.minute = 1199; c.opened.add("journey/pin/Cave");
  if (c.D.realm_key === "prism") { const pad = (() => { for (let y = 0; y < c.D.world.length; y++) { const x = c.D.world[y].indexOf("AirshipPad"); if (x >= 0) return { x, y, aboard: true }; } throw new Error("canonical dock missing"); })(); c.state.air = pad; }
  assert.equal(s.api.saveGame(), true); const raw = s.store.get(s.api.key()), checked = Save.read(raw, c.D.realm_key, c.D.party.members); assert.equal(checked.ok, true); s.counts.writes = 0; return { raw, value: checked.value };
}
function lose(s) { s.api.setUI(1, 27); s.api.party().forEach(m => { m.hp = 0; m.mp = 0; }); s.api.bag()["Herb Tonic"] = 0; s.api.setGold(2); s.c.state.day = 23; s.c.state.minute = 39; s.c.mode = "battle"; s.c.B = { result: "lose", boss: false, foes: [], prevCue: "FIELD", endLines: [] }; s.api.finishBattle(); assert.equal(s.c.mode, "gameover"); assert.equal(s.c.B, null); assert.deepEqual(clone(s.api.ui()), { goIdx: -1, goT: 0, titleIdx: 0, titleT: 0 }); return s; }
function ready(s) { s.tick(1.01); assert.ok(s.api.ui().goT > 1); return s; }
function edges(s) { for (const k of ["a", "b", "start", "up", "down", "left", "right"]) assert.equal(!!s.pressed[k], false, k); }
const texts = (s, y) => s.paints.filter(p => p.kind === "text" && (y === undefined || p.y === y));
function bounds(s) { for (const p of s.paints) { assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p)); if (p.kind === "text") assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), p.label); } }
function assertRestored(s, saved) {
  s.api.applyFade(); assert.equal(s.c.mode, "field"); assert.deepEqual(clone(s.api.party()), saved.value.party); assert.deepEqual(clone(s.api.reserve()), saved.value.reserve); assert.deepEqual(clone(s.api.bag()), saved.value.bag); assert.equal(s.api.gold(), saved.value.gold);
  assert.equal(s.c.state.day, saved.value.day); assert.equal(s.c.state.minute, saved.value.minute); assert.deepEqual([...s.c.state.beaten], saved.value.beaten); assert.deepEqual([...s.c.opened], saved.value.opened); assert.deepEqual(clone(s.c.state.seen), saved.value.seen);
  assert.equal(s.c.map.kind, "interior"); assert.equal(s.c.map.name, "Inn"); assert.equal(s.c.P.x, s.c.D.interiors.Inn.spawn.x); assert.equal(s.c.P.y, s.c.D.interiors.Inn.spawn.y); assert.equal(s.c.P.dir, "up"); assert.equal(s.c.P.moving, 0); if (s.c.state.air) assert.equal(s.c.state.air.aboard, false);
  assert.equal(s.c.state.steps, 0); assert.equal(s.c.state.sinceBattle, 0); assert.equal(s.c.state.returnTo, null); edges(s);
  assert.equal(s.counts.writes, 0); assert.equal(s.counts.erases, 0); assert.equal(s.store.get(s.api.key()), saved.raw); assert.equal(s.c.nameEntry, null);
}
check("a finished defeat resets selection and the entire one-second gate drains every early edge", () => {
  const s = session(); seed(s); lose(s); const before = s.progress(); s.tick(0.5, "a", "b", "start", "up", "down", "left", "right"); edges(s); assert.equal(s.api.ui().goIdx, 0); assert.equal(s.progress(), before);
  s.tick(0.5, "a", "b", "start", "up", "down", "left", "right"); edges(s); assert.equal(s.c.mode, "gameover"); s.tick(0.01); assert.equal(s.c.mode, "gameover"); assert.equal(s.c.fade, 0); assert.equal(s.counts.unlock, 0);
});
check("valid default Continue uses the actual numeric title selection and restores saved wounds without rest/write", () => {
  const s = session(), saved = seed(s); lose(s); ready(s); assert.equal(s.api.ui().goIdx, 0); const cached = s.api.readSavedJourney(); s.tick(0, "a"); assert.equal(s.counts.unlock, 1); assertRestored(s, saved); assert.notEqual(s.api.party(), cached.value.party); assert.notEqual(s.api.party()[0], cached.value.party[0]);
  const hp = cached.value.party[0].hp; s.api.party()[0].hp--; assert.equal(cached.value.party[0].hp, hp); assert.equal(s.store.get(s.api.key()), saved.raw); assert.ok(s.pending.some(p => p.ms === 600), "welcome callback queued, not a timer/game-loop simulation");
});
check("missing save defaults to Title; explicit Continue refuses in place without New Game or erase", () => {
  const s = lose(session()); ready(s); assert.equal(s.api.ui().goIdx, 1); s.tick(0, "up"); assert.equal(s.api.ui().goIdx, 0); const before = s.progress(); s.tick(0, "a"); assert.equal(s.progress(), before); assert.equal(s.c.mode, "gameover"); assert.match(s.notices.at(-1)[0], /No saved journey/); assert.equal(s.counts.unlock, 0); edges(s); s.tick(); assert.equal(s.c.mode, "gameover"); assert.equal(s.counts.writes + s.counts.erases, 0);
  const title = lose(session()); ready(title); title.tick(0, "a"); assert.equal(title.c.mode, "title"); edges(title); title.api.titleTick(0); assert.equal(title.c.fade, 0); assert.equal(title.c.nameEntry, null);
});
check("invalid/unavailable/reader-not-loaded records cannot mutate the lost journey or stored bytes", () => {
  for (const kind of ["invalid", "storage", "reader"]) { const s = session(); seed(s); lose(s); ready(s); if (kind === "invalid") s.store.set(s.api.key(), "{unfinished"); if (kind === "storage") s.c.failReads = true; if (kind === "reader") s.c.PrismJourneySave = undefined;
    const before = s.progress(), bytes = s.store.get(s.api.key()); s.tick(0, "a"); assert.equal(s.progress(), before); assert.equal(s.store.get(s.api.key()), bytes); assert.equal(s.c.mode, "gameover"); assert.equal(s.counts.unlock, 0); assert.equal(s.counts.writes + s.counts.erases, 0); assert.match(s.notices.at(-1)[0], /Continue unavailable/); edges(s); }
});
check("a save changed after the initial offer is revalidated, and a newer valid record is loaded freshly", () => {
  for (const change of ["invalid", "missing", "valid"]) { const s = session(), original = seed(s); lose(s); ready(s); s.draw(); assert.equal(s.api.ui().goIdx, 0);
    const next = clone(original.value); next.party[0].hp = 1; next.party[0].mp = 0; next.gold += 9; next.minute = 622; const raw = change === "valid" ? JSON.stringify(next) : change === "missing" ? null : "{}";
    if (raw === null) s.store.delete(s.api.key()); else s.store.set(s.api.key(), raw); const before = s.progress(); s.tick(0, "a");
    if (change === "valid") assertRestored(s, { raw, value: next }); else { assert.equal(s.progress(), before); assert.equal(s.c.mode, "gameover"); assert.equal(s.store.get(s.api.key()) ?? null, raw); assert.equal(s.counts.unlock, 0); } }
});
check("preparation failure after validation remains detached and keeps Continue retryable", () => {
  const s = session(), saved = seed(s); lose(s); ready(s); const oldInn = s.c.D.interiors.Inn; delete s.c.D.interiors.Inn; const before = s.progress(), serial = s.api.serial(); s.tick(0, "a"); assert.equal(s.progress(), before); assert.equal(s.api.serial(), serial); assert.equal(s.api.ui().goIdx, 0); assert.equal(s.store.get(s.api.key()), saved.raw); assert.match(s.notices.at(-1)[1], /could not prepare/); assert.equal(s.counts.unlock, 0); edges(s);
  s.c.D.interiors.Inn = oldInn; s.tick(); assert.equal(s.c.mode, "gameover"); s.tick(0, "a"); assertRestored(s, saved);
});
check("Back/Start beat simultaneous selection/Confirm and cannot bleed a stale New Game into Title", () => {
  for (const close of [["b"], ["start"], ["b", "start"]]) { const s = session(); seed(s); lose(s); ready(s); s.tick(0, ...close, "a", "up", "down", "left", "right"); assert.equal(s.c.mode, "title"); assert.equal(s.api.ui().titleT, 0); assert.equal(s.c.fade, 0); assert.equal(s.counts.unlock, 0); edges(s); s.api.titleTick(0); assert.equal(s.c.nameEntry, null); assert.equal(s.c.fade, 0); }
  const s = session(); seed(s); lose(s); ready(s); s.tick(0, "up", "down"); assert.equal(s.api.ui().goIdx, 0); s.tick(0, "down"); assert.equal(s.api.ui().goIdx, 1); s.tick(0, "up"); assert.equal(s.api.ui().goIdx, 0);
});
check("first-frame rendering leaves selection untouched and only read-cache identity follows record/data changes", () => {
  const s = session(); seed(s); lose(s); assert.equal(s.api.ui().goIdx, -1); const validates = s.counts.validates; s.draw(); assert.equal(s.api.ui().goIdx, -1); assert.equal(s.counts.validates, validates + 1); const cached = s.api.readSavedJourney(); s.draw(); assert.equal(s.api.readSavedJourney(), cached); assert.equal(s.counts.validates, validates + 1);
  s.c.D = { ...s.c.D }; s.draw(); assert.equal(s.counts.validates, validates + 2); assert.notEqual(s.api.readSavedJourney(), cached); s.draw(); assert.equal(s.counts.validates, validates + 2);
});
for (const width of [320, 256]) check("safe ASCII headings, bounded restored name/level, flat panels and mapped controls fit at " + width, () => {
  const s = session(width); const saved = seed(s), record = clone(saved.value); record.party[0].name = "ß".repeat(64); record.party[0].lv = Number.MAX_SAFE_INTEGER; const raw = JSON.stringify(record); assert.equal(Save.read(raw, "prism", s.c.D.party.members).ok, true); s.store.set(s.api.key(), raw); lose(s); s.labels();
  s.draw(); bounds(s); assert.equal(s.api.ui().goIdx, -1); assert.ok(texts(s, 188).some(p => p.label === "A MOMENT...")); assert.ok(!s.paints.some(p => p.kind === "cursor")); assert.ok(texts(s, 70)[0].label.startsWith("SAVED: SS")); assert.ok(texts(s, 70)[0].label.endsWith(" LV 999+"));
  ready(s); s.draw(); bounds(s); const confirm = texts(s, 212).find(p => p.label === "ABCDEFGH: OK"), title = texts(s, 212).find(p => p.label === "IJKLMNOP/QRSTUVWX: TITLE"); assert.ok(confirm && title); assert.ok(confirm.x + confirm.w < title.x); assert.ok(s.paints.some(p => p.kind === "cursor" && p.y === 126)); assert.ok(texts(s, 196).some(p => p.label === "STARTS ON FOOT AT THE INN."));
  const header = s.paints.find(p => p.kind === "rect" && p.y === 39 && p.h === 1), footer = s.paints.find(p => p.kind === "rect" && p.y === 175 && p.h === 1); assert.ok(header && footer); for (const p of texts(s).filter(p => p.y > 39 && p.y < 175)) assert.ok(p.y + p.h < footer.y);
  s.labels("INVALID LABEL", "<BAD>", "TOO LONG LABEL"); s.draw(); bounds(s); assert.ok(texts(s, 212).some(p => p.label === "Z/SPACE: OK")); assert.ok(texts(s, 212).some(p => p.label === "X/ESC/ENTER: TITLE"));
});
check("Portal retains its original early buffering, return-only paint and no save lookup", () => {
  const s = lose(session(256, "portal")); const reads = s.counts.reads; s.tick(0.5, "a"); assert.equal(s.pressed.a, true); assert.equal(s.api.ui().goIdx, -1); s.draw(); bounds(s); assert.deepEqual(texts(s).map(p => p.label), ["THE HEART GOES DARK", "PRESS START"]); assert.equal(s.counts.reads, reads); s.tick(0.51); assert.equal(s.c.mode, "title"); assert.equal(!!s.pressed.a, false); assert.equal(s.counts.reads, reads); s.api.titleTick(0); assert.equal(s.c.fade, 0);
});
check("controlled string-index and missing-early-drain variants fail actual recovery/fresh-input invariants", () => {
  const numeric = 'titleChoose(TITLE_ITEMS.indexOf("CONTINUE"))'; assert.ok(source.includes(numeric)); const wrong = session(320, "prism", source.replace(numeric, 'titleChoose("CONTINUE")')); const saved = seed(wrong); lose(wrong); ready(wrong); wrong.tick(0, "a"); assert.throws(() => assertRestored(wrong, saved), assert.AssertionError);
  const drain = 'if (goT <= 1) { clearActionButtons(); for (const key of ["up", "down", "left", "right"]) hit(key); return; }'; assert.ok(source.includes(drain)); const stale = session(320, "prism", source.replace(drain, "if (goT <= 1) return;")); seed(stale); lose(stale); stale.tick(1, "a"); stale.tick(0.01); assert.throws(() => assert.equal(stale.c.fade, 0), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline (compile only)" });
console.log("defeat recovery: " + groups + " focused groups passed; canonical v1/Continue with memory/paint/timer peers, no browser/native acceptance");
