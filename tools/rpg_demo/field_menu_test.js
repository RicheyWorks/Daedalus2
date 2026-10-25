// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/field_menu_test.js
// Captures production field menu drawing/navigation with real party, item, fish and spell catalogs.
// No browser, game loop, storage, builds, asset generation or production data writes.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const parties = data("party").party, interiors = data("interiors").interiors, spells = data("spells").spells;
const menus = data("menus").layouts, fish = data("prism-fish").fish;
const clone = value => JSON.parse(JSON.stringify(value));
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
function line(prefix) {
  const found = html.split(/\r?\n/).find(s => s.startsWith(prefix));
  assert.ok(found, "production declaration exists: " + prefix); return found;
}
const source = [
  line("function clearActionButtons()"),
  between("const START_LEVEL =", "/* Recruits:"), line("const spellOf ="),
  between("let menu = null;", "function drawStatus()"), between("const STATUS =", "/* ---------- bestiary"),
  between("function spellHint(", "function drawBattle("), between("function titlePrompt(", "function drawTitle("),
  "this.api = { start: () => { party = buildParty(); }, openMenu, menuTick, drawMenu, fieldItems, fieldSpells, itemLine, " +
  "getParty: () => party, getBag: () => bag, getMenu: () => menu };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(realm = "prism", productionSource = source) {
  const gear = {}, pressed = new Set(), draws = [];
  for (const key of ["portal", realm]) for (const shop of Object.values(interiors[key])) {
    for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
  }
  if (realm === "prism") for (const f of fish) gear[f.name] = { name: f.name, effect: f.effect, price: f.price, fish: true };
  const known = new Set(parties[realm].members.flatMap(m => m.spells));
  const c = {
    D: { realm_key: realm, party: clone(parties[realm]), gear: clone(gear), menus: clone(menus[realm]),
      spells: clone(spells.filter(s => s.realm === realm && (s.tier <= 2 || known.has(s.name)))),
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: realm === "portal" ? 256 : 320, H: 224, PAD: null, map: { kind: "town" }, B: null,
    drawField() {}, spr() {}, gauge() {}, shardCount: () => 0, clockText: () => "08:00", isNight: () => false,
    sfx() {}, clamp: (n, low, high) => Math.max(low, Math.min(high, n)), tw: s => String(s).length * 6,
    hit: key => { const found = pressed.has(key); pressed.delete(key); return found; },
    win: (...rect) => draws.push({ kind: "window", rect }),
    text: (label, x, y, color = "#ffffff") => draws.push({ kind: "text", label: String(label), x, y, color }),
    cursor: (x, y) => draws.push({ kind: "cursor", x, y }),
    g: { fillStyle: "", fillRect() {} }
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.api.start();
  return { c, api: c.api, draws,
    tick: (...keys) => { pressed.clear(); keys.forEach(k => pressed.add(k)); c.api.menuTick(); pressed.clear(); },
    draw: () => { draws.length = 0; c.api.drawMenu(); return draws; } };
}
function fullBag(s) {
  // Every entry is obtainable from the real item shop or Windmere's fishing table.
  for (const it of interiors.prism.Item.stock) if (!(s.api.getBag()[it.name] > 0)) s.api.getBag()[it.name] = 1;
  for (const f of fish) s.api.getBag()[f.name] = 1;
}
function openItems(s) { s.api.openMenu(); s.tick("a"); return s.api.getMenu(); }
function openMagic(s, who) {
  s.api.openMenu(); s.tick("down"); s.tick("a"); const m = s.api.getMenu();
  for (let i = 0; i < s.api.getParty().length && m.who !== who; i++) s.tick("right");
  assert.equal(m.who, who); s.tick("a"); return m;
}
function purchasable(s, target) {
  return interiors.prism.Magic.stock.map(it => s.c.D.spells.find(sp => sp.name === it.name)).filter(sp => sp && (sp.target === "ally") === (target === "ally"));
}
function longCaster(s) {
  const caster = s.api.getParty()[2];
  for (const sp of purchasable(s, "enemy")) if (!caster.spells.includes(sp.name)) caster.spells.push(sp.name);
  return caster;
}
function windowShown(s, entries, index, kind = "item", listCursor = true) {
  const draws = s.draw(), names = entries.map(e => kind === "item" ? e.slice(0, 18) : e.name);
  const menu = s.api.getMenu();
  if (kind === "item" && menu.sub === "item" && s.c.D.realm_key === "prism") {
    const selected = Math.max(0, Math.min(index, entries.length - 1));
    const rows = draws.filter(d => d.kind === "text" && d.x === 24 && d.y >= 62);
    assert.equal(rows.length, Math.min(6, entries.length), "at most six list rows are visible");
    assert.ok(rows.every(d => d.y <= 152 && d.y + 8 <= 160), "row glyphs stay inside the pack viewport");
    const cursors = draws.filter(d => d.kind === "cursor" && d.x === 12); assert.equal(cursors.length, entries.length ? 1 : 0);
    const row = cursors.length ? rows.find(d => d.y === cursors[0].y) : undefined;
    if (entries.length) {
      assert.ok(row && entries[selected].toUpperCase().startsWith(row.label.replace(/\.\.\.$/, "")), "selected entry remains visible");
      assert.ok(draws.some(d => d.kind === "text" && d.x === 12 && d.y === 10 && d.label === entries[selected].toUpperCase()), "full selected name stays in the header");
      assert.ok(draws.some(d => d.kind === "text" && d.y === row.y && d.label === ":" + s.api.getBag()[entries[selected]]));
    }
    assert.ok(draws.some(d => d.kind === "cursor" && d.x === Math.floor(s.c.W / 2) + 12 && d.y === 62 + menu.who * 14), "whole-roster cursor stays visible beside the bag");
    assert.equal(draws.some(d => d.kind === "window" && d.rect.join() === [20,60,220,112].join()), false);
    return { draws, rows, row };
  }
  if (kind === "magic" && menu.sub === "magic-target" && s.c.D.realm_key === "prism") {
    assert.ok(draws.some(d => d.kind === "text" && d.x === 12 && d.y === 10 && d.label === entries[index].name.toUpperCase()));
    assert.ok(draws.some(d => d.kind === "text" && d.y === 10 && d.label === entries[index].mp + " MP"));
    assert.ok(draws.some(d => d.kind === "cursor" && d.x === 12 && d.y === 50 + menu.target * 16), "full target picker follows the same selected companion");
    assert.equal(menu.ii, index, "targeting preserves the original spell index");
    assert.equal(draws.some(d => d.kind === "window" && d.rect.join() === [20,60,220,112].join()), false, "spell popup no longer obscures target rows");
    return { draws, rows: [], row: undefined };
  }
  const rows = draws.filter(d => d.kind === "text" && d.x === 40 && names.includes(d.label));
  assert.equal(rows.length, Math.min(6, entries.length), "at most six list rows are visible");
  assert.ok(rows.every(d => d.y >= 72 && d.y <= 137 && d.y + 8 <= 145), "row glyphs and shadows stay above the range cue");
  const selected = Math.max(0, Math.min(index, entries.length - 1)), row = rows.find(d => d.label === names[selected]);
  if (entries.length) assert.ok(row, "selected entry remains visible");
  const cursors = draws.filter(d => d.kind === "cursor" && d.x === 28);
  assert.equal(cursors.length, entries.length && listCursor ? 1 : 0);
  if (cursors.length) assert.equal(cursors[0].y, row.y, "list cursor follows the visible selected row");
  const range = draws.find(d => d.kind === "text" && d.x === 28 && d.y === 145);
  if (entries.length > 6) {
    const from = Math.max(0, Math.min(selected - 5, entries.length - 6));
    assert.equal(range && range.label, (from + 1) + "-" + (from + 6) + "/" + entries.length);
  } else assert.equal(range, undefined, "short lists need no range cue");
  if (kind === "item" && entries.length) {
    const name = entries[selected], n = s.api.getBag()[name];
    assert.ok(draws.some(d => d.kind === "text" && d.label === ":" + n && d.y === row.y), "selected count stays on its row");
    assert.ok(draws.some(d => d.kind === "text" && d.x === 28 && d.y === 160 && d.label === s.api.itemLine(name).slice(0, 34)), "selected detail stays in its own row");
  } else if (entries.length) {
    assert.ok(draws.some(d => d.kind === "text" && d.label === entries[selected].mp + " MP" && d.y === row.y && d.color === row.color), "selected MP cost stays on its row with the same enabled color");
  }
  return { draws, rows, row };
}
check("a normal long field bag shows first/last selections and wraps both ways", () => {
  const s = session(); fullBag(s); const m = openItems(s), list = Array.from(s.api.fieldItems());
  assert.equal(list.length, 12); assert.equal(list.includes("Smoke Pouch"), false); windowShown(s, list, 0);
  s.tick("up"); assert.equal(m.ii, list.length - 1); windowShown(s, list, m.ii);
  s.tick("down"); assert.equal(m.ii, 0); windowShown(s, list, m.ii);
  for (let i = 1; i < list.length; i++) { s.tick("down"); windowShown(s, list, m.ii); }
});
check("changing the item recipient preserves its scrolled selection", () => {
  const s = session(); fullBag(s); const m = openItems(s); s.tick("up"); const index = m.ii;
  s.tick("right"); assert.equal(m.who, 1); assert.equal(m.ii, index); windowShown(s, Array.from(s.api.fieldItems()), index);
  s.tick("left"); assert.equal(m.who, 0); assert.equal(m.ii, index);
});
check("using the last type clamps the rendered list immediately, then the existing tick cursor", () => {
  const s = session(); fullBag(s); const m = openItems(s); s.tick("up"); s.tick("right"); s.tick("right");
  const index = m.ii, item = s.api.fieldItems()[index], who = s.api.getParty()[m.who]; who.mp = 0;
  assert.equal(item, "Prismscale Koi"); s.tick("a"); assert.ok(who.mp > 0); assert.equal(s.api.getBag()[item], 0);
  assert.equal(m.ii, index, "rendering does not rewrite menu selection state");
  const remaining = Array.from(s.api.fieldItems()); windowShown(s, remaining, remaining.length - 1);
  assert.equal(m.ii, index); s.tick(); assert.equal(m.ii, remaining.length - 1); windowShown(s, remaining, m.ii);
});
check("short Portal field lists keep their existing coordinates and Back behavior", () => {
  const s = session("portal"), m = openItems(s), list = Array.from(s.api.fieldItems());
  assert.equal(list.length, 2); windowShown(s, list, 0); s.tick("up"); assert.equal(m.ii, 1);
  assert.equal(windowShown(s, list, 1).row.y, 85); s.tick("b"); assert.equal(m.sub, null); s.tick("b"); assert.equal(s.c.mode, "field");
});
check("empty bags refuse ITEM, and consuming the sole type never draws a phantom cursor", () => {
  const s = session(), bag = s.api.getBag(); Object.keys(bag).forEach(k => delete bag[k]);
  let m = openItems(s); assert.equal(m.sub, null); assert.equal(m.msg, "THE BAG HOLDS NOTHING TO USE.");
  bag["Herb Tonic"] = 1; s.tick("a"); assert.equal(m.sub, "item"); s.api.getParty()[0].hp -= 130; s.tick("a");
  assert.equal(s.api.fieldItems().length, 0); windowShown(s, [], 0); s.tick(); assert.equal(m.sub, null);
});
check("a long normally purchasable spell book scrolls and keeps offensive spells disabled", () => {
  const s = session(), caster = longCaster(s), m = openMagic(s, 2), list = Array.from(s.api.fieldSpells(caster));
  assert.ok(list.length > 6); windowShown(s, list, 0, "magic"); s.tick("up"); assert.equal(m.ii, list.length - 1);
  const shown = windowShown(s, list, m.ii, "magic"); assert.equal(shown.row.color, "#6c6c8c");
  const mp = caster.mp; s.tick("a"); assert.equal(caster.mp, mp); assert.equal(m.sub, "magic"); assert.match(m.msg, /IS FOR BATTLE/);
  s.tick("down"); assert.equal(m.ii, 0); windowShown(s, list, 0, "magic");
  for (let i = 1; i < list.length; i++) { s.tick("down"); windowShown(s, list, m.ii, "magic"); }
});
check("ally targeting, healing cost and layered Back keep their existing policy", () => {
  const s = session(), m = openMagic(s, 1), caster = s.api.getParty()[1], list = Array.from(s.api.fieldSpells(caster));
  assert.equal(list.length, 2); assert.equal(windowShown(s, list, 0, "magic").row.color, "#ffffff");
  const target = s.api.getParty()[0], mp = caster.mp; target.hp -= 130; const hp = target.hp, sp = list[0];
  s.tick("a"); assert.equal(m.sub, "magic-target"); windowShown(s, list, 0, "magic", false);
  s.tick("down"); assert.equal(m.target, 1); assert.equal(m.ii, 0);
  assert.ok(s.draw().some(d => d.kind === "cursor" && d.x === 12 && d.y === 66), "full picker cursor follows the same ally target");
  s.tick("up"); s.tick("a"); assert.equal(caster.mp, mp - sp.mp);
  assert.equal(target.hp, Math.min(target.max, hp + Math.round(sp.power * 1.5 + caster.st.spr * 3)));
  s.tick("b"); assert.equal(m.sub, "magic"); assert.equal(m.ii, 0); s.tick("b"); assert.equal(m.sub, "magic-who");
  s.tick("b"); assert.equal(m.sub, null); s.tick("b"); assert.equal(s.c.mode, "field");
});
check("magic-target retains its long catalog selection while exposing the full party picker", () => {
  const s = session(), caster = s.api.getParty()[1];
  // A mixed real-catalog book stresses target rendering; no new spell-learning policy is added.
  caster.spells = purchasable(s, "enemy").concat(purchasable(s, "ally")).map(sp => sp.name);
  const m = openMagic(s, 1), list = Array.from(s.api.fieldSpells(caster)), index = list.findIndex(sp => sp.name === "Restore");
  assert.ok(index >= 6); for (let i = 0; i < index; i++) s.tick("down"); s.tick("a"); assert.equal(m.sub, "magic-target");
  windowShown(s, list, index, "magic", false); s.tick("down"); assert.equal(m.ii, index); windowShown(s, list, index, "magic", false);
  s.tick("b"); assert.equal(m.sub, "magic"); assert.equal(m.ii, index); windowShown(s, list, index, "magic");
});
check("a companion without spells still refuses the spell list", () => {
  const s = session(); s.api.openMenu(); s.tick("down"); s.tick("a"); s.tick("left"); assert.equal(s.api.getMenu().who, 0);
  s.tick("a"); assert.equal(s.api.getMenu().sub, "magic-who"); assert.match(s.api.getMenu().msg, /KNOWS NO SPELLS/);
});
const noScroll = source.replaceAll("rows = 6", "rows = Number.MAX_SAFE_INTEGER");
assert.notEqual(noScroll, source, "the controlled old behavior removes the six-row drawing bound");
check("the visibility assertion detects the old unbounded item list", () => {
  const s = session("prism", noScroll); fullBag(s); const m = openItems(s); s.tick("up");
  assert.throws(() => windowShown(s, Array.from(s.api.fieldItems()), m.ii), /six list rows|selected entry|row glyphs/);
});
check("the visibility assertion detects the old unbounded magic list", () => {
  const s = session("prism", noScroll), caster = longCaster(s), m = openMagic(s, 2); s.tick("up");
  assert.throws(() => windowShown(s, Array.from(s.api.fieldSpells(caster)), m.ii, "magic"), /six list rows|selected entry|row glyphs/);
});
console.log("Prismheart/Portal field menus: " + checks + " focused checks passed");
