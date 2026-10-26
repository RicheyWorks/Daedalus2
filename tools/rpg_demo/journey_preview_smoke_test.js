// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/journey_preview_smoke_test.js GENERATED_HTML
// Diagnostic wiring smoke only. Tiny DOM/canvas/focus/event peers are not a browser engine,
// original art, real input-device lifecycle, durable storage, game/runtime or native acceptance.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");

function diagnostic(file) {
  const resolved = path.resolve(file), stat = fs.statSync(resolved);
  assert.ok(stat.isFile() && stat.size > 0 && stat.size <= 8 * 1024 * 1024, "bounded generated HTML file required");
  const html = fs.readFileSync(resolved, "utf8"), listeners = [], microtasks = [], elements = new Map();
  const metrics = { paintCalls: 0, nativeAccesses: 0 }, required = ["formation", "healing", "pack", "battle", "plan", "menu", "location", "width", "screen", "notice", "view", "labels", "error"];
  let document;
  function canvasContext() { const draw = () => { metrics.paintCalls++; }; return { fillRect: draw, strokeRect: draw, fillText: draw, drawImage: draw, fillStyle: "", strokeStyle: "", font: "" }; }
  function element(tagName, id = "", value = "") {
    const local = [], ctx = tagName === "CANVAS" ? canvasContext() : null;
    return { tagName, id, value, textContent: "", dataset: {}, width: 320, height: 224, local,
      addEventListener(type, fn, capture = false) { local.push({ type, fn, capture: !!capture }); },
      focus() { document.activeElement = this; }, getContext(kind) { assert.equal(kind, "2d"); assert.ok(ctx); return ctx; },
      getBoundingClientRect() { return { left: 0, top: 0, width: this.width, height: this.height }; }
    };
  }
  // Parse only the diagnostic's explicit controls, not arbitrary HTML or a DOM framework.
  for (const id of required) {
    const match = html.match(new RegExp("<(button|select|canvas|p|pre)\\b[^>]*\\bid=[\"']" + id + "[\"'][^>]*>", "i"));
    assert.ok(match, "required diagnostic control: " + id); const tag = match[1].toUpperCase();
    const value = id === "location" ? "World" : id === "width" ? "320" : ""; elements.set(id, element(tag, id, value));
  }
  const keys = [...html.matchAll(/<button\b[^>]*data-key=["']([^"']+)["'][^>]*>/gi)].map(m => { const e = element("BUTTON"); e.dataset.key = m[1]; return e; });
  const stages = [...html.matchAll(/<button\b[^>]*data-stage=["']([^"']+)["'][^>]*>/gi)].map(m => { const e = element("BUTTON"); e.dataset.stage = m[1]; return e; });
  assert.deepEqual(keys.map(e => e.dataset.key), ["up", "down", "left", "right", "a", "b", "start"]);
  assert.deepEqual(stages.map(e => Number(e.dataset.stage)), [0, 1, 3, 4, 5]);
  const options = id => { const select = html.match(new RegExp("<select\\b[^>]*id=[\"']" + id + "[\"'][^>]*>([\\s\\S]*?)<\\/select>", "i")); assert.ok(select); return [...select[1].matchAll(/<option\b[^>]*>([^<]*)<\/option>/gi)].map(m => m[1]); };
  const choices = { location: options("location"), width: options("width") };
  assert.equal(choices.location[0], "World"); assert.equal(choices.width[0], "320");
  document = { hidden: false, activeElement: elements.get("screen"), hasFocus: () => true,
    getElementById(id) { assert.ok(elements.has(id), "unexpected DOM id: " + id); return elements.get(id); },
    querySelectorAll(selector) { assert.ok(selector === "[data-key]" || selector === "[data-stage]", selector); return selector === "[data-key]" ? keys : stages; },
    createElement(tag) { assert.equal(tag, "canvas", "only explicit palette canvases are needed"); return element("CANVAS"); }
  };
  const browserWindow = { addEventListener(type, fn, capture = false) { listeners.push({ type, fn, capture: !!capture }); } };
  const context = { document, window: browserWindow, queueMicrotask(fn) { assert.equal(typeof fn, "function"); microtasks.push(fn); } };
  function forbidden(name) { metrics.nativeAccesses++; throw new Error("native/network/import capability is outside this diagnostic: " + name); }
  for (const name of ["localStorage", "sessionStorage", "indexedDB", "fetch", "XMLHttpRequest", "WebSocket", "EventSource", "Worker", "importScripts", "require", "process"]) {
    Object.defineProperty(context, name, { configurable: false, get() { return forbidden(name); } });
    Object.defineProperty(browserWindow, name, { configurable: false, get() { return forbidden("window." + name); } });
  }
  vm.createContext(context, { codeGeneration: { strings: false, wasm: false } });
  const call = new vm.Script("__smokeFunction(__smokeEvent)", { filename: "diagnostic event peer" });
  function invoke(fn, event) { assert.equal(typeof fn, "function"); context.__smokeFunction = fn; context.__smokeEvent = event;
    try { call.runInContext(context, { timeout: 1000 }); } finally { delete context.__smokeFunction; delete context.__smokeEvent; }
  }
  function healthy() { assert.equal(elements.get("error").textContent, "", "diagnostic reported an error"); assert.equal(metrics.nativeAccesses, 0); }
  function flush() { for (let n = 0; microtasks.length; n++) { assert.ok(n < 100, "bounded diagnostic microtasks"); invoke(microtasks.shift()); healthy(); } healthy(); }
  const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]; assert.ok(scripts.length > 0 && scripts.length <= 4);
  scripts.forEach((script, i) => { assert.ok(!/\bsrc\s*=|\btype\s*=\s*["']module/i.test(script[1]), "only generated inline scripts may execute"); new vm.Script(script[2], { filename: resolved + " inline " + (i + 1) }).runInContext(context, { timeout: 2000 }); }); flush();
  function event(target, extra = {}) { const e = { target, ctrlKey: false, metaKey: false, altKey: false, repeat: false, defaultPrevented: false, stopped: false,
    preventDefault() { this.defaultPrevented = true; }, stopImmediatePropagation() { this.stopped = true; }, ...extra }; return e; }
  function dispatch(list, type, e) { for (const entry of list.filter(l => l.type === type).sort((a, b) => Number(b.capture) - Number(a.capture))) { if (e.stopped) break; invoke(entry.fn, e); healthy(); } flush(); }
  function click(e) { invoke(e.onclick, event(e)); flush(); }
  return { metrics, elements, choices,
    view() { healthy(); const result = JSON.parse(elements.get("view").textContent); assert.equal(result.diagnostic, true); return result; },
    labels: () => elements.get("labels").textContent.split("\n"), notice: () => elements.get("notice").textContent,
    scene: id => click(elements.get(id)), key: k => { const e = keys.find(e => e.dataset.key === k); assert.ok(e, k); click(e); },
    stage: n => { const e = stages.find(e => Number(e.dataset.stage) === n); assert.ok(e, String(n)); click(e); },
    change(id, value) { assert.ok(choices[id].includes(String(value)), "actual select option required"); const e = elements.get(id); e.value = String(value); document.activeElement = e; invoke(e.onchange, event(e)); flush(); },
    keyboard(code, key, { up = false, repeat = false } = {}) { const e = event(document.activeElement, { code, key, repeat }); dispatch(listeners, up ? "keyup" : "keydown", e); return e; },
    pointer(x, y) { const cv = elements.get("screen"); dispatch(cv.local, "pointerdown", event(cv, { clientX: x, clientY: y })); }
  };
}

function main() {
  if (process.argv.length !== 3) throw new Error("usage: journey_preview_smoke_test.js GENERATED_HTML");
  const d = diagnostic(process.argv[2]); let groups = 0;
  function check(label, fn) { try { fn(); groups++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
  const clone = x => JSON.parse(JSON.stringify(x)), names = v => v.roster.map(m => m.name);
  const state = v => JSON.stringify({ roster: v.roster, bag: v.bag, gold: v.gold, memorySaves: v.memorySaves });
  const line = prefix => { const found = d.labels().find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
  function type(text) { for (const key of text) { const e = d.keyboard("Key" + key.toUpperCase(), key); assert.equal(e.stopped, true, "real name capture stops the logical input adapter"); assert.equal(e.defaultPrevented, true); } }
  function packItem(name) { for (let n = 0; d.labels()[0] !== name.toUpperCase() && n < 32; n++) d.key("down"); assert.equal(d.labels()[0], name.toUpperCase(), "selected full pack header"); }
  function chooseCommand(index) { for (let n = 0; d.view().battle.command !== index && n < 8; n++) d.key("down"); assert.equal(d.view().battle.command, index); d.key("a"); }
  function menuEntry(index) { d.scene("menu"); for (let n = 0; n < index; n++) d.key("down"); assert.equal(d.view().menu.index, index); d.key("a"); }
  check("boot retains the control/JSON/label contract and explicit diagnostic boundaries", () => {
    const v = d.view(); assert.equal(v.scene, "journey"); assert.equal(v.mode, "menu"); assert.equal(v.width, 320); assert.equal(v.location, "World"); assert.equal(v.roster.length, 8);
    assert.equal(v.memorySaves.writes, 0); assert.deepEqual(v.memorySaves.keys, []); assert.ok(d.metrics.paintCalls > 0); assert.match(d.notice(), /Disposable journey scene/);
  });
  check("all five scene buttons boot their actual named chooser/renderer", () => {
    for (const [id, sub, heading] of [["formation", "order", "FORMATION"], ["healing", "magic-target", "MEND"], ["pack", "item", "HERB TONIC"], ["battle", "target", "ATTACK"], ["plan", "plan", "TURN PLAN"]]) {
      d.scene(id); const v = d.view(); assert.equal(v.scene, id); assert.equal(v.sub, sub); assert.ok(d.labels().includes(heading), heading); assert.equal(v.memorySaves.writes, 0);
      if (id === "plan") { assert.equal(v.battle.acts.length, 3); assert.equal(v.battle.chooser, 3); assert.equal(v.battle.deterministicInitiativeRolls, 0); }
    }
  });
  check("capture-before-bubble naming repaints typed text, repeat/fresh Enter and Escape/grid cancellation", () => {
    d.scene("formation"); const before = d.view(), original = names(before); d.keyboard("Enter", "Enter"); assert.equal(d.view().mode, "name"); assert.equal(d.view().naming.name, "");
    d.keyboard("Enter", "Enter", { repeat: true }); assert.equal(d.view().mode, "name", "opening Enter repeat cannot finish");
    type("NOVA"); assert.equal(d.view().naming.name, "NOVA"); assert.ok(d.labels().some(s => s.trim() === "NOVA"), "capture microtask repaints after mutation");
    d.keyboard("Enter", "Enter", { up: true }); d.keyboard("Enter", "Enter"); let v = d.view(); assert.equal(v.mode, "menu"); assert.equal(v.sub, "order"); assert.equal(v.roster[0].name, "Nova"); assert.deepEqual(names(v).slice(1), original.slice(1)); assert.equal(v.memorySaves.writes, 0);
    d.key("start"); type("OTHER"); d.keyboard("Escape", "Escape"); v = d.view(); assert.equal(v.mode, "menu"); assert.equal(v.roster[0].name, "Nova");
    d.key("start"); d.pointer(26, 64); assert.equal(d.view().naming.name, "A"); d.pointer(26, 194); assert.equal(d.view().mode, "menu"); assert.equal(d.view().roster[0].name, "Nova");
  });
  check("care and pack controls execute real forecasted healing/MP/revival transactions without autosaving", () => {
    d.scene("healing"); let before = d.view(); assert.equal(before.menu.target, 5); const forecast = line("IF CAST: HP ").match(/^IF CAST: HP (\d+)>(\d+) \+(\d+)$/); assert.ok(forecast); assert.equal(Number(forecast[1]), before.roster[5].hp);
    d.key("a"); let after = d.view(); assert.equal(after.roster[5].hp, Number(forecast[2])); assert.equal(after.roster[1].mp, before.roster[1].mp - 5); assert.deepEqual(after.bag, before.bag); assert.equal(after.memorySaves.writes, 0); d.key("b"); assert.equal(d.view().sub, "magic");
    d.scene("pack"); before = d.view(); const hp = line("IF USED: HP ").match(/^IF USED: HP (\d+)>(\d+) \+(\d+)$/); assert.ok(hp); d.key("a"); after = d.view(); assert.equal(after.roster[0].hp, Number(hp[2])); assert.equal(after.bag["Herb Tonic"], before.bag["Herb Tonic"] - 1);
    packItem("Clear Draught"); d.key("right"); before = d.view(); assert.equal(before.menu.who, 1); const mp = line("IF USED: MP ").match(/^IF USED: MP (\d+)>(\d+) \+(\d+)$/); assert.ok(mp);
    d.key("a"); after = d.view(); assert.equal(after.roster[1].mp, Number(mp[2])); assert.equal(after.bag["Clear Draught"], before.bag["Clear Draught"] - 1);
    packItem("Feather of Waking"); for (let n = 0; n < 3; n++) d.key("right"); before = d.view(); assert.equal(before.menu.who, 4); assert.equal(before.roster[4].hp, 0); const revive = line("REVIVE: HP ").match(/^REVIVE: HP 0>(\d+)\. STATUS CLEARED\.$/); assert.ok(revive);
    d.key("a"); after = d.view(); assert.equal(after.roster[4].hp, Number(revive[1])); assert.deepEqual(after.roster[4].status, {}); assert.equal(after.bag["Feather of Waking"], before.bag["Feather of Waking"] - 1); assert.equal(after.memorySaves.writes, 0); assert.equal(after.gold, before.gold);
    packItem("Prismscale Koi"); assert.ok(d.view().menu.item >= 6, "full seeded pack scrolls beyond the six-row viewport"); assert.ok(line("BAG ").includes("/"));
  });
  check("battle target identity reaches PLAN; closing cannot also undo and a fresh Back does", () => {
    d.scene("battle"); const resources = state(d.view()); d.key("right"); assert.equal(d.view().battle.target, 1); d.key("a"); let v = d.view(); assert.equal(v.battle.chooser, 1); assert.equal(v.battle.acts.length, 1); assert.equal(v.battle.acts[0].target.foeSlot, 2);
    d.key("up"); d.key("a"); v = d.view(); assert.equal(v.sub, "plan"); assert.ok(d.labels().includes("TURN PLAN")); assert.ok(d.labels().some(s => s.endsWith(" / FOE 2"))); assert.ok(d.labels().includes("CHOICE ORDER. TURN ORDER MAY DIFFER."));
    d.key("b"); v = d.view(); assert.equal(v.sub, null); assert.equal(v.battle.acts.length, 1); assert.equal(v.battle.chooser, 1); assert.equal(state(v), resources);
    d.key("b"); v = d.view(); assert.equal(v.battle.acts.length, 0); assert.equal(v.battle.chooser, 0); assert.equal(v.battle.phase, "cmd"); assert.equal(v.battle.deterministicInitiativeRolls, 0);
  });
  check("the three-choice PLAN can build initiative and then stops before every battle action", () => {
    d.scene("plan"); const before = d.view(), resources = state(before); assert.equal(before.battle.acts.length, 3); assert.equal(before.battle.chooser, 3); assert.equal(before.battle.queueLength, 0);
    d.key("a"); assert.equal(d.view().sub, null); assert.equal(d.view().battle.acts.length, 3); chooseCommand(3); let v = d.view(); assert.equal(v.battle.phase, "act"); assert.equal(v.battle.stoppedBeforeActions, true); assert.equal(v.battle.queueLength, 7); assert.ok(v.battle.deterministicInitiativeRolls > 0); assert.equal(state(v), resources);
    const battle = clone(v.battle); d.key("a"); v = d.view(); assert.deepEqual(v.battle, battle); assert.equal(state(v), resources); assert.match(d.notice(), /Action execution is excluded/);
  });
  check("width/location/stage controls retain JOURNEY bindings and current-floor isolation", () => {
    d.scene("menu"); d.change("width", 256); assert.equal(d.view().width, 256); assert.equal(d.elements.get("screen").width, 256); d.change("location", "Cinder Forge");
    d.key("up"); d.key("a"); let v = d.view(); assert.equal(v.sub, "journey"); assert.equal(v.menu.page, 0); assert.equal(v.page, v.menu.page); assert.equal(v.route, v.menu.item);
    d.key("right"); assert.equal(d.view().menu.page, 1); d.key("right"); v = d.view(); assert.equal(v.menu.page, 2); assert.ok(d.labels().includes("FLOOR MAP")); assert.match(v.anchor.label, /INSIDE CINDER FORGE/);
    const route = v.menu.item, resources = state(v); d.key("up"); d.key("a"); assert.equal(d.view().menu.item, route); assert.equal(state(d.view()), resources); d.key("left"); assert.ok(d.labels().some(s => s.includes(": PIN X ")), "floor Confirm cannot secretly pin a route");
    for (const stage of [0, 1, 3, 4, 5]) { d.stage(stage); assert.equal(d.view().stage, stage); }
    d.change("location", "Castle"); assert.equal(d.view().menu.page, 0); assert.match(d.view().anchor.label, /INSIDE CASTLE/); d.key("left"); assert.equal(d.view().menu.page, 1); d.key("right"); assert.equal(d.view().menu.page, 0, "non-dungeon page cycle remains two pages");
    d.change("width", 320); assert.equal(d.view().width, 320); d.change("location", "World"); assert.equal(d.view().location, "World");
  });
  check("SAVE uses only disposable memory and excluded scenes remain notices", () => {
    d.change("location", "Cinder Forge"); menuEntry(7); assert.equal(d.view().memorySaves.writes, 0, "normal dungeon SAVE refusal is retained");
    d.change("location", "Town"); menuEntry(7); let v = d.view(); assert.equal(v.memorySaves.writes, 1); assert.deepEqual(v.memorySaves.keys, ["prism.save.v1"]); assert.equal(v.memorySaves.reads, 0);
    d.key("a"); assert.equal(d.view().memorySaves.writes, 2); menuEntry(3); assert.match(d.notice(), /STATUS excluded/); assert.equal(d.view().sub, null);
    d.scene("formation"); v = d.view(); assert.equal(v.memorySaves.writes, 0); assert.deepEqual(v.memorySaves.keys, []); assert.equal(d.metrics.nativeAccesses, 0);
  });
  console.log("journey preview: " + groups + " diagnostic wiring smoke groups passed; fake DOM/canvas/event peers only, no browser/art/device/runtime acceptance");
}
if (require.main === module) main();
