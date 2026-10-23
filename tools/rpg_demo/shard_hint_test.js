// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/shard_hint_test.js
// Actual interact/say/wrap plus authored QUEST/dungeon/boss metadata. No builder/browser/native/storage work.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const portal = fs.readFileSync(path.join(__dirname, "portal_realm.py"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const dungeonCatalog = data("dungeons").dungeons, bosses = data("prism-bosses").bosses;
function quest(text) {
  const declaration = text.match(/^QUEST = \[([^\r\n]+)\]$/m); assert.ok(declaration, "existing authored QUEST declaration");
  return Array.from(declaration[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g), match => [match[1], match[2]]);
}
const finalName = builder.match(/^FINAL = "([^"]+)"$/m)[1];
function projection(realm, spec) {
  return spec.map(([landmark, name]) => {
    const dungeon = dungeonCatalog[realm].find(d => d.name === name); assert.ok(dungeon, "QUEST names an authored dungeon");
    const boss = realm === "prism" ? bosses.find(b => b.dungeon === name) : null;
    if (realm === "prism") assert.ok(boss, "QUEST names an authored boss");
    return { name: dungeon.name, landmark, final: realm === "prism" && name === finalName,
      boss_data: boss ? { name: boss.name, shard: boss.shard } : null };
  });
}
const dungeons = projection("prism", quest(builder)), shardDungeons = dungeons.filter(d => !d.final);
assert.equal(shardDungeons.length, 3, "existing demo uses three shard dungeons");
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const DIRS ="), line("const at ="), line("const npcAt ="),
  between("const carriesShard =", "const chestKey ="), between("let dlg = null;", "function wrap("),
  between("function wrap(", "function drawDialog("), between("const LINES =", "function innPrompt("),
  "this.api = { interact, wrap, dialog: () => dlg, chars: () => CHARS, setRulerLines: lines => { LINES.Ruler = lines; } };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(beaten = [], productionSource = source, realm = "prism") {
  const npc = { type: "Ruler", x: 1, y: 1, dir: "left" }, c = {
    D: { realm_key: realm, dungeons: JSON.parse(JSON.stringify(realm === "prism" ? dungeons : projection("portal", quest(portal)))) },
    P: { x: 1, y: 2, dir: "up" }, map: { kind: "interior", info: {}, npcs: [npc], grid: [["Floor", "Floor"], ["Floor", "Floor"]] },
    state: { beaten: new Set(beaten), quests: { preserved: true }, seen: {} },
    bag: { "Herb Tonic": 8 }, gold: 237, opened: new Set(["existing chest"]), party: [{ name: "Corin", hp: 123, mp: 6 }],
    saveGame() { throw new Error("talking must not save"); }, sfx() {},
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  return { c, npc, api: c.api };
}
const resources = s => JSON.stringify({ bag: s.c.bag, gold: s.c.gold, opened: Array.from(s.c.opened), party: s.c.party,
  beaten: Array.from(s.c.state.beaten), quests: s.c.state.quests, seen: s.c.state.seen, data: s.c.D, grid: s.c.map.grid });
