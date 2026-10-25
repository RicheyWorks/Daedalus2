// SPDX-License-Identifier: MIT
// Focused DOM-free check: node --max-old-space-size=128 tools/rpg_demo/field_spell_info_test.js
// Actual field spell/status drawing, menu handlers, recruited roster and purchasable spell catalogs.
// No browser, game loop, asset generation, real storage, builds or native runtime is launched.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const parties = data("party").party, interiors = data("interiors").interiors, allSpells = data("spells").spells;
const menus = data("menus").layouts, fish = data("prism-fish").fish, bosses = data("prism-bosses").bosses;
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
function line(prefix) {
  const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found;
}
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"),
  between("const START_LEVEL =", "/* Recruits:"), between("function recruitsFor(", "function recruitBeaten("),
  line("const atkOf ="), line("const defOf ="), line("const spellOf ="),
  line("const magicShopCaster ="), between("function buy(", "function shopTick("), between("let menu = null;", "function drawEquip("),
  between("const STATUS =", "/* ---------- bestiary"), between("function spellHint(", "function drawBattle("), between("function titlePrompt(", "function drawTitle("),
  "this.api = { start: () => { party = buildParty(); }, openMenu, menuTick, drawMenu, drawStatus, fieldSpells, spellHint, buy, recruit, " +
  "roster, party: () => party, reserve: () => reserve, menu: () => menu, chars: CHARS, " +
  "setGold: n => { gold = n; }, shortenFront: n => { reserve = party.slice(n).concat(reserve); party = party.slice(0, n); }, " +
  "snapshot: () => ({ party, reserve, bag, gold, menu, beaten: Array.from(state.beaten), opened: Array.from(opened), " +
  "seen: state.seen, fish: state.fish, quests: state.quests, day: state.day, minute: state.minute, air: state.air, " +
  "returnTo: state.returnTo, ways: Array.from(state.ways), pressed }) };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(realm = "prism", productionSource = source) {
  const gear = {}, draws = [], sounds = [], pressed = {}, storage = { record: "existing saved journey", reads: 0, writes: 0 };
  for (const key of ["portal", realm]) for (const shop of Object.values(interiors[key]))
    for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
  if (realm === "prism") for (const f of fish) gear[f.name] = { name: f.name, effect: f.effect, price: f.price, fish: true };
  const known = new Set(parties[realm].members.flatMap(m => m.spells));
  const c = {
    D: { realm_key: realm, party: clone(parties[realm]), gear: clone(gear), menus: clone(menus[realm]), rects: { sprites: {} },
      spells: clone(allSpells.filter(s => s.realm === realm && (s.tier <= 2 || known.has(s.name)))),
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: realm === "portal" ? 256 : 320, H: 224, PAD: null, map: { kind: "town" }, B: null, pressed,
    state: { beaten: new Set(), seen: {}, fish: {}, quests: {}, ways: new Set(), day: 1, minute: 480, air: null, returnTo: null }, opened: new Set(),
    shop: { kind: "magic", msg: "" }, mode: "field", drawField() {}, spr() {}, gauge() {},
    shardCount: () => 0, clockText: () => "D1 08:00", isNight: () => false,
    sfx: sound => sounds.push(sound), clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: s => String(s).length * 6,
    win: (...rect) => draws.push({ kind: "window", rect }),
    text: (label, x, y, color = "#ffffff") => draws.push({ kind: "text", label: String(label).toUpperCase(), x, y, color }),
    cursor: (x, y) => draws.push({ kind: "cursor", x, y }), g: { fillStyle: "", fillRect() {} },
    localStorage: { getItem() { storage.reads++; return storage.record; }, setItem() { storage.writes++; throw new Error("render must not save"); },
      removeItem() { storage.writes++; throw new Error("render must not erase"); } },
    saveGame() { storage.writes++; throw new Error("render must not save"); }
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.api.start();
  return { c, api: c.api, draws, sounds, storage,
    tick(...keys) { keys.forEach(k => { pressed[k] = true; }); c.api.menuTick(); },
    draw() { draws.length = 0; const before = JSON.stringify(c.api.snapshot()), saved = JSON.stringify(storage), soundCount = sounds.length;
      c.api.drawMenu(); assert.equal(JSON.stringify(c.api.snapshot()), before, "drawing cannot change spells, resources, roster, input, selection or saved journey state");
      assert.equal(JSON.stringify(storage), saved, "drawing does not access or replace the saved record"); assert.equal(sounds.length, soundCount); return draws; }
  };
}
function earnedRoster(s) {
  for (const name of ["Cinder Forge", "Windcut Aerie", "Sunwell Sanctum"]) {
    s.api.recruit(name); const boss = bosses.find(b => b.dungeon === name); assert.ok(boss); s.c.state.beaten.add(boss.name);
  }
  assert.equal(s.api.roster().length, 7); return s;
}
function learnShop(s) {
  s.api.setGold(100000); // An affordable purse for actual shop rules; no invented spell-learning route.
  for (const item of interiors.prism.Magic.stock) s.api.buy(clone(item));
  return s;
}
function openBook(s, member) {
  s.api.openMenu(); s.tick("down"); s.tick("a"); const m = s.api.menu();
  const who = s.api.roster().indexOf(member); assert.ok(who >= 0);
  for (let n = 0; n < s.api.roster().length && m.who !== who; n++) s.tick("right");
  assert.equal(m.who, who); s.tick("a"); assert.equal(m.sub, "magic"); return m;
}
function selectedDrawing(s, member, index, battleOnly, target = false) {
  const list = Array.from(s.api.fieldSpells(member)), sp = list[index], m = s.api.menu(); assert.ok(sp);
  if (target && s.c.D.realm_key === "prism") {
    s.draw();
    const heading = s.draws.find(d => d.kind === "text" && d.x === 12 && d.y === 10); assert.equal(heading.label, sp.name.toUpperCase());
    assert.ok(s.draws.some(d => d.kind === "text" && d.y === 10 && d.label === sp.mp + " MP"));
    assert.ok(s.draws.some(d => d.kind === "cursor" && d.x === 12 && d.y === 50 + m.target * 16));
    assert.equal(s.draws.some(d => d.kind === "window" && d.rect.join() === [20,60,220,112].join()), false);
    assert.equal(m.ii, index); return heading;
  }
  const rows = s.draw().filter(d => d.kind === "text" && d.x === 40 && list.some(p => p.name.toUpperCase() === d.label));
  assert.equal(rows.length, Math.min(6, list.length), "existing six-row spell viewport remains bounded");
  assert.ok(rows.every(r => r.y >= 72 && r.y <= 137 && r.y + 8 <= 145));
  const selected = rows.find(r => r.label === sp.name.toUpperCase()); assert.ok(selected, "selected spell remains visible");
  assert.equal(selected.color, battleOnly ? "#6c6c8c" : "#ffffff", "row color agrees with actual field Confirm eligibility");
  const cost = s.draws.find(d => d.kind === "text" && d.label === sp.mp + " MP" && d.y === selected.y && d.x === 220 - s.c.tw(sp.mp + " MP"));
  assert.ok(cost); assert.equal(cost.color, selected.color);
  const hint = s.draws.find(d => d.kind === "text" && d.x === 28 && d.y === 160); assert.ok(hint, "selected spell has a detail row");
  assert.equal(hint.label, (battleOnly ? "BATTLE ONLY. " : "") + s.api.spellHint(sp));
  assert.ok(hint.label.length <= 34 && hint.x + hint.label.length * 6 <= 232 && hint.y + 8 <= 172, "the full detail and shadow fit the current spell window");
  assert.ok(Array.from(hint.label).every(ch => s.api.chars.includes(ch)), "every detail glyph exists in the bitmap font");
  const cursors = s.draws.filter(d => d.kind === "cursor" && d.x === 28); assert.equal(cursors.length, target ? 0 : 1);
  if (!target) assert.equal(cursors[0].y, selected.y);
  const cue = s.draws.find(d => d.kind === "text" && d.x === 28 && d.y === 145);
  if (list.length > 6) {
    const from = Math.max(0, Math.min(index - 5, list.length - 6)); assert.equal(cue.label, (from + 1) + "-" + (from + 6) + "/" + list.length);
  } else assert.equal(cue, undefined);
  assert.equal(m.ii, index); return hint;
}
for (const job of ["Lightmender", "Runecaster", "Beastcaller", "Chronoseer"]) check("actual learned " + job + " book explains each spell without changing Confirm outcomes", () => {
  const s = learnShop(earnedRoster(session())), member = s.api.roster().find(m => m.job === job), m = openBook(s, member);
  const list = Array.from(s.api.fieldSpells(member)); assert.ok(list.length);
  for (let index = 0; index < list.length; index++) {
    m.ii = index; const sp = list[index], before = JSON.stringify({ member, party: s.api.party(), reserve: s.api.reserve() });
    // Use the actual command refusal/target outcome to classify eligibility rather than assuming all ally spells work.
    s.tick("a"); const battleOnly = m.sub === "magic" && / IS FOR BATTLE\.$/.test(m.msg);
    if (!battleOnly) assert.equal(m.sub, "magic-target", "an affordable field spell retains its existing target transition");
    assert.equal(JSON.stringify({ member, party: s.api.party(), reserve: s.api.reserve() }), before, "choosing or refusing a spell spends no MP before an actual target Confirm");
    selectedDrawing(s, member, index, battleOnly, !battleOnly);
    if (!battleOnly) { s.tick("b"); assert.equal(m.sub, "magic"); selectedDrawing(s, member, index, false); }
    else assert.equal(member.mp >= sp.mp, true, "battle-only refusal is not caused by an unaffordable spell");
  }
});
check("Ward and Quicken are visibly battle-only despite their authored ally targets", () => {
  const s = earnedRoster(session());
  for (const [job, name] of [["Lightmender", "Ward"], ["Chronoseer", "Quicken"]]) {
    const member = s.api.roster().find(m => m.job === job), m = openBook(s, member); m.ii = member.spells.indexOf(name); assert.ok(m.ii >= 0);
    selectedDrawing(s, member, m.ii, true); const before = JSON.stringify(s.api.snapshot()); s.tick("a");
    assert.equal(m.sub, "magic"); assert.match(m.msg, /IS FOR BATTLE/); assert.equal(member.mp, JSON.parse(before).party.concat(JSON.parse(before).reserve).find(p => p.job === job).mp);
  }
});
check("a living reserve caster's book is available through the same field MAGIC chooser", () => {
  const s = earnedRoster(session()), member = s.api.reserve().find(m => m.job === "Chronoseer"), m = openBook(s, member);
  assert.ok(m.who >= s.api.party().length); assert.equal(member.spells[0], "Drowse"); selectedDrawing(s, member, 0, true);
});
check("field healing keeps its detail and exact MP cost while changing only the chosen HP", () => {
  const s = session(), member = s.api.party().find(m => m.job === "Lightmender"), m = openBook(s, member), target = s.api.party()[0];
  target.hp = 1; const mp = member.mp, hp = target.hp, sp = s.api.fieldSpells(member)[0]; selectedDrawing(s, member, 0, false);
  s.tick("a"); assert.equal(m.sub, "magic-target"); selectedDrawing(s, member, 0, false, true);
  s.tick("a"); assert.equal(member.mp, mp - sp.mp); assert.ok(target.hp > hp && target.hp <= target.max);
  selectedDrawing(s, member, 0, false, true);
});
check("out-of-MP healing remains field eligible and keeps the existing MP refusal", () => {
  const s = session(), member = s.api.party()[1], m = openBook(s, member); member.mp = 0;
  selectedDrawing(s, member, 0, false); s.tick("a"); assert.equal(m.sub, "magic"); assert.equal(m.msg, "NOT ENOUGH MP."); assert.equal(member.mp, 0);
});
check("downed companion spell access retains its current refusal", () => {
  const s = session(), member = s.api.party()[1]; member.hp = 0; s.api.openMenu(); s.tick("down"); s.tick("a"); s.tick("a");
  assert.equal(s.api.menu().sub, "magic-who"); assert.match(s.api.menu().msg, /IS DOWN\. REVIVE FIRST/);
});
function roles(s) {
  s.api.openMenu(); const m = s.api.menu(); m.sub = "status";
  for (let i = 0; i < s.api.roster().length; i++) {
    m.who = i; const member = s.api.roster()[i], front = s.api.party().includes(member);
    const draws = s.draw();
    if (s.c.D.realm_key === "prism") {
      const row = draws.find(d => d.kind === "text" && d.x === 52 && d.y === 22); assert.ok(row);
      assert.equal(row.label, "LV " + member.lv + (front ? " / FRONT" : " / RESERVE"));
      const count = draws.find(d => d.kind === "text" && d.y === 22 && d.label === (i + 1) + "/" + s.api.roster().length); assert.ok(count);
      assert.ok(row.x + row.label.length * 6 < count.x, "actual membership fits before the member counter");
      assert.ok(draws.some(d => d.kind === "text" && d.x === 52 && d.y === 10 && d.label.endsWith(" - " + member.job.toUpperCase())));
    } else {
      const row = draws.find(d => d.kind === "text" && d.x === 56 && d.y === 22); assert.ok(row);
      assert.equal(row.label, member.job.toUpperCase() + (front ? " / FRONT" : " / RESERVE"));
      assert.ok(row.x + row.label.length * 6 < 200 && row.y + 8 <= 36, "Portal retains the original role placement");
    }
  }
}
check("STATUS marks all authored front and earned reserve members without changing state", () => roles(earnedRoster(session())));
check("STATUS uses actual membership when fewer than four members are in front", () => {
  const s = earnedRoster(session()); s.api.shortenFront(2); assert.equal(s.api.party().length, 2); roles(s);
});
check("shared Portal roster STATUS also marks actual membership", () => roles(session("portal")));
check("controlled old ally-only grey rule is rejected for an ordinary Ward selection", () => {
  const rowRule = /const ok = [^;\r\n]+(?=; text\(sp\.name)/;
  assert.ok(rowRule.test(source), "the actual field spell row eligibility expression is present");
  const legacy = source.replace(rowRule, 'const ok = sp.target === "ally"'); assert.notEqual(legacy, source);
  const s = session("prism", legacy), member = s.api.party()[1], m = openBook(s, member); m.ii = member.spells.indexOf("Ward");
  assert.throws(() => selectedDrawing(s, member, m.ii, true), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute DOM/boot work.
console.log("Prismheart field spell information checks: " + checks + " passed; full inline script compiles.");
