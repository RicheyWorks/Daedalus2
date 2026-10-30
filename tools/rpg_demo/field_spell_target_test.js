// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/field_spell_target_test.js
// Actual menu/cast/recruit/save/gauge functions and canonical runtime spell catalogs.
// Fake canvas/storage/controller-label peers; no browser, device, assets, build or game-loop execution.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Save = require("./journey-save.js");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8"));
const clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, interiors = data("interiors").interiors, menus = data("menus").layouts;
const allSpells = data("spells").spells, bosses = data("prism-bosses").bosses;
function between(start, end, input = html) { const a = input.indexOf(start), b = input.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return input.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const source = [line("const CHARS ="), line("const tw ="), line("const hit ="), line("function clearActionButtons()"),
  between("function gauge(", "/* ---------- party ---------- */"), between("const START_LEVEL =", "/* Recruits:"),
  between("function recruitsFor(", "function recruitBeaten("), line("const atkOf ="), line("const defOf ="), line("const spellOf ="),
  between("const magicShopCaster =", "function shopTick("), between("let menu = null;", "function drawEquip("),
  between("const STATUS =", "/* ---------- bestiary"), between("function spellHint(", "function drawBattle("),
  between("function titlePrompt(", "function drawTitle("), between("function saveGame()", "function eraseSavedJourney()"),
  "this.api={start:()=>{party=buildParty();},openMenu,menuTick,drawMenu,drawFieldSpellTarget,recruit,buy,fieldSpells,saveGame,roster," +
  "party:()=>party,reserve:()=>reserve,menu:()=>menu,chars:CHARS,setGold:n=>{gold=n;}," +
  "shortenFront:n=>{reserve=party.slice(n).concat(reserve);party=party.slice(0,n);}," +
  "resources:()=>({party,reserve,bag,gold,state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},opened:Array.from(opened),map,P,D})," +
  "view:()=>({mode,menu,pressed})};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], sounds = [], pressed = {}, records = new Map(), storage = { reads: 0, writes: 0 }, gear = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors[r]))
    for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = clone(item);
  const known = new Set(parties[realm].members.flatMap(m => m.spells)), math = Object.create(Math);
  math.random = () => { throw new Error("spell targeting/rendering must not consume game RNG"); };
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, menus: clone(menus[realm]), rects: { sprites: {} },
      // This is build_demo.py's existing known-or-tier<=2 selection, not an invented tier-three learning path.
      spells: clone(allSpells.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2))),
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, Math: math, pressed, PAD: null, mode: "field", map: { kind: "town", retained: true }, P: { x: 7, y: 9, dir: "left" }, B: null,
    state: { beaten: new Set(), seen: {}, fish: {}, quests: {}, ways: new Set(), day: 1, minute: 480, air: null, returnTo: null, steps: 0, sinceBattle: 0 },
    opened: new Set(["retained/chest"]), shop: { kind: "magic", msg: "" }, SAVE_KEY: realm + ".save.v1",
    sfx: x => sounds.push(x), clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)),
    drawField: () => paints.push({ kind: "field" }), spr() {}, shardCount: () => 0, clockText: () => "D1 08:00", isNight: () => false,
    // Production draws5x7 glyphs on6px advances with a1px default shadow: this records the full footprint.
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    cursor: (x, y) => paints.push({ kind: "cursor", x, y }), win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }),
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); } },
    localStorage: { getItem(k) { storage.reads++; return records.get(k) ?? null; }, setItem(k, v) { storage.writes++; records.set(k, v); }, removeItem() { throw new Error("targeting cannot erase saves"); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify(c.api.resources());
  return { c, api: c.api, paints, sounds, storage, records, resources,
    tick(...keys) { keys.forEach(k => { pressed[k] = true; }); c.api.menuTick(); },
    draw() { paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), saved = JSON.stringify([...records]), counts = JSON.stringify(storage), soundCount = sounds.length;
      c.api.drawMenu(); assert.equal(resources(), before, "render preserves members, resources, progress, position and map");
      assert.equal(JSON.stringify(c.api.view()), view, "render preserves input edges, target, book and mode");
      assert.equal(JSON.stringify([...records]), saved); assert.equal(JSON.stringify(storage), counts, "render never reads/writes storage"); assert.equal(sounds.length, soundCount); return paints; },
    validSave() { assert.equal(c.api.saveGame(), true); const raw = records.get(c.SAVE_KEY), read = Save.read(raw, realm, c.D.party.members); assert.equal(read.ok, true, read.reason); return read.value; },
    labels(confirm = "ABCDEFGH", cancel = "IJKLMNOP") { c.PAD = { devices: () => [{ index: 0 }], label: action => action === "confirm" ? confirm : cancel }; }
  };
}
function earned(s) {
  // Canonical demo dependency order: three shard routes, then the optional Folly recruit.
  for (const dungeon of ["Cinder Forge", "Windcut Aerie", "Sunwell Sanctum", "Gearwright's Folly"]) {
    assert.ok(s.c.D.party.members.some(m => m.joins === "after " + dungeon));
    s.api.recruit(dungeon); const boss = bosses.find(b => b.dungeon === dungeon); assert.ok(boss); s.c.state.beaten.add(boss.name);
  }
  assert.equal(s.api.roster().length, 8); return s;
}
function learnRestore(s) { s.api.setGold(100000); s.api.buy(clone(interiors.prism.Magic.stock.find(it => it.name === "Restore"))); assert.ok(s.api.roster().find(m => m.job === "Lightmender").spells.includes("Restore")); return s; }
function openTarget(s, name = "Mend", caster = s.api.roster().find(m => m.spells.includes(name))) {
  assert.ok(caster); s.api.openMenu(); s.tick("down"); s.tick("a"); const m = s.api.menu(), who = s.api.roster().indexOf(caster);
  assert.equal(m.sub, "magic-who"); for (let n = 0; m.who !== who && n < s.api.roster().length; n++) s.tick("right");
  assert.equal(m.who, who); s.tick("a"); assert.equal(m.sub, "magic");
  const index = s.api.fieldSpells(caster).findIndex(sp => sp.name === name); assert.ok(index >= 0);
  for (let n = 0; m.ii !== index && n < s.api.fieldSpells(caster).length; n++) s.tick("down");
  assert.equal(m.ii, index); s.tick("a"); assert.equal(m.sub, "magic-target"); assert.equal(m.spell.name, name); return m;
}
function select(s, index) { const m = s.api.menu(), n = s.api.roster().length; for (let i = 0; m.target !== index && i < n; i++) s.tick("down"); assert.equal(m.target, index); }
const at = (s, y, x) => s.paints.filter(p => p.kind === "text" && p.y === y && (x === undefined || p.x === x));
function preview(s) { s.draw(); const row = at(s, 184, 12); assert.equal(row.length, 1); return row[0]; }
function assertPicker(s) {
  s.draw(); const r = Array.from(s.api.roster()), m = s.api.menu();
  assert.equal(s.paints.filter(p => p.kind === "cursor").length, 1); assert.ok(s.paints.some(p => p.kind === "cursor" && p.x === 12 && p.y === 50 + m.target * 16));
  assert.ok(at(s, 34).some(p => p.label === (m.target + 1) + "/" + r.length));
  r.forEach((member, i) => {
    const y = 50 + i * 16, role = at(s, y, s.c.W < 320 ? 98 : 146); assert.equal(role.length, 1);
    assert.equal(role[0].label, s.api.party().includes(member) ? "FRONT" : "RESERVE");
    assert.ok(at(s, y, 26).length === 1, "every roster entry remains visible");
    const gauge = s.paints.filter(p => p.kind === "rect" && p.color === "#f0f0f8" && p.x === 28 && p.y === y + 9);
    assert.equal(gauge.length, 1); assert.equal(gauge[0].h, 5); assert.equal(gauge[0].w, s.c.W - 54); assert.ok(y + 9 + 5 <= 176);
  });
  assert.ok(!s.paints.some(p => p.kind === "window" && p.x === 20 && p.y === 60), "old spell popup cannot cover target rows");
}
function assertBounds(s) {
  for (const p of s.paints.filter(p => ["text", "rect", "window"].includes(p.kind))) {
    assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p));
    if (p.kind === "text") assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), "all shown glyphs are in the bitmap font: " + p.label);
  }
}
check("all eight earned companions, including reserves, remain visible and selectable with exact role/HP/counter", () => {
  const s = earned(session()), m = openTarget(s); s.validSave();
  for (let i = 0; i < 8; i++) { select(s, i); assertPicker(s); const member = s.api.roster()[i], row = at(s, 50 + i * 16);
    assert.ok(row.some(p => p.label === member.name.toUpperCase())); assert.ok(row.some(p => p.label === "HP " + member.hp + "/" + member.max)); }
  assert.equal(m.who, 1, "canonical starter Ysolde remains the selected caster");
  assert.ok(at(s, 10).some(p => p.label === "MEND")); assert.ok(at(s, 10).some(p => p.label === "5 MP"));
  assert.ok(at(s, 22, 12).some(p => p.label === "CASTER YSOLDE MP " + s.api.roster()[1].mp + "/" + s.api.roster()[1].mmax));
  s.tick("down"); assert.equal(m.target, 0, "last companion wraps to the first"); s.tick("up"); assert.equal(m.target, 7);
});
check("reader-valid one/two/three-member fronts label actual membership, including a living reserve caster", () => {
  for (const front of [1, 2, 3]) { const s = earned(session()); s.api.shortenFront(front); const saved = s.validSave(); assert.equal(saved.party.length, front); assert.equal(saved.reserve.length, 8 - front);
    const m = openTarget(s); assert.equal(m.who, 1); select(s, 7); assertPicker(s);
    assert.equal(at(s, 50 + front * 16, 146)[0].label, "RESERVE");
    const caster = s.api.roster()[m.who], target = s.api.roster()[7], mp = caster.mp; target.hp = 1; const forecast = preview(s).label;
    s.tick("a"); assert.equal(caster.mp, mp - m.spell.mp); assert.ok(target.hp > 1); assert.equal(forecast, "IF CAST: HP 1>" + target.hp + " +" + (target.hp - 1));
  }
});
check("Mend forecasts agree with the real Confirm for each front/reserve target and alter only caster MP/recipient HP", () => {
  for (let i = 0; i < 8; i++) { const s = earned(session()), m = openTarget(s), target = s.api.roster()[i], caster = s.api.roster()[m.who]; target.hp = 1; select(s, i);
    const before = clone(s.api.resources()), expected = clone(before), peers = expected.party.concat(expected.reserve), expectedTarget = peers.find(p => p.job === target.job), expectedCaster = peers.find(p => p.job === caster.job);
    const amount = Math.round(m.spell.power * 1.5 + caster.st.spr * 3), hp = Math.min(target.max, 1 + amount); expectedTarget.hp = hp; expectedCaster.mp -= m.spell.mp;
    assert.equal(preview(s).label, "IF CAST: HP 1>" + hp + " +" + (hp - 1)); const storageBefore = JSON.stringify(s.storage), recordsBefore = JSON.stringify([...s.records]); s.tick("a");
    assert.equal(JSON.stringify(s.api.resources()), JSON.stringify(expected)); assert.equal(m.sub, "magic-target");
    assert.equal(JSON.stringify(s.storage), storageBefore, "casting never autosaves or reads storage"); assert.equal(JSON.stringify([...s.records]), recordsBefore);
    const after = s.resources(); s.tick(); assert.equal(s.resources(), after, "no second cast without a fresh Confirm"); s.draw(); assert.ok(at(s, 196, 12)[0].label.includes(" CASTS MEND."));
  }
});
for (const name of ["Mend", "Restore"]) check("canonical " + name + " uses the actual capped HP result while charging normal MP", () => {
  const s = name === "Restore" ? learnRestore(session()) : session(), m = openTarget(s, name), target = s.api.roster()[0], caster = s.api.roster()[m.who];
  target.hp = target.max - 2; const mp = caster.mp; assert.equal(preview(s).label, "IF CAST: HP " + target.hp + ">" + target.max + " +2");
  s.tick("a"); assert.equal(target.hp, target.max); assert.equal(caster.mp, mp - m.spell.mp); assert.equal(m.msg, caster.name.toUpperCase() + " CASTS " + name.toUpperCase() + ". +2 HP.");
  assert.equal(preview(s).label, "IF CAST: HP " + target.max + ">" + target.max + " +0");
});
check("full-HP +0 remains a normal MP-spending cast, rather than implying a new free-cast rule", () => {
  const s = session(), m = openTarget(s), target = s.api.roster()[0], caster = s.api.roster()[1], hp = target.hp, mp = caster.mp;
  assert.equal(preview(s).label, "IF CAST: HP " + hp + ">" + hp + " +0"); s.tick("a"); assert.equal(target.hp, hp); assert.equal(caster.mp, mp - m.spell.mp);
  assert.equal(m.msg, caster.name.toUpperCase() + " CASTS MEND. +0 HP."); s.draw(); assert.equal(at(s, 196, 12)[0].label, m.msg);
});
check("forecast and real Confirm preserve caster-down, target-down, then MP refusal priority without resource changes", () => {
  for (const reason of ["caster", "target", "mp"]) { const s = session(), m = openTarget(s), caster = s.api.roster()[1], target = s.api.roster()[0];
    if (reason === "caster") caster.hp = 0; if (reason !== "mp") target.hp = 0; caster.mp = 0; s.validSave();
    const expected = reason === "caster" ? "CASTER IS DOWN. REVIVE FIRST." : reason === "target" ? "TOO LATE FOR THAT SPELL." : "NOT ENOUGH MP.";
    assert.equal(preview(s).label, expected); assert.equal(at(s, 184, 12)[0].color, "#f8a0a0"); const before = s.resources(), writes = s.storage.writes;
    s.tick("a"); assert.equal(s.resources(), before); assert.equal(s.storage.writes, writes); assert.equal(m.sub, "magic-target");
    assert.equal(m.msg, reason === "caster" ? caster.name.toUpperCase() + " IS DOWN. REVIVE FIRST." : expected); s.draw(); assert.equal(at(s, 196, 12)[0].label, m.msg);
    const after = s.resources(); s.tick(); assert.equal(s.resources(), after);
  }
});
check("Back plus Confirm returns to the original spell book and cannot cast on the next tick", () => {
  const s = learnRestore(earned(session())), m = openTarget(s, "Restore"), spell = m.spell, who = m.who, index = m.ii; select(s, 7); const before = s.resources();
  s.tick("b", "a"); assert.equal(m.sub, "magic"); assert.equal(m.who, who); assert.equal(m.ii, index); assert.equal(m.spell, spell); assert.equal(s.resources(), before);
  s.tick(); assert.equal(m.sub, "magic"); assert.equal(s.resources(), before); assert.equal(s.c.pressed.a, false);
  s.draw(); assert.ok(s.paints.some(p => p.kind === "text" && p.label === "MAGIC" && p.x === 12 && p.y === 10)); assert.ok(!s.paints.some(p => p.kind === "window" && p.x === 20 && p.y === 60)); // Prismheart Back returns to the readable field spellbook, not the legacy popup
});
check("battle-only Ward stays in the original spell book and cannot enter the new target view", () => {
  const s = session(); openTarget(s); s.tick("b"); const m = s.api.menu(); s.tick("down"); assert.equal(s.api.fieldSpells(s.api.roster()[m.who])[m.ii].name, "Ward");
  const before = s.resources(); s.tick("a"); assert.equal(m.sub, "magic"); assert.match(m.msg, /WARD IS FOR BATTLE/); assert.equal(s.resources(), before);
  s.draw(); assert.ok(!at(s, 184, 12).some(p => p.label.startsWith("IF CAST:")));
});
check("Portal preserves its existing spell popup and target Confirm/Back behavior", () => {
  const s = session(256, "portal"), m = openTarget(s), target = s.api.roster()[0], caster = s.api.roster()[m.who]; target.hp = target.max - 2;
  s.draw(); assert.ok(s.paints.some(p => p.kind === "window" && p.x === 20 && p.y === 60 && p.w === 220 && p.h === 112));
  assert.ok(!at(s, 22, 12).some(p => p.label.startsWith("CASTER "))); const mp = caster.mp, amount = Math.round(m.spell.power * 1.5 + caster.st.spr * 3);
  s.tick("a"); assert.equal(target.hp, target.max); assert.equal(caster.mp, mp - m.spell.mp); assert.equal(m.msg, caster.name.toUpperCase() + " CASTS MEND. +" + amount + " HP.");
  assert.notEqual(amount, 2, "Portal retains raw-amount feedback independently of capped actual gain");
  const before = s.resources(); s.tick("b", "a"); assert.equal(m.sub, "magic"); assert.equal(s.resources(), before);
});
for (const width of [320, 256]) check("eight rows, actual five-pixel gauges and legacy names/stat caps remain bounded and pure at " + width, () => {
  const s = earned(session(width)); for (const member of s.api.roster()) { member.name = "ß".repeat(64); member.max = Number.MAX_SAFE_INTEGER; member.hp = member.max; member.mp = member.mmax = Number.MAX_SAFE_INTEGER; }
  const m = openTarget(s), target = s.api.roster()[0]; target.hp -= 10; s.api.roster()[7].hp = 0; m.msg = "ß".repeat(64); s.validSave(); s.labels();
  assertPicker(s); assertBounds(s); assert.ok(at(s, 50, 26)[0].label.endsWith("...")); assert.ok(at(s, 50, 26)[0].label.startsWith("SS"));
  assert.ok(at(s, 50).some(p => p.label === "HP 9999+/9999+")); assert.ok(at(s, 22, 12)[0].label.endsWith(" MP 9999+/9999+"));
  assert.equal(at(s, 184, 12)[0].label, "IF CAST: HP 9999+>9999+ +10"); assert.equal(at(s, 196, 12)[0].label.length, Math.floor((width - 24) / 6));
  assert.equal(at(s, 212, 12)[0].label, "ABCDEFGH: CAST  IJKLMNOP: BACK");
  const roleX = width < 320 ? 98 : 146; for (let i = 0; i < 8; i++) { const row = at(s, 50 + i * 16), name = row.find(p => p.x === 26), role = row.find(p => p.x === roleX), hp = row.find(p => p.label.startsWith("HP "));
    assert.ok(name.x + name.w < role.x && role.x + role.w < hp.x, "name, role and HP columns do not overlap"); }
  const footer = s.paints.findIndex(p => p.kind === "rect" && p.y === 180 && p.h === 44);
  assert.ok(footer >= 0); assert.ok(s.paints.slice(footer + 1).filter(p => p.kind === "rect" && p.color === "#f0f0f8").every(p => p.y + p.h <= 176));
  const first = JSON.stringify(s.paints); s.draw(); assert.equal(JSON.stringify(s.paints), first, "repeat drawing is deterministic and consumes no RNG or storage");
});
check("keyboard fallback and invalid controller labels retain complete physical Confirm/Back guidance", () => {
  const s = session(256); openTarget(s); s.draw(); assertBounds(s); assert.equal(at(s, 212, 12)[0].label, "Z/SPACE: CAST  X/ESC: BACK");
  s.labels("TOO LONG LABEL", "<BAD>"); s.draw(); assertBounds(s); assert.equal(at(s, 212, 12)[0].label, "Z/SPACE: CAST  X/ESC: BACK");
});
check("legacy target fixtures without a pending spell retain the guarded old view", () => {
  const s = session(); s.api.openMenu(); Object.assign(s.api.menu(), { sub: "magic-target", who: 1, target: 0, ii: 0 });
  s.draw(); assert.ok(s.paints.some(p => p.kind === "window" && p.x === 20 && p.y === 60));
});
check("controlled old popup dispatch and uncapped forecast variants fail the behavioral display invariants", () => {
  const dispatch = source.replace('  if (sub === "magic-target" && (D.realm_key || "prism") === "prism" && menu.spell) return drawFieldSpellTarget();', ""); assert.notEqual(dispatch, source);
  assert.throws(() => { const s = earned(session(320, "prism", dispatch)); openTarget(s); assertPicker(s); }, assert.AssertionError);
  const forecast = source.replace("const after = Math.min(target.max, target.hp + Math.round(spell.power * 1.5 + caster.st.spr * 3));", "const after = target.hp + Math.round(spell.power * 1.5 + caster.st.spr * 3);"); assert.notEqual(forecast, source);
  assert.throws(() => { const s = session(320, "prism", forecast); openTarget(s); const t = s.api.roster()[0]; t.hp = t.max - 2; assert.equal(preview(s).label, "IF CAST: HP " + t.hp + ">" + t.max + " +2"); }, assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("field spell target: " + checks + " focused groups passed; fake render/storage/label peers, no runtime/device acceptance");
