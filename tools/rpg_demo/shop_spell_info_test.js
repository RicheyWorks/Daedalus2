// SPDX-License-Identifier: MIT
// Focused offline check: node --max-old-space-size=128 tools/rpg_demo/shop_spell_info_test.js
// Actual shop/party functions and the 34 authored lessons; canvas spies only, no assets/DOM/boot/storage.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value)), parties = data("party").party, interiors = data("interiors").interiors;
const allSpells = data("spells").spells, lessons = interiors.prism.Magic.stock, gear = {};
for (const realm of ["portal", "prism"]) for (const store of Object.values(interiors[realm]))
  for (const item of store.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
assert.equal(lessons.length, 34, "the existing authored demo offers 34 lessons");
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"),
  between("const START_LEVEL =", "/* Recruits:"), between("function recruitsFor(", "function recruitBeaten("),
  line("const spellOf ="), line("const WEAPON_KIND ="), between("const ITEM_KINDS =", "function menuTick()"),
  between("let shop = null;", "/* ---------- field ---------- */"), between("function spellHint(", "function drawBattle("),
  "this.api = { start: () => { party = buildParty(); }, roster, recruit, openShop, shopTick, drawShop, buy, magicShopCaster, spellHint, itemLine, " +
  "party: () => party, reserve: () => reserve, shop: () => shop, gold: () => gold, setGold: n => { gold = n; }, chars: CHARS, " +
  "snapshot: () => ({ party, reserve, bag, gold, shop, data: D, pressed }) };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, productionSource = source) {
  const draws = [], sounds = [], pressed = { a: false, b: false, start: false, up: false, down: false, left: false, right: false }, known = new Set(parties.prism.members.flatMap(m => m.spells));
  const c = { D: { party: clone(parties.prism), gear: clone(gear), interiors: clone(interiors.prism),
      spells: clone(allSpells.filter(s => s.realm === "prism" && (known.has(s.name) || s.tier <= 2))) },
    W: width, H: 224, map: { kind: "interior" }, mode: "field", B: null, pressed,
    state: { beaten: new Set() }, drawField() {}, sfx: sound => sounds.push(sound), say() {},
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: label => String(label).length * 6,
    win: (...rect) => draws.push({ kind: "window", rect }), cursor: (x, y) => draws.push({ kind: "cursor", x, y }),
    text: (label, x, y, color = "#ffffff") => draws.push({ kind: "text", label: String(label).toUpperCase(), x, y, color }),
    g: { fillStyle: "", fillRect() {} },
    localStorage: { getItem() { throw new Error("preview must not access storage"); }, setItem() { throw new Error("preview must not save"); }, removeItem() { throw new Error("preview must not erase"); } } };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.api.start();
  const s = { c, api: c.api, draws, sounds,
    tick(...keys) { keys.forEach(key => { pressed[key] = true; }); c.api.shopTick(); },
    enter(store = "Magic") { c.map.info = c.D.interiors[store]; assert.ok(c.map.info); c.api.openShop(); return this; },
    draw() { draws.length = 0; const before = JSON.stringify(c.api.snapshot()), count = sounds.length;
      c.api.drawShop(); assert.equal(JSON.stringify(c.api.snapshot()), before, "rendering preserves roster, spells, gold, inventory, input, catalog and shop state");
      assert.equal(sounds.length, count, "preview produces no transaction sounds"); return draws; } };
  s.api.setGold(50000); return s.enter();
}
function select(s, name) {
  const shop = s.api.shop(), index = shop.stock.findIndex(it => it.name === name); assert.ok(index >= 0);
  while (shop.idx !== index) s.tick("down"); return shop.stock[index];
}
function preview(s, name, allowTruncation = false) {
  const item = select(s, name), sp = s.c.D.spells.find(x => x.name === name), roster = Array.from(s.api.roster()); assert.ok(sp);
  const caster = roster.find(m => m.job === (sp.target === "ally" ? "Lightmender" : "Runecaster"));
  assert.equal(s.api.magicShopCaster(sp), caster, "preview and purchase use the original first whole-roster recipient");
  const known = caster && caster.spells.includes(sp.name), shop = s.api.shop(); s.draw();
  const footer = s.draws.find(d => d.kind === "text" && d.x === 12 && d.y === 204); assert.ok(footer);
  const parts = footer.label.match(/^([^:]+): (.+)$/); assert.ok(parts, "the preview identifies a recipient before its complete casting details");
  const recipient = caster ? caster.name.toUpperCase() : "NO CASTER";
  if (allowTruncation) assert.ok(recipient.startsWith(parts[1]) && parts[1].length > 0); else assert.equal(parts[1], recipient);
  assert.equal(parts[2], s.api.spellHint(sp) + " " + sp.mp + "MP" + (known ? " KNOWN" : ""));
  assert.ok(footer.x + s.c.tw(footer.label) <= s.c.W - 12 && footer.y + 8 <= 212, "the full hint, MP and known state fit the existing single-line footer");
  assert.ok(Array.from(footer.label).every(char => s.api.chars.includes(char)), "all preview glyphs exist in the current font");
  const rowY = 38 + (shop.idx - shop.top) * 16, row = s.draws.find(d => d.kind === "text" && d.x === 24 && d.y === rowY);
  assert.ok(row && name.toUpperCase().startsWith(row.label));
  assert.equal(row.color, item.price > s.api.gold() || !caster || known ? "#808090" : "#ffffff", "row availability matches gold and learning eligibility, independently of current casting MP");
  assert.ok(s.draws.some(d => d.kind === "text" && d.label === String(item.price) && d.y === rowY && d.x === s.c.W - 102 - s.c.tw(item.price)));
  assert.ok(s.draws.some(d => d.kind === "cursor" && d.x === 10 && d.y === rowY && rowY >= 38 && rowY <= 150));
  assert.ok(s.draws.some(d => d.kind === "text" && d.label === shop.msg.toUpperCase() && d.y === 190));
  assert.ok(s.draws.some(d => d.kind === "text" && d.label === String(s.api.gold()) && d.y === 37 && d.x === s.c.W - 10 - s.c.tw(s.api.gold())));
  return { item, sp, caster, known, footer, row };
}
for (const width of [320, 256]) check("all34 authored lessons preview and learn through the actual shop at " + width, () => {
  const s = session(width); for (const member of s.api.roster()) member.mp = 0;
  for (const lesson of lessons) {
    const p = preview(s, lesson.name), before = JSON.stringify(s.api.roster()), gold = s.api.gold(), spells = Array.from(p.caster.spells);
    s.tick("a");
    if (p.known) { assert.equal(s.api.gold(), gold); assert.equal(JSON.stringify(s.api.roster()), before); assert.match(s.api.shop().msg, /ALREADY KNOW/); }
    else {
      assert.equal(s.api.gold(), gold - lesson.price); assert.deepEqual(Array.from(p.caster.spells), spells.concat([lesson.name]));
      assert.equal(p.caster.mp, 0, "learning never spends or requires casting MP"); assert.match(s.api.shop().msg, / LEARNS /);
    }
    assert.equal(preview(s, lesson.name).known, true); const paid = s.api.gold(); s.tick("a"); assert.equal(s.api.gold(), paid, "a known lesson is never charged twice");
  }
  assert.equal(s.api.shop().stock.length, 34); s.tick("down"); assert.equal(s.api.shop().idx, 0); s.tick("up"); assert.equal(s.api.shop().idx, 33);
});
for (const [job, name] of [["Runecaster", "Gale"], ["Lightmender", "Bulwark"]]) check("the actual " + job + " in reserve remains the previewed recipient", () => {
  const s = session(256); s.api.recruit("Cinder Forge"); const front = s.api.party(), back = s.api.reserve();
  const index = front.findIndex(m => m.job === job); [front[index], back[0]] = [back[0], front[index]];
  const caster = back[0]; caster.hp = 0; caster.mp = 0; const p = preview(s, name); assert.equal(p.caster, caster); assert.equal(p.known, false);
  const gold = s.api.gold(), hp = caster.hp; s.tick("a"); assert.ok(caster.spells.includes(name)); assert.equal(s.api.gold(), gold - p.item.price);
  assert.equal(caster.hp, hp); assert.equal(caster.mp, 0); assert.equal(preview(s, name).known, true);
});
for (const name of ["Gale", "Bulwark"]) check("missing eligible recipient is visibly unlearnable without changing the existing refusal for " + name, () => {
  const s = session(256), sp = s.c.D.spells.find(x => x.name === name), job = sp.target === "ally" ? "Lightmender" : "Runecaster";
  const front = s.api.party(); front.splice(front.findIndex(m => m.job === job), 1); const p = preview(s, name); assert.equal(p.caster, undefined);
  const before = JSON.stringify(s.api.snapshot()); s.tick("a"); assert.match(s.api.shop().msg, /ALREADY KNOW/);
  const after = clone(s.api.snapshot()), prior = JSON.parse(before); after.shop.msg = prior.shop.msg;
  assert.equal(JSON.stringify(after), before, "the existing missing-recipient refusal changes only feedback");
});
check("insufficient gold still takes precedence over a known lesson", () => {
  const s = session(); s.api.setGold(0); const p = preview(s, "Ember"); assert.equal(p.known, true);
  const before = JSON.stringify(s.api.roster()); s.tick("a"); assert.equal(s.api.shop().msg, "NOT ENOUGH GOLD.");
  assert.equal(s.api.gold(), 0); assert.equal(JSON.stringify(s.api.roster()), before);
});
check("an unknown unaffordable lesson still previews its real recipient and casting cost", () => {
  const s = session(256); s.api.setGold(0); const p = preview(s, "Quake"); assert.equal(p.known, false);
  const before = JSON.stringify(s.api.roster()); s.tick("a"); assert.equal(s.api.shop().msg, "NOT ENOUGH GOLD."); assert.equal(JSON.stringify(s.api.roster()), before);
});
for (const width of [320, 256]) check("long displayed recipient preserves full hint and KNOWN at " + width, () => {
  const s = session(width), caster = s.api.roster().find(m => m.job === "Runecaster"); caster.name = "STARLIGHTSAGE";
  select(s, "Leech"); s.tick("a"); const before = JSON.stringify(s.api.roster()), p = preview(s, "Leech", true);
  assert.equal(caster.name, "STARLIGHTSAGE"); assert.equal(JSON.stringify(s.api.roster()), before);
  if (width === 256) assert.ok(p.footer.label.split(":")[0].length < caster.name.length, "only the displayed name is shortened when needed");
});
for (const [store, name] of [["Item", "Herb Tonic"], ["Weapon", "Steel Saber"]]) check(store + " shop keeps its existing footer, tabs and affordability", () => {
  const s = session(256); s.enter(store); const item = select(s, name); s.draw();
  const footer = s.draws.find(d => d.kind === "text" && d.x === 12 && d.y === 204);
  assert.equal(footer.label, item.effect ? s.api.itemLine(name) : "ATTACK " + item.attack);
  assert.ok(s.draws.some(d => d.kind === "text" && d.label === "BUY" && d.y === 9)); assert.ok(s.draws.some(d => d.kind === "text" && d.label === "SELL" && d.y === 9));
  s.tick("right"); assert.equal(s.api.shop().tab, "sell"); s.draw();
  assert.ok(s.draws.some(d => d.kind === "text" && d.y === 204 && d.label === "SELLS FOR HALF ITS PRICE."));
});
check("controlled previous element-only footer fails the same recipient/details assertion", () => {
  const a = source.indexOf('  if (shop.kind === "magic") {', source.indexOf("function drawShop()")), b = source.indexOf("  text(d, 12, 204", a); assert.ok(a >= 0 && b > a);
  const s = session(320, source.slice(0, a) + source.slice(b));
  assert.throws(() => preview(s, "Splash"), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute boot, assets or the game loop.
console.log("Prismheart spell shop preview checks: " + checks + " passed; full inline script compiles.");
