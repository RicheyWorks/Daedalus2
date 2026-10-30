// SPDX-License-Identifier: MIT
// Focused offline check: node --max-old-space-size=128 tools/rpg_demo/folly_workshop_test.js
// Production workshop/dialog/input/save/Continue handlers and canonical catalogs; no browser, assets, native or real storage.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const Save = require("./journey-save.js"), Ways = require("./waystones.js");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value)), parties = data("party").party, interiors = data("interiors"), towns = data("town-tiles"), worlds = data("worldmap-tiles");
function spec(name) { const text = builder.match(new RegExp("^" + name + " = (\\[.*\\])", "m")); assert.ok(text); return JSON.parse(text[1].replace(/\(/g, "[").replace(/\)/g, "]")); }
const original = spec("QUEST"), optional = spec("OPTIONAL_QUEST"), bosses = data("prism-bosses").bosses, dungeonCatalog = data("dungeons").dungeons.prism;
const dungeons = original.concat(optional).map(([landmark, name]) => ({ ...clone(dungeonCatalog.find(d => d.name === name)), landmark,
  final: name === "The Shattered Heart", optional: optional.some(([, n]) => n === name), boss_data: clone(bosses.find(b => b.dungeon === name)) }));
const folly = dungeons.find(d => d.optional), gear = {};
assert.ok(folly && folly.name === "Gearwright's Folly" && folly.boss_data.shard === "-");
for (const realm of ["portal", "prism"]) for (const room of Object.values(interiors.interiors[realm]))
  for (const item of room.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const T ="), between("const LOGICAL =", "const KEYMAP ="), line("const hit ="),
  between("const START_LEVEL =", "const atkOf ="), between('let mode = "title"', "/* ---------- time of day"),
  between("function airUnlocked()", "/* Where a saved skiff"), between("let footCache =", "/* Sky caches"),
  between("let grids =", "const chestKey ="), line("const chestKey ="), line("const WAYS ="), between("function townMap()", "const find ="),
  line("const find ="), between("let dlg = null;", "function wrap("), between("function enterDungeon(", "function stepDone("),
  between("function workshopStat(", "function openChest("), line("let shop ="), line("let menu ="), line("let B ="), line("let ending ="), line("let nameEntry ="),
  between('let SAVE_KEY = "prism.save.v1";', "function titleTick("), between("function titlePrompt(", "function drawTitle("),
  "this.api = { workshopStat, setWorkshopStat, workshopPrompt, startCalibration, say, ask, dialogTick, hit, setHeld, saveGame, readSavedJourney, prepareContinue, titleChoose, beginJourney, interiorMap, recruit, enterDungeon, " +
  "start: names => { party = buildParty(); state.beaten = new Set(names); map = interiorMap('Inn'); mode = 'field'; }, " +
  "current: () => ({ party, reserve, bag, gold, state, opened, map, P, grids, mode, fade, fadeCb, dlg, serial: journeySerial, pressed }), " +
  "fade: () => { const cb = fadeCb; fadeCb = null; if (cb) cb(); } };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session({ cleared = true, oldBuild = false, realm = "prism" } = {}) {
  const store = new Map(), notices = [], timers = [], sounds = [], tiles = rows => Object.fromEntries(rows.filter(t => t.realm === realm).map(t => [t.tile, t]));
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear: clone(gear), dungeons: realm === "prism" ? clone(dungeons.filter(d => !oldBuild || !d.optional)) : [],
      interiors: clone(interiors.interiors[realm]), interior_tiles: tiles(interiors.tiles), town: clone(towns.demo_towns[realm]), town_tiles: tiles(towns.tiles),
      world: clone(worlds.demo_maps[realm]), world_tiles: tiles(worlds.tiles), frames: {}, dungeon_walkable: data("dungeons").walkable },
    PrismJourneySave: Save, PrismWaystones: Ways, W: realm === "prism" ? 320 : 256, SETTINGS: null, PAD: null,
    performance: { now: () => 100 }, unlockAudio() {}, cue() {}, openSettings() {},
    sfx: name => sounds.push(name), toast: (title, sub) => notices.push({ title, sub }),
    setTimeout: (fn, ms) => timers.push({ fn, ms }),
    localStorage: { getItem: key => store.get(key) ?? null, setItem: (key, text) => { c.writes++; store.set(key, text); }, removeItem: key => store.delete(key) }, writes: 0 };
  if (realm === "portal") c.D.realm_profile = { start_level: 1 };
  vm.createContext(c); vm.runInContext(source, c, { timeout: 1000 });
  c.api.start(cleared && realm === "prism" && !oldBuild ? [folly.boss_data.name] : []);
  return { c, api: c.api, store, notices, timers, sounds, key: "prism.save.v1",
    tick(keys = [], dt = 0) { keys.forEach(k => c.api.setHeld("fixture", k, true)); if (c.api.current().dlg) c.api.dialogTick(dt); keys.forEach(k => c.api.setHeld("fixture", k, false)); } };
}
const current = s => s.api.current(), dialog = s => current(s).dlg;
function advance(s) { assert.ok(dialog(s) && !dialog(s).choice); s.tick([], 10); s.tick(["a"]); }
function toChoice(s) { for (let i = 0; i < 8 && dialog(s) && !dialog(s).choice; i++) advance(s); assert.ok(dialog(s)?.choice); s.tick([], 10); return dialog(s); }
function answer(s, index) { toChoice(s); if (dialog(s).choice.idx !== index) s.tick(["down"]); s.tick(["a"]); }
function drain(s) { for (let i = 0; i < 8 && dialog(s) && !dialog(s).choice; i++) advance(s); }
function correct(d) { const text = d.pages[0], word = text.includes("RED GAUGE") ? "VENT" : text.includes("CRYSTAL PULSE") ? "ALIGN" : text.includes("TAIL GEAR") ? "COOL" : null; assert.ok(word); return d.choice.options.indexOf(word); }
function drill(s, wrongAt = -1) {
  s.api.startCalibration(); const readings = [], positions = [];
  for (let turn = 0; turn < 3; turn++) {
    const d = toChoice(s), index = correct(d); assert.ok(index >= 0); readings.push(d.pages[0]); positions.push(index);
    answer(s, turn === wrongAt ? 1 - index : index); assert.ok(dialog(s) && !dialog(s).choice); advance(s);
  }
  assert.ok(dialog(s) && !dialog(s).choice); return { readings, positions, result: Array.from(dialog(s).pages) };
}
function progress(s) { const c = current(s); return JSON.stringify({ party: c.party, reserve: c.reserve, bag: c.bag, gold: c.gold,
  state: { ...c.state, beaten: [...c.state.beaten], ways: [...c.state.ways] }, opened: [...c.opened], grids: c.grids }); }
