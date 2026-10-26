// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/field_spellbook_test.js
// Prepared as a separate unrun fixture artifact; root adopted/reviewed before execution.
// Actual source15 renderer/handlers, canonical factory/recruit/shop spell teaching and save reader.
// Fake paint/storage/controller-label peers; no browser/devices/assets/native runtime or full IIFE.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const demo = path.resolve(process.argv[2] || __dirname), Save = require(path.join(demo, "journey-save.js"));
const html = fs.readFileSync(path.join(demo, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = n => JSON.parse(fs.readFileSync(path.join(demo, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, interiors = data("interiors").interiors, menus = data("menus").layouts, spells = data("spells").spells, bosses = data("prism-bosses").bosses;
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [line("const CHARS ="), line("const tw ="), line("const hit ="), line("function clearActionButtons()"), line("function cursor("),
  between("function gauge(", "/* ---------- party ---------- */"), between("const START_LEVEL =", "/* ---------- maps"),
  between("const magicShopCaster =", "function shopTick("), between("let menu = null;", "function drawEquip("),
  between("const STATUS =", "/* ---------- bestiary:"), between("function spellHint(", "function drawBattle("),
  between("function titlePrompt(", "function drawTitle("), between("function saveGame()", "function eraseSavedJourney()"),
  "function cleanup(now){\n" + cleanup + "\n}",
  "this.api={start:()=>{party=buildParty();},openMenu,menuTick,drawMenu,drawFieldMagicBook,fieldSpells,spellHint,recruit,buy,saveGame,cleanup,roster," +
  "party:()=>party,reserve:()=>reserve,menu:()=>menu,chars:CHARS,setGold:n=>{gold=n;}," +
  "shortenFront:n=>{reserve=party.slice(n).concat(reserve);party=party.slice(0,n);}," +
  "resources:()=>({party,reserve,bag,gold,state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},opened:Array.from(opened),map,P,D,shop})," +
  "view:()=>({mode,menu,pressed,pressedAt,now})};"
].join("\n");
let groups = 0;
function check(label, fn) { try { fn(); groups++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], sounds = [], records = new Map(), storage = { reads: 0, writes: 0 }, gear = {}, pressed = {}, pressedAt = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors[r])) for (const it of shop.stock || []) if (it.effect || it.attack != null || it.defence != null) gear[it.name] = clone(it);
  const known = new Set(parties[realm].members.flatMap(m => m.spells)), math = Object.create(Math);
  math.random = () => { throw new Error("spellbook browsing/rendering cannot consume gameplay RNG"); };
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, menus: clone(menus[realm]), rects: { sprites: {} },
      // Match the current builder's known-or-tier<=2 catalog, not all authored future tiers.
      spells: clone(spells.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2))), ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, Math: math, pressed, pressedAt, now: 0, cursorNow: 0, PAD: null, B: null, fade: 0, mode: "field", map: { kind: "town", retained: true }, P: { x: 7, y: 9, dir: "left" },
    state: { beaten: new Set(), ways: new Set(), seen: {}, fish: {}, quests: {}, day: 1, minute: 600, air: null, returnTo: null, steps: 0, sinceBattle: 0 }, opened: new Set(["retained/chest"]),
    shop: { kind: "magic", msg: "" }, SAVE_KEY: realm + ".save.v1", clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)),
    sfx: x => sounds.push(x), drawField: () => paints.push({ kind: "field" }),
    // Actual cursor() supplies the original8px sprite dimensions and1px blink offset; art itself is a peer.
    spr(sheet, name, x, y, sx, sw, sh, scale = 1) { if (name === "ui:Cursor") paints.push({ kind: "cursor", x, y, w: sw * scale, h: sh * scale }); },
    performance: { now: () => c.cursorNow }, shardCount: () => 0, clockText: () => "D1 10:00", isNight: () => false,
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }),
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); } },
    localStorage: { getItem(k) { storage.reads++; return records.get(k) ?? null; }, setItem(k, v) { storage.writes++; records.set(k, v); }, removeItem() { throw new Error("spellbook cannot erase records"); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify(c.api.resources());
  return { c, api: c.api, paints, sounds, records, storage, resources,
    tick(...keys) { c.now += 16; keys.forEach(k => { pressed[k] = true; pressedAt[k] = c.now; }); c.api.menuTick(); c.api.cleanup(c.now); },
    draw() { paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), saved = JSON.stringify([...records]), counts = JSON.stringify(storage), audio = sounds.length; c.api.drawMenu();
      assert.equal(resources(), before); assert.equal(JSON.stringify(c.api.view()), view, "painting cannot change cursor, stage, feedback, input or time"); assert.equal(JSON.stringify([...records]), saved); assert.equal(JSON.stringify(storage), counts); assert.equal(sounds.length, audio); return paints; },
    validSave() { assert.equal(c.api.saveGame(), true); const r = Save.read(records.get(c.SAVE_KEY), realm, c.D.party.members); assert.equal(r.ok, true, r.reason); return r.value; },
    labels(confirm = "ABCDEFGH", cancel = "IJKLMNOP") { c.PAD = { devices: () => [{ index: 0 }], label: action => action === "confirm" ? confirm : cancel }; }
  };
}
function earned(s) { for (const dungeon of ["Cinder Forge", "Windcut Aerie", "Sunwell Sanctum", "Gearwright's Folly"]) { s.api.recruit(dungeon); const b = bosses.find(b => b.dungeon === dungeon); assert.ok(b); s.c.state.beaten.add(b.name); } assert.equal(s.api.roster().length, 8); return s; }
function learned(s) { s.api.setGold(100000); for (const it of interiors.prism.Magic.stock) s.api.buy(clone(it)); return s; }
function chooser(s, member = s.api.roster().find(m => m.job === "Lightmender") || s.api.roster().find(m => m.spells.length)) {
  s.api.openMenu(); s.tick("down"); s.tick("a"); assert.equal(s.api.menu().sub, "magic-who"); return caster(s, member);
}
function caster(s, member) { const index = s.api.roster().indexOf(member); assert.ok(index >= 0); for (let n = 0; s.api.menu().who !== index && n < s.api.roster().length; n++) s.tick("right"); assert.equal(s.api.menu().who, index); return s; }
function book(s, member) { chooser(s, member); s.tick("a"); assert.equal(s.api.menu().sub, "magic"); return s; }
function spell(s, name) { const m = s.api.menu(), list = s.api.fieldSpells(s.api.roster()[m.who]), index = list.findIndex(sp => sp.name === name); assert.ok(index >= 0, name);
  for (let n = 0; m.ii !== index && n < list.length; n++) s.tick("down"); assert.equal(m.ii, index); return list[index]; }
