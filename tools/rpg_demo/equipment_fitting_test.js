// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/equipment_fitting_test.js
// Actual member/recruit/menu/candidate/equipment/cursor painters with canonical merged shop gear.
// Six-row scrolling uses an explicitly reader-valid legacy all-weapon-kinds record, not a training feature.
// Text and cursor atlas are finite paint peers. No browser, device, full IIFE, native storage or runtime acceptance.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Save = require("./journey-save.js");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, interiors = data("interiors").interiors, gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(interiors[realm])) for (const it of shop.stock || []) if (it.effect || it.attack != null || it.defence != null) gear[it.name] = clone(it);
const slots = ["weapon", "armor", "helm", "shield"];
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="), line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"), line("function cursor("),
  between("function spr(", "function win("), between("function makeMember(", "const atkOf ="), between("const atkOf =", "/* ---------- maps"),
  between("let menu = null;", "function useItem("), between("function drawEquipmentFitting()", "/* ---------- statuses"), between("function titlePrompt(", "function drawTitle("),
  "function cleanup(now){\n" + cleanup + "\n}",
  "this.api={makeMember,recruit,roster,openMenu,menuTick,drawEquip,drawEquipmentFitting,equipCandidates,canEquip,slotOf,atkOf,defOf,atkWith,defWith,cleanup,chars:CHARS,menu:()=>menu," +
  "resources:()=>({party,reserve,bag,gold,GEAR,D,state,map,opened:Array.from(opened)}),view:()=>({mode,menu,pressed,pressedAt,now,fade})};"
].join("\n");
let groups = 0;
function check(label, fn) { try { fn(); groups++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], sounds = [], pressed = {}, pressedAt = {}, calls = { rng: 0, storage: 0 };
  const math = Object.create(Math); math.random = () => { calls.rng++; throw new Error("equipment fitting cannot consume gameplay RNG"); };
  const c = { W: width, H: 224, D: { realm_key: realm, party: clone(parties[realm]), gear: clone(gear), dungeons: [], rects: { sprites: { "ui:Cursor": [0, 0, 16, 8] } }, ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    GEAR: clone(gear), party: [], reserve: [], bag: clone(parties[realm].start_items), gold: 237, map: { kind: "town", retained: true }, state: { day: 3, minute: 620 }, opened: new Set(["retained/chest"]),
    mode: "field", fade: 0, now: 0, cursorNow: 0, pressed, pressedAt, PAD: null, Math: math, IM: { sprites: "cursor-atlas-peer" }, performance: { now: () => c.cursorNow },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: value => String(value).length * 6, sfx: value => sounds.push(value),
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    win(x, y, w, h) { paints.push({ kind: "window", x, y, w, h }); },
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); }, drawImage(image, sx, sy, sw, sh, x, y, w, h) { assert.equal(image, "cursor-atlas-peer"); assert.ok(sx === 0 || sx === 8); assert.equal(sy, 0); paints.push({ kind: "cursor", x, y, w, h, frame: sx / 8 }); } },
    localStorage: Object.fromEntries(["getItem", "setItem", "removeItem"].map(k => [k, () => { calls.storage++; throw new Error("equipment fitting cannot access native storage"); }])),
    saveGame() { calls.storage++; throw new Error("equipment fitting cannot save"); }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, realm === "portal" ? 1 : 15));
  const resources = () => JSON.stringify(c.api.resources());
  return { c, api: c.api, paints, sounds, calls, resources,
    tick(...keys) { c.now += 16; keys.forEach(k => { pressed[k] = true; pressedAt[k] = c.now; }); c.api.menuTick(); c.api.cleanup(c.now); },
    draw() { paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), effects = JSON.stringify({ calls, sounds }); c.api.drawEquip(); assert.equal(resources(), before, "painting changed members/inventory/catalog/progress"); assert.equal(JSON.stringify(c.api.view()), view, "painting changed a choice/input"); assert.equal(JSON.stringify({ calls, sounds }), effects); return paints; },
    labels(confirm = "ABCDEFGH", cancel = "IJKLMNOP") { c.PAD = { devices: () => [{ index: 0 }], label: a => ({ confirm, cancel })[a] }; }
  };
}
function earned(s) { for (const name of ["Cinder Forge", "Windcut Aerie", "Sunwell Sanctum", "Gearwright's Folly"]) s.api.recruit(name); assert.equal(s.api.roster().length, 8); return s; }
function stock(s) { for (const name of Object.keys(gear)) if (gear[name].attack != null || gear[name].defence != null) s.c.bag[name] = 2; return s; }
function open(s, who = 0, slot = "weapon") { s.api.openMenu(); s.tick("down"); s.tick("down"); s.tick("a"); assert.equal(s.api.menu().sub, "equip"); for (let i = 0; i < who; i++) s.tick("right"); for (let i = 0; i < slots.indexOf(slot); i++) s.tick("down"); assert.equal(s.api.menu().who, who); assert.equal(s.api.menu().ii, slots.indexOf(slot)); return s; }
const at = (s, y, x) => s.paints.filter(p => p.kind === "text" && p.y === y && (x === undefined || p.x === x));
const row = (s, y) => at(s, y, Math.floor(s.c.W / 2) + 20)[0];
function edges(s) { for (const k of ["a", "b", "start", "left", "right", "up", "down"]) assert.equal(!!s.c.pressed[k], false, k); }
function bounds(s) { for (const p of s.paints) { assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p)); if (p.kind === "text") assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), p.label); } }
function previewAfter(s, label) { const r = row(s, label === "ATK" ? 70 : 88); assert.ok(r && r.label.startsWith(label + " ")); return Number(r.label.split(">")[1]); }
check("actual recruits expose all eight members and true FRONT/RESERVE, even with fewer active companions", () => {
  const s = earned(session());
  for (let i = 0; i < 8; i++) { open(s, i); s.draw(); const m = s.api.roster()[i]; assert.equal(at(s, 6).find(p => p.x > 12).label, (i + 1) + "/8"); assert.equal(at(s, 18, 12)[0].label, m.name.toUpperCase()); assert.ok(at(s, 18).some(p => p.label === (s.c.party.includes(m) ? "FRONT" : "RESERVE"))); }
  const moved = s.c.party.pop(); s.c.reserve.unshift(moved); open(s, 3); s.draw(); assert.equal(s.api.roster()[3], moved); assert.ok(at(s, 18).some(p => p.label === "RESERVE")); assert.equal(s.c.party.length, 3);
});
check("canonical candidate insertion order and eligibility retain sword/dagger/heavy-armour rules", () => {
  const s = earned(session()); s.c.bag = { "Steel Saber": 99, "Copper Blade": 1, "Oak Staff": 1, "Ring Mail": 1, "Iron Helm": 1, "Kite Shield": 1 };
  const corin = s.c.party[0], rook = s.c.party.find(m => m.job === "Shadowstep"); assert.deepEqual(Array.from(s.api.equipCandidates(corin, "weapon")), ["Steel Saber", "Copper Blade", null]); assert.equal(s.api.canEquip(rook, "Steel Saber"), true); assert.equal(s.api.canEquip(s.c.party[1], "Steel Saber"), false);
  for (const m of s.api.roster()) { assert.equal(s.api.canEquip(m, "Padded Vest"), true); assert.equal(s.api.canEquip(m, "Iron Helm"), m.armor === "heavy"); assert.equal(s.api.canEquip(m, "Kite Shield"), m.armor === "heavy"); }
  assert.equal(s.api.canEquip(s.api.roster().find(m => m.job === "Gearwright"), "Iron Axe"), true); assert.equal(s.api.canEquip(s.api.roster().find(m => m.job === "Starlancer"), "Silver Lance"), true);
  open(s); s.draw(); assert.equal(at(s, 178, 12)[0].label, "2 FITTING TYPES / TAKE OFF AVAILABLE", "type count is distinct from99copies");
});
check("one actual weapon Confirm matches the displayed total and consumes one copy while returning the old weapon", () => {
  const s = session(), m = s.c.party[0]; s.c.bag = { "Steel Saber": 2 }; const old = m.equip.weapon, oldCount = s.c.bag[old] || 0, attack = s.api.atkOf(m), defence = s.api.defOf(m); open(s); s.tick("a"); s.draw();
  assert.equal(s.api.menu().sub, "equip-pick"); assert.equal(at(s, 166, 12)[0].label, "STEEL SABER"); assert.equal(row(s, 124).label, old.toUpperCase()); assert.equal(row(s, 142).label, "IN BAG 2"); const afterAttack = previewAfter(s, "ATK"), afterDefence = previewAfter(s, "DEF"); assert.ok(afterAttack > attack); assert.equal(afterDefence, defence); assert.equal(row(s, 70).color, "#78f8a0");
  s.tick("a"); assert.equal(m.equip.weapon, "Steel Saber"); assert.equal(s.c.bag["Steel Saber"], 1); assert.equal(s.c.bag[old], oldCount + 1); assert.equal(s.api.atkOf(m), afterAttack); assert.equal(s.api.defOf(m), afterDefence); assert.equal(s.api.menu().sub, "equip"); assert.equal(s.api.menu().equipChoice, undefined);
});
check("null TAKE OFF forecasts the exact total and returns one worn shield without spending another item", () => {
  const s = session(), m = s.c.party[0], old = m.equip.shield; assert.ok(old); s.c.bag = {}; const defence = s.api.defOf(m); open(s, 0, "shield"); s.draw(); assert.equal(at(s, 178, 12)[0].label, "0 FITTING TYPES / TAKE OFF AVAILABLE"); s.tick("a"); assert.deepEqual(Array.from(s.api.equipCandidates(m, "shield")), [null]); s.draw();
  assert.equal(at(s, 166, 12)[0].label, "TAKE OFF SHIELD"); assert.equal(at(s, 178, 12)[0].label, "WORN GEAR RETURNS TO THE BAG."); assert.equal(at(s, 212, 12)[0].label, "Z/SPACE: TAKE OFF"); assert.equal(row(s, 142), undefined); const after = previewAfter(s, "DEF"); assert.ok(after < defence); assert.equal(row(s, 88).color, "#f87878"); s.tick("a"); assert.equal(m.equip.shield, null); assert.equal(s.c.bag[old], 1); assert.equal(s.api.defOf(m), after);
});
check("Back beats Confirm in both stages and leaves slot/candidate resources unchanged with fresh edges", () => {
  const s = session(); s.c.bag = { "Steel Saber": 1 }; open(s); s.tick("a"); s.tick("down"); const before = s.resources(); s.draw(); s.tick("b", "a"); assert.equal(s.api.menu().sub, "equip"); assert.equal(s.api.menu().ci, 0); assert.equal(s.api.menu().equipChoice, undefined); assert.equal(s.resources(), before); edges(s); s.tick(); assert.equal(s.api.menu().sub, "equip"); s.tick("b", "a"); assert.equal(s.api.menu().sub, null); assert.equal(s.resources(), before); edges(s);
});
check("stale candidate/worn/member choices still refuse before any transaction", () => {
  for (const change of [s => { delete s.c.bag["Steel Saber"]; }, s => { s.c.party[0].equip.weapon = "Steel Saber"; }, s => { s.api.menu().who = 1; }]) {
    const s = session(); s.c.bag = { "Steel Saber": 1 }; open(s); s.tick("a"); change(s); const before = s.resources(); s.draw(); s.tick("a"); assert.equal(s.resources(), before); assert.equal(s.api.menu().sub, "equip"); assert.match(s.api.menu().msg, /GEAR CHANGED/); edges(s);
  }
});
check("a fresh empty robe-user helm shows EMPTY/no fitting gear and actual Confirm refuses safely", () => {
  const s = session(); s.c.bag = { "Iron Helm": 1 }; open(s, 1, "helm"); const m = s.c.party[1], before = s.resources(); assert.equal(m.equip.helm, null); assert.equal(s.api.equipCandidates(m, "helm").length, 0); s.draw(); assert.equal(row(s, 124).label, "EMPTY"); assert.equal(at(s, 166, 12)[0].label, "EMPTY HELM SLOT"); assert.equal(at(s, 178, 12)[0].label, "NO GEAR IN THE BAG FITS THIS SLOT."); s.tick("a"); assert.equal(s.resources(), before); assert.equal(s.api.menu().sub, "equip"); assert.match(s.api.menu().msg, /NO GEAR FITS/); assert.equal(Object.hasOwn(s.c.bag, "undefined"), false);
});
for (const width of [320, 256]) check("canonical worn/selected gear, columns, panels and actual cursor frames fit both stages at " + width, () => {
  const s = stock(earned(session(width))), split = Math.floor(width / 2) + 8;
  for (let who = 0; who < 8; who++) for (const slot of slots) { open(s, who, slot); const m = s.api.roster()[who];
    for (const blink of [0, 300]) { s.c.cursorNow = blink; s.draw(); bounds(s); const cursor = s.paints.find(p => p.kind === "cursor"); assert.equal(cursor.x, 10 + (blink ? 1 : 0)); assert.ok(cursor.x + cursor.w < 22); assert.equal(row(s, 52).label, "TOTALS"); assert.equal(at(s, 166, 12)[0].label, (m.equip[slot] || "EMPTY " + slot + " SLOT").toUpperCase()); }
    if (!s.api.equipCandidates(m, slot).length) continue; s.tick("a"); const cands = Array.from(s.api.equipCandidates(m, slot)); for (let i = 0; i < cands.length - 1; i++) s.tick("down");
    for (const blink of [0, 300]) { s.c.cursorNow = blink; s.draw(); bounds(s); assert.equal(row(s, 52).label, "PREVIEW"); const cursor = s.paints.find(p => p.kind === "cursor"); assert.equal(cursor.x, 14 + (blink ? 1 : 0)); assert.ok(cursor.x + cursor.w < 26); assert.equal(at(s, 166, 12)[0].label, cands.at(-1) === null ? "TAKE OFF " + slot.toUpperCase() : cands.at(-1).toUpperCase());
      for (const p of s.paints.filter(p => p.kind === "text" && p.y >= 44 && p.y < 160)) assert.ok(p.x < split ? p.x + p.w < split : p.x > split);
      const divider = s.paints.find(p => p.kind === "rect" && p.y === 159 && p.h === 1); assert.ok(divider); for (const p of s.paints.filter(p => p.kind === "text" && p.y < 159)) assert.ok(p.y + p.h <= divider.y);
    }
  }
});
check("reader-valid legacy kinds expose six canonical weapon rows and scroll the seventh TAKE OFF row", () => {
  for (const width of [320, 256]) { const s = session(width), m = s.c.party[0]; m.kinds = ["sword", "staff", "bow", "axe", "lance"]; s.c.bag = Object.fromEntries(Object.keys(gear).filter(name => gear[name].attack != null).map(name => [name, 2]));
    const legacy = { v: 1, realm_key: "prism", party: clone(s.c.party), reserve: [], bag: clone(s.c.bag), gold: 237, opened: [] }; assert.equal(Save.read(JSON.stringify(legacy), "prism", s.c.D.party.members).ok, true); open(s); s.tick("a"); const cands = Array.from(s.api.equipCandidates(m, "weapon")); assert.equal(cands.length, 7); assert.equal(cands.at(-1), null);
    s.draw(); bounds(s); assert.equal(s.paints.filter(p => p.kind === "text" && p.x === 26 && p.y >= 54 && p.y <= 134).length, 6); assert.equal(at(s, 148, 12)[0].label, "1-6/7"); for (let i = 0; i < 6; i++) s.tick("down"); s.draw(); bounds(s); assert.equal(at(s, 148, 12)[0].label, "2-7/7"); assert.equal(at(s, 134, 26)[0].label, "TAKE OFF"); assert.equal(at(s, 166, 12)[0].label, "TAKE OFF WEAPON"); assert.equal(at(s, 212, 12)[0].label, "Z/SPACE: TAKE OFF"); assert.ok(s.paints.some(p => p.kind === "cursor" && p.y === 134)); }
});
check("large accepted aliases/stats/quantities cap only the display and mapped/fallback controls remain separated", () => {
  for (const width of [320, 256]) { const s = session(width), m = s.c.party[0]; m.name = "ß".repeat(64); m.st.str = 10000000; m.st.vit = 10000000; s.c.bag = { "Steel Saber": Number.MAX_SAFE_INTEGER }; s.labels(); open(s); s.tick("a"); const before = s.resources(); s.draw(); bounds(s); assert.ok(at(s, 18, 12)[0].label.startsWith("SS")); assert.equal(row(s, 70).label, "ATK 9999+>9999+"); assert.equal(row(s, 88).label, "DEF 9999+>9999+"); assert.equal(row(s, 142).label, "IN BAG 999+"); assert.match(at(s, 178, 12)[0].label, /IN BAG 999\+/);
    const use = at(s, 212, 12)[0], back = at(s, 212).find(p => p.label === "IJKLMNOP: BACK"); assert.equal(use.label, "ABCDEFGH: EQUIP"); assert.ok(back && use.x + use.w < back.x); assert.equal(s.resources(), before); s.labels("INVALID LABEL", "<BAD>"); s.draw(); bounds(s); assert.equal(at(s, 212, 12)[0].label, "Z/SPACE: EQUIP"); assert.ok(at(s, 212).some(p => p.label === "X/ESC: BACK")); assert.equal(s.calls.rng + s.calls.storage, 0); }
});
check("Portal retains the original renderer and removing Prism dispatch is detected by the new view invariant", () => {
  const p = session(320, "portal"); open(p); p.draw(); assert.equal(p.paints.filter(x => x.kind === "window").length, 4); assert.ok(at(p, 50, 182).some(x => x.label === "ATK")); assert.ok(!p.paints.some(x => x.kind === "text" && x.label === "EQUIPMENT"));
  const dispatch = '  if ((D.realm_key || "prism") === "prism") return drawEquipmentFitting();'; assert.ok(source.includes(dispatch)); const old = session(320, "prism", source.replace(dispatch, "")); open(old); old.draw(); assert.throws(() => assert.ok(at(old, 6, 12).some(x => x.label === "EQUIPMENT")), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline (compile only)" });
console.log("equipment fitting: " + groups + " focused groups passed; canonical transactions and finite legacy/paint peers, no browser/native acceptance");