function saved(s) { assert.equal(s.api.saveGame(), true); const raw = s.store.get(s.key); assert.equal(Save.read(raw, s.c.D.realm_key, s.c.D.party.members).ok, true); return raw; }
function allRecruits(s) { const c = current(s); dungeons.forEach(d => c.state.beaten.add(d.boss_data.name)); dungeons.filter(d => !d.final).forEach(d => s.api.recruit(d.name)); assert.equal(current(s).party.length + current(s).reserve.length, 8); return s; }
function unchanged(s, before, refs) { assert.equal(progress(s), before); const c = current(s); [c.dlg, c.serial, c.map, c.fadeCb].forEach((value, i) => assert.equal(value, refs[i])); }

check("locked, legacy and Portal projections do not open the workshop", () => {
  for (const options of [{ cleared: false }, { oldBuild: true }, { realm: "portal" }]) { const s = session(options); s.api.workshopPrompt(); assert.equal(dialog(s), null); }
});
check("actual workshop greeting and TRY choice reach the first calibration", () => {
  const s = session(); s.api.workshopPrompt(); const d = toChoice(s); assert.match(d.pages[0], /TRY A CALIBRATION/); answer(s, 0); assert.match(dialog(s).pages[0], /^READING 1\/3:/);
});
check("Back plus Confirm leaves the entry question without starting or recording a drill", () => {
  const s = session(); s.api.workshopPrompt(); toChoice(s); const before = progress(s); s.tick(["a", "b"]); assert.equal(progress(s), before); assert.equal(dialog(s), null);
  assert.equal(current(s).pressed.a, false); assert.equal(current(s).pressed.b, false); s.tick(); assert.equal(dialog(s), null);
});
for (const afterAnswers of [0, 1, 2]) check("Back plus Confirm cancels after " + afterAnswers + " readings without score or reward", () => {
  const s = session(), before = progress(s); s.api.startCalibration();
  for (let i = 0; i < afterAnswers; i++) { const d = toChoice(s); answer(s, correct(d)); advance(s); }
  toChoice(s); s.tick(["a", "b"]); assert.equal(progress(s), before); assert.match(dialog(s).pages[0], /NO SCORE OR REWARD/);
  assert.equal(current(s).pressed.a, false); assert.equal(current(s).pressed.b, false); s.tick(); assert.equal(dialog(s).shown, 0);
});
check("three authored readings rotate and correct answers occupy both option positions", () => {
  const s = session(), results = [], baseline = current(s).bag["Herb Tonic"], first = [];
  for (let run = 0; run < 3; run++) { const result = drill(s); results.push(result); first.push(result.readings[0]); assert.equal(s.api.workshopStat("runs"), run + 1); assert.equal(s.api.workshopStat("best"), 3); drain(s); }
  assert.equal(new Set(first.map(text => text.split(": ")[1])).size, 3); assert.deepEqual(results.flatMap(r => r.positions), [0, 0, 0, 0, 0, 1, 0, 1, 1]);
  assert.equal(current(s).bag["Herb Tonic"], baseline + 2, "only the first perfect drill grants the two existing tonics");
  assert.ok(current(s).opened.has("workshop/folly/first-perfect")); assert.equal(s.sounds.filter(n => n === "ITEM").length, 1);
});
check("an imperfect drill records its score without reward, and a later perfect earns exactly two tonics", () => {
  const s = session(), baseline = current(s).bag["Herb Tonic"], gold = current(s).gold, members = JSON.stringify(current(s).party);
  assert.match(drill(s, 1).result[0], /2\/3/); assert.equal(s.api.workshopStat("best"), 2); assert.equal(current(s).bag["Herb Tonic"], baseline);
  drain(s); drill(s); assert.equal(s.api.workshopStat("best"), 3); assert.equal(current(s).bag["Herb Tonic"], baseline + 2); drain(s);
  drill(s, 0); assert.equal(s.api.workshopStat("runs"), 3); assert.equal(s.api.workshopStat("best"), 3); assert.equal(current(s).bag["Herb Tonic"], baseline + 2);
  assert.equal(current(s).gold, gold); assert.equal(JSON.stringify(current(s).party), members, "practice never changes combat stats or health");
});
check("record replacement stays bounded and malformed existing numeric flags are forgiving", () => {
  const s = session(), opened = current(s).opened;
  opened.add("workshop/folly/runs/not-a-number"); assert.equal(s.api.workshopStat("runs"), 0); s.api.setWorkshopStat("runs", 999999);
  assert.equal([...opened].filter(k => k.startsWith("workshop/folly/runs/")).length, 1); s.api.setWorkshopStat("best", 3); drill(s);
  assert.equal(s.api.workshopStat("runs"), 999999); assert.equal(s.api.workshopStat("best"), 3);
  assert.equal([...opened].filter(k => k.startsWith("workshop/folly/runs/")).length, 1); assert.equal([...opened].filter(k => k.startsWith("workshop/folly/best/")).length, 1);
});
check("v1 opened records and all eight companions survive actual save and Continue", () => {
  const origin = allRecruits(session()); drill(origin); const raw = saved(origin), value = JSON.parse(raw), target = session({ cleared: false });
  assert.equal(Object.hasOwn(value, "workshop"), false); assert.equal(value.v, 1); target.store.set(target.key, raw);
  const result = target.api.readSavedJourney(), before = progress(target), prepared = target.api.prepareContinue(result.value);
  assert.equal(progress(target), before, "preparation is detached from the live journey"); assert.equal(current(target).state.beaten.has(folly.boss_data.name), false);
  assert.equal(prepared.inn.npcs.filter(n => n.type === "Brannoc").length, 1, "Inn NPC uses the detached candidate's beaten set");
  assert.equal(prepared.inn.npcs.find(n => n.type === "Brannoc").fieldSprite, "NPC_Merchant"); assert.equal(prepared.inn.walk(prepared.inn.grid[6][11]), true);
  target.api.titleChoose(1); target.api.fade(); const c = current(target);
  assert.equal(c.party.length + c.reserve.length, 8); assert.equal(c.map.name, "Inn"); assert.equal(c.map.npcs.filter(n => n.type === "Brannoc").length, 1);
  assert.equal(target.api.workshopStat("runs"), 1); assert.equal(target.api.workshopStat("best"), 3); assert.ok(c.opened.has("workshop/folly/first-perfect"));
  assert.equal(target.store.get(target.key), raw); assert.equal(target.c.writes, 0, "Continue never rewrites the original save");
});
check("older Folly-cleared save receives owed Brannoc without touching stored bytes", () => {
  const origin = allRecruits(session()), value = JSON.parse(saved(origin)); value.reserve = value.reserve.filter(m => m.job !== "Gearwright");
  const raw = JSON.stringify(value), s = session({ cleared: false }); s.store.set(s.key, raw); s.api.titleChoose(1); s.api.fade();
  assert.equal(current(s).reserve.filter(m => m.job === "Gearwright").length, 1); assert.equal(current(s).party.length + current(s).reserve.length, 8);
  assert.equal(current(s).map.npcs.filter(n => n.type === "Brannoc").length, 1); assert.equal(s.store.get(s.key), raw);
});
check("legacy four-route journey without workshop fields remains valid in the extended build", () => {
  const origin = session({ oldBuild: true }); original.slice(0, 3).forEach(([, name]) => { origin.api.recruit(name); current(origin).state.beaten.add(bosses.find(b => b.dungeon === name).name); });
  const value = JSON.parse(saved(origin)); for (const key of ["realm_key", "day", "minute", "seen", "fish", "quests"]) delete value[key];
  const raw = JSON.stringify(value), s = session({ cleared: false }); s.store.set(s.key, raw); s.api.titleChoose(1); s.api.fade();
  assert.equal(current(s).party.length + current(s).reserve.length, 7); assert.equal(current(s).map.npcs.some(n => n.type === "Brannoc"), false);
  assert.equal(s.api.workshopStat("runs"), 0); assert.equal(s.api.workshopStat("best"), 0); assert.equal(s.store.get(s.key), raw);
});
check("invalid Continue retains the live dialog, progress and callback generation", () => {
  const s = session(); s.api.startCalibration(); toChoice(s); const c = current(s), before = progress(s), refs = [c.dlg, c.serial, c.map, c.fadeCb];
  s.store.set(s.key, "{unfinished"); s.api.titleChoose(1); unchanged(s, before, refs); assert.match(s.notices.at(-1).sub, /kept/);
  assert.equal(s.store.get(s.key), "{unfinished"); assert.equal(s.c.writes, 0);
  answer(s, correct(dialog(s))); advance(s); assert.match(dialog(s).pages[0], /^READING 2\/3:/, "the valid current callback is still usable");
});
function oldCallback(s, stage) {
  if (stage === "greeting") { s.api.workshopPrompt(); return dialog(s).then; }
  if (stage === "try") { s.api.workshopPrompt(); return toChoice(s).choice.then; }
  s.api.startCalibration(); const d = toChoice(s);
  if (stage === "reading") return d.choice.then;
  if (stage === "cancel") return d.choice.cancel;
  answer(s, correct(d)); return dialog(s).then;
}
for (const choice of [0, 1]) check("accepted " + (choice ? "Continue" : "New Game") + " invalidates every old workshop callback", () => {
  for (const stage of ["greeting", "try", "reading", "cancel", "feedback"]) {
    const s = session(); saved(s); const callback = oldCallback(s, stage), serial = current(s).serial;
    s.api.titleChoose(choice); s.api.fade(); assert.equal(current(s).serial, serial + 1); const c = current(s), before = progress(s), refs = [c.dlg, c.serial, c.map, c.fadeCb];
    callback(0); unchanged(s, before, refs);
  }
});
for (const choice of [0, 1]) check("accepted journey cancels stale entry/tutorial timers: choice " + choice, () => {
  const s = session(); saved(s); s.api.beginJourney(); s.api.fade(); const tutorial = s.timers.find(t => t.ms === 600).fn;
  s.api.titleChoose(1); s.api.fade(); const arrival = s.timers.at(-1).fn;
  s.api.titleChoose(choice); s.api.fade(); const before = progress(s), c = current(s), refs = [c.dlg, c.serial, c.map, c.fadeCb];
  tutorial(); arrival(); unchanged(s, before, refs); assert.equal(dialog(s), null);
});
for (const choice of [0, 1]) check("accepted journey invalidates an earlier Folly entry callback: choice " + choice, () => {
  const s=session({cleared:false});dungeons.filter(d=>d.boss_data&&d.boss_data.shard!=="-"&&!d.final).forEach(d=>current(s).state.beaten.add(d.boss_data.name));
  s.api.enterDungeon(4);const entry=dialog(s).then;assert.equal(typeof entry,"function");saved(s);
  s.api.titleChoose(choice);s.api.fade();const c=current(s),before=progress(s),refs=[c.dlg,c.serial,c.map,c.fadeCb];entry();unchanged(s,before,refs);
});
check("current Continue arrival and tutorial timers respect an existing dialog", () => {
  const s = session(); saved(s); s.api.titleChoose(1); s.api.fade(); s.api.say(["A CURRENT CONVERSATION."]); const d = dialog(s);
  s.timers.at(-1).fn(); assert.equal(dialog(s), d); drain(s); s.api.beginJourney(); s.api.fade(); s.timers.at(-1).fn(); assert.ok(dialog(s)); assert.equal(dialog(s).voice, 0);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; no production boot/DOM loop.
console.log("Prismheart Folly workshop/save checks: " + checks + " passed; full inline script compiles.");
