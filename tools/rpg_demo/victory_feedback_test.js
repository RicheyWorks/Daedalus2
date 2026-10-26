// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/victory_feedback_test.js
// Actual factory/recruit/victory/message queue/fade/painter and one controlled successful RUN.
// Canonical records with explicit defeated-foe reward overrides/prior-theft ledger setup; no damage
// simulation, game boot, assets, durable storage, browser, full quest or native acceptance.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8"), PrismSummons = require("./summons.js");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8")), clone = value => JSON.parse(JSON.stringify(value));
const parties = data("party").party, catalogs = { prism: data("prism-bestiary").types, portal: data("portal-bestiary").types }, bosses = data("prism-bosses").bosses;
const dungeonData = data("dungeons").dungeons.prism, gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(data("interiors").interiors[realm])) for (const item of shop.stock || [])
  if (item.attack != null || item.defence != null || item.effect) gear[item.name] = clone(item);
function tuples(name) { const m = builder.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m")); assert.ok(m, name); return Array.from(m[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g), r => [r[1], r[2]]); }
const main = tuples("QUEST"), extra = tuples("OPTIONAL_QUEST"), finalName = builder.match(/^FINAL = "([^"]+)"$/m)[1];
const dungeons = main.concat(extra).map(([landmark, name], i) => ({ ...clone(dungeonData.find(d => d.name === name)), landmark, final: name === finalName, optional: i >= main.length, boss_data: clone(bosses.find(b => b.dungeon === name)) }));
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = prefix => { const found = html.split("\n").find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const hit ="), between("const START_LEVEL =", "/* ---------- maps"),
  between("const carriesShard =", "const chestKey ="), between("const STATUS =", "function inflict("), line("function wrap("),
  between("const BOSS_FLAVOUR =", "function bossGate("), between("function spellHint(", "/* ---------- title:"), between("function titlePrompt(", "function drawTitle("),
  "this.api={start:()=>{party=buildParty();},recruitAll:()=>D.party.members.filter(m=>m.joins.startsWith('after ')).forEach(m=>recruit(m.joins.slice(6)))," +
  "party:()=>party,reserve:()=>reserve,roster,gold:()=>gold,setGold:n=>{gold=n;},bag:()=>bag,startBattle,battleTick,endRound,finishBattle,doAction,drawBattle,wrap,chars:CHARS};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], pressed = {}, sounds = [], dialogs = [], calls = { rng: 0, storage: 0 }, math = Object.create(Math); let clock = 0, runRoll = false;
  math.random = () => { calls.rng++; if (runRoll) return 0; throw new Error("unexpected gameplay RNG"); };
  const c = { W: width, H: 224, D: { realm_key: realm, party: clone(parties[realm]), gear: clone(gear), dungeons: realm === "prism" ? clone(dungeons) : [],
      foes: Object.fromEntries(catalogs[realm].map(f => [f.key, clone(f)])), backdrop_for_zone: { fixture: "field" }, rects: { backdrops: {}, sprites: {}, spells: {} },
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    state: { beaten: new Set(), ways: new Set(), seen: {}, sinceBattle: 0, minute: 480 }, map: { kind: "world", cue: "FIELD" }, mode: "field", B: null,
    fade: 0, fadeCb: null, ending: null, goT: -1, PAD: null, settingsFramePaused: true, IM: {}, pressed, Math: math, performance: { now: () => clock },
    window: { PrismSummons }, PrismSummons, clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: value => String(value).length * 6,
    rnd(a) { calls.rng++; return a; }, passTime() {}, meet() {}, cue() {}, sfx: name => sounds.push(name), fell() {}, toast() {}, say: pages => dialogs.push(pages),
    saveGame() { calls.storage++; throw new Error("unexpected storage use"); }, localStorage: { getItem() { calls.storage++; throw new Error("storage read"); } },
    spr() {}, win() {}, gauge() {}, cursor() {}, g: { fillStyle: "", fillRect() {}, drawImage() {} },
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ label, x, y, w: label.length * 6, h: 8, color }); }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify({ members: c.api.roster(), bag: c.api.bag(), gold: c.api.gold(), beaten: [...c.state.beaten] });
  const snapshot = () => JSON.stringify({ resources: resources(), D: c.D, battle: c.B, map: c.map, mode: c.mode, fade: c.fade, ending: c.ending, calls });
  return { c, api: c.api, paints, pressed, sounds, dialogs, calls, resources,
    begin(boss = null, key = catalogs[realm][0].key) { c.api.startBattle("fixture", boss, boss ? undefined : [key]); const cb = c.fadeCb; c.fadeCb = null; cb(); c.fade = 0; c.B.phase = "act"; return this; },
    settle(exp = 5, gold = 0) { assert.equal(c.B.foes.length, 1); Object.assign(c.B.foes[0], { hp: 0, exp, gold }); c.api.endRound(); assert.equal(c.B.result, "win"); assert.equal(c.B.phase, "end"); return this; },
    tick(dt = 0, ...keys) { keys.forEach(k => { pressed[k] = true; }); c.api.battleTick(dt); },
    next() { if (c.B.wait > 0) c.api.battleTick(c.B.wait); pressed.a = true; c.api.battleTick(0); },
    applyFade() { const cb = c.fadeCb; assert.equal(typeof cb, "function"); c.fadeCb = null; cb(); c.fade = 0; },
    draw(now = clock) { clock = now; paints.length = 0; const before = snapshot(); c.api.drawBattle(); assert.equal(snapshot(), before, "painting changed rewards, queue, progress, RNG or storage"); return paints; },
    allowRun(value) { runRoll = value; }, messages: () => [c.B.msg].concat(Array.from(c.B.endLines || [])), labels: () => paints.map(p => p.label)
  };
}
const growth = (s, m) => s.c.D.party.members.find(record => record.job === m.job).growth;
function nearLevel(s) { s.api.roster().forEach(m => { m.hp = m.max - 7; m.mp = Math.max(0, m.mmax - 3); m.exp = m.next - (s.api.party().includes(m) ? 5 : 2); }); }
function levelMessage(s, m, lv = m.lv) { const g = growth(s, m), name = m.name.toUpperCase(), shown = name.length > 12 ? name.slice(0, 9) + "..." : name;
  return shown + " REACHES LEVEL " + (lv > 999 ? "999+" : lv) + "! MAX HP +" + g.hp + " / MAX MP +" + g.mp + ". ALL STATS +1."; }
check("all eight level messages match actual capacity/current/stat gains without healing away deficits", () => {
  const s = session(); s.api.recruitAll(); assert.equal(s.api.roster().length, 8); nearLevel(s); const before = s.api.roster().map(clone); s.begin().settle();
  const messages = s.messages(); assert.equal(messages.length, 9); assert.equal(messages[0], "VICTORY! 5 EXP AND 0 GOLD.");
  s.api.roster().forEach((m, i) => { const old = before[i], g = growth(s, m); assert.equal(messages[i + 1], levelMessage(s, m)); assert.equal(m.lv, old.lv + 1);
    assert.equal(m.max - old.max, g.hp); assert.equal(m.hp - old.hp, g.hp); assert.equal(m.mmax - old.mmax, g.mp); assert.equal(m.mp - old.mp, g.mp);
    Object.keys(old.st).forEach(key => assert.equal(m.st[key], old.st[key] + 1)); assert.equal(m.max - m.hp, 7); assert.equal(m.mmax - m.mp, old.mmax - old.mp); });
  assert.equal(s.sounds.filter(name => name === "LEVEL").length, 8); assert.deepEqual(s.calls, { rng: 0, storage: 0 });
});
check("multiple levels stay one message per level in original actor/level order", () => {
  const s = session(), member = s.api.party()[0], hp = member.max; member.name = "River"; s.api.party().slice(1).forEach(m => { m.hp = 0; });
  s.begin().settle(400 + Math.round(400 * 1.18)); const messages = s.messages(); assert.equal(member.lv, 17); assert.equal(member.exp, 0); assert.equal(messages.length, 3);
  assert.equal(messages[1], levelMessage(s, member, 16)); assert.equal(messages[2], levelMessage(s, member, 17)); assert.equal(member.max, hp + 2 * growth(s, member).hp);
  assert.equal(s.sounds.filter(name => name === "LEVEL").length, 2);
});
check("standing front/reserve, downed and held eligibility keep their existing EXP awards", () => {
  const s = session(); s.api.recruitAll(); const members = s.api.roster(); members[0].hp = 0; members[4].hp = 0; members[1].status = { sleep: 3 }; members[5].status = { bind: 2 };
  members.forEach(m => { m.exp = 0; }); s.begin().settle(5); members.forEach(m => assert.equal(m.exp, m.hp <= 0 ? 0 : s.api.party().includes(m) ? 5 : 2));
  assert.equal(s.messages().length, 1); assert.equal(members[1].status.sleep, 3); assert.equal(members[5].status.bind, 2);
});
check("ordinary stolen-gold settlement keeps reward/refund before level information and pays once", () => {
  const s = session(), thief = catalogs.prism.find(f => f.behaviour === "steal"); assert.ok(thief); nearLevel(s); const gold = s.api.gold();
  s.api.setGold(gold - 23); s.begin(null, thief.key); s.c.B.foes[0].stolen = 23; // Explicit prior-theft ledger; not a new theft/RNG scenario.
  s.settle(5, 17); const lines = s.messages(); assert.deepEqual(lines.slice(0, 2), ["VICTORY! 5 EXP AND 17 GOLD.", "YOU TAKE BACK 23 STOLEN GOLD."]);
  assert.equal(s.api.gold(), gold + 17); assert.equal(s.c.B.foes[0].stolen, 0); assert.ok(lines[2].includes("REACHES LEVEL")); const paid = s.resources();
  while (s.c.B.endLines.length) s.next(); s.next(); assert.equal(s.c.B.phase, "out"); s.applyFade(); assert.equal(s.c.B, null); assert.equal(s.resources(), paid);
});
check("boss story/summon/recruit messages remain after existing heroes; the new recruit gets no victory growth", () => {
  const s = session(), dungeon = s.c.D.dungeons[0], floor = dungeon.floors.at(-1); nearLevel(s);
  s.c.map = { kind: "dungeon", dungeon: 0, info: floor, grid: floor.grid.map(row => row.slice()), cue: "CAVE" };
  s.begin(dungeon.boss_data).settle(5, 17); const lines = s.messages(), spirit = PrismSummons.table(s.c.D.dungeons.map(d => d.boss_data), "prism").find(sp => sp.warden === dungeon.boss_data.name);
  const record = s.c.D.party.members.find(m => m.joins === "after " + dungeon.name), recruit = s.api.reserve().find(m => m.job === record.job); assert.ok(spirit && recruit);
  assert.equal(lines.length, 9); assert.equal(lines[5], "THE SHARD OF " + dungeon.boss_data.shard.toUpperCase() + " IS YOURS.");
  assert.equal(lines[6], "THE SHARD HUMS. " + spirit.name.toUpperCase() + " WILL ANSWER A SUMMON NOW.");
  assert.equal(lines[7], recruit.name.toUpperCase() + " THE " + recruit.job.toUpperCase() + " JOINS YOU!"); assert.ok(lines[8].startsWith("USE ORDER IN THE MENU"));
  assert.equal(recruit.lv, 16); assert.equal(recruit.exp, 0); assert.equal(recruit.hp, recruit.max); assert.equal(recruit.mp, recruit.mmax); assert.ok(!lines.some(line => line.startsWith(recruit.name.toUpperCase() + " REACHES")));
  const rewarded = JSON.stringify({ members: s.api.roster(), gold: s.api.gold() }); for (const line of lines.slice(1)) { s.next(); assert.equal(s.c.B.msg, line); assert.equal(JSON.stringify({ members: s.api.roster(), gold: s.api.gold() }), rewarded); }
  assert.equal(s.c.B.phase, "end"); assert.equal(s.c.state.beaten.has(dungeon.boss_data.name), false); s.next(); assert.equal(s.c.B.phase, "out"); assert.equal(s.c.mode, "battle");
  const gate = floor.boss.gate; assert.equal(s.c.map.grid[gate.y][gate.x], "BossGate"); s.applyFade(); assert.equal(s.c.B, null); assert.equal(s.c.mode, "field");
  assert.ok(s.c.state.beaten.has(dungeon.boss_data.name)); assert.equal(s.c.map.grid[gate.y][gate.x], "Floor"); assert.equal(s.calls.storage, 0);
});
check("optional and final boss queue text stays truthful without adding level or summon messages", () => {
  for (const optional of [true, false]) { const s = session(), dungeon = s.c.D.dungeons.find(d => optional ? d.optional : d.final); s.begin(dungeon.boss_data).settle(0, 0); const lines = s.messages();
    assert.equal(lines[1], optional ? "THE COLOSSUS FALLS SILENT. BRANNOC STEPS OUT OF THE GEARS." : "THE DEVOURER COMES APART INTO LIGHT. THE HEART IS WHOLE AGAIN.");
    assert.equal(lines.some(line => line.includes("REACHES LEVEL") || line.includes("WILL ANSWER A SUMMON")), false); assert.equal(s.calls.storage, 0); }
});
for (const width of [320, 256]) check("maximum name/level message and static mapped NEXT prompt fit five rows at " + width, () => {
  const s = session(width), member = s.api.party()[0]; member.name = "ß".repeat(64); member.lv = 999; member.exp = member.next - 1; s.api.party().slice(1).forEach(m => { m.hp = 0; });
  s.begin().settle(1); const message = s.messages()[1]; assert.equal(member.lv, 1000); assert.equal(member.name, "ß".repeat(64)); assert.ok(message.startsWith("SSSSSSSSS... REACHES LEVEL 999+!"));
  assert.equal(message, levelMessage(s, member)); s.draw(); assert.equal(s.labels().some(label => label.endsWith(": NEXT")), false); s.next(); assert.equal(s.c.B.msg, message);
  s.c.PAD = { devices: () => [{ index: 2 }], label(action, index) { assert.equal(action, "confirm"); assert.equal(index, 2); return "ABCDEFGH"; } };
  const columns = width < 320 ? 16 : 22, split = width < 320 ? 120 : 150, wrapped = Array.from(s.api.wrap(message, columns)); assert.ok(wrapped.length <= 5);
  for (const now of [0, 400, 800]) { s.draw(now); const body = s.paints.filter(p => p.x === 10 && p.y >= 152 && p.y <= 204); assert.deepEqual(body.map(p => p.label), wrapped);
    const prompt = s.paints.find(p => p.x === 10 && p.y === 214); assert.equal(prompt.label, "ABCDEFGH: NEXT");
    for (const p of body.concat(prompt)) { assert.ok(p.x + p.w <= split && p.y + p.h <= 224); assert.ok([...p.label].every(ch => s.api.chars.includes(ch))); } }
  s.c.B.wait = 0.01; s.draw(); assert.equal(s.labels().some(label => label.endsWith(": NEXT")), false); s.c.B.wait = 0; s.c.PAD = null; s.draw(); assert.ok(s.labels().includes("Z/SPACE: NEXT"));
});
check("actual end wait blocks advancement, then Confirm advances one existing entry until the fade boundary", () => {
  const s = session(); nearLevel(s); s.begin().settle(); const lines = s.messages(), first = s.c.B.msg, earned = s.resources();
  s.tick(0.2, "a"); assert.equal(s.c.B.msg, first); assert.ok(Math.abs(s.c.B.wait - 0.6) < 1e-9); s.pressed.a = false; // Only this wait-gate observation; no synthetic long-lived buffered press.
  for (const line of lines.slice(1)) { s.next(); assert.equal(s.c.B.msg, line); assert.equal(s.resources(), earned); }
  assert.equal(s.c.B.phase, "end"); s.next(); assert.equal(s.c.B.phase, "out"); assert.equal(s.c.mode, "battle"); assert.equal(s.c.fade, 1); assert.equal(s.resources(), earned);
  s.applyFade(); assert.equal(s.c.B, null); assert.equal(s.c.mode, "field"); assert.equal(s.resources(), earned); assert.deepEqual(s.calls, { rng: 0, storage: 0 });
});
check("actual defeat and one controlled successful RUN give no victory EXP/gold or level messages", () => {
  const loss = session(); loss.api.party().forEach(m => { m.hp = 0; }); const beforeLoss = loss.resources(); loss.begin(); loss.api.endRound();
  assert.equal(loss.c.B.result, "lose"); assert.equal(loss.resources(), beforeLoss); assert.equal(loss.sounds.includes("LEVEL"), false); loss.next(); assert.equal(loss.c.B, null); assert.equal(loss.c.mode, "gameover");
  const run = session(), beforeRun = run.resources(); run.begin(); run.allowRun(true); run.api.doAction({ kind: "run", who: run.api.party()[0] }); run.allowRun(false);
  assert.equal(run.c.B.result, "run"); assert.equal(run.resources(), beforeRun); assert.equal(run.calls.rng, 1); assert.equal(run.sounds.includes("LEVEL"), false); run.c.B.wait = 0; run.draw();
  run.next(); assert.equal(run.c.B.phase, "out"); run.applyFade(); assert.equal(run.c.mode, "field"); assert.equal(run.resources(), beforeRun); assert.equal(run.calls.storage, 0);
});
check("Portal keeps original level-message text and blinking arrow without the Prism prompt", () => {
  const s = session(320, "portal"), member = s.api.party()[0]; member.exp = member.next - 1; s.api.party().slice(1).forEach(m => { m.hp = 0; }); s.begin().settle(1);
  const message = s.messages()[1]; assert.equal(message, member.name + " REACHES LEVEL " + member.lv + "!"); assert.equal(/MAX HP|ALL STATS/.test(message), false); s.next();
  s.draw(0); assert.equal(s.paints.some(p => p.label === ">" && p.y === 210), false); s.draw(400); assert.ok(s.paints.some(p => p.label === ">" && p.x === 138 && p.y === 210)); assert.equal(s.labels().some(label => label.endsWith(": NEXT")), false);
});
check("controlled former level string and blinking Prism prompt fail the new feedback contract", () => {
  const old = source.replace('lines.push(shown + " REACHES LEVEL " + (m.lv > 999 ? "999+" : m.lv) + "! MAX HP +" + growth.hp + " / MAX MP +" + growth.mp + ". ALL STATS +1.");', 'lines.push(m.name + " REACHES LEVEL " + m.lv + "!");'); assert.notEqual(old, source);
  const s = session(256, "prism", old); nearLevel(s); s.begin().settle(); assert.throws(() => assert.equal(s.messages()[1], levelMessage(s, s.api.party()[0])), assert.AssertionError);
  const blink = source.replace('if ((D.realm_key || "prism") === "prism") text(titlePrompt("confirm", "Z/SPACE").replace(/^PRESS /, "") + ": NEXT", 10, 214, "#fff070");', 'if ((D.realm_key || "prism") === "prism" && Math.floor(performance.now() / 400) % 2) text("Z/SPACE: NEXT", 10, 214, "#fff070");'); assert.notEqual(blink, source);
  const t = session(256, "prism", blink); t.begin().settle(0); t.c.B.wait = 0; t.draw(0); assert.throws(() => assert.ok(t.labels().includes("Z/SPACE: NEXT")), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("victory feedback: " + checks + " focused groups passed; actual offline functions/controlled RUN only, no assets/browser/native acceptance");
