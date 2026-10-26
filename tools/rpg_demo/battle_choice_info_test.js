// SPDX-License-Identifier: MIT
// Focused offline check: node --max-old-space-size=128 tools/rpg_demo/battle_choice_info_test.js
// Actual battle drawing/chooser/item functions and authored catalogs. Canvas calls are recorded; no assets/DOM/boot.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const PrismSummons = require("./summons.js");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value)), parties = data("party").party, catalog = data("spells").spells;
const quest = Array.from(builder.match(/^QUEST = \[([^\r\n]+)\]$/m)[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g), m => m[2]);
const bosses = data("prism-bosses").bosses.filter(b => quest.includes(b.dungeon)), gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(data("interiors").interiors[realm]))
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
for (const fish of data("prism-fish").fish) gear[fish.name] = { name: fish.name, effect: fish.effect };
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="),
  between("function makeMember(", "/* Recruits:"), between("const atkOf =", "/* ---------- maps"),
  between("const ITEM_KINDS =", "function menuTick()"), between("function useItem(", "/* Four rows"),
  between("const STATUS =", "function inflict("), line("function wrap("), line("const CMDS ="),
  line("const SUMMONS ="), line("const mySpirits ="), line("const battleCmds ="),
  between("function nextChooser(", "function pop("), between("function spellHint(", "/* ---------- title:"),
  "this.api = { makeMember, battleTick, drawBattle, spellHint, itemLine, useItem, battleItems, battleItemStock, mySpirits, wrap, chars: CHARS, commands: CMDS };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, realm = "prism", productionSource = source) {
  const draws = [], cursors = [], pressed = new Set(), known = new Set(parties[realm].members.flatMap(m => m.spells));
  const spells = catalog.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2));
  const c = { D: { party: clone(parties[realm]), spells: clone(spells), realm_key: realm,
    realm_profile: realm === "portal" ? { start_level: 1 } : null,
    dungeons: clone(bosses).map(b => ({ boss_data: b })), rects: { backdrops: {}, sprites: {}, spells: {} } },
    W: width, H: 224, party: [], reserve: [], GEAR: clone(gear), bag: {}, gold: 237,
    state: { beaten: new Set(bosses.map(b => b.name)), minute: 480 }, map: { kind: "world" }, mode: "battle",
    settingsFramePaused: false, window: { PrismSummons }, PrismSummons,
    hit: key => { const found = pressed.has(key); pressed.delete(key); return found; },
    rnd: (a, b) => (a + b) / 2, clamp: (n, a, b) => Math.max(a, Math.min(b, n)),
    sfx() {}, gauge() {}, win() {}, spr() {}, toast() {}, clearAll() {},
    g: { fillStyle: "", fillRect() {}, drawImage() {} }, performance: { now: () => 0 },
    text: (label, x, y, color = "#ffffff") => draws.push({ label: String(label).toUpperCase(), x, y, color }),
    tw: label => String(label).length * 6, cursor: (x, y) => cursors.push({ x, y }),
    saveGame() { throw new Error("browsing choices must not save"); } };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, realm === "portal" ? 1 : 15));
  c.B = { phase: "cmd", sub: "magic", who: 0, cmd: 0, oi: 0, acts: [], summoned: [], foes: [], pops: [], flash: {}, t: 0, fx: null, boss: false, round: 1 };
  return { c, api: c.api, draws, cursors,
    tick(...keys) { keys.forEach(k => pressed.add(k)); c.api.battleTick(1 / 60); },
    draw() { draws.length = 0; cursors.length = 0; const before = JSON.stringify({ party: c.party, bag: c.bag, gold: c.gold, state: c.state, battle: c.B });
      c.api.drawBattle(); assert.equal(JSON.stringify({ party: c.party, bag: c.bag, gold: c.gold, state: c.state, battle: c.B }), before, "drawing preserves chooser state and resources"); return draws; } };
}
function assertInfo(s, name, hint) {
  s.draw(); const split = s.c.W < 320 ? 120 : 150, columns = s.c.W < 320 ? 18 : 23;
  const footer = s.draws.filter(t => t.x === 6 && t.y >= 190), wrapped = Array.from(s.api.wrap(hint, columns));
  assert.ok(wrapped.length <= 2, "the complete hint fits without omitted lines: " + hint);
  assert.deepEqual(footer.map(t => t.label), [name.toUpperCase()].concat(wrapped), "the full selected name and complete effect are visible");
  assert.deepEqual(footer.map(t => t.y), [190].concat(wrapped.map((_, i) => 201 + i * 11)));
  for (const t of footer) {
    assert.ok(t.x + s.c.tw(t.label) <= split - 6 && t.y + 8 <= 220, "footer stays inside its existing command window");
    assert.ok(Array.from(t.label).every(char => s.api.chars.includes(char)), "all information uses supported font glyphs");
  }
  assert.equal(s.cursors.length, 1); assert.ok([152, 165, 178].includes(s.cursors[0].y), "selected cursor stays among three visible rows");
  const row = s.draws.find(t => t.x === 22 && t.y === s.cursors[0].y);
  assert.ok(row && name.toUpperCase().startsWith(row.label), "the cursor identifies the selected visible option");
  return row;
}
const spellMeaning = s => {
  const target = { ally: "ALLY", enemy: "FOE", all_enemies: "ALL FOES" }[s.target]; assert.ok(target);
  const status = { heal: "HEAL", protect: "WARD", haste: "HASTE", slow: "SLOW", sleep: "SLEEP", poison: "POISON", drain_hp: "DARK DRAIN" }[s.status];
  return (status || (s.element === "none" ? "DAMAGE" : s.element.toUpperCase())) + " / " + target;
};
for (const width of [320, 256]) for (const realm of ["prism", "portal"]) check("all authored demo spell choices scroll with complete hints at " + width + "/" + realm, () => {
  const s = session(width, realm), spells = s.c.D.spells, actor = s.c.party[0]; actor.spells = spells.map(sp => sp.name); actor.mp = 1000;
  for (let i = 0; i < spells.length; i++) {
    assert.equal(s.c.B.oi, i); const row = assertInfo(s, spells[i].name, spellMeaning(spells[i]));
    assert.equal(row.color, "#ffffff"); assert.ok(s.draws.some(t => t.y === row.y && t.label === spells[i].mp + "MP"));
    s.tick("down");
  }
  assert.equal(s.c.B.oi, 0, "Down wraps across the whole authored list"); s.tick("up"); assert.equal(s.c.B.oi, spells.length - 1);
  assertInfo(s, spells.at(-1).name, spellMeaning(spells.at(-1)));
});
for (const width of [320, 256]) check("all real battle items retain complete effects and free-stock counts at " + width, () => {
  const s = session(width); s.c.B.sub = "item";
  for (const [name, item] of Object.entries(gear)) if (item.effect) s.c.bag[name] = 2;
  const items = Array.from(s.api.battleItems()); assert.ok(items.includes("Feather of Waking") && !items.includes("Camp Tent"));
  for (let i = 0; i < items.length; i++) {
    assert.equal(s.c.B.oi, i); const row = assertInfo(s, items[i], s.api.itemLine(items[i]));
    assert.ok(s.draws.some(t => t.y === row.y && t.label === ":2")); s.tick("down");
  }
  assert.equal(s.c.B.oi, 0); s.tick("up"); assert.equal(s.c.B.oi, items.length - 1);
});
check("displayed HP and MP item scaling matches actual item use", () => {
  const s = session(), actor = s.c.party[0], caster = s.c.party[2]; s.c.B.sub = "item"; s.c.bag = { "Herb Tonic": 2, "Clear Draught": 2 };
  actor.hp = 1; assert.ok(actor.max > 120); const hp = actor.hp; assertInfo(s, "Herb Tonic", "HEALS 120 HP");
  s.api.useItem("Herb Tonic", actor); assert.equal(actor.hp - hp, 120);
  s.c.B.oi = 1; caster.mp = 0; assertInfo(s, "Clear Draught", "RESTORES 60 MP");
  s.api.useItem("Clear Draught", caster); assert.equal(caster.mp, 60);
});
for (const width of [320, 256]) check("Smoke Pouch discloses existing boss escape refusal at " + width, () => {
  const s = session(width); s.c.B.sub = "item"; s.c.bag = { "Smoke Pouch": 1 };
  assertInfo(s, "Smoke Pouch", s.api.itemLine("Smoke Pouch")); s.c.B.boss = true;
  assertInfo(s, "Smoke Pouch", "NO ESCAPE FROM A BOSS."); assert.equal(s.c.bag["Smoke Pouch"], 1);
});
check("queued item reservations remain excluded from free stock", () => {
  const s = session(); s.c.B.sub = "item"; s.c.bag = { "Herb Tonic": 2, "Wake Bell": 1 };
  s.c.B.acts.push({ kind: "item", who: s.c.party[1], item: "Herb Tonic", target: s.c.party[2] });
  const row = assertInfo(s, "Herb Tonic", s.api.itemLine("Herb Tonic")); assert.ok(s.draws.some(t => t.y === row.y && t.label === ":1"));
  s.c.B.acts.push({ kind: "item", who: s.c.party[2], item: "Herb Tonic", target: s.c.party[0] });
  assert.equal(s.api.battleItems().includes("Herb Tonic"), false); assertInfo(s, "Wake Bell", s.api.itemLine("Wake Bell"));
});
for (const width of [320, 256]) check("unlocked summon choices describe element, all foes and once-per-battle at " + width, () => {
  const s = session(width); s.c.B.sub = "summon"; s.c.party[0].mp = 1000;
  const spirits = Array.from(s.api.mySpirits()); assert.equal(spirits.length, 3, "only the authored demo shard summons are available");
  for (let i = 0; i < spirits.length; i++) {
    const sp = spirits[i], row = assertInfo(s, sp.name, sp.element.toUpperCase() + " / ALL FOES. ONCE PER BATTLE.");
    assert.equal(row.color, "#ffffff"); assert.ok(s.draws.some(t => t.y === row.y && t.label === sp.mp + "MP")); s.tick("down");
  }
  assert.equal(s.c.B.oi, 0);
});
for (const condition of ["called", "planned", "mp"]) check("summon " + condition + " information agrees with the actual selector refusal", () => {
  const s = session(), sp = s.api.mySpirits()[0]; s.c.B.sub = "summon";
  if (condition === "called") s.c.B.summoned.push(sp.name);
  if (condition === "planned") s.c.B.acts.push({ kind: "summon", who: s.c.party[1], spirit: sp, target: "all" });
  if (condition === "mp") s.c.party[0].mp = sp.mp - 1;
  const expected = { called: "ALREADY ANSWERED", planned: "CALL PLANNED", mp: "NOT ENOUGH MP" }[condition];
  assert.equal(assertInfo(s, sp.name, expected).color, "#808090");
  const before = JSON.stringify({ party: s.c.party, bag: s.c.bag, acts: s.c.B.acts }); s.tick("a");
  assert.equal(s.c.B.sub, "summon"); assert.equal(JSON.stringify({ party: s.c.party, bag: s.c.bag, acts: s.c.B.acts }), before);
});
check("a normal summon still plans once without spending MP and is then shown as planned", () => {
  const s = session(), sp = s.api.mySpirits()[0], actor = s.c.party[1]; s.c.B.sub = "summon"; s.c.B.who = 1;
  assert.ok(actor.mp >= sp.mp); const mp = actor.mp;
  s.tick("a"); assert.equal(s.c.B.acts.length, 1); assert.equal(s.c.B.acts[0].spirit.name, sp.name);
  assert.equal(actor.mp, mp); assert.equal(s.c.B.who, 2); s.c.B.sub = "summon";
  assert.equal(assertInfo(s, sp.name, "CALL PLANNED").color, "#808090");
});
check("spell MP shortage and normal ally target selection remain unchanged", () => {
  const s = session(), sp = s.c.D.spells.find(x => x.name === "Mend"); s.c.party[0].spells = [sp.name]; s.c.party[0].mp = sp.mp - 1;
  assert.equal(assertInfo(s, sp.name, "HEAL / ALLY").color, "#808090"); s.tick("a"); assert.equal(s.c.B.sub, "magic");
  s.c.party[0].mp = sp.mp; s.tick("a"); assert.equal(s.c.B.sub, "target"); assert.equal(s.c.B.pending.spell.name, sp.name);
  assert.equal(s.c.B.list.length, s.c.party.length); assert.equal(s.c.B.acts.length, 0); assert.equal(s.c.party[0].mp, sp.mp);
});
check("command availability and empty chooser drawing retain their current behavior", () => {
  const s = session(); s.c.B.sub = null; s.draw();
  for (const cmd of Array.from(s.api.commands).concat(["SUMMON"])) assert.ok(s.draws.some(t => t.label === cmd));
  s.c.B.sub = "magic"; s.c.party[0].spells = []; s.draw(); assert.equal(s.cursors.length, 0);
});
check("controlled former chooser fails the full-name/effect visibility assertion", () => {
  const a = source.indexOf("    const m = party[B.who], called ="), tail = source.slice(a).search(/  \} else \{\r?\n    wrap\(B\.msg/), b = a + tail; assert.ok(a >= 0 && tail > 0);
  const old = '    const m = party[B.who], used = new Set(B.summoned || []);\n' +
    '    const opts = B.sub === "summon" ? mySpirits().map(s => [s.name, s.mp + "MP", m.mp >= s.mp && !used.has(s.name)]) : B.sub === "magic" ? m.spells.map(spellOf).filter(Boolean).map(s => [s.name, s.mp + "MP", m.mp >= s.mp]) : battleItems().map(k => [k, ":" + battleItemStock(k), true]);\n' +
    '    const from = clamp((B.oi || 0) - 3, 0, Math.max(0, opts.length - 5));\n' +
    '    opts.slice(from, from + 5).forEach((o, i) => { text(o[0].slice(0, compact ? 10 : 12), 22, 152 + i * 13, o[2] ? "#ffffff" : "#808090"); text(o[1], split - 6 - tw(o[1]), 152 + i * 13); });\n' +
    '    cursor(10, 152 + ((B.oi || 0) - from) * 13);\n';
  const s = session(320, "prism", source.slice(0, a) + old + source.slice(b)); s.c.B.sub = "item"; s.c.bag = { "Feather of Waking": 1 };
  assert.throws(() => assertInfo(s, "Feather of Waking", s.api.itemLine("Feather of Waking")), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; no boot/game loop or browser work.
console.log("Prismheart battle choice information checks: " + checks + " passed; full inline script compiles.");
