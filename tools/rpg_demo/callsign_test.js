// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/callsign_test.js
// Actual keyboard capture, logical pad callback, touch buttons/grid, naming/ORDER/save handlers.
// Canonical roster/title/gear; fake DOM/canvas/storage peers only. No browser/devices/assets/build/IIFE.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Save = require("./journey-save.js"), Ways = require("./waystones.js");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n"), builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, titles = data("title").realms, menus = data("menus").layouts, interiorData = data("interiors"), bosses = data("prism-bosses").bosses;
const worldData = data("worldmap-tiles"), rawDungeons = data("dungeons").dungeons, spells = data("spells").spells, ways = data("prism-waystones").waystones;
function tuples(name) { const s = builder.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m")); assert.ok(s); return [...s[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g)].map(m => [m[1], m[2]]); }
const original = tuples("QUEST"), optional = tuples("OPTIONAL_QUEST");
const dungeons = original.concat(optional).map(([landmark, name], i) => ({ ...clone(rawDungeons.prism.find(d => d.name === name)), landmark, optional: i >= original.length, final: i === 3, boss_data: clone(bosses.find(b => b.dungeon === name)) }));
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = p => { const s = html.split("\n").find(l => l.startsWith(p)); assert.ok(s, p); return s; };
const padCallback = between("  onChange: e => {", "\n  },\n}) : null;").replace("  onChange: e => {", "this.padChange = e => {") + "\n};";
const source = [between("const LOGICAL =", "/* ---------- controllers:"), line("const PAD_TO_DEMO ="), padCallback,
  line("const CHARS ="), line("const T ="), line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="), line("let journeySerial ="), line("const find ="), line("function airUnlocked()"),
  between("function buildParty()", "let party ="), between("function makeMember(", "/* ---------- maps"), between("const carriesShard =", "const chestKey ="),
  between("function interiorMap(", "function worldMap()"), between("function goto(", "const find ="), between("let menu = null;", "function drawStatus()"),
  between('let SAVE_KEY = "prism.save.v1";', "function beginJourney()"), between("function titlePrompt(", "function drawTitle("),
  between("let nameEntry = null;", "/* ---------- ending ---------- */"),
  "this.api={start:()=>{party=buildParty();},openMenu,menuTick,openCallsign,finishCallsign,nameTick,drawName,neType,neFinish,neBack,neActivate,neRows,nameAt,roster,recruit,saveGame,titleChoose," +
  "menu:()=>menu,entry:()=>nameEntry,inputs:()=>({pressed,held,SRC,codes:Array.from(keyboardCodes)}),press:(...keys)=>keys.forEach(k=>{pressed[k]=true;}),chars:CHARS," +
  "setPad:p=>{PAD=p;},bumpSerial:()=>{journeySerial++;},replaceMenu:()=>{menu={...menu};},key:()=>SAVE_KEY,setKey:k=>{SAVE_KEY=k;}," +
  "applyFade:()=>{if(fadeCb){const cb=fadeCb;fadeCb=null;cb();}fade=0;},view:()=>({mode,menu,nameEntry,fade})," +
  "progress:()=>({party:party.map(m=>({...m,name:undefined})),reserve:reserve.map(m=>({...m,name:undefined})),bag,gold,beaten:Array.from(state.beaten),opened:Array.from(opened),state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},map,P,D})};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const events = {}, docEvents = {}, pointers = [], buttons = {}, paints = [], sounds = [], notices = [], pending = [], store = new Map(), counts = { writes: 0, reads: 0, begins: 0 }, gear = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiorData.interiors[r])) for (const it of shop.stock || []) if (it.attack != null || it.defence != null || it.effect) gear[it.name] = clone(it);
  const rects = {}; parties[realm].members.forEach(m => { rects["Party_" + m.job] = [0, 0, m.job === "Beastcaller" ? 224 : 112, 112]; });
  function add(target, type, fn, capture) { (target[type] ||= []).push({ fn, capture: !!capture }); }
  function button(k) { const callbacks = {}, classes = new Set(); return buttons[k] = { dataset: { k }, callbacks, classes, classList: { add: k => classes.add(k), remove: k => classes.delete(k) }, addEventListener: (type, fn) => { callbacks[type] = fn; } }; }
  const math = Object.create(Math); math.random = () => { throw new Error("call signs cannot use gameplay randomness"); };
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, menus: clone(menus[realm]), title: clone(titles[realm]), dungeons: clone(dungeons),
      interiors: clone(interiorData.interiors[realm]), interior_tiles: Object.fromEntries(interiorData.tiles.map(t => [t.tile, clone(t)])), town_tiles: {}, frames: {},
      world: clone(worldData.demo_maps[realm]), waystones: clone(ways), spells: clone(spells.filter(s => s.realm === realm)), rects: { sprites: rects, tiles: {} }, ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    Math: math, W: width, H: 224, GEAR: {}, party: [], reserve: [], bag: {}, gold: 0, B: null, mode: "field", map: { kind: "world", retained: true }, P: { x: 7, y: 9, dir: "left", moving: 0 },
    state: { beaten: new Set(), seen: {}, quests: {}, fish: {}, ways: new Set(), air: null, returnTo: null, steps: 0, sinceBattle: 0, day: 1, minute: 480 }, opened: new Set(["retained/chest"]), grids: {}, fade: 0, fadeCb: null, dlg: null, shop: null, ending: null,
    PrismJourneySave: Save, PrismWaystones: Ways, WAYS: () => c.D.waystones, recoverAir() { throw new Error("save fixture has no air state"); },
    performance: { now: () => 1000 }, window: { addEventListener: (type, fn, capture) => add(events, type, fn, capture) },
    document: { hidden: false, hasFocus: () => true, addEventListener: (type, fn, capture) => add(docEvents, type, fn, capture), querySelectorAll: () => ["up", "down", "left", "right", "a", "b", "start", "opts"].map(button) },
    touchEl: { querySelectorAll: () => Object.values(buttons).filter(b => b.classes.has("held")) },
    cv: { addEventListener: (type, fn) => { if (type === "pointerdown") pointers.push(fn); }, focus() {}, getBoundingClientRect: () => ({ left: 0, top: 0, width, height: 224 }) },
    sfx: k => sounds.push(k), toast: (...text) => notices.push(text), unlockAudio() {}, cue() {}, say() {}, setTimeout: fn => pending.push(fn), beginJourney: () => { counts.begins++; }, openSettings() {},
    drawField() {}, drawPartyRows() {}, clockText: () => "D1 08:00", isNight: () => false, tags: () => [],
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: v => String(v).length * 6,
    text: (v, x, y, color = "#ffffff") => { const label = String(v).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }), cursor: (x, y) => paints.push({ kind: "cursor", x, y }),
    spr: (sheet, name, x, y, sx, sw, sh, scale = 1) => { const r = c.D.rects.sprites[name]; paints.push({ kind: "sprite", name, x, y, w: (sw || r[2]) * scale, h: (sh || r[3]) * scale }); }, gauge() {},
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h }); }, drawImage() {} },
    localStorage: { getItem(key) { counts.reads++; return store.get(key) ?? null; }, setItem(key, raw) { counts.writes++; store.set(key, raw); }, removeItem() { throw new Error("naming cannot erase saves"); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start(); c.api.setKey(realm + ".save.v1");
  function keyboard(code, key, up = false, repeat = false) { let stop = false; const e = { code, key, repeat, ctrlKey: false, metaKey: false, altKey: false, preventDefault() {}, stopImmediatePropagation() { stop = true; } };
    for (const event of [...(events[up ? "keyup" : "keydown"] || [])].sort((a, b) => Number(b.capture) - Number(a.capture))) { if (stop) break; event.fn(e); } }
  const progress = () => JSON.stringify(c.api.progress());
  return { c, api: c.api, counts, store, notices, paints, buttons, keyboard, progress,
    step(...keys) { c.api.press(...keys); if (c.mode === "name") c.api.nameTick(1 / 60); else if (c.mode === "menu") c.api.menuTick(); },
    type(text) { for (const k of text) keyboard(k === " " ? "Space" : /^[0-9]$/.test(k) ? "Digit" + k : "Key" + k, k); },
    touch(k, up = false) { buttons[k].callbacks[up ? "pointerup" : "pointerdown"]({ preventDefault() {} }); },
    tap(x, y) { for (const fn of pointers) fn({ clientX: x, clientY: y }); },
    pad(action, up = false) { c.padChange({ type: up ? "up" : "down", action }); },
    labels(menuLabel = "START", back = "B") { c.api.setPad({ binding: () => false, devices: () => [{ index: 0 }], label(action) { assert.ok(["menu", "cancel", "confirm"].includes(action)); return action === "menu" ? menuLabel : action === "cancel" ? back : "A"; } }); },
    draw() { paints.length = 0; const before = progress(), view = JSON.stringify(c.api.view()), writes = counts.writes; c.api.drawName(); assert.equal(progress(), before); assert.equal(JSON.stringify(c.api.view()), view); assert.equal(counts.writes, writes); return paints; }
  };
}
function earned(s) { for (const d of s.c.D.dungeons.filter(d => !d.final)) { s.api.recruit(d.name); s.c.state.beaten.add(d.boss_data.name); } assert.equal(s.api.roster().length, 8); return s; }
function formation(s, index = 0) { s.api.openMenu(); for (let i = 0; i < 4; i++) s.step("down"); s.step("a"); assert.equal(s.api.menu().sub, "order");
  for (let i = 0; i < index; i++) s.step("down"); assert.equal(s.api.menu().ii, index); return s; }
function call(s, index = 0) { formation(s, index); s.step("start"); assert.equal(s.c.mode, "name"); assert.equal(s.api.entry().name, ""); return s; }
function edgesClear(s) { const keys = s.api.inputs().pressed; for (const k of ["a", "b", "start", "up", "down", "left", "right"]) assert.equal(!!keys[k], false, "boundary consumes " + k); }
check("all eight earned members, including reserves, rename through keyboard capture and return to the same formation", () => {
  const s = earned(session()), members = Array.from(s.api.roster());
  for (let i = 0; i < members.length; i++) { formation(s, i); const menu = s.api.menu(), map = s.c.map, pos = JSON.stringify(s.c.P), before = s.progress(), oldNames = members.map(m => m.name); s.step("start");
    assert.equal(s.api.entry().target, members[i]); assert.equal(s.api.entry().returnMenu, menu); s.type("ALPHA" + i); s.keyboard("Enter", "Enter");
    assert.equal(members[i].name, "Alpha" + i); assert.equal(s.c.mode, "menu"); assert.equal(s.api.menu(), menu); assert.equal(menu.ii, i); assert.equal(menu.pick, -1); assert.equal(s.api.entry(), null);
    members.forEach((m, index) => assert.equal(m.name, index === i ? "Alpha" + i : oldNames[index], "only the selected call sign changes"));
    assert.equal(s.c.map, map); assert.equal(JSON.stringify(s.c.P), pos); assert.equal(s.progress(), before); assert.equal(s.counts.writes, 0); edgesClear(s);
  }
});
function blankLegacy(production = source) { const s = session(320, "prism", production), name = "MiXeD".repeat(13).slice(0, 64); s.c.party[0].name = name; formation(s); s.step("start"); assert.equal(s.c.mode, "name"); s.api.neFinish();
  assert.equal(s.c.party[0].name, name, "blank END preserves every original character and case"); assert.equal(s.c.mode, "menu"); assert.equal(s.counts.writes, 0); return s; }
check("blank or spaces-only END keeps a 64-character restored name exactly", () => {
  blankLegacy(); const s = call(session()); const name = s.api.entry().originalName; s.type("   "); s.api.neFinish(); assert.equal(s.c.party[0].name, name);
});
for (const width of [320, 256]) check("blank/cancel preserves a 64-character sharp-s name and its uppercase caption fits at " + width, () => {
  const s = session(width), original = "ß".repeat(64); s.c.party[0].name = original;
  for (const action of ["blank", "cancel"]) {
    call(s); if (action === "cancel") s.type("OTHER"); const paints = s.draw(), caption = paints.find(p => p.kind === "text" && p.x === 150 && p.y === 26);
    assert.ok(caption); assert.equal(caption.label, ("WAS " + original).toUpperCase().slice(0, Math.floor((width - 162) / 6)));
    assert.ok(paints.filter(p => p.kind === "text").every(p => p.x >= 0 && p.x + p.w <= width && p.y + p.h <= 224));
    assert.ok(paints.some(p => p.kind === "text" && p.y === 208 && p.label === "BACKSPACE: DELETE ESC OR TAP B: CANCEL"), "the complete physical cancel help remains visible");
    if (action === "blank") s.api.neFinish(); else s.keyboard("Escape", "Escape");
    assert.equal(s.c.party[0].name, original); assert.equal(s.c.mode, "menu"); assert.equal(s.counts.writes, 0);
  }
});
check("Escape, context B and the real grid CANCEL discard a filled buffer", () => {
  for (const route of ["escape", "b", "grid"]) { const s = call(session()), target = s.api.entry().target, original = target.name, before = s.progress(); s.type("OTHER");
    if (route === "escape") s.keyboard("Escape", "Escape"); else if (route === "b") s.step("b", "a", "start"); else s.tap(26, 194);
    assert.equal(target.name, original); assert.equal(s.c.mode, "menu"); assert.equal(s.api.menu().sub, "order"); assert.equal(s.progress(), before); edgesClear(s);
  }
});
check("Backspace deletes without becoming context B, then cancels only on an already empty buffer", () => {
  const s = call(session()); s.type("AB"); s.keyboard("Backspace", "Backspace"); assert.equal(s.api.entry().name, "A"); assert.equal(s.c.mode, "name"); assert.equal(!!s.api.inputs().pressed.b, false);
  s.keyboard("Backspace", "Backspace"); assert.equal(s.api.entry().name, ""); assert.equal(s.c.mode, "name"); s.keyboard("Backspace", "Backspace"); assert.equal(s.c.mode, "menu");
});
check("the actual title-grid limit bounds typed input, and a canvas letter/END tap commits normally", () => {
  const s = call(session()); s.type("ABCDEFGHIJKLM"); assert.equal(s.api.entry().name, "ABCDEFGHI"); assert.equal(s.c.D.title.name_entry.max_len, 9); s.api.neBack();
  call(s); s.tap(26, 64); assert.equal(s.api.entry().name, "A"); s.tap(s.c.W - 45, 194); assert.equal(s.c.party[0].name, "A"); assert.equal(s.c.mode, "menu");
});
function repeatInvariant(production = source) { const s = formation(session(320, "prism", production)); s.keyboard("Enter", "Enter"); s.step(); assert.equal(s.c.mode, "name");
  s.keyboard("Enter", "Enter", false, true); assert.equal(s.c.mode, "name", "opening Enter's repeat cannot close the editor"); s.keyboard("Enter", "Enter", true); s.type("PIP"); s.keyboard("Enter", "Enter"); assert.equal(s.c.mode, "menu"); assert.equal(s.c.party[0].name, "Pip"); return s; }
check("held Enter repeats are consumed and a released fresh Enter finishes", () => repeatInvariant());
check("fresh pad menu/cancel and actual touch START/B preserve modal boundaries", () => {
  for (const input of ["pad", "touch"]) { const s = formation(session()); if (input === "pad") s.pad("menu"); else s.touch("start"); s.step(); assert.equal(s.c.mode, "name");
    if (input === "pad") s.pad("menu", true); else s.touch("start", true); s.type("MOSS");
    if (input === "pad") s.pad("menu"); else s.touch("start"); s.step(); assert.equal(s.c.mode, "menu"); assert.equal(s.c.party[0].name, "Moss");
    if (input === "pad") s.pad("menu", true); else s.touch("start", true); s.step("start"); s.type("NO");
    if (input === "pad") s.pad("cancel"); else s.touch("b"); s.step(); assert.equal(s.c.mode, "menu"); assert.equal(s.c.party[0].name, "Moss");
  }
});
check("entry and return consume all buffered actions/directions while retaining held-source semantics", () => {
  const s = formation(session()); s.touch("right"); s.api.press("a", "b", "start", "up", "down", "left", "right"); s.api.openCallsign(); edgesClear(s);
  assert.equal(s.api.inputs().held.right, true); s.type("FIN"); s.api.press("a", "b", "start", "up", "down", "left", "right"); s.api.finishCallsign(true); edgesClear(s);
  assert.equal(s.api.inputs().held.right, true); s.touch("right", true); s.step(); assert.equal(s.api.menu().pick, -1);
});
for (const stale of ["serial", "target", "menu"]) check("stale " + stale + " context cannot rename or take over the current menu", () => {
  const s = call(session()), target = s.api.entry().target, original = target.name; s.type("STALE");
  if (stale === "serial") s.api.bumpSerial(); else if (stale === "target") s.c.party = s.c.party.filter(m => m !== target); else s.api.replaceMenu();
  const before = JSON.stringify(s.api.view()), progress = s.progress(); s.api.finishCallsign(true);
  assert.equal(target.name, original); assert.equal(JSON.stringify(s.api.view()), before); assert.equal(s.progress(), progress); assert.equal(s.counts.writes, 0);
});
check("pending swap and Portal ORDER cannot open call signs; Back beats Start and Confirm", () => {
  const s = formation(earned(session())); s.step("a"); const before = s.progress(); s.step("start"); assert.equal(s.c.mode, "menu"); assert.equal(s.api.menu().pick, 0); assert.equal(s.api.entry(), null); assert.equal(s.progress(), before);
  s.step("b", "start", "a"); assert.equal(s.api.menu().pick, -1); assert.equal(s.api.entry(), null); assert.equal(s.c.mode, "menu"); s.step(); assert.equal(s.api.menu().pick, -1);
  const portal = formation(session(256, "portal")); portal.step("start"); assert.equal(portal.c.mode, "menu"); assert.equal(portal.api.entry(), null); portal.api.openCallsign(); assert.equal(portal.api.entry(), null);
});
for (const width of [320, 256]) check("every call-sign portrait, letter grid, legacy caption and physical prompt fits at " + width, () => {
  const s = earned(session(width)), members = Array.from(s.api.roster()); s.labels("ABCDEFGH", "B");
  for (let i = 0; i < members.length; i++) { members[i].name = "L".repeat(64); call(s, i); s.type("NINECHARS"); const paints = s.draw(), portrait = paints.find(p => p.kind === "sprite");
    assert.ok(portrait && portrait.name === members[i].sprite); assert.ok(portrait.x >= 0 && portrait.x + portrait.w <= 46 && portrait.y + portrait.h <= 42);
    for (const p of paints.filter(p => p.kind === "text")) { assert.ok(p.x >= 0 && p.x + p.w <= width && p.y >= 0 && p.y + p.h <= 224); assert.ok([...p.label].every(k => s.api.chars.includes(k))); }
    assert.ok(paints.some(p => p.kind === "text" && p.label === "CALL SIGN - " + members[i].job.toUpperCase())); assert.ok(paints.some(p => p.kind === "text" && p.label === "CANCEL"));
    assert.ok(paints.some(p => p.kind === "text" && p.y === 172 && p.label === "PRESS ABCDEFGH TO FINISH.")); s.api.neBack();
  }
});
check("normal SAVE, the v1 reader and accepted Continue preserve reserve call signs without changing jobs", () => {
  const s = call(earned(session()), 7), target = s.api.entry().target, job = target.job; s.type("BRIGHT"); s.keyboard("Enter", "Enter"); assert.equal(s.counts.writes, 0);
  s.api.openMenu(); for (let i = 0; i < 7; i++) s.step("down"); s.step("a"); assert.equal(s.counts.writes, 1);
  const raw = s.store.get(s.api.key()), decoded = Save.read(raw, "prism", parties.prism.members); assert.equal(decoded.ok, true); assert.equal(decoded.value.reserve.find(m => m.job === job).name, "Bright");
  target.name = "Live unsaved"; s.api.titleChoose(1); s.api.applyFade(); assert.equal(s.api.roster().find(m => m.job === job).name, "Bright"); assert.equal(s.store.get(s.api.key()), raw); assert.equal(s.counts.writes, 1);
});
check("New Game naming still finishes via beginJourney and BACK still returns to title", () => {
  const s = session(); s.api.titleChoose(0); s.api.applyFade(); assert.equal(s.c.mode, "name"); assert.equal(s.api.entry().target, undefined); s.api.entry().name = "NOVA"; s.api.neFinish(); assert.equal(s.c.party[0].name, "Nova"); assert.equal(s.counts.begins, 1);
  s.api.titleChoose(0); s.api.applyFade(); s.api.neBack(); s.api.applyFade(); assert.equal(s.c.mode, "title"); assert.equal(s.counts.writes, 0);
});
check("controlled prefilled legacy names, repeated Enter and removed serial guard fail the same invariants", () => {
  const prefill = source.replace('nameEntry = { name: "", r: 0, c: 0, t: 0, target,', 'nameEntry = { name: target.name.toUpperCase(), r: 0, c: 0, t: 0, target,'); assert.notEqual(prefill, source); assert.throws(() => blankLegacy(prefill), assert.AssertionError);
  const repeat = source.replace('if (k === "Enter") { stop(); if (!e.repeat) neFinish(); return; }', 'if (k === "Enter") { stop(); neFinish(); return; }'); assert.notEqual(repeat, source); assert.throws(() => repeatInvariant(repeat), assert.AssertionError);
  const stale = source.replace('ne.serial !== journeySerial || ', ''); assert.notEqual(stale, source); assert.throws(() => { const s = call(session(320, "prism", stale)), name = s.c.party[0].name; s.type("STALE"); s.api.bumpSerial(); s.api.finishCallsign(true); assert.equal(s.c.party[0].name, name); }, assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("call signs: " + checks + " focused groups passed; fake DOM/logical controller peers, no runtime/device acceptance");
