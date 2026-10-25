// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/condition_guide_test.js
// Actual menu/bestiary/status functions and canonical party/foe/gear metadata; paint/storage peers.
// Tiny direct status/cleanup fixtures below are not fights, campaign traversal or runtime acceptance.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, interiors = data("interiors").interiors, menus = data("menus").layouts, spells = data("spells").spells;
const foes = { prism: data("prism-bestiary").types, portal: data("portal-bestiary").types }, bosses = data("prism-bosses").bosses;
const demoRoutes = ["Cinder Forge", "Windcut Aerie", "Sunwell Sanctum", "The Shattered Heart", "Gearwright's Folly"];
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [line("const CHARS ="), line("const tw ="), line("const hit ="), line("function clearActionButtons()"), line("function cursor("), line("const pretty ="),
  between("function gauge(", "/* ---------- party ---------- */"), between("const START_LEVEL =", "/* ---------- maps"),
  between("let menu = null;", "function drawEquip("), between("const STATUS =", "/* ---------- bestiary:"),
  between("const BEHAVIOUR_TEXT =", "/* ---------- battle ---------- */"), line("function wrap("),
  between("function finishBattle()", "function bossGate("), between("function titlePrompt(", "function drawTitle("),
  "function cleanup(now){\n" + cleanup + "\n}",
  "this.api={start:()=>{party=buildParty();},openMenu,menuTick,drawMenu,drawBestiary,drawConditionGuide,bestiaryTick,beastList,meet,conditionList,wrap,cleanup,recruit," +
  "inflict,cure,fieldPoison,roundStatuses,landHit,finishBattle,has,wardMul,conditionText:CONDITION_GUIDE,statuses:STATUS,rounds:ROUNDS," +
  "party:()=>party,reserve:()=>reserve,menu:()=>menu,chars:CHARS,gear:GEAR," +
  "resources:()=>({party,reserve,bag,gold,state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},opened:Array.from(opened),map,P,D,rules:{statuses:STATUS,rounds:ROUNDS,guide:CONDITION_GUIDE}})," +
  "view:()=>({mode,menu,pressed,pressedAt,now,fade,hasFade:!!fadeCb,B,poisonFlash})};"
].join("\n");
let groups = 0;
function check(label, fn) { try { fn(); groups++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism") {
  const paints = [], sounds = [], pops = [], pressed = {}, pressedAt = {}, calls = { rng: 0, storage: 0 }, gear = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors[r])) for (const it of shop.stock || []) if (it.effect || it.attack != null || it.defence != null) gear[it.name] = clone(it);
  const math = Object.create(Math); math.random = () => { calls.rng++; throw new Error("condition browsing must not consume combat RNG"); };
  const known = new Set(parties[realm].members.flatMap(m => m.spells));
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, menus: clone(menus[realm]), rects: { sprites: {} },
      foes: Object.fromEntries(foes[realm].map(f => [f.key, clone(f)])), dungeons: realm === "prism" ? demoRoutes.map(name => ({ name, boss_data: clone(bosses.find(b => b.dungeon === name)) })) : [],
      spells: clone(spells.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2))), ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, Math: math, pressed, pressedAt, now: 0, cursorNow: 0, PAD: null, B: null, fade: 0, fadeCb: null, mode: "field", ending: null,
    map: { kind: "town", cue: "TOWN", retained: true }, P: { x: 7, y: 9, dir: "left" }, opened: new Set(["retained/chest"]),
    state: { beaten: new Set(), ways: new Set(), seen: {}, fish: {}, quests: {}, day: 1, minute: 600, air: null, returnTo: null, steps: 0, sinceBattle: 0 },
    performance: { now: () => c.cursorNow }, clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), sfx: x => sounds.push(x), cue() {}, pop: (target, text, color) => pops.push({ target: target.name, text, color }),
    drawField: () => paints.push({ kind: "field" }), shardCount: () => 0, clockText: () => "D1 10:00", isNight: () => false,
    // Real cursor() supplies original8px dimensions and its1px blink; atlas painting is substituted.
    spr(sheet, name, x, y, sx, sw, sh, scale = 1) { if (name === "ui:Cursor") paints.push({ kind: "cursor", x, y, w: sw * scale, h: sh * scale }); },
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }), g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); } },
    localStorage: { getItem() { calls.storage++; throw new Error("condition guide cannot read saves"); }, setItem() { calls.storage++; throw new Error("condition guide cannot write saves"); }, removeItem() { calls.storage++; throw new Error("condition guide cannot erase saves"); } },
    saveGame() { calls.storage++; throw new Error("condition guide cannot autosave"); }
  };
  vm.createContext(c); vm.runInContext(source, c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify(c.api.resources());
  return { c, api: c.api, paints, sounds, pops, pressed, calls, resources,
    tick(...keys) { c.now += 16; keys.forEach(k => { pressed[k] = true; pressedAt[k] = c.now; }); c.api.menuTick(); c.api.cleanup(c.now); },
    draw(direct = false) { paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), peers = JSON.stringify({ sounds, pops, calls }); c.api[direct ? "drawBestiary" : "drawMenu"]();
      assert.equal(resources(), before, "reading preserves party, resources, discoveries, opened progress, catalogs and position"); assert.equal(JSON.stringify(c.api.view()), view, "reading preserves mode, page, cursors, edges, time and battle state"); assert.equal(JSON.stringify({ sounds, pops, calls }), peers); return paints; },
    labels(confirm = "ABCDEFGH", cancel = "IJKLMNOP") { c.PAD = { devices: () => [{ index: 0 }], label: action => action === "confirm" ? confirm : cancel }; }
  };
}
const at = (s, y, x) => s.paints.filter(p => p.kind === "text" && p.y === y && (x === undefined || p.x === x));
function open(s) { s.api.openMenu(); for (let n = 0; n < 5; n++) s.tick("down"); s.tick("a"); assert.equal(s.api.menu().sub, "bestiary"); return s; }
function help(s) { if (!s.api.menu()) open(s); if (!s.api.menu().bp) s.tick("right"); assert.equal(s.api.menu().bp, 1); return s; }
function choose(s, index) { for (let n = 0; s.api.menu().bc !== index && n < s.api.conditionList().length; n++) s.tick("down"); assert.equal(s.api.menu().bc, index); }
function seen(s) { const keys = Object.keys(s.c.D.foes).slice(0, 3); keys.forEach(k => s.api.meet([s.c.D.foes[k]])); assert.equal(s.api.beastList().length, 3); return s; }
function bounds(s) { for (const p of s.paints.filter(p => ["text", "rect", "window", "cursor"].includes(p.kind))) { assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p)); if (p.kind === "text") assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), p.label); } }
function complete(s, key) {
  s.draw(); const split = s.c.W < 320 ? 104 : 112, columns = Math.floor((s.c.W - split - 24) / 6), record = s.api.statuses[key];
  assert.equal(at(s, 44, split + 12)[0].label, record.word + " / " + record.tag);
  const cures = Object.entries(s.api.gear).filter(([, item]) => ((item.effect || "").match(/cure (\w+)/) || [])[1] === key).map(([name]) => name.toUpperCase());
  const paragraphs = [s.api.rounds[key] ? s.api.rounds[key] + " ROUND-END TICKS." : "NO ROUND EXPIRY.", s.api.conditionText[key][0], cures.length ? cures.join(" OR ") + ": CURE." : s.api.conditionText[key][1]].filter(Boolean);
  const expected = paragraphs.flatMap(p => Array.from(s.api.wrap(p, columns))), body = s.paints.filter(p => p.kind === "text" && p.x === split + 12 && p.y >= 60 && p.y < 182);
  assert.deepEqual(body.map(p => p.label), expected, "every wrapped paragraph is shown, including its end");
  body.forEach((p, i) => { assert.ok(p.x > split && p.x + p.w <= s.c.W - 12 && p.y + p.h <= 181, "body clears divider/footer"); if (i) assert.ok(body[i - 1].y + body[i - 1].h < p.y); });
  s.api.conditionList().forEach((k, i) => { const row = at(s, 44 + i * 12, 22)[0]; assert.equal(row.label, s.api.statuses[k].word); assert.ok(row.x + row.w < split); });
  const arrow = s.paints.find(p => p.kind === "cursor"); assert.ok(arrow && arrow.w === 8); assert.ok(arrow.x + arrow.w < 22 && arrow.y + arrow.h < 182);
  assert.ok(at(s, 188, 12).some(p => p.label === "TIMERS: FRONT AT ROUND END.")); assert.ok(at(s, 200, 12).some(p => p.label === "AFTER BATTLE: FRONT KEEPS ONLY POISON.")); bounds(s);
  return cures;
}
check("fresh BESTIARY opens foes page with independent zeroed condition cursor", () => {
  const s = open(session()), m = s.api.menu(); assert.equal(m.bp, 0); assert.equal(m.bc, 0); assert.equal(m.ii, 0); s.draw(); assert.ok(at(s, 9, 12).some(p => p.label === "BESTIARY")); assert.ok(s.paints.some(p => p.kind === "text" && p.label === "L/R: HELP"));
});
check("empty foe discovery still opens all ten CONDITIONS without inventing an encounter", () => {
  const s = help(open(session())), before = s.resources(); assert.equal(s.api.conditionList().length, 10); assert.deepEqual(Array.from(s.api.conditionList()), Object.keys(s.api.statuses)); s.draw();
  assert.ok(at(s, 10, 12).some(p => p.label === "CONDITIONS")); assert.equal(s.resources(), before); assert.deepEqual(Object.keys(s.c.state.seen), []);
});
check("foe and condition cursors remain independent through both-way cycles and simultaneous navigation", () => {
  const s = open(seen(session())), m = s.api.menu(); s.tick("down"); s.tick("down"); assert.equal(m.ii, 2); s.tick("left"); assert.equal(m.bp, 1); s.tick("up"); assert.equal(m.bc, 9); s.tick("down"); assert.equal(m.bc, 0); s.tick("down"); s.tick("down"); assert.equal(m.bc, 2);
  s.tick("left", "right", "up", "down"); assert.equal(m.bp, 0); assert.equal(m.ii, 2); assert.equal(m.bc, 2); s.tick(); assert.equal(m.ii, 2); s.tick("up"); assert.equal(m.ii, 1);
  s.tick("right"); assert.equal(m.bp, 1); assert.equal(m.bc, 2); assert.equal(m.ii, 1); s.tick("left"); assert.equal(m.bp, 0); assert.equal(s.api.beastList().length, 3);
});
check("Confirm/Back take priority over LR/UD and consume close edges; a fresh entry resets both pages", () => {
  for (const keys of [["a"], ["b"], ["a", "b", "start", "left", "right", "up", "down"]]) { const s = help(open(seen(session()))), m = s.api.menu(); choose(s, 9); const before = s.resources(); s.tick(...keys); assert.equal(m.sub, null); assert.equal(s.resources(), before);
    for (const k of ["a", "b", "start", "left", "right", "up", "down"]) assert.equal(!!s.pressed[k], false); s.tick(); assert.equal(m.sub, null); s.tick("a"); assert.equal(m.sub, "bestiary"); assert.equal(m.bp, 0); assert.equal(m.bc, 0); assert.equal(m.ii, 0); }
});
for (const width of [320, 256]) check("all ten complete condition paragraphs, cures, durations and cursor frames fit at " + width, () => {
  const s = help(open(session(width))); s.labels(); const list = Array.from(s.api.conditionList());
  for (const [index, key] of list.entries()) { choose(s, index); for (const blink of [0, 300]) { s.c.cursorNow = blink; complete(s, key); assert.equal(s.paints.find(p => p.kind === "cursor").x, blink ? 11 : 10); }
    assert.ok(at(s, 10).some(p => p.label === (index + 1) + "/10")); assert.equal(at(s, 212, 12)[0].label, "UP/DOWN ABCDEFGH/IJKLMNOP: CLOSE");
  }
  const before = JSON.stringify(s.paints); s.draw(); assert.equal(JSON.stringify(s.paints), before, "painting is deterministic apart from the explicit cursor clock");
});
check("direct remedies come only from exact current gear cure metadata, never Feather revival", () => {
  const s = help(open(session())), list = Array.from(s.api.conditionList());
  for (const [index, key] of list.entries()) { choose(s, index); const cures = complete(s, key); assert.ok(!cures.includes("FEATHER OF WAKING"));
    const expected = Object.entries(s.c.D.gear).filter(([, item]) => item.effect === "cure " + key).map(([name]) => name.toUpperCase()); assert.deepEqual(cures, expected);
    if (key === "poison") assert.ok(cures.includes("ANTIDOTE LEAF")); else if (key === "sleep") assert.ok(cures.includes("WAKE BELL"));
  }
});
check("displayed infliction durations and haste/slow replacement match the small real status helpers", () => {
  const s = session(), m = s.api.party()[0];
  for (const key of s.api.conditionList()) { m.status = {}; assert.equal(s.api.inflict(m, key), true); assert.equal(m.status[key], key === "poison" ? true : s.api.rounds[key] || 3); assert.equal(s.api.inflict(m, key), false); }
  m.status = {}; s.api.inflict(m, "haste"); s.api.inflict(m, "slow"); assert.equal(m.status.haste, undefined); assert.equal(m.status.slow, s.api.rounds.slow); s.api.inflict(m, "haste"); assert.equal(m.status.slow, undefined); assert.equal(m.status.haste, s.api.rounds.haste);
  for (const key of ["poison", "sleep"]) { s.api.inflict(m, key); assert.equal(s.api.cure(m, key), true); assert.equal(s.api.has(m, key), false); assert.equal(s.api.cure(m, key), false); }
  assert.equal(s.api.wardMul({ status: { protect: 4 } }), 0.6);
});
check("real field poison includes reserves every fourth step, remains nonlethal and ignores burn", () => {
  const s = session(); s.api.recruit("Cinder Forge"); const front = s.api.party()[0], reserve = s.api.reserve()[0], burned = s.api.party()[1];
  front.hp = 1; front.status = { poison: true }; reserve.hp = 2; reserve.status = { poison: true }; burned.hp = 2; burned.status = { burn: 3 };
  s.c.state.steps = 3; s.api.fieldPoison(); assert.equal(reserve.hp, 2); s.c.state.steps = 4; s.api.fieldPoison(); assert.equal(front.hp, 1); assert.equal(reserve.hp, 1); assert.equal(burned.hp, 2); assert.equal(reserve.status.poison, true);
});
check("real round ticks preserve sleep/confuse until hit, leave reserves untouched, and completion cleans only front nonpoison", () => {
  const s = session(); s.api.recruit("Cinder Forge"); const front = s.api.party()[0], reserve = s.api.reserve()[0]; front.hp = 1; front.status = { poison: true, burn: 3, sleep: 3, confuse: 3, protect: 4 }; reserve.hp = 2; reserve.status = { poison: true, burn: 3, sleep: 3, confuse: 3 };
  const saved = JSON.stringify(reserve); s.c.B = { foes: [], flash: {}, pops: [], result: "win", boss: false, prevCue: "TOWN", endLines: [] }; s.api.roundStatuses(); assert.equal(front.hp, 1); assert.equal(front.status.sleep, 2); assert.equal(front.status.confuse, 2); assert.equal(front.status.burn, 2); assert.equal(JSON.stringify(reserve), saved);
  assert.equal(s.api.landHit(front, 1), 1); assert.equal(front.status.sleep, undefined); assert.equal(front.status.confuse, undefined); assert.equal(front.status.poison, true);
  // Cleanup-only finishBattle call: no victory calculation, initiative, actor execution or fade is run.
  s.api.finishBattle(); assert.equal(JSON.stringify(front.status), '{"poison":true}'); assert.equal(JSON.stringify(reserve), saved); assert.equal(s.c.fade, 1); assert.equal(s.c.B.phase, "out");
});
check("mapped fallback labels remain complete and looking never touches native storage or RNG", () => {
  const s = help(open(session(256))); s.draw(); assert.equal(at(s, 212, 12)[0].label, "UP/DOWN Z/SPACE/X/ESC: CLOSE"); s.labels("INVALID LABEL", "<BAD>"); s.draw(); bounds(s); assert.equal(at(s, 212, 12)[0].label, "UP/DOWN Z/SPACE/X/ESC: CLOSE"); assert.deepEqual(s.calls, { rng: 0, storage: 0 });
});
check("Portal retains original bestiary controls and painter rather than entering CONDITIONS", () => {
  const s = open(seen(session(256, "portal"))), m = s.api.menu(); assert.equal(m.bp, undefined); s.tick("right", "left"); assert.equal(m.bp, undefined); assert.equal(m.ii, 0); s.draw(true); assert.ok(at(s, 9, 12).some(p => p.label === "BESTIARY")); assert.ok(!s.paints.some(p => p.kind === "text" && p.label === "CONDITIONS"));
  s.tick("down"); assert.equal(m.ii, 1); s.tick("a", "b"); assert.equal(m.sub, null); assert.equal(s.pressed.a, false); assert.equal(s.pressed.b, false); s.tick(); assert.equal(m.sub, null);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("condition guide: " + groups + " focused groups passed; fake painters/storage, direct status/cleanup seams only, no runtime acceptance");
