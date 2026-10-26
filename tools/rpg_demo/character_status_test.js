// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/character_status_test.js
// Actual factory/recruit/menu/status/victory functions + canonical party/gear. Canvas peers only.
// Victory setup uses a defeated canonical foe with an explicit five-EXP/zero-gold test reward;
// no combat, campaign-earned progression, game boot, assets, browser, storage or native acceptance.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8")), clone = value => JSON.parse(JSON.stringify(value));
const parties = data("party").party, layouts = data("menus").layouts, gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(data("interiors").interiors[realm])) for (const item of shop.stock || [])
  if (item.attack != null || item.defence != null || item.effect) gear[item.name] = clone(item);
const foe = data("prism-bestiary").types.find(f => f.key === "prism_best_gelfin"); assert.ok(foe);
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = prefix => { const found = html.split("\n").find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"),
  between("function gauge(", "/* ---------- party ---------- */"), between("const START_LEVEL =", "/* ---------- maps"),
  between("let menu = null;", "function drawEquip()"), between("const STATUS =", "function inflict("),
  between("function recoverStolenGold()", "function hurtFoe("), between("function endRound()", "function finishBattle()"),
  between("function titlePrompt(", "function drawTitle("),
  "this.api={start:()=>{party=buildParty();},recruitAll:()=>D.party.members.filter(m=>m.joins.startsWith('after ')).forEach(m=>recruit(m.joins.slice(6)))," +
  "makeMember,recruit,roster,party:()=>party,reserve:()=>reserve,setRoster:(front,back)=>{party=front;reserve=back;},gold:()=>gold,bag:()=>bag,menu:()=>menu," +
  "open:()=>{openMenu();menu.idx=MENU_CMDS.indexOf('STATUS');pressed.a=true;menuTick();},select:i=>{menu.who=i;}," +
  "tick:(...keys)=>{keys.forEach(k=>{pressed[k]=true;});menuTick();},drawStatus,drawMenu,endRound,atkOf,defOf,statuses:STATUS,chars:CHARS};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], rectangles = [], sprites = [], windows = [], sounds = [], pressed = {}, calls = { rng: 0, storage: 0 };
  const fixedMath = Object.create(Math); fixedMath.random = () => { calls.rng++; throw new Error("status must not roll RNG"); };
  const rects = Object.fromEntries(parties[realm].members.map(m => ["Party_" + m.job, [0, 0, m.job === "Beastcaller" ? 224 : 112, 112]]));
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear: clone(gear), menus: clone(layouts[realm]), dungeons: [], spells: [], rects: { sprites: rects },
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) }, W: width, H: 224, Math: fixedMath, PAD: null, B: null, pressed,
    state: { beaten: new Set(), ways: new Set(), seen: {}, fish: {}, quests: {}, minute: 480, day: 1 }, opened: new Set(), map: { kind: "world" }, mode: "field",
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: label => String(label).length * 6, drawField() {}, clockText: () => "D1 08:00", isNight: () => false,
    cue() {}, sfx: name => sounds.push(name), fell() {}, SUMMONS: () => [],
    saveGame() { calls.storage++; throw new Error("status cannot save"); }, localStorage: { getItem() { calls.storage++; throw new Error("status cannot read storage"); } },
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ label, x, y, w: label.length * 6, h: 8, color }); },
    spr(sheet, name, x, y, sx, sw, sh, scale) { const r = c.D.rects.sprites[name]; sprites.push({ name, x, y, w: r[2] * scale, h: r[3] * scale }); },
    win: (x, y, w, h) => windows.push({ x, y, w, h }), cursor() {},
    g: { fillStyle: "", fillRect(x, y, w, h) { rectangles.push({ x, y, w, h, color: this.fillStyle }); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start(); if (realm === "prism") c.api.recruitAll(); c.api.open();
  const snapshot = () => JSON.stringify({ D: c.D, roster: c.api.roster(), front: c.api.party().map(m => m.job), gold: c.api.gold(), bag: c.api.bag(), menu: c.api.menu(), pressed,
    map: c.map, mode: c.mode, battle: c.B, state: { ...c.state, beaten: [...c.state.beaten], ways: [...c.state.ways] }, opened: [...c.opened], calls });
  return { c, api: c.api, paints, rectangles, sprites, windows, sounds, pressed, calls,
    draw(index = c.api.menu().who, direct = false) { c.api.select(index); paints.length = rectangles.length = sprites.length = windows.length = 0; const before = snapshot();
      c.api[direct ? "drawStatus" : "drawMenu"](); assert.equal(snapshot(), before, "drawing changed source, resources, progress, inputs, RNG or storage"); return paints; },
    at(x, y) { return paints.find(p => p.x === x && p.y === y); }, labels: () => paints.map(p => p.label)
  };
}
function bounds(s) {
  for (const p of s.paints) { assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, "text outside canvas " + JSON.stringify(p));
    assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), "unsupported status glyph"); }
  for (const r of s.rectangles) assert.ok(r.x >= 0 && r.y >= 0 && r.x + r.w <= s.c.W && r.y + r.h <= 224, "rectangle outside canvas");
  assert.equal(s.sprites.length, 1); const p = s.sprites[0]; assert.ok(p.x === 12 && p.y === 8 && p.w <= 32 && p.h <= 32 && p.x + p.w < 52 && p.y + p.h < 50);
  assert.deepEqual(s.calls, { rng: 0, storage: 0 });
}
function growthLine(s, member) { const job = s.c.D.party.members.find(m => m.job === member.job); return "NEXT: MAX HP +" + job.growth.hp + " / MAX MP +" + job.growth.mp; }
function bar(s, member) {
  const fill = s.rectangles.find(r => r.color === "#9c88df" && r.x === 13 && r.y === 165); assert.ok(fill);
  assert.equal(fill.w, Math.round((s.c.W - 26) * Math.max(0, Math.min(1, member.exp / member.next)))); assert.equal(fill.h, 3);
}
for (const width of [320, 256]) check("canonical eight jobs at " + width + ": actual pools, stats, loadout, membership and growth", () => {
  const s = session(width), roster = s.api.roster(); assert.equal(roster.length, 8);
  roster.forEach((m, index) => { s.draw(index); const half = width / 2, full = s.api.party().includes(m);
    assert.equal(s.at(52, 34).label, "HP " + m.hp + "/" + m.max); assert.equal(s.at(half + 24, 34).label, "MP " + m.mp + "/" + m.mmax);
    assert.equal(s.at(52, 22).label, "LV " + m.lv + " / " + (full ? "FRONT" : "RESERVE"));
    assert.ok(s.labels().includes(growthLine(s, m))); assert.ok(s.labels().includes(full ? "FRONT: FULL VICTORY EXP." : "RESERVE: HALF EXP, ROUNDED DOWN."));
    const values = [m.st.str, m.st.agi, m.st.vit, m.st.int, m.st.spr,
      m.st.str * 2 + ((gear[m.equip.weapon] || {}).attack || 0), Math.floor(m.st.vit / 2) + ["armor", "helm", "shield"].reduce((n, k) => n + ((gear[m.equip[k]] || {}).defence || 0), 0)];
    ["STR", "AGI", "VIT", "INT", "SPR", "ATK", "DEF"].forEach((key, i) => { assert.equal(s.at(12, 58 + i * 12).label, key); assert.ok(s.paints.some(p => p.y === 58 + i * 12 && p.x < half && p.label === String(values[i]))); });
    ["weapon", "armor", "helm", "shield"].forEach((slot, i) => { assert.equal(s.at(half + 12, 58 + i * 20).label, slot.toUpperCase()); const shown = s.at(half + 12, 68 + i * 20).label;
      assert.ok((m.equip[slot] || "-").toUpperCase().startsWith(shown.replace(/\.\.\.$/, ""))); });
    assert.equal(s.at(12, 152).label, "EXP 0/400"); assert.ok(s.labels().includes("NEED 400 EXP")); assert.equal(s.at(12, 200).label, "STATUS: CLEAR"); bar(s, m); bounds(s);
  });
});
check("one-to-three member front lines use membership rather than fixed four-slot position", () => {
  const s = session(256), members = Array.from(s.api.roster());
  for (const count of [1, 2, 3]) { s.api.setRoster(members.slice(0, count), members.slice(count)); s.draw(count - 1); assert.ok(s.labels().includes("FRONT: FULL VICTORY EXP."));
    const m = members[count]; s.draw(count); assert.ok(s.labels().includes("RESERVE: HALF EXP, ROUNDED DOWN.")); m.hp = 0; s.draw(count); assert.equal(s.at(12, 176).label, "DOWN: NO VICTORY EXP.");
    m.hp = 1; m.status = { sleep: 3, bind: 2 }; s.draw(count); assert.equal(s.at(12, 176).label, "RESERVE: HALF EXP, ROUNDED DOWN."); }
});
check("EXP needed/bar use raw progress and never level up while looking", () => {
  const s = session(256), m = s.api.roster()[0], level = m.lv;
  for (const exp of [27, 399, 400]) { m.exp = exp; m.next = 400; s.draw(0); assert.ok(s.labels().includes("NEED " + Math.max(0, 400 - exp) + " EXP")); bar(s, m); assert.equal(m.lv, level); }
});
function victory(s) {
  s.c.B = { foes: [{ ...clone(foe), hp: 0, exp: 5, gold: 0 }], phase: "act", round: 1, acts: [], queue: [] }; // Explicit small reward fixture, not an ordinary-encounter reward claim.
  s.api.endRound(); assert.equal(s.c.B.result, "win"); assert.equal(s.c.B.phase, "end");
}
check("job-based growth display matches one actual level victory for all eight renamed companions", () => {
  const s = session(), members = s.api.roster(), before = [];
  members.forEach((m, i) => { m.name = "Alias" + i; m.hp = m.max - 7; m.mp = Math.max(0, m.mmax - 3); m.exp = m.next - (s.api.party().includes(m) ? 5 : 2); before.push(clone(m));
    s.draw(i); assert.equal(s.at(12, 188).label, growthLine(s, m)); assert.ok(!s.labels().some(label => /FULL HEAL|ALL RESTED|MAIN STAT|STAT GROWTH/.test(label))); });
  victory(s); members.forEach((m, i) => { const original = before[i], growth = s.c.D.party.members.find(record => record.job === m.job).growth;
    assert.equal(m.name, "Alias" + i); assert.equal(m.lv, original.lv + 1); assert.equal(m.exp, 0); assert.equal(m.next, Math.round(original.next * 1.18));
    assert.equal(m.max - original.max, growth.hp); assert.equal(m.hp - original.hp, growth.hp); assert.equal(m.mmax - original.mmax, growth.mp); assert.equal(m.mp - original.mp, growth.mp);
    assert.ok(m.hp < m.max, "level gain does not promise a full heal"); s.draw(i); assert.equal(s.at(12, 188).label, growthLine(s, m)); });
  assert.equal(s.sounds.filter(name => name === "LEVEL").length, 8);
});
check("displayed victory eligibility matches actual downed exclusion, held eligibility and rounded reserve half", () => {
  const s = session(256), members = s.api.roster(); members[0].hp = 0; members[4].hp = 0; members[1].status = { sleep: 3 }; members[5].status = { bind: 2 };
  const expected = members.map((m, i) => { m.exp = 0; s.draw(i); const gain = m.hp <= 0 ? 0 : s.api.party().includes(m) ? 5 : 2;
    assert.equal(s.at(12, 176).label, m.hp <= 0 ? "DOWN: NO VICTORY EXP." : s.api.party().includes(m) ? "FRONT: FULL VICTORY EXP." : "RESERVE: HALF EXP, ROUNDED DOWN."); return gain; });
  victory(s); members.forEach((m, i) => assert.equal(m.exp, expected[i])); assert.equal(members[1].status.sleep, 3); assert.equal(members[5].status.bind, 2);
});
check("only known status words are shown with a truthful bounded remaining count", () => {
  for (const width of [320, 256]) { const s = session(width), m = s.api.roster()[0], entries = Object.entries(s.api.statuses); m.status = { unlisted: 1, ...Object.fromEntries(entries.map(([key]) => [key, 2])) }; s.draw(0);
    const text = s.at(12, 200).label, count = text.match(/ \+(\d+)$/); assert.ok(count, "many simultaneous statuses need a remaining count");
    const words = text.slice("STATUS: ".length).replace(/ \+\d+$/, "").split(", "); assert.ok(words.every(word => entries.some(([, record]) => record.word === word)));
    assert.equal(words.length + Number(count[1]), entries.length); assert.equal(text.includes("UNLISTED"), false); bounds(s); }
});
for (const width of [320, 256]) check("large accepted display values, aliases, portraits and mapped footer fit at " + width, () => {
  const s = session(width), index = s.api.roster().findIndex(m => m.job === "Beastcaller"), m = s.api.roster()[index];
  m.name = "ß".repeat(64); m.lv = m.hp = m.max = m.mp = m.mmax = Number.MAX_SAFE_INTEGER; m.exp = Number.MAX_SAFE_INTEGER - 1; m.next = Number.MAX_SAFE_INTEGER;
  Object.keys(m.st).forEach(key => { m.st[key] = Number.MAX_SAFE_INTEGER; }); s.c.PAD = { devices: () => [{ index: 4 }], label(action, device) { assert.equal(action, "cancel"); assert.equal(device, 4); return "ABCDEFGH"; } };
  s.draw(index); assert.ok(s.at(52, 10).label.includes("... - BEASTCALLER")); assert.equal(s.at(52, 34).label, "HP 9999+/9999+"); assert.equal(s.at(width / 2 + 24, 34).label, "MP 9999+/9999+");
  assert.equal(s.at(12, 152).label, "EXP 999999+/999999+"); assert.ok(s.labels().includes("NEED 1 EXP")); assert.equal(s.at(12, 212).label, "LEFT/RIGHT: WHO ABCDEFGH: BACK");
  assert.equal(m.name, "ß".repeat(64)); assert.equal(m.hp, Number.MAX_SAFE_INTEGER); bar(s, m); bounds(s);
});
check("existing Left/Right wrap and Confirm/Back close consume both close edges", () => {
  const s = session(256); s.api.tick("left"); assert.equal(s.api.menu().who, 7); s.draw(); assert.ok(s.labels().includes("LV 15 / RESERVE")); s.api.tick("right"); assert.equal(s.api.menu().who, 0);
  for (const keys of [["a"], ["b"], ["a", "b"]]) { s.api.open(); s.api.tick(...keys); assert.equal(s.api.menu().sub, null); assert.equal(s.api.menu().idx, 3); assert.equal(s.pressed.a, false); assert.equal(s.pressed.b, false);
    s.api.tick(); assert.equal(s.api.menu().sub, null); }
});
check("Portal stays on the original status painter and factory metadata", () => {
  const s = session(320, "portal"), m = s.api.roster()[0]; s.draw(0); assert.equal(s.windows.length, 3); assert.equal(s.at(56, 10).label, m.name.toUpperCase());
  assert.equal(s.at(120, 36).label, "EXP " + m.exp + "/" + m.next); assert.equal(s.paints.some(p => /^NEXT:|NEED |FRONT:|RESERVE:/.test(p.label)), false); assert.equal(s.sprites[0].h, 44);
});
check("controlled original Prism renderer cannot satisfy the progress-sheet contract", () => {
  const old = source.replace('if ((D.realm_key || "prism") === "prism") return drawCharacterStatus();', 'if (false) return drawCharacterStatus();'); assert.notEqual(old, source);
  const s = session(256, "prism", old); s.draw(0); assert.equal(s.paints.some(p => /^NEXT:/.test(p.label)), false); assert.throws(() => bounds(s), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("character status: " + checks + " focused groups passed; actual source/canonical-record capture only, no battle/assets/browser/native acceptance");
