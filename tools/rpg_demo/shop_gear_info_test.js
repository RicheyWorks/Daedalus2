// SPDX-License-Identifier: MIT
// Focused offline check: node --max-old-space-size=128 tools/rpg_demo/shop_gear_info_test.js
// Actual shop drawing/purchases, recruit/ORDER and stat functions with authored catalogs; no browser/assets/boot.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value)), parties = data("party").party, interiors = data("interiors").interiors;
const spells = data("spells").spells, menus = data("menus").layouts, gear = {};
for (const realm of ["portal", "prism"]) for (const store of Object.values(interiors[realm]))
  for (const item of store.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"),
  between("const START_LEVEL =", "/* Recruits:"), between("function recruitsFor(", "function recruitBeaten("),
  line("const atkOf ="), line("const defOf ="), line("const spellOf ="),
  between("let menu = null;", "function drawPartyRows("), between("let shop = null;", "/* ---------- field ---------- */"),
  between("function spellHint(", "function drawBattle("),
  "this.api = { start: () => { party = buildParty(); }, recruit, roster, openShop, shopTick, drawShop, buy, shopGearChoice, atkOf, defOf, atkWith, defWith, " +
  "openMenu, menuTick, party: () => party, reserve: () => reserve, bag: () => bag, shop: () => shop, menu: () => menu, commands: MENU_CMDS, " +
  "gold: () => gold, setGold: n => { gold = n; }, chars: CHARS, snapshot: () => ({ party, reserve, bag, gold, shop, menu, data: D, pressed }) };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, realm = "prism", productionSource = source) {
  const draws = [], sounds = [], pressed = { a: false, b: false, start: false, up: false, down: false, left: false, right: false };
  const c = { D: { party: clone(parties[realm]), gear: clone(gear), interiors: clone(interiors[realm]), menus: clone(menus[realm]),
      spells: clone(spells.filter(sp => sp.realm === realm)), ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, B: null, map: { kind: "interior" }, mode: "field", pressed, state: { beaten: new Set() },
    drawField() {}, say() {}, sfx: sound => sounds.push(sound), g: { fillStyle: "", fillRect() {} },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: label => String(label).length * 6,
    win: (...rect) => draws.push({ kind: "window", rect }), cursor: (x, y) => draws.push({ kind: "cursor", x, y }),
    text: (label, x, y, color = "#ffffff") => draws.push({ kind: "text", label: String(label).toUpperCase(), x, y, color }),
    localStorage: { getItem() { throw new Error("preview must not read saves"); }, setItem() { throw new Error("preview must not save"); } } };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.api.start(); c.api.setGold(50000);
  return { c, api: c.api, draws, sounds,
    enter(store = "Weapon") { c.map.info = c.D.interiors[store]; assert.ok(c.map.info); c.api.openShop(); return this; },
    shopTick(...keys) { keys.forEach(key => { pressed[key] = true; }); c.api.shopTick(); },
    menuTick(...keys) { keys.forEach(key => { pressed[key] = true; }); c.api.menuTick(); },
    draw() { draws.length = 0; const before = JSON.stringify(c.api.snapshot()), count = sounds.length; c.api.drawShop();
      assert.equal(JSON.stringify(c.api.snapshot()), before, "preview preserves roster, gear, bag, gold, selection, catalog and input");
      assert.equal(sounds.length, count, "rendering emits no purchase sounds"); return draws; } };
}
function select(s, name) {
  const shop = s.api.shop(), index = shop.stock.findIndex(item => item.name === name); assert.ok(index >= 0);
  while (shop.idx !== index) s.shopTick("down"); return shop.stock[index];
}
function preview(s, name, expectedText) {
  const item = select(s, name), choice = s.api.shopGearChoice(item), raw = item.attack ? "ATTACK " + item.attack : "DEFENCE " + item.defence;
  s.draw(); const footer = s.draws.find(d => d.kind === "text" && d.x === 12 && d.y === 204); assert.ok(footer);
  if (expectedText) assert.equal(footer.label, expectedText);
  if (!choice.who) assert.equal(footer.label, raw + " / INTO BAG");
  else {
    const before = choice.slot === "weapon" ? s.api.atkOf(choice.who) : s.api.defOf(choice.who);
    const after = choice.slot === "weapon" ? s.api.atkWith(choice.who, name) : s.api.defWith(choice.who, { ...choice.who.equip, [choice.slot]: name });
    const detail = " " + (choice.slot === "weapon" ? "ATK" : "DEF") + " " + before + ">" + after;
    assert.ok(footer.label.startsWith(raw + " / ") && footer.label.endsWith(detail));
    const shown = footer.label.slice((raw + " / ").length, -detail.length);
    assert.ok(shown.length > 0 && choice.who.name.toUpperCase().startsWith(shown), "only the display recipient may be shortened");
  }
  assert.ok(footer.x + s.c.tw(footer.label) <= s.c.W - 12 && footer.y + 8 <= 212, "raw value, recipient and full stat change fit the existing footer");
  assert.ok(Array.from(footer.label).every(ch => s.api.chars.includes(ch)), "footer uses supported bitmap font glyphs");
  const shop = s.api.shop(), y = 38 + (shop.idx - shop.top) * 16;
  const row = s.draws.find(d => d.kind === "text" && d.x === 24 && d.y === y); assert.ok(row && name.toUpperCase().startsWith(row.label));
  assert.equal(row.color, item.price > s.api.gold() ? "#808090" : "#ffffff", "physical stock keeps its affordability-only color");
  assert.ok(s.draws.some(d => d.kind === "text" && d.label === String(item.price) && d.y === y && d.x === s.c.W - 102 - s.c.tw(item.price)));
  assert.ok(s.draws.some(d => d.kind === "text" && d.y === 190 && d.label === shop.msg.toUpperCase()));
  assert.ok(s.draws.some(d => d.kind === "text" && d.y === 37 && d.label === String(s.api.gold()) && d.x === s.c.W - 10 - s.c.tw(s.api.gold())));
  return { item, choice, footer };
}
function orderSwap(s, first, second) {
  s.shopTick("b"); assert.equal(s.c.mode, "field"); s.api.openMenu(); const m = s.api.menu();
  while (m.idx !== s.api.commands.indexOf("ORDER")) s.menuTick("down"); s.menuTick("a"); assert.equal(m.sub, "order");
  while (m.ii !== first) s.menuTick("down"); s.menuTick("a"); assert.equal(m.pick, first);
  while (m.ii !== second) s.menuTick("down"); s.menuTick("a"); assert.equal(m.msg, "ORDER CHANGED.");
  s.menuTick("b"); s.menuTick("b"); assert.equal(s.c.mode, "field");
}
for (const width of [320, 256]) check("Steel Saber preview follows Corin then Rook and preserves both old blades at " + width, () => {
  const s = session(width).enter(), before = s.api.bag()["Copper Blade"] || 0;
  let p = preview(s, "Steel Saber", "ATTACK 20 / CORIN ATK 54>68"), gold = s.api.gold();
  s.shopTick("a"); assert.equal(s.api.gold(), gold - p.item.price); assert.equal(s.api.party()[0].equip.weapon, "Steel Saber");
  assert.equal(s.api.atkOf(s.api.party()[0]), 68); assert.equal(s.api.bag()["Copper Blade"], before + 1);
  assert.equal(s.api.shop().msg, "Corin EQUIPS THE STEEL SABER.");
  p = preview(s, "Steel Saber", "ATTACK 20 / ROOK ATK 48>62"); gold = s.api.gold(); s.shopTick("a");
  assert.equal(s.api.gold(), gold - p.item.price); assert.equal(s.api.party()[3].equip.weapon, "Steel Saber"); assert.equal(s.api.atkOf(s.api.party()[3]), 62);
  assert.equal(s.api.bag()["Copper Blade"], before + 2); assert.equal(s.api.shop().msg, "Rook EQUIPS THE STEEL SABER.");
  preview(s, "Steel Saber", "ATTACK 20 / INTO BAG"); const count = s.api.bag()["Steel Saber"] || 0; s.shopTick("a");
  assert.equal(s.api.bag()["Steel Saber"], count + 1); assert.equal(s.api.shop().msg, "NO ONE NEEDS IT. INTO THE BAG.");
});
check("actual recruited Fennick and ORDER place the next exact recipient in reserve", () => {
  const s = session(256).enter(); select(s, "Steel Saber"); s.shopTick("a"); s.api.recruit("Cinder Forge");
  assert.equal(s.api.reserve()[0].name, "Fennick"); orderSwap(s, 3, 4); assert.equal(s.api.party()[3].name, "Fennick");
  const rook = s.api.reserve()[0]; assert.equal(rook.name, "Rook"); rook.hp = 0; s.enter();
  const p = preview(s, "Steel Saber", "ATTACK 20 / ROOK ATK 48>62"); assert.equal(p.choice.who, rook);
  const old = s.api.bag()["Copper Blade"] || 0; s.shopTick("a"); assert.equal(rook.equip.weapon, "Steel Saber");
  assert.equal(rook.hp, 0, "original autoequip selection does not filter downed reserve members"); assert.equal(s.api.bag()["Copper Blade"], old + 1);
});
for (const name of ["Copper Blade", "Hunter Bow", "Iron Axe"]) check(name + " correctly previews bag placement without inventing an eligible recruit", () => {
  const s = session(256).enter(), p = preview(s, name), before = JSON.stringify(s.api.roster().map(m => m.equip)), count = s.api.bag()[name] || 0;
  assert.equal(p.choice.who, undefined); assert.ok(!s.api.roster().some(m => m.job === "Gearwright")); const gold = s.api.gold(); s.shopTick("a");
  assert.equal(s.api.gold(), gold - p.item.price); assert.equal(s.api.bag()[name], count + 1); assert.equal(JSON.stringify(s.api.roster().map(m => m.equip)), before);
});
for (const [name, expected, slot] of [["Ring Mail", "DEFENCE 8 / MIREL DEF 6>11", "armor"], ["Tower Shield", "DEFENCE 9 / ARDEN DEF 22>26", "shield"], ["Iron Helm", "DEFENCE 4 / INTO BAG", "helm"]])
  check("real shared-browser armor selection and " + slot + " preview: " + name, () => {
    const s = session(256, "portal").enter("Armor"), p = preview(s, name, expected), who = p.choice.who, old = who && who.equip[slot], oldCount = s.api.bag()[old] || 0;
    s.shopTick("a");
    if (who) { assert.equal(who.equip[slot], name); assert.equal(s.api.bag()[old], oldCount + 1); assert.match(s.api.shop().msg, / PUTS ON THE /); }
    else { assert.equal(s.api.bag()[name], 1); assert.equal(s.api.shop().msg, "INTO THE BAG."); }
  });
check("unaffordable physical stock retains the preview but cannot change gear or bag", () => {
  const s = session().enter(); s.api.setGold(0); preview(s, "Steel Saber", "ATTACK 20 / CORIN ATK 54>68");
  const before = JSON.stringify({ roster: s.api.roster(), bag: s.api.bag() }); s.shopTick("a");
  assert.equal(s.api.gold(), 0); assert.equal(JSON.stringify({ roster: s.api.roster(), bag: s.api.bag() }), before); assert.equal(s.api.shop().msg, "NOT ENOUGH GOLD.");
});
for (const width of [320, 256]) check("all authored weapon/armor previews stay complete and inside the footer at " + width, () => {
  for (const [realm, store] of [["prism", "Weapon"], ["portal", "Armor"]]) {
    const s = session(width, realm).enter(store); for (const item of s.api.shop().stock) preview(s, item.name);
  }
});
check("only the displayed name is shortened to keep raw and total stats complete", () => {
  const s = session(256).enter(), corin = s.api.party()[0]; corin.name = "CORINTHESTALWARTBLADEWARD";
  const before = corin.name, p = preview(s, "Steel Saber"); assert.equal(corin.name, before);
  assert.ok(p.footer.label.length <= 38 && !p.footer.label.includes(before)); assert.ok(p.footer.label.endsWith(" ATK 54>68"));
});
check("controlled former raw-only physical footer fails the recipient/stat preview assertion", () => {
  const a = source.indexOf('  } else if (it.attack || it.defence) {', source.indexOf("function drawShop()")), b = source.indexOf('  text(d, 12, 204', a); assert.ok(a >= 0 && b > a);
  const legacy = source.slice(0, a) + "  }\n" + source.slice(b), s = session(320, "prism", legacy).enter();
  assert.throws(() => preview(s, "Steel Saber", "ATTACK 20 / CORIN ATK 54>68"), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; no boot, browser or game loop.
console.log("Prismheart physical shop preview checks: " + checks + " passed; full inline script compiles.");
