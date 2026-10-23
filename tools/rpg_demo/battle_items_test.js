// SPDX-License-Identifier: MIT
// DOM-free focused regression: node --max-old-space-size=128 tools/rpg_demo/battle_items_test.js
// Uses production battle planning, action, field-item and drawing functions plus real catalogs.
// No browser, game loop, build, real browser storage or production data writes.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const partyData = data("party").party.prism, interiors = data("interiors").interiors;
const spells = data("spells").spells.filter(s => s.realm === "prism");
const foeData = data("prism-bestiary").types.reduce((best, f) => !best || f.hp > best.hp ? f : best, null);
const gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(interiors[realm])) {
  for (const it of shop.stock || []) if (it.attack != null || it.defence != null || it.effect) gear[it.name] = it;
}
const clone = value => JSON.parse(JSON.stringify(value));
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start);
  return html.slice(a, b);
}
const line = prefix => html.split(/\r?\n/).find(s => s.startsWith(prefix));
const source = [
  line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="),
  between("function makeMember(", "/* Recruits:"), between("const atkOf =", "/* ---------- maps"),
  between("const ITEM_KINDS =", "function menuTick()"), between("function useItem(", "/* Four rows"),
  between("const STATUS =", "/* ---------- bestiary"), line("function wakeAt("),
  line("let B = null;"), line("const CMDS ="), line("const battleCmds ="),
  between("function nextChooser(", "/* Foe turns by"),
  between("function drawBattle()", "/* ---------- title:"),
  "this.api = { makeMember, battleItems, battleItemStock, fieldItems, itemStock, itemLine, battleTick, doAction, useItem, drawBattle, commands: () => CMDS, getBattle: () => B, setBattle: value => { B = value; } };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(productionSource = source) {
  const pressed = new Set(), draws = [], notices = [];
  const fixedMath = Object.create(Math); fixedMath.random = () => 0.5;
  const c = {
    D: { party: clone(partyData), spells: clone(spells), rects: { backdrops: {}, sprites: {}, spells: {} } },
    GEAR: clone(gear), party: [], reserve: [], bag: {}, gold: 237,
    map: { kind: "town" }, mode: "battle", W: 320, H: 224, fade: 0, fadeCb: null, settingsFramePaused: false,
    state: { minute: 480, day: 1, steps: 0 }, Math: fixedMath,
    rnd: (a, b) => (a + b) / 2, ri: a => a, clamp: (n, low, high) => Math.max(low, Math.min(high, n)),
    hit: key => { const v = pressed.has(key); pressed.delete(key); return v; },
    sfx() {}, mySpirits: () => [], playChord() {}, gauge() {}, win() {}, spr() {}, cursor() {},
    tw: s => String(s).length * 6, text: (label, x, y) => { draws.push({ label: String(label), x, y }); },
    toast: (title, message) => { notices.push(title + ": " + message); },
    g: { fillStyle: "", fillRect() {}, drawImage() {} },
    wrap: s => [s], performance: { now: () => 0 }
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, 15));
  const f = foeData;
  c.api.setBattle({ phase: "cmd", who: 0, cmd: 0, target: 0, sub: null, list: [], acts: [], queue: [], msg: "",
    t: 0, fx: null, pops: [], flash: {}, boss: false, round: 1, wait: 0,
    foes: [{ key: f.key, name: f.name, hp: f.hp, max: f.hp, atk: f.attack, def: f.defence, spd: f.speed,
      exp: f.exp, gold: f.gold, img: "Foe_" + f.key, size: 56, x: 24, y: 26, beh: "simple" }] });
  return { c, notices, draws,
    tick: (...keys) => { pressed.clear(); keys.forEach(k => pressed.add(k)); c.api.battleTick(1 / 60); pressed.clear(); },
    draw: () => { draws.length = 0; c.api.drawBattle(); return draws; } };
}
function choose(s, name, target = 0) {
  const b = s.c.api.getBattle(); b.cmd = s.c.api.commands().indexOf("ITEM"); s.tick("a");
  assert.equal(b.sub, "item", "ITEM opens with free stock");
  b.oi = s.c.api.battleItems().indexOf(name); assert.ok(b.oi >= 0); s.tick("a");
  if (b.sub === "target") { b.target = target; s.tick("a"); }
}
function resources(s) {
  const c = s.c, b = c.api.getBattle();
  return JSON.stringify({ party: c.party.map(m => ({ hp: m.hp, mp: m.mp, status: m.status })), gold: c.gold,
    phase: b && b.phase, result: b && b.result, fade: c.fade, clock: c.state });
}
function itemAction(s, name, target = 0) {
  return { kind: "item", who: s.c.party[1], item: name, target: s.c.party[target] };
}
function assertRefused(s, name, before, stock) {
  assert.equal(resources(s), before, "party resources and escape state stay unchanged");
  assert.ok(Object.is(s.c.bag[name], stock), "item counter stays unchanged");
  assert.match(s.c.api.getBattle().msg, /NO .* LEFT/);
}