function talk(s) {
  const before = resources(s), beaten = s.c.state.beaten; s.api.interact();
  assert.equal(resources(s), before, "hints preserve inventory, gold, progression, saves and source metadata");
  assert.equal(s.c.state.beaten, beaten); assert.equal(s.npc.dir, "down", "existing NPC facing behavior remains");
  const dialog = s.api.dialog(); assert.ok(dialog && !dialog.choice); return Array.from(dialog.pages);
}
function expectedHint(d) { return "THE " + d.boss_data.shard.toUpperCase() + " SHARD: " + d.name.toUpperCase() + ". MAP: " + d.landmark.toUpperCase() + "."; }
function assertPartial(mask, productionSource = source) {
  const beaten = shardDungeons.filter((_, index) => mask & (1 << index)), remaining = shardDungeons.filter(d => !beaten.includes(d));
  const s = session(beaten.map(d => d.boss_data.name), productionSource), pages = talk(s), count = 3 - beaten.length;
  const original = "THE HEART BURNS A LITTLE BRIGHTER. " + count + (count === 1 ? " SHARD REMAINS." : " SHARDS REMAIN.");
  assert.deepEqual(pages, [original].concat(remaining.map(expectedHint)), "only remaining authored shard routes follow the original partial-progress page");
  assert.equal(s.api.dialog().voice, 1); assert.equal(s.api.dialog().then, null);
  for (const page of pages) {
    const lines = s.api.wrap(page, Math.floor((320 - 32) / 6));
    assert.ok(lines.length <= 4 && lines.every(text => text.length <= 48), "the complete page fits the existing dialog window");
    assert.ok(Array.from(page).every(char => s.api.chars().includes(char)), "all hint glyphs exist in the current bitmap font");
  }
  return pages;
}
for (let mask = 1; mask < 7; mask++) check("partial shard subset " + mask + " lists every remaining route", () => assertPartial(mask));
check("zero-shard Ruler dialogue is preserved exactly", () => {
  const s = session(); assert.deepEqual(talk(s), ["BRING BACK THE SHARDS OF FIRE, GALE AND LIGHT, AND THE REALM WILL REMEMBER YOUR NAMES."]);
});
check("unrelated beaten records do not add hints to the original zero-shard branch", () => {
  const s = session(["UnrelatedBoss"]);
  assert.deepEqual(talk(s), ["THE HEART BURNS A LITTLE BRIGHTER. 3 SHARDS REMAIN."]);
});
check("three shards preserve the existing Crystal Shrine direction", () => {
  const s = session(shardDungeons.map(d => d.boss_data.name));
  assert.deepEqual(talk(s), ["ALL THREE SHARDS! TAKE THEM TO THE CRYSTAL SHRINE IN THE SOUTH-EAST. WHAT WAITS THERE IS HUNGRY."]);
});
for (const includeShards of [false, true]) check("healed-final dialogue remains exact with shard history " + includeShards, () => {
  const finalBoss = dungeons.find(d => d.final).boss_data.name;
  const s = session((includeShards ? shardDungeons.map(d => d.boss_data.name) : []).concat(finalBoss));
  assert.deepEqual(talk(s), ["THE HEART IS WHOLE AGAIN. YOU HAVE THE THANKS OF EVERY ISLAND."]);
});
check("optional non-shard and bossless records cannot become new route hints", () => {
  const s = session([shardDungeons[0].boss_data.name]);
  for (const name of ["Gearwright's Folly", "Fallen Keep"]) {
    const boss = bosses.find(b => b.dungeon === name); assert.equal(boss.shard, "-");
    s.c.D.dungeons.push({ name, final: false, boss_data: { name: boss.name, shard: boss.shard } });
  }
  s.c.D.dungeons.push({ name: "No boss", final: false, boss_data: null });
  assert.deepEqual(talk(s).slice(1), shardDungeons.slice(1).map(expectedHint));
});
check("Portal's actual bossless projection keeps its existing Ruler dialogue", () => {
  const original = portal.match(/"Ruler": \["([^"]+)"\]/)[1];
  for (const beaten of [[], ["UnrelatedBoss"]]) {
    const s = session(beaten, source, "portal"); s.api.setRulerLines([original]); assert.deepEqual(talk(s), [original]);
  }
});
check("custom default NPC lines and unrelated NPC dialogue are unchanged", () => {
  const s = session(); s.npc.lines = ["A PRIVATE AUDIENCE."]; assert.deepEqual(talk(s), s.npc.lines);
  s.npc.type = "Farmer"; delete s.npc.lines; assert.deepEqual(talk(s), ["RABBITS ATE MY TURNIPS AGAIN. THE WOLVES ARE NO HELP."]);
});
check("controlled former count-only dialogue fails the same remaining-route assertion", () => {
  const addition = ".concat(c > 0 ? remainingShardHints() : [])"; assert.ok(source.includes(addition));
  const legacy = source.replace(addition, "");
  for (const mask of [1, 3, 6]) assert.throws(() => assertPartial(mask, legacy), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; no boot, DOM or game loop execution.
console.log("Prismheart shard hint checks: " + checks + " passed; full inline script compiles.");
