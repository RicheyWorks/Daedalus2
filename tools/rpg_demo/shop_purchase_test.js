// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/shop_purchase_test.js
// Uses production party, chest, shop and sell functions with the authored realm catalogs.
// No browser, game loop, storage, asset generation or production data writes.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const parties = data("party").party, interiors = data("interiors").interiors;
const towns = data("town-tiles").demo_towns, spells = data("spells").spells;
const clone = value => JSON.parse(JSON.stringify(value));
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start);
  return html.slice(a, b);
}
function line(prefix) {
  const found = html.split(/\r?\n/).find(s => s.startsWith(prefix));
  assert.ok(found, "production declaration exists: " + prefix); return found;
}
const source = [
  between("const START_LEVEL =", "/* Recruits:"), line("const spellOf ="), line("const WEAPON_KIND ="),
  between("function openChest(", "/* ---------- shops"), between("let shop = null;", "function drawShop()"),
  "this.api = { start: () => { party = buildParty(); }, makeMember, openChest, openShop, buy, sellPrice, sellList, shopTick, " +
  "getParty: () => party, getReserve: () => reserve, getBag: () => bag, getGold: () => gold, setGold: n => { gold = n; }, getShop: () => shop };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(realm, productionSource = source) {
  const gear = {}, pressed = new Set(), sounds = [], messages = [];
  // Same catalog projection as build_demo.py: Portal gear, followed by this realm's shop gear.
  for (const key of ["portal", realm]) for (const shop of Object.values(interiors[key])) {
    for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
  }
  const c = {
    D: { party: clone(parties[realm]), gear: clone(gear), interiors: clone(interiors[realm]),
      spells: clone(spells.filter(s => s.realm === realm)), ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    map: { kind: "town", grid: clone(towns[realm].grid) }, opened: new Set(), mode: "field",
    sfx: sound => sounds.push(sound), say: pages => messages.push(...pages),
    hit: key => { const found = pressed.has(key); pressed.delete(key); return found; },
    clamp: (n, low, high) => Math.max(low, Math.min(high, n))
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.api.start();
  return { c, api: c.api, sounds, messages,
    tick: (...keys) => { pressed.clear(); keys.forEach(k => pressed.add(k)); c.api.shopTick(); pressed.clear(); } };
}
function enter(s, store) {
  s.c.map = { kind: "interior", name: store, info: s.c.D.interiors[store] }; s.api.openShop();
}
function buy(s, store, name) {
  enter(s, store); const item = s.api.getShop().stock.find(it => it.name === name);
  assert.ok(item, "authored shop stocks " + name); s.api.buy(item);
}
function totals(s) {
  const counts = {};
  for (const [name, n] of Object.entries(s.api.getBag())) if (n > 0) counts[name] = n;
  for (const member of s.api.getParty().concat(s.api.getReserve())) for (const name of Object.values(member.equip)) {
    if (name !== null) { assert.equal(typeof name, "string"); counts[name] = (counts[name] || 0) + 1; }
  }
  assert.equal(Object.hasOwn(counts, "undefined"), false); assert.equal(Object.hasOwn(counts, "null"), false);
  return counts;
}
function purchaseConserved(s, before, name, count = 1) {
  const expected = { ...before, [name]: (before[name] || 0) + count };
  assert.deepEqual(totals(s), expected, "bag plus equipped items change only by the purchased stock");
}
function snapshot(s) {
  return JSON.stringify({ gold: s.api.getGold(), bag: s.api.getBag(), equip: s.api.getParty().map(m => m.equip) });
}
function portalChest(s) {
  assert.equal(s.c.map.grid[1][20], "Chest", "the authored Portal town chest is at 20,1");
  assert.equal(s.api.getGold(), 120); s.api.openChest(20, 1); assert.equal(s.api.getGold(), 220);
  assert.equal(s.c.map.grid[1][20], "ChestOpen"); s.api.openChest(20, 1); assert.equal(s.api.getGold(), 220, "chest pays only once");
}
check("Portal's ordinary chest-to-armour purchase preserves Mirel's vest", () => {
  const s = session("portal"); portalChest(s); const before = totals(s);
  buy(s, "Armor", "Ring Mail"); const p = s.api.getParty();
  assert.equal(s.api.getGold(), 40); assert.equal(p[0].equip.armor, "Ring Mail");
  assert.equal(p[1].name, "Mirel"); assert.equal(p[1].equip.armor, "Ring Mail"); assert.equal(p[2].equip.armor, "Padded Vest");
  assert.equal(s.api.getBag()["Padded Vest"], 1); assert.ok(s.api.sellList().includes("Padded Vest")); assert.equal(s.api.sellPrice("Padded Vest"), 22);
  assert.equal(s.api.getShop().msg, "Mirel PUTS ON THE RING MAIL."); purchaseConserved(s, before, "Ring Mail");
});
check("the preserved vest can be sold through the existing shop interaction", () => {
  const s = session("portal"); portalChest(s); buy(s, "Armor", "Ring Mail"); s.tick("right");
  assert.equal(s.api.getShop().tab, "sell"); s.api.getShop().idx = s.api.sellList().indexOf("Padded Vest"); s.tick("a");
  assert.equal(s.api.getGold(), 62); assert.equal(s.api.getBag()["Padded Vest"], 0);
  assert.equal(s.api.sellList().includes("Padded Vest"), false); assert.equal(s.api.getShop().msg, "SOLD PADDED VEST FOR 22 G.");
});
check("Prism's weapon upgrade preserves the old blade and original buyer choice", () => {
  const s = session("prism"); s.api.setGold(480); const before = totals(s); buy(s, "Weapon", "Steel Saber");
  assert.equal(s.api.getParty()[0].name, "Corin"); assert.equal(s.api.getParty()[0].equip.weapon, "Steel Saber");
  assert.equal(s.api.getParty()[3].equip.weapon, "Copper Blade"); assert.equal(s.api.getBag()["Copper Blade"], 1);
  assert.equal(s.api.getGold(), 0); assert.equal(s.api.sellPrice("Copper Blade"), 30);
  assert.equal(s.api.getShop().msg, "Corin EQUIPS THE STEEL SABER."); purchaseConserved(s, before, "Steel Saber");
});
check("consecutive weapon purchases upgrade the next hero, then put surplus in the bag", () => {
  const s = session("prism"); s.api.setGold(1440); const before = totals(s);
  for (let i = 0; i < 3; i++) buy(s, "Weapon", "Steel Saber");
  assert.equal(s.api.getParty()[0].equip.weapon, "Steel Saber"); assert.equal(s.api.getParty()[3].equip.weapon, "Steel Saber");
  assert.equal(s.api.getBag()["Copper Blade"], 2); assert.equal(s.api.getBag()["Steel Saber"], 1); assert.equal(s.api.getGold(), 0);
  assert.equal(s.api.getShop().msg, "NO ONE NEEDS IT. INTO THE BAG."); purchaseConserved(s, before, "Steel Saber", 3);
});
for (const [realm, store, item, old] of [["portal", "Armor", "Ring Mail", "Padded Vest"], ["prism", "Weapon", "Steel Saber", "Copper Blade"]]) {
  check("existing bag counts accumulate once for " + old, () => {
    const s = session(realm); s.api.setGold(1000); s.api.getBag()[old] = 3; const before = totals(s); buy(s, store, item);
    assert.equal(s.api.getBag()[old], 4); purchaseConserved(s, before, item);
  });
}
for (const [store, item, price] of [["Weapon", "Copper Blade", 60], ["Armor", "Padded Vest", 45]]) {
  check("a no-upgrade " + item + " purchase goes to the bag", () => {
    const s = session("portal"), before = totals(s), equipment = JSON.stringify(s.api.getParty().map(m => m.equip)); buy(s, store, item);
    assert.equal(JSON.stringify(s.api.getParty().map(m => m.equip)), equipment); assert.equal(s.api.getBag()[item], 1);
    assert.equal(s.api.getGold(), 120 - price); purchaseConserved(s, before, item);
  });
}
check("insufficient funds leave money and all equipment/inventory untouched", () => {
  const s = session("portal"); s.api.setGold(179); const before = snapshot(s); buy(s, "Armor", "Ring Mail");
  assert.equal(snapshot(s), before); assert.equal(s.api.getShop().msg, "NOT ENOUGH GOLD."); assert.equal(s.sounds.includes("BUY"), false);
});
check("an empty shield slot gains its purchase without inventing an old item", () => {
  const s = session("portal"); s.api.getParty()[0].equip.shield = null; s.api.setGold(150); const before = totals(s);
  buy(s, "Armor", "Kite Shield"); assert.equal(s.api.getParty()[0].equip.shield, "Kite Shield"); purchaseConserved(s, before, "Kite Shield");
});
check("consumable purchases retain their price and bag behavior", () => {
  const s = session("portal"), before = totals(s), n = s.api.getBag()["Herb Tonic"]; buy(s, "Item", "Herb Tonic");
  assert.equal(s.api.getBag()["Herb Tonic"], n + 1); assert.equal(s.api.getGold(), 112); assert.equal(s.api.getShop().msg, "THANK YOU!");
  purchaseConserved(s, before, "Herb Tonic");
});
const preFix = source.replace(/const old = who\.equip(?:\.weapon|\[slot\]); if \(old\) bag\[old\] = \(bag\[old\] \|\| 0\) \+ 1; /g, "");
assert.notEqual(preFix, source, "the controlled pre-fix removes the production preservation statements");
for (const [realm, store, item] of [["portal", "Armor", "Ring Mail"], ["prism", "Weapon", "Steel Saber"]]) {
  check("inventory-conservation assertion detects pre-fix " + store + " loss", () => {
    const s = session(realm, preFix); s.api.setGold(1000); const before = totals(s); buy(s, store, item);
    assert.throws(() => purchaseConserved(s, before, item), /bag plus equipped items/);
  });
}
console.log("Prismheart/Portal shop purchases: " + checks + " focused checks passed");