check("the last item cannot be queued by a second hero", () => {
  const s = session(), b = s.c.api.getBattle(); s.c.bag["Herb Tonic"] = 1;
  choose(s, "Herb Tonic"); assert.equal(b.acts.length, 1); assert.equal(b.who, 1);
  assert.equal(s.c.bag["Herb Tonic"], 1, "planning does not spend the item");
  assert.equal(s.c.api.battleItemStock("Herb Tonic"), 0); assert.equal(s.c.api.battleItems().includes("Herb Tonic"), false);
  b.cmd = s.c.api.commands().indexOf("ITEM"); s.tick("a");
  assert.equal(b.acts.length, 1); assert.equal(b.sub, null); assert.match(b.msg, /PLANNED/);
  assert.match(s.notices.at(-1), /earlier command/);
});
check("backing up releases the existing action's item without touching stock", () => {
  const s = session(), b = s.c.api.getBattle(); s.c.bag["Herb Tonic"] = 1; choose(s, "Herb Tonic");
  s.tick("b"); assert.equal(b.acts.length, 0); assert.equal(b.who, 0);
  assert.equal(s.c.api.battleItemStock("Herb Tonic"), 1); choose(s, "Herb Tonic", 1);
  assert.equal(b.acts.length, 1); assert.equal(b.acts[0].target, s.c.party[1]); assert.equal(s.c.bag["Herb Tonic"], 1);
});
check("cancelling a pending target never reserves an item", () => {
  const s = session(), b = s.c.api.getBattle(); s.c.bag["Herb Tonic"] = 1; b.cmd = 2;
  s.tick("a"); s.tick("a"); assert.equal(b.sub, "target"); s.tick("b"); s.tick("b");
  assert.equal(b.acts.length, 0); assert.equal(s.c.api.battleItemStock("Herb Tonic"), 1);
});
check("a stale pending target cannot queue vanished stock", () => {
  const s = session(), b = s.c.api.getBattle(); s.c.bag["Herb Tonic"] = 1; s.c.bag["Clear Draught"] = 1; b.cmd = 2;
  s.tick("a"); s.tick("a"); s.c.bag["Herb Tonic"] = 0; const before = resources(s); s.tick("a");
  assert.equal(b.acts.length, 0); assert.equal(resources(s), before); assert.equal(s.c.bag["Herb Tonic"], 0);
  assert.equal(b.sub, null); assert.equal(b.pending, null); assert.match(b.msg, /CHOOSE ITEM AGAIN/);
  assert.match(s.notices.at(-1), /available item/); choose(s, "Clear Draught"); assert.equal(b.acts.length, 1);
});
check("two available items plan and execute once each, with free count displayed", () => {
  const s = session(), c = s.c, b = c.api.getBattle(); c.bag["Herb Tonic"] = 2;
  c.party[0].hp -= 130; c.party[1].hp -= 130; const hp = c.party.map(m => m.hp);
  choose(s, "Herb Tonic", 0); b.cmd = 2; s.tick("a");
  assert.ok(s.draw().some(t => t.label === ":1"), "item label shows unreserved stock");
  s.tick("a"); b.target = 1; s.tick("a"); assert.equal(b.acts.length, 2);
  b.phase = "act"; b.acts.forEach(a => c.api.doAction(a));
  assert.equal(c.bag["Herb Tonic"], 0); assert.equal(c.party[0].hp - hp[0], 120); assert.equal(c.party[1].hp - hp[1], 120);
});
check("old duplicate actions still cannot heal twice with one item", () => {
  const s = session(), c = s.c, b = c.api.getBattle(); b.phase = "act"; c.bag["Herb Tonic"] = 1;
  c.party[0].hp -= 130; c.party[2].hp -= 130; c.api.doAction(itemAction(s, "Herb Tonic", 0));
  const before = resources(s); c.api.doAction(itemAction(s, "Herb Tonic", 2)); assertRefused(s, "Herb Tonic", before, 0);
});
for (const stock of [0, undefined, -1, 1.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
  for (const name of ["Herb Tonic", "Clear Draught", "Antidote Leaf", "Feather of Waking", "Smoke Pouch"]) {
    check(name + " refuses stale/invalid stock " + stock + " before any effect", () => {
      const s = session(), c = s.c, b = c.api.getBattle(); b.phase = "act"; c.bag[name] = stock;
      c.party[0].hp = name === "Feather of Waking" ? 0 : c.party[0].max - 130;
      c.party[0].mp = 0; c.party[0].status = { poison: true }; const before = resources(s);
      c.api.doAction(itemAction(s, name)); assertRefused(s, name, before, stock);
    });
  }
}
check("ordinary MP, cure and revive items retain their effects and single consumption", () => {
  const s = session(), c = s.c, b = c.api.getBattle(); b.phase = "act";
  c.bag["Clear Draught"] = 1; c.party[2].mp = 0; c.api.doAction(itemAction(s, "Clear Draught", 2));
  assert.equal(c.party[2].mp, 60); assert.equal(c.bag["Clear Draught"], 0);
  c.bag["Antidote Leaf"] = 1; c.party[0].status = { poison: true }; c.api.doAction(itemAction(s, "Antidote Leaf"));
  assert.equal(c.party[0].status.poison, undefined); assert.equal(c.bag["Antidote Leaf"], 0);
  c.bag["Feather of Waking"] = 1; c.party[0].hp = 0; c.api.doAction(itemAction(s, "Feather of Waking"));
  assert.equal(c.party[0].hp, Math.ceil(c.party[0].max / 4)); assert.equal(c.bag["Feather of Waking"], 0);
});
check("stocked smoke escapes field fights, but still cannot escape a Warden", () => {
  const s = session(), c = s.c, b = c.api.getBattle(); b.phase = "act"; c.bag["Smoke Pouch"] = 1;
  c.api.doAction(itemAction(s, "Smoke Pouch")); assert.equal(b.phase, "end"); assert.equal(b.result, "run"); assert.equal(c.bag["Smoke Pouch"], 0);
  b.phase = "act"; delete b.result; b.boss = true; c.bag["Smoke Pouch"] = 1;
  const before = resources(s); c.api.doAction(itemAction(s, "Smoke Pouch"));
  assert.equal(resources(s), before); assert.equal(c.bag["Smoke Pouch"], 1); assert.match(b.msg, /DOES NOTHING/);
});
check("field tonic and tent paths retain their original behavior", () => {
  const s = session(), c = s.c; c.api.setBattle(null); c.bag["Herb Tonic"] = 1; c.party[0].hp -= 130; const hp = c.party[0].hp;
  c.api.useItem("Herb Tonic", c.party[0]); assert.equal(c.party[0].hp, hp + 120); assert.equal(c.bag["Herb Tonic"], 0);
  const before = resources(s); assert.match(c.api.useItem("Herb Tonic", c.party[0]), /NO .* LEFT/); assert.equal(resources(s), before);
  c.bag["Camp Tent"] = 1; c.map.kind = "world"; c.party[0].status = { poison: true }; c.party[2].mp = 0;
  c.api.useItem("Camp Tent", c.party[0]); assert.equal(c.party[0].hp, c.party[0].max); assert.equal(c.party[2].mp, c.party[2].mmax);
  assert.equal(c.party[0].status.poison, undefined); assert.equal(c.bag["Camp Tent"], 0); assert.equal(c.fade, 1);
});
check("field/battle item filters and refused cure/revive costs remain unchanged", () => {
  const s = session(), c = s.c; c.bag = { "Smoke Pouch": 1, "Camp Tent": 1, "Antidote Leaf": 1, "Feather of Waking": 1 };
  assert.equal(c.api.fieldItems().includes("Smoke Pouch"), false); assert.equal(c.api.battleItems().includes("Camp Tent"), false);
  c.api.setBattle(null); c.api.useItem("Antidote Leaf", c.party[0]); c.api.useItem("Feather of Waking", c.party[0]);
  assert.equal(c.bag["Antidote Leaf"], 1); assert.equal(c.bag["Feather of Waking"], 1);
});
check("normal defend, attack and magic actions remain available without items", () => {
  const s = session(), c = s.c, b = c.api.getBattle(); b.phase = "act";
  c.api.doAction({ kind: "defend", who: c.party[0] }); assert.equal(c.party[0].defend, true);
  const hp = b.foes[0].hp; c.api.doAction({ kind: "attack", who: c.party[0], target: b.foes[0] }); assert.ok(b.foes[0].hp < hp);
  const spell = c.D.spells.find(sp => sp.name === "Mend"), mp = c.party[1].mp; c.party[0].hp -= 100;
  c.api.doAction({ kind: "magic", who: c.party[1], target: c.party[0], spell }); assert.equal(c.party[1].mp, mp - spell.mp);
});
check("reservation assertion detects the old planner predicate", () => {
  const old = source.replace('const battleItems = () => bagItems().filter(k => itemKind(k) !== "camp" && battleItemStock(k) > 0);',
    'const battleItems = () => bagItems().filter(k => itemKind(k) !== "camp");');
  assert.notEqual(old, source); const s = session(old); s.c.bag["Herb Tonic"] = 1; choose(s, "Herb Tonic");
  assert.throws(() => assert.equal(s.c.api.battleItems().includes("Herb Tonic"), false), /true.*false|Expected/);
});
check("resource preservation assertion detects a broken execution stock guard", () => {
  const old = source.replace('const itemStock = name => Number.isSafeInteger(bag[name]) && bag[name] > 0 ? bag[name] : 0;', 'const itemStock = name => 1;');
  assert.notEqual(old, source); const s = session(old), b = s.c.api.getBattle(); b.phase = "act"; s.c.bag["Herb Tonic"] = 0; s.c.party[0].hp -= 130;
  const before = resources(s); s.c.api.doAction(itemAction(s, "Herb Tonic"));
  assert.throws(() => assertRefused(s, "Herb Tonic", before, 0), /party resources|counter/);
});
console.log("Prismheart battle items: " + checks + " focused checks passed");
