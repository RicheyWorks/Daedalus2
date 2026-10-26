// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/shop_cancel_test.js
// Actual shop/input/dialog/member functions and catalogs. No browser, game loop, storage or generated assets.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const party = data("party").party.prism, interiors = data("interiors").interiors, spells = data("spells").spells.filter(s => s.realm === "prism"), gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(interiors[realm]))
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const hit ="), line("function clearActionButtons()"), line("const WEAPON_KIND ="), line("const spellOf ="),
  between("const START_LEVEL =", "/* Recruits:"), between("let dlg = null;", "function wrap("),
  between("let shop = null;", "function drawShop("),
  "this.api = { start: () => { party = buildParty(); gold = 5000; }, openShop, shopTick, dialogTick, sellList, sellPrice, " +
  "party: () => party, bag: () => bag, gold: () => gold, shop: () => shop, dialog: () => dlg };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(kind = "item", tab = "buy", productionSource = source) {
  const pressed = {}, sounds = [], entry = interiors.prism[{ item: "Item", weapon: "Weapon", magic: "Magic" }[kind]];
  assert.ok(entry && entry.stock.length, "actual shop stock exists");
  const c = { D: { party: clone(party), gear: clone(gear), spells: clone(spells) }, pressed, mode: "field",
    map: { info: clone(entry) }, sfx: sound => sounds.push(sound), clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)) };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.api.start(); c.api.openShop();
  const shop = c.api.shop(); shop.tab = tab;
  if (tab === "sell") shop.idx = c.api.sellList().indexOf("Herb Tonic");
  else if (kind === "magic") shop.idx = shop.stock.findIndex(item => {
    const spell = spells.find(s => s.name === item.name), caster = spell && c.api.party().find(m => m.job === (spell.target === "ally" ? "Lightmender" : "Runecaster"));
    return caster && !caster.spells.includes(spell.name);
  });
  else if (kind === "weapon") shop.idx = shop.stock.findIndex(item => item.name === "Steel Saber");
  else shop.idx = shop.stock.findIndex(item => item.name === "Herb Tonic");
  assert.ok(shop.idx >= 0, "real purchasable/sellable entry selected"); sounds.length = 0;
  return { c, api: c.api, shop, pressed, sounds,
    tick: (...keys) => { keys.forEach(key => { pressed[key] = true; }); c.api.shopTick(); },
    farewellTick: () => c.api.dialogTick(0) };
}
const resources = s => JSON.stringify({ gold: s.api.gold(), bag: s.api.bag(), party: s.api.party(), stock: s.c.map.info.stock });
function assertCancelled(kind, tab, keys, productionSource = source) {
  const s = session(kind, tab, productionSource), before = resources(s); s.tick(...keys);
  assert.equal(resources(s), before, "exit cannot buy, sell, equip, learn, or spend gold/items");
  assert.equal(s.api.shop(), null); assert.equal(s.c.mode, "field");
  assert.deepEqual(Array.from(s.api.dialog().pages), ["COME AGAIN!"]); assert.equal(s.api.dialog().shown, 0);
  for (const key of ["a", "b", "start"]) assert.equal(s.pressed[key], false, "exit consumes action edge " + key);
  assert.deepEqual(s.sounds, ["TICK"]); s.farewellTick();
  assert.equal(s.api.dialog().shown, 0, "exiting cannot advance the farewell on the next tick");
  assert.equal(resources(s), before); return s;
}
for (const [kind, tab] of [["item", "buy"], ["weapon", "buy"], ["magic", "buy"], ["item", "sell"]])
  for (const keys of [["a", "b"], ["a", "start"], ["a", "b", "start"]])
    check(kind + " " + tab + " exit wins over " + keys.join("+"), () => assertCancelled(kind, tab, keys));
