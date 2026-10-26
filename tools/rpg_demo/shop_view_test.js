// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/shop_view_test.js
// Actual shop/factory/recruit/stat helpers + canonical catalogs. Canvas-command capture only.
// Shared Portal armour stock is used once as an explicit shared-browser fixture, not a new Prism shop.
// No game boot, assets, DOM, real storage, browser, native runtime or resource-counter access.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8")), clone = value => JSON.parse(JSON.stringify(value));
const parties = data("party").party, interiors = data("interiors").interiors, spells = data("spells").spells, fishes = data("prism-fish").fish, gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(interiors[realm])) for (const it of shop.stock || [])
  if (it.attack != null || it.defence != null || it.effect) gear[it.name] = clone(it);
for (const fish of fishes) gear[fish.name] = { name: fish.name, effect: fish.effect, price: fish.price, fish: true };
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = prefix => { const found = html.split("\n").find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"), between("const START_LEVEL =", "/* ---------- maps"),
  line("const WEAPON_KIND ="), line("const SLOTS ="), line("const atkWith ="), line("const defWith ="), between("const ITEM_KINDS =", "const fieldSpells ="),
  between("let shop = null;", "/* ---------- field ---------- */"), between("function spellHint(", "function drawBattlePlan("), between("function titlePrompt(", "function drawTitle("),
  "this.api={start:()=>{party=buildParty();},recruitAll:()=>D.party.members.filter(m=>m.joins.startsWith('after ')).forEach(m=>recruit(m.joins.slice(6)))," +
  "roster,party:()=>party,reserve:()=>reserve,setRoster:(front,back)=>{party=front;reserve=back;},bag:()=>bag,setBag:value=>{bag=value;},gold:()=>gold,setGold:n=>{gold=n;}," +
  "shop:()=>shop,message:text=>{shop.msg=text;},open:(kind,stock)=>{map={kind:'interior',info:{service:'shop:'+kind,stock}};openShop();}," +
  "tick:(...keys)=>{keys.forEach(key=>{pressed[key]=true;});shopTick();},drawShop,buy,sellList,sellPrice,spellOf,spellHint,shopGearChoice,magicShopCaster,atkOf,atkWith,defOf,defWith,slots:SLOTS,chars:CHARS};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], rectangles = [], cursors = [], windows = [], pressed = {}, dialogs = [], calls = { rng: 0, storage: 0, field: 0 }, math = Object.create(Math);
  math.random = () => { calls.rng++; throw new Error("shop UI cannot roll RNG"); };
  const known = new Set(parties[realm].members.flatMap(m => m.spells));
  const c = { W: width, H: 224, D: { realm_key: realm, party: clone(parties[realm]), gear: clone(gear), interiors: clone(interiors[realm]), spells: clone(spells.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2))),
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) }, B: null, PAD: null, pressed, Math: math, mode: "field", map: { kind: "world" }, state: { beaten: new Set() },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: value => String(value).length * 6, sfx() {}, toast() {}, say: pages => dialogs.push(pages),
    drawField() { calls.field++; }, win: (x, y, w, h) => windows.push({ x, y, w, h }), cursor: (x, y) => cursors.push({ x, y }),
    saveGame() { calls.storage++; throw new Error("shop UI cannot save"); }, localStorage: { getItem() { calls.storage++; throw new Error("storage read"); } },
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ label, x, y, w: label.length * 6, h: 8, color }); },
    g: { fillStyle: "", fillRect(x, y, w, h) { rectangles.push({ x, y, w, h, color: this.fillStyle }); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify({ roster: c.api.roster(), front: c.api.party().map(m => m.job), bag: c.api.bag(), gold: c.api.gold() });
  const snapshot = () => JSON.stringify({ resources: resources(), D: c.D, shop: c.api.shop(), map: c.map, mode: c.mode, pressed, beaten: [...c.state.beaten] });
  return { c, api: c.api, paints, rectangles, cursors, windows, pressed, dialogs, calls, resources,
    open(kind, stock = Object.values(c.D.interiors).find(it => it.service === "shop:" + kind).stock) { c.api.open(kind, clone(stock)); return this; },
    draw() { paints.length = rectangles.length = cursors.length = windows.length = 0; const before = snapshot(), rng = calls.rng, storage = calls.storage, field = calls.field; c.api.drawShop();
      assert.equal(snapshot(), before, "painting changed stock, selection, money, inventory, recipients or inputs"); assert.equal(calls.rng, rng); assert.equal(calls.storage, storage);
      if (realm === "prism") assert.equal(calls.field, field, "Prism shop must not call inherited field paint/lazy state"); return paints; },
    at(x, y) { return paints.find(p => p.x === x && p.y === y); }, labels: () => paints.map(p => p.label)
  };
}
function select(s, name) {
  const shop = s.api.shop(), names = shop.tab === "sell" ? Array.from(s.api.sellList()) : shop.stock.map(it => it.name), index = names.indexOf(name); assert.ok(index >= 0, name);
  for (let i = 0; shop.idx !== index && i < names.length; i++) s.api.tick("down"); assert.equal(shop.idx, index); return shop.stock[index];
}
function bounds(s) {
  for (const p of s.paints) { assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, "shop text outside canvas " + JSON.stringify(p));
    assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), "unsupported shop glyph"); }
  for (const r of s.rectangles) assert.ok(r.x >= 0 && r.y >= 0 && r.x + r.w <= s.c.W && r.y + r.h <= 224);
  assert.equal(s.calls.rng, 0); assert.equal(s.calls.storage, 0);
}
function rows(s) {
  const shop = s.api.shop(), selling = shop.tab === "sell", names = selling ? Array.from(s.api.sellList()) : shop.stock.map(it => it.name);
  const selected = names.length ? Math.max(0, Math.min(shop.idx, names.length - 1)) : -1;
  const top = selected < 0 ? 0 : Math.max(Math.max(0, selected - 7), Math.min(shop.top, Math.min(selected, Math.max(0, names.length - 8))));
  const visible = names.slice(top, top + 8), nameRows = s.paints.filter(p => p.x === 24 && p.y >= 40 && p.y <= 138 && (p.y - 40) % 14 === 0);
  assert.equal(nameRows.length, visible.length); assert.equal(s.cursors.length, selected < 0 ? 0 : 1);
  visible.forEach((name, i) => { const row = nameRows[i], y = 40 + i * 14, value = selling ? s.api.sellPrice(name) : shop.stock[top + i].price;
    const price = (value > 999999 ? "999999+" : String(value)) + "G", priceRow = s.paints.find(p => p.y === y && p.label === price);
    assert.ok(priceRow); assert.equal(row.y, y); assert.ok(row.x + row.w + 8 <= priceRow.x, "name/count overlaps gold price"); assert.equal(priceRow.x + priceRow.w, s.c.W - 12); });
  if (selected >= 0) { assert.equal(s.cursors[0].y, 40 + (selected - top) * 14); assert.ok(s.cursors[0].x + 1 + 8 < 24, "both cursor frames clear text"); }
  return visible;
}
for (const width of [320, 256]) check("canonical item/weapon prices, full selected details and both cursor frames at " + width, () => {
  for (const kind of ["item", "weapon"]) { const s = session(width).open(kind); s.api.setGold(100000);
    for (let i = 0; i < s.api.shop().stock.length; i++) { const it = s.api.shop().stock[i]; assert.equal(s.api.shop().idx, i); s.draw(); rows(s); bounds(s);
      assert.equal(s.at(12, 166).label, it.name.toUpperCase()); assert.ok(s.at(12, 178)); assert.ok(s.at(12, 190).label.startsWith("NEXT BUY:")); s.api.tick("down"); }
    assert.equal(s.api.shop().idx, 0); }
});
for (const width of [320, 256]) check("all 34 magic lessons retain actual stock indices, eight-row scrolling and casting facts at " + width, () => {
  const s = session(width).open("magic"), stock = s.api.shop().stock; assert.equal(stock.length, 34); s.api.setGold(100000);
  for (let i = 0; i < stock.length; i++) { assert.equal(s.api.shop().idx, i); const it = stock[i], sp = s.api.spellOf(it.name), recipient = s.api.magicShopCaster(sp); assert.ok(sp && recipient);
    s.draw(); rows(s); bounds(s); assert.equal(s.at(12, 166).label, it.name.toUpperCase()); assert.equal(s.at(12, 178).label, sp.mp + "MP PER CAST / " + s.api.spellHint(sp));
    const row = s.paints.find(p => p.x === 24 && p.y === s.cursors[0].y); assert.equal(row.color, recipient.spells.includes(sp.name) ? "#808090" : "#ffffff");
    assert.ok(s.at(12, 190).label.startsWith("LEARNS: " + recipient.name.toUpperCase())); assert.equal(s.at(12, 190).label.endsWith(" / KNOWN"), recipient.spells.includes(sp.name)); s.api.tick("down"); }
  assert.equal(s.api.shop().idx, 0); s.api.tick("up"); assert.equal(s.api.shop().idx, 33); s.draw(); rows(s); assert.ok(s.labels().includes("BUY ONLY"));
});
check("reserve/downed MP0 recipient learns normally; known and gold-first refusal remain authoritative", () => {
  const s = session(256); s.api.recruitAll(); const all = Array.from(s.api.roster()), learner = all.find(m => m.job === "Lightmender");
  s.api.setRoster([all[0], all[2], all[3], all[4]], [learner].concat(all.filter(m => ![all[0], all[2], all[3], all[4], learner].includes(m)))); learner.hp = 0; learner.mp = 0;
  s.open("magic"); s.api.setGold(100000); const it = s.api.shop().stock.find(it => { const sp = s.api.spellOf(it.name); return sp.target === "ally" && !learner.spells.includes(sp.name); }); select(s, it.name);
  s.draw(); assert.ok(s.at(12, 190).label.startsWith("LEARNS: YSOLDE")); assert.equal(s.paints.find(p => p.x === 24 && p.y === s.cursors[0].y).color, "#ffffff");
  const gold = s.api.gold(); s.api.tick("a"); assert.equal(s.api.gold(), gold - it.price); assert.ok(learner.spells.includes(it.name)); assert.equal(learner.mp, 0); assert.equal(learner.hp, 0);
  s.draw(); assert.ok(s.at(12, 190).label.endsWith(" / KNOWN")); assert.ok(s.at(12, 202).label.startsWith("LAST: YSOLDE LEARNS")); const paid = s.api.gold(); s.api.tick("a"); assert.equal(s.api.gold(), paid);
  s.api.message("WHAT WOULD YOU LIKE?"); s.api.setGold(0); s.draw(); assert.equal(s.at(12, 202).label, "NOT ENOUGH GOLD."); s.api.tick("a"); assert.equal(s.api.shop().msg, "NOT ENOUGH GOLD.");
});
check("missing learner and unresolved runtime spell remain visible, unavailable and transaction-safe", () => {
  for (const missingSpell of [false, true]) { const s = session(256).open("magic"); s.api.setGold(100000); const it = s.api.shop().stock.find(it => s.api.spellOf(it.name).target === "ally"); select(s, it.name);
    if (missingSpell) s.c.D.spells = s.c.D.spells.filter(sp => sp.name !== it.name); else s.api.setRoster(s.api.party().filter(m => m.job !== "Lightmender"), []);
    s.draw(); rows(s); bounds(s); assert.equal(s.api.shop().stock.length, 34); assert.equal(s.at(12, 190).label, missingSpell ? "LESSON UNAVAILABLE IN THIS BUILD." : "NO COMPANION CAN LEARN THIS.");
    const before = s.resources(); s.api.tick("a"); assert.equal(s.resources(), before); assert.equal(s.api.shop().msg, missingSpell ? "WHAT WOULD YOU LIKE?" : "YOU ALREADY KNOW THAT."); }
});
check("NEXT BUY matches actual first auto-fit recipient including reserve; LAST remains the completed purchase", () => {
  const s = session(256); s.api.recruitAll(); s.open("weapon"); s.api.setGold(100000); select(s, "Steel Saber"); const corin = s.api.party()[0], rook = s.api.party().find(m => m.job === "Shadowstep"), all = Array.from(s.api.roster()), it = s.api.shop().stock[s.api.shop().idx];
  s.draw(); assert.equal(s.at(12, 190).label, "NEXT BUY: CORIN ATK 54>68"); const old = corin.equip.weapon, bagBefore = s.api.bag()[old] || 0, gold = s.api.gold(); s.api.tick("a");
  assert.equal(corin.equip.weapon, it.name); assert.equal(s.api.bag()[old], bagBefore + 1); assert.equal(s.api.gold(), gold - it.price);
  const front = [corin, all[1], all[2], all[4]]; s.api.setRoster(front, [rook].concat(all.filter(m => !front.includes(m) && m !== rook)));
  s.draw(); assert.equal(s.at(12, 190).label, "NEXT BUY: ROOK ATK 48>62"); assert.ok(s.at(12, 202).label.startsWith("LAST: CORIN EQUIPS")); s.api.tick("a"); assert.equal(rook.equip.weapon, it.name); assert.equal(s.api.bag()[old], bagBefore + 2);
});
check("unusable/equal gear goes to bag; shared armour preview uses exact helper and replacement return", () => {
  const s = session(256).open("weapon"); s.api.setGold(100000); select(s, "Iron Axe"); s.draw(); assert.equal(s.at(12, 190).label, "NEXT BUY: INTO BAG."); const equipment = JSON.stringify(s.api.roster().map(m => m.equip)); s.api.tick("a"); assert.equal(s.api.bag()["Iron Axe"], 1); assert.equal(JSON.stringify(s.api.roster().map(m => m.equip)), equipment);
  select(s, "Steel Saber"); for (let i = 0; s.api.shopGearChoice(s.api.shop().stock[s.api.shop().idx]).who && i < 8; i++) s.api.tick("a"); s.draw(); assert.equal(s.at(12, 190).label, "NEXT BUY: INTO BAG."); s.api.tick("a"); assert.equal(s.api.bag()["Steel Saber"], 1);
  const stock = Object.values(interiors.portal).find(it => it.service === "shop:armor").stock, item = stock.slice().sort((a, b) => b.defence - a.defence)[0];
  const armour = session(256).open("armor", [item]); armour.api.setGold(100000); const choice = armour.api.shopGearChoice(item); assert.ok(choice.who); const before = armour.api.defOf(choice.who), after = armour.api.defWith(choice.who, { ...choice.who.equip, [choice.slot]: item.name }), worn = choice.who.equip[choice.slot], count = armour.api.bag()[worn] || 0;
  armour.draw(); assert.equal(armour.at(12, 178).label, "DEFENCE " + item.defence); assert.equal(armour.at(12, 190).label, "NEXT BUY: " + choice.who.name.toUpperCase() + " DEF " + before + ">" + after);
  armour.api.tick("a"); assert.equal(choice.who.equip[choice.slot], item.name); if (worn) assert.equal(armour.api.bag()[worn], count + 1);
});
check("SELL uses bag copies and floor-half price; same-frame tab+Confirm and final empty frame retain policy", () => {
  const s = session(256).open("item"), fish = fishes.find(f => f.name === "Reedling"), price = Math.floor(fish.price / 2); s.api.setBag({ [fish.name]: 2 }); const gold = s.api.gold(), worn = JSON.stringify(s.api.roster().map(m => m.equip));
  s.api.tick("right", "a"); assert.equal(s.api.shop().tab, "sell"); assert.equal(s.api.bag()[fish.name], 1); assert.equal(s.api.gold(), gold + price); s.draw(); rows(s); bounds(s);
  assert.equal(s.at(12, 178).label, "HALF PRICE: " + price + "G / BAG 1"); assert.equal(s.at(12, 190).label, "BAG ITEMS ONLY. WORN GEAR IS KEPT.");
  s.api.tick("a"); assert.equal(s.api.bag()[fish.name], 0); const savedCursor = JSON.stringify({ idx: s.api.shop().idx, top: s.api.shop().top }); s.draw(); rows(s); bounds(s);
  assert.equal(JSON.stringify({ idx: s.api.shop().idx, top: s.api.shop().top }), savedCursor); assert.ok(s.labels().includes("NO BAG ITEMS TO SELL.")); assert.ok(s.labels().includes("NOTHING TO SELL.")); assert.ok(s.at(12, 202).label.startsWith("LAST: SOLD REEDLING"));
  assert.equal(s.api.gold(), gold + 2 * price); assert.equal(JSON.stringify(s.api.roster().map(m => m.equip)), worn);
  const names = Array.from(new Set(Object.values(interiors.prism).find(it => it.service === "shop:item").stock.map(it => it.name).concat(fishes.map(f => f.name)))).sort().slice(0, 9);
  const shrinking = session(256).open("item"); shrinking.api.setBag(Object.fromEntries(names.map(name => [name, 1]))); shrinking.api.tick("right"); select(shrinking, names.at(-1));
  assert.equal(shrinking.api.shop().idx, 8); assert.equal(shrinking.api.shop().top, 1); shrinking.api.tick("a"); assert.equal(shrinking.api.sellList().length, 8);
  shrinking.draw(); rows(shrinking); bounds(shrinking); assert.equal(shrinking.api.shop().idx, 8); assert.equal(shrinking.api.shop().top, 1); assert.equal(shrinking.at(12, 166).label, names[7].toUpperCase());
  shrinking.api.tick("down"); assert.equal(shrinking.api.shop().idx, 0); shrinking.draw(); rows(shrinking); bounds(shrinking); assert.equal(shrinking.at(12, 166).label, names[0].toUpperCase());
  shrinking.api.tick("up"); assert.equal(shrinking.api.shop().idx, 7); shrinking.draw(); rows(shrinking); bounds(shrinking); assert.equal(shrinking.at(12, 166).label, names[7].toUpperCase());
});
check("large values/aliases/mapped hints fit; Back or Start beats simultaneous Confirm", () => {
  for (const width of [320, 256]) { const s = session(width).open("weapon"); select(s, "Steel Saber"); const m = s.api.party()[0]; m.name = "ß".repeat(64); m.st.str = Number.MAX_SAFE_INTEGER; s.api.setGold(Number.MAX_SAFE_INTEGER); s.api.bag()["Steel Saber"] = Number.MAX_SAFE_INTEGER;
    s.c.PAD = { devices: () => [{ index: 5 }], label(action, index) { assert.equal(index, 5); return action === "confirm" ? "ABCDEFGH" : "12345678"; } }; s.draw(); rows(s); bounds(s);
    assert.ok(s.labels().includes("GOLD 999999+")); assert.ok(s.at(12, 190).label.includes("... ATK 9999+>9999+")); assert.equal(m.name, "ß".repeat(64));
    const left = s.at(12, 214), right = s.paints.find(p => p.y === 214 && p.x !== 12); assert.equal(left.label, "ABCDEFGH: BUY ONE"); assert.equal(right.label, "12345678: LEAVE"); assert.ok(left.x + left.w < right.x);
    s.api.tick("right"); s.draw(); rows(s); bounds(s); assert.ok(s.paints.some(p => /X999\+/.test(p.label))); }
  for (const key of ["b", "start"]) { const s = session().open("item"), before = s.resources(); s.api.tick(key, "a"); assert.equal(s.api.shop(), null); assert.equal(s.c.mode, "field"); assert.equal(s.resources(), before); assert.ok(!s.pressed.a && !s.pressed.b && !s.pressed.start); assert.equal(s.dialogs[0][0], "COME AGAIN!"); }
});
check("Portal keeps its original field-backed shop painter and layout", () => {
  const s = session(320, "portal").open("item"); s.draw(); assert.equal(s.calls.field, 1); assert.ok(s.windows.length >= 3); assert.ok(s.paints.some(p => p.x === 24 && p.y === 38));
  assert.equal(s.paints.some(p => p.y === 166 || p.y === 214), false); assert.ok(s.paints.some(p => p.y === 190 && p.label.startsWith("WHAT WOULD YOU LIKE?")));
});
check("controlled old renderer witnesses the ordinary Feather sell overlap and fails the new row contract", () => {
  const old = source.replace('if ((D.realm_key || "prism") === "prism") return drawPrismShop();', 'if (false) return drawPrismShop();'); assert.notEqual(old, source);
  const s = session(256, "prism", old).open("item"); s.api.setBag({ "Feather of Waking": 2 }); s.api.tick("right");
  // The old renderer intentionally calls inherited drawField; temporarily compare only gameplay state for this witness.
  s.paints.length = 0; s.api.drawShop(); const name = s.paints.find(p => p.x === 24 && p.y === 38), price = s.paints.find(p => p.y === 38 && p.x !== 24 && p.label === String(s.api.sellPrice("Feather of Waking")));
  assert.ok(name && price && name.x + name.w > price.x, "ordinary canonical sale name/count crossed its price"); assert.throws(() => rows(s), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("shop view: " + checks + " focused groups passed; actual source/canonical-record capture only, no assets/browser/native acceptance");
