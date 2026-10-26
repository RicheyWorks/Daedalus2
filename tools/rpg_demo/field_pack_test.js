// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/field_pack_test.js
// Actual PACK/menu/useItem/recruit/status/save functions, canonical shop items and fish effects.
// Fake render/storage/controller-label peers; no browser/devices/assets/build/full-IIFE execution.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Save = require("./journey-save.js");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, interiors = data("interiors").interiors, menus = data("menus").layouts;
const fish = data("prism-fish").fish, bosses = data("prism-bosses").bosses, spells = data("spells").spells;
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const source = [line("const CHARS ="), line("const tw ="), line("const hit ="), line("function clearActionButtons()"), line("function wakeAt("),
  between("function gauge(", "/* ---------- party ---------- */"), between("const START_LEVEL =", "/* Recruits:"),
  between("function recruitsFor(", "function recruitBeaten("), line("const atkOf ="), line("const defOf ="), line("const spellOf ="),
  between("const magicShopCaster =", "function shopTick("), between("let menu = null;", "function drawEquip("),
  between("const STATUS =", "/* ---------- bestiary"), between("function spellHint(", "function drawBattle("),
  between("function titlePrompt(", "function drawTitle("), between("function saveGame()", "function eraseSavedJourney()"),
  "this.api={start:()=>{party=buildParty();},openMenu,menuTick,drawMenu,drawFieldPack,fieldItemForecast,useItem,fieldItems,itemStock,itemKind,recruit,buy,saveGame,roster," +
  "party:()=>party,reserve:()=>reserve,bag:()=>bag,menu:()=>menu,chars:CHARS,setGold:n=>{gold=n;},setBag:b=>{bag=b;}," +
  "shortenFront:n=>{reserve=party.slice(n).concat(reserve);party=party.slice(0,n);}," +
  "applyFade:()=>{const cb=fadeCb;fadeCb=null;if(cb)cb();fade=0;}," +
  "resources:()=>({party,reserve,bag,gold,state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},opened:Array.from(opened),map,P,D,B})," +
  "view:()=>({mode,menu,pressed,fade,hasFade:!!fadeCb})};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], sounds = [], pressed = {}, records = new Map(), storage = { reads: 0, writes: 0 }, gear = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors[r]))
    for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = clone(item);
  // Runtime gear metadata for caught fish; fixture bag seeding below does not claim a fishing/UI run.
  if (realm === "prism") for (const f of fish) gear[f.name] = { name: f.name, effect: f.effect, price: f.price, fish: true };
  const known = new Set(parties[realm].members.flatMap(m => m.spells)), math = Object.create(Math);
  math.random = () => { throw new Error("PACK rendering/item use must not consume gameplay RNG"); };
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, menus: clone(menus[realm]), rects: { sprites: {} },
      spells: clone(spells.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2))),
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, Math: math, pressed, PAD: null, mode: "field", map: { kind: "town", retained: true }, P: { x: 7, y: 9, dir: "left" }, B: null, fade: 0, fadeCb: null,
    state: { beaten: new Set(), seen: {}, fish: {}, quests: {}, ways: new Set(), day: 1, minute: 480, air: null, returnTo: null, steps: 0, sinceBattle: 0 },
    opened: new Set(["retained/chest"]), shop: { kind: "item", msg: "" }, SAVE_KEY: realm + ".save.v1",
    sfx: s => sounds.push(s), clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), drawField: () => paints.push({ kind: "field" }), spr() {},
    shardCount: () => 0, clockText: () => "D1 08:00", isNight: () => false,
    // Bitmap glyph5x7 plus default1px shadow on6px advances: these bounds include the shadow.
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    cursor: (x, y) => paints.push({ kind: "cursor", x, y }), win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }),
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); } },
    localStorage: { getItem(k) { storage.reads++; return records.get(k) ?? null; }, setItem(k, v) { storage.writes++; records.set(k, v); }, removeItem() { throw new Error("PACK cannot erase saves"); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify(c.api.resources());
  return { c, api: c.api, paints, sounds, storage, records, resources,
    tick(...keys) { keys.forEach(k => { pressed[k] = true; }); c.api.menuTick(); },
    draw() { paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), saved = JSON.stringify([...records]), counts = JSON.stringify(storage), soundCount = sounds.length;
      c.api.drawMenu(); assert.equal(resources(), before, "render preserves roster, statuses, bag, progress, clock, position and catalogs");
      assert.equal(JSON.stringify(c.api.view()), view, "render preserves cursor/input/mode and does not execute a camp fade");
      assert.equal(JSON.stringify([...records]), saved); assert.equal(JSON.stringify(storage), counts, "render never accesses storage"); assert.equal(sounds.length, soundCount); return paints; },
    validSave() { assert.equal(c.api.saveGame(), true); const read = Save.read(records.get(c.SAVE_KEY), realm, c.D.party.members); assert.equal(read.ok, true, read.reason); return read.value; },
    labels(confirm = "ABCDEFGH", cancel = "IJKLMNOP") { c.PAD = { devices: () => [{ index: 0 }], label: action => action === "confirm" ? confirm : cancel }; }
  };
}
function earned(s) {
  for (const dungeon of ["Cinder Forge", "Windcut Aerie", "Sunwell Sanctum", "Gearwright's Folly"]) {
    s.api.recruit(dungeon); const boss = bosses.find(b => b.dungeon === dungeon); assert.ok(boss); s.c.state.beaten.add(boss.name);
  }
  assert.equal(s.api.roster().length, 8); return s;
}
function stocked(s) {
  s.api.setGold(100000); for (const it of interiors.prism.Item.stock) s.api.buy(clone(it));
  for (const f of fish) s.api.bag()[f.name] = 2; // Caught-fish inventory fixture, using canonical metadata.
  return s;
}
function open(s) { s.api.openMenu(); s.tick("a"); assert.equal(s.api.menu().sub, "item"); return s; }
function item(s, name) { const target = s.api.fieldItems().indexOf(name); assert.ok(target >= 0, name); const m = s.api.menu();
  for (let i = 0; m.ii !== target && i < s.api.fieldItems().length; i++) s.tick("down"); assert.equal(m.ii, target); return name; }