check("Confirm alone still buys exactly one catalog item", () => {
  const s = session(), item = s.shop.stock[s.shop.idx], count = s.api.bag()[item.name], gold = s.api.gold(); s.tick("a");
  assert.equal(s.api.gold(), gold - item.price); assert.equal(s.api.bag()[item.name], count + 1);
  s.tick(); assert.equal(s.api.gold(), gold - item.price); assert.equal(s.c.mode, "shop");
});
check("Confirm alone still auto-equips a real upgrade and returns replaced gear", () => {
  const s = session("weapon"), item = s.shop.stock[s.shop.idx], old = s.api.party()[0].equip.weapon, count = s.api.bag()[old] || 0, gold = s.api.gold(); s.tick("a");
  assert.equal(s.api.gold(), gold - item.price); assert.equal(s.api.party()[0].equip.weapon, item.name); assert.equal(s.api.bag()[old], count + 1);
});
check("Confirm alone still sells one item at the existing price", () => {
  const s = session("item", "sell"), bag = s.api.bag(), count = bag["Herb Tonic"], price = s.api.sellPrice("Herb Tonic"), gold = s.api.gold(); s.tick("a");
  assert.equal(bag["Herb Tonic"], count - 1); assert.equal(s.api.gold(), gold + price); assert.equal(s.c.mode, "shop");
});
check("Confirm alone still teaches the actual unknown shop spell", () => {
  const s = session("magic"), item = s.shop.stock[s.shop.idx], spell = spells.find(sp => sp.name === item.name);
  const caster = s.api.party().find(m => m.job === (spell.target === "ally" ? "Lightmender" : "Runecaster")), gold = s.api.gold(); s.tick("a");
  assert.equal(s.api.gold(), gold - item.price); assert.equal(caster.spells.filter(name => name === spell.name).length, 1);
});
check("normal left/right tabs still toggle for physical shops", () => {
  const s = session(), before = resources(s); s.tick("left"); assert.equal(s.shop.tab, "sell"); s.tick("right");
  assert.equal(s.shop.tab, "buy"); assert.equal(resources(s), before);
});
check("magic keeps its existing no-tab behavior", () => {
  const s = session("magic"), before = resources(s); s.tick("left"); s.tick("right");
  assert.equal(s.shop.tab, "buy"); assert.equal(resources(s), before);
});
check("empty SELL exits safely without manufacturing a transaction", () => {
  const s = session("item", "sell"); for (const name of Object.keys(s.api.bag())) delete s.api.bag()[name];
  const before = resources(s); s.tick("a", "b", "start");
  assert.equal(s.api.shop(), null); assert.equal(s.c.mode, "field"); assert.equal(resources(s), before);
  s.farewellTick(); assert.equal(s.api.dialog().shown, 0);
});
check("idle and unrelated input do not change transactions or selections", () => {
  const s = session(), before = resources(s), selection = JSON.stringify(s.shop); s.tick(); s.tick("unrelated");
  assert.equal(resources(s), before); assert.equal(JSON.stringify(s.shop), selection); assert.equal(s.c.mode, "shop");
});
check("controlled late-exit variants fail the same buy/sell/magic assertions", () => {
  const guard = '  if (hit("b") || hit("start")) { clearActionButtons(); sfx("TICK"); shop = null; mode = "field"; say(["COME AGAIN!"]); return; }';
  assert.ok(source.includes(guard)); let legacy = source.replace(guard, "");
  const late = 'if (hit("b") || hit("start")) { sfx("TICK"); shop = null; mode = "field"; say(["COME AGAIN!"]); }';
  const sellTail = /    return;\r?\n  }\r?\n  const n = shop.stock.length;/;
  assert.ok(sellTail.test(legacy)); legacy = legacy.replace(sellTail, tail => "    " + late + "\n" + tail);
  const buyLine = '  if (hit("a")) buy(shop.stock[shop.idx]);'; assert.ok(legacy.includes(buyLine));
  legacy = legacy.replace(buyLine, buyLine + "\n  " + late);
  for (const [kind, tab] of [["item", "buy"], ["weapon", "buy"], ["magic", "buy"], ["item", "sell"]])
    assert.throws(() => assertCancelled(kind, tab, ["a", "b"], legacy), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute boot or DOM work.
console.log("Prismheart shop cancel checks: " + checks + " passed; full inline script compiles.");