const at = (s, y, x) => s.paints.filter(p => p.kind === "text" && p.y === y && (x === undefined || p.x === x));
function reason(s) { s.draw(); assert.equal(at(s, 190, 12).length, 1); return at(s, 190, 12)[0].label; }
function bounds(s) { for (const p of s.paints.filter(p => ["text", "rect", "window", "cursor"].includes(p.kind))) { assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p)); if (p.kind === "text") assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), p.label); } }
function assertBook(s) {
  s.draw(); const m = s.api.menu(), who = m.sub === "magic-who", r = s.api.roster(), member = r[m.who], list = Array.from(s.api.fieldSpells(member)), half = Math.floor(s.c.W / 2), selected = who ? 0 : Math.max(0, Math.min(m.ii || 0, list.length - 1)), from = Math.max(0, Math.min(selected - 5, list.length - 6));
  assert.ok(at(s, 10, 12).some(p => p.label === "MAGIC")); assert.ok(at(s, 10).some(p => p.label === "CASTER " + (m.who + 1) + "/" + r.length));
  const cursors = s.paints.filter(p => p.kind === "cursor"); assert.equal(cursors.length, list.length || who ? 1 : 0);
  const blink = Math.floor(s.c.cursorNow / 300) % 2;
  if (who) assert.ok(cursors.some(p => p.x === 4 + blink && p.y === 62 + m.who * 12)); else if (list.length) assert.ok(cursors.some(p => p.x === half + 12 + blink && p.y === 62 + (selected - from) * 15));
  r.forEach((entry, i) => { const y = 62 + i * 12, n = s.api.fieldSpells(entry).length, count = at(s, y).find(p => p.x < half && p.x > half - 40 && p.label === String(n)); assert.ok(count, "actual known count for every companion"); assert.equal(at(s, y, 14)[0].label, s.api.party().includes(entry) ? "F" : "R"); assert.ok(at(s, y, 26).length); assert.ok(y + 8 < 160); });
  const rows = s.paints.filter(p => p.kind === "text" && p.x === half + 24 && p.y >= 62 && p.y <= 137); assert.equal(rows.length, Math.min(6, list.length));
  rows.forEach((row, i) => { const sp = list[from + i], cost = at(s, row.y).find(p => p.x >= half && p.label === sp.mp + " MP"); assert.ok(cost); assert.equal(cost.color, row.color); assert.ok(row.x + row.w < cost.x); assert.ok(sp.name.toUpperCase().startsWith(row.label.replace(/\.\.\.$/, ""))); });
  assert.equal(at(s, 48, half + 12)[0].label, "SPELLS " + (list.length ? selected + 1 : 0) + "/" + list.length);
  if (list.length) { assert.equal(at(s, 166, 12)[0].label, list[selected].name.toUpperCase()); assert.equal(at(s, 178, 12)[0].label, s.api.spellHint(list[selected])); }
  else assert.ok(at(s, 62, half + 12).some(p => p.label === "NO KNOWN SPELLS."));
  assert.ok(!s.paints.some(p => p.kind === "window" && p.x === 20 && p.y === 60), "generic spell popup no longer obscures casters");
}
check("all eight earned companions have actual known counts/roles and caster preview without spending", () => {
  const s = learned(earned(session())); chooser(s); s.validSave();
  for (const member of Array.from(s.api.roster())) { caster(s, member); assertBook(s); assert.equal(at(s, 34, 12)[0].label, member.job.toUpperCase() + " / " + (s.api.party().includes(member) ? "FRONT" : "RESERVE")); }
});
check("reader-valid smaller fronts retain true reserve membership and living reserve casting access", () => {
  for (const front of [1, 2, 3]) { const s = earned(session()); s.api.shortenFront(front); const saved = s.validSave(); assert.equal(saved.party.length, front); const healer = s.api.roster().find(m => m.job === "Lightmender"); chooser(s, healer); assertBook(s);
    assert.equal(at(s, 34, 12)[0].label.endsWith("RESERVE"), front === 1); s.tick("a"); assert.equal(s.api.menu().sub, "magic"); }
});
check("who refusal checks down before no-known; living noncasters stay visible and battle-only casters still open", () => {
  const s = earned(session()), corin = s.api.roster()[0]; chooser(s, corin); assert.equal(reason(s), "NO SPELLS. CHOOSE ANOTHER COMPANION."); let before = s.resources(); s.tick("a"); assert.equal(s.api.menu().sub, "magic-who"); assert.equal(s.resources(), before);
  corin.hp = 0; assert.equal(reason(s), "DOWN. REVIVE THIS COMPANION FIRST."); before = s.resources(); s.tick("a"); assert.equal(s.api.menu().sub, "magic-who"); assert.match(s.api.menu().msg, /IS DOWN\. REVIVE FIRST/); assert.equal(s.resources(), before);
  const mage = s.api.roster().find(m => m.job === "Runecaster"); mage.mp = 0; caster(s, mage); assert.equal(reason(s), "OPEN THIS COMPANION'S SPELLBOOK."); s.tick("a"); assert.equal(s.api.menu().sub, "magic");
});
check("battle-only refusal precedes MP while a field spell reports exact missing MP and row colors", () => {
  const s = learned(session()), healer = s.api.roster()[1]; book(s, healer); healer.mp = 0; spell(s, "Ward"); assert.equal(reason(s), "BATTLE ONLY. USE MAGIC IN BATTLE."); const blockedColor = at(s, 190, 12)[0].color; let before = s.resources(); s.tick("a"); assert.match(s.api.menu().msg, /WARD IS FOR BATTLE/); assert.equal(s.resources(), before);
  spell(s, "Mend"); assert.equal(reason(s), "NEED 5 MORE MP."); assert.ok(at(s, 62).some(p => p.x > 160 && p.label === "5 MP" && p.color === "#6c6c8c")); before = s.resources(); s.tick("a"); assert.equal(s.api.menu().msg, "NOT ENOUGH MP."); assert.equal(s.resources(), before);
  healer.mp = 5; assert.equal(reason(s), "CHOOSE A LIVING ALLY TO HEAL."); assert.notEqual(at(s, 190, 12)[0].color, blockedColor); assert.ok(at(s, 62).some(p => p.x > 160 && p.label === "5 MP" && p.color === "#ffffff"));
});
check("actual shop-learned Runecaster book scrolls exact known order with complete selected hint/cost", () => {
  const s = learned(earned(session())), mage = s.api.roster().find(m => m.job === "Runecaster"); book(s, mage); const list = Array.from(s.api.fieldSpells(mage)); assert.ok(list.length > 6);
  for (const sp of list) { spell(s, sp.name); assertBook(s); } s.tick("down"); assert.equal(s.api.menu().ii, 0); s.tick("up"); assert.equal(s.api.menu().ii, list.length - 1);
});
check("unresolved legacy spell strings and unshipped tier-three records never leak into known rows/counts", () => {
  const s = session(), healer = s.api.roster()[1]; assert.ok(!s.c.D.spells.some(sp => sp.name === "Renewal")); healer.spells.push("Renewal", "UNLISTED LEGACY SPELL"); s.validSave(); chooser(s, healer); assertBook(s); assert.equal(s.api.fieldSpells(healer).length, 2);
  assert.ok(!s.paints.some(p => p.kind === "text" && /RENEWAL|UNLISTED/.test(p.label))); s.tick("a"); assertBook(s);
});
check("Mend chooses the existing target view, Back returns to its book, and final Confirm still performs real healing", () => {
  const s = earned(session()), healer = s.api.roster()[1], target = s.api.roster()[0]; target.hp = 1; book(s, healer); spell(s, "Mend"); const before = s.resources(), ii = s.api.menu().ii; s.tick("a"); assert.equal(s.api.menu().sub, "magic-target"); assert.equal(s.resources(), before);
  s.tick("b", "a"); assert.equal(s.api.menu().sub, "magic"); assert.equal(s.api.menu().ii, ii); assert.equal(s.resources(), before); s.tick(); assert.equal(s.api.menu().sub, "magic");
  s.tick("a"); s.draw(); const expected = at(s, 184, 12)[0].label.match(/^IF CAST: HP 1>(\d+) \+(\d+)$/); assert.ok(expected); const mp = healer.mp; s.tick("a"); assert.equal(target.hp, Number(expected[1])); assert.equal(healer.mp, mp - 5); assert.equal(s.storage.writes, 0);
});
check("Back retains book cursor but who previews spell zero without mutating it; fresh A opens from zero", () => {
  const s = learned(session()), mage = s.api.roster()[2]; book(s, mage); const list = s.api.fieldSpells(mage); spell(s, list[list.length - 1].name); const kept = s.api.menu().ii; s.tick("b"); assert.equal(s.api.menu().sub, "magic-who"); assert.equal(s.api.menu().ii, kept); assertBook(s); assert.equal(s.api.menu().ii, kept); assert.equal(at(s, 166, 12)[0].label, list[0].name.toUpperCase());
  s.tick("a"); assert.equal(s.api.menu().ii, 0); assert.equal(s.api.menu().sub, "magic"); s.tick("b"); s.tick("b", "a"); assert.equal(s.api.menu().sub, null); const before = s.resources(); s.tick(); assert.equal(s.api.menu().sub, null); assert.equal(s.resources(), before);
});
check("book Left/Right stays inactive and a stale downed caster gains no invented early casting guard", () => {
  const s = session(), healer = s.api.roster()[1]; book(s, healer); const who = s.api.menu().who; s.tick("left", "right"); assert.equal(s.api.menu().who, who); assert.equal(s.api.menu().sub, "magic"); healer.hp = 0;
  assert.equal(reason(s), "CHOOSE A LIVING ALLY TO HEAL."); assert.ok(at(s, 22, 12)[0].label.endsWith(" / DOWN")); const before = s.resources(); s.tick("a"); assert.equal(s.api.menu().sub, "magic-target"); assert.equal(s.resources(), before); s.tick("a"); assert.match(s.api.menu().msg, /IS DOWN\. REVIVE FIRST/); assert.equal(s.resources(), before);
});
for (const width of [320, 256]) check("eight caster rows, six spell rows, long names/pools and mapped controls fit and stay pure at " + width, () => {
  const s = learned(earned(session(width))); for (const member of s.api.roster()) { member.name = "ß".repeat(64); member.mp = member.mmax = Number.MAX_SAFE_INTEGER; }
  const healer = s.api.roster().find(m => m.job === "Lightmender"); healer.hp = 0; chooser(s, healer); s.validSave(); s.labels(); s.api.menu().msg = "STALE FEEDBACK MUST STAY STORED"; assertBook(s); bounds(s);
  for (const blinkTime of [0, 300]) { s.c.cursorNow = blinkTime; assertBook(s); bounds(s); const arrow = s.paints.find(p => p.kind === "cursor"); assert.equal(arrow.w, 8); assert.ok(arrow.x + arrow.w <= 13, "WHO arrow leaves theF/R marker at14 visible in both frames"); }
  assert.ok(at(s, 22, 12)[0].label.endsWith(" / DOWN")); assert.ok(at(s, 22, 12)[0].label.startsWith("SS")); assert.ok(at(s, 34).some(p => p.label === "MP 9999+/9999+")); assert.ok(!s.paints.some(p => p.kind === "text" && p.label.includes("STALE FEEDBACK")));
  assert.equal(at(s, 202, 12)[0].label, "LEFT/RIGHT: WHO ABCDEFGH: BOOK"); assert.equal(at(s, 214, 12)[0].label, "IJKLMNOP: BACK");
  const mage = s.api.roster().find(m => m.job === "Runecaster"); caster(s, mage); s.tick("a"); spell(s, s.api.fieldSpells(mage).slice(-1)[0].name); assertBook(s); bounds(s);
  for (const blinkTime of [0, 300]) { s.c.cursorNow = blinkTime; assertBook(s); bounds(s); const arrow = s.paints.find(p => p.kind === "cursor"); assert.ok(arrow.x + arrow.w < Math.floor(width / 2) + 24, "book arrow clears the spell name in both frames"); }
  assert.equal(at(s, 202, 12)[0].label, "UP/DOWN: SPELL ABCDEFGH: CHOOSE"); assert.equal(at(s, 214, 12)[0].label, "IJKLMNOP: CASTER");
  const before = JSON.stringify(s.paints); s.draw(); assert.equal(JSON.stringify(s.paints), before);
});
check("physical fallback controls fit both stages without guessing a controller label", () => {
  const s = session(256); chooser(s); s.draw(); bounds(s); assert.equal(at(s, 202, 12)[0].label, "LEFT/RIGHT: WHO Z/SPACE: BOOK"); assert.equal(at(s, 214, 12)[0].label, "X/ESC: BACK");
  s.labels("NOT A LABEL", "<BAD>"); s.tick("a"); s.draw(); bounds(s); assert.equal(at(s, 202, 12)[0].label, "UP/DOWN: SPELL Z/SPACE: CHOOSE"); assert.equal(at(s, 214, 12)[0].label, "X/ESC: CASTER");
});
check("Portal keeps its original caster rows and spell popup/controls", () => {
  const s = session(256, "portal"), member = s.api.roster().find(m => m.spells.length); chooser(s, member); s.draw(); assert.ok(!at(s, 10, 12).some(p => p.label === "MAGIC")); assert.ok(s.paints.some(p => p.kind === "window"));
  s.tick("a"); assert.equal(s.api.menu().sub, "magic"); s.draw(); assert.ok(s.paints.some(p => p.kind === "window" && p.x === 20 && p.y === 60 && p.w === 220 && p.h === 112)); s.tick("b", "a"); assert.equal(s.api.menu().sub, "magic-who");
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("field spellbook: " + groups + " focused groups passed; fake painters/storage/labels, no runtime/device acceptance");
