// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/equipment_menu_test.js
// Runs actual menuTick/drawEquip/factory functions against the real party/shop catalogs.
// No browser, game loop, art generation, real storage or production data writes.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const partyData = data("party").party.prism;
const interiors = data("interiors").interiors;
const gear = {};
// Same source catalog union as build_demo.py: Prism's armour uses Portal's shop numbers.
for (const realm of ["portal", "prism"]) for (const shop of Object.values(interiors[realm])) {
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
}
const clone = value => JSON.parse(JSON.stringify(value));
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start);
  return html.slice(a, b);
}
const source = [
  html.split(/\r?\n/).find(line => line.startsWith("function clearActionButtons()")),
  html.split(/\r?\n/).find(line => line.startsWith("const START_LEVEL =")),
  html.split(/\r?\n/).find(line => line.startsWith("const ACTIVE =")),
  html.split(/\r?\n/).find(line => line.startsWith("const roster =")),
  between("function makeMember(", "/* Recruits:"),
  between("const atkOf =", "/* ---------- maps"),
  between("let menu = null;", "function useItem("),
  between("function drawEquipmentFitting()", "/* ---------- statuses"),
  "this.api = { makeMember, menuTick, drawEquip, equipCandidates, getMenu: () => menu, setMenu: value => { menu = value; } };"
].join("\n");
function session(productionSource = source) {
  const pressed = new Set(), draws = [];
  const c = {
    D: { party: clone(partyData) }, GEAR: clone(gear), party: [], reserve: [],
    bag: clone(partyData.start_items), gold: partyData.start_gold, mode: "menu", W: 320, H: 224,
    clamp: (n, low, high) => Math.max(low, Math.min(high, n)),
    hit: key => { const v = pressed.has(key); pressed.delete(key); return v; },
    sfx() {}, win() {}, tw: s => String(s).length * 6, titlePrompt: (_action, fallback) => "PRESS " + fallback,
    g: { fillStyle: "", fillRect() {} },
    text: (label, x, y) => { draws.push({ kind: "text", label: String(label), x, y }); },
    cursor: (x, y) => { draws.push({ kind: "cursor", x, y }); }
  };
  vm.createContext(c);
  vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, 15));
  return { c, draws,
    tick: (...keys) => { pressed.clear(); keys.forEach(k => pressed.add(k)); c.api.menuTick(); pressed.clear(); },
    draw: () => { draws.length = 0; c.api.drawEquip(); return draws; } };
}
const slots = ["weapon", "armor", "helm", "shield"];
function enter(s, who, slot) {
  s.c.api.setMenu({ idx: 2, sub: "equip", who, ii: slots.indexOf(slot), ci: 0, msg: "" });
  s.tick("a");
}
function inventory(s) { return JSON.stringify({ bag: s.c.bag, equip: s.c.party.concat(s.c.reserve).map(m => m.equip) }); }
function soundInventory(s) {
  assert.equal(Object.hasOwn(s.c.bag, "undefined"), false, "no undefined inventory key");
  assert.ok(Object.values(s.c.bag).every(n => Number.isFinite(n) && n >= 0), "all inventory counts stay finite");
  for (const m of s.c.party.concat(s.c.reserve)) for (const slot of slots) {
    assert.ok(Object.hasOwn(m.equip, slot), "equipment slot remains serializable");
    assert.ok(m.equip[slot] === null || typeof m.equip[slot] === "string", "equipment never becomes undefined");
  }
}
for (const who of [1, 2, 3]) for (const slot of ["helm", "shield"]) {
  check(partyData.members[who].name + " fresh empty " + slot + " refuses safely", () => {
    const s = session(), before = inventory(s);
    assert.equal(s.c.party[who].equip[slot], null);
    enter(s, who, slot); s.tick("a");
    assert.equal(s.c.api.getMenu().sub, "equip"); assert.match(s.c.api.getMenu().msg, /NO GEAR FITS/);
    assert.equal(inventory(s), before); assert.equal(s.c.party[who].equip[slot], null);
    assert.ok(Number.isInteger(s.c.api.getMenu().ci));
    assert.ok(s.draw().every(d => Number.isFinite(d.x) && Number.isFinite(d.y)));
    soundInventory(s);
  });
}
check("successful swap returns the old weapon and spends exactly one candidate", () => {
  const s = session(); s.c.bag["Steel Saber"] = 2; enter(s, 0, "weapon");
  assert.equal(s.c.api.getMenu().sub, "equip-pick"); s.tick("a");
  assert.equal(s.c.party[0].equip.weapon, "Steel Saber"); assert.equal(s.c.bag["Steel Saber"], 1);
  assert.equal(s.c.bag["Copper Blade"], 1); assert.equal(s.c.api.getMenu().sub, "equip");
  assert.equal(s.c.api.getMenu().equipChoice, undefined); soundInventory(s);
});
check("take-off returns exactly one equipped shield", () => {
  const s = session(); enter(s, 0, "shield"); s.tick("a");
  assert.equal(s.c.party[0].equip.shield, null); assert.equal(s.c.bag["Kite Shield"], 1); soundInventory(s);
});
check("cancel after preview preserves every inventory/equipment value", () => {
  const s = session(); s.c.bag["Steel Saber"] = 1; const before = inventory(s);
  enter(s, 0, "weapon"); s.tick("down"); s.draw(); s.tick("b");
  assert.equal(inventory(s), before); assert.equal(s.c.api.getMenu().sub, "equip"); soundInventory(s);
});
check("simultaneous back and confirm cancels without applying a choice", () => {
  const s = session(); s.c.bag["Steel Saber"] = 1; enter(s, 0, "weapon"); const before = inventory(s);
  s.tick("a", "b"); assert.equal(inventory(s), before); assert.equal(s.c.api.getMenu().sub, "equip");
});
for (const value of [undefined, NaN, Infinity, -1, 0.5, 1000000]) check("invalid candidate cursor " + value + " preserves gear", () => {
  const s = session(); s.c.bag["Steel Saber"] = 1; enter(s, 0, "weapon");
  s.c.api.getMenu().ci = value; const before = inventory(s);
  assert.ok(s.draw().every(d => Number.isFinite(d.x) && Number.isFinite(d.y)), "invalid cursor never renders NaN");
  s.tick("a"); assert.equal(inventory(s), before); assert.equal(s.c.api.getMenu().sub, "equip");
  assert.match(s.c.api.getMenu().msg, /CHOOSE THE SLOT AGAIN/); soundInventory(s);
});
const stale = [
  ["selected inventory item disappeared", s => { delete s.c.bag["Steel Saber"]; }],
  ["candidate list gained an item", s => { s.c.bag["Copper Blade"] = 1; }],
  ["equipped item changed", s => { s.c.party[0].equip.weapon = "Oak Staff"; }],
  ["companion changed", s => { s.c.api.getMenu().who = 2; }],
  ["slot changed", s => { s.c.api.getMenu().slot = "armor"; }],
  ["choice record missing", s => { delete s.c.api.getMenu().equipChoice; }],
  ["candidate count became invalid", s => { s.c.bag["Steel Saber"] = Infinity; }],
  ["candidate count became fractional", s => { s.c.bag["Steel Saber"] = 0.5; }],
  ["candidate count became unsafe", s => { s.c.bag["Steel Saber"] = Number.MAX_SAFE_INTEGER + 1; }]
];
for (const [label, change] of stale) check(label + " refuses the stale confirmation", () => {
  const s = session(); s.c.bag["Steel Saber"] = 1; enter(s, 0, "weapon"); change(s); const before = inventory(s);
  s.tick("a"); assert.equal(inventory(s), before); assert.equal(s.c.api.getMenu().sub, "equip");
  assert.match(s.c.api.getMenu().msg, /CHOOSE THE SLOT AGAIN/);
});
check("ordinary weapon restrictions stay unchanged", () => {
  const s = session(); s.c.bag["Silver Lance"] = 1;
  assert.equal(s.c.api.equipCandidates(s.c.party[0], "weapon").includes("Silver Lance"), false);
});
check("a larger future bag scrolls inside the existing candidate window", () => {
  const s = session();
  // Synthetic extra armour only stresses list length; no production catalog or stats are changed.
  for (let i = 0; i < 8; i++) { const name = "Test Mail " + i; s.c.GEAR[name] = { defence: i }; s.c.bag[name] = 1; }
  enter(s, 0, "armor"); s.tick("up");
  const ds = s.draw(), rows = ds.filter(d => d.kind === "text" && d.x === 26 && d.y >= 54 && d.y <= 134);
  assert.equal(rows.length, 6); assert.equal(rows.at(-1).label, "TAKE OFF");
  assert.ok(rows.every(d => d.y < 148), "six rows leave room for the range and full selected-item footer");
  assert.ok(ds.some(d => d.kind === "text" && /\/9$/.test(d.label)), "visible range is shown");
  assert.ok(ds.some(d => d.kind === "cursor" && d.x === 14 && d.y === 134), "selected last choice remains visible");
  const before = inventory(s); s.tick("b"); assert.equal(inventory(s), before);
});
check("regression detects the former empty-list confirmation path", () => {
  const begin = source.indexOf('  if (sub === "equip") {'), end = source.indexOf('  if (sub === "fish")', begin);
  assert.ok(begin >= 0 && end > begin);
  const old = `  if (sub === "equip") {
    if (hit("a")) { menu.sub = "equip-pick"; menu.slot = SLOTS[menu.ii]; menu.ci = 0; }
    return;
  }
  if (sub === "equip-pick") {
    const m = roster()[menu.who], cands = equipCandidates(m, menu.slot);
    menuMove("ci", cands.length);
    if (hit("a")) {
      const pick = cands[menu.ci], old = m.equip[menu.slot];
      if (pick === null) { if (old) { bag[old] = (bag[old] || 0) + 1; m.equip[menu.slot] = null; } }
      else { if (old) bag[old] = (bag[old] || 0) + 1; bag[pick]--; if (!bag[pick]) delete bag[pick]; m.equip[menu.slot] = pick; }
    }
    return;
  }
`;
  const s = session(source.slice(0, begin) + old + source.slice(end)); enter(s, 2, "helm"); s.tick("a");
  assert.throws(() => soundInventory(s), /undefined|finite/, "controlled pre-fix defect is caught without file changes");
});
console.log("Prismheart equipment menu: " + checks + " focused checks passed");