function who(s, index) { const m = s.api.menu(); for (let i = 0; m.who !== index && i < s.api.roster().length; i++) s.tick("right"); assert.equal(m.who, index); return s.api.roster()[index]; }
const at = (s, y, x) => s.paints.filter(p => p.kind === "text" && p.y === y && (x === undefined || p.x === x));
function forecast(s) { s.draw(); assert.equal(at(s, 184, 12).length, 1); return at(s, 184, 12)[0]; }
function noStorage(s, fn) { const counts = JSON.stringify(s.storage), bytes = JSON.stringify([...s.records]); fn(); assert.equal(JSON.stringify(s.storage), counts); assert.equal(JSON.stringify([...s.records]), bytes); }
function bounds(s) { for (const p of s.paints.filter(p => ["text", "rect", "window"].includes(p.kind))) {
  assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p));
  if (p.kind === "text") assert.ok([...p.label].every(k => s.api.chars.includes(k)), p.label);
} }
function assertPack(s) {
  s.draw(); const m = s.api.menu(), items = Array.from(s.api.fieldItems()), selected = Math.max(0, Math.min(m.ii, items.length - 1)), from = Math.max(0, Math.min(selected - 5, items.length - 6)), mid = Math.floor(s.c.W / 2);
  const cursors = s.paints.filter(p => p.kind === "cursor"); assert.equal(cursors.length, items.length ? 2 : 1);
  if (items.length) assert.ok(cursors.some(p => p.x === 12 && p.y === 62 + (selected - from) * 18));
  assert.ok(cursors.some(p => p.x === mid + 12 && p.y === 62 + m.who * 14));
  assert.equal(s.paints.filter(p => p.kind === "text" && p.x === 24 && p.y >= 62 && p.y <= 152).length, Math.min(6, items.length));
  s.api.roster().forEach((member, i) => { const row = at(s, 62 + i * 14); assert.ok(row.some(p => p.x === mid + 24)); assert.ok(row.some(p => p.x >= mid && p.label === (member.hp > 9999 ? "9999+" : String(member.hp)))); });
  assert.ok(!s.paints.some(p => p.kind === "window" && p.x === 20 && p.y === 60), "old popup cannot obscure either column");
}
check("ordinary insertion order/filtering and six-row scrolling preserve the exact selected item", () => {
  const s = open(stocked(earned(session()))); s.api.bag()["Copper Blade"] = 2; s.api.bag().Reedling = 0;
  const expected = ["Herb Tonic", "Antidote Leaf", "Clear Draught", "Feather of Waking", "Wake Bell", "Camp Tent", ...fish.filter(f => f.name !== "Reedling").map(f => f.name)];
  assert.deepEqual(Array.from(s.api.fieldItems()), expected); assert.ok(!s.api.fieldItems().includes("Smoke Pouch"));
  for (let i = 0; i < expected.length; i++) { item(s, expected[i]); assertPack(s); assert.ok(at(s, 10, 12).some(p => p.label === expected[i].toUpperCase()));
    assert.equal(at(s, 50, 24)[0].label, "BAG " + (i + 1) + "/" + expected.length); }
  s.tick("down"); assert.equal(s.api.menu().ii, 0); s.tick("up"); assert.equal(s.api.menu().ii, expected.length - 1);
});
check("all eight companions and reader-valid smaller fronts retain actual membership and independent target/item cursors", () => {
  for (const front of [4, 1, 2, 3]) { const s = stocked(earned(session())); if (front < 4) s.api.shortenFront(front); const saved = s.validSave(); assert.equal(saved.party.length, front); open(s); item(s, "Feather of Waking");
    const ii = s.api.menu().ii; for (let i = 0; i < 8; i++) { const member = who(s, i); assertPack(s); const role = s.api.party().includes(member) ? "FRONT" : "RESERVE";
      assert.equal(at(s, 22, 12)[0].label, "TO " + member.name.toUpperCase() + " / " + role + " HP " + member.hp + "/" + member.max); assert.equal(s.api.menu().ii, ii); }
    s.tick("right"); assert.equal(s.api.menu().who, 0); s.tick("left"); assert.equal(s.api.menu().who, 7);
  }
});
check("every canonical healing item/fish forecast matches the actual selected ally HP and single inventory spend", () => {
  const names = ["Herb Tonic", ...fish.filter(f => /^heal /.test(f.effect)).map(f => f.name)];
  for (const name of names) { const s = open(stocked(earned(session()))), target = who(s, 7); item(s, name); target.hp = 1;
    const count = s.api.bag()[name], before = clone(s.api.resources()), amount = +s.c.D.gear[name].effect.match(/heal (\d+)/)[1] * 4, after = Math.min(target.max, 1 + amount);
    assert.equal(forecast(s).label, "IF USED: HP 1>" + after + " +" + (after - 1)); noStorage(s, () => s.tick("a"));
    const expected = clone(before); expected.reserve.find(m => m.job === target.job).hp = after; expected.bag[name] = count - 1; assert.equal(JSON.stringify(s.api.resources()), JSON.stringify(expected));
    const once = s.resources(); s.tick(); assert.equal(s.resources(), once, "one press cannot consume twice");
  }
});
function downedMp(production = source) {
  for (const name of ["Clear Draught", ...fish.filter(f => /^restore /.test(f.effect)).map(f => f.name)]) { const s = open(stocked(earned(session(320, "prism", production)))), target = who(s, 1); item(s, name); assert.ok(target.mmax > 0); target.hp = 0; target.mp = 0; target.status = { poison: true, sleep: 2 };
    const count = s.api.bag()[name], beforeStatus = JSON.stringify(target.status), after = Math.min(target.mmax, +s.c.D.gear[name].effect.match(/(\d+)/)[1] * 3);
    assert.equal(forecast(s).label, "IF USED: MP 0>" + after + " +" + after); assert.ok(at(s, 22, 12)[0].label.endsWith(" MP 0/" + target.mmax));
    noStorage(s, () => s.tick("a")); assert.equal(target.hp, 0); assert.equal(target.mp, after); assert.equal(JSON.stringify(target.status), beforeStatus); assert.equal(s.api.bag()[name], count - 1);
  }
}
check("every canonical MP draught/fish remains usable on a downed companion without revival/status changes", () => downedMp());
check("full HP/MP forecasts show +0 and real use still consumes one", () => {
  for (const [name, pool, max] of [["Herb Tonic", "hp", "max"], ["Clear Draught", "mp", "mmax"]]) { const s = open(stocked(session())), target = s.api.roster()[1]; who(s, 1); item(s, name); target[pool] = target[max]; const before = target[pool], count = s.api.bag()[name];
    assert.equal(forecast(s).label, "IF USED: " + pool.toUpperCase() + " " + before + ">" + before + " +0"); noStorage(s, () => s.tick("a")); assert.equal(target[pool], before); assert.equal(s.api.bag()[name], count - 1); }
});
check("Feather forecasts quarter-HP revival and real use clears all target statuses while keeping MP", () => {
  const s = open(stocked(earned(session()))), target = who(s, 6); item(s, "Feather of Waking"); assert.ok(target.mmax > 0); target.hp = 0; target.mp = 1; target.status = { poison: true, sleep: 2, protect: 3 };
  const hp = Math.ceil(target.max / 4), count = s.api.bag()["Feather of Waking"]; assert.equal(forecast(s).label, "REVIVE: HP 0>" + hp + ". STATUS CLEARED.");
  noStorage(s, () => s.tick("a")); assert.equal(target.hp, hp); assert.equal(target.mp, 1); assert.equal(JSON.stringify(target.status), "{}"); assert.equal(s.api.bag()["Feather of Waking"], count - 1);
});
check("a standing Feather target is refused without consuming inventory or changing resources", () => {
  const s = open(stocked(session())); item(s, "Feather of Waking"); assert.equal(forecast(s).label, "ALREADY STANDING."); assert.equal(at(s, 184, 12)[0].color, "#f8a0a0"); const before = s.resources();
  s.tick("a"); assert.equal(s.resources(), before); assert.match(s.api.menu().msg, /IS STANDING ALREADY/);
});
check("poison/sleep cures match real truthy status removal and preserve refusal order/inventory", () => {
  for (const [name, key, word] of [["Antidote Leaf", "poison", "POISONED"], ["Wake Bell", "sleep", "ASLEEP"]]) for (const reason of ["present", "absent", "down"]) {
    const s = open(stocked(session())), target = s.api.roster()[0]; item(s, name); target.status = { [key]: reason === "absent" ? 0 : key === "poison" ? true : 2, protect: 3 }; if (reason === "down") target.hp = 0;
    const count = s.api.bag()[name], before = s.resources(), prediction = reason === "down" ? "TOO LATE FOR THAT." : reason === "absent" ? "TARGET IS NOT " + word + "." : "CLEARS " + word + " STATUS.";
    assert.equal(forecast(s).label, prediction); noStorage(s, () => s.tick("a"));
    if (reason === "present") { assert.equal(target.status[key], undefined); assert.equal(target.status.protect, 3); assert.equal(s.api.bag()[name], count - 1); }
    else { assert.equal(s.resources(), before); assert.equal(s.api.menu().msg, reason === "down" ? prediction : target.name + " IS NOT " + word + "."); }
  }
});
check("world camping restores the whole roster, clears only poison and wakes at6 only when its fade runs", () => {
  for (const minute of [240, 480]) { const s = stocked(earned(session())); s.c.map.kind = "world"; s.c.state.day = 2; s.c.state.minute = minute; open(s); item(s, "Camp Tent");
    s.api.roster().forEach((m, i) => { m.hp = i % 2 ? 0 : 1; m.mp = 0; m.status = { poison: true, sleep: 2, protect: 3 }; });
    const count = s.api.bag()["Camp Tent"]; assert.equal(forecast(s).label, "FULL HP/MP. POISON CLEARED."); assert.equal(at(s, 22, 12)[0].label, "CAMP: WHOLE PARTY");
    noStorage(s, () => s.tick("a")); s.api.roster().forEach(m => { assert.equal(m.hp, m.max); assert.equal(m.mp, m.mmax); assert.equal(m.status.poison, undefined); assert.equal(m.status.sleep, 2); assert.equal(m.status.protect, 3); });
    assert.equal(s.api.bag()["Camp Tent"], count - 1); assert.equal(s.c.fade, 1); assert.equal(s.c.state.minute, minute); assert.equal(s.c.state.day, 2); s.draw();
    noStorage(s, () => s.api.applyFade()); assert.equal(s.c.state.minute, 360); assert.equal(s.c.state.day, minute >= 360 ? 3 : 2);
  }
});
check("camping refusal matches actual non-world or battle contexts without a party/inventory/time change", () => {
  for (const context of ["town", "dungeon", "battle"]) { const s = open(stocked(session())); item(s, "Camp Tent"); s.c.map.kind = context === "battle" ? "world" : context; if (context === "battle") s.c.B = {};
    assert.equal(forecast(s).label, "PITCH THE TENT OUT ON THE OPEN ROAD."); const before = s.resources(), view = JSON.stringify(s.api.view()); s.tick("a");
    assert.equal(s.resources(), before); assert.equal(s.c.fade, 0); assert.equal(s.api.menu().msg, "PITCH THE TENT OUT ON THE OPEN ROAD."); assert.equal(JSON.parse(view).hasFade, false);
  }
});
check("consuming the final item leaves a safe empty PACK feedback frame, then follows the existing next-tick exit", () => {
  const s = session(); s.api.setBag({ "Herb Tonic": 1 }); open(s); s.api.roster()[0].hp = 1; s.tick("a"); const m = s.api.menu(); assert.equal(m.sub, "item"); assert.equal(s.api.bag()["Herb Tonic"], 0);
  const message = m.msg; assertPack(s); assert.equal(at(s, 10, 12)[0].label, "PACK"); assert.equal(at(s, 184, 12)[0].label, "NO ITEMS TO USE."); assert.equal(at(s, 196, 12)[0].label, message.toUpperCase());
  const before = s.resources(); s.tick(); assert.equal(m.sub, null); assert.equal(s.resources(), before); assert.equal(m.msg, message);
});
check("Back plus Confirm returns to field commands and cannot use an item on this or the next tick", () => {
  const s = open(stocked(earned(session()))); item(s, "Feather of Waking"); who(s, 7).hp = 0; const before = s.resources(); s.tick("b", "a"); assert.equal(s.api.menu().sub, null); assert.equal(s.resources(), before); assert.equal(s.c.pressed.a, false);
  s.tick(); assert.equal(s.api.menu().sub, null); assert.equal(s.resources(), before);
});
check("Portal retains the old popup, original target controls and item transaction", () => {
  const s = open(session(256, "portal")), target = who(s, 1); target.hp = 1; s.draw(); assert.ok(s.paints.some(p => p.kind === "window" && p.x === 20 && p.y === 60 && p.w === 220 && p.h === 112));
  assert.ok(!at(s, 50, 24).some(p => p.label.startsWith("BAG "))); const count = s.api.bag()["Herb Tonic"], hp = Math.min(target.max, 121); noStorage(s, () => s.tick("a")); assert.equal(target.hp, hp); assert.equal(s.api.bag()["Herb Tonic"], count - 1);
});
for (const width of [320, 256]) check("six item rows/eight companions, large counts, sharp-s names and mapped guidance fit at " + width, () => {
  const s = stocked(earned(session(width))); for (const member of s.api.roster()) { member.name = "ß".repeat(64); member.max = Number.MAX_SAFE_INTEGER; member.hp = member.max; member.mp = member.mmax = Number.MAX_SAFE_INTEGER; }
  for (const k of Object.keys(s.api.bag())) s.api.bag()[k] = Number.MAX_SAFE_INTEGER; open(s); item(s, "Feather of Waking"); who(s, 7); s.api.menu().msg = "ß".repeat(64); s.labels(); s.validSave(); assertPack(s); bounds(s);
  assert.equal(at(s, 10, 12)[0].label, "FEATHER OF WAKING"); assert.ok(at(s, 10).some(p => p.label === "QTY 9999+")); assert.ok(at(s, 22, 12)[0].label.endsWith(" / RESERVE HP 9999+/9999+"));
  assert.ok(at(s, 22, 12)[0].label.startsWith("TO SS")); assert.equal(at(s, 212, 12)[0].label, "ABCDEFGH: USE  IJKLMNOP: BACK");
  const mid = Math.floor(width / 2); for (let i = 0; i < 6; i++) { const row = at(s, 62 + i * 18), name = row.find(p => p.x === 24), count = row.find(p => p.x < mid && p.label.startsWith(":")); assert.ok(name && count); assert.ok(name.x + name.w < count.x && count.x + count.w <= mid - 12); }
  for (let i = 0; i < 8; i++) { const row = at(s, 62 + i * 14), name = row.find(p => p.x === mid + 24), hp = row.find(p => p.x >= mid && p.label === "9999+"); assert.ok(name && hp); assert.ok(name.x + name.w < hp.x); assert.ok(62 + i * 14 + 8 < 180); }
  const first = JSON.stringify(s.paints); s.draw(); assert.equal(JSON.stringify(s.paints), first, "repeated render is deterministic and pure");
});
check("keyboard fallback and invalid controller labels retain complete use/back guidance", () => {
  const s = open(session(256)); s.draw(); bounds(s); assert.equal(at(s, 212, 12)[0].label, "Z/SPACE: USE  X/ESC: BACK"); s.labels("INVALID LABEL", "<BAD>"); s.draw(); bounds(s); assert.equal(at(s, 212, 12)[0].label, "Z/SPACE: USE  X/ESC: BACK");
});
check("controlled old popup and a downed-MP preview refusal reproduce the visibility/rule mismatch", () => {
  const legacy = source.replace('  if (sub === "item" && (D.realm_key || "prism") === "prism") return drawFieldPack();', ""); assert.notEqual(legacy, source);
  assert.throws(() => { const s = open(stocked(earned(session(320, "prism", legacy)))); assertPack(s); }, assert.AssertionError);
  const wrong = source.replace('  if (kind === "mp") {\n    const after', '  if (kind === "mp") {\n    if (member.hp <= 0) return "TOO LATE FOR THAT.";\n    const after'); assert.notEqual(wrong, source);
  assert.throws(() => downedMp(wrong), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("field PACK: " + checks + " focused groups passed; fake render/storage/label peers, no runtime/device acceptance");
